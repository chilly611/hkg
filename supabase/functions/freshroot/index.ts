// freshroot · the FreshRoot API. One Supabase Edge Function.
//
//   GET  /v1/sources                         v_source_status, each row with lookup_url (the source row's official
//                                            public lookup, when it carries one) and, for a catalog source, the
//                                            catalog's release_date and file_period
//   GET  /v1/rosters/{roster_id}             the roster, one summary row per NPI with provider facts and the five
//                                            current checks (state license, state board action, NPI, OIG, SAM)
//   GET  /v1/providers/{npi}/claims          provider facts and current receipts, each with its history; a license
//                                            receipt that matched more than one license lists them all
//   GET  /v1/receipts/{id}/source            the evidence behind one receipt: the source rows it was built from as
//                                            stored (when retained), the artifact hash, capture time and writer
//   GET  /v1/deltas?roster_id=&cursor=&limit= receipts created after the cursor, with change_kind (new,
//                                            status_change, field_change, refresh). A board action receipt that
//                                            lists an action its prior one did not is a status_change.
//   GET  /v1/coverage?roster_id=             roster_coverage(): covered today, in 30 days, under license, never
//   GET  /v1/lookup?q=&state=&roster_id=     up to 20 individual providers by NPI or name, each marked on_roster.
//                                            Reads only; it writes nothing.
//   POST /v1/rosters/{roster_id}/npis        {"npis": [...up to 20]}: adds them to the roster, then writes their
//                                            receipts with the packet builder's SQL writer. With /jobs below, the
//                                            only write routes, so receipts are written only for roster NPIs.
//   POST /v1/rosters/{roster_id}/jobs        up to 5,000 NPIs, as JSON ({"npis": [...]} or a bare array) or as CSV
//                                            (text/csv, a header row with an npi column). An optional state (a
//                                            "state" CSV column, or {"npi", "state"} items) names the license to
//                                            check, as in the packet builder's roster file; without one the board
//                                            comes from the NPPES license states, as on /npis. Creates a freshroot_jobs
//                                            row and answers 202 with the job id at once. The worker is this
//                                            function, in a background task (EdgeRuntime.waitUntil): batches of 100
//                                            NPIs, each added to the roster and receipted by the same writer as
//                                            /npis, with the bulk anomaly guard read after every batch.
//   GET  /v1/jobs/{job_id}                   the job: queued, running, done or failed; added, receipted, unmatched.
//                                            A job whose worker stopped (time limit, restart) has a lapsed lease;
//                                            this GET claims it again and the work carries on from the last batch.
//   GET  /v1/rosters/{roster_id}/export      a zip: receipts.csv, receipts.json, unmatched.csv, coverage.md and
//                                            report.md (one page, every number with the dates it rests on).
//
// Auth: X-FreshRoot-Key, SHA-256 hashed and looked up in api_tenants. No key or an unknown key: 401.
// A tenant reads only the rosters in its roster_ids, and only NPIs on those rosters: anything else is 403.
// Receipts from a source with accepted_for_sale = false are left out unless ?include_unaccepted=true, and every
// row carries shippable and rights ("pending" while the source is not accepted for sale).
// The service role key comes from the function's Supabase secrets; it is never sent to a caller.
// SQL: migrations/2026-10-27_freshroot_api.sql; the name search index is migrations/2026-10-28_freshroot_lookup_index.sql;
// jobs and rosters.test are sql/2026-11-04_jobs.sql beside this file.
// Deployed with verify_jwt = false: the tenant key is the auth.

const SUPABASE_URL = (Deno.env.get("SUPABASE_URL") ?? "").replace(/\/$/, "");
const SERVICE_KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") ?? "";

const DEFAULT_LIMIT = 500;
const MAX_LIMIT = 5000;
const SITE_ORIGIN = "https://health.theknowledgegardens.com";
const LOCALHOST_ORIGIN = /^http:\/\/localhost(:\d{1,5})?$/;

class HttpError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

// A PostgREST error, with the Postgres error code when there is one (57014 is a statement timeout).
class UpstreamError extends HttpError {
  constructor(public pgCode: string | null) {
    super(502, "upstream query failed");
  }
}

function corsHeaders(origin: string | null): Record<string, string> {
  const h: Record<string, string> = { "Vary": "Origin" };
  if (origin && (origin === SITE_ORIGIN || LOCALHOST_ORIGIN.test(origin))) {
    h["Access-Control-Allow-Origin"] = origin;
    h["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS";
    h["Access-Control-Allow-Headers"] = "X-FreshRoot-Key, Content-Type";
    h["Access-Control-Max-Age"] = "600";
    h["Access-Control-Expose-Headers"] = "Content-Disposition";
  }
  return h;
}

function json(body: unknown, status: number, cors: Record<string, string>): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { ...cors, "Content-Type": "application/json", "Cache-Control": "no-store" },
  });
}

// PostgREST with the service role key, the same way scripts/ingestion/core_run.py talks to it:
// the key goes in apikey; a legacy JWT key also goes in Authorization.
// prefer is sent as the Prefer header (an insert's conflict handling, or count=exact).
type Method = "GET" | "POST" | "PATCH";
async function pgrst(method: Method, path: string, params?: Record<string, string>, body?: unknown, prefer?: string) {
  const qs = params ? "?" + new URLSearchParams(params).toString() : "";
  const headers: Record<string, string> = { "apikey": SERVICE_KEY, "Content-Type": "application/json" };
  if (SERVICE_KEY.startsWith("eyJ")) headers["Authorization"] = `Bearer ${SERVICE_KEY}`;
  if (prefer) headers["Prefer"] = prefer;
  const resp = await fetch(`${SUPABASE_URL}/rest/v1/${path}${qs}`, {
    method,
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const text = await resp.text();
  if (!resp.ok) {
    console.error(`PostgREST ${method} ${path} -> ${resp.status}: ${text.slice(0, 500)}`);
    let code: string | null = null;
    try { code = JSON.parse(text)?.code ?? null; } catch { /* not JSON */ }
    throw new UpstreamError(code);
  }
  return { text, headers: resp.headers };
}

async function rest(method: Method, path: string, params?: Record<string, string>, body?: unknown, prefer?: string) {
  const { text } = await pgrst(method, path, params, body, prefer);
  return text ? JSON.parse(text) : null;
}

// Every row of a GET, a page of 1,000 at a time (PostgREST's cap). order must make the pages disjoint.
async function restAll(path: string, params: Record<string, string>, order: string): Promise<Row[]> {
  const out: Row[] = [];
  for (let offset = 0; ; offset += PAGE) {
    const page = await rest("GET", path, { ...params, order, limit: String(PAGE), offset: String(offset) });
    out.push(...page);
    if (page.length < PAGE) return out;
  }
}
const PAGE = 1000;

// Members on a roster, from Content-Range (count=exact is fine here; it times out on providers).
async function rosterCount(rosterId: string): Promise<number> {
  const { headers } = await pgrst("GET", "roster_members", { select: "npi", roster_id: `eq.${rosterId}`, limit: "1" },
    undefined, "count=exact");
  return Number(headers.get("content-range")?.split("/")[1] ?? 0);
}

const rpc = (fn: string, args: Record<string, unknown>) => rest("POST", `rpc/${fn}`, undefined, args);

async function sha256Hex(s: string): Promise<string> {
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(s));
  return Array.from(new Uint8Array(digest), (b) => b.toString(16).padStart(2, "0")).join("");
}

type Tenant = { id: string; name: string; roster_ids: string[] };

async function authenticate(req: Request): Promise<Tenant> {
  const key = req.headers.get("x-freshroot-key");
  if (!key) throw new HttpError(401, "missing X-FreshRoot-Key");
  const rows = await rest("GET", "api_tenants", {
    select: "id,name,roster_ids",
    key_hash: `eq.${await sha256Hex(key)}`,
  });
  if (!rows?.length) throw new HttpError(401, "unknown key");
  return rows[0];
}

function requireRoster(tenant: Tenant, rosterId: string | null): string {
  if (!rosterId) throw new HttpError(400, "roster_id is required");
  // Same answer whether or not the roster exists: a tenant learns nothing about rosters it is not bound to.
  if (!tenant.roster_ids.includes(rosterId)) throw new HttpError(403, "roster not available to this key");
  return rosterId;
}

// Cursor: base64url of "<created_at>|<receipt id>" from the last row of a page (created_at keeps microseconds).
function encodeCursor(createdAt: string, id: string): string {
  return btoa(`${createdAt}|${id}`).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

function decodeCursor(cursor: string): { createdAt: string; id: string } {
  try {
    const [createdAt, id] = atob(cursor.replace(/-/g, "+").replace(/_/g, "/")).split("|");
    if (!createdAt || !/^[0-9a-f-]{36}$/.test(id) || isNaN(Date.parse(createdAt.replace(" ", "T")))) throw 0;
    return { createdAt, id };
  } catch {
    throw new HttpError(400, "bad cursor");
  }
}

// PostgREST takes these lists in the query string and caps a response at 1000 rows; chunks of 100 keep each URL
// short and each response well under the cap (a roster NPI has a handful of current receipts). At most 8 chunks are
// in flight at once, so a 5,000-NPI roster is 50 requests, not 50 at the same moment.
const IN_CHUNK = 100;
const IN_PARALLEL = 8;
// deno-lint-ignore no-explicit-any
type Row = Record<string, any>;
async function inChunks(values: string[], fetchChunk: (inList: string) => Promise<Row[]>): Promise<Row[]> {
  const chunks: string[][] = [];
  for (let i = 0; i < values.length; i += IN_CHUNK) chunks.push(values.slice(i, i + IN_CHUNK));
  const out: Row[][] = new Array(chunks.length);
  let next = 0;
  const lane = async () => {
    while (next < chunks.length) {
      const i = next++;
      out[i] = await fetchChunk(`in.(${chunks[i].join(",")})`);
    }
  };
  await Promise.all(Array.from({ length: Math.min(IN_PARALLEL, chunks.length) }, lane));
  return out.flat();
}

type ProviderFacts = {
  first_name: string | null;
  middle_name: string | null;
  last_name: string | null;
  credential: string | null;
  primary_taxonomy: { code: string; description: string | null } | null;
  practice_states: string[];
  license_states: string[];
};

// Name, credential suffix and primary taxonomy from providers (NPPES), joined on NPI; taxonomy through
// provider_taxonomies.provider_id. NPPES credentials come as typed ("M.D.,"), so only edge spaces and commas go.
// license_states are the NPPES "Provider License Number State Code" values, kept per taxonomy in
// provider_taxonomies.license_state (provider_credentials is empty), and practice_states the NPPES practice-address
// states. Both are loaded for only part of the registry (license states for about 19K NPIs, practice addresses for
// about 572K of 9.4M), so an empty list means the extract names none, never that we picked one.
const FACTS_SELECT = "npi,first_name,middle_name,last_name,credential," +
  "provider_taxonomies(taxonomy_code,taxonomy_description,is_primary,license_state),provider_addresses(state,address_type)";
const PRACTICE_ONLY = { "provider_addresses.address_type": "eq.practice" };

const stateList = (vals: (string | null | undefined)[]) =>
  [...new Set(vals.filter(Boolean).map((s) => String(s).trim().toUpperCase()))].filter((s) => /^[A-Z]{2}$/.test(s)).sort();

function toFacts(p: Row): ProviderFacts {
  const taxes = p.provider_taxonomies ?? [];
  const tax = taxes.find((t: { is_primary: boolean }) => t.is_primary);
  return {
    first_name: p.first_name,
    middle_name: p.middle_name,
    last_name: p.last_name,
    credential: p.credential?.replace(/^[\s,]+|[\s,]+$/g, "") || null,
    primary_taxonomy: tax ? { code: tax.taxonomy_code, description: tax.taxonomy_description } : null,
    practice_states: stateList((p.provider_addresses ?? []).map((a: Row) => a.state)),
    license_states: stateList(taxes.map((t: Row) => t.license_state)),
  };
}

async function providerFacts(npis: string[]): Promise<Map<string, ProviderFacts>> {
  const rows = await inChunks(npis, (inList) => rest("GET", "providers", { select: FACTS_SELECT, ...PRACTICE_ONLY, npi: inList }));
  return new Map(rows.map((p) => [p.npi, toFacts(p)]));
}

// The board a new roster member is checked against: one of its NPPES license states that has a board file, the
// practice state first when it is one of them. Null when it holds no license on file in a covered state; the
// practice address never picks a board.
function licenseBoard(f: ProviderFacts, licenses: Map<string, string>): string | null {
  const boards = f.license_states.filter((s) => licenses.has(s));
  return boards.find((s) => f.practice_states.includes(s)) ?? boards[0] ?? null;
}

const quoteList = (ids: string[]) => `in.(${ids.map((r) => `"${r.replace(/"/g, "")}"`).join(",")})`;

// The five checks a roster row shows, each the current receipt (v_current_receipts) read through
// v_freshroot_receipts so stage carries "stale" and rights match every other route. The license and the board
// action are the ones in the roster state, latest retrieved first, as freshroot_roster picks the license.
const CHECK_CLAIMS = ["state_license", "state_board_action", "npi_status", "oig_exclusion", "sam_exclusion"] as const;
const STATE_CLAIMS = new Set(["state_license", "state_board_action"]);
const CHECK_FIELDS = "id,npi,claim_type,jurisdiction,license_number,normalized_status,raw_status,stage,source_name," +
  "source_published_at,retrieved_at,next_check_due_at,created_at,match_basis,match_confidence,limitations," +
  "accepted_for_sale,shippable,rights";

async function rosterChecks(members: { npi: string; state: string | null }[], includeUnaccepted: boolean) {
  const npis = members.map((m) => m.npi);
  const claimFilter = `in.(${CHECK_CLAIMS.join(",")})`;
  const current = await inChunks(npis, (inList) =>
    rest("GET", "v_current_receipts", { select: "id", npi: inList, claim_type: claimFilter }));
  const rows = await inChunks(current.map((r) => r.id), (inList) =>
    rest("GET", "v_freshroot_receipts", { select: CHECK_FIELDS, id: inList }));
  const stateOf = new Map(members.map((m) => [m.npi, m.state]));
  const out = new Map<string, Record<string, Record<string, unknown> | null>>();
  for (const npi of npis) out.set(npi, Object.fromEntries(CHECK_CLAIMS.map((c) => [c, null])));
  for (const r of rows) {
    if (!includeUnaccepted && !r.accepted_for_sale) continue;
    if (STATE_CLAIMS.has(r.claim_type) && r.jurisdiction !== stateOf.get(r.npi)) continue;
    const checks = out.get(r.npi)!;
    const prev = checks[r.claim_type] as { retrieved_at: string; created_at: string } | null;
    if (prev && (prev.retrieved_at > r.retrieved_at || (prev.retrieved_at === r.retrieved_at && prev.created_at >= r.created_at))) continue;
    const { id, npi: _npi, accepted_for_sale: _a, ...check } = r;
    checks[r.claim_type] = { receipt_id: id, ...check };
  }
  return out;
}

// ---------- receipts for roster NPIs: the packet builder's writer ----------
// The writer is the SQL that scripts/build_credential_packet.py --write-receipts calls: receipts_for_npi_status,
// receipts_for_exclusions (OIG and SAM in one transaction), receipts_for_state_licenses and receipts_for_board_actions
// (the same board run as the license; migrations/2026-11-05_board_action_receipts.sql). This calls the same
// functions the same way: the latest completed run per source, NPIs that already hold a receipt of that claim type
// from that run skipped (one run never writes a claim twice: uq_receipts_one_per_run), and a batch that hits a
// statement timeout split in half and tried again. Nothing here builds a receipt itself.

const ORIGIN = "real";
const RPC_BATCH = 50;
const EXCLUSIONS_BATCH = 10; // receipts_for_exclusions name-scans SAM once per NPI; the packet builder uses 12
const LOOKUP_LIMIT = 20;
const ADD_LIMIT = 20;

async function latestRunId(sourceId: string): Promise<string | null> {
  const runs = await rest("GET", "ingestion_runs", {
    select: "id", source_id: `eq.${sourceId}`, status: "eq.completed", order: "completed_at.desc", limit: "1",
  });
  return runs[0]?.id ?? null;
}

async function namedSourceRunId(name: string): Promise<string | null> {
  const srcs = await rest("GET", "data_sources", { select: "id", name: `eq.${name}` });
  return srcs.length === 1 ? latestRunId(srcs[0].id) : null;
}

// State -> latest completed run of that state's bulk licensing source, for every state that has one: the states a
// license receipt can be written for (TX, FL and CA on 2026-10-28; Utah is seeded and never read). Same source
// filter as the packet builder and receipts_for_state_licenses: licensing, claims state_license, not an api source.
async function licenseRuns(): Promise<Map<string, string>> {
  const srcs = await rest("GET", "data_sources", {
    select: "id,jurisdiction", category: "eq.licensing", claim_types: "cs.{state_license}", or: "(format.is.null,format.neq.api)",
  });
  const runs = await Promise.all(srcs.map(async (s: Row) => [s.jurisdiction, await latestRunId(s.id)] as const));
  return new Map(runs.filter(([st, run]) => st && run) as [string, string][]);
}

async function notYetWritten(npis: string[], claimType: string, runId: string): Promise<string[]> {
  const done = new Set((await inChunks(npis, (inList) =>
    rest("GET", "credential_receipts", {
      select: "npi", claim_type: `eq.${claimType}`, run_id: `eq.${runId}`, origin: `eq.${ORIGIN}`, npi: inList,
    }))).map((r) => r.npi));
  return npis.filter((n) => !done.has(n));
}

// No retries on a network error: a retried call could write receipts the server already committed.
async function rpcReceipts(fn: string, npis: string[], extra: Record<string, unknown>, size: number): Promise<Row[]> {
  const out: Row[] = [];
  const pending: string[][] = [];
  for (let i = 0; i < npis.length; i += size) pending.push(npis.slice(i, i + size));
  while (pending.length) {
    const batch = pending.shift()!;
    try {
      out.push(...await rpc(fn, { p_npis: batch, ...extra }));
    } catch (e) {
      if (e instanceof UpstreamError && e.pgCode === "57014" && batch.length > 1) {
        const half = batch.length >> 1;
        pending.unshift(batch.slice(0, half), batch.slice(half));
        continue;
      }
      throw e;
    }
  }
  return out;
}

// Writes the receipts for roster members and returns the ids written, plus each step that could not run. A failed
// step leaves the others written; adding the same NPIs again retries only what is missing.
async function writeReceipts(members: { npi: string; state: string | null }[], licenses: Map<string, string>) {
  const npis = members.map((m) => m.npi);
  const failed: string[] = [];
  const step = async (label: string, runId: string | null, claimType: string, subset: string[], fn: string,
                      extra: Record<string, unknown>, size: number): Promise<Row[]> => {
    if (!subset.length) return [];
    if (!runId) { failed.push(`${label}: no completed run`); return []; }
    try {
      const todo = await notYetWritten(subset, claimType, runId);
      return todo.length ? await rpcReceipts(fn, todo, { ...extra, p_origin: ORIGIN }, size) : [];
    } catch (e) {
      console.error(`writer ${label}:`, e);
      failed.push(`${label}: write failed`);
      return [];
    }
  };
  const [npiRun, oigRun] = await Promise.all([namedSourceRunId("NPI Registry"), namedSourceRunId("OIG LEIE")]);
  const written = await Promise.all([
    step("npi_status", npiRun, "npi_status", npis, "receipts_for_npi_status", {}, RPC_BATCH),
    // receipts_for_exclusions writes OIG and SAM in one transaction, so the OIG receipt marks both done.
    step("oig_exclusion+sam_exclusion", oigRun, "oig_exclusion", npis, "receipts_for_exclusions", {}, EXCLUSIONS_BATCH),
    ...[...licenses].flatMap(([st, runId]) => {
      const inState = members.filter((m) => m.state === st).map((m) => m.npi);
      return [
        step(`state_license:${st}`, runId, "state_license", inState, "receipts_for_state_licenses", { p_state: st }, RPC_BATCH),
        step(`state_board_action:${st}`, runId, "state_board_action", inState, "receipts_for_board_actions",
          { p_state: st }, RPC_BATCH),
      ];
    }),
  ]);
  return { ids: written.flat().map((r) => r.receipt_id as string), failed };
}

// ---------- lookup ----------

// "Smith, John" is last, first. "John Smith" is tried both ways round (first token, last token). One word is a last
// name. Names are matched as prefixes, upper case as NPPES stores them.
function parseName(q: string): { a: string; b: string | null; bothWays: boolean } {
  const clean = q.toUpperCase().replace(/\./g, " ");
  if (!/^[A-Z][A-Z ,'-]*$/.test(clean.trim())) throw new HttpError(400, "q must be a 10-digit NPI or a name");
  if (clean.includes(",")) {
    const [last, first] = clean.split(",", 2).map((s) => s.trim().split(/\s+/)[0] || "");
    if (last.length < 2) throw new HttpError(400, "a last name needs at least 2 letters");
    return { a: last, b: first || null, bothWays: false };
  }
  const t = clean.trim().split(/\s+/);
  if (t.length === 1) {
    if (t[0].length < 2) throw new HttpError(400, "a last name needs at least 2 letters");
    return { a: t[0], b: null, bothWays: false };
  }
  return { a: t[0], b: t[t.length - 1], bothWays: true };
}

async function lookup(url: URL, tenant: Tenant) {
  const q = (url.searchParams.get("q") ?? "").trim();
  const stateParam = (url.searchParams.get("state") ?? "").trim().toUpperCase();
  if (stateParam && !/^[A-Z]{2}$/.test(stateParam)) throw new HttpError(400, "state must be a 2-letter code");
  const rosterIds = url.searchParams.get("roster_id") ? [requireRoster(tenant, url.searchParams.get("roster_id"))] : tenant.roster_ids;
  if (!q) throw new HttpError(400, "q is required");

  // No ORDER BY: the name index is varchar_pattern_ops, so ordering by the column's collation would fetch and sort
  // every prefix match. The LIMIT stops the index scan early; the page of up to 20 is sorted here.
  const params: Record<string, string> = {
    select: `${FACTS_SELECT},status`,
    entity_type: "eq.individual",
    ...PRACTICE_ONLY,
    limit: String(LOOKUP_LIMIT + 1),
  };
  const digits = q.replace(/[\s-]/g, "");
  if (/^\d+$/.test(digits)) {
    if (digits.length !== 10) throw new HttpError(400, "an NPI is 10 digits");
    params.npi = `eq.${digits}`;
  } else {
    const { a, b, bothWays } = parseName(q);
    if (!b) params.last_name = `like.${a}*`;
    else if (!bothWays) Object.assign(params, { last_name: `like.${a}*`, first_name: `like.${b}*` });
    else params.or = `(and(first_name.like.${a}*,last_name.like.${b}*),and(last_name.like.${a}*,first_name.like.${b}*))`;
  }

  // A state narrows to providers with that NPPES license state or that practice state: two queries, merged. The
  // aliased inner embeds filter which providers match and leave the full taxonomy and address lists intact.
  const queries = stateParam
    ? [
      { ...params, select: `${params.select},lic:provider_taxonomies!inner(license_state)`, "lic.license_state": `eq.${stateParam}` },
      { ...params, select: `${params.select},pa:provider_addresses!inner(state)`, "pa.state": `eq.${stateParam}`, "pa.address_type": "eq.practice" },
    ]
    : [params];
  const t0 = performance.now();
  const [found, licenses] = await Promise.all([Promise.all(queries.map((p) => rest("GET", "providers", p))), licenseRuns()]);
  const tookMs = Math.round(performance.now() - t0);
  const rows = [...new Map((found.flat() as Row[]).map((p) => [p.npi, p])).values()];
  const page = rows.slice(0, LOOKUP_LIMIT);
  const onRoster = new Set(page.length && rosterIds.length
    ? (await rest("GET", "roster_members", { select: "npi", npi: `in.(${page.map((p) => p.npi).join(",")})`, roster_id: quoteList(rosterIds) }))
      .map((r: Row) => r.npi)
    : []);
  const candidates = page.map((p) => {
    const { lic: _l, pa: _p, ...provider } = p;
    const facts = toFacts(provider);
    const board = licenseBoard(facts, licenses);
    return {
      npi: p.npi, ...facts, state: board ?? shownStates(facts)[0] ?? null, npi_status: p.status,
      on_roster: onRoster.has(p.npi), license_board: board, license_covered: !!board,
    };
  }).sort((x, y) => `${x.last_name}|${x.first_name}|${x.npi}`.localeCompare(`${y.last_name}|${y.first_name}|${y.npi}`));
  return {
    q, state: stateParam || null, license_states: [...licenses.keys()].sort(),
    count: candidates.length, more: rows.length > LOOKUP_LIMIT, took_ms: tookMs, candidates,
  };
}

// ---------- roster-add ----------

// The states shown for a provider: the practice states when NPPES lists any, otherwise its license states.
const shownStates = (f: ProviderFacts) => (f.practice_states.length ? f.practice_states : f.license_states);

// The one plain line for a provider with no license on file in a covered state. A state we hold no board file for
// is "not covered yet", never a guess; a covered practice state without a license on file there is said as such.
function noBoardLine(f: ProviderFacts, licenses: Map<string, string>): string {
  const shown = shownStates(f);
  if (!shown.length) return "State license: NPPES lists no license state or practice state for this NPI, so no board was checked.";
  if (shown.every((s) => !licenses.has(s))) return `State license: not covered yet for ${shown.join(", ")}.`;
  return `State license: NPPES records no license in ${[...licenses.keys()].sort().join(", ")} for this NPI, so no board was checked.`;
}

// What the license check says for one member, in plain words. The board is the member's roster state when we hold
// a board file for it; an NPI the board file could not be linked to carries the writer's own limitation text.
function licenseOutcome(state: string | null, facts: ProviderFacts, licenses: Map<string, string>, check: Row | null) {
  if (!state || !licenses.has(state)) return { covered: false, matched: false, reason: noBoardLine(facts, licenses) };
  if (!check) return { covered: true, matched: false, reason: "No license receipt was written; adding again retries it." };
  if (check.match_basis === "none") return { covered: true, matched: false, reason: check.limitations };
  return { covered: true, matched: true, match_basis: check.match_basis, stage: check.stage, reason: check.limitations ?? null };
}

const NOT_IN_NPPES = "not in the NPPES registry extract";
const NOT_INDIVIDUAL = "not an individual provider";

// Puts NPIs on a roster: the one path /npis and /jobs share. Only individual providers in the NPPES extract are added.
// The roster state is the board the member is checked against (licenseBoard), or null when it holds no license on
// file in a covered state. A member already on the roster keeps its row as it is. Returns the members (new and
// already there) the receipt writer should read, and the NPIs it would not add, each with the reason. asked: the
// state a bulk input row named for an NPI; it is the roster state as given, covered by a board file or not.
async function addMembers(rosterId: string, npis: string[], licenses: Map<string, string>, asked = new Map<string, string>()) {
  const found = await inChunks(npis, (inList) =>
    rest("GET", "providers", { select: `${FACTS_SELECT},entity_type`, ...PRACTICE_ONLY, npi: inList }));
  const byNpi = new Map(found.map((p) => [p.npi, p]));
  const notAdded = npis.filter((n) => byNpi.get(n)?.entity_type !== "individual").map((n) => ({
    npi: n, reason: byNpi.has(n) ? NOT_INDIVIDUAL : NOT_IN_NPPES,
  }));
  const addable = npis.filter((n) => byNpi.get(n)?.entity_type === "individual");
  const facts = new Map(addable.map((n) => [n, toFacts(byNpi.get(n)!)]));
  const inserted = addable.length
    ? await rest("POST", "roster_members", undefined,
      addable.map((n) => ({ roster_id: rosterId, npi: n, state: asked.get(n) ?? licenseBoard(facts.get(n)!, licenses) })),
      "resolution=ignore-duplicates,return=representation")
    : [];
  const added = new Set((inserted as Row[]).map((r) => r.npi));
  const members = (addable.length
    ? await inChunks(addable, (inList) =>
      rest("GET", "roster_members", { select: "npi,state", roster_id: `eq.${rosterId}`, npi: inList }))
    : []) as { npi: string; state: string | null }[];
  return { facts, notAdded, added, members };
}

async function addToRoster(req: Request, url: URL, tenant: Tenant, rosterId: string) {
  const includeUnaccepted = url.searchParams.get("include_unaccepted") === "true";
  let body: { npis?: unknown };
  try { body = await req.json(); } catch { throw new HttpError(400, "body must be JSON: {\"npis\": [...]}"); }
  if (!Array.isArray(body?.npis) || !body.npis.length) throw new HttpError(400, "npis must be a non-empty list");
  const npis = [...new Set(body.npis.map((n) => String(n).trim()))];
  if (npis.length > ADD_LIMIT) throw new HttpError(400, `at most ${ADD_LIMIT} NPIs per call`);
  if (!npis.every((n) => /^\d{10}$/.test(n))) throw new HttpError(400, "every npi must be 10 digits");

  const [licenses, countBefore] = await Promise.all([licenseRuns(), rosterCount(rosterId)]);
  const { facts, notAdded, added, members } = await addMembers(rosterId, npis, licenses);
  const { ids, failed } = await writeReceipts(members, licenses);
  const [writtenRows, checks, countAfter] = await Promise.all([
    inChunks(ids, (inList) => rest("GET", "v_freshroot_receipts", { select: CHECK_FIELDS, id: inList })),
    rosterChecks(members, includeUnaccepted),
    rosterCount(rosterId),
  ]);
  const shown = writtenRows.filter((r) => includeUnaccepted || r.accepted_for_sale);
  return {
    roster_id: rosterId,
    roster_count_before: countBefore,
    roster_count_after: countAfter,
    license_states: [...licenses.keys()].sort(),
    receipts_written_count: ids.length,
    write_failures: failed,
    results: members.map((m) => {
      const mine = checks.get(m.npi)!;
      return {
        npi: m.npi,
        added: added.has(m.npi),
        state: m.state,
        provider: facts.get(m.npi)!,
        receipts_written: shown.filter((r) => r.npi === m.npi).map(({ id, accepted_for_sale: _a, ...r }) => ({ receipt_id: id, ...r })),
        checks: mine,
        license: licenseOutcome(m.state, facts.get(m.npi)!, licenses, mine.state_license as Row | null),
      };
    }),
    not_added: notAdded,
  };
}

// ---------- bulk jobs ----------
// POST /v1/rosters/{id}/jobs stores the NPIs on a freshroot_jobs row and answers 202. The worker is this function:
// runJob, in a background task, takes the lease (freshroot_job_claim), then works batches of JOB_BATCH NPIs through
// addMembers and writeReceipts, the same two steps /npis runs, writing progress to the job row after each batch. It
// stops taking batches after JOB_BUDGET_MS and lets the lease lapse, well inside the Edge Function wall clock; the
// next GET /v1/jobs/{id} claims the job again and carries on from `processed`. A worker killed mid-batch leaves the
// lease to lapse the same way; the writer skips receipts it already wrote, so the batch is safe to run again.

declare const EdgeRuntime: { waitUntil(p: Promise<unknown>): void } | undefined;

const JOB_LIMIT = 5000;
const JOB_BATCH = 100;
const JOB_LEASE_S = 300;        // renewed before every batch; one batch of 100 runs well under this
const JOB_BUDGET_MS = 240_000;  // no new batch after this; the Edge Function wall clock is 400 s
const WRITER_CLAIMS = ["npi_status", "oig_exclusion", "sam_exclusion", "state_license", "state_board_action"];

// The bulk anomaly guard. The loaders' guards (header, row count, parse, status vocabulary, match count, flip check)
// already stand between a bad file and a completed run, and the writer reads only completed runs. This one watches
// what the writer does with a large new list: after every batch it reads the receipts this job wrote so far and
// stops the job, before the next batch, when a share runs far past what the garden has seen. Judged once at least
// GUARD_MIN NPIs hold receipts from the job. Receipts already written stay (append-only); the job reads failed with
// the reading that stopped it.
const GUARD_MIN = 100;
const GUARD_LIMITS: [key: string, label: string, limit: number][] = [
  // NPPES individuals read deactivated ~1-2%; 3 of 252 on the first-packet roster.
  ["npi_inactive", "npi_status receipts read inactive (deactivated)", 0.25],
  // OIG or SAM rows tied to the NPI by the publisher's own NPI: about 0.1% of practising physicians.
  ["exclusion_found", "OIG or SAM receipts read excluded on an exact NPI", 0.02],
  // SAM rows with no NPI matched on name: 90 of 2,018 (4.5%) on the first packet.
  ["sam_name_only", "SAM receipts that are name-only candidates", 0.25],
  // Board statuses that map to unknown: each loader stops a file above 5%.
  ["license_unknown", "license receipts read unknown", 0.10],
  // License receipts with no board row linked to the NPI.
  ["license_not_found", "license receipts with no board row linked", 0.60],
];

type Job = Row & { id: string; roster_id: string; npis: string[]; processed: number; status: string };

const JOB_FIELDS = "id,roster_id,status,input_count,npis,states,processed,added,already_on_roster,receipted,receipts_written," +
  "unmatched,guard,write_failures,error,attempts,lease_until,created_at,started_at,finished_at,updated_at";

const patchJob = (id: string, body: Row) =>
  rest("PATCH", "freshroot_jobs", { id: `eq.${id}` }, { ...body, updated_at: new Date().toISOString() }, "return=minimal");

type InputRow = { npi: string; state: string };

// A CSV body: a header row naming an npi column and, optionally, a state column (any case), comma-separated,
// double quotes allowed.
function csvNpis(text: string): InputRow[] {
  const lines = text.replace(/^﻿/, "").split(/\r?\n/).filter((l) => l.trim());
  if (!lines.length) return [];
  const cells = (line: string) => {
    const out: string[] = [];
    let cur = "", q = false;
    for (let i = 0; i < line.length; i++) {
      const ch = line[i];
      if (q) {
        if (ch === '"' && line[i + 1] === '"') { cur += '"'; i++; } else if (ch === '"') q = false; else cur += ch;
      } else if (ch === '"') q = true;
      else if (ch === ",") { out.push(cur); cur = ""; } else cur += ch;
    }
    out.push(cur);
    return out.map((c) => c.trim());
  };
  const head = cells(lines[0]).map((h) => h.toLowerCase());
  const col = head.indexOf("npi"), scol = head.indexOf("state");
  if (col < 0) throw new HttpError(400, "a CSV body needs a header row with an npi column");
  return lines.slice(1).map((l) => {
    const c = cells(l);
    return { npi: c[col] ?? "", state: scol < 0 ? "" : c[scol] ?? "" };
  });
}

async function readJobInput(req: Request): Promise<InputRow[]> {
  const type = (req.headers.get("content-type") ?? "").toLowerCase();
  const text = await req.text();
  if (type.includes("text/csv") || type.includes("text/plain")) return csvNpis(text);
  let body: unknown;
  try { body = JSON.parse(text); } catch {
    throw new HttpError(400, "body must be JSON ({\"npis\": [...]} or [...]) or text/csv with an npi column");
  }
  const list = Array.isArray(body) ? body : (body as { npis?: unknown })?.npis;
  if (!Array.isArray(list)) throw new HttpError(400, "npis must be a list");
  return list.map((n) => (n && typeof n === "object")
    ? { npi: String((n as Row).npi ?? ""), state: String((n as Row).state ?? "") }
    : { npi: String(n ?? ""), state: "" });
}

async function createJob(req: Request, tenant: Tenant, rosterId: string) {
  const raw = (await readJobInput(req)).map((r) => ({ npi: r.npi.trim(), state: r.state.trim().toUpperCase() }))
    .filter((r) => r.npi);
  if (!raw.length) throw new HttpError(400, "no NPIs in the body");
  if (raw.length > JOB_LIMIT) throw new HttpError(400, `at most ${JOB_LIMIT} NPIs per job; this body has ${raw.length}`);
  const [roster] = await rest("GET", "rosters", { select: "id", id: `eq.${rosterId}` });
  if (!roster) throw new HttpError(404, "roster not found");
  const npis: string[] = [];
  const seen = new Set<string>();
  const states: Record<string, string> = {};
  const unmatched: { npi: string; reason: string }[] = [];
  let duplicates = 0;
  for (const { npi, state } of raw) {
    if (!/^\d{10}$/.test(npi)) { unmatched.push({ npi: npi.slice(0, 40), reason: "not a 10-digit NPI" }); continue; }
    if (state && !/^[A-Z]{2}$/.test(state)) { unmatched.push({ npi, reason: `state ${state.slice(0, 20)} is not a 2-letter code` }); continue; }
    if (seen.has(npi)) {
      if ((states[npi] ?? "") !== state) unmatched.push({ npi, reason: `listed again with state ${state || "none"}; kept ${states[npi] || "none"}` });
      else duplicates++;
      continue;
    }
    seen.add(npi);
    npis.push(npi);
    if (state) states[npi] = state;
  }
  const [job] = await rest("POST", "freshroot_jobs", undefined, {
    roster_id: rosterId, tenant_id: tenant.id, input_count: raw.length, npis, states, unmatched,
    ...(npis.length ? {} : { status: "done", finished_at: new Date().toISOString() }),
  }, "return=representation");
  if (npis.length) startWorker(job.id);
  return jobView(job, duplicates);
}

function startWorker(jobId: string) {
  const work = runJob(jobId).catch((e) => console.error(`job ${jobId}:`, e));
  if (typeof EdgeRuntime !== "undefined") EdgeRuntime.waitUntil(work);
}

async function getJob(tenant: Tenant, jobId: string) {
  if (!/^[0-9a-f-]{36}$/.test(jobId)) throw new HttpError(400, "job id must be a uuid");
  const [job] = await rest("GET", "freshroot_jobs", { select: JOB_FIELDS, id: `eq.${jobId}` });
  // Same answer whether or not the job exists: a tenant learns nothing about other rosters' jobs.
  if (!job || !tenant.roster_ids.includes(job.roster_id)) throw new HttpError(403, "job not available to this key");
  const lapsed = !job.lease_until || Date.parse(job.lease_until) < Date.now();
  if ((job.status === "queued" || job.status === "running") && lapsed) startWorker(job.id);
  return jobView(job);
}

function jobView(job: Row, duplicates?: number) {
  const total = (job.npis ?? []).length;
  return {
    job_id: job.id,
    roster_id: job.roster_id,
    status: job.status,
    worker: "freshroot edge function, background task; a GET resumes a job whose worker stopped",
    progress: { processed: job.processed, total, percent: total ? Math.round((100 * job.processed) / total) : 100 },
    counts: {
      input: job.input_count,
      ...(duplicates !== undefined ? { duplicates } : {}),
      added: job.added,
      already_on_roster: job.already_on_roster,
      receipted: job.receipted,
      receipts_written: job.receipts_written,
      unmatched: (job.unmatched ?? []).length,
    },
    unmatched: job.unmatched ?? [],
    guard: job.guard ?? null,
    write_failures: job.write_failures ?? [],
    error: job.error ?? null,
    created_at: job.created_at,
    started_at: job.started_at ?? null,
    finished_at: job.finished_at ?? null,
    updated_at: job.updated_at,
  };
}

type GuardCounts = Record<string, number>;
const emptyGuard = (): GuardCounts => ({
  npis: 0, npi_status: 0, npi_inactive: 0, exclusions: 0, exclusion_found: 0, sam: 0, sam_name_only: 0,
  licenses: 0, license_unknown: 0, license_not_found: 0,
});

// Adds one batch's receipts (every writer claim this job's NPIs got since the job was created) to the counts.
function countReceipts(g: GuardCounts, rows: Row[]) {
  g.npis += new Set(rows.map((r) => r.npi)).size;
  for (const r of rows) {
    if (r.claim_type === "npi_status") {
      g.npi_status++;
      if (r.normalized_status === "inactive" || r.normalized_status === "deactivated") g.npi_inactive++;
    } else if (r.claim_type === "oig_exclusion" || r.claim_type === "sam_exclusion") {
      g.exclusions++;
      if (r.match_basis === "npi_exact" && !["not_found", "unknown"].includes(r.normalized_status)) g.exclusion_found++;
      if (r.claim_type === "sam_exclusion") {
        g.sam++;
        if (r.match_basis === "name_only") g.sam_name_only++;
      }
    } else if (r.claim_type === "state_license") {
      g.licenses++;
      if (r.normalized_status === "unknown") g.license_unknown++;
      if (r.match_basis === "none") g.license_not_found++;
    }
  }
}

function readGuard(g: GuardCounts) {
  const base: Record<string, number> = {
    npi_inactive: g.npi_status, exclusion_found: g.exclusions, sam_name_only: g.sam,
    license_unknown: g.licenses, license_not_found: g.licenses,
  };
  const shares = GUARD_LIMITS.map(([key, label, limit]) => ({
    key, label, limit, count: g[key], of: base[key], share: base[key] ? g[key] / base[key] : 0,
  }));
  const judged = g.npis >= GUARD_MIN;
  const tripped = judged ? shares.filter((s) => s.of > 0 && s.share > s.limit) : [];
  return { judged, min_npis: GUARD_MIN, counts: g, shares, tripped: tripped.map((s) => s.key), tripped_rows: tripped };
}

const pct = (x: number) => `${(100 * x).toFixed(1)}%`;

async function runJob(jobId: string) {
  const t0 = Date.now();
  const [job] = (await rpc("freshroot_job_claim", { p_job_id: jobId, p_lease_seconds: JOB_LEASE_S })) as Job[];
  if (!job) return; // another worker holds it, or it is finished
  const fail = (error: string, extra: Row = {}) =>
    patchJob(jobId, { ...extra, status: "failed", error, lease_until: null, finished_at: new Date().toISOString() });
  try {
    const licenses = await licenseRuns();
    const asked = new Map(Object.entries((job.states ?? {}) as Record<string, string>));
    const g: GuardCounts = { ...emptyGuard(), ...(job.guard?.counts ?? {}) };
    let { processed } = job;
    let added = job.added, already = job.already_on_roster, receipted = job.receipted, written = job.receipts_written;
    const unmatched: Row[] = [...(job.unmatched ?? [])];
    const failures: string[] = [...(job.write_failures ?? [])];
    while (processed < job.npis.length) {
      if (Date.now() - t0 > JOB_BUDGET_MS) {
        await patchJob(jobId, { lease_until: null }); // the next GET /v1/jobs/{id} picks it up
        return;
      }
      await patchJob(jobId, { lease_until: new Date(Date.now() + JOB_LEASE_S * 1000).toISOString() });
      const batch = job.npis.slice(processed, processed + JOB_BATCH);
      const res = await addMembers(job.roster_id, batch, licenses, asked);
      const { failed } = await writeReceipts(res.members, licenses);
      const mine = res.members.map((m) => m.npi);
      const rows = mine.length
        ? await inChunks(mine, (inList) => restAll("credential_receipts", {
          select: "id,npi,claim_type,normalized_status,match_basis", npi: inList, origin: `eq.${ORIGIN}`,
          claim_type: `in.(${WRITER_CLAIMS.join(",")})`, created_at: `gte.${job.created_at}`,
        }, "id"))
        : [];
      countReceipts(g, rows);
      processed += batch.length;
      added += res.added.size;
      already += res.members.length - res.added.size;
      receipted += new Set(rows.map((r) => r.npi)).size;
      written += rows.length;
      unmatched.push(...res.notAdded);
      failures.push(...failed);
      const guard = readGuard(g);
      const progress = {
        processed, added, already_on_roster: already, receipted, receipts_written: written, unmatched,
        guard, write_failures: failures,
      };
      if (failed.length) return await fail(`receipt writer: ${failed.join("; ")}. Posting the same NPIs again ` +
        "retries only what is missing.", progress);
      if (guard.tripped_rows.length) {
        const why = guard.tripped_rows.map((s) => `${pct(s.share)} of ${s.label} (${s.count} of ${s.of}; limit ${pct(s.limit)})`);
        return await fail(`anomaly guard after ${g.npis} receipted NPIs: ${why.join("; ")}. The job stopped before ` +
          "its next batch; receipts already written stay (append-only).", progress);
      }
      await patchJob(jobId, progress);
    }
    await patchJob(jobId, { status: "done", lease_until: null, finished_at: new Date().toISOString() });
  } catch (e) {
    console.error(`job ${jobId} failed:`, e);
    await fail(e instanceof UpstreamError ? `upstream query failed${e.pgCode ? ` (${e.pgCode})` : ""}` : String(e));
  }
}

// ---------- export ----------
// GET /v1/rosters/{id}/export: the packet builder's four files (scripts/build_credential_packet.py: the same columns,
// the same shippable rule, coverage from the same roster_coverage()) plus report.md, zipped. The rows are the current
// receipt per claim for every roster NPI (v_current_receipts), read through v_freshroot_receipts. Rows from sources
// not accepted for sale are left out unless include_unaccepted=true, as on every other route; report.md says how many.

const RECEIPT_COLUMNS = [
  "npi", "claim_type", "jurisdiction", "license_number", "normalized_status", "raw_status",
  "source_name", "source_published_at", "source_effective_at", "retrieved_at", "next_check_due_at",
  "origin", "stage", "match_basis", "match_confidence", "accepted_for_sale", "shippable", "limitations",
  "receipt_id", "supersedes_id", "artifact_sha256",
];
const EXPORT_FIELDS = "id,npi,claim_type,jurisdiction,license_number,normalized_status,raw_status,source_name," +
  "source_published_at,source_effective_at,retrieved_at,next_check_due_at,origin,stage,match_basis,match_confidence," +
  "accepted_for_sale,shippable,limitations,supersedes_id,artifact_sha256,created_at";
const FIXED_LINE = "Internal review · rights pending · 0 shippable";
const LICENSE_FLAGS = ["expired", "inactive", "revoked", "probation"];
const LICENSE_COLUMNS = ["active", "expired", "inactive", "revoked", "probation", "suspended"];

const csvCell = (v: unknown) => {
  const s = v === null || v === undefined ? "" : typeof v === "boolean" ? (v ? "True" : "False") : String(v);
  return /[",\r\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
};
const csvText = (header: string[], rows: unknown[][]) =>
  [header, ...rows].map((r) => r.map(csvCell).join(",")).join("\r\n") + "\r\n";

const day = (iso: string | null | undefined) => (iso ? String(iso).slice(0, 10) : null);
const minute = (iso: string) => new Date(iso).toISOString().slice(0, 16).replace("T", " ") + " UTC";

// "the dates it rests on": per source, the publisher's file date(s) and when the garden read them.
function restsOn(rows: Row[]): string {
  if (!rows.length) return "no receipts";
  const bySource = new Map<string, Row[]>();
  for (const r of rows) bySource.set(r.source_name, [...(bySource.get(r.source_name) ?? []), r]);
  return [...bySource].sort(([a], [b]) => a.localeCompare(b)).map(([name, rs]) => {
    const files = [...new Set(rs.map((r) => day(r.source_published_at) ?? "undated"))].sort();
    const reads = rs.map((r) => r.retrieved_at as string).sort();
    const file = files.length === 1 ? `file ${files[0]}` : `files ${files[0]} to ${files[files.length - 1]}`;
    const read = reads[0] === reads[reads.length - 1] ? `read ${minute(reads[0])}`
      : `read ${minute(reads[0])} to ${minute(reads[reads.length - 1])}`;
    return `${name}: ${file}, ${read}`;
  }).join("; ");
}

// The license receipt a roster row shows: the one in the roster state, latest retrieved first (rosterChecks' rule).
function pickLicense(rows: Row[], state: string | null): Row | null {
  let best: Row | null = null;
  for (const r of rows) {
    if (r.claim_type !== "state_license" || r.jurisdiction !== state) continue;
    if (!best || r.retrieved_at > best.retrieved_at || (r.retrieved_at === best.retrieved_at && r.created_at > best.created_at)) best = r;
  }
  return best;
}

async function exportRoster(url: URL, rosterId: string, cors: Record<string, string>): Promise<Response> {
  const includeUnaccepted = url.searchParams.get("include_unaccepted") === "true";
  const [roster] = await rest("GET", "rosters", { select: "*", id: `eq.${rosterId}` });
  if (!roster) throw new HttpError(404, "roster not found");
  const [members, jobs, licenses, coverageRows] = await Promise.all([
    restAll("roster_members", { select: "npi,state", roster_id: `eq.${rosterId}` }, "npi"),
    restAll("freshroot_jobs", { select: "id,unmatched,created_at", roster_id: `eq.${rosterId}` }, "created_at,id"),
    licenseRuns(),
    rpc("freshroot_coverage", { p_roster_id: rosterId }),
  ]);
  const npis = members.map((m) => m.npi as string);
  const [facts, currentIds] = await Promise.all([
    providerFacts(npis),
    inChunks(npis, (inList) => restAll("v_current_receipts", { select: "id", npi: inList }, "id")),
  ]);
  const all = await inChunks(currentIds.map((r) => r.id), (inList) =>
    rest("GET", "v_freshroot_receipts", { select: EXPORT_FIELDS, id: inList }));
  all.sort((a, b) => a.npi.localeCompare(b.npi) || a.claim_type.localeCompare(b.claim_type) || a.id.localeCompare(b.id));
  const rows = all.filter((r) => includeUnaccepted || r.accepted_for_sale);
  const leftOut = all.length - rows.length;
  const byNpi = new Map<string, Row[]>();
  for (const r of rows) byNpi.set(r.npi, [...(byNpi.get(r.npi) ?? []), r]);
  const builtAt = new Date().toISOString();

  // unmatched: NPIs a job would not add, roster NPIs not in the NPPES extract, and roster NPIs whose license check
  // found no board row (or had no board to ask).
  const onRoster = new Set(npis);
  const unmatched: { npi: string; what: string; reason: string; job_id: string }[] = [];
  const jobMisses = new Map<string, Row>();
  for (const j of jobs) for (const u of j.unmatched ?? []) jobMisses.set(u.npi, { ...u, job_id: j.id });
  for (const [npi, u] of jobMisses) if (!onRoster.has(npi)) unmatched.push({ npi, what: "not added", reason: u.reason, job_id: u.job_id });
  for (const m of members) {
    const f = facts.get(m.npi);
    if (!f) { unmatched.push({ npi: m.npi, what: "not in NPPES", reason: "not in NPPES snapshot held by the garden", job_id: "" }); continue; }
    const lic = pickLicense(byNpi.get(m.npi) ?? [], m.state);
    if (!m.state) unmatched.push({ npi: m.npi, what: "state license", reason: noBoardLine(f, licenses), job_id: "" });
    else if (!licenses.has(m.state)) {
      unmatched.push({ npi: m.npi, what: "state license", reason: `State license: not covered yet for ${m.state}.`, job_id: "" });
    }
    else if (!lic && includeUnaccepted) unmatched.push({ npi: m.npi, what: "state license", reason: `no ${m.state} license receipt written yet`, job_id: "" });
    else if (lic?.match_basis === "none") unmatched.push({ npi: m.npi, what: "state license", reason: lic.limitations || `no ${m.state} board row linked to this NPI`, job_id: "" });
  }

  // coverage, as the packet builder writes it
  const coverage: Record<string, number> = {};
  const notYet: Record<string, string> = {};
  for (const c of coverageRows as Row[]) {
    if (c.covered !== null) coverage[c.claim_key] = c.covered; else notYet[c.claim_key] = c.reason;
  }
  const shippable = rows.filter((r) => r.shippable);
  const review = rows.filter((r) => r.stage === "candidate");
  const stale = rows.filter((r) => r.stage === "stale");
  const unsellable = rows.filter((r) => !r.accepted_for_sale);
  const synthetic = rows.filter((r) => r.origin !== "real");
  const internal = shippable.length < rows.length || !rows.length;
  const statusCounts = new Map<string, number>();
  for (const r of rows) {
    const k = [r.claim_type, r.jurisdiction ?? "", r.normalized_status].join("|");
    statusCounts.set(k, (statusCounts.get(k) ?? 0) + 1);
  }
  const n = npis.length;
  const matched = npis.filter((x) => facts.has(x)).length;
  const coverageMd = [
    internal ? "# Internal review, rights pending" : "# Coverage report",
    "",
    `Built ${builtAt}. Shippable rows: ${shippable.length} of ${rows.length}.` + (internal ? " Nothing in this packet leaves the garden." : ""),
    "",
    `Roster: ${n} NPIs. In the garden: ${matched}. Not found in the NPPES snapshot: ${n - matched}.`,
    `Receipts: ${rows.length}. Needing human review (candidate): ${review.length}. Past due (stale): ${stale.length}.`,
    `Rows from sources not yet accepted for sale: ${unsellable.length} (these do not ship). Synthetic rows: ${synthetic.length}.`,
    ...(leftOut ? [`Left out: ${leftOut} rows from sources not accepted for sale (ask with include_unaccepted=true).`] : []),
    "",
    "## Covered today (NPIs with a current receipt)",
    "",
    "| Claim | Covered | of roster |",
    "| --- | ---: | ---: |",
    ...Object.entries(coverage).map(([k, c]) => `| ${k} | ${c} | ${n ? Math.round((100 * c) / n) : 0}% |`),
    "",
    "## Status counts",
    "",
    "| Claim | Jurisdiction | Status | Rows |",
    "| --- | --- | --- | ---: |",
    ...[...statusCounts].sort(([a], [b]) => a.localeCompare(b)).map(([k, c]) => {
      const [ct, jur, st] = k.split("|");
      return `| ${ct} | ${jur || "—"} | ${st} | ${c} |`;
    }),
    "",
    "## Not yet covered",
    "",
    ...Object.entries(notYet).map(([k, why]) => `- ${k}: ${why}`),
    "",
    "## How to read a row",
    "",
    "Three clocks: source_published_at is the date on the publisher's file; source_effective_at is when the fact took effect;",
    "retrieved_at is when the garden read it. next_check_due_at is retrieved_at plus the source cadence.",
    "normalized_status = not_found means not present in that source's snapshot on that date. It never means clear.",
    "match_basis and match_confidence say how the row was joined to the NPI. name_only rows are candidates for review, not findings.",
    "A row with accepted_for_sale = false comes from a source whose rights or acceptance test are not yet documented and does not ship.",
    "shippable is true only for a real, verified, current row from a source accepted for sale.",
  ].join("\n") + "\n";

  const reportMd = buildReport({
    roster, members, facts, byNpi, rows, licenses, unmatched, builtAt, leftOut, includeUnaccepted, shippable: shippable.length,
  });

  const receiptsCsv = csvText(RECEIPT_COLUMNS, rows.map((r) => RECEIPT_COLUMNS.map((c) => (c === "receipt_id" ? r.id : r[c]))));
  const unmatchedCsv = csvText(["npi", "what", "reason", "job_id"], unmatched.map((u) => [u.npi, u.what, u.reason, u.job_id]));
  const doc = {
    built_at: builtAt,
    roster: {
      id: roster.id, name: roster.name, test: !!roster.test, count: n, matched, unmatched_count: unmatched.length,
    },
    include_unaccepted: includeUnaccepted,
    left_out_not_accepted: leftOut,
    coverage,
    status_counts: Object.fromEntries([...statusCounts].map(([k, c]) => [k.split("|").filter(Boolean).join(":"), c])),
    shippable: shippable.length,
    internal_review_rights_pending: internal,
    needs_review: review.length,
    stale: stale.length,
    not_accepted_for_sale: unsellable.length,
    synthetic_rows: synthetic.length,
    not_yet_covered: notYet,
    unmatched,
    receipts: rows.map(({ id, created_at: _c, ...r }) => ({ receipt_id: id, ...r })),
  };
  const enc = new TextEncoder();
  const zip = await zipFiles([
    { name: "report.md", data: enc.encode(reportMd) },
    { name: "receipts.csv", data: enc.encode(receiptsCsv) },
    { name: "receipts.json", data: enc.encode(JSON.stringify(doc, null, 2)) },
    { name: "unmatched.csv", data: enc.encode(unmatchedCsv) },
    { name: "coverage.md", data: enc.encode(coverageMd) },
  ], new Date(builtAt));
  const fname = `freshroot-${rosterId.replace(/[^A-Za-z0-9._-]/g, "_")}-${builtAt.slice(0, 10)}.zip`;
  return new Response(zip, {
    status: 200,
    headers: {
      ...cors, "Content-Type": "application/zip", "Cache-Control": "no-store",
      "Content-Disposition": `attachment; filename="${fname}"`,
    },
  });
}

// report.md: one page. Every count is followed by the files and reads it rests on.
function buildReport(x: {
  roster: Row; members: Row[]; facts: Map<string, ProviderFacts>; byNpi: Map<string, Row[]>; rows: Row[];
  licenses: Map<string, string>; unmatched: { what: string; reason: string }[]; builtAt: string; leftOut: number;
  includeUnaccepted: boolean; shippable: number;
}): string {
  const { roster, members, byNpi, rows, licenses, unmatched, builtAt } = x;
  const anyAccepted = rows.some((r) => r.accepted_for_sale);
  const pendingSources = [...new Set(rows.filter((r) => !r.accepted_for_sale).map((r) => r.source_name))];
  const top = !anyAccepted ? FIXED_LINE
    : pendingSources.length ? `Internal review · rights pending on ${pendingSources.length} sources · ${x.shippable} shippable`
    : `${x.shippable} of ${rows.length} rows shippable`;
  const L: string[] = [top, ""];
  L.push(`# ${String(roster.name).includes(roster.id) ? roster.name : `${roster.name} (${roster.id})`}`, "");
  if (roster.test) {
    L.push("**Test roster.** Built to test the system, not a customer list. The hourly refresh and the CMS loaders " +
      "skip it; the receipts it has are kept (append-only).", "");
  }
  L.push(`Built ${minute(builtAt)} from the receipts current at that moment. ${members.length} NPIs on the roster, ` +
    `${rows.length} current receipts` + (x.leftOut ? `; ${x.leftOut} rows from sources not accepted for sale left out` : "") +
    (x.includeUnaccepted && !anyAccepted ? "; every row comes from a source not yet accepted for sale" : "") + ".", "");

  // Counts by state: the board each member is checked against.
  const lic = new Map(members.map((m) => [m.npi, pickLicense(byNpi.get(m.npi) ?? [], m.state)]));
  const states = [...new Set(members.map((m) => m.state ?? "none"))].sort((a, b) => (a === "none" ? 1 : b === "none" ? -1 : a.localeCompare(b)));
  // "name match" counts the linked licenses joined by name + state + taxonomy (stage candidate): for review, not findings.
  L.push("## By state", "", `| State | NPIs | ${LICENSE_COLUMNS.join(" | ")} | other | no board row | no receipt | name match | Rests on |`,
    `| --- | ---: | ${LICENSE_COLUMNS.map(() => "---:").join(" | ")} | ---: | ---: | ---: | ---: | --- |`);
  for (const st of states) {
    const ms = members.filter((m) => (m.state ?? "none") === st);
    const ls = ms.map((m) => lic.get(m.npi)).filter(Boolean) as Row[];
    const c = (s: string) => ls.filter((r) => r.normalized_status === s && r.match_basis !== "none").length;
    const linked = ls.filter((r) => r.match_basis !== "none");
    const other = linked.filter((r) => !LICENSE_COLUMNS.includes(r.normalized_status)).length;
    const noRow = ls.filter((r) => r.match_basis === "none").length;
    const label = st === "none" ? "no board" : licenses.has(st) ? st : `${st} (not covered)`;
    const rests = st === "none" ? "NPPES license states: no license on file in " + [...licenses.keys()].sort().join(", ") : restsOn(ls);
    const named = linked.filter((r) => r.stage === "candidate").length;
    L.push(`| ${label} | ${ms.length} | ${LICENSE_COLUMNS.map(c).join(" | ")} | ${other} | ${noRow} | ${ms.length - ls.length} | ${named} | ${rests} |`);
  }
  L.push("");

  // Flags on the license a row shows.
  const flagged = (s: string) => members.map((m) => lic.get(m.npi)).filter((r) => r && r.normalized_status === s && r.match_basis !== "none") as Row[];
  L.push("## License flags", "");
  for (const s of LICENSE_FLAGS) {
    const fr = flagged(s);
    const cand = fr.filter((r) => r.stage === "candidate").length;
    L.push(`- **${s[0].toUpperCase() + s.slice(1)}: ${fr.length}**` + (cand ? ` (${cand} on a name match, for review)` : "") +
      (fr.length ? `. ${restsOn(fr)}.` : "."));
  }
  L.push("");

  // Board actions in the roster state, read only on licenses tied to the NPI by license number.
  const stateOf = new Map(members.map((m) => [m.npi, m.state]));
  const acts = rows.filter((r) => r.claim_type === "state_board_action" && r.jurisdiction === stateOf.get(r.npi));
  L.push("## Board actions", "");
  if (!acts.length) L.push("No board action receipts.");
  for (const st of [...new Set(acts.map((r) => r.jurisdiction))].sort()) {
    const ar = acts.filter((r) => r.jurisdiction === st);
    const on = ar.filter((r) => r.normalized_status === "action_on_record");
    L.push(`- **${st}: ${on.length} with an action on record**, ${ar.length - on.length} none in file, of ${ar.length} NPIs read. ` +
      `${restsOn(ar)}.`);
  }
  L.push("", "An action counts only on a license tied to the NPI by license number. none_in_file never means clear.", "");

  // Exclusions and NPI status.
  const cur = (ct: string) => rows.filter((r) => r.claim_type === ct);
  const found = (r: Row) => r.match_basis === "npi_exact" && !["not_found", "unknown"].includes(r.normalized_status);
  const oig = cur("oig_exclusion"), sam = cur("sam_exclusion"), npiRows = cur("npi_status");
  const samNames = sam.filter((r) => r.match_basis === "name_only");
  L.push("## Exclusions and NPI status", "",
    `- **OIG exclusions found: ${oig.filter(found).length}** of ${oig.length} NPIs checked. ${restsOn(oig)}.`,
    `- **SAM exclusions found: ${sam.filter(found).length}** of ${sam.length} NPIs checked; ${samNames.length} more are name-only candidates for review, not findings. ${restsOn(sam)}.`,
    `- **NPI deactivated: ${npiRows.filter((r) => ["inactive", "deactivated"].includes(r.normalized_status)).length}** of ${npiRows.length} NPIs read. ${restsOn(npiRows)}.`,
    "");

  // Unmatched, by reason.
  const why = new Map<string, number>();
  for (const u of unmatched) {
    const k = `${u.what}: ${u.reason.replace(/\b\d{10}\b/g, "#").replace(/\s+/g, " ").slice(0, 160)}`;
    why.set(k, (why.get(k) ?? 0) + 1);
  }
  L.push(`## Unmatched: ${unmatched.length}`, "");
  if (!why.size) L.push("None.");
  for (const [k, c] of [...why].sort((a, b) => b[1] - a[1]).slice(0, 8)) L.push(`- ${c} · ${k}`);
  if (why.size > 8) L.push(`- ${[...why].slice(8).reduce((a, [, c]) => a + c, 0)} more across ${why.size - 8} other reasons: see unmatched.csv`);
  if (why.size) {
    L.push("", `Matched against the NPPES extract (${restsOn(rows.filter((r) => r.claim_type === "npi_status")) || "no reads"}) ` +
      "and the board files in By state.");
  }
  L.push("");

  // Oldest next check.
  const dues = rows.filter((r) => r.next_check_due_at).sort((a, b) => a.next_check_due_at.localeCompare(b.next_check_due_at));
  L.push("## Oldest next check", "");
  if (!dues.length) L.push("No current receipts.");
  else {
    const o = dues[0];
    const past = dues.filter((r) => Date.parse(r.next_check_due_at) < Date.parse(builtAt));
    L.push(`- **${minute(o.next_check_due_at)}**: ${o.claim_type}${o.jurisdiction ? ` ${o.jurisdiction}` : ""} for NPI ${o.npi}, ` +
      `from ${o.source_name} (file ${day(o.source_published_at) ?? "undated"}, read ${minute(o.retrieved_at)}).`,
      `- **Past due at ${minute(builtAt)}: ${past.length}** of ${rows.length} receipts. ${past.length ? restsOn(past) + "." : ""}`);
  }
  L.push("", "Dates are UTC. A file date is the publisher's (source_published_at); a read is when the garden read it " +
    "(retrieved_at). not_found never means clear. Every row is in receipts.csv with its receipt_id.");
  return L.join("\n") + "\n";
}

// ---------- zip ----------
// A plain zip (deflate, UTF-8 names) with no dependency: CompressionStream("deflate-raw") and a CRC-32 table.
const CRC_TABLE = (() => {
  const t = new Uint32Array(256);
  for (let n = 0; n < 256; n++) {
    let c = n;
    for (let k = 0; k < 8; k++) c = c & 1 ? 0xEDB88320 ^ (c >>> 1) : c >>> 1;
    t[n] = c >>> 0;
  }
  return t;
})();
function crc32(b: Uint8Array): number {
  let c = 0xFFFFFFFF;
  for (let i = 0; i < b.length; i++) c = CRC_TABLE[(c ^ b[i]) & 0xFF] ^ (c >>> 8);
  return (c ^ 0xFFFFFFFF) >>> 0;
}
async function deflateRaw(b: Uint8Array): Promise<Uint8Array> {
  const stream = new Blob([b]).stream().pipeThrough(new CompressionStream("deflate-raw"));
  return new Uint8Array(await new Response(stream).arrayBuffer());
}
async function zipFiles(files: { name: string; data: Uint8Array }[], when: Date): Promise<Uint8Array> {
  const time = (when.getUTCHours() << 11) | (when.getUTCMinutes() << 5) | (when.getUTCSeconds() >> 1);
  const date = ((when.getUTCFullYear() - 1980) << 9) | ((when.getUTCMonth() + 1) << 5) | when.getUTCDate();
  const enc = new TextEncoder();
  const parts: Uint8Array[] = [];
  const central: Uint8Array[] = [];
  let offset = 0;
  for (const f of files) {
    const name = enc.encode(f.name);
    const body = await deflateRaw(f.data);
    const crc = crc32(f.data);
    const local = new DataView(new ArrayBuffer(30));
    [[0, 0x04034b50, 4], [4, 20, 2], [6, 0x0800, 2], [8, 8, 2], [10, time, 2], [12, date, 2], [14, crc, 4],
      [18, body.length, 4], [22, f.data.length, 4], [26, name.length, 2], [28, 0, 2]]
      .forEach(([at, v, size]) => (size === 4 ? local.setUint32(at, v, true) : local.setUint16(at, v, true)));
    const cd = new DataView(new ArrayBuffer(46));
    [[0, 0x02014b50, 4], [4, 20, 2], [6, 20, 2], [8, 0x0800, 2], [10, 8, 2], [12, time, 2], [14, date, 2], [16, crc, 4],
      [20, body.length, 4], [24, f.data.length, 4], [28, name.length, 2], [30, 0, 2], [32, 0, 2], [34, 0, 2], [36, 0, 2],
      [38, 0, 4], [42, offset, 4]]
      .forEach(([at, v, size]) => (size === 4 ? cd.setUint32(at, v, true) : cd.setUint16(at, v, true)));
    parts.push(new Uint8Array(local.buffer), name, body);
    central.push(new Uint8Array(cd.buffer), name);
    offset += 30 + name.length + body.length;
  }
  const cdSize = central.reduce((a, b) => a + b.length, 0);
  const end = new DataView(new ArrayBuffer(22));
  [[0, 0x06054b50, 4], [4, 0, 2], [6, 0, 2], [8, files.length, 2], [10, files.length, 2], [12, cdSize, 4], [16, offset, 4], [20, 0, 2]]
    .forEach(([at, v, size]) => (size === 4 ? end.setUint32(at, v, true) : end.setUint16(at, v, true)));
  const all = [...parts, ...central, new Uint8Array(end.buffer)];
  const out = new Uint8Array(all.reduce((a, b) => a + b.length, 0));
  let p = 0;
  for (const a of all) { out.set(a, p); p += a.length; }
  return out;
}

// ---------- sources ----------

// A data.cms.gov catalog source names two dates in its run notes: the catalog's "modified" date (the release) and
// the period in the version title ("Opt Out Affidavits : 2026-09-01"). Both, or neither.
const CATALOG_NOTE = /from 'modified' of '[^']*? : (\d{4}-\d{2}(?:-\d{2})?)'/;

async function sources() {
  const [status, rows] = await Promise.all([
    rest("GET", "v_source_status", { select: "*" }),
    // select=* so lookup_url is read once the column exists, and null before it does.
    rest("GET", "data_sources", { select: "*", claim_types: "not.is.null" }),
  ]);
  const byName = new Map((rows as Row[]).map((s) => [s.name, s]));
  const catalog = await Promise.all((rows as Row[])
    .filter((s) => String(s.detection_url ?? "").includes("data.cms.gov/data.json"))
    .map(async (s) => {
      const runs = await rest("GET", "ingestion_runs", {
        select: "source_published_at,run_notes", source_id: `eq.${s.id}`, status: "eq.completed",
        order: "completed_at.desc", limit: "1",
      });
      const period = runs[0]?.run_notes?.match(CATALOG_NOTE)?.[1];
      return [s.name, period && runs[0].source_published_at ? { release_date: runs[0].source_published_at, file_period: period } : null] as const;
    }));
  const dates = new Map(catalog);
  return {
    sources: (status as Row[]).map((s) => ({
      ...s,
      lookup_url: byName.get(s.name)?.lookup_url ?? null,
      release_date: dates.get(s.name)?.release_date ?? null,
      file_period: dates.get(s.name)?.file_period ?? null,
    })),
  };
}

// ---------- evidence ----------

// The NPI must sit on one of the tenant's rosters; the same 403 whether or not it exists.
async function requireOnRoster(tenant: Tenant, npi: string | null, refusal: string) {
  if (!npi || !tenant.roster_ids.length) throw new HttpError(403, refusal);
  const onRoster = await rest("GET", "roster_members", {
    select: "roster_id", npi: `eq.${npi}`, roster_id: quoteList(tenant.roster_ids), limit: "1",
  });
  if (!onRoster.length) throw new HttpError(403, refusal);
}

// Lineage tables whose rows are kept in the database, so a receipt can show the row it was read from. Other lineage
// entries (the CMS loaders' row numbers in the artifact file) point into a file we keep only as a hash.
const RETAINED_TABLES = new Set(["providers", "state_license_lookups", "sam_exclusions", "oig_exclusions"]);

async function receiptSource(url: URL, tenant: Tenant, id: string) {
  if (!/^[0-9a-f-]{36}$/.test(id)) throw new HttpError(400, "receipt id must be a uuid");
  const [r] = await rest("GET", "credential_receipts", {
    select: "id,npi,claim_type,jurisdiction,source_id,artifact_id,run_id,retrieved_at,source_published_at,lineage,parser_version",
    id: `eq.${id}`,
  });
  await requireOnRoster(tenant, r?.npi ?? null, "receipt not available to this key");
  const [[src], art, run] = await Promise.all([
    rest("GET", "data_sources", { select: "name,accepted_for_sale", id: `eq.${r.source_id}` }),
    r.artifact_id
      ? rest("GET", "source_artifacts", { select: "sha256,file_name,retrieved_at,source_published_at,row_count", id: `eq.${r.artifact_id}` })
      : [],
    r.run_id ? rest("GET", "ingestion_runs", { select: "completed_at,run_type", id: `eq.${r.run_id}` }) : [],
  ]);
  if (!src.accepted_for_sale && url.searchParams.get("include_unaccepted") !== "true") {
    throw new HttpError(403, "source not accepted for sale; ask with include_unaccepted=true");
  }
  const lineage: Row[] = Array.isArray(r.lineage) ? r.lineage : [];
  const kept = lineage.filter((e) => RETAINED_TABLES.has(e.table) && /^[0-9a-f-]{36}$/.test(String(e.id)));
  const rows = (await Promise.all(kept.map(async (e) => {
    const [row] = await rest("GET", e.table, { select: "*", id: `eq.${e.id}` });
    return row ? { table: e.table, id: e.id, row } : null;
  }))).filter(Boolean);
  return {
    receipt_id: r.id,
    npi: r.npi,
    claim_type: r.claim_type,
    jurisdiction: r.jurisdiction,
    source_name: src.name,
    retained: rows.length > 0,
    rows,
    // Lineage that names a place in the file rather than a stored row (a CMS row number), shown as given.
    file_pointers: lineage.filter((e) => !RETAINED_TABLES.has(e.table)),
    artifact: art[0] ?? null,
    captured_at: art[0]?.retrieved_at ?? r.retrieved_at,
    run_completed_at: run[0]?.completed_at ?? null,
    writer_version: r.parser_version,
  };
}

// A license receipt picks one board row when several link to the NPI (receipts_for_state_licenses/1). These are
// all of them, in the writer's order, the first being the one the receipt carries.
const LICENSE_SELECTION_RULE = "highest match confidence, then active status, then latest issue date, then row id " +
  "(receipts_for_state_licenses/1)";
const LICENSE_ROW_FIELDS = "id,license_number,license_type,raw_status,normalized_status,issue_date,expiration_date," +
  "match_basis,match_confidence,source_record_key";

async function addMatchedLicenses(claims: Row[]) {
  const multi = claims.filter((c) => c.claim_type === "state_license" && Number(c.claim?.licenses_matched) > 1);
  if (!multi.length) return;
  const lineage = new Map((await inChunks(multi.map((c) => c.receipt_id), (inList) =>
    rest("GET", "credential_receipts", { select: "id,lineage", id: inList }))).map((r) => [r.id, r.lineage ?? []]));
  const ids = [...new Set([...lineage.values()].flat().filter((e: Row) => e.table === "state_license_lookups").map((e: Row) => e.id))];
  const rows = new Map((await inChunks(ids as string[], (inList) =>
    rest("GET", "state_license_lookups", { select: LICENSE_ROW_FIELDS, id: inList }))).map((l) => [l.id, l]));
  const rank = (a: Row, b: Row) =>
    Number(b.match_confidence) - Number(a.match_confidence) ||
    Number(b.normalized_status === "active") - Number(a.normalized_status === "active") ||
    (b.issue_date ?? "").localeCompare(a.issue_date ?? "") ||
    String(a.id).localeCompare(String(b.id));
  for (const c of multi) {
    const mine = (lineage.get(c.receipt_id) as Row[]).map((e) => rows.get(e.id)).filter(Boolean) as Row[];
    c.matched_licenses = mine.sort(rank).map(({ id: _id, ...l }, i) => ({ ...l, selected: i === 0 }));
    c.selection_rule = LICENSE_SELECTION_RULE;
    // TODO(link origin): the license writer does not record which store linked the license to the NPI (NPPES
    // license field, provider_credentials, or a prior exact link). Record it on state_license_lookups, then return
    // it here instead of null.
    c.link_origin = null;
  }
}

// ---------- deltas ----------

// field_change: the normalized status is unchanged but a canonical claim field differs from the superseded row.
// Compared: license_number (the receipt column), and issue_date, expiration_date and restrictions in claim;
// restrictions only when either row carries the key. For a board action receipt: the latest action's kind, date and
// reference, and each action both rows list (matched by claim.actions[].key); an action that only the new row lists
// makes the row a status_change instead (a new action), and one that only the old row lists is a field_change.
// Everything else unchanged stays refresh. scripts/refresh_roster_receipts.py change_kind() applies the same rules.
const FIELD_CHANGE_FIELDS: [string, (r: Row) => unknown, (r: Row) => boolean][] = [
  ["license_number", (r) => r.license_number, () => true],
  ["issue_date", (r) => r.claim?.issue_date, () => true],
  ["expiration_date", (r) => r.claim?.expiration_date, () => true],
  ["restrictions", (r) => r.claim?.restrictions, (r) => !!r.claim && "restrictions" in r.claim],
];
const norm = (v: unknown) => (v === undefined || v === null || v === "" ? null : JSON.stringify(v));

const BOARD_ACTION_FIELDS = ["action_kind", "action_date", "reference"];
const ACTION_ITEM_FIELDS = ["license_number", "kind", "classification", "date", "effective_date", "reference", "description"];
const actionsByKey = (r: Row) =>
  new Map(((r.claim?.actions ?? []) as Row[]).filter((a) => a?.key).map((a) => [a.key as string, a]));

function boardActionChanges(r: Row, p: Row) {
  const now = actionsByKey(r), before = actionsByKey(p);
  const added = [...now.keys()].filter((k) => !before.has(k));
  if (added.length) return { kind: "status_change", changes: added.map((k) => ({ field: "actions", old: null, new: now.get(k) })) };
  const changes: Row[] = BOARD_ACTION_FIELDS
    .filter((f) => norm(r.claim?.[f]) !== norm(p.claim?.[f]))
    .map((f) => ({ field: f, old: p.claim?.[f] ?? null, new: r.claim?.[f] ?? null }));
  for (const [k, a] of before) if (!now.has(k)) changes.push({ field: "actions", old: a, new: null });
  for (const [k, a] of now) {
    const b = before.get(k);
    if (!b) continue;
    for (const f of ACTION_ITEM_FIELDS) {
      if (norm(a[f]) !== norm(b[f])) changes.push({ field: `actions[${k}].${f}`, old: b[f] ?? null, new: a[f] ?? null });
    }
  }
  return { kind: changes.length ? "field_change" : "refresh", changes };
}

async function markFieldChanges(rows: Row[]) {
  const refresh = rows.filter((r) => r.change_kind === "refresh" && r.supersedes_id);
  if (!refresh.length) return;
  const prior = new Map((await inChunks([...new Set(refresh.map((r) => r.supersedes_id as string))], (inList) =>
    rest("GET", "credential_receipts", { select: "id,license_number,claim", id: inList }))).map((p) => [p.id, p]));
  for (const r of refresh) {
    const p = prior.get(r.supersedes_id);
    if (!p) continue;
    if (r.claim_type === "state_board_action") {
      const { kind, changes } = boardActionChanges(r, p);
      if (kind === "refresh") continue;
      r.change_kind = kind;
      r.field_changes = changes;
      r.prior_receipt_id = r.supersedes_id;
      continue;
    }
    const changes = FIELD_CHANGE_FIELDS
      .filter(([, get, present]) => (present(r) || present(p)) && norm(get(r)) !== norm(get(p)))
      .map(([field, get]) => ({ field, old: get(p) ?? null, new: get(r) ?? null }));
    if (!changes.length) continue;
    r.change_kind = "field_change";
    r.field_changes = changes;
    r.prior_receipt_id = r.supersedes_id;
  }
}

function parseLimit(raw: string | null): number {
  if (raw === null || raw === "") return DEFAULT_LIMIT;
  const n = Number(raw);
  if (!Number.isInteger(n) || n < 1) throw new HttpError(400, "limit must be a positive integer");
  return Math.min(n, MAX_LIMIT);
}

// A route answers with a body to send as JSON (status 200), or with a Response of its own (the job's 202, the zip).
async function route(req: Request, tenant: Tenant, cors: Record<string, string>): Promise<unknown> {
  const url = new URL(req.url);
  const path = url.pathname.replace(/^.*?\/freshroot(?=\/|$)/, "").replace(/\/+$/, "");
  const includeUnaccepted = url.searchParams.get("include_unaccepted") === "true";
  let m: RegExpMatchArray | null;

  if ((m = path.match(/^\/v1\/rosters\/([^/]+)\/npis$/))) {
    if (req.method !== "POST") throw new HttpError(405, "POST only");
    return addToRoster(req, url, tenant, requireRoster(tenant, decodeURIComponent(m[1])));
  }
  if ((m = path.match(/^\/v1\/rosters\/([^/]+)\/jobs$/))) {
    if (req.method !== "POST") throw new HttpError(405, "POST only");
    return json(await createJob(req, tenant, requireRoster(tenant, decodeURIComponent(m[1]))), 202, cors);
  }
  if (req.method !== "GET") throw new HttpError(405, "GET only");

  if ((m = path.match(/^\/v1\/jobs\/([^/]+)$/))) return getJob(tenant, decodeURIComponent(m[1]));

  if ((m = path.match(/^\/v1\/rosters\/([^/]+)\/export$/))) {
    return exportRoster(url, requireRoster(tenant, decodeURIComponent(m[1])), cors);
  }

  if (path === "/v1/lookup") return lookup(url, tenant);

  if (path === "/v1/sources") return sources();

  if ((m = path.match(/^\/v1\/receipts\/([^/]+)\/source$/))) return receiptSource(url, tenant, decodeURIComponent(m[1]));

  if ((m = path.match(/^\/v1\/rosters\/([^/]+)$/))) {
    const rosterId = requireRoster(tenant, decodeURIComponent(m[1]));
    const roster = await rpc("freshroot_roster", { p_roster_id: rosterId, p_include_unaccepted: includeUnaccepted });
    if (!roster) throw new HttpError(404, "roster not found");
    const npis = roster.members.map((m: { npi: string }) => m.npi);
    const [facts, checks, licenses] = await Promise.all([
      providerFacts(npis), rosterChecks(roster.members, includeUnaccepted), licenseRuns(),
    ]);
    roster.license_states = [...licenses.keys()].sort();
    for (const m of roster.members) {
      m.provider = facts.get(m.npi) ?? null;
      m.checks = checks.get(m.npi);
      const dues = Object.values(m.checks).map((c) => (c as { next_check_due_at?: string } | null)?.next_check_due_at).filter(Boolean) as string[];
      m.next_check_due_at = dues.length ? dues.reduce((a, b) => (Date.parse(a) <= Date.parse(b) ? a : b)) : null;
    }
    return roster;
  }

  if ((m = path.match(/^\/v1\/providers\/([^/]+)\/claims$/))) {
    const npi = m[1];
    if (!/^\d{10}$/.test(npi)) throw new HttpError(400, "npi must be 10 digits");
    await requireOnRoster(tenant, npi, "npi not on a roster available to this key");
    const [claims, facts] = await Promise.all([
      rpc("freshroot_claims", { p_npi: npi, p_include_unaccepted: includeUnaccepted }),
      providerFacts([npi]),
    ]);
    await addMatchedLicenses(claims.claims ?? []);
    return { ...claims, provider: facts.get(npi) ?? null };
  }

  if (path === "/v1/deltas") {
    const rosterId = requireRoster(tenant, url.searchParams.get("roster_id"));
    const limit = parseLimit(url.searchParams.get("limit"));
    const rawCursor = url.searchParams.get("cursor");
    const after = rawCursor ? decodeCursor(rawCursor) : null;
    const rows = await rpc("freshroot_deltas", {
      p_roster_id: rosterId,
      p_after_created_at: after?.createdAt ?? null,
      p_after_id: after?.id ?? null,
      p_limit: limit,
      p_include_unaccepted: includeUnaccepted,
    });
    const page = rows.slice(0, limit);
    await markFieldChanges(page);
    const last = page[page.length - 1];
    return {
      roster_id: rosterId,
      include_unaccepted: includeUnaccepted,
      limit,
      count: page.length,
      has_more: rows.length > limit,
      next_cursor: last ? encodeCursor(last.created_at, last.receipt_id) : rawCursor,
      deltas: page,
    };
  }

  if (path === "/v1/coverage") {
    const rosterId = requireRoster(tenant, url.searchParams.get("roster_id"));
    const rows = await rpc("freshroot_coverage", { p_roster_id: rosterId });
    const buckets: Record<string, unknown[]> = { covered_today: [], in_30_days: [], under_license: [], never: [] };
    let rosterSize = 0;
    for (const { ord: _ord, bucket, roster_size, ...row } of rows) {
      rosterSize = roster_size ?? rosterSize;
      buckets[bucket].push(row);
    }
    return { roster_id: rosterId, roster_size: rosterSize, buckets };
  }

  throw new HttpError(404, "no such route");
}

Deno.serve(async (req: Request) => {
  const cors = corsHeaders(req.headers.get("origin"));
  if (req.method === "OPTIONS") return new Response(null, { status: 204, headers: cors });
  try {
    if (req.method !== "GET" && req.method !== "POST") throw new HttpError(405, "GET or POST only");
    if (!SUPABASE_URL || !SERVICE_KEY) throw new HttpError(500, "function secrets not set");
    const tenant = await authenticate(req);
    const out = await route(req, tenant, cors);
    return out instanceof Response ? out : json(out, 200, cors);
  } catch (e) {
    if (e instanceof HttpError) return json({ error: e.message }, e.status, cors);
    console.error(e);
    return json({ error: "internal error" }, 500, cors);
  }
});

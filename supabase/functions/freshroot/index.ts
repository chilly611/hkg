// freshroot · the FreshRoot API. One Supabase Edge Function.
//
//   GET  /v1/sources                         v_source_status
//   GET  /v1/rosters/{roster_id}             the roster, one summary row per NPI with provider facts and the four
//                                            current checks (state license, NPI, OIG, SAM)
//   GET  /v1/providers/{npi}/claims          provider facts and current receipts, each with its history
//   GET  /v1/deltas?roster_id=&cursor=&limit= receipts created after the cursor, with change_kind
//   GET  /v1/coverage?roster_id=             roster_coverage(): covered today, in 30 days, under license, never
//   GET  /v1/lookup?q=&state=&roster_id=     up to 20 individual providers by NPI or name, each marked on_roster.
//                                            Reads only; it writes nothing.
//   POST /v1/rosters/{roster_id}/npis        {"npis": [...up to 20]}: adds them to the roster, then writes their
//                                            receipts with the packet builder's SQL writer. The only write route,
//                                            so receipts are written only for roster NPIs.
//
// Auth: X-FreshRoot-Key, SHA-256 hashed and looked up in api_tenants. No key or an unknown key: 401.
// A tenant reads only the rosters in its roster_ids, and only NPIs on those rosters: anything else is 403.
// Receipts from a source with accepted_for_sale = false are left out unless ?include_unaccepted=true, and every
// row carries shippable and rights ("pending" while the source is not accepted for sale).
// The service role key comes from the function's Supabase secrets; it is never sent to a caller.
// SQL: migrations/2026-10-27_freshroot_api.sql; the name search index is migrations/2026-10-28_freshroot_lookup_index.sql.
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
async function pgrst(method: "GET" | "POST", path: string, params?: Record<string, string>, body?: unknown, prefer?: string) {
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

async function rest(method: "GET" | "POST", path: string, params?: Record<string, string>, body?: unknown, prefer?: string) {
  const { text } = await pgrst(method, path, params, body, prefer);
  return text ? JSON.parse(text) : null;
}

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
// short and each response well under the cap (a roster NPI has a handful of current receipts).
const IN_CHUNK = 100;
// deno-lint-ignore no-explicit-any
type Row = Record<string, any>;
async function inChunks(values: string[], fetchChunk: (inList: string) => Promise<Row[]>): Promise<Row[]> {
  const chunks: string[][] = [];
  for (let i = 0; i < values.length; i += IN_CHUNK) chunks.push(values.slice(i, i + IN_CHUNK));
  return (await Promise.all(chunks.map((c) => fetchChunk(`in.(${c.join(",")})`)))).flat();
}

type ProviderFacts = {
  first_name: string | null;
  middle_name: string | null;
  last_name: string | null;
  credential: string | null;
  primary_taxonomy: { code: string; description: string | null } | null;
};

// Name, credential suffix and primary taxonomy from providers (NPPES), joined on NPI; taxonomy through
// provider_taxonomies.provider_id. NPPES credentials come as typed ("M.D.,"), so only edge spaces and commas go.
const FACTS_SELECT = "npi,first_name,middle_name,last_name,credential,provider_taxonomies(taxonomy_code,taxonomy_description,is_primary)";

function toFacts(p: Row): ProviderFacts {
  const tax = (p.provider_taxonomies ?? []).find((t: { is_primary: boolean }) => t.is_primary);
  return {
    first_name: p.first_name,
    middle_name: p.middle_name,
    last_name: p.last_name,
    credential: p.credential?.replace(/^[\s,]+|[\s,]+$/g, "") || null,
    primary_taxonomy: tax ? { code: tax.taxonomy_code, description: tax.taxonomy_description } : null,
  };
}

async function providerFacts(npis: string[]): Promise<Map<string, ProviderFacts>> {
  const rows = await inChunks(npis, (inList) => rest("GET", "providers", { select: FACTS_SELECT, npi: inList }));
  return new Map(rows.map((p) => [p.npi, toFacts(p)]));
}

// The NPPES practice-address state, or null. Addresses are loaded for about 572K of the 9.4M providers so far, so
// null is common; it means the registry extract names no state, never that we picked one.
function practiceState(p: Row): string | null {
  const a = (p.provider_addresses ?? []).find((x: { address_type: string }) => x.address_type === "practice");
  return a?.state ? String(a.state).toUpperCase() : null;
}

const quoteList = (ids: string[]) => `in.(${ids.map((r) => `"${r.replace(/"/g, "")}"`).join(",")})`;

// The four checks a roster row shows, each the current receipt (v_current_receipts) read through
// v_freshroot_receipts so stage carries "stale" and rights match every other route. The license is the one in
// the roster state, latest retrieved first, as freshroot_roster picks it.
const CHECK_CLAIMS = ["state_license", "npi_status", "oig_exclusion", "sam_exclusion"] as const;
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
    if (r.claim_type === "state_license" && r.jurisdiction !== stateOf.get(r.npi)) continue;
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
// receipts_for_exclusions (OIG and SAM in one transaction) and receipts_for_state_licenses. This calls the same
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
    ...[...licenses].map(([st, runId]) =>
      step(`state_license:${st}`, runId, "state_license", members.filter((m) => m.state === st).map((m) => m.npi),
        "receipts_for_state_licenses", { p_state: st }, RPC_BATCH)),
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
    select: `${FACTS_SELECT},status,provider_addresses${stateParam ? "!inner" : ""}(state,address_type)`,
    entity_type: "eq.individual",
    "provider_addresses.address_type": "eq.practice",
    limit: String(LOOKUP_LIMIT + 1),
  };
  if (stateParam) params["provider_addresses.state"] = `eq.${stateParam}`;
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

  const t0 = performance.now();
  const [rows, licenses] = await Promise.all([rest("GET", "providers", params), licenseRuns()]);
  const tookMs = Math.round(performance.now() - t0);
  const page = (rows as Row[]).slice(0, LOOKUP_LIMIT);
  const onRoster = new Set(page.length && rosterIds.length
    ? (await rest("GET", "roster_members", { select: "npi", npi: `in.(${page.map((p) => p.npi).join(",")})`, roster_id: quoteList(rosterIds) }))
      .map((r: Row) => r.npi)
    : []);
  const candidates = page.map((p) => {
    const st = practiceState(p);
    return {
      npi: p.npi, ...toFacts(p), state: st, npi_status: p.status,
      on_roster: onRoster.has(p.npi), license_covered: !!st && licenses.has(st),
    };
  }).sort((x, y) => `${x.last_name}|${x.first_name}|${x.npi}`.localeCompare(`${y.last_name}|${y.first_name}|${y.npi}`));
  return {
    q, state: stateParam || null, license_states: [...licenses.keys()].sort(),
    count: candidates.length, more: rows.length > LOOKUP_LIMIT, took_ms: tookMs, candidates,
  };
}

// ---------- roster-add ----------

// What the license check says for one member, in plain words. A state we hold no board file for is "not covered
// yet", never a guess; an NPI the board file could not be linked to carries the writer's own limitation text.
function licenseOutcome(state: string | null, licenses: Map<string, string>, check: Row | null) {
  if (!state) return { covered: false, matched: false, reason: "NPPES lists no practice state for this NPI, so no state license was checked." };
  if (!licenses.has(state)) return { covered: false, matched: false, reason: `State license: not covered yet for ${state}.` };
  if (!check) return { covered: true, matched: false, reason: "No license receipt was written; adding again retries it." };
  if (check.match_basis === "none") return { covered: true, matched: false, reason: check.limitations };
  return { covered: true, matched: true, match_basis: check.match_basis, stage: check.stage, reason: check.limitations ?? null };
}

async function addToRoster(req: Request, url: URL, tenant: Tenant, rosterId: string) {
  const includeUnaccepted = url.searchParams.get("include_unaccepted") === "true";
  let body: { npis?: unknown };
  try { body = await req.json(); } catch { throw new HttpError(400, "body must be JSON: {\"npis\": [...]}"); }
  if (!Array.isArray(body?.npis) || !body.npis.length) throw new HttpError(400, "npis must be a non-empty list");
  const npis = [...new Set(body.npis.map((n) => String(n).trim()))];
  if (npis.length > ADD_LIMIT) throw new HttpError(400, `at most ${ADD_LIMIT} NPIs per call`);
  if (!npis.every((n) => /^\d{10}$/.test(n))) throw new HttpError(400, "every npi must be 10 digits");

  const [found, licenses, countBefore] = await Promise.all([
    rest("GET", "providers", { select: `${FACTS_SELECT},entity_type,provider_addresses(state,address_type)`, npi: `in.(${npis.join(",")})` }),
    licenseRuns(),
    rosterCount(rosterId),
  ]);
  const byNpi = new Map((found as Row[]).map((p) => [p.npi, p]));
  const notAdded = npis.filter((n) => byNpi.get(n)?.entity_type !== "individual").map((n) => ({
    npi: n, reason: byNpi.has(n) ? "not an individual provider" : "not in the NPPES registry extract",
  }));
  const addable = npis.filter((n) => byNpi.get(n)?.entity_type === "individual");

  // The roster state is the NPPES practice state. A member already on the roster keeps its row as it is.
  const inserted = addable.length
    ? await rest("POST", "roster_members", undefined,
      addable.map((n) => ({ roster_id: rosterId, npi: n, state: practiceState(byNpi.get(n)!) })),
      "resolution=ignore-duplicates,return=representation")
    : [];
  const added = new Set((inserted as Row[]).map((r) => r.npi));
  const members: { npi: string; state: string | null }[] = addable.length
    ? await rest("GET", "roster_members", { select: "npi,state", roster_id: `eq.${rosterId}`, npi: `in.(${addable.join(",")})` })
    : [];

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
        provider: toFacts(byNpi.get(m.npi)!),
        receipts_written: shown.filter((r) => r.npi === m.npi).map(({ id, accepted_for_sale: _a, ...r }) => ({ receipt_id: id, ...r })),
        checks: mine,
        license: licenseOutcome(m.state, licenses, mine.state_license as Row | null),
      };
    }),
    not_added: notAdded,
  };
}

function parseLimit(raw: string | null): number {
  if (raw === null || raw === "") return DEFAULT_LIMIT;
  const n = Number(raw);
  if (!Number.isInteger(n) || n < 1) throw new HttpError(400, "limit must be a positive integer");
  return Math.min(n, MAX_LIMIT);
}

async function route(req: Request, tenant: Tenant): Promise<unknown> {
  const url = new URL(req.url);
  const path = url.pathname.replace(/^.*?\/freshroot(?=\/|$)/, "").replace(/\/+$/, "");
  const includeUnaccepted = url.searchParams.get("include_unaccepted") === "true";
  let m: RegExpMatchArray | null;

  if ((m = path.match(/^\/v1\/rosters\/([^/]+)\/npis$/))) {
    if (req.method !== "POST") throw new HttpError(405, "POST only");
    return addToRoster(req, url, tenant, requireRoster(tenant, decodeURIComponent(m[1])));
  }
  if (req.method !== "GET") throw new HttpError(405, "GET only");

  if (path === "/v1/lookup") return lookup(url, tenant);

  if (path === "/v1/sources") {
    return { sources: await rest("GET", "v_source_status", { select: "*" }) };
  }

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
    if (!tenant.roster_ids.length) throw new HttpError(403, "npi not on a roster available to this key");
    const onRoster = await rest("GET", "roster_members", {
      select: "roster_id",
      npi: `eq.${npi}`,
      roster_id: quoteList(tenant.roster_ids),
      limit: "1",
    });
    if (!onRoster.length) throw new HttpError(403, "npi not on a roster available to this key");
    const [claims, facts] = await Promise.all([
      rpc("freshroot_claims", { p_npi: npi, p_include_unaccepted: includeUnaccepted }),
      providerFacts([npi]),
    ]);
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
    return json(await route(req, tenant), 200, cors);
  } catch (e) {
    if (e instanceof HttpError) return json({ error: e.message }, e.status, cors);
    console.error(e);
    return json({ error: "internal error" }, 500, cors);
  }
});

// freshroot · the FreshRoot read API. One Supabase Edge Function, GET only.
//
//   GET /v1/sources                         v_source_status
//   GET /v1/rosters/{roster_id}             the roster, one summary row per NPI with provider facts and the four
//                                           current checks (state license, NPI, OIG, SAM)
//   GET /v1/providers/{npi}/claims          provider facts and current receipts, each with its history
//   GET /v1/deltas?roster_id=&cursor=&limit= receipts created after the cursor, with change_kind
//   GET /v1/coverage?roster_id=             roster_coverage(): covered today, in 30 days, under license, never
//
// Auth: X-FreshRoot-Key, SHA-256 hashed and looked up in api_tenants. No key or an unknown key: 401.
// A tenant reads only the rosters in its roster_ids, and only NPIs on those rosters: anything else is 403.
// Receipts from a source with accepted_for_sale = false are left out unless ?include_unaccepted=true, and every
// row carries shippable and rights ("pending" while the source is not accepted for sale).
// The service role key comes from the function's Supabase secrets; it is never sent to a caller.
// SQL: migrations/2026-10-27_freshroot_api.sql. Deployed with verify_jwt = false: the tenant key is the auth.

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

function corsHeaders(origin: string | null): Record<string, string> {
  const h: Record<string, string> = { "Vary": "Origin" };
  if (origin && (origin === SITE_ORIGIN || LOCALHOST_ORIGIN.test(origin))) {
    h["Access-Control-Allow-Origin"] = origin;
    h["Access-Control-Allow-Methods"] = "GET, OPTIONS";
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
async function rest(method: "GET" | "POST", path: string, params?: Record<string, string>, body?: unknown) {
  const qs = params ? "?" + new URLSearchParams(params).toString() : "";
  const headers: Record<string, string> = { "apikey": SERVICE_KEY, "Content-Type": "application/json" };
  if (SERVICE_KEY.startsWith("eyJ")) headers["Authorization"] = `Bearer ${SERVICE_KEY}`;
  const resp = await fetch(`${SUPABASE_URL}/rest/v1/${path}${qs}`, {
    method,
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const text = await resp.text();
  if (!resp.ok) {
    console.error(`PostgREST ${method} ${path} -> ${resp.status}: ${text.slice(0, 500)}`);
    throw new HttpError(502, "upstream query failed");
  }
  return text ? JSON.parse(text) : null;
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
async function providerFacts(npis: string[]): Promise<Map<string, ProviderFacts>> {
  const rows = await inChunks(npis, (inList) =>
    rest("GET", "providers", {
      select: "npi,first_name,middle_name,last_name,credential,provider_taxonomies(taxonomy_code,taxonomy_description,is_primary)",
      npi: inList,
    }));
  const out = new Map<string, ProviderFacts>();
  for (const p of rows) {
    const tax = (p.provider_taxonomies ?? []).find((t: { is_primary: boolean }) => t.is_primary);
    out.set(p.npi, {
      first_name: p.first_name,
      middle_name: p.middle_name,
      last_name: p.last_name,
      credential: p.credential?.replace(/^[\s,]+|[\s,]+$/g, "") || null,
      primary_taxonomy: tax ? { code: tax.taxonomy_code, description: tax.taxonomy_description } : null,
    });
  }
  return out;
}

// The four checks a roster row shows, each the current receipt (v_current_receipts) read through
// v_freshroot_receipts so stage carries "stale" and rights match every other route. The license is the one in
// the roster state, latest retrieved first, as freshroot_roster picks it.
const CHECK_CLAIMS = ["state_license", "npi_status", "oig_exclusion", "sam_exclusion"] as const;
const CHECK_FIELDS = "id,npi,claim_type,jurisdiction,license_number,normalized_status,raw_status,stage,source_name," +
  "source_published_at,retrieved_at,next_check_due_at,created_at,accepted_for_sale,shippable,rights";

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

  if (path === "/v1/sources") {
    return { sources: await rest("GET", "v_source_status", { select: "*" }) };
  }

  if ((m = path.match(/^\/v1\/rosters\/([^/]+)$/))) {
    const rosterId = requireRoster(tenant, decodeURIComponent(m[1]));
    const roster = await rpc("freshroot_roster", { p_roster_id: rosterId, p_include_unaccepted: includeUnaccepted });
    if (!roster) throw new HttpError(404, "roster not found");
    const npis = roster.members.map((m: { npi: string }) => m.npi);
    const [facts, checks] = await Promise.all([providerFacts(npis), rosterChecks(roster.members, includeUnaccepted)]);
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
      roster_id: `in.(${tenant.roster_ids.map((r) => `"${r.replace(/"/g, "")}"`).join(",")})`,
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
    if (req.method !== "GET") throw new HttpError(405, "GET only");
    if (!SUPABASE_URL || !SERVICE_KEY) throw new HttpError(500, "function secrets not set");
    const tenant = await authenticate(req);
    return json(await route(req, tenant), 200, cors);
  } catch (e) {
    if (e instanceof HttpError) return json({ error: e.message }, e.status, cors);
    console.error(e);
    return json({ error: "internal error" }, 500, cors);
  }
});

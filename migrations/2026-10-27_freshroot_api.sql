-- 2026-10-27 · FreshRoot read API: rosters, tenant keys, and the SQL the freshroot edge function reads
-- Idempotent. Adds, never drops. No receipt, source or rights column is changed.
--
-- What this adds:
--   1. rosters + roster_members: a named list of NPIs a tenant may read
--   2. api_tenants: one row per API key, stored as a SHA-256 hash, bound to roster ids
--   3. v_freshroot_receipts: every receipt with its source name, rights flag and shippable flag
--   4. roster_coverage(npis[]): the coverage buckets. scripts/build_credential_packet.py and the API both call it
--   5. freshroot_coverage / freshroot_roster / freshroot_claims / freshroot_deltas: what the API calls
--
-- Everything here is closed to anon and authenticated. Only service_role (the edge function) reads it.

BEGIN;

-- 1. Rosters.
CREATE TABLE IF NOT EXISTS rosters (
  id          TEXT PRIMARY KEY,                              -- e.g. first-packet-2026-10-26
  name        TEXT NOT NULL,
  source_file TEXT,                                          -- where the NPIs came from
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS roster_members (
  roster_id      TEXT NOT NULL REFERENCES rosters(id) ON DELETE CASCADE,
  npi            VARCHAR(10) NOT NULL CHECK (npi ~ '^[0-9]{10}$'),
  state          VARCHAR(2),                                 -- the state whose license the roster asks about
  license_number VARCHAR(255),
  license_type   TEXT,
  match_basis_at_selection VARCHAR(24),                      -- how the NPI was linked when the roster was built
  created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (roster_id, npi)
);
CREATE INDEX IF NOT EXISTS idx_roster_members_npi ON roster_members(npi);

-- 2. Tenants. The key itself is never stored; only its SHA-256 hex digest.
CREATE TABLE IF NOT EXISTS api_tenants (
  id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name       TEXT NOT NULL UNIQUE,
  key_hash   CHAR(64) NOT NULL UNIQUE CHECK (key_hash ~ '^[0-9a-f]{64}$'),
  roster_ids TEXT[] NOT NULL DEFAULT '{}',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE rosters        ENABLE ROW LEVEL SECURITY;
ALTER TABLE roster_members ENABLE ROW LEVEL SECURITY;
ALTER TABLE api_tenants    ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON rosters, roster_members, api_tenants FROM anon, authenticated;

-- The deltas cursor walks (created_at, id).
CREATE INDEX IF NOT EXISTS idx_receipts_created ON credential_receipts(created_at, id);

-- 3. Every receipt with the fields a reader needs. stage and shippable follow build_credential_packet.py:
--    a verified row past its due date reads as stale, and a row ships only when its source is accepted for sale
--    and it is real, verified and not past due.
CREATE OR REPLACE VIEW v_freshroot_receipts WITH (security_invoker = true) AS
SELECT
  r.id, r.npi, r.claim_type, r.jurisdiction, r.license_number, r.normalized_status, r.raw_status, r.claim,
  r.source_effective_at, r.source_published_at, r.retrieved_at, r.next_check_due_at, r.origin,
  CASE WHEN r.stage = 'verified' AND r.next_check_due_at < NOW() THEN 'stale' ELSE r.stage END AS stage,
  r.match_basis, r.match_confidence, r.limitations, r.supersedes_id, r.created_at,
  s.name AS source_name,
  s.accepted_for_sale,
  (s.accepted_for_sale AND r.origin = 'real' AND r.stage = 'verified' AND r.next_check_due_at >= NOW()) AS shippable,
  CASE WHEN s.accepted_for_sale THEN 'accepted' ELSE 'pending' END AS rights,
  a.sha256 AS artifact_sha256
FROM credential_receipts r
JOIN data_sources s ON s.id = r.source_id
LEFT JOIN source_artifacts a ON a.id = r.artifact_id;

REVOKE ALL ON v_freshroot_receipts FROM anon, authenticated;

-- 4. Coverage for a roster, in four buckets:
--      covered_today  a pilot claim with a current receipt for at least one roster NPI (covered = how many)
--      in_30_days     a pilot claim whose source is seeded but holds no current receipt for this roster yet,
--                     and medicaid_exclusion (not yet ingested)
--      under_license  needs a contract or confirmed terms before it can be loaded
--      never          the garden will not resell it
--    Pilot rows carry covered and roster_size; the rest carry a reason and covered = NULL.
--    This is the one definition: build_credential_packet.py calls it over PostgREST for coverage.md.
CREATE OR REPLACE FUNCTION roster_coverage(p_npis TEXT[])
RETURNS TABLE (ord INTEGER, claim_key TEXT, claim_type TEXT, jurisdiction TEXT, bucket TEXT,
               covered INTEGER, roster_size INTEGER, reason TEXT) AS $$
  WITH roster AS (
    SELECT DISTINCT n AS npi FROM unnest(p_npis) n
  ),
  have AS (
    SELECT DISTINCT c.npi, c.claim_type, COALESCE(c.jurisdiction, '') AS jur
    FROM v_current_receipts c WHERE c.npi = ANY(p_npis)
  ),
  pilot (ord, claim_type, jur) AS (
    VALUES (1, 'npi_status', ''), (2, 'oig_exclusion', ''), (3, 'sam_exclusion', ''),
           (4, 'state_license', 'TX'), (5, 'state_license', 'FL'), (6, 'state_license', 'CA'), (7, 'state_license', 'UT'),
           (8, 'state_board_action', 'TX'), (9, 'state_board_action', 'FL'), (10, 'state_board_action', 'CA'),
           (11, 'state_board_action', 'UT'), (12, 'medicare_optout', ''), (13, 'pecos_enrollment', '')
  ),
  counted AS (
    SELECT p.ord, p.claim_type, p.jur,
           (SELECT count(*) FROM have h JOIN roster r ON r.npi = h.npi
            WHERE h.claim_type = p.claim_type AND h.jur = p.jur)::INTEGER AS covered
    FROM pilot p
  ),
  not_yet (ord, claim_type, bucket, reason) AS (
    VALUES (14, 'dea_registration',    'under_license', 'licensed source (NTIS DEA file); contract not in place'),
           (15, 'board_certification', 'under_license', 'licensed source (ABMS); contract not in place'),
           (16, 'medicaid_exclusion',  'in_30_days',    'state Medicaid exclusion lists; not yet ingested'),
           (17, 'nurse_license',       'under_license', 'Nursys; terms not confirmed'),
           (18, 'npdb',                'never',         'authorized queriers only; never resold. The buyer queries it.')
  )
  SELECT c.ord, c.claim_type || CASE WHEN c.jur = '' THEN '' ELSE ':' || c.jur END, c.claim_type, NULLIF(c.jur, ''),
         CASE WHEN c.covered > 0 THEN 'covered_today' ELSE 'in_30_days' END,
         c.covered, (SELECT count(*) FROM roster)::INTEGER,
         CASE WHEN c.covered > 0 THEN NULL ELSE 'pilot source seeded; no current receipt for this roster yet' END
  FROM counted c
  UNION ALL
  SELECT n.ord, n.claim_type, n.claim_type, NULL, n.bucket, NULL, NULL, n.reason FROM not_yet n
  ORDER BY 1;
$$ LANGUAGE sql STABLE;

-- The API's entry point: the same function over a stored roster (members read in SQL, so no row cap applies).
CREATE OR REPLACE FUNCTION freshroot_coverage(p_roster_id TEXT)
RETURNS TABLE (ord INTEGER, claim_key TEXT, claim_type TEXT, jurisdiction TEXT, bucket TEXT,
               covered INTEGER, roster_size INTEGER, reason TEXT) AS $$
  SELECT * FROM roster_coverage(ARRAY(SELECT m.npi::TEXT FROM roster_members m WHERE m.roster_id = p_roster_id));
$$ LANGUAGE sql STABLE;

-- 5a. One receipt as the API shows it. Values from a source not accepted for sale are withheld unless asked for.
CREATE OR REPLACE FUNCTION freshroot_receipt_json(r v_freshroot_receipts)
RETURNS JSONB AS $$
  SELECT jsonb_build_object(
    'receipt_id', r.id, 'npi', r.npi, 'claim_type', r.claim_type, 'jurisdiction', r.jurisdiction,
    'license_number', r.license_number, 'normalized_status', r.normalized_status, 'raw_status', r.raw_status,
    'claim', r.claim, 'source_name', r.source_name, 'source_published_at', r.source_published_at,
    'source_effective_at', r.source_effective_at, 'retrieved_at', r.retrieved_at,
    'next_check_due_at', r.next_check_due_at, 'origin', r.origin, 'stage', r.stage,
    'match_basis', r.match_basis, 'match_confidence', r.match_confidence, 'limitations', r.limitations,
    'supersedes_id', r.supersedes_id, 'artifact_sha256', r.artifact_sha256, 'created_at', r.created_at,
    'accepted_for_sale', r.accepted_for_sale, 'shippable', r.shippable, 'rights', r.rights);
$$ LANGUAGE sql STABLE;

-- 5b. A roster with one summary row per NPI: the roster state, that state's current license receipt
--     (status, match basis, retrieved_at) and the latest retrieved_at over all the NPI's current receipts.
CREATE OR REPLACE FUNCTION freshroot_roster(p_roster_id TEXT, p_include_unaccepted BOOLEAN DEFAULT FALSE)
RETURNS JSONB AS $$
  SELECT jsonb_build_object(
    'roster_id', ro.id, 'name', ro.name, 'created_at', ro.created_at,
    'count', (SELECT count(*) FROM roster_members m WHERE m.roster_id = ro.id),
    'include_unaccepted', p_include_unaccepted,
    'members', COALESCE((
      SELECT jsonb_agg(jsonb_build_object(
               'npi', m.npi, 'state', m.state,
               'license_status', lic.normalized_status, 'match_basis', lic.match_basis,
               'license_retrieved_at', lic.retrieved_at, 'last_retrieved_at', latest.retrieved_at,
               'accepted_for_sale', lic.accepted_for_sale, 'shippable', COALESCE(lic.shippable, FALSE),
               'rights', lic.rights) ORDER BY m.npi)
      FROM roster_members m
      LEFT JOIN LATERAL (
        SELECT f.* FROM v_current_receipts c JOIN v_freshroot_receipts f ON f.id = c.id
        WHERE c.npi = m.npi AND c.claim_type = 'state_license' AND c.jurisdiction = m.state
          AND (p_include_unaccepted OR f.accepted_for_sale)
        ORDER BY c.retrieved_at DESC, c.created_at DESC LIMIT 1
      ) lic ON TRUE
      LEFT JOIN LATERAL (
        SELECT max(c.retrieved_at) AS retrieved_at FROM v_current_receipts c JOIN data_sources s ON s.id = c.source_id
        WHERE c.npi = m.npi AND (p_include_unaccepted OR s.accepted_for_sale)
      ) latest ON TRUE
      WHERE m.roster_id = ro.id), '[]'::jsonb))
  FROM rosters ro WHERE ro.id = p_roster_id;
$$ LANGUAGE sql STABLE;

-- 5c. Current receipts for one NPI, each with its history: every other receipt for the same NPI, claim type and
--     jurisdiction retrieved at or before the current one, oldest first. "At or before" because v_current_receipts
--     orders by retrieved_at only: two receipts from one run tie, and the one it did not pick belongs here.
CREATE OR REPLACE FUNCTION freshroot_claims(p_npi TEXT, p_include_unaccepted BOOLEAN DEFAULT FALSE)
RETURNS JSONB AS $$
  SELECT jsonb_build_object(
    'npi', p_npi, 'include_unaccepted', p_include_unaccepted,
    'claims', COALESCE(jsonb_agg(
      freshroot_receipt_json(f) || jsonb_build_object('history', COALESCE((
        SELECT jsonb_agg(freshroot_receipt_json(h) ORDER BY h.retrieved_at, h.created_at, h.id)
        FROM v_freshroot_receipts h
        WHERE h.npi = f.npi AND h.claim_type = f.claim_type
          AND COALESCE(h.jurisdiction, '') = COALESCE(f.jurisdiction, '') AND h.id <> f.id
          AND h.retrieved_at <= f.retrieved_at
          AND (p_include_unaccepted OR h.accepted_for_sale)), '[]'::jsonb))
      ORDER BY f.claim_type, f.jurisdiction NULLS FIRST, f.license_number NULLS FIRST), '[]'::jsonb))
  FROM v_current_receipts c
  JOIN v_freshroot_receipts f ON f.id = c.id
  WHERE c.npi = p_npi AND (p_include_unaccepted OR f.accepted_for_sale);
$$ LANGUAGE sql STABLE;

-- 5d. Receipts for a roster's NPIs created after the cursor (created_at, id), oldest first. Returns up to
--     p_limit + 1 rows so the caller can tell whether there is more. change_kind compares with the row named by
--     supersedes_id: status_change if normalized_status differs, refresh if not, new if there is none.
CREATE OR REPLACE FUNCTION freshroot_deltas(p_roster_id TEXT, p_after_created_at TIMESTAMPTZ, p_after_id UUID,
                                            p_limit INTEGER, p_include_unaccepted BOOLEAN DEFAULT FALSE)
RETURNS JSONB AS $$
  SELECT COALESCE(jsonb_agg(d.row ORDER BY d.created_at, d.id), '[]'::jsonb)
  FROM (
    SELECT f.created_at, f.id,
           freshroot_receipt_json(f) || jsonb_build_object(
             'prior_normalized_status', p.normalized_status,
             'change_kind', CASE WHEN p.id IS NULL THEN 'new'
                                 WHEN p.normalized_status <> f.normalized_status THEN 'status_change'
                                 ELSE 'refresh' END) AS row
    FROM v_freshroot_receipts f
    LEFT JOIN credential_receipts p ON p.id = f.supersedes_id
    WHERE f.npi IN (SELECT m.npi FROM roster_members m WHERE m.roster_id = p_roster_id)
      AND (p_after_created_at IS NULL OR (f.created_at, f.id) > (p_after_created_at, p_after_id))
      AND (p_include_unaccepted OR f.accepted_for_sale)
    ORDER BY f.created_at, f.id
    LIMIT p_limit + 1
  ) d;
$$ LANGUAGE sql STABLE;

REVOKE ALL ON FUNCTION roster_coverage(TEXT[])                                          FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION freshroot_coverage(TEXT)                                        FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION freshroot_receipt_json(v_freshroot_receipts)                     FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION freshroot_roster(TEXT, BOOLEAN)                                  FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION freshroot_claims(TEXT, BOOLEAN)                                  FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION freshroot_deltas(TEXT, TIMESTAMPTZ, UUID, INTEGER, BOOLEAN)      FROM PUBLIC, anon, authenticated;
ALTER FUNCTION roster_coverage(TEXT[])                                     SET search_path = public;
ALTER FUNCTION freshroot_coverage(TEXT)                                   SET search_path = public;
ALTER FUNCTION freshroot_receipt_json(v_freshroot_receipts)               SET search_path = public;
ALTER FUNCTION freshroot_roster(TEXT, BOOLEAN)                            SET search_path = public;
ALTER FUNCTION freshroot_claims(TEXT, BOOLEAN)                            SET search_path = public;
ALTER FUNCTION freshroot_deltas(TEXT, TIMESTAMPTZ, UUID, INTEGER, BOOLEAN) SET search_path = public;
GRANT EXECUTE ON FUNCTION roster_coverage(TEXT[])                                       TO service_role;
GRANT EXECUTE ON FUNCTION freshroot_coverage(TEXT)                                     TO service_role;
GRANT EXECUTE ON FUNCTION freshroot_receipt_json(v_freshroot_receipts)                  TO service_role;
GRANT EXECUTE ON FUNCTION freshroot_roster(TEXT, BOOLEAN)                               TO service_role;
GRANT EXECUTE ON FUNCTION freshroot_claims(TEXT, BOOLEAN)                               TO service_role;
GRANT EXECUTE ON FUNCTION freshroot_deltas(TEXT, TIMESTAMPTZ, UUID, INTEGER, BOOLEAN)   TO service_role;

COMMIT;

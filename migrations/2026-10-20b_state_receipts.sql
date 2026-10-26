-- 2026-10-20b · State license receipts
-- Idempotent. Adds, never drops. Runs after 2026-10-20_receipt_layer.sql.
--
-- What this adds:
--   1. state_license_lookups and provider_adverse_actions: run, artifact, match basis and status columns.
--      Board loaders (scripts/ingestion/boards/) write one snapshot of matched rows per run, so a receipt
--      reads exactly the rows of the run it cites. Rows of older runs are pruned by the loader.
--   2. v_state_licenses_current: the rows of the latest completed run per source.
--   3. state_license_name_candidates(state): NPIs eligible for a name_state_taxonomy match.
--   4. receipts_for_state_licenses(npis[], state): one receipt per NPI per state from the latest completed run.
--   5. download and detection URLs for the Texas and Florida sources.

BEGIN;

-- 1. Run-scoped rows with an honest match basis.
ALTER TABLE state_license_lookups
  ADD COLUMN IF NOT EXISTS source_id             UUID REFERENCES data_sources(id),
  ADD COLUMN IF NOT EXISTS run_id                UUID REFERENCES ingestion_runs(id),
  ADD COLUMN IF NOT EXISTS artifact_id           UUID REFERENCES source_artifacts(id),
  ADD COLUMN IF NOT EXISTS source_record_key     TEXT,          -- the board's identity for the row, e.g. license type + number
  ADD COLUMN IF NOT EXISTS raw_status            TEXT,          -- exactly what the board says
  ADD COLUMN IF NOT EXISTS normalized_status     VARCHAR(20) CHECK (normalized_status IN (
                                                   'active','inactive','expired','suspended','revoked','probation','unknown')),
  ADD COLUMN IF NOT EXISTS status_effective_date DATE,          -- the board's date for the status
  ADD COLUMN IF NOT EXISTS match_basis           VARCHAR(24) CHECK (match_basis IN (
                                                   'npi_exact','license_number_exact','name_state_taxonomy')),
  ADD COLUMN IF NOT EXISTS match_confidence      NUMERIC(3,2) CHECK (match_confidence BETWEEN 0 AND 1),
  ADD COLUMN IF NOT EXISTS stage                 VARCHAR(12) CHECK (stage IN ('candidate','verified'));

CREATE UNIQUE INDEX IF NOT EXISTS uq_sll_run_record ON state_license_lookups(run_id, source_record_key);
CREATE INDEX IF NOT EXISTS idx_sll_state_license    ON state_license_lookups(state_code, license_number);
CREATE INDEX IF NOT EXISTS idx_sll_source_run       ON state_license_lookups(source_id, run_id);

ALTER TABLE provider_adverse_actions
  ADD COLUMN IF NOT EXISTS source_id         UUID REFERENCES data_sources(id),
  ADD COLUMN IF NOT EXISTS run_id            UUID REFERENCES ingestion_runs(id),
  ADD COLUMN IF NOT EXISTS artifact_id       UUID REFERENCES source_artifacts(id),
  ADD COLUMN IF NOT EXISTS source_record_key TEXT,
  ADD COLUMN IF NOT EXISTS license_number    VARCHAR(255),
  ADD COLUMN IF NOT EXISTS raw_status        TEXT,
  ADD COLUMN IF NOT EXISTS match_basis       VARCHAR(24) CHECK (match_basis IN (
                                               'npi_exact','license_number_exact','name_state_taxonomy')),
  ADD COLUMN IF NOT EXISTS match_confidence  NUMERIC(3,2) CHECK (match_confidence BETWEEN 0 AND 1),
  ADD COLUMN IF NOT EXISTS stage             VARCHAR(12) CHECK (stage IN ('candidate','verified'));

CREATE UNIQUE INDEX IF NOT EXISTS uq_paa_run_record ON provider_adverse_actions(run_id, source_record_key);
CREATE INDEX IF NOT EXISTS idx_paa_source_run       ON provider_adverse_actions(source_id, run_id);

-- 2. Current rows: the snapshot of the latest completed run of each source.
CREATE OR REPLACE VIEW v_state_licenses_current AS
SELECT l.*
FROM state_license_lookups l
JOIN LATERAL (
  SELECT r.id FROM ingestion_runs r
  WHERE r.source_id = l.source_id AND r.status = 'completed'
  ORDER BY r.completed_at DESC LIMIT 1
) latest ON latest.id = l.run_id;

-- 3. Individuals with a physician taxonomy (207*/208*) and an NPPES practice address in the state.
--    The only population a name match may draw from; the loader still requires the name to be unique.
--    One jsonb array per call: paging a set-returning function re-ran the join per page and hit the
--    API statement timeout.
CREATE INDEX IF NOT EXISTS idx_provider_taxonomies_physician ON provider_taxonomies(provider_id)
  WHERE taxonomy_code LIKE '207%' OR taxonomy_code LIKE '208%';
CREATE INDEX IF NOT EXISTS idx_provider_addresses_state_type ON provider_addresses(state, address_type, provider_id);

DROP FUNCTION IF EXISTS state_license_name_candidates(VARCHAR);
CREATE FUNCTION state_license_name_candidates(p_state VARCHAR)
RETURNS jsonb
LANGUAGE sql STABLE AS $$
  SELECT COALESCE(jsonb_agg(jsonb_build_object('provider_id', c.id, 'npi', c.npi,
                                               'last_name', c.last_name, 'first_name', c.first_name)), '[]'::jsonb)
  FROM (
    SELECT DISTINCT p.id, p.npi, p.last_name, p.first_name
    FROM provider_addresses a
    JOIN provider_taxonomies t ON t.provider_id = a.provider_id
                              AND (t.taxonomy_code LIKE '207%' OR t.taxonomy_code LIKE '208%')
    JOIN providers p ON p.id = a.provider_id AND p.entity_type = 'individual'
    WHERE a.address_type = 'practice' AND a.state = upper(p_state)
  ) c
$$;

-- 4. License receipts for a roster. One receipt per NPI per state, from the latest completed run of that
--    state's licensing source. An NPI with several matched licenses gets the strongest match (then active,
--    then most recently issued); lineage lists every matched row. No matched license is 'not_found':
--    the board files carry no NPI, so absence is a matching result, never proof of no license.
CREATE OR REPLACE FUNCTION receipts_for_state_licenses(p_npis TEXT[], p_state VARCHAR, p_origin TEXT DEFAULT 'real')
RETURNS TABLE (npi VARCHAR, jurisdiction VARCHAR, license_number VARCHAR, normalized_status VARCHAR,
               match_basis VARCHAR, stage VARCHAR, receipt_id UUID) AS $$
#variable_conflict use_column
DECLARE
  v_state VARCHAR := upper(p_state);
  src     data_sources%ROWTYPE;
  run     ingestion_runs%ROWTYPE;
  n_src   INTEGER;
BEGIN
  SELECT count(*) INTO n_src FROM data_sources s
  WHERE s.jurisdiction = v_state AND s.category = 'licensing' AND 'state_license' = ANY(s.claim_types);
  IF n_src <> 1 THEN
    RAISE EXCEPTION 'Expected one licensing source for %, found %.', v_state, n_src;
  END IF;
  SELECT * INTO src FROM data_sources s
  WHERE s.jurisdiction = v_state AND s.category = 'licensing' AND 'state_license' = ANY(s.claim_types);

  SELECT * INTO run FROM ingestion_runs r
  WHERE r.source_id = src.id AND r.status = 'completed' ORDER BY r.completed_at DESC LIMIT 1;
  IF run.id IS NULL THEN
    RAISE EXCEPTION 'No completed run for % (%). Receipts are written by runs, never by hand.', src.name, v_state;
  END IF;

  RETURN QUERY
  WITH roster AS (
    SELECT p.id, p.npi FROM providers p WHERE p.npi = ANY(p_npis)
  ),
  lic AS (
    SELECT l.*,
           row_number() OVER w_rank AS rn,
           count(*)     OVER w_all  AS n_lic,
           jsonb_agg(jsonb_build_object('table','state_license_lookups','id',l.id)) OVER w_all AS all_rows
    FROM state_license_lookups l
    WHERE l.run_id = run.id AND l.provider_id IN (SELECT r.id FROM roster r)
    WINDOW w_all  AS (PARTITION BY l.provider_id),
           w_rank AS (PARTITION BY l.provider_id
                      ORDER BY l.match_confidence DESC, (l.normalized_status = 'active') DESC,
                               l.issue_date DESC NULLS LAST, l.id)
  )
  INSERT INTO credential_receipts
    (npi, provider_id, claim_type, jurisdiction, license_number, raw_status, normalized_status, claim,
     source_id, artifact_id, run_id, source_effective_at, source_published_at, retrieved_at, next_check_due_at,
     origin, stage, match_basis, match_confidence, lineage, parser_version, limitations)
  SELECT
    p.npi, p.id, 'state_license', v_state, l.license_number,
    COALESCE(l.raw_status, 'no license in this snapshot matched to this NPI'),
    COALESCE(l.normalized_status, 'not_found'),
    CASE WHEN l.id IS NULL THEN '{}'::jsonb
         ELSE jsonb_build_object('license_type', l.license_type, 'issue_date', l.issue_date,
                                 'expiration_date', l.expiration_date, 'status_date', l.status_effective_date,
                                 'disciplinary_actions', l.disciplinary_actions, 'licenses_matched', l.n_lic) END,
    src.id, run.artifact_id, run.id,
    l.status_effective_date::timestamptz, run.source_published_at, run.completed_at,
    run.completed_at + make_interval(hours => COALESCE(src.cadence_hours, 24)),
    p_origin,
    COALESCE(l.stage, 'verified'),
    COALESCE(l.match_basis, 'none'),
    COALESCE(l.match_confidence, 0.00),
    COALESCE(l.all_rows, '[]'::jsonb),
    'receipts_for_state_licenses/1',
    CASE COALESCE(l.match_basis, 'none')
      WHEN 'npi_exact' THEN NULL
      WHEN 'license_number_exact' THEN
        'Board file carries no NPI; matched on a license number already recorded for this NPI (NPPES license field, provider_credentials, or a prior exact link).'
      WHEN 'name_state_taxonomy' THEN
        'Board file carries no NPI; matched on last name + first name + NPPES practice-address state + physician taxonomy. Candidate: requires human review.'
      ELSE
        'No license in this snapshot could be linked to this NPI. The board file carries no NPI, so absence is a matching result, not evidence that the provider is unlicensed.'
    END
  FROM roster p
  LEFT JOIN lic l ON l.provider_id = p.id AND l.rn = 1
  RETURNING credential_receipts.npi, credential_receipts.jurisdiction, credential_receipts.license_number,
            credential_receipts.normalized_status, credential_receipts.match_basis, credential_receipts.stage,
            credential_receipts.id;
END $$ LANGUAGE plpgsql;

-- Service role only; nothing public writes receipts or reads the candidate pool.
REVOKE ALL ON FUNCTION receipts_for_state_licenses(TEXT[], VARCHAR, TEXT) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION state_license_name_candidates(VARCHAR)             FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION state_license_name_candidates(VARCHAR) TO service_role;
REVOKE ALL ON v_state_licenses_current FROM anon, authenticated;

-- 5. Where each board file lives.
UPDATE data_sources SET
  download_url  = 'https://data.texas.gov/api/views/tm3v-pfq9/rows.csv?accessType=DOWNLOAD',
  api_url       = 'https://data.texas.gov/api/views/tm3v-pfq9.json',
  detection_url = 'https://data.texas.gov/api/views/tm3v-pfq9.json',
  notes         = 'Texas Open Data "DataSet-01-All Licenses" (tm3v-pfq9), published by TMB, updated daily. Carries status, disciplinary status and current board action, so ORSSP reports are not needed. No NPI. Commercial reuse terms to confirm.'
WHERE name = 'Texas Medical Board licensure file';

UPDATE data_sources SET
  detection_url = 'https://data-download.mqa.flhealthsource.gov/LicensureData',
  notes         = 'DOH MQA Data Download Portal (data-download.mqa.flhealthsource.gov). Licensure, practitioner profile and license status files, pipe-delimited, updated daily. Portal requires a signed-in account (Azure B2C), so files are fetched by a person and passed to the loader. Cadence and reuse to confirm.'
WHERE name = 'Florida MQA licensee data download';

COMMIT;

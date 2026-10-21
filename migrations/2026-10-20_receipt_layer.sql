-- 2026-10-20 · Receipt layer for the credential data product
-- Idempotent. Adds, never drops. Existing tables and the April portal keep working.
--
-- What this adds:
--   1. data_sources: rights fields (a source is not sellable until rights and acceptance are documented)
--   2. ingestion_runs: the two missing clocks (source_published_at, detected_at) and the artifact link
--   3. source_artifacts: one row per downloaded file, hashed
--   4. credential_receipts: append-only, one row per claim with three clocks, origin, stage, match basis
--   5. v_source_status: what the public status page reads
--   6. seed rows for the four pilot boards and the CMS sources (rights = unknown until confirmed)
--   7. receipts_for_exclusions(npis[]): turns OIG and SAM snapshots into receipts for a roster
--
-- Run in the Supabase SQL editor or via the Management API query endpoint. No data is deleted.

BEGIN;

-- 1. Rights on every source. Rights before rows.
ALTER TABLE data_sources
  ADD COLUMN IF NOT EXISTS redistribution_permission VARCHAR(20) NOT NULL DEFAULT 'unknown'
    CHECK (redistribution_permission IN ('unknown','permitted','restricted','prohibited')),
  ADD COLUMN IF NOT EXISTS terms_url TEXT,
  ADD COLUMN IF NOT EXISTS terms_version VARCHAR(100),
  ADD COLUMN IF NOT EXISTS terms_checked_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS accepted_for_sale BOOLEAN NOT NULL DEFAULT FALSE,
  ADD COLUMN IF NOT EXISTS cadence_hours INTEGER,            -- how often the publisher releases; drives next_due
  ADD COLUMN IF NOT EXISTS detection_url TEXT,               -- where the poller looks for a new release
  ADD COLUMN IF NOT EXISTS jurisdiction VARCHAR(2),          -- state code for boards; NULL for federal
  ADD COLUMN IF NOT EXISTS claim_types TEXT[];               -- which claim_type values this source can support

COMMENT ON COLUMN data_sources.accepted_for_sale IS
  'TRUE only after redistribution_permission = permitted and the acceptance test passed. Receipts from a source that is not accepted never ship.';

-- 2. Clocks on every run. Fetching an old file today does not make it current.
ALTER TABLE ingestion_runs
  ADD COLUMN IF NOT EXISTS source_published_at TIMESTAMPTZ,  -- the date the publisher stamps on the file
  ADD COLUMN IF NOT EXISTS detected_at TIMESTAMPTZ,          -- when the poller noticed the release
  ADD COLUMN IF NOT EXISTS artifact_id UUID,
  ADD COLUMN IF NOT EXISTS run_notes TEXT;

-- 3. One row per downloaded file. The hash proves byte consistency, not truth.
CREATE TABLE IF NOT EXISTS source_artifacts (
  id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  source_id           UUID NOT NULL REFERENCES data_sources(id),
  file_name           TEXT NOT NULL,
  download_url        TEXT,
  storage_path        TEXT,                                  -- private bucket path; never a public URL
  sha256              CHAR(64) NOT NULL,
  byte_size           BIGINT,
  row_count           INTEGER,
  source_published_at TIMESTAMPTZ,
  retrieved_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  notes               TEXT,
  created_at          TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE (source_id, sha256)                                 -- re-downloading the same bytes is a no-op
);
CREATE INDEX IF NOT EXISTS idx_source_artifacts_source ON source_artifacts(source_id, retrieved_at DESC);

ALTER TABLE ingestion_runs
  DROP CONSTRAINT IF EXISTS ingestion_runs_artifact_fk,
  ADD CONSTRAINT ingestion_runs_artifact_fk FOREIGN KEY (artifact_id) REFERENCES source_artifacts(id);

-- 4. The receipt. Append-only. Corrections supersede; nothing is edited in place.
CREATE TABLE IF NOT EXISTS credential_receipts (
  id                   UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  npi                  VARCHAR(10) NOT NULL,
  provider_id          UUID REFERENCES providers(id),
  claim_type           VARCHAR(40) NOT NULL CHECK (claim_type IN (
                         'npi_status','oig_exclusion','sam_exclusion','state_license','state_board_action',
                         'medicare_optout','pecos_enrollment','dea_registration','board_certification',
                         'medicaid_exclusion','nurse_license')),
  jurisdiction         VARCHAR(2),                            -- state for licenses; NULL for federal
  license_number       VARCHAR(255),
  raw_status           TEXT,                                  -- exactly what the source says
  normalized_status    VARCHAR(20) NOT NULL CHECK (normalized_status IN (
                         'active','inactive','expired','suspended','revoked','probation',
                         'excluded','reinstated','not_found','unavailable','unknown')),
  claim                JSONB NOT NULL DEFAULT '{}'::jsonb,    -- the structured fields of the claim
  source_id            UUID NOT NULL REFERENCES data_sources(id),
  artifact_id          UUID REFERENCES source_artifacts(id),
  run_id               UUID REFERENCES ingestion_runs(id),
  -- three clocks plus the due date
  source_effective_at  TIMESTAMPTZ,                           -- when the fact took effect (expiration, exclusion date)
  source_published_at  TIMESTAMPTZ,                           -- the date on the publisher's file
  retrieved_at         TIMESTAMPTZ NOT NULL,                  -- when the garden read it; written by the run, never by hand
  next_check_due_at    TIMESTAMPTZ NOT NULL,
  -- the two canon labels
  origin               VARCHAR(10) NOT NULL DEFAULT 'real' CHECK (origin IN ('real','synthetic','unknown')),
  stage                VARCHAR(12) NOT NULL DEFAULT 'verified' CHECK (stage IN (
                         'seed','candidate','verified','stale','superseded','revoked','quarantined')),
  -- how the row was joined to the NPI; honest about fuzzy matches
  match_basis          VARCHAR(24) NOT NULL CHECK (match_basis IN (
                         'npi_exact','license_number_exact','name_dob_state','name_state_taxonomy','name_only','none')),
  match_confidence     NUMERIC(3,2) NOT NULL CHECK (match_confidence BETWEEN 0 AND 1),
  lineage              JSONB NOT NULL DEFAULT '[]'::jsonb,    -- ids of the source rows this receipt was built from
  supersedes_id        UUID REFERENCES credential_receipts(id),
  parser_version       VARCHAR(40),
  reviewer             VARCHAR(255),                          -- set only when a person resolved an ambiguity
  limitations          TEXT,                                  -- e.g. "source does not carry NPI; matched by name and license number"
  created_at           TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_receipts_npi        ON credential_receipts(npi, claim_type, retrieved_at DESC);
CREATE INDEX IF NOT EXISTS idx_receipts_due        ON credential_receipts(next_check_due_at) WHERE stage IN ('verified','candidate');
CREATE INDEX IF NOT EXISTS idx_receipts_source     ON credential_receipts(source_id, retrieved_at DESC);
CREATE INDEX IF NOT EXISTS idx_receipts_supersedes ON credential_receipts(supersedes_id);

COMMENT ON TABLE credential_receipts IS
  'One row per credential claim with a receipt. Append-only: a correction is a new row whose supersedes_id points at the old one. Absence from a snapshot is normalized_status = not_found, never clear.';

-- Append-only guard: the only in-place change allowed is a stage transition to stale, superseded, revoked or quarantined.
CREATE OR REPLACE FUNCTION credential_receipts_guard() RETURNS TRIGGER AS $$
BEGIN
  IF TG_OP = 'DELETE' THEN
    RAISE EXCEPTION 'credential_receipts is append-only; supersede instead of deleting';
  END IF;
  IF NEW.stage NOT IN ('stale','superseded','revoked','quarantined') THEN
    RAISE EXCEPTION 'credential_receipts is append-only; only stage transitions to stale/superseded/revoked/quarantined are allowed';
  END IF;
  IF row_to_json(NEW)::jsonb - 'stage' <> row_to_json(OLD)::jsonb - 'stage' THEN
    RAISE EXCEPTION 'credential_receipts is append-only; only the stage column may change';
  END IF;
  RETURN NEW;
END $$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_credential_receipts_guard ON credential_receipts;
CREATE TRIGGER trg_credential_receipts_guard
  BEFORE UPDATE OR DELETE ON credential_receipts
  FOR EACH ROW EXECUTE FUNCTION credential_receipts_guard();

-- Current view: the latest non-superseded receipt per NPI, claim type and jurisdiction.
CREATE OR REPLACE VIEW v_current_receipts AS
SELECT DISTINCT ON (npi, claim_type, COALESCE(jurisdiction,''), COALESCE(license_number,''))
       r.*,
       (r.next_check_due_at < NOW()) AS is_past_due
FROM credential_receipts r
WHERE r.stage NOT IN ('superseded','revoked','quarantined')
ORDER BY npi, claim_type, COALESCE(jurisdiction,''), COALESCE(license_number,''), retrieved_at DESC;

-- 5. What the public status page reads. Per source: file date, last run, next due, age, state.
CREATE OR REPLACE VIEW v_source_status AS
WITH last_run AS (
  SELECT DISTINCT ON (source_id)
         source_id, completed_at, started_at, status, records_processed, source_published_at, detected_at
  FROM ingestion_runs
  WHERE status = 'completed'
  ORDER BY source_id, completed_at DESC NULLS LAST
)
SELECT
  s.name,
  s.category,
  s.jurisdiction,
  s.claim_types,
  s.cadence_hours,
  s.redistribution_permission,
  s.accepted_for_sale,
  lr.source_published_at                                    AS file_date,
  lr.detected_at,
  lr.completed_at                                           AS last_run_at,
  lr.records_processed,
  CASE WHEN lr.completed_at IS NULL OR s.cadence_hours IS NULL THEN NULL
       ELSE lr.completed_at + make_interval(hours => s.cadence_hours) END AS next_due_at,
  CASE WHEN lr.completed_at IS NULL THEN NULL
       ELSE EXTRACT(EPOCH FROM (NOW() - lr.completed_at)) / 3600.0 END    AS age_hours,
  CASE
    WHEN lr.completed_at IS NULL THEN 'never'
    WHEN s.cadence_hours IS NULL THEN 'unscheduled'
    WHEN NOW() <= lr.completed_at + make_interval(hours => s.cadence_hours) THEN 'fresh'
    WHEN NOW() <= lr.completed_at + make_interval(hours => s.cadence_hours * 2) THEN 'due'
    ELSE 'stale'
  END AS freshness
FROM data_sources s
LEFT JOIN last_run lr ON lr.source_id = s.id
WHERE s.category IN ('provider_data','compliance','licensing')
ORDER BY s.category, s.name;

-- Public read on the status view only. The anon key must never read base tables.
GRANT SELECT ON v_source_status TO anon;
GRANT SELECT ON v_source_status TO authenticated;

-- 6. Seed the pilot sources. Rights stay 'unknown' until a person reads the terms and sets them.
INSERT INTO data_sources (name, category, format, update_frequency, cost, license_type, jurisdiction, cadence_hours, claim_types, notes)
VALUES
  ('Texas Medical Board licensure file',  'licensing', 'csv', 'daily',   'free', 'open_data',       'TX', 24,  ARRAY['state_license','state_board_action'], 'Texas Open Data; ORSSP monthly reports. Commercial reuse terms to confirm.'),
  ('Florida MQA licensee data download',  'licensing', 'txt', 'monthly', 'free', 'public_record',   'FL', 720, ARRAY['state_license','state_board_action'], 'DOH MQA Data Download: licensee, profile, enforcement files, pipe-delimited. Cadence and reuse to confirm.'),
  ('California DCA public information file','licensing','txt','monthly', 'free', 'public_record',   'CA', 720, ARRAY['state_license','state_board_action'], 'DCA Box drop, one file per board, refreshed at the start of each month. No NPI in file; match by name + license number. Reuse to confirm.'),
  ('Utah DOPL licensee list',             'licensing', 'csv', 'on_demand','mixed','public_record',  'UT', 720, ARRAY['state_license','state_board_action'], 'DOPL data request list: status, dates, disciplinary action, docket numbers. Fee, cadence and reuse to confirm.'),
  ('CMS Medicare opt-out affidavits',     'compliance','csv', 'monthly', 'free', 'public_domain',   NULL, 720, ARRAY['medicare_optout'], 'CMS public file. Cadence to confirm.'),
  ('CMS PECOS enrollment',                'compliance','csv', 'monthly', 'free', 'public_domain',   NULL, 720, ARRAY['pecos_enrollment'], 'CMS public enrollment files. Cadence to confirm.')
ON CONFLICT (name) DO NOTHING;

-- Bring the three seeded federal sources into the status view's expectations.
UPDATE data_sources SET cadence_hours = COALESCE(cadence_hours, 168), claim_types = COALESCE(claim_types, ARRAY['npi_status']),      detection_url = COALESCE(detection_url, 'https://download.cms.gov/nppes/NPI_Files.html') WHERE name = 'NPI Registry';
UPDATE data_sources SET cadence_hours = COALESCE(cadence_hours, 720), claim_types = COALESCE(claim_types, ARRAY['oig_exclusion']),   detection_url = COALESCE(detection_url, 'https://oig.hhs.gov/exclusions/exclusions_list.asp') WHERE name = 'OIG LEIE';
UPDATE data_sources SET cadence_hours = COALESCE(cadence_hours, 24),  claim_types = COALESCE(claim_types, ARRAY['sam_exclusion']),   detection_url = COALESCE(detection_url, 'https://sam.gov/data-services/Exclusions') WHERE name = 'SAM.gov';

-- 7. Exclusion receipts for a roster. Reads the latest completed OIG and SAM runs and writes one receipt per NPI per source.
--    OIG rows carry NPI (npi_exact, 1.00). SAM rows do not: a hit is name_only (0.40) and goes in as 'candidate' for review;
--    absence is 'not_found' in this snapshot, never 'clear'.
CREATE OR REPLACE FUNCTION receipts_for_exclusions(p_npis TEXT[], p_origin TEXT DEFAULT 'real')
RETURNS TABLE (npi VARCHAR, claim_type VARCHAR, normalized_status VARCHAR, receipt_id UUID) AS $$
#variable_conflict use_column
DECLARE
  oig_src   data_sources%ROWTYPE;
  sam_src   data_sources%ROWTYPE;
  oig_run   ingestion_runs%ROWTYPE;
  sam_run   ingestion_runs%ROWTYPE;
BEGIN
  SELECT * INTO oig_src FROM data_sources WHERE name = 'OIG LEIE';
  SELECT * INTO sam_src FROM data_sources WHERE name = 'SAM.gov';
  SELECT * INTO oig_run FROM ingestion_runs WHERE source_id = oig_src.id AND status = 'completed' ORDER BY completed_at DESC LIMIT 1;
  SELECT * INTO sam_run FROM ingestion_runs WHERE source_id = sam_src.id AND status = 'completed' ORDER BY completed_at DESC LIMIT 1;

  IF oig_run.id IS NULL THEN
    RAISE EXCEPTION 'No completed OIG LEIE run. Receipts are written by runs, never by hand.';
  END IF;

  -- OIG: exact NPI join.
  RETURN QUERY
  INSERT INTO credential_receipts
    (npi, provider_id, claim_type, raw_status, normalized_status, claim, source_id, artifact_id, run_id,
     source_effective_at, source_published_at, retrieved_at, next_check_due_at, origin, stage, match_basis, match_confidence, lineage, parser_version, limitations)
  SELECT
    p.npi, p.id, 'oig_exclusion',
    CASE WHEN e.id IS NULL THEN 'not in LEIE snapshot'
         WHEN e.reinstatement_date IS NOT NULL AND e.reinstatement_date <= CURRENT_DATE THEN 'reinstated ' || e.reinstatement_date
         ELSE 'excluded ' || COALESCE(e.exclusion_type,'') || ' ' || e.exclusion_date END,
    CASE WHEN e.id IS NULL THEN 'not_found'
         WHEN e.reinstatement_date IS NOT NULL AND e.reinstatement_date <= CURRENT_DATE THEN 'reinstated'
         ELSE 'excluded' END,
    CASE WHEN e.id IS NULL THEN '{}'::jsonb
         ELSE jsonb_build_object('exclusion_type', e.exclusion_type, 'exclusion_date', e.exclusion_date,
                                 'reinstatement_date', e.reinstatement_date, 'state', e.state, 'specialty', e.specialty) END,
    oig_src.id, oig_run.artifact_id, oig_run.id,
    e.exclusion_date::timestamptz, oig_run.source_published_at, oig_run.completed_at,
    oig_run.completed_at + make_interval(hours => COALESCE(oig_src.cadence_hours, 720)),
    p_origin, 'verified', 'npi_exact', 1.00,
    CASE WHEN e.id IS NULL THEN '[]'::jsonb ELSE jsonb_build_array(jsonb_build_object('table','oig_exclusions','id',e.id)) END,
    'receipts_for_exclusions/1', NULL
  FROM providers p
  LEFT JOIN oig_exclusions e ON e.npi = p.npi
  WHERE p.npi = ANY(p_npis)
  RETURNING credential_receipts.npi, credential_receipts.claim_type, credential_receipts.normalized_status, credential_receipts.id;

  -- SAM: no NPI in the file. Name-only candidates for review; absence recorded as not_found.
  IF sam_run.id IS NOT NULL THEN
    RETURN QUERY
    INSERT INTO credential_receipts
      (npi, provider_id, claim_type, raw_status, normalized_status, claim, source_id, artifact_id, run_id,
       source_effective_at, source_published_at, retrieved_at, next_check_due_at, origin, stage, match_basis, match_confidence, lineage, parser_version, limitations)
    SELECT
      p.npi, p.id, 'sam_exclusion',
      CASE WHEN s.id IS NULL THEN 'no name match in SAM snapshot' ELSE 'name match: ' || s.entity_name || ' ' || COALESCE(s.exclusion_program,'') END,
      CASE WHEN s.id IS NULL THEN 'not_found' ELSE 'unknown' END,          -- a name match is a review event, not a conclusion
      CASE WHEN s.id IS NULL THEN '{}'::jsonb
           ELSE jsonb_build_object('entity_name', s.entity_name, 'exclusion_type', s.exclusion_type, 'exclusion_program', s.exclusion_program,
                                   'active_date', s.active_date, 'termination_date', s.termination_date, 'sam_number', s.sam_number) END,
      sam_src.id, sam_run.artifact_id, sam_run.id,
      s.active_date::timestamptz, sam_run.source_published_at, sam_run.completed_at,
      sam_run.completed_at + make_interval(hours => COALESCE(sam_src.cadence_hours, 24)),
      p_origin,
      CASE WHEN s.id IS NULL THEN 'verified' ELSE 'candidate' END,
      CASE WHEN s.id IS NULL THEN 'npi_exact' ELSE 'name_only' END,
      CASE WHEN s.id IS NULL THEN 1.00 ELSE 0.40 END,
      CASE WHEN s.id IS NULL THEN '[]'::jsonb ELSE jsonb_build_array(jsonb_build_object('table','sam_exclusions','id',s.id)) END,
      'receipts_for_exclusions/1',
      'SAM.gov exclusion file carries no NPI; matched on last name + first name only. A match requires human review.'
    FROM providers p
    LEFT JOIN LATERAL (
      SELECT * FROM sam_exclusions x
      WHERE p.entity_type = 'individual'
        AND x.termination_date IS NULL
        AND upper(x.entity_name) LIKE upper(p.last_name) || ',%' || upper(p.first_name) || '%'
      LIMIT 1
    ) s ON TRUE
    WHERE p.npi = ANY(p_npis)
    RETURNING credential_receipts.npi, credential_receipts.claim_type, credential_receipts.normalized_status, credential_receipts.id;
  END IF;
END $$ LANGUAGE plpgsql;

-- NPI status receipts for a roster, from the latest NPPES run.
CREATE OR REPLACE FUNCTION receipts_for_npi_status(p_npis TEXT[], p_origin TEXT DEFAULT 'real')
RETURNS TABLE (npi VARCHAR, normalized_status VARCHAR, receipt_id UUID) AS $$
#variable_conflict use_column
DECLARE
  src data_sources%ROWTYPE;
  run ingestion_runs%ROWTYPE;
BEGIN
  SELECT * INTO src FROM data_sources WHERE name = 'NPI Registry';
  SELECT * INTO run FROM ingestion_runs WHERE source_id = src.id AND status = 'completed' ORDER BY completed_at DESC LIMIT 1;
  IF run.id IS NULL THEN RAISE EXCEPTION 'No completed NPI Registry run.'; END IF;

  RETURN QUERY
  INSERT INTO credential_receipts
    (npi, provider_id, claim_type, raw_status, normalized_status, claim, source_id, artifact_id, run_id,
     source_effective_at, source_published_at, retrieved_at, next_check_due_at, origin, stage, match_basis, match_confidence, lineage, parser_version)
  SELECT
    p.npi, p.id, 'npi_status', p.status,
    CASE p.status WHEN 'active' THEN 'active' ELSE 'inactive' END,
    jsonb_build_object('entity_type', p.entity_type, 'last_name', p.last_name, 'first_name', p.first_name, 'credential', p.credential,
                       'enumeration_date', p.enumeration_date, 'last_update_date', p.last_update_date, 'deactivation_date', p.deactivation_date),
    src.id, run.artifact_id, run.id,
    p.last_update_date::timestamptz, run.source_published_at, run.completed_at,
    run.completed_at + make_interval(hours => COALESCE(src.cadence_hours, 168)),
    p_origin, 'verified', 'npi_exact', 1.00,
    jsonb_build_array(jsonb_build_object('table','providers','id',p.id)), 'receipts_for_npi_status/1'
  FROM providers p
  WHERE p.npi = ANY(p_npis)
  RETURNING credential_receipts.npi, credential_receipts.normalized_status, credential_receipts.id;
END $$ LANGUAGE plpgsql;

-- Service role only on the functions; nothing public writes receipts.
REVOKE ALL ON FUNCTION receipts_for_exclusions(TEXT[], TEXT) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION receipts_for_npi_status(TEXT[], TEXT) FROM PUBLIC, anon, authenticated;

COMMIT;

-- After running:
--   SELECT * FROM v_source_status;                        -- every pilot source shows 'never' until a run completes
--   SELECT * FROM receipts_for_exclusions(ARRAY['1234567893']);   -- fails on purpose until an OIG run row exists

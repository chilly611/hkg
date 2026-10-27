-- 2026-10-26 · California and Utah licensing sources
-- Idempotent. Adds, never drops. Runs after 2026-10-20b_state_receipts.sql.
--
-- What this adds:
--   1. The California DCA public information file row: where the files live and what they carry.
--   2. 'California DCA Search API': a per-license source for re-verification (format 'api').
--   3. receipts_for_state_licenses reads bulk sources only, so a state may also have an api source.
--   4. receipts_for_license_reverify(run_id): the receipt for one re-verified license, from a completed api run.
--   5. The Utah DOPL licensee list row: what the list costs and how it is ordered.
-- Rights (redistribution_permission, accepted_for_sale) are not touched; a person sets those.

BEGIN;

-- 1. California bulk file. Facts from https://www.dca.ca.gov/consumers/public_info/ and the files themselves
--    (2026-10-01 release). The file carries license status only, so it cannot support state_board_action.
UPDATE data_sources SET
  download_url  = 'https://dca.box.com/s/oss6hf8jys2bmgxqd2gdz7w4oepm2il9',
  detection_url = 'https://www.dca.ca.gov/consumers/public_info/index.shtml',
  claim_types   = ARRAY['state_license'],
  notes         = 'DCA public information files, one Box folder per board, refreshed at the beginning of each month. Loader reads MedicalBoard_0800 and Osteopathic_0900 through the read-only token the DCA page itself uses. Files are named .xls but are tab-delimited text. Fields: license type, number (digits; the A/C/G/20A series is in the type name), name, public address of record, issue and expiration dates, status (Current, Delinquent, CurrentInactive). No NPI, no birth year, no board actions. Reuse terms to confirm.'
WHERE name = 'California DCA public information file';

UPDATE state_medical_boards SET
  has_api = TRUE,
  api_url = 'https://iservices.dca.ca.gov/api/search/v1',
  notes   = 'Bulk: DCA public information files (Medical Board and Osteopathic Medical Board folders). Per license: DCA Search API, APP_ID/APP_KEY from an approved iServices application.'
WHERE state_code = 'CA';

-- 2. The DCA Search API as its own source. Live registry reads, so no cadence and no file date.
INSERT INTO data_sources (name, category, format, update_frequency, api_url, jurisdiction, claim_types, notes)
VALUES ('California DCA Search API', 'licensing', 'api', 'on_demand', 'https://iservices.dca.ca.gov/api/search/v1', 'CA',
        ARRAY['state_license'],
        'DCA iServices Search API, getLicenseNumberSearch. Requires an iServices account, a DCA Search API subscription and an application approved by DCA (APP_ID, APP_KEY). Used to re-verify one license already linked to an NPI by an exact basis. Cost and reuse terms to confirm.')
ON CONFLICT (name) DO NOTHING;

-- 3. One bulk licensing source per state feeds the roster receipts; api sources are re-verification only.
--    Same function as 2026-10-20b except the two source lookups add format <> 'api'.
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
  WHERE s.jurisdiction = v_state AND s.category = 'licensing' AND 'state_license' = ANY(s.claim_types)
    AND COALESCE(s.format, '') <> 'api';
  IF n_src <> 1 THEN
    RAISE EXCEPTION 'Expected one bulk licensing source for %, found %.', v_state, n_src;
  END IF;
  SELECT * INTO src FROM data_sources s
  WHERE s.jurisdiction = v_state AND s.category = 'licensing' AND 'state_license' = ANY(s.claim_types)
    AND COALESCE(s.format, '') <> 'api';

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

-- 4. Re-verification receipt. Reads the state_license_lookups rows a completed api run wrote (one per license
--    re-verified); the loader writes those rows only for an NPI the current bulk snapshot links exactly.
--    The new receipt points at the receipt it replaces (supersedes_id); the old row is not edited.
--    next_check_due_at follows the state's bulk file cadence: the next monthly file is the next scheduled check.
CREATE OR REPLACE FUNCTION receipts_for_license_reverify(p_run_id UUID, p_origin TEXT DEFAULT 'real')
RETURNS TABLE (npi VARCHAR, jurisdiction VARCHAR, license_number VARCHAR, normalized_status VARCHAR,
               match_basis VARCHAR, stage VARCHAR, supersedes_id UUID, receipt_id UUID) AS $$
#variable_conflict use_column
DECLARE
  run  ingestion_runs%ROWTYPE;
  src  data_sources%ROWTYPE;
  bulk data_sources%ROWTYPE;
BEGIN
  SELECT * INTO run FROM ingestion_runs r WHERE r.id = p_run_id;
  IF run.id IS NULL OR run.status <> 'completed' THEN
    RAISE EXCEPTION 'Run % is not a completed run. Receipts are written by runs, never by hand.', p_run_id;
  END IF;
  SELECT * INTO src FROM data_sources s WHERE s.id = run.source_id;
  IF COALESCE(src.format, '') <> 'api' THEN
    RAISE EXCEPTION 'Run % belongs to %, not an api source; use receipts_for_state_licenses.', p_run_id, src.name;
  END IF;
  SELECT * INTO bulk FROM data_sources s
  WHERE s.jurisdiction = src.jurisdiction AND s.category = 'licensing' AND 'state_license' = ANY(s.claim_types)
    AND COALESCE(s.format, '') <> 'api';
  IF bulk.cadence_hours IS NULL THEN
    RAISE EXCEPTION 'No bulk licensing cadence for %; cannot set next_check_due_at.', src.jurisdiction;
  END IF;

  RETURN QUERY
  INSERT INTO credential_receipts
    (npi, provider_id, claim_type, jurisdiction, license_number, raw_status, normalized_status, claim,
     source_id, artifact_id, run_id, source_effective_at, source_published_at, retrieved_at, next_check_due_at,
     origin, stage, match_basis, match_confidence, lineage, supersedes_id, parser_version, limitations)
  SELECT
    p.npi, p.id, 'state_license', l.state_code, l.license_number, l.raw_status, l.normalized_status,
    jsonb_build_object('license_type', l.license_type, 'issue_date', l.issue_date,
                       'expiration_date', l.expiration_date, 'status_date', l.status_effective_date,
                       'disciplinary_actions', l.disciplinary_actions, 'via', src.name),
    src.id, run.artifact_id, run.id,
    l.status_effective_date::timestamptz, run.source_published_at, run.completed_at,
    run.completed_at + make_interval(hours => bulk.cadence_hours),
    p_origin, l.stage, l.match_basis, l.match_confidence,
    jsonb_build_array(jsonb_build_object('table','state_license_lookups','id',l.id)),
    prior.id,
    'receipts_for_license_reverify/1',
    'Re-verified live through ' || src.name || ' by license number. The NPI link is the exact link in the current bulk snapshot (license number recorded for this NPI); the registry itself carries no NPI.'
  FROM state_license_lookups l
  JOIN providers p ON p.id = l.provider_id
  LEFT JOIN LATERAL (
    SELECT c.id FROM v_current_receipts c
    WHERE c.npi = p.npi AND c.claim_type = 'state_license' AND c.jurisdiction = l.state_code
      AND (c.license_number = l.license_number OR c.license_number IS NULL)
    ORDER BY (c.license_number = l.license_number) DESC NULLS LAST, c.retrieved_at DESC
    LIMIT 1
  ) prior ON TRUE
  WHERE l.run_id = run.id
  RETURNING credential_receipts.npi, credential_receipts.jurisdiction, credential_receipts.license_number,
            credential_receipts.normalized_status, credential_receipts.match_basis, credential_receipts.stage,
            credential_receipts.supersedes_id, credential_receipts.id;
END $$ LANGUAGE plpgsql;

-- 5. Utah. https://secure.utah.gov/datarequest/professionals/index.html, read 2026-10-26: "Professions Licensed in
--    Utah": name, license type, license status; address, phone and email only with DOPL approval. $5.00 minimum
--    search fee covers the first 200 records, $0.03 per additional record; full list $0.01 per record, subscribers only.
UPDATE data_sources SET
  cost          = 'paid',
  detection_url = 'https://secure.utah.gov/datarequest/professionals/index.html',
  notes         = 'Utah.gov Data Request "Professions Licensed in Utah". Fields per the example list: profession, license type, license number, status, name, issue and expiration dates, disciplinary action, docket numbers. Address, phone and email require DOPL approval (dopllist@utah.gov). Price on the order page 2026-10-26: $5.00 minimum for the first 200 records, $0.03 per additional record; full list $0.01 per record for Utah.gov subscribers. Not loaded until a person orders the list. Cadence and reuse to confirm.'
WHERE name = 'Utah DOPL licensee list';

REVOKE ALL ON FUNCTION receipts_for_state_licenses(TEXT[], VARCHAR, TEXT) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION receipts_for_license_reverify(UUID, TEXT)         FROM PUBLIC, anon, authenticated;

COMMIT;

-- 2026-10-21 · SAM receipts fix
-- (a) receipts_for_exclusions treated any SAM row with a termination_date as inactive. 9,353 SAM exclusions
--     have a FUTURE end date and are active today. Fix: active means termination_date IS NULL OR > CURRENT_DATE.
-- (b) The SAM extract carries an NPI on 19,996 rows; the table had no column for it and the function matched
--     by name only. Fix: add sam_exclusions.npi, have ingest_sam.py fill it, and match npi_exact (1.00, verified)
--     when present, name_only (0.40, candidate) otherwise.
-- Also corrects the two update_frequency strings that disagreed with the cadences.
-- Idempotent. Adds, never drops. Re-running the function does not edit old receipts; it writes new ones.

BEGIN;

ALTER TABLE sam_exclusions ADD COLUMN IF NOT EXISTS npi VARCHAR(10);
CREATE INDEX IF NOT EXISTS idx_sam_exclusions_npi ON sam_exclusions(npi) WHERE npi IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_sam_exclusions_name ON sam_exclusions(upper(entity_name));

UPDATE data_sources SET update_frequency = 'weekly' WHERE name = 'NPI Registry' AND update_frequency <> 'weekly';
UPDATE data_sources SET update_frequency = 'daily'  WHERE name = 'SAM.gov'      AND update_frequency <> 'daily';

CREATE OR REPLACE FUNCTION receipts_for_exclusions(p_npis TEXT[], p_origin TEXT DEFAULT 'real')
RETURNS TABLE (npi VARCHAR, claim_type VARCHAR, normalized_status VARCHAR, receipt_id UUID) AS $$
#variable_conflict use_column
DECLARE
  oig_src data_sources%ROWTYPE;
  sam_src data_sources%ROWTYPE;
  oig_run ingestion_runs%ROWTYPE;
  sam_run ingestion_runs%ROWTYPE;
BEGIN
  SELECT * INTO oig_src FROM data_sources WHERE name = 'OIG LEIE';
  SELECT * INTO sam_src FROM data_sources WHERE name = 'SAM.gov';
  SELECT * INTO oig_run FROM ingestion_runs WHERE source_id = oig_src.id AND status = 'completed' ORDER BY completed_at DESC LIMIT 1;
  SELECT * INTO sam_run FROM ingestion_runs WHERE source_id = sam_src.id AND status = 'completed' ORDER BY completed_at DESC LIMIT 1;

  IF oig_run.id IS NULL THEN
    RAISE EXCEPTION 'No completed OIG LEIE run. Receipts are written by runs, never by hand.';
  END IF;

  -- OIG: exact NPI join. Unchanged from 2026-10-20.
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
    'receipts_for_exclusions/2', NULL
  FROM providers p
  LEFT JOIN oig_exclusions e ON e.npi = p.npi
  WHERE p.npi = ANY(p_npis)
  RETURNING credential_receipts.npi, credential_receipts.claim_type, credential_receipts.normalized_status, credential_receipts.id;

  -- SAM: NPI when the extract carries it; name-only candidate otherwise. Active = no end date or an end date in the future.
  IF sam_run.id IS NOT NULL THEN
    RETURN QUERY
    INSERT INTO credential_receipts
      (npi, provider_id, claim_type, raw_status, normalized_status, claim, source_id, artifact_id, run_id,
       source_effective_at, source_published_at, retrieved_at, next_check_due_at, origin, stage, match_basis, match_confidence, lineage, parser_version, limitations)
    SELECT
      p.npi, p.id, 'sam_exclusion',
      CASE WHEN s.id IS NULL THEN 'not in SAM snapshot'
           WHEN s.npi IS NOT NULL THEN 'excluded ' || COALESCE(s.exclusion_program,'') || ' ' || COALESCE(s.exclusion_type,'') || ' active ' || s.active_date
                                      || CASE WHEN s.termination_date IS NULL THEN ', indefinite' ELSE ', until ' || s.termination_date END
           ELSE 'name match: ' || s.entity_name || ' ' || COALESCE(s.exclusion_program,'') END,
      CASE WHEN s.id IS NULL THEN 'not_found'
           WHEN s.npi IS NOT NULL THEN 'excluded'
           ELSE 'unknown' END,
      CASE WHEN s.id IS NULL THEN '{}'::jsonb
           ELSE jsonb_build_object('entity_name', s.entity_name, 'exclusion_type', s.exclusion_type, 'exclusion_program', s.exclusion_program,
                                   'active_date', s.active_date, 'termination_date', s.termination_date, 'sam_number', s.sam_number,
                                   'sam_npi', s.npi) END,
      sam_src.id, sam_run.artifact_id, sam_run.id,
      s.active_date::timestamptz, sam_run.source_published_at, sam_run.completed_at,
      sam_run.completed_at + make_interval(hours => COALESCE(sam_src.cadence_hours, 24)),
      p_origin,
      CASE WHEN s.id IS NULL OR s.npi IS NOT NULL THEN 'verified' ELSE 'candidate' END,
      CASE WHEN s.id IS NULL OR s.npi IS NOT NULL THEN 'npi_exact' ELSE 'name_only' END,
      CASE WHEN s.id IS NULL OR s.npi IS NOT NULL THEN 1.00 ELSE 0.40 END,
      CASE WHEN s.id IS NULL THEN '[]'::jsonb ELSE jsonb_build_array(jsonb_build_object('table','sam_exclusions','id',s.id)) END,
      'receipts_for_exclusions/2',
      CASE WHEN s.id IS NOT NULL AND s.npi IS NULL
           THEN 'SAM row carries no NPI; matched on last name + first name only. A match requires human review.'
           ELSE NULL END
    FROM providers p
    LEFT JOIN LATERAL (
      SELECT * FROM sam_exclusions x
      WHERE (x.termination_date IS NULL OR x.termination_date > CURRENT_DATE)
        AND (
          x.npi = p.npi
          OR (x.npi IS NULL AND p.entity_type = 'individual'
              AND upper(x.entity_name) LIKE upper(p.last_name) || ',%' || upper(p.first_name) || '%')
        )
      ORDER BY (x.npi = p.npi) DESC NULLS LAST, x.active_date DESC
      LIMIT 1
    ) s ON TRUE
    WHERE p.npi = ANY(p_npis)
    RETURNING credential_receipts.npi, credential_receipts.claim_type, credential_receipts.normalized_status, credential_receipts.id;
  END IF;
END $$ LANGUAGE plpgsql;

REVOKE ALL ON FUNCTION receipts_for_exclusions(TEXT[], TEXT) FROM PUBLIC, anon, authenticated;

COMMIT;

-- After running: re-run ingest_sam.py so the npi column is filled (it must map the extract's NPI field),
-- then: SELECT count(*) FROM sam_exclusions WHERE npi IS NOT NULL;  -- expect about 19,996

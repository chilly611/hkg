-- 2026-11-05 · Board actions as receipts: claim_type state_board_action for the bulk board files (TX, FL, CA)
-- Widens a CHECK list, never narrows it, and adds one writer. No receipt is deleted or edited; no source or rights
-- column is touched. Runs after 2026-10-28_cms_statuses.sql.
--
-- What this adds:
--   1. normalized_status accepts action_on_record and none_in_file (claim_type state_board_action, reserved in the
--      claim_type CHECK since 2026-10-20 and counted by roster_coverage() since 2026-10-27).
--   2. receipts_for_board_actions(npis[], state, origin): one receipt per roster NPI per state per run, written from
--      the board actions the state's bulk loader already stores (provider_adverse_actions, run-scoped beside
--      state_license_lookups). Same source, same run, same three clocks, same artifact (hash) and same
--      supersedes chain (the BEFORE INSERT trigger) as receipts_for_state_licenses.
--
-- The match rule is the license writer's exact rule and nothing looser: an action counts only when it sits on a
-- license the snapshot ties to this NPI by npi_exact or license_number_exact. A license tied by name
-- (name_state_taxonomy, a candidate) is never read into this receipt; the limitations say when one exists.
--
--   action_on_record  the board file lists at least one action for such a license. claim carries the latest
--                     action's kind, date and order or case reference, every action in claim.actions, and the
--                     file date.
--   none_in_file      it lists none, or no license is tied to the NPI by license number. Never clear. A file that
--                     carries no action columns at all (a source whose claim_types lacks state_board_action, i.e.
--                     the California DCA file) still gets none_in_file, and its limitations say the file cannot
--                     show discipline.
--
-- license_number stays NULL on these receipts so v_current_receipts keeps exactly one per NPI and state; the
-- licenses read are in claim.licenses_checked.

BEGIN;

-- 1. Two statuses for board actions.
ALTER TABLE credential_receipts DROP CONSTRAINT IF EXISTS credential_receipts_normalized_status_check;
ALTER TABLE credential_receipts ADD CONSTRAINT credential_receipts_normalized_status_check
  CHECK (normalized_status IN (
    'active','inactive','expired','suspended','revoked','probation',
    'excluded','reinstated','opted_out','enrolled','action_on_record','none_in_file',
    'not_found','unavailable','unknown'));

COMMENT ON COLUMN credential_receipts.normalized_status IS
  'The receipt vocabulary. Licenses and NPI: active, inactive, expired, suspended, revoked, probation. '
  'Exclusions (OIG, SAM): excluded, reinstated. Medicare opt-out: opted_out. PECOS enrollment: enrolled. '
  'Board actions: action_on_record (the board file lists an action on a license tied to the NPI by license number), '
  'none_in_file (it lists none; never clear). '
  'not_found: absent from that source''s snapshot on that date, never clear. unavailable: the source could not be read. '
  'unknown: the source''s status did not map.';

-- 2. The writer.
CREATE OR REPLACE FUNCTION receipts_for_board_actions(p_npis TEXT[], p_state VARCHAR, p_origin TEXT DEFAULT 'real')
RETURNS TABLE (npi VARCHAR, jurisdiction VARCHAR, normalized_status VARCHAR, match_basis VARCHAR, stage VARCHAR,
               receipt_id UUID) AS $$
#variable_conflict use_column
DECLARE
  v_state     VARCHAR := upper(p_state);
  src         data_sources%ROWTYPE;
  run         ingestion_runs%ROWTYPE;
  n_src       INTEGER;
  has_actions BOOLEAN;
BEGIN
  -- The same source and run receipts_for_state_licenses reads: the state's one bulk licensing source.
  SELECT count(*) INTO n_src FROM data_sources s
  WHERE s.jurisdiction = v_state AND s.category = 'licensing' AND 'state_license' = ANY(s.claim_types)
    AND COALESCE(s.format, '') <> 'api';
  IF n_src <> 1 THEN
    RAISE EXCEPTION 'Expected one bulk licensing source for %, found %.', v_state, n_src;
  END IF;
  SELECT * INTO src FROM data_sources s
  WHERE s.jurisdiction = v_state AND s.category = 'licensing' AND 'state_license' = ANY(s.claim_types)
    AND COALESCE(s.format, '') <> 'api';
  has_actions := 'state_board_action' = ANY(src.claim_types);

  SELECT * INTO run FROM ingestion_runs r
  WHERE r.source_id = src.id AND r.status = 'completed' ORDER BY r.completed_at DESC LIMIT 1;
  IF run.id IS NULL THEN
    RAISE EXCEPTION 'No completed run for % (%). Receipts are written by runs, never by hand.', src.name, v_state;
  END IF;

  RETURN QUERY
  WITH roster AS (
    SELECT p.id, p.npi FROM providers p WHERE p.npi = ANY(p_npis)
  ),
  exact_lic AS (
    SELECT l.id, l.provider_id, l.license_number, l.match_basis, l.match_confidence
    FROM state_license_lookups l
    WHERE l.run_id = run.id AND l.provider_id IN (SELECT r.id FROM roster r)
      AND l.match_basis IN ('npi_exact', 'license_number_exact')
  ),
  act AS (
    -- An action row carries the basis of the license row it came from; it must also sit on an exact license.
    SELECT a.id, a.provider_id, a.license_number, a.action_type, a.action_classification, a.action_date,
           a.effective_date, a.description, a.match_basis, a.raw_status::jsonb AS raw
    FROM provider_adverse_actions a
    WHERE a.run_id = run.id AND a.provider_id IN (SELECT r.id FROM roster r)
  ),
  act_exact AS (
    SELECT a.*,
           -- The order or case number when the file prints one (Florida final actions: cse_nbr). Texas prints none.
           CASE WHEN a.raw ? 'cse_nbr' AND COALESCE(a.raw->>'cse_nbr', '') <> '' THEN 'Case ' || (a.raw->>'cse_nbr') END AS reference,
           -- What makes one action the same action from one file to the next, so a new one reads as new.
           concat_ws('|', a.license_number, a.action_classification,
                     COALESCE(NULLIF(a.raw->>'cse_nbr', ''), NULLIF(a.raw->>'rec_key', ''), a.action_date::text)) AS action_key
    FROM act a
    WHERE a.match_basis IN ('npi_exact', 'license_number_exact')
      AND EXISTS (SELECT 1 FROM exact_lic l WHERE l.provider_id = a.provider_id AND l.license_number = a.license_number)
  )
  INSERT INTO credential_receipts
    (npi, provider_id, claim_type, jurisdiction, license_number, raw_status, normalized_status, claim,
     source_id, artifact_id, run_id, source_effective_at, source_published_at, retrieved_at, next_check_due_at,
     origin, stage, match_basis, match_confidence, lineage, parser_version, limitations)
  SELECT
    p.npi, p.id, 'state_board_action', v_state, NULL,
    CASE
      WHEN ax.n > 0 THEN ax.raw
      WHEN NOT has_actions THEN 'this file carries no board actions'
      WHEN lx.n > 0 THEN 'no board action listed for license ' || lx.nums_text || ' in this snapshot'
      ELSE 'no license in this snapshot tied to this NPI by license number'
    END,
    CASE WHEN ax.n > 0 THEN 'action_on_record' ELSE 'none_in_file' END,
    jsonb_build_object(
      'action_kind',       ax.items->0->'kind',
      'action_date',       ax.items->0->'date',
      'reference',         ax.items->0->'reference',
      'license_number',    COALESCE(ax.items->0->'license_number', lx.nums->0),
      'source_file_date',  run.source_published_at::date,
      'actions_on_record', COALESCE(ax.n, 0),
      'actions',           COALESCE(ax.items, '[]'::jsonb),
      'licenses_checked',  COALESCE(lx.nums, '[]'::jsonb),
      'file_lists_actions', has_actions),
    src.id, run.artifact_id, run.id,
    (ax.items->0->>'date')::timestamptz, run.source_published_at, run.completed_at,
    run.completed_at + make_interval(hours => COALESCE(src.cadence_hours, 24)),
    p_origin,
    'verified',
    COALESCE(lx.basis, 'none'),
    COALESCE(lx.conf, 0.00),
    COALESCE(lx.rows, '[]'::jsonb) || COALESCE(ax.rows, '[]'::jsonb),
    'receipts_for_board_actions/1',
    concat_ws(' ',
      CASE
        WHEN NOT has_actions THEN
          src.name || ' carries no board action columns, so none_in_file says only that this file lists no actions; '
          'it cannot show discipline. Check the board''s own lookup.'
        WHEN lx.n IS NULL THEN
          'No license in this snapshot is tied to this NPI by license number, so no board action could be read for it. '
          'None in file is not clear.'
        WHEN ax.n > 0 THEN
          CASE lx.basis WHEN 'npi_exact' THEN NULL ELSE
            'Board file carries no NPI; the action is on a license whose number is already recorded for this NPI '
            '(NPPES license field, provider_credentials, or a prior exact link).' END
        ELSE
          CASE lx.basis WHEN 'npi_exact' THEN 'None in file is not clear.' ELSE
            'Board file carries no NPI; actions are read only for licenses whose number is already recorded for this NPI. '
            'None in file is not clear.' END
      END,
      CASE WHEN cx.n > 0 THEN
        'A license tied to this NPI by name only lists ' || cx.n || ' board action' || CASE WHEN cx.n = 1 THEN '' ELSE 's' END ||
        '; a name match is never read into this receipt.' END)
  FROM roster p
  LEFT JOIN LATERAL (
    SELECT count(*)::INTEGER AS n,
           jsonb_agg(l.license_number ORDER BY l.license_number) AS nums,
           string_agg(l.license_number, ', ' ORDER BY l.license_number) AS nums_text,
           (array_agg(l.match_basis ORDER BY l.match_confidence DESC, l.id))[1] AS basis,
           max(l.match_confidence) AS conf,
           jsonb_agg(jsonb_build_object('table', 'state_license_lookups', 'id', l.id) ORDER BY l.id) AS rows
    FROM exact_lic l WHERE l.provider_id = p.id
    HAVING count(*) > 0
  ) lx ON TRUE
  LEFT JOIN LATERAL (
    SELECT count(*)::INTEGER AS n,
           jsonb_agg(jsonb_build_object(
             'key', a.action_key, 'license_number', a.license_number, 'kind', a.action_type,
             'classification', a.action_classification, 'date', a.action_date, 'effective_date', a.effective_date,
             'reference', a.reference, 'description', a.description)
             ORDER BY a.action_date DESC NULLS LAST, a.action_key) AS items,
           string_agg(concat_ws(': ', a.action_classification, a.action_type)
                      || COALESCE(' (' || a.action_date || ')', ''), ' | '
                      ORDER BY a.action_date DESC NULLS LAST, a.action_key) AS raw,
           jsonb_agg(jsonb_build_object('table', 'provider_adverse_actions', 'id', a.id) ORDER BY a.id) AS rows
    FROM act_exact a WHERE a.provider_id = p.id
    HAVING count(*) > 0
  ) ax ON TRUE
  LEFT JOIN LATERAL (
    SELECT count(*)::INTEGER AS n FROM act a
    WHERE a.provider_id = p.id AND a.match_basis NOT IN ('npi_exact', 'license_number_exact')
    HAVING count(*) > 0
  ) cx ON TRUE
  RETURNING credential_receipts.npi, credential_receipts.jurisdiction, credential_receipts.normalized_status,
            credential_receipts.match_basis, credential_receipts.stage, credential_receipts.id;
END $$ LANGUAGE plpgsql SET search_path = public;

REVOKE ALL ON FUNCTION receipts_for_board_actions(TEXT[], VARCHAR, TEXT) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION receipts_for_board_actions(TEXT[], VARCHAR, TEXT) TO service_role;

COMMIT;

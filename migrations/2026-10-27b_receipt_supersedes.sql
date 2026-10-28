-- 2026-10-27b · Receipt chains: every receipt points at the one it replaces
-- Adds, never drops. No receipt is deleted and no claim content changes; the backfill writes supersedes_id only.
--
-- What this adds:
--   1. credential_receipts_link_prior(): a BEFORE INSERT trigger, so every writer (receipts_for_npi_status,
--      receipts_for_exclusions for OIG and SAM, receipts_for_state_licenses, receipts_for_license_reverify) links
--      a new receipt to the latest prior receipt for the same (npi, claim_type, source_id). A writer that sets
--      supersedes_id itself keeps its own link (receipts_for_license_reverify points across sources on purpose).
--   2. A unique index on (npi, claim_type, source_id, run_id): one run never writes the same claim twice. Same-run
--      duplicates that already exist are exempted by id, found when this runs, and stay in history.
--   3. v_current_receipts: ties broken deterministically (latest retrieved_at, then highest id).
--   4. Backfill: supersedes_id on existing rows, each (npi, claim_type, source_id) chain ordered by retrieved_at
--      then id. The append-only guard is paused for this one UPDATE, and the migration aborts if any column other
--      than supersedes_id differs afterwards.
--
-- "Prior" is the order the chains use everywhere: (retrieved_at, id).

BEGIN;

-- 1. The shared writer: link on insert.
CREATE OR REPLACE FUNCTION credential_receipts_link_prior() RETURNS TRIGGER AS $$
BEGIN
  IF NEW.supersedes_id IS NULL THEN
    SELECT r.id INTO NEW.supersedes_id
    FROM credential_receipts r
    WHERE r.npi = NEW.npi AND r.claim_type = NEW.claim_type AND r.source_id = NEW.source_id
      AND (r.retrieved_at, r.id) < (NEW.retrieved_at, NEW.id)
    ORDER BY r.retrieved_at DESC, r.id DESC
    LIMIT 1;
  END IF;
  RETURN NEW;
END $$ LANGUAGE plpgsql SET search_path = public;

DROP TRIGGER IF EXISTS trg_credential_receipts_link_prior ON credential_receipts;
CREATE TRIGGER trg_credential_receipts_link_prior
  BEFORE INSERT ON credential_receipts
  FOR EACH ROW EXECUTE FUNCTION credential_receipts_link_prior();

-- 2. One receipt per claim per run. The later-written copy of each existing same-run duplicate is exempt.
DO $$
DECLARE
  dup_ids UUID[];
BEGIN
  SELECT COALESCE(array_agg(id ORDER BY id), '{}') INTO dup_ids
  FROM (SELECT id, row_number() OVER (PARTITION BY npi, claim_type, source_id, run_id
                                      ORDER BY created_at, id) AS rn
        FROM credential_receipts WHERE run_id IS NOT NULL) d
  WHERE rn > 1;
  RAISE NOTICE 'same-run duplicates exempted from the unique index: %', cardinality(dup_ids);
  IF to_regclass('public.uq_receipts_one_per_run') IS NULL THEN
    IF cardinality(dup_ids) = 0 THEN
      CREATE UNIQUE INDEX uq_receipts_one_per_run ON credential_receipts(npi, claim_type, source_id, run_id);
    ELSE
      EXECUTE format('CREATE UNIQUE INDEX uq_receipts_one_per_run ON credential_receipts(npi, claim_type, source_id, run_id) '
                     'WHERE id <> ALL (%L::uuid[])', dup_ids);
    END IF;
  END IF;
END $$;

-- 3. Deterministic current view: same rows and columns, ties broken by highest id.
CREATE OR REPLACE VIEW v_current_receipts AS
SELECT DISTINCT ON (npi, claim_type, COALESCE(jurisdiction,''), COALESCE(license_number,''))
       r.*,
       (r.next_check_due_at < NOW()) AS is_past_due
FROM credential_receipts r
WHERE r.stage NOT IN ('superseded','revoked','quarantined')
ORDER BY npi, claim_type, COALESCE(jurisdiction,''), COALESCE(license_number,''), retrieved_at DESC, id DESC;

-- 4. Backfill the link column.
CREATE TEMP TABLE receipts_before ON COMMIT DROP AS
SELECT id, md5((row_to_json(r)::jsonb - 'supersedes_id')::text) AS h FROM credential_receipts r;

ALTER TABLE credential_receipts DISABLE TRIGGER trg_credential_receipts_guard;

DO $$
DECLARE
  n_linked  INTEGER;
  n_changed INTEGER;
BEGIN
  UPDATE credential_receipts c
  SET supersedes_id = ch.prior_id
  FROM (SELECT id, lag(id) OVER (PARTITION BY npi, claim_type, source_id ORDER BY retrieved_at, id) AS prior_id
        FROM credential_receipts) ch
  WHERE c.id = ch.id AND c.supersedes_id IS NULL AND ch.prior_id IS NOT NULL;
  GET DIAGNOSTICS n_linked = ROW_COUNT;

  SELECT count(*) INTO n_changed
  FROM credential_receipts r JOIN receipts_before b ON b.id = r.id
  WHERE md5((row_to_json(r)::jsonb - 'supersedes_id')::text) <> b.h;
  IF n_changed > 0 THEN
    RAISE EXCEPTION 'backfill changed % rows outside supersedes_id; rolled back', n_changed;
  END IF;
  RAISE NOTICE 'backfill linked % receipts', n_linked;
END $$;

ALTER TABLE credential_receipts ENABLE TRIGGER trg_credential_receipts_guard;

COMMIT;

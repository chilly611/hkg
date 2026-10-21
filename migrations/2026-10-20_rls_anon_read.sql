-- 2026-10-20 · RLS and anon read-only access for the public portal
-- Run after 2026-10-20_receipt_layer.sql. Idempotent. Drops no tables and no data.
--
-- The rule after this runs:
--   * RLS is on for every table in public.
--   * anon (and authenticated) may SELECT the 21 tables the April portal (index.html) reads, plus v_source_status.
--   * anon and authenticated may not INSERT, UPDATE, DELETE or TRUNCATE anything, and may not execute functions.
--   * credential_receipts, source_artifacts, ingestion_runs, data_sources and v_current_receipts are closed to
--     anon and authenticated. The public sees them only through v_source_status.
--   * service_role bypasses RLS and keeps its own grants, so the ingestion scripts are unaffected.
--
-- Portal tables, taken from index.html (BROWSE_TABLES, the federated search, the NPI verify view,
-- the drug interaction checker and the record counters):
--   providers, provider_addresses, provider_taxonomies, drugs, drug_interactions, drug_adverse_events,
--   drug_labels, ndc_codes, icd10_cm_codes, icd10_pcs_codes, hcpcs_codes, drg_codes, loinc_codes,
--   mesh_terms, clinical_trials, pubmed_citations, oig_exclusions, medicare_part_d_prescribers,
--   medicare_utilization, hospitals, state_medical_boards
--
-- Note: the portal's RSI write-back (POST/PATCH to providers, provider_addresses, provider_taxonomies)
-- stops working on purpose. A browser holding a public key must not write. That path moves server side.

BEGIN;

-- 1. Close the doors first: no anon or authenticated privileges on any table, view or sequence in public.
REVOKE ALL ON ALL TABLES    IN SCHEMA public FROM anon, authenticated;
REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM anon, authenticated;

-- Functions default to EXECUTE for PUBLIC, which anon inherits. Keep them for service_role only.
REVOKE EXECUTE ON ALL FUNCTIONS IN SCHEMA public FROM PUBLIC, anon, authenticated;
GRANT  EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO service_role;

-- Future objects created by postgres start closed too. A new public table needs an explicit GRANT and policy.
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public REVOKE ALL ON TABLES    FROM anon, authenticated;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public REVOKE ALL ON SEQUENCES FROM anon, authenticated;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public REVOKE EXECUTE ON FUNCTIONS FROM PUBLIC, anon, authenticated;

-- 2. Write policies that named the public role (anon included). Remove them; writes go through service_role.
DROP POLICY IF EXISTS provider_insert_policy     ON providers;
DROP POLICY IF EXISTS provider_update_policy     ON providers;
DROP POLICY IF EXISTS organization_insert_policy ON organizations;

-- 3. RLS on every table in public. Tables without a policy below are readable by service_role only.
DO $$
DECLARE t TEXT;
BEGIN
  FOR t IN SELECT tablename FROM pg_tables WHERE schemaname = 'public' LOOP
    EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY', t);
  END LOOP;
END $$;

-- 4. Read-only access to the portal tables.
DO $$
DECLARE
  t TEXT;
  portal TEXT[] := ARRAY[
    'providers','provider_addresses','provider_taxonomies',
    'drugs','drug_interactions','drug_adverse_events','drug_labels','ndc_codes',
    'icd10_cm_codes','icd10_pcs_codes','hcpcs_codes','drg_codes','loinc_codes','mesh_terms',
    'clinical_trials','pubmed_citations','oig_exclusions',
    'medicare_part_d_prescribers','medicare_utilization','hospitals','state_medical_boards'];
BEGIN
  FOREACH t IN ARRAY portal LOOP
    EXECUTE format('GRANT SELECT ON public.%I TO anon, authenticated', t);
    EXECUTE format('DROP POLICY IF EXISTS portal_read ON public.%I', t);
    EXECUTE format('CREATE POLICY portal_read ON public.%I FOR SELECT TO anon, authenticated USING (true)', t);
  END LOOP;
END $$;

-- 5. The status page. Restores the grant from the receipt layer, which step 1 revoked.
DO $$
BEGIN
  IF to_regclass('public.v_source_status') IS NOT NULL THEN
    GRANT SELECT ON public.v_source_status TO anon, authenticated;
  END IF;
END $$;

-- 6. Prove it inside the transaction: abort if anon can write anywhere or read a receipt-layer object.
DO $$
DECLARE bad TEXT;
BEGIN
  SELECT string_agg(c.relname || ':' || p.priv, ', ') INTO bad
  FROM pg_class c
  JOIN pg_namespace n ON n.oid = c.relnamespace
  CROSS JOIN (VALUES ('INSERT'),('UPDATE'),('DELETE'),('TRUNCATE')) AS p(priv)
  WHERE n.nspname = 'public' AND c.relkind IN ('r','v','m','p')
    AND has_table_privilege('anon', c.oid, p.priv);
  IF bad IS NOT NULL THEN RAISE EXCEPTION 'anon still has write privileges: %', bad; END IF;

  SELECT string_agg(tablename || '.' || policyname, ', ') INTO bad
  FROM pg_policies
  WHERE schemaname = 'public' AND cmd IN ('INSERT','UPDATE','DELETE','ALL')
    AND (roles && ARRAY['anon','public','authenticated']::name[]);
  IF bad IS NOT NULL THEN RAISE EXCEPTION 'write policy still open to anon/public: %', bad; END IF;

  SELECT string_agg(c.relname, ', ') INTO bad
  FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
  WHERE n.nspname = 'public'
    AND c.relname IN ('credential_receipts','source_artifacts','ingestion_runs','data_sources','v_current_receipts')
    AND has_table_privilege('anon', c.oid, 'SELECT');
  IF bad IS NOT NULL THEN RAISE EXCEPTION 'anon can read receipt-layer objects: %', bad; END IF;
END $$;

COMMIT;

-- After running:
--   SELECT tablename, policyname, cmd, roles FROM pg_policies WHERE schemaname = 'public' ORDER BY 1, 2;
--   SELECT relname FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
--    WHERE n.nspname = 'public' AND c.relkind = 'r' AND NOT c.relrowsecurity;   -- expect zero rows

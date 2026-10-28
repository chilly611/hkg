-- 2026-10-28b · data_sources.lookup_url: each source's own official public lookup, for the "Open official lookup"
-- link on a FreshRoot receipt card (supabase/functions/freshroot returns it on /v1/sources; freshroot/index.html
-- builds the link).
--
-- lookup_url is an https address. "{npi}" in it is replaced with the receipt's NPI, a deep link to that provider's
-- page; without it the page opens the search and shows the license number or NPI beside the link to paste.
--
-- Board addresses are the lookup pages in docs/board_survey_2026-10-28.md (read from official pages), never the
-- unverified ones in seed_state_boards.py. Federal addresses are each publisher's own search page. Every address was
-- opened once on 2026-10-28 and landed on the official page named beside it. Utah is seeded but never read, so it
-- gets none yet. Rights (redistribution_permission, accepted_for_sale) are not touched.

BEGIN;

ALTER TABLE data_sources ADD COLUMN IF NOT EXISTS lookup_url TEXT
  CHECK (lookup_url IS NULL OR lookup_url ~ '^https://');

COMMENT ON COLUMN data_sources.lookup_url IS
  'Official public lookup page for this source. {npi} is replaced with the NPI for a deep link; otherwise the search page opens and the license number or NPI is shown to paste.';

UPDATE data_sources AS s SET lookup_url = v.url
FROM (VALUES
  -- NPPES NPI Registry: "Provider Information for <NPI>"
  ('NPI Registry',                          'https://npiregistry.cms.hhs.gov/provider-view/{npi}'),
  -- HHS-OIG: "Search the Exclusions Database"
  ('OIG LEIE',                              'https://exclusions.oig.hhs.gov/'),
  -- SAM.gov Search, Exclusions domain
  ('SAM.gov',                               'https://sam.gov/search/?index=ex'),
  -- data.cms.gov data viewer for each dataset, searchable by NPI
  ('CMS Medicare opt-out affidavits',       'https://data.cms.gov/provider-characteristics/medicare-provider-supplier-enrollment/opt-out-affidavits/data'),
  ('CMS PECOS enrollment',                  'https://data.cms.gov/provider-characteristics/medicare-provider-supplier-enrollment/medicare-fee-for-service-public-provider-enrollment/data'),
  -- Texas Medical Board "Look Up a License" (its search form sits behind a per-session link from this page)
  ('Texas Medical Board licensure file',    'https://www.tmb.texas.gov/resources/for-the-public/look-up-a-license'),
  -- FL DOH MQA Search Portal (License Verification, Practitioner Profile)
  ('Florida MQA licensee data download',    'https://mqa-internet.doh.state.fl.us/MQASearchServices/Home'),
  -- DCA License Search: Medical Board and Osteopathic Medical Board of California, by license number
  ('California DCA public information file', 'https://search.dca.ca.gov/'),
  ('California DCA Search API',             'https://search.dca.ca.gov/')
) AS v(name, url)
WHERE s.name = v.name;

DO $$
DECLARE n INTEGER;
BEGIN
  SELECT count(*) INTO n FROM data_sources WHERE lookup_url IS NOT NULL;
  IF n <> 9 THEN RAISE EXCEPTION 'expected 9 sources with lookup_url, found %', n; END IF;
END $$;

COMMIT;

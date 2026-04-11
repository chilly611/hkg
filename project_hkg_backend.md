---
name: HKG Backend Infrastructure
description: Healthcare Knowledge Garden Supabase database — 1.1M+ records across 10 core data tables, all queryable via PostgREST, separate repo and Supabase instance from BKG
type: project
---

Healthcare Knowledge Garden has a live, queryable Supabase backend.

**Supabase project:** `opbrzaegvfyjpyyrmdfe`
**API base:** `https://opbrzaegvfyjpyyrmdfe.supabase.co/rest/v1/`
**GitHub repo:** `https://github.com/chilly611/hkg` (private)
**Live site:** `https://health.theknowledgegardens.com` (GitHub Pages)
**Auth:** Service role key in `.env` (not committed). Anon key allows public read via RLS.

**Tables and record counts (verified 2026-04-10):**
- providers: 572,351 (expected 9M+ from full NPI load — partial ingest, needs investigation)
- icd10_cm_codes: 97,584
- ndc_codes: 82,740
- oig_exclusions: 82,749
- icd10_pcs_codes: 78,948
- pubmed_citations: 59,798
- provider_taxonomies: 46,723
- clinical_trials: 33,593
- drugs: 25,790
- hcpcs_codes: 22,700

**Total: ~1.1M+ records across 10 core tables**

**Critical schema notes (discovered via debugging 2026-04-10):**
- `hcpcs_codes` columns are `code` and `description` — NOT `hcpcs_code` or `short_description`
- `clinical_trials.conditions` is a **JSONB array**, not text — cannot use `ilike` on it
- `clinical_trials` uses `title` — NOT `brief_title`
- PostgREST `ilike` patterns need `%25` URL encoding (not raw `%`)
- PostgREST OR queries use `or=(col1.op.val,col2.op.val)` syntax
- HEAD requests with `Prefer: count=exact` header → parse `content-range` for counts

**Why:** This is the data backbone for investor demos showing cross-domain healthcare knowledge relationships.
**How to apply:** Always verify column names against these notes before writing queries. Use HEAD+count=exact for record counts. The providers gap (572K vs 9M) needs a full NPI re-ingest before next demo cycle.

# Health Knowledge Garden

Static portal on GitHub Pages (health.theknowledgegardens.com) over Supabase project `opbrzaegvfyjpyyrmdfe`.
See CLAUDE.md for the full picture.

## Keys: where each one goes

| Key | Where it lives | Never |
|-----|----------------|-------|
| Anon (public) key | `SUPABASE_ANON_KEY` constant in the pages listed below | |
| service_role key | `.env` on the founder's machine, as `SUPABASE_SERVICE_ROLE_KEY` | in any page, in git, in a chat |

The anon key is safe to publish only because RLS limits it to reads. `migrations/2026-10-20_rls_anon_read.sql`
grants anon SELECT on the 21 tables the portal reads plus `v_source_status`, and nothing else: no writes,
no functions, no receipts, runs or source rows.

### Setting the anon key

Get it from the Supabase dashboard: Project Settings > API > `anon` / publishable key. Then set the constant in:

- `index.html` (the portal): `var SUPABASE_ANON_KEY="..."`
- `index_v2.html`, `index_v3.html` (older portal copies, still served): same line
- `status/index.html` (the source status page at /status/): `const SUPABASE_ANON_KEY = "..."`

Before pushing, check that no page carries a service_role key:

```bash
grep -rlE 'eyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+' --include='*.html' . | while read f; do grep -oE 'eyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+' "$f" | cut -d. -f2 | base64 -d 2>/dev/null | grep -q service_role && echo "SERVICE_ROLE KEY IN $f"; done
```

## Migrations

Run in order in the Supabase SQL editor (or via the Management API query endpoint):

1. `migrations/2026-10-20_receipt_layer.sql`: rights fields, run clocks, `source_artifacts`, append-only `credential_receipts`, `v_source_status`.
2. `migrations/2026-10-20_rls_anon_read.sql`: RLS on every table, anon read-only on portal tables and `v_source_status`.
3. `migrations/2026-10-20b_state_receipts.sql`: run-scoped board license rows, `v_state_licenses_current`, `receipts_for_state_licenses(npis[], state)`.
4. `migrations/2026-10-26_ca_ut_boards.sql`: California DCA source facts, the `California DCA Search API` source, `receipts_for_license_reverify(run_id)`, bulk-only source selection in `receipts_for_state_licenses`, Utah list pricing.
5. `migrations/2026-10-28_cms_statuses.sql`: receipt statuses `opted_out` (Medicare opt-out) and `enrolled` (PECOS), and the receipt vocabulary as column comments on `credential_receipts`.
6. `migrations/2026-10-28_poll_late.sql`: `data_sources.last_polled_at` (stamped by `scripts/poll_sources.py` on every check) and the `poll late` freshness in `v_source_status` when a polled source has gone 90 minutes unchecked. Already applied to production on 2026-10-28; idempotent, so re-running it is harmless.

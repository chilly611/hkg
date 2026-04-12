# Healthcare Knowledge Garden (HKG)

## Owner
Chilly (Charles Dahlgren), Founder of XRWorkers. Building the Healthcare Knowledge Garden — the third Knowledge Garden vertical after BKG (construction) and OKG (botanical/Ecuagenera).

## What This Is
AI-native operating system for the global healthcare ecosystem. 4 lanes (Admin/Doctor/Patient/Machine), 3 surfaces (Gold/Green/Red), powered by Neo4j + Supabase + Claude API.

## Frontend v3 (LIVE)
- URL: https://health.theknowledgegardens.com/
- Single-file React 18 UMD app (index.html) — zero build step
- 4 lanes: Clinician, Patient/Caregiver, Operations, Explorer
- **Knowledge Graph**: Interactive force-directed canvas visualization (entity detail + full explorer)
- **Quick Actions**: Provider Check, Drug Lookup, Exclusion Screen, Clinical Trials
- Federated search across 13 data types with categorized dropdown
- Browse view with paginated tables, entity detail with relationship drilling
- Animated counters, particle canvas background, skeleton loaders
- Brand: DNA hexagon logo from Supabase Storage, Instrument Serif + DM Sans + JetBrains Mono
- Deployed via GitHub Pages (chilly611/hkg repo, main branch)
- Queries Supabase PostgREST API directly from browser (service_role key — RLS policies pending)

## Supabase Database (LIVE)
- Project: opbrzaegvfyjpyyrmdfe
- 28-table schema deployed with RLS, triggers, GIN indexes
- ~3.8M+ records across 18 populated tables (as of Apr 11, 2026)
- NPI backfill in progress: 814K loaded, 9M target (Pro plan, no limit)
- Connection details in .env (see .env.example)
- Schema source of truth: supabase_schema.sql

### Current Data State
| Table | Records | Source |
|-------|---------|--------|
| providers | 814,381 (backfilling to 9M) | NPPES NPI Registry |
| provider_addresses | 1,175,202 | NPPES (full bulk addr extraction Apr 11, 2026) |
| provider_taxonomies | 778,330 | NPPES (full bulk taxonomy extraction Apr 11, 2026) |
| icd10_cm_codes | 97,584 | CMS FY2025 |
| ndc_codes | 82,740 | FDA openFDA |
| oig_exclusions | 82,749 | HHS-OIG LEIE (Mar 2026) |
| icd10_pcs_codes | 78,948 | CMS FY2025 |
| pubmed_citations | 59,798 | NCBI E-Utilities |
| clinical_trials | 33,593 | ClinicalTrials.gov API v2 |
| drug_adverse_events | 126,000+ (still loading) | FDA FAERS openFDA API |
| drugs | 25,790 | NLM RxNorm |
| hcpcs_codes | 22,700 | CMS Level II |
| drug_interactions | 5,500 | RxNorm-linked |
| drg_codes | 863 | CMS MS-DRG v42 |
| drug_labels | 700 | NLM DailyMed (in progress) |
| state_medical_boards | 51 | 50 states + DC |
| data_sources | 10 | Registry |
| sam_exclusions | 5 | SAM.gov (API issues — needs real key) |

### Pending Data Work
- **NPI backfill**: Run `cd scripts/ingestion && python3 npi_backfill.py` on local Mac (9M target, uses UPSERT)
- **FAERS adverse events**: 106K+ loaded (continuing to grow via sandbox runs)
- **Hospital Quality**: Create `hospitals` table (see create_new_tables.sql), then run `python3 ingest_hospital_quality.py`
- **Medicare Utilization**: Create `medicare_utilization` table, then run `python3 ingest_medicare_utilization.py`
- OIG-NPI reconciliation: ~2,900 of ~9,120 matched. Run `python3 apply_oig_matches.py`
- DailyMed drug labels (5,500 target, ~700 loaded so far)
- SAM.gov exclusions (needs registered API key)

### Cross-Project Note
Frontend was built in the BKG (Builder's Knowledge Garden) project and deployed to health.theknowledgegardens.com. The index.html needs to be migrated into this repo. The BKG project also created HKG-specific markdown files (project_hkg_backend.md, project_hkg_frontend.md) that should be merged here.

## Key Files
- `tasks.todo.md` — Living development plan with checkable items
- `tasks.lessons.md` — Accumulated lessons from BKG/OKG/HKG (MUST READ before major decisions)
- `supabase_schema.sql` — 28-table schema (source of truth)
- `scripts/ingestion/` — All data ingestion scripts (Python, stdlib only)
- `HKG_Data_Architecture.md` — Full data architecture design
- `HKG_Technical_Implementation_Guide.md` — Technical implementation details
- `HKG_AI_Citation_Strategy.md` — The llms.txt / JSON-LD / entity URL strategy
- `HKG_RSI_Heartbeat_System.md` — Recursive Self-Improvement system design
- `MULTI_MACHINE_WORKFLOW.md` — Guide for working across machines/accounts

## Terms
| Term | Meaning |
|------|---------|
| MLP | Minimal Lovable Product — not MVP. Every interaction must feel like the future. |
| RSI | Recursive Self-Improvement — platform autonomously updates with latest knowledge |
| Gold Surface | Dream Machine — aspirational, concierge feel (Patient lane primary) |
| Green Surface | Knowledge Garden — scientific, verified, educational (Doctor lane primary) |
| Red Surface | Killer App — operational, urgent, metric-driven (Admin lane primary) |
| Machine Lane | MCP/API data layer for AI agents, bots, and external systems |
| Gravity Well | The Patient/Public lane — free tier that pulls the entire ecosystem in |
| 3-Point Verification | Cross-check against (1) peer-reviewed lit, (2) clinical guidelines, (3) regulatory/FDA databases |
| Notification Orchestra | Gold/Green/Amber/Red alert system — every alert includes a pre-researched solution |
| Morning Briefing | AI-synthesized, persona-aware narrative that replaces traditional dashboards |
| llms.txt | Structured text file that makes websites AI-agent-readable — the sleeper play |

## Preferences
- Autonomous execution — don't ask, go build
- Plan first, then execute with elegance
- If something breaks, STOP and re-plan
- Simplicity first, no hacks
- The llms.txt / JSON-LD / entity URL strategy is a priority — every page must be an AI citation source
- Update tasks.todo.md and tasks.lessons.md as you work
- Read tasks.lessons.md at session start — it prevents repeating mistakes

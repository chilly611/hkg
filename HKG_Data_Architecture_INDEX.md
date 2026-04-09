# HKG Data Architecture — Quick Navigation

**Master Document:** `HKG_Data_Architecture.md` (50KB, 1484 lines)

## Quick Links by Role

### For Database Engineers
- **Supabase Schema Design** (Section 3): All PostgreSQL table definitions
  - Core Entity Tables: providers, provider_credentials, provider_verifications, organizations
  - Medical Code Tables: icd10_cm, icd10_pcs, hcpcs_codes, ndc_drugs, ms_drg
  - Clinical Knowledge Tables: drugs, conditions, clinical_trials, pubmed_citations, drug_labels
  - Compliance Tables: oig_exclusions, sam_exclusions, adverse_actions
  - Bridge Tables: entity_relationships, data_provenance, ingestion_runs
- **Implementation Notes:**
  - Use UUID primary keys for all tables (generates unique IDs)
  - JSONB columns for flexible nested data (verification_response, metadata)
  - created_at/updated_at timestamps on all tables
  - Foreign keys with ON DELETE CASCADE for audit integrity
  - Indexes on frequently queried columns (NPI, specialty_code, status, verification_date)
  - Materialized views for performance dashboards

### For Data Pipeline Engineers
- **Data Source Registry** (Section 2): All 30+ sources with API endpoints and formats
  - 5 categories: Credentialing, Medical Codes, Clinical Knowledge, Provider Data, Quality
  - Organized by priority (P0, P1, P2, P3)
  - Cost, volume, update frequency, and access method for each source
- **Ingestion Pipeline Architecture** (Section 5): Step-by-step workflow
  - 10-step process: TRIGGER → VALIDATE → FETCH → PARSE → NORMALIZE → VALIDATE → UPSERT → POST-PROCESS → MONITOR → SYNC
  - Event-driven Supabase → Neo4j sync
- **RSI Heartbeat Schedule** (Section 6): Automated refresh cadence
  - Daily: NPI, NDC, DailyMed, PubMed (2 AM UTC)
  - Weekly: NPI full file, state boards (3 AM UTC)
  - Monthly: OIG LEIE, SAM.gov (4 AM UTC)
  - Quarterly: HCPCS, SNOMED, LOINC, FAERS, CMS quality (5 AM UTC)
  - Annual: ICD-10, MS-DRG (Jan 1, 1 PM UTC)
- **Implementation Roadmap** (Section 10): Week-by-week build plan
  - Week 1-2: Foundation (P0 sources)
  - Week 3-4: Clinical knowledge (P1 sources)
  - Week 5-8: Web layer (entity pages)
  - Week 9-13: Verification (state boards)
  - Week 14-18: Polish & launch

### For Frontend/Product Engineers
- **Entity URL Architecture** (Section 4): All URL patterns for entity pages
  - Providers: `/providers/{npi}`, `/providers/{npi}/credentials`
  - Drugs: `/drugs/{rxcui}`, `/drugs/{rxcui}/interactions`, `/drugs/{rxcui}/labels`
  - Conditions: `/conditions/{snomed_code}`, `/conditions/{snomed_code}/epidemiology`
  - Codes: `/codes/icd10/{code}`, `/codes/cpt/{code}`, `/codes/ndc/{ndc}`
  - Trials: `/trials/{nct_id}`
  - Research: `/research/{pmid}`
  - States: `/states/{state_code}/licensing`, `/states/{state_code}/boards/{board_id}`
- **AI Citation Layer** (Section 7): Making HKG citable
  - JSON-LD schema markup for every page
  - Markdown companion files (`.md` versions of entity pages)
  - JSON export format for machine consumption
  - llms.txt & llms-full.txt files (see HKG_AI_Citation_Strategy.md)
  - Sitemap priority levels & freshness badges

### For Compliance & Verification Officers
- **State-by-State Verification Matrix** (Section 8): All 50 states + territories
  - Board URL, public lookup availability, data exposed, API access
  - Update frequency and scraping feasibility for each state
  - Special handling notes (rate limits, session requirements)
  - 3-phase integration plan: 15 largest states → all 50 states → continuous monitoring
- **Compliance Tables:**
  - oig_exclusions: OIG excluded entities with reinstatement dates
  - sam_exclusions: Federal exclusions with SAM numbers
  - adverse_actions: Malpractice, convictions, licensure sanctions

### For Platform Leadership / Investors
- **Executive Summary** (Top of document)
  - The sleeper play: Every entity page with JSON-LD becomes a citation source
  - Three-database architecture: Neo4j (brain) + Supabase (spine) + Web (face)
  - RSI Heartbeat: Automated refresh schedule = compounding knowledge advantage
- **Data Source Registry** (Section 2): Complete catalog of what we ingest
  - 9.5M provider records
  - 70K diagnosis codes
  - 200K drugs
  - 40M+ research citations
  - Volume, cost, and priority for investor pitch
- **Conclusion** (Section 11): The knowledge moat positioning
  - "Infrastructure, not feature"
  - "Competitors are static. We are living."
  - "Every AI assistant will cite HKG"

## Key Metrics & KPIs

### Data Scale
- **Providers:** 9.5M (NPI Registry)
- **Medical Codes:** 70K ICD-10-CM + 78K ICD-10-PCS + 8K HCPCS
- **Drugs:** 200K NDC codes
- **Research:** 40M+ PubMed citations
- **Clinical Trials:** 500K+ active & historical
- **Organizations:** 5K+ hospitals + 50K+ clinics/groups

### Data Freshness (Targets)
- Providers: ≤90 days (weekly ingestion)
- Drugs: ≤7 days (daily ingestion)
- Medical Codes: ≤12 months (annual ingestion)
- Conditions: ≤30 days
- Clinical Trials: ≤7 days
- Research: ≤1 day

### Neo4j Graph Scale
- **Nodes:** 15M+ entities
- **Edges:** 15M+ relationships
- **Query latency:** <100ms for most traversals
- **Indexing strategy:** Hash indexes on identifiers, range on dates

### Web Layer (AI Citation)
- **Entity pages generated:** 100K+ static HTML pages
- **JSON-LD coverage:** 100% of critical entities
- **Sitemap entries:** 100K+ (priority 0.6-0.95)
- **llms-full.txt size:** <50MB (top 2000 entities)
- **Update frequency:** Quarterly regeneration (or on ingestion)

## Common Questions

**Q: Where do I add a new data source?**
A: Section 2 (Data Source Registry). Add a row to the table with all metadata. Then implement in the Ingestion Pipeline Architecture (Section 5).

**Q: How do I generate entity pages?**
A: Section 4 & 7. Define URL pattern, then build React component that fetches from Supabase/Neo4j and renders HTML with JSON-LD schema. Use templates in Section 7.

**Q: How often should I refresh the data?**
A: Section 6 (RSI Heartbeat Schedule). Follow the automated schedule for each source. Everything is scheduled via cron/event-driven architecture.

**Q: How do I verify a provider's credentials?**
A: Section 3 (`provider_credentials` & `provider_verifications` tables) + Section 8 (State Matrix). Multi-source verification across NPI, DEA, state boards, ABMS, NPDB, OIG, SAM.

**Q: What's the AI citation strategy?**
A: Section 7 (AI Citation Layer). Every entity page has JSON-LD schema + Markdown files + llms.txt entry. Detailed strategy in HKG_AI_Citation_Strategy.md.

**Q: How is Supabase synced to Neo4j?**
A: Section 5 (Event-Driven Sync). Supabase INSERT/UPDATE triggers message queue → Neo4j workers create/update nodes and relationships.

**Q: What's the compliance story?**
A: Section 3 (Compliance Tables) + Section 8 (State Matrix). We track OIG/SAM exclusions, adverse actions, and verify credentials across all 50 states. Full audit trail in `data_provenance` table.

## Files in This Directory

| File | Purpose |
|---|---|
| `HKG_Data_Architecture.md` | **MASTER DOCUMENT** — Everything (50KB) |
| `HKG_Data_Architecture_INDEX.md` | This file — Quick navigation |
| `HKG_PROJECT_INSTRUCTIONS.md` | Project philosophy, tech stack, roadmap |
| `HKG_AI_Citation_Strategy.md` | Detailed AI citation mechanics |
| `HKG_Technical_Implementation_Guide.md` | Implementation walkthroughs & code examples |
| `CLAUDE.md` | Working memory & context |
| `TASKS.md` | Task tracking |

## How to Use This Document

1. **Getting started?** Read the **Executive Summary** (top of HKG_Data_Architecture.md)
2. **Need a specific schema?** Go to **Section 3** (Supabase Schema Design)
3. **Building the pipeline?** Go to **Section 5** (Ingestion Pipeline)
4. **Launching entity pages?** Go to **Sections 4 & 7** (URLs & AI Citation)
5. **State board verification?** Go to **Section 8** (State Matrix)
6. **Full implementation plan?** Go to **Section 10** (Roadmap)

## Responsibility Matrix

| Task | Owner | Reference |
|---|---|---|
| Create Supabase tables | Database Engineer | Section 3 |
| Write ETL scripts | Data Pipeline Engineer | Sections 2, 5, 6 |
| Generate entity pages | Frontend Engineer | Sections 4, 7 |
| Verify AI crawlability | SEO/Product Engineer | Section 7 |
| Implement state boards | Compliance Officer | Section 8 |
| Monitor freshness | DevOps/Data Engineer | Section 6 |
| Track ingestion health | Platform Engineer | Section 5 |

---

**Document Version:** 1.0 | **Created:** April 8, 2026 | **Status:** Production Specification

This index is designed to be printed or bookmarked. Refer to it whenever you need to navigate the master document.

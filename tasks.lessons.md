# Healthcare Knowledge Garden (HKG) — Lessons Learned

**Project Lineage:** BKG (construction vertical) → OKG (botanical/Ecuagenera vertical) → HKG (healthcare vertical)

The Knowledge Garden pattern is proven across two verticals. This document captures architectural and development lessons from prior implementations and adds healthcare-specific considerations that must inform every design decision.

---

## Data Ingestion Sprint Lessons (Apr 9-10, 2026)

### Supabase Management API Is the Sandbox Escape Hatch
Direct PostgreSQL connections (psycopg2, pooler) are blocked by sandbox DNS/networking restrictions. The Supabase Management API (`POST /v1/projects/{ref}/database/query`) called from the browser's authenticated JavaScript context works reliably for schema DDL.

**Why:** The sandbox allows HTTPS but blocks TCP database connections. The browser already has Supabase auth tokens in localStorage.

**Action:** For DDL operations (CREATE TABLE, ALTER, functions), use the Management API via browser JS. For bulk data inserts, use the PostgREST REST API with the service_role key from Python — this goes over HTTPS and handles batched inserts at ~1,200-1,800 rec/sec.

### VARCHAR Lengths Must Match Real Data Before Ingestion
Schema columns like `chapter VARCHAR(5)` fail when real data has values like `"01. Infectious & Parasitic (A00-B99)"`. Always check max field lengths in source data BEFORE inserting.

**Action:** Before first insert, sample the parsed data with `max(len(field))` and ALTER TABLE if needed. Build this check into every ingestion script.

### FK Constraints Block Ingestion Order
The `oig_exclusions.npi` FK to `providers.npi` means exclusions can't reference providers that haven't been loaded yet. Similarly, `drug_labels` references `drugs(id)`.

**Action:** Always insert parent tables first. For cross-references that span datasets (OIG→NPI), insert with FK fields NULL, then reconcile with an UPDATE after the referenced table is populated. Create reconciliation functions like `reconcile_oig_exclusions()`.

### PostgREST Column Names Must Match Schema Exactly
PostgREST returns `PGRST204: Could not find column X in schema cache` for any mismatch. Common gotchas: `last_updated` vs `last_update_date`, `state` vs `license_state`.

**Action:** Before writing ingestion scripts, query `information_schema.columns` for the exact column names. Don't guess from the schema SQL file — the deployed schema may differ.

### CMS Download URLs Are Unreliable
CMS changes download URLs frequently. ZIP file URLs from one fiscal year return 404 the next. The NPI NPPES bulk download is the most stable.

**Action:** Build download scripts with fallback URL lists. For CMS data, always try the current year first, then prior year. Keep working download URLs in the `data_sources` table for future reference.

### Batch Size Sweet Spots
- PostgREST inserts: 500 records/batch is optimal for most tables (~1,200/sec)
- NPI full load: 2,000 records/batch works well (~1,750/sec)
- Very large JSONB fields (NDC active_ingredients): reduce to 100-200/batch

### Schema Chunk Splitting Requires FK Ordering
When splitting a large schema migration into chunks, tables MUST be ordered by FK dependency. The original 7-chunk split missed the medical code tables and drugs table, causing chunk 3 (drug_labels) to fail on missing `drugs(id)` reference.

**Action:** Always verify chunk ordering matches CREATE TABLE dependency graph. Use `IF NOT EXISTS` and `CREATE INDEX IF NOT EXISTS` for idempotency.

### Long-Running Background Processes Die Silently in Sandbox
The NPI bulk load (9.4M records, ~90min estimated) was killed repeatedly at ~30min mark with no error message. The sandbox has a hard process lifetime limit around 30 minutes for background processes. Three separate restart attempts all died at similar intervals.

**Action:** For loads exceeding ~30min wall time, the sandbox CANNOT complete them in a single process. Options: (1) chunk the source file and run sequential sub-30-min jobs, (2) build a checkpoint/resume mechanism that skips already-inserted records, (3) run the ingestion from an environment without process limits (local machine, CI/CD, cloud function). UPSERT makes re-runs safe but wastes time re-processing early records. The NPI 9.4M load likely needs to run outside this sandbox.

### Parallel API Ingestion Agents Are Extremely Effective
Launching 4 agents simultaneously (ClinicalTrials.gov, RxNorm, SAM.gov, State Boards) completed all four in ~8 minutes total wall time. Second wave (PubMed, DailyMed, Drug Interactions) similarly efficient.

**Action:** For P1+ data sprints, always parallelize independent data source ingestions. Each agent gets: table schema, API docs, connection details, and target record count. Let them work autonomously.

### SAM.gov API Is Unreliable from Sandbox
The SAM.gov entity exclusions API (api.sam.gov) returned 404s. The DEMO_KEY has rate limits and the API may require registration.

**Action:** SAM.gov needs a registered API key (not DEMO_KEY) for reliable access. Consider downloading the CSV extract from sam.gov/data-services instead. Flag this for manual intervention or a different network environment.

### Cross-Project Work Fragments Context
Building the HKG frontend in the BKG project created a split brain — backend knowledge here, frontend knowledge there, each with its own tasks.lessons.md and tasks.todo.md. Reconciliation cost time and tokens.

**Action:** All HKG work should happen in the HKG repo (chilly611/hkg) or a dedicated HKG Cowork session pointing at that folder. If another project needs to build HKG features, it should clone the HKG repo first, and push results back. One repo = one source of truth. The CLAUDE.md in the repo carries all context.

### CMS NPPES Download URL Requires _V2 Suffix
The NPPES bulk download URL changed — `NPPES_Data_Dissemination_March_2026.zip` (no suffix) returns a 10-byte garbage file. The correct URL is `NPPES_Data_Dissemination_March_2026_V2.zip`. Also, the CMS server does NOT honor HTTP Range requests, so `curl -C -` (resume) silently downloads 0 bytes. If a download is interrupted, delete the partial file and start fresh.

**Action:** Always use `_V2` suffix for NPPES downloads. If interrupted, `rm` the partial file before retrying — don't attempt resume.

### RxNorm Bulk Concept Fetching Is Fast
The /allconcepts endpoint returns all concepts for given TTYs in a single call. SCD+SBD fetched 27,390 concepts in minutes. Individual property lookups (/rxcui/{id}/properties) are slow — skip for initial bulk load.

**Action:** For initial drug population, use /allconcepts with TTY filters. Enrich with individual properties (NDC codes, drug class, interactions) in a separate pass after the base records exist.

### Verify Actual Record Counts After Bulk Load — Don't Trust Script Output
The NPI bulk load script reported inserting 9,078,000 records, but actual API count showed only 572,351. The sandbox kept killing the process at ~30 minutes, and the script was re-run multiple times. The "9M inserted" count was likely the script reading through the CSV and counting processed rows, but the POST requests were failing silently or the process was killed before batches were committed.

**Action:** After any bulk load, ALWAYS verify the actual record count via `cnt(table)` API call or Supabase dashboard. Never trust the script's self-reported count. For loads exceeding 30 min, use the local Mac with the `npi_backfill.py` UPSERT script which safely resumes.

### openFDA API URL Encoding
The openFDA search API requires brackets `[` and `]` to be URL-encoded as `%5B` and `%5D`. Using `urllib.parse.urlencode` double-encodes them, causing 500 errors. Build the URL manually with pre-encoded brackets.

**Action:** For openFDA date range queries, construct URLs like: `search=receivedate:%5B20230101+TO+20230331%5D&limit=100`

### Existing Schema May Differ From Script Expectations
The `drug_adverse_events` table existed from the original schema with columns like `event_date`, `source_quarter`, `rxcui` — NOT `safety_report_id`, `patient_age`, `drug_indication` that a new script might expect. Always check `information_schema.columns` or test with a `?select=*&limit=0` query before writing ingestion scripts.

**Action:** Before writing any ingestion script, query the actual table columns first. Don't assume from docs or SQL files.

### count=exact Times Out on Large Tables — Use count=estimated
The `Prefer: count=exact` header on Supabase PostgREST queries times out on tables with millions of rows (9.4M providers). The `.catch()` in the frontend returned 0, making it look like zero providers existed.

**Action:** For tables with >100K rows, always use `Prefer: count=estimated`. Estimated is fast and accurate enough for display (returned 9,427,624 within <1s). Only use exact for small tables.

### NLM Clinical Tables API Caps at 500 Results Per Query
The NLM Clinical Tables API (`clinicaltables.nlm.nih.gov`) ignores the `start` parameter for paginating beyond 500 results. The `offset` parameter works but the API still caps total results at 500 for blank-term searches.

**Action:** Use recursive prefix drilling: search by numeric prefix (100-999), then letter prefixes (LP, LA). If any prefix returns 500+ results, subdivide into deeper prefixes (1000-1009, etc.). This is the only reliable way to extract the full LOINC dataset (~108K codes).

### CMS Data API Endpoint Discovery
CMS frequently deprecates dataset IDs — old endpoints return 404 or 410. The working approach is to search the CMS data catalog at `data.cms.gov/data.json` for current dataset UUIDs.

**Action:** Before writing any CMS ingestion script, verify the dataset endpoint is live by searching `data.cms.gov/data.json` for the dataset title. Keep working endpoint UUIDs in CLAUDE.md and data_sources table for future reference.

### Git Lock Files Persist in Sandbox
The sandbox cannot delete `.git/index.lock` or `.git/HEAD.lock` files due to filesystem permissions. These accumulate from interrupted git operations and block subsequent commits.

**Action:** When git operations fail with "index.lock exists", the user must run `rm -f .git/index.lock .git/HEAD.lock` from their local Mac terminal before retrying. The sandbox `rm -f` will fail silently.

### GitHub Push Requires Local Mac — Sandbox Has No Git Credentials
The sandbox cannot authenticate with GitHub (no SSH keys, no HTTPS tokens). All git push operations must happen from the user's Mac terminal.

**Action:** After making changes in the sandbox, instruct the user to run `cd ~/Documents/Claude/Projects/Health\ Knowledge\ Garden && git add -A && git commit -m "message" && git push origin main` from their terminal.

---

## Architecture Lessons (from BKG/OKG)

### Neo4j Graph Database Must Be First
Graph database (Neo4j) must be the FIRST infrastructure decision — everything contextual depends on it.

**Why:** The Knowledge Garden pattern relies on relationship-rich data modeling. Building relational-first or API-first and adding Neo4j later creates impedance mismatch, schema migrations, and data integrity issues. In HKG, the graph core must model provider networks, patient pathways, clinical decision trees, credential chains, and billing relationships from day one. The graph IS the knowledge garden.

**Action:** Before writing any feature code, complete the Neo4j schema design. Include: Provider nodes (credentials, specialty, location), Patient nodes (anonymized journey state), Care Pathway nodes (clinical protocols), Credential nodes (state, specialty, expiration), and Billing nodes (CPT codes, ICD-10 mappings, payer rules).

---

### Auth and Billing Are Foundational
Authentication and billing systems must be deployed before any lane-specific features.

**Why:** BKG and OKG learned this the hard way. Every user-facing feature depends on knowing "who is this user" and "what tier are they." Adding auth/billing mid-development creates security debt and forces rework. In healthcare, auth is even more critical—role-based access (patient vs. provider vs. admin) determines what data is visible and what actions are permitted.

**Action:** Deploy a complete auth system (SSO for healthcare providers, password + 2FA for patients) and Stripe billing integration in Phase 1. Verify: provider credential scoping works end-to-end, patient data is never visible cross-tenant, and billing reflects actual usage.

---

### Design System Shared Across Surfaces Reduces Duplication
A single, unified design system used across Gold/Green/Red surfaces prevents component drift and speeds iteration.

**Why:** BKG/OKG teams built Gold once, then had to re-implement half of it for Green and Red. Components drifted. Bugs fixed in one surface leaked into others. The Design System module became the source of truth—colors, typography, form controls, tables, card layouts, modals, notifications.

**Action:** Before building Gold surface, define the HKG Design System as a shared npm module. Include: form primitives (with healthcare-specific validation), notification components (for alerts tied to Notification Orchestra), card layouts (for credential display, patient timeline, care recommendations), and accessibility patterns (WCAG 2.1 AA—required for healthcare).

---

### Three Surfaces Are Three VIEWS of the Same Data, Not Three Apps
Gold, Green, and Red are different user perspectives on the same Knowledge Core, not separate applications.

**Why:** OKG initially treated Red as a separate app. Data inconsistencies followed. Patient credential changed in Green but not Red. The single source of truth must be the Knowledge Core (Neo4j). Surfaces query the same APIs, transform the same data, but show it through persona-specific lenses.

**Healthcare context:** A provider viewing their credentials in Gold, a patient viewing approved providers in Green, and an admin verifying credentialing chains in Red are all reading from the same credential nodes. The graph is the arbiter of truth.

**Action:** Surfaces are stateless consumers of Knowledge Core APIs. Any data mutation goes through the core (with role-based access enforcement), never directly to the database. Test: modify a provider credential in Gold, verify it appears correctly in Green (filtered for patient visibility) and Red (with full audit trail).

---

### Module Structure Matters: Order Your Dependencies Correctly
Build in this order: Neo4j Schema → Auth System → Stripe Billing → Design System → Onboarding → Machine Lane → Lane-Specific Features.

**Why:** BKG learned that building features before foundational layers creates dependency tangles. Lane-specific code (e.g., credentialing workflows) depends on auth to know user identity. Onboarding depends on design system. Machine Lane depends on clean API contracts (which come from schema design).

**Healthcare specific:** Billing depends on having accurate credential and claim data in the graph. Regulatory compliance checks depend on having auth scoped correctly. Building in order prevents rework.

**Action:** Plan explicitly. Use a dependency diagram. If you're tempted to skip a layer or reorder, STOP and re-plan (see Development Process section).

---

### MCP/API Layer (Machine Lane) Is Not Phase 2
The Machine Lane (MCP contracts, API design, data export) must be built alongside the Knowledge Core, not bolted on later.

**Why:** OKG built the core first, then realized the data models didn't support the use cases the Machine Lane needed. Redesign work followed. The data contract—what fields, what relationships, what filters—must be right from the start. In healthcare, this is even more critical: HL7 FHIR and X12 standards define how data should be structured for interoperability.

**Action:** Before building surfaces, design the MCP endpoints and API schema. Include: provider credential export (FHIR format), patient record retrieval (HIPAA-compliant), claims submission (X12 EDI format). Verify that the Neo4j schema can efficiently serve these contracts. If it can't, redesign the schema now, not in Phase 2.

---

## UX Lessons

### Onboarding IS the Product — 30-Second Time-to-Value
Users must see value and understand the product within 30 seconds of signup, or they leave.

**Why:** BKG/OKG analytics showed 60% of users who didn't reach "aha moment" in first 30 seconds never returned. The "aha" is not a tour—it's *showing something useful immediately.* For a construction manager, it's seeing their first project dashboard. For an OKG user, it's seeing plant care recommendations relevant to their garden.

**Healthcare context:** For a provider, the aha is seeing credentialing status and next renewal date. For a patient, it's seeing a list of verified providers matching their zip code and insurance. This must happen without form fields, without reading documentation.

**Action:** Design the 30-second onboarding flow first. Measure it: new user → signup → sees first piece of relevant data. If it takes longer, redesign. Build the onboarding module before lane-specific features—it's not a Phase 2 afterthought.

---

### Morning Briefings > Dashboards
Narrative beats data tables. A well-structured briefing email or mobile notification is more actionable than a dashboard full of charts.

**Why:** OKG Morning Briefings (e.g., "Your monstera needs water today; pest risk is medium; humidity is 65%") drove 5x more engagement than the dashboard. Humans process narrative faster than they scan tables. Context matters.

**Healthcare context:** A provider's morning briefing: "3 credentials expire in 90 days. 1 malpractice claim open. Your patient load is 15% above monthly average." A patient's briefing: "Dr. Smith is now verified in your area. Your medication refill is ready. Your insurance updated claims rules."

**Action:** Build the Briefing Generation system as a top-level feature, not a secondary report. Design the templates (Jinja or similar). Connect to Notification Orchestra. Measure engagement: do users act on briefing content? If not, iterate on the narrative.

---

### Progressive Disclosure Prevents Overwhelm
Reveal complexity only when contextually needed.

**Why:** BKG dashboards initially showed every metric. Users felt lost. OKG learned: start simple (plant name, water status), then reveal details on demand (historical watering data, pest log, seasonal recommendations). Progressive disclosure respects user cognitive load.

**Healthcare context:** A patient initially sees: "Provider verified? Yes/No." On click, they see credentials, specialties, office locations, insurance accepted, reviews. A provider initially sees: "Credentials valid? Yes/No." On click, they see each credential with expiration, issuing board, renewal timeline.

**Action:** Design surface layouts with a "default" view (3–5 key facts) and "expanded" views (details on demand). Test with users: do they feel overwhelmed? If yes, delete information, don't add toggles.

---

### Notification Orchestra Must Include Pre-Researched Solutions
Every alert must come with a suggested next action, not just a problem statement.

**Why:** A notification that says "credential expiring in 60 days" is noise. A notification that says "credential expiring in 60 days. Renewal course at X hospital, next cohort starts April 15. Estimated cost: $500. Button: Apply Now" is actionable. OKG learned this: pair every alert with a solution.

**Healthcare context:** Regulatory requirements, licensing renewal processes, and credentialing pathways are complex. The system must do the research (where to renew, how much it costs, what paperwork is needed) and present it alongside the alert.

**Action:** When building the Notification Orchestra, add a "solutions" layer. For each alert type, define pre-researched paths (e.g., credential renewal → list of authorized training providers). Connect to the Machine Lane—programmatically pull renewal schedules, course listings, costs.

---

### Persona-Awareness Must Be Baked In, Not Bolted On
Every surface, every feature, every notification must be persona-aware from day one.

**Why:** BKG tried adding "role-based views" late. It created code duplication and inconsistency. Personas must shape data modeling, API contracts, UI layouts, notification rules, and permission scoping from the start. A feature that's "only for providers" but you forgot to add the auth check is a data leak.

**Healthcare context:** Personas in HKG: Patient (seeking verified providers), Provider (managing credentials), Payer (auditing claims), Admin (system oversight). Each persona sees a different Knowledge Garden. The permission model must be granular: a patient never sees another patient's data; a provider never sees claims they didn't submit; a payer never sees provider personal data beyond what's necessary for audit.

**Action:** Before coding, list all personas and their data access rules. Add to schema design (e.g., `[:VISIBLE_TO {role: "patient"}]` relationships). Verify in code review: did someone add a field without checking persona scoping? If yes, it's a blocker.

---

## Development Process Lessons

### Write Specs Before Code
Ambiguity in specifications becomes bugs in production.

**Why:** BKG teams moved fast and broke things—then spent 2x the time fixing bugs that could've been prevented with a 30-minute spec. Clear specs (e.g., "when a credential expires, notify provider 60 days prior, then 14 days prior, then 1 day prior") prevent misunderstandings.

**Action:** For any feature with more than 3 acceptance criteria, write a spec first. Include: user story, acceptance criteria, data models affected, API endpoints, error cases. Get feedback. *Then* code. This actually saves time.

---

### Plan Mode for Tasks With 3+ Steps or Architectural Decisions
Complex tasks need a plan before execution.

**Why:** Diving into code on a task like "build credentialing workflow" without a plan leads to rework, wrong abstractions, and half-finished features. A 20-minute plan saves 2 hours of coding and rework.

**Action:** If a task involves 3+ steps or an architectural decision, write a brief plan (text, diagram, or both) before starting. Include: what data models are involved, what APIs need to change, what surfaces are affected, what could go wrong. Share the plan. *Then* execute.

---

### If Something Goes Sideways, STOP and Re-Plan
Don't keep pushing a broken approach.

**Why:** OKG teams got stuck on a dead-end approach (trying to force relational schema onto graph problems) and kept coding instead of stopping to reconsider. 3 days of work went into a design that was fundamentally wrong. A 1-hour re-plan would've caught it.

**Action:** If you hit an unexpected blocker, strange behavior, or find your approach doesn't match the data model, STOP. Don't add workarounds. Re-plan. Talk it through. Update the spec. *Then* resume.

---

### Use Subagents for Parallel Research and Exploration
Complex problems (e.g., "how do we handle state-specific credentialing rules?") benefit from parallel research.

**Why:** BKG learned this when diving into construction billing complexity. One person got stuck in a rabbit hole. Using multiple subagents to research different angles (state regulations, database design, API contracts) in parallel saved a week.

**Healthcare context:** Healthcare has massive regulatory variation. Use subagents to research: HIPAA compliance patterns, state-by-state credentialing requirements, HL7 FHIR implementation patterns, insurance claim processing rules—in parallel.

**Action:** For open-ended research questions, spin up multiple subagents. Summarize findings. Identify consensus and disagreement. Make a decision based on the evidence. Update the spec. Move forward.

---

### Update tasks.todo.md and tasks.lessons.md as You Work
They're living documents, not artifacts.

**Why:** BKG teams treated the task list as "done when project ships." It became stale. OKG learned: update the task list daily. It's how you communicate status, block others from duplicate work, and capture insights. Lessons learned *while you work* are more actionable than those captured in retrospective.

**Action:** Daily: review tasks, update status, add new blockers. Weekly: review lessons learned, add new patterns, update anti-patterns. This is not overhead—it's how the team stays synchronized.

---

### Verify Before Marking Done
Run tests, check logs, demonstrate correctness.

**Why:** "Done" in BKG initially meant "code shipped." It often meant "I didn't see an error." Post-launch, bugs appeared because verification was skipped. OKG enforced: verify before done.

**Action:** For any feature, the definition of done includes: unit tests pass, integration tests pass, manual test on all surfaces (Gold/Green/Red), logs clean (no warnings or errors), and a demo to a peer. A pull request that doesn't meet this is not ready.

---

## Healthcare-Specific Considerations (New for HKG)

### HIPAA Compliance Is Foundational, Not a Retrofit
Every data model decision must account for HIPAA from day one.

**Why:** Retrofitting HIPAA compliance after building the system is expensive and introduces security gaps. HIPAA shapes encryption, access control, audit logging, and data retention. These are architectural decisions, not features.

**Healthcare context:** HIPAA requires: encryption at rest and in transit, audit logs of every PHI access, role-based access control, minimum necessary principle (users see only data they need), secure deletion (when records are purged), breach notification (if data is exposed).

**Action:** Before building any user-facing feature, have a HIPAA checklist. Data model: PHI fields encrypted? Access rules: only necessary data visible? APIs: audit-logged? Deletion: secure and logged? If the answer to any is "we'll add it later," stop. Design it in.

---

### 3-Point Verification Is Both Product Feature and Regulatory Differentiator
Provider credentials must be verified by three independent sources (board, employer, malpractice registry).

**Why:** Regulatory bodies require this. Patients trust this. It's a competitive moat. BKG didn't have this problem (construction licenses are simpler). HKG must build 3-point verification as a core feature, not optional.

**Action:** Model provider credentials with a "verification_sources" array. Each source has: source_name, date_verified, status (verified/pending/failed), expiration_date. The credential is "verified" only when all 3 sources confirm. Build a scheduler to re-verify quarterly. Display the verification sources prominently in Green (patient view).

---

### Medical Billing Codes (CPT, ICD-10, HCPCS) Are Living Standards
These codes update annually. The system must be designed to handle updates without downtime.

**Why:** Medical codes change every January. A system that hardcodes codes will break. OKG didn't face this (botanical data is stable). HKG must treat codes as mutable, versioned data.

**Action:** Store billing codes in Neo4j with version and effective_date. Build an import pipeline for annual updates (CMS publishes them). Test: can you swap the code set without restarting the system? Can you query claims by both old and new codes?

---

### Credentialing Verification Sources Vary by State
Architecture must be pluggable for state-specific rules.

**Why:** California has different requirements than Texas. Nursing is different from medicine. A hard-coded verification logic breaks when expanding to a new state. OKG handled regional plant variation; HKG must handle state variation.

**Action:** Model credentialing rules as data, not code. Create a "State Credentialing Rules" node in the graph: state, specialty, required_sources, renewal_frequency, required_training. Query this before verifying a credential. To add a new state: add a rule node, no code change needed.

---

### FDA Clinical Decision Support Rules Affect How AI Recommendations Are Framed
Recommendations must be framed as decision support (assisting human judgment), not medical advice.

**Why:** The FDA regulates clinical decision support software. If your system says "prescribe X," that's advice (regulated). If it says "research suggests X may help; discuss with your doctor," that's support (not regulated). The framing matters legally and clinically.

**Healthcare context:** HKG may include recommendation engines (e.g., suggesting treatments, flagging unusual patterns). Every recommendation must be framed carefully: "Evidence suggests..." not "You should..." Always defer to human judgment.

**Action:** Create a "recommendation_confidence" scoring system. Low confidence (< 70%): "consider researching..." Medium (70–85%): "evidence suggests..." High (> 85%): "research strongly indicates...". Train the team: recommendations are decision support, not directives.

---

### HL7 FHIR and X12 Standards for Healthcare Data Interoperability
Build to these standards from the start, not as an export option later.

**Why:** Healthcare data exchange increasingly requires FHIR (HL7 FHIR standard for clinical data) and X12 (EDI standard for claims). Systems that don't support these are siloed. OKG didn't face this (no external data exchange). HKG must.

**Action:** When designing the Neo4j schema, map it to FHIR resources (Patient, Practitioner, Organization, Claim, etc.). Build APIs that return FHIR-compliant JSON. For claims, support X12 837 format. Test interoperability: can an external system consume your FHIR export? Can you consume an X12 claim file and ingest it correctly?

---

### Trust Is the #1 Currency in Healthcare
Every pixel must reinforce trustworthiness.

**Why:** A patient trusts their provider based on credentials, ratings, and verification. A provider trusts a system based on security, accuracy, and regulatory compliance. One breach, one error, one unverified credential shown as verified—and trust is gone.

**Healthcare context:** BKG could recover from a data error (build back better). Healthcare cannot. A wrong address shown for a provider erodes trust. An unverified credential shown as verified is a legal liability. An unencrypted patient record is a HIPAA violation.

**Action:** Design for trust: show verification sources explicitly, display expiration dates prominently, log everything, encrypt everything, be transparent about data sources. In UI copy, use phrases like "verified by X source on X date" not "approved." Trust comes from transparency, not from hiding complexity.

---

## Anti-Patterns to Avoid

### Never Organize by Feature Catalog
Always organize by user identity + lifecycle phase + context.

**Why:** Organizing by features (e.g., "credentialing module," "billing module") creates silos. A patient's complete journey (verify provider → book appointment → receive care → pay bill) spans multiple "modules." Organizing by user identity + phase ensures the system serves complete user journeys.

**Action:** Structure the Knowledge Core by: Patient Identity → Care Pathway (discovery → verification → selection → engagement), Provider Identity → Credential Lifecycle (application → verification → practice → renewal → retirement). Features are woven across these structures, not separate buckets.

---

### Never Build Surfaces as Separate Apps
They share the Knowledge Core.

**Why:** BKG built Gold and Green as separate apps once. Data inconsistency followed. The rule: one Knowledge Core, three surfaces. Three apps are three problems.

**Action:** Enforce this in architecture review: surfaces are stateless, they query the same API, mutations go through the core. If someone proposes "a separate Green database," that's a blocker.

---

### Never Skip the Machine Lane
It's the data moat that makes the platform defensible.

**Why:** A system with only Gold/Green/Red is a tool. A system with a robust Machine Lane (APIs, data exports, webhooks, integrations) is a platform. The Machine Lane is where defensibility lives—customers build on top of you.

**Healthcare context:** Payers want to audit claims via API. Providers want to export their credential history. Patients want to port data to a new provider. The system that makes this easy is the system they choose.

**Action:** Treat Machine Lane as a first-class citizen. Design APIs alongside features. Publish API docs. Build webhooks for key events (credential verified, claim submitted, patient enrolled). This is not Phase 2.

---

### Never Hardcode Verification Sources
They change and vary by jurisdiction.

**Why:** A verification source (e.g., "Texas Medical Board") has a URL, API endpoint, or phone number. If you hardcode it, you're stuck when the source changes or when you expand to California. OKG avoided this by building pluggable data sources for plant care (regional plant databases). HKG must do the same.

**Action:** Model verification sources as data: source_name, jurisdiction, endpoint (HTTP or phone), last_updated. The verification logic queries this. To add California: add a source node, no code change.

---

### Never Build Compliance as a Separate Layer
It's woven into every model and API.

**Why:** Compliance built as an afterthought (e.g., "we'll add HIPAA checks in a middleware") leaks. The right model: every data access is compliant by design. Auth checks are on every API. Encryption is on every PHI field. Audit logs are everywhere.

**Healthcare context:** A "separate compliance layer" means you can bypass it. HIPAA compliance is not a feature—it's how the system is built.

**Action:** In code review: does every PHI access go through the auth layer? Is every PHI field encrypted? Is every API call logged? If the answer is "no," it's not compliant by design.

---

## Summary

The Knowledge Garden pattern works. BKG and OKG proved it. HKG will extend it with healthcare-specific rigor: HIPAA-first design, multi-source verification, standards-based interoperability, and trust-centric UX.

These lessons are lived experience. They're not "nice to have"—they're the difference between a tool that works and a platform that scales. Refer to them often. When you're tempted to take a shortcut (skip the spec, hardcode a rule, add a separate database), come back to these lessons. They exist because teams learned them the hard way.

Build it right the first time.

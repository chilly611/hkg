# tasks.todo.md — APR 30 ADDENDUM (Top of File)

> **How to use this file:** Insert this block at the **top** of your existing `tasks.todo.md`, above the "Phase 0" header. These are the items that surfaced from the homebase migration session and from looking at actual current state vs. plan.

---

## ⚡ ACTIVE NOW (Apr 30, 2026)

### Homebase migration cleanup
- [x] Migrate canonical strategy docs from cowork → claude.ai project knowledge
- [x] Write `HKG_PROJECT_INSTRUCTIONS_v2.md` (replaces v1)
- [x] Write `HKG_INDEX.md` (single entry point)
- [x] Write `HKG_PROJECT_MEMORY.md` (concise version for project settings)
- [ ] Merge `tasks_lessons_addendum.md` into `tasks.lessons.md` (top of file)
- [ ] Merge this block into `tasks.todo.md` (top of file)
- [ ] Save updated files back to local `~/Documents/Claude/Projects/Health Knowledge Garden/`
- [ ] Paste `HKG_PROJECT_MEMORY.md` content into claude.ai project custom instructions field
- [ ] Archive old `HKG_PROJECT_INSTRUCTIONS.md` (rename to `_v1_archived.md`)
- [ ] Clean up `scripts/ingestion/` — move stale NPI variants to `_archive/` (keep only canonical `ingest_npi_full.py`)
- [ ] Either populate or delete empty `memory/{context,people,projects}/` directories

### Status verification (confirm before next push)
- [ ] **NPI full load:** What's the current count? (Was 120K, target 9.4M, must run from local machine)
- [ ] **Neo4j:** Is the instance provisioned yet? (Was a Phase 0 prereq, status unknown)
- [ ] **DailyMed drug labels:** Current count vs 5,500 target?
- [ ] **SAM.gov API key:** Acquired or still using DEMO_KEY?
- [ ] **`llms.txt` content:** Last regenerated when? Confirm RSI heartbeat schedule.
- [ ] **Marker backend:** Sync with John — what's actually built behind the landing page?

### Marker integration into HKG architecture
- [ ] Decide: is Marker a sub-brand (`marker.theknowledgegardens.com`) or a feature within HKG Patient/Gold lane?
- [ ] If shared backend: design Marker biomarker tables for Supabase (or document why they should live separately)
- [ ] Map Marker's "50 curated biomarkers" to LOINC codes once LOINC ingestion is complete
- [ ] Add Marker's specialist referral network as data into Neo4j (or design plan for it)
- [ ] Define revenue split / equity structure with John (founder agreement)
- [ ] Plan Marker's data flow into Machine Lane (`llms.txt` for biomarker entity URLs)

### Investor outreach (active)
- [ ] Confirm what's currently the canonical pitch deck (`HKG_Investor_Briefing_Apr2026.docx` vs `HKG_Data_Ingestion_Story_Apr2026.pptx`)
- [ ] Pitch site (`progressreport.theknowledgegardens.com`) — list of investors who have viewed it
- [ ] Decide on Series Seed vs angel-led path; align targets with deck
- [ ] First 10-investor outreach list with personalized hooks per profile

### Live portal (`health.theknowledgegardens.com`) — keep momentum
- [ ] Confirm `index.html` deployed version matches local file (`vercel ls` + diff)
- [ ] Decide whether to fork the live portal into Marker landing (separate page or sub-route)
- [ ] Wire `llms.txt` regeneration into RSI heartbeat (currently appears manual)
- [ ] Add JSON-LD structured data to all entity URLs (in addition to `llms.txt`)

---

## 📋 STANDING DOCTRINE (DON'T LOSE TRACK)

These aren't tasks — they're principles to verify against before marking anything "done":

- Every entity URL should serve `llms.txt` + JSON-LD (the citation moat)
- Every notification ships with a pre-researched solution (Notification Orchestra)
- Every credential check uses 3-Point Verification (lit + guidelines + regulatory)
- Every API call respects HIPAA from day one (encryption, audit, RBAC, minimum-necessary)
- Every AI output framed as decision support, never advice (FDA CDS)
- Read `tasks.lessons.md` at session start (avoid repeating mistakes)

---

*(Existing Phase 0–6 plan continues below this section ↓)*

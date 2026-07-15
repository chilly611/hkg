# HKG INDEX — Single Entry Point for the Healthcare Knowledge Garden

> **Read this first.** This is the map. Everything else hangs off it.
> Last updated: Apr 30, 2026 · Migration from cowork → claude.ai homebase complete.

---

## 1. WHERE THINGS LIVE

### Source of truth
| What | Where | Status |
|---|---|---|
| **This project** (homebase) | claude.ai project files | **Current working environment** |
| **Local working directory** | `~/Documents/Claude/Projects/Health Knowledge Garden/` | Files mirror project knowledge |
| **Live portal source** | local `index.html` (142KB) | Deployed via Vercel |
| **Live portal URL** | https://health.theknowledgegardens.com | ✅ Deployed |
| **Investor pitch site** | local `hkg_pitch_v3.jsx` + Vite app | https://progressreport.theknowledgegardens.com |
| **Garden Wars (RPG tool)** | local `garden-wars/` | Separate Vercel deploy |
| **Marker landing** | local `marker-kg.html` (1,435 lines) | Status: page shipped, backend TBD |
| **Database** | Supabase project `opbrzaegvfyjpyyrmdfe` | 28 tables live, 725K+ records |
| **Vercel account** | `chillyd-2693s-projects` | Multiple deployments |
| **Domain** | `theknowledgegardens.com` (GoDaddy) | DNS via CNAME → Vercel |

---

## 2. READING ORDER FOR A NEW SESSION

If you (or a future Claude instance) are picking this project up cold, read in this order:

1. **`HKG_INDEX.md`** ← *you are here*
2. **`HKG_PROJECT_INSTRUCTIONS_v2.md`** — mission, architecture, current state, working agreements
3. **`tasks.lessons.md`** — what we've already learned the hard way (don't repeat)
4. **`tasks.todo.md`** — what's on deck
5. *(Then dive into a specific area as needed — see §3 below)*

---

## 3. FILES BY PURPOSE

### Strategy & narrative
| File | What it is |
|---|---|
| `HKG_PROJECT_INSTRUCTIONS_v2.md` | Canonical project instructions (mission, architecture, working agreements) |
| `Knowledge_Gardens_Strategic_Command_Center.md` | Cross-vertical (BKG/OKG/HKG) strategy doc |
| `Knowledge_Gardens_Investor_Pitch.md` | Investor-facing narrative |
| `KG_Strategic_Playbook.md` | Operating playbook for the Knowledge Gardens umbrella |
| `Revenue_Architecture_for_a_Healthcare_Knowledge_Graph_Platform...md` | Three-pillar revenue thesis (insurer compliance, consumer healthspan, clinical referral) |
| `Chilly_Dahlgren_Founder_Bio.md` | Founder bio for investor materials |
| `Healthcare_Operating_System.pdf` / `The_Healthcare_Operating_System.pdf` | The HKG strategic narrative document |

### Data architecture
| File | What it is |
|---|---|
| `HKG_Data_Architecture.md` | Full data architecture (51KB — the big one) |
| `HKG_Data_Architecture_EXECUTIVE_BRIEF.md` | TL;DR of the above |
| `HKG_Data_Architecture_INDEX.md` | Index into the architecture doc |
| `HKG_Technical_Implementation_Guide.md` | How to actually build it |
| `HKG_Paid_Data_Sources_Guide.md` | Map of paid vs free data sources |
| `supabase_schema.sql` | 28-table schema (source of truth for DB) |

### The two moats
| File | What it is |
|---|---|
| `HKG_AI_Citation_Strategy.md` | The `llms.txt` / JSON-LD / entity URL strategy (sleeper play) |
| `HKG_RSI_Heartbeat_System.md` | Recursive Self-Improvement system design |

### Code & deployment
| Path | What it is |
|---|---|
| `index.html` (local) | Live deployed Health portal — single static file |
| `dashboard.html` (local) | Internal dashboard prototype |
| `llms.txt`, `llms-full.txt` (local) | AI citation files — already deployed |
| `robots.txt` (local) | SEO/AI crawl config |
| `assets/` (local) | Logo PNGs (heart-hero, hex-logo, tree-hero, og-image) |
| `garden-wars/` (local) | "CEO Strategy RPG" — separate Vercel deploy with API function |
| `scripts/ingestion/` (local) | **31 Python ingestion scripts** (stdlib only) |
| `scripts/create_investor_doc.js` (local) | Investor doc generator |
| `hkg_pitch.jsx` / `hkg_pitch_v3.jsx` | Investor pitch site source |

### Marker (John's product)
| File | What it is |
|---|---|
| `marker-kg.html` | Marker landing page — 1,435 lines, fully designed |

### Operations
| File | What it is |
|---|---|
| `tasks.todo.md` | Living development plan (checkable items) |
| `tasks.lessons.md` | Accumulated lessons — **read at session start** |
| `MULTI_MACHINE_WORKFLOW.md` | How to work across machines/accounts |
| `HOSPITAL_INGESTION_STATUS.md` | Hospital data ingestion specific status |
| `HKG_Investor_Briefing_Apr2026.docx` | Latest investor briefing |
| `HKG_Data_Ingestion_Story_Apr2026.pptx` | Data ingestion narrative deck |
| `TKG_COMPLETE_DOCUMENTATION.md` | Cross-cutting "everything" doc (Apr 14) |

---

## 4. QUICK ANSWERS TO COMMON QUESTIONS

### "What's the current data state?"
→ See **§4 of `HKG_PROJECT_INSTRUCTIONS_v2.md`** or `tasks.todo.md` (status block at top)

### "How do I deploy a change to the live portal?"
→ Edit `index.html` locally, then `vercel --prod` from the project folder. The Vercel project is `chillyd-2693s-projects/app`.

### "Where's the codebase for the live site?"
→ It's not a Next.js app. The live site is **a single static `index.html` file** (142KB) deployed from `~/Documents/Claude/Projects/Health Knowledge Garden/`. There's no `package.json`, no build step. This is intentional — fast, simple, no dependencies to break.

### "How do I run an ingestion script?"
→ `cd scripts/ingestion/ && python3 ingest_*.py`. They're stdlib-only Python (zero deps). Connection details from `.env` (template in `.env.example`).

### "What's the next milestone?"
→ NPI full bulk load (9.4M providers). Must run from local machine — sandbox kills processes after ~30 min. See `tasks.lessons.md` "Long-Running Background Processes" lesson.

### "Where does Marker fit in?"
→ Patient/Gold lane. First premium consumer product in the gravity well. $99/yr starting tier. Direct competitor to Function Health with a "less is more" wedge (50 curated biomarkers vs Function's 160).

### "What's Garden Wars?"
→ A "CEO Strategy RPG" experiment — separate Vercel deploy with its own `api/research.js` function. Tangential to HKG core; flagged for awareness but not a priority.

---

## 5. STATUS FLAGS (CONFIRM AT SESSION START)

These are pieces of state that may have changed since the last session. Verify before relying on them.

- [ ] **NPI full load:** Was at 120K. Targeting 9.4M. Status?
- [ ] **DailyMed drug labels:** In progress, target 5,500. Status?
- [ ] **SAM.gov exclusions:** Needs registered API key. Acquired?
- [ ] **Marker backend:** John was developing. Status?
- [ ] **Neo4j:** Was not yet provisioned in Apr 9 plan. Provisioned?
- [ ] **`llms.txt` content:** Last regenerated when? (RSI heartbeat target.)
- [ ] **Investor outreach:** Pitch site is live; any meetings booked?

---

## 6. THE COWORK → CLAUDE.AI MIGRATION (APR 30, 2026)

**Why we migrated:** cowork was the build environment but produced files that needed manual sync. claude.ai project knowledge gives a single shared context across sessions and machines.

**What moved:** all markdown strategy docs, all `tasks.*` files, the live `index.html`, `llms.txt`/`llms-full.txt`/`robots.txt`, schema, and key logos.

**What stayed local:**
- Voice memo `.m4a` files (~70MB each)
- Midjourney logo concepts (PNG/MP4)
- The 110MB Claude conversation export
- `node_modules`, `.git`, `.env*`
- Ingestion scripts (live in `scripts/ingestion/` locally; documented here but not duplicated as source)

**What's next in the homebase:**
- Verify status flags (§5)
- Pick up wherever `tasks.todo.md` left off
- Begin slotting Marker properly into the Patient/Gold lane architecture

# tasks.lessons.md — ADDENDUM (Apr 30, 2026)

> **How to use this file:** These are NEW lessons to merge into your existing `tasks.lessons.md`. They came from the cowork → claude.ai homebase migration session and the discoveries it surfaced. Append to the top of the existing file, under a new section header dated Apr 30.

---

## Lessons from the Cowork → Claude.ai Homebase Migration (Apr 30, 2026)

### Project knowledge drifts when context lives in two places
The local `~/Documents/Claude/Projects/Health Knowledge Garden/` folder had Apr 12 versions of `tasks.todo.md`, `tasks.lessons.md`, and several strategy docs that never made it into the claude.ai project. Result: prompts were pulling from outdated state.

**Why:** cowork writes to disk; claude.ai project knowledge is a separate uploaded copy. They don't sync automatically. Every iteration in cowork creates drift.

**Action:** Choose one as canonical (now: claude.ai project knowledge). After every meaningful local edit, drag the updated file into project files within the same session. Conversely, when a Claude session updates project knowledge, save the file back to local disk via `present_files`. **Single homebase, bidirectional manual sync, no ambiguity.**

---

### `mdfind` + `npx vercel ls` is the fastest "where the hell is my codebase" recovery tool
When the live portal's source location was unknown, two commands resolved it in under 60 seconds:
- `mdfind -name "package.json" | xargs grep -l "<keyword>"` — finds every project mentioning a keyword
- `npx vercel ls` — lists every deployed project tied to your Vercel account

**Action:** When picking up an old project, run these *before* asking "where's the code?" — saves 20 minutes of navigating folders. Bonus: the `.vercel/project.json` inside any linked folder tells you exactly which Vercel project it deploys to.

---

### A "static HTML deployed via Vercel" stack is a feature, not a bug
The live `health.theknowledgegardens.com` is a single 142KB `index.html` file. No `package.json`, no React build, no `node_modules`, no dependencies to break. Deployment: drop the file, push to Vercel, done.

**Why this matters:** for a marketing/portal layer where the database is queried server-side (Supabase) or via Machine Lane API, a static frontend is *faster, cheaper, and more reliable* than a Next.js app. Don't add complexity until a feature actually requires it.

**Action:** Stay static for portal/landing pages. Reach for Next.js only when state/auth/SSR specifically demands it (e.g., the Doctor Lane app, the Admin Lane credentialing tool). Don't rebuild the live site as Next.js "for consistency" — that's fake elegance.

---

### Iteration history accumulates as filename suffixes — clean it up periodically
The `scripts/ingestion/` folder has 31 files including 7 NPI variants (`ingest_npi.py`, `_clean.py`, `_full.py`, `_from_csv.py`, `_stdin.py`, `_addr_tax.py`, `npi_backfill.py`), 3 Medicare variants, and 3 HCPCS variants. Each one was probably "the working one" at some point.

**Action:** When a script reaches "this is the canonical version" status, rename it to `ingest_<source>.py` and move the others to `scripts/ingestion/_archive/`. Future-you (or future-Claude) reading the folder shouldn't have to guess which file is current.

---

### Empty placeholder folders are confusing — either populate or delete
The `memory/` folder had subdirs `context/`, `people/`, `projects/` — all empty. Looked like a thoughtful memory system from outside; was actually an aspirational scaffold that never got filled.

**Action:** When setting up directory structure, populate at least one example file (or a `README.md` saying what goes here). Empty dirs read as "abandoned" — and in practice, often are.

---

### "John's biomarker app isn't built out yet" can be wrong by a full magnitude
Casual mental model said "Marker is a stub John might work on someday." Reality: Marker is a 1,435-line fully-designed landing page with three-tier pricing, testimonials, and clear positioning against Function Health. **The product strategy was further along than the founder realized.**

**Why this matters:** when partners are working in parallel, your model of their progress decays fast. Periodically *look at what's actually shipped* rather than relying on remembered conversation.

**Action:** Quarterly (or on partner check-ins): list every artifact each co-founder has produced. Compare to mental model. Update the strategy.

---

### Audio/video assets bloat project folders without contributing to context
The local Health Knowledge Garden folder is ~600MB. Of that, ~70MB is `.m4a` voice memos, and ~80MB is Midjourney logo concept PNGs/MP4s. These are not useful to upload to project knowledge — claude.ai can't transcribe `.m4a` from project files, and PNG context bloats token budgets without proportionate value.

**Action:** When migrating to a new homebase, **upload only what claude.ai can read and reason over**: markdown, code, configs, structured docs. Keep media local; reference it with paths if relevant. If you need a voice memo transcribed, do it in a one-off conversation and add the transcript as a markdown file.

---

### Garden Wars exists. Acknowledge tangential projects, don't bury them.
A "CEO Strategy RPG" tool (`garden-wars/`) was sitting in the Health Knowledge Garden folder with its own `api/` and `vercel.json`. It's a separate deploy, tangential to HKG core. The first instinct was to ignore it; that creates the same drift problem we just solved.

**Action:** Catalog every deployable artifact in the project, even tangents. One sentence in `HKG_INDEX.md` is enough — but it has to exist. Otherwise, six months later, no one remembers what it was or whether it should still be running.

---

### When a session starts with "import everything," don't import everything
The instinct was to drag the entire 600MB folder into project knowledge. The right move: identify what's authoritative vs. what's redundant/old/binary, upload only the high-signal subset. Same applies for Drive/file imports in any project — claude.ai context is precious; don't fill it with noise.

**Action:** Before any bulk import, do an `ls -la` and triage: (1) markdown/code/configs → upload, (2) duplicates of files already in project → skip, (3) media/audio/video → keep local, (4) zips → expand and upload contents (claude.ai can't read zips), (5) `.git`/`node_modules`/`.env*` → never upload.

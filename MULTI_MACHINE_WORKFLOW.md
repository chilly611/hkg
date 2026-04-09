# HKG Multi-Machine Workflow Guide

## The Strategy: GitHub Repo + Cloud Database = Work Anywhere

Your database is already in the cloud (Supabase). Your project brain needs to be too. Here's the setup:

### Step 1: Create a GitHub Repo

```bash
cd "Health Knowledge Garden"
git init
git add CLAUDE.md tasks.todo.md tasks.lessons.md supabase_schema.sql
git add scripts/ .env.example
git add HKG_*.md dashboard.html
echo ".env" >> .gitignore
echo "*.m4a" >> .gitignore
echo "*.pdf" >> .gitignore
echo "__pycache__/" >> .gitignore
git add .gitignore
git commit -m "Initial: schema, ingestion scripts, project brain"
gh repo create xrworkers/hkg --private --push
```

### Step 2: Clone on Each Machine

```bash
git clone git@github.com:xrworkers/hkg.git
cp .env.example .env  # fill in real keys
```

### Step 3: Keep in Sync

```bash
git pull            # before starting work
git add . && git commit -m "session update"
git push            # when done
```

---

## What Goes Where

### In the Repo (travels with you)
- `CLAUDE.md` — Project brain. Claude Code reads this automatically from repo root.
- `tasks.todo.md` — Living task list
- `tasks.lessons.md` — Accumulated lessons (prevents repeating mistakes)
- `supabase_schema.sql` — Schema source of truth
- `scripts/ingestion/` — All 21 ingestion scripts
- `HKG_*.md` — Architecture docs, data strategy, implementation guides
- `.env.example` — Credential template (no secrets)
- `dashboard.html` — Live dashboard

### NOT in the Repo (too large or sensitive)
- `.env` — Real Supabase keys (gitignored)
- PDFs (pitch deck) — Keep in Google Drive or local
- Audio files — Keep local
- Raw data files (NPI zip, CSVs) — Re-downloadable from CMS/NLM

### In Supabase (already cloud-portable)
- 725K+ records across 17 tables
- All functions (reconcile_oig_exclusions, search_providers, etc.)
- RLS policies, indexes, triggers
- Accessible from ANY machine with the service_role key

---

## Model Strategy: Opus vs Sonnet

### You Do NOT Have to Use Sonnet

| Environment | Available Models | Best For |
|---|---|---|
| **Cowork (Desktop App)** | Opus, Sonnet | Architecture planning, complex multi-step tasks, document creation |
| **Claude Code (Terminal)** | `claude --model opus` or `claude --model sonnet` | Coding, git operations, running scripts, file edits |
| **claude.ai (Web/Mobile)** | Opus, Sonnet | Quick questions, reviewing docs, strategy |

**Recommendation for MTP velocity:**
- **Opus** for architecture decisions, complex data pipelines, planning sessions
- **Sonnet** for routine coding tasks, file edits, running scripts (faster, still very capable)
- Use `claude --model opus` in Claude Code when you need the heavy thinking

### Different Accounts

If using a second Anthropic account:
- Both accounts can use the same GitHub repo (it's just git)
- Both can hit the same Supabase project (it's just an API key in .env)
- CLAUDE.md in the repo root means both accounts get full project context
- The only thing that doesn't transfer is Cowork's `.auto-memory/` — but everything important is already captured in CLAUDE.md and tasks.lessons.md

---

## Workflow Per Session

### Starting Work (Any Machine)

```bash
cd hkg
git pull                          # get latest from other machines
claude --model opus               # or sonnet for quick tasks
```

Claude Code reads CLAUDE.md automatically. You're up to speed instantly.

### Starting Work in Cowork

1. Select the `hkg` folder as your workspace
2. Cowork reads CLAUDE.md automatically
3. Full project context is loaded

### Ending a Session

```bash
git add -A && git commit -m "session: [what you did]"
git push
```

---

## Critical Files Checklist

Before working on a new machine, verify:

- [ ] Repo cloned and up to date (`git pull`)
- [ ] `.env` file created with Supabase keys
- [ ] Python 3 available (`python3 --version`)
- [ ] Can reach Supabase (`curl https://opbrzaegvfyjpyyrmdfe.supabase.co/rest/v1/ -H "apikey: YOUR_KEY"`)

---

## Remaining Ingestion: Run on Local Machine

The NPI full bulk load (9.4M records) keeps dying in the Cowork sandbox (~30min process limit). Run this from your local machine:

```bash
cd hkg/scripts/ingestion

# Download NPI full dissemination (1.1 GB)
curl -o /tmp/npi_full.zip "https://download.cms.gov/nppes/NPPES_Data_Dissemination_March_2026.zip"

# Run the bulk load (takes ~90 minutes)
unzip -p /tmp/npi_full.zip "npidata_pfile_*.csv" | python3 ingest_npi_stdin.py

# Then run addresses + taxonomies
unzip -p /tmp/npi_full.zip "npidata_pfile_*.csv" | python3 ingest_npi_addr_tax.py

# Then reconcile OIG exclusions (via Supabase SQL Editor or script)
```

The DailyMed label fetch (5,500 labels) also benefits from local execution due to the sequential API calls taking ~20 minutes.

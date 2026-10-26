# Toxicology Knowledge Garden (TKG) — Complete Project Documentation

> **Last Updated:** April 2026  
> **Status:** Production — Live at [toxicology.theknowledgegardens.com](https://toxicology.theknowledgegardens.com)  
> **Owner:** Chilly (The Knowledge Gardens)  
> **Technical Role:** Claude (CTO/Collaborator)  
> **Domain Expert:** Dr. James Dahlgren, M.D. (Envirotoxicology / James Dahlgren Medical)

---

## Table of Contents

1. [Project Vision](#1-project-vision)
2. [Architecture Overview](#2-architecture-overview)
3. [Database Schema](#3-database-schema)
4. [Data Sources & Enrichment](#4-data-sources--enrichment)
5. [Search Infrastructure](#5-search-infrastructure)
6. [MCP Server & AI Layer](#6-mcp-server--ai-layer)
7. [REST API & OpenAPI](#7-rest-api--openapi)
8. [Next.js Website](#8-nextjs-website)
9. [Case Management System](#9-case-management-system)
10. [Sky Valley PCB Case](#10-sky-valley-pcb-case)
11. [CI/CD & Infrastructure](#11-cicd--infrastructure)
12. [Interface Design Vision](#12-interface-design-vision)
13. [Target Audiences](#13-target-audiences)
14. [Build History (8 Chunks)](#14-build-history-8-chunks)
15. [Key Identifiers & Credentials](#15-key-identifiers--credentials)
16. [What's Next](#16-whats-next)

---

## 1. Project Vision

The Toxicology Knowledge Garden is a **multi-audience, production-grade toxicological knowledge platform** built as part of The Knowledge Gardens — a broader multi-domain educational product suite. The TKG is intentionally maintained as a **separate codebase and product** from the Orchid Knowledge Garden.

### Core Purpose
- Aggregate, normalize, enrich, and expose curated toxicological data to humans and machines
- Serve as the foundational layer for all future toxicology-adjacent work: legal AI, health AI, brand certification, regulatory research
- Be natively discoverable by AI agents, LLMs, and emerging autonomous systems — not just human users

### Design Philosophy
The TKG is built to be:
- **AI-first**: Every entity maps to a structured API endpoint. Machines consume the same relational graph as JSON-LD
- **Multi-audience without silos**: Same data, different gravitational pull — audience "lenses" re-weight rather than hide information
- **Foundational**: Schema and architecture decisions made to support 10+ future use cases, not just one
- **Production-grade from day one**: Real deployment, real domain, real CI/CD — not a demo

---

## 2. Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    PUBLIC INTERFACE                       │
│        toxicology.theknowledgegardens.com                │
│           Next.js 16 · SSG · 354 pages                  │
│              Vercel · GoDaddy DNS                        │
└─────────────────────────┬───────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────┐
│                   API LAYER                              │
│  PostgREST (auto-REST) · Supabase Edge Functions        │
│  OpenAPI 3.0 spec · 8 custom RPC search functions       │
│  JSON-LD on all substance pages · robots.txt + sitemap  │
└─────────────────────────┬───────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────┐
│                 SUPABASE POSTGRESQL                      │
│  329 substances · 12 normalized tables                   │
│  90% PubChem-enriched · 5,947 aliases                   │
│  Hybrid FTS + fuzzy + alias + CAS search                 │
│  pgvector ready · RLS enabled · tsvector triggers       │
│  6 case management tables (added Session 13)             │
└─────────────────────────┬───────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────┐
│              AI AGENT / MCP LAYER                        │
│  Node.js MCP Server · 7 registered tools                │
│  Registered in Claude Desktop config                    │
│  GitHub Actions CI/CD · Docker container ready          │
└─────────────────────────────────────────────────────────┘
```

### Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 16, React, Tailwind CSS |
| Hosting | Vercel (SSG + serverless) |
| DNS | GoDaddy CNAME → cname.vercel-dns.com |
| Database | Supabase (PostgreSQL 15) |
| Search | Postgres tsvector, pg_trgm (fuzzy), custom RPC functions |
| Embeddings | pgvector (column exists, embeddings deferred) |
| MCP Server | Node.js, TypeScript |
| CI/CD | GitHub Actions |
| Repo | github.com/chilly611/knowledge-gardens-toxicology |
| Local | Windows, `C:\Users\kmacn\Desktop\TheKnowledgeGardens\toxicology-db\` |

---

## 3. Database Schema

### Core Substance Tables (12 tables)

#### `substances` — Master table
```sql
id             uuid PRIMARY KEY
name           text UNIQUE NOT NULL
cas_number     text UNIQUE          -- e.g. "123-91-1" for 1,4-Dioxane
iupac_name     text
molecular_formula text
molecular_weight  numeric
smiles         text                 -- chemical structure notation
inchi_key      text                 -- standard chemical identifier
pubchem_cid    integer              -- PubChem compound ID
description    text
search_vector  tsvector             -- auto-updated via trigger
embedding      vector(1536)         -- pgvector (deferred)
created_at     timestamptz
updated_at     timestamptz
```

#### `substance_aliases` — Alternative names
```sql
substance_id   uuid FK → substances
alias          text
alias_type     enum('common','trade','iupac','synonym','abbreviation')
```

#### `classifications` — Hierarchical classification system
```sql
id             uuid PRIMARY KEY
name           text
parent_id      uuid (self-referential)
type           enum('chemical_class','use_category','regulatory_category')
-- Examples: "PFAS", "VOC", "Pesticide", "Heavy Metal", "DBP"
```

#### `substance_classifications` — M2M join
```sql
substance_id   uuid FK → substances
classification_id uuid FK → classifications
```

#### `health_effects` — Normalized health effect categories
```sql
id             uuid PRIMARY KEY
name           text
description    text
icd_code       text
-- Examples: "Cancer", "Liver damage", "Endocrine disruption"
```

#### `substance_health_effects` — M2M with evidence quality
```sql
substance_id   uuid FK
health_effect_id uuid FK
evidence_level enum('known','probable','possible','inadequate')
evidence_source text
notes          text
```

#### `regulatory_limits` — Agency safety limits
```sql
substance_id   uuid FK
agency         enum('EPA','WHO','EWG','EU','CalEPA','state')
limit_type     enum('MCL','MCLG','guideline','advisory','action_level')
limit_value    numeric
limit_unit     text                 -- ppb, ppm, mg/L, μg/L
effective_date date
source_url     text
notes          text
```

#### `exposure_routes`
```sql
id   uuid
name enum('drinking_water','air','food','dermal','occupational')
```

#### `substance_exposures` — M2M
```sql
substance_id    uuid FK
exposure_route_id uuid FK
description     text
```

#### `water_data` — EWG tap water detection data
```sql
substance_id       uuid FK
states_detected    integer
states_tested      integer
systems_detected   integer
people_affected    bigint
detection_period   text             -- e.g. "2013-2023"
source             text             -- 'ewg_tapwater'
scraped_at         timestamptz
```

#### `source_documents` — Provenance tracking
```sql
id              uuid
source_name     text                -- 'EWG', 'PubChem', 'EPA IRIS', 'ATSDR'
source_url      text
document_type   text
content_text    text                -- full text for RAG/embeddings
content_embedding vector(1536)
fetched_at      timestamptz
```

#### `substance_sources` — M2M linking substances to data sources
```sql
substance_id       uuid FK
source_document_id uuid FK
data_extracted     jsonb
```

### Convenience View
`substance_full` — joins all tables for single-query access to complete substance profiles

### Seed Data
| Table | Rows | Examples |
|-------|------|---------|
| classifications | 12 | PFAS, VOC, Heavy Metal, Pesticide, DBP |
| health_effects | 18 | Cancer, Liver Damage, Endocrine Disruption, Neurotoxicity |
| exposure_routes | 6 | drinking_water, air, food, dermal, occupational, inhalation |

---

## 4. Data Sources & Enrichment

### Primary Data Sources

| Source | Data Type | Status |
|--------|-----------|--------|
| EWG Tap Water Database | 329 substances, water detection data, regulatory limits | ✅ Fully ingested |
| PubChem API | CAS numbers, SMILES, InChI keys, molecular weight, synonyms | ✅ 90% enriched (297/329 substances) |
| EPA IRIS | Toxicity assessments | Planned |
| ATSDR | Minimum Risk Levels | Planned |
| WHO IARC | Carcinogen classifications | Planned |

### PubChem Enrichment (Chunk 2)
- **Script:** Node.js enrichment script querying PubChem API by substance name
- **Results:** 5,947 aliases ingested across 297 substances
- **Data added per substance:** CAS number, SMILES, InChI key, molecular weight, PubChem CID, IUPAC name, all synonyms
- **Known limitation:** EWG boolean classification flags were noisy (e.g. Arsenic wrongly tagged as PFAS) — PubChem data corrects this

### Substances by Classification (12 seed classifications)
PFAS · VOC · Heavy Metal · Pesticide · Disinfection Byproduct (DBP) · Pharmaceutical · Nitrate · Microorganism · Radionuclide · Industrial Chemical · Natural Toxin · Emerging Contaminant

---

## 5. Search Infrastructure

### 8 RPC Functions
All deployed as Postgres functions callable via Supabase JS client and REST API:

| Function | Description |
|----------|------------|
| `search_substances_hybrid` | Cascading search: FTS → CAS → alias → fuzzy. Returns name, cas_number, description, match_type, score |
| `search_by_cas` | Exact CAS number lookup |
| `search_by_alias` | Trade name / synonym search |
| `search_by_health_effect` | Find substances by health outcome |
| `search_by_classification` | Filter by chemical class |
| `get_substance_full` | Complete substance profile in one call |
| `get_water_stats` | Top substances by people affected |
| `get_regulatory_limits` | Limits for a substance across all agencies |

### Search Architecture
- **Weighted FTS:** `search_vector` tsvector column auto-updated by trigger on insert/update
  - Name: Weight A · Aliases: Weight B · Description: Weight C · Content: Weight D
- **Fuzzy matching:** `pg_trgm` extension for misspelling tolerance
- **Alias search:** Direct lookup in `substance_aliases` table
- **CAS exact:** Indexed CAS number lookup
- **Cascade:** FTS first, then CAS, then alias, then fuzzy — returns best match with match_type label

### Full-Text Search Index
```sql
CREATE INDEX substances_search_idx ON substances USING GIN(search_vector);
```

### Vector Embeddings (Deferred)
- `embedding vector(1536)` column exists on `substances`
- `content_embedding vector(1536)` on `source_documents`
- Ready for: OpenAI text-embedding-3-small or Anthropic equivalent
- Will enable: "What chemicals cause liver damage?" → semantic similarity search

---

## 6. MCP Server & AI Layer

### MCP Server
- **Location:** `toxicology-db/mcp-server/src/index.ts`
- **Build:** `toxicology-db/mcp-server/build/index.js` (compiled TypeScript)
- **Registration:** `%APPDATA%\Claude\claude_desktop_config.json`
- **CI:** GitHub Actions Dockerfile compiles TypeScript on build

### 7 MCP Tools

| Tool | Description |
|------|------------|
| `search_substances` | Keyword search across names, CAS, trade names, fuzzy matches |
| `get_substance_details` | Full profile: chemistry, health effects, regulatory limits, water data, aliases |
| `find_by_health_effect` | Returns all substances linked to a given health outcome |
| `compare_substances` | Side-by-side comparison of two substances |
| `get_water_stats` | Top substances by people affected in tap water |
| `get_regulatory_limits` | All agency limits (EPA, EWG, WHO) for a substance |
| `list_health_effects` | All 18 health effects with substance counts |

### Claude Desktop Config
```json
{
  "mcpServers": {
    "toxicology": {
      "command": "node",
      "args": ["C:\\Users\\kmacn\\Desktop\\TheKnowledgeGardens\\toxicology-db\\mcp-server\\build\\index.js"],
      "env": {
        "SUPABASE_URL": "https://vlezoyalutexenbnzzui.supabase.co",
        "SUPABASE_ANON_KEY": "[anon key]"
      }
    }
  }
}
```

### JSON-LD / Schema.org Layer
- Every substance page emits `schema.org/ChemicalSubstance` JSON-LD
- Health effects emit `schema.org/MedicalCondition` links
- Google Knowledge Panel compatible
- LLM web-crawl friendly

### robots.txt
```
Allow: GPTBot, ClaudeBot, Googlebot-Extended
Sitemap: /sitemap.xml
```

---

## 7. REST API & OpenAPI

- **Auto-generated REST:** PostgREST via Supabase (all tables + views queryable)
- **Custom endpoints:** Supabase Edge Functions for complex queries
- **OpenAPI 3.0 spec:** Auto-generated, exposed via Supabase dashboard
- **Documentation:** Redoc UI
- **RLS Policies:** Public read enabled on all core tables; write requires service role

---

## 8. Next.js Website

### Live Site
**URL:** https://toxicology.theknowledgegardens.com  
**Platform:** Next.js 16.1.6 on Vercel (SSG)  
**Pages:** 354 statically generated

### Route Map

| Route | Type | Description |
|-------|------|-------------|
| `/` | Static | Hero ("What's in Your Water?"), search bar, stats bar, featured contaminants, category chips |
| `/substances` | Dynamic (SSR) | Browse all 329 + hybrid search (name/CAS/trade name/fuzzy) + classification filter chips |
| `/substances/[slug]` | SSG × 329 | 4-tab detail experience |
| `/health-effects` | Static | 18 health effects ranked by linked substance count |
| `/health-effects/[slug]` | SSG × 18 | Substances grouped by evidence level |
| `/about` | Static | Data sources, methodology, disclaimers |

### Substance Detail Page (4 Tabs)

1. **Overview** — Water detection gauges (states affected, people affected, systems), key stats, aliases, PubChem link
2. **Chemistry** — Molecular formula, SMILES, InChI key, molecular weight, 3D structure link
3. **Health Effects** — Interactive Health Ring SVG, evidence-level badges (known/probable/possible), linked outcomes
4. **Regulations** — Agency comparison table (EPA MCL, EPA MCLG, EWG guideline, WHO) with unit normalization

### Design System
- **Typography:** Cormorant Garamond (display) + Space Mono (code/data)
- **Palette:** Teal (#1a7a7a) · Gold (#b8860b) · Parchment (#f4f0e8) · Ink (#1a1a1a) · Steel (#4a5568)
- **Aesthetic:** Victorian engineering meets analytical chemistry — brass instruments, parchment textures, gear elements

### Infrastructure Details
- **Build command:** `npx next build` (from `toxicology-db/website/`)
- **Env vars:** `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY` (set in Vercel dashboard)
- **DNS:** GoDaddy CNAME `toxicology` → `cname.vercel-dns.com` (NOT an A record)
- **SSL:** Auto-provisioned by Vercel
- **Vercel project ID:** chillyd-2693s-projects/website

---

## 9. Case Management System

### Schema (6 new tables — Migration 002)

#### `experts`
```sql
id             uuid PRIMARY KEY
name           text NOT NULL
credentials    text[]              -- ['M.D.', 'Ph.D.']
specialty      text
organization   text
contact_email  text
bio            text
created_at     timestamptz
```

#### `cases`
```sql
id             uuid PRIMARY KEY
name           text NOT NULL
case_number    text
case_type      enum case_type       -- toxic_tort, environmental, product_liability, etc.
status         enum case_status     -- intake, active, discovery, trial_prep, trial, settlement, closed, appeal
jurisdiction   text
court          text
filing_date    date
description    text
notes          text
created_at     timestamptz
updated_at     timestamptz
```

#### `case_parties`
```sql
id             uuid PRIMARY KEY
case_id        uuid FK → cases
party_name     text
role           enum party_role     -- plaintiff, defendant, expert_plaintiff, expert_defense, counsel_plaintiff, etc.
organization   text
notes          text
```

#### `case_documents`
```sql
id             uuid PRIMARY KEY
case_id        uuid FK → cases
title          text
category       enum document_category  -- medical_records, expert_reports, depositions, motions, etc.
file_url       text                -- Google Drive URL
drive_file_id  text                -- Google Drive file/folder ID
document_date  date
description    text
notes          text
```

#### `case_substances`
```sql
id             uuid PRIMARY KEY
case_id        uuid FK → cases
substance_id   uuid FK → substances
role           text                -- 'primary_toxicant', 'related_compound', etc.
exposure_route text
notes          text
```

#### `case_events`
```sql
id             uuid PRIMARY KEY
case_id        uuid FK → cases
event_date     date
event_type     text
description    text
notes          text
```

### Enum Types (4)
```sql
CREATE TYPE case_type AS ENUM (
  'toxic_tort','environmental','product_liability',
  'occupational','class_action','mdi','other'
);
CREATE TYPE case_status AS ENUM (
  'intake','active','discovery','trial_prep',
  'trial','settlement','closed','appeal'
);
CREATE TYPE party_role AS ENUM (
  'plaintiff','defendant','expert_plaintiff','expert_defense',
  'counsel_plaintiff','counsel_defense','judge','mediator'
);
CREATE TYPE document_category AS ENUM (
  'medical_records','expert_reports','depositions','motions',
  'correspondence','evidence','trial_docs','administrative','research','other'
);
```

---

## 10. Sky Valley PCB Case

**Case Name:** Erickson v. Monsanto (Sky Valley PCB Case)  
**Type:** Toxic Tort  
**Status:** Active  
**Source Documents:** Google Drive — `JDM Toxicology Data 2026 > Sky Valley PCB Case`  
**Drive Folder ID:** `1I0iDhmvltPKeA52LaQI6YO8BZEP1XbYK`

### Key UUIDs
| Entity | UUID |
|--------|------|
| Case (Sky Valley PCB Case) | `55021415-8769-4abe-93ba-5b0887110b74` |
| Expert (Dr. James Dahlgren) | `3e5b00a1-0756-4065-9738-407444514106` |

### Seeded Data

| Entity | Count | Details |
|--------|-------|---------|
| Experts | 1 | Dr. James Dahlgren M.D. (Envirotoxicology, James Dahlgren Medical) |
| Cases | 1 | Erickson v. Monsanto |
| Parties | 5 | Plaintiff, defendant (Monsanto), expert (Dr. Dahlgren), plaintiff counsel, defense counsel |
| Documents | 84 | 82 folders + 2 files cataloged from Google Drive |
| Substances | 2 | PCBs (primary_toxicant), Dioxin (related_compound) |
| Events | 12 | Timeline 2016–2024 |

### Case Timeline (12 Events)
Spans 2016–2024 covering discovery, depositions, expert reports, trial prep milestones.

### Documents Cataloged (84 entries)
Source: Google Drive folder `JDM Toxicology Data 2026 > Sky Valley PCB Case`  
Categories covered: medical records, expert reports, depositions, motions, correspondence, evidence, research

---

## 11. CI/CD & Infrastructure

### GitHub Repository
**URL:** https://github.com/chilly611/knowledge-gardens-toxicology  
**Visibility:** Public  
**Default branch:** main

### GitHub Actions
```yaml
# CI passes green (Run #4) — "Fix Dockerfile: compile TypeScript"
# Secrets configured: SUPABASE_URL, SUPABASE_ANON_KEY
# Dockerfile compiles TypeScript itself (no pre-built artifact needed)
```

CI history:
- Run #1 & #2: Failed (Docker COPY .env issue, missing build/ directory)
- Run #3: Failed (intermediate fix)
- **Run #4: ✅ PASSING** (Dockerfile compiles TypeScript on build — 25 seconds)

### File Sync Pattern
Files synced to both:
1. `C:\Users\kmacn\Desktop\TheKnowledgeGardens\toxicology-db\` (project root)
2. `C:\Users\kmacn\Desktop\TheKnowledgeGardens\KG from Claude\` (backup copy)

Then committed and pushed to GitHub at session end.

### Project Files
```
toxicology-db/
├── TOXICOLOGY_DB_PROJECT.md       # canonical project state (load every session)
├── PROJECT_STATE.md               # design vision + session log
├── website/                       # Next.js app
│   ├── src/app/                  # pages
│   │   ├── page.tsx              # home
│   │   ├── substances/           # browse + [slug]
│   │   ├── health-effects/       # index + [slug]
│   │   └── about/
│   ├── src/lib/supabase.ts       # DB client + query functions
│   └── .env.local                # NEXT_PUBLIC_SUPABASE_URL, NEXT_PUBLIC_SUPABASE_ANON_KEY
├── mcp-server/
│   ├── src/index.ts              # 7 MCP tools
│   ├── build/index.js            # compiled
│   └── test-mcp-full.cjs         # 9-test integration suite
├── migrations/
│   ├── 001_schema.sql            # core 12 tables
│   ├── 002_case_management.sql   # 6 case tables + 4 enums
│   └── 003_fix_hybrid.sql        # search_substances_hybrid fix
└── scripts/
    ├── enrich-pubchem.js         # PubChem enrichment
    └── etl-ewg.js                # EWG → normalized schema
```

### Vercel Deployment
```bash
# Deploy command (from website/ directory)
vercel --yes --prod

# Env vars set in Vercel dashboard:
# NEXT_PUBLIC_SUPABASE_URL
# NEXT_PUBLIC_SUPABASE_ANON_KEY
```

### Supabase Details
- **Project URL:** https://vlezoyalutexenbnzzui.supabase.co
- **Creds location:** `C:\Users\kmacn\Desktop\TheKnowledgeGardens\ewg-data\.env`
- **DDL method:** Must use Supabase SQL Editor (browser) — JS client cannot execute raw DDL
- **RLS:** Enabled on all tables; public read via anon key

---

## 12. Interface Design Vision

### Three Candidate Concepts (All Fully Prototyped as HTML Artifacts)

Each concept has been built as a shareable, interactive HTML mockup with role-selection entry screens and differentiated content for Consumer, Doctor, and Lawyer paths.

---

### Concept 1: "The Stratigraph"
**Metaphor:** Depth-as-navigation — geological and biological cross-section

The site is a single continuous vertical column — like boring a core sample through the earth. Scroll navigates you through strata from world-scale to molecular-scale.

**Three layers:**
- **Surface layer** (world-scale): News, cases, brand certifications, regulatory events
- **Tissue layer** (body-scale): Health pathways, supply chains, exposure routes, bioaccumulation
- **Molecular layer** (substance-scale): Chemical data, regulatory limits, structure, properties

**Mechanical elements:** Brass depth gauge on the right rail. Tick marks for each stratum. A split-core macro/micro view that shows both scales simultaneously. Audience role as a physical dial that re-weights content without changing structure.

**Why it works:** Most intuitive for "zoom in / zoom out" users. Maps naturally to the existing data hierarchy (world → system → molecule). Mechanical-organic fusion lives in transition animations between layers.

---

### Concept 2: "The Loom"
**Metaphor:** Knowledge as woven textile

Substances are **warp threads** (vertical), audience contexts (legal, health, brand, student) are **weft** (horizontal). Navigation is the act of weaving — a shuttle drags context across data, materializing fabric at each intersection.

**Interaction model:**
- Shuttle control at top of screen; drag to weave a context thread across substance columns
- Detail cards emerge by pressing into the cloth at an intersection
- Thread irregularity, dye bleed, and imperfect selvedge create tactile imperfection
- Different weaving contexts produce completely different fabric patterns per role

**Why it works:** Most philosophically radical — the user's inquiry is the creative act. Directly resonates with luxury natural fiber / natural dye audience (the textile metaphor is structural, not decorative). No one has built a data platform as a weaving machine.

---

### Concept 3: "The Tidepool"
**Metaphor:** Living bioluminescent ecosystem

All data entities exist as organisms in a shared tidepool. Substances drift like jellyfish. Cases sit like sea urchins on the substrate. Brands float like nautilus shells. A brass/mechanical data substrate is visible beneath the water.

**Layers:**
- **Water surface:** Drifting bioluminescent organisms (data entities)
- **Mechanical substrate:** Brass-traced data relationships, precision instrument readouts
- **AI agent depth:** A third sublayer beneath the mechanical — the machine-readable graph

**Dynamic environment:**
- Scroll changes tide level (low tide exposes substrate data, high tide reveals connections between entities)
- Data updates propagate as ripples through the water
- Ecosystem has weather: regulatory news creates storm patterns, new cases shift organism clustering
- Each role sees a completely different ecosystem population

**Consumer pool:** BPA, formaldehyde, mercury in fish — household substances with friendly actions  
**Doctor pool:** Hepatotoxicity pathways, chelation nodes, ATSDR profiles, metabolic connections  
**Lawyer pool:** Sky Valley case diamond radiating connections to PCBs, Dioxin, Monsanto, Dr. Dahlgren — surrounded by precedent libraries and causation timeline builders

**Why it works:** Highest "never seen before" factor. Best fit for AI agents as first-class citizens (ecosystem already includes non-human participants). Most evocative aesthetically.

---

### Shared Design Principles (All Three Concepts)

- **Tech-mechanical fused with organic:** Brass, copper, precision instruments coexisting with biological forms, fluid dynamics, growth patterns
- **Macro beside micro:** Cityscape ↔ molecular structure visible simultaneously
- **Morphing scroll transitions:** Elements transform rather than fade — a news card peels open to reveal biology beneath
- **Touch of the imperfect:** Thread irregularities, patina accumulation, slight asymmetry — nothing pixel-perfect
- **Animation with mass:** Organic = fluid/growth (slow, asymmetric); Mechanical = precision instruments (linear with overshoot/settle)
- **API-first for machines:** Every visual entity maps 1:1 to a structured API endpoint; AI agents consume JSON-LD

### Technical Implementation (All Three)

- **Rendering:** WebGL / Three.js for heavy visual (fluid, fabric, parallax), CSS transform fallback
- **Real-time:** Supabase real-time subscriptions drive visual phenomena (ripples, new threads, emerging strata)
- **Progressive hydration:** Fast skeleton + ambient animation; data elements hydrate progressively
- **Accessibility:** High-contrast vector mode, screen reader parity with AI agent JSON-LD, reduced-motion preserves spatial relationships
- **Mobile:** Stratigraph → swipeable layer stack; Loom → horizontal scroll weave; Tidepool → luminous touch grid

---

## 13. Target Audiences

| Audience | Use Case | Data Focus |
|----------|----------|-----------|
| **Luxury brands** | Non-toxic / natural material certification, supply chain verification | Substance classifications, regulatory limits, OEKO-TEX-type data |
| **Health & longevity professionals** | Patient exposure counseling, treatment context, biomarker interpretation | Health effects, evidence levels, exposure routes, ATSDR profiles |
| **AI agent workers / health AI** | Tool-based queries, RAG retrieval, automated research | MCP tools, JSON-LD, structured API endpoints |
| **Legal professionals** | Toxic tort case support, causation evidence, expert witness data | Case management, substance-to-case links, expert profiles, document catalog |
| **Autonomous legal agents** | Case research automation, precedent matching, document analysis | Case management API, substance-case linkage, timeline data |
| **Students** | Environmental science, public health, toxicology coursework | Educational summaries, health effect explanations, water data |
| **Any org or machine** | Curated toxicological knowledge access | Full REST API, MCP tools, OpenAPI spec |

---

## 14. Build History (8 Chunks)

All 8 chunks complete. Executed across ~13 sessions.

| Chunk | Name | Status | Key Deliverable |
|-------|------|--------|----------------|
| 1 | Schema Foundation | ✅ Complete | 12 normalized Postgres tables + ETL from EWG flat data |
| 2 | PubChem Enrichment | ✅ Complete | 5,947 aliases, CAS numbers, SMILES for 297/329 substances |
| 3 | Full-Text Search + Embeddings | ✅ Complete | 8 RPC search functions, tsvector triggers, pgvector column |
| 4 | REST API + OpenAPI | ✅ Complete | PostgREST auto-REST, OpenAPI 3.0 spec, Redoc docs |
| 5 | MCP Server | ✅ Complete | 7 AI tools, Node.js + TypeScript, Claude Desktop registered |
| 6 | JSON-LD + SEO | ✅ Complete | Schema.org structured data, sitemap.xml, robots.txt |
| 7 | Frontend (Next.js) | ✅ Complete | 354 static pages, 4-tab substance detail, health ring SVG |
| 8 | GitHub + CI/CD | ✅ Complete | Public repo, GitHub Actions green, Docker container |
| 9 | Case Management Schema | ✅ Complete | 6 new tables, 4 enum types, RLS, auto-timestamp triggers |
| 10 | Sky Valley PCB Case | ✅ Complete | 1 expert, 1 case, 5 parties, 84 docs, 2 substances, 12 events |
| 11 | Design Concepts | ✅ Complete | 3 full HTML mockups with role-selection (Consumer/Doctor/Lawyer) |

### Session Log Summary

| Session | Date | Key Work |
|---------|------|---------|
| 1–3 | Early Feb 2026 | Project architecture, markdown setup, chunk planning |
| 4 | Early Mar 2026 | Schema Foundation (Chunk 1) — 12 tables + EWG ETL |
| 5 | Mar 6, 2026 | PubChem enrichment (Chunk 2) — 5,947 aliases |
| 6 | Mar 7, 2026 | MCP server debug + completion, Claude Desktop registration |
| 7 | Mar 7, 2026 | Chunks 3–4: search RPCs + OpenAPI spec |
| 8 | Mar 8, 2026 | Chunk 6: JSON-LD, sitemap, robots.txt |
| 9–11 | Mar 8–9, 2026 | Chunk 7: Next.js website (354 pages) |
| 12 | Mar 9, 2026 | Vercel deploy, GoDaddy DNS, SSL — **SITE LIVE** |
| 13 | Mar 10, 2026 | Case management schema + Sky Valley PCB case seeding |
| 14 | Mar 13, 2026 | Interface design vision — 3 concepts + HTML mockups |

---

## 15. Key Identifiers & Credentials

### Supabase
- **Project URL:** `https://vlezoyalutexenbnzzui.supabase.co`
- **Creds file:** `C:\Users\kmacn\Desktop\TheKnowledgeGardens\ewg-data\.env`
- **Anon key:** in `.env` file
- **Service role key:** in `.env` file (write access)

### Case UUIDs
- **Sky Valley Case:** `55021415-8769-4abe-93ba-5b0887110b74`
- **Dr. James Dahlgren:** `3e5b00a1-0756-4065-9738-407444514106`

### Google Drive
- **Account:** chillyd@gmail.com
- **Folder:** `JDM Toxicology Data 2026 > Sky Valley PCB Case`
- **Folder ID:** `1I0iDhmvltPKeA52LaQI6YO8BZEP1XbYK`

### GitHub
- **Account:** chilly611
- **Repo:** `github.com/chilly611/knowledge-gardens-toxicology`
- **CI secrets:** SUPABASE_URL, SUPABASE_ANON_KEY (already configured)

### Vercel
- **Project:** chillyd-2693s-projects/website
- **Domain:** toxicology.theknowledgegardens.com
- **DNS:** GoDaddy CNAME `toxicology` → `cname.vercel-dns.com`

### Local Machine
- **OS:** Windows
- **Username:** kmacn
- **Project root:** `C:\Users\kmacn\Desktop\TheKnowledgeGardens\toxicology-db\`
- **Backup:** `C:\Users\kmacn\Desktop\TheKnowledgeGardens\KG from Claude\`

### Website Env Vars
- `NEXT_PUBLIC_SUPABASE_URL` — in `website/.env.local` and Vercel dashboard
- `NEXT_PUBLIC_SUPABASE_ANON_KEY` — in `website/.env.local` and Vercel dashboard

---

## 16. What's Next

### Immediate (Design Direction)
- [ ] Choose one of the three design concepts (Stratigraph / Loom / Tidepool) and begin building into the live site
- [ ] Role-differentiated entry experience (Consumer / Doctor / Lawyer path selection)

### Data Expansion
- [ ] Generate vector embeddings when API key is available (pgvector column ready)
- [ ] Add EPA IRIS toxicity assessments
- [ ] Add ATSDR Minimum Risk Levels
- [ ] Add WHO IARC carcinogen classifications
- [ ] Ingest more Sky Valley PCB case documents from Google Drive (currently 84 entries, many are folder stubs)

### Frontend / Interface
- [ ] Implement chosen design concept in Next.js
- [ ] Case management UI (legal professional path)
- [ ] Expert profile pages (Dr. Dahlgren)
- [ ] Brand certification path (luxury brand audience)

### Infrastructure
- [ ] Connect Git repo to Vercel for auto-deploy on push
- [ ] Rename Vercel project from "website" to "toxicology-kg"
- [ ] Deploy to `theknowledgegardens.com/toxicology` (vs current subdomain)

### AI / Agent Layer
- [ ] Connect TKG to Orchid Knowledge Garden (cross-domain navigation)
- [ ] Expand MCP server tools (case query tools, expert tools)
- [ ] Build public API documentation page

---

## Operational Notes

### Session Continuity
- **Load at session start:** `TOXICOLOGY_DB_PROJECT.md` and `PROJECT_STATE.md`
- **Save at session end:** Update both markdown files + sync to `KG from Claude\` + commit + push
- **Context window management:** Work in deliberate chunks, save state before context limit

### Key Technical Lessons
- **Hardcoded UUIDs over subqueries:** Scalar subqueries in Supabase INSERT can silently return null on name mismatches — use hardcoded UUIDs
- **Desktop Commander write strategy:** Append in 25–35 line chunks after initial rewrite to avoid truncation
- **Supabase DDL:** Must go through SQL Editor browser interface — JS client cannot execute raw DDL
- **Vercel DNS:** Use CNAME (not A record) pointing to `cname.vercel-dns.com`
- **search_substances_hybrid fix (003_fix_hybrid.sql):** Return type must be exactly 5 columns: name, cas_number, description, match_type, score

---

*The Knowledge Gardens · toxicology.theknowledgegardens.com · github.com/chilly611/knowledge-gardens-toxicology*

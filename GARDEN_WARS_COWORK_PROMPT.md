# GARDEN WARS v6 — Cowork Master Prompt

## Context for All Agents

You are building **Garden Wars** — an interactive CEO strategy simulator for **The Knowledge Gardens**, a platform company that deploys AI-native operating systems across fragmented trillion-dollar industries. The founders are:

- **John Bou (CEO):** Built Modio Health → acquired by CHG Healthcare. KLAS #1 credentialing. 700K+ providers, 1,000+ healthcare orgs. 15 years healthcare tech.
- **Chilly Dahlgren (CTO):** Second-generation AI pioneer. Mother Kathleen Dahlgren: MIT Press author (Naive Semantics, 1988), IBM Senior Scientist, founded Cognition Technologies → Nuance. Father Dr. James Dahlgren: world-leading toxicologist. Chilly: NYU Film, Ethereal Engine → Infinite Reality ($75M acquisition, $2.5B valuation).

**The company:** 3 gardens live (Healthcare 12.1M records, Construction shipping to paywall, Botanical with Ecuagenera partnership). 12 commercial verticals scoped. 40 rare-knowledge research databases on the frontier map. Architecture: 4 lanes (Admin, Professional, Public, Machine), 3 surfaces (Gold/Green/Red), Neo4j knowledge graph, RSI heartbeat, Claude AI, MCP server.

**The game's purpose:** Help Chilly and John make real strategic decisions by simulating paths through their business. Every decision branches into more decisions. Every path shows projected revenue, risk, and tradeoffs. Paths are saved as "Hero's Journeys" they can compare and share.

**Live deployment:** https://garden-wars.vercel.app (Vercel, React via Babel standalone, single index.html + /img/ assets)
**GitHub:** chilly611/hkg/garden-wars/
**Vercel token:** [VERCEL_TOKEN_REDACTED]
**GitHub token:** [GITHUB_TOKEN_REDACTED]

---

## The 4 Scores (Primary Metrics)

Every option in the game is scored on these 4 axes (1-10 each):

| Score | Measures | Icon |
|---|---|---|
| **Human Value** 🌱 | How much this helps real humans — health outcomes, knowledge preservation, lives improved |
| **Machine Value** 🤖 | How much this strengthens the AI citation moat — data density, MCP adoption, API consumption |
| **Fun Factor** 🔥 | How excited Chilly and John are to work on this — passion, creative energy, recruiting appeal |
| **Profitability** 💰 | Revenue potential, margins, time-to-revenue, capital efficiency |

---

## Architecture Reference

Read the full architecture doc at: `/mnt/user-data/outputs/GARDEN_WARS_MASTER_ARCHITECTURE.md`

Key files in the project knowledge:
- `01_STRATEGY.md` — North star thesis, sequencing, principles
- `02_BRANDING.md` — Visual identity, voice, per-garden palettes
- `03_PLATFORM.md` — The 4-lane/3-surface/1-graph architecture
- `04_PRODUCTS.md` — Product catalog across all gardens
- `05_RESEARCH_NICHE_TO_EMPIRE.md` — 30+ case studies of niche-to-empire companies
- `06_FRONTIER_MAP_40_GARDENS.md` — All 40 research databases tiered
- `Knowledge_Gardens_Strategic_Command_Center.md` — Master strategy with revenue architecture
- `Revenue_Architecture_for_HKG.md` — Deep revenue research (insurance B2B, healthspan, clinical referrals)
- `Knowledge_Gardens_Investor_Pitch.md` — Investor pitch with market data

---

## Game Flow

### Act 0: Opening Crawl
Star Wars style perspective-scrolling text over a dark field with floating garden imagery. Ambient music. Text explains the existential choices the startup faces. Ends with a glowing "START GARDEN WARS" button.

### Act 1: Frontier Map (Garden Selection)
Full map of ALL 52 gardens (12 commercial + 40 research). Tap to explore. Choose which garden to lead with. Multiple selection possible (dual/triple track).

### Act 2: Lane Selection
4 lanes per garden. Each with full analysis: opportunities, risks, opportunity cost, what gets easy, challenges, 4-scores.

### Act 3: Niche Drilling (Deep Branching)
The core of the game. 20+ sub-niches per lane. Example for HKG Patient Lane: GLP-1 drugs, NAD+, peptides, stem cells, rapamycin, drug interactions, toxicology/environmental health, fertility, functional medicine, telehealth, clinical trials, etc.

### Act 4: Revenue Architecture
How to monetize the chosen niche. Freemium, affiliate, SaaS, API, referrals, advertising, marketplace.

### Act 5: Capital & Team
When to raise, how much, first hires, partnerships.

### Act 6: Expansion
Next garden, next lane, how gardens feed each other.

### The Trail Map
Horizontal branching tree at the bottom. Each node = a decision. Shows 4-score dots, ARR projection. Click any node to rewind. Saved paths = "Hero's Journeys."

---

## Design System

- **DARK THEME** (this is a war room strategy tool, NOT the platform brand which is light/parchment)
- **Colors:** Gold #D4A853, Green #10B981, Purple #A78BFA, Orange #F97316, Red #EF4444, Blue #3B8BD4, Cyan #06B6D4
- **Fonts:** Instrument Serif (display), DM Sans (body), JetBrains Mono (data)
- **Background:** #060608 with radial glow effects
- **Cards:** rgba(255,255,255,.02) with border rgba(255,255,255,.06), hover lift + shadow
- **Animations:** fadeUp entry, stagger delays, floating background images, breathing glows, shimmer bars
- **Compass Nav:** Bottom-right hex button, blooms into labeled vertical menu (🗺️ Frontier, 📊 Dashboard, 💾 Save, 📂 Load, 📧 Share, ← Back, ↺ Restart)
- **37 image assets** in /img/ including construction tools, medical instruments, AI-generated logos

---

## Tech Constraints

- **Single index.html file** with React via Babel standalone (CDN, no build step)
- **No npm, no webpack, no build pipeline** — everything runs from a single HTML file
- **Deploy:** `vercel deploy --prod` from the garden-wars directory
- **Claude API:** Needs a Vercel serverless function at /api/research.js to proxy calls (avoids CORS + exposes no API key to frontend)
- **localStorage** for save/load persistence
- **All 37 images** at ./img/ relative paths (already deployed on Vercel)

---

## What Each Agent Should Build

### If you are building the GAME ENGINE:
Build the React state machine, decision tree traversal, 4-score calculation, undo/redo stack, save/load/export system. The data structure must support infinite branching (not hardcoded paths). Each decision node has: id, category, title, description, options[], and each option has: label, description, effects (4-scores + secondary metrics), unlocks[], analysis panels (opportunities, risks, oppCost, getsEasy, challenges, research).

### If you are building the VISUAL LAYER:
Build the opening crawl (CSS perspective transform + JS scroll animation), the card system, the radar chart for 4-scores, the compass nav, the floating background imagery, all animations and transitions. Match the dark theme aesthetic. Use the 37 existing images aggressively.

### If you are building the FRONTIER MAP:
Populate all 52 gardens with full data. 12 commercial verticals from the Command Center doc. 40 research databases from 06_FRONTIER_MAP_40_GARDENS.md. Each needs: name, icon, TAM, description, revenue model, market data, moat, synergy, 4-scores, status, deploy timeline.

### If you are building DECISION CONTENT:
Write the deep branching content for each act. Start with HKG → Patient Lane → sub-niches (20+ options). Each option needs: full description, market size, revenue model, competitive landscape, regulatory considerations, 4-scores, key questions, pre-built research analysis (200-300 words), what gets easy, what you leave on the table. Use the revenue research docs for numbers.

### If you are building the RESEARCH INTEGRATION:
Create a Vercel serverless function at /api/research.js that proxies Claude API calls. The frontend sends the current game state + decision context. The function calls Claude Sonnet with a strategy-advisor system prompt and returns the analysis. Cache results. Build the in-game research modal that displays results beautifully.

### If you are building the TRAIL MAP:
Build the branching tree visualization (SVG or Canvas). Each node is a decision point. The chosen path is highlighted. Unchosen branches are dimmed. Nodes show 4-score mini-indicators and ARR at that point. Click any node to rewind. Save/export the full tree as a "Hero's Journey." Build the comparison view for two saved journeys.

---

## Critical Files to Read Before Building

1. This prompt (you're reading it)
2. `GARDEN_WARS_MASTER_ARCHITECTURE.md` — full game design doc
3. `01_STRATEGY.md` — the company thesis and principles
4. `03_PLATFORM.md` — the 4-lane/3-surface architecture
5. `06_FRONTIER_MAP_40_GARDENS.md` — all 40 research databases
6. `Knowledge_Gardens_Strategic_Command_Center.md` — master strategy with all 12 verticals
7. `Revenue_Architecture_for_HKG.md` — deep revenue numbers

---

## Definition of Done

The game is done when Chilly and John can:
1. Watch the opening crawl and feel the weight of the decisions ahead
2. Explore all 52 gardens on the frontier map
3. Play through 15-30+ branching decisions from garden to niche to revenue to team
4. Research any decision in-game via Claude API
5. See their full decision tree as a visual branching map
6. Save, name, and compare multiple strategy paths
7. Share a strategy via email
8. Feel MORE confident about their choices, not less

**Ship fast. Ship often. Deploy to Vercel after every meaningful increment. The founders are waiting.**

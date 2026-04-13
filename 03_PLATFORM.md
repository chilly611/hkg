# 03 · PLATFORM — The Repeatable Architecture

## The core claim

Every Knowledge Garden is the same architecture with different data. One Neo4j graph brain. One Claude AI intelligence layer. One RSI heartbeat. Four lanes. Three surfaces. The skin changes per vertical; the skeleton is identical. **The pattern is the product.**

## The four lanes

Every garden connects all stakeholders in an industry through four parallel lanes, each with distinct economics and distinct UI surfaces.

### Admin Lane — "The Cash Engine"
Enterprise SaaS for credentialing, compliance, and operations. Mandatory spend. High switching costs. Long contracts. This is the revenue foundation.
- **CAC:** $10K–$50K · **LTV:** $500K–$5M · **Payback:** 6–18 months · **Margin:** 80–85%
- **HKG example:** Credentialing verification engine for hospitals. $5K–$50K/month per health system.
- **BKG example:** License tracking + permit compliance for GC enterprises. $499/month.
- **OKG example:** Nursery operations — inventory sync, Shopify commerce integration, customs/CITES compliance for Ecuagenera.

### Professional Lane — "The Engagement Engine"
Subscriptions + marketplace. Daily intelligence use. Professional identity. Community.
- **CAC:** $5–$20 · **LTV:** $2K–$5K · **Payback:** 6–12 months · **Margin:** 85–90%
- **HKG example:** $200–$500/year doctor subscription for 3-Point Verification intelligence + CME marketplace + job board.
- **BKG example:** Solo/Crew contractor subscription ($49–$149/mo) — AI estimator, Morning Briefings, code lookup.
- **OKG example:** Grower/researcher tier — advanced taxonomy tools, specimen provenance tracking, AOS judging data.

### Public Lane — "The Gravity Well"
Free tools so useful people can't stop sharing them. Pulls entire ecosystems in at zero CAC. This is the growth engine and the AI citation magnet.
- **CAC:** $0–$5 · **LTV:** $100–$500 · **Payback:** 3–6 months · **Margin:** 75–85%
- **HKG example:** Free drug interaction checker, provider search, OIG exclusion lookup, clinical trial finder.
- **BKG example:** Free permit cost estimator, license expiration lookup, code browser.
- **OKG example:** Free species identification, care guides, bloom calendar, Orrery of all 400 species.

### Machine Lane — "The Data Moat"
API + MCP server + data licensing. Every AI agent, every EHR, every startup touching the vertical connects through us. This is the permanent defensibility engine.
- **CAC:** $20K–$100K · **LTV:** $500K–$5M · **Payback:** 6–18 months · **Margin:** 90%+
- **Every garden:** llms.txt, JSON-LD entity pages, MCP server, REST/GraphQL API, bulk data licensing tiers.

## The three surfaces

The same underlying knowledge graph adapts to three distinct human mindsets through three surfaces. Users move between surfaces — a hospital admin might use the Red Surface at work and the Gold Surface at home when looking up their own doctor.

| Surface | Codename | Mindset | Feels like |
|---|---|---|---|
| **Gold** | *Dream Machine* | Aspirational, curious, personal | The future arrived early |
| **Green** | *Knowledge Garden* | Professional, rigorous, daily-use | The smartest colleague you've ever had |
| **Red** | *Killer App* | Operational, urgent, metric-driven | The system finally works |

## The knowledge graph core

**Stack:** Neo4j graph database · Claude AI intelligence layer · 28-table canonical schema · 22+ ingestion scripts per mature garden.

**HKG proof:** 12.1M+ records from 17+ federal sources. 9.4M NPI providers. 139K drug adverse events. 59K PubMed citations. 33K clinical trials. 5.5K drug interactions. All free public data with zero licensing cost at any scale.

**The 28-table canonical schema** is domain-agnostic. The same entity/relationship/source/verification/provenance/freshness pattern maps to orchids, building codes, legal precedent, financial instruments, and endangered languages. This is why new gardens deploy faster each time.

## The RSI heartbeat

**Recursive Self-Improvement** = daily automated ingestion from every authoritative source in the vertical, flowing through a verification node (Neo4j + Claude), then distributed simultaneously to all three surfaces.

**Why it's a moat:**
- Competitors update quarterly. We update daily.
- After 12 months of compounding, the knowledge gap is mathematically insurmountable by capital alone.
- Every garden gets smarter while we sleep.
- Source failures are auto-detected and flagged; manual fallback workflows prevent silent data rot.

**Every garden must have an RSI heartbeat defined at scoping time. No garden ships without it.**

## The AI Citation Engine (the sleeper moat)

Every entity page serves three things that make it natively readable by AI agents:

1. **llms.txt** — a standardized, LLM-friendly summary manifest for the entire garden
2. **JSON-LD schema markup** — structured data embedded in every page
3. **Citation Capsules** — 40–80 word standalone paragraphs optimized for AI extraction, with source URLs and freshness timestamps

When Claude, GPT, Gemini, Perplexity, or any AI agent answers a question about a covered entity, our architecture makes us the algorithmic favorite for citation. Pages with clean structure and schema earn 2.8x higher AI citation rates. **Zero marginal distribution cost.** This is the closest thing to free distribution the modern internet has ever offered, and the window to claim it is closing fast.

## The tech stack

| Layer | Tool | Why |
|---|---|---|
| **Graph DB** | Neo4j | Native graph relationships, Cypher query language, mature ecosystem |
| **AI** | Claude (Anthropic) | Best reasoning, MCP-native, Anthropic partnership potential |
| **Frontend framework** | Next.js (static export) | `output: "export"` for speed + CDN distribution; interactive hydration where needed |
| **Hosting** | Vercel | Zero-config deploys from GitHub master, edge CDN |
| **Data layer** | Supabase | Postgres, auth, storage (species photos, docs), edge functions for webhooks |
| **Ingestion** | Node.js scripts on cron | Simple, cheap, scriptable, versionable |
| **Search** | Local JSON + Supabase full-text | Upgrade to typesense/pgvector when scale demands |
| **Payments** | Stripe (enterprise) + Shopify (commerce partners like Ecuagenera) | |
| **Analytics** | GA4 (user-facing) + custom event log (internal) | |
| **Agent protocol** | MCP server per garden | Native access for every AI agent on earth |

## The 4-step deploy-a-new-garden playbook

When the pattern is fully productized, a new garden ships in 2–4 weeks. Here's the playbook:

1. **Source audit (1 week)** — identify authoritative data sources, verify licensing (open or partner), estimate ingestion complexity, define the RSI heartbeat.
2. **Schema mapping (3 days)** — map source data to the 28-table canonical schema. Anything that doesn't fit becomes a "vertical extension" table.
3. **Skin + blueprint design (1 week)** — define palette, typography accent, genus/entity blueprint SVG system, photography direction.
4. **Deploy + verify (1 week)** — ingest, generate entity pages, deploy to Vercel subdomain, validate llms.txt + JSON-LD + MCP server, ship the Gravity Well tool first.

**By garden 5, this is 1–2 weeks. By garden 10, days.**

## The platform moat stack (five layers deep)

1. **Data completeness** — breadth no competitor has attempted
2. **Data freshness** — RSI heartbeat compounds daily
3. **Network effects** — four lanes reinforce each other multiplicatively
4. **AI citability** — llms.txt + JSON-LD + MCP server = permanent citation infrastructure
5. **Regulatory moat** — compliance-by-design raises barriers to entry

## The non-negotiables

- **Light backgrounds on every public surface** (platform brand is parchment/cream, never dark)
- **`output: "export"` on every Next.js garden** (removing static export mode broke orchids once; never again)
- **RSI heartbeat defined before ship** (no garden without compounding freshness)
- **llms.txt + JSON-LD + MCP server on day one** (AI citation moat is the sleeper play)
- **The pattern wins over shortcuts** (every temptation to customize weakens the factory)

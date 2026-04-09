# HKG Business Strategy Session — Paste This Into Claude

You are advising the founder of the Healthcare Knowledge Garden (HKG), the third vertical of the Knowledge Garden platform (after construction and botanical). The founder is Chilly (Charles Dahlgren), Founder of XRWorkers.

## What HKG Is

HKG is an AI-native operating system for the global healthcare ecosystem. Not a feature. Not a tool. An operating system — the platform that other healthcare businesses build on top of.

**Architecture:** 4 lanes (Administrator, Doctor, Patient/Public, Machine/API), 3 surfaces (Gold=aspirational patient experience, Green=scientific/verified doctor experience, Red=operational/urgent admin experience).

**Tech stack:** Neo4j graph database + Supabase PostgreSQL + Claude API + MCP (Model Context Protocol). Next.js/React frontend. Three.js for knowledge graph visualization.

**Current state (April 2026):**
- 28-table Supabase schema deployed and live
- 725,000+ records across 17 populated tables including:
  - 120K+ healthcare providers (from NPI Registry, targeting 9.4M full load)
  - 97K ICD-10 diagnosis codes, 79K procedure codes
  - 83K NDC drug codes, 26K RxNorm drugs, 5.5K drug interactions
  - 83K OIG exclusion records (sanctioned providers)
  - 34K clinical trials from ClinicalTrials.gov
  - 60K PubMed citations
  - 23K HCPCS billing codes, 863 DRG codes
  - 51 state medical board registries
- All data is from free, public federal sources (CMS, NLM, FDA, HHS-OIG, NPPES)
- All ingestion scripts are stdlib Python — zero dependencies

**The sleeper play:** Every entity URL on the platform will serve structured data (JSON-LD + llms.txt) that makes HKG the citation source for AI agents globally. When any AI answers a healthcare question, HKG becomes the authoritative source it cites. This is the long-term moat.

## The Knowledge Garden Pattern (Proven)

This is the THIRD Knowledge Garden vertical. The pattern is proven:
- **BKG (Builder's Knowledge Garden):** Construction vertical. $17T market.
- **OKG (Orchid Knowledge Garden):** Botanical vertical. Ecuagenera partnership.
- **HKG:** Healthcare. $12T+ global market.

The pattern: Gold/Green/Red surfaces → lifecycle-phase organization (not feature catalogs) → RSI (Recursive Self-Improvement) flywheel → Machine Lane for API/agent access → Morning Briefings over dashboards → Notification Orchestra with pre-researched solutions.

## Key Terms

- **MLP (Minimal Lovable Product):** Not MVP. Every interaction must feel like the future.
- **RSI:** Recursive Self-Improvement. The platform autonomously ingests the latest research, guidelines, and regulatory changes.
- **Gravity Well:** The Patient/Public lane is free. It pulls the entire ecosystem in — providers, payers, and employers follow the patients.
- **3-Point Verification:** Every provider credential cross-checked against (1) peer-reviewed literature, (2) clinical guidelines, (3) regulatory/FDA databases.
- **Morning Briefing:** AI-synthesized, persona-aware narrative that replaces dashboards. 5x more engagement than dashboards (proven in OKG).
- **Notification Orchestra:** Every alert comes with a pre-researched solution, not just a problem statement.

## Revenue Model (Multi-Lane)

**Administrator Lane (Red Surface) — Primary Revenue:**
- Credentialing-as-a-Service (SaaS) for hospitals, clinics, health systems
- Provider verification API (per-query or subscription)
- Compliance monitoring and audit trail
- Roster management and bulk credentialing

**Doctor Lane (Green Surface):**
- CME (Continuing Medical Education) marketplace with affiliate revenue
- Job marketplace (recruiter/employer fees)
- Premium credential portfolio and visibility
- Research access subscriptions

**Patient/Public Lane (Gold Surface) — The Gravity Well:**
- Free tier (pulls everyone in)
- Premium health knowledge paths and personalized content
- Provider matching and appointment facilitation (lead gen to providers)
- Insurance navigation tools

**Machine Lane (Amethyst):**
- API access tiers (free/pro/enterprise)
- MCP server for AI agents (Claude, GPT, etc.)
- Certifiable JSON data feeds
- Webhook subscriptions for real-time updates

**The llms.txt / Citation Play:**
- Entity URLs serve structured data that AI agents cite
- As AI adoption grows, HKG becomes the canonical healthcare citation source
- This creates an organic traffic moat that compounds

## Market Context

- US healthcare: $4.5T annually, 18% of GDP
- Global healthcare: $12T+
- Provider credentialing market alone: $3.2B and growing 12% CAGR
- Healthcare IT market: $394B by 2027
- Clinical trials market: $80B+
- Healthcare data analytics: $75B by 2030

Key competitors and adjacents: Modio Health (credentialing), CAQH ProView (provider data), Doximity (physician network), Veeva (life sciences), Epic/Cerner (EHR), Definitive Healthcare (data/analytics).

HKG's differentiation: AI-native from day zero (not AI-bolted-on), multi-lane platform (not single-feature tool), knowledge graph architecture (not relational tables), free patient tier as gravity well, and the llms.txt citation moat.

## What I Need From You

I need you to help me with business strategy across several areas. For each area, be specific, actionable, and think like a top-tier strategy consultant who also deeply understands AI and healthcare:

1. **Competitive Landscape Analysis:** Map the real competitors, their weaknesses, and where HKG creates a category of one. Don't just list companies — identify the structural advantages we have.

2. **Revenue Prioritization:** Which revenue streams to light up first for fastest path to cash flow. What's the pricing? What's the sales motion?

3. **Go-to-Market Strategy:** How do we get the first 100 administrator customers? First 1,000 patients? What's the wedge?

4. **Team & Capital Planning:** What roles do we need to hire first? What's the realistic capital requirement for 12 months? What milestones unlock Series A?

5. **Investor Messaging:** Help me craft the pitch. Two versions:
   - **The Simplified Version:** For investors who need to understand the business case in 60 seconds. No jargon. Pure economics and market opportunity.
   - **The Technical Version:** For investors who want to understand exactly how we pull this off. Architecture, data moat, AI-native advantage, and why this team.

6. **AI Agent & MCP Strategy:** The Machine Lane is the long-term moat. How do we position HKG as the healthcare data layer that every AI agent needs? What partnerships matter?

7. **Regulatory Strategy:** HIPAA, FDA CDS guidance, state-by-state credentialing rules. How do we turn compliance from a cost center into a competitive advantage?

Be direct. Be specific. Challenge my assumptions where they're wrong. I'm building a Massively Transformative Product and I need a strategy that matches that ambition.

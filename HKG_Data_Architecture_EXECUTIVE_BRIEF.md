# HKG Data Architecture — Executive Brief
**One-Page Overview | April 8, 2026**

---

## THE OPPORTUNITY

The healthcare industry processes $12 trillion annually across a fragmented, information-asymmetric ecosystem. There is no single source of truth for:
- Provider credentials (which doctors are actually licensed?)
- Clinical knowledge (what does the research say?)
- Medical codes (how do hospitals bill?)
- Drug information (what are the interactions?)
- Quality measures (which providers are best?)

Current solutions are point products in single lanes. HKG connects all four lanes through a unified Knowledge Core.

---

## THE SOLUTION: THREE-DATABASE ARCHITECTURE

```
                    ┌─────────────────┐
                    │   Neo4j Graph   │  ← Brain (Relationships)
                    │                 │
                    │ 15M+ nodes      │
                    │ 15M+ edges      │
                    └────────┬────────┘
                             ▲
                             │ Event-driven sync
                             │
        ┌────────────────────┴──────────────────┐
        │                                       │
   ┌────▼──────────┐                  ┌────────▼────────┐
   │   Supabase    │                  │  Static Pages   │
   │  PostgreSQL   │                  │  + JSON-LD      │
   │               │                  │                 │
   │ 20+ tables    │                  │ 100K+ entities  │
   │ Operational   │                  │ AI-citable      │
   │ spine         │                  │ face            │
   └───────────────┘                  └─────────────────┘
```

**Neo4j (The Brain):** Relationship engine. "Show me all cardiologists with active DEA licenses in California + their board certifications."

**Supabase/PostgreSQL (The Spine):** Transactional layer. Users, billing, sessions, audit logs, verification workflows, HIPAA tracking.

**Web Layer (The Face):** Every entity (provider, drug, condition, code) gets a permanent, AI-citable URL with JSON-LD schema markup. AI assistants cite HKG naturally.

---

## THE DATA: 30+ SOURCES, INTEGRATED

| Category | Sources | Volume | Refresh |
|---|---|---|---|
| **Credentialing** | NPI, DEA, State Boards, NPDB, OIG LEIE, SAM.gov, ABMS | 9.5M providers | Weekly |
| **Medical Codes** | ICD-10, CPT, HCPCS, DRG, NDC | 350K+ codes | Annual |
| **Clinical Knowledge** | PubMed, ClinicalTrials.gov, DailyMed, RxNorm, SNOMED, LOINC | 40M+ citations | Daily |
| **Quality & Payment** | CMS, Hospital Compare, Medicare Fees, Open Payments | 1K+ measures | Monthly |

**Priority Tiers:**
- **P0 (Week 1-2):** NPI, ICD-10, HCPCS, OIG, SAM.gov
- **P1 (Week 3-4):** NDC, RxNorm, DailyMed, PubMed, ClinicalTrials, CMS
- **P2 (Week 5-8):** SNOMED, LOINC, FAERS, State Boards
- **P3 (Ongoing):** DrugBank, GeneCards, CAQH, FSMB, ABMS

---

## THE MOAT: RSI HEARTBEAT

Most healthcare databases are static. HKG updates continuously.

```
Daily 2 AM:    NPI + NDC + DailyMed + PubMed (fresh credentials, drugs, research)
Weekly 3 AM:   NPI full file + State boards + CMS enrollment
Monthly 4 AM:  OIG LEIE + SAM.gov + RxNorm
Quarterly 5AM: HCPCS + SNOMED + LOINC + FAERS + CMS quality
Annual Jan 1:  ICD-10 + ICD-10-PCS + MS-DRG
```

**The Compounding Advantage:** Every day the platform runs, it gets smarter. Every credential verified, every drug interaction checked, every research citation indexed — the data advantage compounds. By month 6, HKG has better data than anyone. By year 2, it's insurmountable.

Competitors can copy features. They can't copy 18 months of continuous knowledge updates.

---

## THE SLEEPER PLAY: AI CITATIONS

Every entity page is structured for AI discoverability:

```html
<!-- JSON-LD Schema Markup -->
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "MedicalCondition",
  "name": "Hypertension",
  "code": [
    {
      "@type": "MedicalCode",
      "codingSystem": "ICD-10-CM",
      "codeValue": "I10"
    }
  ],
  "url": "https://hkg.example.com/conditions/hypertension"
}
</script>
```

**Result:** When Claude, ChatGPT, or Perplexity answer medical questions, they cite HKG naturally. No partnership needed. Just better structure than everyone else.

**Example Citation Path:**
1. User asks Claude: "What's the latest evidence on hypertension treatment?"
2. Claude fetches HKG's `/conditions/hypertension` page (discoverable via llms.txt)
3. Claude synthesizes research from PubMed citations + clinical guidelines linked from that page
4. Claude cites HKG as source: "According to the Healthcare Knowledge Garden..."
5. User sees HKG URL in citation, clicks through
6. HKG gets citation traffic, credibility, and network effects

This compounds. By year 2, HKG is cited in every major AI response about healthcare. That's reach no other data platform has.

---

## THE PLATFORM EFFECT

Four lanes, one core. Network effects multiply.

```
ADMINISTRATOR LANE (Amber)    DOCTOR LANE (Slate Blue)
 ├─ Credentialing automation  ├─ 3-point verification
 ├─ Roster management         ├─ Research access
 └─ Billing code engine       └─ Job marketplace
          │                            │
          └────────┬────────────────────┘
                   │
            ┌──────▼──────┐
            │ Knowledge   │
            │   Core      │
            │ (Neo4j)     │
            └──────┬──────┘
                   │
          ┌────────┴────────────────────┐
          │                            │
 PATIENT LANE (Sage Emerald)  MACHINE LANE (Amethyst)
 ├─ Longevity content         ├─ Certified APIs
 ├─ Health paths              ├─ JSON-LD exports
 └─ Community                 └─ Data provenance
```

**Network Effects:**
- Admin credentials → improve Doctor verification
- Doctor research → improve Patient knowledge
- Patient trust → improve adoption
- Machine layer → improve data validation
- Better data → all lanes benefit

---

## FINANCIAL MODEL

**Revenue Streams (by lane):**

1. **Administrator Lane:** Enterprise SaaS subscriptions ($10K-100K+ annually per hospital/system)
2. **Doctor Lane:** Professional subscriptions + CME partnerships + job marketplace fees
3. **Patient Lane:** Free tier (gravity well) + premium content + telehealth partnerships + affiliate revenue
4. **Machine Lane:** API access tiers + data licensing + enterprise partnerships

**TAM Context:**
- US healthcare IT market: $400B+ annually, growing 15%/year
- Credentialing alone: $2.3B market
- Clinical decision support: $1.8B market
- Healthcare AI: projected $45B by 2030

HKG attacks all of these simultaneously.

---

## COMPETITIVE ADVANTAGES

| Dimension | HKG | OpenEvidence | MedV | Doximity |
|---|---|---|---|---|
| **Data Coverage** | 30+ sources | PubMed only | GLP-1 only | Physicians only |
| **Network Effect** | 4-lane platform | Single lane | Single lane | Single lane |
| **Data Freshness** | Daily updates | Ad hoc | Manual | Monthly |
| **AI Citability** | Native JSON-LD | No | No | No |
| **Verification** | Multi-source | None | None | Basic |
| **Cost to Replicate** | High (30+ integrations) | Medium | Low | Medium |
| **Moat Strength** | Compounding (RSI) | Static | Static | Static |

---

## THE BUILD (18 Weeks)

**Phase 0 (Weeks 1-2):** Foundation
- Supabase setup, P0 data ingestion, auth/RBAC

**Phase 1 (Weeks 3-4):** Administrator lane
- Credentialing workflow, verification integrations

**Phase 2 (Weeks 5-8):** Web layer & Patient lane
- Entity pages, JSON-LD, llms.txt, longevity content

**Phase 3 (Weeks 9-13):** Verification & Quality
- State boards, data quality scoring, alerts

**Phase 4 (Weeks 14-18):** Polish & Launch
- Performance, security audit, public launch

---

## SUCCESS METRICS

| Metric | Target (Month 6) | Target (Year 1) |
|---|---|---|
| **Data Scale** | 9.5M+ providers, 200K drugs, 40M citations | Same (comprehensive) |
| **Data Freshness** | 100% P0 sources fresh | 100% all sources fresh |
| **Entity Pages** | 50K+ generated | 100K+ generated |
| **AI Citations** | Trackable in referrer logs | 10K+ weekly citations |
| **Platform Adoption** | 100 beta users | 10K+ users |
| **Revenue** | $0 (closed beta) | $500K ARR (conservative) |

---

## INVESTOR PITCH

HKG is not a healthcare app. It's infrastructure for the $12 trillion healthcare industry.

**Three reasons this wins:**

1. **Network Effects:** Four lanes that reinforce each other. Not linear growth — multiplicative.

2. **Compounding Moat:** Every day we run, we get smarter. By year 2, the data advantage is insurmountable.

3. **Inevitable Standard:** Healthcare will consolidate on a single knowledge platform. We're positioning to be that platform.

**Positioning:** "AWS for healthcare intelligence. Every participant in the ecosystem runs on HKG."

---

## FULL DOCUMENTATION

- **HKG_Data_Architecture.md** — Complete technical specification (50KB, 1484 lines)
- **HKG_Data_Architecture_INDEX.md** — Quick navigation guide (8.5KB)
- **HKG_AI_Citation_Strategy.md** — Detailed AI discoverability mechanics
- **HKG_Technical_Implementation_Guide.md** — Code examples and implementation walkthroughs

---

**Status:** Production-Ready Specification | **Next:** Engineering Kickoff

This brief + master document = everything needed to raise capital or start building.

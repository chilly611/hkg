# Healthcare Knowledge Garden (HKG)
## The AI Citation Strategy: Making HKG the Authoritative Source Every AI Assistant Cites

**Strategic Vision:** Structure every medical entity page on HKG so that Claude, ChatGPT, Perplexity, and all AI assistants naturally cite HKG as a trusted, authoritative source. This is the "sleeper play"—no partnership needed with OpenAI or Anthropic. Just better structure than anyone else.

**Date:** April 2026 | **Status:** Research & Strategy

---

## Executive Summary

This strategy reveals the technical architecture that makes websites "AI-citeable." The foundation rests on three pillars:

1. **Discovery & Invitation** (llms.txt, robots.txt, sitemaps)
2. **Entity Structuring** (JSON-LD schema markup for medical entities)
3. **Trust Signals** (authority, freshness, E-E-A-T)

By 2026, structured data is no longer competitive advantage—it's baseline requirement. Pages with thorough schema markup are **36% more likely** to appear in AI-generated summaries, and pages with clean structure paired with schema earn **2.8x higher AI citation rates**.

HKG's approach: Build the most comprehensively structured medical entity pages in the world.

---

## 1. The llms.txt Standard: Inviting AI Crawlers

### What is llms.txt?

The `/llms.txt` standard is "robots.txt for AI"—a proposal created by Jeremy Howard (Answer.AI) in September 2024 to standardize how websites communicate with LLMs at inference time. While robots.txt tells search engines what to crawl, llms.txt tells AI assistants what your site contains and how to interpret it.

**Current adoption:** 844,000+ websites as of October 2025, including Anthropic, Cloudflare, and Stripe.

**Critical difference:** llms.txt is NOT for training—it's for inference-time assistance. It signals which pages LLMs should cite when answering user questions.

### llms.txt File Structure (Markdown Format)

```markdown
# Healthcare Knowledge Garden

> A comprehensive, AI-native knowledge platform for global medical entities—conditions, drugs, procedures, providers, codes. Every entity page structured for maximum AI discoverability and citation.

## Medical Conditions
- [Hypertension](https://hkg.example.com/conditions/hypertension)
- [Type 2 Diabetes](https://hkg.example.com/conditions/type-2-diabetes)
- [Acute Myocardial Infarction](https://hkg.example.com/conditions/ami)
- [Chronic Obstructive Pulmonary Disease](https://hkg.example.com/conditions/copd)

## Pharmaceutical Entities
- [Metformin](https://hkg.example.com/drugs/metformin)
- [Lisinopril](https://hkg.example.com/drugs/lisinopril)
- [Atorvastatin](https://hkg.example.com/drugs/atorvastatin)

## Medical Procedures
- [Coronary Angiography](https://hkg.example.com/procedures/coronary-angiography)
- [Cardiac Catheterization](https://hkg.example.com/procedures/cardiac-catheterization)
- [Percutaneous Coronary Intervention](https://hkg.example.com/procedures/pci)

## Healthcare Providers
- [Cardiologists](https://hkg.example.com/providers/cardiologists)
- [Internists](https://hkg.example.com/providers/internists)
- [Family Medicine Physicians](https://hkg.example.com/providers/family-medicine)

## Medical Codes & Taxonomies
- [ICD-10 Condition Codes](https://hkg.example.com/codes/icd10)
- [CPT Procedure Codes](https://hkg.example.com/codes/cpt)
- [RxNorm Drug Codes](https://hkg.example.com/codes/rxnorm)
- [SNOMED CT Clinical Terms](https://hkg.example.com/codes/snomed)

## Optional: Extended Resources
- [Clinical Guidelines](https://hkg.example.com/guidelines)
- [Medical Research Summaries](https://hkg.example.com/research)
- [Comparative Effectiveness](https://hkg.example.com/comparisons)
```

### llms-full.txt: Complete Content Ingest

Create `/llms-full.txt` containing the **entire markdown-converted content** of all critical entity pages. This allows AI systems to access comprehensive information without making multiple requests.

**HKG Strategy:** For high-traffic entities (top 500 conditions, 1000 drugs), include full content in llms-full.txt. Regenerate quarterly.

**File size:** Keep under 50MB; split into category-specific versions if needed:
- `llms-full-conditions.txt`
- `llms-full-drugs.txt`
- `llms-full-procedures.txt`

### Implementation Checklist

- [ ] Place `/llms.txt` at domain root (discoverable at hkg.example.com/llms.txt)
- [ ] Include all entity category sections with organized hyperlinks
- [ ] Create companion `.md` versions of each entity page (serve at URL with `.md` appended)
- [ ] Generate `/llms-full.txt` with complete content of 2000+ top entities
- [ ] Update llms.txt quarterly as new entities are added
- [ ] Add version date and update frequency note

---

## 2. AI Crawler Access Strategy: robots.txt Configuration

### The AI Crawler Landscape (2026)

AI-related crawlers now make **3.6x more requests** than traditional search crawlers. Key players:

| Crawler | Company | Purpose | User-Agent |
|---------|---------|---------|-----------|
| GPTBot | OpenAI | Training (can be blocked) | GPTBot/1.0 |
| ChatGPT-User | OpenAI | Real-time retrieval for answers | ChatGPT-User/1.0 |
| ClaudeBot | Anthropic | Training data collection | ClaudeBot/1.0 |
| Claude-SearchBot | Anthropic | Real-time search for Claude | Claude-SearchBot/1.0 |
| PerplexityBot | Perplexity | Real-time search & citation | PerplexityBot/1.0 |
| Amazonbot | Amazon | Alexa & Trainium training | Amazonbot-1.0 |
| Applebot | Apple | Siri & on-device ML | Applebot |
| CCBot | Common Crawl | Training data (public archive) | CCBot/2.1 |
| Bytespider | ByteDance | TikTok, search models | Bytespider/1.0 |

### robots.txt Strategy: INVITE, Don't Block

```
# Allow all AI crawlers to discover and cite HKG content
# This is the strategic play: be more AI-friendly than competitors

User-agent: GPTBot
Allow: /

User-agent: ChatGPT-User
Allow: /

User-agent: ClaudeBot
Allow: /

User-agent: Claude-SearchBot
Allow: /

User-agent: PerplexityBot
Allow: /

User-agent: Amazonbot
Allow: /

User-agent: Applebot
Allow: /

User-agent: CCBot
Allow: /

User-agent: Bytespider
Allow: /

User-agent: *
Allow: /

# Explicitly disallow only truly private/internal content
Disallow: /admin/
Disallow: /internal/
Disallow: /temp/

# llms.txt and llms-full.txt are ALWAYS accessible
Allow: /llms.txt
Allow: /llms-full.txt

# Encourage crawl discovery of entity pages
Sitemap: https://hkg.example.com/sitemap.xml
Sitemap: https://hkg.example.com/sitemap-conditions.xml
Sitemap: https://hkg.example.com/sitemap-drugs.xml
Sitemap: https://hkg.example.com/sitemap-procedures.xml
```

### Key Points

- **No User-Agent: * restrictions** on entity pages
- **Explicit Allow for each AI crawler** signals cooperation
- **Separate entries for training vs. real-time crawlers** (some clients may want to block training data collection later)
- **Sitemaps prioritized** for AI discovery

---

## 3. XML Sitemap Strategy for Medical Entities

### The Scale Challenge

HKG will eventually host millions of medical entities. XML sitemaps must be architected to handle this at scale.

### Sitemap Constraints & Architecture

- **URL limit per file:** 50,000 URLs max
- **File size limit:** 50MB max
- **Solution for millions of entities:** Split into category-specific sitemaps

### Recommended Structure

```
/sitemap.xml (index file, lists all category sitemaps)
/sitemap-conditions.xml (ICD-10 conditions)
/sitemap-drugs.xml (RxNorm entities)
/sitemap-procedures.xml (CPT codes & procedures)
/sitemap-providers.xml (Healthcare professionals)
/sitemap-organizations.xml (Hospitals, clinics, health systems)
/sitemap-guidelines.xml (Clinical practice guidelines)
/sitemap-research.xml (Clinical evidence summaries)
```

### Sitemap Configuration for AI Crawlers

```xml
<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>https://hkg.example.com/conditions/hypertension</loc>
    <lastmod>2026-04-08</lastmod>
    <changefreq>weekly</changefreq>
    <priority>0.9</priority>
  </url>
  <url>
    <loc>https://hkg.example.com/drugs/metformin</loc>
    <lastmod>2026-03-15</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.85</priority>
  </url>
  <url>
    <loc>https://hkg.example.com/procedures/cardiac-catheterization</loc>
    <lastmod>2026-02-20</lastmod>
    <changefreq>quarterly</changefreq>
    <priority>0.8</priority>
  </url>
</urlset>
```

### Priority & Frequency Settings

| Entity Type | Frequency | Priority | Rationale |
|------------|-----------|----------|-----------|
| Conditions (high-search) | weekly | 0.95 | Medical guidelines & epidemiology constantly updated |
| Drugs (active medications) | weekly | 0.90 | Drug interactions, adverse events, new data |
| Procedures (common) | monthly | 0.85 | Technique & evidence updates quarterly |
| Procedures (rare) | quarterly | 0.70 | Stable procedures, less frequent updates |
| Clinical Guidelines | weekly | 0.95 | Guidelines updated annually with frequent clarifications |
| Research Summaries | monthly | 0.80 | Evidence evolves, meta-analyses published regularly |
| Providers | daily | 0.60 | Contact info, credentials, affiliations change |
| Organizations | monthly | 0.65 | Location, department, organizational changes |

**Important:** Google ignores priority/changefreq values, but they still signal your site's structure to AI crawlers and can influence crawl budget allocation.

### Sitemap Submission & Index File

```xml
<?xml version="1.0" encoding="UTF-8"?>
<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <sitemap>
    <loc>https://hkg.example.com/sitemap-conditions.xml</loc>
    <lastmod>2026-04-08</lastmod>
  </sitemap>
  <sitemap>
    <loc>https://hkg.example.com/sitemap-drugs.xml</loc>
    <lastmod>2026-04-07</lastmod>
  </sitemap>
  <sitemap>
    <loc>https://hkg.example.com/sitemap-procedures.xml</loc>
    <lastmod>2026-04-05</lastmod>
  </sitemap>
  <!-- Additional category sitemaps -->
</sitemapindex>
```

---

## 4. JSON-LD Schema Markup: Making Entities Machine-Readable

### Why JSON-LD Over Other Formats?

- **AI-preferred format:** Every major AI crawler prefers JSON-LD because it's cleanly separated from HTML
- **Easy to parse:** Simple JSON structure; no need to execute JavaScript
- **Google's recommendation:** JSON-LD is Google's preferred method for implementing schema
- **Zero interference:** Doesn't affect HTML structure or rendering

### Core Medical Entity Types (Schema.org)

HKG will implement these primary Schema.org types:

#### 1. MedicalCondition Pages

```json
{
  "@context": "https://schema.org",
  "@type": "MedicalWebPage",
  "name": "Hypertension",
  "headline": "Hypertension (High Blood Pressure): Comprehensive Clinical Overview",
  "description": "Comprehensive overview of hypertension, including pathophysiology, epidemiology, risk factors, diagnosis, and evidence-based treatment strategies.",
  "url": "https://hkg.example.com/conditions/hypertension",
  "datePublished": "2024-06-15",
  "dateModified": "2026-04-08",
  "author": {
    "@type": "Organization",
    "name": "Healthcare Knowledge Garden",
    "url": "https://hkg.example.com"
  },
  "mainEntity": {
    "@type": "MedicalCondition",
    "name": "Hypertension",
    "description": "Persistently elevated blood pressure (≥130/80 mmHg) affecting systemic health and organ function",
    "code": [
      {
        "@type": "MedicalCode",
        "codingSystem": "ICD-10-CM",
        "codeValue": "I10"
      },
      {
        "@type": "MedicalCode",
        "codingSystem": "SNOMED-CT",
        "codeValue": "38341003"
      }
    ],
    "epidemiology": "Affects ~45% of US adults; leading modifiable risk factor for cardiovascular disease",
    "symptom": [
      {
        "@type": "MedicalSymptom",
        "name": "Often asymptomatic (silent disease)"
      },
      {
        "@type": "MedicalSymptom",
        "name": "Headaches (severe cases)"
      },
      {
        "@type": "MedicalSymptom",
        "name": "Shortness of breath"
      }
    ],
    "possibleTreatment": [
      {
        "@type": "Drug",
        "name": "Lisinopril",
        "drugClass": "ACE Inhibitors"
      },
      {
        "@type": "Drug",
        "name": "Amlodipine",
        "drugClass": "Calcium Channel Blockers"
      }
    ],
    "associatedAnatomy": {
      "@type": "AnatomicalStructure",
      "name": "Cardiovascular System"
    }
  },
  "mainContentOfPage": {
    "@type": "WebPageElement",
    "text": "[Full clinical content about hypertension]"
  },
  "aboutPage": {
    "@type": "Thing",
    "name": "Comprehensive medical information for healthcare professionals and patients"
  }
}
```

#### 2. Drug/Pharmaceutical Entity Pages

```json
{
  "@context": "https://schema.org",
  "@type": "MedicalWebPage",
  "name": "Metformin",
  "headline": "Metformin: Comprehensive Drug Profile, Clinical Use, & Safety",
  "description": "Complete clinical monograph for metformin, including mechanism of action, indications, dosing, adverse effects, drug interactions, and clinical evidence.",
  "url": "https://hkg.example.com/drugs/metformin",
  "datePublished": "2024-05-10",
  "dateModified": "2026-04-08",
  "author": {
    "@type": "Organization",
    "name": "Healthcare Knowledge Garden"
  },
  "mainEntity": {
    "@type": "Drug",
    "name": "Metformin",
    "drugClass": "Biguanide",
    "indication": "Type 2 Diabetes Mellitus, Prediabetes, Polycystic Ovary Syndrome",
    "code": [
      {
        "@type": "MedicalCode",
        "codingSystem": "RxNorm",
        "codeValue": "6809"
      },
      {
        "@type": "MedicalCode",
        "codingSystem": "ATC",
        "codeValue": "A10BA02"
      }
    ],
    "dosageForm": "Tablet, Extended-release tablet, Solution",
    "dosageValue": "500–2550 mg daily (divided doses)",
    "mechanismOfAction": "Decreases hepatic glucose production, improves insulin sensitivity, reduces intestinal glucose absorption",
    "adverseEffect": [
      "Gastrointestinal upset (15–25% of patients)",
      "Lactic acidosis (rare, <10 cases/100,000 patient-years)",
      "Vitamin B12 malabsorption"
    ],
    "drugInteraction": [
      {
        "@type": "Thing",
        "name": "Contrast dye (risk of lactic acidosis)",
        "severity": "Moderate-Severe"
      },
      {
        "@type": "Thing",
        "name": "Cimetidine (increases metformin levels)",
        "severity": "Moderate"
      }
    ],
    "contraindication": [
      "Renal impairment (eGFR <30)",
      "Acute illness, sepsis",
      "Iodinated contrast administration"
    ],
    "ageGroup": "18+ years (pediatric use off-label)",
    "pregnancyCategory": "Category B (generally safe)"
  }
}
```

#### 3. Medical Procedure Pages

```json
{
  "@context": "https://schema.org",
  "@type": "MedicalWebPage",
  "name": "Percutaneous Coronary Intervention",
  "headline": "PCI (Angioplasty & Stenting): Procedure Guide, Indications, & Outcomes",
  "url": "https://hkg.example.com/procedures/pci",
  "dateModified": "2026-04-08",
  "mainEntity": {
    "@type": "MedicalProcedure",
    "name": "Percutaneous Coronary Intervention (PCI)",
    "description": "Catheter-based intervention to open coronary artery stenosis using balloon angioplasty ± stent placement",
    "code": [
      {
        "@type": "MedicalCode",
        "codingSystem": "CPT",
        "codeValue": "92920–92944"
      },
      {
        "@type": "MedicalCode",
        "codingSystem": "ICD-10-PCS",
        "codeValue": "02703ZZ"
      }
    ],
    "procedureType": "Interventional Cardiology",
    "indication": [
      "Acute Myocardial Infarction",
      "Unstable Angina",
      "Stable Angina (select cases)"
    ],
    "complication": [
      "Restenosis (5–10% bare metal stents)",
      "Stent thrombosis (<1%)",
      "Acute coronary occlusion"
    ],
    "successRate": "95–98% angiographic success rate",
    "recurrenceRate": "20–30% at 1 year without optimal medical therapy",
    "specialty": "Interventional Cardiology"
  }
}
```

#### 4. Healthcare Provider/Organization Pages

```json
{
  "@context": "https://schema.org",
  "@type": "MedicalBusiness",
  "name": "Johns Hopkins Cardiac Center",
  "description": "Internationally recognized heart disease treatment and research center",
  "url": "https://hkg.example.com/organizations/johns-hopkins-cardiac",
  "address": {
    "@type": "PostalAddress",
    "streetAddress": "1800 Orleans Street",
    "addressLocality": "Baltimore",
    "addressRegion": "MD",
    "postalCode": "21287",
    "addressCountry": "US"
  },
  "telephone": "+1-410-955-5000",
  "medicalSpecialty": [
    "Cardiology",
    "Interventional Cardiology",
    "Cardiac Surgery",
    "Heart Failure"
  ],
  "areaServed": "United States, International",
  "certification": [
    {
      "@type": "Thing",
      "name": "The Joint Commission Accreditation",
      "sameAs": "https://www.jointcommission.org"
    }
  ],
  "availableService": [
    {
      "@type": "MedicalBusiness",
      "name": "Cardiac Catheterization Laboratory"
    },
    {
      "@type": "MedicalBusiness",
      "name": "Electrophysiology Laboratory"
    }
  ],
  "staff": [
    {
      "@type": "Physician",
      "name": "Dr. Jennifer Smith, MD",
      "specialty": "Interventional Cardiology",
      "medicalLicense": "MD123456"
    }
  ]
}
```

### Critical Implementation Details

**Placement:** Include JSON-LD in the `<head>` section of every entity page (before closing `</head>`).

**Validation:** Use [Google's Rich Results Test](https://search.google.com/test/rich-results) to validate markup.

**Nesting:** Link related entities—conditions mention associated drugs, procedures, providers; drugs reference conditions and interactions; procedures reference anatomy and specialty.

**Medical Codes:** ALWAYS include structured medical codes (ICD-10, RxNorm, SNOMED, CPT) in the `code` field.

---

## 5. How AI Crawlers Discover & Cite Sources

### Perplexity's Three-Layer Source Selection Algorithm

Research reveals Perplexity uses a sophisticated ranking system:

**Layer 1: Real-time Web Search**
- Performs live search for user query
- Initial retrieval of candidate sources

**Layer 2: Authority & Trust Scoring**
- Maintains manually curated authority domain lists
- Boosts GitHub, Amazon, LinkedIn, Reddit-associated content
- Evaluates domain age, SSL certificate, institutional affiliation
- Scores author credentials and affiliations

**Layer 3: XGBoost Quality Gate (L3)**
- Filters sources that don't meet entity clarity thresholds
- Evaluates content structure and readability
- Confirms authoritativeness signals
- **Only top-ranking sources survive this gate**

### What Makes Content "Citeable"

Research analyzing 10,000+ AI citations reveals these factors drive citation selection:

| Factor | Citation Lift | Priority |
|--------|---|---|
| Direct answer placed immediately after heading | +40% | CRITICAL |
| 40–80 word standalone answer block | +35% | CRITICAL |
| Clear heading-question format | +45% | CRITICAL |
| Author expertise documented | +30% | HIGH |
| Internal source citations | +30% | HIGH |
| Expert quotations | +30% | HIGH |
| Statistics & original data | +30% | HIGH |
| Content updated in last 30 days | +45% | CRITICAL |
| Content updated in last 90 days | +35% | HIGH |
| Clean structured HTML (no JavaScript injection) | +25% | MEDIUM |
| JSON-LD schema markup present | +25% | MEDIUM |

**Key finding:** Content freshness beats SEO authority. A 3-week-old article from an unknown source beats a 2-year-old article from Mayo Clinic.

### How Each AI System Evaluates Sources

#### Claude (Anthropic)
- Prioritizes sources with clear authorship and institutional affiliation
- Respects structured data (JSON-LD) heavily
- Favors pages with recent modification dates
- Cites content with explicit source metadata

#### ChatGPT (OpenAI)
- Weights domain authority and backlink profile
- Prefers news and journalistic sources
- Values content freshness (daily updates signal reliability)
- Cites pages with rich snippets and structured data

#### Perplexity
- Uses three-layer algorithm described above
- Heavily weights content clarity and direct answers
- Applies topic multipliers (amplifies tech/science/business; suppresses entertainment/sports)
- Prioritizes recent publications (news > established references)
- Citations appear visually next to answers

### The E-E-A-T Framework

All AI systems evaluate E-E-A-T signals:

- **Experience:** Author has lived/professional experience with topic (physicians writing about medicine)
- **Expertise:** Documented credentials, certifications, qualifications
- **Authority:** Recognition by institutions, awards, peer citations
- **Trustworthiness:** Transparent about author/organization, discloses conflicts of interest, cites sources

**HKG Strategy:** Every entity page author should include short bio with credentials; organization pages should display certification and accreditation; content should cite primary sources.

---

## 6. Content Structure for Maximum AI Citability

### The "Citation Capsule" Format

This is the most AI-citeable content structure:

```html
<h2>What is Hypertension?</h2>

<p style="font-weight: bold; margin: 1rem 0;">
  Hypertension is persistently elevated blood pressure (≥130/80 mmHg) 
  affecting 45% of US adults and representing the leading modifiable 
  risk factor for cardiovascular disease.
</p>

<p>
  [Supporting details, pathophysiology, epidemiology, additional context...]
</p>
```

### Answer Capsule Rules

1. **Place immediately after heading** (no preamble)
2. **40–80 words** (comprehensive but scannable)
3. **Standalone paragraph** (must make sense if extracted alone)
4. **Direct answer first** (no "Well, it depends...")
5. **Key numbers** (statistics, prevalence, mortality)
6. **Clinical relevance** (why does this matter to a physician/patient?)

### Page Structure Template for Conditions

```
# [Condition Name]

> One-sentence clinical summary (for llms.txt)

## What is [Condition]?
**[Citation capsule: 40–80 words with definition, prevalence, clinical significance]**

Supporting paragraphs with epidemiology, risk factors, pathophysiology

## Clinical Features & Diagnosis

**[Citation capsule: diagnostic criteria, sensitivity/specificity of tests]**

Detailed diagnostic algorithms, imaging findings, lab values

## Medical Management

**[Citation capsule: evidence-based first-line treatments, success rates]**

Detailed pharmacotherapy, dosing, monitoring, alternatives

## Procedural Interventions
**[Citation capsule: when, success rates, complications]**

## Prognosis & Complications

**[Citation capsule: mortality, morbidity, long-term outcomes]**

## Key References & Clinical Guidelines

[Links to primary literature, systematic reviews, clinical guidelines]
```

### Content Freshness Requirements

To maximize AI citability:

- **Update every condition page:** Every 30 days (statistics, new guidelines)
- **Update every drug page:** Every 7–14 days (new adverse event data, interactions)
- **Update every procedure page:** Every 30–90 days (technique updates, outcomes data)
- **Update every guideline page:** Weekly (monitor ACC/AHA, ESC, specialty societies)

**Strategy:** Implement automated checks for:
- New guideline releases from ACC, AHA, ESC, ASPC, etc.
- New drug approvals and withdrawals
- Updated epidemiological data
- New clinical trial results

---

## 7. Linking & Cross-Reference Architecture

### The Knowledge Graph Within HKG

HKG must function as an internal knowledge graph where entities link to related entities:

**Condition pages link to:**
- Associated drugs (treatments, risk factors)
- Procedures (diagnostic, therapeutic)
- Comorbid conditions
- Related specialties

**Drug pages link to:**
- Indicated conditions
- Drug interactions (other drugs)
- Related pharmacological classes
- Clinical evidence (trials, meta-analyses)

**Procedure pages link to:**
- Indications (conditions)
- Associated medications
- Required specialties
- Complications (conditions that can result)

**Provider pages link to:**
- Specialty (condition pages they treat)
- Organization (hospital/clinic)
- Certifications & credentials

### Implementation via JSON-LD

Use `sameAs`, `relatedLink`, and nested `@type` references:

```json
{
  "@context": "https://schema.org",
  "@type": "MedicalCondition",
  "name": "Type 2 Diabetes",
  "possibleTreatment": [
    {
      "@type": "Drug",
      "name": "Metformin",
      "url": "https://hkg.example.com/drugs/metformin"
    }
  ],
  "associatedCondition": [
    {
      "@type": "MedicalCondition",
      "name": "Hypertension",
      "url": "https://hkg.example.com/conditions/hypertension"
    },
    {
      "@type": "MedicalCondition",
      "name": "Chronic Kidney Disease",
      "url": "https://hkg.example.com/conditions/ckd"
    }
  ]
}
```

---

## 8. Medical Code Integration Strategy

### The Medical Code Taxonomy

HKG must handle multiple overlapping medical coding systems:

| System | Purpose | Scope | Use Case |
|--------|---------|-------|----------|
| **ICD-10-CM** | Diagnosis coding | 70,000+ conditions, disorders | Claims, epidemiology |
| **ICD-10-PCS** | Procedure coding | 70,000+ procedures | Surgical procedures |
| **CPT** | Current Procedural Terminology | 10,000+ procedures | Billing, interventions |
| **RxNorm** | Drug naming standard | 20,000+ medications | Prescription, clinical |
| **SNOMED CT** | Comprehensive clinical terms | 350,000+ concepts | EHR documentation |
| **LOINC** | Lab test ordering & results | 95,000+ tests | Lab values, observations |
| **MeSH** | Medical Subject Headings | 29,000+ terms | Literature indexing |

### HKG Code Architecture

For each condition/drug/procedure, include:

```json
"code": [
  {
    "@type": "MedicalCode",
    "codingSystem": "ICD-10-CM",
    "codeValue": "E11.9",
    "name": "Type 2 Diabetes Mellitus without Complications"
  },
  {
    "@type": "MedicalCode",
    "codingSystem": "SNOMED-CT",
    "codeValue": "44054006",
    "name": "Diabetes Mellitus Type 2"
  },
  {
    "@type": "MedicalCode",
    "codingSystem": "MeSH",
    "codeValue": "D003924",
    "name": "Diabetes Mellitus, Type 2"
  }
]
```

### Benefits of Code-Linked Pages

1. **AI understanding:** Codes disambiguate medical terms (is "diabetes" type 1, type 2, gestational?)
2. **Clinical precision:** Enables linking between different systems
3. **Interoperability:** Physicians can match clinical records to HKG entities
4. **SEO for AI:** Structured codes are signals of clinical authority

---

## 9. Healthcare Website Benchmarks: Learning from Leaders

### Current Authority Hierarchy in AI Citations

**Health information sources dominate AI citations:**

1. **Government institutions:** NIH (~39% of health citations)
2. **Commercial aggregators:** Healthline (~15%), WebMD (~12%)
3. **Academic medical centers:** Mayo Clinic (~14.8%), Cleveland Clinic (~13.8%)
4. **Specialty societies:** ACC/AHA, ESC (variable by query)
5. **Individual physician blogs/sites:** <5% of citations

### Why These Sites Dominate

**Mayo Clinic approach:**
- Exhaustive condition pages (2000+ word averages)
- Regular updates (quarterly for common conditions)
- Clear author credentials (verified physicians)
- High-quality images and diagrams
- Patient + professional versions

**WebMD approach:**
- Encyclopedic coverage (70,000+ articles)
- Medical review boards
- User-friendly explanations
- Strong internal linking

**NIH/PubMed approach:**
- Academic rigor (primary literature)
- Citation standards (every claim sourced)
- Free/open access
- Institutional authority

### HKG's Competitive Advantage

HKG can exceed these by:
- **Structured data density:** More comprehensive schema than any competitor
- **Code integration:** Explicit linking to ICD-10, RxNorm, SNOMED, CPT
- **Freshness:** Daily/weekly updates vs. quarterly
- **AI-native design:** Built for LLM consumption, not human reading
- **Entity precision:** Separate pages for each drug/dose/indication variant
- **Clinical depth:** Physician-authored with board certification verification

---

## 10. Monitoring & Optimization: "AI Citation Performance"

### Key Metrics to Track

| Metric | Definition | Tool | Target |
|--------|-----------|------|--------|
| **AI Citation Frequency** | # times HKG page cited per month | Manual testing (Claude, ChatGPT, Perplexity) | +50% YoY |
| **AI Citation Share** | % of health queries citing HKG vs. competitors | Citation monitoring tools | Top 5% |
| **Crawler Visit Frequency** | Visits from GPTBot, ClaudeBot, PerplexityBot per week | Server logs, Google Search Console | >100/week |
| **Page Freshness Score** | Last modification date relative to content type | Automated monitoring | 0–30 days |
| **Schema Validation Rate** | % of pages with valid JSON-LD schema | Automated crawl | 100% |
| **Citation Capsule Presence** | % of entity pages with >40-word direct answer | Automated text analysis | 100% |
| **Internal Link Density** | Links to related entities per page | Site analysis | 5–10 per page |
| **Code Coverage** | % of entities with ICD/RxNorm/CPT codes linked | Database audit | 95%+ |

### Monthly Monitoring Process

1. **Manual testing:** Query Claude, ChatGPT, Perplexity with 10–20 representative medical questions
   - "What is the treatment for hypertension?"
   - "Side effects of metformin?"
   - "When is cardiac catheterization indicated?"
2. **Record:** Which sources are cited, citation text, position in answer
3. **Analyze:** Trends in HKG citation vs. competitors
4. **Optimization:** Update pages that are cited less frequently than target
5. **Report:** Monthly dashboard to leadership

### Quarterly Content Refresh Cycle

- **Week 1:** Identify underperforming pages (low citation count)
- **Week 2:** Update clinical content, add new references, refresh data
- **Week 3:** Audit schema markup, add/correct medical codes
- **Week 4:** Verify crawl, update modified dates, submit sitemaps

---

## 11. Implementation Roadmap

### Phase 1: Foundation (Months 1–3)

- [ ] Implement `/llms.txt` with top 50 conditions, 100 drugs, 30 procedures
- [ ] Create robots.txt inviting all AI crawlers
- [ ] Set up XML sitemap infrastructure (category-specific sitemaps)
- [ ] Audit and validate JSON-LD schema on all entity pages
- [ ] Establish content freshness schedule (update calendars)

### Phase 2: Scale (Months 4–6)

- [ ] Expand `/llms-full.txt` to top 500 conditions, 1000 drugs
- [ ] Implement citation capsule format on all pages
- [ ] Link medical codes (ICD-10, RxNorm, SNOMED) to every entity
- [ ] Build internal knowledge graph linking (condition→drug→procedure)
- [ ] Begin automated monitoring of AI citations

### Phase 3: Optimization (Months 7–12)

- [ ] Implement content freshness automation (weekly condition updates, etc.)
- [ ] Deploy quarterly schema audit and correction process
- [ ] Analyze citation patterns, optimize underperforming pages
- [ ] Expand coverage to rare conditions, specialized procedures
- [ ] Integrate with clinical guidelines feeds (ACC/AHA, ESC)

### Phase 4: Enterprise (Year 2+)

- [ ] Reach 10,000+ condition pages with complete schema
- [ ] Reach 50,000+ drug variants with full pharmacology
- [ ] Real-time guideline integration
- [ ] AI-specific landing pages for high-traffic queries
- [ ] Partnership discussions (from strength, not need)

---

## 12. Technical Debt & Gotchas

### Common Mistakes to Avoid

1. **JavaScript-Injected Schema:** Don't use JavaScript to add JSON-LD. AI crawlers can't execute JS. All schema must be in the initial HTML response.

2. **Outdated Medical Information:** AI systems penalize pages with old data. A 2-year-old drug interaction study will be passed over for a 3-week-old meta-analysis.

3. **Unstructured Medical Codes:** Random mention of "ICD-10: E11.9" in text is invisible to AI. Use structured schema `"code"` fields.

4. **Broken Internal Links:** A condition page linking to non-existent drug page breaks the knowledge graph. Validate all inter-entity references.

5. **Missing Author/Authority Signals:** Pages without author names and credentials are cited 30% less frequently. Every page needs a physician byline.

6. **Overstuffing Keywords:** "Hypertension treatment hypertension blood pressure treatment" reads as spam to AI systems. Write naturally; let schema handle entity disambiguation.

7. **Ignoring Freshness:** Publishing a comprehensive page then ignoring it for 2 years guarantees it won't be cited. Set up automated reminder calendars for quarterly updates.

### Schema Validation Checklist

- [ ] No JavaScript required to render JSON-LD
- [ ] All schema fields include `@type` and `name` properties
- [ ] Medical codes reference recognized systems (ICD-10-CM, RxNorm, SNOMED CT)
- [ ] All internal links are to valid entity pages
- [ ] `dateModified` timestamp is within 90 days for high-priority pages
- [ ] Author information includes credentials/affiliation
- [ ] No broken or relative URLs in `url` fields
- [ ] Schema validates without errors in [Google Rich Results Test](https://search.google.com/test/rich-results)

---

## 13. Competitive Analysis: Why HKG Wins

### Current State: AI Citations Are Concentrated

99% of health AI citations come from <50 sources:
- NIH/PubMed (27%)
- Mayo Clinic (14.8%)
- Cleveland Clinic (13.8%)
- WebMD (12%)
- Healthline (7%)
- CDC, WHO, AHA, etc. (rest)

**Barrier to entry:** These sites have 30+ years of authority, massive backlinking, institutional credibility.

### HKG's Counter-Strategy: Structure Over Authority

Instead of competing on legacy authority, HKG wins on **algorithmic citability**:

| Factor | Traditional Sites | HKG | Winner |
|--------|---|---|---|
| Domain authority (backlinks) | Mayo: 94/100 | HKG: 20/100 (initially) | Mayo |
| Content freshness | Quarterly | Daily/weekly | **HKG** |
| Structured data density | Limited schema | Comprehensive JSON-LD | **HKG** |
| Medical codes | Implicit, few | Explicit ICD/RxNorm/SNOMED | **HKG** |
| Citation capsule format | Some pages | Every page | **HKG** |
| Answer directness | Variable | Standardized | **HKG** |
| Internal knowledge graph | Weak linking | Dense entity cross-references | **HKG** |
| llms.txt adoption | 0% | 100% | **HKG** |

**Result:** Within 18–24 months, HKG should see:
- 10–15% of health-related AI citations (vs. <1% today)
- Higher citation rates per page for common conditions
- Dominant position for rare conditions (less competition)
- Trusted status with AI systems (algorithmic preference)

---

## 14. Success Metrics & KPIs

### Year 1 Goals

| KPI | Q1 | Q2 | Q3 | Q4 |
|-----|----|----|----|----|
| **AI Citation Frequency** | Baseline | +25% | +50% | +75% |
| **Pages with Valid Schema** | 80% | 95% | 98% | 100% |
| **Content Freshness (0–30 days)** | 40% | 60% | 75% | 85% |
| **Crawler Visits/Week** | 50 | 150 | 300 | 500+ |
| **llms.txt Coverage** | 50 entities | 200 entities | 500 entities | 1000+ entities |
| **Internal Link Density** | 3/page | 5/page | 7/page | 10/page |

### Year 2–3 Goals

- Position HKG as "the" medical knowledge graph for AI assistants
- Achieve 15–20% share of health-related AI citations
- Maintain 100% schema coverage with zero validation errors
- Achieve 100% "freshness within 14 days" for top 500 entities
- Deploy real-time guideline integration
- Reach profitability through:
  - API access for healthcare systems
  - Institutional subscriptions for physicians
  - Data partnerships with AI companies (from strength)

---

## Conclusion: The Sleeper Play

HKG's AI citation strategy isn't about partnerships or persuading OpenAI to integrate HKG's content. It's about building pages so well-structured, so authoritative, so fresh, and so machine-readable that **AI assistants have no choice but to cite HKG**.

Every entity page becomes:
1. **Discoverable** (llms.txt, robots.txt, sitemaps)
2. **Machine-readable** (comprehensive JSON-LD schema)
3. **Citable** (direct answer capsules, clear authorship, E-E-A-T signals)
4. **Relevant** (daily-weekly updates, medical codes, knowledge graph linking)
5. **Trustworthy** (physician authorship, primary source citations, institutional backing)

By 2027, when physicians and patients ask Claude, ChatGPT, or Perplexity medical questions, HKG will appear alongside Mayo Clinic and NIH—not through negotiation, but through excellence.

**That's the strategy.**

---

## Sources & References

- [llms.txt Official Specification](https://llmstxt.org/) — The authoritative standard
- [Semrush: What Is LLMs.txt & Should You Use It?](https://www.semrush.com/blog/llms-txt/)
- [Fern: llms.txt and llms-full.txt](https://buildwithfern.com/learn/docs/ai-features/llms-txt)
- [Perplexity AI Citation Algorithm Research](https://www.trysight.ai/blog/how-perplexity-ai-selects-sources) — How Perplexity chooses sources
- [AI Crawlers & robots.txt Guide](https://momenticmarketing.com/blog/ai-search-crawlers-bots) — Crawler user-agent strings
- [Schema.org Health & Medical Types](https://schema.org/docs/meddocs.html) — Official schema documentation
- [Google Structured Data in AI Search](https://www.brightedge.com/blog/structured-data-ai-search-era) — 36% citation lift with schema
- [AI Content Freshness Study](https://www.thehoth.com/blog/content-freshness-seo/) — Freshness impact on citations
- [Medical Coding Systems Reference](https://www.imohealth.com/resources/medical-coding-systems-explained-icd-10-cm-cpt-snomed-and-others/) — ICD-10, RxNorm, SNOMED explained
- [How to Get Cited by ChatGPT, Perplexity, Claude](https://ideadigital.agency/en/blog/how-make-ai-systems-cite-your-website/) — Practical citation strategies


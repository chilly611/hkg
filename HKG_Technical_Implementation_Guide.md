# Healthcare Knowledge Garden
## Technical Implementation Guide: AI Citation Architecture

**Version:** 1.0 | **Last Updated:** April 2026

---

## Table of Contents

1. [Quick Start: Entity Page Template](#quick-start)
2. [robots.txt Configuration](#robotstxt)
3. [XML Sitemap Generation](#sitemaps)
4. [JSON-LD Schema Examples](#jsonld)
5. [llms.txt File Structure](#llmstxt)
6. [Content Freshness Automation](#freshness)
7. [Crawl Testing & Validation](#testing)

---

## Quick Start: Entity Page Template {#quick-start}

### Directory Structure

```
/hkg-platform
├── /public
│   ├── /conditions
│   │   ├── hypertension.html
│   │   ├── hypertension.md
│   │   ├── diabetes-type-2.html
│   │   └── ...
│   ├── /drugs
│   │   ├── metformin.html
│   │   ├── metformin.md
│   │   ├── lisinopril.html
│   │   └── ...
│   ├── /procedures
│   ├── /providers
│   ├── /organizations
│   ├── llms.txt
│   ├── llms-full.txt
│   ├── robots.txt
│   ├── sitemap.xml
│   ├── sitemap-conditions.xml
│   ├── sitemap-drugs.xml
│   └── sitemap-procedures.xml
├── /content-management
│   ├── /templates
│   ├── /schemas
│   └── /update-schedules
└── /monitoring
    ├── /citation-tracking
    ├── /crawler-logs
    └── /schema-validation
```

### Minimal HTML Entity Page Template

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Hypertension: Clinical Overview | Healthcare Knowledge Garden</title>
    <meta name="description" content="Comprehensive clinical overview of hypertension, including pathophysiology, diagnosis, and evidence-based treatment.">
    
    <!-- JSON-LD Schema Markup (MUST be in head, NOT injected via JavaScript) -->
    <script type="application/ld+json">
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
        "description": "Persistently elevated blood pressure (≥130/80 mmHg) affecting systemic health and organ function.",
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
        ]
      }
    }
    </script>
</head>

<body>
    <header>
        <h1>Hypertension (High Blood Pressure)</h1>
        <p class="subtitle">Comprehensive Clinical Overview</p>
    </header>

    <main>
        <section>
            <h2>Definition & Epidemiology</h2>
            
            <!-- CITATION CAPSULE: 40-80 word direct answer -->
            <p class="citation-capsule">
                Hypertension is persistently elevated blood pressure (systolic ≥130 mmHg or 
                diastolic ≥80 mmHg) affecting approximately 45% of U.S. adults and representing 
                the leading modifiable risk factor for cardiovascular disease, stroke, and chronic 
                kidney disease. It is often asymptomatic, earning the term "silent killer."
            </p>

            <p>
                [Supporting paragraphs: detailed epidemiology, prevalence by demographic, 
                burden of disease, mortality statistics, risk factors...]
            </p>
        </section>

        <section>
            <h2>Pathophysiology</h2>
            
            <!-- CITATION CAPSULE -->
            <p class="citation-capsule">
                Hypertension results from increased peripheral vascular resistance and/or 
                elevated cardiac output. Primary (essential) hypertension (90–95% of cases) 
                involves dysfunction of the renin-angiotensin-aldosterone system (RAAS), 
                sympathetic nervous system dysregulation, and arterial stiffness. Secondary 
                hypertension stems from identifiable causes including renal disease, 
                endocrine disorders, and medications.
            </p>

            [Detailed mechanism sections...]
        </section>

        <section>
            <h2>Clinical Diagnosis</h2>
            
            <!-- CITATION CAPSULE -->
            <p class="citation-capsule">
                Diagnosis requires blood pressure ≥130/80 mmHg documented on ≥2 separate 
                occasions. Initial evaluation includes history, physical examination, and 
                screening for secondary causes and target organ damage. Ambulatory blood 
                pressure monitoring (ABPM) helps diagnose white-coat hypertension and 
                assess BP variability.
            </p>

            [Diagnostic algorithms, imaging, lab work...]
        </section>

        <section>
            <h2>Medical Management</h2>
            
            <!-- CITATION CAPSULE -->
            <p class="citation-capsule">
                First-line pharmacotherapy includes ACE inhibitors, angiotensin receptor 
                blockers (ARBs), calcium channel blockers, and thiazide diuretics. For 
                uncomplicated hypertension, initial monotherapy targets BP <130/80 mmHg; 
                combination therapy is indicated for stage 2 hypertension. Response rates 
                vary (40–60% monotherapy; 80%+ dual therapy).
            </p>

            [Drug classes, dosing, combinations, monitoring, lifestyle...]
        </section>

        <section>
            <h2>Complications & Prognosis</h2>
            
            <!-- CITATION CAPSULE -->
            <p class="citation-capsule">
                Untreated hypertension increases risk of myocardial infarction, stroke 
                (2–4x risk), heart failure, atrial fibrillation, and chronic kidney disease. 
                With treatment, cardiovascular mortality decreases by 10–15% per 10 mmHg 
                systolic BP reduction. Long-term prognosis depends on age, other 
                comorbidities, and treatment adherence.
            </p>

            [Target organ damage, heart failure, stroke risk...]
        </section>

        <section>
            <h2>Related Entities</h2>
            
            <h3>Associated Conditions</h3>
            <ul>
                <li><a href="/conditions/left-ventricular-hypertrophy">Left Ventricular Hypertrophy</a></li>
                <li><a href="/conditions/chronic-kidney-disease">Chronic Kidney Disease</a></li>
                <li><a href="/conditions/atrial-fibrillation">Atrial Fibrillation</a></li>
                <li><a href="/conditions/metabolic-syndrome">Metabolic Syndrome</a></li>
            </ul>

            <h3>Pharmacological Treatments</h3>
            <ul>
                <li><a href="/drugs/lisinopril">Lisinopril (ACE Inhibitor)</a></li>
                <li><a href="/drugs/amlodipine">Amlodipine (Calcium Channel Blocker)</a></li>
                <li><a href="/drugs/hydrochlorothiazide">Hydrochlorothiazide (Thiazide)</a></li>
                <li><a href="/drugs/losartan">Losartan (ARB)</a></li>
            </ul>

            <h3>Diagnostic Procedures</h3>
            <ul>
                <li><a href="/procedures/ambulatory-blood-pressure-monitoring">Ambulatory BP Monitoring</a></li>
                <li><a href="/procedures/echocardiography">Echocardiography</a></li>
                <li><a href="/procedures/renal-artery-imaging">Renal Artery Imaging</a></li>
            </ul>
        </section>

        <section>
            <h2>Clinical References</h2>
            
            <h3>Guidelines</h3>
            <ul>
                <li>ACC/AHA Hypertension Guidelines (2024)</li>
                <li>ESC/ESH Hypertension Guidelines (2024)</li>
                <li>ADA Standards of Care (Hypertension in Diabetes)</li>
            </ul>

            <h3>Key Trials & Evidence</h3>
            <ul>
                <li>SPRINT Trial: Intensive BP control in non-diabetic patients</li>
                <li>ACCORD Trial: Hypertension management in diabetic patients</li>
                <li>Meta-analyses from Cochrane Collaboration</li>
            </ul>
        </section>
    </main>

    <footer>
        <p><strong>Author:</strong> Dr. Jennifer Smith, MD, Cardiology Board-Certified</p>
        <p><strong>Last Updated:</strong> 2026-04-08</p>
        <p><strong>Next Scheduled Update:</strong> 2026-05-08</p>
    </footer>
</body>

</html>
```

### CSS for Citation Capsules

```css
.citation-capsule {
    font-weight: 500;
    border-left: 4px solid #0066cc;
    padding-left: 1rem;
    margin: 1.5rem 0;
    background-color: #f0f6ff;
    padding: 1rem;
    border-radius: 4px;
    line-height: 1.6;
}

.citation-capsule::before {
    content: "📌 Key Point: ";
    font-weight: bold;
    color: #0066cc;
}
```

---

## robots.txt Configuration {#robotstxt}

### Strategic robots.txt for AI Citation Maximization

**Location:** `/robots.txt` (at domain root)

```
# Healthcare Knowledge Garden robots.txt
# Strategic: INVITE AI crawlers to discover and cite our content
# Created: April 2026

# ============================================
# SECTION 1: INVITE ALL AI CRAWLERS
# ============================================

# OpenAI GPT Training Crawler
User-agent: GPTBot
Allow: /

# OpenAI Real-Time Retrieval (used when users ask ChatGPT questions)
User-agent: ChatGPT-User
Allow: /

# Anthropic Claude Training
User-agent: ClaudeBot
Allow: /

# Anthropic Real-Time Search
User-agent: Claude-SearchBot
Allow: /

# Perplexity AI (most active health query crawler)
User-agent: PerplexityBot
Allow: /

# Amazon Alexa & ML training
User-agent: Amazonbot
Allow: /

# Apple Siri & on-device ML
User-agent: Applebot
Allow: /

# Common Crawl (archive.org, training data)
User-agent: CCBot
Allow: /

# ByteDance (TikTok search models)
User-agent: Bytespider
Allow: /

# Google Bot (traditional search + Gemini)
User-agent: Googlebot
Allow: /

# Bing Bot
User-agent: Bingbot
Allow: /

# ============================================
# SECTION 2: DEFAULT POLICY FOR ALL BOTS
# ============================================

User-agent: *
Allow: /

# Block only truly private/internal content
Disallow: /admin/
Disallow: /internal/
Disallow: /temp/
Disallow: /private/
Disallow: /*.pdf$ # If PDF versions are internal only
Disallow: /staging/

# ============================================
# SECTION 3: llms.txt & llms-full.txt
# ============================================

# CRITICAL: These files are always accessible to AI crawlers
# Do NOT block these files under any circumstance
Allow: /llms.txt
Allow: /llms-full.txt

# ============================================
# SECTION 4: SITEMAP LOCATIONS
# ============================================

# Direct crawlers to our categorized sitemaps
Sitemap: https://hkg.example.com/sitemap.xml
Sitemap: https://hkg.example.com/sitemap-conditions.xml
Sitemap: https://hkg.example.com/sitemap-drugs.xml
Sitemap: https://hkg.example.com/sitemap-procedures.xml
Sitemap: https://hkg.example.com/sitemap-providers.xml
Sitemap: https://hkg.example.com/sitemap-organizations.xml

# ============================================
# SECTION 5: CRAWL DELAY
# ============================================

# Don't throttle AI crawlers; we WANT them to crawl aggressively
# Only apply crawl delay to less important crawlers if needed
# (Omit this section entirely if you want maximum crawl speed)

Crawl-delay: 0

# ============================================
# SECTION 6: OPTIONAL: TRAINING DATA EXCLUSION
# ============================================

# Uncomment this section IF you want to block training crawlers
# (but allow real-time retrieval for user queries)
# NOTE: This is NOT recommended for HKG's citation strategy
#
# User-agent: GPTBot
# Disallow: /
#
# User-agent: ClaudeBot
# Disallow: /
#
# # But ALWAYS allow real-time retrieval crawlers
# User-agent: ChatGPT-User
# Allow: /
#
# User-agent: Claude-SearchBot
# Allow: /

# ============================================
# END robots.txt
```

### Verification

Test your robots.txt at:
- [Google Search Console](https://search.google.com/search-console/) → URL Inspection → Check robots.txt
- [robots.txt Tester](https://www.seobility.net/en/robotstxt-checker/)

---

## XML Sitemap Generation {#sitemaps}

### Master Sitemap Index

**File:** `/sitemap.xml`

```xml
<?xml version="1.0" encoding="UTF-8"?>
<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <!-- Master index listing all category-specific sitemaps -->
  
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
    <lastmod>2026-04-06</lastmod>
  </sitemap>

  <sitemap>
    <loc>https://hkg.example.com/sitemap-providers.xml</loc>
    <lastmod>2026-04-08</lastmod>
  </sitemap>

  <sitemap>
    <loc>https://hkg.example.com/sitemap-organizations.xml</loc>
    <lastmod>2026-04-01</lastmod>
  </sitemap>

  <sitemap>
    <loc>https://hkg.example.com/sitemap-guidelines.xml</loc>
    <lastmod>2026-04-08</lastmod>
  </sitemap>

  <sitemap>
    <loc>https://hkg.example.com/sitemap-research.xml</loc>
    <lastmod>2026-04-05</lastmod>
  </sitemap>

</sitemapindex>
```

### Category-Specific Sitemap: Conditions

**File:** `/sitemap-conditions.xml`

```xml
<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  
  <!-- High-traffic condition: Update weekly -->
  <url>
    <loc>https://hkg.example.com/conditions/hypertension</loc>
    <lastmod>2026-04-08</lastmod>
    <changefreq>weekly</changefreq>
    <priority>0.95</priority>
  </url>

  <!-- High-traffic condition: Update weekly -->
  <url>
    <loc>https://hkg.example.com/conditions/type-2-diabetes</loc>
    <lastmod>2026-04-08</lastmod>
    <changefreq>weekly</changefreq>
    <priority>0.95</priority>
  </url>

  <!-- Medium-traffic condition: Update monthly -->
  <url>
    <loc>https://hkg.example.com/conditions/chronic-kidney-disease</loc>
    <lastmod>2026-03-15</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.85</priority>
  </url>

  <!-- Low-traffic condition: Update quarterly -->
  <url>
    <loc>https://hkg.example.com/conditions/porphyria-cutanea-tarda</loc>
    <lastmod>2025-12-01</lastmod>
    <changefreq>quarterly</changefreq>
    <priority>0.70</priority>
  </url>

  <!-- Repeat for all 10,000+ conditions -->

</urlset>
```

### Category-Specific Sitemap: Drugs

**File:** `/sitemap-drugs.xml` (partial example)

```xml
<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  
  <!-- Common drug: Weekly updates (new adverse events, interactions) -->
  <url>
    <loc>https://hkg.example.com/drugs/metformin</loc>
    <lastmod>2026-04-08</lastmod>
    <changefreq>weekly</changefreq>
    <priority>0.95</priority>
  </url>

  <!-- Common drug: Weekly updates -->
  <url>
    <loc>https://hkg.example.com/drugs/lisinopril</loc>
    <lastmod>2026-04-08</lastmod>
    <changefreq>weekly</changefreq>
    <priority>0.92</priority>
  </url>

  <!-- Specialty drug: Monthly updates -->
  <url>
    <loc>https://hkg.example.com/drugs/dupilumab</loc>
    <lastmod>2026-03-20</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.80</priority>
  </url>

  <!-- Niche drug: Quarterly updates -->
  <url>
    <loc>https://hkg.example.com/drugs/ivermectin</loc>
    <lastmod>2025-12-15</lastmod>
    <changefreq>quarterly</changefreq>
    <priority>0.65</priority>
  </url>

</urlset>
```

### Python Script: Auto-Generate Sitemaps

```python
#!/usr/bin/env python3
"""
Auto-generate XML sitemaps for HKG entity pages
Scans database for entities, creates category-specific sitemaps
"""

import xml.etree.ElementTree as ET
from datetime import datetime
import os

def create_sitemap_index(base_url, categories):
    """Create master sitemap index"""
    
    root = ET.Element('sitemapindex')
    root.set('xmlns', 'http://www.sitemaps.org/schemas/sitemap/0.9')
    
    for category in categories:
        sitemap = ET.SubElement(root, 'sitemap')
        
        loc = ET.SubElement(sitemap, 'loc')
        loc.text = f"{base_url}/sitemap-{category}.xml"
        
        lastmod = ET.SubElement(sitemap, 'lastmod')
        lastmod.text = datetime.now().strftime('%Y-%m-%d')
    
    tree = ET.ElementTree(root)
    tree.write('/path/to/public/sitemap.xml', encoding='utf-8', xml_declaration=True)
    print("✓ Created sitemap.xml")


def create_category_sitemap(base_url, category, entities):
    """Create category-specific sitemap
    
    entities = [
        {
            'slug': 'hypertension',
            'lastmod': '2026-04-08',
            'changefreq': 'weekly',
            'priority': 0.95
        },
        ...
    ]
    """
    
    root = ET.Element('urlset')
    root.set('xmlns', 'http://www.sitemaps.org/schemas/sitemap/0.9')
    
    for entity in entities:
        url_elem = ET.SubElement(root, 'url')
        
        loc = ET.SubElement(url_elem, 'loc')
        loc.text = f"{base_url}/{category}/{entity['slug']}"
        
        lastmod = ET.SubElement(url_elem, 'lastmod')
        lastmod.text = entity.get('lastmod', datetime.now().strftime('%Y-%m-%d'))
        
        changefreq = ET.SubElement(url_elem, 'changefreq')
        changefreq.text = entity.get('changefreq', 'monthly')
        
        priority = ET.SubElement(url_elem, 'priority')
        priority.text = str(entity.get('priority', 0.7))
    
    filename = f'/path/to/public/sitemap-{category}.xml'
    tree = ET.ElementTree(root)
    tree.write(filename, encoding='utf-8', xml_declaration=True)
    print(f"✓ Created sitemap-{category}.xml ({len(entities)} URLs)")


# Usage
if __name__ == '__main__':
    BASE_URL = 'https://hkg.example.com'
    CATEGORIES = ['conditions', 'drugs', 'procedures', 'providers', 'organizations']
    
    # Create master index
    create_sitemap_index(BASE_URL, CATEGORIES)
    
    # Query database and create category sitemaps
    # (Pseudo-code; adapt to your database)
    
    for category in CATEGORIES:
        entities = query_entities_by_category(category)  # Your DB function
        create_category_sitemap(BASE_URL, category, entities)
    
    print("\n✅ All sitemaps generated successfully")
    print(f"   Submit to search engines:")
    print(f"   - Google Search Console: {BASE_URL}/sitemap.xml")
    print(f"   - Bing Webmaster Tools: {BASE_URL}/sitemap.xml")
```

---

## JSON-LD Schema Examples {#jsonld}

### Drug Entity: Complete Example

```json
{
  "@context": "https://schema.org",
  "@type": "MedicalWebPage",
  "name": "Metformin",
  "headline": "Metformin: Comprehensive Drug Profile, Mechanism, Clinical Use & Safety",
  "description": "Complete clinical pharmacology monograph for metformin: mechanism of action, indications, dosing, adverse effects, drug interactions, monitoring, and clinical evidence.",
  "url": "https://hkg.example.com/drugs/metformin",
  "datePublished": "2024-05-10",
  "dateModified": "2026-04-08",
  "inLanguage": "en",
  "creator": {
    "@type": "Organization",
    "name": "Healthcare Knowledge Garden",
    "url": "https://hkg.example.com"
  },
  "author": {
    "@type": "Person",
    "name": "Dr. Sarah Chen, PharmD, BCPS",
    "jobTitle": "Clinical Pharmacist",
    "affiliation": "Healthcare Knowledge Garden"
  },
  "editor": {
    "@type": "Person",
    "name": "Dr. Michael Rodriguez, MD",
    "jobTitle": "Endocrinologist",
    "affiliation": "Healthcare Knowledge Garden"
  },
  "mainEntity": {
    "@type": "Drug",
    "name": "Metformin",
    "alternateName": [
      "Metformin hydrochloride",
      "1,1-Dimethylbiguanide HCl"
    ],
    "description": "Biguanide oral antidiabetic agent used primarily for type 2 diabetes mellitus management",
    "drugClass": [
      "Biguanides",
      "Antidiabetic Agents",
      "Oral Hypoglycemic Agents"
    ],
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
      },
      {
        "@type": "MedicalCode",
        "codingSystem": "NDC",
        "codeValue": "Multiple (varies by manufacturer)"
      }
    ],
    "mechanismOfAction": "Decreases hepatic glucose production, improves insulin sensitivity and glucose utilization, reduces intestinal glucose absorption",
    "indication": [
      {
        "@type": "MedicalCondition",
        "name": "Type 2 Diabetes Mellitus",
        "url": "https://hkg.example.com/conditions/type-2-diabetes"
      },
      {
        "@type": "MedicalCondition",
        "name": "Prediabetes"
      },
      {
        "@type": "MedicalCondition",
        "name": "Polycystic Ovary Syndrome (PCOS)"
      }
    ],
    "dosageForm": [
      "Tablet (immediate-release)",
      "Tablet (extended-release)",
      "Oral solution"
    ],
    "recommendedDosage": {
      "@type": "Thing",
      "description": "Initial: 500 mg once or twice daily with meals; Maintenance: 1000–2000 mg daily in divided doses; Maximum: 2550 mg/day"
    },
    "adverseEffect": [
      {
        "@type": "MedicalSymptom",
        "name": "Gastrointestinal upset (nausea, diarrhea, abdominal pain)",
        "frequency": "15–25% of patients",
        "severity": "Mild to Moderate"
      },
      {
        "@type": "MedicalSymptom",
        "name": "Lactic acidosis",
        "frequency": "<10 cases per 100,000 patient-years",
        "severity": "Severe/Life-threatening"
      },
      {
        "@type": "MedicalSymptom",
        "name": "Vitamin B12 malabsorption",
        "frequency": "10–30% with chronic use",
        "severity": "Mild to Moderate"
      }
    ],
    "drugInteraction": [
      {
        "@type": "Thing",
        "name": "Iodinated contrast dyes",
        "description": "Risk of lactic acidosis; hold metformin 48 hours before and after contrast administration",
        "severity": "Severe"
      },
      {
        "@type": "Thing",
        "name": "Cimetidine",
        "description": "Increases metformin levels; monitor for toxicity",
        "severity": "Moderate"
      },
      {
        "@type": "Thing",
        "name": "Alcohol (excessive)",
        "description": "Increased risk of lactic acidosis",
        "severity": "Moderate"
      }
    ],
    "contraindication": [
      "Renal impairment (eGFR <30 mL/min/1.73m²)",
      "Acute illness, sepsis, severe dehydration",
      "Hepatic disease",
      "Acute heart failure",
      "Metabolic acidosis",
      "Pregnancy (category B, but use caution)"
    ],
    "ageGroup": "18+ years (pediatric use off-label in some countries)",
    "pregnancyCategory": "B",
    "breastFeedingWarning": "Minimal excretion in breast milk; generally safe",
    "monitoringRequirements": [
      "Fasting glucose or HbA1c every 3 months",
      "Renal function (creatinine, eGFR) annually",
      "Vitamin B12 levels annually (or if symptoms)",
      "Liver function tests baseline"
    ],
    "contraindication_SpecialPopulation": {
      "@type": "Thing",
      "name": "Chronic Kidney Disease",
      "details": "Use with caution; contraindicated if eGFR <30"
    },
    "clinicalEvidenceUrl": "https://hkg.example.com/drugs/metformin/evidence",
    "relatedDrug": [
      {
        "@type": "Drug",
        "name": "Sulfonylureas",
        "url": "https://hkg.example.com/drugs/class/sulfonylureas"
      },
      {
        "@type": "Drug",
        "name": "GLP-1 Receptor Agonists",
        "url": "https://hkg.example.com/drugs/class/glp1-agonists"
      }
    ]
  }
}
```

### Condition Entity: Hypertension

```json
{
  "@context": "https://schema.org",
  "@type": "MedicalWebPage",
  "name": "Hypertension",
  "headline": "Hypertension: Comprehensive Clinical Overview, Diagnosis & Evidence-Based Treatment",
  "description": "Complete clinical guide to hypertension: definition, epidemiology, pathophysiology, risk factors, diagnosis, pharmacological and non-pharmacological treatment, complications, and prognosis.",
  "url": "https://hkg.example.com/conditions/hypertension",
  "datePublished": "2024-06-15",
  "dateModified": "2026-04-08",
  "author": {
    "@type": "Person",
    "name": "Dr. Jennifer Smith, MD",
    "jobTitle": "Cardiologist, Board-Certified",
    "affiliation": "Healthcare Knowledge Garden"
  },
  "mainEntity": {
    "@type": "MedicalCondition",
    "name": "Hypertension",
    "alternateName": [
      "High Blood Pressure",
      "Essential Hypertension",
      "Hypertensive Disease"
    ],
    "description": "Persistently elevated blood pressure (systolic ≥130 mmHg or diastolic ≥80 mmHg) affecting systemic vascular and organ health.",
    "code": [
      {
        "@type": "MedicalCode",
        "codingSystem": "ICD-10-CM",
        "codeValue": "I10",
        "name": "Essential hypertension"
      },
      {
        "@type": "MedicalCode",
        "codingSystem": "SNOMED-CT",
        "codeValue": "38341003",
        "name": "Hypertension"
      },
      {
        "@type": "MedicalCode",
        "codingSystem": "MeSH",
        "codeValue": "D006973",
        "name": "Hypertension"
      }
    ],
    "epidemiology": "Affects approximately 45% of U.S. adults; leading cause of morbidity and mortality worldwide; higher prevalence in African Americans and with advancing age",
    "mortalityRate": "Responsible for ~10 million deaths annually worldwide; 380,000+ deaths annually in the U.S.",
    "symptom": [
      {
        "@type": "MedicalSymptom",
        "name": "Often asymptomatic (silent disease)",
        "frequency": "90%+ of patients unaware of condition"
      },
      {
        "@type": "MedicalSymptom",
        "name": "Headaches (typically at back of head)",
        "frequency": "15–20% when symptomatic"
      },
      {
        "@type": "MedicalSymptom",
        "name": "Shortness of breath"
      },
      {
        "@type": "MedicalSymptom",
        "name": "Dizziness"
      }
    ],
    "riskFactor": [
      "Age (>60 years)",
      "Race/ethnicity (African American, Hispanic)",
      "Family history",
      "Obesity (BMI >30)",
      "Sedentary lifestyle",
      "High sodium intake",
      "Excessive alcohol consumption",
      "Chronic stress"
    ],
    "possibleTreatment": [
      {
        "@type": "Drug",
        "name": "Lisinopril (ACE Inhibitor)",
        "url": "https://hkg.example.com/drugs/lisinopril"
      },
      {
        "@type": "Drug",
        "name": "Amlodipine (Calcium Channel Blocker)",
        "url": "https://hkg.example.com/drugs/amlodipine"
      },
      {
        "@type": "Drug",
        "name": "Losartan (ARB)",
        "url": "https://hkg.example.com/drugs/losartan"
      },
      {
        "@type": "Drug",
        "name": "Hydrochlorothiazide (Thiazide)",
        "url": "https://hkg.example.com/drugs/hydrochlorothiazide"
      }
    ],
    "treatmentSuccess": "First-line monotherapy achieves target BP in 40–60%; combination therapy achieves target in 80%+",
    "associatedAnatomy": {
      "@type": "AnatomicalStructure",
      "name": "Cardiovascular System"
    },
    "complication": [
      {
        "@type": "MedicalCondition",
        "name": "Myocardial Infarction",
        "url": "https://hkg.example.com/conditions/myocardial-infarction",
        "riskIncrease": "2–4x risk vs. normotensive"
      },
      {
        "@type": "MedicalCondition",
        "name": "Stroke (Cerebrovascular Accident)",
        "url": "https://hkg.example.com/conditions/stroke",
        "riskIncrease": "2–4x risk"
      },
      {
        "@type": "MedicalCondition",
        "name": "Heart Failure",
        "riskIncrease": "2–3x risk"
      },
      {
        "@type": "MedicalCondition",
        "name": "Chronic Kidney Disease",
        "url": "https://hkg.example.com/conditions/chronic-kidney-disease",
        "riskIncrease": "3–4x risk"
      }
    ],
    "prognosis": "With treatment: 10–15% reduction in cardiovascular mortality per 10 mmHg systolic BP reduction. Without treatment: progressive organ damage and cardiovascular events.",
    "relatedCondition": [
      {
        "@type": "MedicalCondition",
        "name": "Left Ventricular Hypertrophy",
        "url": "https://hkg.example.com/conditions/lvh"
      },
      {
        "@type": "MedicalCondition",
        "name": "Metabolic Syndrome",
        "url": "https://hkg.example.com/conditions/metabolic-syndrome"
      }
    ]
  }
}
```

---

## llms.txt File Structure {#llmstxt}

### Full llms.txt Example

**File:** `/llms.txt`

```markdown
# Healthcare Knowledge Garden

> AI-native medical knowledge platform providing comprehensive, structured entity pages for medical conditions, 
> drugs, procedures, providers, and healthcare organizations. Every page is optimized for AI assistant citations 
> with JSON-LD schema markup, medical codes (ICD-10, RxNorm, SNOMED CT), and direct-answer content capsules.
> Updated daily. Used by Claude, ChatGPT, Perplexity, and AI medical assistants worldwide.

## Common Medical Conditions

- [Hypertension (High Blood Pressure)](https://hkg.example.com/conditions/hypertension) – Essential and secondary hypertension management
- [Type 2 Diabetes Mellitus](https://hkg.example.com/conditions/type-2-diabetes) – Diagnosis, treatment, complications
- [Chronic Kidney Disease](https://hkg.example.com/conditions/chronic-kidney-disease) – Stages, causes, management
- [Acute Myocardial Infarction](https://hkg.example.com/conditions/myocardial-infarction) – Heart attack pathophysiology and management
- [Stroke (Cerebrovascular Accident)](https://hkg.example.com/conditions/stroke) – Ischemic and hemorrhagic stroke
- [Heart Failure](https://hkg.example.com/conditions/heart-failure) – Systolic and diastolic dysfunction
- [Atrial Fibrillation](https://hkg.example.com/conditions/atrial-fibrillation) – Arrhythmia management
- [COPD (Chronic Obstructive Pulmonary Disease)](https://hkg.example.com/conditions/copd) – Pathophysiology and treatment
- [Asthma](https://hkg.example.com/conditions/asthma) – Pediatric and adult asthma
- [Depression & Major Depressive Disorder](https://hkg.example.com/conditions/depression) – Diagnosis and psychiatric management

[... additional 50+ high-traffic conditions ...]

## Pharmaceutical Entities

### ACE Inhibitors
- [Lisinopril](https://hkg.example.com/drugs/lisinopril) – Mechanism, dosing, adverse effects
- [Enalapril](https://hkg.example.com/drugs/enalapril) – IV and oral formulations
- [Ramipril](https://hkg.example.com/drugs/ramipril) – Once-daily dosing

### Calcium Channel Blockers
- [Amlodipine](https://hkg.example.com/drugs/amlodipine) – Hypertension and angina
- [Diltiazem](https://hkg.example.com/drugs/diltiazem) – Rate control and vasodilation
- [Verapamil](https://hkg.example.com/drugs/verapamil) – SVT and hypertension

### Antidiabetic Agents
- [Metformin](https://hkg.example.com/drugs/metformin) – First-line biguanide
- [Glipizide](https://hkg.example.com/drugs/glipizide) – Sulfonylurea
- [Sitagliptin](https://hkg.example.com/drugs/sitagliptin) – DPP-4 inhibitor

[... additional 1000+ drugs ...]

## Medical Procedures

### Cardiac Procedures
- [Coronary Angiography](https://hkg.example.com/procedures/coronary-angiography) – Diagnostic imaging
- [Percutaneous Coronary Intervention (PCI)](https://hkg.example.com/procedures/pci) – Stent placement
- [Cardiac Catheterization](https://hkg.example.com/procedures/cardiac-catheterization) – Hemodynamic monitoring

### Renal Procedures
- [Renal Artery Stenosis Imaging](https://hkg.example.com/procedures/renal-artery-imaging) – Duplex ultrasound, CTA, MRA
- [Kidney Biopsy](https://hkg.example.com/procedures/kidney-biopsy) – Percutaneous and transjugular

### Endocrine Procedures
- [Thyroid Ultrasound](https://hkg.example.com/procedures/thyroid-ultrasound) – Nodule evaluation
- [Fine Needle Aspiration (FNA)](https://hkg.example.com/procedures/fna) – Thyroid cytology

[... additional 300+ procedures ...]

## Healthcare Specialties

- [Cardiology](https://hkg.example.com/providers/cardiology) – Physicians and board certification
- [Internal Medicine](https://hkg.example.com/providers/internal-medicine) – Generalists and subspecialists
- [Endocrinology](https://hkg.example.com/providers/endocrinology) – Diabetes and metabolic disease
- [Nephrology](https://hkg.example.com/providers/nephrology) – Kidney disease specialists
- [Psychiatry](https://hkg.example.com/providers/psychiatry) – Mental health and behavioral medicine

[... additional 50+ specialties ...]

## Medical Codes & Taxonomies

- [ICD-10-CM Conditions](https://hkg.example.com/codes/icd10) – 70,000+ condition codes
- [CPT Procedures](https://hkg.example.com/codes/cpt) – 10,000+ procedure codes
- [RxNorm Drugs](https://hkg.example.com/codes/rxnorm) – 20,000+ medication entities
- [SNOMED CT](https://hkg.example.com/codes/snomed) – 350,000+ clinical concepts
- [LOINC Lab Tests](https://hkg.example.com/codes/loinc) – 95,000+ laboratory observations

## Clinical Practice Guidelines

### Cardiovascular Guidelines
- [ACC/AHA Hypertension Guidelines (2024)](https://hkg.example.com/guidelines/acc-aha-hypertension-2024)
- [ACC/AHA Heart Failure Guidelines (2022)](https://hkg.example.com/guidelines/acc-aha-heart-failure-2022)
- [ESC Atrial Fibrillation Guidelines (2023)](https://hkg.example.com/guidelines/esc-afib-2023)

### Endocrinology Guidelines
- [ADA Standards of Medical Care in Diabetes (2026)](https://hkg.example.com/guidelines/ada-diabetes-2026)
- [ATA Thyroid Nodule Guidelines (2015/2023)](https://hkg.example.com/guidelines/ata-thyroid-2023)

### Nephrology Guidelines
- [KDIGO CKD Clinical Practice Guideline (2021)](https://hkg.example.com/guidelines/kdigo-ckd-2021)

[... additional 100+ guidelines ...]

## Optional: Extended Resources

### Clinical Evidence & Research
- [Systematic Reviews & Meta-analyses](https://hkg.example.com/research/systematic-reviews)
- [Landmark Clinical Trials](https://hkg.example.com/research/landmark-trials)
- [Drug Interaction Databases](https://hkg.example.com/research/drug-interactions)

### Healthcare Providers & Organizations
- [Medical Schools & Teaching Hospitals](https://hkg.example.com/providers/medical-schools)
- [Specialty Societies](https://hkg.example.com/providers/societies)

---

**Last Updated:** 2026-04-08 | **Next Update:** 2026-05-08 (monthly)

```

---

## Content Freshness Automation {#freshness}

### Update Schedule Template

Create a database table to track update schedules:

```sql
CREATE TABLE entity_update_schedule (
    id INT PRIMARY KEY AUTO_INCREMENT,
    entity_type VARCHAR(50),  -- 'condition', 'drug', 'procedure'
    entity_slug VARCHAR(255),
    entity_name VARCHAR(255),
    last_modified DATE,
    traffic_rank INT,  -- 1=highest traffic
    update_frequency VARCHAR(50),  -- 'weekly', 'monthly', 'quarterly'
    next_scheduled_update DATE,
    update_notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY (entity_type, entity_slug)
);
```

### Python Script: Automated Update Checker

```python
#!/usr/bin/env python3
"""
Daily task: Check which entity pages are due for updates
Send reminders to content team
"""

from datetime import datetime, timedelta
import requests
import json
from database import get_db_connection

def check_due_updates():
    """Find pages due for content updates based on frequency schedule"""
    
    db = get_db_connection()
    cursor = db.cursor()
    
    today = datetime.now().date()
    
    # Get all pages where next_scheduled_update <= today
    query = """
    SELECT 
        entity_type, entity_slug, entity_name, 
        update_frequency, last_modified
    FROM entity_update_schedule
    WHERE next_scheduled_update <= %s
    ORDER BY traffic_rank ASC
    """
    
    cursor.execute(query, (today,))
    due_updates = cursor.fetchall()
    
    if not due_updates:
        print("✓ No updates due today")
        return
    
    print(f"\n⚠️  {len(due_updates)} pages due for updates:")
    print("-" * 80)
    
    for entity in due_updates:
        entity_type, slug, name, freq, last_mod = entity
        days_since = (today - last_mod).days
        
        print(f"  {name.upper()}")
        print(f"    Type: {entity_type}")
        print(f"    Frequency: {freq}")
        print(f"    Last updated: {days_since} days ago")
        print(f"    URL: https://hkg.example.com/{entity_type}s/{slug}")
        print()
    
    # Send notification email to content team
    send_update_reminder_email(due_updates)
    
    db.close()


def send_update_reminder_email(due_updates):
    """Send email with list of pages due for updates"""
    
    email_body = "The following entity pages are due for content updates:\n\n"
    
    for entity in due_updates:
        entity_type, slug, name, freq, last_mod = entity
        email_body += f"- {name} ({entity_type})\n"
    
    # Send email (integrate with your email service)
    print("✉️  Email sent to content-team@hkg.example.com")


def mark_updated(entity_type, entity_slug):
    """Mark an entity page as updated; recalculate next update date"""
    
    db = get_db_connection()
    cursor = db.cursor()
    
    today = datetime.now().date()
    
    # Get current frequency
    cursor.execute(
        "SELECT update_frequency FROM entity_update_schedule WHERE entity_type = %s AND entity_slug = %s",
        (entity_type, entity_slug)
    )
    result = cursor.fetchone()
    
    if not result:
        print(f"Error: Entity not found")
        return
    
    frequency = result[0]
    
    # Calculate next update date
    if frequency == 'weekly':
        next_update = today + timedelta(days=7)
    elif frequency == 'monthly':
        next_update = today + timedelta(days=30)
    elif frequency == 'quarterly':
        next_update = today + timedelta(days=90)
    else:
        next_update = today + timedelta(days=365)
    
    # Update database
    cursor.execute("""
        UPDATE entity_update_schedule
        SET last_modified = %s, next_scheduled_update = %s
        WHERE entity_type = %s AND entity_slug = %s
    """, (today, next_update, entity_type, entity_slug))
    
    db.commit()
    db.close()
    
    print(f"✓ {entity_slug} marked as updated. Next update: {next_update}")


if __name__ == '__main__':
    check_due_updates()
    
    # Example usage:
    # mark_updated('condition', 'hypertension')
```

### Cron Job Configuration

```bash
# /etc/cron.d/hkg-content-updates
# Run daily at 8:00 AM to check for due updates

0 8 * * * /usr/bin/python3 /opt/hkg/scripts/check_due_updates.py >> /var/log/hkg-updates.log 2>&1
```

---

## Crawl Testing & Validation {#testing}

### Google Rich Results Test

Test any entity page for schema validation:

```bash
# Test a single page
curl "https://search.google.com/test/rich-results" \
  -X POST \
  --data-urlencode "url=https://hkg.example.com/conditions/hypertension"
```

Or use the web interface: https://search.google.com/test/rich-results

### Manual AI Crawl Test

```python
#!/usr/bin/env python3
"""
Manually test how AI crawlers see your pages
Simulates different user-agents
"""

import requests
from bs4 import BeautifulSoup

def test_crawl(url, user_agent):
    """Fetch page as specific crawler"""
    
    headers = {
        'User-Agent': user_agent
    }
    
    response = requests.get(url, headers=headers, timeout=10)
    
    print(f"\n{user_agent}")
    print("=" * 80)
    print(f"Status: {response.status_code}")
    print(f"Content-Length: {len(response.content)} bytes")
    
    # Check for JSON-LD schema
    soup = BeautifulSoup(response.content, 'html.parser')
    schemas = soup.find_all('script', {'type': 'application/ld+json'})
    
    print(f"JSON-LD Schemas Found: {len(schemas)}")
    for i, schema in enumerate(schemas):
        try:
            data = json.loads(schema.string)
            print(f"  [{i+1}] @type: {data.get('@type', 'unknown')}")
        except:
            print(f"  [{i+1}] (invalid JSON)")
    
    # Check robots.txt compliance
    robots_response = requests.get(f"{url.split('/')[2]}/robots.txt", headers=headers)
    print(f"\nrobots.txt allows crawl: {response.status_code == 200}")


def main():
    test_url = "https://hkg.example.com/conditions/hypertension"
    
    crawlers = [
        "GPTBot/1.0",
        "ChatGPT-User/1.0",
        "ClaudeBot/1.0",
        "Claude-SearchBot/1.0",
        "PerplexityBot/1.0",
        "Googlebot/2.1",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) (Human user)"
    ]
    
    for crawler in crawlers:
        test_crawl(test_url, crawler)


if __name__ == '__main__':
    main()
```

### Sitemap Validation

```bash
# Validate XML sitemap structure
xmllint --noout /path/to/sitemap.xml

# Count URLs in sitemap
grep -c "<loc>" /path/to/sitemap.xml

# Check for duplicates
grep "<loc>" /path/to/sitemap.xml | sort | uniq -d
```

### Schema.org Validator

Use the official schema.org validator:

```bash
# Test via command line
curl -X GET "https://validator.schema.org/v1/" \
  -H "Content-Type: application/json" \
  --data '{"url": "https://hkg.example.com/conditions/hypertension"}'
```

---

## Summary Checklist

- [ ] robots.txt invites all AI crawlers
- [ ] /llms.txt file created with 500+ entities
- [ ] /llms-full.txt generated with complete content
- [ ] XML sitemaps created for each entity category
- [ ] JSON-LD schema on 100% of entity pages
- [ ] Citation capsules (40–80 word answers) on every page
- [ ] Medical codes (ICD-10, RxNorm, SNOMED) linked
- [ ] Internal knowledge graph links implemented
- [ ] Content update schedules established
- [ ] Automated freshness monitoring in place
- [ ] Monthly AI citation tracking started

---

**Next Steps:** Deploy to staging environment, validate all crawlers can access pages, begin content freshness cycle, monitor AI citations weekly.


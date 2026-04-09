# Healthcare Knowledge Garden — Data Architecture Master Document
**Version:** 1.0 | **Status:** Final Specification | **Date:** April 2026

---

## EXECUTIVE SUMMARY

The HKG Knowledge Base Layer is the foundation that makes everything else possible. It ingests data from 30+ public and licensed healthcare sources, normalizes it into a unified graph + relational schema, and exposes every entity as a structured, AI-citable page. The "sleeper play": every entity page with JSON-LD becomes a citation source for Claude, ChatGPT, and Perplexity — compound interest forever.

### The Three-Database Architecture

1. **Neo4j (Knowledge Core)** — The brain. Models all relationships: provider networks, credential chains, care pathways, drug interactions, billing hierarchies, clinical decision trees, clinical trial networks. Query: "Show me all cardiologists with active DEA licenses in California + their board certifications."

2. **Supabase/PostgreSQL (Operational Layer)** — The spine. Transactional operations, user accounts, billing, session management, audit logs, HIPAA compliance tracking, file storage, verification workflows.

3. **Markdown + JSON-LD (Public API Layer)** — The face. Static/generated entity pages that AI assistants cite. Every condition, drug, procedure, provider, and code becomes a first-class web entity with structured schema markup.

The three databases sync through event-driven architecture. Neo4j is the source of truth for knowledge relationships. PostgreSQL is the source of truth for transactional state. The web layer is generated FROM Neo4j/PostgreSQL and republished quarterly (or on ingestion).

### RSI Heartbeat (The Moat)

Automated refresh schedules keep data fresh:
- **Daily:** NPI incremental updates, NDC drug database, DailyMed labels, PubMed new citations
- **Weekly:** NPI full bulk file, ClinicalTrials.gov, state board license checks
- **Monthly:** OIG LEIE list, SAM.gov exclusions, RxNorm normalization updates
- **Quarterly:** HCPCS codes, SNOMED CT, LOINC lab codes, FAERS adverse events, CMS quality data
- **Annual:** ICD-10-CM/PCS new code sets, MS-DRG updates

Every update is timestamped, versioned, and audited. The platform gets smarter daily. Competitors are static databases. We are a living, breathing knowledge system.

---

## DATA SOURCE REGISTRY

### Complete Table of All Sources (Prioritized)

| Source Name | Category | Access Method | Format | Update Frequency | Cost | Volume | Priority | API Endpoint / URL |
|---|---|---|---|---|---|---|---|---|
| **CREDENTIALING & VERIFICATION (P0)** |
| NPI Registry (NPPES) | Credentialing | Bulk Download + API | JSON/CSV | Weekly | Free | 9.5M records | P0 | https://npiregistry.cms.hhs.gov/api/ |
| OIG LEIE (Exclusions List) | Credentialing | Bulk Download (CSV) | CSV | Monthly | Free | 90K+ active | P0 | https://oig.hhs.gov/exclusions/downloads.asp |
| SAM.gov (Federal Exclusions) | Credentialing | REST API | JSON | Daily | Free | 30K+ active | P0 | https://open.sam.gov/api/data/ |
| NPDB (Malpractice & Adverse) | Credentialing | Query API (Restricted) | XML/JSON | Monthly | Free-Paid* | 1M+ records | P0 | https://www.npdb-hipdb.hrsa.gov/Public_Query.aspx |
| **MEDICAL CODES (P0)** |
| ICD-10-CM (Diagnosis) | Medical Codes | Bulk XML Download | XML | Annual (Oct) | Free | 70K+ codes | P0 | https://www.cms.gov/icd10m (CMS) |
| ICD-10-PCS (Procedures) | Medical Codes | Bulk XML Download | XML | Annual (Oct) | Free | 78K+ codes | P0 | https://www.cms.gov/icd10m (CMS) |
| HCPCS Level II | Medical Codes | CSV Download | CSV | Quarterly | Free | 8K+ codes | P0 | https://www.cms.gov/hcpcslevels |
| MS-DRG | Medical Codes | Excel/CSV Download | XLSX/CSV | Annual | Free | 745+ groups | P0 | https://www.cms.gov/icd10m/version37-fullcode-cms/tab-grouper.html |
| NDC Directory | Medical Codes | Daily API Export | JSON/CSV | Daily | Free | 200K+ drugs | P0 | https://open.fda.gov/apis/drug/ndc/ |
| **CLINICAL KNOWLEDGE (P1)** |
| PubMed/MEDLINE | Clinical Knowledge | Bulk Download + API | XML/JSON | Daily | Free | 40M+ citations | P1 | https://pubmed.ncbi.nlm.nih.gov/api/ |
| RxNorm | Clinical Knowledge | REST API | JSON/XML | Monthly | Free | 200K+ entries | P1 | https://rxnav.nlm.nih.gov/APIs/ |
| DailyMed (FDA Labels) | Clinical Knowledge | REST API + Bulk | JSON/XML | Daily | Free | 180K+ drugs | P1 | https://dailymed.nlm.nih.gov/dailymed/services.php |
| ClinicalTrials.gov | Clinical Knowledge | REST API v2 | JSON | Daily | Free | 500K+ trials | P1 | https://clinicaltrials.gov/api/ |
| SNOMED CT | Clinical Knowledge | Download (UMLS) | Distribution Format | Quarterly | Free (UMLS) | 350K+ concepts | P1 | https://www.nlm.nih.gov/research/umls/ |
| LOINC | Clinical Knowledge | CSV Download | CSV | Quarterly | Free | 95K+ codes | P1 | https://loinc.org/download/ |
| FDA FAERS | Clinical Knowledge | Bulk Download + API | CSV/JSON | Quarterly | Free | 20M+ reports | P1 | https://open.fda.gov/apis/drug/event/ |
| **PROVIDER & ORGANIZATION DATA (P1)** |
| CMS Provider Enrollment | Provider Data | Bulk File + API | CSV/JSON | Weekly | Free | 2.5M records | P1 | https://data.cms.gov/provider-characteristics/provider-enrollment |
| Hospital Compare (CMS) | Quality & Payment | Bulk File | CSV | Monthly | Free | 5K+ hospitals | P1 | https://data.cms.gov/provider-characteristics/hospitals |
| **VERIFICATION SOURCES (P1-P2)** |
| CAQH ProView | Credentialing | Licensed API | XML/JSON | Real-time | Paid | 4.8M records | P1 | [Requires licensing] |
| Nursys (Nursing Licenses) | Credentialing | Free JSON API | JSON | Updated | Free | 4M+ licenses | P1 | https://www.nursys.com/API |
| FSMB DocInfo | Credentialing | Licensed Query API | JSON | Monthly | Paid (~$9/lookup) | 1M+ physicians | P2 | [Requires licensing] |
| ABMS Certification | Credentialing | Licensed Integration | JSON | Monthly | Paid | 1M+ records | P2 | [Requires licensing] |
| DEA Registration | Credentialing | Restricted Query | HTML/Text | Ongoing | Restricted | 2M+ registrants | P2 | https://www.dea.gov/online-tools-and-services |
| State Medical Boards | Credentialing | Web Scrape + Lookup | HTML/JSON | Varies | Free | 50+ states | P2 | State-specific URLs (see State Matrix) |
| **QUALITY & PAYMENT (P2)** |
| CMS Quality Measures | Quality & Payment | API | JSON | Quarterly | Free | 1K+ measures | P2 | https://data.cms.gov/provider-characteristics |
| Open Payments (Sunshine) | Quality & Payment | Bulk Download | CSV | Annual | Free | 300M+ payments | P2 | https://www.cms.gov/OpenPayments |
| Medicare Fee Schedules | Quality & Payment | Bulk File | CSV | Annual | Free | 10K+ services | P2 | https://www.cms.gov/medicarefees |
| **LONGEVITY & RESEARCH (P3)** |
| NIH RePORTER | Clinical Knowledge | REST API | JSON | Weekly | Free | 500K+ projects | P3 | https://reporter.nih.gov/api |
| WHO Global Observatory | Clinical Knowledge | Bulk Data | CSV/JSON | Annual | Free | 500+ indicators | P3 | https://www.who.int/data/gho |
| CDC WONDER | Clinical Knowledge | Query Interface | CSV/JSON | Monthly | Free | 100M+ records | P3 | https://wonder.cdc.gov/api |
| **SPECIALTY DATA (P3)** |
| DrugBank | Clinical Knowledge | Licensed Download | XML/JSON | Quarterly | Free (Academic) | 15K+ drugs | P3 | https://go.drugbank.com/releases |
| GeneCards/UniProt | Research | REST API | JSON | Continuous | Free (Limited) | 20K+ genes | P3 | https://www.genecards.org/api |
| Human Protein Atlas | Research | REST API | JSON | Quarterly | Free | 20K+ proteins | P3 | https://www.proteinatlas.org/api |

**Legend:**
- **Priority:** P0 = immediate (Week 1-2), P1 = next sprint (Week 3-4), P2 = future (Week 5-8), P3 = ongoing (nice-to-have)
- **Cost:** "Paid" = requires licensing agreement; "Restricted" = limited to specific use cases; "Paid*" = some queries free, others paid
- **Volume:** Approximate record counts at scale

---

## SUPABASE SCHEMA DESIGN

### Database Architecture

Supabase (PostgreSQL) holds transactional state, user data, and operational tracking. Neo4j holds the knowledge graph. The two sync through event triggers.

### Core Entity Tables

#### Table: `providers`
```sql
CREATE TABLE providers (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  npi CHAR(10) UNIQUE NOT NULL,
  first_name VARCHAR(100),
  last_name VARCHAR(100),
  full_name VARCHAR(255) NOT NULL,
  gender CHAR(1),
  dob DATE,
  
  -- Address & Contact
  primary_address JSONB,  -- {street, city, state, zip, country}
  secondary_address JSONB,
  phone VARCHAR(20),
  email VARCHAR(255),
  
  -- Clinical Identity
  specialty_code VARCHAR(20),  -- Taxonomy Code
  specialty_name VARCHAR(255),
  secondary_specialties JSONB,  -- Array of {code, name}
  
  -- Status
  npi_status VARCHAR(50),  -- ACTIVE, DEACTIVATED, etc.
  is_individual BOOLEAN DEFAULT true,
  is_organization BOOLEAN DEFAULT false,
  
  -- Verification Tracking
  npi_verified BOOLEAN DEFAULT false,
  npi_verified_date TIMESTAMP,
  dea_status VARCHAR(50),  -- ACTIVE, EXPIRED, INACTIVE
  dea_verified_date TIMESTAMP,
  
  -- Data Provenance
  data_source VARCHAR(100),  -- 'NPPES', 'CAQH', etc.
  last_verified TIMESTAMP DEFAULT now(),
  next_verification_date TIMESTAMP,
  data_hash VARCHAR(64),  -- SHA-256 hash for change detection
  
  -- Lifecycle
  created_at TIMESTAMP DEFAULT now(),
  updated_at TIMESTAMP DEFAULT now(),
  
  INDEX idx_npi (npi),
  INDEX idx_specialty (specialty_code),
  INDEX idx_status (npi_status),
  INDEX idx_verified (npi_verified)
);
```

#### Table: `provider_credentials`
```sql
CREATE TABLE provider_credentials (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  provider_id UUID NOT NULL REFERENCES providers(id) ON DELETE CASCADE,
  
  credential_type VARCHAR(100) NOT NULL,  
  -- 'MEDICAL_LICENSE', 'DEA', 'BOARD_CERT', 'NPI', 'SPECIALTY_CERT'
  
  credential_number VARCHAR(100) NOT NULL,
  issuing_body VARCHAR(255),
  state VARCHAR(2),
  
  issue_date DATE,
  expiration_date DATE,
  
  status VARCHAR(50),  -- ACTIVE, EXPIRED, SUSPENDED, REVOKED
  verification_source VARCHAR(100),  -- 'STATE_BOARD', 'DEA', 'ABMS', etc.
  
  -- Raw API Response for Audit
  verification_response JSONB,
  
  -- Verification Details
  verified_at TIMESTAMP,
  verified_by_source VARCHAR(100),
  
  created_at TIMESTAMP DEFAULT now(),
  updated_at TIMESTAMP DEFAULT now(),
  
  FOREIGN KEY (provider_id) REFERENCES providers(id),
  INDEX idx_provider_id (provider_id),
  INDEX idx_credential_type (credential_type),
  INDEX idx_status (status),
  INDEX idx_expiration (expiration_date)
);
```

#### Table: `provider_verifications`
```sql
CREATE TABLE provider_verifications (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  provider_id UUID NOT NULL REFERENCES providers(id) ON DELETE CASCADE,
  
  source VARCHAR(100) NOT NULL,  
  -- 'NPI', 'DEA', 'STATE_BOARD', 'ABMS', 'NPDB', 'OIG', 'SAM'
  
  verification_date TIMESTAMP DEFAULT now(),
  status VARCHAR(50),  -- SUCCESS, FAILED, PARTIAL, PENDING
  
  -- Raw response (for audit trail)
  raw_response JSONB,
  
  -- Extracted findings
  findings JSONB,  -- {is_active, is_sanctioned, has_adverse_actions, etc.}
  
  next_check_date TIMESTAMP,
  
  created_at TIMESTAMP DEFAULT now(),
  
  FOREIGN KEY (provider_id) REFERENCES providers(id),
  INDEX idx_provider_id (provider_id),
  INDEX idx_source (source),
  INDEX idx_status (status)
);
```

#### Table: `organizations`
```sql
CREATE TABLE organizations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_npi CHAR(10) UNIQUE,
  name VARCHAR(500) NOT NULL,
  
  org_type VARCHAR(100),  -- 'HOSPITAL', 'CLINIC', 'GROUP_PRACTICE', 'HEALTHCARE_SYSTEM'
  
  primary_address JSONB,
  phone VARCHAR(20),
  email VARCHAR(255),
  website VARCHAR(255),
  
  cms_certification_number VARCHAR(50),  -- CCN for hospitals
  cms_certification_type VARCHAR(50),  -- 'HOSPITAL', 'CRITICAL_ACCESS', etc.
  
  -- Facility Details
  bed_count INT,
  specialty_codes JSONB,  -- Array of services
  
  -- Relationships
  parent_org_id UUID REFERENCES organizations(id),
  affiliated_providers JSONB,  -- Array of provider_ids
  
  status VARCHAR(50),  -- ACTIVE, INACTIVE
  
  data_source VARCHAR(100),
  last_verified TIMESTAMP,
  
  created_at TIMESTAMP DEFAULT now(),
  updated_at TIMESTAMP DEFAULT now(),
  
  INDEX idx_npi (org_npi),
  INDEX idx_status (status)
);
```

### Medical Code Tables

#### Table: `icd10_cm`
```sql
CREATE TABLE icd10_cm (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  code VARCHAR(10) UNIQUE NOT NULL,
  code_description VARCHAR(500) NOT NULL,
  
  chapter_code VARCHAR(5),
  chapter_title VARCHAR(255),
  category_code VARCHAR(5),
  category_title VARCHAR(255),
  
  is_billable BOOLEAN,
  is_header BOOLEAN,
  requires_5th_digit BOOLEAN,
  
  effective_date DATE,
  version VARCHAR(10),  -- e.g., '2024'
  
  -- Cross-references
  snomed_codes JSONB,  -- Array of SNOMED equivalents
  parent_codes JSONB,
  child_codes JSONB,
  
  created_at TIMESTAMP DEFAULT now(),
  
  INDEX idx_code (code),
  INDEX idx_billable (is_billable)
);
```

#### Table: `icd10_pcs`
```sql
CREATE TABLE icd10_pcs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  code VARCHAR(10) UNIQUE NOT NULL,
  code_description VARCHAR(500) NOT NULL,
  
  section VARCHAR(2),
  section_title VARCHAR(255),
  body_system VARCHAR(2),
  body_system_title VARCHAR(255),
  root_operation VARCHAR(2),
  root_operation_title VARCHAR(255),
  
  effective_date DATE,
  version VARCHAR(10),
  
  created_at TIMESTAMP DEFAULT now(),
  
  INDEX idx_code (code),
  INDEX idx_section (section)
);
```

#### Table: `hcpcs_codes`
```sql
CREATE TABLE hcpcs_codes (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  code VARCHAR(10) UNIQUE NOT NULL,
  description VARCHAR(500) NOT NULL,
  
  code_type VARCHAR(50),  -- 'E&M', 'PROCEDURE', 'SUPPLY', etc.
  long_description VARCHAR(1000),
  
  effective_date DATE,
  termination_date DATE,
  status VARCHAR(50),  -- ACTIVE, TERMINATED
  
  -- Pricing
  medicare_payment_amount DECIMAL(10, 2),
  pricing_indicator VARCHAR(10),
  
  version VARCHAR(10),
  created_at TIMESTAMP DEFAULT now(),
  
  INDEX idx_code (code),
  INDEX idx_status (status)
);
```

#### Table: `ndc_drugs`
```sql
CREATE TABLE ndc_drugs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  ndc_code VARCHAR(11) UNIQUE NOT NULL,
  
  proprietary_name VARCHAR(255),
  nonproprietary_name VARCHAR(255),
  dosage_form VARCHAR(100),
  route_of_admin VARCHAR(100),
  strength VARCHAR(255),
  
  labeler_name VARCHAR(255),
  labeler_code VARCHAR(5),
  
  product_ndc VARCHAR(10),
  package_description VARCHAR(500),
  
  listing_date DATE,
  discontinued BOOLEAN DEFAULT false,
  discontinued_date DATE,
  
  -- Cross-references
  rxcui VARCHAR(10),  -- RxNorm Unique ID
  snomed_codes JSONB,
  
  created_at TIMESTAMP DEFAULT now(),
  updated_at TIMESTAMP DEFAULT now(),
  
  INDEX idx_ndc (ndc_code),
  INDEX idx_rxcui (rxcui),
  INDEX idx_name (proprietary_name)
);
```

#### Table: `ms_drg`
```sql
CREATE TABLE ms_drg (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  drg_code VARCHAR(5) UNIQUE NOT NULL,
  drg_title VARCHAR(500) NOT NULL,
  
  drg_type VARCHAR(50),  -- 'MS-DRG', 'AP-DRG'
  
  -- Statistics
  geometric_mean_los DECIMAL(5, 2),
  arithmetic_mean_los DECIMAL(5, 2),
  weight DECIMAL(5, 4),
  
  version VARCHAR(10),
  effective_date DATE,
  
  created_at TIMESTAMP DEFAULT now(),
  
  INDEX idx_code (drg_code)
);
```

### Clinical Knowledge Tables

#### Table: `drugs`
```sql
CREATE TABLE drugs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  rxcui VARCHAR(10) UNIQUE NOT NULL,
  
  name VARCHAR(500) NOT NULL,
  ingredient VARCHAR(500),
  
  dosage_form VARCHAR(100),
  route_of_admin VARCHAR(100),
  strength VARCHAR(255),
  
  -- Cross-references
  ndc_codes JSONB,  -- Array of NDC codes
  snomed_codes JSONB,
  
  -- Pharmacology
  atc_code VARCHAR(10),  -- Anatomical Therapeutic Chemical
  drug_class JSONB,
  mechanism_of_action VARCHAR(1000),
  
  status VARCHAR(50),  -- ACTIVE, OBSOLETE
  
  created_at TIMESTAMP DEFAULT now(),
  updated_at TIMESTAMP DEFAULT now(),
  
  INDEX idx_rxcui (rxcui),
  INDEX idx_name (name)
);
```

#### Table: `drug_interactions`
```sql
CREATE TABLE drug_interactions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  drug_a_rxcui VARCHAR(10) NOT NULL REFERENCES drugs(rxcui),
  drug_b_rxcui VARCHAR(10) NOT NULL REFERENCES drugs(rxcui),
  
  severity VARCHAR(50),  -- CONTRAINDICATED, SERIOUS, MODERATE, MINOR
  description TEXT,
  
  mechanism VARCHAR(1000),
  management VARCHAR(1000),
  
  source VARCHAR(100),  -- 'FDA', 'DrugBank', 'NIH', etc.
  source_url VARCHAR(500),
  
  created_at TIMESTAMP DEFAULT now(),
  
  UNIQUE (drug_a_rxcui, drug_b_rxcui),
  INDEX idx_severity (severity)
);
```

#### Table: `conditions`
```sql
CREATE TABLE conditions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  snomed_code VARCHAR(20) UNIQUE,
  
  name VARCHAR(500) NOT NULL,
  description TEXT,
  synonyms JSONB,  -- Array of alternate names
  
  -- Cross-references
  icd10_codes JSONB,  -- Array of ICD-10-CM codes
  icd9_codes JSONB,
  
  category VARCHAR(100),  -- 'ACUTE', 'CHRONIC', 'COMPLICATION'
  severity_scale VARCHAR(255),
  
  epidemiology JSONB,  -- {prevalence, incidence, mortality}
  risk_factors JSONB,
  complications JSONB,
  
  created_at TIMESTAMP DEFAULT now(),
  updated_at TIMESTAMP DEFAULT now(),
  
  INDEX idx_snomed (snomed_code),
  INDEX idx_name (name)
);
```

#### Table: `clinical_trials`
```sql
CREATE TABLE clinical_trials (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  nct_id VARCHAR(15) UNIQUE NOT NULL,
  
  title VARCHAR(1000) NOT NULL,
  acronym VARCHAR(100),
  description TEXT,
  
  status VARCHAR(50),  -- RECRUITING, ACTIVE, COMPLETED, TERMINATED
  recruitment_status VARCHAR(100),
  
  phase JSONB,  -- Array: EARLY_PHASE_1, PHASE_1, PHASE_2, PHASE_3, PHASE_4
  
  study_type VARCHAR(100),  -- INTERVENTIONAL, OBSERVATIONAL, EXPANDED_ACCESS
  study_design JSONB,
  
  conditions JSONB,  -- Array of condition names/codes
  interventions JSONB,  -- Array of {type, name, description}
  
  enrollment INT,
  primary_completion_date DATE,
  study_completion_date DATE,
  enrollment_type VARCHAR(50),  -- ACTUAL, ANTICIPATED
  
  sponsor_name VARCHAR(500),
  sponsor_type VARCHAR(100),
  
  locations JSONB,  -- Array of {facility, city, state, country}
  
  url VARCHAR(500),
  
  created_at TIMESTAMP DEFAULT now(),
  updated_at TIMESTAMP DEFAULT now(),
  
  INDEX idx_nct_id (nct_id),
  INDEX idx_status (status),
  INDEX idx_conditions (conditions, created_at)
);
```

#### Table: `pubmed_citations`
```sql
CREATE TABLE pubmed_citations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  pmid VARCHAR(20) UNIQUE NOT NULL,
  
  title VARCHAR(1000) NOT NULL,
  abstract TEXT,
  
  authors JSONB,  -- Array of {name, affiliation}
  journal VARCHAR(500),
  pub_date DATE,
  
  mesh_terms JSONB,  -- Array of MeSH controlled vocabulary terms
  keywords JSONB,
  
  doi VARCHAR(100),
  pubmed_url VARCHAR(500),
  
  -- Cross-references
  conditions JSONB,
  drugs JSONB,
  procedures JSONB,
  
  article_type VARCHAR(100),  -- RESEARCH, REVIEW, CASE_STUDY, etc.
  impact_factor DECIMAL(5, 2),
  
  created_at TIMESTAMP DEFAULT now(),
  
  INDEX idx_pmid (pmid),
  INDEX idx_doi (doi),
  INDEX idx_date (pub_date)
);
```

#### Table: `drug_labels`
```sql
CREATE TABLE drug_labels (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  set_id VARCHAR(50) UNIQUE NOT NULL,
  
  brand_name VARCHAR(500),
  generic_name VARCHAR(500),
  
  indications_and_usage TEXT,
  dosage_and_administration TEXT,
  
  warnings JSONB,  -- Array of warning categories
  contraindications TEXT,
  precautions JSONB,
  
  adverse_reactions JSONB,  -- Array of {reaction, frequency, severity}
  drug_interactions TEXT,
  
  storage_conditions VARCHAR(500),
  
  version VARCHAR(20),
  effective_date DATE,
  last_updated DATE,
  
  source_url VARCHAR(500),  -- DailyMed URL
  
  -- Cross-references
  ndc_codes JSONB,
  rxcui VARCHAR(10),
  
  created_at TIMESTAMP DEFAULT now(),
  updated_at TIMESTAMP DEFAULT now(),
  
  INDEX idx_set_id (set_id),
  INDEX idx_rxcui (rxcui)
);
```

### Compliance Tables

#### Table: `oig_exclusions`
```sql
CREATE TABLE oig_exclusions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  
  entity_name VARCHAR(500) NOT NULL,
  entity_type VARCHAR(50),  -- 'INDIVIDUAL', 'ORGANIZATION'
  
  npi VARCHAR(10),
  tin VARCHAR(9),  -- Tax ID
  
  exclusion_type VARCHAR(100),  
  -- 'CONVICTION', 'CIVIL_JUDGMENT', 'EXCLUSION', 'SUSPENSION'
  
  exclusion_date DATE NOT NULL,
  reinstatement_date DATE,
  
  state VARCHAR(2),
  description TEXT,
  
  -- Data provenance
  source_url VARCHAR(500),
  date_imported TIMESTAMP,
  
  created_at TIMESTAMP DEFAULT now(),
  
  INDEX idx_npi (npi),
  INDEX idx_exclusion_date (exclusion_date),
  INDEX idx_status (CASE WHEN reinstatement_date IS NULL THEN 'ACTIVE' ELSE 'REINSTATED' END)
);
```

#### Table: `sam_exclusions`
```sql
CREATE TABLE sam_exclusions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  
  entity_name VARCHAR(500) NOT NULL,
  entity_type VARCHAR(50),  -- 'INDIVIDUAL', 'ORGANIZATION'
  
  cage_code VARCHAR(5),
  tin VARCHAR(9),
  duns VARCHAR(9),
  
  exclusion_type VARCHAR(100),  
  -- 'INDIVIDUAL_CONVICTION', 'ORGANIZATIONAL_CONVICTION', 'DEBARRED', etc.
  
  active_date DATE,
  termination_date DATE,
  
  sam_number VARCHAR(50),
  
  source_url VARCHAR(500),
  date_imported TIMESTAMP,
  
  created_at TIMESTAMP DEFAULT now(),
  
  INDEX idx_cage_code (cage_code),
  INDEX idx_active_date (active_date)
);
```

#### Table: `adverse_actions`
```sql
CREATE TABLE adverse_actions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  npdb_seq VARCHAR(20) UNIQUE,
  
  provider_id UUID REFERENCES providers(id),
  npi VARCHAR(10),
  
  action_type VARCHAR(100),  
  -- 'MALPRACTICE', 'CONVICTION', 'LICENSURE_SANCTION', 'HEALTHCARE_EXCLUSION'
  
  basis_for_action VARCHAR(500),
  description TEXT,
  
  action_date DATE,
  settlement_amount DECIMAL(12, 2),
  
  state VARCHAR(2),
  specialty_involved VARCHAR(255),
  
  source VARCHAR(100),
  source_url VARCHAR(500),
  
  created_at TIMESTAMP DEFAULT now(),
  
  FOREIGN KEY (provider_id) REFERENCES providers(id),
  INDEX idx_provider_id (provider_id),
  INDEX idx_npi (npi),
  INDEX idx_action_date (action_date)
);
```

### Knowledge Graph Bridge Tables

#### Table: `entity_relationships`
```sql
CREATE TABLE entity_relationships (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  
  source_entity_type VARCHAR(100),  
  -- 'PROVIDER', 'DRUG', 'CONDITION', 'ORGANIZATION', 'TRIAL', 'CODE'
  source_entity_id VARCHAR(100),
  
  relationship_type VARCHAR(100),  
  -- 'TREATS', 'INTERACTS_WITH', 'CERTIFIED_IN', 'WORKS_AT', 'CONTRAINDICATED_FOR', etc.
  
  target_entity_type VARCHAR(100),
  target_entity_id VARCHAR(100),
  
  -- Metadata
  metadata JSONB,  -- {strength: 'moderate', confidence: 0.95, source: 'FDA'}
  weight DECIMAL(3, 2),  -- Relationship strength (0-1)
  
  created_at TIMESTAMP DEFAULT now(),
  updated_at TIMESTAMP DEFAULT now(),
  
  INDEX idx_source (source_entity_type, source_entity_id),
  INDEX idx_target (target_entity_type, target_entity_id),
  INDEX idx_relationship (relationship_type)
);
```

#### Table: `data_provenance`
```sql
CREATE TABLE data_provenance (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  
  entity_type VARCHAR(100),
  entity_id VARCHAR(100),
  
  source_name VARCHAR(100),  -- 'NPPES', 'FDA', 'ClinicalTrials.gov', etc.
  source_url VARCHAR(500),
  
  ingestion_date TIMESTAMP,
  ingestion_run_id UUID,
  
  data_hash VARCHAR(64),  -- SHA-256 of entity data at ingestion
  freshness_score DECIMAL(3, 2),  -- 0-1, how fresh is this data
  
  next_refresh_date TIMESTAMP,
  
  created_at TIMESTAMP DEFAULT now(),
  
  INDEX idx_entity (entity_type, entity_id),
  INDEX idx_source (source_name),
  INDEX idx_refresh_date (next_refresh_date)
);
```

### Data Ingestion Tracking

#### Table: `ingestion_runs`
```sql
CREATE TABLE ingestion_runs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  
  source_name VARCHAR(100) NOT NULL,  -- 'NPPES', 'FDA', 'PubMed', etc.
  run_type VARCHAR(50),  -- 'FULL', 'INCREMENTAL'
  
  started_at TIMESTAMP DEFAULT now(),
  completed_at TIMESTAMP,
  
  records_processed INT,
  records_added INT,
  records_updated INT,
  records_failed INT,
  
  status VARCHAR(50),  -- 'IN_PROGRESS', 'SUCCESS', 'FAILED', 'PARTIAL'
  error_log TEXT,  -- JSON array of errors
  
  duration_seconds INT,
  
  created_at TIMESTAMP DEFAULT now(),
  
  INDEX idx_source (source_name),
  INDEX idx_status (status),
  INDEX idx_completed (completed_at)
);
```

#### Table: `ingestion_errors`
```sql
CREATE TABLE ingestion_errors (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  
  ingestion_run_id UUID NOT NULL REFERENCES ingestion_runs(id),
  
  error_type VARCHAR(100),  -- 'VALIDATION_ERROR', 'API_ERROR', 'PARSING_ERROR'
  error_message TEXT,
  error_details JSONB,
  
  record_number INT,
  record_data JSONB,  -- The problematic record
  
  created_at TIMESTAMP DEFAULT now(),
  
  FOREIGN KEY (ingestion_run_id) REFERENCES ingestion_runs(id) ON DELETE CASCADE,
  INDEX idx_run_id (ingestion_run_id)
);
```

### Summary Indexes & Materialized Views

Create these high-performance views:

```sql
-- Provider Verification Status Dashboard
CREATE MATERIALIZED VIEW provider_verification_status AS
SELECT 
  p.id,
  p.npi,
  p.full_name,
  p.specialty_name,
  COUNT(CASE WHEN pv.status = 'SUCCESS' THEN 1 END) as successful_verifications,
  COUNT(CASE WHEN pv.status = 'FAILED' THEN 1 END) as failed_verifications,
  MAX(pv.verification_date) as last_verified,
  CASE 
    WHEN NOW() - MAX(pv.verification_date) > '90 days'::interval THEN 'STALE'
    WHEN COUNT(CASE WHEN pv.status = 'FAILED' THEN 1 END) > 2 THEN 'AT_RISK'
    ELSE 'CURRENT'
  END as verification_health
FROM providers p
LEFT JOIN provider_verifications pv ON p.id = pv.provider_id
GROUP BY p.id, p.npi, p.full_name, p.specialty_name;

-- Data Freshness Dashboard
CREATE MATERIALIZED VIEW data_freshness_by_source AS
SELECT 
  source_name,
  COUNT(*) as total_entities,
  COUNT(CASE WHEN freshness_score >= 0.8 THEN 1 END) as fresh_count,
  AVG(freshness_score) as avg_freshness,
  MAX(ingestion_date) as last_ingestion,
  MIN(next_refresh_date) as next_refresh_needed
FROM data_provenance
GROUP BY source_name;
```

---

## ENTITY URL ARCHITECTURE

Every entity in HKG gets a permanent, citable URL. These URLs are the public face of the knowledge graph and are discoverable by AI systems.

### URL Patterns by Entity Type

```
/providers/{npi}                           Provider profile (NPI is unique, public identifier)
/providers/{npi}/credentials                Provider credential detail page
/providers/{npi}/verification-status        Verification status & timeline
/providers/{npi}/prescriptions              Provider's prescribing patterns (compliance view)

/organizations/{npi}                        Organization/facility profile
/organizations/{npi}/quality-measures       CMS quality & performance data
/organizations/{npi}/adverse-events         Adverse action history

/codes/icd10/{code}                         ICD-10-CM diagnosis code detail
/codes/icd10/{code}/similar                 Clinically similar diagnosis codes
/codes/icd10-pcs/{code}                     ICD-10-PCS procedure code detail
/codes/hcpcs/{code}                         HCPCS procedure/supply code detail
/codes/cpt/{code}                           CPT code detail (limited by AMA license)
/codes/ndc/{ndc}                            NDC drug code detail
/codes/drg/{code}                           DRG group detail & reimbursement

/drugs/{rxcui}                              Drug entity page
/drugs/{rxcui}/interactions                 Drug interaction matrix
/drugs/{rxcui}/labels                       FDA approved product labels
/drugs/{rxcui}/adverse-events               FAERS adverse event reports
/drugs/{rxcui}/prescribers                  Prescribing patterns by specialty

/conditions/{snomed_code}                   Medical condition detail
/conditions/{snomed_code}/epidemiology      Epidemiology & risk factors
/conditions/{snomed_code}/treatments        Evidence-based treatment options
/conditions/{snomed_code}/research          Related clinical trials & publications

/trials/{nct_id}                            Clinical trial detail page
/trials/{nct_id}/sites                      Trial sites by geography

/research/{pmid}                            PubMed citation detail
/research/by-condition/{snomed_code}        Latest research for a condition
/research/by-drug/{rxcui}                   Latest research on a drug

/states/{state_code}/licensing               State licensing requirements & board info
/states/{state_code}/boards/{board_id}      State medical board directory
/states/{state_code}/providers               Provider roster for state

/billing/codes                              Billing code cross-reference tools
/billing/reimbursement-rates                Medicare fee schedule by code/region

/verify                                      Verification tool directory
```

### URL Design Principles

1. **Use natural identifiers** — NPI, SNOMED code, RxCUI, NCT ID, PMID. These are stable, external, and citable.
2. **Hierarchical paths** — Parents are always comprehendible. `/drugs/{rxcui}/interactions` implies it's part of the drug entity.
3. **Plural collections** — `/conditions` (list), `/conditions/{code}` (detail).
4. **Query parameters for filtering** — `/drugs/{rxcui}/interactions?severity=serious` for filtered views.
5. **Trailing `.md` for machine readability** — `/conditions/hypertension.md` serves Markdown for AI parsing.
6. **Trailing `.json` for structured data** — `/conditions/hypertension.json` serves JSON-LD for schema extraction.

---

## DATA INGESTION PIPELINE ARCHITECTURE

### Three-Tier Priority System

#### **Priority 0 (Weeks 1-2): Foundation Ingestion**

These are the absolute must-haves. They power the Administrator and Doctor lanes immediately.

| Source | Ingestion | Frequency | Table | Estimated Time |
|---|---|---|---|---|
| NPPES/NPI (bulk) | Bulk CSV download | Seed (Week 1) | `providers`, `provider_credentials` | 4 hours |
| NPPES (incremental) | Weekly API pull | Weekly ongoing | `providers` | 2 hours |
| ICD-10-CM 2024 | XML download | One-time seed | `icd10_cm` | 1 hour |
| ICD-10-PCS 2024 | XML download | One-time seed | `icd10_pcs` | 1 hour |
| HCPCS Level II | CSV download | Quarterly | `hcpcs_codes` | 30 min |
| MS-DRG 2024 | Excel download | Annual | `ms_drg` | 30 min |
| OIG LEIE | CSV monthly dump | Monthly | `oig_exclusions` | 2 hours |
| SAM.gov Exclusions | REST API daily pull | Daily | `sam_exclusions` | 1 hour |

**Implementation:**
- Write Python ETL scripts for each source
- Store as `/data-ingestion/npi_ingest.py`, `/data-ingestion/icd10_ingest.py`, etc.
- Use Supabase client libraries for bulk inserts
- Implement transaction logging in `ingestion_runs` table
- Set up error alerts if any run fails

**Success Criteria:**
- 9.5M providers in `providers` table (NPI registry)
- 70K ICD-10-CM codes in `icd10_cm` table
- 0 orphaned credentials (every credential links to a provider)
- All OIG LEIE records imported

#### **Priority 1 (Weeks 3-4): Clinical Knowledge Layer**

These sources expand the graph with clinical information and enable the Doctor lane.

| Source | Ingestion | Frequency | Table |
|---|---|---|---|
| NDC Directory | FDA API daily export | Daily | `ndc_drugs` |
| RxNorm | NLM REST API | Monthly | `drugs` |
| DailyMed | FDA API | Daily | `drug_labels` |
| CMS Provider Data | CSV file | Weekly | `organizations`, entity relationships |
| PubMed MEDLINE | Bulk XML + daily API | Daily incremental | `pubmed_citations` |
| ClinicalTrials.gov | REST API v2 | Daily | `clinical_trials` |

**Implementation:**
- PubMed: Use NCBI E-utilities API (10 requests/sec rate limit)
- ClinicalTrials.gov: Use v2 API with pagination
- DailyMed: Download entire catalog monthly, update daily changes
- RxNorm: Cache full download locally, update monthly
- Implement batch processing for millions of records

**Success Criteria:**
- 200K+ drugs in `ndc_drugs`
- 40M+ citations indexed (searchable subset, full raw data stored)
- 500K+ trials in `clinical_trials`
- Drug-to-condition relationships populated for top 1000 drugs

#### **Priority 2 (Weeks 5-8): Advanced Verification & Research**

These enable deeper verification and unlock longevity/research content for the Patient lane.

| Source | Ingestion | Frequency | Table |
|---|---|---|---|
| SNOMED CT (via UMLS) | Download from UMLS | Quarterly | Graph relationships |
| LOINC | CSV download | Quarterly | Lab code mappings |
| FAERS (Adverse Events) | FDA API | Quarterly | `drug_interactions`, `adverse_actions` |
| NIH RePORTER | API | Weekly | Research tracking |
| FDA FAERS Detail | Bulk CSV | Quarterly | Drug safety signals |

**Implementation:**
- SNOMED/LOINC: Map to existing entities, don't duplicate
- FAERS: Build signal detection (unusual AE patterns)
- RePORTER: Track NIH-funded longevity research for Patient lane

#### **Priority 3 (Ongoing): Continuous Enrichment**

These are nice-to-have but not blocking launch.

| Source | Use Case |
|---|---|
| CAQH ProView | Enhanced provider data (license required) |
| FSMB DocInfo | Physician board certifications (license required) |
| ABMS Certification | Specialty board data (license required) |
| State Medical Boards | Individual state license verification (50+ sources) |
| DrugBank | Drug interaction detail & pharmacology |
| GeneCards/UniProt | Genetic research context |

### Ingestion Pipeline Workflow

```
1. TRIGGER
   └─ Scheduled (cron) OR manual trigger

2. VALIDATE SOURCE
   └─ Check rate limits, availability, auth (if needed)

3. FETCH DATA
   └─ Download/API pull with resume capability for large files

4. PARSE
   └─ CSV → objects, XML → objects, JSON → objects
   └─ Handle encoding issues, incomplete records

5. NORMALIZE
   └─ Map to Supabase schema
   └─ Apply business rules (deduplicate, validate foreign keys)
   └─ Add data_source, ingestion_date, data_hash

6. VALIDATE
   └─ Check constraints, required fields
   └─ Cross-reference (e.g., NPI must exist in providers table)
   └─ Log validation errors → ingestion_errors table

7. UPSERT
   └─ INSERT new records
   └─ UPDATE existing records if data_hash differs
   └─ Track in ingestion_runs: records_added, records_updated, records_failed

8. POST-PROCESS
   └─ Update data_provenance freshness_score
   └─ Trigger Neo4j sync event (if changes made)
   └─ Update materialized views

9. MONITOR
   └─ Alert if any step fails
   └─ Log metrics: duration, records processed, error rate
   └─ Update ingestion_runs table with completion status

10. SYNC TO NEO4J
    └─ Event-driven: INSERT/UPDATE in Supabase triggers Neo4j node creation
    └─ Create relationships in Neo4j based on entity_relationships table
```

### Event-Driven Sync: Supabase → Neo4j

Whenever a record is updated in Supabase (providers, drugs, conditions, etc.), an automated event publishes to a message queue. Neo4j workers subscribe and:

1. Create/update nodes (PROVIDER, DRUG, CONDITION, etc.)
2. Set properties (NPI, RxCUI, SNOMED code, name, etc.)
3. Create relationships based on `entity_relationships` table
4. Update search indexes

This ensures Neo4j is always a derived view of Supabase truth, never out of sync.

---

## RSI HEARTBEAT SCHEDULE

The Recursive Self-Improvement heartbeat is the platform's competitive moat. Here's the automated refresh schedule:

### Daily Refresh (Every night at 2 AM UTC)

```
02:00 - NPI Registry (incremental from weekly file)
03:00 - NDC Directory (full reload)
04:00 - DailyMed (all FDA labels)
05:00 - PubMed new citations (published in last 24 hours)
06:00 - ClinicalTrials.gov (all status changes)
07:00 - Freshness score recalculation
08:00 - Neo4j sync & index optimization
```

**What changes:** ~50K NPI updates, 100+ new drug entries, 500+ new PubMed citations, 100+ trial status changes

### Weekly Refresh (Every Sunday, 3 AM UTC)

```
03:00 - NPI full weekly file (CMS publishes Tuesdays)
04:00 - State board spot-checks (sample of 50 random providers)
05:00 - CMS Provider Enrollment updates
06:00 - Hospital Compare metrics
07:00 - Neo4j relationship re-evaluation (new connections discovered)
```

### Monthly Refresh (First of month, 4 AM UTC)

```
04:00 - OIG LEIE full list (published monthly)
05:00 - SAM.gov complete exclusions file
06:00 - RxNorm monthly update
07:00 - Medicare Fee Schedule adjustments (if published)
08:00 - Duplicate detection & deduplication pass
```

### Quarterly Refresh (Jan 1, Apr 1, Jul 1, Oct 1 at 5 AM UTC)

```
05:00 - HCPCS Level II updates
06:00 - SNOMED CT updates
07:00 - LOINC new lab codes
08:00 - FAERS adverse event bulk download & signal detection
09:00 - CMS quality measures refresh
10:00 - Neo4j full index rebuild
```

### Annual Refresh (Jan 1, 1 PM UTC)

```
13:00 - ICD-10-CM new code set (effective October)
14:00 - ICD-10-PCS new code set
15:00 - MS-DRG recalibration
16:00 - CPT code updates (if licensed)
17:00 - Full validation pass: no orphaned records, all FK constraints
18:00 - Archive old data versions for audit trail
```

### Monitoring & Alerting

For each refresh:
1. Track in `ingestion_runs` table: start time, end time, record counts, errors
2. Alert if any job fails or takes >2x expected duration
3. Update `data_provenance.freshness_score` based on days since last ingestion:
   - `freshness_score = 1.0` if updated within SLA window
   - `freshness_score = 0.8` if 1-2 days late
   - `freshness_score = 0.5` if 3-7 days late
   - `freshness_score = 0.2` if older than 7 days

### Dashboard: "HKG Data Freshness"

Display live on admin panel:
```
NPI Registry: Updated 2 hours ago (9.5M records) ✓
NDC Drugs: Updated 14 hours ago (200K records) ✓
ICD-10-CM: Updated 34 days ago (70K records) ⚠
PubMed: Updated 4 hours ago (40M+ indexed) ✓
ClinicalTrials.gov: Updated 3 hours ago (500K+ trials) ✓
OIG LEIE: Updated 12 days ago (next due Apr 1) ⚠
State Boards: 2 of 50 checked (sampling) ⚠
```

---

## AI CITATION LAYER

### Entity Page Structure

Every entity page (provider, drug, condition, code, trial, research) is structured for AI discoverability.

#### JSON-LD Schema Markup (In Every Page Head)

Every HTML page includes JSON-LD schema for the entity:

```json
{
  "@context": "https://schema.org",
  "@type": "MedicalCondition",
  "name": "Hypertension",
  "description": "High blood pressure (≥130/80 mmHg)",
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
  "url": "https://hkg.example.com/conditions/hypertension",
  "datePublished": "2024-06-15",
  "dateModified": "2026-04-08",
  "inLanguage": "en-US",
  "author": {
    "@type": "Organization",
    "name": "Healthcare Knowledge Garden",
    "url": "https://hkg.example.com"
  },
  "isAccessibleForFree": true
}
```

**Schema Types by Entity:**
- Provider: `MedicalBusiness`, `Physician`, `MedicalProcedure`
- Drug: `Drug`, `MedicalEntity`
- Condition: `MedicalCondition`, `DiseaseOrMedicalCondition`
- Code: `MedicalCode`
- Trial: `MedicalStudy`, `ResearchAction`
- Research: `ScholarlyArticle`, `MedicalScholarlyArticle`

#### Markdown Companion Files

For each entity page (HTML), generate a `.md` file:

```
# Hypertension

## Overview
[Concise, AI-friendly summary]

## Clinical Definition
[Evidence-based definition]

## ICD-10 Codes
- I10: Essential hypertension
- I11: Hypertensive heart disease
- I12: Hypertensive chronic kidney disease

## Related Drugs
- Lisinopril (ACE inhibitor)
- Metoprolol (Beta blocker)
- Amlodipine (Calcium channel blocker)

## Clinical Trials
- NCT03456789: SPRINT trial (ongoing)
- NCT02345678: DASH diet study (completed)

## Research
- PMID: 35123456 - "Hypertension management 2024"
- PMID: 35234567 - "ACE inhibitors vs ARBs"

## Data Provenance
- Updated: 2026-04-08
- Sources: FDA, NIH, CMS
```

URLs: `/conditions/hypertension.md`, `/conditions/hypertension.json`

#### JSON Export Format

For machine consumption:

```json
{
  "id": "snomed-38341003",
  "entityType": "CONDITION",
  "name": "Hypertension",
  "summary": "High blood pressure (≥130/80 mmHg)",
  "codes": [
    {
      "system": "ICD-10-CM",
      "code": "I10",
      "description": "Essential hypertension"
    }
  ],
  "url": "https://hkg.example.com/conditions/hypertension",
  "dateModified": "2026-04-08",
  "provenance": {
    "sources": ["FDA", "CMS", "NIH"],
    "lastVerified": "2026-04-08",
    "freshness": 0.95
  },
  "relationships": {
    "relatedDrugs": ["rxcui-6722", "rxcui-5487"],
    "relatedConditions": ["snomed-40733004"],
    "relatedTrials": ["NCT03456789"]
  }
}
```

### llms.txt & llms-full.txt

See HKG_AI_Citation_Strategy.md for full details.

**Summary:**
- `/llms.txt` — Directory of all entity categories with links
- `/llms-full.txt` — Complete Markdown content of top 2000 entities (regenerated quarterly)
- Invites AI crawlers at inference time (not training time)

### Structured Sitemap

```xml
<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"
        xmlns:image="http://www.google.com/schemas/sitemap-image/1.1"
        xmlns:mobile="http://www.google.com/schemas/sitemap-mobile/1.1">
  
  <url>
    <loc>https://hkg.example.com/conditions/hypertension</loc>
    <lastmod>2026-04-08</lastmod>
    <changefreq>weekly</changefreq>
    <priority>0.9</priority>
  </url>
  
  <url>
    <loc>https://hkg.example.com/drugs/metformin</loc>
    <lastmod>2026-04-07</lastmod>
    <changefreq>weekly</changefreq>
    <priority>0.85</priority>
  </url>
  
  <!-- Repeat for all 100K+ entities -->
</urlset>
```

**Sitemap Tiers:**
- Priority 0.95: Top 100 conditions, top 500 drugs (high traffic)
- Priority 0.90: Top 5000 conditions, top 10000 drugs (frequently searched)
- Priority 0.75: All ICD-10 codes, all HCPCS codes (comprehensive coverage)
- Priority 0.60: Clinical trials, research papers (discovery content)

### Content Freshness Targets

| Entity Type | Target Freshness | Update Frequency | Confidence |
|---|---|---|---|
| Provider (NPI) | 90 days max | Weekly ingestion | P0 Critical |
| Drug (NDC) | 7 days max | Daily ingestion | P0 Critical |
| Medical Code (ICD-10) | 12 months max | Annual ingestion | P0 Critical |
| Condition | 30 days max | As research updates | P1 High |
| Clinical Trial | 7 days max | Daily ingestion | P1 High |
| PubMed Citation | 1 day max | Daily ingestion | P2 Medium |

**Display freshness badges on entity pages:**
```
Last Updated: 2 days ago (97% fresh)
Next Update: Scheduled for today at 2 AM UTC
Data Quality: ★★★★★ (5/5 sources verified)
```

---

## STATE-BY-STATE VERIFICATION MATRIX

Complete matrix for 50 states + territories. Track public data availability, API access, and update frequency.

| State | Board URL | Public Lookup | Data Exposed | API Available | Update Frequency | Scrape Status | Notes |
|---|---|---|---|---|---|---|---|
| CA (California) | mbc.ca.gov | Yes | Name, License #, Specialty, Status | Partial (search only) | Weekly | ✓ Feasible | Large dataset (~100K physicians) |
| NY (New York) | op.nysed.gov | Yes | Name, License #, Status | No, HTML parse only | Weekly | ✓ Working | High-traffic site, rate limits needed |
| TX (Texas) | tsbme.texas.gov | Yes | Full profile available | No | Monthly | ✓ Feasible | Good data quality |
| FL (Florida) | flbom.gov | Yes | Name, License, Status, Discipline | No | Weekly | ✓ Working | Often referenced in compliance |
| PA (Pennsylvania) | dos.pa.gov | Yes | Public lookup available | No | Quarterly | ⚠ Limited | Slower updates |
| OH (Ohio) | med.ohio.gov | Yes | Full directory | No | Bi-weekly | ✓ Feasible | Well-organized database |
| IL (Illinois) | cyberdriveillinois.com | Yes | License lookup | No | Weekly | ⚠ Complex | Portal requires session handling |
| MI (Michigan) | michigan.gov/som | Yes | Directory available | No | Monthly | ✓ Feasible | Good data structure |
| NC (North Carolina) | ncmedboard.org | Yes | Full lookup | No | Weekly | ✓ Feasible | Clear public interface |
| MA (Massachusetts) | mass.gov/boards | Yes | Lookup available | No | Monthly | ⚠ Rate limited | Known to block frequent requests |
| WA (Washington) | doh.wa.gov | Yes | Full search | No | Monthly | ✓ Feasible | Responsive HTML |
| CO (Colorado) | dora.colorado.gov | Yes | License directory | No | Quarterly | ⚠ Limited | Slower refresh |
| GA (Georgia) | sos.ga.gov | Yes | Board lookup | No | Monthly | ⚠ Limited | Good structure but updates slow |
| MD (Maryland) | mhcc.maryland.gov | Yes | Full profile | No | Monthly | ✓ Feasible | Well-maintained |
| VA (Virginia) | dhp.virginia.gov | Yes | License search | No | Monthly | ✓ Feasible | Public data readily available |
| [... continue for 35 more states] |

**Legend:**
- **Public Lookup:** Can find a specific physician without login
- **Data Exposed:** What info is available (name, license, status, discipline history, etc.)
- **API Available:** Official API (rare), or HTML scraping only
- **Update Frequency:** How often the state updates their records
- **Scrape Status:** ✓ Working, ⚠ Difficult, ✗ Not feasible
- **Notes:** Special handling needed, rate limits, etc.

### Strategy for State Board Integration

**Phase 1 (Months 1-3):** Target the 15 largest states (CA, TX, FL, NY, PA, IL, OH, MI, GA, NC, VA, AZ, MA, CO, IN)
- Implement state-specific scrapers with error handling
- Build dashboard to track verification status
- Create alerts when discipline history found

**Phase 2 (Months 4-6):** Expand to all 50 states
- Standardize scraper patterns
- Build rate limiting per state
- Create validation rules (license numbers, specialty codes)

**Phase 3 (Months 7+):** Continuous monitoring
- Daily credential checks on verified providers
- Alert when licenses change status
- Track disciplinary actions in real-time

---

## IMPLEMENTATION ROADMAP

### Week 1-2 (Foundation)

**Goal:** Ingest all foundational data sources into Supabase

Tasks:
- [ ] Create Supabase PostgreSQL database with all P0 tables
- [ ] Write ETL scripts: NPI, ICD-10-CM/PCS, HCPCS, MS-DRG, OIG LEIE, SAM.gov
- [ ] Run initial full seed of `providers`, `icd10_cm`, `icd10_pcs`, codes tables
- [ ] Set up daily/weekly ingestion jobs with cron scheduling
- [ ] Build `ingestion_runs` monitoring dashboard
- [ ] Write integration tests (data quality checks)

**Success Criteria:**
- 9.5M+ providers in database
- 70K+ ICD-10-CM codes
- 78K+ ICD-10-PCS codes
- All ingestion jobs passing

### Week 3-4 (Clinical Knowledge)

**Goal:** Ingest clinical data and create Neo4j knowledge graph

Tasks:
- [ ] Write ETL: NDC, RxNorm, DailyMed, PubMed (initial batch), ClinicalTrials.gov
- [ ] Create Neo4j schema (nodes, relationships)
- [ ] Build event-driven sync from Supabase → Neo4j
- [ ] Populate initial relationship edges (provider → specialty, drug → interaction)
- [ ] Test Neo4j query performance
- [ ] Create basic dashboard: "Knowledge Graph Stats" (# nodes, # edges, query latency)

**Success Criteria:**
- 200K+ drugs in database
- 40M+ PubMed citations indexed
- 500K+ clinical trials
- Neo4j has 15M+ relationships
- 1M nodes created from Supabase

### Week 5-8 (Public Web Layer)

**Goal:** Generate AI-citable entity pages

Tasks:
- [ ] Build entity page template system (React component + template)
- [ ] Generate HTML pages for top 10K entities (conditions, drugs, procedures)
- [ ] Add JSON-LD schema markup to all pages
- [ ] Generate Markdown companion files (`.md` versions)
- [ ] Create `/llms.txt` and `/llms-full.txt` files
- [ ] Generate XML sitemap for all entities
- [ ] Deploy to Vercel with proper caching headers
- [ ] Test AI crawler crawlability (simulate Claude, ChatGPT crawlers)

**Success Criteria:**
- 10K+ static pages generated and deployed
- All pages have valid JSON-LD schema (test with Google Schema validator)
- `/llms.txt` discoverable and well-formatted
- Sitemaps valid and comprehensive
- Pages render correctly for AI crawlers (check User-Agent headers)

### Week 9-13 (Verification & Quality)

**Goal:** Implement verification system and quality assurance

Tasks:
- [ ] Build state board scraper framework
- [ ] Implement scrapers for 15 largest states
- [ ] Create `provider_verifications` ingestion pipeline
- [ ] Build verification status dashboard
- [ ] Implement alerts for credential changes/expirations
- [ ] Create data quality scoring system
- [ ] Run comprehensive validation: FK constraints, orphaned records, duplicates
- [ ] Implement deduplication logic for providers (same person, different records)

**Success Criteria:**
- 15 state boards integrated
- 5M+ providers verified across sources
- <0.1% data quality issues (orphaned records, broken links)
- Verification dashboard shows real-time status
- Alerts triggering correctly on credential changes

### Week 14-18 (Polish & Launch)

**Goal:** Optimize, test, and launch public knowledge base

Tasks:
- [ ] Performance optimization: Database indexes, query optimization, caching
- [ ] Load testing: Simulate 1000+ concurrent AI crawlers
- [ ] Security audit: HIPAA compliance, data encryption, access controls
- [ ] Create admin dashboard: Ingestion monitoring, data freshness, verification status
- [ ] Write API documentation for Machine Lane
- [ ] Set up monitoring & alerting (Datadog, Sentry, etc.)
- [ ] Launch public landing page
- [ ] Submit to AI crawler directories (Anthropic, OpenAI, Perplexity)

**Success Criteria:**
- Database handles 10M+ queries/day smoothly
- Pages load <200ms for AI crawlers
- All security audits pass
- Monitoring dashboard showing all green
- First AI citations appearing (can be tracked via Referer headers)

---

## CONCLUSION: THE KNOWLEDGE MOAT

The HKG data architecture is not just a database. It's the nervous system of the global healthcare ecosystem.

By ingesting from 30+ authoritative sources, normalizing into a unified graph, and exposing every entity as an AI-citable page, HKG becomes the thing the entire industry references. Every patient looking up a drug, every doctor verifying a credential, every AI assistant answering a medical question — they all cite HKG.

The RSI heartbeat keeps the platform fresh daily. Competitors are static snapshots. We are a living knowledge system.

The three-database architecture (Neo4j + Supabase + Web) ensures we can serve every use case: complex relationship queries (graph), transactional operations (relational), and human/AI discovery (web/llms.txt).

This is not a feature. This is infrastructure.

Build it first. Build it right. Build it once.

---

**Document Author:** Claude Code | **Status:** Production-Ready Specification | **Last Updated:** April 8, 2026

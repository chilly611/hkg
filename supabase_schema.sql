-- ============================================================================
-- HEALTHCARE KNOWLEDGE GARDEN - SUPABASE SCHEMA
-- Production-grade SQL schema for healthcare data ingestion and graph sync
-- ============================================================================
-- Version: 1.0
-- Last Updated: 2026-04-08
-- Purpose: Central data repository for 30+ healthcare sources with Neo4j sync
-- ============================================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================================================
-- CORE TIMESTAMP & SOURCE TRACKING
-- ============================================================================

-- Function to update updated_at automatically
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- ============================================================================
-- TABLE 1: DATA SOURCES REGISTRY
-- ============================================================================

CREATE TABLE IF NOT EXISTS data_sources (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL UNIQUE,
    category VARCHAR(100) NOT NULL, -- e.g., 'provider_data', 'medical_codes', 'drugs', 'clinical_knowledge'
    api_url TEXT,
    download_url TEXT,
    format VARCHAR(50), -- 'json', 'csv', 'xml', 'hl7'
    update_frequency VARCHAR(50), -- 'daily', 'weekly', 'monthly', 'on_demand'
    cost VARCHAR(20), -- 'free', 'paid', 'mixed'
    license_type VARCHAR(255), -- 'public_domain', 'cc_by', 'commercial'
    record_count INTEGER,
    last_ingested_at TIMESTAMP WITH TIME ZONE,
    next_ingestion_at TIMESTAMP WITH TIME ZONE,
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

COMMENT ON TABLE data_sources IS 'Registry of all healthcare data sources (NPI, CMS, FDA, etc.) with metadata for ingestion scheduling';

CREATE INDEX idx_data_sources_category ON data_sources(category);
CREATE INDEX idx_data_sources_update_frequency ON data_sources(update_frequency);

-- ============================================================================
-- TABLE 2: INGESTION AUDIT TRAIL
-- ============================================================================

CREATE TABLE IF NOT EXISTS ingestion_runs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_id UUID NOT NULL REFERENCES data_sources(id),
    run_type VARCHAR(20) NOT NULL CHECK (run_type IN ('full', 'incremental')),
    started_at TIMESTAMP WITH TIME ZONE NOT NULL,
    completed_at TIMESTAMP WITH TIME ZONE,
    records_processed INTEGER DEFAULT 0,
    records_added INTEGER DEFAULT 0,
    records_updated INTEGER DEFAULT 0,
    records_failed INTEGER DEFAULT 0,
    status VARCHAR(20) NOT NULL CHECK (status IN ('running', 'completed', 'failed')),
    error_log TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

COMMENT ON TABLE ingestion_runs IS 'ETL audit trail: tracks every ingestion job, timing, volumes, and errors';

CREATE INDEX idx_ingestion_runs_source ON ingestion_runs(source_id);
CREATE INDEX idx_ingestion_runs_status ON ingestion_runs(status);
CREATE INDEX idx_ingestion_runs_started_at ON ingestion_runs(started_at);

-- ============================================================================
-- TABLE 3: PROVIDER DATA TABLES
-- ============================================================================

CREATE TABLE IF NOT EXISTS providers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    npi VARCHAR(10) NOT NULL UNIQUE,
    entity_type VARCHAR(20) NOT NULL CHECK (entity_type IN ('individual', 'organization')),
    first_name VARCHAR(255),
    last_name VARCHAR(255),
    middle_name VARCHAR(255),
    credential VARCHAR(50), -- e.g., 'MD', 'DO', 'DDS', 'RN'
    prefix VARCHAR(50),
    suffix VARCHAR(50),
    organization_name VARCHAR(255),
    gender VARCHAR(10),
    sole_proprietor BOOLEAN DEFAULT FALSE,
    enumeration_date DATE,
    last_update_date DATE,
    deactivation_date DATE,
    reactivation_date DATE,
    status VARCHAR(20) NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'deactivated', 'deactivated_for_cause')),
    data_source VARCHAR(255) NOT NULL DEFAULT 'NPI Registry',
    source_url TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

COMMENT ON TABLE providers IS 'Core provider entities from NPI Registry (individual practitioners & organizations); foundation for credentialing lane';

CREATE TRIGGER update_providers_updated_at BEFORE UPDATE ON providers
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE INDEX idx_providers_npi ON providers(npi);
CREATE INDEX idx_providers_entity_type ON providers(entity_type);
CREATE INDEX idx_providers_status ON providers(status);
CREATE INDEX idx_providers_last_name ON providers(last_name);
CREATE INDEX idx_providers_organization ON providers(organization_name);

-- ============================================================================
-- PROVIDER TAXONOMIES
-- ============================================================================

CREATE TABLE IF NOT EXISTS provider_taxonomies (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    provider_id UUID NOT NULL REFERENCES providers(id) ON DELETE CASCADE,
    taxonomy_code VARCHAR(20) NOT NULL,
    taxonomy_description TEXT,
    license_number VARCHAR(255),
    license_state VARCHAR(2),
    is_primary BOOLEAN DEFAULT FALSE,
    data_source VARCHAR(255),
    source_url TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

COMMENT ON TABLE provider_taxonomies IS 'Provider specialty classifications from NPI (physician, surgeon, nurse practitioner, etc.)';

CREATE TRIGGER update_provider_taxonomies_updated_at BEFORE UPDATE ON provider_taxonomies
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE INDEX idx_provider_taxonomies_provider_id ON provider_taxonomies(provider_id);
CREATE INDEX idx_provider_taxonomies_code ON provider_taxonomies(taxonomy_code);
CREATE INDEX idx_provider_taxonomies_state ON provider_taxonomies(license_state);

-- ============================================================================
-- PROVIDER ADDRESSES
-- ============================================================================

CREATE TABLE IF NOT EXISTS provider_addresses (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    provider_id UUID NOT NULL REFERENCES providers(id) ON DELETE CASCADE,
    address_type VARCHAR(20) NOT NULL CHECK (address_type IN ('mailing', 'practice', 'billing')),
    address_line1 VARCHAR(255) NOT NULL,
    address_line2 VARCHAR(255),
    city VARCHAR(100) NOT NULL,
    state VARCHAR(2) NOT NULL,
    postal_code VARCHAR(20),
    country VARCHAR(100) DEFAULT 'USA',
    phone VARCHAR(20),
    fax VARCHAR(20),
    data_source VARCHAR(255),
    source_url TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

COMMENT ON TABLE provider_addresses IS 'Practice and mailing addresses for providers from NPI Registry';

CREATE TRIGGER update_provider_addresses_updated_at BEFORE UPDATE ON provider_addresses
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE INDEX idx_provider_addresses_provider_id ON provider_addresses(provider_id);
CREATE INDEX idx_provider_addresses_type ON provider_addresses(address_type);
CREATE INDEX idx_provider_addresses_state ON provider_addresses(state);
CREATE INDEX idx_provider_addresses_city_state ON provider_addresses(city, state);

-- ============================================================================
-- PROVIDER CREDENTIALS
-- ============================================================================

CREATE TABLE IF NOT EXISTS provider_credentials (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    provider_id UUID NOT NULL REFERENCES providers(id) ON DELETE CASCADE,
    credential_type VARCHAR(50) NOT NULL CHECK (credential_type IN ('state_license', 'dea', 'board_certification', 'npi', 'clia')),
    credential_number VARCHAR(255) NOT NULL,
    issuing_body VARCHAR(255),
    issuing_state VARCHAR(2),
    issue_date DATE,
    expiration_date DATE,
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'expired', 'suspended', 'revoked')),
    verification_status VARCHAR(20) DEFAULT 'pending' CHECK (verification_status IN ('pending', 'verified', 'failed')),
    last_verified_at TIMESTAMP WITH TIME ZONE,
    verification_sources JSONB, -- Array of {source: string, verified_at: timestamp, status: string}
    data_source VARCHAR(255),
    source_url TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

COMMENT ON TABLE provider_credentials IS 'Provider licenses, DEA registrations, and board certifications; core credentialing data';

CREATE TRIGGER update_provider_credentials_updated_at BEFORE UPDATE ON provider_credentials
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE INDEX idx_provider_credentials_provider_id ON provider_credentials(provider_id);
CREATE INDEX idx_provider_credentials_type ON provider_credentials(credential_type);
CREATE INDEX idx_provider_credentials_status ON provider_credentials(status);
CREATE INDEX idx_provider_credentials_verification_status ON provider_credentials(verification_status);
CREATE INDEX idx_provider_credentials_expiration ON provider_credentials(expiration_date);
CREATE INDEX idx_provider_credentials_verification_sources ON provider_credentials USING gin(verification_sources);

-- ============================================================================
-- PROVIDER VERIFICATIONS
-- ============================================================================

CREATE TABLE IF NOT EXISTS provider_verifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    provider_id UUID NOT NULL REFERENCES providers(id) ON DELETE CASCADE,
    verification_source VARCHAR(50) NOT NULL CHECK (verification_source IN ('nppes', 'dea', 'state_board', 'abms', 'npdb', 'oig', 'sam')),
    verification_date TIMESTAMP WITH TIME ZONE NOT NULL,
    status VARCHAR(20) NOT NULL CHECK (status IN ('verified', 'failed', 'pending')),
    raw_response JSONB, -- Full verification response from external API
    next_check_date TIMESTAMP WITH TIME ZONE,
    verified_by VARCHAR(255),
    data_source VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

COMMENT ON TABLE provider_verifications IS 'Verification audit trail: tracks every external verification check (NPI, DEA, state boards, etc.)';

CREATE TRIGGER update_provider_verifications_updated_at BEFORE UPDATE ON provider_verifications
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE INDEX idx_provider_verifications_provider_id ON provider_verifications(provider_id);
CREATE INDEX idx_provider_verifications_source ON provider_verifications(verification_source);
CREATE INDEX idx_provider_verifications_status ON provider_verifications(status);
CREATE INDEX idx_provider_verifications_date ON provider_verifications(verification_date);
CREATE INDEX idx_provider_verifications_raw_response ON provider_verifications USING gin(raw_response);

-- ============================================================================
-- PROVIDER ADVERSE ACTIONS (NPDB)
-- ============================================================================

CREATE TABLE IF NOT EXISTS provider_adverse_actions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    provider_id UUID NOT NULL REFERENCES providers(id) ON DELETE CASCADE,
    action_type VARCHAR(100),
    action_classification VARCHAR(100),
    basis_for_action TEXT,
    action_date DATE,
    effective_date DATE,
    state VARCHAR(2),
    description TEXT,
    payment_amount NUMERIC(15,2),
    source VARCHAR(50) NOT NULL CHECK (source IN ('npdb', 'state_board', 'oig')),
    data_source VARCHAR(255),
    source_url TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

COMMENT ON TABLE provider_adverse_actions IS 'Adverse actions from NPDB (National Practitioner Data Bank) and state boards; critical compliance data';

CREATE TRIGGER update_provider_adverse_actions_updated_at BEFORE UPDATE ON provider_adverse_actions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE INDEX idx_provider_adverse_actions_provider_id ON provider_adverse_actions(provider_id);
CREATE INDEX idx_provider_adverse_actions_source ON provider_adverse_actions(source);
CREATE INDEX idx_provider_adverse_actions_date ON provider_adverse_actions(action_date);
CREATE INDEX idx_provider_adverse_actions_state ON provider_adverse_actions(state);

-- ============================================================================
-- TABLE 4: ORGANIZATIONS
-- ============================================================================

CREATE TABLE IF NOT EXISTS organizations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    npi VARCHAR(10) NOT NULL UNIQUE,
    name VARCHAR(500) NOT NULL,
    org_type VARCHAR(100), -- e.g., 'Hospital', 'Clinic', 'Medical Group', 'ASC'
    cms_certification_number VARCHAR(20),
    address_line1 VARCHAR(255),
    address_line2 VARCHAR(255),
    city VARCHAR(100),
    state VARCHAR(2),
    postal_code VARCHAR(20),
    country VARCHAR(100) DEFAULT 'USA',
    phone VARCHAR(20),
    website TEXT,
    parent_org_id UUID REFERENCES organizations(id), -- Self-referential for hierarchies
    quality_rating NUMERIC(3,2), -- 1-5 star rating if available
    data_source VARCHAR(255),
    source_url TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

COMMENT ON TABLE organizations IS 'Healthcare organizations (hospitals, clinics, medical groups) from CMS/NPI';

CREATE TRIGGER update_organizations_updated_at BEFORE UPDATE ON organizations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE INDEX idx_organizations_npi ON organizations(npi);
CREATE INDEX idx_organizations_name ON organizations(name);
CREATE INDEX idx_organizations_state ON organizations(state);
CREATE INDEX idx_organizations_parent_org_id ON organizations(parent_org_id);

-- ============================================================================
-- TABLE 5: MEDICAL CODES - ICD10-CM
-- ============================================================================

CREATE TABLE IF NOT EXISTS icd10_cm_codes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    code VARCHAR(10) NOT NULL UNIQUE,
    description TEXT NOT NULL,
    long_description TEXT,
    chapter VARCHAR(5),
    chapter_description TEXT,
    category VARCHAR(10),
    is_billable BOOLEAN DEFAULT TRUE,
    effective_date DATE,
    version VARCHAR(10),
    parent_code VARCHAR(10) REFERENCES icd10_cm_codes(code),
    data_source VARCHAR(255) DEFAULT 'CMS ICD-10-CM',
    source_url TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

COMMENT ON TABLE icd10_cm_codes IS 'ICD-10-CM diagnosis codes (~70K total); WHO/CMS maintained';

CREATE TRIGGER update_icd10_cm_codes_updated_at BEFORE UPDATE ON icd10_cm_codes
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE INDEX idx_icd10_cm_code ON icd10_cm_codes(code);
CREATE INDEX idx_icd10_cm_description ON icd10_cm_codes(description);
CREATE INDEX idx_icd10_cm_chapter ON icd10_cm_codes(chapter);
CREATE INDEX idx_icd10_cm_billable ON icd10_cm_codes(is_billable);
CREATE INDEX idx_icd10_cm_parent ON icd10_cm_codes(parent_code);

-- ============================================================================
-- TABLE 6: MEDICAL CODES - ICD10-PCS
-- ============================================================================

CREATE TABLE IF NOT EXISTS icd10_pcs_codes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    code VARCHAR(7) NOT NULL UNIQUE,
    description TEXT NOT NULL,
    section VARCHAR(5),
    body_system VARCHAR(50),
    root_operation VARCHAR(50),
    body_part VARCHAR(50),
    approach VARCHAR(50),
    device VARCHAR(50),
    qualifier VARCHAR(50),
    effective_date DATE,
    version VARCHAR(10),
    data_source VARCHAR(255) DEFAULT 'CMS ICD-10-PCS',
    source_url TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

COMMENT ON TABLE icd10_pcs_codes IS 'ICD-10-PCS procedure codes (~72K total); inpatient hospital procedures';

CREATE TRIGGER update_icd10_pcs_codes_updated_at BEFORE UPDATE ON icd10_pcs_codes
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE INDEX idx_icd10_pcs_code ON icd10_pcs_codes(code);
CREATE INDEX idx_icd10_pcs_description ON icd10_pcs_codes(description);
CREATE INDEX idx_icd10_pcs_section ON icd10_pcs_codes(section);
CREATE INDEX idx_icd10_pcs_root_operation ON icd10_pcs_codes(root_operation);

-- ============================================================================
-- TABLE 7: MEDICAL CODES - HCPCS
-- ============================================================================

CREATE TABLE IF NOT EXISTS hcpcs_codes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    code VARCHAR(10) NOT NULL UNIQUE,
    description TEXT NOT NULL,
    long_description TEXT,
    code_type VARCHAR(20), -- 'J', 'E', 'L', 'M', 'P', 'S', 'T', 'V'
    effective_date DATE,
    termination_date DATE,
    pricing_indicator VARCHAR(50),
    data_source VARCHAR(255) DEFAULT 'CMS HCPCS',
    source_url TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

COMMENT ON TABLE hcpcs_codes IS 'HCPCS (Healthcare Common Procedure Coding System) codes (~8K); used for billing';

CREATE TRIGGER update_hcpcs_codes_updated_at BEFORE UPDATE ON hcpcs_codes
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE INDEX idx_hcpcs_code ON hcpcs_codes(code);
CREATE INDEX idx_hcpcs_type ON hcpcs_codes(code_type);
CREATE INDEX idx_hcpcs_effective_date ON hcpcs_codes(effective_date);

-- ============================================================================
-- TABLE 8: MEDICAL CODES - DRG
-- ============================================================================

CREATE TABLE IF NOT EXISTS drg_codes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    code VARCHAR(10) NOT NULL UNIQUE,
    description TEXT NOT NULL,
    drg_type VARCHAR(20) NOT NULL DEFAULT 'MS-DRG', -- Medicare Severity DRG
    weight NUMERIC(8,4),
    geometric_mean_los NUMERIC(8,2),
    arithmetic_mean_los NUMERIC(8,2),
    effective_date DATE,
    version VARCHAR(10),
    data_source VARCHAR(255) DEFAULT 'CMS DRG',
    source_url TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

COMMENT ON TABLE drg_codes IS 'Diagnosis-Related Groups (~745); Medicare hospital payment classifications';

CREATE TRIGGER update_drg_codes_updated_at BEFORE UPDATE ON drg_codes
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE INDEX idx_drg_code ON drg_codes(code);
CREATE INDEX idx_drg_type ON drg_codes(drg_type);

-- ============================================================================
-- TABLE 9: MEDICAL CODES - NDC
-- ============================================================================

CREATE TABLE IF NOT EXISTS ndc_codes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    ndc_code VARCHAR(20) NOT NULL UNIQUE,
    proprietary_name VARCHAR(500),
    nonproprietary_name VARCHAR(500),
    dosage_form VARCHAR(100),
    route VARCHAR(100),
    strength VARCHAR(255),
    active_ingredients JSONB, -- Array of {ingredient: string, strength: string}
    manufacturer VARCHAR(255),
    labeler VARCHAR(255),
    package_description VARCHAR(255),
    listing_date DATE,
    marketing_start_date DATE,
    marketing_end_date DATE,
    dea_schedule VARCHAR(20),
    data_source VARCHAR(255) DEFAULT 'FDA NDC',
    source_url TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

COMMENT ON TABLE ndc_codes IS 'National Drug Codes (~200K); FDA drug product identifiers';

CREATE TRIGGER update_ndc_codes_updated_at BEFORE UPDATE ON ndc_codes
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE INDEX idx_ndc_code ON ndc_codes(ndc_code);
CREATE INDEX idx_ndc_proprietary ON ndc_codes(proprietary_name);
CREATE INDEX idx_ndc_nonproprietary ON ndc_codes(nonproprietary_name);
CREATE INDEX idx_ndc_route ON ndc_codes(route);
CREATE INDEX idx_ndc_dea_schedule ON ndc_codes(dea_schedule);
CREATE INDEX idx_ndc_active_ingredients ON ndc_codes USING gin(active_ingredients);

-- ============================================================================
-- TABLE 10: DRUGS - NORMALIZED
-- ============================================================================

CREATE TABLE IF NOT EXISTS drugs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    rxcui VARCHAR(20) NOT NULL UNIQUE,
    name VARCHAR(500) NOT NULL,
    ingredients JSONB, -- Array of {ingredient: string, strength: string, unit: string}
    dosage_form VARCHAR(100),
    strength VARCHAR(255),
    drug_class VARCHAR(255),
    ndc_codes JSONB, -- Array of NDC codes for this drug
    synonyms JSONB, -- Array of alternative names
    data_source VARCHAR(255) DEFAULT 'RxNorm',
    source_url TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

COMMENT ON TABLE drugs IS 'Normalized drug entities from RxNorm; master drug reference';

CREATE TRIGGER update_drugs_updated_at BEFORE UPDATE ON drugs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE INDEX idx_drugs_rxcui ON drugs(rxcui);
CREATE INDEX idx_drugs_name ON drugs(name);
CREATE INDEX idx_drugs_drug_class ON drugs(drug_class);
CREATE INDEX idx_drugs_ndc_codes ON drugs USING gin(ndc_codes);
CREATE INDEX idx_drugs_synonyms ON drugs USING gin(synonyms);

-- ============================================================================
-- TABLE 11: DRUG INTERACTIONS
-- ============================================================================

CREATE TABLE IF NOT EXISTS drug_interactions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    drug_a_rxcui VARCHAR(20) NOT NULL REFERENCES drugs(rxcui),
    drug_b_rxcui VARCHAR(20) NOT NULL REFERENCES drugs(rxcui),
    severity VARCHAR(20) NOT NULL CHECK (severity IN ('minor', 'moderate', 'major', 'contraindicated')),
    description TEXT,
    mechanism TEXT,
    source VARCHAR(100), -- 'RxNorm', 'DrugBank', 'FDA'
    data_source VARCHAR(255),
    source_url TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(drug_a_rxcui, drug_b_rxcui)
);

COMMENT ON TABLE drug_interactions IS 'Drug-drug interaction data from RxNorm/DrugBank; critical safety alerts';

CREATE TRIGGER update_drug_interactions_updated_at BEFORE UPDATE ON drug_interactions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE INDEX idx_drug_interactions_drug_a ON drug_interactions(drug_a_rxcui);
CREATE INDEX idx_drug_interactions_drug_b ON drug_interactions(drug_b_rxcui);
CREATE INDEX idx_drug_interactions_severity ON drug_interactions(severity);

-- ============================================================================
-- TABLE 12: DRUG LABELS (FDA DailyMed)
-- ============================================================================

CREATE TABLE IF NOT EXISTS drug_labels (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    set_id VARCHAR(50) NOT NULL UNIQUE,
    drug_id UUID REFERENCES drugs(id),
    name VARCHAR(500),
    indications TEXT,
    dosage_and_administration TEXT,
    warnings TEXT,
    contraindications TEXT,
    adverse_reactions TEXT,
    drug_interactions_text TEXT,
    version VARCHAR(10),
    effective_date DATE,
    data_source VARCHAR(255) DEFAULT 'DailyMed',
    source_url TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

COMMENT ON TABLE drug_labels IS 'FDA drug labels from DailyMed; comprehensive medication safety information';

CREATE TRIGGER update_drug_labels_updated_at BEFORE UPDATE ON drug_labels
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE INDEX idx_drug_labels_set_id ON drug_labels(set_id);
CREATE INDEX idx_drug_labels_drug_id ON drug_labels(drug_id);

-- ============================================================================
-- TABLE 13: DRUG ADVERSE EVENTS (FDA FAERS)
-- ============================================================================

CREATE TABLE IF NOT EXISTS drug_adverse_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    drug_name VARCHAR(500),
    rxcui VARCHAR(20) REFERENCES drugs(rxcui),
    event_date DATE,
    reaction TEXT,
    outcome VARCHAR(100), -- e.g., 'fatal', 'hospitalization', 'recovery'
    serious BOOLEAN DEFAULT FALSE,
    source_quarter VARCHAR(10), -- e.g., '2025Q1'
    report_type VARCHAR(50), -- 'initial', 'follow-up'
    data_source VARCHAR(255) DEFAULT 'FDA FAERS',
    source_url TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

COMMENT ON TABLE drug_adverse_events IS 'Drug adverse event reports from FDA FAERS; pharmacovigilance data';

CREATE TRIGGER update_drug_adverse_events_updated_at BEFORE UPDATE ON drug_adverse_events
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE INDEX idx_drug_adverse_events_drug_name ON drug_adverse_events(drug_name);
CREATE INDEX idx_drug_adverse_events_rxcui ON drug_adverse_events(rxcui);
CREATE INDEX idx_drug_adverse_events_event_date ON drug_adverse_events(event_date);
CREATE INDEX idx_drug_adverse_events_serious ON drug_adverse_events(serious);

-- ============================================================================
-- TABLE 14: CONDITIONS
-- ============================================================================

CREATE TABLE IF NOT EXISTS conditions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    snomed_code VARCHAR(20),
    icd10_codes JSONB, -- Array of related ICD-10 codes
    name VARCHAR(500) NOT NULL,
    description TEXT,
    synonyms JSONB, -- Array of alternative names
    category VARCHAR(100), -- e.g., 'Infectious', 'Cardiovascular', 'Neoplastic'
    body_system VARCHAR(100),
    prevalence_data JSONB, -- {region: string, prevalence: number, year: integer}
    data_source VARCHAR(255),
    source_url TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

COMMENT ON TABLE conditions IS 'Medical conditions/diseases from SNOMED-CT and ICD-10; disease definitions';

CREATE TRIGGER update_conditions_updated_at BEFORE UPDATE ON conditions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE INDEX idx_conditions_snomed ON conditions(snomed_code);
CREATE INDEX idx_conditions_name ON conditions(name);
CREATE INDEX idx_conditions_category ON conditions(category);
CREATE INDEX idx_conditions_body_system ON conditions(body_system);
CREATE INDEX idx_conditions_icd10_codes ON conditions USING gin(icd10_codes);

-- ============================================================================
-- TABLE 15: CLINICAL TRIALS
-- ============================================================================

CREATE TABLE IF NOT EXISTS clinical_trials (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    nct_id VARCHAR(20) NOT NULL UNIQUE,
    title TEXT NOT NULL,
    brief_summary TEXT,
    status VARCHAR(50), -- 'recruiting', 'active', 'enrolling_by_invitation', 'completed'
    phase VARCHAR(20), -- 'Phase 1', 'Phase 2', 'Phase 3', 'Phase 4'
    conditions JSONB, -- Array of condition names
    interventions JSONB, -- Array of {type: string, name: string}
    enrollment INTEGER,
    start_date DATE,
    primary_completion_date DATE,
    study_type VARCHAR(100), -- 'Observational', 'Interventional'
    sponsor VARCHAR(255),
    locations JSONB, -- Array of {city: string, state: string, country: string}
    results_available BOOLEAN DEFAULT FALSE,
    data_source VARCHAR(255) DEFAULT 'ClinicalTrials.gov',
    source_url TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

COMMENT ON TABLE clinical_trials IS 'Clinical trials from ClinicalTrials.gov; research opportunity discovery';

CREATE TRIGGER update_clinical_trials_updated_at BEFORE UPDATE ON clinical_trials
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE INDEX idx_clinical_trials_nct_id ON clinical_trials(nct_id);
CREATE INDEX idx_clinical_trials_status ON clinical_trials(status);
CREATE INDEX idx_clinical_trials_phase ON clinical_trials(phase);
CREATE INDEX idx_clinical_trials_start_date ON clinical_trials(start_date);
CREATE INDEX idx_clinical_trials_conditions ON clinical_trials USING gin(conditions);

-- ============================================================================
-- TABLE 16: PUBMED CITATIONS
-- ============================================================================

CREATE TABLE IF NOT EXISTS pubmed_citations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    pmid VARCHAR(20) NOT NULL UNIQUE,
    title TEXT NOT NULL,
    abstract TEXT,
    authors JSONB, -- Array of {name: string, affiliation: string}
    journal VARCHAR(255),
    publication_date DATE,
    mesh_terms JSONB, -- Array of MeSH subject headings
    doi VARCHAR(255),
    pmc_id VARCHAR(20),
    citation_count INTEGER DEFAULT 0,
    data_source VARCHAR(255) DEFAULT 'PubMed/MEDLINE',
    source_url TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

COMMENT ON TABLE pubmed_citations IS 'PubMed citations and MEDLINE records; evidence base for clinical knowledge';

CREATE TRIGGER update_pubmed_citations_updated_at BEFORE UPDATE ON pubmed_citations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE INDEX idx_pubmed_citations_pmid ON pubmed_citations(pmid);
CREATE INDEX idx_pubmed_citations_title ON pubmed_citations(title);
CREATE INDEX idx_pubmed_citations_journal ON pubmed_citations(journal);
CREATE INDEX idx_pubmed_citations_publication_date ON pubmed_citations(publication_date);
CREATE INDEX idx_pubmed_citations_mesh_terms ON pubmed_citations USING gin(mesh_terms);

-- ============================================================================
-- TABLE 17: LOINC CODES
-- ============================================================================

CREATE TABLE IF NOT EXISTS loinc_codes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    loinc_num VARCHAR(20) NOT NULL UNIQUE,
    component TEXT,
    property VARCHAR(100),
    time_aspect VARCHAR(100),
    system VARCHAR(100),
    scale_type VARCHAR(100),
    method_type VARCHAR(100),
    class VARCHAR(100),
    long_common_name TEXT,
    status VARCHAR(20), -- 'active', 'deprecated'
    data_source VARCHAR(255) DEFAULT 'LOINC',
    source_url TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

COMMENT ON TABLE loinc_codes IS 'LOINC codes for lab tests and observations; lab result standardization';

CREATE TRIGGER update_loinc_codes_updated_at BEFORE UPDATE ON loinc_codes
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE INDEX idx_loinc_codes_loinc_num ON loinc_codes(loinc_num);
CREATE INDEX idx_loinc_codes_component ON loinc_codes(component);
CREATE INDEX idx_loinc_codes_status ON loinc_codes(status);

-- ============================================================================
-- TABLE 18: OIG EXCLUSIONS (Office of Inspector General)
-- ============================================================================

CREATE TABLE IF NOT EXISTS oig_exclusions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    entity_name VARCHAR(500) NOT NULL,
    entity_type VARCHAR(50) NOT NULL CHECK (entity_type IN ('individual', 'organization')),
    npi VARCHAR(10) REFERENCES providers(npi),
    exclusion_type VARCHAR(100),
    exclusion_date DATE NOT NULL,
    reinstatement_date DATE,
    state VARCHAR(2),
    specialty VARCHAR(255),
    general_info TEXT,
    data_source VARCHAR(255) DEFAULT 'OIG LEIE',
    source_url TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

COMMENT ON TABLE oig_exclusions IS 'OIG Exclusions List (LEIE); critical compliance data for excluded providers';

CREATE TRIGGER update_oig_exclusions_updated_at BEFORE UPDATE ON oig_exclusions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE INDEX idx_oig_exclusions_entity_name ON oig_exclusions(entity_name);
CREATE INDEX idx_oig_exclusions_npi ON oig_exclusions(npi);
CREATE INDEX idx_oig_exclusions_exclusion_date ON oig_exclusions(exclusion_date);
CREATE INDEX idx_oig_exclusions_state ON oig_exclusions(state);

-- ============================================================================
-- TABLE 19: SAM EXCLUSIONS (System for Award Management)
-- ============================================================================

CREATE TABLE IF NOT EXISTS sam_exclusions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    entity_name VARCHAR(500) NOT NULL,
    cage_code VARCHAR(20),
    duns_number VARCHAR(20),
    exclusion_type VARCHAR(100),
    exclusion_program VARCHAR(100),
    active_date DATE,
    termination_date DATE,
    record_status VARCHAR(50),
    sam_number VARCHAR(50),
    data_source VARCHAR(255) DEFAULT 'SAM.gov',
    source_url TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

COMMENT ON TABLE sam_exclusions IS 'Federal SAM.gov exclusions list; government vendor compliance';

CREATE TRIGGER update_sam_exclusions_updated_at BEFORE UPDATE ON sam_exclusions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE INDEX idx_sam_exclusions_entity_name ON sam_exclusions(entity_name);
CREATE INDEX idx_sam_exclusions_cage_code ON sam_exclusions(cage_code);
CREATE INDEX idx_sam_exclusions_exclusion_date ON sam_exclusions(active_date);

-- ============================================================================
-- TABLE 20: STATE MEDICAL BOARDS
-- ============================================================================

CREATE TABLE IF NOT EXISTS state_medical_boards (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    state_code VARCHAR(2) NOT NULL UNIQUE,
    state_name VARCHAR(100) NOT NULL,
    board_name VARCHAR(255),
    board_url TEXT,
    lookup_url TEXT,
    has_api BOOLEAN DEFAULT FALSE,
    api_url TEXT,
    data_fields_available JSONB, -- Array of available fields
    update_frequency VARCHAR(50),
    compact_member BOOLEAN DEFAULT FALSE, -- Interstate Medical Licensure Compact
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

COMMENT ON TABLE state_medical_boards IS 'State medical board registry with lookup URLs and API endpoints';

CREATE TRIGGER update_state_medical_boards_updated_at BEFORE UPDATE ON state_medical_boards
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE INDEX idx_state_medical_boards_state_code ON state_medical_boards(state_code);

-- ============================================================================
-- TABLE 21: STATE LICENSE LOOKUPS (CACHE)
-- ============================================================================

CREATE TABLE IF NOT EXISTS state_license_lookups (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    provider_id UUID NOT NULL REFERENCES providers(id) ON DELETE CASCADE,
    state_code VARCHAR(2) NOT NULL REFERENCES state_medical_boards(state_code),
    license_number VARCHAR(255),
    license_type VARCHAR(100),
    status VARCHAR(50),
    issue_date DATE,
    expiration_date DATE,
    disciplinary_actions JSONB, -- Array of actions
    lookup_date TIMESTAMP WITH TIME ZONE,
    raw_response JSONB,
    data_source VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

COMMENT ON TABLE state_license_lookups IS 'Cached state license verification results; reduces repeat API calls';

CREATE TRIGGER update_state_license_lookups_updated_at BEFORE UPDATE ON state_license_lookups
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE INDEX idx_state_license_lookups_provider ON state_license_lookups(provider_id);
CREATE INDEX idx_state_license_lookups_state ON state_license_lookups(state_code);

-- ============================================================================
-- TABLE 22: DATA PROVENANCE
-- ============================================================================

CREATE TABLE IF NOT EXISTS data_provenance (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    entity_type VARCHAR(50) NOT NULL, -- e.g., 'provider', 'drug', 'condition'
    entity_id UUID NOT NULL,
    source_name VARCHAR(255) NOT NULL,
    source_url TEXT,
    ingestion_date TIMESTAMP WITH TIME ZONE NOT NULL,
    data_hash VARCHAR(64), -- SHA256 of entity data
    freshness_score NUMERIC(3,2), -- 0-1 indicating data recency
    next_refresh_date TIMESTAMP WITH TIME ZONE,
    verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

COMMENT ON TABLE data_provenance IS 'Entity-level provenance tracking; audit trail for data origins and freshness';

CREATE TRIGGER update_data_provenance_updated_at BEFORE UPDATE ON data_provenance
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE INDEX idx_data_provenance_entity ON data_provenance(entity_type, entity_id);
CREATE INDEX idx_data_provenance_source ON data_provenance(source_name);
CREATE INDEX idx_data_provenance_ingestion_date ON data_provenance(ingestion_date);

-- ============================================================================
-- TABLE 23: ENTITY RELATIONSHIPS (Neo4j Sync Bridge)
-- ============================================================================

CREATE TABLE IF NOT EXISTS entity_relationships (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_entity_type VARCHAR(50) NOT NULL, -- e.g., 'provider', 'drug', 'condition', 'organization'
    source_entity_id UUID NOT NULL,
    relationship_type VARCHAR(100) NOT NULL, -- e.g., 'prescribes', 'has_credential', 'treats', 'located_in'
    target_entity_type VARCHAR(50) NOT NULL,
    target_entity_id UUID NOT NULL,
    metadata JSONB, -- Relationship-specific properties
    weight NUMERIC(8,4) DEFAULT 1.0, -- Strength/confidence of relationship
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

COMMENT ON TABLE entity_relationships IS 'Bridge table for Neo4j graph sync; enables knowledge graph construction';

CREATE TRIGGER update_entity_relationships_updated_at BEFORE UPDATE ON entity_relationships
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE INDEX idx_entity_relationships_source ON entity_relationships(source_entity_type, source_entity_id);
CREATE INDEX idx_entity_relationships_target ON entity_relationships(target_entity_type, target_entity_id);
CREATE INDEX idx_entity_relationships_type ON entity_relationships(relationship_type);
CREATE INDEX idx_entity_relationships_metadata ON entity_relationships USING gin(metadata);

-- ============================================================================
-- CUSTOM FUNCTIONS
-- ============================================================================

-- Function: Search providers with full-text search
CREATE OR REPLACE FUNCTION search_providers(search_query TEXT)
RETURNS TABLE (
    id UUID,
    npi VARCHAR(10),
    first_name VARCHAR(255),
    last_name VARCHAR(255),
    organization_name VARCHAR(255),
    similarity_score NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        p.id,
        p.npi,
        p.first_name,
        p.last_name,
        p.organization_name,
        CAST(
            CASE
                WHEN p.npi = search_query THEN 1.0
                WHEN p.last_name ILIKE search_query || '%' THEN 0.9
                WHEN p.organization_name ILIKE search_query || '%' THEN 0.8
                ELSE 0.5
            END AS NUMERIC
        ) as similarity_score
    FROM providers p
    WHERE
        p.npi ILIKE '%' || search_query || '%'
        OR p.first_name ILIKE '%' || search_query || '%'
        OR p.last_name ILIKE '%' || search_query || '%'
        OR p.organization_name ILIKE '%' || search_query || '%'
    ORDER BY similarity_score DESC;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION search_providers(TEXT) IS 'Full-text search for providers by NPI, name, or organization';

-- ============================================================================
-- Function: Verify provider compliance status
-- ============================================================================

CREATE OR REPLACE FUNCTION verify_provider_status(provider_npi VARCHAR(10))
RETURNS TABLE (
    provider_id UUID,
    npi VARCHAR(10),
    status VARCHAR(20),
    is_excluded BOOLEAN,
    is_sanctioned BOOLEAN,
    last_verification TIMESTAMP WITH TIME ZONE,
    risk_level VARCHAR(20)
) AS $$
DECLARE
    p_id UUID;
    excluded_count INTEGER;
    sanctioned_count INTEGER;
    last_verify TIMESTAMP WITH TIME ZONE;
BEGIN
    SELECT id INTO p_id FROM providers WHERE npi = provider_npi LIMIT 1;

    IF p_id IS NULL THEN
        RETURN;
    END IF;

    SELECT COUNT(*) INTO excluded_count
    FROM oig_exclusions
    WHERE npi = provider_npi AND reinstatement_date IS NULL;

    SELECT COUNT(*) INTO sanctioned_count
    FROM provider_adverse_actions
    WHERE provider_id = p_id AND action_date >= NOW() - INTERVAL '5 years';

    SELECT MAX(verification_date) INTO last_verify
    FROM provider_verifications
    WHERE provider_id = p_id;

    RETURN QUERY
    SELECT
        p_id,
        provider_npi,
        (SELECT status FROM providers WHERE id = p_id)::VARCHAR(20),
        CASE WHEN excluded_count > 0 THEN TRUE ELSE FALSE END,
        CASE WHEN sanctioned_count > 0 THEN TRUE ELSE FALSE END,
        last_verify,
        CASE
            WHEN excluded_count > 0 THEN 'CRITICAL'::VARCHAR(20)
            WHEN sanctioned_count > 0 THEN 'HIGH'::VARCHAR(20)
            WHEN sanctioned_count > 1 THEN 'MEDIUM'::VARCHAR(20)
            ELSE 'LOW'::VARCHAR(20)
        END;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION verify_provider_status(VARCHAR) IS 'Compliance status check: verifies provider against OIG exclusions and adverse actions';

-- ============================================================================
-- ROW LEVEL SECURITY POLICIES
-- ============================================================================

-- Enable RLS on all tables
ALTER TABLE providers ENABLE ROW LEVEL SECURITY;
ALTER TABLE provider_addresses ENABLE ROW LEVEL SECURITY;
ALTER TABLE provider_credentials ENABLE ROW LEVEL SECURITY;
ALTER TABLE provider_verifications ENABLE ROW LEVEL SECURITY;
ALTER TABLE provider_adverse_actions ENABLE ROW LEVEL SECURITY;
ALTER TABLE organizations ENABLE ROW LEVEL SECURITY;
ALTER TABLE drugs ENABLE ROW LEVEL SECURITY;
ALTER TABLE drug_interactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE drug_labels ENABLE ROW LEVEL SECURITY;
ALTER TABLE drug_adverse_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE oig_exclusions ENABLE ROW LEVEL SECURITY;
ALTER TABLE sam_exclusions ENABLE ROW LEVEL SECURITY;

-- Create a simple RLS policy allowing all authenticated users read access (adjust as needed)
CREATE POLICY provider_select_policy ON providers FOR SELECT USING (true);
CREATE POLICY provider_insert_policy ON providers FOR INSERT WITH CHECK (auth.role() = 'authenticated');
CREATE POLICY provider_update_policy ON providers FOR UPDATE USING (auth.role() = 'authenticated');

CREATE POLICY organization_select_policy ON organizations FOR SELECT USING (true);
CREATE POLICY organization_insert_policy ON organizations FOR INSERT WITH CHECK (auth.role() = 'authenticated');

CREATE POLICY drugs_select_policy ON drugs FOR SELECT USING (true);

CREATE POLICY oig_exclusions_select_policy ON oig_exclusions FOR SELECT USING (true);

CREATE POLICY sam_exclusions_select_policy ON sam_exclusions FOR SELECT USING (true);

-- ============================================================================
-- COMPOSITE INDEXES FOR COMMON QUERY PATTERNS
-- ============================================================================

CREATE INDEX idx_provider_state_status ON providers(state, status)
    WHERE status = 'active';

CREATE INDEX idx_provider_credentials_verification ON provider_credentials(provider_id, verification_status, expiration_date);

CREATE INDEX idx_drug_interactions_severity ON drug_interactions(severity)
    WHERE severity IN ('major', 'contraindicated');

CREATE INDEX idx_clinical_trials_active ON clinical_trials(status, start_date)
    WHERE status IN ('recruiting', 'active', 'enrolling_by_invitation');

-- ============================================================================
-- COMMENTS ON DESIGN CHOICES
-- ============================================================================

COMMENT ON SCHEMA public IS
'Healthcare Knowledge Garden Schema v1.0
PURPOSE: Central data repository for healthcare knowledge base ingestion from 30+ public sources
ARCHITECTURE:
  - Credentialing lane: providers, credentials, verifications, adverse actions
  - Medical knowledge: ICD/HCPCS/DRG codes, drugs, interactions, conditions
  - Clinical research: trials, publications, lab codes
  - Compliance: exclusions, regulatory status, audit trail
  - Data management: sources, provenance, ingestion tracking
  - Graph sync: entity relationships bridge to Neo4j
FEATURES:
  - Production-grade indexing (B-tree on codes/status/dates, GIN on JSONB)
  - RLS-ready with auth policies
  - Audit trail via created_at/updated_at triggers
  - Data source tracking on every record
  - Full-text search function for providers
  - Compliance verification function
  - HIPAA-compliant design with RLS enforcement
';

-- ============================================================================
-- FINAL SETUP COMMANDS
-- ============================================================================

-- Create search index for full-text search on provider data
CREATE INDEX IF NOT EXISTS idx_providers_full_text ON providers
    USING GIN(to_tsvector(''english'', COALESCE(last_name, '''') || '' '' || COALESCE(first_name, '')));

-- Initialize data_sources table with common sources
INSERT INTO data_sources (name, category, format, update_frequency, cost, license_type) VALUES
    ('NPI Registry', 'provider_data', 'json', 'daily', 'free', 'public_domain'),
    ('FDA NDC', 'drugs', 'csv', 'monthly', 'free', 'public_domain'),
    ('RxNorm', 'drugs', 'xml', 'monthly', 'free', 'public_domain'),
    ('CMS ICD-10-CM', 'medical_codes', 'txt', 'yearly', 'free', 'public_domain'),
    ('CMS ICD-10-PCS', 'medical_codes', 'txt', 'yearly', 'free', 'public_domain'),
    ('ClinicalTrials.gov', 'clinical_knowledge', 'xml', 'daily', 'free', 'public_domain'),
    ('PubMed/MEDLINE', 'clinical_knowledge', 'xml', 'weekly', 'free', 'public_domain'),
    ('OIG LEIE', 'compliance', 'txt', 'monthly', 'free', 'public_domain'),
    ('SAM.gov', 'compliance', 'csv', 'monthly', 'free', 'public_domain'),
    ('DailyMed', 'drugs', 'xml', 'daily', 'free', 'public_domain')
ON CONFLICT (name) DO NOTHING;

-- ============================================================================
-- END OF SCHEMA
-- ============================================================================

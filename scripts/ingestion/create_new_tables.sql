-- Run this in Supabase SQL Editor to create tables for P0 datasets
-- Then run the corresponding Python scripts to populate them

-- 1. FDA FAERS Adverse Events
CREATE TABLE IF NOT EXISTS drug_adverse_events (
    id BIGSERIAL PRIMARY KEY,
    safety_report_id TEXT,
    report_date TEXT,
    patient_age TEXT,
    patient_sex TEXT,
    drug_name TEXT,
    drug_indication TEXT,
    reaction TEXT,
    outcome TEXT,
    serious BOOLEAN,
    source_country TEXT,
    data_source TEXT DEFAULT 'FDA FAERS',
    created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_dae_drug ON drug_adverse_events(drug_name);
CREATE INDEX IF NOT EXISTS idx_dae_reaction ON drug_adverse_events(reaction);
CREATE INDEX IF NOT EXISTS idx_dae_serious ON drug_adverse_events(serious);

-- 2. CMS Hospital Quality (Hospital Compare)
CREATE TABLE IF NOT EXISTS hospitals (
    id BIGSERIAL PRIMARY KEY,
    facility_id TEXT UNIQUE,
    facility_name TEXT,
    address TEXT,
    city TEXT,
    state TEXT,
    zip_code TEXT,
    county TEXT,
    phone TEXT,
    hospital_type TEXT,
    hospital_ownership TEXT,
    emergency_services BOOLEAN,
    overall_rating TEXT,
    mortality_rating TEXT,
    safety_rating TEXT,
    readmission_rating TEXT,
    patient_experience_rating TEXT,
    effectiveness_rating TEXT,
    timeliness_rating TEXT,
    efficient_use_of_imaging TEXT,
    data_source TEXT DEFAULT 'CMS Hospital Compare',
    created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_hosp_state ON hospitals(state);
CREATE INDEX IF NOT EXISTS idx_hosp_rating ON hospitals(overall_rating);
CREATE INDEX IF NOT EXISTS idx_hosp_facility ON hospitals(facility_id);

-- 3. Medicare Provider Utilization & Payment
CREATE TABLE IF NOT EXISTS medicare_utilization (
    id BIGSERIAL PRIMARY KEY,
    npi TEXT,
    provider_last_name TEXT,
    provider_first_name TEXT,
    provider_type TEXT,
    provider_state TEXT,
    hcpcs_code TEXT,
    hcpcs_description TEXT,
    service_count INTEGER,
    beneficiary_count INTEGER,
    avg_submitted_charge NUMERIC(12,2),
    avg_medicare_allowed NUMERIC(12,2),
    avg_medicare_payment NUMERIC(12,2),
    year TEXT,
    data_source TEXT DEFAULT 'CMS Medicare Utilization',
    created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_mu_npi ON medicare_utilization(npi);
CREATE INDEX IF NOT EXISTS idx_mu_hcpcs ON medicare_utilization(hcpcs_code);
CREATE INDEX IF NOT EXISTS idx_mu_state ON medicare_utilization(provider_state);

-- Grant access for service role (already has access via RLS bypass)
-- If you want anon access later, add SELECT policies

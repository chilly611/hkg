-- HKG: Create all new tables for P0b data ingestion sprint
-- Run this ENTIRE file in Supabase SQL Editor (one paste, one click)
-- Then the parallel ingestion scripts will populate them

-- 1. Medicare Part D Prescriber Data (Provider→Drug relationships)
CREATE TABLE IF NOT EXISTS medicare_part_d_prescribers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    npi TEXT,
    provider_last_name TEXT,
    provider_first_name TEXT,
    provider_state TEXT,
    specialty_description TEXT,
    drug_name TEXT,
    generic_name TEXT,
    total_claim_count INTEGER,
    total_30_day_fill_count INTEGER,
    total_day_supply INTEGER,
    total_drug_cost NUMERIC(14,2),
    bene_count INTEGER,
    year TEXT,
    data_source TEXT DEFAULT 'CMS Medicare Part D',
    source_url TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_partd_npi ON medicare_part_d_prescribers(npi);
CREATE INDEX IF NOT EXISTS idx_partd_drug ON medicare_part_d_prescribers(drug_name);
CREATE INDEX IF NOT EXISTS idx_partd_generic ON medicare_part_d_prescribers(generic_name);
CREATE INDEX IF NOT EXISTS idx_partd_state ON medicare_part_d_prescribers(provider_state);
CREATE INDEX IF NOT EXISTS idx_partd_year ON medicare_part_d_prescribers(year);
COMMENT ON TABLE medicare_part_d_prescribers IS 'CMS Medicare Part D prescribing data — links providers to drugs they prescribe';

-- 2. NLM MeSH Terms (Medical Subject Headings)
CREATE TABLE IF NOT EXISTS mesh_terms (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    mesh_id TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    tree_numbers TEXT[],
    scope_note TEXT,
    category TEXT,
    qualifier_list TEXT[],
    parent_ids TEXT[],
    data_source TEXT DEFAULT 'NLM MeSH',
    source_url TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_mesh_id ON mesh_terms(mesh_id);
CREATE INDEX IF NOT EXISTS idx_mesh_name ON mesh_terms USING gin(to_tsvector('english', name));
CREATE INDEX IF NOT EXISTS idx_mesh_category ON mesh_terms(category);
CREATE INDEX IF NOT EXISTS idx_mesh_tree ON mesh_terms USING gin(tree_numbers);
COMMENT ON TABLE mesh_terms IS 'NLM MeSH medical subject headings — links PubMed citations to conditions, drugs, procedures';

-- 3. CMS Hospital Quality (Hospital Compare)
CREATE TABLE IF NOT EXISTS hospitals (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
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
    source_url TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_hosp_state ON hospitals(state);
CREATE INDEX IF NOT EXISTS idx_hosp_rating ON hospitals(overall_rating);
CREATE INDEX IF NOT EXISTS idx_hosp_facility ON hospitals(facility_id);
COMMENT ON TABLE hospitals IS 'CMS Hospital Compare — quality ratings for US hospitals';

-- 4. Medicare Provider Utilization & Payment
CREATE TABLE IF NOT EXISTS medicare_utilization (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
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
    source_url TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_mu_npi ON medicare_utilization(npi);
CREATE INDEX IF NOT EXISTS idx_mu_hcpcs ON medicare_utilization(hcpcs_code);
CREATE INDEX IF NOT EXISTS idx_mu_state ON medicare_utilization(provider_state);
COMMENT ON TABLE medicare_utilization IS 'CMS Medicare provider utilization & payment data';

-- Triggers for updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column_safe()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

DO $$ BEGIN
    CREATE TRIGGER update_partd_updated_at BEFORE UPDATE ON medicare_part_d_prescribers FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE TRIGGER update_mesh_updated_at BEFORE UPDATE ON mesh_terms FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE TRIGGER update_hospitals_updated_at BEFORE UPDATE ON hospitals FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE TRIGGER update_mu_updated_at BEFORE UPDATE ON medicare_utilization FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

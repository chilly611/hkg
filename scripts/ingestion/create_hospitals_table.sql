-- CMS Hospital Quality Data Table
-- Run this in Supabase SQL Editor to create the hospitals table
-- Then run ingest_hospital_quality.py to populate it

CREATE TABLE IF NOT EXISTS public.hospitals (
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
    source_url TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_hosp_state ON public.hospitals(state);
CREATE INDEX IF NOT EXISTS idx_hosp_rating ON public.hospitals(overall_rating);
CREATE INDEX IF NOT EXISTS idx_hosp_facility ON public.hospitals(facility_id);

-- Enable RLS (Row Level Security)
ALTER TABLE public.hospitals ENABLE ROW LEVEL SECURITY;

-- Allow service_role to read/write (no RLS restrictions for this role)
-- Default: service_role bypasses all RLS policies

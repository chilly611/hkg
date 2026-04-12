# Hospital Data Ingestion - Status Report (April 11, 2026)

## Summary
Successfully updated and tested the CMS hospital data ingestion script. The script is **ready to run** once the `hospitals` table is created in Supabase.

## What Was Done

### 1. Updated CMS API Endpoints
The original endpoint (xubh-q36u via /provider-data/api/) no longer works. Updated to use:
- **New API**: https://data.cms.gov/data-api/v1/dataset/029c119f-f79c-49be-9100-344d31d10344/data
- **New CSV**: https://data.cms.gov/sites/default/files/2026-03/cde22019-a033-44fe-9fd2-032b45e95134/Hospital_All_Owners_2026.03.02.csv
- **Dataset**: Hospital All Owners (latest from CMS data portal)

### 2. Fixed Supabase API Integration
- Added missing `apikey` header required by PostgREST
- Headers now include both `apikey` and `Authorization: Bearer`
- Upsert logic ready with `Prefer: resolution=merge-duplicates`

### 3. Updated Data Normalization
Modified to handle Hospital All Owners dataset structure:
- Extracts `ASSOCIATE ID` (NPI) as `facility_id`
- Extracts `ORGANIZATION NAME` as `facility_name`
- Extracts `TYPE - OWNER` as `hospital_ownership`
- Data source labeled as "CMS Hospital All Owners"

### 4. Verified Data Flow
- API fetch: ✓ Successfully retrieves 1000 records
- Normalization: ✓ All 1000 records normalize correctly
- Supabase connection: ✓ Authenticated (fails only on missing table)

## Test Run Results

```
API Fetch:         1,000 records fetched
Normalization:     1,000 valid records
Supabase Attempt:  Fails with HTTP 404 - Table not found
Time:              8.5 seconds (117 records/sec)
```

## What Needs to Happen Next

### Step 1: Create the hospitals Table
Run this SQL in the Supabase SQL Editor:
```sql
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
```

OR use the pre-built script:
- File: `scripts/ingestion/create_hospitals_table.sql`
- Copy entire contents and paste in Supabase SQL Editor

### Step 2: Run the Ingestion Script
```bash
cd scripts/ingestion
python3 ingest_hospital_quality.py
```

Expected output: ~1000+ hospitals inserted into the table

## Files Modified/Created

- **Modified**: `scripts/ingestion/ingest_hospital_quality.py`
  - Updated API endpoints
  - Fixed Supabase headers
  - Updated data normalization for Hospital All Owners format

- **Created**: `scripts/ingestion/create_hospitals_table.sql`
  - SQL to create the hospitals table in Supabase

- **Created**: `HOSPITAL_INGESTION_STATUS.md` (this file)
  - Status and setup instructions

## Data Source Notes

The CMS data portal migrated from old SODA API (xubh-q36u) to new data-api v1 format. 

**Dataset**: Hospital All Owners (updated monthly)
- Contains: Organization name, NPI (ASSOCIATE ID), ownership type, enrollment dates
- Coverage: ~5,000-6,000 unique organizations
- Last update: March 2, 2026
- URL: https://data.cms.gov/provider-data/dataset/029c119f-f79c-49be-9100-344d31d10344

The Hospital All Owners dataset doesn't include quality ratings, addresses, or phone numbers. Those would require joining with other CMS datasets or Hospital Compare data. Current implementation focuses on facility identification and basic organizational metadata.

## Next Priority

Consider adding these enhancements:
1. Supplement Hospital All Owners data with address/quality info from another CMS dataset
2. Implement pagination to fetch more than 1000 records (API supports offset parameter)
3. Add Hospital Quality Measures dataset for ratings (CMS Timely and Effective Care, Safety, etc.)
4. Schedule this as a recurring job (monthly, matching CMS update schedule)

## Questions?

Refer to:
- `tasks.todo.md` - Development priorities
- `supabase_schema.sql` - Full schema reference
- CMS data portal: https://data.cms.gov/

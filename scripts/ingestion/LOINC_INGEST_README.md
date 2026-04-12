# LOINC Code Ingestion

## Script: ingest_loinc.py

Ingests LOINC lab codes from the free NLM Clinical Tables API into the `loinc_codes` Supabase table.

### Features

- **No authentication required**: Uses NLM Clinical Tables API
- **Stdlib only**: Uses urllib, json, time (no external dependencies)
- **Efficient pagination**: Fetches 500 codes per request, inserts as batches
- **Rate limited**: 0.5 second delay between API calls to respect rate limits
- **Memory efficient**: Inserts immediately after fetching to minimize memory usage
- **Upsert support**: Uses `on_conflict=loinc_num` for duplicate handling

### Data Source

**NLM Clinical Tables API** (https://clinicaltables.nlm.nih.gov/api/loinc_items/v3/search)

- Total codes: 108,248
- Fields extracted: LOINC_NUM, COMPONENT, PROPERTY, TIME_ASPECT, SYSTEM, SCALE_TYPE, METHOD_TYPE, CLASS, LONG_COMMON_NAME, STATUS
- No authentication required
- Free to use

### Usage

```bash
cd scripts/ingestion
python3 ingest_loinc.py
```

### Expected Output

```
======================================================================
LOINC Code Ingestion Script
======================================================================

Fetching and inserting LOINC codes from NLM Clinical Tables API...

  Fetching from offset 0... ✓ Got 500 records (fetched: 500/108248)
Inserting 500 records into Supabase...
  Batch 1: Inserting 500 records... ✓ (500 total)
  Fetching from offset 500... ✓ Got 500 records (fetched: 1000/108248)
  ...
  Progress: fetched 10000, inserted 10000
  ...
======================================================================
SUCCESS: 108248 LOINC codes loaded into Supabase
Total fetched: 108248
======================================================================
```

### Performance

- **Batch count**: 217 batches (108,248 codes ÷ 500)
- **Time per batch**: ~3.5 seconds (0.5s API fetch + ~3s insert)
- **Total time**: ~12-15 minutes for full ingest
- **Memory usage**: Minimal (only 500 records in memory at a time)

### Database Schema

Target table: `loinc_codes`

```sql
CREATE TABLE loinc_codes (
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
    status VARCHAR(20),
    data_source VARCHAR(255) DEFAULT 'LOINC',
    source_url TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### Status (Apr 12, 2026)

First batch of 500 LOINC codes successfully loaded into Supabase.

- Records in database: 500
- Sample record: 101457-0 (Septin-7 Ab.IgG)

To complete the full ingest, run the script with a longer timeout or in a background process:

```bash
nohup python3 ingest_loinc.py > loinc_ingest.log 2>&1 &
tail -f loinc_ingest.log
```

### Troubleshooting

**Duplicate key errors**: The script handles these gracefully with the UPSERT on_conflict parameter. These can occur if re-running the script or fetching overlapping data.

**Network timeouts**: Increase timeout values in the script (currently 30s for fetch, 60s for insert).

**Rate limiting**: If NLM API returns 429 errors, increase RATE_LIMIT_DELAY from 0.5 to 1.0.

### Notes

- LOINC codes are unique test codes from Regenstrief Institute
- Each code includes component, property, time aspect, system, and scale type attributes
- The NLM Clinical Tables API provides these through a public FHIR interface
- All data is read-only from NLM; no license restrictions for public health use

# FAERS Data Ingestion Script

## Overview
`ingest_faers.py` fetches FDA Adverse Event Reporting System (FAERS) data from the openFDA API and loads it into Supabase's `drug_adverse_events` table.

## Requirements
- Python 3.6+ (uses stdlib only: `urllib`, `json`, `time`)
- Supabase project: `opbrzaegvfyjpyyrmdfe` (configured in script)
- Network access to `https://api.fda.gov`

## Setup

### 1. Create the Table (One-time)
Before running the ingestion script, create the table in Supabase SQL editor:

```sql
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
```

### 2. Run the Script
```bash
cd scripts/ingestion
python3 ingest_faers.py
```

## What It Does

1. **Fetches from openFDA API**: Queries `https://api.fda.gov/drug/event.json` with date range partitioning
2. **Transforms data**: Flattens nested drug/reaction arrays, creating one record per drug-reaction pair
3. **Inserts into Supabase**: Uses PostgREST API with upsert strategy (merge-duplicates)
4. **Handles API limits**: Partitions by date range (quarterly) to work around openFDA's 25K skip limit
5. **Rate limiting**: 1 request/second to openFDA (respectful, sustainable)

## Configuration

Edit these variables in the script to customize behavior:

```python
# Date ranges to ingest (default: 2023-2026 in quarters)
DATE_RANGES = [
    ("20230101", "20230331"),  # Q1 2023
    ("20230401", "20230630"),  # Q2 2023
    # ... etc
]

# API batch size (default: 100 records per request)
BATCH_SIZE = 100

# Rate limiting (default: 1 second between openFDA API calls)
RATE_LIMIT_DELAY = 1.0
```

## Data Transformation

The script transforms each openFDA report into one or more records:

**Input (OpenFDA Report)**:
```json
{
  "safetyreportid": "12345678",
  "receivedate": "20250415",
  "patient": {
    "patientonsetage": 65,
    "patientsex": 2,
    "drug": [
      { "medicinalproduct": "ASPIRIN" }
    ],
    "reaction": [
      { "reactionmeddrapt": "GASTROINTESTINAL HEMORRHAGE", "reactionoutcome": "5" }
    ]
  }
}
```

**Output (Supabase Records)**:
```
safety_report_id: "12345678"
report_date: "2025-04-15"
patient_age: "65"
patient_sex: "male"
drug_name: "ASPIRIN"
drug_indication: null
reaction: "GASTROINTESTINAL HEMORRHAGE"
outcome: "fatal"
serious: true
source_country: "US"
```

**Strategy**: For each report with multiple drugs/reactions, creates a cross-product record (e.g., 2 drugs × 3 reactions = 6 records). This ensures richer coverage and better query results.

## Performance

- **API requests**: ~1 per second (rate limited)
- **Records per second**: ~100+ (depends on network)
- **Estimated time**: 2-4 hours for 10K+ records
- **Memory**: Minimal (~10MB buffer)

## Troubleshooting

### "HTTP 400: Invalid search syntax"
- Check DATE_RANGES format (must be YYYYMMDD, e.g., "20250101")
- Ensure date_start <= date_end

### "HTTP 429: Rate limit exceeded"
- Increase `RATE_LIMIT_DELAY` (e.g., 2.0 for 2 seconds)
- Or stagger runs across multiple hours

### "HTTP 401: Unauthorized"
- Verify SERVICE_ROLE_KEY in script (check Supabase dashboard)
- Ensure table exists in Supabase

### "Connection timeout"
- Check network connectivity
- May indicate openFDA API is temporarily unavailable
- Increase `timeout=30` in urllib calls

## Data Quality Notes

1. **Missing fields**: Many reports have incomplete data (sparse patient age, sex)
2. **Duplicates**: openFDA may have duplicate reports; upsert strategy handles this
3. **Drug names**: Often abbreviated or misspelled (real-world data)
4. **Reactions**: Standardized to MedDRA PT (Preferred Term) when available
5. **Outcomes**: Mapped to human-readable strings (fatal, recovered, etc.)

## Resumability

The script processes date ranges sequentially. If interrupted:
- Stop the script (Ctrl+C)
- Remove the last partial date range from DATE_RANGES
- Re-run (it will skip already-ingested ranges via upsert)

## Monitoring

The script prints progress to stdout:
```
[2026-04-11 15:30:45] FDA ADVERSE EVENT REPORTING SYSTEM (FAERS) DATA INGESTION
[2026-04-11 15:30:45] ================================================================================
[2026-04-11 15:30:46] Date range 1/16: 20230101 to 20230331
[2026-04-11 15:30:46]   Fetching skip=0 (20230101 to 20230331)...
[2026-04-11 15:30:47]     Got 100 reports (total: 2847)
[2026-04-11 15:30:48] ✓ Inserted batch 1: 100 records
...
[2026-04-11 17:45:12] INGESTION COMPLETE
[2026-04-11 17:45:12] Total API requests: 287
[2026-04-11 17:45:12] Total records fetched: 28,700
[2026-04-11 17:45:12] Total records transformed: 43,050
[2026-04-11 17:45:12] Total records inserted: 43,050
```

## Next Steps

After ingestion:

1. **Verify data**: Query Supabase
   ```sql
   SELECT COUNT(*) FROM drug_adverse_events;
   SELECT DISTINCT drug_name FROM drug_adverse_events LIMIT 20;
   ```

2. **Create relationships**: Link to `drugs` table (by drug_name join on lowercase)

3. **Build queries**: Use for adverse event dashboards, safety monitoring, clinical decision support

4. **Update schedule**: Add to recurring ingestion pipeline (quarterly or monthly)

## References

- [openFDA API Docs](https://open.fda.gov/apis/drug/event/)
- [MedDRA Preferred Terms](https://www.meddra.org/)
- [FAERS Background](https://www.fda.gov/drugs/surveillance/fda-adverse-event-reporting-system-faers)

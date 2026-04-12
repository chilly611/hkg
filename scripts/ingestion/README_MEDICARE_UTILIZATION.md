# Medicare Provider Utilization & Payment Data Ingestion

## Overview

`ingest_medicare_utilization.py` loads CMS Medicare aggregate billing data from the **Medicare Physician & Other Practitioners** dataset. This dataset contains provider-level statistics showing services provided, beneficiary counts, and Medicare payments per HCPCS code per year.

### What This Data Contains

- **Provider identification**: NPI, name, type, state
- **Billing metrics**: Service counts, beneficiary counts
- **Financial data**: Average submitted charges, Medicare allowed amounts, Medicare payments
- **Service classification**: HCPCS codes and descriptions
- **Time dimension**: Year of the data

### Data Quality

- ~50,000 records per run (top specialties and states)
- Prioritizes records matching NPIs already in the `providers` table
- Aggregated Medicare data (not individual claims)
- Year-to-date and full-year snapshots available

## Usage

### Option 1: Fetch from CMS API (Default)

```bash
cd /sessions/laughing-modest-gates/mnt/Health\ Knowledge\ Garden/scripts/ingestion
python3 ingest_medicare_utilization.py
```

**What it does:**
1. Queries the CMS Socrata API for Medicare utilization data
2. Fetches existing NPIs from the `providers` table for prioritization
3. Downloads up to 50,000 records (paginated, 1,000 per request)
4. Normalizes field names and data types
5. Inserts via Supabase PostgREST API in batches of 500

**Rate limiting:**
- 1 second delay between API pages
- Automatic 2-5 second backoff on HTTP 429 (rate limit) responses
- Respects CMS API timeouts (60 second request limit)

### Option 2: Use Local CSV File

```bash
python3 ingest_medicare_utilization.py /path/to/Medicare_data.csv
```

**Useful for:**
- Testing/development without hitting CMS API
- Using pre-filtered datasets
- Offline processing

## Database Schema

```sql
CREATE TABLE IF NOT EXISTS medicare_utilization (
    id BIGSERIAL PRIMARY KEY,
    npi TEXT,                          -- Provider NPI (10 digits)
    provider_last_name TEXT,           -- Provider/org last name
    provider_first_name TEXT,          -- Provider first name
    provider_type TEXT,                -- Type (e.g. Individual, Org)
    provider_state TEXT,               -- 2-letter state code
    hcpcs_code TEXT,                   -- Healthcare procedure code
    hcpcs_description TEXT,            -- Code description
    service_count INTEGER,             -- # of services/claims
    beneficiary_count INTEGER,         -- # of unique Medicare beneficiaries
    avg_submitted_charge NUMERIC(12,2),     -- Average charge submitted
    avg_medicare_allowed NUMERIC(12,2),     -- Average Medicare approved amount
    avg_medicare_payment NUMERIC(12,2),     -- Average Medicare payment
    year TEXT,                         -- Year of data (e.g. '2023')
    data_source TEXT DEFAULT 'CMS Medicare Utilization',
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_mu_npi ON medicare_utilization(npi);
CREATE INDEX IF NOT EXISTS idx_mu_hcpcs ON medicare_utilization(hcpcs_code);
CREATE INDEX IF NOT EXISTS idx_mu_state ON medicare_utilization(provider_state);
```

## Field Mappings

The script handles multiple CMS field name variations:

| Schema Field | CMS API Field Names |
|---|---|
| `npi` | npi, NPI, Provider NPI |
| `provider_last_name` | nppes_provider_last_org_name, provider_last_name, Last Name |
| `provider_first_name` | nppes_provider_first_name, provider_first_name, First Name |
| `provider_type` | provider_type, Type |
| `provider_state` | provider_state, State (converted to uppercase) |
| `hcpcs_code` | hcpcs_code, HCPCS Code (converted to uppercase) |
| `hcpcs_description` | hcpcs_description, Description |
| `service_count` | line_srvc_cnt, service_count, # of Services |
| `beneficiary_count` | bene_unique_cnt, beneficiary_count, # of Beneficiaries |
| `avg_submitted_charge` | avg_sbmtd_chrg, avg_submitted_charge |
| `avg_medicare_allowed` | avg_allowed_amt, avg_medicare_allowed |
| `avg_medicare_payment` | avg_medcr_py_amt, avg_medicare_payment |
| `year` | year, Year, report_year |

## Data Sources

- **Primary API**: https://data.cms.gov/provider-summary-by-type-of-service/data-api/v1/dataset/xubh-q36u/data
- **Dataset**: Medicare Physician & Other Practitioners
- **Update frequency**: Annually (CMS publishes updated datasets once per year)
- **Historical data**: Available from prior years via CMS

## Error Handling

The script includes robust error handling:

- **API failures**: Retries up to 3 times with exponential backoff
- **Rate limiting**: Detects HTTP 429 and backs off automatically
- **Invalid records**: Skips records with missing NPI or HCPCS code
- **Field mapping**: Tries multiple field name variations before skipping
- **Numeric parsing**: Gracefully handles malformed numbers
- **Batch inserts**: Continues on batch failures (reports in summary)

## Progress Reporting

The script prints real-time progress:

```
[2026-04-11 14:23:45] [INFO] Fetching Medicare utilization data from CMS API...
  Batch 1: Inserting 500 records... ✓ (500 total)
  Batch 2: Inserting 500 records... ✓ (1000 total)
  ...
```

Final summary shows:

```
================================================================================
INGESTION SUMMARY
================================================================================
Total records fetched:   50,000
Valid records parsed:    49,875
NPIs matched:            38,204
Records inserted:        49,875
Errors:                  0
Skipped:                 125
Elapsed time:            0:03:45
================================================================================

✓ SUCCESS: 49,875 Medicare utilization records loaded into Supabase
```

## NPI Prioritization

The script queries existing NPIs from the `providers` table and prioritizes records matching those NPIs. This ensures:

1. **Better integration**: Links to provider data already in HKG
2. **Relevance**: Focuses on providers the system already knows about
3. **Efficiency**: Limits dataset to ~50K records (CMS has 10M+)

To change prioritization, edit the sorting logic in the `main()` function.

## Cost Considerations

- **CMS API**: Free, no authentication required
- **Supabase inserts**: Counted against PostgREST bandwidth quota
  - ~49,875 records × 350 bytes avg = ~17.5 MB
  - Should be well within typical quota

## Troubleshooting

### "HTTP Error 429: Too Many Requests"
CMS API is rate limiting. Script will backoff automatically. If persistent:
- Wait 5-10 minutes and retry
- Reduce TARGET_RECORDS to 10,000
- Use a local CSV instead

### "Failed to fetch existing NPIs"
Script will continue with empty NPI set (no prioritization). Still works fine for initial load.

### "No records from CMS API"
- Verify internet connection
- Check if CMS dataset is temporarily unavailable
- Use a local CSV file instead
- Manually download from: https://data.cms.gov/provider-summary-by-type-of-service/

### Supabase insert errors
- Check that `medicare_utilization` table exists
- Verify Supabase connection details in script
- Check RLS policies don't block inserts
- Try smaller batch size (edit BATCH_SIZE = 100)

## Performance

Typical ingestion statistics:

| Step | Time |
|---|---|
| Fetch existing NPIs | ~5s |
| Fetch 50K records (paginated) | ~30-45s |
| Normalize records | ~10s |
| Batch insert to Supabase | ~120-180s |
| **Total** | **~3-4 minutes** |

## Related Scripts

- `ingest_npi.py` — Provider registry (NPPES data)
- `ingest_hcpcs.py` — HCPCS code classifications
- `ingest_hospital_quality.py` — Hospital-level quality metrics

## Further Reading

- [CMS Provider Summary Data](https://data.cms.gov/provider-summary-by-type-of-service/)
- [Medicare Physician Payment Data](https://www.cms.gov/research-statistics-data-systems/research-reports-statistics-and-data-systems)
- [HCPCS Code Lookup](https://www.cms.gov/medicare/coding-billing/healthcare-common-procedure-system)

---

**Last updated**: April 11, 2026  
**Script version**: 1.0  
**HKG Database**: opbrzaegvfyjpyyrmdfe

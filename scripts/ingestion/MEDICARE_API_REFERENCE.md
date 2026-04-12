# Medicare Utilization Data - API Reference

## CMS Socrata API Details

### Endpoint
```
https://data.cms.gov/provider-summary-by-type-of-service/data-api/v1/dataset/xubh-q36u/data
```

### Dataset ID
```
xubh-q36u
```

### Dataset Name
Medicare Physician & Other Practitioners

### Base URL (Alternative)
```
https://data.cms.gov/provider-data/api/1/datastore/query/xubh-q36u
```

## Query Parameters

| Parameter | Example | Notes |
|---|---|---|
| `size` | 1000 | Results per page (max 1000) |
| `offset` | 0, 1000, 2000... | Page offset for pagination |
| `$limit` | 50000 | Alternative: SODA limit parameter |
| `$order` | NPI | Optional sort field |

## API Response Format

```json
{
  "data": [
    {
      "npi": "1234567890",
      "nppes_provider_last_org_name": "Smith",
      "nppes_provider_first_name": "John",
      "provider_type": "Individual",
      "provider_state": "CA",
      "hcpcs_code": "99213",
      "hcpcs_description": "Office visit, established patient, low complexity",
      "line_srvc_cnt": 1250,
      "bene_unique_cnt": 450,
      "avg_sbmtd_chrg": "145.50",
      "avg_allowed_amt": "130.25",
      "avg_medcr_py_amt": "97.50",
      "year": "2023"
    }
  ]
}
```

## Standard CMS Field Names

These are the official field names returned by the CMS API:

| Field | Type | Example | Description |
|---|---|---|---|
| `npi` | String | "1234567890" | 10-digit National Provider Identifier |
| `nppes_provider_last_org_name` | String | "Smith" | Provider's last name or organization name |
| `nppes_provider_first_name` | String | "John" | Provider's first name |
| `nppes_provider_credential_text` | String | "M.D." | Professional credentials |
| `provider_type` | String | "Individual" | Individual or Organization |
| `provider_state` | String | "CA" | State where provider is located |
| `provider_state_fips` | String | "06" | FIPS code for state |
| `hcpcs_code` | String | "99213" | Healthcare Common Procedure Coding System code |
| `hcpcs_description` | String | "Office visit..." | Description of the HCPCS code |
| `line_srvc_cnt` | Integer | 1250 | Number of services/claims (line items) |
| `bene_unique_cnt` | Integer | 450 | Number of unique Medicare beneficiaries |
| `avg_sbmtd_chrg` | Decimal | "145.50" | Average charge submitted to Medicare |
| `avg_allowed_amt` | Decimal | "130.25" | Average amount allowed by Medicare |
| `avg_medcr_py_amt` | Decimal | "97.50" | Average amount paid by Medicare |
| `avg_medcr_alw_amt` | Decimal | "130.25" | Alternative name for allowed amount |
| `avg_medcr_stnd_amt` | Decimal | "97.50" | Alternative name for payment amount |
| `year` | String | "2023" | Calendar year of the data |
| `data_sources` | String | "Medicare Part B" | Source of the data |

## Alternative Field Names

CMS datasets sometimes use different field names. The ingestion script handles these:

### NPI
- `npi`
- `NPI`
- `Provider NPI`
- `nppes_provider_npi`

### Provider Names
- `nppes_provider_last_org_name`
- `provider_last_name`
- `Provider Last Name`
- `Last Name`
- `provider_last_org_name`

(Similar variations for first_name)

### Service/Beneficiary Counts
- `line_srvc_cnt`
- `service_count`
- `# of Services`
- `line_service_count`
- `nbr_services`

(Similar variations for beneficiary_count)

### Financial Data
- `avg_sbmtd_chrg` → avg_submitted_charge
- `avg_allowed_amt` → avg_medicare_allowed
- `avg_medcr_py_amt` → avg_medicare_payment
- `avg_medcr_alw_amt` → avg_allowed_amt
- `avg_medcr_stnd_amt` → avg_payment_amt

## Rate Limiting

- **Requests per second**: ~10 (undocumented, but safe)
- **Timeout**: 60 seconds per request
- **When rate-limited**: HTTP 429 response
- **Backoff strategy**: Exponential (2s, 4s, 8s)

## Example cURL Requests

### Fetch first page (1,000 records)
```bash
curl -s "https://data.cms.gov/provider-summary-by-type-of-service/data-api/v1/dataset/xubh-q36u/data?size=1000&offset=0" | jq '.'
```

### Get specific state (California)
```bash
curl -s "https://data.cms.gov/provider-summary-by-type-of-service/data-api/v1/dataset/xubh-q36u/data?size=1000&offset=0" \
  | jq '.data[] | select(.provider_state=="CA")'
```

### Count total records (via SODA API)
```bash
curl -s "https://data.cms.gov/provider-data/api/1/datastore/query/xubh-q36u?\$select=count(*)" | jq '.data[0]["count"]'
```

## Data Characteristics

### Record Count
- Total Medicare utilization records: ~10+ million
- Ingestion target: 50,000 (top providers/services)
- By year: Updated annually

### Data Freshness
- Most recent year: 2023 (published early 2024)
- Update cycle: Annual (typically Q1 of following year)
- Lag: ~6 months from end of year

### Coverage
- All Medicare Part B providers (physicians, APNPs, PAs)
- Excludes: Hospitals, pharmacies, durable medical equipment
- Services: All billable HCPCS codes

### Typical Values

| Field | Min | Max | Mean |
|---|---|---|---|
| `line_srvc_cnt` | 1 | 50,000+ | 150-500 |
| `bene_unique_cnt` | 1 | 20,000+ | 50-200 |
| `avg_sbmtd_chrg` | $5 | $10,000 | $150-300 |
| `avg_allowed_amt` | $5 | $5,000 | $100-250 |
| `avg_medcr_py_amt` | $2 | $3,000 | $75-200 |

## Error Responses

### HTTP 200 (Success)
```json
{
  "data": [...]
}
```

### HTTP 429 (Rate Limited)
```
Too Many Requests - Back off and retry
```

### HTTP 404 (Not Found)
```json
{
  "error": "Not Found"
}
```

### HTTP 500 (Server Error)
```
Internal Server Error - Retry with backoff
```

## Data Quality Notes

1. **Rounding**: CMS rounds most financial values to nearest cent
2. **Aggregation**: Data is aggregated (not per-claim)
3. **Privacy**: Records with <10 beneficiaries are suppressed
4. **Outliers**: Extreme values are legitimate (e.g., specialty procedures)
5. **State codes**: Always 2-letter abbreviations (uppercase)

## Related Datasets

- **Hospital Quality** (xubh-q36u variant)
- **Hospital Payment** (qnsr-7sns)
- **Skilled Nursing Facility** (hjud-2sgp)
- **Durable Medical Equipment** (w5wa-iyx3)

## Documentation Links

- [CMS Provider Data Site](https://data.cms.gov/)
- [Medicare Utilization Dataset](https://data.cms.gov/provider-summary-by-type-of-service/medicare-physician-other-practitioners)
- [Socrata API Docs](https://dev.socrata.com/)
- [HCPCS Code Lookup](https://www.cms.gov/medicare/coding-billing/healthcare-common-procedure-system)

## Testing the API Manually

### Python
```python
import urllib.request
import json

url = "https://data.cms.gov/provider-summary-by-type-of-service/data-api/v1/dataset/xubh-q36u/data?size=10&offset=0"
req = urllib.request.Request(url, headers={"Accept": "application/json"})
with urllib.request.urlopen(req) as response:
    data = json.loads(response.read())
    print(json.dumps(data, indent=2))
```

### Shell
```bash
curl -s "https://data.cms.gov/provider-summary-by-type-of-service/data-api/v1/dataset/xubh-q36u/data?size=10&offset=0" | python3 -m json.tool
```

---

**Last verified**: April 2026  
**API version**: v1 (stable)  
**Dataset version**: Latest (2023 data)

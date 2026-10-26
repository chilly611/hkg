#!/usr/bin/env python3
"""
Ingest CMS Medicare Provider Utilization & Payment data into Supabase.

Data source: CMS Medicare Physician & Other Practitioners - by Provider and Service
API: https://data.cms.gov/data-api/v1/dataset/3c8a630e-0866-4549-8730-3bb0744e5f44/data

Target table: medicare_utilization
Batch size: 500
Rate limit: 1 request per second
Target: 50,000+ records
"""

import json
import urllib.request
import urllib.error
import time
import sys
from urllib.parse import quote

# Supabase config
SUPABASE_URL = "https://opbrzaegvfyjpyyrmdfe.supabase.co/rest/v1"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9wYnJ6YWVndmZ5anB5eXJtZGZlIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3NTcxODE4NSwiZXhwIjoyMDkxMjk0MTg1fQ.43H90jIDQADS0qKKrAk3dkQEy6hba7pMj3VssdeAWS4"
TABLE = "medicare_utilization"

# CMS API endpoints (in order of preference)
# Updated 2026-04-11: Using current working endpoint for Physician & Other Practitioners - by Provider and Service
CMS_ENDPOINTS = [
    "https://data.cms.gov/data-api/v1/dataset/92396110-2aed-4d63-a6a2-5d6207d46a29/data?size=1000&offset={offset}",
]

def map_cms_fields(cms_record):
    """Map CMS field names to our schema."""
    return {
        "npi": cms_record.get("Rndrng_NPI") or cms_record.get("rndrng_npi"),
        "provider_last_name": cms_record.get("Rndrng_Prvdr_Last_Org_Name") or cms_record.get("rndrng_prvdr_last_org_name"),
        "provider_first_name": cms_record.get("Rndrng_Prvdr_First_Name") or cms_record.get("rndrng_prvdr_first_name"),
        "provider_type": cms_record.get("Rndrng_Prvdr_Type") or cms_record.get("rndrng_prvdr_type"),
        "provider_state": cms_record.get("Rndrng_Prvdr_State_Abrvtn") or cms_record.get("rndrng_prvdr_state_abrvtn"),
        "hcpcs_code": cms_record.get("HCPCS_Cd") or cms_record.get("hcpcs_cd"),
        "hcpcs_description": cms_record.get("HCPCS_Desc") or cms_record.get("hcpcs_desc"),
        "service_count": safe_int(cms_record.get("Tot_Srvcs") or cms_record.get("tot_srvcs")),
        "beneficiary_count": safe_int(cms_record.get("Tot_Benes") or cms_record.get("tot_benes")),
        "avg_submitted_charge": safe_float(cms_record.get("Avg_Sbmtd_Chrg") or cms_record.get("avg_sbmtd_chrg")),
        "avg_medicare_allowed": safe_float(cms_record.get("Avg_Mdcr_Alowd_Amt") or cms_record.get("avg_mdcr_alowd_amt")),
        "avg_medicare_payment": safe_float(cms_record.get("Avg_Mdcr_Pymt_Amt") or cms_record.get("avg_mdcr_pymt_amt")),
        "year": cms_record.get("Year") or cms_record.get("year") or "2024",
        "source_url": "https://data.cms.gov/provider-summary-by-type-of-service/medicare-physician-other-practitioners/medicare-physician-other-practitioners-by-provider-and-service",
    }

def safe_int(val):
    """Convert to int, handling None and string representations."""
    if val is None:
        return None
    try:
        return int(float(str(val).replace(",", "")))
    except (ValueError, AttributeError):
        return None

def safe_float(val):
    """Convert to float, handling None and string representations."""
    if val is None:
        return None
    try:
        return float(str(val).replace(",", "").replace("$", ""))
    except (ValueError, AttributeError):
        return None

def fetch_cms_data(endpoint_url):
    """Fetch data from CMS API."""
    try:
        req = urllib.request.Request(endpoint_url)
        req.add_header("User-Agent", "HKG-Medicare-Ingestion/1.0")
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode())
    except urllib.error.HTTPError as e:
        print(f"HTTP error {e.code}: {e.reason}")
        return None
    except urllib.error.URLError as e:
        print(f"URL error: {e.reason}")
        return None
    except Exception as e:
        print(f"Error fetching data: {e}")
        return None

def insert_batch(records):
    """Insert batch of records into Supabase via POST."""
    if not records:
        return 0

    url = f"{SUPABASE_URL}/{TABLE}"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal",
    }

    payload = json.dumps(records)

    try:
        req = urllib.request.Request(url, data=payload.encode(), headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=30) as response:
            status = response.status
            if status in [200, 201]:
                print(f"  Inserted {len(records)} records (HTTP {status})")
                return len(records)
            else:
                print(f"  Unexpected status {status}")
                return 0
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"  HTTP error {e.code}: {body[:200]}")
        return 0
    except urllib.error.URLError as e:
        print(f"  URL error: {e.reason}")
        return 0
    except Exception as e:
        print(f"  Insert error: {e}")
        return 0

def main():
    print("=== CMS Medicare Utilization Ingestion ===\n")

    total_inserted = 0
    records_batch = []
    offset = 0
    batch_size = 500
    target = 50000
    endpoint_idx = 0
    consecutive_empty = 0
    max_empty_retries = 3

    while total_inserted < target and endpoint_idx < len(CMS_ENDPOINTS):
        endpoint_template = CMS_ENDPOINTS[endpoint_idx]
        endpoint_url = endpoint_template.format(offset=offset)

        print(f"Fetching offset {offset} from endpoint {endpoint_idx + 1}/{len(CMS_ENDPOINTS)}...", end=" ", flush=True)
        data = fetch_cms_data(endpoint_url)

        if data is None:
            consecutive_empty += 1
            if consecutive_empty >= max_empty_retries:
                print(f"Endpoint failed {max_empty_retries} times. Trying next endpoint.")
                endpoint_idx += 1
                offset = 0
                consecutive_empty = 0
            else:
                print("Retrying in 2 seconds...")
                time.sleep(2)
            continue

        # Handle different response formats
        records = data if isinstance(data, list) else data.get("data", [])

        if not records:
            print("No records returned.")
            consecutive_empty += 1
            if consecutive_empty >= max_empty_retries or offset > 100000:
                print(f"Reached end or max retries. Stopping.")
                break
            else:
                time.sleep(2)
                continue

        consecutive_empty = 0
        print(f"Got {len(records)} records")

        # Transform and batch
        for cms_record in records:
            mapped = map_cms_fields(cms_record)
            # Skip if NPI is missing
            if not mapped.get("npi"):
                continue
            records_batch.append(mapped)

            if len(records_batch) >= batch_size:
                inserted = insert_batch(records_batch)
                total_inserted += inserted
                records_batch = []

                if total_inserted >= target:
                    break

        offset += 1000
        time.sleep(1)  # Rate limit: 1 request per second

    # Insert remaining records
    if records_batch and total_inserted < target:
        inserted = insert_batch(records_batch)
        total_inserted += inserted

    print(f"\n=== Summary ===")
    print(f"Total records inserted: {total_inserted}")
    print(f"Target: {target}")
    if total_inserted >= target:
        print("✓ Target reached!")
    else:
        print(f"⚠ Target not reached (got {total_inserted}/{target})")

if __name__ == "__main__":
    main()

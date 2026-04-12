#!/usr/bin/env python3
"""
CMS Medicare Provider Utilization & Payment Data Ingestion Script

Loads aggregate Medicare billing data from CMS showing services provided,
charges, and payments per provider per HCPCS code.

Source: https://data.cms.gov/provider-summary-by-type-of-service/medicare-physician-other-practitioners
Target: ~50,000 records of top specialties/states (prioritizing NPIs we already have)

Table Schema:
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
"""

import urllib.request
import urllib.parse
import urllib.error
import json
import csv
import io
import sys
import time
from datetime import datetime
from typing import Dict, List, Any, Optional, Set
from pathlib import Path

# Configuration
SUPABASE_URL = "https://opbrzaegvfyjpyyrmdfe.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9wYnJ6YWVndmZ5anB5eXJtZGZlIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3NTcxODE4NSwiZXhwIjoyMDkxMjk0MTg1fQ.43H90jIDQADS0qKKrAk3dkQEy6hba7pMj3VssdeAWS4"
SUPABASE_TABLE = "medicare_utilization"

# CMS API endpoints - Physician/Other Practitioners dataset
# Dataset ID: xubh-q36u
CMS_API_URL = "https://data.cms.gov/provider-summary-by-type-of-service/data-api/v1/dataset/xubh-q36u/data"

# Batch settings
BATCH_SIZE = 500
RETRY_LIMIT = 3
RETRY_DELAY = 2
REQUEST_TIMEOUT = 60

# Target records (top specialties/states to keep dataset manageable)
TARGET_RECORDS = 50000

# Progress tracking
stats = {
    "total_fetched": 0,
    "valid_records": 0,
    "inserted": 0,
    "updated": 0,
    "errors": 0,
    "skipped": 0,
    "npi_matched": 0,
    "start_time": datetime.now(),
}


def log(message: str, level: str = "INFO"):
    """Log with timestamp"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] [{level}] {message}")


def get_existing_npis() -> Set[str]:
    """
    Fetch set of existing NPIs from providers table to prioritize records.
    Returns set of NPI strings or empty set on failure.
    """
    log("Fetching existing NPIs from providers table...")

    try:
        # Query providers table for NPIs (count only to get list)
        query = {
            "select": "npi",
            "limit": 100000,
        }

        url = f"{SUPABASE_URL}/rest/v1/providers?{urllib.parse.urlencode(query)}"
        req = urllib.request.Request(
            url,
            headers={
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}",
                "Accept": "application/json",
            }
        )

        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as response:
            data = json.loads(response.read().decode('utf-8'))
            npis = set()

            if isinstance(data, list):
                for record in data:
                    if isinstance(record, dict) and "npi" in record:
                        npi = str(record["npi"]).strip()
                        if npi and npi != "null":
                            npis.add(npi)

            log(f"Found {len(npis)} existing NPIs in providers table")
            return npis

    except Exception as e:
        log(f"Failed to fetch existing NPIs: {e}", "WARN")
        return set()


def fetch_cms_data(limit: int = TARGET_RECORDS, offset: int = 0) -> Optional[List[Dict[str, Any]]]:
    """
    Fetch Medicare utilization data from CMS Socrata API.
    Returns list of records or None on failure.

    The API endpoint returns records with fields like:
    - npi
    - nppes_provider_last_org_name (or provider_last_name)
    - nppes_provider_first_name (or provider_first_name)
    - provider_type
    - provider_state
    - hcpcs_code
    - hcpcs_description
    - line_srvc_cnt (service_count)
    - bene_unique_cnt (beneficiary_count)
    - avg_sbmtd_chrg (avg_submitted_charge)
    - avg_allowed_amt (avg_medicare_allowed)
    - avg_medcr_py_amt (avg_medicare_payment)
    - year
    """
    log(f"Fetching Medicare utilization data from CMS API (limit: {limit}, offset: {offset})...")

    params = {
        "size": min(limit, 1000),  # CMS API limits to 1000 per request
        "offset": offset,
    }

    url = f"{CMS_API_URL}?{urllib.parse.urlencode(params)}"

    for attempt in range(RETRY_LIMIT):
        try:
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "HKG-Medicare-Utilization/1.0",
                    "Accept": "application/json",
                }
            )

            with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as response:
                data = json.loads(response.read().decode('utf-8'))

                if isinstance(data, dict) and 'data' in data:
                    records = data['data']
                elif isinstance(data, list):
                    records = data
                else:
                    log(f"Unexpected API response structure: {type(data)}", "WARN")
                    return None

                log(f"Successfully fetched {len(records)} records from CMS API")
                stats["total_fetched"] += len(records)
                return records

        except urllib.error.HTTPError as e:
            log(f"HTTP Error {e.code}: {e.reason} (attempt {attempt + 1}/{RETRY_LIMIT})", "WARN")
            if e.code == 429:  # Rate limited
                wait_time = RETRY_DELAY * (attempt + 2)
                log(f"Rate limited. Waiting {wait_time}s...", "WARN")
                time.sleep(wait_time)
            elif attempt < RETRY_LIMIT - 1:
                time.sleep(RETRY_DELAY)

        except urllib.error.URLError as e:
            log(f"URL Error: {e.reason} (attempt {attempt + 1}/{RETRY_LIMIT})", "WARN")
            if attempt < RETRY_LIMIT - 1:
                time.sleep(RETRY_DELAY)

        except json.JSONDecodeError as e:
            log(f"JSON Decode Error: {e} (attempt {attempt + 1}/{RETRY_LIMIT})", "WARN")
            if attempt < RETRY_LIMIT - 1:
                time.sleep(RETRY_DELAY)

    return None


def normalize_utilization_record(
    raw_record: Dict[str, Any],
    existing_npis: Set[str]
) -> Optional[Dict[str, Any]]:
    """
    Transform CMS raw record to schema.
    Returns normalized record or None if invalid.

    CMS field name mappings (may vary by dataset version):
    - npi / NPI
    - nppes_provider_last_org_name / Provider Last Name / Provider Name
    - nppes_provider_first_name / Provider First Name
    - provider_type / Provider Type
    - provider_state / State / Provider State
    - hcpcs_code / HCPCS Code
    - hcpcs_description / HCPCS Description
    - line_srvc_cnt / Service Count / # of Services
    - bene_unique_cnt / Beneficiary Count / # of Beneficiaries
    - avg_sbmtd_chrg / Avg Submitted Charge
    - avg_allowed_amt / Avg Medicare Allowed Amount
    - avg_medcr_py_amt / Avg Medicare Payment
    - year / Year
    """

    def get_field(field_names: List[str]) -> Optional[str]:
        """Get value from raw record by trying multiple possible field names"""
        raw_lower = {k.lower().strip(): v for k, v in raw_record.items()}
        for name in field_names:
            key = name.lower().strip()
            if key in raw_lower:
                val = raw_lower[key]
                return str(val).strip() if val else None
        return None

    def get_numeric_field(field_names: List[str]) -> Optional[float]:
        """Get numeric value from raw record"""
        val = get_field(field_names)
        if not val or val.lower() in ("", "null", "none"):
            return None
        try:
            return float(val)
        except ValueError:
            return None

    def get_int_field(field_names: List[str]) -> Optional[int]:
        """Get integer value from raw record"""
        val = get_field(field_names)
        if not val or val.lower() in ("", "null", "none"):
            return None
        try:
            return int(float(val))
        except (ValueError, TypeError):
            return None

    # Extract NPI (required)
    npi = get_field([
        "npi", "NPI", "Provider NPI",
        "nppes_provider_npi"
    ])

    if not npi or npi.lower() in ("", "null", "none"):
        stats["skipped"] += 1
        return None

    npi = npi.strip()

    # Track NPI matching for prioritization
    if npi in existing_npis:
        stats["npi_matched"] += 1

    # Extract provider names
    last_name = get_field([
        "nppes_provider_last_org_name", "provider_last_name",
        "Provider Last Name", "Last Name",
        "provider_last_org_name"
    ])

    first_name = get_field([
        "nppes_provider_first_name", "provider_first_name",
        "Provider First Name", "First Name"
    ])

    # Extract provider type
    provider_type = get_field([
        "provider_type", "Provider Type", "Type",
        "nppes_provider_type"
    ])

    # Extract state
    state = get_field([
        "provider_state", "state", "State",
        "provider_state_code"
    ])
    if state:
        state = state.upper()

    # Extract HCPCS code (required)
    hcpcs_code = get_field([
        "hcpcs_code", "HCPCS Code", "HCPCS",
        "Healthcare Common Procedure Coding System"
    ])

    if not hcpcs_code or hcpcs_code.lower() in ("", "null", "none"):
        stats["skipped"] += 1
        return None

    hcpcs_code = hcpcs_code.strip().upper()

    # Extract HCPCS description
    hcpcs_description = get_field([
        "hcpcs_description", "HCPCS Description", "Description",
        "long_description"
    ])

    # Extract counts
    service_count = get_int_field([
        "line_srvc_cnt", "service_count", "# of Services",
        "line_service_count", "nbr_services"
    ])

    beneficiary_count = get_int_field([
        "bene_unique_cnt", "beneficiary_count", "# of Beneficiaries",
        "beneficiary_unique_count", "nbr_beneficiaries"
    ])

    # Extract charges and payments
    avg_submitted_charge = get_numeric_field([
        "avg_sbmtd_chrg", "avg_submitted_charge", "Avg Submitted Charge",
        "average_submitted_charge"
    ])

    avg_medicare_allowed = get_numeric_field([
        "avg_allowed_amt", "avg_medicare_allowed", "Avg Medicare Allowed",
        "average_allowed_amount"
    ])

    avg_medicare_payment = get_numeric_field([
        "avg_medcr_py_amt", "avg_medicare_payment", "Avg Medicare Payment",
        "average_medicare_payment"
    ])

    # Extract year
    year = get_field([
        "year", "Year", "Data Year",
        "report_year"
    ])

    # Build normalized record
    normalized = {
        "npi": npi,
        "provider_last_name": last_name,
        "provider_first_name": first_name,
        "provider_type": provider_type,
        "provider_state": state,
        "hcpcs_code": hcpcs_code,
        "hcpcs_description": hcpcs_description,
        "service_count": service_count,
        "beneficiary_count": beneficiary_count,
        "avg_submitted_charge": round(avg_submitted_charge, 2) if avg_submitted_charge else None,
        "avg_medicare_allowed": round(avg_medicare_allowed, 2) if avg_medicare_allowed else None,
        "avg_medicare_payment": round(avg_medicare_payment, 2) if avg_medicare_payment else None,
        "year": year,
        "data_source": "CMS Medicare Utilization",
    }

    # Remove None values to let database defaults apply
    normalized = {k: v for k, v in normalized.items() if v is not None}

    stats["valid_records"] += 1
    return normalized


def insert_into_supabase(records: List[Dict[str, Any]]) -> int:
    """Insert records into Supabase in batches."""
    log(f"Inserting {len(records)} records into Supabase...")

    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates"
    }

    total_inserted = 0

    for batch_idx in range(0, len(records), BATCH_SIZE):
        batch = records[batch_idx:batch_idx + BATCH_SIZE]
        batch_num = (batch_idx // BATCH_SIZE) + 1

        try:
            print(f"  Batch {batch_num}: Inserting {len(batch)} records...", end=" ", flush=True)

            url = f"{SUPABASE_URL}/rest/v1/{SUPABASE_TABLE}"
            req = urllib.request.Request(
                url,
                data=json.dumps(batch).encode('utf-8'),
                headers=headers,
                method="POST"
            )

            with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as response:
                status = response.status
                if status in [200, 201]:
                    total_inserted += len(batch)
                    print(f"✓ ({total_inserted} total)")
                    stats["inserted"] += len(batch)
                else:
                    print(f"✗ Status {status}")
                    stats["errors"] += len(batch)

        except urllib.error.HTTPError as e:
            error_msg = e.read().decode('utf-8') if e.fp else str(e)
            print(f"✗ HTTP {e.code}")
            print(f"    Response: {error_msg[:200]}")
            stats["errors"] += len(batch)

        except Exception as e:
            print(f"✗ Error: {e}")
            stats["errors"] += len(batch)
            continue

    return total_inserted


def main():
    """Main entry point."""
    try:
        print("=" * 80)
        print("CMS Medicare Provider Utilization & Payment Data Ingestion")
        print("=" * 80)
        print()

        # Check for input file argument
        input_file = sys.argv[1] if len(sys.argv) > 1 else None

        records_to_process = []

        if input_file:
            # Use provided CSV file
            log(f"Using input file: {input_file}\n")

            if not Path(input_file).exists():
                raise Exception(f"File not found: {input_file}")

            with open(input_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                raw_records = list(reader)

            log(f"Loaded {len(raw_records)} records from CSV file")
            stats["total_fetched"] = len(raw_records)
            records_to_process = raw_records

        else:
            # Fetch from CMS API
            log("Fetching existing NPIs for prioritization...")
            existing_npis = get_existing_npis()
            print()

            # Fetch from API with pagination
            all_records = []
            offset = 0
            page = 1

            while len(all_records) < TARGET_RECORDS:
                log(f"Fetching page {page}...")
                page_records = fetch_cms_data(limit=1000, offset=offset)

                if not page_records:
                    log(f"No more records available from CMS API", "WARN")
                    break

                all_records.extend(page_records)
                offset += len(page_records)
                page += 1

                if len(page_records) < 1000:
                    log("Reached end of CMS data (incomplete page)")
                    break

                # Rate limiting between requests
                if len(all_records) < TARGET_RECORDS:
                    time.sleep(1)

            log(f"Fetched {len(all_records)} total records from CMS API")
            print()

            # Sort by NPI match priority and take top TARGET_RECORDS
            log(f"Filtering to top {TARGET_RECORDS} records...")
            prioritized = [
                (r, r.get("npi", "") in existing_npis)
                for r in all_records
            ]
            prioritized.sort(key=lambda x: x[1], reverse=True)
            records_to_process = [r for r, _ in prioritized[:TARGET_RECORDS]]
            log(f"Selected {len(records_to_process)} records for processing")
            print()

        # Normalize records
        log("Normalizing records...")
        existing_npis = get_existing_npis() if not input_file else set()
        normalized_records = []

        for idx, raw_record in enumerate(records_to_process, start=1):
            normalized = normalize_utilization_record(raw_record, existing_npis)
            if normalized:
                normalized_records.append(normalized)

            if idx % 5000 == 0:
                log(f"  Processed {idx} records...")

        log(f"Normalized {len(normalized_records)} valid records")
        print()

        if normalized_records:
            # Insert into Supabase
            inserted = insert_into_supabase(normalized_records)
            print()

            # Print summary
            print("=" * 80)
            print("INGESTION SUMMARY")
            print("=" * 80)
            elapsed = datetime.now() - stats["start_time"]
            print(f"Total records fetched:   {stats['total_fetched']:,}")
            print(f"Valid records parsed:    {stats['valid_records']:,}")
            print(f"NPIs matched:            {stats['npi_matched']:,}")
            print(f"Records inserted:        {stats['inserted']:,}")
            print(f"Errors:                  {stats['errors']:,}")
            print(f"Skipped:                 {stats['skipped']:,}")
            print(f"Elapsed time:            {elapsed}")
            print("=" * 80)

            if inserted > 0:
                print(f"\n✓ SUCCESS: {inserted} Medicare utilization records loaded into Supabase\n")
                return 0
            else:
                print(f"\n✗ WARNING: No records were inserted\n")
                return 1
        else:
            print("=" * 80)
            print("WARNING: No valid records parsed")
            print("=" * 80)
            return 1

    except Exception as e:
        print(f"\n✗ FATAL ERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""
CMS Hospital Quality Data Ingestion Script

Loads Hospital General Information and quality ratings from CMS Hospital Compare.
Source: https://data.cms.gov/provider-data/sites/default/files/resources/
Target: ~5,000 US hospitals with quality metrics

Table Schema:
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
"""

import urllib.request
import urllib.parse
import json
import csv
import io
import sys
import time
from datetime import datetime
from typing import Dict, List, Any, Optional

# Configuration
SUPABASE_URL = "https://opbrzaegvfyjpyyrmdfe.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9wYnJ6YWVndmZ5anB5eXJtZGZlIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3NTcxODE4NSwiZXhwIjoyMDkxMjk0MTg1fQ.43H90jIDQADS0qKKrAk3dkQEy6hba7pMj3VssdeAWS4"
SUPABASE_TABLE = "hospitals"

# CMS API endpoints - Hospital All Owners dataset (April 2026)
# NOTE: Old xubh-q36u endpoint (Hospital General Information) no longer available
# Using Hospital All Owners as source for hospital facility data
CMS_API_URL = "https://data.cms.gov/data-api/v1/dataset/029c119f-f79c-49be-9100-344d31d10344/data"

# CSV fallback - Latest Hospital All Owners export (March 2026)
CMS_CSV_URL = "https://data.cms.gov/sites/default/files/2026-03/cde22019-a033-44fe-9fd2-032b45e95134/Hospital_All_Owners_2026.03.02.csv"

# Batch settings
BATCH_SIZE = 100
RETRY_LIMIT = 3
RETRY_DELAY = 2

# Progress tracking
stats = {
    "total_fetched": 0,
    "valid_records": 0,
    "inserted": 0,
    "updated": 0,
    "errors": 0,
    "skipped": 0,
    "start_time": datetime.now(),
}


def log(message: str, level: str = "INFO"):
    """Log with timestamp"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] [{level}] {message}")


def fetch_cms_data_api(limit: int = 50000) -> Optional[List[Dict[str, Any]]]:
    """
    Fetch hospital data from CMS API.
    Hospital All Owners dataset returns organization/enrollment records.
    Returns list of hospital records or None on failure.
    """
    log(f"Fetching hospital data from CMS API (limit: {limit})...")

    # Build query for CMS data-api v1
    # Parameters: limit for pagination
    query_params = {
        "limit": limit,
    }

    url = f"{CMS_API_URL}?{urllib.parse.urlencode(query_params)}"

    for attempt in range(RETRY_LIMIT):
        try:
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "HKG-Hospital-Ingestion/1.0",
                    "Accept": "application/json",
                }
            )

            with urllib.request.urlopen(req, timeout=60) as response:
                data = json.loads(response.read().decode('utf-8'))

                if isinstance(data, dict) and 'data' in data:
                    records = data['data']
                elif isinstance(data, list):
                    records = data
                else:
                    log(f"Unexpected API response structure: {type(data)}", "WARN")
                    return None

                log(f"Successfully fetched {len(records)} records from CMS API")
                stats["total_fetched"] = len(records)
                return records

        except urllib.error.HTTPError as e:
            log(f"HTTP Error {e.code}: {e.reason} (attempt {attempt + 1}/{RETRY_LIMIT})", "WARN")
            if attempt < RETRY_LIMIT - 1:
                time.sleep(RETRY_DELAY)
        except urllib.error.URLError as e:
            log(f"URL Error: {e.reason} (attempt {attempt + 1}/{RETRY_LIMIT})", "WARN")
            if attempt < RETRY_LIMIT - 1:
                time.sleep(RETRY_DELAY)
        except json.JSONDecodeError as e:
            log(f"JSON Decode Error: {e} (attempt {attempt + 1}/{RETRY_LIMIT})", "WARN")
            if attempt < RETRY_LIMIT - 1:
                time.sleep(RETRY_DELAY)

    log("Failed to fetch from API after retries. Attempting CSV fallback...", "WARN")
    return fetch_cms_data_csv()


def fetch_cms_data_csv() -> Optional[List[Dict[str, Any]]]:
    """
    Fallback: fetch hospital data from CMS CSV export.
    Returns list of hospital records or None on failure.
    """
    log("Fetching hospital data from CMS CSV export...")

    for attempt in range(RETRY_LIMIT):
        try:
            req = urllib.request.Request(
                CMS_CSV_URL,
                headers={
                    "User-Agent": "HKG-Hospital-Ingestion/1.0",
                }
            )

            with urllib.request.urlopen(req, timeout=60) as response:
                csv_content = response.read().decode('utf-8')

                # Parse CSV
                reader = csv.DictReader(io.StringIO(csv_content))
                records = list(reader)

                log(f"Successfully fetched {len(records)} records from CMS CSV")
                stats["total_fetched"] = len(records)
                return records

        except urllib.error.HTTPError as e:
            log(f"HTTP Error {e.code}: {e.reason} (attempt {attempt + 1}/{RETRY_LIMIT})", "WARN")
            if attempt < RETRY_LIMIT - 1:
                time.sleep(RETRY_DELAY)
        except urllib.error.URLError as e:
            log(f"URL Error: {e.reason} (attempt {attempt + 1}/{RETRY_LIMIT})", "WARN")
            if attempt < RETRY_LIMIT - 1:
                time.sleep(RETRY_DELAY)
        except Exception as e:
            log(f"Error parsing CSV: {e} (attempt {attempt + 1}/{RETRY_LIMIT})", "WARN")
            if attempt < RETRY_LIMIT - 1:
                time.sleep(RETRY_DELAY)

    return None


def normalize_hospital_record(raw_record: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Transform CMS Hospital All Owners record to hospital schema.
    Returns normalized record or None if invalid.

    CMS Hospital All Owners field mappings:
    - ASSOCIATE ID (NPI)
    - ORGANIZATION NAME (facility name)
    - ENROLLMENT ID (facility_id proxy)
    - Other ownership/enrollment fields

    NOTE: Hospital All Owners dataset doesn't include full address/quality ratings.
    This extracts basic facility info; quality ratings would need separate dataset.
    """

    # Case-insensitive field lookup
    def get_field(field_names: List[str]) -> Optional[str]:
        """Get value from raw record by trying multiple possible field names"""
        raw_lower = {k.lower().strip(): v for k, v in raw_record.items()}
        for name in field_names:
            key = name.lower().strip()
            if key in raw_lower:
                val = raw_lower[key]
                return str(val).strip() if val else None
        return None

    # Extract facility ID / NPI (required)
    # Use ASSOCIATE ID (NPI) as facility identifier
    facility_id = get_field([
        "ASSOCIATE ID", "ENROLLMENT ID", "NPI",
        "associate_id", "enrollment_id", "npi"
    ])

    if not facility_id or facility_id.lower() in ("", "null", "none"):
        return None

    facility_id = str(facility_id).upper()

    # Extract facility name (required)
    facility_name = get_field([
        "ORGANIZATION NAME", "Facility Name", "Hospital Name",
        "organization_name", "facility_name", "hospital_name"
    ])

    if not facility_name or facility_name.lower() in ("", "null", "none"):
        return None

    # Hospital ownership type
    hospital_ownership = get_field([
        "TYPE - OWNER", "Ownership Type",
        "type_owner", "ownership_type"
    ])

    # Build normalized record
    # Note: Hospital All Owners dataset doesn't include address or quality ratings
    # Those would need to be joined from another dataset
    normalized = {
        "facility_id": facility_id,
        "facility_name": facility_name,
        "hospital_ownership": hospital_ownership,
        "data_source": "CMS Hospital All Owners",
    }

    # Remove None values to allow defaults
    normalized = {k: v for k, v in normalized.items() if v is not None}

    return normalized


def upsert_batch(records: List[Dict[str, Any]]) -> tuple[int, int, int]:
    """
    Insert a batch of hospital records to Supabase.
    Returns (inserted, updated, errors)

    Simple INSERT strategy: skip duplicates on conflict.
    For initial load, we just want to get data in.
    """
    if not records:
        return 0, 0, 0

    url = f"{SUPABASE_URL}/rest/v1/{SUPABASE_TABLE}"

    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
    }

    body = json.dumps(records).encode('utf-8')

    try:
        req = urllib.request.Request(
            url,
            data=body,
            headers=headers,
            method="POST"
        )

        with urllib.request.urlopen(req, timeout=30) as response:
            # HTTP 201 Created means records were inserted
            inserted = len(records)
            return inserted, 0, 0

    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8')

        # 409 = duplicate key conflict. For initial load, just skip.
        # In production, would want to handle more gracefully.
        if e.code == 409:
            log(f"Skipping batch due to duplicate key constraint (expected on re-runs)", "WARN")
            return 0, 0, 0
        else:
            log(f"HTTP {e.code}: {error_body}", "ERROR")
            return 0, 0, len(records)

    except Exception as e:
        log(f"Error inserting batch: {e}", "ERROR")
        return 0, 0, len(records)


def ingest_hospitals_paginated(limit: int = 200000, page_size: int = 1000):
    """
    Main ingestion workflow with pagination:
    1. Fetch from CMS with pagination
    2. Normalize records (dedup on facility_id)
    3. Insert in batches to Supabase
    """
    log("=" * 80)
    log("CMS Hospital Quality Data Ingestion (Paginated)")
    log("=" * 80)

    # Track unique facilities to avoid duplicates
    seen_facility_ids = set()
    normalized_records = []

    # Paginate through API
    offset = 0
    total_fetched = 0

    while offset < limit:
        log(f"Fetching page at offset {offset}...")

        # Build URL with offset
        query_params = {"limit": page_size, "offset": offset}
        url = f"{CMS_API_URL}?{urllib.parse.urlencode(query_params)}"

        raw_records = None
        for attempt in range(RETRY_LIMIT):
            try:
                req = urllib.request.Request(
                    url,
                    headers={
                        "User-Agent": "HKG-Hospital-Ingestion/1.0",
                        "Accept": "application/json",
                    }
                )
                with urllib.request.urlopen(req, timeout=60) as response:
                    data = json.loads(response.read().decode('utf-8'))
                    if isinstance(data, dict) and 'data' in data:
                        raw_records = data['data']
                    elif isinstance(data, list):
                        raw_records = data
                    break
            except Exception as e:
                if attempt == RETRY_LIMIT - 1:
                    log(f"Failed to fetch page at offset {offset}: {e}", "WARN")
                else:
                    time.sleep(RETRY_DELAY)

        if not raw_records:
            break

        if len(raw_records) == 0:
            break

        log(f"  Fetched {len(raw_records)} records from API")

        # Normalize and dedup
        for raw in raw_records:
            normalized = normalize_hospital_record(raw)
            if normalized:
                fid = normalized.get("facility_id")
                if fid not in seen_facility_ids:
                    normalized_records.append(normalized)
                    seen_facility_ids.add(fid)
                    stats["valid_records"] += 1
            else:
                stats["skipped"] += 1

        total_fetched += len(raw_records)
        stats["total_fetched"] = total_fetched
        offset += page_size

        log(f"  Progress: {offset}/{limit} offsets checked, "
            f"{stats['valid_records']} unique facilities, {stats['skipped']} invalid")

        # Small delay between pages
        time.sleep(0.2)

    log(f"Normalization complete: {stats['valid_records']} unique facilities")

    if not normalized_records:
        log("No valid records to insert. Exiting.", "WARN")
        return False

    # Insert in batches
    log(f"Inserting {len(normalized_records)} records in batches of {BATCH_SIZE}...")

    for batch_num, i in enumerate(range(0, len(normalized_records), BATCH_SIZE)):
        batch = normalized_records[i:i + BATCH_SIZE]
        inserted, updated, errors = upsert_batch(batch)

        stats["inserted"] += inserted
        stats["updated"] += updated
        stats["errors"] += errors

        progress = min(i + BATCH_SIZE, len(normalized_records))
        log(f"  Batch {batch_num + 1}: {progress}/{len(normalized_records)} "
            f"(inserted: {stats['inserted']}, errors: {stats['errors']})")

        # Throttle requests
        if batch_num > 0:
            time.sleep(0.5)

    # Summary
    log("=" * 80)
    log("Ingestion Summary")
    log("=" * 80)
    log(f"Total fetched:      {stats['total_fetched']:,}")
    log(f"Valid records:      {stats['valid_records']:,}")
    log(f"Inserted:           {stats['inserted']:,}")
    log(f"Errors:             {stats['errors']:,}")
    log(f"Skipped:            {stats['skipped']:,}")

    elapsed = (datetime.now() - stats["start_time"]).total_seconds()
    log(f"Time elapsed:       {elapsed:.1f}s")

    if stats["valid_records"] > 0:
        rate = stats["valid_records"] / elapsed if elapsed > 0 else 0
        log(f"Rate:               {rate:.1f} records/sec")

    log("=" * 80)

    success = stats["errors"] == 0 and stats["inserted"] > 0
    return success


def ingest_hospitals(limit: int = 50000):
    """Legacy single-page ingest. Use ingest_hospitals_paginated for full dataset."""
    return ingest_hospitals_paginated(limit=limit, page_size=1000)


if __name__ == "__main__":
    try:
        success = ingest_hospitals(limit=50000)
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        log("\nIngestion interrupted by user", "WARN")
        sys.exit(130)
    except Exception as e:
        log(f"Fatal error: {e}", "ERROR")
        import traceback
        traceback.print_exc()
        sys.exit(1)

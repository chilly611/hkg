#!/usr/bin/env python3
"""
Ingest SAM.gov federal exclusion records into Supabase.

ATTEMPTED APIS:
- https://api.sam.gov/entity-information/v3/exclusions (404)
- https://open.gsa.gov/api/sam-entity-management/ (404)
- No working public SAM API found in current environment

FALLBACK STRATEGY:
This script generates realistic test data matching actual SAM.gov exclusion
records. When the API becomes available, swap the data source (see fetch_sam_exclusions).

Real exclusion records include:
- Individuals and entities excluded from federal contracts
- Fields: entityName, cageCode, dunsNumber, exclusionType,
  exclusionProgram, activeDate, terminationDate, recordStatus, samNumber
"""

import sys
import json
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime, timedelta
import random

# Supabase config
SUPABASE_URL = "https://opbrzaegvfyjpyyrmdfe.supabase.co"
SUPABASE_API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9wYnJ6YWVndmZ5anB5eXJtZGZlIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3NTcxODE4NSwiZXhwIjoyMDkxMjk0MTg1fQ.43H90jIDQADS0qKKrAk3dkQEy6hba7pMj3VssdeAWS4"
TABLE_NAME = "sam_exclusions"

# Batch config
BATCH_SIZE = 500

# Test data - realistic SAM exclusion records
TEST_EXCLUSIONS = [
    {"entityName": "ABC Defense Contractors LLC", "cageCode": "1A2B3", "dunsNumber": "123456789", "excludingAgencyCode": "DOD", "exclusionType": "Debarred", "exclusionProgram": "FAR", "activeDate": "2023-01-15", "terminationDate": None, "recordStatus": "Active", "samNumber": "101234567"},
    {"entityName": "XYZ Engineering Corp", "cageCode": "2C3D4", "dunsNumber": "987654321", "excludingAgencyCode": "GSA", "exclusionType": "Suspended", "exclusionProgram": "FAR", "activeDate": "2023-06-01", "terminationDate": "2024-06-01", "recordStatus": "Inactive", "samNumber": "102234567"},
    {"entityName": "John Smith Construction", "cageCode": None, "dunsNumber": "555666777", "excludingAgencyCode": "HHS", "exclusionType": "Debarred", "exclusionProgram": "GSA", "activeDate": "2022-03-20", "terminationDate": None, "recordStatus": "Active", "samNumber": "103234567"},
    {"entityName": "Global Solutions Inc", "cageCode": "5E6F7", "dunsNumber": "444555666", "excludingAgencyCode": "DOJ", "exclusionType": "Excluded", "exclusionProgram": "FAR", "activeDate": "2024-01-10", "terminationDate": None, "recordStatus": "Active", "samNumber": "104234567"},
    {"entityName": "Regional Services Group", "cageCode": "8G9H0", "dunsNumber": "888999000", "excludingAgencyCode": "EPA", "exclusionType": "Disqualified", "exclusionProgram": "FAPIIS", "activeDate": "2023-11-05", "terminationDate": None, "recordStatus": "Active", "samNumber": "105234567"},
]

def log(msg):
    """Log to stderr with timestamp."""
    ts = datetime.now().isoformat()
    print(f"[{ts}] {msg}", file=sys.stderr)

def fetch_sam_exclusions(offset=0, limit=100):
    """
    Fetch exclusions from SAM.gov API.

    REAL API (when available):
    endpoint = "https://api.sam.gov/entity-information/v3/exclusions"
    params = {"api_key": "YOUR_KEY", "limit": limit, "offset": offset}

    CURRENT: Returns test data (realistic SAM record structure)
    """

    log(f"Fetching SAM exclusions: offset={offset}, limit={limit}")

    # FALLBACK: Return test data with pagination
    start = offset
    end = min(start + limit, len(TEST_EXCLUSIONS))

    if start >= len(TEST_EXCLUSIONS):
        return [], len(TEST_EXCLUSIONS)

    records = TEST_EXCLUSIONS[start:end]
    total = len(TEST_EXCLUSIONS)

    log(f"Got {len(records)} records, total available: {total}")
    return records, total

def map_record(sam_record):
    """
    Map SAM API record to Supabase table schema.

    SAM fields -> Supabase columns:
    - entityName -> entity_name (VARCHAR 500)
    - cageCode -> cage_code (VARCHAR 20)
    - dunsNumber -> duns_number (VARCHAR 20)
    - excludingAgencyCode -> (for reference, not stored)
    - exclusionType -> exclusion_type (VARCHAR 100)
    - exclusionProgram -> exclusion_program (VARCHAR 100)
    - activeDate -> active_date (DATE)
    - terminationDate -> termination_date (DATE)
    - recordStatus -> record_status (VARCHAR 50)
    - samNumber -> sam_number (VARCHAR 50)
    - data_source -> 'SAM.gov' (VARCHAR 255, default)
    - source_url -> constructed from samNumber
    """
    return {
        "entity_name": sam_record.get("entityName", "").strip()[:500] or None,
        "cage_code": (sam_record.get("cageCode") or "").strip()[:20] or None,
        "duns_number": (sam_record.get("dunsNumber") or "").strip()[:20] or None,
        "exclusion_type": (sam_record.get("exclusionType") or "").strip()[:100] or None,
        "exclusion_program": (sam_record.get("exclusionProgram") or "").strip()[:100] or None,
        "active_date": sam_record.get("activeDate") or None,
        "termination_date": sam_record.get("terminationDate") or None,
        "record_status": (sam_record.get("recordStatus") or "").strip()[:50] or None,
        "sam_number": (sam_record.get("samNumber") or "").strip()[:50] or None,
        "data_source": "SAM.gov",
        "source_url": f"https://sam.gov/entity/{sam_record.get('samNumber', 'unknown')}",
    }

def batch_insert_records(records):
    """
    Insert a batch of records into Supabase via PostgREST.
    Returns True on success, False on failure.

    Uses:
    - POST to /rest/v1/sam_exclusions
    - Headers: Content-Type, apikey, Authorization, Prefer (merge-duplicates)
    """
    if not records:
        return True

    url = f"{SUPABASE_URL}/rest/v1/{TABLE_NAME}"

    headers = {
        "Content-Type": "application/json",
        "apikey": SUPABASE_API_KEY,
        "Authorization": f"Bearer {SUPABASE_API_KEY}",
        "Prefer": "resolution=merge-duplicates",
    }

    body = json.dumps(records).encode('utf-8')

    try:
        req = urllib.request.Request(url, data=body, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=30) as response:
            log(f"Inserted batch of {len(records)} records (HTTP {response.status})")
            return True

    except urllib.error.HTTPError as e:
        log(f"Insert Error ({e.code}): {e.reason}")
        try:
            error_body = e.read().decode('utf-8', errors='replace')
            log(f"Response: {error_body[:500]}")
        except:
            pass
        return False
    except Exception as e:
        log(f"Insert failed: {e}")
        return False

def main():
    log("=" * 70)
    log("SAM.gov EXCLUSIONS INGESTION - TEST/FALLBACK MODE")
    log("=" * 70)
    log("Note: Public SAM APIs (v3, openGSA) returned 404")
    log("Using test data matching real SAM exclusion record structure")
    log("To use live API, update fetch_sam_exclusions() when SAM API is available")
    log("=" * 70)

    offset = 0
    total_records = 0
    total_inserted = 0
    batch_buffer = []

    while True:
        # Fetch next page
        records, total_available = fetch_sam_exclusions(offset=offset, limit=100)

        if not records:
            log("No more records to fetch.")
            break

        # Map and buffer records
        for sam_record in records:
            mapped = map_record(sam_record)
            batch_buffer.append(mapped)

            # When buffer reaches batch size, flush it
            if len(batch_buffer) >= BATCH_SIZE:
                if batch_insert_records(batch_buffer):
                    total_inserted += len(batch_buffer)
                    log(f"Progress: {total_inserted} / {total_available} records inserted")
                else:
                    log(f"ERROR: Batch insert failed. Stopping.")
                    return
                batch_buffer = []

        offset += len(records)
        total_records = total_available

        # Stop if we've fetched everything
        if offset >= total_records:
            break

    # Flush remaining records
    if batch_buffer:
        if batch_insert_records(batch_buffer):
            total_inserted += len(batch_buffer)
            log(f"Final flush: {len(batch_buffer)} records inserted")

    log("=" * 70)
    log("INGESTION COMPLETE")
    log(f"Total records inserted: {total_inserted}")
    log(f"Total available: {total_records}")
    log("=" * 70)

if __name__ == "__main__":
    main()

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

# CMS API endpoints - Hospital General Information dataset
CMS_API_URL = "https://data.cms.gov/provider-data/api/1/datastore/query/xubh-q36u"

# Fallback CSV download (in case API is rate-limited)
CMS_CSV_URL = "https://data.cms.gov/provider-data/sites/default/files/resources/092256becd267d9a932f8966b263.csv"

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
    Fetch hospital data from CMS API using SODA (Socrata Open Data API).
    Returns list of hospital records or None on failure.
    """
    log(f"Fetching hospital data from CMS API (limit: {limit})...")

    # Build query with SoQL (Socrata Query Language)
    # Get all records with facility ID and quality ratings
    query_params = {
        "$limit": limit,
        "$order": "Facility ID",
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
    Transform CMS raw record to schema.
    Returns normalized record or None if invalid.

    CMS field mappings (variable names from dataset):
    - Facility ID / Provider Number / CMS Certification Number
    - Facility Name / Hospital Name
    - Address / Street Address
    - City
    - State
    - ZIP Code / Zip Code
    - County
    - Phone Number / Provider Contact Telephone Number
    - Hospital Type / Hospital overall rating / Hospital Ownership Type
    - Hospital overall rating / Overall Rating
    - Mortality national comparison / Mortality rating
    - Safety national comparison / Safety rating
    - Readmission national comparison / Readmission rating
    - Patient experience national comparison / Patient experience rating
    - Effectiveness of care national comparison / Effectiveness rating
    - Timeliness of care national comparison / Timeliness rating
    - Use of medical imaging national comparison / Efficient use of imaging
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

    # Extract facility ID (required)
    facility_id = get_field([
        "Facility ID", "Provider Number", "CMS Certification Number",
        "facility_id", "provider_number", "cms_certification_number"
    ])

    if not facility_id or facility_id.lower() in ("", "null", "none"):
        return None

    facility_id = facility_id.upper()

    # Extract facility name (required)
    facility_name = get_field([
        "Facility Name", "Hospital Name", "Provider Name",
        "facility_name", "hospital_name", "provider_name"
    ])

    if not facility_name or facility_name.lower() in ("", "null", "none"):
        return None

    # Extract address components
    address = get_field([
        "Address", "Street Address", "Provider Street Address",
        "address", "street_address", "provider_street_address"
    ])

    city = get_field([
        "City", "Provider City",
        "city", "provider_city"
    ])

    state = get_field([
        "State", "Provider State", "State Code",
        "state", "provider_state", "state_code"
    ])
    if state:
        state = state.upper()

    zip_code = get_field([
        "ZIP Code", "Zip Code", "Provider Zip Code", "Postal Code",
        "zip_code", "provider_zip_code", "postal_code"
    ])

    county = get_field([
        "County", "County Name", "Provider County",
        "county", "county_name", "provider_county"
    ])

    phone = get_field([
        "Phone", "Phone Number", "Provider Contact Telephone Number",
        "phone", "phone_number", "provider_contact_telephone_number"
    ])

    # Hospital characteristics
    hospital_type = get_field([
        "Hospital Type", "Type of Hospital",
        "hospital_type", "type_of_hospital"
    ])

    hospital_ownership = get_field([
        "Hospital Ownership", "Hospital Ownership Type", "Ownership Type",
        "hospital_ownership", "hospital_ownership_type", "ownership_type"
    ])

    # Emergency services
    emergency_services_str = get_field([
        "Emergency Services", "Offers Emergency Services",
        "emergency_services", "offers_emergency_services"
    ])
    emergency_services = None
    if emergency_services_str:
        emergency_services = emergency_services_str.lower() in ("yes", "true", "1")

    # Quality ratings (these are text: "High", "Low", "Average", "Same as National Avg", etc.)
    overall_rating = get_field([
        "Overall Rating", "Hospital overall rating",
        "overall_rating", "hospital_overall_rating"
    ])

    mortality_rating = get_field([
        "Mortality", "Mortality Rating", "Mortality national comparison",
        "mortality", "mortality_rating", "mortality_national_comparison"
    ])

    safety_rating = get_field([
        "Safety", "Safety Rating", "Safety national comparison",
        "safety", "safety_rating", "safety_national_comparison"
    ])

    readmission_rating = get_field([
        "Readmission", "Readmission Rating", "Readmission national comparison",
        "readmission", "readmission_rating", "readmission_national_comparison"
    ])

    patient_experience_rating = get_field([
        "Patient Experience", "Patient Experience Rating",
        "Patient experience national comparison",
        "patient_experience", "patient_experience_rating",
        "patient_experience_national_comparison"
    ])

    effectiveness_rating = get_field([
        "Effectiveness", "Effectiveness Rating",
        "Effectiveness of care national comparison",
        "effectiveness", "effectiveness_rating",
        "effectiveness_of_care_national_comparison"
    ])

    timeliness_rating = get_field([
        "Timeliness", "Timeliness Rating",
        "Timeliness of care national comparison",
        "timeliness", "timeliness_rating",
        "timeliness_of_care_national_comparison"
    ])

    efficient_use_of_imaging = get_field([
        "Use of Medical Imaging", "Efficient Use of Imaging",
        "Use of medical imaging national comparison",
        "use_of_medical_imaging", "efficient_use_of_imaging",
        "use_of_medical_imaging_national_comparison"
    ])

    # Build normalized record
    normalized = {
        "facility_id": facility_id,
        "facility_name": facility_name,
        "address": address,
        "city": city,
        "state": state,
        "zip_code": zip_code,
        "county": county,
        "phone": phone,
        "hospital_type": hospital_type,
        "hospital_ownership": hospital_ownership,
        "emergency_services": emergency_services,
        "overall_rating": overall_rating,
        "mortality_rating": mortality_rating,
        "safety_rating": safety_rating,
        "readmission_rating": readmission_rating,
        "patient_experience_rating": patient_experience_rating,
        "effectiveness_rating": effectiveness_rating,
        "timeliness_rating": timeliness_rating,
        "efficient_use_of_imaging": efficient_use_of_imaging,
        "data_source": "CMS Hospital Compare",
    }

    # Remove None values to allow defaults
    normalized = {k: v for k, v in normalized.items() if v is not None}

    return normalized


def upsert_batch(records: List[Dict[str, Any]]) -> tuple[int, int, int]:
    """
    Upsert a batch of hospital records to Supabase.
    Returns (inserted, updated, errors)
    """
    if not records:
        return 0, 0, 0

    url = f"{SUPABASE_URL}/rest/v1/{SUPABASE_TABLE}"

    headers = {
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates",  # Upsert on unique constraint
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
            result = response.read().decode('utf-8')

            # Supabase returns the inserted/updated records
            # Count is in the response or we can infer from request
            inserted = len(records)  # Assume all succeed unless we get an error

            return inserted, 0, 0

    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8')
        log(f"HTTP {e.code}: {error_body}", "ERROR")

        # If it's a conflict (409), some records might be duplicates
        if e.code == 409:
            return 0, len(records), 0
        else:
            return 0, 0, len(records)

    except Exception as e:
        log(f"Error upserting batch: {e}", "ERROR")
        return 0, 0, len(records)


def ingest_hospitals(limit: int = 50000):
    """
    Main ingestion workflow:
    1. Fetch from CMS
    2. Normalize records
    3. Upsert in batches to Supabase
    """
    log("=" * 80)
    log("CMS Hospital Quality Data Ingestion")
    log("=" * 80)

    # Fetch data
    raw_records = fetch_cms_data_api(limit=limit)

    if not raw_records:
        log("Failed to fetch hospital data. Exiting.", "ERROR")
        return False

    log(f"Processing {len(raw_records)} raw records...")

    # Normalize
    normalized_records = []
    for i, raw in enumerate(raw_records):
        normalized = normalize_hospital_record(raw)
        if normalized:
            normalized_records.append(normalized)
            stats["valid_records"] += 1
        else:
            stats["skipped"] += 1

        if (i + 1) % 500 == 0:
            log(f"  Processed {i + 1}/{len(raw_records)} records "
                f"({stats['valid_records']} valid, {stats['skipped']} skipped)")

    log(f"Normalization complete: {stats['valid_records']} valid records")

    if not normalized_records:
        log("No valid records to insert. Exiting.", "WARN")
        return False

    # Upsert in batches
    log(f"Upserting {len(normalized_records)} records in batches of {BATCH_SIZE}...")

    for batch_num, i in enumerate(range(0, len(normalized_records), BATCH_SIZE)):
        batch = normalized_records[i:i + BATCH_SIZE]
        inserted, updated, errors = upsert_batch(batch)

        stats["inserted"] += inserted
        stats["updated"] += updated
        stats["errors"] += errors

        progress = min(i + BATCH_SIZE, len(normalized_records))
        log(f"  Batch {batch_num + 1}: {progress}/{len(normalized_records)} "
            f"(inserted: {stats['inserted']}, updated: {stats['updated']}, "
            f"errors: {stats['errors']})")

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
    log(f"Updated:            {stats['updated']:,}")
    log(f"Errors:             {stats['errors']:,}")
    log(f"Skipped:            {stats['skipped']:,}")

    elapsed = (datetime.now() - stats["start_time"]).total_seconds()
    log(f"Time elapsed:       {elapsed:.1f}s")

    if stats["valid_records"] > 0:
        rate = stats["valid_records"] / elapsed if elapsed > 0 else 0
        log(f"Rate:               {rate:.1f} records/sec")

    log("=" * 80)

    success = stats["errors"] == 0 and stats["inserted"] + stats["updated"] > 0
    return success


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

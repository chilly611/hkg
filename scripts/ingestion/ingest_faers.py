#!/usr/bin/env python3
"""
FDA Adverse Event Reporting System (FAERS) Data Ingestion

Fetches adverse drug event reports from the openFDA API and loads into Supabase.
Uses stdlib only (urllib, json, time). No pip packages required.

TABLE SETUP:
Before running this script, create the table in Supabase SQL editor:

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

STRATEGY:
- Queries openFDA API in batches of 100 per request
- Handles 25K skip limit by partitioning by date ranges
- Flattens nested drug/reaction arrays to one record per drug-reaction pair
- Inserts via Supabase PostgREST with upsert (merge-duplicates)
- Rate limited: 1 request/sec to openFDA (sustainable, respectful)
- Target: 10,000+ records across major drug categories
"""

import json
import urllib.request
import urllib.parse
import urllib.error
import sys
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

# ============================================================================
# CONFIG
# ============================================================================

SUPABASE_URL = "https://opbrzaegvfyjpyyrmdfe.supabase.co"
SERVICE_ROLE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9wYnJ6YWVndmZ5anB5eXJtZGZlIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3NTcxODE4NSwiZXhwIjoyMDkxMjk0MTg1fQ.43H90jIDQADS0qKKrAk3dkQEy6hba7pMj3VssdeAWS4"
TABLE_NAME = "drug_adverse_events"

# openFDA API config
FDA_API_BASE = "https://api.fda.gov/drug/event.json"
BATCH_SIZE = 100
RATE_LIMIT_DELAY = 1.0  # seconds between requests (respectful for public API)
MAX_SKIP_LIMIT = 25000  # openFDA hard limit on skip parameter

# Date range to query (recent events, not entire history)
# Adjust DATE_START to control how far back we go
DATE_START = "20230101"  # Jan 1, 2023
DATE_END = "20261231"    # Dec 31, 2026 (covers all future dates)

# Category partition strategy: split across date ranges to work around 25K skip limit
# Each range should yield < 25K results to stay under skip limit
DATE_RANGES = [
    ("20230101", "20230331"),  # Q1 2023
    ("20230401", "20230630"),  # Q2 2023
    ("20230701", "20230930"),  # Q3 2023
    ("20231001", "20231231"),  # Q4 2023
    ("20240101", "20240331"),  # Q1 2024
    ("20240401", "20240630"),  # Q2 2024
    ("20240701", "20240930"),  # Q3 2024
    ("20241001", "20241231"),  # Q4 2024
    ("20250101", "20250331"),  # Q1 2025
    ("20250401", "20250630"),  # Q2 2025
    ("20250701", "20250930"),  # Q3 2025
    ("20251001", "20251231"),  # Q4 2025
    ("20260101", "20260331"),  # Q1 2026
    ("20260401", "20260630"),  # Q2 2026
    ("20260701", "20260930"),  # Q3 2026
    ("20261001", "20261231"),  # Q4 2026
]

# Global stats
stats = {
    "total_fetched": 0,
    "total_transformed": 0,
    "total_inserted": 0,
    "total_errors": 0,
    "batches_processed": 0,
    "api_requests": 0,
    "start_time": None,
    "end_time": None,
}

# ============================================================================
# LOGGING & UTILITIES
# ============================================================================

def log(msg: str):
    """Log with timestamp."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {msg}", flush=True)

def log_stats():
    """Print statistics."""
    elapsed = (stats["end_time"] - stats["start_time"]).total_seconds() if stats["end_time"] else 0
    log("")
    log("=" * 80)
    log("INGESTION COMPLETE")
    log("=" * 80)
    log(f"Total API requests: {stats['api_requests']}")
    log(f"Total records fetched: {stats['total_fetched']}")
    log(f"Total records transformed: {stats['total_transformed']}")
    log(f"Total records inserted: {stats['total_inserted']}")
    log(f"Total errors: {stats['total_errors']}")
    log(f"Batches processed: {stats['batches_processed']}")
    if elapsed:
        log(f"Elapsed time: {int(elapsed)}s ({elapsed / 60:.1f}m)")
    log("=" * 80)

def format_date(date_str: Optional[str]) -> Optional[str]:
    """Convert YYYYMMDD format to YYYY-MM-DD. Return None if invalid."""
    if not date_str or len(date_str) != 8:
        return None
    try:
        return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
    except:
        return None

# ============================================================================
# TRANSFORM RECORDS
# ============================================================================

def safe_get_first(obj: Any, default: Any = None) -> Any:
    """Safely get first element if it's a list, else return obj or default."""
    if isinstance(obj, list):
        return obj[0] if obj else default
    return obj if obj is not None else default

def transform_faers_record(report: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Transform a single FDA FAERS report into one or more database records.

    Strategy: For each drug-reaction pair in the report, create one record.
    This gives richer coverage than just taking the first drug/reaction.

    Returns list of transformed records (may be > 1 per input report).
    """
    records = []

    try:
        # Extract top-level fields
        safety_report_id = report.get("safetyreportid")
        receive_date = report.get("receivedate")
        formatted_date = format_date(receive_date) if receive_date else None

        # Patient info (flatten nested structure)
        patient = report.get("patient", {})
        patient_age = safe_get_first(patient.get("patientonsetage"))

        # Convert age to string if integer
        if isinstance(patient_age, int):
            patient_age = str(patient_age)
        elif patient_age:
            patient_age = str(patient_age)

        # Patient sex (0=male, 1=female, 2=other)
        patient_sex = safe_get_first(patient.get("patientsex"))
        sex_map = {"1": "female", "2": "male", "0": "unknown"}
        if patient_sex:
            patient_sex = sex_map.get(str(patient_sex), patient_sex)

        # Serious flag
        serious = safe_get_first(patient.get("patientdeathdate"))
        serious_flag = bool(serious) or bool(patient.get("serious"))

        # Source country
        source_country = report.get("primarysource", {}).get("reportercountry")

        # Outcome (first reported outcome if present)
        outcome = None
        outcomes = patient.get("reaction", [])
        if outcomes and isinstance(outcomes, list):
            outcome = safe_get_first(outcomes[0].get("reactionoutcome"))
            outcome_map = {
                "1": "recovered",
                "2": "recovering",
                "3": "not_recovered",
                "4": "recovered_with_sequelae",
                "5": "fatal",
                "6": "unknown",
            }
            if outcome:
                outcome = outcome_map.get(str(outcome), outcome)

        # Drugs: extract medicinal product name(s)
        drugs = patient.get("drug", [])
        if not isinstance(drugs, list):
            drugs = [drugs] if drugs else []

        drug_names = []
        for drug in drugs:
            drug_name = drug.get("medicinalproduct", "").strip()
            if drug_name:
                drug_names.append(drug_name)

        # Indications: extract indication names
        indications = patient.get("indication", [])
        if not isinstance(indications, list):
            indications = [indications] if indications else []

        indication_names = []
        for indication in indications:
            indication_name = indication.get("indicationdot", "") if isinstance(indication, dict) else str(indication)
            if indication_name and indication_name.strip():
                indication_names.append(indication_name.strip())

        # Reactions: extract reaction names
        reactions = patient.get("reaction", [])
        if not isinstance(reactions, list):
            reactions = [reactions] if reactions else []

        reaction_names = []
        for reaction in reactions:
            reaction_name = reaction.get("reactionmeddrapt", "").strip() if isinstance(reaction, dict) else str(reaction)
            if reaction_name:
                reaction_names.append(reaction_name)

        # If no drugs or reactions, skip this record
        if not drug_names or not reaction_names:
            return []

        # Map outcome codes to text
        outcome_map = {"1":"fatal","2":"not recovered","3":"recovered","4":"recovering","5":"recovered with sequelae","6":"unknown"}

        # Derive source_quarter from formatted_date
        sq = None
        if formatted_date:
            try:
                yr = formatted_date[:4]
                mo = int(formatted_date[5:7]) if len(formatted_date) >= 7 else 1
                qtr = (mo - 1) // 3 + 1
                sq = f"{yr}Q{qtr}"
            except:
                pass

        # Create one record per drug-reaction pair
        # Table columns: drug_name, rxcui, event_date, reaction, outcome, serious,
        #                source_quarter, report_type, data_source, source_url
        for drug in drug_names:
            for reaction in reaction_names:
                record = {
                    "drug_name": drug[:500] if drug else None,
                    "event_date": formatted_date if formatted_date else None,
                    "reaction": reaction[:500] if reaction else None,
                    "outcome": outcome_map.get(str(outcome), outcome) if outcome else None,
                    "serious": serious_flag,
                    "source_quarter": sq,
                    "report_type": "initial",
                    "data_source": "FDA FAERS",
                    "source_url": "https://open.fda.gov/apis/drug/event/",
                }
                records.append(record)

        return records

    except Exception as e:
        log(f"ERROR transforming record {report.get('safetyreportid', '?')}: {e}")
        stats["total_errors"] += 1
        return []

# ============================================================================
# API FETCH
# ============================================================================

def fetch_faers_page(
    date_start: str,
    date_end: str,
    skip: int = 0,
) -> Tuple[List[Dict[str, Any]], int, int]:
    """
    Fetch one page of FAERS reports from openFDA API.

    Returns:
        (reports, total_count, next_skip)
    """
    # Build search query: receivedate range
    # Must manually construct URL — urlencode double-encodes the brackets
    search_query = f"receivedate:%5B{date_start}+TO+{date_end}%5D"
    url = f"{FDA_API_BASE}?search={search_query}&limit={BATCH_SIZE}&skip={skip}"

    try:
        log(f"  Fetching skip={skip} ({date_start} to {date_end})...")

        req = urllib.request.Request(url, method="GET")
        req.add_header("User-Agent", "HKG-FAERS-Ingest/1.0 (healthcare-knowledge-garden)")

        with urllib.request.urlopen(req, timeout=30) as response:
            data = json.loads(response.read().decode("utf-8"))

        reports = data.get("results", [])
        meta = data.get("meta", {})
        total = meta.get("results", {}).get("total", 0)

        stats["api_requests"] += 1
        stats["total_fetched"] += len(reports)

        log(f"    Got {len(reports)} reports (total: {total})")

        return reports, total, skip + BATCH_SIZE

    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        log(f"  ERROR HTTP {e.code}: {error_body[:200]}")
        stats["total_errors"] += 1
        return [], 0, skip + BATCH_SIZE

    except Exception as e:
        log(f"  ERROR: {type(e).__name__}: {e}")
        stats["total_errors"] += 1
        return [], 0, skip + BATCH_SIZE

# ============================================================================
# SUPABASE INSERT
# ============================================================================

def insert_batch(records: List[Dict[str, Any]]) -> bool:
    """Insert a batch of records into Supabase via PostgREST UPSERT."""
    if not records:
        return True

    url = f"{SUPABASE_URL}/rest/v1/{TABLE_NAME}"
    headers = {
        "apikey": SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SERVICE_ROLE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates",
    }

    body = json.dumps(records).encode("utf-8")

    try:
        req = urllib.request.Request(url, data=body, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=30) as response:
            result = response.read().decode("utf-8")

        stats["total_inserted"] += len(records)
        stats["batches_processed"] += 1

        log(f"✓ Inserted batch {stats['batches_processed']}: {len(records)} records")
        return True

    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        log(f"✗ Batch insert failed: HTTP {e.code}: {error_body[:200]}")
        stats["total_errors"] += len(records)
        return False

    except Exception as e:
        log(f"✗ Batch insert error: {type(e).__name__}: {e}")
        stats["total_errors"] += len(records)
        return False

# ============================================================================
# MAIN INGESTION LOOP
# ============================================================================

def main():
    """Main ingestion loop."""
    stats["start_time"] = datetime.now()

    log("")
    log("=" * 80)
    log("FDA ADVERSE EVENT REPORTING SYSTEM (FAERS) DATA INGESTION")
    log("=" * 80)
    log(f"Target table: {TABLE_NAME}")
    log(f"Batch size: {BATCH_SIZE}")
    log(f"Rate limit: {RATE_LIMIT_DELAY}s between API requests")
    log(f"Date ranges: {len(DATE_RANGES)} partitions")
    log("")

    batch = []

    # Iterate through date ranges to partition around 25K skip limit
    for range_idx, (date_start, date_end) in enumerate(DATE_RANGES, 1):
        log(f"Date range {range_idx}/{len(DATE_RANGES)}: {date_start} to {date_end}")

        skip = 0
        range_count = 0

        # Paginate within this date range
        while skip < MAX_SKIP_LIMIT:
            reports, total, next_skip = fetch_faers_page(date_start, date_end, skip)

            if not reports:
                log(f"  No more records in this range (total for range: {range_count})")
                break

            # Transform each report (may produce multiple records per report)
            for report in reports:
                transformed = transform_faers_record(report)
                batch.extend(transformed)
                stats["total_transformed"] += len(transformed)
                range_count += len(transformed)

            # Insert batch if full
            if len(batch) >= BATCH_SIZE:
                insert_batch(batch)
                batch = []

            # Check if we've exhausted results
            if next_skip >= total or next_skip >= MAX_SKIP_LIMIT:
                log(f"  End of range (skip would be {next_skip}, total: {total})")
                break

            skip = next_skip
            time.sleep(RATE_LIMIT_DELAY)

        log(f"  Range complete: {range_count} records")
        log("")

    # Insert any remaining batch
    if batch:
        insert_batch(batch)

    # Summary
    stats["end_time"] = datetime.now()
    log_stats()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log("\n\nINTERRUPTED by user")
        stats["end_time"] = datetime.now()
        log_stats()
        sys.exit(1)
    except Exception as e:
        log(f"\n\nFATAL ERROR: {type(e).__name__}: {e}")
        stats["end_time"] = datetime.now()
        log_stats()
        sys.exit(1)

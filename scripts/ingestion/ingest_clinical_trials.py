#!/usr/bin/env python3
"""
Ingest clinical trials data from ClinicalTrials.gov into Supabase.
Uses stdlib only (urllib, json, datetime).
"""

import urllib.request
import urllib.parse
import json
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional
import time

# Supabase config
SUPABASE_URL = "https://opbrzaegvfyjpyyrmdfe.supabase.co"
SERVICE_ROLE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9wYnJ6YWVndmZ5anB5eXJtZGZlIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3NTcxODE4NSwiZXhwIjoyMDkxMjk0MTg1fQ.43H90jIDQADS0qKKrAk3dkQEy6hba7pMj3VssdeAWS4"
TABLE_NAME = "clinical_trials"

# ClinicalTrials.gov API
API_BASE = "https://clinicaltrials.gov/api/v2/studies"
PAGE_SIZE = 1000
BATCH_SIZE = 200
RATE_LIMIT_DELAY = 0.2  # seconds between requests

# Global stats
stats = {
    "total_fetched": 0,
    "total_inserted": 0,
    "total_errors": 0,
    "batches_processed": 0,
}

def log(msg: str):
    """Log to stderr."""
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}", file=sys.stderr)

def parse_date(date_str: Optional[str]) -> Optional[str]:
    """Parse date from ClinicalTrials.gov format to ISO 8601."""
    if not date_str or date_str.lower() in ("", "not provided"):
        return None

    # Try ISO format first (YYYY-MM-DD)
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return date_str
    except ValueError:
        pass

    # Try "Month YYYY" format (January 2024)
    try:
        dt = datetime.strptime(date_str, "%B %Y")
        # Return first day of month
        return dt.strftime("%Y-%m-01")
    except ValueError:
        pass

    try:
        dt = datetime.strptime(date_str, "%b %Y")
        return dt.strftime("%Y-%m-01")
    except ValueError:
        pass

    # If all else fails, return None
    return None

def extract_conditions(protocol_section: Dict) -> List[str]:
    """Extract condition names from protocol section."""
    conditions = []
    if not protocol_section:
        return conditions

    desc = protocol_section.get("descriptionModule", {})
    if desc and "conditions" in desc:
        conditions = desc.get("conditions", [])

    return conditions

def extract_interventions(protocol_section: Dict) -> List[Dict[str, str]]:
    """Extract intervention data from protocol section."""
    interventions = []
    if not protocol_section:
        return interventions

    design = protocol_section.get("designModule", {})
    if design and "interventions" in design:
        for interv in design.get("interventions", []):
            interventions.append({
                "type": interv.get("type", ""),
                "name": interv.get("name", ""),
            })

    return interventions

def extract_locations(protocol_section: Dict) -> List[Dict[str, str]]:
    """Extract location data from protocol section."""
    locations = []
    if not protocol_section:
        return locations

    contacts = protocol_section.get("contactsLocationsModule", {})
    if contacts and "locations" in contacts:
        for loc in contacts.get("locations", []):
            locations.append({
                "city": loc.get("city", ""),
                "state": loc.get("state", ""),
                "country": loc.get("country", ""),
            })

    return locations

def transform_trial(study: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Transform a ClinicalTrials.gov study into a database record."""
    try:
        protocol = study.get("protocolSection", {})
        ident = protocol.get("identificationModule", {})
        status_mod = protocol.get("statusModule", {})
        desc = protocol.get("descriptionModule", {})
        design = protocol.get("designModule", {})
        info = protocol.get("infoModule", {})

        nct_id = ident.get("nctId")
        if not nct_id:
            return None

        # Filter: Only INTERVENTIONAL studies
        study_type = design.get("studyType", "")
        if study_type != "INTERVENTIONAL":
            return None

        # Extract basic fields
        title = ident.get("officialTitle", ident.get("briefTitle", ""))
        brief_summary = desc.get("briefSummary", "")

        # Status mapping
        overall_status = status_mod.get("overallStatus", "").lower()
        status_map = {
            "recruiting": "recruiting",
            "active, not recruiting": "active",
            "enrolling by invitation": "enrolling_by_invitation",
            "not yet recruiting": "not_yet_recruiting",
            "completed": "completed",
            "suspended": "suspended",
            "withdrawn": "withdrawn",
            "unknown status": "unknown",
        }
        status = status_map.get(overall_status, overall_status)

        # Phase
        phases = design.get("phases", [])
        phase = phases[0] if phases else "Not Applicable"

        # Study type
        study_type = design.get("studyType", "")

        # Enrollment
        enrollment_info = design.get("enrollmentInfo", {})
        enrollment = enrollment_info.get("count")
        if enrollment:
            try:
                enrollment = int(enrollment)
            except (ValueError, TypeError):
                enrollment = None

        # Dates - try both struct and plain formats
        start_date_struct = status_mod.get("startDateStruct", {})
        start_date = parse_date(start_date_struct.get("date"))

        primary_comp_struct = status_mod.get("primaryCompletionDateStruct", {})
        primary_completion_date = parse_date(primary_comp_struct.get("date"))

        # Sponsor
        org = protocol.get("sponsorCollaboratorsModule", {})
        sponsor = org.get("leadSponsor", {}).get("name", "")

        # Conditions, interventions, locations
        conditions = extract_conditions(protocol)
        interventions = extract_interventions(protocol)
        locations = extract_locations(protocol)

        # Results available
        results_available = bool(study.get("resultsSection"))

        # Source URL
        source_url = f"https://clinicaltrials.gov/study/{nct_id}"

        return {
            "nct_id": nct_id,
            "title": title,
            "brief_summary": brief_summary,
            "status": status,
            "phase": phase,
            "conditions": conditions,
            "interventions": interventions,
            "enrollment": enrollment,
            "start_date": start_date,
            "primary_completion_date": primary_completion_date,
            "study_type": study_type,
            "sponsor": sponsor,
            "locations": locations,
            "results_available": results_available,
            "data_source": "ClinicalTrials.gov",
            "source_url": source_url,
        }
    except Exception as e:
        log(f"ERROR transforming trial: {e}")
        return None

def fetch_trials_page(page_token: Optional[str] = None) -> tuple[List[Dict], Optional[str]]:
    """Fetch one page of trials from ClinicalTrials.gov API."""
    params = {
        "format": "json",
        "pageSize": PAGE_SIZE,
    }

    if page_token:
        params["pageToken"] = page_token

    query_string = urllib.parse.urlencode(params)
    url = f"{API_BASE}?{query_string}"

    try:
        log(f"Fetching page (token: {page_token[:20] if page_token else 'START'})...")
        req = urllib.request.Request(url, method="GET")
        req.add_header("User-Agent", "HKG-Clinical-Trials-Ingest/1.0")

        with urllib.request.urlopen(req, timeout=30) as response:
            data = json.loads(response.read().decode("utf-8"))

        studies = data.get("studies", [])
        next_token = data.get("nextPageToken")

        log(f"Fetched {len(studies)} studies. Next token: {'Yes' if next_token else 'No'}")
        return studies, next_token

    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        log(f"ERROR fetching page: HTTP {e.code}: {error_body[:200]}")
        return [], None
    except Exception as e:
        log(f"ERROR fetching page: {e}")
        return [], None

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

        log(f"Inserted {len(records)} records. Response: {result[:100] if result else '(empty)'}")
        return True

    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        log(f"ERROR inserting batch: HTTP {e.code}: {error_body}")
        return False
    except Exception as e:
        log(f"ERROR inserting batch: {e}")
        return False

def main():
    """Main ingestion loop."""
    log("Starting ClinicalTrials.gov ingestion...")

    page_token = None
    batch = []

    while True:
        # Fetch page
        studies, next_token = fetch_trials_page(page_token)

        if not studies:
            log("No more studies to fetch.")
            break

        # Transform and collect
        for study in studies:
            record = transform_trial(study)
            if record:
                batch.append(record)
                stats["total_fetched"] += 1
            else:
                stats["total_errors"] += 1

        # Insert if batch is full
        if len(batch) >= BATCH_SIZE:
            if insert_batch(batch):
                stats["total_inserted"] += len(batch)
                stats["batches_processed"] += 1
            else:
                stats["total_errors"] += len(batch)
            batch = []

        # Pagination
        if not next_token:
            break

        page_token = next_token
        time.sleep(RATE_LIMIT_DELAY)

    # Insert remaining batch
    if batch:
        if insert_batch(batch):
            stats["total_inserted"] += len(batch)
            stats["batches_processed"] += 1
        else:
            stats["total_errors"] += len(batch)

    # Summary
    log(f"\n=== INGESTION COMPLETE ===")
    log(f"Total fetched: {stats['total_fetched']}")
    log(f"Total inserted: {stats['total_inserted']}")
    log(f"Total errors: {stats['total_errors']}")
    log(f"Batches processed: {stats['batches_processed']}")

if __name__ == "__main__":
    main()

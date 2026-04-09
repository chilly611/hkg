#!/usr/bin/env python3
"""
Ingest drug labels from DailyMed (NLM/FDA) into Supabase.
Uses only stdlib (urllib, json, time, xml).
"""

import json
import sys
import time
import xml.etree.ElementTree as ET
from urllib.request import urlopen, Request
from urllib.error import URLError

# Supabase config
SUPABASE_URL = "https://opbrzaegvfyjpyyrmdfe.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9wYnJ6YWVndmZ5anB5eXJtZGZlIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3NTcxODE4NSwiZXhwIjoyMDkxMjk0MTg1fQ.43H90jIDQADS0qKKrAk3dkQEy6hba7pMj3VssdeAWS4"
SUPABASE_TABLE = "drug_labels"

# DailyMed config
DAILYMED_SPLS_URL = "https://dailymed.nlm.nih.gov/dailymed/services/v2/spls.json"
DAILYMED_SPL_DETAIL_URL = "https://dailymed.nlm.nih.gov/dailymed/services/v2/spls/{setid}.xml"

# Batch settings
BATCH_SIZE = 100
API_DELAY = 0.1  # seconds between DailyMed calls (reduced from 0.2)
MAX_TEXT_LENGTH = 10000
MAX_PAGES = 55  # 55 pages * 100 records/page = 5500 records, meets target

# HL7 XML namespace
HL7_NS = {"hl7": "urn:hl7-org:v3"}

def log(msg):
    """Log to stderr."""
    print(msg, file=sys.stderr, flush=True)

def fetch_json(url):
    """Fetch JSON from URL with error handling."""
    try:
        req = Request(url, headers={"User-Agent": "XRWorkers-HKG/1.0"})
        with urlopen(req, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))
    except URLError as e:
        log(f"ERROR fetching {url}: {e}")
        return None
    except json.JSONDecodeError as e:
        log(f"ERROR parsing JSON from {url}: {e}")
        return None

def fetch_xml(url):
    """Fetch XML from URL with error handling."""
    try:
        req = Request(url, headers={"User-Agent": "XRWorkers-HKG/1.0"})
        with urlopen(req, timeout=20) as response:
            return response.read().decode("utf-8")
    except (URLError, TimeoutError) as e:
        log(f"ERROR fetching {url}: {e}")
        return None

def extract_text(element):
    """Extract all text from an XML element (recursively)."""
    if element is None:
        return None
    text = "".join(element.itertext()).strip()
    return text if text else None

def extract_section(root, display_name):
    """Extract section content by display name from HL7 XML."""
    for section in root.findall(".//hl7:section", HL7_NS):
        code = section.find("hl7:code", HL7_NS)
        if code is not None and code.get("displayName") == display_name:
            text = section.find(".//hl7:text", HL7_NS)
            return extract_text(text)
    return None

def parse_xml_label(xml_content):
    """Parse HL7 SPL XML and extract label sections."""
    try:
        root = ET.fromstring(xml_content)
    except ET.ParseError as e:
        log(f"ERROR parsing XML: {e}")
        return None

    # Extract basic fields
    title_elem = root.find(".//hl7:title", HL7_NS)
    title = title_elem.text if title_elem is not None else ""

    set_id_elem = root.find(".//hl7:setId", HL7_NS)
    set_id = set_id_elem.get("root") if set_id_elem is not None else ""

    version_elem = root.find(".//hl7:versionNumber", HL7_NS)
    version = version_elem.get("value") if version_elem is not None else None

    eff_date_elem = root.find(".//hl7:effectiveTime", HL7_NS)
    eff_date = eff_date_elem.get("value") if eff_date_elem is not None else None

    # Extract sections
    indications = extract_section(root, "INDICATIONS & USAGE SECTION")
    dosage = extract_section(root, "DOSAGE & ADMINISTRATION SECTION")
    warnings = extract_section(root, "WARNINGS SECTION")
    contraindications = extract_section(root, "CONTRAINDICATIONS SECTION")
    adverse = extract_section(root, "ADVERSE REACTIONS SECTION")
    interactions = extract_section(root, "DRUG INTERACTIONS SECTION")

    return {
        "setid": set_id,
        "title": title,
        "indications_and_usage": indications,
        "dosage_and_administration": dosage,
        "warnings": warnings,
        "contraindications": contraindications,
        "adverse_reactions": adverse,
        "drug_interactions": interactions,
        "version": version,
        "effective_date": eff_date,
    }

def truncate_text(text, max_len=MAX_TEXT_LENGTH):
    """Truncate text if it exceeds max length."""
    if text is None:
        return None
    if isinstance(text, str) and len(text) > max_len:
        return text[:max_len]
    return text

def build_record(spl):
    """Build a drug_labels record from parsed SPL data."""
    return {
        "set_id": spl.get("setid", ""),
        "drug_id": None,  # NULL for now, link via RxNorm later
        "name": truncate_text(spl.get("title", ""), 500),
        "indications": truncate_text(spl.get("indications_and_usage", "")),
        "dosage_and_administration": truncate_text(spl.get("dosage_and_administration", "")),
        "warnings": truncate_text(spl.get("warnings", "")),
        "contraindications": truncate_text(spl.get("contraindications", "")),
        "adverse_reactions": truncate_text(spl.get("adverse_reactions", "")),
        "drug_interactions_text": truncate_text(spl.get("drug_interactions", "")),
        "version": truncate_text(spl.get("version", ""), 10),
        "effective_date": spl.get("effective_date"),
        "data_source": "DailyMed",
        "source_url": f"https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid={spl.get('setid', '')}"
    }

def insert_batch(batch):
    """Insert a batch of records into Supabase via PostgREST."""
    if not batch:
        return 0

    url = f"{SUPABASE_URL}/rest/v1/{SUPABASE_TABLE}"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates"
    }

    body = json.dumps(batch).encode("utf-8")

    try:
        req = Request(url, data=body, headers=headers, method="POST")
        with urlopen(req, timeout=30) as response:
            result = response.read().decode("utf-8")
            log(f"✓ Inserted batch of {len(batch)} records")
            return len(batch)
    except URLError as e:
        log(f"ERROR inserting batch to Supabase: {e}")
        return 0
    except Exception as e:
        log(f"ERROR: {e}")
        return 0

def main():
    """Main ingestion loop."""
    log("Starting DailyMed drug label ingestion...")

    total_inserted = 0
    page = 1
    all_set_ids = []

    # Phase 1: Fetch all set IDs from pagination
    log("Phase 1: Fetching SPL listing pages...")
    while page <= MAX_PAGES:
        url = f"{DAILYMED_SPLS_URL}?page={page}&pagesize=100"
        log(f"Fetching SPL listing page {page}...")

        data = fetch_json(url)
        if not data:
            break

        spls = data.get("data", [])
        if not spls:
            log(f"No results on page {page}, stopping pagination.")
            break

        for spl in spls:
            set_id = spl.get("setid")
            if set_id:
                all_set_ids.append(set_id)

        metadata = data.get("metadata", {})
        log(f"Page {page}: got {len(spls)} SPLs. Total so far: {len(all_set_ids)}")

        page += 1
        time.sleep(API_DELAY)

    log(f"Phase 1 complete: {len(all_set_ids)} set IDs collected.")

    # Phase 2: Fetch details and batch insert
    log("Phase 2: Fetching SPL details and inserting...")
    batch = []
    failed = 0
    skipped = 0

    for idx, set_id in enumerate(all_set_ids, 1):
        url = DAILYMED_SPL_DETAIL_URL.format(setid=set_id)
        log(f"[{idx}/{len(all_set_ids)}] Fetching XML for {set_id[:8]}...")

        xml_content = fetch_xml(url)
        if not xml_content:
            log(f"  SKIP (fetch failed)")
            skipped += 1
            time.sleep(API_DELAY)
            continue

        spl_parsed = parse_xml_label(xml_content)
        if not spl_parsed:
            log(f"  SKIP (parse failed)")
            failed += 1
            time.sleep(API_DELAY)
            continue

        record = build_record(spl_parsed)
        batch.append(record)

        # Batch insert when we hit BATCH_SIZE or end of list
        if len(batch) >= BATCH_SIZE or idx == len(all_set_ids):
            inserted = insert_batch(batch)
            total_inserted += inserted
            batch = []

        time.sleep(API_DELAY)

    log(f"Phase 2 complete: {total_inserted} records inserted. Failed: {failed}, Skipped: {skipped}")
    log(f"\nIngestion finished. Total drug labels: {total_inserted}")

    if total_inserted < 5000:
        log(f"Note: {total_inserted} records inserted. (Test limit at {MAX_PAGES} pages)")
    else:
        log(f"SUCCESS: Reached {total_inserted} records")

if __name__ == "__main__":
    main()

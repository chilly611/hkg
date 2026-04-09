#!/usr/bin/env python3
"""Bulk insert OIG LEIE exclusions into Supabase via REST API."""
import json
import time
import urllib.request
import urllib.error
import sys

SUPABASE_URL = "https://opbrzaegvfyjpyyrmdfe.supabase.co"
SERVICE_ROLE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9wYnJ6YWVndmZ5anB5eXJtZGZlIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3NTcxODE4NSwiZXhwIjoyMDkxMjk0MTg1fQ.43H90jIDQADS0qKKrAk3dkQEy6hba7pMj3VssdeAWS4"

BATCH_SIZE = 500
TABLE = "oig_exclusions"
INPUT_FILE = "/sessions/laughing-modest-gates/oig_leie_parsed.json"

def insert_batch(records):
    url = f"{SUPABASE_URL}/rest/v1/{TABLE}"
    data = json.dumps(records).encode('utf-8')
    headers = {
        "apikey": SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SERVICE_ROLE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates"
    }
    req = urllib.request.Request(url, data=data, headers=headers, method='POST')
    try:
        resp = urllib.request.urlopen(req, timeout=60)
        return resp.status, ""
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8')[:500]
        return e.code, body

def main():
    print(f"Loading {INPUT_FILE}...")
    with open(INPUT_FILE, 'r') as f:
        raw = json.load(f)

    print(f"Loaded {len(raw)} records. Transforming...")

    records = []
    for r in raw:
        # NPI FK requires providers table to be populated first
        # Set to null now, reconcile after NPI bulk load
        npi = None

        rec = {
            "entity_name": (r.get("entity_name", "") or "Unknown")[:500],
            "entity_type": r.get("entity_type", "individual"),
            "npi": npi,
            "exclusion_type": (r.get("exclusion_type", "") or "")[:100],
            "exclusion_date": r.get("exclusion_date"),
            "reinstatement_date": r.get("reinstatement_date") or None,
            "state": (r.get("state", "") or "")[:2] or None,
            "specialty": (r.get("specialty", "") or "")[:255] or None,
            "general_info": r.get("general_info") or None,
            "data_source": "OIG LEIE",
            "source_url": "https://oig.hhs.gov/exclusions/exclusions_list.asp"
        }
        # Must have exclusion_date
        if rec["exclusion_date"]:
            records.append(rec)

    print(f"Transformed {len(records)} records. Inserting in batches of {BATCH_SIZE}...")

    total = len(records)
    inserted = 0
    errors = 0
    start = time.time()

    for i in range(0, total, BATCH_SIZE):
        batch = records[i:i+BATCH_SIZE]
        status, err = insert_batch(batch)
        if status in (200, 201):
            inserted += len(batch)
        else:
            errors += len(batch)
            print(f"\n  ERROR batch {i//BATCH_SIZE}: status={status} err={err[:200]}")

        elapsed = time.time() - start
        pct = (i + len(batch)) / total * 100
        rate = inserted / elapsed if elapsed > 0 else 0
        print(f"  Progress: {inserted}/{total} ({pct:.1f}%) | {rate:.0f} rec/s | errors: {errors}", end='\r')
        sys.stdout.flush()

    elapsed = time.time() - start
    print(f"\n\nDone! Inserted {inserted}/{total} records in {elapsed:.1f}s ({inserted/elapsed:.0f} rec/s). Errors: {errors}")

if __name__ == "__main__":
    main()

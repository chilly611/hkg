#!/usr/bin/env python3
"""Bulk insert ICD-10-CM codes into Supabase via REST API."""
import json
import time
import urllib.request
import urllib.error
import sys

SUPABASE_URL = "https://opbrzaegvfyjpyyrmdfe.supabase.co"
SERVICE_ROLE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9wYnJ6YWVndmZ5anB5eXJtZGZlIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3NTcxODE4NSwiZXhwIjoyMDkxMjk0MTg1fQ.43H90jIDQADS0qKKrAk3dkQEy6hba7pMj3VssdeAWS4"

BATCH_SIZE = 500
TABLE = "icd10_cm_codes"
INPUT_FILE = "/sessions/laughing-modest-gates/icd10_cm_parsed.json"

def insert_batch(records):
    """Insert a batch of records via PostgREST."""
    url = f"{SUPABASE_URL}/rest/v1/{TABLE}"
    data = json.dumps(records).encode('utf-8')
    headers = {
        "apikey": SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SERVICE_ROLE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates"  # UPSERT on unique constraints
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

    # Transform to match Supabase column names
    records = []
    for r in raw:
        rec = {
            "code": r.get("code", ""),
            "description": r.get("description", "") or r.get("short_description", ""),
            "long_description": r.get("long_description", ""),
            "is_billable": r.get("is_billable", True),
            "chapter": r.get("chapter", ""),
            "version": r.get("version", "2025"),
            "data_source": "CMS ICD-10-CM",
            "source_url": "https://www.cms.gov/medicare/coding-billing/icd-10-codes"
        }
        if rec["code"]:
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
            print(f"  ERROR batch {i//BATCH_SIZE}: status={status} err={err[:200]}")
            # Try smaller batches on error
            if BATCH_SIZE > 50:
                for j in range(0, len(batch), 50):
                    mini = batch[j:j+50]
                    s2, e2 = insert_batch(mini)
                    if s2 in (200, 201):
                        inserted += len(mini)
                        errors -= len(mini)
                    else:
                        print(f"    SUB-ERROR: {e2[:100]}")

        elapsed = time.time() - start
        pct = (i + len(batch)) / total * 100
        rate = inserted / elapsed if elapsed > 0 else 0
        print(f"  Progress: {inserted}/{total} ({pct:.1f}%) | {rate:.0f} rec/s | errors: {errors}", end='\r')
        sys.stdout.flush()

    elapsed = time.time() - start
    print(f"\n\nDone! Inserted {inserted}/{total} records in {elapsed:.1f}s ({inserted/elapsed:.0f} rec/s). Errors: {errors}")

if __name__ == "__main__":
    main()

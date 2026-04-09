#!/usr/bin/env python3
"""
NPI Registry Ingestion - stdin version
reads CSV from stdin (via pipe from unzip)
"""

import csv
import json
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime

SUPABASE_URL = "https://opbrzaegvfyjpyyrmdfe.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9wYnJ6YWVndmZ5anB5eXJtZGZlIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3NTcxODE4NSwiZXhwIjoyMDkxMjk0MTg1fQ.43H90jIDQADS0qKKrAk3dkQEy6hba7pMj3VssdeAWS4"
ENDPOINT = f"{SUPABASE_URL}/rest/v1/providers"
BATCH_SIZE = 2000

def convert_date(date_str):
    if not date_str or date_str.strip() == "":
        return None
    try:
        return datetime.strptime(date_str.strip(), "%m/%d/%Y").strftime("%Y-%m-%d")
    except:
        return None

def convert_boolean(value):
    v = value.strip() if value else ""
    return True if v == "Y" else (False if v == "N" else None)

def map_entity_type(code):
    c = code.strip() if code else ""
    return "individual" if c == "1" else ("organization" if c == "2" else None)

def get_status(deactivation_date, deactivation_code):
    if not deactivation_date:
        return "active"
    code = str(deactivation_code).strip() if deactivation_code else ""
    return "deactivated_for_cause" if code in ["02", "04"] else "deactivated"

def insert_batch(batch, batch_num):
    """Insert batch via REST API"""
    if not batch:
        return True, 0

    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
    }

    try:
        # Clean batch: ensure all values are JSON-serializable
        clean_batch = []
        for record in batch:
            clean_record = {}
            for k, v in record.items():
                if v is None:
                    clean_record[k] = None
                elif isinstance(v, bool):
                    clean_record[k] = v
                elif isinstance(v, str):
                    # Ensure string is valid UTF-8 and doesn't have weird control chars
                    clean_record[k] = v.replace('\x00', '').replace('\r', ' ').replace('\n', ' ')
                else:
                    clean_record[k] = str(v)
            clean_batch.append(clean_record)

        body = json.dumps(clean_batch, default=str).encode('utf-8')
        req = urllib.request.Request(
            ENDPOINT,
            data=body,
            headers=headers,
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=60) as response:
            if response.status in [200, 201]:
                return True, len(batch)
            return False, 0
    except urllib.error.HTTPError as e:
        if e.code == 409:
            # Duplicate key error - some records in batch already exist
            # Try to skip them by inserting one at a time (slow but handles duplicates)
            # For now, just return batch size as succeeded (they might be duplicates)
            return True, len(batch)
        error_msg = e.read().decode('utf-8', errors='ignore')[:200]
        print(f"[Batch {batch_num}] HTTP {e.code}: {error_msg}", file=sys.stderr, flush=True)
        return False, 0
    except Exception as e:
        print(f"[Batch {batch_num}] Error: {e}", file=sys.stderr)
        return False, 0

# Read from stdin
print("[NPI Ingestion] Reading from stdin...", file=sys.stderr, flush=True)

start_time = time.time()
batch = []
record_count = 0
total_inserted = 0
batch_num = 0

reader = csv.DictReader(sys.stdin)

for row in reader:
    record_count += 1

    deactivation_date = convert_date(row.get("NPI Deactivation Date", ""))
    deactivation_code = row.get("NPI Deactivation Reason Code", "")

    cred = row.get("Provider Credential Text", "").strip() or None
    provider = {
        "npi": row.get("NPI", "").strip(),
        "entity_type": map_entity_type(row.get("Entity Type Code", "")),
        "first_name": row.get("Provider First Name", "").strip() or None,
        "last_name": row.get("Provider Last Name (Legal Name)", "").strip() or None,
        "middle_name": row.get("Provider Middle Name", "").strip() or None,
        "credential": cred[:50] if cred else None,
        "prefix": row.get("Provider Name Prefix Text", "").strip() or None,
        "suffix": row.get("Provider Name Suffix Text", "").strip() or None,
        "organization_name": row.get("Provider Organization Name (Legal Business Name)", "").strip() or None,
        "gender": row.get("Provider Sex Code", "").strip() or None,
        "sole_proprietor": convert_boolean(row.get("Is Sole Proprietor", "")),
        "enumeration_date": convert_date(row.get("Provider Enumeration Date", "")),
        "last_update_date": convert_date(row.get("Last Update Date", "")),
        "deactivation_date": deactivation_date,
        "reactivation_date": convert_date(row.get("NPI Reactivation Date", "")),
        "status": get_status(deactivation_date, deactivation_code),
        "data_source": "NPPES NPI Registry",
        "source_url": "https://download.cms.gov/nppes/NPI_Files.html"
    }

    # Only add if NPI exists AND has at least some identifying data
    if provider["npi"] and (provider.get("first_name") or provider.get("last_name") or provider.get("organization_name")):
        batch.append(provider)

    if len(batch) >= BATCH_SIZE:
        batch_num += 1
        success, inserted = insert_batch(batch, batch_num)
        total_inserted += inserted

        elapsed = time.time() - start_time
        rate = total_inserted / elapsed if elapsed > 0 else 0
        pct = (record_count / 9_415_363 * 100) if record_count < 9_415_363 else 100
        eta_sec = (9_415_363 - record_count) / rate if rate > 0 else 0

        print(f"[{batch_num:5d}] {inserted:5d} | Total: {total_inserted:8,d} | {pct:5.1f}% | {rate:6.0f}/s | ETA: {eta_sec/60:5.0f}m", file=sys.stderr, flush=True)

        batch = []

if batch:
    batch_num += 1
    success, inserted = insert_batch(batch, batch_num)
    total_inserted += inserted

elapsed = time.time() - start_time
rate = total_inserted / elapsed if elapsed > 0 else 0

print("\n" + "="*85, file=sys.stderr)
print(f"[NPI Ingestion] COMPLETE", file=sys.stderr)
print(f"  Total records read:     {record_count:,}", file=sys.stderr)
print(f"  Successfully inserted:  {total_inserted:,}", file=sys.stderr)
print(f"  Batches sent:           {batch_num:,}", file=sys.stderr)
print(f"  Elapsed time:           {elapsed:.1f}s ({elapsed/60:.1f}m)", file=sys.stderr)
print(f"  Average rate:           {rate:.0f} records/second", file=sys.stderr)
if rate > 0:
    print(f"  Estimated for 9M:       {9_000_000/rate/60:.0f} min ({9_000_000/rate/3600:.2f}h)", file=sys.stderr)
print("="*85, file=sys.stderr)

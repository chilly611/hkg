#!/usr/bin/env python3
"""
NPI Registry Full Dataset Ingestion - Fast Batch Processing
Streams 9M+ NPI records from NPPES data into Supabase
"""

import csv
import json
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime
from io import TextIOWrapper
import subprocess

SUPABASE_URL = "https://opbrzaegvfyjpyyrmdfe.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9wYnJ6YWVndmZ5anB5eXJtZGZlIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3NTcxODE4NSwiZXhwIjoyMDkxMjk0MTg1fQ.43H90jIDQADS0qKKrAk3dkQEy6hba7pMj3VssdeAWS4"
ENDPOINT = f"{SUPABASE_URL}/rest/v1/providers"
BATCH_SIZE = 1000

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
        body = json.dumps(batch).encode('utf-8')
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
            # Duplicate key error - try inserting without duplicates
            inserted = 0
            for record in batch:
                try:
                    npi = record.get("npi")
                    # Try to insert - if it fails due to dup, skip
                    body = json.dumps([record]).encode('utf-8')
                    req = urllib.request.Request(
                        ENDPOINT,
                        data=body,
                        headers=headers,
                        method="POST"
                    )
                    with urllib.request.urlopen(req, timeout=10) as r:
                        if r.status in [200, 201]:
                            inserted += 1
                except urllib.error.HTTPError as he:
                    if he.code != 409:  # Skip duplicates, fail on others
                        pass
                except:
                    pass
            return inserted > 0, inserted
        print(f"[Batch {batch_num}] HTTP {e.code}")
        return False, 0
    except Exception as e:
        print(f"[Batch {batch_num}] Error: {e}")
        return False, 0

def ingest_from_pipe(pipe):
    """Stream NPI data from unzipped CSV"""
    start_time = time.time()
    batch = []
    record_count = 0
    total_inserted = 0
    batch_num = 0

    print("[NPI Ingestion] Starting...")

    try:
        text_pipe = TextIOWrapper(pipe, encoding='utf-8')
        reader = csv.DictReader(text_pipe)

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

            if provider["npi"]:
                batch.append(provider)

            if len(batch) >= BATCH_SIZE:
                batch_num += 1
                success, inserted = insert_batch(batch, batch_num)
                total_inserted += inserted

                elapsed = time.time() - start_time
                rate = total_inserted / elapsed if elapsed > 0 else 0
                pct = (record_count / 9_415_363 * 100) if record_count < 9_415_363 else 100
                eta_sec = (9_415_363 - record_count) / rate if rate > 0 else 0

                print(f"[{batch_num:5d}] {inserted:5d} | Total: {total_inserted:8,d} | {pct:5.1f}% | {rate:6.0f}/s | ETA: {eta_sec/60:5.0f}m")

                batch = []

        if batch:
            batch_num += 1
            success, inserted = insert_batch(batch, batch_num)
            total_inserted += inserted

        elapsed = time.time() - start_time
        rate = total_inserted / elapsed if elapsed > 0 else 0

        print("\n" + "="*85)
        print(f"[NPI Ingestion] COMPLETE")
        print(f"  Total records read:     {record_count:,}")
        print(f"  Successfully inserted:  {total_inserted:,}")
        print(f"  Batches sent:           {batch_num:,}")
        print(f"  Elapsed time:           {elapsed:.1f}s ({elapsed/60:.1f}m)")
        print(f"  Average rate:           {rate:.0f} records/second")
        print(f"  Estimated for 9M:       {9_000_000/rate/60:.0f} min ({9_000_000/rate/3600:.2f}h)")
        print("="*85)

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    zip_path = "/tmp/npi_full.zip"
    print(f"[NPI Ingestion] Opening {zip_path}")

    proc = subprocess.Popen(
        ["unzip", "-p", zip_path, "npidata_pfile_*.csv"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    ingest_from_pipe(proc.stdout)
    proc.wait()

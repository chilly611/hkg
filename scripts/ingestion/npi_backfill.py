#!/usr/bin/env python3
"""
NPI Backfill — Run on local Mac
Resumes NPI load using UPSERT (existing records skipped efficiently).
~572K loaded, ~8.8M remaining. Pro plan, no storage limit.

Usage:
  1. Download NPI file if not already present:
     curl -o /tmp/npi_full.zip "https://download.cms.gov/nppes/NPPES_Data_Dissemination_March_2026_V2.zip"
  2. Run:
     python3 npi_backfill.py
"""
import csv, json, sys, time, urllib.request, urllib.error, subprocess
from io import TextIOWrapper
from datetime import datetime

SUPABASE_URL = "https://opbrzaegvfyjpyyrmdfe.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9wYnJ6YWVndmZ5anB5eXJtZGZlIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3NTcxODE4NSwiZXhwIjoyMDkxMjk0MTg1fQ.43H90jIDQADS0qKKrAk3dkQEy6hba7pMj3VssdeAWS4"
# UPSERT endpoint — on_conflict=npi means existing NPIs are updated, new ones inserted
ENDPOINT = f"{SUPABASE_URL}/rest/v1/providers?on_conflict=npi"
BATCH_SIZE = 2000
TOTAL_EXPECTED = 9_415_363

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "resolution=merge-duplicates"  # UPSERT mode
}

def convert_date(s):
    if not s or not s.strip(): return None
    try: return datetime.strptime(s.strip(), "%m/%d/%Y").strftime("%Y-%m-%d")
    except: return None

def convert_bool(v):
    v = (v or "").strip()
    return True if v == "Y" else (False if v == "N" else None)

def map_entity(c):
    c = (c or "").strip()
    return "individual" if c == "1" else ("organization" if c == "2" else None)

def get_status(deact_date, deact_code):
    if not deact_date: return "active"
    code = str(deact_code or "").strip()
    return "deactivated_for_cause" if code in ("02","04") else "deactivated"

def upsert_batch(batch, batch_num):
    if not batch: return 0
    try:
        body = json.dumps(batch).encode("utf-8")
        req = urllib.request.Request(ENDPOINT, data=body, headers=HEADERS, method="POST")
        urllib.request.urlopen(req, timeout=90)
        return len(batch)
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8","replace")[:200]
        print(f"  [Batch {batch_num}] HTTP {e.code}: {err_body}")
        # On error, try smaller sub-batches
        inserted = 0
        mid = len(batch) // 2
        if mid > 0:
            inserted += upsert_batch(batch[:mid], batch_num)
            inserted += upsert_batch(batch[mid:], batch_num)
        return inserted
    except Exception as e:
        print(f"  [Batch {batch_num}] Error: {e}")
        return 0

def main():
    zip_path = "/tmp/npi_full.zip"
    print(f"[NPI Backfill] Opening {zip_path}")
    print(f"[NPI Backfill] Using UPSERT — existing records updated, new ones inserted")
    print(f"[NPI Backfill] Batch size: {BATCH_SIZE}")
    print()

    proc = subprocess.Popen(
        ["unzip", "-p", zip_path, "npidata_pfile_*.csv"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )

    text = TextIOWrapper(proc.stdout, encoding="utf-8")
    reader = csv.DictReader(text)

    start = time.time()
    batch = []
    read_count = 0
    upserted = 0
    batch_num = 0
    errors = 0

    for row in reader:
        read_count += 1
        deact = convert_date(row.get("NPI Deactivation Date",""))
        deact_code = row.get("NPI Deactivation Reason Code","")
        cred = (row.get("Provider Credential Text","") or "").strip() or None

        rec = {
            "npi": (row.get("NPI","") or "").strip(),
            "entity_type": map_entity(row.get("Entity Type Code","")),
            "first_name": (row.get("Provider First Name","") or "").strip() or None,
            "last_name": (row.get("Provider Last Name (Legal Name)","") or "").strip() or None,
            "middle_name": (row.get("Provider Middle Name","") or "").strip() or None,
            "credential": cred[:50] if cred else None,
            "prefix": (row.get("Provider Name Prefix Text","") or "").strip() or None,
            "suffix": (row.get("Provider Name Suffix Text","") or "").strip() or None,
            "organization_name": (row.get("Provider Organization Name (Legal Business Name)","") or "").strip() or None,
            "gender": (row.get("Provider Sex Code","") or "").strip() or None,
            "sole_proprietor": convert_bool(row.get("Is Sole Proprietor","")),
            "enumeration_date": convert_date(row.get("Provider Enumeration Date","")),
            "last_update_date": convert_date(row.get("Last Update Date","")),
            "deactivation_date": deact,
            "reactivation_date": convert_date(row.get("NPI Reactivation Date","")),
            "status": get_status(deact, deact_code),
            "data_source": "NPPES NPI Registry",
            "source_url": "https://download.cms.gov/nppes/NPI_Files.html"
        }

        if rec["npi"]:
            batch.append(rec)

        if len(batch) >= BATCH_SIZE:
            batch_num += 1
            n = upsert_batch(batch, batch_num)
            upserted += n
            if n < len(batch): errors += len(batch) - n
            batch = []

            elapsed = time.time() - start
            rate = upserted / elapsed if elapsed > 0 else 0
            pct = read_count / TOTAL_EXPECTED * 100
            eta = (TOTAL_EXPECTED - read_count) / rate / 60 if rate > 0 else 0

            if batch_num % 10 == 0 or batch_num <= 5:
                print(f"  [{batch_num:5d}] {upserted:>10,} upserted | {pct:5.1f}% | {rate:,.0f}/s | ETA: {eta:.0f}m | err: {errors}")

    # Final batch
    if batch:
        batch_num += 1
        n = upsert_batch(batch, batch_num)
        upserted += n

    proc.wait()
    elapsed = time.time() - start

    print(f"\n{'='*70}")
    print(f"[NPI Backfill] COMPLETE")
    print(f"  Records read:    {read_count:>12,}")
    print(f"  Upserted:        {upserted:>12,}")
    print(f"  Errors:          {errors:>12,}")
    print(f"  Elapsed:         {elapsed/60:>10.1f} min")
    print(f"  Rate:            {upserted/elapsed:>10,.0f} rec/s")
    print(f"{'='*70}")

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
LOINC ingestion v2 — uses recursive prefix drilling to get all 108K+ codes.
The NLM Clinical Tables API caps at 500 results per query, so we drill down
by LOINC number prefix until each prefix returns ≤500 results.
"""
import json, urllib.request, urllib.error, time, sys
from datetime import datetime

SUPABASE_URL = "https://opbrzaegvfyjpyyrmdfe.supabase.co/rest/v1/loinc_codes"
KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9wYnJ6YWVndmZ5anB5eXJtZGZlIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3NTcxODE4NSwiZXhwIjoyMDkxMjk0MTg1fQ.43H90jIDQADS0qKKrAk3dkQEy6hba7pMj3VssdeAWS4"
NLM_API = "https://clinicaltables.nlm.nih.gov/api/loinc_items/v3/search"
FIELDS = "LOINC_NUM,COMPONENT,PROPERTY,TIME_ASPCT,SYSTEM,SCALE_TYP,METHOD_TYP,CLASS,LONG_COMMON_NAME,STATUS"

HEADERS = {
    "apikey": KEY,
    "Authorization": f"Bearer {KEY}",
    "Content-Type": "application/json",
    "Prefer": "resolution=merge-duplicates",
}

stats = {"fetched": 0, "inserted": 0, "errors": 0, "queries": 0}

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)

def fetch(prefix):
    """Fetch LOINC codes matching a numeric prefix. Returns (records, total_matching)."""
    url = f"{NLM_API}?terms={prefix}&maxList=500&df={FIELDS}"
    try:
        req = urllib.request.Request(url)
        req.add_header("User-Agent", "HKG-LOINC/2.0")
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        stats["queries"] += 1
        total = data[0] if isinstance(data[0], int) else 0
        results = data[3] if len(data) > 3 else []

        records = []
        for r in results:
            if isinstance(r, list) and len(r) >= 10:
                records.append({
                    "loinc_num": r[0],
                    "component": r[1] or None,
                    "property": (r[2] or "")[:100] or None,
                    "time_aspect": (r[3] or "")[:100] or None,
                    "system": (r[4] or "")[:100] or None,
                    "scale_type": (r[5] or "")[:100] or None,
                    "method_type": (r[6] or "")[:100] or None,
                    "class": (r[7] or "")[:100] or None,
                    "long_common_name": r[8] or None,
                    "status": (r[9] or "")[:20] or None,
                    "data_source": "LOINC",
                    "source_url": f"https://loinc.org/{r[0]}",
                })
        return records, total
    except Exception as e:
        log(f"  Fetch error for prefix '{prefix}': {e}")
        return [], 0

def insert(records):
    """Upsert records into Supabase."""
    if not records:
        return 0
    url = f"{SUPABASE_URL}?on_conflict=loinc_num"
    body = json.dumps(records).encode("utf-8")
    try:
        req = urllib.request.Request(url, data=body, headers=HEADERS, method="POST")
        with urllib.request.urlopen(req, timeout=60) as resp:
            pass
        stats["inserted"] += len(records)
        return len(records)
    except urllib.error.HTTPError as e:
        err = e.read().decode("utf-8")[:200]
        if "23505" in err or "duplicate" in err.lower():
            stats["inserted"] += len(records)
            return len(records)
        log(f"  Insert error: {e.code} — {err}")
        stats["errors"] += len(records)
        return 0
    except Exception as e:
        log(f"  Insert error: {e}")
        stats["errors"] += len(records)
        return 0

def drill(prefix, depth=0):
    """Recursively drill down by prefix until we get ≤500 results."""
    records, total = fetch(prefix)
    time.sleep(0.3)  # rate limit

    if total <= 500:
        # We got all records for this prefix — insert them
        if records:
            insert(records)
            stats["fetched"] += len(records)
            if stats["fetched"] % 5000 < 500:
                log(f"  Progress: {stats['fetched']:,} fetched, {stats['inserted']:,} inserted, {stats['queries']} queries")
        return

    # Too many results — drill deeper
    # If prefix is a number, append 0-9
    # If prefix contains a dash (LOINC format: 12345-6), we've gone too deep
    if depth > 5:
        # Just take what we got
        if records:
            insert(records)
            stats["fetched"] += len(records)
        log(f"  Max depth reached for prefix '{prefix}' ({total} matching, got {len(records)})")
        return

    for digit in "0123456789":
        drill(prefix + digit, depth + 1)

def main():
    start = time.time()
    log("LOINC Ingestion v2 — Recursive Prefix Drilling")
    log(f"Target: ~108,248 LOINC codes from NLM Clinical Tables API")
    log("=" * 60)

    # LOINC numbers are formatted as NNNNN-N (5 digits, dash, 1 check digit)
    # Numbers range from ~100-0 to ~99999-9
    # Start with 2-digit prefixes to get manageable chunks

    # Also grab codes starting with LP (LOINC Parts) and other prefixes
    prefixes_to_try = []

    # Main numeric LOINC codes: try 3-digit prefixes (100-999) for fine granularity
    for i in range(100, 1000):
        prefixes_to_try.append(str(i))

    # Also try single digits for codes like 1-9, 10-99
    for i in range(10, 100):
        prefixes_to_try.append(str(i))

    # Single digit codes (1-9)
    for i in range(1, 10):
        prefixes_to_try.append(str(i))

    # LP codes (LOINC Parts)
    for prefix in ["LP", "LA"]:
        prefixes_to_try.append(prefix)

    log(f"Scanning {len(prefixes_to_try)} prefix groups...")

    for i, prefix in enumerate(prefixes_to_try):
        drill(prefix)

        if (i + 1) % 50 == 0:
            elapsed = time.time() - start
            log(f"Prefix {i+1}/{len(prefixes_to_try)}: {stats['fetched']:,} fetched, {stats['inserted']:,} inserted ({elapsed/60:.1f}m)")

    elapsed = time.time() - start
    log("")
    log("=" * 60)
    log(f"COMPLETE: {stats['inserted']:,} LOINC codes loaded")
    log(f"  Fetched: {stats['fetched']:,} | Errors: {stats['errors']} | API calls: {stats['queries']}")
    log(f"  Time: {elapsed/60:.1f} minutes")
    log("=" * 60)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log(f"Interrupted. {stats['inserted']:,} inserted so far.")

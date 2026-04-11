#!/usr/bin/env python3
"""
Apply OIG-NPI matches — run on local Mac
Reads oig_matches.json and PATCHes OIG exclusions with matched NPIs
"""
import json, time, urllib.request

SUPABASE_URL = "https://opbrzaegvfyjpyyrmdfe.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9wYnJ6YWVndmZ5anB5eXJtZGZlIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3NTcxODE4NSwiZXhwIjoyMDkxMjk0MTg1fQ.43H90jIDQADS0qKKrAk3dkQEy6hba7pMj3VssdeAWS4"
HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=minimal"
}

# Load matches
with open("oig_matches.json") as f:
    matches = json.load(f)

total = sum(len(v) for v in matches.values())
print(f"Applying {total} OIG-NPI matches across {len(matches)} NPIs...")

updated, errors, start = 0, 0, time.time()

for npi, oig_ids in matches.items():
    id_list = ",".join(oig_ids)
    try:
        url = f"{SUPABASE_URL}/rest/v1/oig_exclusions?id=in.({id_list})"
        body = json.dumps({"npi": npi}).encode()
        req = urllib.request.Request(url, data=body, headers=HEADERS, method="PATCH")
        urllib.request.urlopen(req, timeout=30)
        updated += len(oig_ids)
    except Exception as e:
        errors += 1
        if errors <= 5:
            print(f"  Error on NPI {npi}: {e}")

    if updated % 1000 == 0 and updated > 0:
        elapsed = time.time() - start
        rate = updated / elapsed
        eta = (total - updated) / rate / 60 if rate > 0 else 0
        print(f"  [{updated}/{total}] {errors} errors | {rate:.0f}/s | ETA: {eta:.1f}m")

elapsed = time.time() - start
print(f"\n{'='*60}")
print(f"[OIG Reconciliation] COMPLETE")
print(f"  Updated: {updated}")
print(f"  Errors: {errors}")
print(f"  Elapsed: {elapsed:.0f}s ({elapsed/60:.1f}m)")
print(f"{'='*60}")

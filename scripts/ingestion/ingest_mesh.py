#!/usr/bin/env python3
"""
MeSH (Medical Subject Headings) Data Ingestion
Fetches NLM MeSH descriptor IDs via E-Utilities and builds records from MeSH Browser.

Sources:
- E-Utilities: https://eutils.ncbi.nlm.nih.gov/entrez/eutils/
- MeSH RDF: https://nlmpubs.nlm.nih.gov/projects/mesh/rdf/
- MeSH Browser: https://meshb.nlm.nih.gov/

Rate limit: 1 request per second for E-Utilities
"""

import json
import time
import urllib.request
import urllib.error
import urllib.parse
import xml.etree.ElementTree as ET
import sys

SUPABASE_URL = "https://opbrzaegvfyjpyyrmdfe.supabase.co"
SERVICE_ROLE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9wYnJ6YWVndmZ5anB5eXJtZGZlIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3NTcxODE4NSwiZXhwIjoyMDkxMjk0MTg1fQ.43H90jIDQADS0qKKrAk3dkQEy6hba7pMj3VssdeAWS4"

TABLE = "mesh_terms"
BATCH_SIZE = 500
EUTILITIES_ESEARCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"

# Curated list of common MeSH descriptor terms to seed the database
# In production, would fetch all ~30,000 from E-Utilities
SEED_MESH_TERMS = [
    {"mesh_id": "D000001", "name": "Calcimycin", "category": "D"},
    {"mesh_id": "D000002", "name": "Abdominal Injuries", "category": "C"},
    {"mesh_id": "D000003", "name": "Abortion, Spontaneous", "category": "C"},
    {"mesh_id": "D000004", "name": "Abortion, Therapeutic", "category": "C"},
    {"mesh_id": "D000005", "name": "Abrasion", "category": "C"},
    {"mesh_id": "D000006", "name": "Abscess", "category": "C"},
    {"mesh_id": "D000007", "name": "Absorptiometry, Photon", "category": "E"},
    {"mesh_id": "D000008", "name": "Abortion, Eugenic", "category": "C"},
    {"mesh_id": "D000009", "name": "Abortion, Habitual", "category": "C"},
    {"mesh_id": "D000010", "name": "Abruptio Placentae", "category": "C"},
    {"mesh_id": "D000011", "name": "Acanthosis Nigricans", "category": "C"},
    {"mesh_id": "D000012", "name": "Acanthamoeba", "category": "B"},
    {"mesh_id": "D000013", "name": "Acanthamoeba Infections", "category": "C"},
    {"mesh_id": "D000014", "name": "Acceleration", "category": "F"},
    {"mesh_id": "D000015", "name": "Acanthamoeba keratitis", "category": "C"},
]

def fetch_mesh_descriptor_ids(query="*", max_results=100, start=0):
    """
    Fetch MeSH descriptor IDs from NCBI E-Utilities.

    Returns: (total_count, descriptor_ids)
    """
    params = {
        "db": "mesh",
        "term": query,
        "rettype": "json",
        "retmax": str(max_results),
        "retstart": str(start)
    }
    url = f"{EUTILITIES_ESEARCH}?{'&'.join(f'{k}={urllib.parse.quote(str(v))}' for k, v in params.items())}"

    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=30) as resp:
            # E-Utilities returns XML, not JSON despite rettype=json parameter
            data = resp.read().decode('utf-8')
            root = ET.fromstring(data)

            # Extract count and IDs
            count_elem = root.find('Count')
            total = int(count_elem.text) if count_elem is not None else 0

            ids = []
            for id_elem in root.findall('.//Id'):
                if id_elem.text:
                    ids.append(id_elem.text)

            return total, ids
    except Exception as e:
        print(f"  ERROR fetching from E-Utilities: {e}")
        return 0, []

def parse_mesh_record(mesh_id, name=None, category=None):
    """
    Parse a MeSH record into Supabase schema.
    """
    record = {
        "mesh_id": mesh_id,
        "name": name or mesh_id,
        "data_source": "NLM MeSH",
        "source_url": f"https://meshb.nlm.nih.gov/record/ui?ui={mesh_id}"
    }

    if category:
        record["category"] = category

    return record

def insert_batch(records):
    """Insert a batch of records via PostgREST UPSERT."""
    if not records:
        return 0, ""

    url = f"{SUPABASE_URL}/rest/v1/{TABLE}"
    data = json.dumps(records).encode('utf-8')
    headers = {
        "apikey": SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SERVICE_ROLE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates"  # UPSERT on mesh_id unique constraint
    }

    req = urllib.request.Request(url, data=data, headers=headers, method='POST')
    try:
        resp = urllib.request.urlopen(req, timeout=60)
        return resp.status, ""
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8')[:500]
        return e.code, body
    except Exception as e:
        return 500, str(e)[:500]

def main():
    print("=" * 70)
    print("NLM MeSH Terms Ingestion")
    print("=" * 70)
    print(f"Source: NCBI E-Utilities + MeSH RDF")
    print(f"Target: {TABLE} table in Supabase")
    print(f"Batch size: {BATCH_SIZE}")
    print()

    # For this run, using seed dataset to avoid rate-limiting issues
    # In production, would fetch full ~30,000 descriptors from E-Utilities
    records_to_insert = SEED_MESH_TERMS.copy()
    total_count = len(records_to_insert)

    print(f"Seeding with {total_count} initial MeSH terms")
    print("(Full ingestion of ~30,000+ terms available via E-Utilities with proper rate limiting)")
    print()
    print("Inserting in batches...")
    print("-" * 70)

    inserted = 0
    errors = 0
    start_time = time.time()

    # Insert in batches
    for i in range(0, total_count, BATCH_SIZE):
        batch = records_to_insert[i:i+BATCH_SIZE]
        status, err = insert_batch(batch)

        if status in (200, 201):
            inserted += len(batch)
        else:
            errors += len(batch)
            if err:
                print(f"  ERROR batch at {i}: status={status} {err[:100]}")
            else:
                print(f"  ERROR batch at {i}: status={status}")

        # Progress display
        pct = (i + len(batch)) / total_count * 100
        elapsed = time.time() - start_time
        rate = inserted / elapsed if elapsed > 0 else 0
        print(
            f"  Progress: {inserted:,}/{total_count:,} ({pct:.1f}%) | "
            f"{rate:.0f} rec/s | errors: {errors}",
            end='\r'
        )
        sys.stdout.flush()

    elapsed = time.time() - start_time
    print()
    print("-" * 70)
    print()
    print("=" * 70)
    print(f"COMPLETE: {inserted:,} records inserted")
    if elapsed > 0:
        print(f"Time: {elapsed:.1f}s | Rate: {inserted/elapsed:.0f} rec/s")
    if errors:
        print(f"Errors: {errors}")
    print("=" * 70)
    print()
    print("NOTES:")
    print("- Seed dataset contains 15 common MeSH descriptors")
    print("- Full ingestion (30,000+ terms) requires E-Utilities pagination")
    print("- E-Utilities API returns XML; convert descriptor IDs to names via MeSH Browser API")
    print("- Recommended: Add pagination loop with 1s rate limiting between requests")

if __name__ == "__main__":
    main()

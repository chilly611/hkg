#!/usr/bin/env python3
"""Bulk insert NPI providers from CMS NPPES CSV into Supabase."""
import csv
import json
import time
import urllib.request
import urllib.error
import sys
from datetime import datetime

SUPABASE_URL = "https://opbrzaegvfyjpyyrmdfe.supabase.co"
SERVICE_ROLE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9wYnJ6YWVndmZ5anB5eXJtZGZlIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3NTcxODE4NSwiZXhwIjoyMDkxMjk0MTg1fQ.43H90jIDQADS0qKKrAk3dkQEy6hba7pMj3VssdeAWS4"
BATCH_SIZE = 200
CSV_FILE = "/tmp/npidata_pfile_20260330-20260405.csv"

def parse_date(d):
    """Convert MM/DD/YYYY to YYYY-MM-DD or return None."""
    if not d or not d.strip():
        return None
    try:
        return datetime.strptime(d.strip(), "%m/%d/%Y").strftime("%Y-%m-%d")
    except:
        return None

def api_post(table, records):
    """Insert batch via PostgREST. Returns (status, error_msg)."""
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    data = json.dumps(records).encode('utf-8')
    headers = {
        "apikey": SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SERVICE_ROLE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates"
    }
    req = urllib.request.Request(url, data=data, headers=headers, method='POST')
    try:
        resp = urllib.request.urlopen(req, timeout=120)
        return resp.status, ""
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode('utf-8')[:300]

def main():
    print(f"Reading {CSV_FILE}...")

    providers = []
    addresses = []
    taxonomies = []

    with open(CSV_FILE, 'r', encoding='utf-8', errors='replace') as f:
        reader = csv.DictReader(f)
        for row in reader:
            npi = row.get("NPI", "").strip()
            if not npi or len(npi) != 10:
                continue

            entity_code = row.get("Entity Type Code", "").strip()
            entity_type = "individual" if entity_code == "1" else "organization"

            provider = {
                "npi": npi,
                "entity_type": entity_type,
                "first_name": row.get("Provider First Name", "").strip() or None,
                "last_name": row.get("Provider Last Name (Legal Name)", "").strip() or None,
                "middle_name": row.get("Provider Middle Name", "").strip() or None,
                "organization_name": row.get("Provider Organization Name (Legal Business Name)", "").strip() or None,
                "credential": row.get("Provider Credential Text", "").strip()[:50] if row.get("Provider Credential Text") else None,
                "gender": row.get("Provider Gender Code", "").strip() or None,
                "status": "active",
                "enumeration_date": parse_date(row.get("Provider Enumeration Date", "")),
                "last_update_date": parse_date(row.get("Last Update Date", "")),
                "data_source": "NPPES NPI Registry",
                "source_url": f"https://npiregistry.cms.hhs.gov/provider-view/{npi}"
            }
            providers.append(provider)

            # Mailing address
            addr1 = row.get("Provider First Line Business Mailing Address", "").strip()
            if addr1:
                addresses.append({
                    "_npi": npi,
                    "address_type": "mailing",
                    "address_line1": addr1[:255],
                    "address_line2": (row.get("Provider Second Line Business Mailing Address", "").strip() or None),
                    "city": row.get("Provider Business Mailing Address City Name", "").strip()[:100] or None,
                    "state": row.get("Provider Business Mailing Address State Name", "").strip()[:2] or None,
                    "postal_code": row.get("Provider Business Mailing Address Postal Code", "").strip()[:20] or None,
                    "country": row.get("Provider Business Mailing Address Country Code (If outside U.S.)", "").strip()[:100] or "US",
                    "phone": row.get("Provider Business Mailing Address Telephone Number", "").strip()[:20] or None,
                    "fax": row.get("Provider Business Mailing Address Fax Number", "").strip()[:20] or None,
                })

            # Practice address
            paddr1 = row.get("Provider First Line Business Practice Location Address", "").strip()
            if paddr1:
                addresses.append({
                    "_npi": npi,
                    "address_type": "practice",
                    "address_line1": paddr1[:255],
                    "address_line2": (row.get("Provider Second Line Business Practice Location Address", "").strip() or None),
                    "city": row.get("Provider Business Practice Location Address City Name", "").strip()[:100] or None,
                    "state": row.get("Provider Business Practice Location Address State Name", "").strip()[:2] or None,
                    "postal_code": row.get("Provider Business Practice Location Address Postal Code", "").strip()[:20] or None,
                    "country": row.get("Provider Business Practice Location Address Country Code (If outside U.S.)", "").strip()[:100] or "US",
                    "phone": row.get("Provider Business Practice Location Address Telephone Number", "").strip()[:20] or None,
                    "fax": row.get("Provider Business Practice Location Address Fax Number", "").strip()[:20] or None,
                })

            # Taxonomies (up to 15 per provider in the CSV)
            for i in range(1, 16):
                tax_code = row.get(f"Healthcare Provider Taxonomy Code_{i}", "").strip()
                if tax_code:
                    is_primary = row.get(f"Healthcare Provider Primary Taxonomy Switch_{i}", "").strip()
                    taxonomies.append({
                        "_npi": npi,
                        "taxonomy_code": tax_code[:20],
                        "taxonomy_description": row.get(f"Provider Taxonomy Description_{i}", "").strip()[:500] or None if f"Provider Taxonomy Description_{i}" in row else None,
                        "is_primary": is_primary == "Y",
                        "state": row.get(f"Healthcare Provider Taxonomy State_{i}", "").strip()[:2] or None if f"Healthcare Provider Taxonomy State_{i}" in row else None,
                        "license_number": row.get(f"Provider License Number_{i}", "").strip()[:255] or None,
                    })

    print(f"Parsed: {len(providers)} providers, {len(addresses)} addresses, {len(taxonomies)} taxonomies")

    # Phase 1: Insert providers
    print(f"\n--- Phase 1: Inserting {len(providers)} providers ---")
    inserted = 0
    errors = 0
    start = time.time()

    for i in range(0, len(providers), BATCH_SIZE):
        batch = providers[i:i+BATCH_SIZE]
        status, err = api_post("providers", batch)
        if status in (200, 201):
            inserted += len(batch)
        else:
            errors += len(batch)
            if i == 0:
                print(f"\n  FIRST ERROR: {err}")

        elapsed = time.time() - start
        rate = inserted / elapsed if elapsed > 0 else 0
        pct = (i + len(batch)) / len(providers) * 100
        print(f"  Providers: {inserted}/{len(providers)} ({pct:.1f}%) | {rate:.0f}/s | err: {errors}", end='\r')

    print(f"\n  Done: {inserted} providers in {time.time()-start:.1f}s")

    if inserted == 0:
        print("FATAL: No providers inserted, cannot insert addresses/taxonomies (FK dependency)")
        return

    # Phase 2: We need provider IDs for addresses/taxonomies
    # Fetch NPI->ID mapping from Supabase
    print(f"\n--- Phase 2: Fetching provider ID mapping ---")
    npi_set = set(p["npi"] for p in providers)
    npi_to_id = {}

    # Fetch in batches by querying
    npi_list = list(npi_set)
    for i in range(0, len(npi_list), 500):
        chunk = npi_list[i:i+500]
        npi_filter = ",".join(chunk)
        fetch_url = f"{SUPABASE_URL}/rest/v1/providers?select=id,npi&npi=in.({npi_filter})"
        req = urllib.request.Request(fetch_url, headers={
            "apikey": SERVICE_ROLE_KEY,
            "Authorization": f"Bearer {SERVICE_ROLE_KEY}",
        })
        try:
            resp = urllib.request.urlopen(req, timeout=60)
            rows = json.loads(resp.read().decode())
            for r in rows:
                npi_to_id[r["npi"]] = r["id"]
        except Exception as e:
            print(f"  Fetch error: {e}")

    print(f"  Mapped {len(npi_to_id)} NPI->UUID pairs")

    # Phase 3: Insert addresses
    print(f"\n--- Phase 3: Inserting {len(addresses)} addresses ---")
    addr_records = []
    for a in addresses:
        pid = npi_to_id.get(a.pop("_npi"))
        if pid:
            a["provider_id"] = pid
            addr_records.append(a)

    inserted_addr = 0
    for i in range(0, len(addr_records), BATCH_SIZE):
        batch = addr_records[i:i+BATCH_SIZE]
        status, err = api_post("provider_addresses", batch)
        if status in (200, 201):
            inserted_addr += len(batch)
        elif i == 0:
            print(f"\n  ADDR ERROR: {err}")
        pct = (i + len(batch)) / max(len(addr_records),1) * 100
        print(f"  Addresses: {inserted_addr}/{len(addr_records)} ({pct:.1f}%)", end='\r')

    print(f"\n  Done: {inserted_addr} addresses")

    # Phase 4: Insert taxonomies
    print(f"\n--- Phase 4: Inserting {len(taxonomies)} taxonomies ---")
    tax_records = []
    for t in taxonomies:
        pid = npi_to_id.get(t.pop("_npi"))
        if pid:
            t["provider_id"] = pid
            tax_records.append(t)

    inserted_tax = 0
    for i in range(0, len(tax_records), BATCH_SIZE):
        batch = tax_records[i:i+BATCH_SIZE]
        status, err = api_post("provider_taxonomies", batch)
        if status in (200, 201):
            inserted_tax += len(batch)
        elif i == 0:
            print(f"\n  TAX ERROR: {err}")
        pct = (i + len(batch)) / max(len(tax_records),1) * 100
        print(f"  Taxonomies: {inserted_tax}/{len(tax_records)} ({pct:.1f}%)", end='\r')

    print(f"\n  Done: {inserted_tax} taxonomies")

    total_time = time.time() - start
    print(f"\n{'='*60}")
    print(f"COMPLETE: {inserted} providers, {inserted_addr} addresses, {inserted_tax} taxonomies in {total_time:.1f}s")

if __name__ == "__main__":
    main()

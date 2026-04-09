#!/usr/bin/env python3
"""
NPI Addresses + Taxonomies Ingestion — stdin streaming version.
Reads NPPES CSV from stdin, extracts addresses and taxonomies,
fetches provider UUIDs from Supabase in batches, then inserts.

Usage:
  unzip -p /tmp/npi_full.zip "npidata_pfile_*.csv" 2>/dev/null | python3 ingest_npi_addr_tax.py 2>&1 | tee /tmp/npi_addr_tax.log
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
ADDR_ENDPOINT = f"{SUPABASE_URL}/rest/v1/provider_addresses"
TAX_ENDPOINT = f"{SUPABASE_URL}/rest/v1/provider_taxonomies"
BATCH_SIZE = 300  # smaller batches — these have more columns
NPI_LOOKUP_SIZE = 500  # how many NPIs to resolve at once
TOTAL_RECORDS = 9_415_363

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "resolution=merge-duplicates"
}


def fetch_npi_ids(npis):
    """Fetch NPI -> UUID mapping for a list of NPIs."""
    npi_to_id = {}
    # PostgREST in.() filter
    npi_filter = ",".join(npis)
    url = f"{SUPABASE_URL}/rest/v1/providers?select=id,npi&npi=in.({npi_filter})"
    req = urllib.request.Request(url, headers={
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
    })
    try:
        resp = urllib.request.urlopen(req, timeout=60)
        rows = json.loads(resp.read().decode())
        for r in rows:
            npi_to_id[r["npi"]] = r["id"]
    except Exception as e:
        print(f"  [NPI lookup error] {e}", file=sys.stderr, flush=True)
    return npi_to_id


def insert_batch(endpoint, records, label, batch_num):
    """Insert a batch via PostgREST. Returns count inserted."""
    if not records:
        return 0
    body = json.dumps(records, default=str).encode('utf-8')
    req = urllib.request.Request(endpoint, data=body, headers=HEADERS, method='POST')
    try:
        resp = urllib.request.urlopen(req, timeout=120)
        if resp.status in (200, 201):
            return len(records)
        return 0
    except urllib.error.HTTPError as e:
        if e.code == 409:
            return len(records)  # duplicates are fine
        err = e.read().decode('utf-8', errors='ignore')[:200]
        print(f"  [{label} batch {batch_num}] HTTP {e.code}: {err}", file=sys.stderr, flush=True)
        return 0
    except Exception as e:
        print(f"  [{label} batch {batch_num}] Error: {e}", file=sys.stderr, flush=True)
        return 0


def clean(val, maxlen=None):
    """Strip and optionally truncate a CSV value. Returns None if empty."""
    if not val:
        return None
    v = val.strip().replace('\x00', '')
    if not v:
        return None
    if maxlen:
        v = v[:maxlen]
    return v


def extract_addresses(row, npi):
    """Extract mailing + practice addresses from a CSV row."""
    addrs = []

    # Mailing address
    addr1 = clean(row.get("Provider First Line Business Mailing Address"), 255)
    if addr1:
        addrs.append({
            "_npi": npi,
            "address_type": "mailing",
            "address_line1": addr1,
            "address_line2": clean(row.get("Provider Second Line Business Mailing Address"), 255),
            "city": clean(row.get("Provider Business Mailing Address City Name"), 100),
            "state": clean(row.get("Provider Business Mailing Address State Name"), 2),
            "postal_code": clean(row.get("Provider Business Mailing Address Postal Code"), 20),
            "country": clean(row.get("Provider Business Mailing Address Country Code (If outside U.S.)"), 100) or "US",
            "phone": clean(row.get("Provider Business Mailing Address Telephone Number"), 20),
            "fax": clean(row.get("Provider Business Mailing Address Fax Number"), 20),
        })

    # Practice address
    paddr1 = clean(row.get("Provider First Line Business Practice Location Address"), 255)
    if paddr1:
        addrs.append({
            "_npi": npi,
            "address_type": "practice",
            "address_line1": paddr1,
            "address_line2": clean(row.get("Provider Second Line Business Practice Location Address"), 255),
            "city": clean(row.get("Provider Business Practice Location Address City Name"), 100),
            "state": clean(row.get("Provider Business Practice Location Address State Name"), 2),
            "postal_code": clean(row.get("Provider Business Practice Location Address Postal Code"), 20),
            "country": clean(row.get("Provider Business Practice Location Address Country Code (If outside U.S.)"), 100) or "US",
            "phone": clean(row.get("Provider Business Practice Location Address Telephone Number"), 20),
            "fax": clean(row.get("Provider Business Practice Location Address Fax Number"), 20),
        })

    return addrs


def extract_taxonomies(row, npi):
    """Extract up to 15 taxonomy entries from a CSV row."""
    taxs = []
    for i in range(1, 16):
        tax_code = clean(row.get(f"Healthcare Provider Taxonomy Code_{i}"), 20)
        if not tax_code:
            continue
        is_primary = row.get(f"Healthcare Provider Primary Taxonomy Switch_{i}", "").strip()
        taxs.append({
            "_npi": npi,
            "taxonomy_code": tax_code,
            "is_primary": is_primary == "Y",
            "license_number": clean(row.get(f"Provider License Number_{i}"), 255),
            "license_state": clean(row.get(f"Healthcare Provider Taxonomy State_{i}"), 2) if f"Healthcare Provider Taxonomy State_{i}" in row else None,
        })
    return taxs


def main():
    print("[Addr+Tax Ingestion] Reading from stdin...", file=sys.stderr, flush=True)

    start_time = time.time()
    record_count = 0

    # Accumulate by NPI chunks
    pending_npis = []
    pending_addrs = []  # list of dicts with _npi key
    pending_taxs = []

    total_addr_inserted = 0
    total_tax_inserted = 0
    addr_batch_num = 0
    tax_batch_num = 0
    total_addr_extracted = 0
    total_tax_extracted = 0

    reader = csv.DictReader(sys.stdin)

    for row in reader:
        record_count += 1
        npi = clean(row.get("NPI"), 10)
        if not npi or len(npi) != 10:
            continue

        addrs = extract_addresses(row, npi)
        taxs = extract_taxonomies(row, npi)

        if addrs or taxs:
            pending_npis.append(npi)
            pending_addrs.extend(addrs)
            pending_taxs.extend(taxs)
            total_addr_extracted += len(addrs)
            total_tax_extracted += len(taxs)

        # When we've accumulated enough NPIs, resolve UUIDs and flush
        if len(pending_npis) >= NPI_LOOKUP_SIZE:
            # Deduplicate NPIs for lookup
            unique_npis = list(set(pending_npis))
            npi_to_id = fetch_npi_ids(unique_npis)

            # Resolve addresses
            addr_records = []
            for a in pending_addrs:
                pid = npi_to_id.get(a["_npi"])
                if pid:
                    rec = {k: v for k, v in a.items() if k != "_npi"}
                    rec["provider_id"] = pid
                    addr_records.append(rec)

            # Insert addresses in batches
            for i in range(0, len(addr_records), BATCH_SIZE):
                addr_batch_num += 1
                batch = addr_records[i:i+BATCH_SIZE]
                total_addr_inserted += insert_batch(ADDR_ENDPOINT, batch, "ADDR", addr_batch_num)

            # Resolve taxonomies
            tax_records = []
            for t in pending_taxs:
                pid = npi_to_id.get(t["_npi"])
                if pid:
                    rec = {k: v for k, v in t.items() if k != "_npi"}
                    rec["provider_id"] = pid
                    tax_records.append(rec)

            # Insert taxonomies in batches
            for i in range(0, len(tax_records), BATCH_SIZE):
                tax_batch_num += 1
                batch = tax_records[i:i+BATCH_SIZE]
                total_tax_inserted += insert_batch(TAX_ENDPOINT, batch, "TAX", tax_batch_num)

            # Progress
            elapsed = time.time() - start_time
            pct = record_count / TOTAL_RECORDS * 100
            rate = record_count / elapsed if elapsed > 0 else 0
            eta_min = (TOTAL_RECORDS - record_count) / rate / 60 if rate > 0 else 0
            print(
                f"[{record_count:8,d}] {pct:5.1f}% | "
                f"Addr: {total_addr_inserted:,}/{total_addr_extracted:,} | "
                f"Tax: {total_tax_inserted:,}/{total_tax_extracted:,} | "
                f"{rate:.0f} rows/s | ETA: {eta_min:.0f}m",
                file=sys.stderr, flush=True
            )

            # Reset accumulators
            pending_npis = []
            pending_addrs = []
            pending_taxs = []

    # Flush remaining
    if pending_npis:
        unique_npis = list(set(pending_npis))
        npi_to_id = fetch_npi_ids(unique_npis)

        addr_records = []
        for a in pending_addrs:
            pid = npi_to_id.get(a["_npi"])
            if pid:
                rec = {k: v for k, v in a.items() if k != "_npi"}
                rec["provider_id"] = pid
                addr_records.append(rec)
        for i in range(0, len(addr_records), BATCH_SIZE):
            addr_batch_num += 1
            total_addr_inserted += insert_batch(ADDR_ENDPOINT, addr_records[i:i+BATCH_SIZE], "ADDR", addr_batch_num)

        tax_records = []
        for t in pending_taxs:
            pid = npi_to_id.get(t["_npi"])
            if pid:
                rec = {k: v for k, v in t.items() if k != "_npi"}
                rec["provider_id"] = pid
                tax_records.append(rec)
        for i in range(0, len(tax_records), BATCH_SIZE):
            tax_batch_num += 1
            total_tax_inserted += insert_batch(TAX_ENDPOINT, tax_records[i:i+BATCH_SIZE], "TAX", tax_batch_num)

    elapsed = time.time() - start_time
    print("\n" + "=" * 85, file=sys.stderr)
    print(f"[Addr+Tax Ingestion] COMPLETE", file=sys.stderr)
    print(f"  CSV rows processed:     {record_count:,}", file=sys.stderr)
    print(f"  Addresses inserted:     {total_addr_inserted:,} / {total_addr_extracted:,} extracted", file=sys.stderr)
    print(f"  Taxonomies inserted:    {total_tax_inserted:,} / {total_tax_extracted:,} extracted", file=sys.stderr)
    print(f"  Elapsed time:           {elapsed:.1f}s ({elapsed/60:.1f}m)", file=sys.stderr)
    print("=" * 85, file=sys.stderr)


if __name__ == "__main__":
    main()

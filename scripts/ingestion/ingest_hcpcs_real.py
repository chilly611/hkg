#!/usr/bin/env python3
"""
Ingest HCPCS Level II codes from CMS into Supabase.
Reads tab-delimited or CSV file and upserts records via PostgREST.
"""

import json
import csv
import sys
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path

# Configuration
SUPABASE_URL = "https://opbrzaegvfyjpyyrmdfe.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9wYnJ6YWVndmZ5anB5eXJtZGZlIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3NTcxODE4NSwiZXhwIjoyMDkxMjk0MTg1fQ.43H90jIDQADS0qKKrAk3dkQEy6hba7pMj3VssdeAWS4"
TABLE_NAME = "hcpcs_codes"
BATCH_SIZE = 500

def detect_delimiter(filepath):
    """Auto-detect if file is tab or pipe delimited."""
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        first_line = f.readline()
        if '\t' in first_line:
            return '\t'
        elif '|' in first_line:
            return '|'
        elif ',' in first_line:
            return ','
    return '\t'  # default to tab

def parse_date(date_str):
    """Parse various date formats. Return YYYY-MM-DD or None."""
    if not date_str or date_str.strip() == '':
        return None

    date_str = date_str.strip()
    formats = [
        '%m/%d/%Y',
        '%m-%d-%Y',
        '%Y-%m-%d',
        '%Y/%m/%d',
        '%m%d%Y',
        '%Y%m%d',
    ]

    for fmt in formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.strftime('%Y-%m-%d')
        except ValueError:
            continue

    return None

def read_hcpcs_file(filepath):
    """Read HCPCS file and yield records."""
    delimiter = detect_delimiter(filepath)
    print(f"Detected delimiter: {repr(delimiter)}")

    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        reader = csv.DictReader(f, delimiter=delimiter)

        # Inspect headers
        if reader.fieldnames:
            print(f"File headers: {reader.fieldnames}")

        for row_num, row in enumerate(reader, 1):
            # Normalize keys (handle various column name variations)
            row_lower = {k.lower().strip(): v for k, v in row.items()}

            # Extract HCPC code (primary key)
            code = (row_lower.get('hcpc') or
                   row_lower.get('code') or
                   row_lower.get('hcpcs code') or
                   '').strip()

            if not code:
                print(f"Warning: Row {row_num} missing code, skipping")
                continue

            # Extract descriptions
            description = (row_lower.get('description') or
                          row_lower.get('short description') or
                          row_lower.get('short_description') or
                          '').strip()[:500]

            long_description = (row_lower.get('long description') or
                               row_lower.get('long_description') or
                               row_lower.get('description') or
                               '').strip()

            # If no long description, use description
            if not long_description and description:
                long_description = description

            # Extract code type (first letter of code)
            code_type = code[0] if code else None

            # Extract dates
            effective_date = parse_date(
                row_lower.get('add date') or
                row_lower.get('add_date') or
                row_lower.get('effective date') or
                row_lower.get('effective_date') or
                ''
            )

            termination_date = parse_date(
                row_lower.get('termination date') or
                row_lower.get('termination_date') or
                row_lower.get('deletion effective date') or
                ''
            )

            # Extract pricing indicator
            pricing_indicator = (row_lower.get('pricing indicator') or
                               row_lower.get('pricing_indicator') or
                               row_lower.get('pi') or
                               '').strip()

            if not pricing_indicator:
                pricing_indicator = None

            record = {
                'code': code,
                'description': description or code,
                'long_description': long_description or code,
                'code_type': code_type,
                'effective_date': effective_date,
                'termination_date': termination_date,
                'pricing_indicator': pricing_indicator,
                'data_source': 'CMS HCPCS',
                'source_url': 'https://www.cms.gov/medicare/coding-billing/healthcare-common-procedure-system'
            }

            yield record

def upsert_batch(records):
    """Upsert a batch of records to Supabase via PostgREST."""
    if not records:
        return 0

    url = f"{SUPABASE_URL}/rest/v1/{TABLE_NAME}"

    headers = {
        'apikey': SUPABASE_KEY,
        'Authorization': f'Bearer {SUPABASE_KEY}',
        'Content-Type': 'application/json',
        'Prefer': 'resolution=merge-duplicates'
    }

    data = json.dumps(records).encode('utf-8')

    req = urllib.request.Request(
        url,
        data=data,
        headers=headers,
        method='POST'
    )

    try:
        with urllib.request.urlopen(req) as response:
            status = response.status
            body = response.read().decode('utf-8')

            if status not in (200, 201):
                print(f"ERROR: HTTP {status}")
                print(f"Response: {body[:200]}")
                return 0

            return len(records)

    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8')

        # Check if error is due to conflict - if so, try DELETE + INSERT
        if e.code == 409 and 'duplicate key' in error_body.lower():
            # Extract conflicting codes and delete them
            return insert_with_delete_on_conflict(records)
        else:
            print(f"HTTP Error {e.code}: {e.reason}")
            print(f"Response: {error_body[:500]}")
            return 0
    except Exception as e:
        print(f"Error upserting batch: {e}")
        return 0

def insert_with_delete_on_conflict(records):
    """Delete existing codes and insert new ones."""
    # Extract codes
    codes = [r['code'] for r in records]

    # Delete existing codes
    for code in codes:
        url = f"{SUPABASE_URL}/rest/v1/{TABLE_NAME}?code=eq.{code}"
        headers = {
            'apikey': SUPABASE_KEY,
            'Authorization': f'Bearer {SUPABASE_KEY}',
            'Content-Type': 'application/json',
        }

        req = urllib.request.Request(url, data=b'', headers=headers, method='DELETE')
        try:
            with urllib.request.urlopen(req) as response:
                pass  # Deleted
        except:
            pass  # Already gone or other error

    # Now insert
    url = f"{SUPABASE_URL}/rest/v1/{TABLE_NAME}"
    headers = {
        'apikey': SUPABASE_KEY,
        'Authorization': f'Bearer {SUPABASE_KEY}',
        'Content-Type': 'application/json',
    }

    data = json.dumps(records).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers=headers, method='POST')

    try:
        with urllib.request.urlopen(req) as response:
            if response.status in (200, 201):
                return len(records)
    except:
        pass

    return 0

def main():
    # Look for HCPCS file
    hcpcs_file = Path('/tmp/hcpcs_data.txt')

    if not hcpcs_file.exists():
        # Check for unzipped file
        for candidate in Path('/tmp').glob('**/HCPC*.txt') + Path('/tmp').glob('**/*anweb*'):
            if candidate.is_file():
                hcpcs_file = candidate
                break

    if not hcpcs_file.exists():
        print(f"Error: HCPCS file not found at {hcpcs_file}")
        print("Expected file at /tmp/hcpcs_data.txt or similar")
        sys.exit(1)

    print(f"Reading HCPCS file: {hcpcs_file}")
    print(f"File size: {hcpcs_file.stat().st_size} bytes\n")

    # First pass: examine format
    with open(hcpcs_file, 'r', encoding='utf-8', errors='ignore') as f:
        print("First 5 lines of file:")
        for i in range(5):
            print(f"  {f.readline().rstrip()}")
    print()

    # Ingest records
    batch = []
    total_ingested = 0

    for record in read_hcpcs_file(hcpcs_file):
        batch.append(record)

        if len(batch) >= BATCH_SIZE:
            inserted = upsert_batch(batch)
            total_ingested += inserted
            print(f"Upserted batch of {inserted} records. Total: {total_ingested}")
            batch = []

    # Final batch
    if batch:
        inserted = upsert_batch(batch)
        total_ingested += inserted
        print(f"Upserted final batch of {inserted} records. Total: {total_ingested}")

    print(f"\n✓ Ingestion complete!")
    print(f"  Total records inserted: {total_ingested}")
    print(f"  Supabase table: {TABLE_NAME}")
    print(f"  Endpoint: {SUPABASE_URL}/rest/v1/{TABLE_NAME}")

if __name__ == '__main__':
    main()

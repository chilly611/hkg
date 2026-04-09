#!/usr/bin/env python3
"""
Fast HCPCS ingestion - direct insert into Supabase.
Simpler, more direct approach using batched POST requests.
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
BATCH_SIZE = 100

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
    return '\t'

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

    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        reader = csv.DictReader(f, delimiter=delimiter)

        for row_num, row in enumerate(reader, 1):
            # Normalize keys
            row_lower = {k.lower().strip(): v for k, v in row.items()}

            code = (row_lower.get('hcpc') or
                   row_lower.get('code') or
                   '').strip()

            if not code:
                continue

            description = (row_lower.get('description') or
                          row_lower.get('short description') or
                          '').strip()[:500]

            long_description = (row_lower.get('long description') or
                               row_lower.get('description') or
                               '').strip()

            if not long_description and description:
                long_description = description

            code_type = code[0] if code else None

            effective_date = parse_date(
                row_lower.get('add date') or
                row_lower.get('add_date') or
                ''
            )

            termination_date = parse_date(
                row_lower.get('termination date') or
                row_lower.get('termination_date') or
                ''
            )

            pricing_indicator = (row_lower.get('pricing indicator') or
                               row_lower.get('pricing_indicator') or
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

def insert_batch(records):
    """Insert a batch of records to Supabase."""
    if not records:
        return 0

    url = f"{SUPABASE_URL}/rest/v1/{TABLE_NAME}"
    headers = {
        'apikey': SUPABASE_KEY,
        'Authorization': f'Bearer {SUPABASE_KEY}',
        'Content-Type': 'application/json',
    }

    data = json.dumps(records).encode('utf-8')

    req = urllib.request.Request(
        url,
        data=data,
        headers=headers,
        method='POST'
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            if response.status in (200, 201):
                return len(records)
            else:
                print(f"Warning: HTTP {response.status}")
                return 0

    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8')
        print(f"HTTP {e.code}: {e.reason}")
        print(f"  {body[:200]}")
        return 0
    except Exception as e:
        print(f"Error: {e}")
        return 0

def main():
    hcpcs_file = Path('/tmp/hcpcs_data.txt')

    if not hcpcs_file.exists():
        for candidate in list(Path('/tmp').glob('**/HCPC*.txt')) + list(Path('/tmp').glob('**/*anweb*')):
            if candidate.is_file():
                hcpcs_file = candidate
                break

    if not hcpcs_file.exists():
        print(f"Error: HCPCS file not found")
        sys.exit(1)

    print(f"Reading: {hcpcs_file}")
    print(f"Size: {hcpcs_file.stat().st_size / 1024 / 1024:.1f} MB\n")

    batch = []
    total_inserted = 0
    batch_num = 0

    for record in read_hcpcs_file(hcpcs_file):
        batch.append(record)

        if len(batch) >= BATCH_SIZE:
            batch_num += 1
            inserted = insert_batch(batch)
            total_inserted += inserted

            if inserted > 0:
                print(f"Batch {batch_num:3d}: {inserted:4d} records inserted | Total: {total_inserted:6d}")
            else:
                print(f"Batch {batch_num:3d}: FAILED")

            batch = []

    # Final batch
    if batch:
        batch_num += 1
        inserted = insert_batch(batch)
        total_inserted += inserted
        print(f"Batch {batch_num:3d}: {inserted:4d} records inserted | Total: {total_inserted:6d}")

    print(f"\n{'='*60}")
    print(f"✓ Ingestion complete!")
    print(f"  Total inserted: {total_inserted:,} records")
    print(f"  Batches: {batch_num}")
    print(f"  Table: {TABLE_NAME}")
    print(f"  Endpoint: {SUPABASE_URL}/rest/v1/{TABLE_NAME}")

if __name__ == '__main__':
    main()

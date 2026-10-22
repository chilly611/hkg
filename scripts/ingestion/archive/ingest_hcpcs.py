#!/usr/bin/env python3
"""
Ingest HCPCS Level II codes from CMS into Supabase.

Usage:
  python3 ingest_hcpcs.py                    # Downloads from CMS
  python3 ingest_hcpcs.py /path/to/file.zip # Uses local file
  python3 ingest_hcpcs.py /path/to/data.txt # Uses local data file
"""

import os
import sys
import json
import csv
import zipfile
import io
import requests
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

# Configuration
SUPABASE_URL = "https://opbrzaegvfyjpyyrmdfe.supabase.co/rest/v1/hcpcs_codes"
SERVICE_ROLE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9wYnJ6YWVndmZ5anB5eXJtZGZlIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3NTcxODE4NSwiZXhwIjoyMDkxMjk0MTg1fQ.43H90jIDQADS0qKKrAk3dkQEy6hba7pMj3VssdeAWS4"

CMS_URLS = [
    "https://www.cms.gov/files/zip/2025-alpha-numeric-hcpcs-file.zip",
    "https://www.cms.gov/files/zip/2026-alpha-numeric-hcpcs-file.zip",
    "https://www.cms.gov/files/zip/25anweb.zip",
]

BATCH_SIZE = 500


def download_hcpcs_file() -> bytes:
    """Download HCPCS file from CMS, trying multiple URLs."""
    print("Downloading HCPCS file from CMS...")
    print("  Note: This may fail if CMS URLs are not publicly accessible.")
    print()

    for url in CMS_URLS:
        try:
            print(f"  Trying: {url}")
            response = requests.get(url, timeout=30, allow_redirects=True)
            if response.status_code == 200:
                print(f"  ✓ Downloaded successfully ({len(response.content)} bytes)")
                return response.content
            else:
                print(f"  ✗ Status {response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"  ✗ Failed: {type(e).__name__}")
            continue

    # Provide helpful message
    print("\n  HCPCS files are not currently accessible from CMS URLs.")
    print("  Please:")
    print("    1. Download manually from https://www.cms.gov/")
    print("    2. Run this script with the file path as argument:")
    print("       python3 ingest_hcpcs.py /path/to/file.zip")
    print()
    raise Exception("Could not download HCPCS file from any CMS URL")


def extract_and_find_data_file(zip_content: bytes) -> tuple[str, str]:
    """Extract ZIP and find the data file. Returns (filename, content)."""
    print("Extracting ZIP file...")

    try:
        with zipfile.ZipFile(io.BytesIO(zip_content)) as z:
            files = z.namelist()
            print(f"  Found {len(files)} files in ZIP:")
            for f in files:
                print(f"    - {f}")

            # Look for common data file patterns
            data_file = None
            for pattern in ['alpha', 'hcpc', 'hcpcs', '.txt', '.csv', '.xlsx', '.xls']:
                for f in files:
                    if pattern.lower() in f.lower() and not f.startswith('__MACOSX'):
                        data_file = f
                        break
                if data_file:
                    break

            if not data_file:
                data_file = [f for f in files if not f.startswith('__MACOSX') and not f.endswith('/')][0]

            print(f"  Using data file: {data_file}")
            content = z.read(data_file).decode('utf-8', errors='replace')
            return data_file, content

    except Exception as e:
        raise Exception(f"Failed to extract ZIP: {e}")


def parse_hcpcs_data(filename: str, content: str) -> List[Dict[str, Any]]:
    """Parse HCPCS data file (supports TSV and CSV)."""
    print("Parsing HCPCS data...")

    records = []
    lines = content.split('\n')

    # Detect delimiter (tab or comma)
    delimiter = '\t' if '\t' in lines[0] else ','
    delimiter_name = 'TAB' if delimiter == '\t' else 'COMMA'
    print(f"  Detected delimiter: {delimiter_name}")

    # Parse as CSV/TSV
    reader = csv.DictReader(
        io.StringIO(content),
        delimiter=delimiter
    )

    if not reader.fieldnames:
        raise Exception("Could not detect column headers")

    print(f"  Column headers: {reader.fieldnames}")

    # Map common column names
    code_col = next((c for c in reader.fieldnames if 'hcpc' in c.lower() or 'code' in c.lower()), None)
    short_desc_col = next((c for c in reader.fieldnames if 'short' in c.lower() and 'desc' in c.lower()), None)
    long_desc_col = next((c for c in reader.fieldnames if 'long' in c.lower() and 'desc' in c.lower()), None)

    if not code_col:
        code_col = reader.fieldnames[0]
    if not short_desc_col:
        short_desc_col = reader.fieldnames[1] if len(reader.fieldnames) > 1 else code_col
    if not long_desc_col:
        long_desc_col = reader.fieldnames[2] if len(reader.fieldnames) > 2 else short_desc_col

    print(f"  Mapped columns: code={code_col}, short_desc={short_desc_col}, long_desc={long_desc_col}")

    for row_idx, row in enumerate(reader, start=1):
        try:
            code = (row.get(code_col, '') or '').strip()
            short_desc = (row.get(short_desc_col, '') or '').strip()
            long_desc = (row.get(long_desc_col, '') or '').strip()

            # Skip empty rows
            if not code:
                continue

            record = {
                "code": code,
                "description": short_desc or long_desc or code,
                "long_description": long_desc or short_desc or code,
                "code_type": code[0] if code else None,
                "effective_date": None,
                "termination_date": None,
                "pricing_indicator": None,
                "data_source": "CMS HCPCS",
                "source_url": "https://www.cms.gov/medicare/coding-billing/healthcare-common-procedure-system"
            }

            records.append(record)

            if row_idx % 1000 == 0:
                print(f"  Parsed {row_idx} rows...")

        except Exception as e:
            print(f"  Warning: Failed to parse row {row_idx}: {e}")
            continue

    print(f"  Total records parsed: {len(records)}")
    return records


def insert_into_supabase(records: List[Dict[str, Any]]) -> int:
    """Insert records into Supabase in batches."""
    print(f"Inserting {len(records)} records into Supabase...")

    headers = {
        "apikey": SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SERVICE_ROLE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates"
    }

    total_inserted = 0

    for batch_idx in range(0, len(records), BATCH_SIZE):
        batch = records[batch_idx:batch_idx + BATCH_SIZE]
        batch_num = (batch_idx // BATCH_SIZE) + 1

        try:
            print(f"  Batch {batch_num}: Inserting {len(batch)} records...", end=" ", flush=True)

            response = requests.post(
                SUPABASE_URL,
                headers=headers,
                json=batch,
                timeout=60
            )

            if response.status_code in [200, 201]:
                total_inserted += len(batch)
                print(f"✓ ({total_inserted} total)")
            else:
                print(f"✗ Status {response.status_code}")
                print(f"    Response: {response.text[:200]}")

        except Exception as e:
            print(f"✗ Error: {e}")
            continue

    return total_inserted


def main():
    """Main entry point."""
    try:
        print("=" * 70)
        print("HCPCS Code Ingestion Script")
        print("=" * 70)
        print()

        # Check for input file argument
        input_file = sys.argv[1] if len(sys.argv) > 1 else None

        if input_file:
            # Use provided file
            print(f"Using input file: {input_file}\n")

            if not os.path.exists(input_file):
                raise Exception(f"File not found: {input_file}")

            with open(input_file, 'rb') as f:
                file_content = f.read()

            # Determine if it's a ZIP or text file
            if input_file.endswith('.zip'):
                filename, content = extract_and_find_data_file(file_content)
                print(f"✓ Extracted {len(content)} characters from ZIP\n")
            else:
                filename = os.path.basename(input_file)
                content = file_content.decode('utf-8', errors='replace')
                print(f"✓ Read {len(content)} characters from file\n")
        else:
            # Download from CMS
            zip_content = download_hcpcs_file()
            print(f"✓ Downloaded {len(zip_content)} bytes\n")

            # Extract
            filename, content = extract_and_find_data_file(zip_content)
            print(f"✓ Extracted {len(content)} characters from ZIP\n")

        # Parse
        records = parse_hcpcs_data(filename, content)
        print(f"✓ Parsed {len(records)} records\n")

        if records:
            # Insert
            inserted = insert_into_supabase(records)
            print(f"✓ Inserted {inserted} records\n")

            print("=" * 70)
            print(f"SUCCESS: {inserted} HCPCS codes loaded into Supabase")
            print("=" * 70)
            return 0
        else:
            print("=" * 70)
            print("WARNING: No records parsed from file")
            print("=" * 70)
            return 1

    except Exception as e:
        print(f"\n✗ FATAL ERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""
Ingest ICD-10-PCS codes from CMS into Supabase.
Parses the CMS format and inserts via PostgREST API.
"""

import json
import urllib.request
import urllib.error
import sys
from typing import List, Dict

# Supabase configuration
SUPABASE_URL = "https://opbrzaegvfyjpyyrmdfe.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9wYnJ6YWVndmZ5anB5eXJtZGZlIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3NTcxODE4NSwiZXhwIjoyMDkxMjk0MTg1fQ.43H90jIDQADS0qKKrAk3dkQEy6hba7pMj3VssdeAWS4"
API_ENDPOINT = f"{SUPABASE_URL}/rest/v1/icd10_pcs_codes"

# ICD-10-PCS code structure
ICD10PCS_COMPONENTS = {
    0: "section",           # Position 0: Section (0-9, A-Z)
    1: "body_system",       # Position 1: Body System
    2: "root_operation",    # Position 2: Root Operation
    3: "body_part",         # Position 3: Body Part
    4: "approach",          # Position 4: Approach
    5: "device",            # Position 5: Device
    6: "qualifier"          # Position 6: Qualifier
}


def parse_icd10pcs_line(line: str) -> Dict:
    """Parse a line from the ICD-10-PCS codes file."""
    if not line.strip():
        return None

    parts = line.rstrip('\n').split(None, 1)  # Split on first whitespace
    if len(parts) < 2:
        return None

    code = parts[0].strip()
    description = parts[1].strip()

    if len(code) != 7:
        return None

    # Extract individual components
    components = {
        "code": code,
        "description": description,
        "section": code[0],
        "body_system": code[1],
        "root_operation": code[2],
        "body_part": code[3],
        "approach": code[4],
        "device": code[5],
        "qualifier": code[6],
        "version": "2025",
        "data_source": "CMS ICD-10-PCS",
        "source_url": "https://www.cms.gov/medicare/coding-billing/icd-10-codes"
    }

    return components


def batch_insert(batch: List[Dict], batch_num: int) -> bool:
    """Insert a batch of records via PostgREST API."""
    try:
        data = json.dumps(batch).encode('utf-8')

        req = urllib.request.Request(
            API_ENDPOINT,
            data=data,
            headers={
                'apikey': SUPABASE_KEY,
                'Authorization': f'Bearer {SUPABASE_KEY}',
                'Content-Type': 'application/json',
                'Prefer': 'resolution=merge-duplicates'
            },
            method='POST'
        )

        with urllib.request.urlopen(req, timeout=30) as response:
            status = response.status
            response_text = response.read().decode('utf-8')

            if status in [200, 201]:
                print(f"✓ Batch {batch_num}: {len(batch)} records inserted (HTTP {status})")
                return True
            else:
                print(f"✗ Batch {batch_num}: HTTP {status}")
                print(f"  Response: {response_text[:200]}")
                return False

    except urllib.error.HTTPError as e:
        print(f"✗ Batch {batch_num}: HTTP Error {e.code}")
        try:
            error_text = e.read().decode('utf-8')
            print(f"  Response: {error_text[:200]}")
        except:
            pass
        return False
    except Exception as e:
        print(f"✗ Batch {batch_num}: {type(e).__name__}: {str(e)[:100]}")
        return False


def ingest_from_file(filepath: str, batch_size: int = 500) -> int:
    """Read ICD-10-PCS codes from file and ingest into Supabase."""

    print(f"Ingesting ICD-10-PCS codes from: {filepath}")
    print(f"Batch size: {batch_size}")
    print(f"Target endpoint: {API_ENDPOINT}")
    print("-" * 70)

    batch = []
    total_count = 0
    batch_num = 0
    success_count = 0
    failed_batches = 0

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                record = parse_icd10pcs_line(line)

                if record:
                    batch.append(record)
                    total_count += 1

                    # Insert when batch is full
                    if len(batch) >= batch_size:
                        batch_num += 1
                        if batch_insert(batch, batch_num):
                            success_count += len(batch)
                        else:
                            failed_batches += 1
                        batch = []

                        # Progress indicator
                        if batch_num % 10 == 0:
                            print(f"  Progress: {total_count} codes processed...")

        # Insert remaining batch
        if batch:
            batch_num += 1
            if batch_insert(batch, batch_num):
                success_count += len(batch)
            else:
                failed_batches += 1

    except FileNotFoundError:
        print(f"ERROR: File not found: {filepath}")
        return 0
    except Exception as e:
        print(f"ERROR reading file: {e}")
        return success_count

    # Summary report
    print("-" * 70)
    print(f"Ingestion complete!")
    print(f"  Total codes parsed: {total_count}")
    print(f"  Total batches: {batch_num}")
    print(f"  Successful inserts: {success_count}")
    print(f"  Failed batches: {failed_batches}")
    print(f"  Success rate: {success_count/total_count*100:.1f}%" if total_count > 0 else "  Success rate: N/A")

    return success_count


if __name__ == "__main__":
    input_file = "/tmp/icd10pcs_codes_2025.txt"

    if len(sys.argv) > 1:
        input_file = sys.argv[1]

    ingest_from_file(input_file)

#!/usr/bin/env python3
"""
NDC Data Ingestion - Optimized for stability and resumability
"""

import json
import urllib.request
import urllib.error
import sys
from datetime import datetime

SUPABASE_URL = "https://opbrzaegvfyjpyyrmdfe.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9wYnJ6YWVndmZ5anB5eXJtZGZlIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3NTcxODE4NSwiZXhwIjoyMDkxMjk0MTg1fQ.43H90jIDQADS0qKKrAk3dkQEy6hba7pMj3VssdeAWS4"
TABLE_ENDPOINT = f"{SUPABASE_URL}/rest/v1/ndc_codes"
BATCH_SIZE = 100
SOURCE_FILE = "/tmp/drug-ndc-0001-of-0001.json"

def format_date(date_str):
    if not date_str or len(date_str) != 8:
        return None
    try:
        return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
    except:
        return None

def transform_ndc_record(record):
    ndc_code = record.get('product_ndc', '')
    route = record.get('route', [])
    if isinstance(route, list):
        route = route[0] if route else None

    marketing_start = record.get('marketing_start_date', '')
    marketing_start_date = format_date(marketing_start) if marketing_start else None

    dea_schedule = None
    if record.get('openfda', {}).get('dea_schedule_category'):
        dea_schedule = record['openfda']['dea_schedule_category'][0]

    ingredients = None
    if record.get('generic_name'):
        ingredients = [{"ingredient": record.get('generic_name', ''), "strength": ""}]

    return {
        "ndc_code": ndc_code,
        "proprietary_name": (record.get('brand_name') or '')[:500],
        "nonproprietary_name": (record.get('generic_name') or '')[:500],
        "dosage_form": record.get('dosage_form', ''),
        "route": route,
        "strength": None,
        "active_ingredients": ingredients,
        "manufacturer": (record.get('openfda', {}).get('manufacturer_name', [''])[0] or '')[:255],
        "labeler": (record.get('labeler_name') or '')[:255],
        "dea_schedule": dea_schedule,
        "marketing_start_date": marketing_start_date,
        "data_source": "FDA NDC",
        "source_url": "https://www.fda.gov/drugs/drug-approvals-and-databases/national-drug-code-directory"
    }

def batch_insert(batch_records, batch_num):
    if not batch_records:
        return 0

    headers = {
        'apikey': SUPABASE_KEY,
        'Authorization': f'Bearer {SUPABASE_KEY}',
        'Content-Type': 'application/json',
        'Prefer': 'resolution=merge-duplicates'
    }

    payload = json.dumps(batch_records).encode('utf-8')

    try:
        req = urllib.request.Request(TABLE_ENDPOINT, data=payload, headers=headers, method='POST')
        with urllib.request.urlopen(req, timeout=30) as response:
            if response.status in [200, 201]:
                print(f"✓ Batch {batch_num}: {len(batch_records)} records", flush=True)
                return len(batch_records)
    except urllib.error.HTTPError as e:
        if e.code == 409:
            print(f"~ Batch {batch_num}: Skipped (conflict)", flush=True)
        else:
            print(f"✗ Batch {batch_num}: HTTP {e.code}", flush=True)
    except Exception as e:
        print(f"✗ Batch {batch_num}: {type(e).__name__}", flush=True)

    return 0

print("=" * 70)
print("NDC Data Ingestion")
print("=" * 70)
print(f"Loading {SOURCE_FILE}...", flush=True)

with open(SOURCE_FILE, 'r') as f:
    data = json.load(f)

ndc_records = data.get('results', [])
print(f"Loaded {len(ndc_records)} records\n", flush=True)

print(f"Processing {len(ndc_records)} records in batches of {BATCH_SIZE}...", flush=True)
print("-" * 70, flush=True)

total_inserted = 0
batch_num = 1
batch_buffer = []

for i, record in enumerate(ndc_records):
    try:
        batch_buffer.append(transform_ndc_record(record))
        if len(batch_buffer) >= BATCH_SIZE:
            total_inserted += batch_insert(batch_buffer, batch_num)
            batch_num += 1
            batch_buffer = []
    except Exception:
        pass

if batch_buffer:
    total_inserted += batch_insert(batch_buffer, batch_num)

print("-" * 70)
print()
print("=" * 70)
print(f"COMPLETE: {total_inserted:,} / {len(ndc_records):,} records inserted")
print("=" * 70)

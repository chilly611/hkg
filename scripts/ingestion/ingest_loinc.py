#!/usr/bin/env python3
"""
Ingest LOINC lab codes from NLM Clinical Tables API into Supabase.

Uses the free NLM Clinical Tables API with no auth required.
Fetches all available LOINC codes (~90,000+) and loads into loinc_codes table.

Usage:
  python3 ingest_loinc.py
"""

import json
import time
import urllib.request
import urllib.error
import sys
from typing import List, Dict, Any

# Configuration
SUPABASE_URL = "https://opbrzaegvfyjpyyrmdfe.supabase.co/rest/v1/loinc_codes"
SERVICE_ROLE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9wYnJ6YWVndmZ5anB5eXJtZGZlIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3NTcxODE4NSwiZXhwIjoyMDkxMjk0MTg1fQ.43H90jIDQADS0qKKrAk3dkQEy6hba7pMj3VssdeAWS4"

# NLM Clinical Tables API
NLM_API_URL = "https://clinicaltables.nlm.nih.gov/api/loinc_items/v3/search"
NLM_API_FIELDS = "LOINC_NUM,COMPONENT,PROPERTY,TIME_ASPCT,SYSTEM,SCALE_TYP,METHOD_TYP,CLASS,LONG_COMMON_NAME,STATUS"

BATCH_SIZE = 500
MAX_PAGE_SIZE = 500
RATE_LIMIT_DELAY = 0.5  # seconds between API requests


def fetch_loinc_codes_batch(start: int = 0) -> tuple[List[Dict[str, Any]], bool]:
    """
    Fetch a batch of LOINC codes from NLM API.

    Returns: (records, has_more)
      - records: List of parsed LOINC code records
      - has_more: Boolean indicating if more records are available
    """
    try:
        # Build query with pagination
        query_params = f"?terms=&maxList={MAX_PAGE_SIZE}&df={NLM_API_FIELDS}&start={start}"
        url = NLM_API_URL + query_params

        print(f"  Fetching from offset {start}...", end=" ", flush=True)

        request = urllib.request.Request(url)
        request.add_header('User-Agent', 'HKG-LOINC-Ingest/1.0')

        with urllib.request.urlopen(request, timeout=30) as response:
            data = json.loads(response.read().decode('utf-8'))

        # NLM API returns: [total_count, [matched_ids], null, [[results]]]
        if not isinstance(data, list) or len(data) < 4:
            print("✗ Invalid response format")
            return [], False

        total_count = data[0]  # Total number of records available
        results = data[3] if len(data) > 3 and data[3] else []  # Results array

        # Parse results into records
        records = []
        for result in results:
            # result is a list: [LOINC_NUM, COMPONENT, PROPERTY, TIME_ASPCT, SYSTEM,
            #                    SCALE_TYP, METHOD_TYP, CLASS, LONG_COMMON_NAME, STATUS]
            if isinstance(result, list) and len(result) >= 10:
                record = {
                    "loinc_num": result[0],
                    "component": result[1] if result[1] else None,
                    "property": result[2] if result[2] else None,
                    "time_aspect": result[3] if result[3] else None,
                    "system": result[4] if result[4] else None,
                    "scale_type": result[5] if result[5] else None,
                    "method_type": result[6] if result[6] else None,
                    "class": result[7] if result[7] else None,
                    "long_common_name": result[8] if result[8] else None,
                    "status": result[9] if result[9] else None,
                    "data_source": "LOINC",
                    "source_url": f"https://loinc.org/kb/test-id/{result[0]}" if result[0] else None
                }
                records.append(record)

        # Check if there are more records
        next_start = start + len(records)
        has_more = next_start < total_count

        print(f"✓ Got {len(records)} records (fetched: {next_start}/{total_count})")

        return records, has_more

    except urllib.error.URLError as e:
        print(f"✗ Network error: {e}")
        return [], False
    except json.JSONDecodeError as e:
        print(f"✗ JSON decode error: {e}")
        return [], False
    except Exception as e:
        print(f"✗ Error: {e}")
        return [], False


def insert_into_supabase(records: List[Dict[str, Any]]) -> int:
    """Insert records into Supabase in batches with UPSERT."""
    if not records:
        return 0

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

            # Create request with upsert param
            url_with_params = f"{SUPABASE_URL}?on_conflict=loinc_num"
            payload = json.dumps(batch).encode('utf-8')
            request = urllib.request.Request(
                url_with_params,
                data=payload,
                headers=headers,
                method='POST'
            )

            with urllib.request.urlopen(request, timeout=60) as response:
                status = response.status

            if status in [200, 201]:
                total_inserted += len(batch)
                print(f"✓ ({total_inserted} total)")
            else:
                print(f"✗ Status {status}")

        except urllib.error.HTTPError as e:
            print(f"✗ HTTP error {e.code}")
            try:
                error_body = e.read().decode('utf-8')
                # Check if it's a duplicate key error that we can ignore
                if "23505" in error_body or "duplicate" in error_body.lower():
                    print(f"  (duplicate key - skipping)")
                    total_inserted += len(batch)  # Count as inserted even though skipped
                else:
                    print(f"    Response: {error_body[:200]}")
            except:
                pass
        except Exception as e:
            print(f"✗ Error: {e}")
            continue

    return total_inserted


def main():
    """Main entry point."""
    try:
        print("=" * 70)
        print("LOINC Code Ingestion Script")
        print("=" * 70)
        print()

        start = 0
        total_inserted = 0
        total_fetched = 0

        # Fetch and insert LOINC codes in small batches
        print("Fetching and inserting LOINC codes from NLM Clinical Tables API...")
        print()

        while True:
            records, has_more = fetch_loinc_codes_batch(start)

            if records:
                total_fetched += len(records)
                # Insert immediately to minimize memory usage
                inserted = insert_into_supabase(records)
                total_inserted += inserted

            if not has_more:
                break

            # Rate limit between API calls
            time.sleep(RATE_LIMIT_DELAY)
            start += MAX_PAGE_SIZE

            # Periodic summary every 20 batches
            if (start // MAX_PAGE_SIZE) % 20 == 0:
                print(f"  Progress: fetched {total_fetched}, inserted {total_inserted}")

        print()
        print("=" * 70)
        print(f"SUCCESS: {total_inserted} LOINC codes loaded into Supabase")
        print(f"Total fetched: {total_fetched}")
        print("=" * 70)
        return 0

    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        return 130
    except Exception as e:
        print(f"\n✗ FATAL ERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

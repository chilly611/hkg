#!/usr/bin/env python3
"""
RxNorm Data Ingestion Script for Supabase
Fetches drug data from NLM RxNorm API and inserts into Supabase.
Uses only stdlib Python (urllib, json, time).
"""

import json
import urllib.request
import urllib.error
import sys
import time
from typing import List, Dict, Any

# Supabase config
SUPABASE_URL = "https://opbrzaegvfyjpyyrmdfe.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9wYnJ6YWVndmZ5anB5eXJtZGZlIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3NTcxODE4NSwiZXhwIjoyMDkxMjk0MTg1fQ.43H90jIDQADS0qKKrAk3dkQEy6hba7pMj3VssdeAWS4"
SUPABASE_TABLE = "drugs"

# RxNorm API
RXNORM_BASE = "https://rxnav.nlm.nih.gov/REST"

# Batch size for inserts
BATCH_SIZE = 200
API_DELAY = 0.1  # seconds between API calls

def log(msg: str):
    """Log to stderr."""
    print(f"[RxNorm Ingest] {msg}", file=sys.stderr)

def fetch_json(url: str) -> Dict[str, Any]:
    """Fetch JSON from URL with error handling."""
    try:
        log(f"Fetching: {url}")
        req = urllib.request.Request(url)
        req.add_header('User-Agent', 'RxNorm-Ingest/1.0')
        with urllib.request.urlopen(req, timeout=30) as response:
            data = json.loads(response.read().decode('utf-8'))
        time.sleep(API_DELAY)
        return data
    except urllib.error.URLError as e:
        log(f"ERROR fetching {url}: {e}")
        return {}
    except json.JSONDecodeError as e:
        log(f"ERROR parsing JSON from {url}: {e}")
        return {}

def get_all_concepts(tty_list: str) -> List[Dict[str, str]]:
    """
    Fetch all concepts for given TTY types.
    Returns list of {rxcui, name} dicts.
    RxNorm API returns minConceptGroup.minConcept array.
    """
    url = f"{RXNORM_BASE}/allconcepts.json?tty={tty_list}"
    data = fetch_json(url)

    concepts = []
    if 'minConceptGroup' in data:
        min_concept_group = data['minConceptGroup']
        if 'minConcept' in min_concept_group:
            for item in min_concept_group['minConcept']:
                rxcui = item.get('rxcui')
                name = item.get('name')
                if rxcui and name:
                    concepts.append({
                        'rxcui': rxcui,
                        'name': name,
                        'tty': item.get('tty', ''),
                    })

    log(f"Fetched {len(concepts)} concepts for TTY: {tty_list}")
    return concepts

def get_ndcs(rxcui: str) -> List[str]:
    """Get NDC codes for a drug."""
    url = f"{RXNORM_BASE}/rxcui/{rxcui}/ndcs.json"
    data = fetch_json(url)

    ndcs = []
    if 'ndcList' in data and 'ndcItem' in data['ndcList']:
        for item in data['ndcList']['ndcItem']:
            if 'id' in item:
                ndcs.append(item['id'])

    return ndcs

def get_ingredients(rxcui: str) -> List[Dict[str, str]]:
    """Get ingredients for a drug."""
    url = f"{RXNORM_BASE}/rxcui/{rxcui}/allrelated.json"
    data = fetch_json(url)

    ingredients = []
    if 'allRelatedGroup' in data:
        for group in data['allRelatedGroup']:
            if 'conceptGroup' in group:
                for cg in group['conceptGroup']:
                    if cg.get('tty') in ['IN', 'PIN']:  # Ingredient, Precise Ingredient
                        for concept in cg.get('conceptProperties', []):
                            ingredients.append({
                                'ingredient': concept.get('name', ''),
                                'strength': '',
                                'unit': '',
                            })

    return ingredients

def get_drug_class(rxcui: str) -> str:
    """Get drug class/classification."""
    url = f"https://rxnav.nlm.nih.gov/REST/rxclass/class/byRxcui.json?rxcui={rxcui}"
    data = fetch_json(url)

    if 'rxclassList' in data and 'rxclassMinConceptItem' in data['rxclassList']:
        items = data['rxclassList']['rxclassMinConceptItem']
        if items:
            return items[0].get('className', '')

    return ''

def build_drug_record(concept: Dict[str, str]) -> Dict[str, Any]:
    """
    Build a complete drug record.
    Minimal approach: rxcui, name, basic properties.
    """
    rxcui = concept['rxcui']

    record = {
        'rxcui': rxcui,
        'name': concept.get('name', ''),
        'dosage_form': '',
        'strength': '',
        'drug_class': '',
        'ingredients': [],
        'ndc_codes': [],
        'synonyms': [],
        'data_source': 'RxNorm',
        'source_url': f"https://www.nlm.nih.gov/research/umls/rxnorm/search?search={rxcui}",
    }

    # Try to extract dosage form from name (simple heuristic)
    name_lower = concept.get('name', '').lower()
    dosage_keywords = {
        'tablet': 'TABLET',
        'capsule': 'CAPSULE',
        'liquid': 'LIQUID',
        'injection': 'INJECTION',
        'cream': 'CREAM',
        'ointment': 'OINTMENT',
        'patch': 'PATCH',
        'spray': 'SPRAY',
        'powder': 'POWDER',
        'suspension': 'SUSPENSION',
        'solution': 'SOLUTION',
    }
    for keyword, form in dosage_keywords.items():
        if keyword in name_lower:
            record['dosage_form'] = form
            break

    return record

def insert_batch(batch: List[Dict[str, Any]]) -> bool:
    """Insert a batch of records into Supabase."""
    if not batch:
        return True

    headers = {
        'apikey': SUPABASE_KEY,
        'Authorization': f'Bearer {SUPABASE_KEY}',
        'Content-Type': 'application/json',
        'Prefer': 'resolution=merge-duplicates',
    }

    url = f"{SUPABASE_URL}/rest/v1/{SUPABASE_TABLE}"
    data = json.dumps(batch).encode('utf-8')

    try:
        req = urllib.request.Request(url, data=data, headers=headers, method='POST')
        with urllib.request.urlopen(req, timeout=30) as response:
            response.read()
        log(f"Inserted {len(batch)} records successfully")
        return True
    except urllib.error.URLError as e:
        log(f"ERROR inserting batch: {e}")
        return False
    except Exception as e:
        log(f"ERROR: {e}")
        return False

def main():
    """Main ingestion flow."""
    log("Starting RxNorm data ingestion...")

    # Fetch SCD (Semantic Clinical Drug) and SBD (Semantic Branded Drug) concepts
    # These are the most useful for clinical use
    # Fetch them separately to handle API pagination/limits
    concepts = []

    for tty in ["SCD", "SBD"]:
        log(f"Fetching all concepts for TTY: {tty}")
        tty_concepts = get_all_concepts(tty)
        concepts.extend(tty_concepts)
        log(f"Fetched {len(tty_concepts)} {tty} concepts (total: {len(concepts)})")

    if not concepts:
        log("ERROR: No concepts fetched. Aborting.")
        return

    log(f"Total concepts to process: {len(concepts)}")

    # Process and batch insert
    batch = []
    inserted = 0
    skipped = 0

    for i, concept in enumerate(concepts):
        try:
            record = build_drug_record(concept)
            batch.append(record)

            # Insert when batch is full
            if len(batch) >= BATCH_SIZE:
                if insert_batch(batch):
                    inserted += len(batch)
                else:
                    skipped += len(batch)
                batch = []
                log(f"Progress: {inserted + skipped}/{len(concepts)} processed")

            # Progress indicator every 500 records
            if (i + 1) % 500 == 0:
                log(f"Processed {i + 1}/{len(concepts)} concepts...")

        except Exception as e:
            log(f"ERROR processing concept {concept.get('rxcui')}: {e}")
            skipped += 1

    # Insert remaining batch
    if batch:
        if insert_batch(batch):
            inserted += len(batch)
        else:
            skipped += len(batch)

    log(f"\n=== INGESTION COMPLETE ===")
    log(f"Total concepts: {len(concepts)}")
    log(f"Successfully inserted: {inserted}")
    log(f"Skipped/failed: {skipped}")
    log(f"Success rate: {100 * inserted / len(concepts):.1f}%")

if __name__ == '__main__':
    main()

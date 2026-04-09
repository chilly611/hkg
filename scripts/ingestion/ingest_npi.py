#!/usr/bin/env python3
"""
NPI Registry Ingestion Script
==============================
Fetches provider data from the NPI Registry API and inserts into Supabase.
Uses state-by-state iteration to manage API load and track progress.

Documentation:
- NPI Registry API: https://npiregistry.cms.hhs.gov/api/?version=2.1
- Supabase REST API: https://supabase.co/docs/guides/api

Author: Claude (XRWorkers / Healthcare Knowledge Garden)
Date: 2026-04-09
"""

import requests
import json
import time
import sys
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path

# ============================================================================
# CONFIGURATION
# ============================================================================

SUPABASE_URL = "https://opbrzaegvfyjpyyrmdfe.supabase.co"
SERVICE_ROLE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9wYnJ6YWVndmZ5anB5eXJtZGZlIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3NTcxODE4NSwiZXhwIjoyMDkxMjk0MTg1fQ.43H90jIDQADS0qKKrAk3dkQEy6hba7pMj3VssdeAWS4"

NPI_REGISTRY_API = "https://npiregistry.cms.hhs.gov/api/"
NPI_API_VERSION = "2.1"
NPI_API_LIMIT = 200  # Max records per call

# Batch size for Supabase inserts
BATCH_SIZE = 100

# States for initial ingestion (start with small set for testing)
TEST_STATES = ["WY", "VT", "AK"]  # Wyoming, Vermont, Alaska - small populations
FULL_STATES = [
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
    "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
    "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
    "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
    "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY"
]

# ============================================================================
# DATA MODELS
# ============================================================================

@dataclass
class Provider:
    """Individual provider record"""
    npi: str
    entity_type: int  # 1=individual, 2=organization
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    middle_name: Optional[str] = None
    organization_name: Optional[str] = None
    credential: Optional[str] = None
    gender: Optional[str] = None
    status: str = "active"
    enumeration_date: Optional[str] = None
    last_updated: Optional[str] = None
    data_source: str = "NPPES NPI Registry"
    source_url: Optional[str] = None


@dataclass
class ProviderAddress:
    """Provider address record"""
    npi: str
    address_type: str  # 'mailing' or 'practice'
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None
    phone: Optional[str] = None
    fax: Optional[str] = None


@dataclass
class ProviderTaxonomy:
    """Provider taxonomy/specialization record"""
    npi: str
    taxonomy_code: str
    taxonomy_description: Optional[str] = None
    is_primary: bool = False
    state: Optional[str] = None
    license_number: Optional[str] = None


# ============================================================================
# NPI REGISTRY API CLIENT
# ============================================================================

class NPIRegistryClient:
    """Handles all NPI Registry API calls with rate limiting and error handling"""

    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self.session = requests.Session()
        self.call_count = 0
        self.last_call_time = 0
        self.min_interval = 0.1  # Minimum seconds between API calls

    def _rate_limit(self):
        """Enforce rate limiting between API calls"""
        elapsed = time.time() - self.last_call_time
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self.last_call_time = time.time()

    def query_state(self, state: str, skip: int = 0) -> Tuple[List[Dict], int]:
        """
        Query NPI Registry for all providers in a state.
        Returns (providers_list, total_count)
        """
        self._rate_limit()

        params = {
            "version": NPI_API_VERSION,
            "state": state,
            "limit": NPI_API_LIMIT,
            "skip": skip,
        }

        try:
            response = self.session.get(
                NPI_REGISTRY_API,
                params=params,
                timeout=self.timeout,
            )
            response.raise_for_status()
            self.call_count += 1

            data = response.json()
            return data.get("results", []), data.get("result_count", 0)

        except requests.exceptions.RequestException as e:
            print(f"ERROR: NPI API call failed for state {state}: {e}", file=sys.stderr)
            return [], 0

    def fetch_all_providers_by_state(self, state: str) -> List[Dict]:
        """
        Fetch ALL providers for a state, handling pagination.
        """
        all_providers = []
        skip = 0

        print(f"  Fetching {state}...", end="", flush=True)

        while True:
            providers, total = self.query_state(state, skip)

            if not providers:
                break

            all_providers.extend(providers)
            skip += NPI_API_LIMIT

            if skip >= total:
                break

            # Progress indicator
            print(f" ({len(all_providers)}/{total})", end="", flush=True)
            time.sleep(0.2)

        print(f" ✓ {len(all_providers)} providers")
        return all_providers


# ============================================================================
# DATA TRANSFORMATION
# ============================================================================

class DataTransformer:
    """Transforms raw NPI API responses to Supabase schema"""

    @staticmethod
    def parse_provider(raw: Dict) -> Optional[Provider]:
        """Extract provider from NPI API response"""
        try:
            entity_type = raw.get("enumeration_type", 1)
            entity_type_int = 1 if entity_type == "Individual" else 2

            provider = Provider(
                npi=str(raw.get("number", "")).strip(),
                entity_type=entity_type_int,
                first_name=raw.get("first_name", "").strip() or None,
                last_name=raw.get("last_name", "").strip() or None,
                middle_name=raw.get("middle_name", "").strip() or None,
                organization_name=raw.get("organization_name", "").strip() or None,
                credential=raw.get("credential", "").strip() or None,
                gender=raw.get("gender", "").strip() or None,
                enumeration_date=raw.get("enumeration_date"),
                last_updated=raw.get("last_updated"),
                source_url=f"https://npiregistry.cms.hhs.gov/registry/view-record/{raw.get('number')}",
            )

            # Validate NPI is present
            if not provider.npi or len(provider.npi) != 10:
                return None

            return provider
        except Exception as e:
            print(f"WARN: Failed to parse provider: {e}", file=sys.stderr)
            return None

    @staticmethod
    def parse_addresses(raw: Dict, npi: str) -> List[ProviderAddress]:
        """Extract all addresses from NPI API response"""
        addresses = []

        # Practice location
        if raw.get("addresses"):
            for addr in raw["addresses"]:
                address_type = addr.get("address_purpose", "practice")
                if address_type.lower() == "mailing":
                    addr_type_str = "mailing"
                else:
                    addr_type_str = "practice"

                address = ProviderAddress(
                    npi=npi,
                    address_type=addr_type_str,
                    address_line1=addr.get("address_1", "").strip() or None,
                    address_line2=addr.get("address_2", "").strip() or None,
                    city=addr.get("city", "").strip() or None,
                    state=addr.get("state", "").strip() or None,
                    postal_code=addr.get("postal_code", "").strip() or None,
                    country=addr.get("country_code", "").strip() or None,
                    phone=addr.get("telephone_number", "").strip() or None,
                    fax=addr.get("fax_number", "").strip() or None,
                )
                addresses.append(address)

        return addresses

    @staticmethod
    def parse_taxonomies(raw: Dict, npi: str) -> List[ProviderTaxonomy]:
        """Extract all taxonomies from NPI API response"""
        taxonomies = []

        if raw.get("taxonomies"):
            for tax in raw["taxonomies"]:
                taxonomy = ProviderTaxonomy(
                    npi=npi,
                    taxonomy_code=tax.get("code", "").strip(),
                    taxonomy_description=tax.get("desc", "").strip() or None,
                    is_primary=tax.get("primary", False),
                    state=tax.get("state", "").strip() or None,
                    license_number=tax.get("license", "").strip() or None,
                )
                if taxonomy.taxonomy_code:
                    taxonomies.append(taxonomy)

        return taxonomies


# ============================================================================
# SUPABASE CLIENT
# ============================================================================

class SupabaseClient:
    """Handles all Supabase REST API interactions"""

    def __init__(self, url: str, service_role_key: str):
        self.url = url
        self.service_role_key = service_role_key
        self.session = requests.Session()
        self.session.headers.update({
            "apikey": service_role_key,
            "Authorization": f"Bearer {service_role_key}",
            "Content-Type": "application/json",
        })

    def insert_providers(self, providers: List[Provider]) -> Tuple[int, int]:
        """
        Batch insert providers using merge-duplicates for upsert.
        Returns (success_count, error_count)
        """
        if not providers:
            return 0, 0

        success_count = 0
        error_count = 0

        # Convert to dicts and remove None values
        data = []
        for p in providers:
            p_dict = asdict(p)
            p_dict = {k: v for k, v in p_dict.items() if v is not None}
            data.append(p_dict)

        try:
            response = self.session.post(
                f"{self.url}/rest/v1/providers",
                json=data,
                headers={
                    **self.session.headers,
                    "Prefer": "return=representation,resolution=merge-duplicates",
                },
                timeout=60,
            )

            if response.status_code in [200, 201]:
                success_count = len(providers)
                print(f"    ✓ Inserted {success_count} providers")
            else:
                error_count = len(providers)
                print(
                    f"    ✗ Insert failed: {response.status_code} - {response.text[:200]}",
                    file=sys.stderr,
                )

        except Exception as e:
            error_count = len(providers)
            print(f"    ✗ Exception: {e}", file=sys.stderr)

        return success_count, error_count

    def insert_addresses(self, addresses: List[ProviderAddress]) -> Tuple[int, int]:
        """Batch insert provider addresses"""
        if not addresses:
            return 0, 0

        success_count = 0
        error_count = 0

        # Convert to dicts, remove None values, rename npi to provider_npi
        data = []
        for a in addresses:
            a_dict = asdict(a)
            a_dict = {k: v for k, v in a_dict.items() if v is not None}
            data.append(a_dict)

        try:
            response = self.session.post(
                f"{self.url}/rest/v1/provider_addresses",
                json=data,
                headers={
                    **self.session.headers,
                    "Prefer": "return=representation,resolution=merge-duplicates",
                },
                timeout=60,
            )

            if response.status_code in [200, 201]:
                success_count = len(addresses)
                print(f"    ✓ Inserted {success_count} addresses")
            else:
                error_count = len(addresses)
                print(
                    f"    ✗ Address insert failed: {response.status_code}",
                    file=sys.stderr,
                )

        except Exception as e:
            error_count = len(addresses)
            print(f"    ✗ Exception: {e}", file=sys.stderr)

        return success_count, error_count

    def insert_taxonomies(self, taxonomies: List[ProviderTaxonomy]) -> Tuple[int, int]:
        """Batch insert provider taxonomies"""
        if not taxonomies:
            return 0, 0

        success_count = 0
        error_count = 0

        # Convert to dicts, remove None values
        data = []
        for t in taxonomies:
            t_dict = asdict(t)
            t_dict = {k: v for k, v in t_dict.items() if v is not None}
            data.append(t_dict)

        try:
            response = self.session.post(
                f"{self.url}/rest/v1/provider_taxonomies",
                json=data,
                headers={
                    **self.session.headers,
                    "Prefer": "return=representation,resolution=merge-duplicates",
                },
                timeout=60,
            )

            if response.status_code in [200, 201]:
                success_count = len(taxonomies)
                print(f"    ✓ Inserted {success_count} taxonomies")
            else:
                error_count = len(taxonomies)
                print(
                    f"    ✗ Taxonomy insert failed: {response.status_code}",
                    file=sys.stderr,
                )

        except Exception as e:
            error_count = len(taxonomies)
            print(f"    ✗ Exception: {e}", file=sys.stderr)

        return success_count, error_count


# ============================================================================
# MAIN INGESTION ORCHESTRATOR
# ============================================================================

class NPIIngestionPipeline:
    """Orchestrates the complete NPI ingestion workflow"""

    def __init__(self, test_mode: bool = True):
        self.test_mode = test_mode
        self.npi_client = NPIRegistryClient()
        self.supabase = SupabaseClient(SUPABASE_URL, SERVICE_ROLE_KEY)
        self.states = TEST_STATES if test_mode else FULL_STATES

        self.stats = {
            "providers_fetched": 0,
            "providers_inserted": 0,
            "providers_errors": 0,
            "addresses_inserted": 0,
            "addresses_errors": 0,
            "taxonomies_inserted": 0,
            "taxonomies_errors": 0,
            "states_completed": 0,
            "start_time": datetime.now(),
        }

    def process_state(self, state: str) -> None:
        """Process all providers in a single state"""
        print(f"\n--- Processing {state} ---")

        # Fetch all providers from NPI API
        raw_providers = self.npi_client.fetch_all_providers_by_state(state)
        self.stats["providers_fetched"] += len(raw_providers)

        if not raw_providers:
            print(f"  No providers found for {state}")
            self.stats["states_completed"] += 1
            return

        # Transform and insert in batches
        all_addresses = []
        all_taxonomies = []
        batch_providers = []

        for raw in raw_providers:
            # Transform provider
            provider = DataTransformer.parse_provider(raw)
            if not provider:
                continue

            batch_providers.append(provider)

            # Transform addresses
            addresses = DataTransformer.parse_addresses(raw, provider.npi)
            all_addresses.extend(addresses)

            # Transform taxonomies
            taxonomies = DataTransformer.parse_taxonomies(raw, provider.npi)
            all_taxonomies.extend(taxonomies)

            # Batch insert providers
            if len(batch_providers) >= BATCH_SIZE:
                success, errors = self.supabase.insert_providers(batch_providers)
                self.stats["providers_inserted"] += success
                self.stats["providers_errors"] += errors
                batch_providers = []

        # Final batch
        if batch_providers:
            success, errors = self.supabase.insert_providers(batch_providers)
            self.stats["providers_inserted"] += success
            self.stats["providers_errors"] += errors

        # Insert addresses in batches
        for i in range(0, len(all_addresses), BATCH_SIZE):
            batch = all_addresses[i : i + BATCH_SIZE]
            success, errors = self.supabase.insert_addresses(batch)
            self.stats["addresses_inserted"] += success
            self.stats["addresses_errors"] += errors

        # Insert taxonomies in batches
        for i in range(0, len(all_taxonomies), BATCH_SIZE):
            batch = all_taxonomies[i : i + BATCH_SIZE]
            success, errors = self.supabase.insert_taxonomies(batch)
            self.stats["taxonomies_inserted"] += success
            self.stats["taxonomies_errors"] += errors

        self.stats["states_completed"] += 1

    def run(self) -> None:
        """Execute the full ingestion pipeline"""
        print("=" * 70)
        print("NPI REGISTRY INGESTION PIPELINE")
        print("=" * 70)
        print(f"Mode: {'TEST (3 small states)' if self.test_mode else 'FULL (all 50 states)'}")
        print(f"Start time: {self.stats['start_time']}")
        print(f"States to process: {len(self.states)}")
        print("=" * 70)

        try:
            for state in self.states:
                self.process_state(state)

            # Print final report
            self.print_report()

        except KeyboardInterrupt:
            print("\n\nIngestion interrupted by user.", file=sys.stderr)
            self.print_report()
            sys.exit(1)

    def print_report(self) -> None:
        """Print final ingestion report"""
        end_time = datetime.now()
        duration = end_time - self.stats["start_time"]

        print("\n" + "=" * 70)
        print("INGESTION REPORT")
        print("=" * 70)
        print(f"Duration: {duration}")
        print(f"States completed: {self.stats['states_completed']}")
        print()
        print("PROVIDERS:")
        print(f"  Fetched: {self.stats['providers_fetched']:>8}")
        print(f"  Inserted: {self.stats['providers_inserted']:>8}")
        print(f"  Errors: {self.stats['providers_errors']:>8}")
        print()
        print("ADDRESSES:")
        print(f"  Inserted: {self.stats['addresses_inserted']:>8}")
        print(f"  Errors: {self.stats['addresses_errors']:>8}")
        print()
        print("TAXONOMIES:")
        print(f"  Inserted: {self.stats['taxonomies_inserted']:>8}")
        print(f"  Errors: {self.stats['taxonomies_errors']:>8}")
        print()
        print(f"Total API calls to NPI Registry: {self.npi_client.call_count}")
        print("=" * 70)


# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    # Parse command line args
    test_mode = True
    if len(sys.argv) > 1:
        if sys.argv[1] == "--full":
            test_mode = False
        elif sys.argv[1] == "--state":
            # Single state mode
            if len(sys.argv) > 2:
                single_state = sys.argv[2].upper()
                pipeline = NPIIngestionPipeline(test_mode=True)
                pipeline.states = [single_state]
                pipeline.run()
            else:
                print("Usage: python ingest_npi.py --state STATE_CODE", file=sys.stderr)
                sys.exit(1)
        else:
            print(f"Unknown option: {sys.argv[1]}", file=sys.stderr)
            print("Usage: python ingest_npi.py [--test (default) | --full | --state CODE]", file=sys.stderr)
            sys.exit(1)
    else:
        # Default: test mode
        pipeline = NPIIngestionPipeline(test_mode=True)
        pipeline.run()

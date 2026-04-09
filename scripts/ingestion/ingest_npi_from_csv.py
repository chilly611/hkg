#!/usr/bin/env python3
"""
NPI Registry CSV Ingestion Script
==================================
Ingests provider data from the CMS NPPES bulk data CSV files into Supabase.
Much more efficient than API-based approach.

Uses the weekly NPI data dissemination files:
- npidata_pfile_[DATE].csv - Main provider records
- othername_pfile_[DATE].csv - Alternative names
- endpoint_pfile_[DATE].csv - Endpoints/contact info
- pl_pfile_[DATE].csv - Practice locations

Author: Claude (XRWorkers / Healthcare Knowledge Garden)
Date: 2026-04-09
"""

import csv
import sys
import time
import requests
from typing import List, Dict, Optional, Tuple
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, asdict


# ============================================================================
# CONFIGURATION
# ============================================================================

SUPABASE_URL = "https://opbrzaegvfyjpyyrmdfe.supabase.co"
SERVICE_ROLE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9wYnJ6YWVndmZ5anB5eXJtZGZlIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3NTcxODE4NSwiZXhwIjoyMDkxMjk0MTg1fQ.43H90jIDQADS0qKKrAk3dkQEy6hba7pMj3VssdeAWS4"

BATCH_SIZE = 200  # Batch size for Supabase inserts


# ============================================================================
# DATA MODELS
# ============================================================================

@dataclass
class Provider:
    """Provider record mapped to Supabase schema"""
    npi: str
    entity_type: str  # 'Individual' or 'Organization'
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    middle_name: Optional[str] = None
    prefix: Optional[str] = None
    suffix: Optional[str] = None
    credential: Optional[str] = None
    organization_name: Optional[str] = None
    gender: Optional[str] = None
    sole_proprietor: Optional[bool] = None
    status: str = "active"
    enumeration_date: Optional[str] = None
    last_update_date: Optional[str] = None
    deactivation_date: Optional[str] = None
    reactivation_date: Optional[str] = None
    data_source: str = "NPPES NPI Registry"
    source_url: Optional[str] = None


@dataclass
class ProviderAddress:
    """Provider address record"""
    npi: str
    address_type: str
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
    """Provider taxonomy record"""
    npi: str
    taxonomy_code: str
    taxonomy_description: Optional[str] = None
    is_primary: bool = False
    state: Optional[str] = None
    license_number: Optional[str] = None


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
        """Batch insert providers using merge-duplicates for upsert"""
        if not providers:
            return 0, 0

        success_count = 0
        error_count = 0

        # Convert to dicts - ensure all records have same keys
        # First pass: collect all non-empty keys
        all_keys = set()
        data_dicts = []
        for p in providers:
            p_dict = asdict(p)
            # Remove None and empty string values but keep 0/False
            p_dict = {k: v for k, v in p_dict.items() if v not in (None, "")}
            all_keys.update(p_dict.keys())
            data_dicts.append(p_dict)

        # Second pass: ensure all records have all keys (fill with None for missing)
        data = []
        for p_dict in data_dicts:
            normalized = {k: p_dict.get(k, None) for k in all_keys}
            data.append(normalized)

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
                return success_count, error_count
            else:
                error_count = len(providers)
                print(
                    f"ERROR: Provider insert failed: {response.status_code} - {response.text[:200]}",
                    file=sys.stderr,
                )
                return success_count, error_count

        except Exception as e:
            error_count = len(providers)
            print(f"ERROR: {e}", file=sys.stderr)
            return success_count, error_count

    def insert_addresses(self, addresses: List[ProviderAddress]) -> Tuple[int, int]:
        """Batch insert provider addresses"""
        if not addresses:
            return 0, 0

        success_count = 0
        error_count = 0

        # Ensure all records have same keys
        all_keys = set()
        data_dicts = []
        for a in addresses:
            a_dict = asdict(a)
            # Remove None and empty string values
            a_dict = {k: v for k, v in a_dict.items() if v not in (None, "")}
            all_keys.update(a_dict.keys())
            data_dicts.append(a_dict)

        # Normalize: ensure all records have all keys
        data = []
        for a_dict in data_dicts:
            normalized = {k: a_dict.get(k, None) for k in all_keys}
            data.append(normalized)

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
                return success_count, error_count
            else:
                error_count = len(addresses)
                print(
                    f"ERROR: Address insert failed: {response.status_code}",
                    file=sys.stderr,
                )
                return success_count, error_count

        except Exception as e:
            error_count = len(addresses)
            print(f"ERROR: {e}", file=sys.stderr)
            return success_count, error_count

    def insert_taxonomies(self, taxonomies: List[ProviderTaxonomy]) -> Tuple[int, int]:
        """Batch insert provider taxonomies"""
        if not taxonomies:
            return 0, 0

        success_count = 0
        error_count = 0

        # Ensure all records have same keys
        all_keys = set()
        data_dicts = []
        for t in taxonomies:
            t_dict = asdict(t)
            # Remove None and empty string values but keep False
            t_dict = {k: v for k, v in t_dict.items() if v not in (None, "")}
            all_keys.update(t_dict.keys())
            data_dicts.append(t_dict)

        # Normalize: ensure all records have all keys
        data = []
        for t_dict in data_dicts:
            normalized = {k: t_dict.get(k, None) for k in all_keys}
            data.append(normalized)

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
                return success_count, error_count
            else:
                error_count = len(taxonomies)
                print(
                    f"ERROR: Taxonomy insert failed: {response.status_code}",
                    file=sys.stderr,
                )
                return success_count, error_count

        except Exception as e:
            error_count = len(taxonomies)
            print(f"ERROR: {e}", file=sys.stderr)
            return success_count, error_count


# ============================================================================
# CSV PARSERS
# ============================================================================

class CSVParser:
    """Parses NPPES CSV files and transforms to Supabase schema"""

    @staticmethod
    def parse_npidata_row(row: Dict[str, str], npi_index: int, total_rows: int) -> Tuple[Optional[Provider], List[ProviderAddress], List[ProviderTaxonomy]]:
        """Parse a single row from npidata CSV"""
        try:
            npi = row.get("NPI", "").strip()
            if not npi or len(npi) != 10:
                return None, [], []

            # Basic provider info
            entity_type_code = row.get("Entity Type Code", "1").strip()
            if not entity_type_code:
                entity_type_code = "1"
            # Convert 1 to Individual, 2 to Organization
            entity_type_str = "Individual" if entity_type_code == "1" else "Organization"

            # Parse sole_proprietor
            sole_prop = row.get("Is Sole Proprietor", "").strip()
            sole_proprietor = True if sole_prop == "Y" else (False if sole_prop == "N" else None)

            provider = Provider(
                npi=npi,
                entity_type=entity_type_str,
                first_name=row.get("Provider First Name", "").strip() or None,
                last_name=row.get("Provider Last Name (Legal Name)", "").strip() or None,
                middle_name=row.get("Provider Middle Name", "").strip() or None,
                prefix=row.get("Provider Name Prefix Text", "").strip() or None,
                suffix=row.get("Provider Name Suffix Text", "").strip() or None,
                credential=row.get("Provider Credential Text", "").strip() or None,
                organization_name=row.get("Provider Organization Name (Legal Business Name)", "").strip() or None,
                gender=row.get("Provider Sex Code", "").strip() or None,
                sole_proprietor=sole_proprietor,
                enumeration_date=row.get("Provider Enumeration Date"),
                last_update_date=row.get("Last Update Date"),
                deactivation_date=row.get("NPI Deactivation Date"),
                reactivation_date=row.get("NPI Reactivation Date"),
                source_url=f"https://npiregistry.cms.hhs.gov/registry/view-record/{npi}",
            )

            # Mailing address
            addresses = []
            mailing_addr1 = row.get("Provider First Line Business Mailing Address", "").strip()
            if mailing_addr1:
                addresses.append(ProviderAddress(
                    npi=npi,
                    address_type="mailing",
                    address_line1=mailing_addr1 or None,
                    address_line2=row.get("Provider Second Line Business Mailing Address", "").strip() or None,
                    city=row.get("Provider Business Mailing Address City Name", "").strip() or None,
                    state=row.get("Provider Business Mailing Address State Name", "").strip() or None,
                    postal_code=row.get("Provider Business Mailing Address Postal Code", "").strip() or None,
                    country=row.get("Provider Business Mailing Address Country Code (If outside U.S.)", "").strip() or "US",
                    phone=row.get("Provider Business Mailing Address Telephone Number", "").strip() or None,
                    fax=row.get("Provider Business Mailing Address Fax Number", "").strip() or None,
                ))

            # Practice location address
            practice_addr1 = row.get("Provider First Line Business Practice Location Address", "").strip()
            if practice_addr1:
                addresses.append(ProviderAddress(
                    npi=npi,
                    address_type="practice",
                    address_line1=practice_addr1 or None,
                    address_line2=row.get("Provider Second Line Business Practice Location Address", "").strip() or None,
                    city=row.get("Provider Business Practice Location Address City Name", "").strip() or None,
                    state=row.get("Provider Business Practice Location Address State Name", "").strip() or None,
                    postal_code=row.get("Provider Business Practice Location Address Postal Code", "").strip() or None,
                    country=row.get("Provider Business Practice Location Address Country Code (If outside U.S.)", "").strip() or "US",
                    phone=row.get("Provider Business Practice Location Address Telephone Number", "").strip() or None,
                    fax=row.get("Provider Business Practice Location Address Fax Number", "").strip() or None,
                ))

            # Extract taxonomies (1-15)
            taxonomies = []
            for i in range(1, 16):
                tax_code = row.get(f"Healthcare Provider Taxonomy Code_{i}", "").strip()
                if tax_code:
                    taxonomies.append(ProviderTaxonomy(
                        npi=npi,
                        taxonomy_code=tax_code,
                        is_primary=row.get(f"Healthcare Provider Primary Taxonomy Switch_{i}", "").strip() == "Y",
                        state=row.get(f"Provider License Number State Code_{i}", "").strip() or None,
                        license_number=row.get(f"Provider License Number_{i}", "").strip() or None,
                    ))

            # Progress indicator
            if npi_index % 1000 == 0:
                percent = (npi_index / total_rows) * 100
                print(f"  Processing... {npi_index:>7} / {total_rows} ({percent:>5.1f}%)", end="\r", flush=True)

            return provider, addresses, taxonomies

        except Exception as e:
            print(f"ERROR parsing row {npi_index}: {e}", file=sys.stderr)
            return None, [], []


# ============================================================================
# MAIN INGESTION ORCHESTRATOR
# ============================================================================

class NPICSVIngestionPipeline:
    """Orchestrates CSV-based NPI ingestion"""

    def __init__(self, csv_file: Path):
        self.csv_file = csv_file
        self.supabase = SupabaseClient(SUPABASE_URL, SERVICE_ROLE_KEY)
        self.stats = {
            "providers_read": 0,
            "providers_inserted": 0,
            "providers_errors": 0,
            "addresses_inserted": 0,
            "addresses_errors": 0,
            "taxonomies_inserted": 0,
            "taxonomies_errors": 0,
            "start_time": datetime.now(),
        }

    def run(self) -> None:
        """Execute the ingestion pipeline"""
        print("=" * 70)
        print("NPI REGISTRY CSV INGESTION PIPELINE")
        print("=" * 70)
        print(f"Source: {self.csv_file}")
        print(f"Start time: {self.stats['start_time']}")
        print("=" * 70)

        # Read CSV and count rows first
        print("\nCounting rows in CSV...")
        with open(self.csv_file, "r", encoding="utf-8") as f:
            total_rows = sum(1 for _ in f) - 1  # Exclude header
        print(f"Found {total_rows:,} provider records")

        # Process CSV in batches
        batch_providers = []
        all_addresses = []
        all_taxonomies = []
        row_index = 0

        print("\nProcessing providers...")
        with open(self.csv_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)

            for row in reader:
                row_index += 1
                provider, addresses, taxonomies = CSVParser.parse_npidata_row(row, row_index, total_rows)

                if not provider:
                    continue

                self.stats["providers_read"] += 1
                batch_providers.append(provider)
                all_addresses.extend(addresses)
                all_taxonomies.extend(taxonomies)

                # Batch insert when we hit batch size
                if len(batch_providers) >= BATCH_SIZE:
                    self._flush_batch(batch_providers, all_addresses, all_taxonomies)
                    batch_providers = []
                    all_addresses = []
                    all_taxonomies = []

        # Final batch
        if batch_providers:
            self._flush_batch(batch_providers, all_addresses, all_taxonomies)

        print("\n" * 2)  # Clear progress line
        self.print_report()

    def _flush_batch(self, providers: List[Provider], addresses: List[ProviderAddress], taxonomies: List[ProviderTaxonomy]) -> None:
        """Flush a batch of providers/addresses/taxonomies to Supabase"""
        if providers:
            success, errors = self.supabase.insert_providers(providers)
            self.stats["providers_inserted"] += success
            self.stats["providers_errors"] += errors

        if addresses:
            for i in range(0, len(addresses), BATCH_SIZE):
                batch = addresses[i : i + BATCH_SIZE]
                success, errors = self.supabase.insert_addresses(batch)
                self.stats["addresses_inserted"] += success
                self.stats["addresses_errors"] += errors

        if taxonomies:
            for i in range(0, len(taxonomies), BATCH_SIZE):
                batch = taxonomies[i : i + BATCH_SIZE]
                success, errors = self.supabase.insert_taxonomies(batch)
                self.stats["taxonomies_inserted"] += success
                self.stats["taxonomies_errors"] += errors

    def print_report(self) -> None:
        """Print final ingestion report"""
        end_time = datetime.now()
        duration = end_time - self.stats["start_time"]

        print("=" * 70)
        print("INGESTION REPORT")
        print("=" * 70)
        print(f"Duration: {duration}")
        print()
        print("PROVIDERS:")
        print(f"  Read: {self.stats['providers_read']:>8}")
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
        print("=" * 70)


# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python ingest_npi_from_csv.py <path_to_csv_file>", file=sys.stderr)
        print("", file=sys.stderr)
        print("Example:", file=sys.stderr)
        print("  python ingest_npi_from_csv.py npidata_pfile_20260330-20260405.csv", file=sys.stderr)
        sys.exit(1)

    csv_path = Path(sys.argv[1])
    if not csv_path.exists():
        print(f"ERROR: File not found: {csv_path}", file=sys.stderr)
        sys.exit(1)

    if not csv_path.name.startswith("npidata_"):
        print(f"WARNING: File doesn't appear to be NPI data file: {csv_path.name}", file=sys.stderr)

    pipeline = NPICSVIngestionPipeline(csv_path)
    pipeline.run()

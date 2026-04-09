#!/usr/bin/env python3
"""
Seed state medical boards reference table in Supabase.
Uses only stdlib (urllib, json).
"""

import urllib.request
import json
import uuid
from typing import List, Dict, Any

# Supabase config
SUPABASE_URL = "https://opbrzaegvfyjpyyrmdfe.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9wYnJ6YWVndmZ5anB5eXJtZGZlIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3NTcxODE4NSwiZXhwIjoyMDkxMjk0MTg1fQ.43H90jIDQADS0qKKrAk3dkQEy6hba7pMj3VssdeAWS4"
TABLE = "state_medical_boards"

# IMLC members as of 2024
IMLC_MEMBERS = {
    "AL", "AZ", "CO", "DC", "DE", "GA", "HI", "IA", "ID", "IL", "IN", "KS", "KY",
    "LA", "ME", "MD", "MI", "MN", "MS", "MT", "NE", "NH", "NV", "NJ", "ND", "OH",
    "OK", "PA", "SC", "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY"
}

# State medical boards data
STATES_DATA = [
    {
        "state_code": "AL",
        "state_name": "Alabama",
        "board_name": "Alabama Board of Medical Examiners",
        "board_url": "https://www.albme.org/",
        "lookup_url": "https://www.albme.org/verification/",
        "data_fields_available": ["name", "license_number", "status", "expiration_date", "specialty"],
        "update_frequency": "daily",
    },
    {
        "state_code": "AK",
        "state_name": "Alaska",
        "board_name": "Alaska State Medical Board",
        "board_url": "https://www.commerce.alaska.gov/web/cbpl/professionallicensing/occupations/physician/",
        "lookup_url": "https://www.commerce.alaska.gov/web/cbpl/publicsearch/",
        "data_fields_available": ["name", "license_number", "status", "expiration_date"],
        "update_frequency": "weekly",
    },
    {
        "state_code": "AZ",
        "state_name": "Arizona",
        "board_name": "Arizona Medical Board",
        "board_url": "https://medicalboard.az.gov/",
        "lookup_url": "https://medicalboard.az.gov/public-search/",
        "data_fields_available": ["name", "license_number", "status", "expiration_date", "specialty", "education"],
        "update_frequency": "daily",
    },
    {
        "state_code": "AR",
        "state_name": "Arkansas",
        "board_name": "Arkansas State Medical Board",
        "board_url": "https://www.armedicalboard.org/",
        "lookup_url": "https://www.armedicalboard.org/physicians/",
        "data_fields_available": ["name", "license_number", "status", "expiration_date", "specialty"],
        "update_frequency": "weekly",
    },
    {
        "state_code": "CA",
        "state_name": "California",
        "board_name": "California Medical Board",
        "board_url": "https://www.mbc.ca.gov/",
        "lookup_url": "https://www.mbc.ca.gov/applicants-licensees/physician-surgeon/verify-physician-surgeon-license/",
        "data_fields_available": ["name", "license_number", "status", "expiration_date", "specialty", "education", "complaints"],
        "update_frequency": "daily",
    },
    {
        "state_code": "CO",
        "state_name": "Colorado",
        "board_name": "Colorado Medical Board",
        "board_url": "https://dora.colorado.gov/division-professions-occupations/medical-board",
        "lookup_url": "https://dora.colorado.gov/pocketcard/",
        "data_fields_available": ["name", "license_number", "status", "expiration_date", "specialty"],
        "update_frequency": "daily",
    },
    {
        "state_code": "CT",
        "state_name": "Connecticut",
        "board_name": "Connecticut Department of Public Health Medical Board",
        "board_url": "https://portal.ct.gov/dph/Public_Health_Preparedness/Licensure/Medical-Board",
        "lookup_url": "https://www.sos.ct.gov/sots/registry.aspx",
        "data_fields_available": ["name", "license_number", "status", "expiration_date"],
        "update_frequency": "weekly",
    },
    {
        "state_code": "DE",
        "state_name": "Delaware",
        "board_name": "Delaware State Medical Society & Board of Medical Licensure",
        "board_url": "https://dnrec.delaware.gov/health-social-services/division-public-health/physicians/",
        "lookup_url": "https://dnrec.delaware.gov/health-social-services/division-public-health/physicians/physician-lookup/",
        "data_fields_available": ["name", "license_number", "status", "expiration_date", "specialty"],
        "update_frequency": "weekly",
    },
    {
        "state_code": "DC",
        "state_name": "District of Columbia",
        "board_name": "District of Columbia Board of Medicine",
        "board_url": "https://doee.dc.gov/service/board-medicine",
        "lookup_url": "https://doee.dc.gov/service/verify-professional-license",
        "data_fields_available": ["name", "license_number", "status", "expiration_date", "specialty"],
        "update_frequency": "weekly",
    },
    {
        "state_code": "FL",
        "state_name": "Florida",
        "board_name": "Florida Board of Medicine",
        "board_url": "https://flboardofmedicine.gov/",
        "lookup_url": "https://flboardofmedicine.gov/verify-a-license/",
        "data_fields_available": ["name", "license_number", "status", "expiration_date", "specialty", "education"],
        "update_frequency": "daily",
    },
    {
        "state_code": "GA",
        "state_name": "Georgia",
        "board_name": "Georgia Composite Medical Board",
        "board_url": "https://sos.ga.gov/plb/medical",
        "lookup_url": "https://sos.ga.gov/plb/medical/verification.html",
        "data_fields_available": ["name", "license_number", "status", "expiration_date", "specialty"],
        "update_frequency": "daily",
    },
    {
        "state_code": "HI",
        "state_name": "Hawaii",
        "board_name": "Hawaii Board of Medicine",
        "board_url": "https://health.hawaii.gov/about/boards-and-commissions/",
        "lookup_url": "https://hca.hawaii.gov/hca-app-store/dcca-license-lookup/",
        "data_fields_available": ["name", "license_number", "status", "expiration_date"],
        "update_frequency": "weekly",
    },
    {
        "state_code": "ID",
        "state_name": "Idaho",
        "board_name": "Idaho State Board of Medicine",
        "board_url": "https://bom.idaho.gov/",
        "lookup_url": "https://bom.idaho.gov/verification/",
        "data_fields_available": ["name", "license_number", "status", "expiration_date", "specialty"],
        "update_frequency": "daily",
    },
    {
        "state_code": "IL",
        "state_name": "Illinois",
        "board_name": "Illinois Department of Financial and Professional Regulation (IDFPR) Medical Board",
        "board_url": "https://www.idfpr.com/",
        "lookup_url": "https://ilehealth.illinois.gov/Lookup/",
        "data_fields_available": ["name", "license_number", "status", "expiration_date", "specialty"],
        "update_frequency": "daily",
    },
    {
        "state_code": "IN",
        "state_name": "Indiana",
        "board_name": "Indiana Medical Licensing Board",
        "board_url": "https://www.in.gov/pla/medical-licensing-board/",
        "lookup_url": "https://www.in.gov/pla/health-professions/lookup-license/",
        "data_fields_available": ["name", "license_number", "status", "expiration_date", "specialty"],
        "update_frequency": "daily",
    },
    {
        "state_code": "IA",
        "state_name": "Iowa",
        "board_name": "Iowa Board of Medicine",
        "board_url": "https://medicalboard.iowa.gov/",
        "lookup_url": "https://medicalboard.iowa.gov/physician-information/physician-verification/",
        "data_fields_available": ["name", "license_number", "status", "expiration_date", "specialty"],
        "update_frequency": "daily",
    },
    {
        "state_code": "KS",
        "state_name": "Kansas",
        "board_name": "Kansas Medical Board",
        "board_url": "https://ksmb.ks.gov/",
        "lookup_url": "https://ksmb.ks.gov/verify-a-physician-license/",
        "data_fields_available": ["name", "license_number", "status", "expiration_date", "specialty"],
        "update_frequency": "daily",
    },
    {
        "state_code": "KY",
        "state_name": "Kentucky",
        "board_name": "Kentucky Board of Medical Licensure",
        "board_url": "https://kbml.ky.gov/",
        "lookup_url": "https://kbml.ky.gov/verify",
        "data_fields_available": ["name", "license_number", "status", "expiration_date", "specialty"],
        "update_frequency": "daily",
    },
    {
        "state_code": "LA",
        "state_name": "Louisiana",
        "board_name": "Louisiana State Board of Medical Examiners",
        "board_url": "https://www.lsbme.org/",
        "lookup_url": "https://www.lsbme.org/physician-search/",
        "data_fields_available": ["name", "license_number", "status", "expiration_date", "specialty"],
        "update_frequency": "daily",
    },
    {
        "state_code": "ME",
        "state_name": "Maine",
        "board_name": "Maine Board of Licensure in Medicine",
        "board_url": "https://www.maine.gov/dhhs/mecdc/public-health-standards/medboard/",
        "lookup_url": "https://www.maine.gov/dhhs/mecdc/public-health-standards/medboard/verification/",
        "data_fields_available": ["name", "license_number", "status", "expiration_date"],
        "update_frequency": "weekly",
    },
    {
        "state_code": "MD",
        "state_name": "Maryland",
        "board_name": "Maryland Board of Physicians",
        "board_url": "https://mhcc.maryland.gov/mhcc/pages/home/default.aspx",
        "lookup_url": "https://www.dhmh.maryland.gov/bophp/Pages/index.aspx",
        "data_fields_available": ["name", "license_number", "status", "expiration_date", "specialty"],
        "update_frequency": "daily",
    },
    {
        "state_code": "MA",
        "state_name": "Massachusetts",
        "board_name": "Massachusetts Board of Registration in Medicine",
        "board_url": "https://www.mass.gov/listings/board-of-registration-in-medicine",
        "lookup_url": "https://www.mass.gov/doc/verify-a-medical-license/download",
        "data_fields_available": ["name", "license_number", "status", "expiration_date"],
        "update_frequency": "weekly",
    },
    {
        "state_code": "MI",
        "state_name": "Michigan",
        "board_name": "Michigan Department of Licensing and Regulatory Affairs (LARA)",
        "board_url": "https://www.michigan.gov/lara",
        "lookup_url": "https://www.michigan.gov/lara/0,4601,7-154-89334_72600---,00.html",
        "data_fields_available": ["name", "license_number", "status", "expiration_date", "specialty"],
        "update_frequency": "daily",
    },
    {
        "state_code": "MN",
        "state_name": "Minnesota",
        "board_name": "Minnesota Medical Practice Board",
        "board_url": "https://www.revisor.mn.gov/boards/medical/",
        "lookup_url": "https://mn.gov/health-licensing-boards/medical-practice/",
        "data_fields_available": ["name", "license_number", "status", "expiration_date", "specialty"],
        "update_frequency": "daily",
    },
    {
        "state_code": "MS",
        "state_name": "Mississippi",
        "board_name": "Mississippi State Board of Medical Licensure",
        "board_url": "https://www.msmedicalboard.mshealth.org/",
        "lookup_url": "https://www.msmedicalboard.mshealth.org/verify/",
        "data_fields_available": ["name", "license_number", "status", "expiration_date", "specialty"],
        "update_frequency": "daily",
    },
    {
        "state_code": "MO",
        "state_name": "Missouri",
        "board_name": "Missouri State Board of Registration for the Healing Arts",
        "board_url": "https://pr.mo.gov/boards/healing-arts/",
        "lookup_url": "https://data.mo.gov/resource/ai5k-h73g.json",
        "data_fields_available": ["name", "license_number", "status", "expiration_date", "specialty"],
        "update_frequency": "daily",
    },
    {
        "state_code": "MT",
        "state_name": "Montana",
        "board_name": "Montana Board of Medical Examiners",
        "board_url": "https://dli.mt.gov/bsd/license-types/physician-surgeon-and-physician-assistant",
        "lookup_url": "https://dli.mt.gov/bsd/lists-rosters-licensees",
        "data_fields_available": ["name", "license_number", "status", "expiration_date"],
        "update_frequency": "weekly",
    },
    {
        "state_code": "NE",
        "state_name": "Nebraska",
        "board_name": "Nebraska Board of Medicine and Surgery",
        "board_url": "https://dhhs.ne.gov/licensure/Pages/Medicine.aspx",
        "lookup_url": "https://www.ne.gov/home/Sections/Licensure/Medicine",
        "data_fields_available": ["name", "license_number", "status", "expiration_date", "specialty"],
        "update_frequency": "daily",
    },
    {
        "state_code": "NV",
        "state_name": "Nevada",
        "board_name": "Nevada State Board of Medical Examiners",
        "board_url": "https://medboard.nv.gov/",
        "lookup_url": "https://medboard.nv.gov/Licensees/Verification/",
        "data_fields_available": ["name", "license_number", "status", "expiration_date", "specialty"],
        "update_frequency": "daily",
    },
    {
        "state_code": "NH",
        "state_name": "New Hampshire",
        "board_name": "New Hampshire Board of Medicine",
        "board_url": "https://www.nh.gov/nhprofessional/boards/medicine/index.htm",
        "lookup_url": "https://www.nh.gov/nhprofessional/boards/medicine/lookup.htm",
        "data_fields_available": ["name", "license_number", "status", "expiration_date", "specialty"],
        "update_frequency": "daily",
    },
    {
        "state_code": "NJ",
        "state_name": "New Jersey",
        "board_name": "New Jersey State Board of Medical Examiners",
        "board_url": "https://www.nj.gov/oag/ca/profboard/bme.html",
        "lookup_url": "https://www.njconsumeraffairs.gov/Pages/Verify-a-License.aspx",
        "data_fields_available": ["name", "license_number", "status", "expiration_date", "specialty"],
        "update_frequency": "daily",
    },
    {
        "state_code": "NM",
        "state_name": "New Mexico",
        "board_name": "New Mexico Board of Medical Examiners",
        "board_url": "https://www.env.nm.gov/bme/",
        "lookup_url": "https://www.env.nm.gov/bme/verify-license/",
        "data_fields_available": ["name", "license_number", "status", "expiration_date"],
        "update_frequency": "weekly",
    },
    {
        "state_code": "NY",
        "state_name": "New York",
        "board_name": "New York State Board of Medicine",
        "board_url": "https://www.health.ny.gov/professionals/doctors/index.htm",
        "lookup_url": "https://www.health.ny.gov/professionals/doctors/conduct/public_information/index.html",
        "data_fields_available": ["name", "license_number", "status", "expiration_date", "specialty", "education"],
        "update_frequency": "daily",
    },
    {
        "state_code": "NC",
        "state_name": "North Carolina",
        "board_name": "North Carolina Medical Board",
        "board_url": "https://www.ncmedboard.org/",
        "lookup_url": "https://www.ncmedboard.org/physician-licensure/physician-license-lookup/",
        "data_fields_available": ["name", "license_number", "status", "expiration_date", "specialty"],
        "update_frequency": "daily",
    },
    {
        "state_code": "ND",
        "state_name": "North Dakota",
        "board_name": "North Dakota State Board of Medical Examiners",
        "board_url": "https://www.ndbomex.com/",
        "lookup_url": "https://www.ndbomex.com/verification/",
        "data_fields_available": ["name", "license_number", "status", "expiration_date", "specialty"],
        "update_frequency": "daily",
    },
    {
        "state_code": "OH",
        "state_name": "Ohio",
        "board_name": "State Medical Board of Ohio",
        "board_url": "https://www.med.ohio.gov/",
        "lookup_url": "https://www.med.ohio.gov/verification",
        "data_fields_available": ["name", "license_number", "status", "expiration_date", "specialty"],
        "update_frequency": "daily",
    },
    {
        "state_code": "OK",
        "state_name": "Oklahoma",
        "board_name": "Oklahoma State Board of Medical Licensure and Supervision",
        "board_url": "https://www.okmedicalboard.org/",
        "lookup_url": "https://www.okmedicalboard.org/verification/",
        "data_fields_available": ["name", "license_number", "status", "expiration_date", "specialty"],
        "update_frequency": "daily",
    },
    {
        "state_code": "OR",
        "state_name": "Oregon",
        "board_name": "Oregon Medical Board",
        "board_url": "https://www.oregon.gov/healthcareworkforce/Pages/index.aspx",
        "lookup_url": "https://omb.oregon.gov/verification/",
        "data_fields_available": ["name", "license_number", "status", "expiration_date", "specialty"],
        "update_frequency": "daily",
    },
    {
        "state_code": "PA",
        "state_name": "Pennsylvania",
        "board_name": "Pennsylvania State Board of Medicine",
        "board_url": "https://www.dos.pa.gov/Business/Licensing/Pages/default.aspx",
        "lookup_url": "https://www.dos.pa.gov/BusinessEducation/Business/Licensing/Pages/Verification.aspx",
        "data_fields_available": ["name", "license_number", "status", "expiration_date", "specialty"],
        "update_frequency": "daily",
    },
    {
        "state_code": "RI",
        "state_name": "Rhode Island",
        "board_name": "Rhode Island Board of Medical Licensure and Discipline",
        "board_url": "https://dem.ri.gov/business/licensing/boards/medical-licensure-discipline",
        "lookup_url": "https://dem.ri.gov/business/licensing/verification",
        "data_fields_available": ["name", "license_number", "status", "expiration_date"],
        "update_frequency": "weekly",
    },
    {
        "state_code": "SC",
        "state_name": "South Carolina",
        "board_name": "South Carolina Board of Medical Examiners",
        "board_url": "https://www.llr.sc.gov/med/",
        "lookup_url": "https://www.llr.sc.gov/med/verification.asp",
        "data_fields_available": ["name", "license_number", "status", "expiration_date", "specialty"],
        "update_frequency": "daily",
    },
    {
        "state_code": "SD",
        "state_name": "South Dakota",
        "board_name": "South Dakota State Board of Medical and Osteopathic Examiners",
        "board_url": "https://dlr.sd.gov/professional-regulation/medical-and-osteopathic-examiners/",
        "lookup_url": "https://dlr.sd.gov/professional-regulation/search-license/",
        "data_fields_available": ["name", "license_number", "status", "expiration_date", "specialty"],
        "update_frequency": "daily",
    },
    {
        "state_code": "TN",
        "state_name": "Tennessee",
        "board_name": "Tennessee Board of Medical Examiners",
        "board_url": "https://www.tn.gov/health/health-program-areas/health-licensure-and-regulation/boards/medical-examiners-board.html",
        "lookup_url": "https://tn.gov/health/health-program-areas/health-licensure-and-regulation/boards/medical-examiners-board/verify-a-license.html",
        "data_fields_available": ["name", "license_number", "status", "expiration_date", "specialty"],
        "update_frequency": "daily",
    },
    {
        "state_code": "TX",
        "state_name": "Texas",
        "board_name": "Texas Medical Board",
        "board_url": "https://www.tmb.state.tx.us/",
        "lookup_url": "https://www.tmb.state.tx.us/verification/",
        "data_fields_available": ["name", "license_number", "status", "expiration_date", "specialty", "education"],
        "update_frequency": "daily",
    },
    {
        "state_code": "UT",
        "state_name": "Utah",
        "board_name": "Utah State Board of Medicine",
        "board_url": "https://dopl.utah.gov/",
        "lookup_url": "https://dopl.utah.gov/verifications/",
        "data_fields_available": ["name", "license_number", "status", "expiration_date", "specialty"],
        "update_frequency": "daily",
    },
    {
        "state_code": "VT",
        "state_name": "Vermont",
        "board_name": "Vermont Board of Medical Practice",
        "board_url": "https://sos.vermont.gov/professional-regulation/",
        "lookup_url": "https://sos.vermont.gov/professional-regulation/board-of-medical-practice/",
        "data_fields_available": ["name", "license_number", "status", "expiration_date"],
        "update_frequency": "weekly",
    },
    {
        "state_code": "VA",
        "state_name": "Virginia",
        "board_name": "Virginia Board of Medicine",
        "board_url": "https://www.dhp.virginia.gov/medicine/",
        "lookup_url": "https://www.dhp.virginia.gov/Verification/",
        "data_fields_available": ["name", "license_number", "status", "expiration_date", "specialty"],
        "update_frequency": "daily",
    },
    {
        "state_code": "WA",
        "state_name": "Washington",
        "board_name": "Washington Medical Commission",
        "board_url": "https://doh.wa.gov/",
        "lookup_url": "https://doh.wa.gov/licenses-permits-and-certificates/provider-credential-search",
        "data_fields_available": ["name", "license_number", "status", "expiration_date", "specialty"],
        "update_frequency": "daily",
    },
    {
        "state_code": "WV",
        "state_name": "West Virginia",
        "board_name": "West Virginia Board of Medicine",
        "board_url": "https://dhhr.wv.gov/",
        "lookup_url": "https://dhhr.wv.gov/office-health-facility-licensure/",
        "data_fields_available": ["name", "license_number", "status", "expiration_date", "specialty"],
        "update_frequency": "weekly",
    },
    {
        "state_code": "WI",
        "state_name": "Wisconsin",
        "board_name": "Wisconsin Medical Examining Board",
        "board_url": "https://dsps.wi.gov/industry/medical-examining-board/",
        "lookup_url": "https://dsps.wi.gov/industry/medical-examining-board/verify-a-license/",
        "data_fields_available": ["name", "license_number", "status", "expiration_date", "specialty"],
        "update_frequency": "daily",
    },
    {
        "state_code": "WY",
        "state_name": "Wyoming",
        "board_name": "Wyoming Board of Medicine",
        "board_url": "https://health.wyo.gov/publichealth/medical-licensing/",
        "lookup_url": "https://health.wyo.gov/publichealth/medical-licensing/license-verification/",
        "data_fields_available": ["name", "license_number", "status", "expiration_date", "specialty"],
        "update_frequency": "daily",
    },
]


def build_records() -> List[Dict[str, Any]]:
    """Build list of records with generated UUIDs and IMLC membership."""
    records = []
    for state_data in STATES_DATA:
        record = {
            "id": str(uuid.uuid4()),
            "state_code": state_data["state_code"],
            "state_name": state_data["state_name"],
            "board_name": state_data["board_name"],
            "board_url": state_data["board_url"],
            "lookup_url": state_data["lookup_url"],
            "has_api": False,
            "api_url": None,
            "data_fields_available": state_data["data_fields_available"],
            "update_frequency": state_data["update_frequency"],
            "compact_member": state_data["state_code"] in IMLC_MEMBERS,
            "notes": None,
        }
        records.append(record)
    return records


def insert_records(records: List[Dict[str, Any]]) -> None:
    """Insert records into Supabase via PostgREST."""
    url = f"{SUPABASE_URL}/rest/v1/{TABLE}"

    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates",
    }

    body = json.dumps(records).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=body,
        headers=headers,
        method="POST",
    )

    try:
        with urllib.request.urlopen(req) as response:
            status = response.status
            response_text = response.read().decode("utf-8")
            print(f"Status: {status}")
            print(f"Response: {response_text}")
            if status in [200, 201]:
                print(f"\nSuccessfully inserted {len(records)} records!")
            else:
                print(f"\nWarning: Unexpected status code {status}")
    except urllib.error.HTTPError as e:
        error_text = e.read().decode("utf-8")
        print(f"HTTP Error {e.code}: {error_text}")
        raise
    except Exception as e:
        print(f"Error: {e}")
        raise


def main():
    """Main entry point."""
    print("Building state medical boards records...")
    records = build_records()
    print(f"Built {len(records)} records")

    print("\nSample record:")
    print(json.dumps(records[0], indent=2))

    print(f"\nInserting {len(records)} records into Supabase...")
    insert_records(records)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Texas Medical Board licensure ingestion. Downloads "DataSet-01-All Licenses" (tm3v-pfq9) from Texas
Open Data, records the artifact and the run, matches each license to an NPI, and writes this run's
snapshot of matched rows into state_license_lookups and provider_adverse_actions.

The open-data file already carries Disciplinary Status, License Status and Current Board Action, so
the ORSSP monthly reports are not needed for board actions. It carries no NPI, so matches are
license_number_exact or name_state_taxonomy (see boards/common.py).

source_published_at: rowsUpdatedAt in the dataset's metadata (the publisher's last row update); if that
cannot be read, the CSV's HTTP Last-Modified; otherwise NULL with [CONFIRM] in run_notes.

Usage:
  python3 boards/tx_tmb.py              # full run against the live database
  python3 boards/tx_tmb.py --dry-run    # download, parse and match; writes nothing
  python3 boards/tx_tmb.py --run-id ID  # adopt a run opened by poll_sources.py
"""
import argparse
import csv
import json
import tempfile
from collections import Counter
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

import common
from common import LicenseRow, Matcher, assign_keys, log, report, status_guard
from core_run import Rest, download, fetch_text, run_source

SOURCE = "Texas Medical Board licensure file"
STATE = "TX"
DATASET = "tm3v-pfq9"
META_URL = f"https://data.texas.gov/api/views/{DATASET}.json"
FILE_URL = f"https://data.texas.gov/api/views/{DATASET}/rows.csv?accessType=DOWNLOAD"
SOURCE_URL = f"https://data.texas.gov/d/{DATASET}"
PLACEHOLDER_NUMBERS = {"PHYTEMP", "PATEMP", "ACTEMP"}  # shared by every temporary license of that kind

# Registration Status -> normalized_status. Keys are the board's strings, upper-cased (the file mixes
# 'Terminated' and 'TERMINATED'). A string not in this table maps to 'unknown', never 'active'.
REGISTRATION_STATUS = {
    "ACTIVE": "active",
    "PERMIT ISSUED": "active",
    "LICENSE ISSUED": "active",
    "ISSUED": "active",
    "TEXAS LICENSE ISSUED": "active",
    "TEXAS ISSUED": "active",
    "RELICENSURE LICENSE ISSUED": "active",
    "VOLUNTARY CHARITY CARE ONLY": "active",
    "CANC NON-RENEWAL": "expired",
    "CANCELLED FOR NONRENEWAL": "expired",
    "CANCELLED FOR NON-RENEWAL": "expired",
    "CANCELLED NON-RENEWAL": "expired",
    "CANCELLED,DID NOT RENEW": "expired",
    "CONSIDERED CANCELLED": "expired",
    "PERMIT EXPIRED": "expired",
    "EXPIRED": "expired",
    "DELINQUENT": "expired",
    "DELINQUENT - INCOMPLETE REGISTRATION": "expired",
    "DELINQUENT - ADDITIONAL PENALTY": "expired",
    "PERMIT TERMINATED": "inactive",
    "TERMINATED": "inactive",
    "CANCELLED": "inactive",
    "CANCELLED BY REQUEST": "inactive",
    "BOARD CANCELLED BY REQUEST": "inactive",
    "DECEASED": "inactive",
    "TEXAS RETIRED": "inactive",
    "TEXAS RETIRED - EMERITUS": "inactive",
    "NON-STANDARD RETIRED AFFIDAVIT": "inactive",
    "NOT ACTIVE": "inactive",
    "INACTIVE - NO LONGER REQUIRED BY STATUTE": "inactive",
    "INACTIVE/OUT OF STATE": "inactive",
    "LICENSE SUPERSEDED - OTHER LICENSE ISSUED": "inactive",
    "CHANGE PROGRAM": "inactive",
    "APPLIED FOR RELICENSURE": "inactive",
    "INACTIVE PERMIT APPLICATION": "inactive",
    "WITHDRAWN APPLICATION": "inactive",
    "SUSPENDED, ACTIVE": "suspended",
    "SUSPENDED BY BOARD-ACTIVE": "suspended",
    "SUSPENDED BY THE BOARD-ACTIVE": "suspended",
    "PERMIT SUSPENDED": "suspended",
    "TEMPORARILY SUSPENDED": "suspended",
    "ADMINISTRATIVE - LICENSE RESCINDED": "revoked",
    # Seen in the file and deliberately left 'unknown': RENEWAL, PAYMENT PROCESSING DELAY,
    # LIC. ISSUED DUE TO ADMIN ERROR, CA, and blank.
}

# Board orders that override the registration status. suspended/revoked apply whatever the registration
# says; probation applies only to a license that is otherwise active.
DISCIPLINARY_OVERLAY = {
    "SUSPENDED BY BOARD": "suspended",
    "CANCELLED BY BOARD": "revoked",
    "CANCELLED BY THE BOARD": "revoked",
    "UNDER BOARD ORDER": "probation",
}
LICENSE_STATUS_OVERLAY = {
    "SUSPENDED BY COUNTY COURT": "suspended",
    "SUSPENDED BY ATTORNEY GENERAL": "suspended",
    "PERM. LICENSE RESTRICTED": "probation",
    "TEMP. LICENSE RESTRICTED": "probation",
    "ENF NON-DISC LIC RESTRICTED": "probation",
}
SEVERITY = {"revoked": 3, "suspended": 2}


def family(license_type):
    lt = (license_type or "").upper()
    if "PHYSICIAN ASSISTANT" in lt:
        return "pa"
    if ("PHYSICIAN" in lt or lt in {"INSTITUTIONAL PERMIT", "FACULTY TEMPORARY LICENSE",
                                    "VISITING PROFESSOR TEMPORARY LICENSE",
                                    "NATIONAL HEALTH SERVICE CORPS TEMPORARY LICENSE"}):
        return "physician"
    if "RESPIRATORY CARE" in lt:
        return "rcp"
    if "RADIOLOGIC" in lt or "RADIOLOGICAL" in lt or "RADIOLOGIST ASSISTANT" in lt:
        return "mrt"
    if "ACUPUNCTUR" in lt or "ACUDETOX" in lt:
        return "acu"
    return None


def normalize_status(reg, disc, lic_status):
    """Returns (normalized_status, raw_status). raw_status is the board's own strings, labelled."""
    base = REGISTRATION_STATUS.get((reg or "").strip().upper(), "unknown")
    raw = (reg or "").strip()
    final = base
    for label, value, table in (("Disciplinary Status", disc, DISCIPLINARY_OVERLAY),
                                ("License Status", lic_status, LICENSE_STATUS_OVERLAY)):
        over = table.get((value or "").strip().upper())
        if not over:
            continue
        if over == "probation" and final != "active":
            continue
        if over != "probation" and SEVERITY.get(final, 0) >= SEVERITY[over]:
            continue
        final = over
        raw += f" | {label}: {value.strip()}"
    return final, raw


def parse_date(s):
    s = (s or "").strip()
    return datetime.strptime(s[:10], "%m/%d/%Y").strftime("%Y-%m-%d") if s else None


def actions_of(r):
    """The board-action facts in a row, verbatim, as provider_adverse_actions items."""
    out = []
    disc, lic_status = r["Disciplinary Status"].strip(), r["License Status"].strip()
    desc = r["Current Board Action Description"].strip()
    if desc or (disc and disc.upper() != "NONE"):
        out.append({
            "action_type": disc if disc and disc.upper() != "NONE" else "Board action",
            "classification": "Current Board Action",
            "action_date": parse_date(r["Current Board Action Date"]) or parse_date(r["Disciplinary Status Date"]),
            "effective_date": parse_date(r["Disciplinary Status Date"]),
            "description": desc or None,
            "raw": {k: r[k] for k in ("Disciplinary Status", "Disciplinary Status Date",
                                      "Current Board Action Date", "Current Board Action Description")},
        })
    if lic_status and lic_status.upper() != "NONE":
        out.append({
            "action_type": lic_status,
            "classification": "License Status",
            "action_date": parse_date(r["License Status Date"]),
            "effective_date": parse_date(r["License Status Date"]),
            "description": None,
            "raw": {k: r[k] for k in ("License Status", "License Status Date")},
        })
    return out


def parse_file(path):
    """Returns (header, rows, row_count, failed)."""
    rows, failed, row_count = [], 0, 0
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        header = reader.fieldnames
        for r in reader:
            row_count += 1
            try:
                number = r["License Number"].strip()
                if not r["License Type"].strip() or not number or not r["Last Name"].strip():
                    raise ValueError("missing license type, number or last name")
                status, raw_status = normalize_status(r["Registration Status"], r["Disciplinary Status"],
                                                      r["License Status"])
                fam = family(r["License Type"])
                rows.append(LicenseRow(
                    license_type=r["License Type"].strip(),
                    license_number=number,
                    family=fam,
                    npi=None,  # the file carries no NPI
                    last_name=r["Last Name"].strip(),
                    first_name=r["First Name"].strip(),
                    birth_year=r["Year of Birth"].strip() or None,
                    raw_status=raw_status,
                    normalized_status=status,
                    status_date=parse_date(r["Registration Status Date"]),
                    issue_date=parse_date(r["License Issue Date"]),
                    expiration_date=parse_date(r["License Expiration Date"]),
                    actions=actions_of(r),
                    raw=r,
                    placeholder=number.upper() in PLACEHOLDER_NUMBERS,
                    physician_active=(fam == "physician" and r["Currently Licensed"].strip() == "Y"
                                      and "TRAINING" not in r["License Type"].upper()),
                ))
            except Exception as e:
                failed += 1
                if failed <= 5:
                    log(f"unparseable row {row_count}: {e}")
    assign_keys(rows,
                base_key=lambda r: f"{r.license_type}|{r.license_number}",
                full_key=lambda r: f"{r.license_type}|{r.license_number}|{r.last_name}|{r.first_name}|"
                                   f"{r.birth_year}|{r.issue_date}")
    return header, rows, row_count, failed


def publisher_date(headers):
    try:
        meta = json.loads(fetch_text(META_URL)[0])
        ts = meta.get("rowsUpdatedAt")
        if ts:
            return (datetime.fromtimestamp(int(ts), tz=timezone.utc).isoformat(),
                    f"rowsUpdatedAt in {META_URL}")
    except Exception as e:
        log(f"could not read {META_URL}: {e}")
    if headers.get("Last-Modified"):
        return (parsedate_to_datetime(headers["Last-Modified"]).isoformat(),
                f"HTTP Last-Modified of {FILE_URL} (metadata unreadable)")
    return None, f"{META_URL} and HTTP Last-Modified"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--run-id", help="adopt a 'running' ingestion_runs row opened by poll_sources.py")
    args = ap.parse_args(argv)
    db = Rest()

    with tempfile.TemporaryDirectory(prefix="hkg_tx_tmb_") as workdir:
        def fetch():
            path = Path(workdir) / f"{DATASET}.csv"
            sha, size, headers, retrieved_at = download(FILE_URL, path)
            return path, sha, size, headers, retrieved_at

        if args.dry_run:
            path, sha, size, headers, _ = fetch()
            published, how = publisher_date(headers)
            header, rows, row_count, failed = parse_file(path)
            source_id = db.select("data_sources", {"select": "id", "name": f"eq.{SOURCE}"})[0]["id"]
            matches, outcome = Matcher(db, STATE, source_id, family).match_all(rows)
            log(f"dry run: {row_count:,} rows, {failed} unparseable, published {published} ({how}), sha256 {sha}")
            report(STATE, rows, matches, outcome, REGISTRATION_STATUS,
                   [("Disciplinary Status overlay", DISCIPLINARY_OVERLAY),
                    ("License Status overlay", LICENSE_STATUS_OVERLAY)], 0, 0)
            return

        def body(run):
            path, sha, size, headers, retrieved_at = fetch()
            run.set_published(*publisher_date(headers))
            header, rows, row_count, failed = parse_file(path)
            run.register_artifact(path, f"{DATASET}.csv", FILE_URL, sha, size, row_count, retrieved_at)
            run.check_row_count(row_count)
            status_guard(run, rows)
            common.set_board_fields(db, STATE, header)
            matches, outcome = Matcher(db, STATE, run.source_id, family).match_all(rows)
            licenses, actions = common.write_snapshot(run, STATE, SOURCE, SOURCE_URL, rows, matches, retrieved_at)
            common.prune_snapshots(run)
            text = report(STATE, rows, matches, outcome, REGISTRATION_STATUS,
                          [("Disciplinary Status overlay", DISCIPLINARY_OVERLAY),
                           ("License Status overlay", LICENSE_STATUS_OVERLAY)], licenses, actions)
            run.note(text.split("\nnormalized_status mapping")[0])
            run.counts.update(records_processed=row_count, records_added=licenses + actions,
                              records_updated=0, records_failed=failed)

        run_source(SOURCE, "full", body, db, run_id=args.run_id)


if __name__ == "__main__":
    main()

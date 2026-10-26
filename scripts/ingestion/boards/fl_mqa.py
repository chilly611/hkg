#!/usr/bin/env python3
"""
Florida DOH MQA licensure ingestion: same pipeline as tx_tmb.py (artifact, run, clocks, anomaly guard,
NPI matching ladder, run-scoped snapshot in state_license_lookups and provider_adverse_actions).

The MQA Data Download Portal (https://data-download.mqa.flhealthsource.gov/) requires a signed-in
account, so the loader does not download. A person signs in, downloads the pipe-delimited files and
their metadata documents, and passes the paths:
  - Licensure Data: profession "Medical Doctor" (and "Osteopathic Physician"), "All Statuses"
  - Practitioner Profile Data: the master table and the disciplinary/legal action tables
  - License Status Data

The column layout is read from those files, never assumed. Until FIELDS below has been filled from a
real header and its metadata document, a load refuses to start; --inspect prints what the files carry.

Usage:
  python3 boards/fl_mqa.py --inspect FILE [FILE ...]        # header, row count, distinct statuses; no writes
  python3 boards/fl_mqa.py --licensure FILE [--profile FILE ...] [--dry-run]
"""
import argparse
import csv
import hashlib
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

import common
from common import LicenseRow, Matcher, assign_keys, log, report, status_guard
from core_run import Rest, now_iso, run_source

SOURCE = "Florida MQA licensee data download"
STATE = "FL"
PORTAL_URL = "https://data-download.mqa.flhealthsource.gov/"

# Logical field -> header name in the licensure file. Filled from the file's own header and its metadata
# document; a blank value means "not confirmed yet".
FIELDS = {
    "license_number": "",
    "license_type": "",
    "last_name": "",
    "first_name": "",
    "status": "",
    "status_date": "",
    "issue_date": "",
    "expiration_date": "",
    "npi": "",          # leave blank if the file has no NPI column
}
REQUIRED = ("license_number", "license_type", "last_name", "first_name", "status")

# Board status string -> normalized_status. Filled from the distinct values --inspect prints.
# A string not in this table maps to 'unknown', never 'active'.
STATUS = {}


def read_header(path):
    with open(path, newline="", encoding="utf-8", errors="replace") as f:
        return next(csv.reader(f, delimiter="|"))


def inspect(paths):
    for p in paths:
        header = read_header(p)
        with open(p, newline="", encoding="utf-8", errors="replace") as f:
            reader = csv.reader(f, delimiter="|")
            next(reader)
            n, distinct = 0, [Counter() for _ in header]
            for row in reader:
                n += 1
                for i, v in enumerate(row[:len(header)]):
                    if len(distinct[i]) < 200:
                        distinct[i][v.strip()] += 1
        print(f"== {p}: {n:,} rows, {len(header)} columns")
        for i, col in enumerate(header):
            top = ", ".join(f"{v or '(blank)'} ({c:,})" for v, c in distinct[i].most_common(6))
            print(f"  {i:>2} {col:<40} {top[:160]}")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--inspect", nargs="+", metavar="FILE")
    ap.add_argument("--licensure", metavar="FILE")
    ap.add_argument("--profile", nargs="*", default=[], metavar="FILE")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--run-id", help="adopt a 'running' ingestion_runs row opened by poll_sources.py")
    args = ap.parse_args(argv)

    if args.inspect:
        inspect(args.inspect)
        return
    if not args.licensure:
        ap.error("--licensure FILE is required (download it from the MQA portal first)")

    missing = [k for k in REQUIRED if not FIELDS[k]]
    if missing or not STATUS:
        sys.exit(f"Florida layout not confirmed: FIELDS missing {missing}, STATUS table "
                 f"{'empty' if not STATUS else 'set'}. Run --inspect on the downloaded files, fill both from "
                 f"the real header and metadata, then load. No run was started.")
    header = read_header(args.licensure)
    absent = [v for v in FIELDS.values() if v and v not in header]
    if absent:
        sys.exit(f"columns {absent} are not in {args.licensure}; the layout changed. No run was started.")

    db = Rest()
    licensure = Path(args.licensure)

    if args.dry_run:
        header, rows, row_count, failed = parse_file(licensure)
        source_id = db.select("data_sources", {"select": "id", "name": f"eq.{SOURCE}"})[0]["id"]
        matches, outcome = Matcher(db, STATE, source_id, family).match_all(rows)
        log(f"dry run: {row_count:,} rows, {failed} unparseable")
        report(STATE, rows, matches, outcome, STATUS, [], 0, 0)
        return

    def body(run):
        sha, size = file_digest(licensure)
        run.set_published(None, f"file {licensure.name} (the portal stamps no publication date in the file)")
        header, rows, row_count, failed = parse_file(licensure)
        run.register_artifact(licensure, licensure.name, PORTAL_URL, sha, size, row_count, now_iso())
        for p in map(Path, args.profile):
            psha, psize = file_digest(p)
            if not db.select("source_artifacts", {"select": "id", "source_id": f"eq.{run.source_id}",
                                                  "sha256": f"eq.{psha}"}):
                db.insert("source_artifacts", [{"source_id": run.source_id, "file_name": p.name,
                                                "download_url": PORTAL_URL, "sha256": psha, "byte_size": psize,
                                                "retrieved_at": now_iso(),
                                                "notes": f"profile file read with run {run.id}"}])
        run.check_row_count(row_count)
        status_guard(run, rows)
        common.set_board_fields(db, STATE, header)
        matches, outcome = Matcher(db, STATE, run.source_id, family).match_all(rows)
        licenses, actions = common.write_snapshot(run, STATE, SOURCE, PORTAL_URL, rows, matches, now_iso())
        common.prune_snapshots(run)
        text = report(STATE, rows, matches, outcome, STATUS, [], licenses, actions)
        run.note(text.split("\nnormalized_status mapping")[0])
        run.counts.update(records_processed=row_count, records_added=licenses + actions,
                          records_updated=0, records_failed=failed)

    run_source(SOURCE, "full", body, db, run_id=args.run_id)


def family(license_type):
    lt = (license_type or "").upper()
    if "PHYSICIAN ASSISTANT" in lt:
        return "pa"
    if "MEDICAL DOCTOR" in lt or "OSTEOPATHIC" in lt or "PHYSICIAN" in lt:
        return "physician"
    return None


def file_digest(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest(), path.stat().st_size


def field(r, name):
    col = FIELDS[name]
    return (r.get(col) or "").strip() if col else ""


def parse_date(s):
    s = (s or "").strip()
    for fmt in ("%m/%d/%Y", "%Y-%m-%d", "%Y%m%d"):
        try:
            return datetime.strptime(s[:10], fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def parse_file(path):
    """Returns (header, rows, row_count, failed). Board actions come from the profile tables once mapped."""
    rows, failed, row_count = [], 0, 0
    with open(path, newline="", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f, delimiter="|")
        header = reader.fieldnames
        for r in reader:
            row_count += 1
            try:
                number, last = field(r, "license_number"), field(r, "last_name")
                if not number or not last:
                    raise ValueError("missing license number or last name")
                raw = field(r, "status")
                npi = field(r, "npi")
                rows.append(LicenseRow(
                    license_type=field(r, "license_type"),
                    license_number=number,
                    family=family(field(r, "license_type")),
                    npi=npi if len(npi) == 10 and npi.isdigit() else None,
                    last_name=last,
                    first_name=field(r, "first_name"),
                    birth_year=None,
                    raw_status=raw,
                    normalized_status=STATUS.get(raw.upper(), "unknown"),
                    status_date=parse_date(field(r, "status_date")),
                    issue_date=parse_date(field(r, "issue_date")),
                    expiration_date=parse_date(field(r, "expiration_date")),
                    actions=[],
                    raw=r,
                    placeholder=False,
                    physician_active=(family(field(r, "license_type")) == "physician"
                                      and STATUS.get(raw.upper()) == "active"),
                ))
            except Exception as e:
                failed += 1
                if failed <= 5:
                    log(f"unparseable row {row_count}: {e}")
    assign_keys(rows,
                base_key=lambda r: f"{r.license_type}|{r.license_number}",
                full_key=lambda r: f"{r.license_type}|{r.license_number}|{r.last_name}|{r.first_name}")
    return header, rows, row_count, failed


if __name__ == "__main__":
    main()

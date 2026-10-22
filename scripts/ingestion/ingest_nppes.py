#!/usr/bin/env python3
"""
NPPES (NPI Registry) ingestion. Finds the newest weekly V2 incremental file on the CMS NPI Files
page, records the artifact and the run, and upserts its rows into providers on npi.

source_published_at: the end date of the weekly file's range in its file name, e.g.
NPPES_Data_Dissemination_101226_101826_Weekly_V2.zip -> 2026-10-18. For a monthly file passed with
--url, the file name's month (first of the month). NULL with [CONFIRM] if neither can be read.

The 50% row-count guard compares a weekly file only with the last loaded weekly file, and a
monthly file only with the last loaded monthly file.

Usage:
  python3 ingest_nppes.py                 # newest weekly file, live database
  python3 ingest_nppes.py --url URL       # a specific NPPES zip (weekly or monthly)
  python3 ingest_nppes.py --dry-run       # download and parse; writes nothing
"""
import argparse
import csv
import io
import re
import tempfile
import urllib.parse
import zipfile
from datetime import datetime
from pathlib import Path

from core_run import Rest, chunks, download, fetch_text, in_list, log, run_source

SOURCE = "NPI Registry"
PAGE_URL = "https://download.cms.gov/nppes/NPI_Files.html"
WEEKLY_RE = re.compile(r"NPPES_Data_Dissemination_(\d{6})_(\d{6})_Weekly_V2\.zip", re.I)
MONTHLY_RE = re.compile(r"NPPES_Data_Dissemination_([A-Za-z]+)_(\d{4})_V2\.zip", re.I)
DATA_RE = re.compile(r"npidata_pfile_[\d-]+\.csv$", re.I)
BATCH = 1000


def latest_weekly():
    page, _ = fetch_text(PAGE_URL)
    links = {m.group(0): m for m in WEEKLY_RE.finditer(page)}
    if not links:
        raise RuntimeError(f"no weekly V2 file listed on {PAGE_URL} (page may be down for maintenance)")
    name = max(links, key=lambda n: datetime.strptime(links[n].group(2), "%m%d%y"))
    return name, urllib.parse.urljoin(PAGE_URL, name)


def published_from_name(name):
    m = WEEKLY_RE.search(name)
    if m:
        return datetime.strptime(m.group(2), "%m%d%y").strftime("%Y-%m-%d"), "end date of the weekly range in the file name", "weekly"
    m = MONTHLY_RE.search(name)
    if m:
        return datetime.strptime(f"{m.group(1)} {m.group(2)}", "%B %Y").strftime("%Y-%m-01"), "month in the file name", "monthly"
    return None, f"file name {name}", "other"


def convert_date(s):
    s = (s or "").strip()
    return datetime.strptime(s, "%m/%d/%Y").strftime("%Y-%m-%d") if s else None


def convert_bool(v):
    v = (v or "").strip()
    return True if v == "Y" else (False if v == "N" else None)


def text(row, col, n=255):
    v = (row.get(col) or "").strip()
    return v[:n] or None


def map_row(row):
    deact = convert_date(row.get("NPI Deactivation Date"))
    code = (row.get("NPI Deactivation Reason Code") or "").strip()
    return {
        "npi": (row.get("NPI") or "").strip(),
        "entity_type": "organization" if (row.get("Entity Type Code") or "").strip() == "2" else "individual",
        "first_name": text(row, "Provider First Name"),
        "last_name": text(row, "Provider Last Name (Legal Name)"),
        "middle_name": text(row, "Provider Middle Name"),
        "credential": text(row, "Provider Credential Text", 50),
        "prefix": text(row, "Provider Name Prefix Text", 50),
        "suffix": text(row, "Provider Name Suffix Text", 50),
        "organization_name": text(row, "Provider Organization Name (Legal Business Name)"),
        "gender": text(row, "Provider Sex Code", 10),
        "sole_proprietor": convert_bool(row.get("Is Sole Proprietor")),
        "enumeration_date": convert_date(row.get("Provider Enumeration Date")),
        "last_update_date": convert_date(row.get("Last Update Date")),
        "deactivation_date": deact,
        "reactivation_date": convert_date(row.get("NPI Reactivation Date")),
        "status": ("deactivated_for_cause" if code in ("02", "04") else "deactivated") if deact else "active",
        "data_source": "NPPES NPI Registry",
        "source_url": PAGE_URL,
    }


def data_member(z):
    members = [n for n in z.namelist() if DATA_RE.search(n) and "fileheader" not in n.lower()]
    if len(members) != 1:
        raise RuntimeError(f"expected one npidata_pfile CSV in the zip, found {members}")
    return members[0]


def count_rows(path):
    with zipfile.ZipFile(path) as z, z.open(data_member(z)) as raw:
        return sum(1 for _ in raw) - 1


def iter_records(path):
    with zipfile.ZipFile(path) as z, z.open(data_member(z)) as raw:
        for row in csv.DictReader(io.TextIOWrapper(raw, encoding="utf-8", errors="replace", newline="")):
            yield map_row(row)


def load(db, path):
    added = updated = failed = batches = 0
    batch = []

    def flush():
        nonlocal added, updated
        npis = [r["npi"] for r in batch]
        known = set()
        for chunk in chunks(npis, 300):
            known.update(r["npi"] for r in db.select("providers", {"select": "npi", "npi": in_list(chunk)}))
        db.insert("providers", batch, upsert_on="npi")
        updated += len(known)
        added += len(batch) - len(known)
        batch.clear()

    for rec in iter_records(path):
        if not (len(rec["npi"]) == 10 and rec["npi"].isdigit()):
            failed += 1
            continue
        batch.append(rec)
        if len(batch) >= BATCH:
            flush()
            batches += 1
            if batches % 50 == 0:
                log(f"  {added + updated:,} upserted")
    if batch:
        flush()
    return added, updated, failed


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--url", help="a specific NPPES zip instead of the newest weekly file")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)
    db = Rest()

    with tempfile.TemporaryDirectory(prefix="hkg_nppes_") as workdir:
        def fetch():
            if args.url:
                url = args.url
                name = Path(urllib.parse.urlparse(url).path).name
            else:
                name, url = latest_weekly()
            path = Path(workdir) / name
            sha, size, _, retrieved_at = download(url, path)
            if not zipfile.is_zipfile(path):
                raise RuntimeError(f"{name} is not a zip ({size} bytes); CMS serves a short error body for missing files")
            return name, url, path, sha, size, retrieved_at

        if args.dry_run:
            name, url, path, sha, size, _ = fetch()
            published, how, kind = published_from_name(name)
            log(f"dry run: {name} {count_rows(path):,} rows, published {published} ({how}), sha256 {sha}")
            return

        def body(run):
            name, url, path, sha, size, retrieved_at = fetch()
            published, how, kind = published_from_name(name)
            run.set_published(published, how)
            row_count = count_rows(path)
            run.register_artifact(path, name, url, sha, size, row_count, retrieved_at)
            run.check_row_count(row_count, same_kind=lambda fn: published_from_name(fn)[2] == kind)
            added, updated, failed = load(db, path)
            run.counts.update(records_processed=row_count, records_added=added,
                              records_updated=updated, records_failed=failed)

        run_type = "incremental" if not args.url or WEEKLY_RE.search(args.url) else "full"
        run_source(SOURCE, run_type, body, db)


if __name__ == "__main__":
    main()

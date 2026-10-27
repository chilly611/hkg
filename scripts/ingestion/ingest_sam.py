#!/usr/bin/env python3
"""
SAM.gov exclusions ingestion. Downloads the latest daily "Exclusions / Public V2" extract from
the public file-extract service (no API key needed), records the artifact and the run, and syncs
sam_exclusions to that snapshot.

The extract holds every active exclusion record and is refreshed daily. SAM Number is unique per
record, so the sync is keyed on it: new numbers are inserted, changed rows are updated in place,
and numbers no longer in the extract are deleted (the exclusion ended or was removed).

entity_name for individuals is "Last, First Middle", the shape receipts_for_exclusions matches on.
"Indefinite" termination dates are stored as NULL. npi is the extract's NPI field when it is a real
10-digit NPI; the placeholder 0000000000 is stored as NULL.

source_published_at: the Julian date (YYDDD) in the extract's file name inside the zip, e.g.
SAM_Exclusions_Public_Extract_V2_26293.CSV -> 2026-10-20. NULL with [CONFIRM] if it cannot be read.

Usage:
  python3 ingest_sam.py              # full run against the live database
  python3 ingest_sam.py --dry-run    # download, parse and diff; writes nothing
  python3 ingest_sam.py --run-id ID  # finish a run scripts/poll_sources.py created
"""
import argparse
import csv
import io
import json
import re
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path

from core_run import Rest, chunks, download, fetch_text, in_list, log, run_source

SOURCE = "SAM.gov"
SERVICE = "https://sam.gov/api/prod/fileextractservices/v1/api"
DOMAIN = "Exclusions/Public%20V2"
LIST_URL = f"{SERVICE}/listfiles?domain={DOMAIN}&privacy=Public"
FILE_RE = re.compile(r"SAM_Exclusions_Public_Extract_V2_(\d{2})(\d{3})\.(?:ZIP|CSV)$", re.I)
SOURCE_URL = "https://sam.gov/data-services/Exclusions"
FIELDS = ("entity_name", "cage_code", "duns_number", "exclusion_type", "exclusion_program",
          "active_date", "termination_date", "record_status", "sam_number", "npi", "data_source", "source_url")
BATCH = 500
MAX_DELETE_SHARE = 0.2


def latest_extract():
    text, _ = fetch_text(LIST_URL)
    items = json.loads(text)["_embedded"]["customS3ObjectSummaryList"]
    names = [i["displayKey"] for i in items if FILE_RE.search(i["displayKey"])]
    if not names:
        raise RuntimeError(f"no SAM_Exclusions_Public_Extract_V2 file listed at {LIST_URL}")
    name = max(names, key=lambda n: FILE_RE.search(n).groups())
    return name, f"{SERVICE}/download/{DOMAIN}/{name}?privacy=Public"


def julian_date(file_name):
    m = FILE_RE.search(file_name)
    if not m:
        return None
    return datetime.strptime("20" + m.group(1) + m.group(2), "%Y%j").strftime("%Y-%m-%d")


def clean(s, n):
    s = (s or "").strip()
    return s[:n] or None


def parse_date(s):
    s = (s or "").strip()
    if not s or s.lower() == "indefinite":
        return None
    return datetime.strptime(s, "%Y-%m-%d").strftime("%Y-%m-%d")


def sam_npi(s):
    """The extract's NPI, or None. About 12K rows carry the placeholder 0000000000, which is not an NPI;
    storing it would also hide the row from the name-only fallback in receipts_for_exclusions."""
    s = (s or "").strip()
    return s if re.fullmatch(r"\d{10}", s) and s != "0000000000" else None


def parse_zip(path):
    """Returns (inner csv name, records, row_count, failed)."""
    with zipfile.ZipFile(path) as z:
        members = [n for n in z.namelist() if n.lower().endswith(".csv")]
        if len(members) != 1:
            raise RuntimeError(f"expected one CSV in the extract, found {members}")
        inner = members[0]
        records, failed, row_count = [], 0, 0
        with z.open(inner) as raw:
            for r in csv.DictReader(io.TextIOWrapper(raw, encoding="utf-8", newline="")):
                row_count += 1
                try:
                    if r["Classification"] == "Individual" and r["Last"].strip():
                        person = " ".join(p for p in (r["First"].strip(), r["Middle"].strip()) if p)
                        name = f"{r['Last'].strip()}, {person}" if person else r["Last"].strip()
                    else:
                        name = r["Name"].strip() or " ".join(r[k].strip() for k in ("First", "Middle") if r[k].strip())
                    if not name or not r["SAM Number"].strip():
                        raise ValueError("missing name or SAM Number")
                    records.append({
                        "entity_name": name[:500],
                        "cage_code": clean(r["CAGE"], 20),
                        "duns_number": None,  # V2 extract carries UEI, not DUNS
                        "exclusion_type": clean(r["Exclusion Type"], 100),
                        "exclusion_program": clean(r["Exclusion Program"], 100),
                        "active_date": parse_date(r["Active Date"]),
                        "termination_date": parse_date(r["Termination Date"]),
                        "record_status": clean(r["Record Status"], 50),
                        "sam_number": r["SAM Number"].strip()[:50],
                        "npi": sam_npi(r["NPI"]),
                        "data_source": "SAM.gov",
                        "source_url": SOURCE_URL,
                    })
                except Exception as e:
                    failed += 1
                    if failed <= 5:
                        log(f"unparseable row {row_count}: {e}")
    return inner, records, row_count, failed


def plan_sync(db, records):
    existing = db.select_all("sam_exclusions", "id," + ",".join(FIELDS))
    by_number = {}
    duplicates = []
    for row in existing:
        if row["sam_number"] in by_number:
            duplicates.append(row["id"])
        else:
            by_number[row["sam_number"]] = row
    inserts, updates, unchanged, seen = [], [], 0, set()
    for rec in records:
        if rec["sam_number"] in seen:
            continue
        seen.add(rec["sam_number"])
        row = by_number.pop(rec["sam_number"], None)
        if row is None:
            inserts.append(rec)
        elif any(row[f] != rec[f] for f in FIELDS):
            updates.append({"id": row["id"], **rec})
        else:
            unchanged += 1
    deletes = [r["id"] for r in by_number.values()] + duplicates
    return {"existing": len(existing), "inserts": inserts, "updates": updates, "deletes": deletes,
            "unchanged": unchanged, "removed_sample": [r["entity_name"] for r in list(by_number.values())[:5]]}


def summarize(plan):
    return (f"existing {plan['existing']:,}; insert {len(plan['inserts']):,}; update {len(plan['updates']):,}; "
            f"delete {len(plan['deletes']):,} (e.g. {plan['removed_sample']}); unchanged {plan['unchanged']:,}")


def apply_sync(db, plan):
    for batch in chunks(plan["inserts"], BATCH):
        db.insert("sam_exclusions", batch)
    for batch in chunks(plan["updates"], BATCH):
        db.insert("sam_exclusions", batch, upsert_on="id")
    for batch in chunks(plan["deletes"], 200):
        db.delete("sam_exclusions", id=in_list(batch))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--run-id", help="adopt this running ingestion_runs row (set by scripts/poll_sources.py)")
    ap.add_argument("--allow-large-diff", action="store_true",
                    help=f"permit deleting more than {MAX_DELETE_SHARE:.0%} of existing rows")
    args = ap.parse_args(argv)
    db = Rest()

    with tempfile.TemporaryDirectory(prefix="hkg_sam_") as workdir:
        def fetch():
            name, url = latest_extract()
            path = Path(workdir) / name
            sha, size, _, retrieved_at = download(url, path)
            inner, records, row_count, failed = parse_zip(path)
            return name, url, path, sha, size, retrieved_at, inner, records, row_count, failed

        if args.dry_run:
            name, url, path, sha, size, _, inner, records, row_count, failed = fetch()
            log(f"dry run: {name} ({inner}) {row_count:,} rows, {failed} unparseable, "
                f"published {julian_date(inner)}, sha256 {sha}")
            log("dry run: " + summarize(plan_sync(db, records)))
            return

        def body(run):
            name, url, path, sha, size, retrieved_at, inner, records, row_count, failed = fetch()
            run.set_published(julian_date(inner), f"Julian date in extract file name {inner}")
            run.register_artifact(path, name, url, sha, size, row_count, retrieved_at)
            run.check_row_count(row_count, table_fallback=db.count("sam_exclusions"))
            plan = plan_sync(db, records)
            run.note(summarize(plan))
            if (plan["existing"] > 1000 and len(plan["deletes"]) > plan["existing"] * MAX_DELETE_SHARE
                    and not args.allow_large_diff):
                raise RuntimeError(f"anomalous diff: would delete {len(plan['deletes']):,} of "
                                   f"{plan['existing']:,} rows; rerun with --allow-large-diff after review")
            apply_sync(db, plan)
            run.counts.update(records_processed=row_count, records_added=len(plan["inserts"]),
                              records_updated=len(plan["updates"]), records_failed=failed)
            run.note(f"deleted {len(plan['deletes']):,} rows no longer in the extract")

        run_source(SOURCE, "full", body, db, run_id=args.run_id)


if __name__ == "__main__":
    main()

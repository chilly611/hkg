#!/usr/bin/env python3
"""
OIG LEIE ingestion. Downloads UPDATED.csv, records the artifact and the run, and syncs
oig_exclusions to that snapshot.

Sync rules:
  - A file row that matches an existing row on every stored field keeps that row's id
    (receipt lineage points at oig_exclusions ids).
  - New file rows are inserted. Rows no longer in the snapshot are deleted: OIG removes
    reinstated parties from UPDATED.csv, so keeping them would report a lifted exclusion.
  - npi comes only from the file's own NPI column, and only when that NPI exists in providers
    (FK). receipts_for_exclusions treats oig_exclusions.npi as npi_exact, so an NPI matched by
    name is never kept here.

source_published_at: the "Last Update" date on the OIG exclusions page; if the page cannot be
read, the file's HTTP Last-Modified header; otherwise NULL with [CONFIRM] in run_notes.

Usage:
  python3 ingest_oig.py              # full run against the live database
  python3 ingest_oig.py --dry-run    # download, parse and diff; writes nothing
  python3 ingest_oig.py --run-id ID  # finish a run scripts/poll_sources.py created
"""
import argparse
import csv
import re
import tempfile
from collections import defaultdict
from datetime import datetime
from email.utils import parsedate_to_datetime
from pathlib import Path

from core_run import Rest, chunks, download, fetch_text, in_list, log, run_source

SOURCE = "OIG LEIE"
PAGE_URL = "https://oig.hhs.gov/exclusions/exclusions_list.asp"
FILE_URL = "https://oig.hhs.gov/exclusions/downloadables/UPDATED.csv"
FIELDS = ("entity_name", "entity_type", "exclusion_type", "exclusion_date", "reinstatement_date",
          "state", "specialty", "general_info")
BATCH = 500
MAX_DELETE_SHARE = 0.2  # a diff that deletes more than this share of the table is treated as parser drift


def read_page_date():
    """The 'MM-DD-YYYY Last Update' stamp on the exclusions page, as YYYY-MM-DD, or None."""
    try:
        page, _ = fetch_text(PAGE_URL)
    except Exception as e:
        log(f"could not read {PAGE_URL}: {e}")
        return None
    text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", page))
    m = re.search(r"(\d{2})-(\d{2})-(\d{4}) Last Update", text)
    if not m:
        return None
    return datetime.strptime("-".join(m.groups()), "%m-%d-%Y").strftime("%Y-%m-%d")


def parse_date(s):
    s = (s or "").strip()
    if not s or s == "0":
        return None
    return datetime.strptime(s, "%Y%m%d").strftime("%Y-%m-%d")


def clean(s, n):
    s = (s or "").strip()
    return s[:n] or None


def parse_file(path):
    """Returns (records, row_count, failed). Each record carries file_npi alongside the table fields."""
    records, failed, row_count = [], 0, 0
    with open(path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            row_count += 1
            try:
                last, first, bus = r["LASTNAME"].strip(), r["FIRSTNAME"].strip(), r["BUSNAME"].strip()
                if last:
                    entity_type, name = "individual", (f"{last}, {first}" if first else last)
                else:
                    entity_type, name = "organization", bus
                excl = parse_date(r["EXCLDATE"])
                if not name or not excl:
                    raise ValueError("missing name or exclusion date")
                npi = r["NPI"].strip()
                records.append({
                    "entity_name": name[:500],
                    "entity_type": entity_type,
                    "exclusion_type": clean(r["EXCLTYPE"], 100),
                    "exclusion_date": excl,
                    "reinstatement_date": parse_date(r["REINDATE"]),
                    "state": clean(r["STATE"], 2),
                    "specialty": clean(r["SPECIALTY"], 255),
                    "general_info": clean(r["GENERAL"], 10000),
                    "file_npi": npi if len(npi) == 10 and npi.isdigit() and npi != "0000000000" else None,
                })
            except Exception as e:
                failed += 1
                if failed <= 5:
                    log(f"unparseable row {row_count}: {e}")
    return records, row_count, failed


def known_npis(db, npis):
    found = set()
    for chunk in chunks(sorted(npis), 300):
        found.update(r["npi"] for r in db.select("providers", {"select": "npi", "npi": in_list(chunk)}))
    return found


def plan_sync(db, records):
    file_npis = {r["file_npi"] for r in records if r["file_npi"]}
    in_providers = known_npis(db, file_npis)
    existing = db.select_all("oig_exclusions", "id,npi," + ",".join(FIELDS))
    index = defaultdict(list)
    for row in existing:
        index[tuple(row[f] for f in FIELDS)].append(row)

    inserts, updates, unchanged, npi_cleared = [], [], 0, 0
    for rec in records:
        npi = rec["file_npi"] if rec["file_npi"] in in_providers else None
        row = {f: rec[f] for f in FIELDS}
        row.update(npi=npi, data_source="OIG LEIE", source_url=PAGE_URL)
        candidates = index.get(tuple(rec[f] for f in FIELDS))
        if not candidates:
            inserts.append(row)
            continue
        match = next((c for c in candidates if c["npi"] == npi), candidates[0])
        candidates.remove(match)
        if match["npi"] == npi:
            unchanged += 1
        else:
            if match["npi"] and npi is None:
                npi_cleared += 1
            updates.append({"id": match["id"], **row})
    deletes = [row["id"] for rows in index.values() for row in rows]
    return {
        "existing": len(existing), "inserts": inserts, "updates": updates, "deletes": deletes,
        "unchanged": unchanged, "npi_cleared": npi_cleared,
        "file_npis": len(file_npis), "file_npis_in_providers": len(in_providers),
    }


def summarize(plan):
    return (f"existing {plan['existing']:,}; insert {len(plan['inserts']):,}; update {len(plan['updates']):,} "
            f"(npi cleared on {plan['npi_cleared']:,} rows whose npi the file does not carry); "
            f"delete {len(plan['deletes']):,}; unchanged {plan['unchanged']:,}; "
            f"file NPIs {plan['file_npis']:,}, of which in providers {plan['file_npis_in_providers']:,}")


def apply_sync(db, plan):
    for batch in chunks(plan["inserts"], BATCH):
        db.insert("oig_exclusions", batch)
    for batch in chunks(plan["updates"], BATCH):
        db.insert("oig_exclusions", batch, upsert_on="id")
    for batch in chunks(plan["deletes"], 200):
        db.delete("oig_exclusions", id=in_list(batch))


def fetch(workdir):
    published, how = read_page_date(), f"'Last Update' on {PAGE_URL}"
    path = Path(workdir) / "UPDATED.csv"
    sha, size, headers, retrieved_at = download(FILE_URL, path)
    if not published and headers.get("Last-Modified"):
        published = parsedate_to_datetime(headers["Last-Modified"]).isoformat()
        how = f"HTTP Last-Modified of {FILE_URL} (page date unreadable)"
    return path, sha, size, retrieved_at, published, how


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--run-id", help="adopt this running ingestion_runs row (set by scripts/poll_sources.py)")
    ap.add_argument("--allow-large-diff", action="store_true",
                    help=f"permit deleting more than {MAX_DELETE_SHARE:.0%} of existing rows")
    args = ap.parse_args(argv)
    db = Rest()

    with tempfile.TemporaryDirectory(prefix="hkg_leie_") as workdir:
        if args.dry_run:
            path, sha, size, _, published, how = fetch(workdir)
            records, row_count, failed = parse_file(path)
            log(f"dry run: {row_count:,} rows, {failed} unparseable, published {published} ({how}), sha256 {sha}")
            log("dry run: " + summarize(plan_sync(db, records)))
            return

        def body(run):
            path, sha, size, retrieved_at, published, how = fetch(workdir)
            run.set_published(published, how)
            records, row_count, failed = parse_file(path)
            run.register_artifact(path, "UPDATED.csv", FILE_URL, sha, size, row_count, retrieved_at)
            run.check_row_count(row_count, table_fallback=db.count("oig_exclusions"))
            plan = plan_sync(db, records)
            run.note(summarize(plan))
            if (plan["existing"] > 1000 and len(plan["deletes"]) > plan["existing"] * MAX_DELETE_SHARE
                    and not args.allow_large_diff):
                raise RuntimeError(f"anomalous diff: would delete {len(plan['deletes']):,} of "
                                   f"{plan['existing']:,} rows; rerun with --allow-large-diff after review")
            apply_sync(db, plan)
            run.counts.update(records_processed=row_count, records_added=len(plan["inserts"]),
                              records_updated=len(plan["updates"]), records_failed=failed)
            run.note(f"deleted {len(plan['deletes']):,} rows no longer in the snapshot")

        run_source(SOURCE, "full", body, db, run_id=args.run_id)


if __name__ == "__main__":
    main()

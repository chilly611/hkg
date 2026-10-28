#!/usr/bin/env python3
"""
CMS Medicare Opt Out Affidavits (data.cms.gov) -> medicare_optout receipts for roster NPIs.

Downloads the latest version's CSV (the list of practitioners currently opted out of Medicare),
records the artifact and the run, runs the anomaly guard in cms_data.py, then writes one receipt per
roster NPI:
  in the file      raw_status "opted_out <effective> to <end>", claim.status = opted_out, with the
                   effective and end dates of the affidavit; source_effective_at = effective date
  not in the file  not_found (not on this month's list; never "participating")

normalized_status uses the receipt vocabulary, read for the claim "Medicare opt-out":
  active    the opt-out is in effect today (effective <= today <= end)
  expired   the end date has passed (the list is published monthly, so it can lag)
  inactive  the effective date is still ahead
A provider can hold more than one affidavit; the receipt reports the one in effect today, else the
latest by effective date, and lists every affidavit in claim.affidavits.

source_published_at: the version's 'modified' date in the data.cms.gov catalog.

Usage:
  python3 ingest_cms_optout.py                                  # every roster
  python3 ingest_cms_optout.py --roster first-packet-2026-10-26 # one roster (repeatable)
  python3 ingest_cms_optout.py --dry-run                        # download, parse, match; writes nothing
  python3 ingest_cms_optout.py --run-id ID                      # finish a run scripts/poll_sources.py created
"""
import argparse
import csv
import re
import tempfile
from pathlib import Path

import cms_data
from core_run import Rest, download, log, run_source

SOURCE = "CMS Medicare opt-out affidavits"
SERIES = "9887a515-7552-4693-bf58-735c77af46d7"   # Opt Out Affidavits
CLAIM_TYPE = "medicare_optout"
PARSER = "ingest_cms_optout/1"
COLUMNS = ("NPI", "Optout Effective Date", "Optout End Date", "Specialty", "State Code",
           "Eligible to Order and Refer", "Last Updated", "First Name", "Last Name")
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
LIMITATIONS = ("CMS lists practitioners currently opted out of Medicare, published monthly; an opt-out that "
               "began or ended after the list was cut is not reflected. not_found means not on this list.")


def parse_file(path):
    """Returns ({npi: [affidavit, ...]}, row_count, failed). Each affidavit keeps its file row number."""
    by_npi, row_count, failed = {}, 0, 0
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        cms_data.check_header(reader.fieldnames, COLUMNS, path.name)
        for r in reader:
            row_count += 1
            npi = (r["NPI"] or "").strip()
            eff, end = (r["Optout Effective Date"] or "").strip(), (r["Optout End Date"] or "").strip()
            if not (len(npi) == 10 and npi.isdigit() and DATE.match(eff) and DATE.match(end)):
                failed += 1
                if failed <= 5:
                    log(f"unparseable row {row_count}: NPI {npi!r} effective {eff!r} end {end!r}")
                continue
            by_npi.setdefault(npi, []).append({
                "row": row_count + 1,   # +1 for the header line
                "effective_date": eff,
                "end_date": end,
                "specialty": (r["Specialty"] or "").strip() or None,
                "state": (r["State Code"] or "").strip() or None,
                "eligible_to_order_and_refer": (r["Eligible to Order and Refer"] or "").strip() or None,
                "last_updated": (r["Last Updated"] or "").strip() or None,
            })
    return by_npi, row_count, failed


def status_on(aff, today):
    if aff["effective_date"] > today:
        return "inactive"
    if aff["end_date"] < today:
        return "expired"
    return "active"


def claim_for(affidavits, today, artifact_id):
    in_effect = [a for a in affidavits if status_on(a, today) == "active"]
    pick = max(in_effect or affidavits, key=lambda a: (a["effective_date"], a["end_date"]))
    norm = status_on(pick, today)
    raw = f"opted_out {pick['effective_date']} to {pick['end_date']}"
    claim = {
        "status": "opted_out",
        "effective_date": pick["effective_date"],
        "end_date": pick["end_date"],
        "specialty": pick["specialty"],
        "state": pick["state"],
        "eligible_to_order_and_refer": pick["eligible_to_order_and_refer"],
        "last_updated": pick["last_updated"],
        "affidavits": [{k: a[k] for k in ("effective_date", "end_date", "specialty", "state")} for a in affidavits],
    }
    lineage = [{"artifact_id": artifact_id, "row": a["row"]} for a in affidavits]
    return raw, norm, claim, pick["effective_date"], lineage


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--roster", action="append", default=[], help="rosters.id to write receipts for (repeatable)")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--run-id", help="adopt this running ingestion_runs row (set by scripts/poll_sources.py)")
    ap.add_argument("--allow-large-diff", action="store_true",
                    help=f"permit more than {cms_data.FLIP_LIMIT:.0%} of roster NPIs to change sides since the last run")
    args = ap.parse_args(argv)
    db = Rest()
    today = cms_data.now_utc_date()

    with tempfile.TemporaryDirectory(prefix="hkg_optout_") as workdir:
        release = cms_data.Release(SERIES)
        path = Path(workdir) / release.file_name
        if args.dry_run:
            sha, size, _, _ = download(release.csv_url, path)
            by_npi, row_count, failed = parse_file(path)
            roster = cms_data.roster_npis(db, args.roster)
            hits = sum(1 for n in roster if n in by_npi)
            log(f"dry run: {release.title} published {release.published}; {row_count:,} rows, {failed} unparseable, "
                f"{len(by_npi):,} NPIs, sha256 {sha}; roster {len(roster)} NPIs, {hits} on the list")
            return

        def body(run):
            run.set_published(release.published, release.signal)
            sha, size, _, retrieved_at = download(release.csv_url, path)
            by_npi, row_count, failed = parse_file(path)
            run.register_artifact(path, release.file_name, release.csv_url, sha, size, row_count, retrieved_at)
            cms_data.check_published_count(run, release, row_count)
            run.check_row_count(row_count)
            cms_data.check_parse(run, row_count, failed)
            roster = cms_data.roster_npis(db, args.roster)
            run.note(f"roster: {', '.join(args.roster) or 'all rosters'}; {len(roster)} NPIs")
            cms_data.check_flips(run, CLAIM_TYPE, {n: n in by_npi for n in roster}, args.allow_large_diff)
            claims = {n: claim_for(by_npi[n], today, run.artifact["id"]) for n in roster if n in by_npi}
            run.counts.update(records_processed=row_count, records_failed=failed)
            cms_data.write_receipts(run, release, CLAIM_TYPE, roster, claims, retrieved_at, PARSER, LIMITATIONS)

        run_source(SOURCE, "full", body, db, run_id=args.run_id)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
CMS Medicare Fee-For-Service Public Provider Enrollment (data.cms.gov, from PECOS) -> pecos_enrollment
receipts for roster NPIs.

Downloads the latest version's Enrollment file (one row per enrollment currently approved to bill or
to order and refer; about 3M rows, 330 MB), records the artifact and the run, runs the anomaly guard in
cms_data.py, then writes one receipt per roster NPI:
  in the file      raw_status "enrolled <type> <state>", claim.status = enrolled, normalized_status
                   active (an approved enrollment on file), with the enrollment type and state of each
                   of the NPI's enrollments in claim.enrollments; the receipt's own enrollment_type and
                   state are the first enrollment by enrollment id
  not in the file  not_found (no approved enrollment under this NPI in this extract)

The Enrollment file lists one NPI per enrollment. NPIs that appear only in the Additional NPIs sub-file
are not read here, and the file carries no enrollment dates, so source_effective_at stays NULL.

source_published_at: the version's 'modified' date in the data.cms.gov catalog.

Usage:
  python3 ingest_cms_pecos.py                                  # every roster
  python3 ingest_cms_pecos.py --roster first-packet-2026-10-26 # one roster (repeatable)
  python3 ingest_cms_pecos.py --dry-run                        # download, parse, match; writes nothing
  python3 ingest_cms_pecos.py --run-id ID                      # finish a run scripts/poll_sources.py created
"""
import argparse
import csv
import tempfile
from pathlib import Path

import cms_data
from core_run import Rest, download, log, run_source

SOURCE = "CMS PECOS enrollment"
SERIES = "2457ea29-fc82-48b0-86ec-3b0755de7515"   # Medicare Fee-For-Service Public Provider Enrollment
CLAIM_TYPE = "pecos_enrollment"
PARSER = "ingest_cms_pecos/1"
COLUMNS = ("NPI", "MULTIPLE_NPI_FLAG", "PECOS_ASCT_CNTL_ID", "ENRLMT_ID", "PROVIDER_TYPE_CD",
           "PROVIDER_TYPE_DESC", "STATE_CD")
# First two characters of PROVIDER_TYPE_CD (PPEF Data Guidance, section 3.2).
ENROLLMENT_TYPES = {
    "00": "PART A PROVIDER", "12": "PART B SUPPLIER", "14": "PRACTITIONER",
    "30": "DME SUPPLIER", "33": "ORDER AND REFERRING ONLY", "53": "MDPP SUPPLIER",
}
LIMITATIONS = ("CMS Public Provider Enrollment lists enrollments currently approved to bill Medicare or to order "
               "and refer, one NPI per enrollment, published quarterly; it omits opted-out providers, NPIs listed "
               "only in the Additional NPIs sub-file, and enrollments CMS held back for data quality. not_found "
               "means no approved enrollment under this NPI in this extract.")


def parse_file(path, wanted):
    """Reads every row; keeps the enrollments of NPIs in wanted. Returns ({npi: [enrollment]}, row_count, failed)."""
    by_npi, row_count, failed = {}, 0, 0
    # The extract is not UTF-8 (names carry Latin-1 bytes such as 0xA0); every field read here is ASCII.
    with open(path, newline="", encoding="latin-1") as f:
        reader = csv.DictReader(f)
        cms_data.check_header(reader.fieldnames, COLUMNS, path.name)
        for r in reader:
            row_count += 1
            npi = (r["NPI"] or "").strip()
            code = (r["PROVIDER_TYPE_CD"] or "").strip()
            if not (len(npi) == 10 and npi.isdigit() and code[:2] in ENROLLMENT_TYPES):
                failed += 1
                if failed <= 5:
                    log(f"unparseable row {row_count}: NPI {npi!r} PROVIDER_TYPE_CD {code!r}")
                continue
            if npi in wanted:
                by_npi.setdefault(npi, []).append({
                    "row": row_count + 1,   # +1 for the header line
                    "enrollment_id": (r["ENRLMT_ID"] or "").strip(),
                    "enrollment_type": ENROLLMENT_TYPES[code[:2]],
                    "provider_type_cd": code,
                    "provider_type_desc": (r["PROVIDER_TYPE_DESC"] or "").strip() or None,
                    "state": (r["STATE_CD"] or "").strip() or None,
                    "pac_id": (r["PECOS_ASCT_CNTL_ID"] or "").strip() or None,
                    "multiple_npi_flag": (r["MULTIPLE_NPI_FLAG"] or "").strip() or None,
                })
            if row_count % 500_000 == 0:
                log(f"  {row_count:,} rows read")
    return by_npi, row_count, failed


def claim_for(enrollments, artifact_id):
    enrollments = sorted(enrollments, key=lambda e: e["enrollment_id"])
    first = enrollments[0]
    raw = f"enrolled {first['enrollment_type']} {first['state'] or ''}".strip()
    if len(enrollments) > 1:
        raw += f" (+{len(enrollments) - 1} more enrollments)"
    claim = {
        "status": "enrolled",
        "enrollment_type": first["enrollment_type"],
        "state": first["state"],
        "provider_type_cd": first["provider_type_cd"],
        "provider_type_desc": first["provider_type_desc"],
        "enrollments": [{k: e[k] for k in ("enrollment_id", "enrollment_type", "provider_type_cd",
                                           "provider_type_desc", "state", "pac_id")} for e in enrollments],
    }
    lineage = [{"artifact_id": artifact_id, "row": e["row"], "enrollment_id": e["enrollment_id"]} for e in enrollments]
    return raw, "active", claim, None, lineage


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--roster", action="append", default=[], help="rosters.id to write receipts for (repeatable)")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--run-id", help="adopt this running ingestion_runs row (set by scripts/poll_sources.py)")
    ap.add_argument("--allow-large-diff", action="store_true",
                    help=f"permit more than {cms_data.FLIP_LIMIT:.0%} of roster NPIs to change sides since the last run")
    args = ap.parse_args(argv)
    db = Rest()

    with tempfile.TemporaryDirectory(prefix="hkg_pecos_") as workdir:
        release = cms_data.Release(SERIES)
        path = Path(workdir) / release.file_name
        if args.dry_run:
            roster = cms_data.roster_npis(db, args.roster)
            sha, size, _, _ = download(release.csv_url, path, timeout=1800)
            by_npi, row_count, failed = parse_file(path, roster)
            log(f"dry run: {release.title} published {release.published}; {row_count:,} rows, {failed} unparseable, "
                f"sha256 {sha}; roster {len(roster)} NPIs, {len(by_npi)} enrolled")
            return

        def body(run):
            run.set_published(release.published, release.signal)
            roster = cms_data.roster_npis(db, args.roster)
            run.note(f"roster: {', '.join(args.roster) or 'all rosters'}; {len(roster)} NPIs")
            sha, size, _, retrieved_at = download(release.csv_url, path, timeout=1800)
            by_npi, row_count, failed = parse_file(path, roster)
            run.register_artifact(path, release.file_name, release.csv_url, sha, size, row_count, retrieved_at)
            cms_data.check_published_count(run, release, row_count)
            run.check_row_count(row_count)
            cms_data.check_parse(run, row_count, failed)
            cms_data.check_flips(run, CLAIM_TYPE, {n: n in by_npi for n in roster}, args.allow_large_diff)
            claims = {n: claim_for(by_npi[n], run.artifact["id"]) for n in by_npi}
            run.counts.update(records_processed=row_count, records_failed=failed)
            cms_data.write_receipts(run, release, CLAIM_TYPE, roster, claims, retrieved_at, PARSER, LIMITATIONS)

        run_source(SOURCE, "full", body, db, run_id=args.run_id)


if __name__ == "__main__":
    main()

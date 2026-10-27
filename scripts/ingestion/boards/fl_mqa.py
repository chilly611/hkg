#!/usr/bin/env python3
"""
Florida DOH MQA licensure ingestion: same pipeline as tx_tmb.py (artifact, run, clocks, anomaly guard,
NPI matching ladder, run-scoped snapshot in state_license_lookups and provider_adverse_actions).

The MQA Data Download Portal (https://data-download.mqa.flhealthsource.gov/) requires a signed-in
account, so the loader does not download. A person signs in and downloads, pipe-delimited:
  - Licensure Data, "All Statuses", one file per profession: 1501-P.txt (Medical Doctor),
    1901-P.txt (Osteopathic Physician), 1512-P.txt (Physician Assistant)
  - Practitioner Profile Data: tp_ahca_discip.txt (Final Disciplinary Actions, the Department's own)
    and tp_disciplinary.txt (Disciplinary Actions by other licensing bodies and institutions)
The layout below was read from those files' headers and the portal's metadata documents
(LicensureDataMetaData.pdf, Profile_*MetaData.pdf), 2026-10-26. Neither file carries an NPI.
A header that no longer has a mapped column stops the load before a run starts.

source_published_at: the created date the portal shows for the licensure file (its FTPFileInfo
handler), passed with --published because the file itself carries no date. Without it, NULL and
[CONFIRM] in run_notes.

Usage:
  python3 boards/fl_mqa.py --inspect FILE [FILE ...]
  python3 boards/fl_mqa.py --licensure 1501-P.txt 1901-P.txt 1512-P.txt \\
      --actions tp_ahca_discip.txt --other-actions tp_disciplinary.txt --published 2026-10-25 [--dry-run]
"""
import argparse
import csv
import hashlib
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

import common
from common import LicenseRow, Matcher, assign_keys, log, report, status_guard
from core_run import Rest, now_iso, run_source

SOURCE = "Florida MQA licensee data download"
STATE = "FL"
PORTAL_URL = "https://data-download.mqa.flhealthsource.gov/"
LICENSURE_URL = PORTAL_URL + "LicensureData"
PROFILE_URL = PORTAL_URL + "ProfileData"

# Licensure file columns this loader reads (LicensureDataMetaData.pdf).
LICENSURE_COLUMNS = ("pro_cde", "Profession-Name", "lic_id", "Expire-Date", "Original-Date", "Rank-Code",
                     "License-Number", "Status-Effective-Date", "Board-Action-Indicator",
                     "License-Status-Description", "Last-Name", "First-Name",
                     "License-Active-Status-Description", "Birth-Year-Range")
FINAL_ACTION_COLUMNS = ("cse_nbr", "pro_cde", "lic_id", "close_date", "action_desc", "under_appeal_ind")
OTHER_ACTION_COLUMNS = ("pro_cde", "lic_id", "rec_key", "disc_body", "disc_type", "disc_date",
                        "disc_action_desc", "disc_viol_desc", "under_appeal", "publishable")

# License-Status-Description -> normalized_status. A string not in this table maps to 'unknown', never
# 'active'. 'Clear' or 'Military Active' with License-Active-Status-Description 'Inactive' is 'inactive'.
STATUS = {
    "CLEAR": "active",
    "MILITARY ACTIVE": "active",
    "DELINQUENT": "expired",
    "NULL AND VOID": "expired",
    "VOL RELINQUISH": "inactive",
    "RETIRED": "inactive",
    "DECEASED": "inactive",
    "VOLUN WITHDRAW": "inactive",
    "DENIED - RNEWAL": "inactive",
    "OBLIGATIONS": "probation",
    "CONDITIONAL": "probation",
    "PROBATION": "probation",
    "SUSPENDED": "suspended",
    "EMERG SUSPENS": "suspended",
    "ADMIN SUSPENDED": "suspended",
    "REVOKED": "revoked",
    "DISC RELINQUISH": "revoked",  # relinquished while discipline was pending: an adverse outcome
    # Seen in the file and deliberately left 'unknown': VR PEND BD ACT (relinquishment pending board action).
}


def family(license_type):
    lt = (license_type or "").upper()
    if "PHYSICIAN ASSISTANT" in lt:
        return "pa"
    if "MEDICAL DOCTOR" in lt or "OSTEOPATHIC" in lt:
        return "physician"
    return None


def file_digest(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest(), path.stat().st_size


def read_rows(path, required):
    """Yields (row_number, dict or None). Data rows end with a trailing '|'; a row with more fields than
    the header plus that trailing one is malformed and yields None."""
    with open(path, newline="", encoding="utf-8", errors="replace") as f:
        reader = csv.reader(f, delimiter="|", quoting=csv.QUOTE_NONE)
        header = [h.strip() for h in next(reader)]
        if header and header[-1] == "":
            header = header[:-1]
        missing = [c for c in required if c not in header]
        if missing:
            sys.exit(f"columns {missing} are not in {path}; the layout changed. No run was started.")
        yield 0, header
        for i, row in enumerate(reader, 1):
            if len(row) > len(header) + 1 or (len(row) == len(header) + 1 and row[-1] != ""):
                yield i, None
            else:
                yield i, dict(zip(header, (v.strip() for v in row)))


def header_of(path, required):
    return next(read_rows(path, required))[1]


def parse_date(s, fmt="%m/%d/%Y"):
    s = (s or "").strip()
    try:
        d = datetime.strptime(s, fmt)
    except ValueError:
        return None
    return None if d.year <= 1901 else d.strftime("%Y-%m-%d")  # 01/01/1901 is the file's "no date"


def load_actions(final_path, other_path):
    """(pro_cde, lic_id) -> list of provider_adverse_actions items, verbatim from the profile files."""
    actions = defaultdict(list)
    if final_path:
        rows = read_rows(final_path, FINAL_ACTION_COLUMNS)
        next(rows)
        for _, r in rows:
            if r:
                actions[(r["pro_cde"], r["lic_id"])].append({
                    "action_type": r["action_desc"],
                    "classification": "Florida final disciplinary action",
                    "action_date": parse_date(r["close_date"]),
                    "effective_date": parse_date(r["close_date"]),
                    "description": f"Case {r['cse_nbr']}: {r['action_desc']}"
                                   + (" (under appeal)" if r["under_appeal_ind"] == "Y" else ""),
                    "raw": r,
                })
    if other_path:
        rows = read_rows(other_path, OTHER_ACTION_COLUMNS)
        next(rows)
        for _, r in rows:
            if r and r["publishable"] == "Y":
                actions[(r["pro_cde"], r["lic_id"])].append({
                    "action_type": r["disc_action_desc"],
                    "classification": f"{r['disc_type']}: {r['disc_body']}",
                    "action_date": parse_date(r["disc_date"], "%d-%b-%y"),
                    "effective_date": parse_date(r["disc_date"], "%d-%b-%y"),
                    "description": r["disc_viol_desc"] or None,
                    "raw": r,
                })
    return actions


def normalize_status(primary, secondary):
    norm = STATUS.get(primary.upper(), "unknown")
    if norm == "active" and secondary.upper() == "INACTIVE":
        norm = "inactive"
    return norm, (f"{primary} | {secondary}" if secondary else primary)


def parse_licensure(paths, actions):
    """Returns (header, rows, row_count, failed, per-file row counts)."""
    rows, failed, row_count, per_file, header = [], 0, 0, {}, None
    for path in paths:
        it = read_rows(path, LICENSURE_COLUMNS)
        _, header = next(it)
        n = 0
        for i, r in it:
            n += 1
            if r is None or not r["lic_id"] or not r["Last-Name"]:
                failed += 1
                if failed <= 5:
                    log(f"unparseable row {i} in {path.name}")
                continue
            status, raw_status = normalize_status(r["License-Status-Description"],
                                                  r["License-Active-Status-Description"])
            number = r["License-Number"]
            items = list(actions.get((r["pro_cde"], r["lic_id"]), []))
            if not items and r["Board-Action-Indicator"] == "Y":
                items.append({"action_type": "Board action on record",
                              "classification": "Board-Action-Indicator", "action_date": None,
                              "effective_date": None,
                              "description": "Licensure file flags a board action; no detail in the profile files.",
                              "raw": {"Board-Action-Indicator": "Y"}})
            fam = family(r["Profession-Name"])
            rows.append(LicenseRow(
                license_type=r["Profession-Name"],
                license_number=f"{r['Rank-Code']}{number}" if number else None,  # e.g. ME15733, as NPPES records it
                family=fam,
                npi=None,  # neither licensure nor profile files carry an NPI
                last_name=r["Last-Name"],
                first_name=r["First-Name"],
                birth_year=None if r["Birth-Year-Range"] in ("", "N/A") else r["Birth-Year-Range"],
                raw_status=raw_status,
                normalized_status=status,
                status_date=parse_date(r["Status-Effective-Date"]),
                issue_date=parse_date(r["Original-Date"]),
                expiration_date=parse_date(r["Expire-Date"]),
                actions=items,
                raw=r,
                placeholder=not number,
                physician_active=(fam == "physician" and status == "active"),
            ))
            rows[-1].key = f"{r['pro_cde']}|{r['lic_id']}"
        per_file[path] = n
        row_count += n
    assign_keys(rows, base_key=lambda r: r.key, full_key=lambda r: f"{r.key}|{r.last_name}|{r.first_name}")
    return header, rows, row_count, failed, per_file


def inspect(paths):
    for p in paths:
        it = read_rows(p, ())
        _, header = next(it)
        n, bad, distinct = 0, 0, [Counter() for _ in header]
        for _, r in it:
            n += 1
            if r is None:
                bad += 1
                continue
            for i, col in enumerate(header):
                if len(distinct[i]) < 200:
                    distinct[i][r.get(col, "")] += 1
        print(f"== {p}: {n:,} rows ({bad} malformed), {len(header)} columns")
        for i, col in enumerate(header):
            top = ", ".join(f"{v or '(blank)'} ({c:,})" for v, c in distinct[i].most_common(6))
            print(f"  {i:>2} {col:<40} {top[:160]}")


def check_file_count(run, path, rows):
    """50% guard for a licensure file other than the run's primary artifact: compare with the last
    artifact of the same file name."""
    prior = run.db.select("source_artifacts", {"select": "row_count,retrieved_at", "source_id": f"eq.{run.source_id}",
                                               "file_name": f"eq.{path.name}", "row_count": "not.is.null",
                                               "order": "retrieved_at.desc", "limit": 1})
    if prior and rows < prior[0]["row_count"] * common.MATCH_DROP_RATIO:
        raise RuntimeError(f"anomalous row count: {path.name} has {rows:,} rows, last artifact had "
                           f"{prior[0]['row_count']:,}; not loaded")
    run.note(f"{path.name}: {rows:,} rows" + (f" vs {prior[0]['row_count']:,} last time" if prior else ""))


def register_extra(run, path, rows, published, notes):
    sha, size = file_digest(path)
    if run.db.select("source_artifacts", {"select": "id", "source_id": f"eq.{run.source_id}", "sha256": f"eq.{sha}"}):
        run.note(f"unchanged file: {path.name} sha256 {sha}")
        return
    run.db.insert("source_artifacts", [{"source_id": run.source_id, "file_name": path.name,
                                        "download_url": LICENSURE_URL if rows is not None else PROFILE_URL,
                                        "sha256": sha, "byte_size": size, "row_count": rows,
                                        "source_published_at": published, "retrieved_at": now_iso(),
                                        "notes": notes}])


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--inspect", nargs="+", metavar="FILE", type=Path)
    ap.add_argument("--licensure", nargs="+", metavar="FILE", type=Path,
                    help="licensure 'All Statuses' files; the first is the run's primary artifact")
    ap.add_argument("--actions", type=Path, metavar="tp_ahca_discip.txt")
    ap.add_argument("--other-actions", type=Path, metavar="tp_disciplinary.txt")
    ap.add_argument("--published", help="created date the portal shows for the licensure files, YYYY-MM-DD")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--run-id", help="adopt a 'running' ingestion_runs row opened by poll_sources.py")
    args = ap.parse_args(argv)

    if args.inspect:
        inspect(args.inspect)
        return
    if not args.licensure:
        ap.error("--licensure FILE [FILE ...] is required (download from the MQA portal first)")
    for p in [*args.licensure, args.actions, args.other_actions]:
        if p:
            header_of(p, ())  # exits before any run if a file is unreadable
    published = datetime.strptime(args.published, "%Y-%m-%d").strftime("%Y-%m-%d") if args.published else None

    db = Rest()
    if args.dry_run:
        actions = load_actions(args.actions, args.other_actions)
        header, rows, row_count, failed, _ = parse_licensure(args.licensure, actions)
        source_id = db.select("data_sources", {"select": "id", "name": f"eq.{SOURCE}"})[0]["id"]
        matches, outcome = Matcher(db, STATE, source_id, family).match_all(rows)
        log(f"dry run: {row_count:,} rows, {failed} unparseable")
        report(STATE, rows, matches, outcome, STATUS, [], 0, 0)
        return

    def body(run):
        run.set_published(published, "created date shown by the MQA portal for the licensure files"
                          if published else "the licensure files (they carry no date; pass --published)")
        actions = load_actions(args.actions, args.other_actions)
        header, rows, row_count, failed, per_file = parse_licensure(args.licensure, actions)
        primary = args.licensure[0]
        sha, size = file_digest(primary)
        run.register_artifact(primary, primary.name, LICENSURE_URL, sha, size, per_file[primary], now_iso())
        run.check_row_count(per_file[primary], same_kind=lambda fn: fn == primary.name)
        for p in args.licensure[1:]:
            check_file_count(run, p, per_file[p])
            register_extra(run, p, per_file[p], published, f"licensure file read with run {run.id}")
        for p in (args.actions, args.other_actions):
            if p:
                register_extra(run, p, None, None, f"profile action file read with run {run.id}")
        status_guard(run, rows)
        common.set_board_fields(db, STATE, header)
        matches, outcome = Matcher(db, STATE, run.source_id, family).match_all(rows)
        licenses, n_actions = common.write_snapshot(run, STATE, SOURCE, PROFILE_URL, rows, matches, now_iso())
        common.prune_snapshots(run)
        text = report(STATE, rows, matches, outcome, STATUS, [], licenses, n_actions)
        run.note(text.split("\nnormalized_status mapping")[0])
        run.counts.update(records_processed=row_count, records_added=licenses + n_actions,
                          records_updated=0, records_failed=failed)

    run_source(SOURCE, "full", body, db, run_id=args.run_id)


if __name__ == "__main__":
    main()

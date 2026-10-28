#!/usr/bin/env python3
"""
Release poller, run at :17 and :47 every hour (.github/workflows/poll_sources.yml). For each
data_sources row with a detection_url, look for a new release and, when one is found, open an
ingestion_runs row and hand it to the matching loader.

Detection, per source:
  NPI Registry  newest weekly V2 file name on detection_url; publisher date = end of its date range
  OIG LEIE      "Last Update" stamp on detection_url; else Last-Modified of UPDATED.csv
  SAM.gov       newest Exclusions Public V2 extract in the file-extract service listing (the
                detection_url page is a script-rendered app with no date in it); publisher date =
                the Julian date in the file name
  California    earliest Box content_modified_at of the DCA data files (boards/ca_dca.py), from the
                folder listing alone; the landing page's hash changes without a new release
  Texas         rowsUpdatedAt in the Socrata view metadata at detection_url (detect_generic)
  CMS opt-out   'modified' of the series' latest version in the data.cms.gov DCAT catalog
  and PECOS     (detection_url, cms_data.py); the data API answers Last-Modified = now, so it cannot
                date a release. Each loader writes receipts for every roster
  Florida       not polled: the MQA portal sits behind an Azure B2C sign-in, so neither the release
                date nor the files can be read unattended. A signed-in person downloads them and runs
                boards/fl_mqa.py (PERSON_RUN)
  any other     rowsUpdatedAt when detection_url is Socrata view metadata (/api/views/<id>.json);
                else Last-Modified of detection_url; else the body's sha256 against the latest
                artifact, only when that artifact was downloaded from detection_url itself. ETag is
                recorded with every check but never decides on its own: there is no stored ETag to
                compare it with.

A release is new when its publisher date is later than every completed or running run of that
source. Then the poller:
  1. inserts ingestion_runs: status 'running', started_at = detected_at = now,
     source_published_at = the publisher's date, run_notes = signal and detection delay
  2. runs the loader with --run-id; the loader marks the run completed or failed
  3. never marks a run completed. If the loader exits and the row is still 'running' (crash,
     kill, timeout), the poller marks it failed so no run is left open.

It skips a source while one of its runs is 'running', and stops retrying a release after
MAX_FAILED failed runs for it. A source with no loader is reported, never given a run.

Detection delay = detected_at - source_published_at, printed per source and written to
run_notes. Publisher dates are day precision, so the delay counts from 00:00 UTC that day.

Usage:
  python3 scripts/poll_sources.py                      # poll every source, start loaders
  python3 scripts/poll_sources.py --dry-run            # detect only; writes nothing, loads nothing
  python3 scripts/poll_sources.py --source "SAM.gov"   # one source (repeatable)

An unreachable publisher is a detection miss, not a poller failure. When the detector's fetch fails
(HTTP error, DNS, refused or reset connection, timeout) or the publisher's page says it is down for
maintenance, the poller appends one line, "unreachable: <status or error>, <timestamp>", to the
run_notes of that source's latest run, opens no run, marks nothing completed and moves on. The
source keeps its last clocks, so v_source_status ages it to due and stale on its own.

Every source the poller checks, reachable or not, gets data_sources.last_polled_at = the time of the
check (a dry run stamps nothing). v_source_status reads "poll late" when that stamp is more than 90
minutes old, so a delayed or dropped GitHub run is never shown as a publisher miss
(scripts/sql/2026-10-28_poll_late.sql). A failed stamp is logged and never fails the poll.

Exit code 1 if the poller itself fails (an uncaught error, a detector that read a reachable page and
could not parse it, a loader run that ended failed, a release that failed MAX_FAILED times) or every
source it checked was unreachable. Unreachable sources alone never fail the run.
Credentials: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY from the repo-root .env or the
environment (see scripts/ingestion/core_run.py). Stdlib only.
"""
import argparse
import hashlib
import http.client
import json
import re
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

INGESTION = Path(__file__).resolve().parent / "ingestion"
sys.path.insert(0, str(INGESTION))
sys.path.insert(0, str(INGESTION / "boards"))

import ca_dca  # noqa: E402
import cms_data  # noqa: E402
import ingest_cms_optout  # noqa: E402
import ingest_cms_pecos  # noqa: E402
import ingest_nppes  # noqa: E402
import ingest_oig  # noqa: E402
import ingest_sam  # noqa: E402
from core_run import USER_AGENT, Rest, fetch_text, log, now_iso  # noqa: E402

STATUS_CATEGORIES = ("provider_data", "compliance", "licensing")  # the sources v_source_status shows
MAX_FAILED = 3
LOADER_TIMEOUT = 4 * 3600
STUCK_HOURS = 6
MAINTENANCE = re.compile(r"down for maint", re.I)   # CMS's NPPES page reads "down for maintance"


class Unavailable(Exception):
    """The publisher says it is down; nothing to compare."""


# A fetch that never got a usable answer from the publisher. HTTPError is a URLError.
UNREACHABLE = (Unavailable, urllib.error.URLError, TimeoutError, ConnectionError, http.client.HTTPException)


def unreachable_reason(e):
    if isinstance(e, urllib.error.HTTPError):
        return f"HTTP {e.code} {e.reason}"
    if isinstance(e, urllib.error.URLError):
        return str(e.reason)
    if isinstance(e, Unavailable):
        return str(e)
    return f"{type(e).__name__}: {e}"


class Detection:
    def __init__(self, published, signal, checked_url, run_type="full", loader_args=(), etag=None, last_modified=None):
        self.published = published          # ISO date or datetime string from the publisher; None if unreadable
        self.signal = signal                # what the date or hash came from
        self.checked_url = checked_url
        self.run_type = run_type
        self.loader_args = list(loader_args)
        self.etag = etag
        self.last_modified = last_modified
        self.sha256 = None


def head(url):
    req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.headers


def http_date(value):
    return parsedate_to_datetime(value).astimezone(timezone.utc).isoformat() if value else None


# ----------------------------------------------------------------------------
# Detectors
# ----------------------------------------------------------------------------

def detect_nppes(source):
    url = source["detection_url"]
    page, headers = fetch_text(url)
    if not ingest_nppes.WEEKLY_RE.search(page):
        if MAINTENANCE.search(page):
            raise Unavailable("publisher page says it is down for maintenance; no files listed")
        raise RuntimeError(f"no weekly V2 file listed on {url}; page layout may have changed")
    name, file_url = ingest_nppes.latest_weekly()
    published, how, _ = ingest_nppes.published_from_name(name)
    return Detection(published, f"{how} ({name})", url, "incremental", ["--url", file_url],
                     headers.get("ETag"), headers.get("Last-Modified"))


def detect_oig(source):
    url = source["detection_url"]
    file_headers = head(ingest_oig.FILE_URL)
    published = ingest_oig.read_page_date()
    signal = f"'Last Update' on {url}"
    if not published:
        published = http_date(file_headers.get("Last-Modified"))
        signal = f"HTTP Last-Modified of {ingest_oig.FILE_URL} (page date unreadable)"
    return Detection(published, signal, url, "full", [], file_headers.get("ETag"), file_headers.get("Last-Modified"))


def detect_sam(source):
    name, _ = ingest_sam.latest_extract()
    published = ingest_sam.julian_date(name)
    return Detection(published, f"Julian date in extract file name {name}", ingest_sam.LIST_URL, "full")


def detect_ca(source):
    published, signal = ca_dca.latest_release()
    return Detection(published, signal, f"Box folder {ca_dca.ROOT_FOLDER} behind {ca_dca.PAGE_URL}", "full")


def detect_cms(series):
    def detect(source):
        release = cms_data.Release(series)
        return Detection(release.published, release.signal, source["detection_url"], "full")
    return detect


def socrata_updated(body):
    """rowsUpdatedAt from a Socrata view's metadata (…/api/views/<id>.json), or None."""
    try:
        stamp = json.loads(body).get("rowsUpdatedAt")
    except (ValueError, AttributeError):
        return None
    return datetime.fromtimestamp(stamp, timezone.utc).isoformat() if isinstance(stamp, int) else None


def detect_generic(source):
    url = source["detection_url"]
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=120) as resp:
        body, headers = resp.read(), resp.headers
    det = Detection(None, None, url, etag=headers.get("ETag"), last_modified=headers.get("Last-Modified"))
    if "/api/views/" in url and (stamp := socrata_updated(body)):
        det.published, det.signal = stamp, f"rowsUpdatedAt in Socrata metadata {url}"
    elif headers.get("Last-Modified"):
        det.published, det.signal = http_date(headers["Last-Modified"]), f"HTTP Last-Modified of {url}"
    else:
        det.sha256 = hashlib.sha256(body).hexdigest()
        det.signal = f"sha256 of {url}"
    return det


DETECTORS = {
    "NPI Registry": detect_nppes,
    "OIG LEIE": detect_oig,
    "SAM.gov": detect_sam,
    "California DCA public information file": detect_ca,
    "Texas Medical Board licensure file": detect_generic,
    ingest_cms_optout.SOURCE: detect_cms(ingest_cms_optout.SERIES),
    ingest_cms_pecos.SOURCE: detect_cms(ingest_cms_pecos.SERIES),
}
LOADERS = {   # paths relative to scripts/ingestion; each loader accepts --run-id
    "NPI Registry": "ingest_nppes.py",
    "OIG LEIE": "ingest_oig.py",
    "SAM.gov": "ingest_sam.py",
    "California DCA public information file": "boards/ca_dca.py",
    "Texas Medical Board licensure file": "boards/tx_tmb.py",
    ingest_cms_optout.SOURCE: "ingest_cms_optout.py",
    ingest_cms_pecos.SOURCE: "ingest_cms_pecos.py",
}
# Loaders a person runs: the poller can neither read the release date nor fetch the files unattended.
PERSON_RUN = {
    "Florida MQA licensee data download": (
        "the MQA portal requires a signed-in person; they download the Licensure and profile files "
        "and run boards/fl_mqa.py --licensure ... --actions ... --published DATE"),
}


# ----------------------------------------------------------------------------
# Comparison with what the garden already has
# ----------------------------------------------------------------------------

def parse_ts(value):
    """ISO date or datetime -> aware UTC datetime. A bare date is 00:00 UTC that day."""
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def is_newer(detected, known):
    """Compare at the detected value's precision: a bare date is compared by day."""
    if known is None:
        return True
    if len(detected) == 10:
        return parse_ts(detected).date() > parse_ts(known).date()
    return parse_ts(detected) > parse_ts(known)


def same_release(detected, other):
    if len(detected) == 10:
        return parse_ts(detected).date() == parse_ts(other).date()
    return parse_ts(detected) == parse_ts(other)


def history(db, source_id):
    runs = db.select("ingestion_runs", {
        "select": "id,status,started_at,source_published_at", "source_id": f"eq.{source_id}",
        "order": "started_at.desc", "limit": 200})
    known = [r["source_published_at"] for r in runs
             if r["status"] in ("completed", "running") and r["source_published_at"]]
    latest_known = max(known, key=parse_ts) if known else None
    return runs, latest_known


def hours_between(start, end):
    return (parse_ts(end) - parse_ts(start)).total_seconds() / 3600.0


# ----------------------------------------------------------------------------
# Runs
# ----------------------------------------------------------------------------

def open_run(db, source, det, delay_h):
    ts = now_iso()
    notes = (f"detected by scripts/poll_sources.py at {ts}: {det.signal}; checked {det.checked_url}"
             + (f"; ETag {det.etag}" if det.etag else "")
             + (f"; Last-Modified {det.last_modified}" if det.last_modified else "")
             + (f"; detection delay {delay_h:.1f}h from source_published_at {det.published}"
                if delay_h is not None else "; [CONFIRM] no publisher date, detection delay unknown"))
    row = db.insert("ingestion_runs", [{
        "source_id": source["id"],
        "run_type": det.run_type,
        "status": "running",
        "started_at": ts,
        "detected_at": ts,
        "source_published_at": det.published,
        "run_notes": notes,
    }], returning=True)[0]
    log(f"run {row['id']} opened for {source['name']}: {notes}")
    return row


def note_miss(db, runs, line):
    """Append line to the run_notes of the source's latest run. Returns that run's id, or None if it has none."""
    if not runs:
        return None
    run_id = runs[0]["id"]   # history() orders by started_at desc
    notes = db.select("ingestion_runs", {"select": "run_notes", "id": f"eq.{run_id}"})[0]["run_notes"]
    db.patch("ingestion_runs", {"run_notes": f"{notes}\n{line}" if notes else line}, id=f"eq.{run_id}")
    return run_id


def invoke_loader(db, source, run, det):
    cmd = [sys.executable, str(INGESTION / LOADERS[source["name"]]), "--run-id", run["id"], *det.loader_args]
    log(f"loader: {' '.join(cmd[1:])}")
    try:
        code = subprocess.run(cmd, cwd=str(INGESTION), timeout=LOADER_TIMEOUT).returncode
        reason = f"loader exited with code {code}"
    except subprocess.TimeoutExpired:
        code, reason = None, f"loader killed after {LOADER_TIMEOUT // 3600}h"
    row = db.select("ingestion_runs", {"select": "id,status,detected_at,source_published_at,completed_at",
                                       "id": f"eq.{run['id']}"})[0]
    if row["status"] == "running":
        # The loader never closed the run. Close it as failed; completion is only the loader's to write.
        db.patch("ingestion_runs", {"status": "failed", "completed_at": now_iso(),
                                    "error_log": f"{reason} and left the run open; closed by scripts/poll_sources.py"},
                 id=f"eq.{run['id']}")
        row["status"] = "failed"
    return row, reason


# ----------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------

def poll(db, source, dry_run):
    """Returns a result dict for the report."""
    res = {"name": source["name"], "outcome": None, "published": None, "known": None, "signal": None,
           "delay_h": None, "run_id": None, "run_status": None, "error": False, "checked": False,
           "unreachable": False}
    if source["name"] in PERSON_RUN:
        res["outcome"] = f"not polled: {PERSON_RUN[source['name']]}"
        return res
    if not source.get("detection_url"):
        res["outcome"] = "not polled: no detection_url [CONFIRM] a person sets it"
        return res

    runs, known = history(db, source["id"])
    res["known"] = known
    running = [r for r in runs if r["status"] == "running"]
    res["checked"] = True
    try:
        detector = DETECTORS.get(source["name"])
        det = (detector or detect_generic)(source)
    except UNREACHABLE as e:
        # A detection miss: note it on the source, open no run, keep the last clocks.
        line = f"unreachable: {unreachable_reason(e)}, {now_iso()}"
        res["unreachable"] = True
        if dry_run:
            res["outcome"] = f"{line} (dry run: not noted)"
        else:
            noted = note_miss(db, runs, line)
            res["outcome"] = f"{line} (noted on run {noted})" if noted else f"{line} (no run to note it on)"
        return res
    except Exception as e:
        res["outcome"], res["error"] = f"detection error: {e}", True
        return res
    res["published"], res["signal"] = det.published, det.signal

    if det.published:
        new = is_newer(det.published, known)
    elif det.sha256:
        # A hash only means something against an artifact downloaded from this same URL.
        # A landing page's hash never equals a data file's hash, so it would fire every hour.
        arts = db.select("source_artifacts", {"select": "sha256,download_url", "source_id": f"eq.{source['id']}",
                                              "order": "retrieved_at.desc", "limit": 1})
        if arts and arts[0]["download_url"] != det.checked_url:
            res["outcome"] = ("cannot tell: no publisher date or Last-Modified, and detection_url is not the file "
                              "the loader downloads [CONFIRM] needs a source-specific detector")
            return res
        new = not arts or arts[0]["sha256"] != det.sha256
    else:
        res["outcome"], res["error"] = "detection error: no publisher date, Last-Modified or hash", True
        return res

    if not new:
        res["outcome"] = "no new release"
        return res
    if det.published:
        res["delay_h"] = hours_between(det.published, now_iso())
    if running:
        age = hours_between(running[0]["started_at"], now_iso())
        res["outcome"] = (f"new release, skipped: run {running[0]['id']} has been running {age:.1f}h"
                          + (" (possibly stuck; needs a person)" if age > STUCK_HOURS else ""))
        return res
    failed = [r for r in runs if r["status"] == "failed" and r["source_published_at"] and det.published
              and same_release(det.published, r["source_published_at"])]
    if len(failed) >= MAX_FAILED:
        res["outcome"] = f"new release, skipped: {len(failed)} failed runs for it already; needs a person"
        res["error"] = True
        return res
    if source["name"] not in LOADERS:
        res["outcome"] = "new release, no loader for this source; no run opened"
        return res

    if dry_run:
        res["outcome"] = "new release (dry run: no run opened)"
        return res

    run = open_run(db, source, det, res["delay_h"])
    row, reason = invoke_loader(db, source, run, det)
    res.update(run_id=row["id"], run_status=row["status"], outcome=f"new release, run {row['status']} ({reason})",
               error=row["status"] != "completed")
    return res


def stamp_polled(db, source, polled_at):
    """The poller looked at this source: v_source_status ages last_polled_at into "poll late"."""
    try:
        db.patch("data_sources", {"last_polled_at": polled_at}, id=f"eq.{source['id']}")
    except Exception as e:
        log(f"    could not stamp last_polled_at: {e}")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true", help="detect only; write nothing, load nothing")
    ap.add_argument("--source", action="append", default=[], help="poll only this data_sources.name")
    args = ap.parse_args(argv)
    db = Rest()

    sources = db.select("data_sources", {"select": "id,name,category,detection_url", "order": "category,name"})
    sources = [s for s in sources if s["detection_url"] or s["category"] in STATUS_CATEGORIES]
    if args.source:
        sources = [s for s in sources if s["name"] in args.source]
        missing = set(args.source) - {s["name"] for s in sources}
        if missing:
            sys.exit(f"no such source: {', '.join(sorted(missing))}")

    started = now_iso()
    results = []
    for source in sources:
        log(f"=== {source['name']}")
        polled_at = now_iso()
        res = poll(db, source, args.dry_run)
        log(f"    {res['outcome']}")
        if res["checked"] and not args.dry_run:
            stamp_polled(db, source, polled_at)
        results.append(res)

    print(f"\nPoll at {started}{' (dry run)' if args.dry_run else ''}: {len(results)} sources")
    width = max(len(r["name"]) for r in results)
    print(f"{'source':<{width}}  {'publisher date':<25}  {'last loaded':<25}  {'delay':>7}  outcome")
    for r in results:
        delay = f"{r['delay_h']:.1f}h" if r["delay_h"] is not None else "-"
        print(f"{r['name']:<{width}}  {str(r['published'] or '-'):<25}  {str(r['known'] or '-'):<25}  "
              f"{delay:>7}  {r['outcome']}" + (f"  [run {r['run_id']}]" if r["run_id"] else ""))
    for r in results:
        if r["signal"]:
            print(f"  {r['name']}: signal: {r['signal']}")
    checked = [r for r in results if r["checked"]]
    if checked and all(r["unreachable"] for r in checked):
        print(f"\nfailing: every source checked ({len(checked)}) was unreachable")
        sys.exit(1)
    if any(r["error"] for r in results):
        print("\nfailing: " + "; ".join(f"{r['name']}: {r['outcome']}" for r in results if r["error"]))
        sys.exit(1)


if __name__ == "__main__":
    main()

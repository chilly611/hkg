#!/usr/bin/env python3
"""
Shared machinery for the data.cms.gov roster loaders (ingest_cms_optout.py, ingest_cms_pecos.py).

Release: data.cms.gov publishes each dataset as a series of dated versions. The DCAT catalog
(CATALOG_URL) names the series' latest version ("last"), and that version's entry carries:
  modified            the publisher's date for the version: source_published_at
  accrualPeriodicity  the stated cadence: data_sources.cadence_hours
  distribution        the version's CSV download and its version-specific data API
The data-viewer and file endpoints answer with Last-Modified = now, so they cannot date a release.

The loaders hold no table of their own. A run downloads the full CSV (the artifact, hashed like
every other source), checks it, and writes one credential_receipts row per roster NPI from that
file: the claim when the NPI is in the file, not_found when it is not. Rosters come from
roster_members (migrations/2026-10-27_freshroot_api.sql); a run with no --roster covers every roster.

Anomaly guard, on every run (each check stops the run before any receipt is written):
  1. header   the file carries every column the parser reads
  2. count    the file's row count equals the version's total_rows on the data API, and is at
              least 50% of the last completed run's artifact (core_run.check_row_count)
  3. parse    no more than PARSE_FAIL_LIMIT of rows have an unreadable NPI or date
  4. flips    among roster NPIs that hold a receipt from this source's last completed run, no more
              than FLIP_LIMIT moved between found and not_found; --allow-large-diff after review

Stdlib only.
"""
import json
import urllib.request
from datetime import datetime, timedelta, timezone

from core_run import USER_AGENT, chunks, in_list, log

CATALOG_URL = "https://data.cms.gov/data.json"
API_BASE = "https://data.cms.gov/data-api/v1/dataset"
PERIODICITY_HOURS = {"daily": 24, "weekly": 168, "monthly": 720, "quarterly": 2190, "annual": 8760}
PARSE_FAIL_LIMIT = 0.01
FLIP_LIMIT = 0.2
FLIP_MIN = 10           # fewer prior receipts than this cannot say much about drift
BATCH = 500

_catalog = None


def catalog():
    """The DCAT catalog, read once per process (about 18 MB; the poller's two CMS detectors share it)."""
    global _catalog
    if _catalog is None:
        req = urllib.request.Request(CATALOG_URL, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=300) as resp:
            _catalog = json.loads(resp.read())
    return _catalog


def uuid_of(url):
    return url.split("/dataset/")[1].split("/")[0]


class Release:
    """The latest version of one data.cms.gov dataset series, as the catalog states it."""

    def __init__(self, series_uuid):
        cat = catalog()
        series = next((s for s in cat.get("datasetSeries", []) if series_uuid in s["identifier"]), None)
        if not series:
            raise RuntimeError(f"series {series_uuid} not in {CATALOG_URL}; catalog layout may have changed")
        last = series["last"]["identifier"]
        version = next((d for d in cat["dataset"] if d["identifier"] == last), None)
        if not version:
            raise RuntimeError(f"latest version {last} of series {series_uuid} not in {CATALOG_URL}")
        csvs = [d for d in version["distribution"] if d.get("format") == "CSV" and d.get("downloadURL")]
        apis = [uuid_of(d["accessURL"]) for d in version["distribution"]
                if d.get("format") == "API" and uuid_of(d["accessURL"]) != series_uuid]
        if len(csvs) != 1 or len(apis) != 1:
            raise RuntimeError(f"{version['title']}: expected one CSV and one version API, "
                               f"found {len(csvs)} and {len(apis)}")
        self.series_uuid = series_uuid
        self.title = version["title"]
        self.published = version["modified"]                  # YYYY-MM-DD
        self.periodicity = version.get("accrualPeriodicity") or series.get("accrualPeriodicity")
        self.csv_url = csvs[0]["downloadURL"]
        self.file_name = self.csv_url.rsplit("/", 1)[-1]
        self.version_uuid = apis[0]
        self.landing = (series.get("landingPage") or {}).get("accessURL")
        self.signal = f"'modified' of '{self.title}' in {CATALOG_URL}"

    def published_rows(self):
        """total_rows the data API reports for this version."""
        url = f"{API_BASE}/{self.version_uuid}/data/stats"
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=120) as resp:
            return int(json.loads(resp.read())["total_rows"]), url


def check_header(fieldnames, required, file_name):
    missing = [c for c in required if c not in (fieldnames or [])]
    if missing:
        raise RuntimeError(f"anomalous header: {file_name} lacks {missing}; got {fieldnames}. Not loaded.")


def check_published_count(run, release, row_count):
    expected, url = release.published_rows()
    if row_count != expected:
        raise RuntimeError(f"anomalous row count: {release.file_name} has {row_count:,} rows, the data API "
                           f"({url}) reports {expected:,} for this version. Not loaded.")
    run.note(f"row count {row_count:,} equals total_rows on {url}")


def check_parse(run, row_count, failed):
    share = failed / max(row_count, 1)
    run.note(f"unparseable rows: {failed:,} ({share:.2%})")
    if share > PARSE_FAIL_LIMIT:
        raise RuntimeError(f"anomalous parse: {failed:,} of {row_count:,} rows unreadable ({share:.1%}). Not loaded.")


def roster_npis(db, roster_ids):
    """{npi: provider_id or None} for the named rosters, or for every roster when none are named."""
    if roster_ids:
        known = {r["id"] for r in db.select("rosters", {"select": "id", "id": in_list(roster_ids)})}
        missing = sorted(set(roster_ids) - known)
        if missing:
            raise RuntimeError(f"no such roster: {', '.join(missing)}")
        members = db.select_all("roster_members", "roster_id,npi", order="roster_id,npi", roster_id=in_list(roster_ids))
    else:
        members = db.select_all("roster_members", "roster_id,npi", order="roster_id,npi")
    npis = sorted({m["npi"] for m in members})
    out = {n: None for n in npis}
    for batch in chunks(npis, 300):
        for r in db.select("providers", {"select": "id,npi", "npi": in_list(batch)}):
            out[r["npi"]] = r["id"]
    return out


def prior_found(db, source_id, claim_type, npis):
    """{npi: found?} from the receipts of this source's last completed run, for the given NPIs."""
    runs = db.select("ingestion_runs", {"select": "id", "source_id": f"eq.{source_id}", "status": "eq.completed",
                                        "order": "completed_at.desc", "limit": 1})
    if not runs:
        return {}
    out = {}
    for batch in chunks(sorted(npis), 300):
        for r in db.select("credential_receipts", {"select": "npi,normalized_status", "run_id": f"eq.{runs[0]['id']}",
                                                   "claim_type": f"eq.{claim_type}", "npi": in_list(batch)}):
            out[r["npi"]] = r["normalized_status"] != "not_found"
    return out


def check_flips(run, claim_type, found_now, allow_large_diff):
    """found_now: {npi: found in this file?}. Stops when too many roster NPIs changed sides since the last run."""
    before = prior_found(run.db, run.source_id, claim_type, found_now)
    if not before:
        run.note("flip check: no prior receipts from this source")
        return
    flips = [n for n, was in before.items() if was != found_now[n]]
    share = len(flips) / len(before)
    run.note(f"flip check: {len(flips)} of {len(before)} roster NPIs moved between found and not_found "
             f"since the last completed run ({share:.1%})" + (f": {flips[:10]}" if flips else ""))
    if len(before) >= FLIP_MIN and share > FLIP_LIMIT and not allow_large_diff:
        raise RuntimeError(f"anomalous diff: {share:.0%} of roster NPIs changed between found and not_found; "
                           f"rerun with --allow-large-diff after review")


def write_receipts(run, release, claim_type, roster, claims, retrieved_at, parser_version, limitations):
    """claims: {npi: (raw_status, normalized_status, claim, source_effective_at, lineage)} for NPIs in the file.
    Writes one receipt per roster NPI. Returns a Counter-ready dict of normalized_status -> count."""
    cadence = run.source.get("cadence_hours") or PERIODICITY_HOURS.get(release.periodicity, 720)
    due = (datetime.fromisoformat(retrieved_at) + timedelta(hours=cadence)).isoformat()
    common = {
        "claim_type": claim_type, "source_id": run.source_id, "artifact_id": run.artifact["id"], "run_id": run.id,
        "source_published_at": release.published, "retrieved_at": retrieved_at, "next_check_due_at": due,
        "origin": "real", "stage": "verified", "match_basis": "npi_exact", "match_confidence": 1.00,
        "parser_version": parser_version, "limitations": limitations,
    }
    rows, counts = [], {}
    for npi, provider_id in sorted(roster.items()):
        if npi in claims:
            raw, norm, claim, effective, lineage = claims[npi]
        else:
            raw, norm, claim, effective, lineage = (f"not in {release.file_name}", "not_found", {}, None, [])
        rows.append({**common, "npi": npi, "provider_id": provider_id, "raw_status": raw, "normalized_status": norm,
                     "claim": claim, "source_effective_at": effective, "lineage": lineage})
        counts[norm] = counts.get(norm, 0) + 1
    for batch in chunks(rows, BATCH):
        run.db.insert("credential_receipts", batch)
    run.counts["records_added"] = len(rows)
    run.note(f"{claim_type} receipts written for {len(rows)} roster NPIs: {counts}")
    log(f"{claim_type} receipts: {counts}")
    return counts


def now_utc_date():
    return datetime.now(timezone.utc).date().isoformat()

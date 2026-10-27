#!/usr/bin/env python3
"""
California DCA public information file ingestion, Medical Board and Osteopathic Medical Board: same
pipeline as tx_tmb.py (artifact, run, clocks, anomaly guard, NPI matching ladder, run-scoped snapshot in
state_license_lookups), plus a single-license re-verification through the DCA Search API.

Bulk files. DCA publishes one folder per board in a public Box folder linked from
https://www.dca.ca.gov/consumers/public_info/, refreshed at the start of each month. The page's own
download widget reads the folder with a read-only token from https://www.dca.ca.gov/boxToken/getToken;
this loader uses the same token and the Box API, nothing else. Each board folder holds a counts CSV and
one or more data files named *_DataNN.xls. Despite the extension the data files are tab-delimited text.
Columns (read from the header and checked against EXPECTED_HEADER; a changed header stops the run):
agency, license type, license number, name, public address of record, issue date, expiration date and
license status. No NPI (the Medical Board does not collect it), no birth year, no board actions.

Both boards' data files are one artifact: sha256 over the files' bytes in folder order, per-file hashes
in source_artifacts.notes. source_published_at is the earliest Box content_modified_at of the data files.

License numbers. The file stores digits only; the letter series lives in the license type name
("Physician and Surgeon A") or the osteopathic type code ("Osteopathic Physician and Surgeon 20A").
Rows are stored as the board writes the full number: A12345, C12345, G12345, 20A1234. NPPES writes the
same numbers with or without zero padding (G082297), which compare equal here. A bare-digit NPPES
number (12345) could be A, C or G and is never used.

Matching (boards/common.py ladder, with California rules for step 3):
  1. npi_exact             never: the file has no NPI
  2. license_number_exact  0.95  A/C/G/20A licenses only, the full number recorded for exactly one NPI,
                                 and that NPI shares the last or the first name with the board row (NPPES
                                 records sometimes carry another clinician's number)
  3. name_state_taxonomy   0.70  candidate; A/C/G/20A individuals only; the last + first name appears on
                                 exactly one A/C/G/20A license in both files (no birth year to tell two
                                 people apart) and belongs to exactly one NPPES 207*/208* NPI practicing in CA
  4. no row; counted as unmatched
Postgraduate training licenses, Mexico program licenses, special faculty permits and the non-physician
types are loaded only when step 2 matches them, which today it cannot: their numbers carry no series.

Re-verification. --reverify LICENSE --npi NPI asks the DCA Search API (getLicenseNumberSearch) for one
license, records the response as the artifact of a run of 'California DCA Search API', writes one
state_license_lookups row in that run, and calls receipts_for_license_reverify(run_id) for the receipt.
It refuses unless the current snapshot already links the NPI to that license by an exact basis. A
name-matched license cannot become license_number_exact by being re-verified. Needs DCA_APP_ID and DCA_APP_KEY from an
approved iServices application (https://iservices.dca.ca.gov/).

Usage:
  python3 boards/ca_dca.py                              # full run against the live database
  python3 boards/ca_dca.py --dry-run                    # download, parse and match; writes nothing
  python3 boards/ca_dca.py --run-id ID                  # adopt a run opened by poll_sources.py
  python3 boards/ca_dca.py --reverify A12345 --npi NPI  # one license through the DCA Search API
"""
import argparse
import csv
import hashlib
import json
import os
import re
import tempfile
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

import common
from common import LicenseRow, Matcher, assign_keys, log, norm_first, norm_last, report, status_guard
from core_run import USER_AGENT, Rest, now_iso, run_source

SOURCE = "California DCA public information file"
API_SOURCE = "California DCA Search API"
STATE = "CA"
PAGE_URL = "https://www.dca.ca.gov/consumers/public_info/index.shtml"
TOKEN_URL = "https://www.dca.ca.gov/boxToken/getToken"
ROOT_FOLDER = "66089580694"   # the folder id in the page's Box widget
BOX_API = "https://api.box.com/2.0"
API_BASE = "https://iservices.dca.ca.gov/api/search/v1"
BOARD_FOLDERS = ("MedicalBoard_0800", "Osteopathic_0900")
DATA_FILE = re.compile(r"_Data\d+\.xls$", re.I)
COUNTS_FILE = re.compile(r"_Counts\.csv$", re.I)

EXPECTED_HEADER = [
    "Agency Code", "Agency Name", "LicTypeCode", "License Type", "License Number", "Indiv/Org",
    "Org/Last Name", "First Name", "Middle Name", "Suffix", "Address Line 1", "Address Line 2", "City",
    "County", "State", "Zip", "Country", "Original Issue Date", "Expiration Date", "License Status",
]

# License Status -> normalized_status. Keys upper-cased. The page defines the field as "Current,
# Delinquent and Inactive"; the osteopathic file writes the last one as CurrentInactive. A delinquent
# license was not renewed and may not be used to practice. A string not in this table maps to 'unknown'.
LICENSE_STATUS = {
    "CURRENT": "active",
    "DELINQUENT": "expired",
    "CURRENTINACTIVE": "inactive",
    "INACTIVE": "inactive",
}

# License types whose full number the board writes with a series prefix. Every other type is stored
# as digits plus its type name and takes no part in license-number or name matching.
SERIES = {
    "PHYSICIAN AND SURGEON A": "A",
    "PHYSICIAN AND SURGEON C": "C",
    "PHYSICIAN AND SURGEON G": "G",
    "OSTEOPATHIC PHYSICIAN AND SURGEON 20A": "20A",
}
PHYSICIAN_TYPES = {"POSTGRADUATE TRAINING LICENSE", "PHYSICIAN'S & SURGEON'S FROM MEXICO", "SPECIAL FACULTY PERMIT"}
CANON = re.compile(r"^(20A|[ACG])0*(\d+)$")


def canon_license(s):
    """'G082297' -> 'G82297', 'A 1234' -> 'A1234', '20A01234' -> '20A1234'; anything else -> None."""
    m = CANON.match(common.norm_license(s))
    return f"{m.group(1)}{m.group(2)}" if m else None


def family(license_type):
    lt = (license_type or "").upper()
    return "physician" if lt in SERIES or lt in PHYSICIAN_TYPES else None


def parse_date(s):
    s = (s or "").strip()
    return datetime.strptime(s, "%m-%d-%Y").strftime("%Y-%m-%d") if s else None


# ----------------------------------------------------------------------------
# Box folder
# ----------------------------------------------------------------------------

class Box:
    def __init__(self):
        req = urllib.request.Request(TOKEN_URL, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=60) as resp:
            self.token = resp.read().decode().strip()
        if not self.token:
            raise RuntimeError(f"{TOKEN_URL} returned no token")

    def _open(self, url, timeout=600):
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {self.token}", "User-Agent": USER_AGENT})
        return urllib.request.urlopen(req, timeout=timeout)

    def items(self, folder_id):
        fields = "id,type,name,size,sha1,content_modified_at,modified_at"
        with self._open(f"{BOX_API}/folders/{folder_id}/items?limit=1000&fields={fields}", 60) as resp:
            data = json.loads(resp.read())
        if data.get("total_count", 0) > len(data.get("entries", [])):
            raise RuntimeError(f"Box folder {folder_id} has more than 1000 items; paging not implemented")
        return data["entries"]

    def download(self, item, dest):
        """Returns (sha256, byte_size, retrieved_at), and checks Box's own sha1 of the file."""
        sha256, sha1, size = hashlib.sha256(), hashlib.sha1(), 0
        with self._open(f"{BOX_API}/files/{item['id']}/content") as resp, open(dest, "wb") as out:
            while chunk := resp.read(1 << 20):
                sha256.update(chunk)
                sha1.update(chunk)
                out.write(chunk)
                size += len(chunk)
        if size == 0:
            raise RuntimeError(f"Box file {item['name']} returned 0 bytes")
        if item.get("sha1") and sha1.hexdigest() != item["sha1"]:
            raise RuntimeError(f"Box file {item['name']}: sha1 {sha1.hexdigest()} differs from Box's {item['sha1']}")
        log(f"downloaded {size:,} bytes: {item['name']}")
        return sha256.hexdigest(), size, now_iso()


def fetch_files(workdir):
    """Download every board's data and counts files. Returns (files, counts) in folder order."""
    box = Box()
    folders = {e["name"]: e for e in box.items(ROOT_FOLDER) if e["type"] == "folder"}
    missing = [n for n in BOARD_FOLDERS if n not in folders]
    if missing:
        raise RuntimeError(f"board folders missing from the DCA Box folder: {missing}")
    files, counts = [], {}
    for name in BOARD_FOLDERS:
        entries = sorted((e for e in box.items(folders[name]["id"]) if e["type"] == "file"), key=lambda e: e["name"])
        data = [e for e in entries if DATA_FILE.search(e["name"])]
        if not data:
            raise RuntimeError(f"no *_DataNN.xls file in Box folder {name}")
        for e in data:
            path = Path(workdir) / e["name"]
            sha, size, retrieved_at = box.download(e, path)
            files.append({"board": name, "item": e, "path": path, "sha256": sha, "size": size,
                          "retrieved_at": retrieved_at})
        for e in entries:
            if COUNTS_FILE.search(e["name"]):
                path = Path(workdir) / e["name"]
                box.download(e, path)
                with open(path, newline="", encoding="utf-8", errors="replace") as f:
                    for r in csv.DictReader(f):
                        if (r.get("License Type Name") or "").strip():
                            counts[(r["Agency Name"].strip(), r["License Type Name"].strip())] = int(r["License Count"])
    return files, counts


def bundle(files):
    """One artifact for the run: sha256 over all data files' bytes in folder order."""
    h = hashlib.sha256()
    for f in files:
        with open(f["path"], "rb") as fh:
            while chunk := fh.read(1 << 20):
                h.update(chunk)
    return h.hexdigest(), sum(f["size"] for f in files), max(f["retrieved_at"] for f in files)


def publisher_date(files):
    dates = [f["item"].get("content_modified_at") for f in files]
    if all(dates):
        return min(dates), "Box content_modified_at of " + ", ".join(
            f"{f['item']['name']} ({f['item']['content_modified_at']})" for f in files)
    return None, "Box content_modified_at of the data files"


# ----------------------------------------------------------------------------
# Parse and match
# ----------------------------------------------------------------------------

def parse_file(path):
    """Returns (header, rows, row_count, failed)."""
    rows, failed, row_count = [], 0, 0
    with open(path, newline="", encoding="utf-8", errors="replace") as f:
        reader = csv.reader(f, delimiter="\t")
        header = next(reader)
        if header != EXPECTED_HEADER:
            raise RuntimeError(f"{path.name}: header changed, not loaded. Got {header}")
        for values in reader:
            row_count += 1
            try:
                if len(values) != len(header):
                    raise ValueError(f"{len(values)} columns, expected {len(header)}")
                r = dict(zip(header, values))
                lic_type, digits = r["License Type"].strip(), r["License Number"].strip()
                if not lic_type or not digits.isdigit() or not r["Org/Last Name"].strip():
                    raise ValueError("missing license type, numeric license number or name")
                series = SERIES.get(lic_type.upper())
                number = f"{series}{int(digits)}" if series else digits
                individual = r["Indiv/Org"].strip() == "I"
                raw_status = r["License Status"].strip()
                status = LICENSE_STATUS.get(raw_status.upper(), "unknown")
                rows.append(LicenseRow(
                    license_type=lic_type,
                    license_number=number,
                    family=family(lic_type) if individual else None,
                    npi=None,  # the file carries no NPI
                    last_name=r["Org/Last Name"].strip() if individual else None,
                    first_name=r["First Name"].strip() if individual else None,
                    birth_year=None,
                    raw_status=raw_status,
                    normalized_status=status,
                    status_date=None,  # the file has no status date
                    issue_date=parse_date(r["Original Issue Date"]),
                    expiration_date=parse_date(r["Expiration Date"]),
                    actions=[],  # the file carries no board actions
                    raw=r,
                    placeholder=not series,  # no series, no full number: never matched on the number
                    physician_active=individual and bool(series) and status == "active",
                ))
            except Exception as e:
                failed += 1
                if failed <= 5:
                    log(f"{path.name}: unparseable row {row_count}: {e}")
    return header, rows, row_count, failed


class CaMatcher(Matcher):
    """The common ladder with California's license numbers and California's name rule."""

    def _load(self, family_of_license_type):
        super()._load(family_of_license_type)
        rekeyed, self.bare_digit_refs = defaultdict(set), 0
        for (fam, lic), ids in self.by_license.items():
            c = canon_license(lic)
            if c:
                rekeyed[(fam, c)] |= ids
            elif lic.isdigit():
                self.bare_digit_refs += 1
        self.by_license = rekeyed
        # NPPES records sometimes carry another clinician's license number. A license link whose NPI shares
        # neither the last nor the first name with the board row is refused; a changed surname alone is not.
        self.names = {}
        for chunk in common.chunks(sorted({pid for ids in rekeyed.values() for pid in ids}), 200):
            for p in self.db.select("providers", {"select": "id,last_name,first_name", "id": common.in_list(chunk)}):
                self.names[p["id"]] = (norm_last(p["last_name"]), norm_first(p["first_name"]))
        log(f"CA license references in A/C/G/20A form: {len(rekeyed):,}; bare-digit references not used: "
            f"{self.bare_digit_refs:,}")

    def same_person(self, provider_id, row):
        last, first = self.names.get(provider_id, ("", ""))
        return last == norm_last(row.last_name) or first == norm_first(row.first_name)

    def match_all(self, rows):
        series_rows = [r for r in rows if r.family == "physician" and not r.placeholder]
        holders = Counter((norm_last(r.last_name), norm_first(r.first_name)) for r in series_rows)
        matches, outcome = {}, Counter()
        for r in rows:
            if not r.placeholder:
                ids = (self.by_license.get((r.family, r.license_number), set())
                       | self.by_license.get((None, r.license_number), set()))
                if len(ids) == 1 and self.same_person(next(iter(ids)), r):
                    matches[r.key] = (next(iter(ids)), "license_number_exact")
                    outcome["license_number_exact"] += 1
                    continue
                if len(ids) == 1:
                    outcome["license_name_conflict"] += 1
                if len(ids) > 1:
                    outcome["license_number_ambiguous"] += 1
            if r.family == "physician" and not r.placeholder:
                name = (norm_last(r.last_name), norm_first(r.first_name))
                ids = self.by_name.get(name, set()) if all(name) else set()
                if len(ids) == 1 and holders[name] == 1:
                    matches[r.key] = (next(iter(ids)), "name_state_taxonomy")
                    outcome["name_state_taxonomy"] += 1
                    continue
                if len(ids) > 1 or (ids and holders[name] > 1):
                    outcome["name_ambiguous"] += 1
            outcome["unmatched"] += 1
        return matches, outcome


def parse_all(files, counts, note=log):
    header, rows, row_count, failed = None, [], 0, 0
    for f in files:
        h, r, n, bad = parse_file(f["path"])
        header = header or h
        rows += r
        row_count += n
        failed += bad
        f["row_count"] = n
        note(f"{f['item']['name']}: {n:,} rows, {bad} unparseable")
    by_type = Counter((r.raw["Agency Name"].strip(), r.license_type) for r in rows)
    diffs = {f"{a} / {t}": f"file {by_type.get((a, t), 0):,} vs counts {c:,}"
             for (a, t), c in counts.items() if by_type.get((a, t), 0) != c}
    note(f"counts CSV cross-check: {'all license types agree' if not diffs else diffs}")
    assign_keys(rows,
                base_key=lambda r: f"{r.raw['Agency Code']}|{r.license_type}|{r.license_number}",
                full_key=lambda r: f"{r.raw['Agency Code']}|{r.license_type}|{r.license_number}|"
                                   f"{r.raw['Org/Last Name']}|{r.raw['First Name']}|{r.issue_date}")
    return header, rows, row_count, failed


def check_board_rows(run, files):
    """Per board file, the same 50% guard as the bundle: a vanished osteopathic file would hide inside it."""
    runs = run.db.select("ingestion_runs", {
        "select": "source_artifacts(notes)", "source_id": f"eq.{run.source_id}", "status": "eq.completed",
        "artifact_id": "not.is.null", "order": "completed_at.desc", "limit": 1})
    notes = ((runs[0].get("source_artifacts") or {}).get("notes") if runs else None) or "{}"
    prior = {f["file_name"]: f["row_count"] for f in json.loads(notes).get("files", [])}
    for f in files:
        before = prior.get(f["item"]["name"])
        if before and f["row_count"] < before * 0.5:
            raise RuntimeError(f"anomalous row count: {f['item']['name']} has {f['row_count']:,} rows, "
                               f"{before:,} in the last completed run; not loaded")


def artifact_notes(files):
    return json.dumps({"files": [{
        "board": f["board"], "file_name": f["item"]["name"], "box_file_id": f["item"]["id"],
        "box_sha1": f["item"].get("sha1"), "sha256": f["sha256"], "byte_size": f["size"],
        "row_count": f["row_count"], "content_modified_at": f["item"].get("content_modified_at"),
    } for f in files]}, sort_keys=True)


# ----------------------------------------------------------------------------
# DCA Search API re-verification
# ----------------------------------------------------------------------------

def api_credentials():
    app_id, app_key = os.environ.get("DCA_APP_ID"), os.environ.get("DCA_APP_KEY")
    if not (app_id and app_key):
        raise SystemExit("DCA_APP_ID and DCA_APP_KEY are not set. Register at https://iservices.dca.ca.gov/, "
                         "subscribe to the DCA Search API, create an application and wait for DCA to approve it, "
                         "then put both values in .env.")
    return app_id, app_key


def api_get(path, params):
    app_id, app_key = api_credentials()
    url = f"{API_BASE}/{path}" + (f"?{urllib.parse.urlencode(params)}" if params else "")
    req = urllib.request.Request(url, headers={"APP_ID": app_id, "APP_KEY": app_key, "User-Agent": USER_AGENT,
                                               "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read(), url


def exact_link(db, npi, license_number):
    """The current exact link between this NPI and this CA license, or None. Every exact link the bulk run
    accepted is in its snapshot; one it refused (ambiguous, or a name conflict) is not, and stays refused."""
    prov = db.select("providers", {"select": "id", "npi": f"eq.{npi}"})
    if not prov:
        raise SystemExit(f"NPI {npi} is not in providers")
    pid = prov[0]["id"]
    for r in db.select("v_state_licenses_current", {"select": "id,license_number,match_basis", "provider_id": f"eq.{pid}",
                                                    "state_code": f"eq.{STATE}",
                                                    "match_basis": "in.(npi_exact,license_number_exact)"}):
        if canon_license(r["license_number"]) == license_number:
            return pid, f"{r['match_basis']} link in state_license_lookups {r['id']}"
    return pid, None


def reverify(db, license_number, npi):
    lic = canon_license(license_number)
    if not lic:
        raise SystemExit(f"{license_number!r} is not an A, C, G or 20A license number")
    series, digits = CANON.match(lic).groups()
    api_credentials()  # before any run row exists: a missing key is not a failed run
    provider_id, basis = exact_link(db, npi, lic)
    if not basis:
        raise SystemExit(f"NPI {npi} has no exact link to CA license {lic}. A name-matched license cannot be "
                         f"re-verified into a license_number_exact receipt.")
    bulk = db.select("v_state_licenses_current", {"select": "license_type,raw_response", "state_code": f"eq.{STATE}",
                                                  "license_number": f"eq.{lic}", "limit": 1})
    lic_type_code = (bulk[0]["raw_response"] or {}).get("LicTypeCode") if bulk else None
    if not lic_type_code:
        lic_type_code = "9001" if series == "20A" else "8002"  # the type codes the bulk file uses for these series
    log(f"re-verifying {lic} (licType {lic_type_code}, rank {series}) for NPI {npi}; link: {basis}")

    with tempfile.TemporaryDirectory(prefix="hkg_ca_dca_api_") as workdir:
        def body(run):
            run.set_published(None, "the DCA Search API (a live registry read; no publisher file date)")
            params = {"licType": lic_type_code, "licNumber": digits}
            if series != "20A":
                params["licRank"] = series
            raw, url = api_get("licenseSearchService/getLicenseNumberSearch", params)
            statuses_raw, _ = api_get("statusListService/getLicenseStatuses", None)
            path = Path(workdir) / f"dca_search_{lic}.json"
            path.write_bytes(raw)
            doc = json.loads(raw)
            details = [d for item in doc.get("licenseDetails", []) for d in item.get("getFullLicenseDetail", [])]
            run.register_artifact(path, path.name, url, hashlib.sha256(raw).hexdigest(), len(raw), len(details),
                                  now_iso())
            lic_rows = [ld for d in details for ld in d.get("getLicenseDetails", [])]
            if len(lic_rows) != 1:
                raise RuntimeError(f"DCA Search API returned {len(lic_rows)} license records for {lic}; expected 1")
            ld = lic_rows[0]
            answered = re.sub(r"\D", "", ld.get("licNumber") or "")
            if not answered or int(answered) != int(digits):
                raise RuntimeError(f"DCA Search API answered for license {ld.get('licNumber')!r}, not {lic}")
            code = ld.get("primaryStatusCode")
            desc = next((s.get("statusDescription") for c in json.loads(statuses_raw).get("getLicenseStatuses", [])
                         for s in c.get("statusDetails", []) if s.get("statusCode") == code), None)
            raw_status = f"{desc or ''} (primaryStatusCode {code})".strip()
            normalized = API_STATUS.get((desc or "").strip().upper(), "unknown")
            run.note(f"DCA Search API: {lic} status {raw_status!r} -> {normalized}")
            run.db.insert("state_license_lookups", [{
                "source_id": run.source_id, "run_id": run.id, "artifact_id": run.artifact["id"],
                "provider_id": provider_id, "state_code": STATE, "license_number": lic,
                "license_type": common.clip(bulk[0]["license_type"] if bulk else None, 100),
                "status": normalized, "raw_status": raw_status, "normalized_status": normalized,
                "issue_date": _api_date(ld.get("issueDate")), "expiration_date": _api_date(ld.get("expDate")),
                "disciplinary_actions": [], "lookup_date": now_iso(), "raw_response": doc,
                "data_source": API_SOURCE, "source_record_key": f"{lic_type_code}|{lic}",
                "match_basis": "license_number_exact", "match_confidence": 0.95, "stage": "verified",
            }])
            run.counts.update(records_processed=1, records_added=1)

        run = run_source(API_SOURCE, "incremental", body, db)
    receipts = db.request("POST", "rpc/receipts_for_license_reverify", body={"p_run_id": run.id})[1]
    print(json.dumps(receipts, indent=2, default=str))
    return receipts


# DCA Search API status descriptions -> normalized_status. Only the strings the public information page
# defines are mapped until getLicenseStatuses has been read with a key; anything else maps to 'unknown'.
API_STATUS = {
    "CURRENT": "active",
    "DELINQUENT": "expired",
    "CURRENT INACTIVE": "inactive",
    "CURRENTINACTIVE": "inactive",
    "INACTIVE": "inactive",
}


def _api_date(s):
    s = (s or "").strip()
    for fmt in ("%m/%d/%Y", "%Y-%m-%d", "%m-%d-%Y"):
        try:
            return datetime.strptime(s[:10], fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


# ----------------------------------------------------------------------------

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--run-id", help="adopt a 'running' ingestion_runs row opened by poll_sources.py")
    ap.add_argument("--reverify", metavar="LICENSE", help="re-verify one license through the DCA Search API")
    ap.add_argument("--npi", help="the NPI the re-verified license belongs to")
    args = ap.parse_args(argv)
    db = Rest()

    if args.reverify:
        if not args.npi:
            ap.error("--reverify needs --npi")
        reverify(db, args.reverify, args.npi)
        return

    with tempfile.TemporaryDirectory(prefix="hkg_ca_dca_") as workdir:
        if args.dry_run:
            files, counts = fetch_files(workdir)
            published, how = publisher_date(files)
            header, rows, row_count, failed = parse_all(files, counts)
            source_id = db.select("data_sources", {"select": "id", "name": f"eq.{SOURCE}"})[0]["id"]
            matches, outcome = CaMatcher(db, STATE, source_id, family).match_all(rows)
            log(f"dry run: {row_count:,} rows, {failed} unparseable, published {published} ({how}), "
                f"bundle sha256 {bundle(files)[0]}")
            report(STATE, rows, matches, outcome, LICENSE_STATUS, [], 0, 0)
            log(f"license links refused for a name conflict: {outcome['license_name_conflict']:,}")
            return

        def body(run):
            files, counts = fetch_files(workdir)
            run.set_published(*publisher_date(files))
            header, rows, row_count, failed = parse_all(files, counts, run.note)
            sha, size, retrieved_at = bundle(files)
            artifact = run.register_artifact(None, "+".join(f["item"]["name"] for f in files), PAGE_URL, sha, size,
                                             row_count, retrieved_at)
            if not artifact.get("notes"):
                run.db.patch("source_artifacts", {"notes": artifact_notes(files)}, id=f"eq.{artifact['id']}")
            run.check_row_count(row_count)
            check_board_rows(run, files)
            status_guard(run, rows)
            common.set_board_fields(db, STATE, header)
            matches, outcome = CaMatcher(db, STATE, run.source_id, family).match_all(rows)
            licenses, actions = common.write_snapshot(run, STATE, SOURCE, PAGE_URL, rows, matches, retrieved_at)
            common.prune_snapshots(run)
            text = report(STATE, rows, matches, outcome, LICENSE_STATUS, [], licenses, actions)
            run.note(text.split("\nnormalized_status mapping")[0])
            run.note(f"license links refused for a name conflict: {outcome['license_name_conflict']:,}")
            run.counts.update(records_processed=row_count, records_added=licenses, records_updated=0,
                              records_failed=failed)

        run_source(SOURCE, "full", body, db, run_id=args.run_id)


if __name__ == "__main__":
    main()

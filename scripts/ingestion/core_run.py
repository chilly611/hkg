#!/usr/bin/env python3
"""
Shared run bookkeeping for the core sources (NPPES, OIG LEIE, SAM.gov).

Every core ingestion goes through run_source():
  1. an ingestion_runs row is inserted with status 'running' and detected_at = now, or, when
     scripts/poll_sources.py detected the release, the poller's 'running' row is adopted by id
     (--run-id) and its detected_at is kept
  2. the script downloads the file; register_artifact() hashes it and inserts one
     source_artifacts row, or reuses the row with the same (source_id, sha256) ("unchanged file")
  3. check_row_count() refuses to load a file with fewer than 50% of the rows of the
     artifact behind the last completed run ("anomalous row count")
  4. on success the run is marked 'completed' with its counts; on any exception it is
     marked 'failed' with error_log and the exception is re-raised. No run is left 'running'.

Credentials come from the repo-root .env (SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY) or the
environment. Nothing here prints a key. Stdlib only.
"""
import hashlib
import json
import os
import sys
import time
import traceback
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
USER_AGENT = "HKG-ingest/1.0 (+https://health.theknowledgegardens.com)"
ANOMALY_RATIO = 0.5


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def load_env():
    env_path = REPO_ROOT / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
    missing = [k for k in ("SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY") if not os.environ.get(k)]
    if missing:
        sys.exit(f"Missing {', '.join(missing)}: put them in {env_path} or the environment.")
    return os.environ["SUPABASE_URL"].rstrip("/"), os.environ["SUPABASE_SERVICE_ROLE_KEY"]


# ----------------------------------------------------------------------------
# PostgREST client
# ----------------------------------------------------------------------------

class Rest:
    def __init__(self, url=None, key=None):
        if not (url and key):
            url, key = load_env()
        self.base = f"{url}/rest/v1"
        self.key = key

    def request(self, method, table, params=None, body=None, prefer=None, timeout=120, retries=3):
        qs = urllib.parse.urlencode(params or {}, safe="(),.:*!", quote_via=urllib.parse.quote)
        url = f"{self.base}/{table}" + (f"?{qs}" if qs else "")
        headers = {"apikey": self.key, "Content-Type": "application/json"}
        if self.key.startswith("eyJ"):  # legacy JWT key; new sb_secret_ keys go in apikey only
            headers["Authorization"] = f"Bearer {self.key}"
        if prefer:
            headers["Prefer"] = prefer
        data = json.dumps(body).encode("utf-8") if body is not None else None
        for attempt in range(retries + 1):
            req = urllib.request.Request(url, data=data, headers=headers, method=method)
            try:
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    raw = resp.read()
                    return resp.headers, (json.loads(raw) if raw else None)
            except urllib.error.HTTPError as e:
                detail = e.read().decode("utf-8", "replace")[:500]
                if e.code >= 500 and attempt < retries:
                    time.sleep(2 ** attempt)
                    continue
                raise RuntimeError(f"PostgREST {method} {table} -> HTTP {e.code}: {detail}") from None
            except (urllib.error.URLError, TimeoutError) as e:
                if attempt < retries:
                    time.sleep(2 ** attempt)
                    continue
                raise RuntimeError(f"PostgREST {method} {table} -> {e}") from None

    def select(self, table, params):
        return self.request("GET", table, params)[1]

    def select_all(self, table, select, order="id", page=1000, **filters):
        rows, offset = [], 0
        while True:
            params = {"select": select, "order": order, "limit": page, "offset": offset, **filters}
            batch = self.select(table, params)
            rows.extend(batch)
            if len(batch) < page:
                return rows
            offset += page

    def count(self, table, **filters):
        headers, _ = self.request("GET", table, {"select": "id", "limit": 1, **filters}, prefer="count=exact")
        return int(headers.get("Content-Range", "*/0").split("/")[-1])

    def insert(self, table, rows, returning=False, upsert_on=None):
        prefer = ["return=representation" if returning else "return=minimal"]
        params = {}
        if upsert_on:
            prefer.append("resolution=merge-duplicates")
            params["on_conflict"] = upsert_on
        return self.request("POST", table, params, rows, prefer=",".join(prefer))[1]

    def patch(self, table, body, **filters):
        return self.request("PATCH", table, filters, body, prefer="return=minimal")[1]

    def delete(self, table, **filters):
        return self.request("DELETE", table, filters, prefer="return=minimal")[1]


def in_list(values):
    return "in.(" + ",".join(f'"{v}"' for v in values) + ")"


def chunks(seq, n):
    for i in range(0, len(seq), n):
        yield seq[i:i + n]


# ----------------------------------------------------------------------------
# Downloads and artifacts
# ----------------------------------------------------------------------------

def fetch_text(url, timeout=60):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode(resp.headers.get_content_charset() or "utf-8", "replace"), resp.headers


def download(url, dest, timeout=600):
    """Stream url to dest. Returns (sha256, byte_size, response headers, retrieved_at)."""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    h = hashlib.sha256()
    size = 0
    with urllib.request.urlopen(req, timeout=timeout) as resp, open(dest, "wb") as out:
        if resp.status != 200:
            raise RuntimeError(f"download {url} -> HTTP {resp.status}")
        headers = resp.headers
        while True:
            chunk = resp.read(1 << 20)
            if not chunk:
                break
            h.update(chunk)
            out.write(chunk)
            size += len(chunk)
    retrieved_at = now_iso()
    if size == 0:
        raise RuntimeError(f"download {url} returned 0 bytes")
    log(f"downloaded {size:,} bytes from {url}")
    return h.hexdigest(), size, headers, retrieved_at


class Run:
    """One ingestion_runs row and the artifact it read."""

    def __init__(self, db, source_name, run_type):
        rows = db.select("data_sources", {"select": "id,name,cadence_hours", "name": f"eq.{source_name}"})
        if not rows:
            raise RuntimeError(f"data_sources has no row named {source_name!r}")
        self.db = db
        self.source = rows[0]
        self.source_id = rows[0]["id"]
        self.run_type = run_type
        self.id = None
        self.artifact = None
        self.source_published_at = None
        self.notes = []
        self.counts = {"records_processed": 0, "records_added": 0, "records_updated": 0, "records_failed": 0}

    def note(self, text):
        self.notes.append(text)
        log(text)

    def start(self):
        ts = now_iso()
        row = self.db.insert("ingestion_runs", [{
            "source_id": self.source_id,
            "run_type": self.run_type,
            "status": "running",
            "started_at": ts,
            "detected_at": ts,  # run by hand, not by the poller: detection is the start of this run
        }], returning=True)[0]
        self.id = row["id"]
        log(f"run {self.id} started for {self.source['name']}")

    def adopt(self, run_id):
        """Take over a 'running' row the poller created. Its detected_at and started_at stay as written."""
        rows = self.db.select("ingestion_runs", {"select": "id,source_id,status,run_notes", "id": f"eq.{run_id}"})
        if not rows:
            raise RuntimeError(f"ingestion_runs has no row {run_id}")
        row = rows[0]
        if row["source_id"] != self.source_id or row["status"] != "running":
            raise RuntimeError(f"run {run_id} is {row['status']} for source {row['source_id']}; "
                               f"expected a running run for {self.source['name']}")
        self.id = row["id"]
        if row.get("run_notes"):
            self.notes.append(row["run_notes"])
        log(f"run {self.id} adopted for {self.source['name']}")

    def update(self, **fields):
        self.db.patch("ingestion_runs", fields, id=f"eq.{self.id}")

    def set_published(self, source_published_at, how):
        """Record the publisher's date. None means it could not be read; never guessed."""
        if source_published_at:
            self.note(f"source_published_at {source_published_at} from {how}")
        else:
            self.note(f"[CONFIRM] publisher date could not be read from {how}; source_published_at left NULL")
        self.source_published_at = source_published_at
        self.update(source_published_at=source_published_at, run_notes="\n".join(self.notes))

    def register_artifact(self, path, file_name, download_url, sha256, byte_size, row_count, retrieved_at):
        existing = self.db.select("source_artifacts", {
            "select": "*", "source_id": f"eq.{self.source_id}", "sha256": f"eq.{sha256}"})
        if existing:
            self.artifact = existing[0]
            self.note(f"unchanged file: {file_name} sha256 {sha256} matches artifact {self.artifact['id']}")
        else:
            self.artifact = self.db.insert("source_artifacts", [{
                "source_id": self.source_id,
                "file_name": file_name,
                "download_url": download_url,
                "sha256": sha256,
                "byte_size": byte_size,
                "row_count": row_count,
                "source_published_at": self.source_published_at,
                "retrieved_at": retrieved_at,
            }], returning=True)[0]
            log(f"artifact {self.artifact['id']} {file_name} {row_count:,} rows sha256 {sha256}")
        self.update(artifact_id=self.artifact["id"], run_notes="\n".join(self.notes))
        return self.artifact

    def baseline_row_count(self, same_kind=None):
        """row_count of the artifact behind the last completed run of this source.
        same_kind(file_name) -> bool limits the comparison to files of the same kind (weekly vs monthly)."""
        runs = self.db.select("ingestion_runs", {
            "select": "artifact_id,completed_at,source_artifacts(file_name,row_count)",
            "source_id": f"eq.{self.source_id}", "status": "eq.completed",
            "artifact_id": "not.is.null", "order": "completed_at.desc", "limit": 20})
        for r in runs:
            art = r.get("source_artifacts") or {}
            if art.get("row_count") is not None and (not same_kind or same_kind(art["file_name"])):
                return art["row_count"], f"artifact {r['artifact_id']}"
        return None, None

    def check_row_count(self, row_count, same_kind=None, table_fallback=None):
        """Stop before loading if the file has fewer than 50% of the baseline rows."""
        baseline, basis = self.baseline_row_count(same_kind)
        if baseline is None and table_fallback is not None:
            baseline, basis = table_fallback, "current table row count (no prior artifact)"
        if row_count == 0 or (baseline and row_count < baseline * ANOMALY_RATIO):
            raise RuntimeError(f"anomalous row count: file has {row_count:,} rows, baseline {baseline} from {basis}; not loaded")
        if baseline is None:
            self.note(f"row count {row_count:,}; no baseline to compare against")
        else:
            self.note(f"row count {row_count:,} vs baseline {baseline:,} from {basis}")

    def complete(self):
        self.update(status="completed", completed_at=now_iso(), run_notes="\n".join(self.notes), **self.counts)
        log(f"run {self.id} completed: {self.counts}")

    def fail(self, exc):
        err = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))[-4000:]
        self.update(status="failed", completed_at=now_iso(), error_log=err,
                    run_notes="\n".join(self.notes), **self.counts)
        log(f"run {self.id} FAILED: {exc}")


def run_source(source_name, run_type, body, db=None, run_id=None):
    """Create (or adopt, with run_id) a run, call body(run), and close the run as completed or failed.
    Re-raises on failure."""
    db = db or Rest()
    run = Run(db, source_name, run_type)
    if run_id:
        run.adopt(run_id)
    else:
        run.start()
    try:
        body(run)
    except BaseException as exc:  # KeyboardInterrupt too: never leave a run 'running'
        try:
            run.fail(exc)
        except Exception as mark_err:
            log(f"could not mark run {run.id} failed: {mark_err}")
        raise
    run.complete()
    return run


def print_source_status(db=None):
    db = db or Rest()
    rows = db.select("v_source_status", {"select": "name,freshness,file_date,last_run_at"})
    width = max(len(r["name"]) for r in rows)
    print(f"{'name':<{width}}  {'freshness':<11}  {'file_date':<25}  last_run_at")
    for r in rows:
        print(f"{r['name']:<{width}}  {r['freshness'] or '':<11}  {str(r['file_date']):<25}  {r['last_run_at']}")
    return rows

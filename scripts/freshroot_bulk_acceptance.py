#!/usr/bin/env python3
"""
freshroot_bulk_acceptance.py · the acceptance run for bulk input and report output, end to end through the API.

  python scripts/freshroot_bulk_acceptance.py --out /tmp/bulk_acceptance

1. Picks N NPIs (default 1,000) from the TX, FL and CA board snapshots: the latest completed run of each state's
   bulk licensing source, the license rows linked to an individual NPI, a third from each state, in a fixed order
   (sha256 of the row's provider id with --seed), leaving out NPIs already on any roster.
2. Creates the scratch roster (--roster, rosters.test = true) with no members. A test roster is skipped by the
   hourly refresh; its receipts stay, since receipts are append-only.
3. Issues a tenant key bound only to that roster. The key lives in this process's memory: it is never printed and
   never written to a file, and the tenant is deleted when the run ends, pass or fail.
4. POSTs the NPIs to /v1/rosters/{id}/jobs as a CSV body (npi, and state: the board file the NPI was picked from,
   so its license is checked there), polls GET /v1/jobs/{id} until done or failed, and prints
   the final counts.
5. GETs /v1/rosters/{id}/export, saves the zip in --out, checks it holds the five files, and prints report.md.

Same client and env as the loaders (scripts/ingestion/core_run.py): SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY from
the repo-root .env or the environment. The service role key is used only for the admin steps (roster, tenant,
picking NPIs) and is never sent to the edge function. Stdlib only.
"""

import argparse
import hashlib
import io
import json
import secrets
import sys
import time
import urllib.error
import urllib.request
import zipfile
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "ingestion"))

from core_run import Rest, chunks, log  # noqa: E402

STATES = ["TX", "FL", "CA"]
EXPORT_FILES = {"receipts.csv", "receipts.json", "unmatched.csv", "coverage.md", "report.md"}


def latest_board_run(db, state):
    srcs = db.select("data_sources", {"select": "id,name", "jurisdiction": f"eq.{state}", "category": "eq.licensing",
                                      "claim_types": "cs.{state_license}", "or": "(format.is.null,format.neq.api)"})
    if len(srcs) != 1:
        sys.exit(f"error: expected one {state} board source, found {len(srcs)}")
    runs = db.select("ingestion_runs", {"select": "id,completed_at", "source_id": f"eq.{srcs[0]['id']}",
                                        "status": "eq.completed", "order": "completed_at.desc", "limit": 1})
    if not runs:
        sys.exit(f"error: {srcs[0]['name']} has no completed run")
    return srcs[0]["name"], runs[0]


def pick_npis(db, total, seed):
    """{state: [npi, ...]} with total NPIs in all, split as evenly as the states allow."""
    taken = {m["npi"] for m in db.select_all("roster_members", "roster_id,npi", order="roster_id,npi")}
    per = {st: total // len(STATES) + (1 if i < total % len(STATES) else 0) for i, st in enumerate(STATES)}
    out, seen = {}, set(taken)
    for st in STATES:
        name, run = latest_board_run(db, st)
        rows = db.select_all("state_license_lookups", "id,provider_id", order="id", run_id=f"eq.{run['id']}")
        ids = sorted({r["provider_id"] for r in rows if r["provider_id"]},
                     key=lambda pid: hashlib.sha256(f"{seed}:{pid}".encode()).hexdigest())
        picked = []
        for batch in chunks(ids, 100):
            provs = {p["id"]: p for p in db.select("providers", {
                "select": "id,npi,entity_type", "id": f"in.({','.join(batch)})"})}
            for pid in batch:
                p = provs.get(pid)
                if p and p["entity_type"] == "individual" and p["npi"] not in seen:
                    seen.add(p["npi"])
                    picked.append(p["npi"])
                if len(picked) == per[st]:
                    break
            if len(picked) == per[st]:
                break
        log(f"{st}: {len(picked)} NPIs from {name}, run {run['id']} (completed {run['completed_at']}), "
            f"{len(ids):,} linked providers in the snapshot")
        out[st] = picked
    return out


def api(base, key, method, path, body=None, content_type=None, raw=False, timeout=300):
    headers = {"X-FreshRoot-Key": key}
    if content_type:
        headers["Content-Type"] = content_type
    req = urllib.request.Request(f"{base}{path}", data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = resp.read()
            return resp.status, (data if raw else json.loads(data))
    except urllib.error.HTTPError as e:
        sys.exit(f"error: {method} {path} -> HTTP {e.code}: {e.read().decode('utf-8', 'replace')[:500]}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    stamp = datetime.now().strftime("%Y-%m-%d")
    ap.add_argument("--roster", default=f"scratch-bulk-{stamp}", help="scratch roster id (created, test = true)")
    ap.add_argument("--count", type=int, default=1000)
    ap.add_argument("--seed", default=stamp, help="fixes which NPIs are picked")
    ap.add_argument("--out", required=True, help="directory for the export zip (keep it out of the repo)")
    ap.add_argument("--poll", type=float, default=5.0)
    ap.add_argument("--max-minutes", type=float, default=60.0)
    args = ap.parse_args()

    db = Rest()
    fn = db.base.replace("/rest/v1", "/functions/v1/freshroot")
    if db.select("rosters", {"select": "id", "id": f"eq.{args.roster}"}):
        sys.exit(f"error: roster {args.roster} exists; pick another --roster (receipts are append-only, so a "
                 "scratch roster is never reused)")

    by_state = pick_npis(db, args.count, args.seed)
    npis = [n for st in STATES for n in by_state[st]]
    if len(npis) != args.count:
        sys.exit(f"error: picked {len(npis)} NPIs, wanted {args.count}")
    db.insert("rosters", [{
        "id": args.roster, "name": f"Scratch: bulk job acceptance ({args.roster})", "test": True,
        "source_file": "TX, FL and CA board snapshots, latest completed runs: "
                       + ", ".join(f"{st} {len(by_state[st])}" for st in STATES),
    }])
    log(f"roster {args.roster} created, test = true, no members")

    tenant = f"scratch-{args.roster}"
    key = "fr_" + secrets.token_urlsafe(32)
    db.insert("api_tenants", [{"name": tenant, "key_hash": hashlib.sha256(key.encode()).hexdigest(),
                               "roster_ids": [args.roster]}])
    log(f"tenant {tenant} created for this run only (key held in memory)")
    try:
        csv_body = ("npi,state\n" + "".join(f"{n},{st}\n" for st in STATES for n in by_state[st])).encode()
        t0 = time.time()
        status, job = api(fn, key, "POST", f"/v1/rosters/{args.roster}/jobs", csv_body, "text/csv")
        log(f"POST jobs -> {status}: job {job['job_id']}, {job['counts']['input']} input lines, status {job['status']}")
        last = None
        while True:
            _, job = api(fn, key, "GET", f"/v1/jobs/{job['job_id']}")
            line = (f"{job['status']}: {job['progress']['processed']}/{job['progress']['total']} processed, "
                    f"{job['counts']['added']} added, {job['counts']['receipted']} receipted, "
                    f"{job['counts']['receipts_written']} receipts, {job['counts']['unmatched']} unmatched")
            if line != last:
                log(line)
                last = line
            if job["status"] in ("done", "failed"):
                break
            if time.time() - t0 > args.max_minutes * 60:
                sys.exit(f"error: job {job['job_id']} still {job['status']} after {args.max_minutes} minutes")
            time.sleep(args.poll)
        log(f"job {job['status']} in {time.time() - t0:.0f} s")
        print("\nFinal job:\n" + json.dumps({k: job[k] for k in (
            "job_id", "roster_id", "status", "progress", "counts", "guard", "write_failures", "error",
            "created_at", "started_at", "finished_at")}, indent=2))
        print("Unmatched:", json.dumps(job["unmatched"], indent=2))

        _, blob = api(fn, key, "GET", f"/v1/rosters/{args.roster}/export?include_unaccepted=true", raw=True, timeout=600)
        out = Path(args.out)
        out.mkdir(parents=True, exist_ok=True)
        zpath = out / f"freshroot-{args.roster}.zip"
        zpath.write_bytes(blob)
        with zipfile.ZipFile(io.BytesIO(blob)) as z:
            names = set(z.namelist())
            bad = z.testzip()
            if bad or names != EXPORT_FILES:
                sys.exit(f"error: export zip is wrong: files {sorted(names)}, first bad member {bad}")
            report = z.read("report.md").decode()
            sizes = {n: z.getinfo(n).file_size for n in sorted(names)}
        log(f"export saved to {zpath} ({len(blob):,} bytes): {sizes}")
        print("\n" + report)
        return 0 if job["status"] == "done" else 1
    finally:
        db.delete("api_tenants", name=f"eq.{tenant}")
        log(f"tenant {tenant} deleted; roster {args.roster} and its receipts stay (test = true)")


if __name__ == "__main__":
    sys.exit(main())

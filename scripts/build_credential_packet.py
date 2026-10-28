#!/usr/bin/env python3
"""
build_credential_packet.py · roster of NPIs in, the packet out.

Outputs (in --out, default ./packet_<timestamp>/):
  receipts.csv          one row per receipt (the sellable rows)
  receipts.json         the same rows, plus the roster and coverage, as one document
  coverage.md           what is covered today, by claim type and jurisdiction, and what is not
  unmatched.csv         NPIs on the roster that are not in the garden at all

Talks to Supabase over PostgREST (HTTPS only, works from the Mac and from a sandbox), through the same
client as the loaders (scripts/ingestion/core_run.py), so it reads the repo-root .env and sends an sb_secret
key in the apikey header only.
Env:
  SUPABASE_URL                 e.g. https://opbrzaegvfyjpyyrmdfe.supabase.co
  SUPABASE_SERVICE_ROLE_KEY    server-side only. Never in a page, never in git.

Usage:
  python build_credential_packet.py roster.csv --out ./packet_modio
  python build_credential_packet.py roster.csv --write-receipts      # runs the SQL functions first (needs completed runs)
  python build_credential_packet.py roster.csv --origin synthetic    # demo packets are labeled, never shipped

The roster file is a CSV with a column named npi, or a plain text file with one NPI per line. An optional
state column (TX, FL, CA, UT) asks --write-receipts for that state's license receipt for that NPI; other
columns are ignored.
--write-receipts skips any NPI that already holds a receipt of that claim type from the source's latest
completed run, so a re-run after a partial failure never writes the same receipt twice.
Rows from sources with accepted_for_sale = false are included in the packet but flagged; they never ship to a buyer.
A row is shippable only when its source is accepted for sale and it is real, verified and not past due. A packet
with any row that is not shippable is headed "Internal review, rights pending".
"""

import argparse
import csv
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "ingestion"))

from core_run import Rest  # noqa: E402

REST = None
RPC_BATCH = 50
EXCLUSIONS_BATCH = 12  # receipts_for_exclusions name-scans SAM once per NPI; 25 hit the API statement timeout

PILOT_STATES = ["TX", "FL", "CA", "UT"]  # the pilot claims and the not-yet list live in SQL: roster_coverage()

RECEIPT_COLUMNS = [
    "npi", "claim_type", "jurisdiction", "license_number", "normalized_status", "raw_status",
    "source_name", "source_published_at", "source_effective_at", "retrieved_at", "next_check_due_at",
    "origin", "stage", "match_basis", "match_confidence", "accepted_for_sale", "shippable", "limitations",
    "receipt_id", "supersedes_id", "artifact_sha256",
]


def die(msg):
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(1)


def rest():
    global REST
    if REST is None:
        REST = Rest()
    return REST


def read_roster(path):
    """Returns (npis, states): the NPIs in roster order, and the state asked for each NPI that names one."""
    p = Path(path)
    if not p.exists():
        die(f"roster not found: {path}")
    pairs = []
    with p.open(newline="") as f:
        sample = f.read(2048)
        f.seek(0)
        if "," in sample or "npi" in sample.lower():
            reader = csv.DictReader(f)
            fields = {c.strip().lower(): c for c in (reader.fieldnames or []) if c}
            col, scol = fields.get("npi"), fields.get("state")
            if col is None:
                f.seek(0)
                pairs = [(line.strip(), "") for line in f if line.strip()]
            else:
                pairs = [(row[col].strip(), (row.get(scol) or "").strip().upper() if scol else "")
                         for row in reader if row.get(col)]
        else:
            pairs = [(line.strip(), "") for line in f if line.strip()]
    clean = []
    bad = []
    states = {}
    for n, st in pairs:
        digits = "".join(ch for ch in n if ch.isdigit())
        if len(digits) != 10:
            bad.append(digits or n)
            continue
        clean.append(digits)
        if st:
            if st not in PILOT_STATES:
                die(f"roster asks for state {st} for {digits}; pilot states are {', '.join(PILOT_STATES)}")
            if states.get(digits, st) != st:
                die(f"roster asks for two states for {digits}; put each state in its own roster")
            states[digits] = st
    seen = set()
    clean = [n for n in clean if not (n in seen or seen.add(n))]
    if bad:
        print(f"warning: {len(bad)} roster rows are not 10-digit NPIs and were skipped: {bad[:5]}{'...' if len(bad) > 5 else ''}")
    if not clean:
        die("roster has no usable NPIs")
    return clean, states


def rest_get(path, params):
    try:
        return rest().select(path, params)
    except RuntimeError as e:
        die(str(e))


def chunks(seq, n):
    for i in range(0, len(seq), n):
        yield seq[i:i + n]


def fetch_providers(npis):
    out = {}
    for batch in chunks(npis, 300):
        rows = rest_get("providers", {
            "select": "id,npi,entity_type,first_name,last_name,credential,status,last_update_date",
            "npi": f"in.({','.join(batch)})",
        })
        for row in rows:
            out[row["npi"]] = row
    return out


def fetch_receipts(npis):
    """Latest non-superseded receipt per (npi, claim_type, jurisdiction, license_number) from v_current_receipts.
    Paged: 300 NPIs hold well over PostgREST's 1,000-row cap. id breaks ties so the pages never overlap."""
    out = []
    for batch in chunks(npis, 300):
        try:
            out += rest().select_all(
                "v_current_receipts",
                "id,npi,claim_type,jurisdiction,license_number,normalized_status,raw_status,claim,"
                "source_effective_at,source_published_at,retrieved_at,next_check_due_at,origin,stage,"
                "match_basis,match_confidence,limitations,supersedes_id,is_past_due,source_id,artifact_id",
                order="npi.asc,claim_type.asc,id.asc", npi=f"in.({','.join(batch)})")
        except RuntimeError as e:
            die(str(e))
    return out


def fetch_sources():
    rows = rest_get("data_sources", {
        "select": "id,name,jurisdiction,cadence_hours,redistribution_permission,accepted_for_sale,claim_types",
    })
    return {r["id"]: r for r in rows}


def fetch_artifacts(ids):
    ids = [i for i in set(ids) if i]
    out = {}
    for batch in chunks(ids, 300):
        rows = rest_get("source_artifacts", {"select": "id,sha256,file_name", "id": f"in.({','.join(batch)})"})
        for r in rows:
            out[r["id"]] = r
    return out


def fetch_coverage(npis):
    """Coverage buckets from roster_coverage() (migrations/2026-10-27_freshroot_api.sql), the one definition the
    FreshRoot API also serves. Returns (coverage, not_yet): NPIs with a current receipt per pilot claim key, in
    order, and the reason for each claim type not loaded at all."""
    try:
        rows = rest().request("POST", "rpc/roster_coverage", body={"p_npis": npis})[1]
    except RuntimeError as e:
        die(str(e))
    coverage = {r["claim_key"]: r["covered"] for r in rows if r["covered"] is not None}
    not_yet = {r["claim_key"]: r["reason"] for r in rows if r["covered"] is None}
    return coverage, not_yet


def latest_run_id(source_filter):
    """The latest completed run of the one source matching source_filter, or None."""
    srcs = rest_get("data_sources", {"select": "id", **source_filter})
    if len(srcs) != 1:
        die(f"expected one source for {source_filter}, found {len(srcs)}")
    runs = rest_get("ingestion_runs", {"select": "id", "source_id": f"eq.{srcs[0]['id']}", "status": "eq.completed",
                                       "order": "completed_at.desc", "limit": 1})
    return runs[0]["id"] if runs else None


def not_yet_written(npis, claim_type, run_id, origin):
    """NPIs that hold no receipt of this claim type from this run."""
    if run_id is None:
        return list(npis)  # the function itself refuses to run without a completed run
    done = set()
    for batch in chunks(npis, 300):
        for row in rest_get("credential_receipts", {"select": "npi", "claim_type": f"eq.{claim_type}",
                                                    "run_id": f"eq.{run_id}", "origin": f"eq.{origin}",
                                                    "npi": f"in.({','.join(batch)})"}):
            done.add(row["npi"])
    skipped = len([n for n in npis if n in done])
    if skipped:
        print(f"  {claim_type}: {skipped} NPIs already have a receipt from run {run_id}; not written again")
    return [n for n in npis if n not in done]


def rpc_batches(db, fn, npis, extra, size=RPC_BATCH):
    """Calls a receipt function in batches. A statement timeout (57014) cancels and rolls back the whole call,
    so that batch is split in half and tried again; any other error is raised (RuntimeError). Also used by
    scripts/refresh_roster_receipts.py."""
    out = []
    pending = list(chunks(npis, size))
    while pending:
        batch = pending.pop(0)
        try:
            # No client retries: a retried network timeout could write receipts the server already committed.
            out += db.request("POST", f"rpc/{fn}", body={"p_npis": batch, **extra}, timeout=600, retries=0)[1]
        except RuntimeError as e:
            if '"57014"' in str(e) and len(batch) > 1:
                half = len(batch) // 2
                print(f"  {fn}: statement timeout on {len(batch)} NPIs; retrying as {half} + {len(batch) - half}")
                pending[:0] = [batch[:half], batch[half:]]
                continue
            raise
    return out


def rpc_receipts(fn, npis, extra, size=RPC_BATCH):
    """rpc_batches; any error stops the build."""
    try:
        return rpc_batches(rest(), fn, npis, extra, size)
    except RuntimeError as e:
        die(str(e))


def write_receipts(npis, states, origin):
    """Runs the SQL functions that turn the latest snapshots into receipts for this roster.
    State license receipts are asked only for the state each roster row names: receipts_for_state_licenses
    writes a receipt for every NPI it is given, so an NPI asked in the wrong state would get a not_found."""
    counts = Counter()
    todo = not_yet_written(npis, "npi_status", latest_run_id({"name": "eq.NPI Registry"}), origin)
    for row in rpc_receipts("receipts_for_npi_status", todo, {"p_origin": origin}):
        counts["npi_status:" + row["normalized_status"]] += 1
    # receipts_for_exclusions writes OIG and SAM in one transaction, so the OIG receipt marks both done.
    todo = not_yet_written(npis, "oig_exclusion", latest_run_id({"name": "eq.OIG LEIE"}), origin)
    for row in rpc_receipts("receipts_for_exclusions", todo, {"p_origin": origin}, size=EXCLUSIONS_BATCH):
        counts[row["claim_type"] + ":" + row["normalized_status"]] += 1
    for st in PILOT_STATES:
        roster = [n for n in npis if states.get(n) == st]
        if not roster:
            continue
        run_id = latest_run_id({"jurisdiction": f"eq.{st}", "category": "eq.licensing",
                                "or": "(format.is.null,format.neq.api)", "claim_types": "cs.{state_license}"})
        todo = not_yet_written(roster, "state_license", run_id, origin)
        for row in rpc_receipts("receipts_for_state_licenses", todo, {"p_state": st, "p_origin": origin}):
            counts[f"state_license:{st}:{row['normalized_status']}"] += 1
    print("receipts written:" if counts else "receipts written: none")
    for k, v in sorted(counts.items()):
        print(f"  {k:32s} {v}")


def build(npis, origin, out_dir):
    providers = fetch_providers(npis)
    receipts = fetch_receipts(npis)
    sources = fetch_sources()
    artifacts = fetch_artifacts([r.get("artifact_id") for r in receipts])

    unmatched = [n for n in npis if n not in providers]
    rows = []
    for r in receipts:
        src = sources.get(r["source_id"], {})
        art = artifacts.get(r.get("artifact_id") or "", {})
        stage = "stale" if r.get("is_past_due") and r["stage"] == "verified" else r["stage"]
        accepted = bool(src.get("accepted_for_sale"))
        rows.append({
            "npi": r["npi"],
            "claim_type": r["claim_type"],
            "jurisdiction": r.get("jurisdiction") or "",
            "license_number": r.get("license_number") or "",
            "normalized_status": r["normalized_status"],
            "raw_status": r.get("raw_status") or "",
            "source_name": src.get("name", ""),
            "source_published_at": r.get("source_published_at") or "",
            "source_effective_at": r.get("source_effective_at") or "",
            "retrieved_at": r["retrieved_at"],
            "next_check_due_at": r["next_check_due_at"],
            "origin": r["origin"],
            "stage": stage,
            "match_basis": r["match_basis"],
            "match_confidence": r["match_confidence"],
            "accepted_for_sale": accepted,
            "shippable": accepted and r["origin"] == "real" and stage == "verified",
            "limitations": r.get("limitations") or "",
            "receipt_id": r["id"],
            "supersedes_id": r.get("supersedes_id") or "",
            "artifact_sha256": art.get("sha256", ""),
        })

    coverage, not_yet = fetch_coverage(npis)

    status_counts = Counter((row["claim_type"], row["jurisdiction"], row["normalized_status"]) for row in rows)
    review = [row for row in rows if row["stage"] == "candidate"]
    stale = [row for row in rows if row["stage"] == "stale"]
    unsellable = [row for row in rows if not row["accepted_for_sale"]]
    synthetic = [row for row in rows if row["origin"] != "real"]
    shippable = [row for row in rows if row["shippable"]]
    internal = len(shippable) < len(rows) or not rows

    out_dir.mkdir(parents=True, exist_ok=True)
    with (out_dir / "receipts.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=RECEIPT_COLUMNS)
        w.writeheader()
        w.writerows(rows)
    with (out_dir / "unmatched.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["npi", "note"])
        for n in unmatched:
            w.writerow([n, "not in NPPES snapshot held by the garden"])

    built_at = datetime.now(timezone.utc).isoformat()
    doc = {
        "built_at": built_at,
        "origin_requested": origin,
        "roster": {"count": len(npis), "matched": len(npis) - len(unmatched), "unmatched": unmatched},
        "coverage": coverage,
        "status_counts": {":".join(x for x in k if x): c for k, c in sorted(status_counts.items())},
        "shippable": len(shippable),
        "internal_review_rights_pending": internal,
        "needs_review": len(review),
        "stale": len(stale),
        "not_accepted_for_sale": len(unsellable),
        "synthetic_rows": len(synthetic),
        "not_yet_covered": not_yet,
        "receipts": rows,
    }
    (out_dir / "receipts.json").write_text(json.dumps(doc, indent=2, default=str))

    n = len(npis)
    lines = [
        "# Internal review, rights pending" if internal else "# Coverage report",
        "",
        f"Built {built_at}. Shippable rows: {len(shippable)} of {len(rows)}."
        + (" Nothing in this packet leaves the garden." if internal else ""),
        "",
        f"Roster: {n} NPIs. In the garden: {n - len(unmatched)}. Not found in the NPPES snapshot: {len(unmatched)}.",
        f"Receipts: {len(rows)}. Needing human review (candidate): {len(review)}. Past due (stale): {len(stale)}.",
        f"Rows from sources not yet accepted for sale: {len(unsellable)} (these do not ship). Synthetic rows: {len(synthetic)}.",
        "",
        "## Covered today (NPIs with a current receipt)",
        "",
        "| Claim | Covered | of roster |",
        "| --- | ---: | ---: |",
    ]
    for k, c in coverage.items():
        lines.append(f"| {k} | {c} | {100.0 * c / n:.0f}% |")
    lines += ["", "## Status counts", "", "| Claim | Jurisdiction | Status | Rows |", "| --- | --- | --- | ---: |"]
    for (ct, jur, st), c in sorted(status_counts.items()):
        lines.append(f"| {ct} | {jur or '—'} | {st} | {c} |")
    lines += ["", "## Not yet covered", ""]
    for k, why in not_yet.items():
        lines.append(f"- {k}: {why}")
    lines += [
        "",
        "## How to read a row",
        "",
        "Three clocks: source_published_at is the date on the publisher's file; source_effective_at is when the fact took effect;",
        "retrieved_at is when the garden read it. next_check_due_at is retrieved_at plus the source cadence.",
        "normalized_status = not_found means not present in that source's snapshot on that date. It never means clear.",
        "match_basis and match_confidence say how the row was joined to the NPI. name_only rows are candidates for review, not findings.",
        "A row with accepted_for_sale = false comes from a source whose rights or acceptance test are not yet documented and does not ship.",
        "shippable is true only for a real, verified, current row from a source accepted for sale.",
    ]
    (out_dir / "coverage.md").write_text("\n".join(lines) + "\n")

    print(f"packet written to {out_dir}/")
    print(f"  roster {n}, matched {n - len(unmatched)}, receipts {len(rows)}, review {len(review)}, stale {len(stale)}, not-for-sale {len(unsellable)}, shippable {len(shippable)}")
    if synthetic and origin == "real":
        print("warning: synthetic rows present in a packet requested as real. Do not ship.")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("roster", help="CSV with an npi column, or one NPI per line")
    ap.add_argument("--out", help="output directory")
    ap.add_argument("--origin", default="real", choices=["real", "synthetic"], help="label for receipts written in this run")
    ap.add_argument("--write-receipts", action="store_true",
                    help="run receipts_for_npi_status, receipts_for_exclusions and, per roster state, receipts_for_state_licenses first")
    args = ap.parse_args()

    npis, states = read_roster(args.roster)
    out_dir = Path(args.out or f"packet_{datetime.now().strftime('%Y%m%d_%H%M')}")
    if args.write_receipts:
        write_receipts(npis, states, args.origin)
    build(npis, args.origin, out_dir)


if __name__ == "__main__":
    main()

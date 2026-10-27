#!/usr/bin/env python3
"""
build_credential_packet.py · roster of NPIs in, the packet out.

Outputs (in --out, default ./packet_<timestamp>/):
  receipts.csv          one row per receipt (the sellable rows)
  receipts.json         the same rows, plus the roster and coverage, as one document
  coverage.md           what is covered today, by claim type and jurisdiction, and what is not
  unmatched.csv         NPIs on the roster that are not in the garden at all

Talks to Supabase over PostgREST (HTTPS only, works from the Mac and from a sandbox).
Env:
  SUPABASE_URL                 e.g. https://opbrzaegvfyjpyyrmdfe.supabase.co
  SUPABASE_SERVICE_ROLE_KEY    server-side only. Never in a page, never in git.

Usage:
  python build_credential_packet.py roster.csv --out ./packet_modio
  python build_credential_packet.py roster.csv --write-receipts      # runs the SQL functions first (needs completed runs)
  python build_credential_packet.py roster.csv --origin synthetic    # demo packets are labeled, never shipped

The roster file is a CSV with a column named npi (other columns are ignored), or a plain text file with one NPI per line.
Rows from sources with accepted_for_sale = false are included in the packet but flagged; they never ship to a buyer.
"""

import argparse
import csv
import json
import os
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import requests

SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")

PILOT_CLAIM_TYPES = [
    "npi_status", "oig_exclusion", "sam_exclusion", "state_license", "state_board_action",
    "medicare_optout", "pecos_enrollment",
]
PILOT_STATES = ["TX", "FL", "CA", "UT"]
NOT_YET = {
    "dea_registration": "licensed source (NTIS DEA file); contract not in place",
    "board_certification": "licensed source (ABMS); contract not in place",
    "medicaid_exclusion": "state Medicaid exclusion lists; not yet ingested",
    "nurse_license": "Nursys; terms not confirmed",
    "npdb": "authorized queriers only; never resold. The buyer queries it.",
}

RECEIPT_COLUMNS = [
    "npi", "claim_type", "jurisdiction", "license_number", "normalized_status", "raw_status",
    "source_name", "source_published_at", "source_effective_at", "retrieved_at", "next_check_due_at",
    "origin", "stage", "match_basis", "match_confidence", "accepted_for_sale", "limitations",
    "receipt_id", "supersedes_id", "artifact_sha256",
]


def die(msg):
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(1)


def headers():
    if not SUPABASE_URL or not SERVICE_KEY:
        die("set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY")
    return {
        "apikey": SERVICE_KEY,
        "Authorization": f"Bearer {SERVICE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "count=none",
    }


def read_roster(path):
    p = Path(path)
    if not p.exists():
        die(f"roster not found: {path}")
    npis = []
    with p.open(newline="") as f:
        sample = f.read(2048)
        f.seek(0)
        if "," in sample or "npi" in sample.lower():
            reader = csv.DictReader(f)
            col = next((c for c in (reader.fieldnames or []) if c and c.strip().lower() == "npi"), None)
            if col is None:
                f.seek(0)
                npis = [line.strip() for line in f if line.strip()]
            else:
                npis = [row[col].strip() for row in reader if row.get(col)]
        else:
            npis = [line.strip() for line in f if line.strip()]
    clean = []
    bad = []
    for n in npis:
        digits = "".join(ch for ch in n if ch.isdigit())
        (clean if len(digits) == 10 else bad).append(digits or n)
    seen = set()
    clean = [n for n in clean if not (n in seen or seen.add(n))]
    if bad:
        print(f"warning: {len(bad)} roster rows are not 10-digit NPIs and were skipped: {bad[:5]}{'...' if len(bad) > 5 else ''}")
    if not clean:
        die("roster has no usable NPIs")
    return clean


def rest_get(path, params):
    r = requests.get(f"{SUPABASE_URL}/rest/v1/{path}", headers=headers(), params=params, timeout=120)
    if r.status_code >= 400:
        die(f"GET {path} failed {r.status_code}: {r.text[:300]}")
    return r.json()


def rest_rpc(fn, payload):
    r = requests.post(f"{SUPABASE_URL}/rest/v1/rpc/{fn}", headers=headers(), data=json.dumps(payload), timeout=600)
    if r.status_code >= 400:
        die(f"rpc {fn} failed {r.status_code}: {r.text[:300]}")
    return r.json()


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
    """Latest non-superseded receipt per (npi, claim_type, jurisdiction, license_number) from v_current_receipts."""
    out = []
    for batch in chunks(npis, 300):
        rows = rest_get("v_current_receipts", {
            "select": "id,npi,claim_type,jurisdiction,license_number,normalized_status,raw_status,claim,"
                      "source_effective_at,source_published_at,retrieved_at,next_check_due_at,origin,stage,"
                      "match_basis,match_confidence,limitations,supersedes_id,is_past_due,source_id,artifact_id",
            "npi": f"in.({','.join(batch)})",
            "order": "npi.asc,claim_type.asc",
        })
        out.extend(rows)
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


def write_receipts(npis, origin):
    """Runs the SQL functions that turn the latest snapshots into receipts for this roster."""
    counts = Counter()
    for batch in chunks(npis, 500):
        for row in rest_rpc("receipts_for_npi_status", {"p_npis": batch, "p_origin": origin}):
            counts["npi_status:" + row["normalized_status"]] += 1
        for row in rest_rpc("receipts_for_exclusions", {"p_npis": batch, "p_origin": origin}):
            counts[row["claim_type"] + ":" + row["normalized_status"]] += 1
    print("receipts written:")
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
            "stage": "stale" if r.get("is_past_due") and r["stage"] == "verified" else r["stage"],
            "match_basis": r["match_basis"],
            "match_confidence": r["match_confidence"],
            "accepted_for_sale": bool(src.get("accepted_for_sale")),
            "limitations": r.get("limitations") or "",
            "receipt_id": r["id"],
            "supersedes_id": r.get("supersedes_id") or "",
            "artifact_sha256": art.get("sha256", ""),
        })

    # Coverage: for each NPI on the roster, which pilot claim types have a current receipt.
    have = defaultdict(set)
    for row in rows:
        key = row["claim_type"] + (":" + row["jurisdiction"] if row["jurisdiction"] else "")
        have[row["npi"]].add(key)

    coverage = {}
    for ct in PILOT_CLAIM_TYPES:
        if ct in ("state_license", "state_board_action"):
            for st in PILOT_STATES:
                k = f"{ct}:{st}"
                coverage[k] = sum(1 for n in npis if k in have[n])
        else:
            coverage[ct] = sum(1 for n in npis if ct in have[n])

    status_counts = Counter((row["claim_type"], row["normalized_status"]) for row in rows)
    review = [row for row in rows if row["stage"] == "candidate"]
    stale = [row for row in rows if row["stage"] == "stale"]
    unsellable = [row for row in rows if not row["accepted_for_sale"]]
    synthetic = [row for row in rows if row["origin"] != "real"]

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
        "status_counts": {f"{ct}:{st}": c for (ct, st), c in sorted(status_counts.items())},
        "needs_review": len(review),
        "stale": len(stale),
        "not_accepted_for_sale": len(unsellable),
        "synthetic_rows": len(synthetic),
        "not_yet_covered": NOT_YET,
        "receipts": rows,
    }
    (out_dir / "receipts.json").write_text(json.dumps(doc, indent=2, default=str))

    n = len(npis)
    lines = [
        f"# Coverage report · built {built_at}",
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
    lines += ["", "## Status counts", "", "| Claim | Status | Rows |", "| --- | --- | ---: |"]
    for (ct, st), c in sorted(status_counts.items()):
        lines.append(f"| {ct} | {st} | {c} |")
    lines += ["", "## Not yet covered", ""]
    for k, why in NOT_YET.items():
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
    ]
    (out_dir / "coverage.md").write_text("\n".join(lines) + "\n")

    print(f"packet written to {out_dir}/")
    print(f"  roster {n}, matched {n - len(unmatched)}, receipts {len(rows)}, review {len(review)}, stale {len(stale)}, not-for-sale {len(unsellable)}")
    if synthetic and origin == "real":
        print("warning: synthetic rows present in a packet requested as real. Do not ship.")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("roster", help="CSV with an npi column, or one NPI per line")
    ap.add_argument("--out", help="output directory")
    ap.add_argument("--origin", default="real", choices=["real", "synthetic"], help="label for receipts written in this run")
    ap.add_argument("--write-receipts", action="store_true", help="run receipts_for_npi_status and receipts_for_exclusions first")
    args = ap.parse_args()

    npis = read_roster(args.roster)
    out_dir = Path(args.out or f"packet_{datetime.now().strftime('%Y%m%d_%H%M')}")
    if args.write_receipts:
        write_receipts(npis, args.origin)
    build(npis, args.origin, out_dir)


if __name__ == "__main__":
    main()

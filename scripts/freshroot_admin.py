#!/usr/bin/env python3
"""
freshroot_admin.py · rosters and tenant keys for the FreshRoot read API (supabase/functions/freshroot).

  python scripts/freshroot_admin.py load-roster packets/2026-10-26_first_packet/roster.csv \
      --id first-packet-2026-10-26 --name "First packet, 2026-10-26"
  python scripts/freshroot_admin.py create-tenant internal-review --roster first-packet-2026-10-26
  python scripts/freshroot_admin.py delete-tenant internal-review

create-tenant prints the new key once, to stdout, and stores only its SHA-256 hex digest in api_tenants.
The key is never written to a file. Lose it and create the tenant again (delete-tenant first).

Same client and env as the loaders (scripts/ingestion/core_run.py): SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY
from the repo-root .env or the environment.
"""

import argparse
import csv
import hashlib
import secrets
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "ingestion"))

from core_run import Rest  # noqa: E402

KEY_PREFIX = "fr_"


def load_roster(rest, path, roster_id, name):
    with Path(path).open(newline="") as f:
        reader = csv.DictReader(f)
        rows = []
        for row in reader:
            npi = "".join(ch for ch in (row.get("npi") or "") if ch.isdigit())
            if len(npi) != 10:
                sys.exit(f"error: roster row is not a 10-digit NPI: {row.get('npi')!r}")
            rows.append({
                "roster_id": roster_id,
                "npi": npi,
                "state": (row.get("state") or "").strip().upper() or None,
                "license_number": (row.get("license_number") or "").strip() or None,
                "license_type": (row.get("license_type") or "").strip() or None,
                "match_basis_at_selection": (row.get("match_basis") or "").strip() or None,
            })
    if len({r["npi"] for r in rows}) != len(rows):
        sys.exit("error: roster lists an NPI twice")
    rest.insert("rosters", [{"id": roster_id, "name": name, "source_file": str(path)}], upsert_on="id")
    rest.insert("roster_members", rows, upsert_on="roster_id,npi")
    held = rest.select("roster_members", {"select": "npi", "roster_id": f"eq.{roster_id}"})
    print(f"roster {roster_id}: {len(held)} NPIs")


def create_tenant(rest, name, roster_ids):
    if rest.select("api_tenants", {"select": "id", "name": f"eq.{name}"}):
        sys.exit(f"error: tenant {name} exists; delete-tenant first to issue a new key")
    for rid in roster_ids:
        if not rest.select("rosters", {"select": "id", "id": f"eq.{rid}"}):
            sys.exit(f"error: no roster {rid}")
    key = KEY_PREFIX + secrets.token_urlsafe(32)
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
    rest.insert("api_tenants", [{"name": name, "key_hash": digest, "roster_ids": roster_ids}])
    print(key)


def delete_tenant(rest, name):
    rest.request("DELETE", "api_tenants", {"name": f"eq.{name}"}, prefer="return=minimal")
    print(f"tenant {name} deleted")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    lr = sub.add_parser("load-roster", help="create or refresh a roster from a CSV with an npi column")
    lr.add_argument("csv")
    lr.add_argument("--id", required=True)
    lr.add_argument("--name", required=True)
    ct = sub.add_parser("create-tenant", help="issue a key bound to rosters; prints the key once")
    ct.add_argument("name")
    ct.add_argument("--roster", action="append", required=True, help="roster id; repeat for more than one")
    dt = sub.add_parser("delete-tenant", help="remove a tenant and its key")
    dt.add_argument("name")
    args = ap.parse_args()

    rest = Rest()
    if args.cmd == "load-roster":
        load_roster(rest, args.csv, args.id, args.name)
    elif args.cmd == "create-tenant":
        create_tenant(rest, args.name, args.roster)
    else:
        delete_tenant(rest, args.name)


if __name__ == "__main__":
    main()

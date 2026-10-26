#!/usr/bin/env python3
"""
Run the three core sources in order (NPPES, OIG LEIE, SAM.gov), then print v_source_status.

NPPES goes first because oig_exclusions.npi references providers. A failure in one source is
recorded on its own ingestion_runs row and does not stop the others. Exit code 1 if any failed.

Usage:
  python3 run_all_core.py
  python3 run_all_core.py --skip nppes     # e.g. while the CMS download site is down
"""
import argparse
import sys

import ingest_nppes
import ingest_oig
import ingest_sam
from core_run import Rest, log, print_source_status

STEPS = [("nppes", ingest_nppes), ("oig", ingest_oig), ("sam", ingest_sam)]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--skip", action="append", default=[], choices=[k for k, _ in STEPS])
    args = ap.parse_args()

    failed = []
    for key, module in STEPS:
        if key in args.skip:
            log(f"=== {key}: skipped")
            continue
        log(f"=== {key}")
        try:
            module.main([])
        except Exception as e:
            failed.append(key)
            log(f"=== {key} failed: {e}")

    print()
    print_source_status(Rest())
    if failed:
        print(f"\nfailed: {', '.join(failed)}")
        sys.exit(1)


if __name__ == "__main__":
    main()

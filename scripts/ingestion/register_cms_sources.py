#!/usr/bin/env python3
"""
Registers the two data.cms.gov sources with the poller: sets detection_url, cadence_hours and
update_frequency on their data_sources rows from the catalog's stated accrualPeriodicity, and records
each dataset's data-use page in terms_url for a person to read.

Neither dataset states a license: the catalog's license and rights fields are empty for both, and each
landing page lists the privacy level "Public Use File (Free)". terms_url therefore points at the landing
page. The rights fields (redistribution_permission, accepted_for_sale, terms_version, terms_checked_at)
are left as they are: a person sets them after reading the terms.

Idempotent. Usage:
  python3 register_cms_sources.py            # update both rows
  python3 register_cms_sources.py --dry-run  # print what would be set
"""
import argparse

import cms_data
import ingest_cms_optout
import ingest_cms_pecos
from core_run import Rest, log

SOURCES = (ingest_cms_optout, ingest_cms_pecos)


def fields(release):
    hours = cms_data.PERIODICITY_HOURS.get(release.periodicity)
    if not hours:
        raise RuntimeError(f"{release.title}: no cadence for accrualPeriodicity {release.periodicity!r}")
    return {
        "detection_url": cms_data.CATALOG_URL,
        "cadence_hours": hours,
        "update_frequency": release.periodicity,
        "terms_url": release.landing,
        "notes": (f"data.cms.gov series {release.series_uuid}; stated cadence {release.periodicity} "
                  f"(accrualPeriodicity). No license in the catalog (license and rights empty); the landing page "
                  f"lists privacy level 'Public Use File (Free)'. Rights unset until a person reads terms_url."),
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)
    db = Rest()
    for mod in SOURCES:
        body = fields(cms_data.Release(mod.SERIES))
        if not db.select("data_sources", {"select": "id", "name": f"eq.{mod.SOURCE}"}):
            raise RuntimeError(f"data_sources has no row named {mod.SOURCE!r}")
        log(f"{mod.SOURCE}: {body}" + (" (dry run)" if args.dry_run else ""))
        if not args.dry_run:
            db.patch("data_sources", body, name=f"eq.{mod.SOURCE}")


if __name__ == "__main__":
    main()

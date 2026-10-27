#!/usr/bin/env python3
"""
Shared machinery for state licensing board loaders (tx_tmb.py, fl_mqa.py).

A board loader runs inside core_run.run_source like the core sources: artifact row, run row, clocks,
anomaly guard. On top of that it matches each license row to an NPI and writes one snapshot of the
matched rows per run into state_license_lookups and provider_adverse_actions, stamped with run_id and
artifact_id. receipts_for_state_licenses reads the snapshot of the latest completed run only, so a
failed run never changes what a receipt says. Snapshots older than the last KEEP_RUNS completed runs
are pruned at the end of a successful run.

Matching ladder, in this order, recorded on every row:
  1. npi_exact             1.00  verified   the board file carries the NPI
  2. license_number_exact  0.95  verified   the license number is already recorded for exactly one NPI in
                                            this state: provider_credentials, a prior npi_exact or
                                            license_number_exact state_license_lookups row, or the NPPES
                                            license field (provider_taxonomies.license_number), with the
                                            NPPES taxonomy in the same profession as the board license
  3. name_state_taxonomy   0.70  candidate  physician license; last name + first name equal to exactly one
                                            NPI with an NPPES practice address in the state and a 207*/208*
                                            taxonomy; the board name belongs to one person (one birth year)
  4. no row; counted as unmatched
A license is never matched on name alone. A name-matched row never seeds a license_number_exact match.
"""
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core_run import Rest, chunks, in_list, log, now_iso  # noqa: E402

MATCH = {
    "npi_exact": (1.00, "verified"),
    "license_number_exact": (0.95, "verified"),
    "name_state_taxonomy": (0.70, "candidate"),
}
KEEP_RUNS = 3
UNKNOWN_SHARE_LIMIT = 0.05  # more unmapped statuses than this means the board changed its vocabulary
MATCH_DROP_RATIO = 0.5      # fewer matched rows than this share of the last run means a reference table broke
BATCH = 500

# NUCC taxonomy prefixes per profession, for checking an NPPES license number against the board's license type.
TAXONOMY_FAMILY = (
    ("3902", "physician"),  # student in an organized training program (residents)
    ("363A", "pa"),
    ("2278", "rcp"),
    ("2279", "rcp"),
    ("2471", "mrt"),
    ("1711", "acu"),
    ("20", "physician"),    # 202*, 204*, 207*, 208* allopathic and osteopathic physicians
)


def taxonomy_family(code):
    code = (code or "").upper()
    return next((fam for prefix, fam in TAXONOMY_FAMILY if code.startswith(prefix)), None)


def norm_license(s):
    """License numbers compare on letters and digits only: 'J-1234' == 'J1234'."""
    return re.sub(r"[^A-Z0-9]", "", (s or "").upper())


def norm_last(s):
    return re.sub(r"[^A-Z]", "", (s or "").upper())


def norm_first(s):
    """First token of the first name, letters only: boards often append the middle name to it."""
    tokens = (s or "").upper().split()
    return re.sub(r"[^A-Z]", "", tokens[0]) if tokens else ""


def clip(s, n):
    s = (s or "").strip()
    return s[:n] or None


class LicenseRow:
    """One board license row, already parsed by the state adapter."""
    __slots__ = ("key", "license_type", "license_number", "family", "npi", "last_name", "first_name",
                 "birth_year", "raw_status", "normalized_status", "status_date", "issue_date",
                 "expiration_date", "actions", "raw", "placeholder", "physician_active")

    def __init__(self, **kw):
        for k in self.__slots__:
            setattr(self, k, kw.get(k))


class Matcher:
    def __init__(self, db, state, source_id, family_of_license_type):
        self.db, self.state, self.source_id = db, state, source_id
        self.by_npi = {}
        self.by_license = defaultdict(set)   # (family or None, normalized license) -> provider ids
        self.by_name = defaultdict(set)      # (last, first) -> provider ids
        self.ref_counts = Counter()
        self._load(family_of_license_type)

    def _load(self, family_of_license_type):
        # License references come from individual NPIs only: an organization lists its clinicians'
        # license numbers in NPPES, but it is not the licensee.
        db, st = self.db, self.state
        individual = {"providers.entity_type": "eq.individual"}
        for r in db.select_all("provider_taxonomies",
                               "id,provider_id,taxonomy_code,license_number,providers!inner(entity_type)",
                               license_state=f"eq.{st}", license_number="not.is.null", **individual):
            fam = taxonomy_family(r["taxonomy_code"])
            lic = norm_license(r["license_number"])
            if fam and lic:
                self.by_license[(fam, lic)].add(r["provider_id"])
                self.ref_counts["nppes_license_field"] += 1
        for r in db.select_all("provider_credentials",
                               "id,provider_id,credential_number,providers!inner(entity_type)",
                               issuing_state=f"eq.{st}", credential_number="not.is.null", **individual):
            lic = norm_license(r["credential_number"])
            if lic:
                self.by_license[(None, lic)].add(r["provider_id"])
                self.ref_counts["provider_credentials"] += 1
        for r in db.select_all("state_license_lookups",
                               "id,provider_id,license_type,license_number,providers!inner(entity_type)",
                               state_code=f"eq.{st}", match_basis="in.(npi_exact,license_number_exact)",
                               **individual):
            lic = norm_license(r["license_number"])
            if lic:
                self.by_license[(family_of_license_type(r["license_type"]), lic)].add(r["provider_id"])
                self.ref_counts["prior_exact_links"] += 1
        candidates = db.request("POST", "rpc/state_license_name_candidates", body={"p_state": st}, timeout=300)[1]
        for r in candidates:
            name = (norm_last(r["last_name"]), norm_first(r["first_name"]))
            if all(name):
                self.by_name[name].add(r["provider_id"])
                self.ref_counts["name_candidates"] += 1
        log(f"match references for {st}: {dict(self.ref_counts)}")

    def provider_for_npis(self, npis):
        for chunk in chunks(sorted(set(npis)), 300):
            for r in self.db.select("providers", {"select": "id,npi", "npi": in_list(chunk)}):
                self.by_npi[r["npi"]] = r["id"]

    def match_all(self, rows):
        """Returns {row.key: (provider_id, basis)} and Counter of outcomes."""
        npis = [r.npi for r in rows if r.npi]
        if npis:
            self.provider_for_npis(npis)

        # A board name is one person only if all its physician rows share one birth year.
        years = defaultdict(set)
        for r in rows:
            if r.family == "physician":
                years[(norm_last(r.last_name), norm_first(r.first_name))].add(r.birth_year or "?")

        matches, outcome = {}, Counter()
        for r in rows:
            if r.npi and r.npi in self.by_npi:
                matches[r.key] = (self.by_npi[r.npi], "npi_exact")
                outcome["npi_exact"] += 1
                continue
            if r.npi:
                outcome["npi_not_in_providers"] += 1
            lic = norm_license(r.license_number)
            if lic and not r.placeholder:
                ids = self.by_license.get((r.family, lic), set()) | self.by_license.get((None, lic), set())
                if len(ids) == 1:
                    matches[r.key] = (next(iter(ids)), "license_number_exact")
                    outcome["license_number_exact"] += 1
                    continue
                if len(ids) > 1:
                    outcome["license_number_ambiguous"] += 1
            if r.family == "physician":
                name = (norm_last(r.last_name), norm_first(r.first_name))
                ids = self.by_name.get(name, set()) if all(name) else set()
                if len(ids) == 1 and len(years[name]) == 1:
                    matches[r.key] = (next(iter(ids)), "name_state_taxonomy")
                    outcome["name_state_taxonomy"] += 1
                    continue
                if len(ids) > 1 or (ids and len(years[name]) > 1):
                    outcome["name_ambiguous"] += 1
            outcome["unmatched"] += 1
        return matches, outcome


def assign_keys(rows, base_key, full_key):
    """base_key(row) for rows whose base key is unique in the file; full_key(row) otherwise; '#n' as a last resort."""
    counts = Counter(None if r.placeholder else base_key(r) for r in rows)
    seen = Counter()
    for r in rows:
        k = base_key(r) if not r.placeholder and counts[base_key(r)] == 1 else full_key(r)
        seen[k] += 1
        r.key = k if seen[k] == 1 else f"{k}#{seen[k]}"


def status_guard(run, rows):
    unknown = Counter(r.raw_status for r in rows if r.normalized_status == "unknown")
    share = sum(unknown.values()) / max(len(rows), 1)
    run.note(f"unmapped statuses: {sum(unknown.values()):,} rows ({share:.2%}): {dict(unknown.most_common(10))}")
    if share > UNKNOWN_SHARE_LIMIT:
        raise RuntimeError(f"anomalous status vocabulary: {share:.1%} of rows map to 'unknown'; "
                           f"extend the mapping table after review")


def previous_snapshot_size(db, source_id):
    runs = db.select("ingestion_runs", {"select": "id", "source_id": f"eq.{source_id}", "status": "eq.completed",
                                        "order": "completed_at.desc", "limit": 1})
    return db.count("state_license_lookups", run_id=f"eq.{runs[0]['id']}") if runs else None


def write_snapshot(run, state, source_name, source_url, rows, matches, retrieved_at):
    """Insert this run's matched license rows and board actions. Returns (licenses, actions) written."""
    db = run.db
    prior = previous_snapshot_size(db, run.source_id)
    if prior and len(matches) < prior * MATCH_DROP_RATIO:
        raise RuntimeError(f"anomalous match count: {len(matches):,} matched rows vs {prior:,} in the last "
                           f"completed run; a reference table may be broken. Not loaded.")
    common = {"source_id": run.source_id, "run_id": run.id, "artifact_id": run.artifact["id"]}
    licenses, actions = [], []
    for r in rows:
        hit = matches.get(r.key)
        if not hit:
            continue
        provider_id, basis = hit
        confidence, stage = MATCH[basis]
        licenses.append({
            **common,
            "provider_id": provider_id,
            "state_code": state,
            "license_number": clip(r.license_number, 255),
            "license_type": clip(r.license_type, 100),
            "status": r.normalized_status,
            "raw_status": r.raw_status,
            "normalized_status": r.normalized_status,
            "status_effective_date": r.status_date,
            "issue_date": r.issue_date,
            "expiration_date": r.expiration_date,
            "disciplinary_actions": r.actions,
            "lookup_date": retrieved_at,
            "raw_response": r.raw,
            "data_source": source_name,
            "source_record_key": r.key,
            "match_basis": basis,
            "match_confidence": confidence,
            "stage": stage,
        })
        for i, a in enumerate(r.actions):
            actions.append({
                **common,
                "provider_id": provider_id,
                "action_type": clip(a.get("action_type"), 100),
                "action_classification": clip(a.get("classification"), 255),
                "action_date": a.get("action_date"),
                "effective_date": a.get("effective_date"),
                "state": state,
                "description": a.get("description"),
                "source": "state_board",
                "data_source": source_name,
                "source_url": source_url,
                "source_record_key": f"{r.key}|action{i}",
                "license_number": clip(r.license_number, 255),
                "raw_status": json.dumps(a.get("raw"), sort_keys=True),
                "match_basis": basis,
                "match_confidence": confidence,
                "stage": stage,
            })
    for batch in chunks(licenses, BATCH):
        db.insert("state_license_lookups", batch)
    for batch in chunks(actions, BATCH):
        db.insert("provider_adverse_actions", batch)
    return len(licenses), len(actions)


def prune_snapshots(run):
    """Keep the snapshots of the last KEEP_RUNS completed runs plus this one; drop older and failed-run rows."""
    db = run.db
    keep = [r["id"] for r in db.select("ingestion_runs", {
        "select": "id", "source_id": f"eq.{run.source_id}", "status": "eq.completed",
        "order": "completed_at.desc", "limit": KEEP_RUNS - 1})] + [run.id]
    for table in ("provider_adverse_actions", "state_license_lookups"):  # actions first: same run ids
        db.delete(table, source_id=f"eq.{run.source_id}", run_id=f"not.in.({','.join(keep)})")


def set_board_fields(db, state, header):
    db.patch("state_medical_boards", {"data_fields_available": header, "updated_at": now_iso()},
             state_code=f"eq.{state}")


def report(state, rows, matches, outcome, mapping, overlays, licenses, actions):
    """Print the acceptance report: counts, match rate by basis, and the status mapping table."""
    total = len(rows)
    matched = sum(outcome[b] for b in MATCH)
    phys = [r for r in rows if r.physician_active]
    lines = [
        f"== {state} load report",
        f"file rows: {total:,}; license rows written: {licenses:,}; board action rows written: {actions:,}",
        f"matched {matched:,} of {total:,} rows ({matched / max(total, 1):.2%}); unmatched {outcome['unmatched']:,} "
        f"({outcome['unmatched'] / max(total, 1):.2%})",
    ]
    for basis in MATCH:
        conf, stage = MATCH[basis]
        lines.append(f"  {basis:<22} {conf:.2f} {stage:<9} {outcome[basis]:>9,}  {outcome[basis] / max(total, 1):7.2%}")
    for k in ("license_number_ambiguous", "name_ambiguous", "npi_not_in_providers"):
        if outcome[k]:
            lines.append(f"  ({k}: {outcome[k]:,} rows fell through)")
    if phys:
        by_basis = Counter(matches[r.key][1] for r in phys if r.key in matches)
        n = sum(by_basis.values())
        lines.append(f"currently licensed physicians: {len(phys):,}; matched {n:,} ({n / len(phys):.2%}): "
                     f"{dict(by_basis)}")
    lines.append("")
    lines.append("normalized_status mapping (raw board string -> normalized; rows in this file):")
    seen = Counter(r.raw_status.split(" | ")[0].strip().upper() if r.raw_status else "" for r in rows)
    width = max(len(k) for k in mapping) + 2
    for raw, norm in sorted(mapping.items(), key=lambda kv: (kv[1], kv[0])):
        lines.append(f"  {raw:<{width}} -> {norm:<10} {seen.get(raw, 0):>9,}")
    unmapped = sorted(k for k in seen if k not in mapping)
    for raw in unmapped:
        lines.append(f"  {(raw or '(blank)'):<{width}} -> {'unknown':<10} {seen[raw]:>9,}  (not in table)")
    for title, table in overlays:
        lines.append(f"{title}:")
        for raw, norm in table.items():
            lines.append(f"  {raw:<{width}} -> {norm}")
    lines.append(f"normalized totals: {dict(Counter(r.normalized_status for r in rows).most_common())}")
    text = "\n".join(lines)
    print(text, flush=True)
    return text

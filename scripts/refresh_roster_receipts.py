#!/usr/bin/env python3
"""
Roster refresh: keeps every roster's receipts current with nobody running the packet builder.
Runs hourly as its own step after scripts/poll_sources.py (.github/workflows/poll_sources.yml).

Every roster is monitored (rosters, roster_members: migrations/2026-10-27_freshroot_api.sql). Rosters are the only
thing that gets receipts: the NPIs come from roster_members, and only NPIs that already hold a receipt from a source
are refreshed for it. For each source behind a current roster receipt (v_current_receipts):
  new file   the source's latest completed run read a file (artifact) other than the receipt's: every such
             receipt is rewritten from that run, past due or not
  past due   next_check_due_at has passed and the receipt is from the latest file: the source is read again
             (its detector, then its loader, as a run of its own) and the receipt rewritten from that run.
             Same file: a refresh receipt, same source_published_at, new retrieved_at and next_check_due_at.
             New file: what the writer does today. The delta (freshroot_deltas) reads status_change or refresh.

The writer is the packet builder's SQL: receipts_for_npi_status, receipts_for_exclusions and, per state,
receipts_for_state_licenses. Each writes from its sources' latest completed run with retrieved_at = that run's
completed_at, and one run holds one receipt per claim per NPI (uq_receipts_one_per_run). So an NPI is written only
when no source of its writer has a latest run already holding its receipt; a source that does is read again first.
receipts_for_exclusions writes OIG and SAM in one transaction, so a SAM rewrite reads OIG again too. The CMS loaders
(opt-out, PECOS) write their own receipts for every roster; their refresh is the loader run itself.

A source is read again only when its detector reaches the publisher and finds the release the garden holds.
Skipped, with the reason: a new release not loaded yet (the poller loads it), an unreachable publisher, a run in
progress, a person-run source (Florida), a source with no loader or no roster writer.

Anomaly guard: re-reads go through the loaders, so each passes the checks a poll does (header, row count, parse, and
for CMS the flip check, never with --allow-large-diff). A run that fails them is closed failed and writes nothing.

run_notes: one line per roster and source that had receipts to refresh, on the run the receipts were written from,
or for a skip on the source's latest run:
  roster refresh <ts>, roster <id>: <source> <claim>: <n> written (<k> status_change, <m> refresh), <u> unmatched,
  <s> skipped[: why]

Never fails the poll: an error is noted and printed and the exit code stays 0. The workflow step is also
continue-on-error, so neither the source loads nor the status page depend on it.

Usage:
  python3 scripts/refresh_roster_receipts.py             # refresh what is new or past due
  python3 scripts/refresh_roster_receipts.py --dry-run   # report only; reads no source, writes nothing
Credentials: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY from the repo-root .env or the environment. Stdlib only.
"""
import argparse
import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_credential_packet as packet  # noqa: E402
import poll_sources as poller  # noqa: E402
from core_run import Rest, chunks, in_list, log, now_iso  # noqa: E402

EXCLUSIONS = ("OIG LEIE", "SAM.gov")
LOADER_WRITES = (poller.ingest_cms_optout.SOURCE, poller.ingest_cms_pecos.SOURCE)  # their loaders write receipts


class Writer:
    """One receipt writer and the sources it writes from. fn None: the source's loader writes its own receipts."""

    def __init__(self, key, sources, fn=None, extra=None, size=packet.RPC_BATCH):
        self.key, self.sources, self.fn, self.extra, self.size = key, sources, fn, extra or {}, size


def writer_for(source, by_name):
    name = source["name"]
    if name == "NPI Registry":
        return Writer("npi_status", [source], "receipts_for_npi_status")
    if name in EXCLUSIONS:
        return Writer("exclusions", [by_name[n] for n in EXCLUSIONS], "receipts_for_exclusions",
                      size=packet.EXCLUSIONS_BATCH)
    if name in LOADER_WRITES:
        return Writer(name, [source])
    if (source["category"] == "licensing" and "state_license" in (source["claim_types"] or [])
            and (source["format"] or "") != "api" and source["jurisdiction"] in packet.PILOT_STATES):
        st = source["jurisdiction"]
        return Writer(f"state_license:{st}", [source], "receipts_for_state_licenses", {"p_state": st})
    return None


# ----------------------------------------------------------------------------
# Reads
# ----------------------------------------------------------------------------

def latest_completed(db, source_id):
    rows = db.select("ingestion_runs", {"select": "id,artifact_id,completed_at,detected_at,source_published_at",
                                        "source_id": f"eq.{source_id}", "status": "eq.completed",
                                        "order": "completed_at.desc", "limit": 1})
    return rows[0] if rows else None


def run_past_due(run, source):
    """The writers set next_check_due_at = the run's completed_at + the source's cadence."""
    cadence = source.get("cadence_hours")
    return bool(cadence) and poller.hours_between(run["completed_at"], now_iso()) >= cadence


def current_receipts(db, npis):
    out = []
    for batch in chunks(sorted(npis), 200):
        out += db.select_all("v_current_receipts", "id,npi,claim_type,source_id,artifact_id,origin,next_check_due_at,is_past_due",
                             order="npi,id", npi=in_list(batch))
    return out


def held(db, run_id, npis):
    """NPIs that already hold a receipt from this run."""
    out = set()
    for batch in chunks(sorted(npis), 200):
        out |= {r["npi"] for r in db.select_all("credential_receipts", "id,npi", run_id=f"eq.{run_id}",
                                                npi=in_list(batch))}
    return out


def written_with_deltas(db, run_ids, npis):
    """Receipts these runs hold for these NPIs, each with change_kind as freshroot_deltas reads it. Called only for
    NPIs the runs held nothing for before the writer ran, so these are exactly the receipts just written."""
    rows = []
    for run_id in run_ids:
        for batch in chunks(sorted(npis), 200):
            rows += db.select_all("credential_receipts", "id,npi,claim_type,source_id,normalized_status,supersedes_id",
                                  run_id=f"eq.{run_id}", npi=in_list(batch))
    prior = {}
    for batch in chunks(sorted({r["supersedes_id"] for r in rows if r["supersedes_id"]}), 200):
        prior.update({p["id"]: p["normalized_status"] for p in
                      db.select("credential_receipts", {"select": "id,normalized_status", "id": in_list(batch)})})
    for r in rows:
        before = prior.get(r["supersedes_id"])
        r["change_kind"] = ("new" if before is None else "status_change" if before != r["normalized_status"]
                            else "refresh")
    return rows


def append_note(db, run_id, line):
    """Append to a run's run_notes. A skip that repeats the last line word for word (bar the time) is not repeated."""
    notes = db.select("ingestion_runs", {"select": "run_notes", "id": f"eq.{run_id}"})[0]["run_notes"] or ""
    last = notes.rsplit("\n", 1)[-1]
    body = line.split(", ", 1)[-1]
    if "skipped" in body and last.startswith("roster refresh ") and last.split(", ", 1)[-1] == body:
        return
    db.patch("ingestion_runs", {"run_notes": f"{notes}\n{line}" if notes else line}, id=f"eq.{run_id}")


# ----------------------------------------------------------------------------
# Re-reading a source
# ----------------------------------------------------------------------------

def reread(db, source):
    """Read a source again whose release the garden already holds: its detector, then its loader in a run of its own.
    Returns (completed run row, None) or (None, why not)."""
    name = source["name"]
    if name in poller.PERSON_RUN:
        return None, f"{name} is loaded by a person, not unattended ({poller.PERSON_RUN[name]})"
    if name not in poller.LOADERS or not source.get("detection_url"):
        return None, f"{name} has no loader the poller can run"
    runs, known = poller.history(db, source["id"])
    running = [r for r in runs if r["status"] == "running"]
    if running:
        return None, f"{name} run {running[0]['id']} is in progress"
    try:
        det = (poller.DETECTORS.get(name) or poller.detect_generic)(source)
    except poller.UNREACHABLE as e:
        return None, f"{name} publisher unreachable ({poller.unreachable_reason(e)})"
    if not det.published:
        return None, f"{name} detector read no publisher date, so it cannot tell the held release is current"
    if poller.is_newer(det.published, known):
        return None, f"{name} has a new release ({det.published}) not loaded yet; the poller loads it"
    last = latest_completed(db, source["id"])
    ts = now_iso()
    notes = (f"roster refresh by scripts/refresh_roster_receipts.py at {ts}: roster receipts past due; "
             f"publisher still at {det.published} ({det.signal}); checked {det.checked_url}; the file is read again")
    run = db.insert("ingestion_runs", [{
        "source_id": source["id"], "run_type": det.run_type, "status": "running", "started_at": ts,
        # detected_at stays when this release was first detected; this run re-reads it
        "detected_at": (last or {}).get("detected_at") or ts,
        "source_published_at": det.published, "run_notes": notes}], returning=True)[0]
    log(f"run {run['id']} opened to re-read {name}")
    row, reason = poller.invoke_loader(db, source, run, det)
    if row["status"] != "completed":
        return None, f"{name} re-read run {row['id']} {row['status']} ({reason})"
    return row, None


# ----------------------------------------------------------------------------
# One writer
# ----------------------------------------------------------------------------

def refresh(db, writer, receipts, rosters, dry_run):
    """receipts: current real roster receipts from this writer's sources. Returns run_notes lines, [(run_id, line)]."""
    latest = {s["id"]: latest_completed(db, s["id"]) for s in writer.sources}
    need = {}   # npi -> why
    for r in receipts:
        run = latest.get(r["source_id"])
        if run and r["artifact_id"] != run["artifact_id"]:
            need[r["npi"]] = "new file"
        elif r["is_past_due"] and r["npi"] not in need:
            need[r["npi"]] = "past due"
    if not need:
        return []
    log(f"{writer.key}: {len(need)} NPIs to refresh "
        f"({sum(v == 'new file' for v in need.values())} new file, {sum(v == 'past due' for v in need.values())} past due)")
    skipped = {}   # npi -> why
    if dry_run:
        skipped = {n: "dry run" for n in need}
    else:
        for src in writer.sources:
            run = latest[src["id"]]
            if writer.fn is None or not run or run_past_due(run, src):
                # The loader writes its own receipts, or the run would only write receipts already past due.
                blocked = set(need)
            else:
                blocked = held(db, run["id"], need)
            if not blocked:
                continue
            row, why = reread(db, src)
            if row:
                latest[src["id"]] = row
                if writer.fn is not None:
                    still = held(db, row["id"], blocked)
                    for n in still:
                        skipped[n] = f"re-read run {row['id']} already holds this receipt"
            else:
                for n in blocked:
                    skipped.setdefault(n, why)

    todo = sorted(n for n in need if n not in skipped)
    written, error = [], None
    if todo:
        try:
            if writer.fn:
                packet.rpc_batches(db, writer.fn, todo, {"p_origin": "real", **writer.extra}, writer.size)
        except Exception as e:
            error = f"writer {writer.fn} failed: {e}"
            log(error)
        # Read back from the runs, so a writer that failed part way still reports what it committed.
        written = written_with_deltas(db, [latest[s["id"]]["id"] for s in writer.sources], todo)
        if error:
            got = {w["npi"] for w in written}
            for n in todo:
                if n not in got:
                    skipped[n] = error

    lines = []
    ts = now_iso()
    for src in writer.sources:
        claim = "/".join(sorted({r["claim_type"] for r in receipts if r["source_id"] == src["id"]})
                         or src["claim_types"] or [])
        mine = [w for w in written if w["source_id"] == src["id"]]
        for roster_id, members in sorted(rosters.items()):
            in_roster = members & set(need)
            if not in_roster:
                continue
            w = [x for x in mine if x["npi"] in members]
            got = {x["npi"] for x in w}
            sk = {n: skipped[n] for n in in_roster if n in skipped}
            unmatched = sorted(n for n in in_roster if n not in got and n not in sk)
            kinds = {k: sum(x["change_kind"] == k for x in w) for k in ("status_change", "refresh", "new")}
            whys = sorted(set(sk.values()))
            line = (f"roster refresh {ts}, roster {roster_id}: {src['name']} {claim}: {len(w)} written "
                    f"({kinds['status_change']} status_change, {kinds['refresh']} refresh"
                    + (f", {kinds['new']} new" if kinds["new"] else "") + f"), {len(unmatched)} unmatched"
                    + (f" {unmatched[:5]}" if unmatched else "")
                    + f", {len(sk)} skipped" + (f": {'; '.join(whys)}" if whys else ""))
            target = (latest.get(src["id"]) or {}).get("id")
            if not target:
                runs, _ = poller.history(db, src["id"])
                target = runs[0]["id"] if runs else None
            lines.append((target, line))
    return lines


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true", help="report only; reads no source, writes nothing")
    args = ap.parse_args(argv)
    started = now_iso()
    try:
        db = Rest()
        members = db.select_all("roster_members", "roster_id,npi", order="roster_id,npi")
        rosters = {}
        for m in members:
            rosters.setdefault(m["roster_id"], set()).add(m["npi"])
        npis = {m["npi"] for m in members}
        sources = {s["id"]: s for s in db.select("data_sources", {
            "select": "id,name,category,format,jurisdiction,claim_types,detection_url,cadence_hours"})}
        by_name = {s["name"]: s for s in sources.values()}
        receipts = [r for r in current_receipts(db, npis) if r["origin"] == "real"]
    except Exception:
        print(f"roster refresh at {started}: could not read rosters or receipts\n{traceback.format_exc()}")
        return 0

    writers, orphan = {}, set()
    for r in receipts:
        src = sources.get(r["source_id"])
        w = writer_for(src, by_name) if src else None
        if not w:
            orphan.add(src["name"] if src else r["source_id"])
            continue
        writers.setdefault(w.key, (w, []))[1].append(r)

    print(f"\nRoster refresh at {started}{' (dry run)' if args.dry_run else ''}: "
          f"{len(rosters)} rosters, {len(npis)} NPIs, {len(receipts)} current receipts")
    for key, (writer, rs) in sorted(writers.items()):
        try:
            lines = refresh(db, writer, rs, rosters, args.dry_run)
        except Exception as e:
            print(f"  {key}: failed: {e}\n{traceback.format_exc()}")
            lines = []
            for src in writer.sources:
                runs, _ = poller.history(db, src["id"])
                if runs:
                    lines.append((runs[0]["id"], f"roster refresh {now_iso()}, all rosters: {src['name']}: "
                                                 f"0 written, refresh failed: {e}"))
        if not lines:
            print(f"  {key}: current")
        for run_id, line in lines:
            print(f"  {line}" + (f"  [run {run_id}]" if run_id else ""))
            if run_id and not args.dry_run:
                try:
                    append_note(db, run_id, line)
                except Exception as e:
                    print(f"  could not note on run {run_id}: {e}")
    for name in sorted(orphan):
        print(f"  {name}: holds roster receipts but has no roster writer; not refreshed")
    return 0


if __name__ == "__main__":
    sys.exit(main())

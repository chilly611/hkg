#!/usr/bin/env python3
"""
build_fields_json.py · docs/field_map_2026-11-04.md -> freshroot/fields.json

  python3 docs/build_fields_json.py           # write freshroot/fields.json
  python3 docs/build_fields_json.py --check   # exit 1 when freshroot/fields.json differs from the markdown

Reads the table under "## The fifty fields", the class and headline-group definitions and the "## Sources read"
table, checks them (50 rows, unique IDs, a known class, a named file or agreement where the class needs one, known
headline groups, every "Read in" key a listed source, every source with a URL and a read date),
and writes them as one JSON document the Coverage surface's Fields view reads. The output depends only on the
markdown, so running it twice gives the same file. Stdlib only.
"""

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "docs" / "field_map_2026-11-04.md"
TARGET = ROOT / "freshroot" / "fields.json"

CLASSES = ["covered today", "public file", "agreement needed", "self-reported", "plan-internal"]
NAMED = {"public file", "agreement needed"}  # these must name the file or the agreement
GROUPS = ["Expired", "Sanctioned", "Boarded"]
COLUMNS = ["ID", "Field", "Group", "Standards", "Read in", "Primary source", "Cadence", "Class", "Class detail", "Drives"]
SOURCE_COLUMNS = ["Key", "Document", "URL", "Read", "Notes"]
EXPECTED = 50


def section(text, heading):
    """The lines under '## heading', up to the next '## '."""
    m = re.search(rf"^## {re.escape(heading)}\n(.*?)(?=^## |\Z)", text, re.S | re.M)
    if not m:
        sys.exit(f"error: no '## {heading}' section in {SOURCE.name}")
    return m.group(1)


def table(block):
    """Rows of the first markdown table in block, as lists of stripped cells (header and divider dropped)."""
    lines = [l for l in block.splitlines() if l.startswith("|")]
    rows = [[c.strip() for c in l.strip().strip("|").split("|")] for l in lines]
    return rows[0], [r for r in rows[2:]]


def split_top(cell):
    """Split on ';' outside parentheses, so a citation like '(N2 p.11; N3 p.13)' stays whole."""
    parts, depth, cur = [], 0, ""
    for ch in cell:
        depth += ch == "("
        depth -= ch == ")"
        if ch == ";" and depth == 0:
            parts.append(cur)
            cur = ""
        else:
            cur += ch
    return [p.strip() for p in parts + [cur] if p.strip()]


def build():
    text = SOURCE.read_text()
    errors = []

    head, class_rows = table(section(text, "Coverage classes"))
    classes = [{"key": r[0], "meaning": r[1]} for r in class_rows]
    if [c["key"] for c in classes] != CLASSES:
        errors.append(f"coverage classes are {[c['key'] for c in classes]}, expected {CLASSES}")

    groups = []
    for g in GROUPS:
        m = re.search(rf"^- \*\*{g}\*\*: (.+)$", section(text, "Coverage classes"), re.M)
        if not m:
            errors.append(f"headline group {g} has no definition line")
        groups.append({"key": g, "meaning": m.group(1).strip() if m else ""})

    sources_block = section(text, "Sources read")
    head, source_rows = table(sources_block)
    if head != SOURCE_COLUMNS:
        errors.append(f"sources table columns are {head}, expected {SOURCE_COLUMNS}")
    sources = [dict(zip(["key", "document", "url", "read", "notes"], r)) for r in source_rows]
    for src in sources:
        if not re.fullmatch(r"[A-Z]\d", src["key"]) or not src["url"].startswith("https://") \
                or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", src["read"]):
            errors.append(f"source {src['key']!r}: needs a key like N1, an https URL and a read date")
    keys = {src["key"] for src in sources}
    not_read = [m.group(1).strip() for m in re.finditer(r"^- (.+)$", sources_block.split("Not read", 1)[-1], re.M)] \
        if "Not read" in sources_block else []

    head, rows = table(section(text, "The fifty fields"))
    if head != COLUMNS:
        errors.append(f"field table columns are {head}, expected {COLUMNS}")
    fields, seen = [], set()
    for r in rows:
        if len(r) != len(COLUMNS):
            errors.append(f"row {r[:1]} has {len(r)} cells, expected {len(COLUMNS)}")
            continue
        f = dict(zip(["id", "field", "group", "standards", "read_in", "source", "cadence", "class", "detail", "drives"], r))
        f["read_in"] = [k.strip() for k in f["read_in"].split(",") if k.strip()]
        for k in f["read_in"]:
            if k not in keys:
                errors.append(f"{f['id']}: read-in key {k!r} is not in Sources read")
        if not f["read_in"] and "[CONFIRM]" not in f["standards"]:
            errors.append(f"{f['id']}: no source read and no [CONFIRM]")
        if not re.fullmatch(r"F\d{2}", f["id"]) or f["id"] in seen:
            errors.append(f"bad or repeated id {f['id']!r}")
        seen.add(f["id"])
        if f["class"] not in CLASSES:
            errors.append(f"{f['id']}: unknown class {f['class']!r}")
        if f["class"] in NAMED and not f["detail"]:
            errors.append(f"{f['id']}: class {f['class']} must name the file or agreement")
        f["standards"] = split_top(f["standards"])
        f["drives"] = [d.strip() for d in f["drives"].split(",") if d.strip()]
        for d in f["drives"]:
            if d not in GROUPS:
                errors.append(f"{f['id']}: unknown headline group {d!r}")
        if any(not f[k] for k in ("field", "group", "source", "cadence")) or not f["standards"]:
            errors.append(f"{f['id']}: an empty cell")
        fields.append(f)
    if len(fields) != EXPECTED:
        errors.append(f"{len(fields)} fields, expected {EXPECTED}")
    if errors:
        sys.exit("error: " + "\n       ".join(errors))

    filed = re.search(r"^Filed (\d{4}-\d{2}-\d{2})", text, re.M)
    return {
        "source": "docs/field_map_2026-11-04.md",
        "generated_by": "docs/build_fields_json.py",
        "filed": filed.group(1) if filed else None,
        "sources": sources,
        "not_read": not_read,
        "classes": classes,
        "counts": {c: sum(f["class"] == c for f in fields) for c in CLASSES},
        "headline_groups": [{**g, "fields": [f["id"] for f in fields if g["key"] in f["drives"]]} for g in groups],
        "fields": fields,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="fail when freshroot/fields.json is out of date")
    args = ap.parse_args()
    out = json.dumps(build(), indent=2, ensure_ascii=False) + "\n"
    if args.check:
        if not TARGET.exists() or TARGET.read_text() != out:
            sys.exit(f"error: {TARGET.relative_to(ROOT)} is out of date; run python3 docs/build_fields_json.py")
        print(f"{TARGET.relative_to(ROOT)} is current")
        return
    TARGET.write_text(out)
    doc = json.loads(out)
    print(f"wrote {TARGET.relative_to(ROOT)}: {len(doc['fields'])} fields, "
          + ", ".join(f"{c} {n}" for c, n in doc["counts"].items()))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""check_enum_coherence.py — meta-repo drift gate (D89, tier 2).

The mechanical floor under the D80 capture-time blast-radius sweep. When a
decision changes an enumerated set (the checkpoint `reconcile` kind, D68) or a
registry (a new code-map arm, D77/D79), every doc that *restates* it must be
updated too. The manual sweep is what failed the align cold-audit's 10 findings;
this gate makes forgetting fail the commit instead.

Two invariant kinds, both DECIDABLE (a finding is a fact, so it can block):
  * ENUM  — an owner declares the authoritative value set (e.g. the checkpoint
            `kind` enum in shared/schemas.md); every consumer that restates it
            must mention every value. Presence coverage, never prose.
  * COUNT — an owner registry has N members (e.g. the code-map precise arms in
            codemap.py's ARMS list); a consumer's "N <label>" claim must equal N.

Presence/count only — semantic drift ("X is described wrong") is `align`'s job.
Meta-repo only: it reads spec docs (10-roster.md, 11-roadmap.md) that never
ship, so it rides the meta-repo pre-commit beside check-status-coherence.sh —
NOT the shipped per-project checks.sh.
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # scripts/ -> repo root

# --- ENUM invariants ---------------------------------------------------------
# owner_re must capture the pipe-joined value set on the owning line.
ENUMS = [
    {
        "name": "checkpoint.kind",
        "owner": "shared/schemas.md",
        # anchor to the `request` line so we don't grab integrations/issue `kind:`.
        "owner_re": r"request[^\n]*kind:\s*([a-z]+(?:\|[a-z]+)+)",
        "consumers": ["skills/checkpoint/SKILL.md", "10-roster.md"],
    },
]

# --- COUNT invariants --------------------------------------------------------
COUNTS = [
    {
        "name": "codemap.precise_arms",
        "owner": "scripts/codemap/codemap.py",
        "owner_re": r"ARMS\s*=\s*\[([^\]]*)\]",   # ARMS = [PythonArm(), ..., GenericArm()]
        "exclude": {"GenericArm"},                # the tier-0 floor is not a "precise arm"
        "consumers": ["11-roadmap.md"],
        # "<count> precise [resolver] arms" — count may be a word or a digit.
        "consumer_re": r"\b([A-Za-z]+|\d+)\s+precise\s+(?:resolver\s+)?arms?\b",
    },
]

WORDS = {"zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
         "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12}


def _default_read(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as f:
        return f.read()


def _num(tok):
    """A count token as an int, or None if it is not a number word/digit."""
    tok = tok.lower()
    return int(tok) if tok.isdigit() else WORDS.get(tok)


def enum_values(owner_text, owner_re):
    """The authoritative value list, or None if the anchor pattern moved."""
    m = re.search(owner_re, owner_text)
    return [v for v in m.group(1).split("|") if v] if m else None


def registry_count(owner_text, owner_re, exclude):
    """Member count of an `X = [A(), B(), ...]` registry, minus excluded classes."""
    m = re.search(owner_re, owner_text, re.S)
    if not m:
        return None
    members = re.findall(r"(\w+)\s*\(\)", m.group(1))
    return len([x for x in members if x not in exclude])


def check_enums(read=_default_read):
    errs = []
    for inv in ENUMS:
        values = enum_values(read(inv["owner"]), inv["owner_re"])
        if values is None:
            errs.append(f"{inv['name']}: owner pattern not found in {inv['owner']} "
                        f"(the gate's own anchor moved — update check_enum_coherence.py)")
            continue
        for cons in inv["consumers"]:
            text = read(cons)
            missing = [v for v in values if not re.search(rf"\b{re.escape(v)}\b", text)]
            if missing:
                errs.append(f"{inv['name']}: {cons} is missing value(s) {', '.join(missing)} "
                            f"— owner {inv['owner']} declares {'|'.join(values)}")
    return errs


def check_counts(read=_default_read):
    errs = []
    for inv in COUNTS:
        n = registry_count(read(inv["owner"]), inv["owner_re"], inv.get("exclude", set()))
        if n is None:
            errs.append(f"{inv['name']}: registry pattern not found in {inv['owner']}")
            continue
        for cons in inv["consumers"]:
            text = read(cons)
            for m in re.finditer(inv["consumer_re"], text):
                claimed = _num(m.group(1))
                if claimed is None:
                    continue  # e.g. "the precise arms" — not a count claim, skip
                if claimed != n:
                    errs.append(f"{inv['name']}: {cons} claims {m.group(0)!r} but "
                                f"{inv['owner']} registers {n} "
                                f"(excluding {sorted(inv.get('exclude', []))})")
    return errs


def main(read=_default_read):
    errs = check_enums(read) + check_counts(read)
    if errs:
        print("enum-coherence: DRIFT")
        for e in errs:
            print(f"  - {e}")
        return 1
    print(f"OK: enum + registry coherence ({len(ENUMS)} enum, {len(COUNTS)} registry)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

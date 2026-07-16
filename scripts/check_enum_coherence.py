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
    {
        "name": "inbox.kind",
        "owner": "shared/schemas.md",
        # the typed-inbox message kinds (D93); anchors on `verdict|` so it can't
        # collide with the checkpoint `kind: demo|qa|…` line above.
        "owner_re": r"kind:\s*(verdict(?:\|[a-z]+)+)",
        "consumers": ["05-shared-state.md"],
    },
    {
        "name": "checkpoint.verdict.outcome",
        "owner": "shared/schemas.md",
        # the checkpoint verdict verb-enum (D97); anchors on `outcome:` so it can't
        # collide with either `kind:` enum above.
        "owner_re": r"outcome:\s*(approve(?:\|[a-z]+)+)",
        "consumers": ["skills/checkpoint/SKILL.md", "scripts/bus.py"],
        "consumer_re": {"scripts/bus.py": r"VERDICT_OUTCOMES\s*=\s*\(([^)]*)\)"},
    },
    {
        "name": "inbox.control.op",
        "owner": "shared/schemas.md",
        # A control op has no durable effect anchor, so the only thing making a
        # redelivered one safe is that re-applying it is a no-op. That holds only while
        # the set stays CLOSED and every member is idempotent by construction — so the
        # set drifting apart from the code that enforces it is exactly the failure this
        # gate exists to catch.
        "owner_re": r"op:\s*(reprioritize(?:\|[a-z]+)+)",
        "consumers": ["scripts/bus.py"],
        "consumer_re": {"scripts/bus.py": r"CONTROL_OPS\s*=\s*\(([^)]*)\)"},
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


# --- LAYOUT invariants (D114) ------------------------------------------------
# 05's disk-layout tree is the OWNER of three per-path properties: commit-class
# (RUNTIME vs committed), `bus:` (what the bus daemon does with the path), and
# `pin`/`no-pin` (native-FS relocation — a RUNTIME-only question, since a
# committed file lives on the repo mount by construction).
#
# These were prose lists before, in four places, and drifted three times: D105
# added `outbox/` and reached neither the served nor the pin list; D111 added
# `secrets/` and reached one pin list of two; `parked/` was pinned by 05 and not
# by schemas.md. The lists are gone — the tree carries the markers and these
# rules hold the two SHIPPED consumers to it (the spec-side readers just point).
LAYOUT_OWNER = "05-shared-state.md"
BUS_VALUES = {"read", "static", "write", "none"}


def _norm(path):
    """A tree path → its `.workflow/` key: `parked/<id>.json` → `parked`."""
    return path.strip().split("/")[0]


def parse_workflow_tree(text):
    """The `.workflow/` leaf rows of 05's layout tree as [(path, comment)].

    None if the anchor moved (the gate fails loudly rather than passing empty).
    """
    m = re.search(r"## Disk layout.*?\n```\n(.*?)\n```", text, re.S)
    if m is None:
        return None
    rows, base = [], None
    for line in m.group(1).split("\n"):
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip())
        if re.match(r"\s*\.workflow/\s*$", line):
            base = indent
            continue
        if base is None:
            continue          # still above `.workflow/`
        if indent <= base:
            break             # back out to a sibling — the block is done
        path, _, comment = line.strip().partition("#")
        rows.append((path.strip(), comment.strip()))
    return rows or None


def _pin_of(comment):
    """True (pinned) / False (explicitly not) / None (undeclared)."""
    if "no-pin" in comment:
        return False
    return True if re.search(r"(?<!-)\bpin\b", comment) else None


def check_layout_markers(rows):
    """R1 — every `.workflow/` path answers both questions at declaration."""
    errs = []
    for path, comment in rows:
        m = re.search(r"\bbus:([a-z]+)", comment)
        if m is None:
            errs.append(f"layout.markers: `{path}` declares no `bus:` marker in {LAYOUT_OWNER} "
                        f"(one of {'|'.join(sorted(BUS_VALUES))}) — does the bus read/serve/write it?")
        elif m.group(1) not in BUS_VALUES:
            errs.append(f"layout.markers: `{path}` declares `bus:{m.group(1)}` — not one of "
                        f"{'|'.join(sorted(BUS_VALUES))}")
        if "RUNTIME" in comment and _pin_of(comment) is None:
            errs.append(f"layout.markers: RUNTIME `{path}` declares neither `pin` nor `no-pin` in "
                        f"{LAYOUT_OWNER} — every runtime path states whether it is native-FS-pinned")
    return errs


def schemas_native_paths(text):
    """`.workflow/` keys whose schemas.md header claims a native filesystem."""
    out = set()
    for line in text.split("\n"):
        if line.startswith("## ") and "kept on a native filesystem" in line:
            m = re.search(r"`\.workflow/([^`<]+)", line)
            if m:
                out.add(_norm(m.group(1)))
    return out


def check_pin_consumer(rows, schemas_text):
    """R2 — the tree's `pin` set == schemas.md's native-FS claims, both ways."""
    pinned = {_norm(p) for p, c in rows if _pin_of(c) is True}
    claimed = schemas_native_paths(schemas_text)
    errs = []
    for miss in sorted(pinned - claimed):
        errs.append(f"layout.pin: {LAYOUT_OWNER} marks `{miss}` pin, but no shared/schemas.md header "
                    f"says it is 'kept on a native filesystem'")
    for extra in sorted(claimed - pinned):
        errs.append(f"layout.pin: shared/schemas.md says `{extra}` is 'kept on a native filesystem', "
                    f"but {LAYOUT_OWNER}'s tree does not mark it pin")
    return errs


def check_gitignore_consumer(rows, start_text):
    """R3 — every RUNTIME path in the tree is in start.md's gitignore scaffold."""
    m = re.search(r"Add the \*\*runtime\*\* paths to the target's `\.gitignore`(.*?);\s*the durable artifacts",
                  start_text, re.S)
    if m is None:
        return ["layout.gitignore: the gitignore-scaffold clause was not found in commands/start.md "
                "(the gate's own anchor moved — update check_enum_coherence.py)"]
    clause = m.group(1)
    return [f"layout.gitignore: {LAYOUT_OWNER} marks `{p}` RUNTIME, but commands/start.md's gitignore "
            f"scaffold does not list it — it would be committed"
            for p in sorted({_norm(p) for p, c in rows if "RUNTIME" in c}) if p not in clause]


def check_layout(read=_default_read):
    rows = parse_workflow_tree(read(LAYOUT_OWNER))
    if rows is None:
        return [f"layout: the disk-layout tree was not found in {LAYOUT_OWNER} "
                f"(the gate's own anchor moved — update check_enum_coherence.py)"]
    return (check_layout_markers(rows)
            + check_pin_consumer(rows, read("shared/schemas.md"))
            + check_gitignore_consumer(rows, read("commands/start.md")))


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


def declared_values(consumer_text, consumer_re):
    """The value list a CODE consumer declares, or None if the declaration moved."""
    m = re.search(consumer_re, consumer_text, re.S)
    if not m:
        return None
    return re.findall(r"['\"]([a-z][a-z-]*)['\"]", m.group(1))


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
            cre = (inv.get("consumer_re") or {}).get(cons)
            if cre:
                # A CODE consumer declares the set as a literal, so compare the literal
                # exactly — in both directions. A bare word-search is worthless here: it
                # passes on any mention anywhere in the file, and these values are common
                # English ("resume", "pause") that appear in prose and docstrings. This
                # gate was toothless until it stopped searching and started parsing.
                got = declared_values(text, cre)
                if got is None:
                    errs.append(f"{inv['name']}: declaration not found in {cons} "
                                f"(the gate's own anchor moved — update "
                                f"check_enum_coherence.py)")
                elif set(got) != set(values):
                    errs.append(
                        f"{inv['name']}: {cons} declares {'|'.join(got) or '(none)'} "
                        f"— owner {inv['owner']} declares {'|'.join(values)}")
            else:
                missing = [v for v in values if not re.search(rf"\b{re.escape(v)}\b", text)]
                if missing:
                    errs.append(f"{inv['name']}: {cons} is missing value(s) "
                                f"{', '.join(missing)} — owner {inv['owner']} "
                                f"declares {'|'.join(values)}")
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
    errs = check_enums(read) + check_counts(read) + check_layout(read)
    if errs:
        print("enum-coherence: DRIFT")
        for e in errs:
            print(f"  - {e}")
        return 1
    print(f"OK: enum + registry + layout coherence "
          f"({len(ENUMS)} enum, {len(COUNTS)} registry, 3 layout)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Contract linter — the decidable half of `align` (the alignment scan).

`align` reconciles the package's own wiring against itself. Most of that is
judgment (does the code honour the spec?) and rides a scoped semantic pass. This
script is the part a machine can settle: the **routing graph** (`loop.md`) is real
structured data, so its consistency with the skills is a *fact*, not a suspicion —
and a fact can hard-block a commit the way advisory prose never can. It is the
mechanical sibling of `check_promise_coverage.py` and `check-status-coherence.sh`.

WHAT IT CHECKS
  Hard (exit 1 — a genuinely broken graph):
    1. Dangling target — a routing table `next` points at something that is neither
       a node, a declared side-door, nor a known terminal (`idle`/`backlog`).
    2. Unrouted mode-ref — a skill body invokes a `node:mode` (e.g. `document:audit`)
       that `loop.md` never routes (an injected maintenance mode with no routing edge).
  Advisory (exit 0 — surfaced for human triage, never blocks; a skill may legitimately
  be a called sub-skill or a not-yet-wired entry):
    3. Coverage gap — a `skills/` dir is neither a `loop.md` node nor a side-door
       (e.g. a bootstrap entry that was never wired into the loop).
    4. Commitment-tag drift — a hyphenated derivative of a commitment enum value
       (e.g. `locked-candidate`) that isn't the bare enum.
    5. Novel `kind=` — a `kind=x` outside the union of the schema kind-enums.

HONEST CEILING (so no one mistakes this for the whole of `align`): this settles
only what `loop.md`'s table structure makes decidable. Schema producer/consumer
mismatches, spec↔code alignment, and promise adequacy are NOT decidable from prose
and are the job of `align`'s semantic pass — not this script. The enum checks (4/5)
are grep heuristics (advisory) — they can't tell a checkpoint-`kind` from an
issue-`kind` in prose, so they check the *union* and flag only the genuinely novel.
"""
import argparse
import json
import os
import re
import sys

# `schemas.md` is SPLIT (it outgrew the Read ceiling), so reading it as one file no longer
# yields the whole schema. The enum checks below union values out of whatever text they are
# handed: measured against the real split, a survivor-only read drops `generic` and `slack`
# out of the kind-union, and check 5 then reports legitimate uses as novel kinds. That is
# false-positive noise rather than a silent pass -- but noise is what teaches a human to stop
# reading advisories, and the union is simply wrong. `check_doc_budget.py` owns the split
# marker, so it owns following it.
#
# The import DEGRADES, it does not crash. Both scripts ship in the same manifest set, so in
# any real install the sibling is there — but this script's whole test suite exists because it
# once died in every product repo, and "resolve it or say so, never traceback" is the rule it
# was given then. A partial copy now reads the survivor and SAYS the split went unfollowed.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from check_doc_budget import read_with_splits
except ImportError:
    def read_with_splits(path):
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
        # A deliberately LOOSE sentinel, not a second copy of the marker: its only job is to
        # decide whether there is anything to warn about, so an unsplit schema stays quiet.
        note = ("check_doc_budget.py is not beside this script, so the split pointer in "
                "%s could not be followed" % os.path.basename(path))
        return text, [note] if "doc-budget:" in text else []

BACKTICK = re.compile(r"`([^`]+)`")
# a `node:mode` token: lower-kebab left + colon + lower-kebab right
MODE_REF = re.compile(r"^[a-z][a-z-]*:[a-z][a-z-]+$")
KIND_ASSIGN = re.compile(r"kind=([a-z][a-z-]*)")

TERMINALS = {"idle", "backlog", "start"}  # graph endpoints, never skill nodes


def _norm(tok):
    """Strip the routing table's optional-gate markers: `create-demo?` -> `create-demo`."""
    return tok.strip().rstrip("?!").strip()


def parse_loop(text):
    """Extract (nodes, targets, side_doors) from loop.md.

    `nodes` = full node ids from the table's first column (e.g. `planner:plan-one`).
    `targets` = every backticked token appearing as a routing destination (last column).
    `side_doors` = tokens on the 'Side doors' line.
    """
    nodes, targets, side_doors = set(), set(), set()
    for line in text.splitlines():
        s = line.strip()
        if s.lower().startswith("side door"):
            side_doors.update(_norm(m) for m in BACKTICK.findall(s))
            continue
        # a data row of the routing table: starts with '|' and carries backticks
        # (the header `| node | ... |` and separator `|---|` have none, so they skip)
        if s.startswith("|") and "`" in s:
            cols = [c.strip() for c in s.strip("|").split("|")]
            if len(cols) < 3:
                continue
            node_toks = BACKTICK.findall(cols[0])
            if node_toks:
                nodes.add(_norm(node_toks[0]))
            targets.update(_norm(m) for m in BACKTICK.findall(cols[-1]))
    return nodes, targets, side_doors


def parse_enums(schemas_text):
    """Pull the commitment enum + the union of kind-enums from schemas.md (kept DRY —
    the linter never hardcodes values that live in the schema)."""
    commitment = set()
    # anchor on the enum DEFINITION (`commitment` ∈ `{ ... }`), not the first brace
    # after the word — several field lists mention `commitment` as a member.
    m = re.search(r"`commitment`\s*∈\s*`?\{([^}]*)\}", schemas_text)
    if m:
        commitment = {v.strip() for v in m.group(1).split(",") if v.strip()}
    kinds = set()
    for grp in re.findall(r"kind:\s*([a-z|]+)", schemas_text):
        kinds.update(v.strip() for v in grp.split("|") if v.strip())
    return commitment, kinds


# An abstract *base* skill (e.g. `adjudicate`) is specialized by other skills and
# is never invoked directly, so it is deliberately neither a node nor a side-door —
# consumed by inheritance, not routing, so it is exempt from the coverage-gap advisory.
_BASE_SKILL = re.compile(r"not invoked directly|base procedure|abstract base", re.I)


def _is_base_skill(body):
    return bool(_BASE_SKILL.search(body))


def check(loop_text, skills, schemas_text):
    """skills: {name: body}. Returns (hard, advisory) — lists of message strings."""
    hard, advisory = [], []
    nodes, targets, side_doors = parse_loop(loop_text)
    node_bases = {n.split(":")[0] for n in nodes}
    reachable = nodes | node_bases | side_doors | TERMINALS
    commitment, kinds = parse_enums(schemas_text)

    # 1. dangling routing targets (hard)
    for t in sorted(targets - reachable):
        hard.append(f"loop.md routes to {t!r}, which is not a node, side-door, or terminal")

    # 2. unrouted mode-refs invoked by a skill (hard)
    routed = nodes | targets
    for name in sorted(skills):
        for tok in BACKTICK.findall(skills[name]):
            tok = tok.strip()
            if MODE_REF.match(tok) and tok.split(":")[0] in skills and tok not in routed:
                hard.append(
                    f"{name}: invokes {tok!r}, a node:mode that loop.md never routes"
                )

    # 3. coverage gap — a skill that is neither a node nor a side-door (advisory).
    #    Abstract base skills (specialized, never invoked directly) are exempt.
    covered = node_bases | side_doors
    for name in sorted(set(skills) - covered):
        if _is_base_skill(skills[name]):
            continue
        advisory.append(
            f"{name}: no loop.md node and not a declared side-door "
            f"(a called sub-skill is fine; an unrouted entry is drift)"
        )

    # 4. commitment-tag drift (advisory)
    if commitment:
        pat = re.compile(r"\b(?:" + "|".join(sorted(commitment)) + r")-[a-z][a-z-]*")
        for name in sorted(skills):
            for tag in sorted({m.group(0) for m in pat.finditer(skills[name])}):
                advisory.append(
                    f"{name}: uses commitment-derived tag {tag!r} outside the enum "
                    f"{sorted(commitment)}"
                )

    # 5. novel kind= (advisory)
    if kinds:
        for name in sorted(skills):
            for val in sorted(set(KIND_ASSIGN.findall(skills[name]))):
                if val not in kinds:
                    advisory.append(
                        f"{name}: kind={val!r} is outside the schema kind-enums {sorted(kinds)}"
                    )
    return hard, advisory


# --- forecast mode -----------------------------------------------------------
# A chain-forecast is a PREDICTION OVER THIS GRAPH, never a second graph — that is the
# whole reason every event has to name a real `loop.md` node, and it is what makes the
# forecast lintable at all (one routing owner). The check belongs here rather than
# in `forecast.py` because "is this a real node" is a `loop.md` fact, and this script
# already owns `loop.md` parsing; `forecast.py` owns the LIFECYCLE facts (freeze,
# reality, divergence, names-only) — one owner per fact-domain.

def check_forecast(loop_text, forecast):
    """Every event (and every branch target) names a place the graph really has.

    Returns a list of hard findings — a forecast routing somewhere `loop.md` does not go
    is decidably broken, exactly like a dangling routing target."""
    nodes, targets, side_doors = parse_loop(loop_text)
    reachable = nodes | {n.split(":")[0] for n in nodes} | side_doors | TERMINALS
    events = forecast.get("events") if isinstance(forecast, dict) else None
    if not isinstance(events, list) or not events:
        return ["forecast carries no `events[]` — there is no chain to lint"]

    def _resolve(tok, where):
        if not isinstance(tok, str) or not tok.strip():
            return [f"{where}: names no loop.md node (an event with no node is a "
                    f"prediction about nothing — it can never be matched to reality)"]
        tok = _norm(tok)
        # a mode of a real node (`document:audit`) is a real place, same as `check`'s rule
        if tok in reachable or tok.split(":")[0] in reachable:
            return []
        return [f"{where}: names {tok!r}, which is not a loop.md node, side-door, or terminal"]

    hard = []
    for i, ev in enumerate(events):
        if not isinstance(ev, dict):
            hard.append(f"event {i + 1}: is not an object")
            continue
        label = f"event {ev.get('n', i + 1)}"
        hard += _resolve(ev.get("node"), label)
        for j, br in enumerate(ev.get("branch") or []):
            if isinstance(br, dict):
                hard += _resolve(br.get("then"), f"{label} branch {j + 1}")
    return hard


def _read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def _load_skills(skills_dir):
    skills = {}
    for name in os.listdir(skills_dir):
        p = os.path.join(skills_dir, name, "SKILL.md")
        if os.path.isfile(p):
            skills[name] = _read(p)
    return skills


def default_paths(script=None, env=None):
    """(loop, skills_dir, schemas) for the layout this script is sitting in.

    Two real layouts, and the defaults must fit BOTH — `align` invokes this with no
    arguments from an installed project, and the meta-repo pre-commit invokes it with
    no arguments from the package tree.

      PACKAGE  `<root>/scripts/check_contracts.py`  (the meta-repo's `product/`, or a
               plugin root) → everything is a sibling of `scripts/`.
      INSTALLED `<project>/.claude/scripts/check_contracts.py` → the pieces live in two
               different trees: the routing graph the orchestrator actually follows is
               the PROJECT's `.workflow/loop.md` (`/start` copies it there), while the
               skills and `shared/schemas.md` are never installed at all — they stay
               under `${CLAUDE_PLUGIN_ROOT}`. Resolving all three as siblings of
               `.claude/scripts/` is what made this crash in every product repo.

    A path this cannot resolve comes back empty rather than wrong; `main` reports it.
    """
    script = script or os.path.abspath(__file__)
    root = os.path.dirname(os.path.dirname(script))
    if os.path.basename(root) != ".claude":
        return (os.path.join(root, "templates", "loop.md"),
                os.path.join(root, "skills"),
                os.path.join(root, "shared", "schemas.md"))
    project = os.path.dirname(root)
    plugin = (env if env is not None else os.environ).get("CLAUDE_PLUGIN_ROOT") or ""
    return (os.path.join(project, ".workflow", "loop.md"),
            os.path.join(plugin, "skills") if plugin else "",
            os.path.join(plugin, "shared", "schemas.md") if plugin else "")


def main(argv=None):
    d_loop, d_skills, d_schemas = default_paths()
    ap = argparse.ArgumentParser(description="Lint the routing graph against the skills.")
    ap.add_argument("--loop", default=d_loop)
    ap.add_argument("--skills-dir", default=d_skills)
    ap.add_argument("--schemas", default=d_schemas)
    ap.add_argument("--forecast", metavar="PATH",
                    help="lint a chain-forecast's events against the graph, and nothing "
                         "else (the package-wiring checks need inputs a forecast run has "
                         "no reason to resolve)")
    args = ap.parse_args(argv)

    # An input that is EXPLICITLY named but absent is a caller bug; an input that was
    # only defaulted and is absent is an environment we degrade through. Either way the
    # answer is an exit code and a sentence, never a traceback — `align` reads this.
    def _missing(flag, path, default, ok):
        if path and ok(path):
            return None
        if path and path != default:
            ap.error(f"{flag} {path!r} does not exist")
        return flag

    if _missing("--loop", args.loop, d_loop, os.path.isfile):
        ap.error(
            f"no routing graph to lint: {args.loop or '(unresolved)'} does not exist "
            "(installed layout expects the project's .workflow/loop.md)"
        )

    if args.forecast:
        try:
            with open(args.forecast, encoding="utf-8") as fh:
                fc = json.load(fh)
        except OSError as exc:
            ap.error(f"--forecast {args.forecast!r}: {exc.strerror}")
        except ValueError as exc:
            ap.error(f"--forecast {args.forecast!r} is not valid JSON: {exc}")
        hard = check_forecast(_read(args.loop), fc)
        if hard:
            print("BLOCKED: the forecast routes outside the graph:", file=sys.stderr)
            for h in hard:
                print(f"  - {h}", file=sys.stderr)
            return 1
        print("forecast: OK (every event names a real loop.md node)", file=sys.stderr)
        return 0

    # The package-wiring half needs the plugin tree, which an install does not copy.
    # Missing ⇒ run the graph-only half and SAY the rest was skipped: `align`'s own rule
    # is degrade-never-halt, but a silent skip reads as "all clear" (honest truncation).
    unread = [f for f in (_missing("--skills-dir", args.skills_dir, d_skills, os.path.isdir),
                          _missing("--schemas", args.schemas, d_schemas, os.path.isfile)) if f]
    skills = _load_skills(args.skills_dir) if "--skills-dir" not in unread else {}
    # Follow the split, so the enum union is taken over the WHOLE schema and not just the
    # survivor -- see the import note. An unreadable split half is announced, never swallowed.
    schemas_text, lost_splits = (
        read_with_splits(args.schemas) if "--schemas" not in unread else ("", []))

    hard, advisory = check(_read(args.loop), skills, schemas_text)

    for a in advisory:
        print(f"advisory: {a}", file=sys.stderr)
    for miss in lost_splits:
        print(f"advisory: schema split detail unreadable — {miss}; the enum union is "
              f"INCOMPLETE, so a novel `kind=` may go unflagged", file=sys.stderr)
    if unread:
        print(
            f"contracts: NOT CHECKED — {', '.join(unread)} unresolved"
            + (" (set CLAUDE_PLUGIN_ROOT)" if not os.environ.get("CLAUDE_PLUGIN_ROOT") else "")
            + "; only the routing-graph half ran (skill/enum checks skipped)",
            file=sys.stderr,
        )
    if hard:
        print("BLOCKED: contract linter found a broken routing graph:", file=sys.stderr)
        for h in hard:
            print(f"  - {h}", file=sys.stderr)
        return 1
    print(
        f"contracts: OK (routing graph consistent; {len(advisory)} advisory)",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

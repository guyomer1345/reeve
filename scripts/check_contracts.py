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
import os
import re
import sys

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


def main():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ap = argparse.ArgumentParser(description="Lint the routing graph against the skills.")
    ap.add_argument("--loop", default=os.path.join(root, "templates", "loop.md"))
    ap.add_argument("--skills-dir", default=os.path.join(root, "skills"))
    ap.add_argument("--schemas", default=os.path.join(root, "shared", "schemas.md"))
    args = ap.parse_args()

    hard, advisory = check(_read(args.loop), _load_skills(args.skills_dir), _read(args.schemas))

    for a in advisory:
        print(f"advisory: {a}", file=sys.stderr)
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

#!/usr/bin/env python3
"""The one report a human reads -- four fields, goal-relative, with NAMES instead of ids.

THE COMPLAINT THIS ANSWERS, in the maintainer's words: *"a lot of times i ask for status reports
or it even just stops and gives them to me ... currently i get a bunch of text with a lot of
references to [a decision id], Ref X ... i have no idea what the 91st decision of this project
was ... however if you actually name it, 'The X api integration decision', then i will have some
understanding. the status always comes extremely long and jumbled as well."* Three complaints, three different
answers, and only one of them is about layout:

  1. AN ID IS A POINTER, and a pointer rendered to a reader who cannot dereference it is noise
     that looks like rigour. Every id printed here is resolved to the title its OWNER records --
     `docs/decisions/index.md` for a decision, `goal.json` for an acceptance, the item's own
     `plan.md` heading for an item. An id whose title cannot be resolved is printed as
     UNRESOLVABLE, never silently dropped and never guessed: `missing` and `zero` are different
     answers here exactly as they are in `project_state.py`.
  2. LENGTH IS NOT FIXABLE BY ASKING FOR BREVITY. Every field has a hard line budget and every
     line a hard width; the overflow renders as `+N more (ask)`. A budget in a renderer holds. A
     budget in a SKILL.md is a suggestion the model is free to feel strongly about.
  3. A FORMAT DESCRIBED IN PROSE IS PROSE. The whole point of this file is that the report is
     GENERATED -- the orchestrator runs it and pastes the block rather than composing one --
     which is what makes the format a fact rather than an intention. `hooks/report_gate.py` is
     the actuator that makes skipping it impossible.

WHY IT IS GOAL-RELATIVE AND NOT PROJECT-RELATIVE. `project_state.py` answers "where is this
project" across five faces, and it is the right answer to that question. This answers a different
one -- *"where is the GOAL I set"* -- which is the question an overseer of an unattended drive is
actually asking. Nothing here is re-derived: the three measurable fields are `converge.py`'s
`measure()` re-rendered for a human, so this cannot disagree with the thing the driver stops on.
A second opinion about whether a goal is met is the last thing this loop needs.

FOUR CHANGES TO THE FORMAT AS ASKED FOR, each of which is an argument the maintainer is owed:
  · A GOAL LINE AT THE TOP. Every field says "for the goal" and none of them named it.
  · `decision for you` FLOATS TO THE TOP when non-empty and is OMITTED -- not rendered empty --
    when it is not. He is right that it is usually empty; a section that usually says nothing
    trains the eye to skip it, and the one time it matters it gets skipped too.
  · `in flight` SAYS WHETHER IT IS MOVING -- the node, the age, and the stall verdict. Without
    that, the field cannot distinguish working from stuck, which is the whole of his second ask.
  · A MACHINE MARKER at the foot, carrying a digest of the material state. It is what lets the
    `Stop` gate tell a current report from a stale or hand-written one without trusting either.

THE DIGEST DELIBERATELY EXCLUDES AGES AND TIMESTAMPS. It covers what the report SAYS -- goal,
progress, parked ticket ids, in-flight items and their nodes, discharged and outstanding
acceptance -- and nothing that moves on its own. A digest that changed every second would make
every report stale on arrival and the gate that reads it a nuisance to be disabled.

FAIL DIRECTION: report what is there, name what is not. A missing `goal.json` is a real and
common state (the loop runs item-at-a-time without one) and renders as such. Nothing here raises,
nothing here writes, and -- like `project_state.py` -- **nothing here is ever stored**: a
synthesized status doc is stale the moment the next commit lands, and a stale one is worse than
none because it is believed.

Usage:
    python3 status_report.py [--workflow .workflow] [--json] [--max N]
    python3 status_report.py --digest            # the marker's digest alone, for a gate
    python3 status_report.py --check FILE|-      # lint prose for ids rendered without a name
"""
import argparse
import hashlib
import io
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

MAX_LINES = 5          # per field, before the overflow line
LINE_CHARS = 150       # per rendered bullet
MARKER = "[reeve-report state:%s]"
MARKER_RE = re.compile(r"\[reeve-report state:([0-9a-f]{12})\]")

# Every id shape that reaches a human from this loop. Kept in one place because the renderer and
# the lint must agree about what an id IS -- two lists would drift and the lint would start
# passing exactly the tokens the renderer stopped naming.
ID_RE = re.compile(r"(?<![\w/-])(D-?\d{1,4}|ga-\d+|[A-Z]{2,4}-\d{1,5}|I-\d{1,5})(?![\w/-])")


# --- reading ------------------------------------------------------------------

def _read(path):
    try:
        with io.open(path, encoding="utf-8") as fh:
            return fh.read()
    except (OSError, UnicodeDecodeError):
        return None


def _json(path):
    raw = _read(path)
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except ValueError:
        return None


def _git(repo, *args):
    try:
        p = subprocess.run(["git", "-C", repo, *args],
                           capture_output=True, text=True, timeout=15)
    except (OSError, subprocess.SubprocessError):
        return None
    return p.stdout.strip() if p.returncode == 0 else None


def roots(workflow):
    """(repo, docs_root) -- honouring config.json's project_root/docs_root split, as
    `project_state.py` does. Org mode is the only caller that sets them apart."""
    cfg = _json(os.path.join(workflow, "config.json")) or {}
    base = os.path.dirname(os.path.abspath(workflow)) or "."
    repo = os.path.normpath(os.path.join(base, cfg.get("project_root") or "."))
    docs = cfg.get("docs_root")
    return repo, (os.path.normpath(os.path.join(base, docs)) if docs else repo)


# --- names, which is the whole point ------------------------------------------

DECISION_ROW = re.compile(r"^\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|")


def names(workflow, docs_root):
    """{id: title} from each id's OWNER. Never invents, never falls back to another owner.

    The owners, and why each: a decision's title is the one line `decision-engineer` wrote into
    `docs/decisions/index.md`, which is a table precisely so it can be read; a goal acceptance's
    text is in `goal.json`, the only place it carries an id at all; an item's name is the first
    heading of its own `plan.md`, because the plan is the thing that named it.
    """
    out = {}
    index = _read(os.path.join(docs_root, "docs", "decisions", "index.md")) or ""
    for line in index.splitlines():
        m = DECISION_ROW.match(line.strip())
        if not m:
            continue
        ident, title = m.group(1).strip(" `*"), m.group(2).strip(" `*")
        if ID_RE.fullmatch(ident) and title.lower() not in ("title", "---", ""):
            out[ident] = title
    goal = _json(os.path.join(workflow, "goal.json")) or {}
    for a in goal.get("acceptance") or []:
        if isinstance(a, dict) and a.get("id"):
            out[str(a["id"])] = (a.get("text") or "").strip() or None
    items = os.path.join(workflow, "items")
    for item in sorted(os.listdir(items)) if os.path.isdir(items) else []:
        head = _read(os.path.join(items, item, "plan.md")) or ""
        for line in head.splitlines():
            if line.startswith("# "):
                out[item] = line[2:].strip()
                break
    return {k: v for k, v in out.items() if v}


def gloss(ident, known, drop_if_unresolvable=False):
    """`D-001 (the thing it decided)` -- or a printed admission that it cannot be resolved.

    The admission is the load-bearing half. Dropping an unresolvable id would hide the defect
    (an index row nobody wrote); printing it bare is the thing being complained about.
    """
    title = known.get(ident)
    if title:
        return "%s (%s)" % (ident, title)
    if drop_if_unresolvable:
        # For an OPTIONAL attribution only, and there is one structural case that needs it: a
        # promoted item's directory -- `plan.md` with it -- is pruned by `retention.py`, so the
        # name of the item that discharged an acceptance months ago is gone BY DESIGN. Printing
        # `UNRESOLVABLE` there would cry wolf on the normal case and teach the reader to ignore
        # the word on the day it means something. The acceptance itself is still named; what is
        # dropped is a pointer the reader could not have followed either way.
        return None
    return "%s (UNRESOLVABLE — nothing names this id)" % ident


def bare_ids(text, known=None):
    """-> [(id, line number)] for every id rendered WITHOUT a name beside it.

    The convention being enforced is exactly one character wide: an id is named when the next
    thing after it -- past a space or a backtick -- is `(`. Anything looser (a title "somewhere nearby") is not decidable, and a lint
    that guesses is a lint that gets argued with.

    Fenced code blocks are skipped whole: a command line or a JSON body quoting an id is machine
    text that a human is not being asked to dereference.
    """
    out, fenced = [], False
    for n, line in enumerate(text.splitlines(), 1):
        if line.lstrip().startswith("```"):
            fenced = not fenced
            continue
        if fenced:
            continue
        for m in ID_RE.finditer(line):
            after = line[m.end():m.end() + 4].lstrip(" `")
            if after.startswith("("):
                continue
            out.append((m.group(1), n))
    return out


# --- the four fields ----------------------------------------------------------

def _age(seconds):
    if seconds is None:
        return "age unknown"
    m = int(seconds // 60)
    if m < 60:
        return "%dm" % max(m, 0)
    if m < 60 * 48:
        return "%dh" % (m // 60)
    return "%dd" % (m // 1440)


def _mtime(path):
    try:
        return os.path.getmtime(path)
    except OSError:
        return None


def open_items(workflow, now):
    """Items present on disk without a `promoted.json` -- `converge.py`'s own definition of open,
    reused rather than restated so the two can never disagree about what is in flight."""
    items_dir = os.path.join(workflow, "items")
    out = []
    for name in sorted(os.listdir(items_dir)) if os.path.isdir(items_dir) else []:
        d = os.path.join(items_dir, name)
        if not os.path.isdir(d) or os.path.exists(os.path.join(d, "promoted.json")):
            continue
        stamps = [t for t in (_mtime(os.path.join(d, f)) for f in os.listdir(d)) if t]
        newest = max(stamps) if stamps else _mtime(d)
        promises = _json(os.path.join(d, "promises.json")) or {}
        refs = sorted({(c.get("goal_ref") or "").strip()
                       for c in promises.get("criteria") or [] if isinstance(c, dict)} - {""})
        out.append({"item": name, "refs": refs,
                    "idle_seconds": (now - newest) if newest else None})
    return out


def parked(workflow, now):
    """The `decision for me to take` field, and the reason it floats to the top when non-empty."""
    d = os.path.join(workflow, "parked")
    out = []
    for name in sorted(os.listdir(d)) if os.path.isdir(d) else []:
        if not name.endswith(".json"):
            continue
        path = os.path.join(d, name)
        rec = _json(path) or {}
        cp = rec.get("checkpoint") or {}
        request = cp.get("request") if isinstance(cp.get("request"), dict) else {}
        what = rec.get("summary") or request.get("what") or "(no summary on the parked record)"
        stamp = _mtime(path)
        out.append({"ticket": rec.get("ticket_id") or name[:-5],
                    "kind": cp.get("kind") or "unknown",
                    "what": str(what),
                    "waiting": _age(now - stamp if stamp else None)})
    return out


def build(workflow, now=None, repo=None, docs_root=None):
    """The whole report as one dict. Every number in it comes from `converge.py` or a file."""
    import time
    now = time.time() if now is None else now
    if repo is None or docs_root is None:
        repo, docs_root = roots(workflow)
    import converge

    goal = converge.read_goal(workflow)
    m = converge.measure(goal, converge.read_ledger(workflow),
                         converge.open_bindings(workflow))
    known = names(workflow, docs_root)
    state = _json(os.path.join(workflow, "state.json")) or {}

    # Which item discharged which acceptance, for the ACHIEVED field. The ledger is the owner:
    # `document` wrote it at promote time and the item dir it refers to may since be pruned.
    by_ref = {}
    for e in converge.read_ledger(workflow):
        for r in e.get("refs") or []:
            by_ref.setdefault(r, e.get("item"))

    flight = open_items(workflow, now)
    bound_by = {}
    for it in flight:
        for r in it["refs"]:
            bound_by.setdefault(r, []).append(it["item"])

    status = m.get("status") or {}
    return {
        "goal": {
            "id": m.get("goal"),
            "statement": (goal or {}).get("statement", ""),
            "progress": m.get("progress"),
            "met": bool(m.get("met")),
            "stalled": bool(m.get("stalled")),
            "streak": m.get("streak"),
            "stall_limit": m.get("stall_limit"),
            "reason": m.get("reason"),
        },
        "decisions": parked(workflow, now),
        "achieved": [{"id": a, "name": gloss(a, known),
                      "by": gloss(by_ref[a], known, drop_if_unresolvable=True)
                            if by_ref.get(a) else None}
                     for a in sorted(status) if status[a] == "discharged"],
        "in_flight": [{"item": it["item"], "name": gloss(it["item"], known),
                       "node": state.get("node") if state.get("current_item") == it["item"]
                               else None,
                       "idle": _age(it["idle_seconds"]),
                       "discharges": [gloss(r, known) for r in it["refs"]]}
                      for it in flight],
        "left": [{"id": a, "name": gloss(a, known), "state": status[a],
                  "by": [gloss(i, known) for i in bound_by.get(a, [])]}
                 for a in sorted(status) if status[a] in ("planned", "unbound")],
        "loop": {"status": state.get("status"), "node": state.get("node"),
                 "current_item": state.get("current_item"),
                 "head": (_git(repo, "rev-parse", "--short", "HEAD") or "")},
    }


def digest(report):
    """A fingerprint of what the report SAYS -- never of when it was said.

    Ages, deadlines and timestamps are excluded on purpose: a digest that moved on its own would
    make every report stale on arrival, and a gate that rejects a report written ten seconds ago
    is a gate that gets switched off within the day.
    """
    g = report.get("goal") or {}
    material = {
        "goal": g.get("id"), "progress": g.get("progress"),
        "met": g.get("met"), "stalled": g.get("stalled"),
        "decisions": sorted(d["ticket"] for d in report.get("decisions") or []),
        "in_flight": sorted((i["item"], i.get("node") or "") for i in report.get("in_flight") or []),
        "achieved": sorted(a["id"] for a in report.get("achieved") or []),
        "left": sorted((l["id"], l["state"]) for l in report.get("left") or []),
        "head": (report.get("loop") or {}).get("head"),
    }
    blob = json.dumps(material, sort_keys=True, default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:12]


# --- rendering ----------------------------------------------------------------

def _bullets(rows, limit):
    """The budget, applied in one place. `+N more (ask)` rather than a silent truncation: a
    report that quietly drops its tail is how "extremely long" gets replaced by "wrong"."""
    out = ["  - %s" % r[:LINE_CHARS] for r in rows[:limit]]
    if len(rows) > limit:
        out.append("  +%d more (ask)" % (len(rows) - limit))
    return out


def render(report, limit=MAX_LINES):
    g = report["goal"]
    lines = []
    if not g.get("id"):
        lines.append("GOAL — none set. %s" % (g.get("reason") or "nothing to converge on"))
    else:
        moving = "MET" if g["met"] else ("STALLED — %s promotions with no new acceptance"
                                         % g.get("streak") if g["stalled"] else "moving")
        lines.append("GOAL — %s  ·  %s  ·  %s" % (g.get("statement") or g["id"],
                                                  g.get("progress"), moving))
    # FIRST when non-empty, ABSENT when not. A section that usually says nothing teaches the eye
    # to skip it, and then it is skipped on the one day it matters.
    if report["decisions"]:
        lines.append("")
        lines.append("DECISION FOR YOU (%d)" % len(report["decisions"]))
        # The ticket id LEADS, in the same `id (name)` shape as everything else here — it is
        # the handle the human quotes back to answer, so it is the one id in this block that is
        # not merely a pointer, and it still may not appear without its name.
        lines += _bullets(["%s (%s) — %s checkpoint, waiting %s"
                           % (d["ticket"], d["what"], d["kind"], d["waiting"])
                           for d in report["decisions"]], limit)
    lines.append("")
    lines.append("ACHIEVED (%d)" % len(report["achieved"]))
    lines += _bullets(["%s%s" % (a["name"], " — by %s" % a["by"] if a["by"] else "")
                       for a in report["achieved"]] or ["nothing discharged yet"], limit)
    lines.append("")
    lines.append("IN FLIGHT (%d)" % len(report["in_flight"]))
    lines += _bullets(["%s — %s, idle %s%s" % (
        i["name"], i["node"] or "not the current item", i["idle"],
        "; discharges " + ", ".join(i["discharges"]) if i["discharges"]
        else "; BINDS NO GOAL ACCEPTANCE")
        for i in report["in_flight"]] or ["nothing open"], limit)
    lines.append("")
    lines.append("LEFT (%d)" % len(report["left"]))
    lines += _bullets(["%s — %s" % (
        l["name"], ("planned in " + ", ".join(l["by"])) if l["state"] == "planned"
        else "UNBOUND: no plan attempts this, so the goal cannot be met as planned")
        for l in report["left"]] or ["nothing outstanding"], limit)
    lines.append("")
    lines.append(MARKER % digest(report))
    return "\n".join(lines)


# --- entry --------------------------------------------------------------------

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--workflow", default=".workflow")
    ap.add_argument("--json", action="store_true", help="the structure, not the rendered block")
    ap.add_argument("--digest", action="store_true", help="the marker digest alone, for a gate")
    ap.add_argument("--max", type=int, default=MAX_LINES, help="bullets per field")
    ap.add_argument("--check", metavar="FILE",
                    help="lint prose for ids printed without a name ('-' for stdin)")
    args = ap.parse_args(argv)

    if args.check:
        text = sys.stdin.read() if args.check == "-" else (_read(args.check) or "")
        known = names(args.workflow, roots(args.workflow)[1])
        findings = bare_ids(text, known)
        for ident, line in findings:
            print("line %d: `%s` printed with no name — write `%s`"
                  % (line, ident, gloss(ident, known)), file=sys.stderr)
        if findings:
            print("%d bare id(s): an id is a pointer, and a pointer the reader cannot "
                  "dereference is noise that looks like rigour." % len(findings), file=sys.stderr)
            return 1
        print("OK: every id is named")
        return 0

    if not os.path.isdir(args.workflow):
        print("no %s here — this is not an initialised project" % args.workflow, file=sys.stderr)
        return 2
    report = build(args.workflow)
    if args.digest:
        print(digest(report))
    elif args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(render(report, args.max))
    return 0


if __name__ == "__main__":
    sys.exit(main())

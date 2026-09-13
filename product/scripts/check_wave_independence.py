#!/usr/bin/env python3
"""The fan-out gate — what may legally be dispatched in the SAME turn, and nothing more.

The loop is allowed to run several work items concurrently, each in its own worktree. That
permission is worth exactly as much as the proof behind it, so this script answers one
question and refuses to answer any other:

    given these candidate items, what is the largest batch that can be SHOWN to be
    mutually non-intervening right now?

THE PREDICATE. A candidate enters the batch only if all three hold:
  1. DEPENDENCY-READY  every id in its `depends_on` is finished.
  2. FILE-DISJOINT     its declared file scope shares nothing with any other batch member,
                       nor with any item already in flight or parked.
  3. NOT A 1-HOP NEIGHBOUR  no file it declares is one code-map edge away from a file another
                       member declares. Two files that import each other are one change, even
                       when they are two files.

THE FAILURE DIRECTION IS THE WHOLE POINT. The burden of proof is on fanning out, never on
staying serial. Every input this gate needs is evidence; when the evidence is absent,
unreadable or ambiguous the answer is NOT "probably fine", it is "runs serially". No plan, no
declared file scope, no code map, a scope entry that names something this script cannot
resolve to a path, a dependency it cannot locate — each of those is a candidate held back, and
the reason is printed rather than swallowed. A gate that guesses in the permissive direction
is not a gate; it is a coin flip with a log file.

ADJACENCY REJECTS. IT DOES NOT FLAG. An earlier design graded clause 3 softly: trip it and the
item still started, merely marked for heavier integration checking. That grading assumed the
neighbour was working LATER, against a tree the first item had already landed. Under same-turn
dispatch it is working at the SAME MOMENT, on a tree neither of them has landed yet, and the
raised rigor has nothing to be rigorous about. So clause 3 is hard here. The trip is still
reported as its own clause, because "these two are one edge apart" is useful to an operator
either way -- but it never admits a candidate.

WHY EVERY REJECTION NAMES A CLAUSE AND A COUNTERPARTY. "not eligible" is an answer nobody can
act on. A human deciding whether to re-slice an item, and a loop deciding what to queue next,
both need to know it was clause 2 against item X on `src/a.py` -- not that something,
somewhere, said no.

DETERMINISM. Same inputs must always give the same batch, or a wave cannot be reproduced or
reviewed. Selection is a greedy first-fit walk in QUEUE ORDER: the order rows appear in
`backlog.md`, ties (and anything absent from it) broken by ascending id. Greedy in queue order
is deliberately NOT maximum-cardinality: dropping the head of the queue to fit two items from
further down would silently re-order the queue, and ordering belongs to the prioritize step,
not to a safety check. The head of the queue enters the batch whenever it legally can.

WHAT COUNTS AS FINISHED, AND THE PRICE OF SAYING SO PRECISELY. A dependency is done when its
item dir carries the `promoted.json` marker -- the same marker the retention pass keys the
item-dir prune off, so there is one owner for "this item is finished" and no second copy to
drift. Backlog prose is NOT consulted for doneness: a row that merely looks closed would make
its dependents look ready, which is a failure in the permissive direction. The price is real
and is stated rather than hidden: once a finished item's dir has been pruned, the only
surviving evidence that it finished is git history, which this script does not read, so a
candidate depending on a pruned item is held serial until someone says otherwise.

WHERE THE BURDEN DOES NOT FALL, said plainly because it is the one judgement call in here. A
parked ticket with no item dir -- a checkpoint waiting on a human, say -- declares no file
scope, and there is no plan for it to be missing. It is a request, not a writer, so it is
reported and it does not block the batch. A parked or in-flight id that DOES have an item dir
is a writer; if its plan cannot be read, nothing can be proven disjoint from it and the whole
batch is refused. The burden of proof falls on the thing asking to be dispatched.

EXIT CODES -- TWO, AND THE SECOND ONE IS THE SAFE DEFAULT.
    0  FAN-OUT   a batch of two or more was proven independent. Dispatch it in one turn.
    1  SERIAL    no such batch could be proven. Run one item at a time.
There is deliberately no third code for "something went wrong". Every failure to compute --
an unreadable config, a missing code map, a plan that will not parse -- lands on 1, because
1 is the conservative answer and a caller that can tell an error from a verdict will sooner
or later treat the error as a verdict. The consequence is worth stating: a shell caller that
ignores the report entirely and branches on the exit status alone still behaves correctly,
since the only non-zero answer it can get is "stay serial". The report and `--json` DO
separate "proven not independent" from "could not be proven", so an operator can act on the
difference.

  --project-root PATH   where `.workflow/` lives (default `.`).
  [ID ...]              candidates to test. Default: every open backlog row that is not
                        already in flight or parked.
  --max N               ceiling on concurrent workers (default 3); items already in flight
                        count against it. Bounded concurrency is retained on purpose -- the
                        number of simultaneous writers a single human can still review is
                        small, and it is not the batch former's job to discover that.
  --json                machine-readable verdict.
"""
import argparse
import fnmatch
import glob
import json
import os
import re
import sys

CONFIG_REL = os.path.join(".workflow", "config.json")
WILDCARD = re.compile(r"[*?\[]")

# Clause labels. One spelling, used by the renderer, the JSON and the tests alike -- a reason
# string a caller has to pattern-match on is a contract, so it gets named once.
DEPENDENCY = "dependency"     # clause 1
OVERLAP = "file-overlap"      # clause 2
ADJACENCY = "adjacency"       # clause 3 -- hard here, see the module docstring
SCOPE = "scope"               # nothing to test clause 2 or 3 against
GRAPH = "code-map"            # clause 3 cannot be evaluated at all
HELD = "held-scope"           # a writer is already out there with an unknown file scope
CAPACITY = "capacity"         # legal, but the concurrency ceiling is full


# ---------------------------------------------------------------- roots and config

def _read_json(path, default=None):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return default


def roots(project_root):
    """-> (workflow_root, code_root, docs_root), all absolute and normalised.

    `project_root` and `docs_root` are commonly RELATIVE spellings (`./project`), and a
    relative spelling joined onto an absolute one produces `<root>/./project/...`, which
    denotes the same file as `<root>/project/...` and compares unequal to it. A sibling gate
    double-counted a document for exactly that reason. So every path this script will ever
    compare is normalised the moment it is built, and nothing downstream is allowed to build
    one by hand.
    """
    wf = os.path.abspath(project_root)
    cfg = _read_json(os.path.join(wf, CONFIG_REL), {}) or {}
    proot = cfg.get("project_root") or "."
    droot = cfg.get("docs_root") or proot
    return (wf,
            os.path.normpath(os.path.join(wf, proot)),
            os.path.normpath(os.path.join(wf, droot)))


def _key(wf, path):
    """The one canonical spelling of a file: workflow-root-relative, POSIX separators.

    Everything -- plan entries, code-map nodes, on-disk hits -- is reduced to this before any
    comparison. Two spellings of one file that compare unequal is the bug class this exists to
    remove, and it is not hypothetical.
    """
    return os.path.relpath(os.path.normpath(path), wf).replace(os.sep, "/")


# ---------------------------------------------------------------- the code map

def load_graph(wf, code_root, docs_root):
    """-> (neighbours, info). `neighbours[key]` is the set of keys one edge away, undirected.

    WHERE IT LIVES AND WHAT IT IS ABOUT ARE TWO ROOTS. The map is written under the docs root
    and its node paths are anchored at the CODE root; those coincide everywhere except the mode
    that clones a repo it does not own, and collapsing them there would look for the map in the
    owner's tree.

    THE `root` FIELD IN THE GRAPH IS NOT TRUSTED. A real generated map carried `"root": "."`
    while its nodes were scoped to the nested code root -- the field records where the
    extractor was invoked, which is not reliably where its paths are anchored. So each node
    path is anchored by trying the code root first and the workflow root second, preferring
    whichever actually exists on disk. Edge endpoints go through the same function, so both
    ends of an edge can never disagree about which file they mean.

    Direction is discarded on purpose: for "are these two areas one change?", A importing B and
    B importing A are the same answer.
    """
    path = os.path.join(docs_root, "docs", "knowledge", "graph.json")
    info = {"path": _key(wf, path), "present": False, "nodes": 0, "edges": 0, "why": ""}
    data = _read_json(path)
    if not isinstance(data, dict) or not isinstance(data.get("nodes"), list) \
            or not isinstance(data.get("edges"), list):
        info["why"] = ("no readable code map at %s -- clause 3 cannot be evaluated"
                       % info["path"])
        return {}, info

    def anchor(rel):
        rel = str(rel or "").replace("\\", "/").lstrip("/")
        if not rel:
            return None
        for base in (code_root, wf):
            cand = os.path.normpath(os.path.join(base, rel))
            if os.path.exists(cand):
                return _key(wf, cand)
        return _key(wf, os.path.join(code_root, rel))

    nodes = set()
    for n in data["nodes"]:
        k = anchor(n.get("path") if isinstance(n, dict) else n)
        if k:
            nodes.add(k)
    nbr = {}
    edges = 0
    for e in data["edges"]:
        if not isinstance(e, dict):
            continue
        a, b = anchor(e.get("from")), anchor(e.get("to"))
        if not a or not b or a == b:
            continue
        nbr.setdefault(a, set()).add(b)
        nbr.setdefault(b, set()).add(a)
        edges += 1
    info.update(present=True, nodes=len(nodes), edges=edges)
    info["node_set"] = nodes
    return nbr, info


# ---------------------------------------------------------------- the backlog

ROW = re.compile(r"^\s*[-*]\s+(?:\[[ xX]\]\s*)?(?:\*\*|`)?(?P<id>[A-Za-z0-9][A-Za-z0-9._/-]*)"
                 r"(?:\*\*|`)?\s*(?P<rest>[·:—-].*)?$")
DEPS = re.compile(r"\b(?:deps|depends_on|depends on)\b\s*[:=]?\s*(?P<v>[^·|]*)", re.I)
EMPTY_DEPS = {"", "-", "--", "—", "none", "n/a", "na", "nil", "[]"}


def parse_backlog(wf):
    """-> (rows, present). Each row: `{id, order, deps, deps_raw, unparsed_deps}`.

    The backlog is prose with structure in it, not a data file, and the shapes below are the
    ones real queues use: a bolded or backticked id at the head of a list item, fields
    separated by middots, and a `deps:` (or `depends_on:`) field that is either a comma list of
    ids or the word `none`. A dependency field this cannot reduce to ids is kept VERBATIM in
    `unparsed_deps` and rejects the candidate -- prose like "X plus a clean audit path" is a
    real dependency statement that no reader here can settle, and settling it by ignoring it
    would dispatch a worker onto unready ground.
    """
    path = os.path.join(wf, ".workflow", "backlog.md")
    try:
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
    except OSError:
        return [], False
    rows, seen, order = [], set(), 0
    for line in text.splitlines():
        if line.lstrip().startswith(">"):
            continue                     # a banner/blockquote is commentary, never a row
        m = ROW.match(line)
        if not m:
            continue
        ident = m.group("id")
        if ident in seen:
            continue                     # first mention wins: it is the one that sets order
        rest = m.group("rest") or ""
        deps, raw, bad = [], "", []
        dm = DEPS.search(rest)
        if dm:
            raw = dm.group("v").strip()
            cleaned = raw.strip().strip("*").strip()
            if cleaned.strip("`").strip().lower() in EMPTY_DEPS:
                pass
            else:
                for tok in re.split(r"[,+/]| and ", cleaned):
                    tok = tok.strip().strip("*`").strip().rstrip(".")
                    if not tok:
                        continue
                    if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", tok):
                        deps.append(tok)
                    else:
                        bad.append(tok)
        seen.add(ident)
        order += 1
        rows.append({"id": ident, "order": order, "deps": deps,
                     "deps_raw": raw, "unparsed_deps": bad})
    return rows, True


# ---------------------------------------------------------------- the plan's file scope

HEADING = re.compile(r"^#+\s*files[ _]touched\b[^\n]*$(.*?)(?=^#+\s|\Z)", re.M | re.S | re.I)


def plan_tokens(wf, item):
    """-> (tokens, why). The backticked entries of a plan's declared file scope.

    Both real spellings of the section are read -- a `|`-table under `## Files touched` and a
    bullet list under `## files_touched` -- because plans in one repo use each, and a parser
    that knows one scores the other as declaring nothing. Only the head of a bullet (before the
    em-dash) and the first cell of a table row are read: the prose after it routinely
    backquotes symbols and function names, and folding those in would silently widen the
    declared scope until it covered files the plan never claimed.

    `why` distinguishes the absences, which are not the same absence: `no plan` (never
    planned), `no scope` (planned, declares nothing). Both hold the candidate serial; only one
    of them is fixed by writing a plan.
    """
    try:
        with open(os.path.join(wf, ".workflow", "items", item, "plan.md"),
                  encoding="utf-8") as fh:
            text = fh.read()
    except OSError:
        return [], "no plan"
    m = HEADING.search(text)
    if not m:
        return [], "no scope"
    toks = []
    for line in m.group(1).splitlines():
        row = line.strip()
        if row.startswith("|"):
            if row.count("|") < 2:
                continue
            cell = line.split("|")[1]
            if re.fullmatch(r"[\s:|-]*", cell):
                continue                 # the table's own separator row
        elif row.startswith(("-", "*", "+")):
            cell = re.split(r"—|--", row.lstrip("-*+ "), maxsplit=1)[0]
        else:
            continue                     # a wrapped continuation line is prose, not a row
        toks.extend(t.strip() for t in re.findall(r"`([^`]+)`", cell))
    return [t for t in toks if t], ("" if toks else "no scope")


def _braces(tok):
    """`a/{x,y}/z` -> [`a/x/z`, `a/y/z`]. Real plans use it; an unexpanded brace matches
    nothing on disk and would read as an unresolvable entry, which is a rejection for the
    wrong reason."""
    m = re.search(r"\{([^{}]*)\}", tok)
    if not m:
        return [tok]
    out = []
    for part in m.group(1).split(","):
        out.extend(_braces(tok[:m.start()] + part.strip() + tok[m.end():]))
    return out


def resolve_scope(wf, code_root, graph_nodes, tokens):
    """-> `{files, patterns, prospective, unresolved}` for one item's declared scope.

    A declared entry is accepted only if it can be pinned to a path: it exists on disk, or the
    code map knows it, or it is a file the plan will CREATE in a directory that exists. Nothing
    else is admitted. A bare symbol name, a shell fragment, a basename with no directory -- all
    of them land in `unresolved`, and an item with any unresolved entry is held serial, because
    a scope declaration that cannot be read completely has not been read at all: the entry this
    script skipped is exactly the one the other worker might also be writing.

    `prospective` is called out separately and is NOT an unresolved entry. A file that does not
    exist yet cannot be imported by anything, so it has no code-map neighbours -- legitimately,
    not for want of evidence. What stays undecidable is whether the new file will END UP
    coupled to another member's work, and no code map can answer that before the code exists.
    It is listed in the report so the reader knows which part of the answer is a fact about the
    graph and which part is a fact about a file that has not been written.
    """
    out = {"files": set(), "patterns": set(), "prospective": set(), "unresolved": []}

    def pin(v):
        """One brace-free entry -> (kind, key) or (None, None). Tried against the workflow
        root first and the nested code root second, because plans spell paths both ways."""
        for base in (wf, code_root):
            cand = os.path.normpath(os.path.join(base, v))
            k = _key(wf, cand)
            if os.path.isdir(cand):
                return "dir", k
            if os.path.isfile(cand) or k in graph_nodes:
                return "file", k
        # A file the plan will CREATE: exactly one path, in a directory that already exists.
        for base in (wf, code_root):
            cand = os.path.normpath(os.path.join(base, v))
            if "/" in v and os.path.splitext(v)[1] and os.path.isdir(os.path.dirname(cand)):
                return "new", _key(wf, cand)
        return None, None

    def spread(v):
        """One brace-free WILDCARD entry -> (matched keys, pattern) or (None, None)."""
        for base in (wf, code_root):
            pat = _key(wf, os.path.normpath(os.path.join(base, v)))
            got = {_key(wf, p) for p in glob.glob(os.path.join(base, v), recursive=True)
                   if os.path.isfile(p)}
            got |= {k for k in graph_nodes if fnmatch.fnmatch(k, pat)}
            if got:
                return got, pat
        return None, None

    for tok in tokens:
        raw = tok.strip()
        if raw.startswith("./"):
            raw = raw[2:]
        for v in _braces(raw):
            v = v.strip().replace("\\", "/")
            if not v:
                out["unresolved"].append(raw)
                continue
            if WILDCARD.search(v):
                got, pat = spread(v)
                if got is None:
                    out["unresolved"].append(v)
                else:
                    out["files"].update(got)
                    out["patterns"].add(pat)
                continue
            kind, k = pin(v)
            if kind is None:
                out["unresolved"].append(v)
            elif kind == "dir":
                # A directory names its whole subtree. Both the key and the subtree pattern
                # are kept: the key catches an exact repeat, the pattern catches another item
                # naming a file inside it.
                out["files"].add(k)
                out["patterns"].add(k.rstrip("/") + "/*")
            else:
                out["files"].add(k)
                if kind == "new":
                    out["prospective"].add(k)
    out["unresolved"] = sorted(set(out["unresolved"]))
    return out


def item_scope(wf, code_root, graph_nodes, item):
    """-> (scope, why). The full read for one item: plan -> tokens -> resolved paths."""
    toks, why = plan_tokens(wf, item)
    if why:
        return None, why
    scope = resolve_scope(wf, code_root, graph_nodes, toks)
    if scope["unresolved"]:
        return scope, ("scope entries this gate cannot resolve to a path: %s"
                       % ", ".join("`%s`" % u for u in scope["unresolved"]))
    if not scope["files"]:
        return scope, "no scope"
    return scope, ""


# ---------------------------------------------------------------- the three clauses

def _witness_overlap(a, b):
    """First shared file between two scopes, or None. Deterministic: sorted, first hit.

    Two WILDCARD patterns are treated as overlapping when they share a directory prefix, even
    though neither literally matches the other. `a/*.py` and `a/test_*.py` name intersecting
    sets that no literal match will reveal, and an ambiguity resolved permissively is the one
    thing this gate must not do.
    """
    shared = sorted(a["files"] & b["files"])
    if shared:
        return shared[0]
    for pat in sorted(a["patterns"]):
        for f in sorted(b["files"]):
            if fnmatch.fnmatch(f, pat):
                return "%s (matches `%s`)" % (f, pat)
    for pat in sorted(b["patterns"]):
        for f in sorted(a["files"]):
            if fnmatch.fnmatch(f, pat):
                return "%s (matches `%s`)" % (f, pat)
    for pa in sorted(a["patterns"]):
        for pb in sorted(b["patterns"]):
            if os.path.dirname(pa) == os.path.dirname(pb):
                return "`%s` and `%s` can name the same files" % (pa, pb)
    return None


def _witness_adjacency(a, b, nbr):
    """First 1-hop link from a file in `a` to a file in `b`, or None."""
    for f in sorted(a["files"]):
        for n in sorted(nbr.get(f, ())):
            if n in b["files"]:
                return "%s -> %s" % (f, n)
            for pat in sorted(b["patterns"]):
                if fnmatch.fnmatch(n, pat):
                    return "%s -> %s (matches `%s`)" % (f, n, pat)
    return None


def dependency_reasons(wf, row):
    """Clause 1. A dependency is finished only on its item dir's `promoted.json` marker."""
    out = []
    for bad in row.get("unparsed_deps", []):
        out.append({"clause": DEPENDENCY, "against": None,
                    "detail": "dependency `%s` is prose this gate cannot resolve to an item id"
                              % bad})
    for dep in row.get("deps", []):
        marker = _read_json(os.path.join(wf, ".workflow", "items", dep, "promoted.json"))
        if isinstance(marker, dict) and marker.get("promoted"):
            continue
        if os.path.isdir(os.path.join(wf, ".workflow", "items", dep)):
            out.append({"clause": DEPENDENCY, "against": dep,
                        "detail": "dependency `%s` is not finished (no promoted marker)" % dep})
        else:
            out.append({"clause": DEPENDENCY, "against": dep,
                        "detail": "dependency `%s` cannot be located -- no item dir, so "
                                  "nothing shows it finished" % dep})
    return out


# ---------------------------------------------------------------- held work

def held(wf, code_root, graph_nodes):
    """-> `{in_flight, parked, scopes, without_scope, blocked}`.

    Work already dispatched constrains the batch without being in it. An id with an item dir is
    a writer and its scope must be readable; if it is not, nothing can be proven disjoint from
    it and the caller is told to stay serial outright. An id with no item dir declares no files
    and is reported without blocking -- see the module docstring for why that asymmetry is
    deliberate and where its risk sits.
    """
    res = {"in_flight": [], "parked": [], "scopes": {}, "without_scope": [], "blocked": []}
    state = _read_json(os.path.join(wf, ".workflow", "state.json"), {}) or {}
    cur = state.get("current_item")
    if isinstance(cur, str) and cur.strip():
        res["in_flight"].append(cur.strip())
    pdir = os.path.join(wf, ".workflow", "parked")
    for name in sorted(os.listdir(pdir)) if os.path.isdir(pdir) else []:
        if not name.endswith(".json"):
            continue
        rec = _read_json(os.path.join(pdir, name))
        tid = (rec or {}).get("ticket_id") if isinstance(rec, dict) else None
        tid = tid if isinstance(tid, str) and tid.strip() else os.path.splitext(name)[0]
        if tid not in res["parked"]:
            res["parked"].append(tid.strip())
    for ident in res["in_flight"] + res["parked"]:
        if not os.path.isdir(os.path.join(wf, ".workflow", "items", ident)):
            res["without_scope"].append(ident)
            continue
        scope, why = item_scope(wf, code_root, graph_nodes, ident)
        if why:
            res["blocked"].append("held item `%s`: %s -- nothing can be proven disjoint from "
                                  "a writer whose scope is unknown" % (ident, why))
        else:
            res["scopes"][ident] = scope
    return res


# ---------------------------------------------------------------- the batch

def scan(project_root, candidates=None, max_batch=3):
    wf, code_root, docs_root = roots(project_root)
    nbr, ginfo = load_graph(wf, code_root, docs_root)
    gnodes = ginfo.pop("node_set", set())
    rows, backlog_present = parse_backlog(wf)
    by_id = {r["id"]: r for r in rows}

    hold = held(wf, code_root, gnodes)
    blocked = list(hold["blocked"])
    if not backlog_present:
        blocked.append("no `.workflow/backlog.md` -- dependency readiness cannot be read")
    if not ginfo["present"]:
        blocked.append(ginfo["why"])

    if candidates:
        wanted = list(dict.fromkeys(candidates))
    else:
        # TWO SOURCES, UNIONED, because neither alone is the candidate set. The backlog is the
        # queue but a row is not planned until it is picked, and an item with no plan declares
        # no scope; the item dirs hold the plans but say nothing about order or dependencies.
        # Finished items (the promoted marker) and already-dispatched ones are not candidates.
        busy = set(hold["in_flight"]) | set(hold["parked"])
        idir = os.path.join(wf, ".workflow", "items")
        planned = [n for n in sorted(os.listdir(idir))
                   if os.path.isfile(os.path.join(idir, n, "plan.md"))] \
            if os.path.isdir(idir) else []
        wanted = []
        for ident in [r["id"] for r in rows] + planned:
            if ident in busy or ident in wanted:
                continue
            m = _read_json(os.path.join(idir, ident, "promoted.json"))
            if isinstance(m, dict) and m.get("promoted"):
                continue
            wanted.append(ident)

    # Queue order first, ascending id as the tie-break -- and as the whole ordering for an id
    # the backlog never mentions, which sorts after every row it does.
    wanted.sort(key=lambda i: (by_id[i]["order"] if i in by_id else len(rows) + 1, i))

    considered = []
    for ident in wanted:
        entry = {"id": ident, "eligible": False, "reasons": [], "files": [],
                 "prospective": [], "unresolved": []}
        row = by_id.get(ident)
        if row is None:
            entry["reasons"].append(
                {"clause": DEPENDENCY, "against": None,
                 "detail": "no backlog row for `%s`, so its dependencies are unknown" % ident})
        else:
            entry["reasons"].extend(dependency_reasons(wf, row))
        scope, why = item_scope(wf, code_root, gnodes, ident)
        if why:
            entry["reasons"].append({"clause": SCOPE, "against": None, "detail": why})
        if scope:
            entry["files"] = sorted(scope["files"])
            entry["prospective"] = sorted(scope["prospective"])
            entry["unresolved"] = list(scope["unresolved"])
        if not ginfo["present"]:
            entry["reasons"].append({"clause": GRAPH, "against": None, "detail": ginfo["why"]})
        entry["_scope"] = scope if not why else None
        considered.append(entry)

    # Items already in flight are concurrent writers and count against the ceiling; parked
    # items hold a worktree but no worker, so they constrain disjointness and not the count.
    slots = max(0, int(max_batch) - len(hold["in_flight"]))

    batch, members = [], dict(hold["scopes"])
    for entry in considered:
        if blocked:
            # Not a silent skip: a caller must be able to see WHY nothing was admitted, and
            # "a writer with an unknown scope is already out there" is a different remedy from
            # "this candidate collides with that one".
            for b in blocked:
                entry["reasons"].append({"clause": HELD, "against": None, "detail": b})
            continue
        if entry["reasons"] or entry["_scope"] is None:
            continue
        if len(batch) >= slots:
            entry["reasons"].append(
                {"clause": CAPACITY, "against": None,
                 "detail": "the concurrency ceiling (%d) is already taken" % max_batch})
            continue
        mine, clash = entry["_scope"], False
        for other in sorted(members):
            w = _witness_overlap(mine, members[other])
            if w:
                entry["reasons"].append({"clause": OVERLAP, "against": other,
                                         "detail": "both declare %s" % w})
                clash = True
            w = _witness_adjacency(mine, members[other], nbr) \
                or _witness_adjacency(members[other], mine, nbr)
            if w:
                entry["reasons"].append(
                    {"clause": ADJACENCY, "against": other,
                     "detail": "one code-map edge apart: %s" % w})
                clash = True
        if clash:
            continue
        entry["eligible"] = True
        members[entry["id"]] = mine
        batch.append(entry["id"])

    for entry in considered:
        entry.pop("_scope", None)
    return {"batch": batch,
            "fan_out": len(batch) > 1,
            "candidates": considered,
            "held": {k: v for k, v in hold.items() if k != "scopes"},
            "held_files": {k: sorted(v["files"]) for k, v in hold["scopes"].items()},
            "blocked": blocked,
            "code_map": ginfo,
            "max_batch": int(max_batch),
            "slots": slots}


def render(res):
    lines = []
    if res["fan_out"]:
        lines.append("FAN-OUT: %d item(s) proven independent -- %s"
                     % (len(res["batch"]), ", ".join(res["batch"])))
    else:
        # The single eligible item is still worth naming: "serial" is an instruction to
        # dispatch ONE thing, and the reader should not have to re-derive which.
        lines.append("SERIAL: no batch of two could be proven independent (%d candidate(s) "
                     "considered)%s"
                     % (len(res["candidates"]),
                        ("; `%s` may go alone" % res["batch"][0]) if res["batch"] else ""))
    for b in res["blocked"]:
        lines.append("  BLOCKED: %s" % b)
    if res["held"]["in_flight"]:
        lines.append("  in flight: %s" % ", ".join(res["held"]["in_flight"]))
    if res["held"]["parked"]:
        lines.append("  parked: %s" % ", ".join(res["held"]["parked"]))
    if res["held"]["without_scope"]:
        lines.append("  held but declaring no files (no item dir, so no plan to read): %s"
                     % ", ".join(res["held"]["without_scope"]))
    shown = 0
    for c in res["candidates"]:
        if c["eligible"]:
            extra = (" [%d file(s) not yet on disk: adjacency for those is unknowable]"
                     % len(c["prospective"])) if c["prospective"] else ""
            lines.append("  OK   %s -- %d file(s)%s" % (c["id"], len(c["files"]), extra))
            continue
        if shown >= 20:
            continue
        shown += 1
        lines.append("  HOLD %s" % c["id"])
        for r in c["reasons"]:
            lines.append("       %s%s: %s"
                         % (r["clause"],
                            (" vs %s" % r["against"]) if r["against"] else "",
                            r["detail"]))
    held_back = sum(1 for c in res["candidates"] if not c["eligible"])
    if held_back > shown:
        lines.append("  ... and %d more held serial (--json for all)" % (held_back - shown))
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="what may legally be dispatched in the same turn")
    ap.add_argument("candidates", nargs="*",
                    help="item ids to test (default: the open backlog)")
    ap.add_argument("--project-root", default=".")
    ap.add_argument("--max", type=int, default=3, dest="max_batch",
                    help="ceiling on concurrent workers, in-flight included (default 3)")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    res = scan(os.path.abspath(args.project_root), args.candidates, args.max_batch)
    print(json.dumps(res, indent=2, sort_keys=True) if args.json else render(res))
    return 0 if res["fan_out"] else 1


if __name__ == "__main__":
    sys.exit(main())

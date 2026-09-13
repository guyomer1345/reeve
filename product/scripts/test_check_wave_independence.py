"""Tests for check_wave_independence.py — the fan-out gate.

What these pin down is the FAILURE DIRECTION, not the arithmetic. Any competent version of
this script will notice two items naming the same file; the thing worth protecting with tests
is that a *missing* plan, a *missing* code map, an unparseable scope entry and an unlocatable
dependency all come out as "runs serially" rather than as "nothing objected, so go". Every one
of those is a case where the permissive answer looks identical to the correct one right up to
the moment two workers write the same file, so each gets its own test.

Also pinned: that clause 3 REJECTS rather than flags. An earlier design let a 1-hop neighbour
start with heavier integration checking, which only makes sense if the neighbour is working
later; a same-turn dispatch makes it a concurrent writer, and the test asserts it never reaches
the batch.
"""
import json
import os
import subprocess
import sys

import pytest

import check_wave_independence as wi

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "check_wave_independence.py")


# ---------------------------------------------------------------- fixtures

def _project(root, project_root=".", rows=(), graph=None, state=None, parked=None):
    """A workflow tree: config, a backlog of `- **id** · deps: …` rows, and a code map.

    `rows` is a list of `(id, deps)`; `deps` is the raw text of the `deps:` field, so a test can
    hand it prose as easily as ids. `graph=None` writes NO code map — the fail-closed case.
    """
    root = str(root)
    os.makedirs(os.path.join(root, ".workflow"), exist_ok=True)
    with open(os.path.join(root, ".workflow", "config.json"), "w") as fh:
        json.dump({"project_root": project_root}, fh)
    lines = ["# Backlog", "", "## Open", ""]
    for ident, deps in rows:
        lines.append("- **%s** · kind: feature · severity: medium · deps: %s" % (ident, deps))
    with open(os.path.join(root, ".workflow", "backlog.md"), "w") as fh:
        fh.write("\n".join(lines) + "\n")
    if graph is not None:
        gdir = os.path.join(root, project_root, "docs", "knowledge")
        os.makedirs(gdir, exist_ok=True)
        with open(os.path.join(gdir, "graph.json"), "w") as fh:
            json.dump(graph, fh)
    if state is not None:
        with open(os.path.join(root, ".workflow", "state.json"), "w") as fh:
            json.dump(state, fh)
    for name, rec in (parked or {}).items():
        pdir = os.path.join(root, ".workflow", "parked")
        os.makedirs(pdir, exist_ok=True)
        with open(os.path.join(pdir, name + ".json"), "w") as fh:
            json.dump(rec, fh)
    return root


def _graph(nodes, edges=()):
    return {"root": ".", "nodes": [{"path": n} for n in nodes],
            "edges": [{"from": a, "to": b, "kind": "import"} for a, b in edges]}


def _code(root, *rels, project_root="."):
    """Real files on disk, so a declared path resolves to something."""
    for rel in rels:
        path = os.path.join(str(root), project_root, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as fh:
            fh.write("x\n")


def _plan(root, item, body=None, files=(), table=False):
    """An item's plan. `table` writes the `|`-table spelling, otherwise the bullet spelling —
    both are real and the parser must read each."""
    d = os.path.join(str(root), ".workflow", "items", item)
    os.makedirs(d, exist_ok=True)
    if body is None:
        if table:
            rows = ["## Files touched", "", "| path | why |", "|---|---|"]
            rows += ["| `%s` | because |" % f for f in files]
        else:
            rows = ["## files_touched"]
            rows += ["- `%s` — because" % f for f in files]
        body = "# Plan — %s\n\n## Goal\ndo it\n\n%s\n\n## Steps\n1. go\n" % (
            item, "\n".join(rows))
    with open(os.path.join(d, "plan.md"), "w") as fh:
        fh.write(body)


def _done(root, item):
    """The one marker that means finished — the same one the item-dir prune keys off."""
    d = os.path.join(str(root), ".workflow", "items", item)
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "promoted.json"), "w") as fh:
        json.dump({"promoted": True}, fh)


def _reasons(res, ident):
    for c in res["candidates"]:
        if c["id"] == ident:
            return c["reasons"]
    raise AssertionError("%s was not even considered" % ident)


def _clauses(res, ident):
    return {r["clause"] for r in _reasons(res, ident)}


# ---------------------------------------------------------------- the clean case

def _clean(tmp_path, n=3):
    rows = [("item-%d" % i, "none") for i in range(1, n + 1)]
    root = _project(tmp_path, rows=rows,
                    graph=_graph(["src/a%d.py" % i for i in range(1, n + 1)]))
    for i in range(1, n + 1):
        _code(root, "src/a%d.py" % i)
        _plan(root, "item-%d" % i, files=["src/a%d.py" % i])
    return root


def test_three_independent_items_fan_out(tmp_path):
    """The capability itself: three items, disjoint files, no edges between them, no
    dependencies — all three may be dispatched in one turn."""
    res = wi.scan(_clean(tmp_path))
    assert res["blocked"] == []
    assert res["batch"] == ["item-1", "item-2", "item-3"]
    assert res["fan_out"] is True


def test_the_table_spelling_of_the_scope_section_reads_the_same(tmp_path):
    """Real plans in one repo use both a `|`-table and a bullet list. A parser that knows one
    scores the other as declaring nothing, which fails closed for the wrong reason."""
    root = _project(tmp_path, rows=[("a", "none"), ("b", "none")],
                    graph=_graph(["src/a.py", "src/b.py"]))
    _code(root, "src/a.py", "src/b.py")
    _plan(root, "a", files=["src/a.py"], table=True)
    _plan(root, "b", files=["src/b.py"], table=False)
    assert wi.scan(root)["batch"] == ["a", "b"]


def test_the_queue_order_is_the_batch_order_and_ties_break_on_id(tmp_path):
    """Backlog order is the queue's order and this gate does not re-order it. An id the
    backlog never mentions sorts after every row that it does."""
    root = _project(tmp_path, rows=[("zeta", "none"), ("alpha", "none")],
                    graph=_graph(["src/z.py", "src/a.py"]))
    _code(root, "src/z.py", "src/a.py")
    _plan(root, "zeta", files=["src/z.py"])
    _plan(root, "alpha", files=["src/a.py"])
    assert wi.scan(root)["batch"] == ["zeta", "alpha"]


# ---------------------------------------------------------------- clause 1

def test_a_dependency_that_is_not_finished_excludes_the_candidate(tmp_path):
    root = _clean(tmp_path)
    with open(os.path.join(root, ".workflow", "backlog.md"), "a") as fh:
        fh.write("- **item-4** · deps: item-1\n")
    _code(root, "src/a4.py")
    _plan(root, "item-4", files=["src/a4.py"])
    res = wi.scan(root, max_batch=9)
    assert "item-4" not in res["batch"]
    assert _clauses(res, "item-4") == {wi.DEPENDENCY}
    assert "item-1" in _reasons(res, "item-4")[0]["detail"]


def test_a_finished_dependency_is_one_carrying_the_promoted_marker(tmp_path):
    """Doneness has exactly one owner. Note what is NOT consulted: the backlog row's own
    prose. A row that merely reads as closed would make its dependents look ready, and that
    is a mistake in the permissive direction."""
    root = _project(tmp_path, rows=[("dep", "none"), ("b", "dep")],
                    graph=_graph(["src/d.py", "src/b.py"]))
    _code(root, "src/d.py", "src/b.py")
    _plan(root, "dep", files=["src/d.py"])
    _plan(root, "b", files=["src/b.py"])
    assert wi.DEPENDENCY in _clauses(wi.scan(root), "b")
    _done(root, "dep")
    assert wi.DEPENDENCY not in _clauses(wi.scan(root), "b")


def test_a_dependency_with_no_item_dir_is_unknown_not_finished(tmp_path):
    """The hard one to get right. A dependency nobody can locate is indistinguishable from a
    typo, and reading it as "must have been finished" dispatches a worker onto unready
    ground."""
    root = _project(tmp_path, rows=[("b", "ghost-item")], graph=_graph(["src/b.py"]))
    _code(root, "src/b.py")
    _plan(root, "b", files=["src/b.py"])
    res = wi.scan(root)
    assert res["batch"] == []
    assert "cannot be located" in _reasons(res, "b")[0]["detail"]


def test_a_prose_dependency_field_is_not_settled_by_ignoring_it(tmp_path):
    """Real queues write `deps: OBS + a clean audit path`. That is a genuine dependency
    statement no parser here can settle; skipping it silently is the permissive failure."""
    root = _project(tmp_path, rows=[("b", "OBS and a clean audit path")],
                    graph=_graph(["src/b.py"]))
    _code(root, "src/b.py")
    _plan(root, "b", files=["src/b.py"])
    res = wi.scan(root)
    assert res["batch"] == []
    assert any("prose" in r["detail"] for r in _reasons(res, "b"))


def test_deps_none_means_no_dependencies(tmp_path):
    root = _project(tmp_path, rows=[("a", "none"), ("b", "—")], graph=_graph(["src/a.py"]))
    _code(root, "src/a.py", "src/b.py")
    _plan(root, "a", files=["src/a.py"])
    _plan(root, "b", files=["src/b.py"])
    res = wi.scan(root)
    assert res["batch"] == ["a", "b"]


def test_a_candidate_with_no_backlog_row_has_unknown_dependencies(tmp_path):
    """An explicit candidate list may name something the queue does not. Its plan may be
    perfect and it is still held: nothing says what it is waiting on."""
    root = _clean(tmp_path)
    _code(root, "src/loose.py")
    _plan(root, "loose", files=["src/loose.py"])
    res = wi.scan(root, ["item-1", "loose"])
    assert res["batch"] == ["item-1"] and res["fan_out"] is False
    assert "dependencies are unknown" in _reasons(res, "loose")[0]["detail"]


# ---------------------------------------------------------------- clause 2

def test_two_candidates_sharing_a_file_come_down_to_one(tmp_path):
    root = _project(tmp_path, rows=[("a", "none"), ("b", "none"), ("c", "none")],
                    graph=_graph(["src/shared.py", "src/c.py"]))
    _code(root, "src/shared.py", "src/c.py")
    _plan(root, "a", files=["src/shared.py"])
    _plan(root, "b", files=["src/shared.py"])
    _plan(root, "c", files=["src/c.py"])
    res = wi.scan(root)
    assert res["batch"] == ["a", "c"], "the queue head wins; the later claimant waits"
    assert _clauses(res, "b") == {wi.OVERLAP}
    r = _reasons(res, "b")[0]
    assert r["against"] == "a" and "src/shared.py" in r["detail"], \
        "a rejection nobody can act on is useless: name the clause AND the counterparty"


def test_a_directory_scope_collides_with_a_file_inside_it(tmp_path):
    root = _project(tmp_path, rows=[("a", "none"), ("b", "none")],
                    graph=_graph(["src/pkg/x.py"]))
    _code(root, "src/pkg/x.py")
    _plan(root, "a", files=["src/pkg/"])
    _plan(root, "b", files=["src/pkg/x.py"])
    res = wi.scan(root)
    assert res["batch"] == ["a"]
    assert _clauses(res, "b") == {wi.OVERLAP}


def test_two_wildcards_that_could_name_the_same_files_collide(tmp_path):
    """`src/*.py` and `src/test_*.py` intersect, and no literal match reveals it. An
    ambiguity resolved permissively is the one thing this gate must not do."""
    root = _project(tmp_path, rows=[("a", "none"), ("b", "none")],
                    graph=_graph(["src/one.py", "src/test_one.py"]))
    _code(root, "src/one.py", "src/test_one.py")
    _plan(root, "a", files=["src/*.py"])
    _plan(root, "b", files=["src/test_*.py"])
    res = wi.scan(root)
    assert res["batch"] == ["a"]
    assert _clauses(res, "b") == {wi.OVERLAP}


# ---------------------------------------------------------------- clause 3

def test_a_one_hop_neighbour_is_rejected_not_flagged(tmp_path):
    """The reversal this gate exists to hold. The two items touch disjoint files, so clause 2
    is clean — and they are one import apart, so they are one change. An earlier design
    started the second item FLAGGED for heavier integration checking; that only makes sense
    when the neighbour lands later, and a same-turn dispatch makes it a concurrent writer.
    The batch must be one item, and the reason must name the adjacency clause and the file
    pair."""
    root = _project(tmp_path, rows=[("a", "none"), ("b", "none")],
                    graph=_graph(["src/a.py", "src/b.py"], [("src/b.py", "src/a.py")]))
    _code(root, "src/a.py", "src/b.py")
    _plan(root, "a", files=["src/a.py"])
    _plan(root, "b", files=["src/b.py"])
    res = wi.scan(root)
    assert res["batch"] == ["a"]
    assert res["fan_out"] is False
    r, = _reasons(res, "b")
    assert r["clause"] == wi.ADJACENCY and r["against"] == "a"
    assert "src/a.py" in r["detail"] and "src/b.py" in r["detail"]
    assert not any(c["eligible"] and c["id"] == "b" for c in res["candidates"]), \
        "there is no flagged-start path: the soft gate reports, it never admits"


def test_adjacency_is_undirected(tmp_path):
    """For "are these one change?", A importing B and B importing A are the same answer."""
    root = _project(tmp_path, rows=[("a", "none"), ("b", "none")],
                    graph=_graph(["src/a.py", "src/b.py"], [("src/a.py", "src/b.py")]))
    _code(root, "src/a.py", "src/b.py")
    _plan(root, "a", files=["src/a.py"])
    _plan(root, "b", files=["src/b.py"])
    assert wi.scan(root)["batch"] == ["a"]


def test_two_hops_apart_is_not_a_neighbour(tmp_path):
    """The predicate says ONE hop. A gate that walked the whole transitive closure would
    reject every pair in a connected codebase, which is a gate nobody can use."""
    root = _project(tmp_path, rows=[("a", "none"), ("b", "none")],
                    graph=_graph(["src/a.py", "src/mid.py", "src/b.py"],
                                 [("src/a.py", "src/mid.py"), ("src/mid.py", "src/b.py")]))
    _code(root, "src/a.py", "src/mid.py", "src/b.py")
    _plan(root, "a", files=["src/a.py"])
    _plan(root, "b", files=["src/b.py"])
    assert wi.scan(root)["batch"] == ["a", "b"]


# ---------------------------------------------------------------- fail-closed paths

def test_no_plan_means_serial(tmp_path):
    root = _clean(tmp_path)
    with open(os.path.join(root, ".workflow", "backlog.md"), "a") as fh:
        fh.write("- **unplanned** · deps: none\n")
    res = wi.scan(root, ["item-1", "unplanned"])
    assert "unplanned" not in res["batch"] and res["fan_out"] is False
    assert _clauses(res, "unplanned") == {wi.SCOPE}
    assert _reasons(res, "unplanned")[0]["detail"] == "no plan"


def test_a_plan_with_no_files_touched_section_means_serial(tmp_path):
    root = _clean(tmp_path)
    with open(os.path.join(root, ".workflow", "backlog.md"), "a") as fh:
        fh.write("- **scopeless** · deps: none\n")
    _plan(root, "scopeless", body="# Plan\n\n## Goal\ndo it\n\n## Steps\n1. go\n")
    res = wi.scan(root, ["item-1", "scopeless"])
    assert "scopeless" not in res["batch"] and res["fan_out"] is False
    assert _reasons(res, "scopeless")[0]["detail"] == "no scope"


def test_a_files_touched_section_that_names_no_paths_means_serial(tmp_path):
    """A section that is all prose declares nothing, and declaring nothing is not the same as
    declaring disjointness."""
    root = _clean(tmp_path)
    with open(os.path.join(root, ".workflow", "backlog.md"), "a") as fh:
        fh.write("- **prosey** · deps: none\n")
    _plan(root, "prosey", body="# Plan\n\n## Files touched\n\nwhatever is needed\n\n## Steps\n")
    res = wi.scan(root, ["item-1", "prosey"])
    assert "prosey" not in res["batch"] and res["fan_out"] is False
    assert _reasons(res, "prosey")[0]["detail"] == "no scope"


def test_an_unresolvable_scope_entry_means_serial(tmp_path):
    """Real plans put symbol names and shell fragments in the path column. A scope declaration
    that cannot be read completely has not been read at all — the entry that was skipped is
    exactly the one another worker might also be writing."""
    root = _clean(tmp_path)
    with open(os.path.join(root, ".workflow", "backlog.md"), "a") as fh:
        fh.write("- **fuzzy** · deps: none\n")
    _code(root, "src/real.py")
    _plan(root, "fuzzy", files=["src/real.py", "ExplorerContext", "git add -A"])
    res = wi.scan(root, ["item-1", "fuzzy"])
    assert "fuzzy" not in res["batch"] and res["fan_out"] is False
    detail = _reasons(res, "fuzzy")[0]["detail"]
    assert "ExplorerContext" in detail and "git add -A" in detail
    assert _clauses(res, "fuzzy") == {wi.SCOPE}


def test_no_code_map_means_serial_for_everything(tmp_path):
    """Without the map, clause 3 is not merely unknown — it is unaskable. Two items with
    perfectly disjoint files could still be a single change, and nothing here can tell."""
    root = _project(tmp_path, rows=[("a", "none"), ("b", "none")], graph=None)
    _code(root, "src/a.py", "src/b.py")
    _plan(root, "a", files=["src/a.py"])
    _plan(root, "b", files=["src/b.py"])
    res = wi.scan(root)
    assert res["batch"] == []
    assert res["code_map"]["present"] is False
    assert any("code map" in b for b in res["blocked"])
    assert wi.GRAPH in _clauses(res, "a") and wi.GRAPH in _clauses(res, "b"), \
        "each candidate carries the reason; a blocker only in the header is one a caller misses"


def test_an_unparseable_code_map_is_the_same_as_a_missing_one(tmp_path):
    root = _project(tmp_path, rows=[("a", "none"), ("b", "none")], graph=_graph([]))
    gpath = os.path.join(root, "docs", "knowledge", "graph.json")
    with open(gpath, "w") as fh:
        fh.write("{ this is not json")
    _code(root, "src/a.py", "src/b.py")
    _plan(root, "a", files=["src/a.py"])
    _plan(root, "b", files=["src/b.py"])
    res = wi.scan(root)
    assert res["batch"] == [] and res["code_map"]["present"] is False


def test_a_missing_backlog_blocks_the_whole_batch(tmp_path):
    root = _clean(tmp_path)
    os.remove(os.path.join(root, ".workflow", "backlog.md"))
    res = wi.scan(root, ["item-1", "item-2"])
    assert res["batch"] == []
    assert any("backlog" in b for b in res["blocked"])


# ---------------------------------------------------------------- held work

def test_an_in_flight_items_files_are_respected(tmp_path):
    root = _project(tmp_path, rows=[("a", "none"), ("b", "none")],
                    graph=_graph(["src/a.py", "src/b.py"]),
                    state={"current_item": "flying"})
    _code(root, "src/a.py", "src/b.py")
    _plan(root, "a", files=["src/a.py"])
    _plan(root, "b", files=["src/b.py"])
    _plan(root, "flying", files=["src/a.py"])
    res = wi.scan(root)
    assert res["held"]["in_flight"] == ["flying"]
    assert res["batch"] == ["b"], "the in-flight writer owns src/a.py, so `a` waits"
    assert _reasons(res, "a")[0]["against"] == "flying"


def test_a_parked_items_files_are_respected(tmp_path):
    root = _project(tmp_path, rows=[("a", "none"), ("b", "none")],
                    graph=_graph(["src/a.py", "src/b.py"]),
                    parked={"held": {"ticket_id": "held"}})
    _code(root, "src/a.py", "src/b.py")
    _plan(root, "a", files=["src/a.py"])
    _plan(root, "b", files=["src/b.py"])
    _plan(root, "held", files=["src/b.py"])
    res = wi.scan(root)
    assert res["held"]["parked"] == ["held"]
    assert res["batch"] == ["a"]
    assert _reasons(res, "b")[0]["against"] == "held"


def test_a_parked_item_is_a_neighbour_too(tmp_path):
    """Clause 3 runs against held work, not just against other batch members: a parked
    worktree holds edits that a neighbouring file's author would be writing against."""
    root = _project(tmp_path, rows=[("a", "none")],
                    graph=_graph(["src/a.py", "src/h.py"], [("src/h.py", "src/a.py")]),
                    parked={"held": {"ticket_id": "held"}})
    _code(root, "src/a.py", "src/h.py")
    _plan(root, "a", files=["src/a.py"])
    _plan(root, "held", files=["src/h.py"])
    res = wi.scan(root)
    assert res["batch"] == []
    assert _clauses(res, "a") == {wi.ADJACENCY}


def test_a_held_item_whose_plan_cannot_be_read_refuses_the_whole_batch(tmp_path):
    """It has an item dir, so it is a writer; its scope is unreadable, so nothing can be proven
    disjoint from it. Refusing everything is the only honest answer."""
    root = _clean(tmp_path)
    os.makedirs(os.path.join(root, ".workflow", "items", "mystery"), exist_ok=True)
    with open(os.path.join(root, ".workflow", "state.json"), "w") as fh:
        json.dump({"current_item": "mystery"}, fh)
    res = wi.scan(root)
    assert res["batch"] == []
    assert any("mystery" in b for b in res["blocked"])
    assert wi.HELD in _clauses(res, "item-1")


def test_a_parked_ticket_with_no_item_dir_declares_no_files_and_says_so(tmp_path):
    """The one place the burden is not on the held side, and it is deliberate. A checkpoint
    waiting on a human has no item dir and therefore no plan to be missing — it is a request,
    not a writer. It is REPORTED so a reader can see the assumption, and it does not block."""
    root = _clean(tmp_path)
    pdir = os.path.join(root, ".workflow", "parked")
    os.makedirs(pdir, exist_ok=True)
    with open(os.path.join(pdir, "CHK-ask.json"), "w") as fh:
        json.dump({"ticket_id": "CHK-ask", "checkpoint": {"kind": "demo"}}, fh)
    res = wi.scan(root)
    assert res["held"]["without_scope"] == ["CHK-ask"]
    assert res["blocked"] == []
    assert res["batch"] == ["item-1", "item-2", "item-3"]
    assert "declaring no files" in wi.render(res)


def test_held_work_is_not_offered_as_a_candidate(tmp_path):
    root = _clean(tmp_path)
    with open(os.path.join(root, ".workflow", "state.json"), "w") as fh:
        json.dump({"current_item": "item-1"}, fh)
    res = wi.scan(root)
    assert "item-1" not in [c["id"] for c in res["candidates"]]


# ---------------------------------------------------------------- bounds and determinism

def test_the_concurrency_ceiling_caps_the_batch_and_says_why(tmp_path):
    root = _clean(tmp_path, n=4)
    res = wi.scan(root, max_batch=2)
    assert res["batch"] == ["item-1", "item-2"]
    assert {r["clause"] for r in _reasons(res, "item-3")} == {wi.CAPACITY}


def test_in_flight_work_counts_against_the_ceiling(tmp_path):
    """A worker already out there is a concurrent writer, so it spends a slot. A parked item
    holds a worktree but no worker, so it does not."""
    root = _clean(tmp_path, n=3)
    _code(root, "src/flying.py")
    _plan(root, "flying", files=["src/flying.py"])
    with open(os.path.join(root, ".workflow", "state.json"), "w") as fh:
        json.dump({"current_item": "flying"}, fh)
    res = wi.scan(root, max_batch=3)
    assert res["slots"] == 2
    assert res["batch"] == ["item-1", "item-2"]


def test_the_same_inputs_always_yield_the_same_batch(tmp_path):
    """A wave that cannot be reproduced cannot be reviewed. Nothing in the selection may
    depend on set iteration order or on filesystem listing order."""
    root = _clean(tmp_path, n=4)
    _code(root, "src/dup.py")
    _plan(root, "item-4", files=["src/dup.py", "src/a1.py"])   # collides with item-1
    first = wi.scan(root, max_batch=9)
    second = wi.scan(root, max_batch=9)
    assert first["batch"] == second["batch"] == ["item-1", "item-2", "item-3"]
    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)


def test_a_prospective_new_file_is_scope_but_its_adjacency_is_unknowable(tmp_path):
    """A file the plan will create has no code-map neighbours — legitimately, since nothing can
    import a file that does not exist. What no map can answer is whether it will END UP coupled
    to another member's work, so the report names it instead of implying the graph settled it."""
    root = _project(tmp_path, rows=[("a", "none")], graph=_graph(["src/a.py"]))
    _code(root, "src/a.py")
    _plan(root, "a", files=["src/a.py", "src/brand_new.py"])
    res = wi.scan(root)
    c, = [c for c in res["candidates"] if c["id"] == "a"]
    assert c["eligible"] is True
    assert c["prospective"] == ["src/brand_new.py"]
    assert "not yet on disk" in wi.render(res)


def test_a_nested_code_root_is_honoured(tmp_path):
    """Greenfield puts the product under `./project`, so both the code map and the paths a plan
    spells relative to it must resolve. A relative root spelling joined onto an absolute one is
    the exact shape that double-counted a file in a sibling gate."""
    root = _project(tmp_path, project_root="./project",
                    rows=[("a", "none"), ("b", "none")],
                    graph=_graph(["src/a.py", "src/b.py"], [("src/b.py", "src/a.py")]))
    _code(root, "src/a.py", "src/b.py", project_root="project")
    _plan(root, "a", files=["project/src/a.py"])
    _plan(root, "b", files=["src/b.py"])          # spelled relative to the code root
    res = wi.scan(root)
    assert res["code_map"]["present"] is True
    assert res["batch"] == ["a"], "both spellings must land on the same file for the edge to bite"
    assert _clauses(res, "b") == {wi.ADJACENCY}


# ---------------------------------------------------------------- the CLI contract

def _run(root, *args):
    p = subprocess.run([sys.executable, SCRIPT, "--project-root", str(root)] + list(args),
                       capture_output=True, text=True)
    return p


def test_exit_zero_means_fan_out_and_one_means_serial(tmp_path):
    """Two codes, and the only non-zero one is the conservative answer — so a caller that
    branches on the exit status alone and never reads the report still behaves correctly."""
    assert _run(_clean(tmp_path)).returncode == 0
    root = _project(tmp_path / "solo", rows=[("a", "none")], graph=_graph(["src/a.py"]))
    _code(root, "src/a.py")
    _plan(root, "a", files=["src/a.py"])
    assert _run(root).returncode == 1


def test_a_broken_tree_exits_one_rather_than_crashing(tmp_path):
    """There is deliberately no third code for "something went wrong": a caller that can tell
    an error from a verdict will eventually treat the error as a verdict."""
    p = _run(tmp_path / "nothing-here")
    assert p.returncode == 1
    assert "SERIAL" in p.stdout


def test_json_carries_every_rejection(tmp_path):
    root = _clean(tmp_path)
    p = _run(root, "--json", "--max", "2")
    assert p.returncode == 0
    res = json.loads(p.stdout)
    assert res["batch"] == ["item-1", "item-2"]
    assert [c["id"] for c in res["candidates"]] == ["item-1", "item-2", "item-3"]
    assert res["candidates"][2]["reasons"][0]["clause"] == wi.CAPACITY


def test_explicit_candidates_are_honoured(tmp_path):
    root = _clean(tmp_path, n=3)
    res = wi.scan(root, ["item-3", "item-2"])
    assert [c["id"] for c in res["candidates"]] == ["item-2", "item-3"], \
        "argv order must not change the answer — queue order decides"
    assert res["batch"] == ["item-2", "item-3"]


# ---------------------------------------------------------------- plan freshness (widening)
#
# Under plan-ahead a plan can sit unbuilt while siblings land, so the gate can no longer read a
# declared scope as fact. These pin the seam between the two scripts: the classifier says what
# moved, the gate decides what that costs. The whole point is that an untrustworthy declaration
# is absorbed PESSIMISTICALLY -- so every assertion here is that fan-out got HARDER, never that
# it got easier, and the negative control checks the tests can actually go red.

def _git(root, *args):
    subprocess.run(("git", "-C", str(root)) + args, check=True, capture_output=True, text=True)


def _gitproject(root, **kw):
    """The `_project` tree, but a real repository — freshness is inert without one."""
    root = _project(root, **kw)
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "t@t")
    _git(root, "config", "user.name", "t")
    return root


def _snap(root, msg="c"):
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", msg)
    return subprocess.run(("git", "-C", str(root), "rev-parse", "HEAD"),
                          capture_output=True, text=True).stdout.strip()


def _stamp(root, item, base, count=None):
    """Add the freshness fields to an already-written plan."""
    path = os.path.join(str(root), ".workflow", "items", item, "plan.md")
    with open(path) as fh:
        body = fh.read()
    extra = "- **base_sha** — `%s`\n" % base
    if count is not None:
        extra += "- **refresh_count** — %d\n" % count
    with open(path, "w") as fh:
        fh.write(body.replace("## Goal\n", "## Goal\n" + extra, 1))


def test_a_stale_plan_is_read_at_two_hops_and_loses_the_batch(tmp_path):
    """`b` declares only its own file and would fan out beside `a`. Its plan is stale, and the
    file that moved under it imports `a`'s — so the pessimistic read reaches `a` and `b` is
    held. Nothing about `b`'s declaration changed; only our trust in it did."""
    root = _gitproject(tmp_path, rows=[("a", "none"), ("b", "none")],
                       graph=_graph(["x.py", "m.py", "y.py"],
                                    edges=[("y.py", "m.py"), ("m.py", "x.py")]))
    _code(root, "x.py", "m.py", "y.py")
    _plan(root, "a", files=["x.py"])
    _plan(root, "b", files=["y.py"])
    base = _snap(root)
    _stamp(root, "a", base)
    _stamp(root, "b", base)
    assert wi.scan(str(root), [], 5)["batch"] == ["a", "b"]        # fresh: two hops apart, both go

    _code(root, "y.py")                                            # y.py moves under b's plan
    with open(os.path.join(str(root), "y.py"), "w") as fh:
        fh.write("changed\n")
    _snap(root, "move y")
    res = wi.scan(str(root), [], 5)
    assert res["batch"] == ["a"]
    held = [c for c in res["candidates"] if c["id"] == "b"][0]
    assert held["freshness"] == "suspect"
    assert held["widened"] == ["m.py"]
    assert held["held_by_widening_only"] is True                   # and it says so


def test_the_widening_hold_is_reported_not_silent(tmp_path):
    """Starvation nobody can see is indistinguishable from a busy queue."""
    root = _gitproject(tmp_path, rows=[("a", "none"), ("b", "none")],
                       graph=_graph(["x.py", "m.py", "y.py"],
                                    edges=[("y.py", "m.py"), ("m.py", "x.py")]))
    _code(root, "x.py", "m.py", "y.py")
    _plan(root, "a", files=["x.py"])
    _plan(root, "b", files=["y.py"])
    base = _snap(root)
    _stamp(root, "a", base)
    _stamp(root, "b", base)
    with open(os.path.join(str(root), "y.py"), "w") as fh:
        fh.write("changed\n")
    _snap(root, "move y")
    out = wi.render(wi.scan(str(root), [], 5))
    assert "held ONLY by pessimistic widening" in out


def test_widening_never_admits_a_pair_a_bare_read_rejects(tmp_path):
    """The direction that matters. Two items on the same file must stay serial no matter how
    stale either plan is — widening is allowed to hold, never to release."""
    root = _gitproject(tmp_path, rows=[("a", "none"), ("b", "none")],
                       graph=_graph(["x.py"]))
    _code(root, "x.py")
    _plan(root, "a", files=["x.py"])
    _plan(root, "b", files=["x.py"])
    base = _snap(root)
    _stamp(root, "a", base)
    _stamp(root, "b", base)
    with open(os.path.join(str(root), "x.py"), "w") as fh:
        fh.write("changed\n")
    _snap(root, "move x")
    assert wi.scan(str(root), [], 5)["fan_out"] is False


def test_a_replan_verdict_holds_the_item_and_names_the_remedy(tmp_path):
    """A plan past the refresh cap is not refreshable, so the gate must not spend a worker on
    it — and must say *re-plan*, since "not eligible" is unactionable."""
    root = _gitproject(tmp_path, rows=[("a", "none"), ("b", "none")],
                       graph=_graph(["x.py", "y.py"]))
    _code(root, "x.py", "y.py")
    _plan(root, "a", files=["x.py"])
    _plan(root, "b", files=["y.py"])
    base = _snap(root)
    _stamp(root, "a", base)
    _stamp(root, "b", base, count=2)
    res = wi.scan(str(root), [], 5)
    assert res["batch"] == ["a"]
    held = [c for c in res["candidates"] if c["id"] == "b"][0]
    assert held["freshness"] == "replan"
    assert any("RE-PLANNED" in r["detail"] for r in held["reasons"])


def test_a_plan_with_no_base_sha_cannot_be_dispatched_in_a_repo(tmp_path):
    """The migration case, and it must fail towards work rather than towards trust."""
    root = _gitproject(tmp_path, rows=[("a", "none")], graph=_graph(["x.py"]))
    _code(root, "x.py")
    _plan(root, "a", files=["x.py"])
    _snap(root)
    res = wi.scan(str(root), [], 5)
    assert res["batch"] == []
    assert [c for c in res["candidates"] if c["id"] == "a"][0]["freshness"] == "replan"


def test_the_selected_batch_names_what_must_be_refreshed_first(tmp_path):
    """Order B: choose the wave pessimistically, then refresh only what it means to spend."""
    root = _gitproject(tmp_path, rows=[("a", "none"), ("b", "none")],
                       graph=_graph(["x.py", "y.py"]))
    _code(root, "x.py", "y.py")
    _plan(root, "a", files=["x.py"])
    _plan(root, "b", files=["y.py"])
    base = _snap(root)
    _stamp(root, "a", base)
    _stamp(root, "b", base)
    with open(os.path.join(str(root), "y.py"), "w") as fh:
        fh.write("changed\n")
    _snap(root, "move y")
    res = wi.scan(str(root), [], 5)
    assert res["batch"] == ["a", "b"]            # no shared neighbourhood, so both still fit
    assert "REFRESH FIRST" in wi.render(res)
    # And it is flagged even though widening added nothing: the trigger is the verdict, not
    # its blast radius. A suspect declaration is untrustworthy whether or not it has neighbours.
    assert [c for c in res["candidates"] if c["id"] == "b"][0]["widened"] == []


def test_neutering_the_freshness_read_reddens_the_widening_test(tmp_path, monkeypatch):
    """Negative control. A green test that cannot go red is not evidence: if the gate stopped
    consulting freshness, the stale item would sail into the batch — so make it stop, and check
    that it does."""
    root = _gitproject(tmp_path, rows=[("a", "none"), ("b", "none")],
                       graph=_graph(["x.py", "m.py", "y.py"],
                                    edges=[("y.py", "m.py"), ("m.py", "x.py")]))
    _code(root, "x.py", "m.py", "y.py")
    _plan(root, "a", files=["x.py"])
    _plan(root, "b", files=["y.py"])
    base = _snap(root)
    _stamp(root, "a", base)
    _stamp(root, "b", base)
    with open(os.path.join(str(root), "y.py"), "w") as fh:
        fh.write("changed\n")
    _snap(root, "move y")
    assert wi.scan(str(root), [], 5)["batch"] == ["a"]

    import plan_freshness
    monkeypatch.setattr(plan_freshness, "classify",
                        lambda wf, item, cap=None: {"id": item, "state": plan_freshness.FRESH,
                                                    "moved": [], "why": ""})
    assert wi.scan(str(root), [], 5)["batch"] == ["a", "b"]


def test_execute_max_comes_from_config(tmp_path):
    root = str(tmp_path)
    os.makedirs(os.path.join(root, ".workflow"))
    with open(os.path.join(root, ".workflow", "config.json"), "w") as fh:
        json.dump({"project_root": ".", "run": {"wave": {"execute_max": 9}}}, fh)
    assert wi.execute_max(root) == 9
    with open(os.path.join(root, ".workflow", "config.json"), "w") as fh:
        json.dump({"project_root": "."}, fh)
    assert wi.execute_max(root) == wi.DEFAULT_EXECUTE_MAX == 5

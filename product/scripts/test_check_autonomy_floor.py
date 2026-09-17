"""Tests for scripts/check_autonomy_floor.py — the goal-preserving autonomy floor.

What these pin down is the gate's JUDGEMENT, not its arithmetic: that the three firing
conditions fire, that the tier below `locked` does NOT (a floor that routed provisional work
would route everything, and a gate that always fires is a gate a human learns to skip), that
reformatting is not a goal change, that every undetermined answer routes rather than passes,
and — the one that is easy to get wrong twice — that a relative `./project` project_root
resolves to one path with one spelling.

The marker-shape test is built from the forms a REAL spec uses, copied into a fixture rather
than read from the live file: a test that reads someone's working document fails the day they
edit it, and then proves nothing about the parser.
"""
import json
import os
import subprocess
import sys

import pytest

import check_autonomy_floor as af

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "check_autonomy_floor.py")


# ---------------------------------------------------------------- fixtures

# The four marker forms observed in a real, live spec. Every one of them must parse; the
# parser exists for these shapes and not for an idealised one.
REAL_SHAPES = """# Spec — a real project

> The product definition the whole build runs against. Every element carries a `commitment`
> tag: `locked` · `provisional` · `unspecified`.
>
> Derived from the design phase (8 gates A–H, locked 2026-08-06). The full reasoning lives
> elsewhere; this spec is the distillation.

## audience
**Solo operator** — a single hunter who is also the builder. The human is in the loop:
confirms scope and approves every submission. — commitment: `locked`

## screens
Mostly headless. Two thin surfaces:
- **Read-only measurement dashboard** — the scorecard + per-run drill-down (SQL views over
  append-only JSONB step-events; no OpenTelemetry v1). — commitment: `locked` (existence) /
  `provisional` (layout, styling)
- **Operator theming** — colours, density, font size. — commitment: `provisional`

## features
Each `{ name, purpose, acceptance_criteria, commitment }`. Behavior is `locked`; thresholds
tagged `provisional` where numeric.

1. **Deterministic containment** — a single egress choke point enforces a per-request
   allowlist on the observed destination. **Hard gate: zero successful scope escapes.**
   — `locked`
   - **Where the choke route stands today** *(a status note ADDED beside the element above
     and never edited into it; it records what is true, and adds no commitment)*. The
     replayer now has exactly one production call site.
2. **v1 vulnerability triad** — detect BOLA/IDOR, reflected + stored XSS, and SSRF via an
   unforgeable OOB callback token. — `locked` (triad) / business-logic + others
   `unspecified`(deferred)
3. **Rotating holdout refresh** — the holdout set is re-cut each quarter. — `unspecified`

## integrations
- **Model providers** — via the gateway; provider **not locked** (replaceable). — `locked`
  (interface) / provider `provisional`
"""


def _write(root, rel, text):
    path = os.path.join(root, rel)
    d = os.path.dirname(path)
    if d:
        os.makedirs(d, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)
    return path


def _git(root, *args):
    return subprocess.run(["git"] + list(args), cwd=root, capture_output=True, text=True,
                          check=True)


def _project(tmp_path, spec_text, project_root="."):
    """A committed git project with a spec at `<project_root>/docs/spec.md`."""
    root = str(tmp_path)
    _write(root, ".workflow/config.json", json.dumps({"project_root": project_root}))
    _write(root, os.path.normpath(os.path.join(project_root, "docs/spec.md")), spec_text)
    _git(root, "init", "-q", "-b", "main")
    _git(root, "config", "user.email", "t@t")
    _git(root, "config", "user.name", "t")
    _git(root, "add", "-A")
    _git(root, "commit", "-qm", "base")
    return root


def _spec_path(root, project_root="."):
    return os.path.normpath(os.path.join(root, project_root, "docs/spec.md"))


def _edit(root, old, new, project_root="."):
    path = _spec_path(root, project_root)
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    assert old in text, "fixture drift: %r is not in the spec" % old
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text.replace(old, new))
    _git(root, "add", "-A")


def _run(root, project_root="."):
    return af.run(root)


def _rules(result):
    return sorted({f["rule"] for f in result["findings"]})


# ---------------------------------------------------------------- the three firing conditions

SIMPLE = """# Spec

## features
- **Ledger export** — CSV of every settled transaction, one row per leg. — commitment: `locked`
- **Export theming** — column order and header casing. — commitment: `provisional`
- **Bulk import** — shape not decided yet. — commitment: `unspecified`
"""


def test_condition_1_editing_a_locked_block_routes(tmp_path):
    """The floor's core: the text of a locked element moved, so this is not the loop's call
    however small the edit looks."""
    root = _project(tmp_path, SIMPLE)
    _edit(root, "one row per leg", "one row per transaction")
    res = _run(root)
    assert res["status"] == "route"
    assert _rules(res) == [af.RULE_LOCKED_BLOCK]
    assert "Ledger export" in res["findings"][0]["element"], "the report must NAME the element"


def test_condition_2_deleting_the_marker_outright_routes(tmp_path):
    """Losing the marker is the cheapest way to make a goal change look routine, so it is a
    rule of its own rather than a side effect of rule 1."""
    root = _project(tmp_path, SIMPLE)
    _edit(root, "one row per leg. — commitment: `locked`", "one row per leg.")
    res = _run(root)
    assert res["status"] == "route"
    assert af.RULE_MARKER_LOST in _rules(res)
    lost = [f for f in res["findings"] if f["rule"] == af.RULE_MARKER_LOST][0]
    assert "no commitment marker" in lost["detail"]
    assert "Ledger export" in lost["element"], "the report must NAME the element that lost it"


def test_condition_2_locked_downgraded_to_provisional_routes(tmp_path):
    """The named weakening case. The block is still there and still says something — it just
    says something weaker, which is precisely a goal change."""
    root = _project(tmp_path, SIMPLE)
    _edit(root, "one row per leg. — commitment: `locked`",
          "one row per leg. — commitment: `provisional`")
    res = _run(root)
    assert res["status"] == "route"
    assert af.RULE_MARKER_LOST in _rules(res)
    detail = [f for f in res["findings"] if f["rule"] == af.RULE_MARKER_LOST][0]["detail"]
    assert "`provisional`" in detail


AC_SPEC = """# Spec

## features
- **Ledger export** — CSV of every settled transaction. — commitment: `provisional`
  acceptance_criteria:
    - the export completes in under 5s for 10k rows
    - every row carries a stable id
- **Import** — the other half. — commitment: `provisional`

### acceptance criteria
- the importer rejects a malformed header
"""


def test_condition_3_editing_a_criterion_routes_even_on_a_provisional_element(tmp_path):
    """The element is `provisional`, so rule 1 is silent — and the change still routes.
    Editing a criterion IS altering what it demands, whatever the element's commitment."""
    root = _project(tmp_path, AC_SPEC)
    _edit(root, "under 5s for 10k rows", "under 30s for 10k rows")
    res = _run(root)
    assert res["status"] == "route"
    assert _rules(res) == [af.RULE_ACCEPTANCE]


def test_condition_3_also_reads_the_heading_form_of_a_criteria_region(tmp_path):
    root = _project(tmp_path, AC_SPEC)
    _edit(root, "rejects a malformed header", "rejects a malformed or absent header")
    res = _run(root)
    assert res["status"] == "route"
    assert _rules(res) == [af.RULE_ACCEPTANCE]


def test_the_criteria_field_NAME_in_a_schema_line_is_not_a_region(tmp_path):
    """`{ name, purpose, acceptance_criteria, commitment }` describes the shape of a feature;
    it does not open a criteria region. If it did, every edit under `## features` would route
    and the gate would be noise."""
    root = _project(tmp_path, REAL_SHAPES)
    _edit(root, "the holdout set is re-cut each quarter",
          "the holdout set is re-cut every six months")
    res = _run(root)
    assert res["status"] == "clear", res["findings"]


# ---------------------------------------------------------------- what must NOT route

def test_a_provisional_element_does_not_route(tmp_path):
    """The whole point of the floor is that the loop keeps taking the decisions below it."""
    root = _project(tmp_path, SIMPLE)
    _edit(root, "column order and header casing", "column order, header casing and width")
    res = _run(root)
    assert res["status"] == "clear", res["findings"]


def test_an_unspecified_element_does_not_route(tmp_path):
    root = _project(tmp_path, SIMPLE)
    _edit(root, "shape not decided yet", "shape still not decided")
    res = _run(root)
    assert res["status"] == "clear", res["findings"]


def test_whitespace_only_change_in_a_locked_block_does_not_route(tmp_path):
    """A re-wrap is not a goal change. Routing on it would teach an operator to wave the gate
    through, which is how a safety gate dies."""
    root = _project(tmp_path, SIMPLE)
    _edit(root, "CSV of every settled transaction, one row per leg.",
          "CSV   of every settled   transaction,\n  one row per leg.")
    res = _run(root)
    assert res["status"] == "clear", res["findings"]
    assert res["hunks"] >= 1, "the hunk must exist and have been judged, not missed"


def test_comment_only_change_in_a_locked_block_does_not_route(tmp_path):
    root = _project(tmp_path, SIMPLE)
    _edit(root, "## features", "## features\n<!-- reviewed 2026-09-13 -->")
    res = _run(root)
    assert res["status"] == "clear", res["findings"]


def test_an_untouched_spec_is_clear(tmp_path):
    root = _project(tmp_path, SIMPLE)
    _write(root, "src/app.py", "print(1)\n")
    _git(root, "add", "-A")
    res = _run(root)
    assert res["status"] == "clear"
    assert res["hunks"] == 0


# ---------------------------------------------------------------- fail-closed

def test_an_unreadable_spec_routes(tmp_path):
    """The gate cannot see the commitment, so it cannot say the commitment is untouched.
    'Could not tell' and 'crossed' share an exit code on purpose."""
    root = _project(tmp_path, SIMPLE)
    _git(root, "commit", "-q", "--allow-empty", "-m", "next")
    os.remove(_spec_path(root))          # the ref has it; the side being diffed does not
    res = af.run(root, mode="ref", ref="HEAD~1")
    assert res["status"] == "route"
    assert any("could not be read" in u for u in res["undetermined"]), \
        "an unreadable side must SAY so rather than be read as an empty one"


def test_deleting_the_spec_routes(tmp_path):
    """The document that defines the goal is gone. Every rule asks what a block SAYS, and an
    absent spec says nothing — so this is reported as an uncomputable floor, not as silence."""
    root = _project(tmp_path, SIMPLE)
    os.remove(_spec_path(root))
    _git(root, "add", "-A")
    res = _run(root)
    assert res["status"] == "route"
    assert any("DELETES the spec" in u for u in res["undetermined"])


def test_an_unreadable_config_routes(tmp_path):
    """An unparseable config means the spec path this gate is about to trust is a guess."""
    root = _project(tmp_path, SIMPLE)
    _write(root, ".workflow/config.json", "{not json")
    res = _run(root)
    assert res["status"] == "route"
    assert any("config.json" in u for u in res["undetermined"])


def test_no_git_worktree_routes(tmp_path):
    """No diff means no answer. It must not mean 'nothing changed'."""
    root = str(tmp_path)
    _write(root, ".workflow/config.json", json.dumps({"project_root": "."}))
    _write(root, "docs/spec.md", SIMPLE)
    res = af.run(root)
    assert res["status"] == "route"
    assert any("not a git worktree" in u for u in res["undetermined"])


def test_an_unexpected_spec_path_routes(tmp_path):
    """PATH DRIFT. A spec changed somewhere the config does not point, so this gate just read
    a different document — and would otherwise have reported CLEAR with total confidence."""
    root = _project(tmp_path, SIMPLE, project_root="./project")
    _write(root, "other/docs/spec.md", SIMPLE)
    _git(root, "add", "-A")
    res = _run(root)
    assert res["status"] == "route"
    assert any("other/docs/spec.md" in u for u in res["undetermined"])


def test_an_internal_failure_still_routes(tmp_path, monkeypatch, capsys):
    """The last line of the fail-closed discipline: an exception is an unanswered question,
    and an unanswered question routes. Nothing this gate can throw may reach a caller as a
    zero exit."""
    root = _project(tmp_path, SIMPLE)

    def _boom(*a, **kw):
        raise RuntimeError("the index is corrupt")

    monkeypatch.setattr(af, "run", _boom)
    assert af.main(["--project-root", root, "--json"]) == 1
    out = json.loads(capsys.readouterr().out)
    assert out["status"] == "route"
    assert any("the index is corrupt" in u for u in out["undetermined"])


# ---------------------------------------------------------------- path resolution

def test_a_relative_project_root_resolves_to_one_normalised_path(tmp_path):
    """`./project` is the common spelling, and the un-normalised join (`<root>/./project/...`)
    is the exact slip that double-counted a document in the sibling gate. Here it would break
    the git-relative path and silently find no spec at all."""
    root = _project(tmp_path, SIMPLE, project_root="./project")
    path, problem = af.resolve_spec(root)
    assert problem is None
    assert "/./" not in path.replace(os.sep, "/")
    assert path == os.path.normpath(os.path.join(root, "project", "docs", "spec.md"))
    _edit(root, "one row per leg", "one row per transaction", project_root="./project")
    res = _run(root)
    assert res["status"] == "route", res["undetermined"]
    assert _rules(res) == [af.RULE_LOCKED_BLOCK]
    assert res["spec"] == "project/docs/spec.md"


def test_docs_root_overrides_project_root(tmp_path):
    """Two named roots, each with one owner — they differ only where the workflow's tree is a
    clone of a repo it does not own."""
    root = str(tmp_path)
    _write(root, ".workflow/config.json",
           json.dumps({"project_root": "./project", "docs_root": "./.workflow/derived"}))
    path, _ = af.resolve_spec(root)
    assert path == os.path.normpath(
        os.path.join(root, ".workflow", "derived", "docs", "spec.md"))


# ---------------------------------------------------------------- the real spec's shapes

@pytest.mark.parametrize("old,new", [
    # `— commitment: `locked``  (a paragraph)
    ("confirms scope and approves every submission",
     "confirms scope, reviews severity and approves every submission"),
    # `— commitment: `locked` (existence) / `provisional` (layout, styling)`  (wrapped marker)
    ("no OpenTelemetry v1", "OpenTelemetry v1 included"),
    # `— `locked``  (a numbered feature)
    ("zero successful scope escapes", "at most one scope escape"),
    # `— `locked` (triad) / ... `unspecified`(deferred)`
    ("detect BOLA/IDOR", "detect BOLA/IDOR and CSRF"),
    # `— `locked` (interface) / provider `provisional``
    ("via the gateway", "via the new gateway"),
])
def test_the_marker_forms_a_real_spec_actually_uses_all_parse(tmp_path, old, new):
    root = _project(tmp_path, REAL_SHAPES)
    _edit(root, old, new)
    res = _run(root)
    assert res["status"] == "route", "%r -> %r was not caught" % (old, new)
    assert af.RULE_LOCKED_BLOCK in _rules(res)


def test_a_mixed_marker_routes_and_says_it_could_not_decide(tmp_path):
    """The half of the rule that genuinely is not mechanical: which ASPECT of a mixed
    `locked (existence) / provisional (layout)` element a prose edit touches. It routes, and
    the report says why rather than pretending to know."""
    root = _project(tmp_path, REAL_SHAPES)
    _edit(root, "no OpenTelemetry v1", "OpenTelemetry v1 included")
    res = _run(root)
    detail = [f for f in res["findings"] if f["rule"] == af.RULE_LOCKED_BLOCK][0]["detail"]
    assert "MIXED" in detail and "`provisional`" in detail


def test_a_provisional_only_bullet_beside_locked_ones_does_not_route(tmp_path):
    """Same list, same section, same document — and below the floor. If this routed, the
    floor would be a section-level rule wearing an element-level name."""
    root = _project(tmp_path, REAL_SHAPES)
    _edit(root, "colours, density, font size", "colours, density, font size, spacing")
    res = _run(root)
    assert res["status"] == "clear", res["findings"]


def test_a_nested_sub_bullet_inherits_its_locked_parent(tmp_path):
    """A sub-bullet of a locked element is part of that element — even one whose own text
    says it 'adds no commitment'. Deliberate over-routing: the safe direction."""
    root = _project(tmp_path, REAL_SHAPES)
    _edit(root, "exactly one production call site", "two production call sites")
    res = _run(root)
    assert res["status"] == "route"
    assert "inherited" in res["findings"][0]["detail"]


def test_prose_containing_the_word_locked_is_not_a_marker(tmp_path):
    """"8 gates A–H, locked 2026-08-06" is a real line in a real spec. An unbackticked match
    there would mark the whole header block as locked forever, and a gate that fires on every
    edit is a gate a human learns to skip."""
    root = _project(tmp_path, REAL_SHAPES)
    _edit(root, "this spec is the distillation", "this spec is the distilled form")
    res = _run(root)
    assert res["status"] == "clear", res["findings"]


def test_markers_in_line_reads_the_shapes_directly():
    """The parser's unit-level contract, stated once so a reader can see the accepted set."""
    assert af.markers_in_line("...text. — commitment: `locked`") == {"locked"}
    assert af.markers_in_line("...text. — `locked`") == {"locked"}
    assert af.markers_in_line("— commitment: `locked` (existence) / `provisional` (layout)") \
        == {"locked", "provisional"}
    assert af.markers_in_line("— `locked` (triad) / others `unspecified`(deferred)") \
        == {"locked", "unspecified"}
    assert af.markers_in_line("commitment: locked") == {"locked"}, \
        "an explicit `commitment:` accepts a bare token; a missed marker is an UNDER-route"
    assert af.markers_in_line("Derived from 8 gates A–H, locked 2026-08-06.") == set(), \
        "a bare dash needs a BACKTICKED token, or prose becomes a commitment"


# ---------------------------------------------------------------- the other input modes

def test_ref_mode_diffs_against_an_arbitrary_ref(tmp_path):
    root = _project(tmp_path, SIMPLE)
    _edit(root, "one row per leg", "one row per transaction")
    _git(root, "commit", "-qm", "edit")
    assert af.run(root, mode="staged")["status"] == "clear", "nothing is staged any more"
    res = af.run(root, mode="ref", ref="HEAD~1")
    assert res["status"] == "route"
    assert _rules(res) == [af.RULE_LOCKED_BLOCK]


def test_stdin_mode_reads_a_unified_diff(tmp_path):
    root = _project(tmp_path, SIMPLE)
    _edit(root, "one row per leg", "one row per transaction")
    diff = subprocess.run(["git", "diff", "--cached", "-U5"], cwd=root,
                          capture_output=True, text=True, check=True).stdout
    res = af.run(root, mode="stdin", diff_text=diff)
    assert res["status"] == "route"
    assert af.RULE_LOCKED_BLOCK in _rules(res)


def test_stdin_with_a_hunk_window_that_hides_the_marker_routes_as_undetermined(tmp_path):
    """The honest half of the narrow read: with no context and no matching file on disk, a
    marker outside the window cannot be ruled out — so it is UNDETERMINED, which routes."""
    root = _project(tmp_path, SIMPLE)
    diff = ("diff --git a/docs/spec.md b/docs/spec.md\n"
            "--- a/docs/spec.md\n+++ b/docs/spec.md\n"
            "@@ -400,1 +400,1 @@\n-old text\n+new text\n")
    res = af.run(root, mode="stdin", diff_text=diff)
    assert res["status"] == "route"
    assert res["findings"] == []
    assert res["undetermined"], "a narrow read must SAY it was narrow, never imply all-clear"


# ---------------------------------------------------------------- the CLI contract

def test_exit_codes_and_json(tmp_path):
    """Two outcomes and no third one for 'something went wrong': a caller that can tell an
    error from a clear result will eventually treat the error as clear."""
    root = _project(tmp_path, SIMPLE)
    clear = subprocess.run([sys.executable, SCRIPT, "--project-root", root, "--json"],
                           capture_output=True, text=True)
    assert clear.returncode == 0
    assert json.loads(clear.stdout)["status"] == "clear"

    _edit(root, "one row per leg", "one row per transaction")
    route = subprocess.run([sys.executable, SCRIPT, "--project-root", root],
                           capture_output=True, text=True)
    assert route.returncode == 1
    assert "ROUTE REQUIRED" in route.stdout
    assert "Ledger export" in route.stdout, "the human view must name the element touched"


def test_both_views_state_the_spec_diff_limit(tmp_path):
    """Required, not decorative: a floor that reads as 'everything goal-affecting is caught'
    is worse than no floor. Both the clear and the route render must say what it cannot see."""
    root = _project(tmp_path, SIMPLE)
    assert "SPEC DIFF only" in af.render(_run(root))
    _edit(root, "one row per leg", "one row per transaction")
    assert "SPEC DIFF only" in af.render(_run(root))
    assert "never a cap" in af.LIMIT


# ---------------------------------------------------------------- the wrap window (D219 #4)

# THE SHAPE VERBATIM FROM THE DRIVE THAT REPORTED IT (`D219` #4), not an idealised one — the
# same discipline as REAL_SHAPES above, and for the same reason. Both elements are tagged
# `unspecified`; the word `locked` appears only in a sentence explaining that nothing is. The
# old wrap window armed on the marker, stayed open, and read the prose three lines down as
# part of it — so `unspecified` elements were reported as `locked` ones.
PROSE_ABOUT_COMMITMENTS = """# Spec — notes

## purpose
A tiny note-taking CLI over a flat file. — `provisional`

## screens
- **list** — `unspecified`
  Prints one line per note, numbered from 1.
- **NOTE — this section changed with I-001.** It previously recorded "each note's `text`, one
  per line", which was a reading of the pre-`done` code. The old wording was an `unspecified`
  ingest reconstruction, never a
  `locked` invariant, so A2 supersedes it rather than contradicting it.
- **NOTE — still `unspecified`.** The command now exists, but no human has confirmed that
  *position* is the right address (see D-002 § confidence, and D-001 — nothing in this spec is
  `locked`). Matching by text prefix remains a live alternative.
"""


def test_prose_mentioning_locked_is_not_a_locked_element(tmp_path):
    """D219 #4 — the spurious `locked-block` that stopped a real drive.

    The block's first line uses an em-dash as ordinary punctuation. Under the old rule that
    armed the wrap window, every backticked commitment word below it in the block became a
    marker, so editing a paragraph ABOUT commitment tags routed as editing a locked element.
    A gate that fires on the word rather than the structure stops drives that have nothing
    locked in them.
    """
    root = _project(tmp_path, PROSE_ABOUT_COMMITMENTS)
    _edit(root, "The command now exists, but no human has confirmed that",
          "The command exists, but no human has yet confirmed that")
    res = _run(root)
    assert res["status"] == "clear", _rules(res)


def test_the_wrap_window_closes_on_a_line_that_contributes_nothing(tmp_path):
    """A real marker earlier in the block must not licence prose further down it.

    `purpose` is genuinely tagged `provisional` — below the floor. If the window stayed open
    to the end of the block, the sentence mentioning `` `locked` `` two lines later would
    widen that element to a locked one and route.
    """
    root = _project(tmp_path, PROSE_ABOUT_COMMITMENTS + (
        "\n## data_model\nOne line per note, tab-separated. — `provisional`\n"
        "The `locked` form was rejected: see the decision record.\n"))
    _edit(root, "One line per note, tab-separated.", "One note per line, tab-separated.")
    res = _run(root)
    assert res["status"] == "clear", _rules(res)


def test_a_dangling_introducer_still_opens_the_window(tmp_path):
    """The one shape that asserts no token and still means a marker is coming.

    The window must arm on it, or a marker written entirely on its continuation line is
    missed — and a missed marker is an UNDER-route, the failure direction this file does not
    accept.
    """
    root = _project(tmp_path, "# Spec\n\n## audience\nSolo operator. — commitment:\n"
                              "`locked`\n")
    _edit(root, "Solo operator.", "Solo operator, plus a reviewer.")
    res = _run(root)
    assert res["status"] == "route"
    assert af.RULE_LOCKED_BLOCK in _rules(res)


def test_a_genuine_wrapped_mixed_marker_still_widens(tmp_path):
    """The case the window exists for, pinned from the other side: the continuation line
    carries no introducer of its own and must still contribute."""
    root = _project(tmp_path, "# Spec\n\n## screens\n"
                              "- **Dashboard** — the scorecard. — commitment: `locked` (existence) /\n"
                              "  `provisional` (layout, styling)\n")
    _edit(root, "the scorecard.", "the scorecard and a drill-down.")
    res = _run(root)
    assert res["status"] == "route"
    detail = [f for f in res["findings"] if f["rule"] == af.RULE_LOCKED_BLOCK][0]["detail"]
    assert "MIXED" in detail and "`provisional`" in detail


# ---------------------------------------------------------------- creation is not an edit

ACCEPTANCE = """# Spec

## Acceptance criteria
<!-- acceptance:begin -->
- The CLI prints a greeting. — commitment: `locked`
- Exit code 0 on success. — commitment: `locked`
<!-- acceptance:end -->
"""


def _bare_repo(tmp_path, project_root="."):
    """An initialised git project with NO spec yet — the state every project starts in."""
    root = str(tmp_path)
    _write(root, ".workflow/config.json", json.dumps({"project_root": project_root}))
    _git(root, "init", "-q", "-b", "main")
    _git(root, "config", "user.email", "t@t")
    _git(root, "config", "user.name", "t")
    _git(root, "add", "-A")
    _git(root, "commit", "-qm", "base")
    return root


def test_a_created_spec_is_clear_and_says_the_floor_was_vacuous(tmp_path):
    """The measured defect, as a test: a brand-new spec full of locked acceptance criteria
    read as three criteria EDITED, and blocked the first spec commit of every new project.
    The rules are about altering an existing demand; a criterion that did not exist has none.
    It must also SAY that, because a bare clear reads as `the floor was computed and passed`.
    """
    root = _bare_repo(tmp_path)
    _write(root, "docs/spec.md", ACCEPTANCE)
    _git(root, "add", "-A")
    res = _run(root)
    assert res["status"] == "clear", res["findings"]
    assert res["created"] is True
    assert res["findings"] == []
    assert res["hunks"], "the hunks are still counted — the diff was read, not skipped"
    rendered = af.render(res)
    assert "CREATES" in rendered and "VACUOUS" in rendered
    assert "discuss" in rendered and "reconcile" in rendered, \
        "the admission must name where the human gate on a first spec actually is"


def test_a_created_spec_that_also_cannot_be_computed_still_routes(tmp_path):
    """Creation clears the three RULES; it does not clear a failure to compute. A first spec
    written to a path config does not point at is exactly the drift the stray check exists
    for, and `created` must not become a way past it."""
    root = _bare_repo(tmp_path, project_root="./project")
    _write(root, "project/docs/spec.md", ACCEPTANCE)
    _write(root, "other/docs/spec.md", ACCEPTANCE)       # a second spec, where config does not point
    _git(root, "add", "-A")
    res = _run(root)
    assert res["status"] == "route"
    assert res["created"] is True
    assert any("which one owns the goal" in u for u in res["undetermined"])
    assert "SPEC CREATED" in af.render(res), \
        "a route on a created spec must still say the spec is new"


def test_editing_a_created_specs_criterion_later_still_routes(tmp_path):
    """The other half of the pair, and the one that keeps the fix honest: once the spec
    exists, the very same criterion is an edit again."""
    root = _bare_repo(tmp_path)
    _write(root, "docs/spec.md", ACCEPTANCE)
    _git(root, "add", "-A")
    _git(root, "commit", "-qm", "first spec")
    _edit(root, "prints a greeting", "prints a greeting in French")
    res = _run(root)
    assert res["status"] == "route"
    assert res["created"] is False
    assert af.RULE_ACCEPTANCE in _rules(res)


def test_a_deletion_elsewhere_in_the_diff_is_not_the_specs(tmp_path):
    """`--stdin` is routinely handed a whole-commit diff, and `/dev/null` belongs to a FILE,
    not to a change. Searching the whole text for `+++ /dev/null` made any deleted file in
    the commit read as `this change DELETES the spec`."""
    root = _project(tmp_path, ACCEPTANCE)
    diff = (
        "diff --git a/notes.txt b/notes.txt\n"
        "deleted file mode 100644\n"
        "--- a/notes.txt\n"
        "+++ /dev/null\n"
        "@@ -1,2 +0,0 @@\n"
        "-gone\n"
        "-away\n"
        "diff --git a/docs/spec.md b/docs/spec.md\n"
        "--- a/docs/spec.md\n"
        "+++ b/docs/spec.md\n"
        "@@ -3,5 +3,5 @@\n"
        " ## Acceptance criteria\n"
        " <!-- acceptance:begin -->\n"
        "-- The CLI prints a greeting. — commitment: `locked`\n"
        "+- The CLI prints a greeting in French. — commitment: `locked`\n"
        " - Exit code 0 on success. — commitment: `locked`\n"
        " <!-- acceptance:end -->\n")
    res = af.run(root, mode="stdin", diff_text=diff)
    assert not any("DELETES the spec" in u for u in res["undetermined"]), \
        "the deleted file was notes.txt; the spec was merely edited"
    assert res["created"] is False
    assert af.RULE_ACCEPTANCE in _rules(res)


def test_a_creation_elsewhere_in_the_diff_is_not_the_specs(tmp_path):
    """The mirror, and the one that would silently UNDER-route: a commit that adds any new
    file while editing the spec must not read as `the spec is new, so nothing to alter`."""
    root = _project(tmp_path, ACCEPTANCE)
    diff = (
        "diff --git a/src/new.py b/src/new.py\n"
        "new file mode 100644\n"
        "--- /dev/null\n"
        "+++ b/src/new.py\n"
        "@@ -0,0 +1 @@\n"
        "+print(1)\n"
        "diff --git a/docs/spec.md b/docs/spec.md\n"
        "--- a/docs/spec.md\n"
        "+++ b/docs/spec.md\n"
        "@@ -3,5 +3,5 @@\n"
        " ## Acceptance criteria\n"
        " <!-- acceptance:begin -->\n"
        "-- The CLI prints a greeting. — commitment: `locked`\n"
        "+- The CLI prints a greeting in French. — commitment: `locked`\n"
        " - Exit code 0 on success. — commitment: `locked`\n"
        " <!-- acceptance:end -->\n")
    res = af.run(root, mode="stdin", diff_text=diff)
    assert res["created"] is False, "src/new.py is new; the spec is not"
    assert res["status"] == "route"
    assert af.RULE_ACCEPTANCE in _rules(res)


def test_file_sides_reads_a_plain_diff_with_no_git_headers(tmp_path):
    """Not every diff arriving on stdin comes from `git diff` — a plain unified diff has no
    `diff --git` line at all, so `---` is what starts a section."""
    plain = ("--- /dev/null\n"
             "+++ b/docs/spec.md\n"
             "@@ -0,0 +1 @@\n"
             "+- A criterion. — commitment: `locked`\n"
             "--- a/README.md\n"
             "+++ b/README.md\n"
             "@@ -1 +1 @@\n"
             "-old\n"
             "+new\n")
    sides = af.file_sides(plain)
    assert sides["docs/spec.md"] == {"created": True, "deleted": False}
    assert sides["README.md"] == {"created": False, "deleted": False}

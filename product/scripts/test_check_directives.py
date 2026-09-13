"""Tests for scripts/check_directives.py — the schema gate over `.workflow/directives.md`.

What these pin down is the JUDGMENT, not the parsing. The parse is the cheap half; the
expensive half is that this file is ALWAYS-LOADED and grows by hand, so each rule here is one
of the three pressures that keep it from becoming unbounded prose:

  * a `mechanized` entry is an INDEX ROW and is held to it — one line, and a pointer that
    resolves. That cap is the mechanical proxy for the stated-twice hazard, so the tests assert
    the two-line body FAILS and that the failure SAYS why, not just that it fails;
  * the type triage cannot be dodged in either direction — mechanized without a mechanism, and
    behavioural WITH one, are both errors. The second is the one that matters: it is the
    mechanized entry sneaking past the one-line cap;
  * a retire path fires by itself. An `on:` date passing and a `when:` path appearing are both
    events nothing else in the system would notice, which is why they fail a build here.

Plus the two rules that decide whether anyone keeps the gate: `--report` never fails, and a
MISSING file is not a failure — but is reported distinctly, because "no directives" and "all
directives valid" are different facts.
"""
import datetime
import json
import os
import subprocess
import sys

import pytest

import check_directives as cd

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "check_directives.py")
TODAY = datetime.date(2026, 9, 13)


# ---------------------------------------------------------------- fixtures

def _write(root, text):
    d = os.path.join(str(root), ".workflow")
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "directives.md"), "w", encoding="utf-8") as fh:
        fh.write(text)
    return str(root)


def _entry(title="A directive", type="behavioural", entered="2026-01-01",
           retire="standing", mechanism=None, body="do the thing."):
    lines = ["## %s" % title, "- type: %s" % type, "- entered: %s" % entered,
             "- retire: %s" % retire]
    if mechanism is not None:
        lines.append("- mechanism: %s" % mechanism)
    lines += ["", body]
    return "\n".join(lines) + "\n"


def _scan(root, **kw):
    kw.setdefault("today", TODAY)
    return cd.scan(str(root), **kw)


def _errs(res):
    return [w for e in res["entries"] for w in e["errors"]]


def _retired(res):
    return [w for e in res["entries"] for w in e["retired"]]


def _run(root, *args):
    return subprocess.run([sys.executable, SCRIPT, "--project-root", str(root), *args],
                          capture_output=True, text=True)


# ---------------------------------------------------------------- the happy path

def test_a_well_formed_behavioural_entry_passes(tmp_path):
    res = _scan(_write(tmp_path, _entry()))
    assert not cd.failed(res)
    assert res["entries"][0]["type"] == "behavioural"
    assert res["entries"][0]["title"] == "A directive"


def test_the_shipped_seed_is_green(tmp_path):
    """The load-bearing one, and the same discipline every other gate here holds: `/start`
    seeds this file, so a gate that is red on a fresh install is a gate a human learns to skip.
    Measured against the REAL seed, not a fixture — the seed is what ships."""
    seed = os.path.join(os.path.dirname(HERE), "templates", "directives.md")
    with open(seed, encoding="utf-8") as fh:
        root = _write(tmp_path, fh.read())
    res = _scan(root)
    assert not cd.failed(res), _errs(res) + _retired(res)
    assert len(res["entries"]) >= 1, "the seed ships the autonomy boundary as its first resident"


def test_the_format_guide_in_a_comment_is_not_parsed_as_content(tmp_path):
    """The seed carries its how-to-add crib in an HTML comment. If comments were parsed, that
    crib's `type  mechanized | behavioural` lines would be read as fields or as body — and on a
    mechanized entry the body cap would then fail on text nobody wrote as a directive."""
    root = _write(tmp_path, "<!-- type: nonsense\n- retire: never -->\n" + _entry())
    res = _scan(root)
    assert not cd.failed(res)
    assert res["entries"][0]["retire"] == "standing"


# ---------------------------------------------------------------- the type triage

def test_mechanized_without_a_mechanism_fails(tmp_path):
    """`mechanism` is required IFF mechanized: without it the entry claims a rule lives
    somewhere real while naming nowhere, which is prose wearing a hook's badge."""
    root = _write(tmp_path, _entry(type="mechanized", body="the gate holds it."))
    res = _scan(root)
    assert cd.failed(res)
    assert any("requires `mechanism`" in w for w in _errs(res))


def test_behavioural_with_a_mechanism_fails(tmp_path):
    """The direction that actually gets abused. A behavioural entry naming where it is enforced
    IS mechanized — and calling it behavioural is how a mechanized entry dodges the one-line cap
    and re-states a hook's logic in prose."""
    root = _write(tmp_path, _entry(type="behavioural", mechanism=".workflow/config.json"))
    res = _scan(root)
    assert cd.failed(res)
    assert any("forbidden on a `behavioural` entry" in w for w in _errs(res))


def test_an_unknown_type_fails(tmp_path):
    res = _scan(_write(tmp_path, _entry(type="advisory")))
    assert cd.failed(res)
    assert any("`type: advisory`" in w for w in _errs(res))


@pytest.mark.parametrize("field", ["type", "entered", "retire"])
def test_every_required_field_is_required(tmp_path, field):
    text = "\n".join(ln for ln in _entry().splitlines() if not ln.startswith("- %s:" % field))
    res = _scan(_write(tmp_path, text + "\n"))
    assert cd.failed(res)
    assert any("missing required field `%s`" % field in w for w in _errs(res))


def test_a_misspelled_field_is_named_rather_than_demoted_to_prose(tmp_path):
    """`- retires: standing` would otherwise vanish into the body and re-surface two errors
    later as 'missing required field: retire' — while the retire is sitting right there."""
    root = _write(tmp_path, _entry().replace("- retire: standing", "- retires: standing"))
    res = _scan(root)
    assert any("unknown field `retires`" in w for w in _errs(res))


def test_a_field_below_the_body_is_named(tmp_path):
    root = _write(tmp_path, _entry(retire="standing") + "- mechanism: x\n")
    res = _scan(root)
    assert any("appears below the body" in w for w in _errs(res))


def test_an_entered_date_must_be_a_real_date(tmp_path):
    assert any("`entered: 2026-13-40`" in w
               for w in _errs(_scan(_write(tmp_path, _entry(entered="2026-13-40")))))
    assert any("not a YYYY-MM-DD date" in w
               for w in _errs(_scan(_write(tmp_path, _entry(entered="last tuesday")))))


# ---------------------------------------------------------------- the one-line cap (D80)

def test_a_two_line_mechanized_body_fails_and_says_why(tmp_path):
    """THE rule this gate exists for. A mechanized entry is an index row; a body long enough to
    restate the hook's logic gives the loop two masters that drift. The message has to say that
    — 'too long' alone reads as a style nit and gets argued with."""
    root = _write(tmp_path, _entry(type="mechanized", mechanism=".workflow/config.json",
                                   body="stops at 30%.\nand also re-reads the handoff first."))
    os.makedirs(os.path.join(str(tmp_path), ".workflow"), exist_ok=True)
    with open(os.path.join(str(tmp_path), ".workflow", "config.json"), "w") as fh:
        json.dump({}, fh)
    res = _scan(root)
    assert cd.failed(res)
    why = " ".join(_errs(res))
    assert "capped at ONE line" in why and "STATED-TWICE" in why and "two masters" in why


def test_a_multi_line_behavioural_body_is_fine(tmp_path):
    """The cap is on the INDEX ROW, not on prose. A genuinely behavioural directive has nowhere
    else to live, so capping it would just push it back into the conversation."""
    root = _write(tmp_path, _entry(body="one thing.\ntwo thing.\nthree thing."))
    assert not cd.failed(_scan(root))


def test_an_entry_with_no_body_fails(tmp_path):
    root = _write(tmp_path, "## empty\n- type: behavioural\n- entered: 2026-01-01\n"
                            "- retire: standing\n")
    res = _scan(root)
    assert cd.failed(res)
    assert any("no body" in w for w in _errs(res))


# ---------------------------------------------------------------- the pointer must resolve

def test_a_dangling_mechanism_path_fails(tmp_path):
    """A pointer that does not resolve is how an index rots: the row keeps claiming a mechanism
    is in force long after the file moved."""
    root = _write(tmp_path, _entry(type="mechanized", mechanism=".claude/hooks/gone.py",
                                   body="blocks the push."))
    res = _scan(root)
    assert cd.failed(res)
    why = " ".join(_errs(res))
    assert "no such path" in why and "index rots" in why


def test_a_mechanism_that_exists_resolves(tmp_path):
    root = str(tmp_path)
    os.makedirs(os.path.join(root, ".claude", "hooks"))
    open(os.path.join(root, ".claude", "hooks", "guard.sh"), "w").close()
    _write(tmp_path, _entry(type="mechanized", mechanism=".claude/hooks/guard.sh",
                            body="blocks the push."))
    assert not cd.failed(_scan(root))


def test_a_config_key_mechanism_is_resolved_into_the_file(tmp_path):
    """`<path>#<dotted.key>` is the config-knob spelling. The key is checked too — a knob that
    was renamed leaves the row pointing at a file that still exists and a setting that does
    not, which reads as healthy and is not."""
    root = str(tmp_path)
    os.makedirs(os.path.join(root, ".workflow"), exist_ok=True)
    with open(os.path.join(root, ".workflow", "config.json"), "w") as fh:
        json.dump({"context": {"warn_pct": 30}}, fh)

    _write(tmp_path, _entry(type="mechanized",
                            mechanism=".workflow/config.json#context.warn_pct",
                            body="hands off before the window gets tight."))
    assert not cd.failed(_scan(root))

    _write(tmp_path, _entry(type="mechanized",
                            mechanism=".workflow/config.json#context.warn_at",
                            body="hands off before the window gets tight."))
    res = _scan(root)
    assert cd.failed(res)
    assert any("no config key" in w for w in _errs(res))


# ---------------------------------------------------------------- retire paths fire

def test_an_expired_on_date_fails(tmp_path):
    """An expired directive stops the build rather than quietly staying in force — the whole
    point of refusing 'a human remembers' as a retire path."""
    root = _write(tmp_path, _entry(retire="on:2026-09-12"))
    res = _scan(root, today=TODAY)
    assert cd.failed(res)
    assert any("has passed" in w for w in _retired(res))
    assert not _errs(res), "an expired entry is not a MALFORMED entry — different remedy"


def test_an_on_date_is_still_in_force_on_the_day_itself(tmp_path):
    res = _scan(_write(tmp_path, _entry(retire="on:2026-09-13")), today=TODAY)
    assert not cd.failed(res)


def test_a_malformed_on_date_fails_as_a_schema_error(tmp_path):
    res = _scan(_write(tmp_path, _entry(retire="on:soon")))
    assert any("not a YYYY-MM-DD date" in w for w in _errs(res))


def test_a_when_path_that_now_exists_fails(tmp_path):
    """This is what makes mechanical-first hold OVER TIME rather than only at entry: the prose
    is a placeholder, and the day its hook lands the hook's own existence forces it out."""
    root = str(tmp_path)
    _write(tmp_path, _entry(retire="when:.claude/hooks/budget.py"))
    assert not cd.failed(_scan(root)), "not yet built — the placeholder is legitimate"

    os.makedirs(os.path.join(root, ".claude", "hooks"), exist_ok=True)
    open(os.path.join(root, ".claude", "hooks", "budget.py"), "w").close()
    res = _scan(root)
    assert cd.failed(res)
    why = " ".join(_retired(res))
    assert "has fired" in why and "the hook is the directive now" in why


def test_standing_never_fails_but_is_always_listed(tmp_path):
    """`standing` is legal and deliberately the least convenient. It never fails, so the report
    listing is the ONLY pressure on it — re-confirmed each read, rather than accumulated."""
    root = _write(tmp_path, _entry(title="Always true", retire="standing"))
    res = _scan(root)
    assert not cd.failed(res)
    out = cd.render(res, report=True)
    assert "STANDING" in out and "Always true" in out
    assert "STANDING" not in cd.render(res, report=False), "the gate view is failures only"


def test_an_unparseable_retire_fails(tmp_path):
    res = _scan(_write(tmp_path, _entry(retire="when I feel like it")))
    assert any("is not one of" in w for w in _errs(res))


# ---------------------------------------------------------------- the modes

def test_report_never_fails_a_commit(tmp_path):
    """The read-only view's whole job is to be safe to run anywhere — the same rule as the
    sibling doc-budget gate. It still SHOWS the breach; it just does not exit 1 on it."""
    root = _write(tmp_path, _entry(type="mechanized", body="x"))   # invalid: no mechanism
    assert cd.failed(_scan(root))
    done = _run(root, "--report")
    assert done.returncode == 0
    assert "INVALID" in done.stdout
    assert _run(root).returncode == 1


def test_a_missing_file_is_not_a_failure_but_is_said_distinctly(tmp_path):
    """A project may simply have no standing directives. But 'no such file' and '0 entries, all
    valid' are different facts, and a gate that renders them identically cannot tell you it
    never ran."""
    res = _scan(tmp_path)
    assert res["present"] is False
    assert not cd.failed(res)
    out = cd.render(res, report=False)
    assert "no directives" in out and "does not exist" in out
    assert _run(tmp_path).returncode == 0


def test_an_empty_file_is_zero_entries_not_an_error(tmp_path):
    res = _scan(_write(tmp_path, "# Directives\n\nnothing standing yet.\n"))
    assert res["present"] is True and res["entries"] == []
    assert not cd.failed(res)
    assert "0 entry(s)" in cd.render(res, report=False)


def test_json_carries_the_verdict_for_a_machine(tmp_path):
    done = _run(_write(tmp_path, _entry(type="mechanized", body="x")), "--json")
    payload = json.loads(done.stdout)
    assert done.returncode == 1
    assert payload["present"] is True and payload["failures"]


def test_every_bad_entry_is_reported_not_just_the_first(tmp_path):
    """A gate that stops at the first error makes an operator fix a hand-written file one round
    trip at a time, which is how a hand-written file stops being hand-written."""
    root = _write(tmp_path, _entry(title="one", type="mechanized", body="x")
                  + "\n" + _entry(title="two", retire="on:2020-01-01")
                  + "\n" + _entry(title="three"))
    res = _scan(root)
    assert [e["title"] for e in res["failures"]] == ["one", "two"]
    assert len(res["entries"]) == 3

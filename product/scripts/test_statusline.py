"""Tests for scripts/statusline.py — the interactive context governor's statusline half.

Runs the script exactly as Claude Code does: `python3 statusline.py` with a status JSON on
stdin. Asserts the budget banner appears only past `config.context.warn_pct`, that it composes
over a captured user statusline (never clobbers it), and that it never crashes the line (a
non-zero exit would blank the statusline entirely).
"""
import json
import subprocess
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent            # product/scripts
SCRIPT = HERE / "statusline.py"


def _run(status, cwd):
    return subprocess.run(
        ["python3", str(SCRIPT)],
        input=json.dumps(status), cwd=cwd, capture_output=True, text=True,
    )


def _status(pct=None, tokens=None, size=None, project_dir=None):
    cw = {}
    if pct is not None:
        cw["used_percentage"] = pct
    if tokens is not None:
        cw["total_input_tokens"] = tokens
    if size is not None:
        cw["context_window_size"] = size
    return {
        "cwd": project_dir or ".",
        "model": {"display_name": "Opus"},
        "workspace": {"project_dir": project_dir or ".", "current_dir": project_dir or "."},
        "context_window": cw,
    }


def _wf(tmp_path):
    (tmp_path / ".workflow").mkdir(parents=True, exist_ok=True)
    return tmp_path


# --- the banner gates on the percentage threshold ---

def test_banner_absent_below_threshold(tmp_path):
    root = _wf(tmp_path)
    r = _run(_status(pct=20, project_dir=str(root)), root)
    assert r.returncode == 0
    assert "/dispatch" not in r.stdout


def test_banner_present_at_and_above_threshold(tmp_path):
    root = _wf(tmp_path)
    r = _run(_status(pct=80, project_dir=str(root)), root)
    assert r.returncode == 0
    assert "/dispatch" in r.stdout and "/clear" in r.stdout
    assert "80%" in r.stdout


def test_default_threshold_is_30(tmp_path):
    root = _wf(tmp_path)                                   # no config.context.warn_pct
    assert "/dispatch" not in _run(_status(pct=29, project_dir=str(root)), root).stdout
    assert "/dispatch" in _run(_status(pct=30, project_dir=str(root)), root).stdout


def test_config_warn_pct_override(tmp_path):
    root = _wf(tmp_path)
    (root / ".workflow" / "config.json").write_text(json.dumps({"context": {"warn_pct": 50}}))
    assert "/dispatch" in _run(_status(pct=55, project_dir=str(root)), root).stdout
    assert "/dispatch" not in _run(_status(pct=45, project_dir=str(root)), root).stdout


def test_percentage_computed_from_tokens_when_no_used_percentage(tmp_path):
    root = _wf(tmp_path)
    # 180k / 200k = 90% -> over the default 30.
    r = _run(_status(tokens=180000, size=200000, project_dir=str(root)), root)
    assert "/dispatch" in r.stdout


# --- composition: delegate to a captured user statusline, never clobber it ---

def test_composes_over_delegate(tmp_path):
    root = _wf(tmp_path)
    (root / ".workflow" / "statusline.delegate").write_text("echo MY-CUSTOM-LINE\n")
    r = _run(_status(pct=80, project_dir=str(root)), root)
    assert "MY-CUSTOM-LINE" in r.stdout          # the user's line survives
    assert "/dispatch" in r.stdout               # and the banner is appended below it


def test_delegate_receives_the_status_json_on_stdin(tmp_path):
    root = _wf(tmp_path)
    # A delegate that echoes back a field proves the same stdin is piped through.
    (root / ".workflow" / "statusline.delegate").write_text(
        "python3 -c 'import sys,json; print(json.load(sys.stdin)[\"model\"][\"display_name\"])'\n")
    r = _run(_status(pct=10, project_dir=str(root)), root)
    assert "Opus" in r.stdout


def test_minimal_base_when_no_delegate(tmp_path):
    root = _wf(tmp_path)
    r = _run(_status(pct=10, project_dir=str(root)), root)
    assert "Opus" in r.stdout                     # model shown in the minimal base
    assert "ctx 10%" in r.stdout


# --- never crash the status line ---

def test_garbage_stdin_exits_zero(tmp_path):
    r = subprocess.run(["python3", str(SCRIPT)], input="not json", cwd=tmp_path,
                       capture_output=True, text=True)
    assert r.returncode == 0


def test_empty_stdin_exits_zero(tmp_path):
    r = subprocess.run(["python3", str(SCRIPT)], input="", cwd=tmp_path,
                       capture_output=True, text=True)
    assert r.returncode == 0


def test_no_context_window_prints_base_no_banner(tmp_path):
    root = _wf(tmp_path)
    status = {"model": {"display_name": "Opus"}, "workspace": {"project_dir": str(root)}}
    r = _run(status, root)
    assert r.returncode == 0
    assert "/dispatch" not in r.stdout
    assert "Opus" in r.stdout


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))


# --- the band: two-sided, and an absent knob must not become a ceiling -------

def test_an_absent_warn_pct_does_not_become_a_ceiling(tmp_path):
    """The regression that would make the band unreachable. A defaulted 30% ceiling fires long
    before runway ever runs low, so an absent knob silently materialised into one would mean
    the work-budget arithmetic never governs anything."""
    root = _wf(tmp_path)                                   # no config.context.warn_pct
    r = _run(_status(tokens=400_000, size=1_000_000, project_dir=str(root)), root)
    assert "/dispatch" not in r.stdout                     # 40% full, but ~50 nodes of runway
    assert "hand off" not in r.stdout


def test_a_set_warn_pct_still_fires_as_an_explicit_ceiling(tmp_path):
    """A human who sets the knob is giving a standing instruction; the band must not overrule
    it just because the arithmetic disagrees."""
    root = _wf(tmp_path)
    (root / ".workflow" / "config.json").write_text(json.dumps({"context": {"warn_pct": 30}}))
    r = _run(_status(tokens=400_000, size=1_000_000, project_dir=str(root)), root)
    assert "hand off NOW" in r.stdout
    assert "your instruction rather than the arithmetic" in r.stdout


def test_low_runway_hands_off_even_on_a_huge_window(tmp_path):
    root = _wf(tmp_path)
    r = _run(_status(tokens=995_000, size=1_000_000, project_dir=str(root)), root)
    assert "hand off NOW" in r.stdout


def test_the_statusline_publishes_the_reading(tmp_path):
    """The crossing of the wall: the statusline is the only surface with a token count, so
    nothing else can learn it unless this file writes it down."""
    root = _wf(tmp_path)
    _run(_status(tokens=120_000, size=200_000, project_dir=str(root)), root)
    published = json.loads((root / ".workflow" / "context.json").read_text())
    assert published["used"] == 120_000 and published["window"] == 200_000


def test_a_hold_prints_no_banner_at_all(tmp_path):
    """A persistent "you are fine" line is how a status line teaches someone to ignore it."""
    root = _wf(tmp_path)
    r = _run(_status(tokens=100_000, size=1_000_000, project_dir=str(root)), root)
    assert "hand off" not in r.stdout
    assert "nodes left" in r.stdout          # the figure is on the base line instead

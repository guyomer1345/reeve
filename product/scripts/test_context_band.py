"""Tests for context_band.py — when should this session hand off?

The point of the band is that it has TWO sides. The rule it replaces had a ceiling and no
floor, so nothing could ever say "not yet" and under-use was invisible. Most of what follows is
about the floor, because the ceiling was never the part that was missing.

The second theme is the unit. A percentage makes a 200k and a 1M window read identically while
leaving them wildly different amounts of work, and there is a test that holds those two windows
at the same fraction and asserts they get DIFFERENT verdicts — which is the whole argument for
the change, stated as an assertion rather than as a paragraph.
"""
import json
import os
import time

import pytest

import context_band as cb


M = cb.PER_NODE_TOKENS


def _at(runway_nodes, window=1_000_000):
    """A reading with exactly this many nodes of runway left."""
    return window - runway_nodes * M, window


# --- the two sides -----------------------------------------------------------

def test_plenty_of_runway_says_HOLD(tmp_path):
    v = cb.band(*_at(20))
    assert v["verdict"] == "hold"
    assert "still has work in it" in v["reason"]


def test_below_the_reserve_says_HAND_OFF_NOW():
    v = cb.band(*_at(cb.RESERVE_NODES - 0.5))
    assert v["verdict"] == "handoff-now"
    assert "complete handoff" in v["reason"]


def test_the_middle_says_AT_THE_NEXT_BOUNDARY():
    mid = (cb.RESERVE_NODES + cb.COMFORTABLE_NODES) / 2.0
    v = cb.band(*_at(mid))
    assert v["verdict"] == "handoff-at-boundary"
    assert "never mid-item" in v["reason"]


def test_the_floor_exists_at_all(tmp_path):
    """The regression this module was built for: the old rule could say 'go' and never
    'not yet', so a premature hand-off was free and invisible."""
    assert cb.band(*_at(cb.COMFORTABLE_NODES + 1))["verdict"] == "hold"


# --- the unit is WORK, not a fraction ----------------------------------------

def test_the_same_fraction_gives_different_verdicts_on_different_windows():
    """The entire argument for the change, as an assertion. Both windows are 97% full; one
    has ~6k of runway and the other ~30k, which are not the same situation."""
    small = cb.band(200_000 * 0.97, 200_000)
    large = cb.band(1_000_000 * 0.97, 1_000_000)
    assert small["pct"] == large["pct"] == 97.0
    assert small["verdict"] == "handoff-now"
    assert large["verdict"] != "handoff-now"


def test_runway_is_reported_in_nodes():
    v = cb.band(*_at(4))
    assert v["runway_nodes"] == pytest.approx(4.0, abs=0.1)


def test_a_full_window_is_hand_off_now_and_never_negative():
    v = cb.band(500_000, 400_000)          # over-full, which the harness can report
    assert v["verdict"] == "handoff-now"
    assert v["runway_nodes"] == 0.0


# --- the operator ceiling outranks the arithmetic ----------------------------

def test_an_explicit_warn_pct_fires_even_with_runway_to_spare():
    """A human who sets the knob is giving a standing instruction. A governor that silently
    ignored it would reproduce the failure the directive channel exists to stop."""
    v = cb.band(*_at(20), warn_pct=30)     # 20 nodes left on a 1M window is ~76% used
    assert v["verdict"] == "handoff-now"
    assert v["operator_ceiling"] == 30
    assert "your instruction rather than the arithmetic" in v["reason"]


def test_below_the_operator_ceiling_the_band_still_governs():
    v = cb.band(*_at(20, window=1_000_000), warn_pct=99)
    assert v["verdict"] == "hold"


def test_a_nonsense_ceiling_is_ignored_rather_than_obeyed():
    for bad in (0, -5, 150, "thirty", None):
        assert cb.band(*_at(20), warn_pct=bad)["verdict"] == "hold"


# --- fail direction: unknown, never `hold` -----------------------------------

def test_no_window_size_is_unknown_not_hold():
    """A wrong `hold` tells a session to keep filling a window it should be leaving, and the
    cost of that is a session that stops with no anchor written."""
    assert cb.band(1000, None)["verdict"] == "unknown"
    assert cb.band(1000, 0)["verdict"] == "unknown"


def test_no_token_count_is_unknown():
    assert cb.band(None, 200_000)["verdict"] == "unknown"
    assert cb.band("lots", 200_000)["verdict"] == "unknown"


# --- publishing: the crossing of the sensor/actuator wall --------------------

def test_publish_then_read_round_trips(tmp_path):
    wf = str(tmp_path / ".workflow")
    assert cb.publish(wf, 120_000, 200_000, time.monotonic()) is True
    r = cb.read_reading(wf, now=time.monotonic())
    assert r["used"] == 120_000 and r["window"] == 200_000


def test_a_stale_reading_reads_as_absent(tmp_path):
    """It describes a session that has probably already ended, and a verdict about a dead
    session's window is worse than no verdict."""
    wf = str(tmp_path / ".workflow")
    cb.publish(wf, 120_000, 200_000, time.monotonic() - cb.STALE_SECONDS - 1)
    assert cb.read_reading(wf, now=time.monotonic()) is None


def test_a_fresh_reading_survives(tmp_path):
    wf = str(tmp_path / ".workflow")
    cb.publish(wf, 1, 2, time.monotonic() - 5)
    assert cb.read_reading(wf, now=time.monotonic()) is not None


def test_publish_never_raises_on_an_unwritable_path():
    """It runs inside the status line, and a status line that crashes blanks itself."""
    assert cb.publish("/proc/nonexistent/nope", 1, 2, 0.0) is False


def test_an_unparseable_reading_is_absent_not_a_crash(tmp_path):
    wf = tmp_path / ".workflow"
    wf.mkdir()
    (wf / "context.json").write_text("{ truncated", encoding="utf-8")
    assert cb.read_reading(str(wf), now=time.monotonic()) is None


def test_publish_is_atomic_leaving_no_partial_file(tmp_path):
    wf = str(tmp_path / ".workflow")
    cb.publish(wf, 1, 2, 0.0)
    names = sorted(os.listdir(wf))
    assert names == ["context.json"], names       # no .tmp left behind


# --- the cli contract --------------------------------------------------------

def test_exit_code_encodes_urgency(tmp_path, capsys):
    wf = str(tmp_path / ".workflow")
    cb.publish(wf, *_at(20), mono=time.monotonic())
    assert cb.main(["--workflow-dir", wf]) == 0                       # hold
    cb.publish(wf, *_at(0.5), mono=time.monotonic())
    assert cb.main(["--workflow-dir", wf]) == 2                       # hand off now


def test_no_reading_at_all_is_not_an_error(tmp_path):
    """A session with no statusline configured must not look like a failure."""
    assert cb.main(["--workflow-dir", str(tmp_path)]) == 0

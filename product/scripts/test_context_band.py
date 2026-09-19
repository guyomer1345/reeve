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



# A REAL anchor: fresh mtime is only half of "written" — `context_band` also requires the
# anchor to name a base commit, because a resume reads `git log <base_sha>..HEAD` and one
# without it cannot say what moved (`D219` #3). A bare "# handoff" is the exact shape a
# real drive produced and nothing caught.
ANCHOR = "# handoff\n\nbase_sha: 1a2b3c4\n"
FRESH = "# fresh\n\nbase_sha: 9f8e7d6\n"

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


# --- the gate: the half that acts --------------------------------------------
#
# The band above was right and read by nobody. Everything below is about the two verdicts that
# turn it into a control, and about the one that must NEVER be inferred: `clear_safe`, whose
# consumer resets a live session.

def _wf(tmp_path, runway_nodes, window=1_000_000):
    wf = str(tmp_path / ".workflow")
    cb.publish(wf, *_at(runway_nodes, window), mono=time.monotonic())
    return wf


def _handoff(wf, text=ANCHOR, bump=0.0):
    os.makedirs(wf, exist_ok=True)
    path = os.path.join(wf, "handoff.md")
    with open(path, "w") as fh:
        fh.write(text)
    if bump:
        os.utime(path, (os.path.getatime(path), os.path.getmtime(path) + bump))
    return path


def test_handoff_now_with_no_anchor_OWES_one(tmp_path):
    wf = _wf(tmp_path, 0.5)
    d = cb.demand(wf)
    assert d["verdict"] == "handoff-now"
    assert d["needs_handoff"] is True
    assert d["handoff_written"] is False


def test_writing_the_anchor_DISCHARGES_the_demand(tmp_path):
    """The negative control for the test above — without it the hook would block forever."""
    wf = _wf(tmp_path, 0.5)
    _handoff(wf)                              # an anchor that predates the demand
    assert cb.demand(wf)["needs_handoff"] is True
    _handoff(wf, FRESH, bump=10)        # one written since
    d = cb.demand(wf)
    assert d["handoff_written"] is True
    assert d["needs_handoff"] is False


def test_freshness_is_measured_from_when_the_band_ENTERED_handoff_now(tmp_path):
    """Not a TTL and not "recently" — an anchor written before the demand does not discharge it."""
    wf = _wf(tmp_path, 0.5)
    _handoff(wf)
    cb.demand(wf)                                            # arms, latching that mtime
    latched = cb._read_latch(wf)["armed_handoff_mtime"]
    assert latched == pytest.approx(os.path.getmtime(os.path.join(wf, "handoff.md")))
    assert cb.demand(wf)["needs_handoff"] is True            # same file, still owed


def test_leaving_handoff_now_DISARMS_so_the_demand_is_once_per_fill(tmp_path):
    """In practice this is the turn after a /clear. Without it the hook nags forever."""
    wf = _wf(tmp_path, 0.5)
    cb.demand(wf)
    cb.record_demand(wf)
    assert cb._read_latch(wf) is not None
    cb.publish(wf, *_at(20), mono=time.monotonic())          # cleared: the window emptied
    d = cb.demand(wf)
    assert d["needs_handoff"] is False
    assert cb._read_latch(wf) is None
    assert d["demands"] == 0


def test_no_arm_asks_without_latching(tmp_path):
    wf = _wf(tmp_path, 0.5)
    assert cb.demand(wf, arm=False)["needs_handoff"] is True
    assert cb._read_latch(wf) is None


def test_demands_counts_only_when_recorded(tmp_path):
    """Asking must never inflate the loop-stop counter — the hook would give up early."""
    wf = _wf(tmp_path, 0.5)
    for _ in range(5):
        cb.demand(wf)
    assert cb.demand(wf)["demands"] == 0
    assert cb.record_demand(wf) == 1
    assert cb.demand(wf)["demands"] == 1


def test_an_unwritten_anchor_is_never_clear_safe(tmp_path):
    wf = _wf(tmp_path, 0.5)
    g = cb.gate(wf)
    assert g["clear_safe"] is False
    assert any("no handoff has been written" in b for b in g["blocked_by"])


def test_clear_safe_once_the_anchor_is_fresh_and_nobody_is_waiting_AND_IDLE(tmp_path):
    wf = _wf(tmp_path, 0.5)
    _handoff(wf)
    cb.demand(wf)
    _handoff(wf, FRESH, bump=10)
    # The first three conditions are now all true — and that is precisely the state a real
    # drive reset a RUNNING session in, because the anchor is written during a turn.
    assert cb.gate(wf)["clear_safe"] is False
    cb.mark_idle(wf, {"kind": "idle_prompt"})
    g = cb.gate(wf)
    assert g["parked_open"] == 0
    assert g["clear_safe"] is True, g["blocked_by"]


def test_a_RUNNING_TURN_blocks_the_reset_however_good_everything_else_looks(tmp_path):
    """The fourth condition, and the only one stated in the positive. Absent reads as not idle:
    the cost of holding is a reset that waits a poll, the cost of firing is a prompt box full of
    unsubmitted text that only Esc clears — and Esc then runs the `/clear` with no `continue`."""
    wf = _wf(tmp_path, 0.5)
    _handoff(wf)
    cb.demand(wf)
    _handoff(wf, FRESH, bump=10)
    cb.mark_idle(wf)
    assert cb.gate(wf)["clear_safe"] is True
    cb.clear_idle(wf)                                   # a prompt was submitted; the turn runs
    g = cb.gate(wf)
    assert g["clear_safe"] is False
    assert g["session_idle"] is None
    assert any("not known to be idle" in b for b in g["blocked_by"]), g["blocked_by"]


def _ready(tmp_path):
    """Every `clear_safe` condition true — the state a reset may actually happen in."""
    wf = _wf(tmp_path, 0.5)
    _handoff(wf)
    cb.demand(wf)
    _handoff(wf, FRESH, bump=10)
    cb.mark_idle(wf)
    assert cb.gate(wf)["clear_safe"] is True
    return wf


def _dispatch(wf, tid="toolu_1", agent="reeve:planner"):
    d = os.path.join(wf, cb.IN_FLIGHT_DIR)
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, tid + ".json"), "w") as fh:
        json.dump({"agent": agent}, fh)
    return os.path.join(d, tid + ".json")


def test_a_BACKGROUNDED_WORKER_blocks_the_reset(tmp_path):
    """The parent is idle BECAUSE it is waiting. `idle_prompt` fires either way — the harness is
    not wrong, it just cannot tell the two apart — so idle alone would have cleared a session
    mid-dispatch and thrown the worker away."""
    wf = _ready(tmp_path)
    _dispatch(wf)
    g = cb.gate(wf)
    assert g["clear_safe"] is False
    assert any("have not returned" in b for b in g["blocked_by"]), g["blocked_by"]
    assert [r["agent"] for r in g["workers_in_flight"]] == ["reeve:planner"]


def test_the_reset_resumes_the_moment_the_worker_RETURNS(tmp_path):
    wf = _ready(tmp_path)
    path = _dispatch(wf)
    assert cb.gate(wf)["clear_safe"] is False
    os.remove(path)                                  # PostToolUse retires the mark
    assert cb.gate(wf)["clear_safe"] is True


def test_a_worker_that_NEVER_RETURNS_ages_out_rather_than_wedging(tmp_path):
    """The backstop, and the only reason a TTL exists here at all. SessionStart clears the
    directory across sessions; this covers a worker that vanishes inside a session that keeps
    running, where an entry that never expired would hold the reset gate forever."""
    wf = _ready(tmp_path)
    path = _dispatch(wf)
    old = time.time() - cb.IN_FLIGHT_STALE_SECONDS - 60
    os.utime(path, (old, old))
    assert cb.workers_in_flight(wf) == []
    assert cb.gate(wf)["clear_safe"] is True


def test_an_unreadable_in_flight_entry_still_counts_as_a_worker(tmp_path):
    """Presence is the fact. Reading a torn scratch file as "nothing is running" is how the
    worker gets thrown away."""
    wf = _ready(tmp_path)
    path = _dispatch(wf)
    with open(path, "w") as fh:
        fh.write("{torn")
    assert cb.gate(wf)["clear_safe"] is False


def test_an_unreadable_idle_flag_still_counts_as_idle(tmp_path):
    """Its PRESENCE is the fact — one hook writes it, another removes it, and the body is only
    for humans. Refusing to read a torn scratch file as idle would disable the supervisor over
    bookkeeping, which is the opposite of how the dialog flag fails and deliberately so."""
    wf = _wf(tmp_path, 0.5)
    _handoff(wf)
    cb.demand(wf)
    _handoff(wf, FRESH, bump=10)
    with open(os.path.join(wf, cb.IDLE_FILE), "w") as fh:
        fh.write("{torn")
    assert cb.gate(wf)["clear_safe"] is True


def test_a_parked_checkpoint_blocks_the_reset(tmp_path):
    """`clear_safe` is not `needs_handoff` with extra steps — a person mid-conversation."""
    wf = _wf(tmp_path, 0.5)
    _handoff(wf)
    cb.demand(wf)
    _handoff(wf, FRESH, bump=10)
    os.makedirs(os.path.join(wf, "parked"))
    with open(os.path.join(wf, "parked", "TCK-1.json"), "w") as fh:
        json.dump({"ticket_id": "TCK-1"}, fh)
    g = cb.gate(wf)
    assert g["parked_open"] == 1
    assert g["clear_safe"] is False
    assert any("await a human verdict" in b for b in g["blocked_by"])


def test_an_unreachable_runtime_root_reads_as_somebody_IS_waiting(tmp_path):
    """`bus.Paths` raises SystemExit here (the /rebind case), which is not an Exception."""
    wf = _wf(tmp_path, 0.5)
    _handoff(wf)
    cb.demand(wf)
    _handoff(wf, FRESH, bump=10)
    with open(os.path.join(wf, "runtime.json"), "w") as fh:
        json.dump({"runtime_root": str(tmp_path / "gone")}, fh)
    g = cb.gate(wf)
    assert g["parked_open"] is None            # None is NOT zero
    assert g["clear_safe"] is False


def test_a_missing_anchor_is_still_owed_not_excused(tmp_path):
    wf = _wf(tmp_path, 0.5)                    # no handoff.md at all
    assert cb.demand(wf)["needs_handoff"] is True


def test_the_gate_never_fires_on_handoff_at_boundary(tmp_path):
    """The middle verdict means there IS runway; interrupting a turn to spend it would defeat
    the floor half of the band."""
    wf = _wf(tmp_path, (cb.RESERVE_NODES + cb.COMFORTABLE_NODES) / 2.0)
    d = cb.demand(wf)
    assert d["verdict"] == "handoff-at-boundary"
    assert d["needs_handoff"] is False


def test_no_reading_owes_nothing(tmp_path):
    """A session with no statusline configured must not be told it owes an anchor forever."""
    wf = str(tmp_path / ".workflow")
    os.makedirs(wf)
    d = cb.demand(wf)
    assert d["verdict"] == "unknown"
    assert d["needs_handoff"] is False


def test_gate_cli_exit_code_is_may_i_reset(tmp_path, capsys):
    wf = _wf(tmp_path, 0.5)
    assert cb.main(["--workflow-dir", wf, "--gate"]) == 1        # anchor owed
    out = json.loads(capsys.readouterr().out)
    assert out["needs_handoff"] is True
    _handoff(wf, FRESH, bump=10)
    cb.mark_idle(wf)
    assert cb.main(["--workflow-dir", wf, "--gate"]) == 0        # reset is safe
    assert json.loads(capsys.readouterr().out)["clear_safe"] is True


def test_the_operator_ceiling_reaches_the_gate_too(tmp_path):
    """It outranked the arithmetic in the statusline and was ignored by the CLI — one owner now."""
    wf = _wf(tmp_path, 30)                                      # plenty of runway
    assert cb.demand(wf)["verdict"] == "hold"
    with open(os.path.join(wf, "config.json"), "w") as fh:
        json.dump({"context": {"warn_pct": 1}}, fh)
    d = cb.demand(wf, project_dir=str(tmp_path))
    assert d["verdict"] == "handoff-now"
    assert d["operator_ceiling"] == 1


# ------------------------------------------------- the anchor must NAME A BASE (D219 #3)

def test_a_fresh_anchor_with_no_base_sha_does_not_discharge_the_demand(tmp_path):
    """The exact shape a real drive produced: an item that went all the way round — planned,
    executed, verified, documented, committed — and then wrote an anchor nothing could resume
    from. A resume reads `git log <base_sha>..HEAD`; without the field it cannot see what
    moved, and `12h`'s supervisor clears sessions on purpose.
    """
    wf = _wf(tmp_path, 0.5)
    _handoff(wf, "# handoff\n\nEverything is fine.\n")   # armed at this mtime
    cb.demand(wf)
    _handoff(wf, "# handoff\n\nStill no base commit named.\n", bump=10)
    d = cb.demand(wf)
    assert d["anchor_fresh"] is True, "the file did move — that half is not what failed"
    assert d["anchor_names_base"] is False
    assert d["handoff_written"] is False
    assert d["needs_handoff"] is True
    assert "base_sha" in d["reason"], "the demand must say WHICH half is missing"


def test_adding_the_base_sha_alone_discharges_it(tmp_path):
    """The fix path is additive: the anchor's prose stands and the field is added."""
    wf = _wf(tmp_path, 0.5)
    _handoff(wf, "# handoff\n\nEverything is fine.\n")
    cb.demand(wf)
    _handoff(wf, "# handoff\n\nEverything is fine.\n\n- base_sha: 81d362e\n", bump=10)
    d = cb.demand(wf)
    assert d["handoff_written"] is True and d["needs_handoff"] is False


def test_clear_is_NOT_safe_on_an_anchor_naming_no_base(tmp_path):
    """The supervisor's half. Resetting a session whose anchor cannot be resumed from is the
    one reset that loses the loop's place outright."""
    wf = _wf(tmp_path, 0.5)
    _handoff(wf, "# handoff\n")
    cb.demand(wf)
    _handoff(wf, "# handoff\n\nrewritten, still no base\n", bump=10)
    g = cb.gate(wf)
    assert g["clear_safe"] is False
    assert any("base_sha" in b for b in g["blocked_by"])


@pytest.mark.parametrize("value,ok", [
    ("base_sha: 81d362e", True),
    ("- base_sha: 1a2b3c4d5e6f7890", True),
    ("**base_sha**: `deadbee`", True),
    ("base_sha = 81d362e", True),
    ("base sha: 81d362e", True),
    ("base_sha: none", False),
    ("base_sha: unknown", False),
    ("base_sha:", False),
    ("the base_sha field belongs here", False),
    ("nothing about it at all", False),
])
def test_what_counts_as_naming_a_base_commit(tmp_path, value, ok):
    """Permissive on spelling, strict on substance. The `none`/`unknown`/empty rows are the
    shapes a session writes when it did not look, and they must not pass."""
    path = tmp_path / "handoff.md"
    path.write_text("# handoff\n\n%s\n" % value)
    assert cb.anchor_names_base(str(path)) is ok

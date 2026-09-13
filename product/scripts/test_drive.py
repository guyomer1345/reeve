"""Tests for drive.py — should the driver spawn another session?

The asymmetry runs the other way from converge.py's and that is the point. `converge.py`
reports and may be permissive; this thing SPAWNS PROCESSES on a machine nobody is watching. So
every "cannot compute" case below asserts the same thing: it stops. A driver that continues on
a predicate it could not evaluate is an unattended night of work nobody can account for.

The second theme is that the driver reads durable state and never a session's report. Each test
kills, crashes or silences the session and asserts the verdict is still correct — a dead session
cannot say why it died, and nothing here needs it to.
"""
import json
import os
import subprocess
import sys

import pytest

import drive


def _git(root, *args):
    subprocess.run(("git", "-C", str(root)) + args, check=True, capture_output=True, text=True)


@pytest.fixture
def repo(tmp_path):
    """A real git repo with a .workflow/ — the driver fingerprints HEAD, so git must be real."""
    root = tmp_path / "proj"
    (root / ".workflow" / "items").mkdir(parents=True)
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "t@t")
    _git(root, "config", "user.name", "t")
    (root / "f.txt").write_text("one", encoding="utf-8")
    _git(root, "add", "-A")
    _git(root, "commit", "-qm", "init")
    return root


def wf(repo):
    return str(repo / ".workflow")


def _goal(repo, acceptance=("ga-1",)):
    (repo / ".workflow" / "goal.json").write_text(json.dumps(
        {"id": "g-1", "status": "active",
         "acceptance": [{"id": a, "text": a} for a in acceptance]}), encoding="utf-8")


def _ledger(repo, *entries):
    (repo / ".workflow" / "goal-ledger.jsonl").write_text(
        "".join(json.dumps(e) + "\n" for e in entries), encoding="utf-8")


def _pause(repo, paused=True):
    rt = repo / ".workflow"
    (rt / "control.json").write_text(json.dumps({"paused": paused, "at": "now", "by": "m-1"}),
                                     encoding="utf-8")


# --- the progress fingerprint -------------------------------------------------

def test_fingerprint_moves_when_a_commit_lands(repo):
    a = drive.fingerprint(wf(repo))
    (repo / "f.txt").write_text("two", encoding="utf-8")
    _git(repo, "commit", "-qam", "second")
    assert drive.fingerprint(wf(repo)) != a


def test_fingerprint_moves_on_an_item_anchor_with_no_commit(repo):
    """The case a HEAD-only driver gets wrong: an item bigger than one session advances
    through nodes without committing, and must not read as a stall."""
    a = drive.fingerprint(wf(repo))
    d = repo / ".workflow" / "items" / "i-1"
    d.mkdir()
    (d / "plan.md").write_text("# plan", encoding="utf-8")
    assert drive.fingerprint(wf(repo)) != a


def test_fingerprint_ignores_anchor_CONTENT(repo):
    """Presence is what the anchor proves. Hashing bodies would let an edited draft — or a
    reformatted file — read as a node having run."""
    d = repo / ".workflow" / "items" / "i-1"
    d.mkdir()
    (d / "plan.md").write_text("# plan", encoding="utf-8")
    a = drive.fingerprint(wf(repo))
    (d / "plan.md").write_text("# plan, rewritten at length", encoding="utf-8")
    assert drive.fingerprint(wf(repo)) == a


def test_fingerprint_is_none_without_git(tmp_path):
    (tmp_path / ".workflow").mkdir()
    assert drive.fingerprint(str(tmp_path / ".workflow")) is None


# --- the stop predicates, in precedence order ---------------------------------

def test_a_pause_outranks_everything(repo):
    _goal(repo)
    _pause(repo)
    v = drive.decide(wf(repo), None, 0)
    assert v["cont"] is False and "PAUSED" in v["reason"]


def test_a_cleared_pause_lets_the_driver_run(repo):
    _pause(repo, paused=False)
    assert drive.decide(wf(repo), None, 0)["cont"] is True


def test_a_met_goal_stops_the_driver(repo):
    _goal(repo, ("ga-1", "ga-2"))
    _ledger(repo, {"item": "i-1", "refs": ["ga-1", "ga-2"]})
    v = drive.decide(wf(repo), None, 0)
    assert v["cont"] is False and v.get("met") is True


def test_an_unmet_goal_does_not_stop_the_driver(repo):
    _goal(repo, ("ga-1", "ga-2"))
    _ledger(repo, {"item": "i-1", "refs": ["ga-1"]})
    assert drive.decide(wf(repo), None, 0)["cont"] is True


def test_a_stalled_goal_stops_the_driver(repo):
    _goal(repo)
    _ledger(repo, *[{"item": "m-%d" % i, "refs": []} for i in range(6)])
    v = drive.decide(wf(repo), None, 0)
    assert v["cont"] is False and v.get("stalled") is True


def test_no_goal_still_drives(repo):
    """A goal is optional. Without one the loop works its backlog and only the no-progress
    guard can stop it — a driver that refused to run without a goal would be a regression on
    the runner it generalizes."""
    assert drive.decide(wf(repo), None, 0)["cont"] is True


# --- the no-progress guard ----------------------------------------------------

def test_the_first_tick_never_scores_no_progress(repo):
    v = drive.decide(wf(repo), None, 0)
    assert v["cont"] is True and v["streak"] == 0


def test_an_unchanged_fingerprint_increments_the_streak(repo):
    fp = drive.fingerprint(wf(repo))
    v = drive.decide(wf(repo), fp, 0)
    assert v["cont"] is True and v["streak"] == 1


def test_the_streak_stops_the_driver_at_the_limit(repo):
    fp = drive.fingerprint(wf(repo))
    v = drive.decide(wf(repo), fp, drive.MAX_NOPROGRESS - 1)
    assert v["cont"] is False and "NO PROGRESS" in v["reason"]


def test_any_progress_resets_the_streak(repo):
    fp = drive.fingerprint(wf(repo))
    d = repo / ".workflow" / "items" / "i-1"
    d.mkdir()
    (d / "changelog.md").write_text("did a thing", encoding="utf-8")
    v = drive.decide(wf(repo), fp, drive.MAX_NOPROGRESS - 1)
    assert v["cont"] is True and v["streak"] == 0


def test_the_limit_matches_the_relaunch_runners(repo):
    """One mechanism that gives up, not two that disagree about when."""
    import bus
    assert drive.MAX_NOPROGRESS == bus.RUNNER_MAX_ATTEMPTS


# --- fail direction: anything uncomputable STOPS ------------------------------

def test_no_git_stops_rather_than_spawning_blind(tmp_path):
    (tmp_path / ".workflow").mkdir()
    v = drive.decide(str(tmp_path / ".workflow"), None, 0)
    assert v["cont"] is False and "fingerprint" in v["reason"]


def test_an_unreadable_pause_latch_stops(repo, monkeypatch):
    import drain
    monkeypatch.setattr(drain, "read_control", lambda p: (_ for _ in ()).throw(OSError("boom")))
    v = drive.decide(wf(repo), None, 0)
    assert v["cont"] is False and "pause latch" in v["reason"]


def test_a_corrupt_goal_does_not_read_as_met(repo):
    """converge.py fails closed, and the driver must inherit that rather than re-deciding."""
    (repo / ".workflow" / "goal.json").write_text("{ truncated", encoding="utf-8")
    v = drive.decide(wf(repo), None, 0)
    assert v.get("met") is not True


# --- the shell contract the driver actually consumes --------------------------

def test_shell_output_is_evalable_and_quotes_the_reason(repo):
    _pause(repo)
    out = subprocess.run([sys.executable, os.path.join(os.path.dirname(drive.__file__),
                                                       "drive.py"),
                          "--workflow-dir", wf(repo), "tick", "--shell"],
                         capture_output=True, text=True)
    assert out.returncode == 1                       # 1 = stop
    body = out.stdout
    assert "DRIVE_CONTINUE=0" in body
    # The reason contains spaces and an em dash; unquoted it would break `eval`.
    got = subprocess.run(["bash", "-c", 'eval "$1"; echo "$DRIVE_REASON"', "_", body],
                         capture_output=True, text=True)
    assert got.returncode == 0 and "PAUSED" in got.stdout


# --- the steer checkpoint: making a terminal stop REACHABLE ---------------------

def _tick(repo):
    return subprocess.run([sys.executable, os.path.join(os.path.dirname(drive.__file__),
                                                        "drive.py"),
                           "--workflow-dir", wf(repo), "tick"],
                          capture_output=True, text=True)


def _parked(repo):
    d = repo / ".workflow" / "parked"
    return sorted(p.name for p in d.iterdir()) if d.is_dir() else []


def test_a_met_goal_parks_a_steer_checkpoint(repo):
    """An unattended drive that just goes quiet is indistinguishable from one that died.
    The park is what the daemon's away channel already alerts on."""
    _goal(repo, ("ga-1",))
    _ledger(repo, {"item": "i-1", "refs": ["ga-1"]})
    assert _tick(repo).returncode == 1
    names = _parked(repo)
    assert names == ["steer-g-1-met.json"], names
    rec = json.loads((repo / ".workflow" / "parked" / names[0]).read_text())
    assert rec["checkpoint"]["kind"] == "steer"
    assert rec["token"], "a tokenless park can be answered but never resumed"


def test_a_stalled_goal_parks_a_DIFFERENT_steer_ticket(repo):
    """Met and stalled are different asks and must not overwrite each other."""
    _goal(repo, ("ga-1",))
    _ledger(repo, *[{"item": "m-%d" % i, "refs": []} for i in range(6)])
    _tick(repo)
    assert _parked(repo) == ["steer-g-1-stalled.json"]


def test_re_running_the_driver_does_not_file_a_SECOND_ticket(repo):
    """The idempotence that keeps an away channel worth reading. A stalled goal nobody has
    answered yet must not accumulate one ticket per driver launch — that is exactly how a
    human is trained to ignore the notifications."""
    _goal(repo, ("ga-1",))
    _ledger(repo, {"item": "i-1", "refs": ["ga-1"]})
    for _ in range(3):
        _tick(repo)
    assert len(_parked(repo)) == 1


def test_a_pause_does_NOT_park_a_steer(repo):
    """The human who paused already knows. Asking them to answer a checkpoint about their
    own instruction is noise on the channel."""
    _goal(repo, ("ga-1",))
    _pause(repo)
    assert _tick(repo).returncode == 1
    assert _parked(repo) == []


def test_a_no_progress_giveup_does_NOT_park_a_steer(repo):
    """It is the driver's own guard, not a verdict about the goal — it can fire on a
    perfectly healthy goal that is merely blocked."""
    _goal(repo, ("ga-1",))
    v = drive.decide(wf(repo), drive.fingerprint(wf(repo)), drive.MAX_NOPROGRESS - 1)
    assert v["cont"] is False
    assert not v.get("met") and not v.get("stalled")


def test_a_park_failure_never_turns_a_clean_stop_into_a_crash(repo, monkeypatch):
    """The driver has already decided to stop. A failed park must be reported, not fatal."""
    monkeypatch.setattr(drive, "_goal_id", lambda w: "g-1")
    out = drive.park_steer("/nonexistent/nowhere", {"met": True, "reason": "r", "goal": "g-1"})
    assert "error" in out


def test_a_reason_full_of_shell_metacharacters_survives_eval(repo, monkeypatch):
    """The bug the exit test caught, pinned so it cannot come back. Reasons are written for
    humans and contain backticks — "resume with a `control` message" — which inside double
    quotes are COMMAND SUBSTITUTION, not text. json.dumps quoting produced a line `eval` ran as
    a command. The safety must come from the quoting, never from nobody writing an awkward
    sentence, so this asserts against the nastiest reason a human could plausibly provoke."""
    nasty = "`touch /tmp/pwned` $(echo no) 'quoted' \"double\" ; rm -rf / & | still text"
    line = drive._shell({"cont": False, "reason": nasty, "fingerprint": "abc", "streak": 0})
    got = subprocess.run(["bash", "-c", 'eval "$1"; printf %s "$DRIVE_REASON"', "_", line],
                         capture_output=True, text=True)
    assert got.returncode == 0, got.stderr
    assert got.stdout == nasty          # byte-identical: nothing expanded, nothing executed
    assert "command not found" not in got.stderr


def test_a_fingerprint_is_quoted_too(repo):
    """It is hex today. It is quoted anyway — an unquoted field is a bug waiting for the day
    the value changes shape."""
    line = drive._shell({"cont": True, "reason": "ok", "fingerprint": "", "streak": 0})
    got = subprocess.run(["bash", "-c", 'eval "$1"; echo "[$DRIVE_FINGERPRINT]"', "_", line],
                         capture_output=True, text=True)
    assert got.returncode == 0 and got.stdout.strip() == "[]"


def test_tick_exit_code_is_the_spawn_decision(repo):
    d = os.path.join(os.path.dirname(drive.__file__), "drive.py")
    go = subprocess.run([sys.executable, d, "--workflow-dir", wf(repo), "tick"],
                        capture_output=True, text=True)
    assert go.returncode == 0
    _pause(repo)
    stop = subprocess.run([sys.executable, d, "--workflow-dir", wf(repo), "tick"],
                          capture_output=True, text=True)
    assert stop.returncode == 1

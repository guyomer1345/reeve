"""Tests for hooks/ask_guard.py — an unattended drive may not stop to ask a dialog.

The two properties are opposite failures and both get a test. A dialog raised in a supervised
run is the worst halt this package has: it blocks every context reset, the heartbeat reads it as
*a human owes an answer* and goes quiet, and the away channel only alerts on checkpoints — so
the drive stops and nothing says so. And a gate that fired in an INTERACTIVE session would stop
the model talking to the person sitting in front of it, which is worse, because that halt at
least has somebody present to end it.
"""
import json
import os
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent              # product/scripts
HOOK = HERE.parent / "hooks" / "ask_guard.py"


def _run(payload, supervised):
    env = dict(os.environ)
    env.pop("REEVE_SUPERVISE", None)
    if supervised:
        # Exactly what `loop.sh --supervise` exports into the session it starts. The
        # environment IS the proof the session was launched unattended — no file, no guess.
        env["REEVE_SUPERVISE"] = "1"
    return subprocess.run(["python3", str(HOOK)], input=json.dumps(payload),
                          capture_output=True, text=True, env=env)


def _ask(questions=None):
    return {"tool_name": "AskUserQuestion",
            "tool_input": {"questions": questions if questions is not None else
                           [{"header": "Auth method", "question": "Which auth?"}]}}


# --- the halt it exists to prevent -------------------------------------------

def test_an_unattended_session_may_NOT_raise_a_dialog():
    r = _run(_ask(), supervised=True)
    assert r.returncode == 2, r.stderr
    assert "BLOCKED" in r.stderr


def test_the_block_ROUTES_rather_than_merely_refusing():
    """`guard.sh`'s shape: a block that only says no teaches nothing and gets worked around.
    Both owners are named, because which one applies is the autonomy floor's question."""
    err = _run(_ask(), supervised=True).stderr
    assert "reeve:decision-engineer" in err, err      # a BUILD decision
    assert "reeve:checkpoint" in err, err             # a PRODUCT-OWNER decision
    # and the third case: wanting a fact is not wanting a decision
    assert "reeve:research" in err, err


def test_the_block_SAYS_WHY_the_halt_is_the_dangerous_kind():
    """A gate whose reason is "not allowed" gets re-tried. This one has to carry the mechanism,
    because the cost is invisible from inside the session that pays it."""
    err = _run(_ask(), supervised=True).stderr
    assert "reset" in err and "checkpoint" in err


def test_the_open_questions_are_NAMED_in_the_block():
    """So the loop can route THIS question rather than guess which of several it was."""
    err = _run(_ask([{"header": "Stack choice", "question": "Postgres or SQLite?"}]),
               supervised=True).stderr
    assert "Stack choice" in err


# --- the opposite failure: never gag an interactive session ------------------

def test_an_INTERACTIVE_session_asks_freely():
    """A human is sitting there; asking them is the correct thing to do."""
    r = _run(_ask(), supervised=False)
    assert r.returncode == 0 and not r.stderr.strip()


def test_another_tool_is_never_touched():
    r = _run({"tool_name": "Bash", "tool_input": {"command": "ls"}}, supervised=True)
    assert r.returncode == 0 and not r.stderr.strip()


# --- fail direction: allow ---------------------------------------------------

def test_an_UNREADABLE_payload_lets_the_question_through():
    """FAIL OPEN, throughout. A gate that blocked a question it could not classify would be a
    gate that silences an interactive session over a parse error."""
    env = dict(os.environ)
    env["REEVE_SUPERVISE"] = "1"
    r = subprocess.run(["python3", str(HOOK)], input="{not json at all",
                       capture_output=True, text=True, env=env)
    assert r.returncode == 0


def test_a_dialog_with_NO_questions_still_blocks_and_says_less():
    """The naming is best-effort; the gate is not. A malformed `questions` must not become a
    way through."""
    r = _run({"tool_name": "AskUserQuestion", "tool_input": {}}, supervised=True)
    assert r.returncode == 2
    assert "decision-engineer" in r.stderr


def test_an_EMPTY_supervise_flag_is_not_supervision():
    """`REEVE_SUPERVISE=` is what an unset-but-exported variable looks like, and it must read as
    an ordinary interactive session rather than as proof of anything."""
    env = dict(os.environ)
    env["REEVE_SUPERVISE"] = ""
    r = subprocess.run(["python3", str(HOOK)], input=json.dumps(_ask()),
                       capture_output=True, text=True, env=env)
    assert r.returncode == 0

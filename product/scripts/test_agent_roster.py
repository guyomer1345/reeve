"""The agent roster's frontmatter invariants, made mechanical.

These have been true since the roster split and were held only by prose — the roster doc
asserts that every dispatched agent's `tools:` line carries them, which is a claim nothing
checked. Adding a sixth agent is the moment that stops being acceptable: the invariants are
what make the hub-and-spoke topology real, and a topology enforced by remembering is a
topology that survives exactly until someone copies a frontmatter block.

WHY `Task`/`Agent` MATTERS MOST. A leaf that can spawn is not a leaf, and the whole cost
argument for dispatching rests on a worker's context never landing in the router's. A leaf that
spawns also quietly acquires the authority it was built not to have: `execute` and `planner`
both stop on an undecided question and hand it back precisely because they *cannot* resolve it
themselves. Give either one a dispatch tool and the discipline becomes a preference.
"""
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
AGENTS = os.path.normpath(os.path.join(HERE, "..", "agents"))

SPAWN = {"task", "agent"}
WEB = {"websearch", "webfetch"}
# The two writers. A writer that can browse is a writer that improvises: anything it would have
# looked up is missing plan input, and the correct move is to return a blocker to the caller.
NO_WEB = {"execute", "create-demo", "planner"}


def _agents():
    out = {}
    for name in sorted(os.listdir(AGENTS)):
        if not name.endswith(".md"):
            continue
        with open(os.path.join(AGENTS, name), encoding="utf-8") as fh:
            out[name[:-3]] = fh.read()
    return out


def _tools(body):
    m = re.search(r"^tools:\s*(.+)$", body, re.M)
    assert m, "every agent must declare `tools:` — an absent line inherits everything"
    return {t.strip().lower() for t in m.group(1).split(",") if t.strip()}


def test_the_roster_is_not_empty():
    assert len(_agents()) >= 6


def test_no_agent_can_spawn():
    for name, body in _agents().items():
        assert not (_tools(body) & SPAWN), "%s can spawn; a leaf that spawns is not a leaf" % name


def test_no_agent_body_claims_to_call_another_capability():
    """The prose half of the same invariant. `## Calls` on a leaf must say so explicitly rather
    than naming a capability, or the file and its frontmatter disagree about what it is."""
    for name, body in _agents().items():
        m = re.search(r"^## Calls\s*\n(.+?)(?=\n## |\Z)", body, re.M | re.S)
        if not m:
            continue
        assert re.match(r"\s*(none|nothing)\b", m.group(1).strip(), re.I), \
            "%s declares Calls; a leaf worker spawns nothing" % name


def test_the_writers_have_no_web_tools():
    for name in NO_WEB:
        assert not (_tools(_agents()[name]) & WEB), \
            "%s can browse; what it would look up is missing input, not something to fetch" % name


def test_planner_is_an_agent_and_returns_decisions_rather_than_resolving_them():
    """The move that made waves possible: `planner` was inline solely because it spawned
    `decision-engineer`, and N heavy planning passes inline is the router's window spent on the
    work fan-out exists to move off it."""
    body = _agents()["planner"]
    assert "decision-engineer" in body                      # it still knows where they go
    assert re.search(r"blocker", body, re.I)
    assert "Never spawn sub-agents" in body

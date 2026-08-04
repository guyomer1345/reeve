"""Tests for skills/answer/SKILL.md — the ONE thing about it a machine can settle.

WHY A TEST OVER PROSE AT ALL. `answer` is specified entirely in prose; there is no
estimate-and-decide code seam to reach (D170 checked: `rotate_at_tokens` appears only in
this skill and the schema docs, and `bus.py` merely *displays* `rotations`). But the
defect that shipped was not a judgment call — it was an ORDERING, and an ordering over
numbered steps is decidable. The bug: steps ran 4 append -> 5 rotate -> 6 record, and
rotation CLEARS `turns`, which carry the idempotency anchor step 2 depends on. A crash in
that window left the message unrecorded AND unanchored, so the retry answered twice — the
exact outcome the anchor exists to prevent.

HONEST CEILING, stated so nobody mistakes this for more than it is: this asserts that the
SPEC still says the right thing. It cannot assert that the model FOLLOWS the spec — no
test in this package can, because there is no seam between the prose and the behaviour.
What it buys is that a future edit which re-orders the steps fails loudly here instead of
silently in a crash window nobody drives. That is regression cover for the specification,
and it is the only mechanical cover available. The behaviour itself is proven by driving
it (D170), not by this file.

A rename that breaks the anchors below is the CORRECT failure — same philosophy as
`test_bus._js_function`: run the real shipped source, never a copy of it that can drift.
"""
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent                       # product/scripts
SKILL = HERE.parent / "skills" / "answer" / "SKILL.md"
SCHEMAS = HERE.parent / "shared" / "schemas.md"


def _steps(text):
    """{step number: body} for the numbered steps under `## Workflow`.

    Parsed from the real file rather than matched as substrings: a substring check would
    still pass if a future edit renumbered the steps while leaving the order broken, and
    the number IS the ordering.
    """
    body = text.split("## Workflow", 1)[1].split("\n## ", 1)[0]
    steps, cur = {}, None
    for line in body.splitlines():
        head = line.split(". ", 1)
        if len(head) == 2 and head[0].strip().isdigit():
            cur = int(head[0].strip())
            steps[cur] = head[1]
        elif cur is not None:
            steps[cur] += "\n" + line
    return steps


def _step_named(steps, directive):
    """The step whose BOLD LEAD is `directive` — its instruction, not its prose.

    Matching anywhere in the body is wrong and was measured wrong: step 2 legitimately
    *mentions* `drain.py record` while explaining the anchor, so a body match reports two
    record steps and the ordering assertion becomes meaningless. A step is identified by
    what it tells you to do.
    """
    hits = [n for n, b in steps.items() if b.strip().startswith("**" + directive + "**")]
    assert len(hits) == 1, "expected exactly one step led by %r, got %r" % (directive, hits)
    return hits[0]


def test_record_precedes_rotate():
    """The whole defect in one assertion: consume the message before destroying the anchor."""
    steps = _steps(SKILL.read_text(encoding="utf-8"))
    record = _step_named(steps, "`drain.py record`")
    rotate = _step_named(steps, "Rotate if the thread is over budget.")
    assert record < rotate, (
        "answer/SKILL.md rotates (step %d) BEFORE recording (step %d). Rotation clears "
        "`turns`, which carry step 2's idempotency anchor — so a crash in that window "
        "leaves the message unrecorded AND unanchored, and the retry answers it twice."
        % (rotate, record))


def test_the_append_step_still_precedes_both():
    """The anchor covers exactly the append->record window; append must open it.

    Asserted because the fix is a swap of the LAST two steps, and the swap is only safe if
    it leaves this window untouched — which is the claim the whole idempotency story rests
    on, and therefore the claim worth pinning rather than assuming.
    """
    steps = _steps(SKILL.read_text(encoding="utf-8"))
    append = _step_named(steps, "Append the turns")
    record = _step_named(steps, "`drain.py record`")
    rotate = _step_named(steps, "Rotate if the thread is over budget.")
    assert append < record < rotate
    # ...and nothing was inserted between them: the window the anchor covers must stay
    # exactly one step wide, which is what makes "unchanged by the swap" a fact.
    assert record == append + 1


def test_the_post_rotation_idempotency_story_is_written_down():
    """Post-rotation the anchor is UNREACHABLE and only the watermark carries idempotency.

    That is correct — rotation runs after the record, so a rotated message is already
    consumed — but it was unsaid, and an unsaid invariant is one the next reader re-breaks.
    """
    steps = _steps(SKILL.read_text(encoding="utf-8"))
    assert "watermark" in steps[2], (
        "step 2 must say that after a rotation the anchor is gone and idempotency rests "
        "on the drain watermark alone")


def test_the_schema_and_the_skill_do_not_disagree_about_the_order():
    """`schemas.md` POINTS at this order (it does not own it). A silent drift between the
    two is how a reader ends up trusting whichever they opened first."""
    assert "Rotation happens only after `drain.py record`" in SCHEMAS.read_text(encoding="utf-8")


def test_the_handoff_carry_list_forbids_project_prose():
    """The structural half of the laundering fix: what rotation may carry is a FLOOR.

    Not a test of the distillation itself — that is judgment and unreachable. It pins that
    the rule survives in the two places that state it, because the fix IS the rule.
    """
    skill = SKILL.read_text(encoding="utf-8")
    schemas = SCHEMAS.read_text(encoding="utf-8")
    assert "none of your own prose answers" in skill
    assert "It carries NO project prose answer" in schemas
    assert "the human's turns verbatim" in schemas


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))

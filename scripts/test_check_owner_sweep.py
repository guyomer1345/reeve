"""Tests for check_owner_sweep.py — the backstop for the sweep nobody remembers to run.

Meta-only. These pin the three invariants against SYNTHETIC text rather than the live docs, for the
reason the autonomy-floor tests give: a test that reads the working record fails the day somebody
edits it, and then proves nothing about the check.

Both invariants were written against real drift found in one sitting — a `07` question closed by
a decision `07` never heard of, and an ask carrying two queue entries — so each has a test for
the shape that was actually found, not an idealised one.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_owner_sweep as cs


# --- invariant 1: a settled question is struck -------------------------------

LOG_CLAIMS = """## D100 — something unrelated
Body text.

## D183 — `building` with no current item is LEGAL **[DECIDED · BUILT in D188 — settles the question `07` names as upstream]**
Body.

## D190 — another one
Body.
"""


def test_a_settle_claim_with_no_mark_in_07_is_flagged():
    """The real shape: the decision's own header says it settled the question, and `07` still
    reads as open, so the next reader picks up work that is already done."""
    out = cs.settled_questions_are_struck(LOG_CLAIMS, "nothing about it here")
    assert len(out) == 1 and "D183" in out[0]


def test_a_settle_claim_that_07_acknowledges_is_clean():
    out = cs.settled_questions_are_struck(
        LOG_CLAIMS, "- **~~the thing~~ `[CLOSED (D183) — BUILT in D188]`** ...")
    assert out == []


@pytest.mark.parametrize("verb", ["settles", "closes", "answers", "discharges"])
def test_every_claim_verb_counts(verb):
    log = "## D7 — a decision that %s the question `07` raised\nBody.\n" % verb
    assert len(cs.settled_questions_are_struck(log, "")) == 1


def test_a_decision_that_merely_TOUCHES_07_is_not_a_claim():
    """Thirty-odd decisions name `07` in their trailer because they edited it. Treating that as a
    claim would make this gate fire constantly and get switched off."""
    log = "## D9 — a decision\nBody about things.\n→ `05`, `07`, `11`.\n"
    assert cs.settled_questions_are_struck(log, "") == []


def test_the_verb_and_the_reference_must_be_on_ONE_line():
    """A paragraph that happens to contain both is not a claim about that document."""
    log = "## D9 — a decision\nThis closes a long-standing problem.\nSeparately, `07` lists more.\n"
    assert cs.settled_questions_are_struck(log, "") == []


def test_a_claim_before_any_heading_is_ignored():
    """Preamble text belongs to no decision, so there is nothing to require of `07`."""
    log = "Intro that closes the question `07` asks.\n\n## D1 — real\nBody.\n"
    assert cs.settled_questions_are_struck(log, "") == []


# --- invariant 2: an ask has one entry ---------------------------------------

def test_an_ask_with_a_closed_AND_an_open_entry_is_a_GHOST():
    """The real shape: `12g` closed it, and the older queue entry proposing exactly what `12g`
    built stayed behind."""
    roadmap = (
        "#### `12g` — never wait alone, ENFORCED. ✅ **CLOSED 2026-09-14 — `D216`.** `[ask #6]`\n"
        "body\n"
        "#### Then — never wait alone, ENFORCED. `[ask #6]` `[core]`\n"
        "body\n")
    out = cs.one_entry_per_ask(roadmap)
    assert len(out) == 1 and "ask #6" in out[0]


def test_one_closed_entry_is_clean():
    assert cs.one_entry_per_ask(
        "#### `12f` — the band. ✅ **CLOSED — `D215`.** `[ask #9]`\n") == []


def test_one_open_entry_is_clean():
    """An ask still to be built is the normal state and must never be flagged."""
    assert cs.one_entry_per_ask("#### Then — bounding a WORKER. `[asks #3 + #7]`\n") == []


def test_two_entries_that_are_BOTH_open_is_not_this_finding():
    """Two open entries for one ask is untidy but not a ghost — nothing has been built twice.
    Flagging it would put noise in a gate whose value is that it is quiet."""
    assert cs.one_entry_per_ask(
        "#### A — `[ask #3]`\n#### B — `[ask #3]`\n") == []


def test_a_tick_alone_counts_as_closed():
    """Headings mark closure either way; reading only the word would miss half of them."""
    roadmap = "#### `12x` — done ✅ `[ask #4]`\n#### Then — the same thing `[ask #4]`\n"
    assert len(cs.one_entry_per_ask(roadmap)) == 1


def test_only_H4_QUEUE_headings_are_read():
    """Prose mentioning an ask, and the ACCEPTANCE LEDGER table above the queue, must not read as
    queue entries — the ledger names every ask and would collide with all of them."""
    roadmap = ("| 6 | use the hangs | `12g` · `D216` | ✅ |\n"
               "Some prose about `[ask #6]` being closed.\n"
               "#### `12g` — ENFORCED ✅ **CLOSED** `[ask #6]`\n")
    assert cs.one_entry_per_ask(roadmap) == []


# --- the gate as a whole -----------------------------------------------------

def test_the_live_repo_is_clean():
    """The one test that DOES read the working record, deliberately: these invariants exist to
    hold on this repo, and a green suite over synthetic text while the real docs drift is the
    exact failure mode both of them describe."""
    assert cs.run() == [], cs.run()


def test_the_cli_exit_code_is_the_verdict():
    assert cs.main([]) == 0


# --- invariant 3: an ask has SOMETHING against it ----------------------------
# `D214`'s own defect, mechanized. Five asks of ten closed while unmet because the request had no
# owner; the ledger gave it one, and this makes the owner check itself rather than relying on
# whoever remembers to re-read both tables. Note the shape it must NOT have: requiring a tagged
# queue entry would fire on the seven historical rows that predate the tag or were discharged by
# a disposition, and a gate needing seven exemptions is a gate somebody switches off.

LEDGER = """### The Phase-9 ACCEPTANCE LEDGER — what was asked for
Preamble prose.

| # | The ask | Discharged by | State |
|---|---|---|---|
| 1 | a thing he asked for | `9a` · `D100` | OK |
| 2 | another thing | %s | %s |

### The ordered build sequence
#### `9a` — the thing. CLOSED — `D100`. `[ask #1]`
Body.
"""

LOG3 = "## D100 — a decision\nBody.\n"


def _ledger(cell, state="open", tail=""):
    return (LEDGER % (cell, state)) + tail


def test_an_ask_with_NOTHING_against_it_is_flagged():
    """The exact state that lost five of ten: a row nobody built and nobody dispositioned."""
    out = cs.every_ask_has_an_entry(_ledger(""), LOG3)
    assert len(out) == 1 and "ask #2" in out[0]


def test_a_tagged_queue_entry_discharges_it():
    out = cs.every_ask_has_an_entry(
        _ledger("", tail="#### `9b` — the other thing. `[ask #2]`\n"), LOG3)
    assert out == []


def test_a_DISPOSITION_counts_as_a_discharger():
    """Two of the ten real rows are `answered — they do` and `parked`. Neither is a slice and
    both are legitimate; a gate that called them missing would be wrong about the thing it is
    named for."""
    assert cs.every_ask_has_an_entry(_ledger("answered — they do", "done"), LOG3) == []
    assert cs.every_ask_has_an_entry(_ledger("parked", "done"), LOG3) == []


@pytest.mark.parametrize("cell", ["-", "—", "TBD", "?", "n/a", "none", "**—**"])
def test_a_cell_that_only_LOOKS_filled_is_still_empty(cell):
    assert len(cs.every_ask_has_an_entry(_ledger(cell), LOG3)) == 1


def test_a_citation_to_a_decision_NOBODY_WROTE_is_refused():
    """A discharge that cites a decision the log does not contain reads exactly like a
    discharge — and is the cheapest way for a row to look green while naming nothing."""
    out = cs.every_ask_has_an_entry(_ledger("`9z` · `D999`", "done"), LOG3)
    assert len(out) == 1 and "D999" in out[0]


def test_rows_OUTSIDE_a_ledger_table_are_not_asks():
    """The roadmap carries other tables; a bare `| 3 |` in one of them is not an ask."""
    text = ("### Some other section\n\n| # | thing | owner | state |\n"
            "|---|---|---|---|\n| 3 | a row in an unrelated table | | |\n")
    assert cs.every_ask_has_an_entry(text, LOG3) == []


def test_the_ledger_scope_ENDS_at_the_next_heading_of_equal_depth():
    text = _ledger("`9a`", "done") + ("\n| 7 | a row under the build sequence heading | | |\n")
    assert cs.every_ask_has_an_entry(text, LOG3) == [], "scope leaked past the ledger section"


def test_the_live_docs_pass_all_three():
    """The one test that reads the real record — not to pin its content, but because a gate
    added in the same commit as the rows it grades must be shown to grade them green."""
    assert cs.run() == []

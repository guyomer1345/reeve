#!/usr/bin/env python3
"""What does this turn OWE before it is allowed to end? -- the unattended-drive turn ladder.

TWO COMPLAINTS, ONE CATCH POINT. The maintainer, after living in the loop: *"the workflow pauses
a lot for no reason ... sometimes its really minor decisions that have no reason to stop and wait
for my intervence, sometimes it says 'okay now doing X' and never dispatches X"*, and separately
that the reports he gets are long, jumbled, and full of ids that mean nothing to him. Both of
those happen at exactly the same instant -- **the turn ends** -- and that instant is decidable,
which is why the answer to both lives here instead of in a rule nobody can enforce.

THE LADDER, in order. The first rung that has something to say wins; a turn told two things at
once obeys neither.

  1. MAY THIS TURN END AT ALL? In an unattended drive, ending is an EVENT, not a default: it
     hands the machine back to a human who is not there. So it requires a reason, and the set of
     reasons is closed and mechanical --
         · something is PARKED (the human genuinely owes an answer),
         · the goal is MET or STALLED (`converge.py`, the same verdict the driver stops on),
         · the loop is PAUSED (`control.json`, the operator's own latch),
         · the loop is `idle` -- backlog empty, awaiting steering,
         · the loop is not `building` at all, so there is nothing in flight to abandon.
     None of those ⇒ the session is stopping for nothing, which is the complaint verbatim. The
     block says WHICH of the two shapes it is, because they send the reader to different places:
     a turn that moved no anchor said it would do something and did not; a turn that moved
     anchors and stopped anyway finished a piece and quit instead of picking up the next.
  2. IS THE ANCHOR AN ANCHOR? `handoff.md` carries one load-bearing field -- `base_sha`, the
     commit a resumed session reads `git log <base_sha>..HEAD` against. It was ASKED FOR in
     `/dispatch` and in `handoff_gate.py`'s instruction, and CHECKED nowhere except under
     context pressure, so the ordinary path -- a session rewriting the anchor at the end of an
     item, with plenty of context left -- could leave a handoff that is prose with no resume in
     it. A real greenfield drive did exactly that, twice, while brownfield's was fine; the seam
     that caught it is in `smoke_drive.py` and nothing inside the package was looking. This rung
     fires ONLY when the file exists and the field does not: a project that has written no
     anchor at all is `handoff_gate.py`'s business, under the band, and is not touched here.
  3. IS THE REPORT CURRENT? A turn that may legitimately end must leave the four-field,
     goal-relative report behind it (`status_report.py`), because the human's next contact with
     this project is reading it.

WHY A CLOSED SET OF REASONS RATHER THAN A JUDGEMENT. Every rung reads durable state the session
does not author for this purpose -- the same discipline `drive.py` argues for its own stop
predicates, and for the same reason: a session that wants to stop is the last thing that should
be asked whether stopping is allowed. Nothing here asks the model anything.

WHAT THIS DELIBERATELY DOES NOT DO. It does not decide whether a PARK was justified -- that is
`bus.py park`'s refusal, at the moment of parking, where the evidence is. A turn-end gate that
re-litigated a park would be judging a decision already made, and its only available verdict
(block the stop) would trap the session with a ticket it cannot un-park.

FAIL DIRECTION IS PERMISSIVE, on every path. Unreadable state, no goal, no git -- every one of
them returns "may end". The gate exists to stop a session from quitting for nothing; a gate that
stopped a session from quitting *at all* would be the more expensive failure by a wide margin,
and it is the failure that cannot be recovered by typing the command again.

Usage:
    python3 turn_check.py [--workflow .workflow]            # what this turn owes, in English
    python3 turn_check.py --json
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)


def _json_file(path):
    try:
        with open(path, encoding="utf-8") as fh:
            val = json.load(fh)
    except (OSError, ValueError):
        return None
    return val if isinstance(val, dict) else None


def _parked(workflow):
    d = os.path.join(workflow, "parked")
    try:
        return sorted(n for n in os.listdir(d) if n.endswith(".json"))
    except OSError:
        return []


def may_end(workflow):
    """-> (True, why it may) | (False, why it may not). The closed set, in one function."""
    state = _json_file(os.path.join(workflow, "state.json"))
    if state is None:
        return True, "no readable state.json — nothing to be sure about, so nothing to block"
    status = state.get("status")
    if status != "building":
        return True, "the loop is `%s`, not building" % status
    tickets = _parked(workflow)
    if tickets:
        return True, "%d checkpoint(s) parked — the human genuinely owes an answer" % len(tickets)
    control = _json_file(os.path.join(workflow, "control.json")) or {}
    if control.get("paused"):
        return True, "the loop is paused by the operator"
    try:
        import converge
        m = converge.measure(converge.read_goal(workflow), converge.read_ledger(workflow),
                             converge.open_bindings(workflow))
    except Exception:
        return True, "convergence could not be measured — permissive by design"
    if m.get("met"):
        return True, "the goal is met"
    if m.get("stalled"):
        return True, "the goal is stalled — %s promotions with no new acceptance" % m.get("streak")
    return False, ("the loop is building, nothing is parked, the goal is neither met nor stalled "
                   "and the operator has not paused — there is no reason for this turn to end")


def moved(workflow, prev_fingerprint):
    """Did anything durable move since the previous turn ended? None ⇒ cannot tell.

    Reuses `drive.py`'s fingerprint rather than inventing a second notion of progress: HEAD plus
    the per-item anchor set, presence-only. One definition of "the loop moved", used by the
    driver that decides whether to spawn and by the gate that decides whether a turn may stop.
    """
    try:
        import drive
        now = drive.fingerprint(workflow)
    except Exception:
        return None, None
    if now is None or prev_fingerprint is None:
        return None, now
    return (now != prev_fingerprint), now


CONTINUE = (
    "TURN GATE — %s\n\n"
    "Do not end this turn. One of these, and nothing else:\n"
    "1. **Continue the loop.** Pick up where `.workflow/state.json` says you are and dispatch "
    "the next node. If you named an action this turn and did not take it, take it now — that is "
    "the exact failure this gate exists for.\n"
    "2. **Resolve the decision yourself** if you stopped because something was undecided. An "
    "open build decision goes to `reeve:decision-engineer`, not to the human; a plan assumption "
    "that turned out false goes to `reeve:refine`. Only a goal-changing or spec-changing "
    "question belongs to a person.\n"
    "3. **Park a checkpoint** if it truly does belong to a person — `python3 "
    ".claude/scripts/bus.py park` with one of the seven kinds. A parked ticket is a legitimate "
    "reason to end; a question typed into your reply is not, because nobody is reading it.\n"
    "4. **Stop properly** if the work is genuinely finished: the backlog being empty means "
    "`state.json` says `idle`, and the goal being met means `converge.py` says so."
)

REPORT = (
    "TURN GATE — %s\n\n"
    "Before this turn ends, leave the human the current report. Run it and paste the WHOLE "
    "block, verbatim, as the last thing in your reply:\n"
    "    python3 .claude/scripts/status_report.py --workflow .workflow\n"
    "Do not retype it, do not summarise it, do not reorder the fields, and do not drop the "
    "`[reeve-report state:…]` line — that line is how this gate recognises a current report, and "
    "a hand-written one will simply be asked for again. Anything you want to say beyond the four "
    "fields goes ABOVE the block, in prose, with every id named: write `D-001 (the thing it "
    "decided)`, never a bare `D-001`."
)


ANCHOR = (
    "TURN GATE — %s\n\n"
    "`.workflow/handoff.md` exists but is not a resume anchor: it names no `base_sha`, so a "
    "session that picks this project up cannot run `git log <base_sha>..HEAD` and cannot see "
    "what moved while you held it. Fix the file you already wrote — do not rewrite it whole and "
    "do not start new work:\n"
    "1. `git rev-parse HEAD`\n"
    "2. Add a `base_sha: <that id>` line near the top of `.workflow/handoff.md`, with Write/Edit "
    "and never a Bash `>` redirect. Say in the same line what the commit is (`F1-1's base; this "
    "session's commit sits on top`) so a stranger knows what it anchors.\n"
    "3. Leave both machine blocks (`drain:begin…`, `parked:begin…`) byte for byte, and leave the "
    "rest of the anchor alone — the prose is fine, it is the one field that is missing."
)


def check(workflow, last_text="", prev_fingerprint=None, satisfied_digest=None):
    """-> {demand: None|'continue'|'anchor'|'report', why, instruction, fingerprint, digest}.

    `last_text` is the session's final assistant message; the report rung looks for the
    renderer's marker in it. `satisfied_digest` is the digest this session last satisfied, which
    is what stops an unchanged loop being asked for the same report twice.
    """
    out = {"demand": None, "why": "", "instruction": "", "fingerprint": None, "digest": None}
    ok, why = may_end(workflow)
    changed, fp = moved(workflow, prev_fingerprint)
    out["fingerprint"] = fp
    if not ok:
        shape = {
            True: " This turn DID move the loop and then stopped anyway — finish the next node "
                  "rather than handing back a machine nobody is watching.",
            False: " This turn moved NOTHING durable: no commit, no plan, no changelog, no "
                   "verdict. That is the shape of announcing an action and not taking it.",
            None: "",
        }[changed]
        out.update(demand="continue", why=why, instruction=CONTINUE % (why + shape))
        return out

    # RUNG 2 -- the anchor exists but cannot be resumed from. Between the two on purpose:
    # losing the loop's place costs more than a stale report, and less than a session that
    # announced work and abandoned it. `anchor_names_base` is `context_band`'s, not a second
    # matcher -- one owner for "does this name a base commit", which is the whole point of
    # reusing it rather than re-deriving the regex here.
    handoff = os.path.join(workflow, "handoff.md")
    if os.path.exists(handoff):
        try:
            import context_band as cb
            named = cb.anchor_names_base(handoff)
        except Exception:
            named = True                # cannot tell -> permissive, like every other path here
        if not named:
            why = ("the resume anchor names no `base_sha`, so nothing can tell what moved "
                   "while this session held the project")
            out.update(demand="anchor", why=why, instruction=ANCHOR % why)
            return out

    try:
        import status_report as sr
        report = sr.build(workflow)
        out["digest"] = sr.digest(report)
    except Exception:
        return out                      # no renderer, no demand — permissive by design
    found = {m.group(1) for m in sr.MARKER_RE.finditer(last_text or "")}
    if out["digest"] in found or satisfied_digest == out["digest"]:
        return out
    why = ("the report in this turn is stale — the loop has moved since"
           if found else "no goal report was given this turn")
    out.update(demand="report", why=why, instruction=REPORT % why)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--workflow", default=".workflow")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    if not os.path.isdir(args.workflow):
        print("no %s here" % args.workflow, file=sys.stderr)
        return 2
    # Asked from a command line there is no transcript and no latch, so this reports the rung
    # that WOULD fire on a bare turn end — which is the question a human asking it has.
    res = check(args.workflow)
    if args.json:
        print(json.dumps(res, indent=2, sort_keys=True))
    elif res["demand"]:
        print("OWES: %s — %s" % (res["demand"], res["why"]))
    else:
        print("owes nothing: this turn may end")
    return 0


if __name__ == "__main__":
    sys.exit(main())

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
     WITH NO GOAL AT ALL, `met` and `stalled` are not false -- they are UNREACHABLE, so the
     rung says that instead of reporting "neither met nor stalled", which is a claim about a
     goal that does not exist. A goal is genuinely optional (`drive.py` drives item-at-a-time
     without one), so its absence is only a DEMAND once the loop has PLANNED work: inception
     is what mints it (`planner:decompose` greenfield, the `reconcile` checkpoint brownfield),
     and BOTH paths mint it before anything is planned, so an item with a plan and no goal is
     inception skipped rather than inception in progress. Measured three times, and the sibling
     of the dispatch rung below -- that one catches the orchestrator doing a node's work itself,
     and structurally cannot catch a node that never ran at all.
     PLANNED, NOT PROMOTED, and the difference is a whole drive: the third occurrence dispatched
     exactly two workers -- `research`, then `planner` in plan-one mode on a roadmap item the
     router had minted ITSELF -- and never promoted anything at all. A rung keyed on promotion
     sat silent for the entire session. Planning is the earliest point at which the goal is
     unambiguously late, so it is where this fires.
  2. IS THE ANCHOR AN ANCHOR? `handoff.md` carries one load-bearing field -- `base_sha`, the
     commit a resumed session reads `git log <base_sha>..HEAD` against. It was ASKED FOR in
     `/dispatch` and in `handoff_gate.py`'s instruction, and CHECKED nowhere except under
     context pressure, so the ordinary path -- a session rewriting the anchor at the end of an
     item, with plenty of context left -- could leave a handoff that is prose with no resume in
     it. A real greenfield drive did exactly that, twice, while brownfield's was fine; the seam
     that caught it is in `smoke_drive.py` and nothing inside the package was looking. This rung
     fires ONLY when the file exists and the field does not: a project that has written no
     anchor at all is `handoff_gate.py`'s business, under the band, and is not touched here.
  3. WAS THE WORK DISPATCHED? `planner`, `execute` and `document` are dispatch-only -- "you
     never do a node's work yourself", "a property of the node, not a judgement call". A real
     drive took an item all the way round -- built, verified, documented, committed -- with no
     worker anywhere, twice, on both modes, and the item looked perfect: that is what makes this
     worth a rung. The cost is invisible and compounding: the router's context holds what a
     worker would have held, the worker token cap has nothing to cap, a wave has nothing to run
     in parallel, and `execute`'s refusal to guess is replaced by the router simply deciding.
     It fires ONCE per item, on the turn the item is promoted, and it does NOT ask for a
     rebuild -- the correction it wants is the next item, dispatched.
  4. IS THE REPORT CURRENT? A turn that may legitimately end must leave the four-field,
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
    if m.get("goal") is None:
        # NOT permissive, and not the same sentence with a word changed: with no goal there is
        # no `met` and no `stalled` to reach, so saying "neither met nor stalled" asserts
        # something about a goal that does not exist. Which of the two stops this drive has
        # left -- an empty backlog, or the no-progress guard -- is `drive.py`'s, and neither
        # of them is DONE. The two ways to have no goal are kept apart here for the same reason
        # the rung below keeps them apart: one is a node that never ran, the other is a file to
        # repair, and they send the session to different places.
        return False, ("the loop is building, nothing is parked, the operator has not paused, "
                       "and %s — so `met` and `stalled` are both unreachable and this drive "
                       "has no stop-when-done condition at all"
                       % ("NO GOAL IS SET" if _goal_missing(workflow) else
                          "the goal file is present but could not be read as a goal"))
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


def _goal_missing(workflow):
    """True only when the goal file is CONFIRMED ABSENT — which is not the same question as
    `converge.read_goal() is None`, and the difference is the whole rung: that returns None for
    a goal that exists and will not parse too. This demand says *you skipped the node that
    mints it*, and sending a session to re-mint a goal already sitting on disk is a worse turn
    than the one it replaced."""
    try:
        import converge
        name = converge.GOAL_FILE
    except Exception:
        return False                    # cannot even name the file -> say nothing
    return not os.path.exists(os.path.join(workflow, name))


def _planned_items(workflow):
    """-> item ids that exist at all. `planner` mkdirs the item dir when it plans, so the
    directory IS the evidence that planning happened -- and it survives `retention.py` pruning
    `plan.md` away at promote time, which is why this asks about the dir rather than the file."""
    idir = os.path.join(workflow, "items")
    try:
        return sorted(n for n in os.listdir(idir)
                      if os.path.isdir(os.path.join(idir, n)))
    except OSError:
        return []


def promoted_items(workflow):
    """-> sorted ids carrying `promoted.json` — the package's own finished marker.

    Not a notion invented here: `check_wave_independence.py` treats it as "dependency finished",
    `retention.py` keys pruning on it, and `forecast.py` prunes a forecast against it. Written by
    `document`, so it also means the item reached the tail of the loop rather than dying earlier.
    """
    idir = os.path.join(workflow, "items")
    out = []
    for name in sorted(os.listdir(idir)) if os.path.isdir(idir) else []:
        rec = _json_file(os.path.join(idir, name, "promoted.json"))
        if isinstance(rec, dict) and rec.get("promoted"):
            out.append(name)
    return out


DISPATCH = (
    "TURN GATE — %s\n\n"
    "`planner`, `execute` and `document` are DISPATCHED, not performed here. The brief puts it "
    "as plainly as it can: *you never do a node's work yourself*, and the mechanism is *a "
    "property of the node, not a judgement call*. This turn finished an item with no worker "
    "behind it anywhere, which means the router did the work.\n\n"
    "What it costs, so this reads as a reason and not a rule: your own context holds everything "
    "a worker would have held and handed back as a pointer, so the window runs out sooner and "
    "every reset loses more; the worker token budget has nothing to cap; a wave cannot run two "
    "items at once because there is nothing to run in parallel; and `execute`'s refusal to guess "
    "is gone — it stops and returns a blocker on an undecided question, and you simply decided.\n"
    "\n"
    "The item that is built is built; do not rebuild it. Before this turn ends:\n"
    "1. Say plainly, in your reply, which item was built without dispatch and that it was.\n"
    "2. File it with `python3 .claude/scripts/bus.py` or into `.workflow/backlog.md` if its "
    "quality is now in doubt — an item nothing reviewed is not the same as an item `verify` "
    "passed on a worker's changelog.\n"
    "3. Take the NEXT item through `reeve:planner` and `reeve:execute` as dispatches. That is "
    "the correction this gate is actually asking for."
)


GOAL = (
    "TURN GATE — %s\n\n"
    "This loop has PLANNED work and has no `.workflow/goal.json`, which means the node that "
    "mints one never ran: `planner:decompose` on the greenfield path, the `reconcile` "
    "checkpoint on the brownfield one. Nothing failed loudly — the gates that read convergence "
    "simply have nothing to read, so the drive cannot stop on DONE, no plan criterion carries "
    "a `goal_ref`, and `status_report.py` has no goal to be relative to.\n\n"
    "One of these, and not a third:\n"
    "1. **Mint it.** Greenfield: dispatch `reeve:planner` in decompose mode over the spec and "
    "let it write `goal.json` from the roadmap it emits. Brownfield: the reconcile checkpoint "
    "writes it from the acceptance the human confirmed — if that checkpoint has already "
    "passed, write the goal from the spec's acceptance and say in your reply that you did.\n"
    "2. **Say it is deliberate**, if this project really is meant to run item-at-a-time with "
    "no goal: park a `steer` checkpoint (`python3 .claude/scripts/bus.py park`) asking for "
    "exactly that, and the human's answer settles it. A drive with no goal has no DONE, and "
    "that is a decision for a person, not a state to arrive in by omission.\n"
    "Do not simply continue: the items being built are not bound to anything that can be "
    "measured, and the loop cannot tell you when it is finished."
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


def check(workflow, last_text="", prev_fingerprint=None, satisfied_digest=None,
          prev_promoted=None, workers_seen=None):
    """-> {demand: None|'continue'|'anchor'|'report', why, instruction, fingerprint, digest}.

    `last_text` is the session's final assistant message; the report rung looks for the
    renderer's marker in it. `satisfied_digest` is the digest this session last satisfied, which
    is what stops an unchanged loop being asked for the same report twice.

    `prev_promoted` and `workers_seen` are the dispatch rung's two inputs, PASSED IN rather than
    read here: the first is the promoted set at the previous stop (the caller's latch owns it,
    and that is what makes "newly promoted" answerable at all), the second is how many workers
    this SESSION has run (only the caller knows which session this is). Both `None` mean cannot
    tell, and the rung stays silent -- a gate that fires when it does not know is a gate that
    gets switched off.
    """
    out = {"demand": None, "why": "", "instruction": "", "fingerprint": None, "digest": None,
           "promoted": promoted_items(workflow)}
    ok, why = may_end(workflow)
    changed, fp = moved(workflow, prev_fingerprint)
    out["fingerprint"] = fp
    if not ok and _planned_items(workflow) and _goal_missing(workflow):
        # Rung 1, with the one reason that is actionable rather than generic. Gated on PLANNED
        # work so that a session still inside inception -- where the goal is not minted yet
        # because the node that mints it has not run yet -- is not told it skipped anything.
        # Once an item has a directory, `planner` has run on it, and both graph paths mint the
        # goal before that happens.
        out.update(demand="goal", why=why, instruction=GOAL % why)
        return out
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

    # RUNG 3 -- an item finished with no worker behind it. Placed AFTER the anchor because
    # losing the loop's place breaks the next session outright, while this breach has already
    # happened and the correction it asks for is the NEXT item. Placed before the report because
    # a report that says an item shipped, without saying nothing reviewed it, is the more
    # misleading of the two.
    # `changed is not False` guards the one inherited case: a session that promoted an item and
    # died before its Stop hook ran never got the item into the latch, so the NEXT session sees
    # it as fresh with none of its own workers and would be blamed for a predecessor's work. A
    # session that moved nothing durable this turn cannot have built anything. Cannot-tell still
    # fires -- the rung's job is the breach, and silence on unknown would cover the common case.
    if prev_promoted is not None and workers_seen is not None and changed is not False:
        fresh = [i for i in out["promoted"] if i not in set(prev_promoted)]
        if fresh and not workers_seen:
            why = ("%s finished this turn with no worker dispatched anywhere — the router did "
                   "the work itself" % ", ".join(fresh))
            out.update(demand="dispatch", why=why, instruction=DISPATCH % why)
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

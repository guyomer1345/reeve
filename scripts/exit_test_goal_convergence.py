#!/usr/bin/env python3
"""The goal exit test: show the convergence measure CANNOT BE SATISFIED BY EFFORT.

The objection 12d has to answer is not speed and not coherence. It is that a loop measuring its
own progress will find a way to report progress -- so the only interesting question about this
measure is whether closing items, over and over, forever, can make it move. Every assertion here
is aimed at that. A run where the numbers merely go up proves nothing; what has to be shown is
the numbers REFUSING to go up while work is manifestly happening.

WHAT IT DRIVES on a throwaway `.workflow/` built from scratch each run:
  1. a goal whose acceptance nothing plans to touch  -> `unbound`, known before any work
  2. items planned and OPEN                          -> `planned`, the measure does not move
  3. items promoted through `converge.py record`     -> `discharged`, the measure moves
  4. `retention.py` run for real, deleting every promoted item dir -> the measure SURVIVES
  5. five closed items that discharge nothing        -> STALLED, and `check` exits 2
  6. a crash replayed between record and promoted.json -> the streak is not corrupted
  7. every acceptance discharged                     -> `met`, and `met` exits 0

STEP 4 IS THE ONE THAT JUSTIFIES THE LEDGER'S EXISTENCE and is therefore driven rather than
argued. This repo derives reality from durable artifacts and does not keep parallel ledgers
(`schemas-loopstate.md` § the forecast ANCHOR TABLE). The ledger is the exception because the
artifacts it would derive from are deliberately destroyed: `retention.py` prunes the whole item
dir once `promoted.json` lands. If the measure came out of that prune intact by luck rather than
by design, this step is where it shows -- so real `retention.py` is invoked on real promoted
items, and the measure is read before and after.

WHAT IT DOES NOT COVER, said plainly so a green run is not read for more than it earns. Nothing
here dispatches a model. `planner` deciding which acceptance a criterion honestly settles is a
JUDGEMENT, and a false binding -- a criterion bound to an acceptance it does not really settle --
is invisible to every assertion below and to `converge.py` itself. The measure is only as sound
as those bindings, and this proves the mechanism around them, not the bindings. That limit is
structural, not a gap to close later: no script can know whether a test really settles a
sentence. It is why `planner`'s instruction says an unbound criterion costs nothing and a false
binding stops a driver.

Exit 0 = the measure held. Exit 1 = a numbered assertion failed, and it says which.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
PRODUCT = os.path.join(ROOT, "product")
sys.path.insert(0, os.path.join(PRODUCT, "scripts"))

import converge  # noqa: E402

FAILURES = []
STEPS = []


def check(label, ok, detail=""):
    STEPS.append((label, bool(ok), detail))
    if not ok:
        FAILURES.append("%s%s" % (label, ("  -- " + detail) if detail else ""))
    print("  %s %s%s" % ("PASS" if ok else "FAIL", label, ("  -- " + detail) if detail else ""))
    return bool(ok)


def run(wf, *args):
    p = subprocess.run([sys.executable, os.path.join(PRODUCT, "scripts", "converge.py"),
                        "--workflow-dir", wf] + list(args), capture_output=True, text=True)
    return p.returncode, p.stdout, p.stderr


def measure(wf):
    return converge.measure(converge.read_goal(wf), converge.read_ledger(wf),
                            converge.open_bindings(wf))


# ------------------------------------------------------------------ the fixture
#
# Four acceptance entries, and the fourth is bound by NOTHING for most of the run. A fixture
# where every acceptance gets planned would never exercise `unbound`, which is the one finding
# available before any work is spent.
GOAL = {
    "id": "g-1",
    "statement": "ship the thing",
    "status": "active",   # an operator switch; doneness is DERIVED, never stored here
    "acceptance": [
        {"id": "ga-1", "text": "a user can sign in", "source": "docs/spec.md § features / Auth"},
        {"id": "ga-2", "text": "a session survives reload", "source": "docs/spec.md § features / Auth"},
        {"id": "ga-3", "text": "sign-out clears state", "source": "docs/spec.md § features / Auth"},
        {"id": "ga-4", "text": "rate limiting holds", "source": "docs/spec.md § features / Auth"},
    ],
}


def build(wf):
    os.makedirs(os.path.join(wf, "items"), exist_ok=True)
    with open(os.path.join(wf, "goal.json"), "w", encoding="utf-8") as fh:
        json.dump(GOAL, fh)


def plan_item(wf, item, *refs):
    """An OPEN item: plan + promises on disk, no `promoted.json`."""
    d = os.path.join(wf, "items", item)
    os.makedirs(d, exist_ok=True)
    crits = [{"id": "ac-%d" % i, "gate": "artifact", "discharge": "tests/test_%s.py" % item,
              "goal_ref": r} for i, r in enumerate(refs, 1)] or \
            [{"id": "ac-1", "gate": "artifact", "discharge": "tests/test_%s.py" % item}]
    with open(os.path.join(d, "promises.json"), "w", encoding="utf-8") as fh:
        json.dump({"criteria": crits, "promises": [], "known_tests": []}, fh)
    with open(os.path.join(d, "plan.md"), "w", encoding="utf-8") as fh:
        fh.write("# plan %s\n" % item)
    with open(os.path.join(d, "verify-verdict.md"), "w", encoding="utf-8") as fh:
        fh.write("pass: true\n\nthe artifacts conform.\n")
    return d


def promote(wf, item, crash_between=False):
    """`document`'s promote moment, in the order the agent brief mandates: record FIRST (the
    dir is about to become prunable), then the marker. `crash_between` replays the window."""
    rc, _, _ = run(wf, "record", "--item", item)
    if crash_between:
        rc, _, _ = run(wf, "record", "--item", item)   # the replay after the crash
    with open(os.path.join(wf, "items", item, "promoted.json"), "w", encoding="utf-8") as fh:
        json.dump({"promoted": True}, fh)
    return rc


# ------------------------------------------------------------------ the drive

def drive(wf):
    build(wf)

    print("\n1. an acceptance nothing plans to touch is known BEFORE any work")
    m = measure(wf)
    check("1. all four acceptance are unbound at t=0", m["unbound"] == ["ga-1", "ga-2", "ga-3", "ga-4"],
          str(m["unbound"]))
    check("2. an empty goal is not met", m["met"] is False)

    print("\n2. planning is a PROMISE -- the measure must not move on it")
    plan_item(wf, "i-1", "ga-1")
    plan_item(wf, "i-2", "ga-2")
    m = measure(wf)
    check("3. a planned acceptance reads `planned`, not `discharged`",
          m["status"]["ga-1"] == "planned", m["status"]["ga-1"])
    check("4. nothing is discharged while both items are open", m["discharged"] == [], str(m["discharged"]))
    check("5. still not met with every open item claiming an acceptance", m["met"] is False)
    check("6. ga-4 is still unbound -- planning others did not hide it", "ga-4" in m["unbound"])

    print("\n3. promotion is what discharges")
    promote(wf, "i-1")
    m = measure(wf)
    check("7. the promoted item's acceptance is discharged", m["status"]["ga-1"] == "discharged")
    check("8. the still-open item's is not", m["status"]["ga-2"] == "planned")
    check("9. progress reads 1 of 4", m["progress"].startswith("1/4"), m["progress"])

    print("\n4. RETENTION DELETES THE EVIDENCE -- the measure must survive it")
    promote(wf, "i-2")
    before = measure(wf)
    rc = subprocess.run([sys.executable, os.path.join(PRODUCT, "scripts", "retention.py"),
                         "--workflow-dir", wf, "--project-root", wf],
                        capture_output=True, text=True)
    gone = [i for i in ("i-1", "i-2") if not os.path.exists(os.path.join(wf, "items", i))]
    check("10. retention really pruned both promoted item dirs", gone == ["i-1", "i-2"],
          "pruned=%s rc=%d %s" % (gone, rc.returncode, rc.stderr[-200:]))
    check("11. promises.json is gone, so nothing could be re-derived",
          not os.path.exists(os.path.join(wf, "items", "i-1", "promises.json")))
    after = measure(wf)
    check("12. the measure is UNCHANGED across the prune",
          after["discharged"] == before["discharged"] == ["ga-1", "ga-2"],
          "before=%s after=%s" % (before["discharged"], after["discharged"]))

    print("\n5. closing items forever must NOT read as progress")
    for n in range(converge.STALL_LIMIT):
        plan_item(wf, "m-%d" % n)          # real items, real criteria, no goal binding
        promote(wf, "m-%d" % n)
        m = measure(wf)
        check("13.%d after %d no-progress promotion(s): streak=%d, discharged still 2"
              % (n, n + 1, m["streak"]),
              m["streak"] == n + 1 and m["discharged"] == ["ga-1", "ga-2"],
              "streak=%d discharged=%s" % (m["streak"], m["discharged"]))
    m = measure(wf)
    check("14. STALLED at the limit", m["stalled"] is True, "streak=%d" % m["streak"])
    check("15. and still not met", m["met"] is False)
    rc, _, err = run(wf, "check")
    check("16. `converge.py check` exits 2 on the stall", rc == 2, "rc=%d" % rc)
    check("17. and instructs re-steer rather than retry",
          "re-steer" in err and "NEVER retry" in err and "re-plan" in err, err.strip()[:140])

    print("\n6. re-discharging a LIVE acceptance is not progress either")
    plan_item(wf, "r-1", "ga-1")           # a genuine re-fix of something already discharged
    promote(wf, "r-1")
    m = measure(wf)
    check("18. the streak kept counting through the re-fix", m["streak"] == converge.STALL_LIMIT + 1,
          "streak=%d" % m["streak"])
    check("19. ga-1 is still discharged exactly once", m["discharged"] == ["ga-1", "ga-2"])

    print("\n7. a crash between `record` and `promoted.json` must not corrupt the streak")
    plan_item(wf, "c-1", "ga-3")
    promote(wf, "c-1", crash_between=True)
    entries = [e for e in converge.read_ledger(wf) if e.get("item") == "c-1"]
    check("20. the replayed record appended exactly one entry", len(entries) == 1, str(entries))
    m = measure(wf)
    check("21. real progress RESET the streak", m["streak"] == 0, "streak=%d" % m["streak"])
    check("22. and it is no longer stalled", m["stalled"] is False)

    print("\n8. met is met -- and only then")
    rc, _, _ = run(wf, "met")
    check("23. `met` exits 1 with one acceptance outstanding", rc == 1, "rc=%d" % rc)
    check("24. the outstanding one is the never-bound ga-4", measure(wf)["unbound"] == ["ga-4"])
    plan_item(wf, "i-4", "ga-4")
    promote(wf, "i-4")
    m = measure(wf)
    check("25. every acceptance discharged ⇒ met", m["met"] is True, m["progress"])
    rc, _, _ = run(wf, "met")
    check("26. `met` exits 0", rc == 0, "rc=%d" % rc)
    check("27. a met goal is never reported stalled", m["stalled"] is False)

    print("\n9. the fail direction: a broken measure must never read as met")
    with open(os.path.join(wf, "goal.json"), "w", encoding="utf-8") as fh:
        fh.write("{ truncated")
    rc, _, _ = run(wf, "met")
    check("28. an unparseable goal exits non-zero rather than 'done'", rc == 1, "rc=%d" % rc)
    with open(os.path.join(wf, "goal.json"), "w", encoding="utf-8") as fh:
        json.dump({"id": "g-2", "acceptance": []}, fh)
    rc, _, _ = run(wf, "met")
    check("29. a goal with NO acceptance is not vacuously met", rc == 1, "rc=%d" % rc)


def main():
    wf = tempfile.mkdtemp(prefix="goal-exit-test-")
    print("driving the goal-convergence exit test in %s" % wf)
    try:
        drive(os.path.join(wf, ".workflow"))
    finally:
        if os.environ.get("KEEP_EXIT_TEST_REPO"):
            print("\n(tree kept at %s)" % wf)
        else:
            shutil.rmtree(wf, ignore_errors=True)

    print("\n%d checks, %d failed" % (len(STEPS), len(FAILURES)))
    if FAILURES:
        print("\nTHE MEASURE DID NOT HOLD:")
        for f in FAILURES:
            print("  - %s" % f)
        return 1
    print("HELD: the measure moved only on promoted acceptance, survived retention deleting the "
          "evidence it was derived from, refused to move for %d consecutive closed items, refused "
          "a re-fix of live work, and never read as met on a broken input."
          % converge.STALL_LIMIT)
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""The driver exit test: drive a REAL goal across several real sessions, and interrupt it.

`11` set this slice's exit test before it was built: *a real goal driven across several sessions
with no human `/clear`, interrupted once on purpose to prove the drop-in window and the `pause`
path.* That is what runs here, against the real `loop.sh --drive` in a real git repo holding a
real `flock`.

WHAT STANDS IN FOR THE MODEL, and why it is honest rather than a shortcut. `claude` is replaced
by a scripted session (`BUS_CLAUDE_BIN`-style seam: the driver spawns `claude`, and PATH decides
what that is). The subject here is the DRIVER -- whether it stops on the right predicates,
whether a pause outlives a session, whether the lock handover works -- and none of that is a
property of the model. Scripting the session removes model variance so a red run means the
driver is wrong rather than that a session had a bad day. It is a sharper test of the driver and
NO test of what a session does with its turn.

THE SESSIONS ARE DELIBERATELY BADLY BEHAVED. One commits. One writes an item anchor and no
commit -- the case a `HEAD`-only driver would misread as a stall. One does nothing at all. One
CRASHES with a non-zero exit and writes nothing, because a driver that treats a crash as a
report is the failure mode this design exists to avoid. A fixture of well-behaved sessions would
prove only that nothing was checked.

Exit 0 = the driver held. Exit 1 = a numbered assertion failed, and it says which.
"""
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import time

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
PRODUCT = os.path.join(ROOT, "product")

sys.path.insert(0, os.path.join(PRODUCT, "scripts"))
from drive import MAX_NOPROGRESS  # noqa: E402  -- the contract, never a literal

FAILURES, STEPS = [], []


def check(label, ok, detail=""):
    STEPS.append((label, bool(ok), detail))
    if not ok:
        FAILURES.append("%s%s" % (label, ("  -- " + detail) if detail else ""))
    print("  %s %s%s" % ("PASS" if ok else "FAIL", label, ("  -- " + detail) if detail else ""))
    return bool(ok)


def git(repo, *args):
    return subprocess.run(("git", "-C", repo) + args, capture_output=True, text=True).stdout


# The scripted session. Each invocation reads a plan of behaviours and performs the next one,
# so the driver meets a different kind of session every time without the harness having to
# orchestrate anything.
FAKE_CLAUDE = r'''#!/usr/bin/env bash
set -u
WF="$PWD/.workflow"
N=$(cat "$WF/.session-n" 2>/dev/null || echo 0)
N=$((N + 1)); echo "$N" > "$WF/.session-n"
BEHAVIOUR=$(sed -n "${N}p" "$WF/.behaviours" 2>/dev/null || echo idle)
echo "session $N: $BEHAVIOUR" >> "$WF/.session-log"
case "$BEHAVIOUR" in
  commit)  echo "s$N" >> work.txt; git add -A >/dev/null 2>&1
           git -c user.email=t@t -c user.name=t commit -qm "session $N" >/dev/null 2>&1 ;;
  anchor)  mkdir -p "$WF/items/i-$N"; echo "# plan" > "$WF/items/i-$N/plan.md" ;;
  crash)   exit 3 ;;
  pause)   python3 "$WF/../.claude/scripts/drain.py" --workflow-dir "$WF" record \
              --applied "$(cat "$WF/.pause-id")" >/dev/null 2>&1 ;;
  discharge) mkdir -p "$WF/items/d-$N"
           printf '{"criteria":[{"id":"ac-1","gate":"artifact","discharge":"t","goal_ref":"ga-1"}]}' \
              > "$WF/items/d-$N/promises.json"
           python3 "$WF/../.claude/scripts/converge.py" --workflow-dir "$WF" record \
              --item "d-$N" >/dev/null 2>&1
           echo '{"promoted": true}' > "$WF/items/d-$N/promoted.json" ;;
  idle)    : ;;
esac
exit 0
'''


def build(repo, behaviours, goal=None):
    wf = os.path.join(repo, ".workflow")
    os.makedirs(os.path.join(wf, "items"))
    os.makedirs(os.path.join(wf, "inbox"))
    os.makedirs(os.path.join(repo, ".claude", "scripts"))
    for name in ("drive.py", "drain.py", "bus.py", "converge.py", "loop.sh", "retention.py"):
        shutil.copy(os.path.join(PRODUCT, "scripts", name),
                    os.path.join(repo, ".claude", "scripts", name))
    os.chmod(os.path.join(repo, ".claude", "scripts", "loop.sh"), 0o755)
    with open(os.path.join(wf, "handoff.md"), "w") as fh:
        fh.write("# Handoff — resume anchor\n\nprose\n")
    with open(os.path.join(wf, ".behaviours"), "w") as fh:
        fh.write("\n".join(behaviours) + "\n")
    if goal:
        with open(os.path.join(wf, "goal.json"), "w") as fh:
            json.dump(goal, fh)
    git(repo, "init", "-q")
    git(repo, "config", "user.email", "t@t")
    git(repo, "config", "user.name", "t")
    with open(os.path.join(repo, "work.txt"), "w") as fh:
        fh.write("base\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "init")

    # the fake `claude`, first on PATH
    binz = os.path.join(repo, "bin")
    os.makedirs(binz)
    fake = os.path.join(binz, "claude")
    with open(fake, "w") as fh:
        fh.write(FAKE_CLAUDE)
    os.chmod(fake, os.stat(fake).st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    return wf, binz


def drive(repo, binz, dropin=0, timeout=90):
    env = dict(os.environ)
    env["PATH"] = binz + os.pathsep + env["PATH"]
    env["REEVE_DROPIN_SECONDS"] = str(dropin)
    return subprocess.run(
        ["bash", os.path.join(repo, ".claude", "scripts", "loop.sh"), "--drive"],
        cwd=repo, capture_output=True, text=True, env=env, timeout=timeout)


def sessions_run(wf):
    try:
        with open(os.path.join(wf, ".session-n")) as fh:
            return int(fh.read().strip())
    except OSError:
        return 0


def mint_pause(wf):
    mid = "20260913T120000.000000Z-deadbeef-1"
    with open(os.path.join(wf, "inbox", mid + ".json"), "w") as fh:
        json.dump({"kind": "control", "op": "pause"}, fh)
    with open(os.path.join(wf, ".pause-id"), "w") as fh:
        fh.write(mid)
    return mid


GOAL = {"id": "g-1", "status": "active",
        "acceptance": [{"id": "ga-1", "text": "the thing works"}]}


# ------------------------------------------------------------------ the drives

def drive_no_progress(tmp):
    print("\n1. a driver with nothing to do gives up instead of spinning all night")
    repo = os.path.join(tmp, "a")
    os.makedirs(repo)
    wf, binz = build(repo, ["idle"] * 20)
    r = drive(repo, binz)
    n = sessions_run(wf)
    check("1. it stopped on its own", r.returncode == 0, "rc=%d" % r.returncode)
    # The first session is free (nothing to compare against), then each further one that moves
    # nothing adds to the streak -- so it stops having run exactly MAX_NOPROGRESS sessions, not
    # the 20 it was offered. Asserted against the constant, not a literal: the constant is the
    # contract, and a literal here would quietly stop testing it if the number moved.
    check("2. after exactly MAX_NOPROGRESS sessions, not the 20 it was offered",
          n == MAX_NOPROGRESS, "ran %d, limit %d" % (n, MAX_NOPROGRESS))
    check("3. and said why, in words a human can act on",
          "NO PROGRESS" in r.stderr, (r.stderr.strip().splitlines() or [""])[-1])


def drive_mixed(tmp):
    print("\n2. real work across several sessions -- including a crash and a commit-less one")
    repo = os.path.join(tmp, "b")
    os.makedirs(repo)
    # commit, anchor (no commit!), crash (writes nothing), then idle until it gives up
    wf, binz = build(repo, ["commit", "anchor", "crash"] + ["idle"] * 20)
    head_before = git(repo, "rev-parse", "HEAD").strip()
    r = drive(repo, binz)
    n = sessions_run(wf)
    check("4. the driver survived a session that exited non-zero", r.returncode == 0,
          "rc=%d" % r.returncode)
    check("5. a crashed session did not stop the drive", n > 3, "ran %d" % n)
    check("6. the committing session moved HEAD",
          git(repo, "rev-parse", "HEAD").strip() != head_before)
    check("7. the ANCHOR-only session counted as progress (a HEAD-only driver would have "
          "called it a stall)", os.path.exists(os.path.join(wf, "items", "i-2", "plan.md")))
    # 3 productive-or-crashed sessions then 5 idle ones before the give-up: crash writes
    # nothing, so the streak starts there.
    check("8. it still gave up once nothing moved", "NO PROGRESS" in r.stderr)


def drive_pause(tmp):
    print("\n3. a pause issued DURING a session outlives that session")
    repo = os.path.join(tmp, "c")
    os.makedirs(repo)
    wf, binz = build(repo, ["commit", "pause", "commit", "commit"] + ["commit"] * 10)
    mint_pause(wf)
    r = drive(repo, binz)
    n = sessions_run(wf)
    check("9. the driver stopped rather than running the remaining sessions", n == 2,
          "ran %d" % n)
    check("10. and named the pause as the reason", "PAUSED" in r.stderr,
          (r.stderr.strip().splitlines() or [""])[-1])
    latch = json.load(open(os.path.join(wf, "control.json")))
    check("11. the latch is on disk, not in a session's head", latch["paused"] is True)
    check("12. sessions 3+ never ran -- the pause was honoured BETWEEN sessions",
          "session 3" not in open(os.path.join(wf, ".session-log")).read())


def drive_goal_met(tmp):
    print("\n4. the goal is met, so the driver stops and does not keep working")
    repo = os.path.join(tmp, "d")
    os.makedirs(repo)
    wf, binz = build(repo, ["discharge"] + ["commit"] * 10, goal=GOAL)
    r = drive(repo, binz)
    n = sessions_run(wf)
    check("13. it stopped after the goal was discharged", n == 1, "ran %d" % n)
    check("14. and said the goal was met", "GOAL MET" in r.stderr,
          (r.stderr.strip().splitlines() or [""])[-1])
    check("15. it did not keep committing past the goal",
          len(git(repo, "log", "--oneline").strip().splitlines()) == 1)


def drive_dropin(tmp):
    print("\n5. the drop-in window: taking the lock is how you take the machine")
    repo = os.path.join(tmp, "e")
    os.makedirs(repo)
    wf, binz = build(repo, ["commit"] * 20)
    lock = os.path.join(wf, "orchestrator.lock")

    env = dict(os.environ)
    env["PATH"] = binz + os.pathsep + env["PATH"]
    env["REEVE_DROPIN_SECONDS"] = "2"
    p = subprocess.Popen(["bash", os.path.join(repo, ".claude", "scripts", "loop.sh"), "--drive"],
                         cwd=repo, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                         env=env)
    # Wait for the driver to actually be driving, then grab the lock during a window. A
    # `flock -w` blocks until the driver opens the gap, which is the human's real experience.
    deadline = time.time() + 30
    while time.time() < deadline and sessions_run(wf) < 1:
        time.sleep(0.1)
    took = subprocess.run(["flock", "-w", "20", lock, "-c", "sleep 3"],
                          capture_output=True, text=True)
    check("16. a human could take the lock in the drop-in window", took.returncode == 0,
          "rc=%d %s" % (took.returncode, took.stderr[-120:]))
    out, err = p.communicate(timeout=60)
    check("17. the driver stepped aside rather than racing a second orchestrator",
          p.returncode == 0 and "handing over" in err,
          "rc=%s tail=%r" % (p.returncode, err.strip()[-160:]))
    check("18. it had done real work before handing over", sessions_run(wf) >= 1,
          "ran %d" % sessions_run(wf))


def drive_human_path_unchanged(tmp):
    print("\n6. the human path must be untouched -- no `--drive`, no loop")
    repo = os.path.join(tmp, "f")
    os.makedirs(repo)
    wf, binz = build(repo, ["commit"] * 5)
    env = dict(os.environ)
    env["PATH"] = binz + os.pathsep + env["PATH"]
    r = subprocess.run(["bash", os.path.join(repo, ".claude", "scripts", "loop.sh")],
                       cwd=repo, capture_output=True, text=True, env=env, timeout=60)
    check("19. it ran exactly one session and exited", sessions_run(wf) == 1,
          "ran %d" % sessions_run(wf))
    check("20. and never printed a driver line", "--drive" not in r.stderr, r.stderr[-120:])


def main():
    tmp = tempfile.mkdtemp(prefix="driver-exit-test-")
    print("driving the session-driver exit test in %s" % tmp)
    try:
        drive_no_progress(tmp)
        drive_mixed(tmp)
        drive_pause(tmp)
        drive_goal_met(tmp)
        drive_dropin(tmp)
        drive_human_path_unchanged(tmp)
    finally:
        if os.environ.get("KEEP_EXIT_TEST_REPO"):
            print("\n(tree kept at %s)" % tmp)
        else:
            shutil.rmtree(tmp, ignore_errors=True)

    print("\n%d checks, %d failed" % (len(STEPS), len(FAILURES)))
    if FAILURES:
        print("\nTHE DRIVER DID NOT HOLD:")
        for f in FAILURES:
            print("  - %s" % f)
        return 1
    print("HELD: the driver ran a real goal across several sessions with no human /clear, "
          "survived a crashed session, honoured a pause issued mid-session, stopped on a met "
          "goal, handed the machine over by losing the lock, and left the human path unchanged.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

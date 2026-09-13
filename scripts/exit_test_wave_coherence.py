#!/usr/bin/env python3
"""The wave exit test: drive a real fan-out and show the MERGED RESULT IS CORRECT.

This is the test D192 asked for and D194 could not supply. Its subject is deliberately not
throughput -- that was never the objection. D91 declined real concurrency because N workers
editing one repo at once produce a merged tree nobody has shown to be coherent, and speed is
worthless if the thing you end up with is wrong. So every assertion below is about the state of
the tree after the wave, never about how long the wave took.

WHAT IT DRIVES, on a throwaway repo built from scratch each run:
  wave 1  gate -> batch -> mint -> N real git worktrees -> N CONCURRENT writers ->
          `checks.sh --check` contending for the wave build slot -> merge -> coherence
  wave 2  the freshness lifecycle across a real wave boundary: a plan left behind by wave 1
          goes stale because wave 1 landed under it, is refused, is refreshed, is dispatchable
          again, and finally exhausts its refresh budget and routes to a full re-plan.

WHAT IT DOES NOT COVER, said plainly so nobody reads more into a green run than it earns. The
writers are SCRIPTED, not dispatched models. That is a deliberate choice and not a shortcut:
coherence is a property of the coordination -- the gate's predicate, worktree isolation, the
build slot, the merge -- and scripting the writers removes model variance so a red run means
the mechanism is wrong rather than that a worker had a bad day. It is a sharper test of the
mechanism and NO test of the loop. Driving real `planner`/`execute` agents through a live
`/start` remains the thing that tests the loop, and this does not stand in for it.

Exit 0 = coherent. Exit 1 = a numbered assertion failed, and it says which.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
PRODUCT = os.path.join(ROOT, "product")

FAILURES = []
STEPS = []


def check(label, ok, detail=""):
    STEPS.append((label, bool(ok), detail))
    if not ok:
        FAILURES.append("%s%s" % (label, ("  -- " + detail) if detail else ""))
    print("  %s %s%s" % ("PASS" if ok else "FAIL", label, ("  -- " + detail) if detail else ""))
    return bool(ok)


def git(repo, *args, check_rc=True):
    p = subprocess.run(("git", "-C", repo) + args, capture_output=True, text=True)
    if check_rc and p.returncode != 0:
        raise RuntimeError("git %s failed in %s:\n%s" % (" ".join(args), repo, p.stderr))
    return p.stdout


def script(repo, name, *args):
    p = subprocess.run([sys.executable, os.path.join(repo, ".claude", "scripts", name)] + list(args),
                       capture_output=True, text=True, cwd=repo)
    return p.returncode, p.stdout, p.stderr


# ------------------------------------------------------------------ the fixture
#
# The code map is built to exercise every rejection clause on real data rather than to make the
# batch look good: `d` imports `a` (clause 3, adjacency), item E declares `a` outright
# (clause 2, overlap), and the ceiling is set to 3 so a genuinely independent item still gets
# turned away for capacity. A fixture where everything passes proves only that nothing was
# checked.

# The project's own test suite, and the wave build slot's stopwatch. The dwell is deliberate:
# three instantaneous runs can finish back to back with no lock at all, so without it a broken
# lock would pass. `--slot-log` records the window the gate actually held.
TEST_RUNNER = """import json, os, pathlib, sys, time

log = None
if "--slot-log" in sys.argv:
    log = sys.argv[sys.argv.index("--slot-log") + 1]
who = os.path.basename(os.getcwd())
t0 = time.time()
time.sleep(0.4)

bad = []
for p in sorted(pathlib.Path("src").glob("*.py")):
    head = p.read_text().strip().splitlines()[:1]
    ok = bool(head) and head[0].startswith("VALUE = ") and head[0][8:].strip().isdigit()
    if not ok:
        bad.append(str(p))

if log:
    with open(log, "a") as fh:
        fh.write(json.dumps({"who": who, "in": t0, "out": time.time()}) + chr(10))
sys.exit(1 if bad else 0)
"""

FILES = ["src/a.py", "src/b.py", "src/c.py", "src/d.py",
         "src/e.py", "src/f.py", "src/g.py"]
EDGES = [("src/d.py", "src/a.py"), ("src/f.py", "src/e.py")]

# QUEUE ORDER IS PART OF THE FIXTURE, and getting it wrong made the first run of this test
# useless. Selection is a greedy first-fit walk down `backlog.md`, and the capacity check sits
# BEFORE the overlap and adjacency checks -- so once the ceiling is full every later candidate
# is rejected for capacity and the interesting clauses are never reached. D and E therefore sit
# high in the queue, where the batch still has room and their own clause has to do the work.
ITEMS = [("A", ["src/a.py"], "none"),      # -> batch
         ("D", ["src/d.py"], "none"),      # clause 3: one code-map edge from A
         ("E", ["src/a.py"], "none"),      # clause 2: the same file as A
         ("B", ["src/b.py"], "none"),      # -> batch
         ("C", ["src/c.py"], "none"),      # -> batch, and the ceiling is now full
         ("F", ["src/f.py"], "Z"),         # clause 1: Z has never finished
         ("G", ["src/g.py"], "none")]      # independent, and refused anyway: no slots left
SCOPE = {i: f for i, f, _ in ITEMS}
BATCH_ITEMS = ["A", "B", "C"]


def install(repo):
    """Perform the real install, derived from the manifest — not a hand-picked subset."""
    manifest = json.load(open(os.path.join(PRODUCT, "MANIFEST.json"), encoding="utf-8"))
    for entry in manifest["install"]:
        src, dest = os.path.join(PRODUCT, entry["src"]), os.path.join(repo, entry["dest"])
        if not os.path.isfile(src):
            continue
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        shutil.copy2(src, dest)
    shutil.copy2(os.path.join(PRODUCT, "templates", "checks.sh"), os.path.join(repo, "checks.sh"))
    os.chmod(os.path.join(repo, "checks.sh"), 0o755)


def plan(repo, item, files, base=None, count=None):
    d = os.path.join(repo, ".workflow", "items", item)
    os.makedirs(d, exist_ok=True)
    body = ["# Plan — %s" % item, "", "## Goal", "make %s work" % item, ""]
    if base:
        body.append("- **base_sha** — `%s`" % base)
    if count is not None:
        body.append("- **refresh_count** — %d" % count)
    body += ["", "## files_touched"] + ["- `%s` — the change" % f for f in files]
    body += ["", "## Steps", "1. edit it", ""]
    open(os.path.join(d, "plan.md"), "w").write("\n".join(body))


def build_repo(repo):
    os.makedirs(os.path.join(repo, "src"), exist_ok=True)
    for f in FILES:
        open(os.path.join(repo, f), "w").write("VALUE = 0\n")
    open(os.path.join(repo, "run_tests.py"), "w").write(TEST_RUNNER)

    git(repo, "init", "-q", "-b", "main")
    git(repo, "config", "user.email", "exit-test@local")
    git(repo, "config", "user.name", "exit test")

    wf = os.path.join(repo, ".workflow")
    os.makedirs(os.path.join(wf, "items"), exist_ok=True)
    json.dump({"project": "wave-exit-test", "project_root": ".",
               "run": {"wave": {"plan_max": 10, "execute_max": 3, "refresh_max": 2}}},
              open(os.path.join(wf, "config.json"), "w"), indent=2)
    json.dump({"phase": "building", "current_item": None, "wave": None, "note": "exit test"},
              open(os.path.join(wf, "state.json"), "w"), indent=2)
    # The stack gate is what the wave build slot serialises, so the TEST command is also the
    # instrument: it stamps its own entry and exit into a shared log. Measuring the whole
    # `checks.sh` run instead would prove nothing -- the lock is released before the
    # stack-agnostic coverage gates, so those overlap by design and an outer timer sees overlap
    # on a perfectly working lock. The first version of this test made exactly that mistake.
    open(os.path.join(wf, "checks.env"), "w").write(
        'TEST="python3 run_tests.py --slot-log %s"\n' % os.path.join(repo, "slot-log.jsonl"))
    open(os.path.join(wf, "backlog.md"), "w").write(
        "# Backlog\n\n## Open\n\n" +
        "".join("- **%s** · kind: feature · severity: medium · deps: %s\n" % (i, d)
                for i, _, d in ITEMS))

    gdir = os.path.join(repo, "docs", "knowledge")
    os.makedirs(gdir, exist_ok=True)
    json.dump({"root": ".", "nodes": [{"path": f} for f in FILES],
               "edges": [{"from": a, "to": b, "kind": "import"} for a, b in EDGES]},
              open(os.path.join(gdir, "graph.json"), "w"))

    install(repo)
    for item, files, _ in ITEMS:
        plan(repo, item, files)
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "fixture")
    base = git(repo, "rev-parse", "HEAD").strip()
    for item, files, _ in ITEMS:                    # stamp every plan against the real base
        plan(repo, item, files, base=base)
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "stamp plans")
    return git(repo, "rev-parse", "HEAD").strip()


# ------------------------------------------------------------------ the concurrent writers

def worker(repo, item, files, results, barrier):
    """One wave member: its own worktree, its own file, then the authoritative gate.

    The barrier makes the concurrency real rather than nominal — without it three fast workers
    can finish in sequence and the build slot is never contended, which would let a broken lock
    pass. Enter/exit times around the gate are recorded so the exclusion can be checked instead
    of assumed.
    """
    wt = os.path.join(repo, ".worktrees", item)
    try:
        git(repo, "worktree", "add", "-q", "-b", "wave/%s" % item, wt, "HEAD")
        for f in files:
            open(os.path.join(wt, f), "w").write("VALUE = %d\n" % (ord(item) - 64))
        cdir = os.path.join(wt, ".workflow", "items", item)
        os.makedirs(cdir, exist_ok=True)
        open(os.path.join(cdir, "changelog.md"), "w").write(
            "# Changelog — %s\n\n- edited %s\n" % (item, ", ".join(files)))
        barrier.wait(timeout=60)
        t0 = time.time()
        p = subprocess.run(["bash", os.path.join(wt, "checks.sh"), "--check"],
                           capture_output=True, text=True, cwd=wt)
        t1 = time.time()
        git(wt, "add", "-A")
        git(wt, "commit", "-q", "-m", "feat(%s): the change" % item)
        results[item] = {"gate_rc": p.returncode, "in": t0, "out": t1,
                         "out_text": p.stdout + p.stderr,
                         "sha": git(wt, "rev-parse", "HEAD").strip()}
    except Exception as exc:                                       # noqa: BLE001
        results[item] = {"error": "%s: %s" % (type(exc).__name__, exc)}


def drive_wave_one(repo):
    print("\n== WAVE 1 — fan out, contend for the build slot, merge ==")
    rc, out, err = script(repo, "check_wave_independence.py", "--project-root", repo, "--json")
    res = json.loads(out)

    check("1. the gate proves a batch and it is the expected one",
          res["batch"] == BATCH_ITEMS, "batch=%s" % res["batch"])
    check("2. fan-out is signalled by exit code 0", rc == 0, "rc=%d" % rc)
    by = {c["id"]: c for c in res["candidates"]}
    check("3. clause 2 (overlap) rejects E against A, naming the file",
          any(r["clause"] == "file-overlap" and r["against"] == "A" for r in by["E"]["reasons"]),
          str(by["E"]["reasons"][:1]))
    check("4. clause 3 (adjacency) rejects D against A — two files, one change",
          any(r["clause"] == "adjacency" and r["against"] == "A" for r in by["D"]["reasons"]),
          str(by["D"]["reasons"][:1]))
    check("5. clause 1 (dependency) rejects F — Z has never finished",
          any(r["clause"] == "dependency" for r in by["F"]["reasons"]),
          str(by["F"]["reasons"][:1]))
    check("5b. an independent item is still refused when the ceiling is full",
          any(r["clause"] == "capacity" for r in by["G"]["reasons"]),
          "G reasons=%s" % [r["clause"] for r in by["G"]["reasons"]])
    check("6. every plan reads FRESH before anything has landed",
          all(by[i]["freshness"] == "fresh" for i in by),
          str({i: by[i]["freshness"] for i in by}))

    rc, out, _ = script(repo, "wave_build.py", "mint", *BATCH_ITEMS)
    wave = out.strip()
    state = json.load(open(os.path.join(repo, ".workflow", "state.json")))
    state["wave"] = wave
    json.dump(state, open(os.path.join(repo, ".workflow", "state.json"), "w"), indent=2)
    check("7. the wave is named, and the name is derived not allocated",
          wave.startswith("w-") and wave == script(repo, "wave_build.py", "mint",
                                                   *reversed(BATCH_ITEMS))[1].strip(), wave)

    results, barrier = {}, threading.Barrier(len(BATCH_ITEMS))
    threads = []
    for item in BATCH_ITEMS:
        files = SCOPE[item]
        threads.append(threading.Thread(target=worker,
                                        args=(repo, item, files, results, barrier)))
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=300)

    check("8. every worker completed without error",
          all("error" not in results.get(i, {"error": "missing"}) for i in BATCH_ITEMS),
          str({i: results.get(i, {}).get("error") for i in BATCH_ITEMS}))
    if FAILURES:
        return None, results

    check("9. every worker's authoritative gate passed in its own worktree",
          all(results[i]["gate_rc"] == 0 for i in BATCH_ITEMS),
          str({i: results[i]["gate_rc"] for i in BATCH_ITEMS}))

    overlap = _overlaps(os.path.join(repo, "slot-log.jsonl"))
    check("10. the build slot serialised the authoritative gate — no two held it at once",
          not overlap, "overlapping pairs: %s" % overlap)

    # NEGATIVE CONTROL. Check 10 is only evidence if it can fail, so run the identical workload
    # with no lock around it: same barrier, same dwell, same detector. If THAT does not overlap,
    # check 10 was never testing the lock.
    unlocked = os.path.join(repo, "unlocked-log.jsonl")
    bar = threading.Barrier(len(BATCH_ITEMS))
    ts = [threading.Thread(target=_bare_gate, args=(repo, i, unlocked, bar))
          for i in BATCH_ITEMS]
    for t in ts:
        t.start()
    for t in ts:
        t.join(timeout=120)
    check("10b. NEGATIVE CONTROL — the same workload with no slot DOES overlap",
          bool(_overlaps(unlocked)), "so check 10 is measuring the lock, not the clock")

    return wave, results


def _overlaps(path):
    """Pairwise overlap between recorded [in, out] windows, by start order."""
    if not os.path.isfile(path):
        return [("(no log)", "(no log)")]
    rows = [json.loads(ln) for ln in open(path) if ln.strip()]
    rows.sort(key=lambda r: r["in"])
    return [(a["who"], b["who"]) for a, b in zip(rows, rows[1:]) if b["in"] < a["out"]]


def _bare_gate(repo, item, log, barrier):
    wt = os.path.join(repo, ".worktrees", item)
    barrier.wait(timeout=60)
    subprocess.run([sys.executable, os.path.join(wt, "run_tests.py"), "--slot-log", log],
                   cwd=wt, capture_output=True)


def merge_and_check(repo, results):
    print("\n== MERGE — the coherence question ==")
    base = git(repo, "rev-parse", "HEAD").strip()
    conflicts = []
    for item in BATCH_ITEMS:
        p = subprocess.run(("git", "-C", repo, "merge", "--no-edit", "wave/%s" % item),
                           capture_output=True, text=True)
        if p.returncode != 0:
            conflicts.append((item, p.stdout + p.stderr))
            subprocess.run(("git", "-C", repo, "merge", "--abort"), capture_output=True)
    check("11. the three branches merged with no conflict", not conflicts,
          str([c[0] for c in conflicts]))
    if conflicts:
        return

    for item in BATCH_ITEMS:
        f = SCOPE[item][0]
        want = "VALUE = %d\n" % (ord(item) - 64)
        got = open(os.path.join(repo, f)).read()
        check("12.%s %s's change survived the merge intact" % (item, item), got == want,
              "%s = %r" % (f, got))

    for item in BATCH_ITEMS:
        check("13.%s %s's changelog is present in the merged tree" % (item, item),
              os.path.isfile(os.path.join(repo, ".workflow", "items", item, "changelog.md")))

    p = subprocess.run([sys.executable, "run_tests.py"], cwd=repo, capture_output=True, text=True)
    check("14. the MERGED tree passes the project's own tests", p.returncode == 0, p.stderr[-200:])

    # The verify invariant, checked mechanically: did any worker write outside what its plan
    # declared? In a wave that declaration is what the gate proved disjointness with, so a diff
    # beyond it means the proof covered something other than what happened.
    for item in BATCH_ITEMS:
        declared = set(SCOPE[item]) | {".workflow/items/%s/changelog.md" % item}
        touched = {ln.strip() for ln in
                   git(repo, "diff", "--name-only", base,
                       results[item]["sha"]).splitlines() if ln.strip()}
        stray = {t for t in touched if t not in declared} & set(FILES)
        check("15.%s %s wrote nothing outside its declared scope" % (item, item),
              not stray, str(stray))


def drive_wave_two(repo):
    print("\n== WAVE 2 — freshness across a real wave boundary ==")
    rc, out, _ = script(repo, "plan_freshness.py", "--project-root", repo, "--json")
    res = {r["id"]: r for r in json.loads(out)["results"]}

    check("16. E is SUSPECT — wave 1 landed under the plan it declares",
          res["E"]["state"] == "suspect" and "src/a.py" in res["E"]["moved"],
          "%s moved=%s" % (res["E"]["state"], res["E"]["moved"]))
    check("17. an untouched plan is still FRESH — staleness is not contagious",
          res["F"]["state"] == "fresh", res["F"]["state"])
    check("18. the classifier reports exit 1 when anything is not fresh", rc == 1, "rc=%d" % rc)

    rc, out, _ = script(repo, "check_wave_independence.py", "--project-root", repo, "--json")
    gate = {c["id"]: c for c in json.loads(out)["candidates"]}
    check("19. the gate refuses to spend E on a stale plan",
          gate["E"]["freshness"] == "suspect" and not gate["E"]["eligible"],
          "freshness=%s eligible=%s" % (gate["E"]["freshness"], gate["E"]["eligible"]))

    # A refresh, performed exactly as `planner:refresh` is specified to leave things.
    head = git(repo, "rev-parse", "HEAD").strip()
    plan(repo, "E", ["src/a.py"], base=head, count=1)
    rc, out, _ = script(repo, "plan_freshness.py", "--project-root", repo, "--json", "E")
    check("20. after a refresh E is FRESH again and carries its refresh count",
          json.loads(out)["results"][0]["state"] == "fresh"
          and json.loads(out)["results"][0]["refresh_count"] == 1,
          out.strip()[:120])

    plan(repo, "E", ["src/a.py"], base=head, count=2)
    rc, out, _ = script(repo, "plan_freshness.py", "--project-root", repo, "--json", "E")
    r = json.loads(out)["results"][0]
    check("21. at the refresh cap E routes to a full RE-PLAN, untouched tree or not",
          r["state"] == "replan" and "cap" in r["why"], r["why"])

    open(os.path.join(repo, "src", "f.py"), "w").write("VALUE = 99\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "delete nothing, move f")
    git(repo, "rm", "-q", "src/f.py")
    git(repo, "commit", "-q", "-m", "remove f")
    rc, out, _ = script(repo, "plan_freshness.py", "--project-root", repo, "--json", "F")
    r = json.loads(out)["results"][0]
    check("22. a DELETED declared file voids the plan rather than dating it",
          r["state"] == "replan" and "deleted" in r["why"], r["why"])

    rc, out, _ = script(repo, "wave_build.py", "mint", "D", "F")
    check("23. the next wave gets a different name", out.strip().startswith("w-"), out.strip())


def main():
    repo = tempfile.mkdtemp(prefix="wave-exit-test-")
    print("driving the wave exit test in %s" % repo)
    try:
        build_repo(repo)
        wave, results = drive_wave_one(repo)
        if wave:
            merge_and_check(repo, results)
            drive_wave_two(repo)
    finally:
        keep = os.environ.get("KEEP_EXIT_TEST_REPO")
        if keep:
            print("\n(repo kept at %s)" % repo)
        else:
            shutil.rmtree(repo, ignore_errors=True)

    print("\n%d checks, %d failed" % (len(STEPS), len(FAILURES)))
    if FAILURES:
        print("\nCOHERENCE NOT SHOWN:")
        for f in FAILURES:
            print("  - %s" % f)
        return 1
    print("COHERENT: a fanned-out wave merged clean, kept every worker's change, passed the "
          "project's own tests on the merged tree, stayed inside every declared scope, and the "
          "freshness lifecycle held across the wave boundary.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

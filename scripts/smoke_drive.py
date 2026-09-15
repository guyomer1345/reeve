#!/usr/bin/env python3
"""The smoke drive — the package as an INSTALLED, RUNNING WHOLE, once, before a release.

WHY IT EXISTS, in one number. Two live drives found FOUR package defects that 1,137 unit tests
and three green exit-test harnesses found none of — two of them shipped hours earlier, and one
would have blocked the first commit of every project bootstrapped from that version. Not one of
the four was a bug *in* a component. Every one was a bug *between* components, and the blind spot
is structural: nothing tested the package as an installed, running whole. This repo has now
learned that lesson three times; the first fix was a documented manual step, and a documented
step nobody runs is not a control.

WHAT IT DOES. Throwaway repo → a real install derived from `MANIFEST.json` → a real `/start` →
one real item through `planner` → `execute` → `verify` → `document` → `commit` → assertions.
BOTH bootstrap modes, because the defect that made this necessary (brownfield never minting a
goal) is only visible when the two paths are compared.

THREE CONSTRAINTS, EACH LEARNED RATHER THAN CHOSEN.

  1. IT CAN NEVER JOIN THE ROUTINE SUITE. It spends real model calls and takes roughly forty
     minutes. It is a deliberate pre-release gate, run beside `build-release.py --check`.

  2. IT ASSERTS SEAMS, NOT BEHAVIOUR. Did the install close · did a real `git commit` land with
     the real `guard.sh` in the way · was a spec-approval receipt written AND accepted by the
     gate · does the code map see only product files · is a `goal.json` present on BOTH paths ·
     was the dispatch boundary's viability question actually recorded · is there a resume anchor
     naming a base commit. Asserting what the model *wrote* would be flaky and would prove
     nothing; a seam either connects or it does not.

  3. IT MUST BE ABLE TO GO RED. Every assertion here is a PURE FUNCTION over the finished tree,
     and `--self-test` builds a tree that satisfies all of them, then breaks each seam in turn
     and requires that exactly that assertion — and no other — fails. That half costs nothing
     and runs in the routine suite, which is the only reason the expensive half can be trusted:
     a forty-minute green light nobody has ever seen go red is not evidence.

METHOD RESIDUE, recorded so the next session does not rediscover it. `claude -p` nested inside a
session works. `.claude/` is write-guarded ABOVE the settings allowlist, so `/start` cannot
complete non-interactively — the harness therefore performs the manifest install itself and lets
`/start` do the rest. The target repo needs its own `.claude/settings.local.json` allowlist,
because `--permission-mode bypassPermissions` is refused.

  scripts/smoke_drive.py --self-test          # the negative controls; no model calls
  scripts/smoke_drive.py --mode both          # the real thing; real tokens, ~40 minutes
"""
import argparse
import json
import re
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
PRODUCT = os.path.join(ROOT, "product")
sys.path.insert(0, os.path.join(ROOT, "scripts"))

FAILURES, STEPS = [], []

# The receipt is what turns this from a documented step into a control. `build-release.py --out`
# refuses to emit without one at the current HEAD, so "run the smoke drive before a release" is
# no longer a sentence somebody has to remember -- which is the same lesson, for the third time:
# a documented step nobody runs is not a control.
RECEIPT = os.path.join(ROOT, ".smoke-receipt.json")


def check(label, ok, detail=""):
    STEPS.append((label, bool(ok), detail))
    if not ok:
        FAILURES.append("%s%s" % (label, ("  -- " + detail) if detail else ""))
    print("  %s %s%s" % ("PASS" if ok else "FAIL", label, ("  -- " + detail) if detail else ""))
    return bool(ok)


def git(repo, *args):
    return subprocess.run(("git", "-C", repo) + args, capture_output=True, text=True)


def load_manifest():
    with open(os.path.join(PRODUCT, "MANIFEST.json"), encoding="utf-8") as fh:
        return json.load(fh)


# --------------------------------------------------------------- the seams, as pure functions
#
# Each takes the finished repo and answers (ok, detail). Nothing here inspects prose: a seam
# either connects or it does not, and that is the whole reason these can be trusted at all.

def seam_install_closed(repo):
    """Every file the manifest promises to install is present AND is the file we shipped."""
    missing, differing = [], []
    for entry in load_manifest().get("install", []):
        src = os.path.join(PRODUCT, entry["src"])
        dest = os.path.join(repo, entry["dest"])
        if not os.path.exists(dest):
            missing.append(entry["dest"])
        elif os.path.isfile(src) and os.path.isfile(dest):
            with open(src, "rb") as a, open(dest, "rb") as b:
                if a.read() != b.read():
                    differing.append(entry["dest"])
    if missing:
        return False, "not installed: %s" % ", ".join(sorted(missing)[:4])
    if differing:
        return False, "installed but stale: %s" % ", ".join(sorted(differing)[:4])
    return True, "%d install entries present and identical" % len(load_manifest()["install"])


def seam_commit_landed_through_the_guard(repo):
    """A real commit, with the real pre-commit hook in the way when it landed.

    The distinction matters and is exactly the class of defect this harness exists for: a commit
    that landed because the gate was absent looks identical, in git, to one the gate approved.
    """
    hook = os.path.join(repo, ".git", "hooks", "pre-commit")
    if not os.path.exists(hook):
        return False, "no .git/hooks/pre-commit — a commit here proves nothing"
    if not os.access(hook, os.X_OK):
        return False, "pre-commit hook is present but not executable — it never ran"
    log = git(repo, "log", "--oneline").stdout.strip().splitlines()
    if not log:
        return False, "no commits at all"
    return True, "%d commit(s), guard installed and executable" % len(log)


def seam_spec_approval_accepted(repo):
    """If the drive crossed the autonomy floor, the receipt exists AND the gate accepts it.

    Written-but-rejected is the interesting failure: a receipt the commit gate refuses is a
    project that can never commit again, and it is invisible from the writing side.
    """
    path = os.path.join(repo, ".workflow", "spec-approval.json")
    if not os.path.exists(path):
        return True, "no floor crossing in this drive (not a failure)"
    try:
        with open(path, encoding="utf-8") as fh:
            rec = json.load(fh)
    except (OSError, ValueError) as exc:
        return False, "receipt is unreadable: %s" % exc
    for field in ("spec_sha256", "ticket_id", "spec_path"):
        if not rec.get(field):
            return False, "receipt is missing `%s`, so the commit gate will refuse it" % field
    spec = os.path.join(repo, rec["spec_path"])
    if not os.path.exists(spec):
        return False, "receipt names %s, which does not exist" % rec["spec_path"]
    import hashlib
    with open(spec, "rb") as fh:
        actual = hashlib.sha256(fh.read()).hexdigest()
    if actual != rec["spec_sha256"]:
        return False, "receipt approves a spec digest that no longer matches the spec"
    return True, "receipt written and its digest still matches"


def seam_code_map_sees_only_product_files(repo):
    """The map is of the PRODUCT. A map that had ingested the workflow's own machinery would
    make every later blast-radius answer wrong, quietly."""
    path = os.path.join(repo, "docs", "knowledge", "graph.json")
    if not os.path.exists(path):
        for alt in ("project/docs/knowledge/graph.json", ".workflow/docs/knowledge/graph.json"):
            if os.path.exists(os.path.join(repo, alt)):
                path = os.path.join(repo, alt)
                break
        else:
            return False, "no code map was generated"
    try:
        with open(path, encoding="utf-8") as fh:
            graph = json.load(fh)
    except (OSError, ValueError) as exc:
        return False, "code map is unreadable: %s" % exc
    nodes = graph.get("nodes") or []
    leaked = [n.get("path") for n in nodes
              if isinstance(n.get("path"), str)
              and (n["path"].startswith(".claude/") or n["path"].startswith(".workflow/")
                   or "/.claude/" in n["path"] or "/.workflow/" in n["path"])]
    if leaked:
        return False, "the map ingested the workflow's own files: %s" % ", ".join(leaked[:4])
    # EMPTY IS NOT CLEAN, and the harness's own first run is why this is here: greenfield passed
    # this seam with ZERO nodes, because nothing had been built yet. An assertion that cannot
    # tell "mapped nothing forbidden" from "mapped nothing" is half a seam — it would stay green
    # through a code map that had stopped working entirely.
    if not nodes:
        source = _product_source(repo)
        if source:
            return False, ("the map is EMPTY while %d source file(s) exist under the project "
                           "root (e.g. %s) — that is a map that did not run, not a clean one"
                           % (len(source), ", ".join(source[:3])))
        return False, ("the map is empty and so is the project — this run built nothing, so "
                       "the seam has nothing to attest")
    return True, "%d node(s), none of them package machinery" % len(nodes)


def _product_source(repo):
    """Source files under the configured project root — what a code map is supposed to see."""
    try:
        with open(os.path.join(repo, ".workflow", "config.json"), encoding="utf-8") as fh:
            root = (json.load(fh) or {}).get("project_root") or "."
    except (OSError, ValueError):
        root = "."
    base = os.path.normpath(os.path.join(repo, root))
    exts = (".py", ".js", ".ts", ".tsx", ".jsx", ".go", ".rs", ".java", ".rb", ".cs")
    found = []
    for dirpath, dirnames, filenames in os.walk(base):
        dirnames[:] = [d for d in dirnames
                       if d not in (".git", ".claude", ".workflow", "node_modules", "__pycache__")]
        for name in filenames:
            if name.endswith(exts):
                found.append(os.path.relpath(os.path.join(dirpath, name), repo))
    return sorted(found)


def seam_goal_minted(repo):
    """A goal on BOTH bootstrap paths. Brownfield failing to mint one is the defect that made
    comparing the two modes a requirement rather than a nicety."""
    path = os.path.join(repo, ".workflow", "goal.json")
    if not os.path.exists(path):
        return False, "no .workflow/goal.json — this path never minted a goal"
    try:
        with open(path, encoding="utf-8") as fh:
            goal = json.load(fh)
    except (OSError, ValueError) as exc:
        return False, "goal.json is unreadable: %s" % exc
    if not goal.get("id"):
        return False, "goal.json carries no id, so convergence has nothing to measure against"
    return True, "goal %s" % goal["id"]


def seam_viability_was_recorded(repo):
    """The dispatch boundary's recorded answer to "what else could run right now?". Its absence
    means an `execute` went out without the question being asked — which the guard should have
    refused, so an absent record on a tree that committed means the guard did not fire."""
    path = os.path.join(repo, ".workflow", "wave-decision.json")
    if not os.path.exists(path):
        return False, "no wave-decision.json — the boundary never recorded a verdict"
    try:
        with open(path, encoding="utf-8") as fh:
            rec = json.load(fh)
    except (OSError, ValueError) as exc:
        return False, "wave-decision.json is unreadable: %s" % exc
    if "considered" not in rec:
        return False, "the record names nothing it considered"
    return True, "considered %d candidate(s)" % len(rec.get("considered") or [])


# The SAME question the shipped gate asks, deliberately asked the same way: `context_band.py`
# now refuses to call an anchor written until it names a base commit, and a seam that accepted
# a weaker anchor than the gate does would go green on a tree the package itself would block.
# Kept as its own expression rather than importing the shipped module — this harness asserts
# over a finished tree from outside, and importing the thing under test is how a seam starts
# agreeing with a bug.
BASE_SHA_RE = re.compile(r"(?i)base[_\s-]?sha\W{0,6}\b([0-9a-f]{7,40})\b")


def seam_resume_anchor(repo):
    """A handoff naming a base commit — what a cleared or dead session resumes from."""
    path = os.path.join(repo, ".workflow", "handoff.md")
    if not os.path.exists(path):
        return False, "no .workflow/handoff.md"
    text = open(path, encoding="utf-8").read()
    m = BASE_SHA_RE.search(text)
    if not m:
        # The word alone was the old bar, and it is not enough: `base_sha: unknown` is the
        # shape a session writes when it did not look, and it reads as a field that is there.
        why = ("names `base_sha` but no commit id after it"
               if "base_sha" in text else "names no base_sha at all")
        return False, "the anchor %s, so a resume cannot read the diff since it" % why
    return True, "anchor present, names base commit %s" % m.group(1)[:12]


def seam_worker_budget_saw_a_real_worker(repo):
    """The hook behind ask #3, which had never been observed to run at all.

    `worker_budget.py` is built to fail silent on every path, and one of those paths — no
    `agent_id` on the payload — is also its NORMAL exit, because it is registered on PostToolUse
    with no matcher and therefore fires on the orchestrator's own tool calls. So a dead trigger
    and a healthy loop produced exactly the same evidence: none. The ask was ticked off against
    a mechanism nobody could show had ever executed.

    The hook now drops a breadcrumb per exit under `.workflow/worker-budget/`, and THIS DRIVE
    holds the fact that makes them readable: a real item went through a real `reeve:execute`,
    so workers certainly ran. Under that condition `located.json` is not optional.

    What it proves: the reading half ran inside a worker and resolved that worker's own
    transcript. What it does NOT prove, stated here rather than left to be assumed: that the
    yield INSTRUCTION was ever acted on. A worker is free to ignore it — `PostToolUse` can add
    context, it cannot stop a model. That ceiling is the hook's by design; this seam closes the
    gap between "cannot be proven to work" and "cannot be proven to be obeyed", which are very
    different admissions.
    """
    d = os.path.join(repo, ".workflow", "worker-budget")
    if not os.path.isdir(d):
        return False, ("no breadcrumbs at all — the hook never ran on any tool call, so this is "
                       "an INSTALL or registration failure, not a trigger failure")
    seen = sorted(n[:-5] for n in os.listdir(d) if n.endswith(".json"))
    if "located" in seen:
        try:
            with open(os.path.join(d, "located.json"), encoding="utf-8") as fh:
                rec = json.load(fh)
        except (OSError, ValueError) as exc:
            return False, "located.json is unreadable: %s" % exc
        return True, ("read a real worker at %s%% (%s tokens), %d observation(s); fired=%s"
                      % (rec.get("pct"), rec.get("used"), rec.get("count"), rec.get("fired")))
    if "no-transcript" in seen:
        try:
            with open(os.path.join(d, "no-transcript.json"), encoding="utf-8") as fh:
                tried = (json.load(fh) or {}).get("tried") or []
        except (OSError, ValueError):
            tried = []
        return False, ("a worker was identified and its transcript was NOT found — the locator "
                       "is wrong. It tried: %s" % (", ".join(tried[:3]) or "nothing"))
    return False, ("only %s — a real worker ran and the hook never saw one, so `agent_id` does "
                   "not reach it and the mechanism is a permanent no-op" % ", ".join(seen))


def _hook_scripts(settings_obj):
    """Every hook script named anywhere in a settings object, by basename.

    Basename rather than the whole command because `/start` is free to rewrite the path prefix
    (`$CLAUDE_PROJECT_DIR` vs an absolute root) and that rewrite is not the thing under test.
    """
    names = set()
    hooks = settings_obj.get("hooks")
    if not isinstance(hooks, dict):
        return names
    for entries in hooks.values():
        for entry in entries if isinstance(entries, list) else []:
            for hook in (entry or {}).get("hooks") or []:
                cmd = hook.get("command")
                if not isinstance(cmd, str):
                    continue
                for tok in re.findall(r"[\w.-]+\.(?:py|sh)", cmd):
                    names.add(os.path.basename(tok))
    return names


def seam_shipped_hooks_are_REGISTERED(repo):
    """A hook file that is installed but not registered is a hook that does nothing.

    `install closed` checks that every manifest destination EXISTS, and that is a different
    question. Found the hard way: a `--resume` re-installed the package into a kept tree, put
    `worker_budget.py` on disk, and left `.claude/settings.json` exactly as an older `/start`
    had written it — no PostToolUse registration for it at all. The tree then ran a real item,
    dispatched real workers, and produced not one breadcrumb, while `install closed` stayed
    green. The registration is written by `/start`, and `--resume` skips `/start`.

    The package's OWN `templates/settings.json` is the expectation, so this seam needs no list
    of its own to drift out of date: ship a new hook, register it there, and this starts
    requiring it everywhere.
    """
    tree = os.path.join(repo, ".claude", "settings.json")
    if not os.path.exists(tree):
        return False, "the tree has no .claude/settings.json — nothing is registered at all"
    try:
        with open(tree, encoding="utf-8") as fh:
            got = _hook_scripts(json.load(fh))
        with open(os.path.join(PRODUCT, "templates", "settings.json"), encoding="utf-8") as fh:
            want = _hook_scripts(json.load(fh))
    except (OSError, ValueError) as exc:
        return False, "settings are unreadable: %s" % exc
    if not want:
        return False, "the package template registers no hooks — the seam has nothing to check"
    missing = sorted(want - got)
    if missing:
        return False, ("installed but NOT REGISTERED: %s — %s on disk and never invoked"
                       % (", ".join(missing),
                          "it is" if len(missing) == 1 else "they are"))
    return True, "all %d shipped hook(s) registered" % len(want)


def seam_the_report_RENDERS_in_the_installed_tree(repo):
    """The four-field report, produced by the tree's own copy against the tree's own state.

    Between-component by construction and free of model cost: it runs the INSTALLED
    `status_report.py`, which imports `converge.py` out of the same installed directory and reads
    the real `goal.json`, `parked/` and items this drive produced. Unit tests build their own
    fixtures; this is the first thing that renders a report over a project a model actually made.

    What it checks beyond "it ran": the four fields are present in order, and **no id reaches the
    output without its name** — the lint runs over the block the renderer just produced, which is
    the one place that invariant can be checked against real data rather than a fixture.
    """
    script = os.path.join(repo, ".claude", "scripts", "status_report.py")
    if not os.path.exists(script):
        return False, "status_report.py is not installed — the report has no producer"
    p = subprocess.run(["python3", script, "--workflow", ".workflow"], cwd=repo,
                       capture_output=True, text=True, timeout=120)
    if p.returncode != 0:
        return False, "the renderer failed: %s" % (p.stderr or "").strip()[:200]
    block = p.stdout
    for field in ("GOAL —", "ACHIEVED", "IN FLIGHT", "LEFT", "[reeve-report state:"):
        if field not in block:
            return False, "the block is missing `%s`" % field
    lint = subprocess.run(["python3", script, "--workflow", ".workflow", "--check", "-"],
                          cwd=repo, input=block, capture_output=True, text=True, timeout=120)
    if lint.returncode != 0:
        return False, ("the report printed an id with no name: %s"
                       % (lint.stderr or "").strip().splitlines()[:1])
    return True, "four fields + marker, every id named (%d chars)" % len(block)


def seam_the_turn_gate_REFUSES_a_stop_for_nothing(repo):
    """The hook, run the way the harness runs it, against the tree this drive actually built.

    `shipped hooks are registered` proves it would be invoked; this proves that when it IS
    invoked it can reach its own judgement — import `turn_check` out of the installed scripts
    directory, read the real `state.json`/`parked/`/`goal.json`, and block. That is the whole
    between-component surface, and it costs no model calls, which is why it is asserted here
    rather than by driving another real session.

    **What it cannot prove, stated rather than implied:** that Claude Code invokes `Stop` hooks at
    all. Nothing in a throwaway tree can establish that; the registration seam and a sibling hook
    already live in the field are the evidence for it.

    SKIPPED, not failed, when the tree is legitimately allowed to stop — a drive that ended with
    the backlog empty (`idle`) or a checkpoint parked has no stop-for-nothing to refuse, and
    grading it red would be grading the drive's luck.
    """
    hook = os.path.join(repo, ".claude", "hooks", "turn_gate.py")
    if not os.path.exists(hook):
        return False, "turn_gate.py is not installed — nothing enforces the turn ladder"
    checker = os.path.join(repo, ".claude", "scripts", "turn_check.py")
    if not os.path.exists(checker):
        return False, "turn_check.py is not installed — the hook has no judgement to reach"
    verdict = subprocess.run(["python3", checker, "--workflow", ".workflow", "--json"], cwd=repo,
                             capture_output=True, text=True, timeout=120)
    try:
        owed = json.loads(verdict.stdout or "{}")
    except ValueError:
        return False, "turn_check.py did not answer: %s" % (verdict.stderr or "")[:200]
    payload = json.dumps({"hook_event_name": "Stop", "cwd": repo})
    p = subprocess.run(["python3", hook], input=payload, capture_output=True, text=True,
                       timeout=120, env=dict(os.environ, REEVE_DRIVE="1"))
    blocked = p.returncode == 2 or '"decision": "block"' in (p.stdout or "")
    if not owed.get("demand"):
        return True, "nothing owed (%s) — the tree may legitimately stop; not graded" % owed.get("why", "")[:80]
    if not blocked:
        return False, ("the ladder says `%s` is owed and the hook let the turn end — it is "
                       "installed and inert" % owed["demand"])
    return True, "refused a stop owing `%s`" % owed["demand"]


SEAMS = [
    ("install closed", seam_install_closed),
    ("commit landed through the guard", seam_commit_landed_through_the_guard),
    ("spec-approval receipt accepted", seam_spec_approval_accepted),
    ("code map sees only product files", seam_code_map_sees_only_product_files),
    ("goal minted", seam_goal_minted),
    ("viability recorded at the boundary", seam_viability_was_recorded),
    ("resume anchor written", seam_resume_anchor),
    ("worker budget observed a real worker", seam_worker_budget_saw_a_real_worker),
    ("shipped hooks are registered", seam_shipped_hooks_are_REGISTERED),
    ("the report renders", seam_the_report_RENDERS_in_the_installed_tree),
    ("the turn gate refuses a stop for nothing", seam_the_turn_gate_REFUSES_a_stop_for_nothing),
]


def assert_seams(repo, label):
    print("\n== seams (%s) ==" % label)
    ok = True
    for name, fn in SEAMS:
        try:
            passed, detail = fn(repo)
        except Exception as exc:                      # a seam check must never crash the run
            passed, detail = False, "check raised: %r" % exc
        ok = check("%s: %s" % (label, name), passed, detail) and ok
    return ok


# ------------------------------------------------------------------ the negative controls
#
# THE HALF THAT MAKES THE OTHER HALF WORTH RUNNING. A forty-minute gate nobody has seen go red
# is not evidence of anything. This builds a tree every seam accepts, then breaks each seam in
# turn and requires that EXACTLY that one fails -- a break that trips two assertions means one
# of them is not measuring what it claims to.
#
# It costs nothing and runs in the routine suite. The drive never can.

def _good_tree(repo):
    """The smallest tree every seam above accepts."""
    import hashlib
    os.makedirs(os.path.join(repo, ".workflow"), exist_ok=True)
    os.makedirs(os.path.join(repo, "docs", "knowledge"), exist_ok=True)
    os.makedirs(os.path.join(repo, "src"), exist_ok=True)

    for entry in load_manifest().get("install", []):
        src, dest = os.path.join(PRODUCT, entry["src"]), os.path.join(repo, entry["dest"])
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        (shutil.copytree if os.path.isdir(src) else shutil.copy)(
            src, dest, **({"dirs_exist_ok": True} if os.path.isdir(src) else {}))

    spec_dir = os.path.join(repo, "docs")
    with open(os.path.join(spec_dir, "spec.md"), "w", encoding="utf-8") as fh:
        fh.write("# spec\n")
    digest = hashlib.sha256(open(os.path.join(spec_dir, "spec.md"), "rb").read()).hexdigest()
    _json(repo, ".workflow/spec-approval.json",
          {"spec_sha256": digest, "ticket_id": "TCK-1", "spec_path": "docs/spec.md"})
    _json(repo, "docs/knowledge/graph.json",
          {"root": ".", "nodes": [{"path": "src/app.py"}], "edges": []})
    shutil.copy(os.path.join(PRODUCT, "templates", "settings.json"),
                os.path.join(repo, ".claude", "settings.json"))
    _json(repo, ".workflow/config.json", {"project_root": "."})
    _json(repo, ".workflow/goal.json",
          {"id": "G-1", "statement": "ship it",
           "acceptance": [{"id": "ga-1", "text": "the thing works"}]})
    _json(repo, ".workflow/state.json", {"status": "building", "node": "execute"})
    _json(repo, ".workflow/wave-decision.json",
          {"considered": ["i1"], "batch": ["i1"], "head": "deadbeef"})
    with open(os.path.join(repo, ".workflow", "handoff.md"), "w", encoding="utf-8") as fh:
        fh.write("# handoff\nbase_sha: deadbeef\n")
    _json(repo, ".workflow/worker-budget/located.json",
          {"outcome": "located", "count": 3, "used": 55_791, "pct": 27.9, "fired": False})
    with open(os.path.join(repo, "src", "app.py"), "w", encoding="utf-8") as fh:
        fh.write("x = 1\n")

    subprocess.run(["git", "init", "-q", repo], check=True, capture_output=True)
    for k, v in (("user.email", "t@t"), ("user.name", "t")):
        git(repo, "config", k, v)
    hook = os.path.join(repo, ".git", "hooks", "pre-commit")
    with open(hook, "w", encoding="utf-8") as fh:
        fh.write("#!/bin/sh\nexit 0\n")
    os.chmod(hook, 0o755)
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "feat: seed")
    return repo


def _json(repo, rel, obj):
    path = os.path.join(repo, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh)


def _break_install(repo):
    os.remove(os.path.join(repo, load_manifest()["install"][0]["dest"]))


def _break_guard(repo):
    os.remove(os.path.join(repo, ".git", "hooks", "pre-commit"))


def _break_approval(repo):
    # Written but no longer matching — the failure that is invisible from the writing side.
    with open(os.path.join(repo, "docs", "spec.md"), "a", encoding="utf-8") as fh:
        fh.write("changed after approval\n")


def _break_code_map(repo):
    _json(repo, "docs/knowledge/graph.json",
          {"root": ".", "nodes": [{"path": "src/app.py"}, {"path": ".claude/scripts/bus.py"}],
           "edges": []})


def _break_goal(repo):
    os.remove(os.path.join(repo, ".workflow", "goal.json"))


def _break_viability(repo):
    os.remove(os.path.join(repo, ".workflow", "wave-decision.json"))


def _break_anchor(repo):
    with open(os.path.join(repo, ".workflow", "handoff.md"), "w", encoding="utf-8") as fh:
        fh.write("# handoff\nno commit named here\n")


def _break_anchor_by_naming_no_commit(repo):
    """The half the old seam let through: the FIELD is there and the COMMIT is not.

    `base_sha: unknown` reads as a field that was filled in, and a substring check for the
    word cannot tell it from one that was. Same shape as *empty is not clean* one seam over —
    an assertion that cannot distinguish "answered" from "answered with nothing".
    """
    with open(os.path.join(repo, ".workflow", "handoff.md"), "w", encoding="utf-8") as fh:
        fh.write("# handoff\nbase_sha: unknown\n")


def _break_code_map_by_emptying_it(repo):
    """The case the harness's own first run passed vacuously: a map with nothing in it, over a
    project that has source to map."""
    _json(repo, "docs/knowledge/graph.json", {"root": ".", "nodes": [], "edges": []})


def _break_worker_budget_by_never_running(repo):
    """The install/registration failure: no breadcrumbs at all."""
    shutil.rmtree(os.path.join(repo, ".workflow", "worker-budget"))


def _break_worker_budget_by_never_seeing_a_worker(repo):
    """THE FAILURE THIS SEAM WAS BUILT FOR, and the one that hid for two phases: the hook runs
    on every tool call and only ever takes the orchestrator exit. Indistinguishable from health
    until something recorded which exit was taken."""
    d = os.path.join(repo, ".workflow", "worker-budget")
    os.remove(os.path.join(d, "located.json"))
    _json(repo, ".workflow/worker-budget/no-agent-id.json",
          {"outcome": "no-agent-id", "count": 412,
           "payload_keys": ["cwd", "session_id", "tool_name", "transcript_path"]})


def _break_worker_budget_by_losing_the_transcript(repo):
    """The locator failure — an agent id arrived and its transcript was not found. Kept apart
    from the one above because the two send you to different files: this one to the locator,
    that one to the payload."""
    d = os.path.join(repo, ".workflow", "worker-budget")
    os.remove(os.path.join(d, "located.json"))
    _json(repo, ".workflow/worker-budget/no-transcript.json",
          {"outcome": "no-transcript", "count": 9, "agent_id": "a1",
           "tried": ["/p/subagents/agent-a1.jsonl"]})


def _break_registration_by_staleness(repo):
    """THE REAL SHAPE: settings written by an older /start, package files refreshed over it."""
    path = os.path.join(repo, ".claude", "settings.json")
    with open(path, encoding="utf-8") as fh:
        obj = json.load(fh)
    obj["hooks"]["PostToolUse"] = [e for e in obj["hooks"]["PostToolUse"]
                                   if "worker_budget" not in json.dumps(e)]
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh)


def _break_report_by_uninstalling_the_renderer(repo):
    """The report has no producer — which is what "the format is a rule in a SKILL.md" looks
    like from outside once the rule is the only thing left."""
    os.remove(os.path.join(repo, ".claude", "scripts", "status_report.py"))


def _break_report_by_dropping_a_field(repo):
    """A renderer that still runs and still looks like a report. The four fields are the ask;
    a block missing one is the "long and jumbled" prose it replaced, wearing the marker."""
    with open(os.path.join(repo, ".claude", "scripts", "status_report.py"), "w",
              encoding="utf-8") as fh:
        fh.write("print('GOAL — something\n\nACHIEVED (0)\n\n[reeve-report state:000000000000]')\n")


def _break_turn_gate_by_uninstalling_it(repo):
    os.remove(os.path.join(repo, ".claude", "hooks", "turn_gate.py"))


def _break_turn_gate_by_making_it_INERT(repo):
    """THE FAILURE THE SEAM EXISTS FOR, and the one `D222` taught: a hook that is installed,
    registered, runs, and does nothing. Indistinguishable from a healthy loop unless something
    asks the ladder what was owed and then checks that the hook acted on it."""
    with open(os.path.join(repo, ".claude", "hooks", "turn_gate.py"), "w",
              encoding="utf-8") as fh:
        fh.write("import sys\nsys.exit(0)\n")


BREAKS = [
    ("code map sees only product files", _break_code_map_by_emptying_it),
    ("install closed", _break_install),
    ("commit landed through the guard", _break_guard),
    ("spec-approval receipt accepted", _break_approval),
    ("code map sees only product files", _break_code_map),
    ("goal minted", _break_goal),
    ("viability recorded at the boundary", _break_viability),
    ("resume anchor written", _break_anchor),
    ("resume anchor written", _break_anchor_by_naming_no_commit),
    ("worker budget observed a real worker", _break_worker_budget_by_never_running),
    ("worker budget observed a real worker", _break_worker_budget_by_never_seeing_a_worker),
    ("worker budget observed a real worker", _break_worker_budget_by_losing_the_transcript),
    ("shipped hooks are registered", _break_registration_by_staleness),
    (("the report renders", "install closed"), _break_report_by_uninstalling_the_renderer),
    (("the report renders", "install closed"), _break_report_by_dropping_a_field),
    (("the turn gate refuses a stop for nothing", "install closed"),
     _break_turn_gate_by_uninstalling_it),
    (("the turn gate refuses a stop for nothing", "install closed"),
     _break_turn_gate_by_making_it_INERT),
]


def _verdicts(repo):
    out = {}
    for name, fn in SEAMS:
        try:
            out[name] = bool(fn(repo)[0])
        except Exception:
            out[name] = False
    return out


def self_test():
    """Green on a good tree; then the named red per break and nothing unexpected. No model calls."""
    print("== self-test: can every seam go red? ==")
    ok = True
    with tempfile.TemporaryDirectory() as tmp:
        good = _good_tree(os.path.join(tmp, "good"))
        base = _verdicts(good)
        ok = check("a good tree passes every seam",
                   all(base.values()),
                   ", ".join(n for n, v in base.items() if not v) or "") and ok

    for target, breaker in BREAKS:
        # A break names the seam it must turn red, and MAY name others it is allowed to trip.
        # The allowance exists for one honest case rather than as a general escape: a break
        # that removes or rewrites a SHIPPED file is supposed to be noticed by `install closed`
        # too — that seam compares bytes against the manifest, and a self-test that called its
        # correct answer a false positive would be training the wrong reflex. Every other break
        # names exactly one seam and the containment assertion is unchanged for them.
        expected = {target} if isinstance(target, str) else set(target)
        primary = target if isinstance(target, str) else target[0]
        with tempfile.TemporaryDirectory() as tmp:
            repo = _good_tree(os.path.join(tmp, "broken"))
            breaker(repo)
            v = _verdicts(repo)
            failed = {n for n, passed in v.items() if not passed}
            ok = check("breaking `%s` turns it red" % primary, primary in failed) and ok
            ok = check("breaking `%s` trips nothing unexpected" % primary,
                       failed <= expected,
                       "also red: %s" % ", ".join(sorted(failed - expected))) and ok
    return ok


# ------------------------------------------------------------------------- the real drive

GREENFIELD_SEED = None          # an empty repo IS the greenfield case

BROWNFIELD_SEED = {
    "README.md": "# notes\n\nA tiny note-taking CLI.\n",
    "CLAUDE.md": "# notes\n\nA tiny note-taking CLI: `add`, `list`, `done`. Notes live in notes.json.\n",
    "notes.py": (
        "import json, sys\n\n"
        "def load(p='notes.json'):\n"
        "    try:\n        return json.load(open(p))\n"
        "    except Exception:\n        return []\n\n"
        "def add(text):\n"
        "    items = load(); items.append({'text': text, 'done': False})\n"
        "    json.dump(items, open('notes.json', 'w'))\n\n"
        "def main(argv):\n"
        "    if argv[:1] == ['add']:\n        add(' '.join(argv[1:]))\n"
        "    else:\n        print('\\n'.join(i['text'] for i in load()))\n\n"
        "if __name__ == '__main__':\n    main(sys.argv[1:])\n"
    ),
}

# The allowlist the target needs. `--permission-mode bypassPermissions` is REFUSED, so the
# permission surface has to be opened the ordinary way, per-project.
TARGET_SETTINGS = {
    "permissions": {"allow": ["Edit", "Write", "Read", "Glob", "Grep", "Task", "TodoWrite",
                              "Bash", "WebSearch", "WebFetch"]},
    "enabledPlugins": {"reeve@reeve": True},
}


def install_package(repo, resuming=False):
    """The manifest install, performed by the harness.

    `/start` does this itself in real life and CANNOT here: `.claude/` is write-guarded above
    the settings allowlist, so a non-interactive `/start` stalls on it. Doing it from the
    manifest keeps the thing under test — that every promised file lands where it is promised —
    honest, because `seam_install_closed` then checks this against the same manifest.

    `.claude/settings.json` IS NOT A MANIFEST ENTRY, and on a resume that is a hole. The hook
    REGISTRATIONS live there and `/start` writes them; a resume skips `/start`, so a kept tree
    took the new hook FILES over an old tree's registrations and ran a whole item with a hook
    that was on disk and never invoked — `install closed` green the entire time, because every
    manifest destination really was present. For a real project the package's own answer is
    `/update`, which owns `templates/settings.json` -> `.claude/settings.json` behind a confirm;
    for a throwaway tree with nothing worth preserving, copying it is that same reconcile.

    ONLY ON A RESUME, deliberately. Doing it on a fresh run would write the registrations that
    `/start` is supposed to write, and `seam_shipped_hooks_are_REGISTERED` would then be
    grading the harness instead of the package.
    """
    for entry in load_manifest().get("install", []):
        src, dest = os.path.join(PRODUCT, entry["src"]), os.path.join(repo, entry["dest"])
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        if os.path.isdir(src):
            shutil.copytree(src, dest, dirs_exist_ok=True)
        else:
            shutil.copy(src, dest)
    if resuming:
        dest = os.path.join(repo, ".claude", "settings.json")
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        shutil.copy(os.path.join(PRODUCT, "templates", "settings.json"), dest)
        print("  refreshed .claude/settings.json (hook registrations) — /start is skipped here")
    _json(repo, ".claude/settings.local.json", TARGET_SETTINGS)


# A tree's OWN RECORD of which bootstrap path made it. Under `.git/` on purpose: it is harness
# metadata, and anywhere else `git add -A` would commit it into the repo under test and it would
# show up in the very diffs the seams read.
MODE_MARKER = os.path.join(".git", "smoke-mode")


def tree_mode(repo):
    """Which mode built this tree, or None if it cannot be known WITHOUT GUESSING.

    `--resume` needs this because the receipt is per mode: attesting the wrong one is not a
    lost run, it is a receipt that says a path was proven when it never ran. The directory name
    is the fallback rather than the primary because the harness chose that name itself — it is
    evidence, but it is evidence a human can rename.
    """
    try:
        with open(os.path.join(repo, MODE_MARKER), encoding="utf-8") as fh:
            val = fh.read().strip()
        if val in ("greenfield", "brownfield"):
            return val
    except OSError:
        pass
    base = os.path.basename(os.path.normpath(repo))
    for mode in ("greenfield", "brownfield"):
        if base.startswith("reeve-smoke-%s-" % mode):
            return mode
    return None


def seed(repo, mode):
    os.makedirs(repo, exist_ok=True)
    subprocess.run(["git", "init", "-q", repo], check=True, capture_output=True)
    with open(os.path.join(repo, MODE_MARKER), "w", encoding="utf-8") as fh:
        fh.write(mode + "\n")
    for k, v in (("user.email", "smoke@local"), ("user.name", "smoke")):
        git(repo, "config", k, v)
    for name, body in (BROWNFIELD_SEED if mode == "brownfield" else {}).items():
        with open(os.path.join(repo, name), "w", encoding="utf-8") as fh:
            fh.write(body)
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "seed", "--allow-empty")


def drive(repo, prompt, timeout):
    """One real session. `claude -p` nested inside a session works — that is measured, not
    assumed — and it is the only way to hand a whole instruction to a real model unattended."""
    print("  → %s" % prompt.splitlines()[0][:100])
    try:
        p = subprocess.run(["claude", "-p", prompt], cwd=repo, capture_output=True,
                           text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return False, "timed out after %ds" % timeout
    except OSError as exc:
        return False, "could not launch claude: %s" % exc
    tail = (p.stdout or p.stderr or "").strip().splitlines()[-3:]
    return p.returncode == 0, " / ".join(tail)[:400]


START_PROMPT = (
    "/reeve:start\n\n"
    "This is an unattended smoke run. Take every decision yourself and never park a "
    "checkpoint for a human — if a gate would block on a person, record the reason and "
    "proceed with the most conservative option. Keep the spec to one small feature."
)

ITEM_PROMPT = (
    "continue\n\n"
    "Take exactly ONE item from the backlog all the way round: plan it, execute it, verify it, "
    "document it, and commit it. Then stop. Never park a checkpoint for a human — this run is "
    "unattended. Do not start a second item."
)


def bootstrapped(repo):
    """Has `/start` already run here? The resume predicate, read from the tree rather than
    remembered — a resumed run must not trust a note it wrote about itself."""
    return os.path.exists(os.path.join(repo, ".workflow", "config.json"))


def run_mode(mode, timeout, keep, resume=None):
    """One bootstrap path, end to end — or the part of it that is not already done.

    `resume` re-enters a KEPT tree and skips the phases it can see are finished. The drive costs
    about an hour per mode, and the run that exposed the first four defects failed in the SECOND
    phase of one mode: repeating the first phase to retry the second buys nothing and costs most
    of the time. The predicate is read off the tree, never from a note the harness left itself.
    """
    print("\n=== %s ===" % mode)
    fresh = resume is None
    repo = resume or tempfile.mkdtemp(prefix="reeve-smoke-%s-" % mode)
    try:
        if fresh:
            seed(repo, mode)
            install_package(repo)
        else:
            print("  resuming %s" % repo)
            # The package under test may have moved since the tree was made; re-installing is
            # the whole point of resuming, and it is the cheap half.
            install_package(repo, resuming=True)

        if bootstrapped(repo):
            check("%s: /start completed" % mode, True, "already bootstrapped — skipped")
        else:
            ok, detail = drive(repo, START_PROMPT, timeout)
            if not check("%s: /start completed" % mode, ok, detail):
                print("  tree kept at %s" % repo)
                return False

        ok2, detail2 = drive(repo, ITEM_PROMPT, timeout)
        check("%s: one item went round" % mode, ok2, detail2)
        good = assert_seams(repo, mode)
        if keep or not good:
            print("  tree kept at %s" % repo)
        return good
    finally:
        if fresh and not keep and not FAILURES:
            shutil.rmtree(repo, ignore_errors=True)


def head():
    p = subprocess.run(["git", "-C", ROOT, "rev-parse", "HEAD"], capture_output=True, text=True)
    return (p.stdout.strip() or None) if p.returncode == 0 else None


def package_digest():
    """The identity the receipt attests to. `build-release.py` owns it — it owns `shipped_files`,
    and a second answer to "what is the package" is the drift this repo's own law forbids."""
    import importlib.util
    path = os.path.join(ROOT, "scripts", "build-release.py")
    spec = importlib.util.spec_from_file_location("build_release", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.package_digest()


def record_mode(mode):
    """Attest ONE mode, against the package it was run on.

    PER MODE AND KEYED ON THE PACKAGE, both for the same reason: a two-hour gate that has to be
    re-run whole after every fix is a gate that gets skipped. Fixing greenfield should cost a
    greenfield run, not a greenfield run plus an hour re-proving a brownfield path nothing
    touched — and a decision-log commit should cost nothing at all, because it cannot change
    what the package does. The digest invalidates exactly the runs a package change invalidates.
    """
    import datetime
    rec = read_receipt() or {}
    modes = rec.get("modes") if isinstance(rec.get("modes"), dict) else {}
    modes[mode] = {
        "package": package_digest(),
        "head": head(),
        "at": datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0)
              .isoformat().replace("+00:00", "Z"),
        "seams": [name for name, _ in SEAMS],
    }
    rec["modes"] = modes
    with open(RECEIPT, "w", encoding="utf-8") as fh:
        json.dump(rec, fh, indent=2, sort_keys=True)
    print("  %s attested for package %s" % (mode, modes[mode]["package"][:12]))


def attested(mode):
    """Is this mode already green on THIS package? The basis for skipping it."""
    rec = read_receipt() or {}
    entry = (rec.get("modes") or {}).get(mode)
    return isinstance(entry, dict) and entry.get("package") == package_digest()


def read_receipt():
    try:
        with open(RECEIPT, encoding="utf-8") as fh:
            val = json.load(fh)
    except (OSError, ValueError):
        return None
    return val if isinstance(val, dict) else None


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--self-test", action="store_true",
                    help="run only the negative controls — no model calls, no tokens")
    ap.add_argument("--assert-only", metavar="DIR",
                    help="re-run the seam assertions against a KEPT tree and exit. No model "
                         "calls, seconds not hours — for iterating on a seam, or re-checking a "
                         "tree after a fix, without paying for the drive again.")
    ap.add_argument("--resume", metavar="DIR",
                    help="re-enter a kept tree, reinstall the package into it, and run only the "
                         "phases it cannot see are already done")
    ap.add_argument("--mode", choices=["greenfield", "brownfield", "both"], default="both")
    ap.add_argument("--timeout", type=int, default=1800, help="seconds per session")
    ap.add_argument("--keep", action="store_true", help="keep the throwaway trees")
    ap.add_argument("--force", action="store_true",
                    help="re-run a mode already attested for this exact package")
    args = ap.parse_args(argv)

    if args.self_test:
        self_test()
    elif args.assert_only:
        assert_seams(args.assert_only, os.path.basename(args.assert_only.rstrip("/")))
    else:
        if not shutil.which("claude"):
            print("smoke_drive: `claude` is not on PATH — this gate drives a real session.")
            return 69
        modes = ["greenfield", "brownfield"] if args.mode == "both" else [args.mode]
        # A RESUME IS ONE TREE, AND A TREE IS ONE MODE. Left alone, `--resume DIR` inherited the
        # default `--mode both` and drove that single tree twice — once labelled greenfield and
        # once brownfield — then attested BOTH. A brownfield tree would have earned greenfield's
        # ✅ on the receipt, which is worse than no receipt: the gate would have gone quiet on a
        # path nothing had run. Caught by reading the first four lines of a real resume.
        if args.resume:
            found = tree_mode(args.resume)
            if not found:
                print("smoke_drive: cannot tell which mode built %s — it carries no marker and "
                      "its name does not say. Re-run it fresh with --mode; a resume will not "
                      "guess, because the receipt it writes is per mode." % args.resume)
                return 2
            if args.mode != "both" and args.mode != found:
                print("smoke_drive: --mode %s contradicts the tree, which is %s. Refusing."
                      % (args.mode, found))
                return 2
            modes = [found]
            print("  resuming a %s tree" % found)
        # SKIP WHAT IS ALREADY PROVEN ON THIS PACKAGE. The receipt is per mode and keyed on the
        # shipped tree, so re-running a green mode against an unchanged package proves nothing
        # and costs an hour. `--force` says otherwise out loud.
        todo = [m for m in modes if args.force or args.resume or not attested(m)]
        for skipped in [m for m in modes if m not in todo]:
            print("  %s: already attested for this package — skipping (--force to re-run)"
                  % skipped)
        if not todo:
            print("smoke_drive: nothing to run; every requested mode is attested.")
        else:
            print("smoke_drive: REAL model calls, about an hour per mode. Never run this in CI.")
        for mode in todo:
            before = len(FAILURES)
            if run_mode(mode, args.timeout, args.keep, resume=args.resume) \
                    and len(FAILURES) == before:
                record_mode(mode)

    print("\n%d step(s), %d failure(s)" % (len(STEPS), len(FAILURES)))
    for f in FAILURES:
        print("  FAIL %s" % f)
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())

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
import glob
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


def _an_item_was_promoted(repo):
    """Did any item reach `document`? The code map has exactly one loop owner and that is it,
    so a drive whose item never got there has nothing to grade — grading it red would report a
    defect in the mechanism when the truth is that the mechanism never ran."""
    items = os.path.join(repo, ".workflow", "items")
    for name in sorted(os.listdir(items)) if os.path.isdir(items) else []:
        if os.path.exists(os.path.join(items, name, "promoted.json")):
            return True
    return False


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
            if not _an_item_was_promoted(repo):
                return True, ("no map, and nothing was due to build one — `document` owns the "
                              "rebuild and no item reached it in this drive")
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
    """A goal on the path that can mint one WITHOUT A HUMAN, and only that path.

    It used to require one on both, and that was this harness making `D221`'s mistake a second
    time. The two paths do not mint it the same way: `planner:decompose` derives it from the
    roadmap it just emitted (greenfield, no human needed past the spec), while **brownfield's is
    written by the RECONCILE CHECKPOINT from the acceptance a human just confirmed**. This drive
    runs with nobody there. So a brownfield tree with no goal is the correct outcome of an
    unattended run, and a session that minted one anyway would have manufactured a confirmation
    nobody gave — which the drive that found this refused to do, in those words, citing the same
    forgery rule that stops it faking a spec receipt.

    **The earlier receipt PASSED this seam on brownfield**, which means a previous session did
    mint one unattended. The seam was rewarding the worse behaviour; that is the whole finding.
    """
    path = os.path.join(repo, ".workflow", "goal.json")
    if not os.path.exists(path):
        if tree_mode(repo) == "brownfield":
            return True, ("no goal, and that is correct here — brownfield mints it from "
                          "acceptance a human confirms at reconcile, and this run had no human")
        return False, "no .workflow/goal.json — this path never minted a goal"
    try:
        with open(path, encoding="utf-8") as fh:
            goal = json.load(fh)
    except (OSError, ValueError) as exc:
        return False, "goal.json is unreadable: %s" % exc
    if not goal.get("id"):
        return False, "goal.json carries no id, so convergence has nothing to measure against"
    # A goal that exists and is not COMMITTED is not a stop condition -- it is a file a `git clean`
    # or a fresh clone loses, and the drive it was minted for reads convergence off it every turn.
    # Run 10 left it staged (no commit edge for `planner:decompose`), and three earlier greenfield
    # runs let it ride an unrelated `feat(...)` commit; this seam saw neither, because it only ever
    # asked whether the file was on disk. Brownfield mints it inside the ingest commit, so the
    # check is the same question on both paths.
    # Asked as `is it in HEAD`, not `does it have a git log`: `git log -- <path>` still answers for a
    # file that was committed and later removed, so the obvious phrasing passes the very tree it is
    # meant to fail. The negative control below is what caught that.
    if git(repo, "cat-file", "-e", "HEAD:.workflow/goal.json").returncode != 0:
        return False, ("goal %s exists in the worktree and is NOT in HEAD -- the drive's stop "
                       "condition is sitting outside git" % goal["id"])
    return True, "goal %s, in HEAD" % goal["id"]


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


def _session_dir(repo):
    """-> Claude Code's transcript directory for a session run in `repo`, or None.

    Meta-only coupling to the CLI's own layout, and acceptable for the same reason
    `dev-reinstall.sh` reaches into the plugin cache: this harness grades an installed whole, so
    it is allowed to read what the install actually produced. `None` means CANNOT TELL, and every
    caller below turns that into a refusal rather than a pass."""
    enc = "-" + re.sub(r"[^A-Za-z0-9]", "-", os.path.abspath(repo).lstrip("/"))
    d = os.path.join(os.path.expanduser("~"), ".claude", "projects", enc)
    return d if os.path.isdir(d) else None


def workers_ran(repo):
    """-> (count, how). GROUND TRUTH for "did a subagent actually run", from the transcripts the
    CLI writes rather than from anything the package itself claims.

    This exists because the seam below asserted it instead of checking it, and then reported a
    confident diagnosis that was false. See `seam_worker_budget_saw_a_real_worker`."""
    d = _session_dir(repo)
    if d is None:
        return None, "no transcript directory for this repo — cannot tell whether a worker ran"
    n = len(glob.glob(os.path.join(d, "*", "subagents", "agent-*.jsonl")))
    return n, "%d subagent transcript(s) under %s" % (n, d)


def _promoted_items(repo):
    """-> ([items carrying the finished marker], [every item dir]).

    `promoted.json` is the package's own finished marker, not one invented here: it is what
    `check_wave_independence.py` treats as "dependency finished", what retention keys pruning on,
    and what `forecast.py` prunes a forecast against. Written by `document`, so it also proves
    the item reached the tail of the loop rather than dying after execute."""
    idir = os.path.join(repo, ".workflow", "items")
    names = sorted(os.listdir(idir)) if os.path.isdir(idir) else []
    done = []
    for name in names:
        try:
            with open(os.path.join(idir, name, "promoted.json"), encoding="utf-8") as fh:
                rec = json.load(fh)
        except (OSError, ValueError):
            continue
        if isinstance(rec, dict) and rec.get("promoted"):
            done.append(name)
    return done, names


def seam_worker_budget_saw_a_real_worker(repo):
    """The hook behind ask #3, which had never been observed to run at all.

    `worker_budget.py` is built to fail silent on every path, and one of those paths — no
    `agent_id` on the payload — is also its NORMAL exit, because it is registered on PostToolUse
    with no matcher and therefore fires on the orchestrator's own tool calls. So a dead trigger
    and a healthy loop produced exactly the same evidence: none. The ask was ticked off against
    a mechanism nobody could show had ever executed.

    The hook now drops a breadcrumb per exit under `.workflow/worker-budget/`, and the reading of
    those breadcrumbs turns entirely on ONE precondition: that a real worker ran at all. This
    seam used to state that precondition in this docstring — *"a real item went through a real
    `reeve:execute`, so workers certainly ran"* — AND NEVER CHECK IT. On a drive whose loop was
    blocked at intake, nothing dispatched a worker, only `no-agent-id` breadcrumbs existed, and
    the seam reported *"`agent_id` does not reach it and the mechanism is a permanent no-op"* —
    about a mechanism the other mode proved working on the same package digest an hour later.

    A FALSE DIAGNOSIS IN THE FAIL DIRECTION IS NOT THE SAFE KIND. It costs the next session a
    hunt for a bug that does not exist, and it discredits the seam that was right. So the
    precondition is now evidence: `workers_ran()` counts the CLI's own subagent transcripts, and
    "no worker ran" is a different verdict from "the hook missed a worker" — still red, because a
    drive that never dispatched one has not tested this, but red for what actually happened.

    What a PASS proves: the reading half ran inside a worker and resolved that worker's own
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
    if "identified-no-transcript" in seen:
        try:
            with open(os.path.join(d, "identified-no-transcript.json"), encoding="utf-8") as fh:
                tried = json.load(fh).get("tried") or []
        except (OSError, ValueError):
            tried = []
        return False, ("a worker was identified and its transcript was NOT found — the locator "
                       "is wrong. It tried: %s" % (", ".join(tried[:3]) or "nothing"))
    # Only `no-agent-id`, which is the hook's normal exit on the ORCHESTRATOR's own tool calls.
    # It is evidence of nothing on its own; what it means depends on whether a worker ever ran.
    n, how = workers_ran(repo)
    if n is None:
        return False, ("only %s, and %s — so this drive cannot say whether the hook is broken "
                       "or was never given a worker to see" % (", ".join(seen), how))
    if n == 0:
        # TWO VERY DIFFERENT UPSTREAM FAILURES, and saying "the loop stopped early" for both is
        # the misdescription this seam has already been fixed for once. If an item went ALL THE
        # WAY ROUND with no worker anywhere, the loop did not stop — the orchestrator did the
        # leaf work ITSELF. `planner`, `execute` and `document` are dispatch-only in the
        # orchestrator brief ("You never do a node's work yourself"; the mechanism is "a property
        # of the node, not a judgement call"), and nothing in the package detects the breach:
        # `dispatch_guard.py` governs HOW you dispatch and refuses a lone wait, never the failure
        # to dispatch at all. That is the architecture's core invariant sitting on prose.
        done, _ = _promoted_items(repo)
        if done:
            return False, ("only %s and %s, yet %s went all the way round — so the loop did not "
                           "stop, the ORCHESTRATOR DID THE LEAF WORK ITSELF. `planner`/`execute`"
                           "/`document` are dispatch-only, and nothing enforces it."
                           % (", ".join(seen), how, ", ".join(done)))
        return False, ("only %s, and NO WORKER EVER RAN (%s) — so this seam tested nothing. The "
                       "failure is upstream: the loop stopped before it dispatched, and no item "
                       "completed either. `no-agent-id` is the hook's normal exit on the "
                       "orchestrator's own tool calls and is not evidence against it."
                       % (", ".join(seen), how))
    return False, ("only %s, yet %s — a real worker ran and the hook never saw one, so "
                   "`agent_id` does not reach it and the mechanism is a permanent no-op"
                   % (", ".join(seen), how))


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

    THE LATCH IS SET ASIDE FOR THE PROBE, and the first run with the gate live is why. The hook
    keeps a demand counter between turns and, past `MAX_DEMANDS`, DELIBERATELY gives up and lets
    the turn end — a hook that blocks forever wedges the session it was protecting. A drive that
    left the counter spent therefore has a hook that exits 0 for the documented reason, and this
    seam read that as "installed and inert": a red seam accusing a hook of doing nothing, on the
    evidence of it doing exactly what it says it does. The probe asks whether the hook BLOCKS
    when something is owed, so it asks from the state that question is about. The give-up path is
    the unit suite's, where it can be tested without a spent latch being mistaken for a dead one.
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
    latch = os.path.join(repo, ".workflow", "turn-gate.json")
    saved = None
    if os.path.exists(latch):
        with open(latch, "rb") as fh:
            saved = fh.read()
        os.remove(latch)
    try:
        p = subprocess.run(["python3", hook], input=payload, capture_output=True, text=True,
                           timeout=120, env=dict(os.environ, REEVE_DRIVE="1"))
    finally:
        # Restore byte for byte — the tree is evidence, and the next seam may read it.
        if saved is not None:
            with open(latch, "wb") as fh:
                fh.write(saved)
        elif os.path.exists(latch):
            os.remove(latch)
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


def _break_goal_by_never_committing_it(repo):
    """The half the old seam let through: the goal EXISTS and is not in git. This is run 10's tree
    exactly -- `planner:decompose` minted it, the router staged it, and no commit edge ever took it.
    Rewrite the history so the file survives in the worktree with no commit behind it."""
    path = os.path.join(repo, ".workflow", "goal.json")
    with open(path, encoding="utf-8") as fh:
        body = fh.read()
    git(repo, "rm", "-q", "--cached", ".workflow/goal.json")
    git(repo, "commit", "-q", "--no-verify", "-m", "drop the goal from history")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(body)


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
    ("goal minted", _break_goal_by_never_committing_it),
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


def _exclude_patterns():
    """The manifest's own `exclude` globs, as `shutil.ignore_patterns` wants them (basenames),
    plus `__pycache__` — which is never copied but is created the instant anything imports the
    installed scripts, and a tree carrying one fails the package's own leak check."""
    pats = [os.path.basename(p) for p in load_manifest().get("exclude", [])]
    return pats + ["__pycache__"]


PLUGIN_STATE = os.path.expanduser("~/.claude/plugins/installed_plugins.json")


def _build_release():
    """`build-release.py` as a module. It OWNS what the package is — `shipped_files` and the
    digest over them — and a second answer to that is the drift this repo's own law forbids."""
    import importlib.util
    path = os.path.join(ROOT, "scripts", "build-release.py")
    spec = importlib.util.spec_from_file_location("build_release", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def package_digest():
    """The identity the receipt attests to."""
    return _build_release().package_digest()


def installed_digest(path):
    """-> the shipped-file digest of an INSTALLED plugin, or None if it cannot be computed.

    `claude plugin install` copies `product/` to the root of a cache directory, so the same
    manifest walk that measures this tree measures the install. `None` means CANNOT TELL — a
    missing directory, an unreadable file, or a copy that is missing a shipped file entirely
    (an old install predating a file that now ships digests to nothing, and must not be allowed
    to compare equal to anything)."""
    if not path or not os.path.isdir(path):
        return None
    try:
        return _build_release().package_digest(root=path)
    except Exception:
        return None


def stale_plugin(repo=None):
    """-> why the installed plugin cannot be trusted for this run, or None.

    THE HOLE THIS CLOSES was found by a drive that had already been paid for. The tree gets its
    scripts and hooks from the manifest at HEAD; the SKILLS, COMMANDS and AGENTS come from the
    plugin cache, which is pinned at whatever commit was last installed. The first run of the
    Phase-13 package drove `/reeve:start` from a plugin five commits old that predated every
    decision under test, and nothing anywhere said so — `install closed` was green, because it
    grades the tree, and the tree was fine.

    IT COMPARES THE PACKAGE, NOT `HEAD`, and that is the second correction this gate has needed.
    Keying on the commit was `D220`'s already-rejected mistake reappearing one layer up: the
    receipt is keyed on the shipped file set precisely because a commit that cannot change
    behaviour must not invalidate an attestation about behaviour. A gate keyed on `HEAD` refuses
    after any meta-only commit — a fix to this very harness — and the prescribed remedy does not
    work on a `--resume`, because `dev-reinstall.sh` updates the user-scope install and cannot
    reach a kept tree's own local registration. That leaves `--allow-stale` as the only door,
    which is the deadlock this gate was rewritten once already to escape. Measured on the run of
    2026-09-15: two installs, two commits apart, digesting to the same `2fb64f8d2fee`.

    UNKNOWABLE IS NOT CURRENT. A missing or unreadable plugin record, an install whose files
    cannot be read, and an install missing a shipped file all return a reason — the gate refuses
    on "cannot tell", because the whole failure being prevented is a receipt that reads as proof
    while measuring something else.

    ONLY THE ENTRIES THAT COULD GOVERN *THIS* RUN ARE READ, and getting that wrong deadlocked the
    gate on its own exhaust. Every drive leaves a permanent `scope: local` registration behind for
    its throwaway `/tmp` tree, and nothing ever removes it. The governing set is every non-local
    entry, plus the local entry for the tree actually being driven, which exists only on
    `--resume`. A local entry for some other directory cannot reach this run, alive or dead."""
    try:
        want = package_digest()
    except Exception as exc:
        return "this repo's own package digest cannot be computed (%s)" % exc
    try:
        with open(PLUGIN_STATE, encoding="utf-8") as fh:
            state = json.load(fh)
    except (OSError, ValueError) as exc:
        return "the installed-plugin record is unreadable (%s)" % exc
    entries = []
    for name, rows in (state.get("plugins") or {}).items():
        if "reeve" in name:
            entries.extend(rows if isinstance(rows, list) else [rows])
    if not entries:
        return "no `reeve` plugin is installed, so `/reeve:start` would not resolve at all"
    target = os.path.realpath(repo) if repo else None
    governing = [e for e in entries if isinstance(e, dict) and _governs(e, target)]
    if not governing:
        return ("no `reeve` plugin is installed for this run — the record holds only local "
                "registrations for other directories, so `/reeve:start` would not resolve")
    bad = []
    for e in governing:
        got = installed_digest(e.get("installPath"))
        if got != want:
            bad.append("%s (%s)" % (str(e.get("gitCommitSha") or "?")[:12],
                                    "unreadable" if got is None else got[:12]))
    if not bad:
        return None
    return ("the installed plugin does not carry this package: %s, and this repo ships %s"
            % (", ".join(sorted(set(bad))), want[:12]))


def _governs(entry, target):
    """Can this registration supply the skills for the session this run is about to launch?

    A `scope: local` entry is bound to one `projectPath` and reaches nothing else. Anything else —
    `user`, `project`, an absent scope this repo does not recognise — is treated as reaching, so
    an unreadable record refuses rather than being quietly filtered into agreement."""
    if entry.get("scope") != "local":
        return True
    path = entry.get("projectPath")
    if not path:
        return True
    return target is not None and os.path.realpath(path) == target


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
            # THE MANIFEST'S `exclude` APPLIES TO A DIRECTORY ENTRY, and this harness ignored it
            # — so `scripts/codemap/test_codemap.py` landed in every tree this drive built, and
            # the drive's own session found it at `/start` step 7 and could not delete it
            # (`.claude/` sits above the settings allowlist). `/start` gets this right and says
            # so in prose; the harness that stands in for `/start` did not, which made the leak
            # look like a product defect when it was the measuring instrument's.
            shutil.copytree(src, dest, dirs_exist_ok=True,
                            ignore=shutil.ignore_patterns(*_exclude_patterns()))
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


def _was_it_moving(repo):
    """After a timeout: was the session WORKING, or had it stopped? -> one sentence.

    A timeout on its own says nothing about which, and the two want opposite fixes: a session
    still writing needs a longer window, a session that stopped writing is the defect. The
    answer is already on disk — `monitor.py`'s pulse is the newest write the loop made, and the
    worker-budget breadcrumb moves on EVERY tool call, so a quiet pulse means no tool call ran.
    The first run to hit this timed out with its last write 24 minutes earlier and `state.json`
    still reading *"grading the batch before marking <item> in flight"*: not slow, stopped.
    """
    try:
        sys.path.insert(0, os.path.join(PRODUCT, "scripts"))
        import monitor
        beat = monitor.pulse(os.path.join(repo, ".workflow"))
    except Exception:                              # noqa: BLE001 — a diagnosis never fails a run
        return "could not tell whether it was still moving"
    if beat is None:
        return "the loop never wrote anything at all"
    import time
    quiet = int(time.time() - beat) // 60
    if quiet < 2:
        return "still writing when it was killed — the window is too short, not the loop"
    return ("STOPPED: the loop wrote nothing for the last %dm, so no tool call ran in that "
            "time — a longer timeout would not have helped" % quiet)


def an_item_actually_completed(repo, session_detail):
    """-> (ok, detail). Did an ITEM go round, or did a SESSION merely exit cleanly?

    `drive()` returns the process's exit status, and `claude -p` exits 0 whenever the model
    finished its turn — including the turn where it explains, at length and correctly, that it
    is blocked and can do nothing. So the step labelled "one item went round" passed on a drive
    whose loop never left intake, and its PASS then propped up a sibling seam that assumed a
    worker must have run. Two loose labels reinforced each other into a confident wrong
    conclusion; this is the half that stops claiming more than it checked.

    `promoted.json` is the package's own finished marker, not one invented here: it is what
    `check_wave_independence.py` treats as "dependency finished", what retention keys pruning
    on, and what `forecast.py` prunes a forecast against. Written by `document`, so it also
    proves the item reached the tail of the loop rather than dying after execute.
    """
    done, started = _promoted_items(repo)
    if done:
        return True, "%s promoted / %s" % (", ".join(done), session_detail)
    return False, ("the session exited 0 but NO item carries a `promoted.json` marker, so "
                   "nothing went round (%s). The session's own last words: %s"
                   % ("items started: " + ", ".join(started) if started
                      else "no item dir was ever created", session_detail))


def drive(repo, prompt, timeout, drive_turn=True):
    """One real session. `claude -p` nested inside a session works — that is measured, not
    assumed — and it is the only way to hand a whole instruction to a real model unattended.

    `REEVE_DRIVE` IS EXPORTED FOR THE DRIVE TURNS BECAUSE THEY ARE, LITERALLY, AN UNATTENDED
    DRIVE. `turn_gate.py` is scoped to one at the maintainer's word — a gate firing while a human
    sat there planning would be switched off within the hour, taking the unattended case with it
    — and it detects one from exactly this variable, which `loop.sh` exports for real runs.
    Without it the shipped Stop hook lay DORMANT in every smoke run, so the harness was grading a
    configuration no unattended user runs, and the seam that checks the gate had to invoke it
    synthetically to see anything at all.

    NOT FOR BOOTSTRAP, and that is not a convenience. The gate's first rung asks whether a turn
    may end AT ALL, and the set of reasons is closed: parked, met, stalled, paused, idle. After
    `/start` the loop is `building` with a full backlog, so none of them hold and the bootstrap
    turn may never end — it simply keeps building the project until the window expires. Measured:
    a greenfield `/start` burned the whole 3600s having already committed the stack decision and
    a feature, sitting in `planner:plan-one`. That is the gate working exactly as specified on a
    turn that is not a drive turn. `/start` is a human-initiated setup step that hands back; the
    drive is what happens afterwards, and `loop.sh` exports the variable for that, not for this.

    It is bounded on the turns that do carry it: `MAX_DEMANDS` lets the gate block twice and then
    give up, so a session it disagrees with costs two extra turns rather than the whole window."""
    print("  → %s" % prompt.splitlines()[0][:100])
    env = dict(os.environ)
    if drive_turn:
        env["REEVE_DRIVE"] = "1"
    else:
        env.pop("REEVE_DRIVE", None)
    try:
        p = subprocess.run(["claude", "-p", prompt], cwd=repo, capture_output=True,
                           text=True, timeout=timeout, env=env)
    except subprocess.TimeoutExpired:
        return False, "timed out after %ds — %s" % (timeout, _was_it_moving(repo))
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


# The window is PER MODE, because the two modes do measurably different amounts of work and one
# number could only be wrong for one of them. MEASURED, not guessed: on the run of 2026-09-15 a
# brownfield item went round comfortably inside 1800s, while greenfield was killed at exactly
# 1800s **inside `document`**, with `verify` already passed on 18 tests. Its three red seams were
# one event — `document` owns the code-map rebuild, and the resume anchor is written at turn end,
# so both died with the node that was running. `_was_it_moving()` had already said "still
# writing", and the tree agreed.
#
# Greenfield builds a feature from nothing: spec, plan, execute, verify, document, commit.
# Brownfield starts with code and a backlog already reconstructed by `ingest`, so its first item
# is a much shorter road. Raising both to the greenfield number would buy nothing and make a
# genuinely stopped brownfield session take twice as long to report it — the window is also how
# fast a stall is detected, which is why this is two numbers rather than one large one.
#
# BROWNFIELD MOVED ONCE, and the reason is worth keeping rather than smoothing into a bigger
# number: 1800s was measured BEFORE this harness exported `REEVE_DRIVE`, when the shipped turn
# gate lay dormant in every run. With the gate live the loop is asked to justify each turn-end,
# which is the point of it, and that costs turns. The run of 2026-09-15 finished its item — goal
# MET, committed, every seam green — and was killed while still winding the session down. The
# window is still the tighter of the two, because it is also how fast a genuinely STOPPED session
# is reported, and brownfield still starts from a backlog `ingest` already reconstructed.
MODE_TIMEOUT = {"greenfield": 3600, "brownfield": 2700}
DEFAULT_TIMEOUT = 1800


def mode_timeout(mode, override=None):
    return override if override else MODE_TIMEOUT.get(mode, DEFAULT_TIMEOUT)


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
            ok, detail = drive(repo, START_PROMPT, timeout, drive_turn=False)
            if not check("%s: /start completed" % mode, ok, detail):
                print("  tree kept at %s" % repo)
                return False

        ok2, detail2 = drive(repo, ITEM_PROMPT, timeout)
        # A clean exit is necessary and nowhere near sufficient — see the helper.
        if ok2:
            ok2, detail2 = an_item_actually_completed(repo, detail2)
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
    ap.add_argument("--timeout", type=int, default=None,
                    help="seconds per session, overriding the per-mode default "
                         "(greenfield %d, brownfield %d)"
                         % (MODE_TIMEOUT["greenfield"], MODE_TIMEOUT["brownfield"]))
    ap.add_argument("--keep", action="store_true", help="keep the throwaway trees")
    ap.add_argument("--allow-stale", action="store_true",
                    help="drive even though the INSTALLED PLUGIN is not this repo's HEAD. The "
                         "skills, commands and agents come from the plugin cache, not from the "
                         "tree this harness builds, so a stale one means the receipt attests a "
                         "mixture. Named rather than silent, and never a default.")
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
        # LAST, after the arguments are validated: a bad --mode is a usage error and must
        # still read as one. This refuses on the ENVIRONMENT, which is a different answer.
        stale = stale_plugin(args.resume)
        if stale and not args.allow_stale:
            print("smoke_drive: REFUSING to drive — %s" % stale)
            print("             The drive invokes `/reeve:start` and the `reeve:*` skills, and "
                  "those resolve to the INSTALLED PLUGIN, not to the tree this harness builds. "
                  "A run against a stale plugin attests a mixture: current scripts and hooks in "
                  "the tree, older commands and skills driving them — and the receipt would say "
                  "the package works.")
            print("             Fix it (`scripts/dev-reinstall.sh`, or `claude plugin "
                  "marketplace update reeve && claude plugin update reeve`, then restart), or "
                  "pass --allow-stale if you genuinely mean to grade a mixture.")
            return 70
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
            if run_mode(mode, mode_timeout(mode, args.timeout), args.keep,
                        resume=args.resume) \
                    and len(FAILURES) == before:
                record_mode(mode)

    print("\n%d step(s), %d failure(s)" % (len(STEPS), len(FAILURES)))
    for f in FAILURES:
        print("  FAIL %s" % f)
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())

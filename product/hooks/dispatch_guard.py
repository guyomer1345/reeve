#!/usr/bin/env python3
"""PreToolUse(Agent/Task) gate: a loop node is never dispatched to a general worker.

WHY THIS IS A HOOK AND NOT A SENTENCE IN THE BRIEF
The package ships a role for every node — what `execute` must refuse, the exact first line
`verify` has to print because a commit hook parses it, the backup a destructive plan needs.
None of that reaches a `general-purpose` worker: it arrives with an empty role and whatever
the dispatch prompt happened to say. Measured on a real drive, every loop node except the one
declared agent was dispatched that way, each carrying a hand-typed paraphrase of the file it
was supposed to be running — and what the paraphrase dropped was, every time, the load-bearing
half. The brief now states the rule; this is the part that makes it true, because the failure
mode being guarded is precisely "the advisory rule was not followed".

WHAT IT BLOCKS
A dispatch whose `subagent_type` is NOT one of this package's own capabilities, when the
dispatch is aimed at a loop node. Two independent signals, either is enough:
  A. the dispatch TITLE names a node — `description`, or the prompt's first line, starting
     with a node name ("Execute S2a-evidence-store", "Document the item").
  B. the prompt reaches into the loop's own runtime — `.workflow/items/...`, a plan, a
     changelog, a verdict. Ordinary general-purpose work does not name those paths.

WHERE THE NODE NAMES COME FROM
`.workflow/loop.md` — the routing graph, which is already the single owner of "what the nodes
are". This file reads that owner; it never keeps a list of its own, so a node added to the
graph is covered here on the next call with no edit.

FAILURE MODES, ON PURPOSE
  - no `.workflow/loop.md`  → ALLOW. There is no loop in this project to protect.
  - loop.md present but unparseable → BLOCK non-package dispatches, and say why. An empty node
    set would pass every dispatch vacuously, which is the one way a gate dies silently.
  - a namespaced dispatch (`reeve:<name>`) → always allowed, including when
    the graph is unreadable, so a corrupted file can never stall the loop's own work.

KNOWN COST, STATED RATHER THAN DISCOVERED: signal B blocks a general-purpose dispatch that
legitimately mentions `.workflow/` in passing. That is the deliberate trade — the block prints
what to do instead, and a re-dispatch by capability name is one turn.

--------------------------------------------------------------------------------------------
THE SECOND GATE: NEVER WAIT ALONE, AND NOW IT IS ENFORCED.

"The orchestrator may never wait alone" was made a first-class rule and the wave machinery was
built under it — and the rule itself lived only as a sentence in `loop.md`. A router that blocks
on one `execute` while two others were eligible violates nothing, and **nothing notices**. The
hard half (`check_wave_independence.py`, which computes what may safely run beside what) shipped,
and the half that makes the omission impossible did not.

This is the asked-for half. A `reeve:execute` dispatch is REFUSED unless the gate's own verdict
covers it — `.workflow/wave-decision.json`, written by `check_wave_independence.py --record` and
by nothing else. Four ways to fail it, each naming its fix:
  1. no record at all      → the question was never asked.
  2. recorded at another HEAD → asked, but before the commit that changed the answer. A commit
     per item is the boundary's cadence, so HEAD is the honest staleness test, not a TTL.
  3. this item not among `considered` → the gate looked, but not at this.
  4. the record puts this item in a batch of N>1 and `state.json.wave` is null → the gate said
     these may run together and this is being sent alone. Mint the wave, send them in one turn.

WHAT THIS CANNOT ENFORCE, SAID PLAINLY RATHER THAN LEFT TO BE DISCOVERED. A `PreToolUse` hook
fires once per tool call and cannot see the call's siblings, so it can never prove that the
other members of a minted batch went out in the SAME turn — only that the batch was minted
before the first one left. Minting a batch of three and then dispatching one is the residual.
It is a far smaller hole than "nothing notices", and it is a hole, not a corner that was
rounded off quietly. Scope is likewise narrow on purpose: `execute` is the blocking dispatch the
rule is about and the only one the independence gate grades. `document`, `create-demo`,
`research` and `setup-guide` block too and are NOT covered here — there is no gate that computes
what may run beside them, and inventing one would be new judgement rather than a check.
"""
import json
import os
import re
import sys

PLUGIN = "reeve"
WORKFLOW = ".workflow"
DISPATCH_TOOLS = {"Agent", "Task"}
# The one leaf the wave gate grades, and the one whose solo dispatch is the ask's subject.
WAVE_GATED = "execute"
# An item id as it appears in a dispatch — the item directory is the only spelling a prompt
# reliably carries, and it is the one `check_wave_independence.py` keys its verdict on.
ITEM_RE = re.compile(r"\.workflow/items/([A-Za-z0-9][\w.-]*)")
TITLE_CHARS = 200          # a dispatch title is short; the node name leads it or it isn't a title
# The loop's own runtime artifacts. Deliberately narrow: `.workflow/` alone would catch a
# passing mention, these are the paths only a node's work touches.
RUNTIME_RE = re.compile(
    r"\.workflow/(items|plans?|demos|forecasts)/"
    r"|\.workflow/[\w.-]*(plan|changelog|verdict|spec)[\w.-]*\.(md|json)",
    re.I,
)
# a routing-table row: `| `node` | on output | next |` — the first backticked token is the node
ROW_NODE_RE = re.compile(r"^\|\s*`([^`]+)`")


def read_payload():
    try:
        return json.load(sys.stdin)
    except Exception:
        return {}


def loop_nodes(workflow_dir):
    """Node base names from the routing graph. Returns None when there is no graph at all
    (a project that never initialised), an empty set when the graph read but yielded nothing."""
    path = os.path.join(workflow_dir, "loop.md")
    try:
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
    except OSError:
        return None
    names = set()
    for line in text.splitlines():
        s = line.strip()
        if s.lower().startswith("side door"):
            names.update(t.strip().rstrip("?!").strip() for t in re.findall(r"`([^`]+)`", s))
            continue
        m = ROW_NODE_RE.match(s)
        if m:
            names.add(m.group(1).strip().rstrip("?!").strip())
    # `planner:plan-one` and `planner` are the same capability to a dispatcher
    bases = {n.split(":")[0] for n in names if n}
    return {b for b in bases if re.fullmatch(r"[a-z][a-z-]*", b)}


def targeted_node(nodes, description, prompt):
    """The node this dispatch is aimed at, or None. See signals A and B in the docstring."""
    first_line = (prompt or "").strip().splitlines()[:1]
    titles = [(description or "").strip(), first_line[0].strip() if first_line else ""]
    for title in titles:
        head = title[:TITLE_CHARS].lower()
        for node in sorted(nodes, key=len, reverse=True):
            # a title POSITION: the node name leads the title, or follows a bare imperative
            # opener ("Run execute for item 3"), never merely appears somewhere in prose.
            if re.match(r"^\W*(run|do|start|perform|dispatch|use|the)?\W*" + re.escape(node) + r"\b",
                        head):
                return node
    if RUNTIME_RE.search(prompt or ""):
        return "a loop node"
    return None


def _head(root):
    import subprocess
    try:
        p = subprocess.run(["git", "-C", root, "rev-parse", "HEAD"],
                           capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return None
    return (p.stdout.strip() or None) if p.returncode == 0 else None


def _minted_wave(project_dir):
    """`state.json`'s wave, through `wave_build.py` — the single owner of that resolution
    (runtime pointer, worktree fallback). Its reader is CWD-relative, so the cwd is moved to
    the project for the call rather than the resolution being re-derived here; this process
    exists for one tool call and has nothing else to be relative to."""
    try:
        sys.path.insert(0, os.path.join(project_dir, ".claude", "scripts"))
        import wave_build
        here = os.getcwd()
        try:
            os.chdir(project_dir)
            return wave_build.wave_id()
        finally:
            os.chdir(here)
    except Exception:
        return None


def viability_gate(project_dir, workflow, prompt, description):
    """Refuse an `execute` that no recorded wave verdict covers. See the second half of the
    module docstring for the four failures and for what this deliberately cannot prove."""
    path = os.path.join(workflow, "wave-decision.json")
    try:
        with open(path, encoding="utf-8") as fh:
            rec = json.load(fh)
    except (OSError, ValueError):
        rec = None
    if not isinstance(rec, dict):
        block(
            "there is no recorded answer to \"what else could run right now?\" — "
            f"{path} is missing or unreadable, so this `execute` is about to block the loop "
            "with nothing establishing that it had to go alone.\n"
            "  Run `python3 .claude/scripts/check_wave_independence.py --record` at the "
            "boundary, then dispatch the batch it returns in ONE turn.\n"
            "  The rule it enforces: never dispatch a blocking call by itself while other "
            "viable work exists (`loop.md § Dispatch boundary`)."
        )

    head = _head(project_dir)
    if not head or rec.get("head") != head:
        block(
            f"the recorded wave verdict was made at {rec.get('head') or '(no commit)'} and HEAD "
            f"is now {head or '(git cannot say)'}. A commit is what changes the answer — one "
            "lands per item — so this verdict is stale.\n"
            "  Re-run `python3 .claude/scripts/check_wave_independence.py --record`."
        )

    ids = set(ITEM_RE.findall(prompt or "")) | set(ITEM_RE.findall(description or ""))
    considered = set(rec.get("considered") or [])
    unknown = sorted(ids - considered)
    if unknown:
        block(
            f"the wave verdict at this commit never looked at {', '.join(unknown)} — it "
            f"considered {', '.join(sorted(considered)) or '(nothing)'}. A dispatch the gate "
            "has not graded is one whose independence nobody has established.\n"
            "  Re-run `python3 .claude/scripts/check_wave_independence.py --record` "
            f"{' '.join(unknown)}."
        )

    batch = [b for b in (rec.get("batch") or []) if isinstance(b, str)]
    if len(batch) > 1 and ids & set(batch) and not _minted_wave(project_dir):
        block(
            f"the gate says {len(batch)} items may run concurrently right now "
            f"({', '.join(batch)}) and this is being sent on its own, with no wave minted. "
            "Concurrency in this harness exists ONLY for work dispatched in the same turn — "
            "while this Task is in flight nothing else can start.\n"
            f"  Mint the wave (`python3 .claude/scripts/wave_build.py mint {' '.join(batch)}` "
            "→ `state.json`'s `wave`), then send all of them in ONE turn.\n"
            "  If one of them genuinely must not run now, re-run the gate with the ids that "
            "may (`check_wave_independence.py --record <ids…>`) so the record says so."
        )


def main():
    payload = read_payload()
    if payload.get("tool_name") not in DISPATCH_TOOLS:
        return 0
    tool_input = payload.get("tool_input") or {}
    subagent = (tool_input.get("subagent_type") or "").strip()

    project_dir = os.environ.get("CLAUDE_PROJECT_DIR") or payload.get("cwd") or "."
    workflow = os.path.join(project_dir, WORKFLOW)

    # This package's own capabilities are the point of the FIRST rule — always allowed there.
    # `execute` still answers to the second gate: it is the blocking dispatch that "never wait
    # alone" is about, and being the right agent says nothing about whether it should be alone.
    if subagent.startswith(PLUGIN + ":"):
        if (subagent.split(":", 1)[1].strip() == WAVE_GATED
                and os.path.isdir(workflow)):
            viability_gate(project_dir, workflow,
                           tool_input.get("prompt") or "", tool_input.get("description") or "")
        return 0

    nodes = loop_nodes(workflow)
    if nodes is None:
        return 0                       # no loop here; nothing to protect

    description = tool_input.get("description") or ""
    prompt = tool_input.get("prompt") or ""

    if not nodes:
        block(
            f"the routing graph at {os.path.join(workflow, 'loop.md')} names no nodes, so this "
            f"gate cannot tell whether {subagent or 'this dispatch'} is a loop node. Fix the "
            f"graph, or dispatch the capability by name ({PLUGIN}:<name>), which is never blocked."
        )

    node = targeted_node(nodes, description, prompt)
    if not node:
        return 0

    block(
        f"this dispatch targets `{node}`, a loop node, but sends it to "
        f"`{subagent or '(unnamed)'}` — a worker that arrives with none of this package's "
        f"rules and improvises whatever the prompt left out.\n"
        f"  Run it by name instead: dispatch the AGENT `{PLUGIN}:{node}` if it is one of the "
        f"heavy leaves (planner · execute · document · create-demo · research · setup-guide), otherwise "
        f"run the SKILL `{PLUGIN}:{node}` inline in this session.\n"
        f"  Pass inputs — paths, ids, the item — not a description of how to do the job."
    )


def block(reason):
    print(f"BLOCKED by disciplined-builder dispatch guard: {reason}", file=sys.stderr)
    sys.exit(2)


if __name__ == "__main__":
    sys.exit(main())

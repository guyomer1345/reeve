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
  - a namespaced dispatch (`dev-autonomous-workflow:<name>`) → always allowed, including when
    the graph is unreadable, so a corrupted file can never stall the loop's own work.

KNOWN COST, STATED RATHER THAN DISCOVERED: signal B blocks a general-purpose dispatch that
legitimately mentions `.workflow/` in passing. That is the deliberate trade — the block prints
what to do instead, and a re-dispatch by capability name is one turn.
"""
import json
import os
import re
import sys

PLUGIN = "dev-autonomous-workflow"
WORKFLOW = ".workflow"
DISPATCH_TOOLS = {"Agent", "Task"}
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


def main():
    payload = read_payload()
    if payload.get("tool_name") not in DISPATCH_TOOLS:
        return 0
    tool_input = payload.get("tool_input") or {}
    subagent = (tool_input.get("subagent_type") or "").strip()

    # This package's own capabilities are the point of the rule — always allowed.
    if subagent.startswith(PLUGIN + ":"):
        return 0

    workflow = os.environ.get("CLAUDE_PROJECT_DIR", "")
    workflow = os.path.join(workflow, WORKFLOW) if workflow else WORKFLOW
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
        f"heavy leaves (execute · document · create-demo · research · setup-guide), otherwise "
        f"run the SKILL `{PLUGIN}:{node}` inline in this session.\n"
        f"  Pass inputs — paths, ids, the item — not a description of how to do the job."
    )


def block(reason):
    print(f"BLOCKED by disciplined-builder dispatch guard: {reason}", file=sys.stderr)
    sys.exit(2)


if __name__ == "__main__":
    sys.exit(main())

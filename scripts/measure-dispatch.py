#!/usr/bin/env python3
"""Measure dispatch fidelity on a real drive, from the session transcripts.

META-ONLY — this never ships. It reads the maintainer's own `~/.claude/projects/<slug>/`
transcripts to answer questions that were invisible to reading the package and obvious the
moment anyone counted:

  - **who did the work** — dispatches by `subagent_type`. A loop node on `general-purpose`
    is a node running with none of its own rules.
  - **did the role arrive** — for a namespaced dispatch the agent file IS the worker's
    prompt, so the role arrives by construction; for anything else the only way it could
    arrive is a `Skill` call inside the subagent. Measured across a whole drive, that rate
    was ZERO, which is the finding this script exists to keep measurable.
  - **what each node costs** — tokens and wall-clock per dispatch, per node. Sizing the
    writer is guesswork without it.
  - **the invariant violations** — a leaf that spawned its own agent, and web tools inside
    a worker that has no business browsing.

The defect this was written for was not visible to reading the package. Re-run it after a
drive rather than reasoning about whether the fix held.

USAGE
    scripts/measure-dispatch.py [PROJECT_PATH] [--json] [--since 2026-08-07]
    scripts/measure-dispatch.py --dir ~/.claude/projects/-mnt-c-...-agentic-cyber

TRANSCRIPT SHAPE (as of CLI 2.1.x)
    <slug>/<session-id>.jsonl                     the main window
    <slug>/<session-id>/subagents/agent-<id>.jsonl        one per dispatched worker
    <slug>/<session-id>/subagents/agent-<id>.meta.json    {agentType, description, spawnDepth}
A shape that stops matching should fail loudly here rather than report a confident zero, so
an empty scan is reported as "no data", never as a clean bill.
"""
import argparse
import json
import os
import re
import sys
from collections import Counter, defaultdict

PLUGIN = "dev-autonomous-workflow"
DISPATCH_TOOLS = {"Agent", "Task"}
WEB_TOOLS = {"WebSearch", "WebFetch"}
# The loop's node names. Unlike the shipped gate — which reads the project's own loop.md and
# must never carry a list — this is a meta-side reporting label: it only decides which bucket
# a number is printed under, and an unmatched dispatch is reported as unattributed, not lost.
NODES = [
    "create-forecast", "create-demo", "create-issue", "close-issue", "decision-engineer",
    "setup-guide", "prioritize", "checkpoint", "adjudicate", "planner", "execute", "verify",
    "document", "research", "discuss", "refine", "ingest", "commit", "align", "answer",
    "status", "debug",
]


def slugify(path):
    """`/mnt/c/.../agentic cyber` -> `-mnt-c----agentic-cyber` (every non-alphanumeric
    becomes a dash, one for one — the CLI's own rule, verified against a real tree)."""
    return re.sub(r"[^A-Za-z0-9]", "-", os.path.abspath(os.path.expanduser(path)))


def transcript_dir(project, explicit=None):
    if explicit:
        return os.path.abspath(os.path.expanduser(explicit))
    return os.path.join(os.path.expanduser("~"), ".claude", "projects", slugify(project))


def read_jsonl(path):
    try:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    yield json.loads(line)
                except ValueError:
                    continue
    except OSError:
        return


def tool_uses(record):
    if record.get("type") != "assistant":
        return
    for block in (record.get("message") or {}).get("content") or []:
        if isinstance(block, dict) and block.get("type") == "tool_use":
            yield block


def usage_of(record):
    """The four token counters on one assistant turn, or None.

    DELIBERATELY NOT ONE NUMBER. The per-dispatch figure the CLI prints in its UI is not
    written to the transcript, so any single total here would be a reconstruction dressed up
    as a measurement. The three that ARE derivable answer different questions and the
    writer-sizing work needs all three kept apart:
      new  = input + cache_creation + output — tokens this dispatch caused to be processed
             fresh; the closest honest cost proxy.
      peak = the largest cache_read on any turn — how big the worker's context actually got.
      read = the sum of cache_read — the re-read tax of a long tool loop, which grows with
             turn count even when the context never does.
    A node whose `new` is dominated by cache_creation is READ-dominated (it is being fed, or
    feeding itself, a lot of material); one dominated by output is WRITE-dominated. Those two
    diagnoses take opposite fixes, which is why they are never summed into one number here.
    """
    if record.get("type") != "assistant":
        return None
    u = (record.get("message") or {}).get("usage")
    return u if isinstance(u, dict) else None


def _int(u, k):
    return int(u.get(k) or 0)


def node_of(agent_type, description, prompt):
    """(node, how) — the loop node a dispatch was aimed at, and how confidently we know.

    A namespaced dispatch NAMES its node; anything else has to be inferred from the title
    the orchestrator typed, and inference that fails says so rather than guessing.
    """
    if agent_type.startswith(PLUGIN + ":"):
        return agent_type.split(":", 1)[1], "declared"
    head = ((description or "") + " || " + (prompt or "")[:300]).lower()
    for node in sorted(NODES, key=len, reverse=True):
        if re.search(r"\b" + re.escape(node) + r"\b", head):
            return node, "inferred"
    return "(unattributed)", "unknown"


def first_prompt(records):
    for r in records:
        if r.get("type") == "user":
            msg = r.get("message") or {}
            content = msg.get("content")
            if isinstance(content, str):
                return content
            if isinstance(content, list):
                return "".join(b.get("text", "") for b in content if isinstance(b, dict))
    return ""


def scan_subagent(jsonl_path, meta_path, since):
    records = list(read_jsonl(jsonl_path))
    if not records:
        return None
    try:
        with open(meta_path, encoding="utf-8") as fh:
            meta = json.load(fh)
    except (OSError, ValueError):
        meta = {}
    stamps = [r.get("timestamp") for r in records if r.get("timestamp")]
    started = min(stamps) if stamps else ""
    if since and started and started[:10] < since:
        return None

    prompt = first_prompt(records)
    agent_type = (meta.get("agentType") or "").strip()
    node, how = node_of(agent_type, meta.get("description"), prompt)
    tools = Counter()
    new = created = out_toks = read = peak = 0
    for r in records:
        u = usage_of(r)
        if u:
            created += _int(u, "cache_creation_input_tokens")
            out_toks += _int(u, "output_tokens")
            new += _int(u, "input_tokens")
            read += _int(u, "cache_read_input_tokens")
            peak = max(peak, _int(u, "cache_read_input_tokens"))
        for use in tool_uses(r):
            tools[use.get("name")] += 1
    return {
        "agent_id": meta.get("agentId") or os.path.basename(jsonl_path),
        "agent_type": agent_type or "(none)",
        "description": meta.get("description") or "",
        "spawn_depth": meta.get("spawnDepth"),
        "node": node,
        "attribution": how,
        "prompt_chars": len(prompt),
        "new_tokens": new + created + out_toks,
        "created_tokens": created,
        "output_tokens": out_toks,
        "read_tokens": read,
        "peak_context": peak,
        "turns": sum(1 for r in records if r.get("type") == "assistant"),
        "seconds": _elapsed(stamps),
        "tools": dict(tools),
        "skill_loads": tools.get("Skill", 0),
        "web_calls": sum(tools.get(t, 0) for t in WEB_TOOLS),
        "nested_dispatches": sum(tools.get(t, 0) for t in DISPATCH_TOOLS),
        "started": started,
    }


def _elapsed(stamps):
    if len(stamps) < 2:
        return 0
    import datetime
    try:
        lo = datetime.datetime.fromisoformat(min(stamps).replace("Z", "+00:00"))
        hi = datetime.datetime.fromisoformat(max(stamps).replace("Z", "+00:00"))
        return int((hi - lo).total_seconds())
    except ValueError:
        return 0


def scan(root, since=None):
    sessions = sorted(
        p for p in os.listdir(root) if os.path.isdir(os.path.join(root, p))
    ) if os.path.isdir(root) else []
    subagents, main_skills, main_dispatches = [], Counter(), 0
    for session in sessions:
        sub_dir = os.path.join(root, session, "subagents")
        if not os.path.isdir(sub_dir):
            continue
        for fn in sorted(os.listdir(sub_dir)):
            if not fn.endswith(".jsonl"):
                continue
            got = scan_subagent(os.path.join(sub_dir, fn),
                                os.path.join(sub_dir, fn[:-6] + ".meta.json"), since)
            if got:
                got["session"] = session
                subagents.append(got)
    # the main window: what it dispatched, and what it loaded into its OWN context
    for fn in sorted(os.listdir(root)) if os.path.isdir(root) else []:
        if not fn.endswith(".jsonl"):
            continue
        for r in read_jsonl(os.path.join(root, fn)):
            if r.get("isSidechain"):
                continue
            ts = r.get("timestamp") or ""
            if since and ts and ts[:10] < since:
                continue
            for use in tool_uses(r):
                if use.get("name") in DISPATCH_TOOLS:
                    main_dispatches += 1
                elif use.get("name") == "Skill":
                    skill = (use.get("input") or {}).get("skill") or "(unnamed)"
                    main_skills[skill] += 1
    return subagents, main_skills, main_dispatches


def report(subagents, main_skills, main_dispatches, out=None):
    out = out or sys.stdout
    n = len(subagents)
    if not n:
        print("no subagent transcripts found — nothing measured.\n"
              "  (an empty scan is NOT a clean result: check the path, the --since bound, "
              "and whether the transcript layout still matches this script's assumptions)",
              file=out)
        return 1

    by_type = Counter(s["agent_type"] for s in subagents)
    declared = [s for s in subagents if s["attribution"] == "declared"]
    general = [s for s in subagents if not s["agent_type"].startswith(PLUGIN + ":")]
    loop_general = [s for s in general if s["node"] != "(unattributed)"]
    role_arrived = [s for s in subagents if s["attribution"] == "declared" or s["skill_loads"]]

    print(f"DISPATCH FIDELITY — {n} subagent transcripts, "
          f"{main_dispatches} dispatches seen in the main window\n", file=out)

    print("dispatches by subagent_type", file=out)
    for t, c in by_type.most_common():
        mark = "  " if t.startswith(PLUGIN + ":") else " <"
        print(f"  {c:4d}  {t}{mark}", file=out)

    print(f"\nrole delivery", file=out)
    print(f"  {len(declared):4d}/{n}  dispatched by capability name (the role IS the "
          f"worker's prompt)", file=out)
    print(f"  {sum(1 for s in subagents if s['skill_loads']):4d}/{n}  loaded a skill inside "
          f"the subagent", file=out)
    print(f"  {len(role_arrived):4d}/{n}  role reached the worker by either path", file=out)
    print(f"  {len(loop_general):4d}      LOOP NODES ON A GENERAL WORKER  <-- must be 0",
          file=out)
    for s in loop_general:
        print(f"          {s['node']:<18} {s['agent_type']:<22} "
              f"{s['prompt_chars']:>6}-char hand-written prompt   {s['description'][:44]}",
              file=out)

    print(f"\nmain window (the telephone game: a skill read HERE and re-typed into a prompt)",
          file=out)
    if main_skills:
        for s, c in main_skills.most_common():
            print(f"  {c:4d}  Skill {s}", file=out)
    else:
        print("     0  skills loaded in the orchestrator's own context", file=out)

    print(f"\nper-node cost — medians (the UI's single per-dispatch figure is not in the "
          f"transcript; these are its parts)", file=out)
    per = defaultdict(list)
    for s in subagents:
        per[s["node"]].append(s)
    print(f"  {'node':<18} {'n':>3} {'new':>8} {'fed in':>8} {'written':>8} {'peak ctx':>9} "
          f"{'turns':>6} {'secs':>6} {'prompt':>7}", file=out)
    for node, rows in sorted(per.items(),
                             key=lambda kv: -_median([r["new_tokens"] for r in kv[1]])):
        med = lambda k: _median([r[k] for r in rows])  # noqa: E731
        print(f"  {node:<18} {len(rows):>3} {_k(med('new_tokens')):>8} "
              f"{_k(med('created_tokens')):>8} {_k(med('output_tokens')):>8} "
              f"{_k(med('peak_context')):>9} {med('turns'):>6} {med('seconds'):>6} "
              f"{med('prompt_chars'):>7}", file=out)
    print("  new = fed in + written + uncached input · fed in ≫ written means the node is "
          "READ-dominated", file=out)

    nested = [s for s in subagents if s["nested_dispatches"]]
    web = [s for s in subagents if s["web_calls"] and s["node"] not in ("research", "setup-guide")]
    print(f"\ninvariant violations", file=out)
    print(f"  {len(nested):4d}  leaves that spawned their own agent (leaves must not spawn)",
          file=out)
    for s in nested:
        print(f"          {s['node']} / {s['agent_type']} — {s['nested_dispatches']}", file=out)
    print(f"  {sum(s['web_calls'] for s in web):4d}  web calls inside a worker that is not an "
          f"information gatherer (across {len(web)} workers) — "
          f"{sum(s['web_calls'] for s in subagents)} across all workers, which is only "
          f"legitimate where the node's job IS to gather", file=out)

    return 0 if not loop_general and not nested else 2


def _median(xs):
    xs = sorted(xs)
    if not xs:
        return 0
    mid = len(xs) // 2
    return xs[mid] if len(xs) % 2 else (xs[mid - 1] + xs[mid]) // 2


def _k(n):
    return f"{n/1000:.1f}k" if n >= 1000 else str(n)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("project", nargs="?", default=os.getcwd(),
                    help="the project path whose transcripts to read (default: cwd)")
    ap.add_argument("--dir", help="the transcript dir directly, instead of deriving it")
    ap.add_argument("--since", metavar="YYYY-MM-DD",
                    help="ignore anything that started before this date")
    ap.add_argument("--json", action="store_true", help="emit the raw per-dispatch rows")
    args = ap.parse_args(argv)

    root = transcript_dir(args.project, args.dir)
    if not os.path.isdir(root):
        print(f"no transcripts at {root}\n"
              f"  (derived from {args.project!r} — pass --dir to point at it directly)",
              file=sys.stderr)
        return 1
    subagents, main_skills, main_dispatches = scan(root, args.since)
    if args.json:
        json.dump({"root": root, "subagents": subagents,
                   "main_window_skill_loads": dict(main_skills),
                   "main_window_dispatches": main_dispatches}, sys.stdout, indent=2)
        print()
        return 0 if subagents else 1
    return report(subagents, main_skills, main_dispatches)


if __name__ == "__main__":
    sys.exit(main())

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
  - **`--writer-scope`: where a node's fed-in tokens CAME FROM** — discovery reads vs test
    output vs the bytes it authored, the re-read tax, and the share of reads on files the
    item's plan never declared. "READ-dominated" is not yet a diagnosis: if the reads are the
    plan's own files the writer is doing its job, and if they are off-plan hunting the plan
    under-supplied scope. Those take opposite fixes, so the split is the point.

The defect this was written for was not visible to reading the package. Re-run it after a
drive rather than reasoning about whether the fix held.

...INCLUDING ITS OWN. The first version of this script summed the token counters over
transcript RECORDS, and the CLI writes one record per content block, each repeating the whole
response's `usage` — so every reported "fed in" figure was 2.8-3.5x too high. It is fixed
(see `api_calls`), and the moral is the script's own: re-measure, do not re-reason.

USAGE
    scripts/measure-dispatch.py [PROJECT_PATH] [--json] [--since 2026-08-07] [--writer-scope]
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
import fnmatch
import re
import sys
from collections import Counter, defaultdict

PLUGIN = "reeve"
DISPATCH_TOOLS = {"Agent", "Task"}
WEB_TOOLS = {"WebSearch", "WebFetch"}
# ---- the writer-scope attribution (11f) ----------------------------------------------
# A node's cost splits three ways and only one of the three is the work itself. Which bucket
# dominates picks the fix, and the two candidate fixes are opposite, so the buckets are kept
# apart the same way the token components are.
READ_TOOLS = {"Read", "NotebookRead"}          # named-file discovery
SEARCH_TOOLS = {"Grep", "Glob"}                # unnamed-file discovery — hunting
WRITE_TOOLS = {"Write", "Edit", "MultiEdit", "NotebookEdit"}
# A worker can read just as much through Bash as through Read, and a measurement that only
# counts `Read` would report a clean write-dominated node that is actually catting files.
BASH_READ = re.compile(
    r"^\s*(?:cat|head|tail|sed|awk|less|more|nl|wc|ls|find|tree|grep|rg|ag|"
    r"git\s+(?:show|log|diff|status|blame|ls-files))\b")
CHARS_PER_TOKEN = 4  # the usual rough constant; used for SHARES, never for a headline total
# The prompt cache's TTL. A dispatch that idles longer than this between calls pays to write
# its ENTIRE prefix again on the next one — which shows up in `fed in` as if the worker had
# been handed that much new material. MEASURED: the 11e `execute` had one 659s gap and the
# next call wrote 55.5k of cache, alone accounting for 47% of its "fed in".
CACHE_TTL_SECONDS = 300
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


def stalls(records, ttl=CACHE_TTL_SECONDS):
    """(count, tokens) — cache re-writes caused by idling past the prompt cache's TTL.

    Without this, a node that stalled once reads as a node that consumed twice the context.
    That misreading is not hypothetical: it is half of the number that opened this phase.
    """
    import datetime
    marks, seen = [], set()
    for r in records:
        if r.get("type") != "assistant":
            continue
        msg = r.get("message") or {}
        key = msg.get("id") or r.get("requestId") or r.get("uuid")
        if key in seen:
            continue
        seen.add(key)
        try:
            when = datetime.datetime.fromisoformat(
                str(r.get("timestamp") or "").replace("Z", "+00:00"))
        except ValueError:
            continue
        marks.append((when, _int(msg.get("usage") or {}, "cache_creation_input_tokens")))
    count = tokens = 0
    for i in range(len(marks) - 1):
        if (marks[i + 1][0] - marks[i][0]).total_seconds() > ttl:
            count += 1
            tokens += marks[i + 1][1]
    return count, tokens


def api_calls(records):
    """One row per API RESPONSE, not per transcript record — the counters are per response.

    MEASURED, and it invalidated this script's own first numbers: the CLI writes **one record
    per content block**, so a single response that thought, spoke and called three tools lands
    as five assistant records **each repeating the same `usage` object**. Summing over records
    therefore multiplies `cache_creation` by the block count — on the 11e drive that inflated
    `execute` from a true 119.1k to a reported 335.6k (2.8x), and `document`/`research` by
    3.4-3.5x. `output_tokens` was barely affected because the partial records carry partial
    counts and only the last carries the total, which is also why the aggregation is MAX
    within a response rather than first-wins.

    Grouped on `message.id`, falling back to `requestId` then the record `uuid` — the last of
    which is unique per record, so an unknown shape degrades to the old over-count rather than
    silently dropping turns.
    """
    groups = {}
    order = []
    for r in records:
        if r.get("type") != "assistant":
            continue
        msg = r.get("message") or {}
        key = msg.get("id") or r.get("requestId") or r.get("uuid") or len(order)
        u = msg.get("usage") if isinstance(msg.get("usage"), dict) else {}
        if key not in groups:
            groups[key] = {"input_tokens": 0, "cache_creation_input_tokens": 0,
                           "cache_read_input_tokens": 0, "output_tokens": 0}
            order.append(key)
        cur = groups[key]
        for field in cur:
            cur[field] = max(cur[field], _int(u, field))
    return [groups[k] for k in order]


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


def tool_results(records):
    """{tool_use_id: result_chars} — how much text each call actually fed back.

    The token counters say a worker was fed 335k; they do not say WHAT. This is the only
    place the transcript records the size of an individual tool's return, so it is the only
    way to split "the material it went and found" from "the material it produced".
    """
    sizes = {}
    for r in records:
        if r.get("type") != "user":
            continue
        content = (r.get("message") or {}).get("content")
        if not isinstance(content, list):
            continue
        for block in content:
            if isinstance(block, dict) and block.get("type") == "tool_result":
                body = block.get("content")
                if isinstance(body, list):
                    n = sum(len(b.get("text", "")) for b in body if isinstance(b, dict))
                elif body is None:
                    n = 0
                else:
                    n = len(str(body))
                sizes[block.get("tool_use_id")] = sizes.get(block.get("tool_use_id"), 0) + n
    return sizes


def _rel(path, project_root):
    """A worker's absolute path as the plan would have written it — repo-relative."""
    if not path:
        return ""
    p = str(path)
    if project_root:
        root = os.path.abspath(os.path.expanduser(project_root))
        ap = os.path.abspath(os.path.expanduser(p))
        if ap.startswith(root + os.sep):
            return os.path.relpath(ap, root)
    return p.lstrip("./")


def attribute(records, project_root=None):
    """Where a worker's fed-in tokens came from, and what it wrote — the 11f attribution.

    Three buckets, deliberately not summed:
      discovery — Read/Grep/Glob and read-shaped Bash: material the worker went and FOUND.
      exec      — everything else that came back from Bash: test runs, gates, git. Feedback
                  on work already done, not context for work not yet done. It is neither
                  planner's to supply nor the writer's to shrink, so it is never folded into
                  discovery — doing so would blame the planner for a test suite's output.
      produced  — the bytes the worker actually authored (Write content + Edit new_string).
    Plus the two ratios a bucket total cannot show: how much of the discovery was the SAME
    file read again, and how much of it was OFF the plan's declared `files_touched`.
    """
    sizes = tool_results(records)
    reads, read_chars = [], 0
    search_calls, search_chars = 0, 0
    exec_calls, exec_chars = 0, 0
    produced_chars, write_calls = 0, 0
    written_paths = []
    for r in records:
        for use in tool_uses(r):
            name = use.get("name")
            inp = use.get("input") if isinstance(use.get("input"), dict) else {}
            got = sizes.get(use.get("id"), 0)
            if name in READ_TOOLS:
                reads.append(_rel(inp.get("file_path") or inp.get("notebook_path"),
                                  project_root))
                read_chars += got
            elif name in SEARCH_TOOLS:
                search_calls += 1
                search_chars += got
            elif name == "Bash":
                if BASH_READ.match(str(inp.get("command") or "")):
                    read_chars += got
                    search_calls += 1  # an unnamed-file read is still hunting
                else:
                    exec_calls += 1
                    exec_chars += got
            elif name in WRITE_TOOLS:
                write_calls += 1
                written_paths.append(_rel(inp.get("file_path") or inp.get("notebook_path"),
                                          project_root))
                produced_chars += len(str(inp.get("content") or ""))
                produced_chars += len(str(inp.get("new_string") or ""))
                for e in inp.get("edits") or []:
                    if isinstance(e, dict):
                        produced_chars += len(str(e.get("new_string") or ""))
    counts = Counter(p for p in reads if p)
    return {
        "read_calls": len(reads),
        "distinct_files_read": len(counts),
        "reread_calls": sum(c - 1 for c in counts.values()),
        "search_calls": search_calls,
        "exec_calls": exec_calls,
        "write_calls": write_calls,
        "discovery_chars": read_chars + search_chars,
        "exec_chars": exec_chars,
        "produced_chars": produced_chars,
        "files_read": dict(counts),
        "files_written": sorted(set(p for p in written_paths if p)),
    }


def plan_files(project_root, item):
    """The `files_touched` set from an item's plan, as glob patterns.

    The plan's own `## Files touched` table is the declaration of scope; a read outside it is
    a read the plan did not anticipate. Placeholders (`<entry>`) become wildcards, so a plan
    that names a directory's contents generically is not scored as if it named nothing.
    """
    if not project_root or not item:
        return None
    path = os.path.join(project_root, ".workflow", "items", item, "plan.md")
    try:
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
    except OSError:
        return None
    m = re.search(r"^#+\s*Files touched\s*$(.*?)(?=^#+\s)", text, re.M | re.S)
    if not m:
        return None
    pats = []
    for line in m.group(1).splitlines():
        if not line.strip().startswith("|"):
            continue
        cell = line.split("|")[1] if line.count("|") >= 2 else ""
        for tok in re.findall(r"`([^`]+)`", cell):
            pats.append(re.sub(r"<[^>]*>", "*", tok.strip()).lstrip("./"))
    return pats or None


def is_scaffolding(path):
    """The loop's own runtime, which every worker is TOLD to read.

    Kept out of the plan score deliberately, and this is not a detail: scoring it in made the
    first run of this report say `execute` did 43-57% of its reading off-plan, which reads as
    a writer casting about for context it was not given. Every one of those reads was the
    item's own `plan.md`, `promises.json` or `checks.env` — files a plan does not list in its
    own `Files touched` table because they are not what the item changes. The hunting signal
    is reads of PRODUCT files the plan never named; everything else is the worker following
    its instructions.
    """
    p = (path or "").replace("\\", "/")
    return p.startswith(".workflow/") or p.startswith(".claude/") or p == "CLAUDE.md"


def off_plan(files_read, patterns):
    """(on, off, scaffolding) read-call counts against the plan's declared scope."""
    on = off = scaffold = 0
    for path, n in (files_read or {}).items():
        if is_scaffolding(path):
            scaffold += n
            continue
        hit = any(fnmatch.fnmatch(path, p) or fnmatch.fnmatch(path, p.rstrip("/") + "/*")
                  or path.startswith(p.rstrip("/") + "/") for p in patterns)
        if hit:
            on += n
        else:
            off += n
    return on, off, scaffold


def item_of(prompt, project_root=None):
    """The item a dispatch was about — from the runtime path in its own prompt."""
    m = re.search(r"\.workflow[/\\]items[/\\]([A-Za-z0-9._-]+)", prompt or "")
    if m:
        return m.group(1)
    m = re.search(r"\b([A-Z][A-Z0-9]*-[A-Za-z0-9]+)\b", prompt or "")
    if m:
        return m.group(1)
    if project_root:
        d = os.path.join(project_root, ".workflow", "items")
        try:
            items = [x for x in os.listdir(d) if os.path.isdir(os.path.join(d, x))]
        except OSError:
            return None
        if len(items) == 1:
            return items[0]
    return None


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


def scan_subagent(jsonl_path, meta_path, since, project_root=None):
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
    calls = api_calls(records)
    # What the dispatch paid before it did anything: the first response's cache write is the
    # system prompt + the agent file + the tool schemas. It is a FIXED per-dispatch cost, so
    # splitting one plan across N dispatches pays it N times — the number any plan-size
    # budget has to beat.
    boot = _int(calls[0], "cache_creation_input_tokens") if calls else 0
    stall_count, stall_tokens = stalls(records)
    for u in calls:
        created += _int(u, "cache_creation_input_tokens")
        out_toks += _int(u, "output_tokens")
        new += _int(u, "input_tokens")
        read += _int(u, "cache_read_input_tokens")
        peak = max(peak, _int(u, "cache_read_input_tokens"))
    for r in records:
        for use in tool_uses(r):
            tools[use.get("name")] += 1
    item = item_of(prompt, project_root)
    scope = attribute(records, project_root)
    patterns = plan_files(project_root, item)
    if patterns is not None:
        on, off, scaffold = off_plan(scope["files_read"], patterns)
        scope["plan_patterns"] = patterns
        scope["on_plan_reads"] = on
        scope["off_plan_reads"] = off
        scope["scaffolding_reads"] = scaffold
    return {
        "agent_id": meta.get("agentId") or os.path.basename(jsonl_path),
        "item": item,
        "scope": scope,
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
        "boot_tokens": boot,
        "stalls": stall_count,
        "stall_tokens": stall_tokens,
        "turns": len(calls),  # API responses, not transcript records — see api_calls()
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


def scan(root, since=None, project_root=None):
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
                                os.path.join(sub_dir, fn[:-6] + ".meta.json"), since,
                                project_root)
            if got:
                got["session"] = session
                subagents.append(got)
    # the main window: what it dispatched, what it loaded into its OWN context — and what
    # that context cost. The inline half of the loop (`planner`, `verify`, `commit`) runs
    # HERE, so a per-worker report alone measures only the half that was pushed out, and the
    # D84 inline-`verify` tension is precisely about the half that was not.
    main_cost = {"fed_in": 0, "written": 0, "peak": 0, "turns": 0, "trace": []}
    for fn in sorted(os.listdir(root)) if os.path.isdir(root) else []:
        if not fn.endswith(".jsonl"):
            continue
        records = []
        for r in read_jsonl(os.path.join(root, fn)):
            if r.get("isSidechain"):
                continue
            ts = r.get("timestamp") or ""
            if since and ts and ts[:10] < since:
                continue
            records.append(r)
            for use in tool_uses(r):
                if use.get("name") in DISPATCH_TOOLS:
                    main_dispatches += 1
                elif use.get("name") == "Skill":
                    skill = (use.get("input") or {}).get("skill") or "(unnamed)"
                    main_skills[skill] += 1
        for u in api_calls(records):
            main_cost["fed_in"] += _int(u, "cache_creation_input_tokens")
            main_cost["written"] += _int(u, "output_tokens")
            main_cost["peak"] = max(main_cost["peak"], _int(u, "cache_read_input_tokens"))
            main_cost["turns"] += 1
        trace = router_trace(records)
        if len(trace) > len(main_cost["trace"]):
            main_cost["trace"] = trace  # the session that actually drove the loop
    return subagents, main_skills, main_dispatches, main_cost


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
          f"{'boot':>7} {'turns':>6} {'secs':>6} {'prompt':>7}", file=out)
    for node, rows in sorted(per.items(),
                             key=lambda kv: -_median([r["new_tokens"] for r in kv[1]])):
        med = lambda k: _median([r[k] for r in rows])  # noqa: E731
        print(f"  {node:<18} {len(rows):>3} {_k(med('new_tokens')):>8} "
              f"{_k(med('created_tokens')):>8} {_k(med('output_tokens')):>8} "
              f"{_k(med('peak_context')):>9} {_k(med('boot_tokens')):>7} "
              f"{med('turns'):>6} {med('seconds'):>6} {med('prompt_chars'):>7}", file=out)
    print("  new = fed in + written + uncached input · fed in ≫ written means the node is "
          "READ-dominated · boot = the fixed cost of EXISTING, paid once per dispatch",
          file=out)
    stalled = [s for s in subagents if s.get("stalls")]
    if stalled:
        print(f"  CAUTION: {len(stalled)} dispatch(es) idled past the {CACHE_TTL_SECONDS}s "
              f"prompt-cache TTL and paid to re-write their whole prefix — "
              f"{sum(s['stall_tokens'] for s in stalled)/1000:.1f}k of the `fed in` above is "
              f"that re-write, not material anyone supplied:", file=out)
        for s in stalled:
            print(f"          {s['node']:<18} {s['stalls']} stall(s), "
                  f"{s['stall_tokens']/1000:.1f}k re-written of {s['created_tokens']/1000:.1f}k"
                  f" fed in", file=out)

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


def router_trace(records):
    """What each node cost the ROUTER's own window, in order.

    The dispatch rule's whole claim is that a heavy leaf costs the orchestrator almost
    nothing while an inline node costs it everything the node reads. That is measurable, and
    nowhere else: walk the main window in order, note the context size at each `Skill`/`Agent`
    call, and the growth to the NEXT call is what that node added to the router.

    Honest about what it is: the delta also contains whatever routing the orchestrator did in
    between, so it is an upper bound per node, not a clean isolate. It is still the only view
    that puts an inline node and a dispatched one on the same axis.
    """
    marks, seen, ctx = [], set(), 0
    for r in records:
        if r.get("isSidechain") or r.get("type") != "assistant":
            continue
        msg = r.get("message") or {}
        key = msg.get("id") or r.get("requestId") or r.get("uuid")
        u = msg.get("usage") if isinstance(msg.get("usage"), dict) else {}
        if key not in seen:
            seen.add(key)
            ctx = max(ctx, _int(u, "cache_read_input_tokens"))
        for use in tool_uses(r):
            name = use.get("name")
            if name not in DISPATCH_TOOLS and name != "Skill":
                continue
            inp = use.get("input") if isinstance(use.get("input"), dict) else {}
            label = inp.get("skill") or inp.get("subagent_type") or "(unnamed)"
            marks.append({"how": "inline" if name == "Skill" else "dispatch",
                          "label": str(label).split(":")[-1], "at": ctx})
    for i, m in enumerate(marks):
        nxt = marks[i + 1]["at"] if i + 1 < len(marks) else ctx
        m["added"] = max(0, nxt - m["at"])
    return marks


def report_writer_scope(subagents, out=None, top=8, main_cost=None, trace=None):
    """The 11f attribution: WHERE a node's fed-in tokens came from, not just how many.

    "READ-dominated" is where the token components stop. It is not yet a diagnosis, because
    the two fixes it could imply are opposite: if the reads are the plan's own declared files,
    the writer is doing its job and a plan-size budget would only split the same reading
    across more dispatches; if they are off-plan hunting, the plan under-supplied scope and
    the fix is upstream in `planner`. This section is the part that tells those apart.
    """
    out = out or sys.stdout
    rows = [s for s in subagents if s.get("scope")]
    if not rows:
        print("\nwriter scope — no tool-level data in these transcripts (nothing measured)",
              file=out)
        return
    print("\nwriter scope — where the fed-in tokens came from (est. from tool-result sizes, "
          f"~{CHARS_PER_TOKEN} chars/token; SHARES are the point, not the absolute)", file=out)
    per = defaultdict(list)
    for s in rows:
        per[s["node"]].append(s)
    print(f"  {'node':<18} {'n':>3} {'discovery':>10} {'exec':>9} {'produced':>9} "
          f"{'disc:prod':>10} {'reads':>6} {'re-read':>8} {'off-plan':>9} {'loop':>6}",
          file=out)
    for node, rs in sorted(per.items(), key=lambda kv: -sum(
            r["scope"]["discovery_chars"] for r in kv[1])):
        disc = sum(r["scope"]["discovery_chars"] for r in rs) // CHARS_PER_TOKEN
        ex = sum(r["scope"]["exec_chars"] for r in rs) // CHARS_PER_TOKEN
        prod = sum(r["scope"]["produced_chars"] for r in rs) // CHARS_PER_TOKEN
        reads = sum(r["scope"]["read_calls"] for r in rs)
        rereads = sum(r["scope"]["reread_calls"] for r in rs)
        on = sum(r["scope"].get("on_plan_reads", 0) for r in rs)
        off = sum(r["scope"].get("off_plan_reads", 0) for r in rs)
        scaffold = sum(r["scope"].get("scaffolding_reads", 0) for r in rs)
        scored = on + off
        ratio = f"{disc/prod:.1f}x" if prod else "—"
        rr = f"{rereads/reads:.0%}" if reads else "—"
        op = f"{off/scored:.0%}" if scored else "no plan"
        print(f"  {node:<18} {len(rs):>3} {_k(disc):>10} {_k(ex):>9} {_k(prod):>9} "
              f"{ratio:>10} {reads:>6} {rr:>8} {op:>9} {scaffold:>6}", file=out)
    print("  discovery = Read/Grep/Glob + read-shaped Bash · exec = test/gate/git output "
          "(feedback, not context) · produced = bytes the worker authored", file=out)
    print("  off-plan = share of PRODUCT read calls on files the plan never named — the "
          "hunting signal (`no plan` = nothing to score against)", file=out)
    print("  loop = reads of .workflow/.claude the worker was told to make; never scored "
          "against a plan that does not list them", file=out)

    # The two lists that turn a ratio into an action: what got read again, and what the plan
    # never mentioned. A percentage says there is a problem; these say what to do about it.
    rereads = Counter()
    offs = Counter()
    for s in rows:
        pats = s["scope"].get("plan_patterns")
        for path, n in s["scope"]["files_read"].items():
            if n > 1:
                rereads[path] += n - 1
            if pats is not None and off_plan({path: n}, pats)[1]:
                offs[path] += n
    if rereads:
        print("\n  most re-read files (extra reads beyond the first, all workers)", file=out)
        for path, n in rereads.most_common(top):
            print(f"    {n:>4}  {path}", file=out)
    if offs:
        print("\n  most-read files the plan never named", file=out)
        for path, n in offs.most_common(top):
            print(f"    {n:>4}  {path}", file=out)

    if main_cost and main_cost.get("turns"):
        worker_in = sum(r["created_tokens"] for r in rows)
        worker_out = sum(r["output_tokens"] for r in rows)
        print(f"\n  the orchestrator's own window — where every INLINE node ran "
              f"(`planner`, `verify`, `commit`, …)", file=out)
        print(f"    {_k(main_cost['fed_in']):>8} fed in · {_k(main_cost['written']):>7} "
              f"written · {_k(main_cost['peak']):>7} peak · {main_cost['turns']:>4} calls",
              file=out)
        print(f"    {_k(worker_in):>8} fed in · {_k(worker_out):>7} written ·"
              f"          — · {len(rows):>4} workers   (all dispatched workers, summed)",
              file=out)
        share = main_cost["fed_in"] / (main_cost["fed_in"] + worker_in or 1)
        print(f"    the router is {share:.0%} of the drive's fed-in tokens — a plan-size "
              f"budget moves work ACROSS this line, it does not remove it", file=out)

    if trace:
        print(f"\n  what each node cost the ROUTER's window (context gained from this node "
              f"starting to the next one starting)", file=out)
        for m in trace:
            print(f"    at {m['at']/1000:6.1f}k  +{m['added']/1000:5.1f}k  "
                  f"{m['how']:<8} {m['label']}", file=out)
        inline = [m["added"] for m in trace if m["how"] == "inline"]
        disp = [m["added"] for m in trace if m["how"] == "dispatch"]
        if inline and disp:
            print(f"    median: inline {_median(inline)/1000:.1f}k vs dispatched "
                  f"{_median(disp)/1000:.1f}k per node — the dispatch rule's claim, measured",
                  file=out)


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
    ap.add_argument("--writer-scope", action="store_true",
                    help="also attribute the fed-in tokens: discovery vs exec vs produced, "
                         "the re-read tax, and reads off the plan's files_touched")
    args = ap.parse_args(argv)

    root = transcript_dir(args.project, args.dir)
    if not os.path.isdir(root):
        print(f"no transcripts at {root}\n"
              f"  (derived from {args.project!r} — pass --dir to point at it directly)",
              file=sys.stderr)
        return 1
    # The attribution needs the project tree itself (its plans name the declared scope), so it
    # is only offered when the transcripts were derived FROM a project rather than pointed at
    # with --dir. Silently scoring against no plan would report 0% off-plan on every node.
    project_root = args.project if not args.dir else None
    subagents, main_skills, main_dispatches, main_cost = scan(root, args.since,
                                                                 project_root)
    if args.json:
        json.dump({"root": root, "subagents": subagents,
                   "main_window_skill_loads": dict(main_skills),
                   "main_window_dispatches": main_dispatches,
                   "main_window_cost": main_cost}, sys.stdout, indent=2)
        print()
        return 0 if subagents else 1
    rc = report(subagents, main_skills, main_dispatches)
    if args.writer_scope and subagents:
        report_writer_scope(subagents, main_cost=main_cost,
                            trace=main_cost.get("trace"))
    return rc


if __name__ == "__main__":
    sys.exit(main())

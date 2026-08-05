#!/usr/bin/env python3
"""Synthesize "where is this project" from what the project already records.

The gap this closes: a project's state is real but SCATTERED — the spec holds intent, the backlog
holds what's left, the code map holds how it connects, git and `.workflow/items/` hold what was
actually done. Answering "where is this project" meant opening five things and holding them in your
head, so nobody did it, and the answer drifted.

DESIGN RULE — this is GENERATED, never stored. It writes no file and caches nothing. A synthesized
status doc is a doc that rots: it is stale the moment the next commit lands, and a stale status doc
is worse than none because it is believed. Run it again instead; it is cheap.

DIVISION OF LABOUR. This script does only the part a machine can settle exactly — counting, reading
frontmatter, resolving paths, ranking by centrality. It deliberately does NOT summarize, judge
progress, or infer intent; that is the `status` skill's job, reading this output. Keeping the
mechanical half deterministic is what makes the narrated half checkable: a reader can always ask
"where did that number come from" and get a file.

WHAT IT REFUSES TO DO. It never guesses. Every section reports its own source, and a section whose
source is missing says so rather than inferring from something else — a project with no spec is a
real and common state (a brownfield repo before `ingest`), and reporting "0 features" there would be
a lie dressed as data. `missing` and `zero` are different answers and are always rendered
differently.

Usage:
    python3 project_state.py [--workflow .workflow] [--json]

Exit codes: 0 always, unless the workflow root itself is absent (2) — "no project here" is a usage
error, not a state to render.
"""
import argparse
import json
import os
import re
import subprocess
import sys

# ---------------------------------------------------------------- small readers


def read_text(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return fh.read()
    except (OSError, UnicodeDecodeError):
        return None


def read_json(path):
    raw = read_text(path)
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def git(repo, *args):
    """Read-only git. Returns stdout, or None if git is unusable here.

    Never raises: a project need not be a git repo, and `status` must still answer for one that
    is not. `git -C <nonexistent>` returns non-zero rather than raising, so the returncode check
    is the real guard, not the exception handler.
    """
    try:
        p = subprocess.run(["git", "-C", repo, *args],
                           capture_output=True, text=True, timeout=15)
    except (OSError, subprocess.SubprocessError):
        return None
    return p.stdout.strip() if p.returncode == 0 else None


# ---------------------------------------------------------------- path resolution


def resolve_roots(workflow):
    """(repo, docs_root) — honouring config.json's project_root/docs_root split.

    `docs_root` absent means it equals `project_root`, which is the ordinary case; org mode sets
    it so the derived tree never interleaves with an owner's own `docs/`. Getting this wrong would
    make `status` read the WRONG project's spec in the one mode where that matters most.
    """
    cfg = read_json(os.path.join(workflow, "config.json")) or {}
    repo = os.path.dirname(os.path.abspath(workflow)) or "."
    proot = cfg.get("project_root") or "."
    repo = os.path.normpath(os.path.join(repo, proot))
    droot = cfg.get("docs_root")
    docs = os.path.normpath(os.path.join(repo, droot)) if droot else repo
    return repo, docs


# ---------------------------------------------------------------- the three faces


COMMITMENTS = ("locked", "provisional", "unspecified")


def spec_face(docs_root):
    """WHAT IS INTENDED — features/screens and how settled each one is.

    Commitment lives on the spec element and nowhere else, so this is the only place it is read
    from. The counts are the useful signal: a project that is 90% `provisional` has not been
    decided yet, however much code exists.
    """
    path = os.path.join(docs_root, "docs", "spec.md")
    text = read_text(path)
    if text is None:
        return {"source": path, "present": False}

    # Count commitment tags as WRITTEN, not as inferred. A bare mention in prose is not a tag, so
    # anchor on the `commitment:`/`commitment =` forms the schema actually emits.
    tags = {c: 0 for c in COMMITMENTS}
    for m in re.finditer(r"commitment\s*[:=]\s*`?\*{0,2}(\w+)", text, re.I):
        v = m.group(1).lower()
        if v in tags:
            tags[v] += 1

    open_decisions = len(re.findall(r"TBD\s*(?:→|->)\s*decision-engineer", text, re.I))
    headings = re.findall(r"^##+\s+(.+?)\s*$", text, re.M)
    return {
        "source": path,
        "present": True,
        "sections": headings[:40],
        "section_count": len(headings),
        "commitment": tags,
        "commitment_total": sum(tags.values()),
        "open_decisions": open_decisions,
    }


def connect_face(docs_root, top=10):
    """HOW IT CONNECTS — the code map's two centrality lenses.

    Read from graph.json's summary fields only. The graph is machine-data and is never loaded
    whole into a reading context; taking the top-N per lens is the bounded read the memory model
    requires, and it is also the only part a human can act on.
    """
    path = os.path.join(docs_root, "docs", "knowledge", "graph.json")
    graph = read_json(path)
    if graph is None:
        return {"source": path, "present": False}

    nodes = graph.get("nodes") or []
    if isinstance(nodes, dict):                       # tolerate a mapping shape
        nodes = [{**v, "path": k} for k, v in nodes.items()]

    def rank(lens):
        scored = []
        for n in nodes:
            if not isinstance(n, dict):
                continue
            cen = n.get("centrality") or {}
            val = cen.get(lens)
            if isinstance(val, (int, float)):
                scored.append((val, n.get("path") or n.get("id") or "?"))
        scored.sort(reverse=True)
        return [{"path": p, "score": round(v, 5)} for v, p in scored[:top]]

    langs = {}
    for n in nodes:
        if isinstance(n, dict) and n.get("lang"):
            langs[n["lang"]] = langs.get(n["lang"], 0) + 1

    return {
        "source": path,
        "present": True,
        "node_count": len(nodes),
        "edge_count": len(graph.get("edges") or []),
        "languages": dict(sorted(langs.items(), key=lambda kv: -kv[1])),
        "impact": rank("impact"),
        "orchestration": rank("orchestration"),
    }


def left_face(workflow):
    """WHAT IS LEFT — the backlog queue plus anything parked awaiting a human.

    Parked items are called out separately and first. They are not "left to do" in the ordinary
    sense: they are BLOCKED ON THE READER, and burying them in a backlog count is how a checkpoint
    sits unanswered for a week.
    """
    backlog_path = os.path.join(workflow, "backlog.md")
    text = read_text(backlog_path)
    items = []
    if text:
        for line in text.splitlines():
            s = line.strip()
            m = re.match(r"^[-*]\s*\[( |x|X)\]\s*(.+)$", s)
            if m:
                items.append({"done": m.group(1).lower() == "x", "title": m.group(2).strip()})
            elif re.match(r"^[-*]\s+\S", s):
                items.append({"done": False, "title": s.lstrip("-* ").strip()})

    parked = []
    pdir = os.path.join(workflow, "parked")
    if os.path.isdir(pdir):
        for name in sorted(os.listdir(pdir)):
            rec = read_json(os.path.join(pdir, name))
            if isinstance(rec, dict):
                parked.append({
                    "id": rec.get("item") or os.path.splitext(name)[0],
                    "kind": rec.get("kind"),
                    "question": rec.get("question") or rec.get("summary"),
                })
    return {
        "source": backlog_path,
        "backlog_present": text is not None,
        "open": [i for i in items if not i["done"]],
        "done": [i for i in items if i["done"]],
        "parked": parked,
    }


def done_face(workflow, repo, limit=15):
    """WHAT IS DONE — completed items, corroborated by git rather than self-reported.

    `.workflow/items/<id>/` says what the loop BELIEVES it finished; git says what actually
    landed. Both are reported, deliberately unreconciled: where they disagree, that disagreement
    is the interesting fact and is not this script's to resolve.
    """
    items = []
    idir = os.path.join(workflow, "items")
    if os.path.isdir(idir):
        for name in sorted(os.listdir(idir)):
            d = os.path.join(idir, name)
            if not os.path.isdir(d):
                continue
            verdict = read_text(os.path.join(d, "verify-verdict.md")) or ""
            first = verdict.splitlines()[0].strip() if verdict else ""
            items.append({
                "id": name,
                "verified": first == "pass: true",
                "verdict_present": bool(verdict),
            })

    log = git(repo, "log", "--oneline", "-n", str(limit))
    commits = [l for l in log.splitlines() if l.strip()] if log else []
    return {
        "items": items,
        "item_count": len(items),
        "verified_count": sum(1 for i in items if i["verified"]),
        "commits": commits,
        "git_available": log is not None,
    }


def position_face(workflow):
    """WHERE THE LOOP IS RIGHT NOW — state.json, reported verbatim, never inferred."""
    state = read_json(os.path.join(workflow, "state.json"))
    if state is None:
        return {"present": False}
    return {
        "present": True,
        "status": state.get("status"),
        "phase": state.get("phase"),
        "node": state.get("node"),
        "current_item": state.get("current_item"),
        "wave": state.get("wave"),
        "note": state.get("note"),
    }


# ---------------------------------------------------------------- render


def collect(workflow):
    repo, docs = resolve_roots(workflow)
    return {
        "workflow": workflow,
        "repo": repo,
        "docs_root": docs,
        "position": position_face(workflow),
        "intent": spec_face(docs),
        "connects": connect_face(docs),
        "left": left_face(workflow),
        "done": done_face(workflow, repo),
    }


def _bar(label, n, width=28):
    return "%-14s %s %d" % (label, "#" * min(n, width), n)


def render(s):
    out = []
    a = out.append
    a("WHERE IS THIS PROJECT")
    a("=" * 60)
    a("repo:      %s" % s["repo"])
    if s["docs_root"] != s["repo"]:
        a("docs root: %s   (split — org mode)" % s["docs_root"])
    a("")

    p = s["position"]
    a("-- RIGHT NOW " + "-" * 47)
    if not p["present"]:
        a("  no state.json — the loop has never run here.")
    else:
        a("  status:  %s" % (p["status"] or "?"))
        a("  node:    %s" % (p["node"] or "?"))
        if p["phase"]:
            a("  phase:   %s" % p["phase"])
        if p["current_item"]:
            a("  item:    %s" % p["current_item"])
        if p["note"]:
            a("  note:    %s" % p["note"])
    a("")

    i = s["intent"]
    a("-- WHAT IS INTENDED " + "-" * 40)
    if not i["present"]:
        a("  no spec at %s" % i["source"])
        a("  (a brownfield repo before `ingest` is legitimately here — not an error)")
    else:
        a("  %d sections, %d commitment tags, %d open decision%s"
          % (i["section_count"], i["commitment_total"], i["open_decisions"],
             "" if i["open_decisions"] == 1 else "s"))
        for c in COMMITMENTS:
            a("    " + _bar(c, i["commitment"][c]))
        if i["commitment_total"] == 0:
            a("    (no commitment tags found — intent is recorded but not graded)")
    a("")

    c = s["connects"]
    a("-- HOW IT CONNECTS " + "-" * 41)
    if not c["present"]:
        a("  no code map at %s" % c["source"])
        a("  (run the code map to populate this)")
    else:
        a("  %d files, %d edges   %s" % (
            c["node_count"], c["edge_count"],
            ", ".join("%s:%d" % kv for kv in list(c["languages"].items())[:6]) or "-"))
        if c["impact"]:
            a("  most depended-upon (change blast-radius):")
            for n in c["impact"][:5]:
                a("    %-48s %s" % (n["path"][:48], n["score"]))
        if c["orchestration"]:
            a("  composes the most (where behaviour lives):")
            for n in c["orchestration"][:5]:
                a("    %-48s %s" % (n["path"][:48], n["score"]))
    a("")

    d = s["done"]
    a("-- WHAT IS DONE " + "-" * 44)
    a("  %d items recorded, %d with a passing verify" % (d["item_count"], d["verified_count"]))
    if not d["git_available"]:
        a("  git unavailable here — commit history not corroborated")
    else:
        a("  recent commits:")
        for line in d["commits"][:8]:
            a("    " + line)
    a("")

    l = s["left"]
    a("-- WHAT IS LEFT " + "-" * 44)
    if l["parked"]:
        a("  BLOCKED ON YOU — %d parked:" % len(l["parked"]))
        for pk in l["parked"]:
            a("    [%s] %s — %s" % (pk["kind"] or "?", pk["id"], (pk["question"] or "")[:60]))
    if not l["backlog_present"]:
        a("  no backlog at %s" % l["source"])
    else:
        a("  %d open, %d done" % (len(l["open"]), len(l["done"])))
        for it in l["open"][:10]:
            a("    - " + it["title"][:70])
        if len(l["open"]) > 10:
            a("    ... and %d more" % (len(l["open"]) - 10))
    a("")
    a("(generated fresh — nothing here is stored, so nothing here can go stale)")
    return "\n".join(out)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Synthesize where this project is.")
    ap.add_argument("--workflow", default=os.environ.get("WORKFLOW_DIR", ".workflow"))
    ap.add_argument("--json", action="store_true", help="emit the raw structure instead of prose")
    args = ap.parse_args(argv)

    if not os.path.isdir(args.workflow):
        sys.stderr.write(
            "project_state: no workflow root at %r — is this a started project?\n" % args.workflow)
        return 2

    s = collect(args.workflow)
    print(json.dumps(s, indent=2) if args.json else render(s))
    return 0


if __name__ == "__main__":
    sys.exit(main())

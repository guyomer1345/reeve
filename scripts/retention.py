#!/usr/bin/env python3
"""Retention pass — the deterministic memory-bound enforcer (the `audit` script).

Bounds the append-only tier by READ-COST, not disk: the working tree is a bounded
cache, git is the ledger (see shared/memory-model.md). This is the mechanical half
of the `audit` maintenance item — pure counts / moves / deletes, zero judgment.
The judgment half (the deletion-test over CLAUDE.md + rules/) is a separate model-run
step, NOT this script.

Three caps, all idempotent (re-running a bounded tree is a no-op):

  1. Sessions cap   — per knowledge node, keep the last K `## [date] kind | title`
                      entries on disk; older ones live in git. A one-line marker under
                      `# Sessions` records how many were dropped and the git anchor.
  2. Decisions GC   — a decision-record whose frontmatter `status: superseded` has its
                      body dropped to git; `docs/decisions/index.md` keeps a tombstone
                      row (id | title | superseded->X | git <sha>).
  3. Items prune    — a closed item dir `.workflow/items/<id>/` is removed ONLY once
                      `document` has folded its essence (a `promoted.json` marker). No
                      marker -> skip, so the script can never delete un-promoted memory.

The git-log cold-start bound is a READ convention (handoff.base_sha), not an action here.
Dead-node prune (deleted source -> delete node) is a staleness signal, owned by
`document`, not this size-cap script.

Deletions are made in the working tree and left UNSTAGED for the `audit` item's commit
to pick up (its `git add -A` stages them); the content stays recoverable in history. The
only git call here is reading HEAD for the archive anchor.

Usage:  retention.py [--workflow-dir DIR] [--project-root DIR] [--sessions-k K]
                     [--dry-run] [--json]
  --workflow-dir   the `.workflow/` root (default: .workflow)
  --project-root   docs-root parent; default: read from <workflow-dir>/config.json
  --sessions-k     override the Sessions cap; default: config.retention.sessions_k or 10
  --dry-run        report what would change, touch nothing
  --json           emit the summary as JSON
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys

DEFAULT_SESSIONS_K = 10

# marker written under `# Sessions`; the (\d+) is parsed back to accumulate across runs
SESSIONS_MARKER_RE = re.compile(r"<!--\s*retention:\s*(\d+)\s+Sessions entries archived")
ENTRY_RE = re.compile(r"^## ")           # a Sessions entry header: `## [date] kind | title`
TOPLEVEL_RE = re.compile(r"^# \S")       # a top-level `# Heading` line


def git_anchor(cwd):
    """Short HEAD sha the archived content is findable at/before; safe fallback."""
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=cwd, capture_output=True, text=True, check=True,
        )
        return out.stdout.strip() or "uncommitted"
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "uncommitted"


def load_config(workflow_dir):
    path = os.path.join(workflow_dir, "config.json")
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (FileNotFoundError, ValueError):
        return {}


# --- cap 1: Sessions ---------------------------------------------------------

def split_sessions(lines):
    """Return (head, region, tail): the lines before `# Sessions`, the section body,
    and any trailing top-level section. Returns None if the node has no `# Sessions`.

    A `# `-prefixed line *inside* a postmortem body (a markdown H1, a diff/comment line)
    must NOT be mistaken for the section boundary — that would truncate the region and
    leave later entries uncapped. So a top-level heading only ends the region if it
    appears BEFORE the first `## ` entry; once entries have begun, the region runs to
    EOF (by the node convention that `# Sessions` is the terminal section)."""
    start = next((i for i, ln in enumerate(lines)
                  if ln.rstrip() == "# Sessions" or ln.startswith("# Sessions ")), None)
    if start is None:
        return None
    end = len(lines)
    seen_entry = False
    for i in range(start + 1, len(lines)):
        if ENTRY_RE.match(lines[i]):
            seen_entry = True
        elif TOPLEVEL_RE.match(lines[i]) and not seen_entry:
            end = i
            break
    return lines[:start + 1], lines[start + 1:end], lines[end:]


def parse_entries(region):
    """Split a Sessions region into (existing_archived_count, [entry_blocks])."""
    archived = 0
    entries, cur = [], None
    for ln in region:
        m = SESSIONS_MARKER_RE.search(ln)
        if m:
            archived = int(m.group(1))
            continue
        if ENTRY_RE.match(ln):
            if cur is not None:
                entries.append(cur)
            cur = [ln]
        elif cur is not None:
            cur.append(ln)
        # lines before the first entry (blank/whitespace) are dropped on rebuild
    if cur is not None:
        entries.append(cur)
    return archived, entries


def cap_sessions(path, k, anchor, dry_run):
    with open(path, encoding="utf-8") as fh:
        lines = fh.read().splitlines(keepends=True)
    split = split_sessions(lines)
    if split is None:
        return 0
    head, region, tail = split
    archived, entries = parse_entries(region)
    if len(entries) <= k:
        return 0
    drop = entries[:-k]
    kept = entries[-k:]
    total = archived + len(drop)
    marker = f"<!-- retention: {total} Sessions entries archived -> git @ {anchor} -->\n"
    new_region = ["\n", marker, "\n"] + [ln for entry in kept for ln in entry]
    if not dry_run:
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("".join(head) + "".join(new_region) + "".join(tail))
    return len(drop)


# --- cap 2: decisions --------------------------------------------------------

def parse_frontmatter(text):
    """Minimal `key: value` frontmatter parse (no YAML dep). Returns {} if none."""
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end == -1:
        return {}
    fm = {}
    for ln in text[3:end].splitlines():
        if ":" in ln:
            key, val = ln.split(":", 1)
            fm[key.strip()] = val.strip().strip("'\"")
    return fm


INDEX_HEADER = "| id | title | status | ref |\n|---|---|---|---|\n"


def read_index_rows(index_path):
    """Return (preamble_lines, ordered {id: row_cells}, postamble_lines). Row cells
    exclude the id. Prose after the table (postamble) is preserved, not dropped."""
    rows = {}
    preamble = []
    postamble = []
    try:
        with open(index_path, encoding="utf-8") as fh:
            lines = fh.read().splitlines()
    except FileNotFoundError:
        return ["# Decision Index", ""], rows, []
    table_seen = 0
    for ln in lines:
        if ln.lstrip().startswith("|"):
            cells = [c.strip() for c in ln.strip().strip("|").split("|")]
            table_seen += 1
            if table_seen <= 2:      # header + separator
                continue
            if cells:
                rows[cells[0]] = cells[1:]
        elif table_seen == 0:
            preamble.append(ln)
        else:                        # non-table line after the table: human prose, keep it
            postamble.append(ln)
    return preamble, rows, postamble


def write_index(index_path, preamble, rows, postamble=None):
    body = INDEX_HEADER
    for did, cells in rows.items():
        body += "| " + " | ".join([did] + cells) + " |\n"
    text = "\n".join(preamble).rstrip("\n") + "\n\n" + body
    if postamble and any(ln.strip() for ln in postamble):
        text += "\n" + "\n".join(postamble).strip("\n") + "\n"
    with open(index_path, "w", encoding="utf-8") as fh:
        fh.write(text)


def gc_decisions(decisions_dir, anchor, dry_run):
    if not os.path.isdir(decisions_dir):
        return []
    preamble, rows, postamble = read_index_rows(os.path.join(decisions_dir, "index.md"))
    gcd = []
    for fn in sorted(os.listdir(decisions_dir)):
        if not fn.endswith(".md") or fn == "index.md":
            continue
        path = os.path.join(decisions_dir, fn)
        with open(path, encoding="utf-8") as fh:
            fm = parse_frontmatter(fh.read())
        if fm.get("status") != "superseded":
            continue
        did = fm.get("id") or os.path.splitext(fn)[0]
        title = fm.get("title") or fm.get("question") or did
        by = fm.get("superseded_by", "?")
        rows[did] = [title, f"superseded->{by}", f"git {anchor}"]
        gcd.append(did)
        if not dry_run:
            os.remove(path)
    if gcd and not dry_run:
        write_index(os.path.join(decisions_dir, "index.md"), preamble, rows, postamble)
    return gcd


# --- cap 3: items ------------------------------------------------------------

def prune_items(items_dir, dry_run):
    """Prune item dirs carrying a `promoted.json` marker. Returns (pruned, skipped)."""
    if not os.path.isdir(items_dir):
        return [], []
    pruned, skipped = [], []
    for name in sorted(os.listdir(items_dir)):
        item = os.path.join(items_dir, name)
        if not os.path.isdir(item):
            continue
        marker = os.path.join(item, "promoted.json")
        promoted = False
        try:
            with open(marker, encoding="utf-8") as fh:
                promoted = json.load(fh).get("promoted") is True
        except (FileNotFoundError, ValueError):
            promoted = False
        if promoted:
            pruned.append(name)
            if not dry_run:
                shutil.rmtree(item)
        else:
            skipped.append(name)
    return pruned, skipped


# --- driver ------------------------------------------------------------------

def main(argv=None):
    ap = argparse.ArgumentParser(description="Deterministic retention pass (the audit script).")
    ap.add_argument("--workflow-dir", default=".workflow")
    ap.add_argument("--project-root", default=None)
    ap.add_argument("--sessions-k", type=int, default=None)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    cfg = load_config(args.workflow_dir)
    project_root = args.project_root or cfg.get("project_root", ".")
    k = args.sessions_k if args.sessions_k is not None \
        else cfg.get("retention", {}).get("sessions_k", DEFAULT_SESSIONS_K)

    docs = os.path.join(project_root, "docs")
    knowledge_dir = os.path.join(docs, "knowledge")
    decisions_dir = os.path.join(docs, "decisions")
    items_dir = os.path.join(args.workflow_dir, "items")
    anchor = git_anchor(args.workflow_dir)

    sessions = {}
    if os.path.isdir(knowledge_dir):
        for dirpath, _, filenames in os.walk(knowledge_dir):
            for fn in sorted(filenames):
                if fn.endswith(".md"):
                    path = os.path.join(dirpath, fn)
                    dropped = cap_sessions(path, k, anchor, args.dry_run)
                    if dropped:
                        sessions[os.path.relpath(path, docs)] = dropped

    gcd = gc_decisions(decisions_dir, anchor, args.dry_run)
    pruned, skipped = prune_items(items_dir, args.dry_run)

    summary = {
        "dry_run": args.dry_run,
        "sessions_k": k,
        "anchor": anchor,
        "sessions_archived": sessions,
        "decisions_gcd": gcd,
        "items_pruned": pruned,
        "items_skipped_unmarked": skipped,
    }
    if args.json:
        print(json.dumps(summary, indent=2))
    else:
        verb = "would " if args.dry_run else ""
        total_entries = sum(sessions.values())
        print(f"retention (K={k}, anchor={anchor}):")
        print(f"  {verb}archive {total_entries} Sessions entries across {len(sessions)} node(s)")
        for node, n in sessions.items():
            print(f"    - {node}: {n}")
        print(f"  {verb}GC {len(gcd)} superseded decision(s): {', '.join(gcd) or '-'}")
        print(f"  {verb}prune {len(pruned)} promoted item(s): {', '.join(pruned) or '-'}")
        if skipped:
            print(f"  skipped {len(skipped)} unmarked item dir(s) (open or not-yet-promoted): "
                  f"{', '.join(skipped)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

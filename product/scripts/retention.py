#!/usr/bin/env python3
"""Retention pass — the deterministic memory-bound enforcer (the `audit` script).

Bounds the append-only tier by READ-COST, not disk: the working tree is a bounded
cache, git is the ledger (see shared/memory-model.md). This is the mechanical half
of the `audit` maintenance item — pure counts / moves / deletes, zero judgment.
The judgment half (the deletion-test over CLAUDE.md + rules/) is a separate model-run
step, NOT this script.

The caps, in RUN ORDER, all idempotent (re-running a bounded tree is a no-op):

  1. Sessions cap   — per knowledge node, keep the last K `## [date] kind | title`
                      entries on disk; older ones live in git. A one-line marker under
                      `# Sessions` records how many were dropped and the git anchor.
  2. Decisions GC   — a decision-record whose frontmatter `status: superseded` has its
                      body dropped to git; `docs/decisions/index.md` keeps a tombstone
                      row (id | title | superseded->X | git <sha>).
  3. Forecast prune — a chain-forecast `.workflow/forecasts/<id>.json` is removed on the
                      SAME `promoted.json` marker that authorizes closing its item dir,
                      so the committed forecast has the item-dir lifecycle exactly.
                      Runs BEFORE cap 4, which deletes the marker they share.
  4. Items prune    — a closed item dir `.workflow/items/<id>/` is removed ONLY once
                      `document` has folded its essence (a `promoted.json` marker). No
                      marker -> skip, so the script can never delete un-promoted memory.
  5. Demos prune    — a throwaway demo bundle with no open checkpoint pointing at it
                      (the straggler backstop; the primary delete is the verdict-apply).

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


# --- cap 3b: chain-forecasts --------------------------------------------------

def _promoted_items(items_dir):
    """Item ids whose `promoted.json` says `document` has folded their essence."""
    out = set()
    try:
        names = os.listdir(items_dir)
    except OSError:
        return out
    for name in names:
        try:
            with open(os.path.join(items_dir, name, "promoted.json"), encoding="utf-8") as fh:
                if json.load(fh).get("promoted") is True:
                    out.add(name)
        except (OSError, ValueError):
            continue
    return out


def prune_forecasts(forecasts_dir, items_dir, dry_run):
    """Prune `forecasts/<id>.json` for every item the same marker authorizes closing.

    The forecast is a COMMITTED artifact with the ITEM-DIR lifecycle: committed
    while the change is open, pruned when it closes, history in git. "Copies the item-dir
    lifecycle exactly" is meant literally — it keys off the *same* `promoted.json` marker
    `prune_items` does, so there is one closure fact and one writer for it, not a second
    signal to keep in step.

    Closure is read POSITIVELY and never inferred from absence. A forecast is written at
    intake, before the demo and before any item dir exists (a forecast placed after the
    demo cannot predict the demo checkpoint — one of the very gates it exists to
    front-load). So a missing item dir is what a brand-new forecast looks like, and
    "no dir ⇒ closed" would delete every forecast at birth. Returns (pruned, kept).

    Honest ceiling, stated rather than papered over: a forecast for a change that never
    became an item — an intake abandoned before planning — is never pruned by this. It is
    the same straggler class as an orphaned demo bundle, and it is left for a human rather
    than guessed at, because the guess that would collect it is the same guess that would
    delete a live one.
    """
    if not os.path.isdir(forecasts_dir):
        return [], []
    promoted = _promoted_items(items_dir)
    pruned, kept = [], []
    for name in sorted(os.listdir(forecasts_dir)):
        if not name.endswith(".json"):
            continue
        fid = name[:-5]
        if fid in promoted:
            pruned.append(fid)
            if not dry_run:
                try:
                    os.remove(os.path.join(forecasts_dir, name))
                except OSError:
                    pass
        else:
            kept.append(fid)
    return pruned, kept


# --- cap 4: demo sandboxes ---------------------------------------------------

def prune_demos(demos_dir, parked_dir, dry_run):
    """Straggler-prune throwaway demo bundles.

    A demo sandbox is only needed while its checkpoint is open, and an open checkpoint
    always has a `parked/<id>.json` record pointing at it. So a `demos/<id>/` with no
    matching parked record is a resolved (approved/rejected) or crashed-past checkpoint's
    leftover — safe to delete. This is the BACKSTOP: the primary prune is the
    terminal-verdict apply path (approve -> lock the spec / reject -> discuss), which
    deletes the bundle at resolve; this sweeps a bundle orphaned by a crash between
    resolve and delete. Conservative by construction — an unreadable parked record, or
    one that names this id by ticket or demo pointer, keeps the bundle. Returns
    (pruned, skipped)."""
    if not os.path.isdir(demos_dir):
        return [], []
    open_ids = set()
    try:
        parked_names = os.listdir(parked_dir)
    except OSError:
        parked_names = []
    for n in parked_names:
        if not n.endswith(".json"):
            continue
        open_ids.add(n[:-5])                       # the record stem
        try:
            with open(os.path.join(parked_dir, n), encoding="utf-8") as fh:
                rec = json.load(fh)
        except (OSError, ValueError):
            continue                               # unreadable -> stem already kept
        if isinstance(rec, dict):
            if rec.get("ticket_id"):
                open_ids.add(rec["ticket_id"])
            cp = rec.get("checkpoint") or {}
            if isinstance(cp, dict) and cp.get("demo_id"):
                open_ids.add(cp["demo_id"])
    pruned, skipped = [], []
    for name in sorted(os.listdir(demos_dir)):
        d = os.path.join(demos_dir, name)
        if not os.path.isdir(d):
            continue
        if name in open_ids:
            skipped.append(name)                   # checkpoint still open — keep it
        else:
            pruned.append(name)
            if not dry_run:
                shutil.rmtree(d, ignore_errors=True)
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
    forecasts_dir = os.path.join(args.workflow_dir, "forecasts")
    demos_dir = os.path.join(args.workflow_dir, "demos")
    parked_dir = os.path.join(args.workflow_dir, "parked")
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
    # BEFORE prune_items, and the order is load-bearing: both read the same
    # `promoted.json`, and prune_items deletes the dir that holds it. The other way round,
    # a crash between the two would strand a forecast whose marker no longer exists —
    # nothing could ever authorize its delete again. This way a crash leaves only the item
    # dir, which the next audit re-prunes.
    fc_pruned, fc_kept = prune_forecasts(forecasts_dir, items_dir, args.dry_run)
    pruned, skipped = prune_items(items_dir, args.dry_run)
    demos_pruned, demos_skipped = prune_demos(demos_dir, parked_dir, args.dry_run)

    summary = {
        "dry_run": args.dry_run,
        "sessions_k": k,
        "anchor": anchor,
        "sessions_archived": sessions,
        "decisions_gcd": gcd,
        "forecasts_pruned": fc_pruned,
        "forecasts_kept_open": fc_kept,
        "items_pruned": pruned,
        "items_skipped_unmarked": skipped,
        "demos_pruned": demos_pruned,
        "demos_skipped_open": demos_skipped,
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
        print(f"  {verb}prune {len(fc_pruned)} closed-change forecast(s): "
              f"{', '.join(fc_pruned) or '-'}")
        if fc_kept:
            print(f"  kept {len(fc_kept)} forecast(s) whose change is still open: "
                  f"{', '.join(fc_kept)}")
        if skipped:
            print(f"  skipped {len(skipped)} unmarked item dir(s) (open or not-yet-promoted): "
                  f"{', '.join(skipped)}")
        print(f"  {verb}prune {len(demos_pruned)} resolved demo bundle(s): "
              f"{', '.join(demos_pruned) or '-'}")
        if demos_skipped:
            print(f"  skipped {len(demos_skipped)} demo bundle(s) with an open checkpoint: "
                  f"{', '.join(demos_skipped)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

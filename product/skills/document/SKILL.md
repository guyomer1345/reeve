---
name: document
description: Fold completed changes and the decisions behind them into the project knowledge base — its knowledge nodes, typed edges, and per-file history log. Runs after a phase passes its checkpoint. Reads the changelog plus the decision/event stream, not just the diff.
---

# Document — keep the knowledge base current

Core principle: document-as-it-goes so the workflow can stay autonomous — fold each completed change and
the decisions behind it into the knowledge base.

## When
After a phase/item passes its checkpoint, before or with `commit`.

## Inputs
`changelog` + `decision-record`s + `debug-report`s — the decision/event stream, not just the changelog — plus
the item's `spec` + each element's `commitment` (its own rules need them: never flag a `provisional` item, and
judge intent-vs-actual divergence against the recorded intent).

## Workflow
1. Update `docs/knowledge/` nodes for touched files — `purpose` (intent vs actual), typed edges with their
   `why`.
2. Refresh the **architecture doc** (inline Mermaid-C4 L1/L2) in the **same item** when the change moves
   system/container structure — STABLE, changes only with the code. *(It lives at
   `<project_root>/docs/architecture.md`; resolve `<project_root>` from `config.json`.)* **Adopt an existing
   architecture doc — never a second one:** scan `<project_root>/docs/` **case-insensitively** first; if the
   project already ships one (e.g. an adopted `ARCHITECTURE.md`), refresh **that** file in place. The committed
   `docs/` often lives on a case-insensitive filesystem (Windows / WSL `/mnt/*` 9p / default macOS), where
   `architecture.md` and `ARCHITECTURE.md` are the **same file** — so creating the lowercase name would silently
   overwrite the adopted doc. Only create `docs/architecture.md` when no case-variant exists (the greenfield case).
3. Append a per-file `# Sessions` entry where a postmortem applies (a `debug-report` maps directly:
   symptom / cause / fix / avoid). Each entry's header is **`## [date] kind | title`** — the strict,
   lint-parseable form `retention.py` splits entries on; keep `# Sessions` the node's terminal section.
4. Flag intent-vs-actual divergence as a signal.
5. **Mark the item promoted** — once this item's essence is folded (the `# Sessions` entry written, its
   `decision-record`s already in `docs/decisions/`), write `.workflow/items/<id>/promoted.json`
   (`{ "promoted": true }`). This is the sole gate the audit prune reads: no marker → the dir is never pruned, so
   the mechanical pass can't delete un-promoted memory.

## Rules
- **Never** flag divergence for `provisional` items, or the drift alarm chases ghosts.

## Output
Updated `docs/knowledge/` (nodes, graph, Sessions) + the architecture doc.

## Audit mode (retention + prune)
A second mode, run as a maintenance item `prioritize` injects on a count/size threshold (not after each phase).
Keeps disk + context high-signal:
- **Distil FIRST, then cap — the order is load-bearing.** For each entry about to fall past *K*, write its
  one-line lesson into the node's **`# Lessons`** section before the script runs. Compression beats raw retention:
  a distilled entry leaves something behind, a raw one dropped to git leaves nothing a future session will read.
  The script is deterministic and cannot distil, so this pass must precede it — distilling *after* the cap means
  distilling from git. `# Lessons` is append-only and **not** capped (it is already the compressed form), and it
  is a **top-level section placed BEFORE `# Sessions`** — never a `##` inside it, because the Sessions region runs
  to EOF once entries begin, so a nested heading would be read as a session entry and capped away.
- **Run the retention script** (`.claude/scripts/retention.py` — mechanical + idempotent, counts/moves/deletes,
  no judgment): caps each node's `# Sessions` to the last *K* (`config.retention.sessions_k`; older → git, a
  one-line head marker under `# Sessions`), GCs superseded `docs/decisions/` bodies to git + tombstones
  `docs/decisions/index.md`, and prunes only `items/<id>/` carrying a `promoted.json` marker (unmarked → skipped).
  It leaves deletions staged for this item's `commit`. (The `git log` cold-start bound rides `handoff.base_sha`.)
- **Deletion-test (judgment)** over `CLAUDE.md` + `rules/` — cut prose the agent no longer needs; bloat makes
  it ignore its own instructions.
- **Dead-node prune:** a deleted source file → delete its `docs/knowledge/` node.
- **Doc budget is a SEPARATE item, not part of this one.** `doc-budget` has its own trigger and its own remedy
  (trim / split-and-pointer); folding it in here would tie doc size to memory pressure, which is the coupling
  the three decoupled thresholds exist to avoid.

## Route
→ `commit`.

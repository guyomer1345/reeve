---
name: ingest
description: Brownfield bootstrap — build the project knowledge base and reconstruct a spec from an existing codebase, then gate on a human reconciliation before the loop drives. Generates the structural code map, seeds the app's core intended behaviour from the existing CLAUDE.md/docs (never guessed from code), and hands the reconstructed understanding to a blocking checkpoint. Invoked by /start on an existing repo; routes to the normal loop once the human confirms.
---

# Ingest — reconstruct the knowledge base from existing code

Core principle: a code map tells you what depends on what; only the humans' prose tells you what the app is
*for*. Derive the structure mechanically; reconstruct intent from the existing docs — never guess intent from
code alone.

## When
`/start` on a brownfield repo (existing code), or a re-ingest after a large external change. Greenfield skips it.

## Inputs
- the existing codebase + any existing `CLAUDE.md` / `docs/` / README — the only source of behavioural intent.
- the `/start`-generated code-map runner (`.workflow/codemap.sh`) — a thin stack-independent wrapper that
  auto-dispatches every file to its language arm; there is nothing per-stack to detect before running it.

## Workflow
**Signal every stage.** This build runs for tens of minutes on a real repo; a silent build reads as a hang. At
every stage boundary below, publish `.workflow/state.json` (atomic) as `{"status": "building",
"phase": "bootstrap", "node": "ingest:<stage>", "note": "<one human line — 'codemap: 374 nodes',
'seeding knowledge nodes 40/95'"}` and print the same one-line banner — the console's "Now" panel renders
exactly these fields.

1. **Generate the structure.** Run the code-map extractor to build `docs/knowledge/graph.json`: typed
   import/call edges plus two centrality signals — *impact* (most-depended-upon → change blast-radius) and
   *orchestration* (composes many → where behaviour lives). Generated, never hand-authored.
2. **Recover the behavioural core first** (so node seeding isn't driven by centrality). Dispatch `research` to
   **gather** — read, not synthesize — the existing `CLAUDE.md`/docs/README + the orchestration-central files and
   return `findings`; **`ingest` then synthesizes** the reconstructed `spec` from them — **write it per the
   `spec` schema (`schemas.md`)**: audience, runtime, purpose, screens[], features[], data_model, integrations[],
   tech_stack. Synthesis is ingest's job, not `research`'s gather-only charter. Tag every
   reconstructed element `unspecified`. **Fallback when the docs are thin/absent** (the common case): recover the
   core from **entry-points + BOTH centrality lenses** (impact ∪ orchestration), tag even more `unspecified`, and
   **widen the reconciliation checkpoint** — ask the human more, since less intent was recorded. `research`
   returns a **bounded** gather — condensed findings + pointers, never whole file bodies (its charter): the point
   of the dispatch is that raw reading happens in *its* window, not here.
3. **Seed the nodes — without reading `graph.json` into context.** `graph.json` is machine-data: on a real repo
   it lists all N files (tens of thousands of tokens), and the seed selection is deterministic — computed, never
   judged. Get the bounded set mechanically:
   `python3 .claude/scripts/codemap/codemap.py --seed-list <K> --include <spec-core paths>` prints the
   **recovered spec-core ∪ top-K per centrality lens** with each node's frontmatter fields (path, type, lang,
   tier, both signals) ready to copy — read only that emission, never the graph itself; pick K so the set stays
   a bounded seed, not all N (the memory model is bounded by construction). Never centrality *alone* — the
   `--include` spec-core is what keeps the behavioural core in the set (the import graph's most-central file is
   not the app's core). Then write one node per selected file **per the `knowledge-node` schema
   (`schemas.md`)** — don't re-derive the format. **Run the extractive `purpose` pass in batched subagent
   windows, not here:** dispatch batches of the selected files to a subagent that returns a one-paragraph
   extractive `purpose` per file (from signatures/docstrings); write the nodes from those returns. Leave the
   edge `why` and `# Sessions` empty (`document` authors those on first real touch).
4. **Reconcile.** Route to a blocking `checkpoint` (kind=reconcile): present the reconstructed understanding —
   what the app does, its stack, its core flows — for the human to confirm or correct, and lock the load-bearing
   invariants they name (those flip `unspecified → locked`). Corrections rewrite the spec before the loop starts.
   Parking it sets the `handoff.md` ledger to `bootstrap: reconcile-parked` and **ends this context window by
   design**: tell the user the reconcile is waiting on the console, and end the session — the loop resumes on
   the verdict in a fresh window (the drain/runner picks it up). Never roll the bootstrap window into feature
   work.
5. Hand to the normal loop — in the fresh post-verdict session, which flips the ledger to `bootstrap: complete`.

## Rules
- **Never infer product intent from code alone** — structure is generated, intent comes from the existing docs
  + the human. The import graph's most-*central* file is not the app's *core*; keep the two apart.
- **Default the reconstructed spec to `unspecified`, not `provisional`** — provisional spawns a finalize-later
  item per element and floods the backlog on a large repo.
- **Never hand-edit `graph.json`** — regenerate it. `ingest` writes durable prose (the spec + node seeds), not
  structure.
- **Never read `graph.json` whole into context** — selection is `--seed-list`'s job (step 3). If you find
  yourself opening the graph to "pick the important files," stop and use the emission: the selection is a
  deterministic top-K, exactly the kind of computation that is never left to judgment.
- **Adopt an existing `docs/`**: write to known subpaths, never clobber; namespace ours on a name collision.
  Match existing subpaths **case-insensitively** — the committed `docs/` usually sits on a case-insensitive
  filesystem (Windows / WSL `/mnt/*` 9p / default macOS), where a workflow-owned `docs/architecture.md` and an
  adopted `docs/ARCHITECTURE.md` are the **same file**. On a case-variant collision, **adopt the existing file**
  (record its real path so `document` refreshes it in place) — never create a lowercase twin that silently
  overwrites it.

## Output
A populated `docs/knowledge/` (graph + seeded nodes) + a reconstructed, commitment-tagged `spec` + the
reconciliation `verdict`.

## Calls
`research` (read code + existing docs) · `checkpoint` (the reconciliation gate). *(`ingest` **seeds** the nodes
itself, per step 3 — the extractive `purpose` batches run in subagent windows; `document` authors the durable
`why` / `# Sessions` later, on first real touch — it is **not** called during ingest.)*

## Route
reconcile pass → the normal loop (`prioritize`). corrections → rewrite the spec, re-present.

---
name: ingest
description: Brownfield bootstrap — build the project knowledge base and reconstruct a spec from an existing codebase, then gate on a human reconciliation before the loop drives. Generates the structural code map, seeds behavioural-core intent from the existing CLAUDE.md/docs (never guessed from code), and hands the reconstructed understanding to a blocking checkpoint. Invoked by /start on an existing repo; routes to the normal loop once the human confirms.
---

# Ingest — reconstruct the knowledge base from existing code

Core principle: a code map tells you what depends on what; only the humans' prose tells you what the app is
*for*. Derive the structure mechanically; reconstruct intent from the existing docs — never guess intent from
code alone.

## When
`/start` on a brownfield repo (existing code), or a re-ingest after a large external change. Greenfield skips it.

## Inputs
- the existing codebase + any existing `CLAUDE.md` / `docs/` / README — the only source of behavioural intent.
- the `/start`-generated per-stack code-map extractor (`.workflow/codemap.sh`).

## Workflow
1. **Generate the structure.** Run the code-map extractor to build `docs/knowledge/graph.json`: typed
   import/call edges plus two centrality signals — *impact* (most-depended-upon → change blast-radius) and
   *orchestration* (composes many → where behaviour lives). Generated, never hand-authored.
2. **Seed the nodes.** One node per source file: fill the generated skeleton (path, type, edge targets, the two
   signals) and add a cheap extractive `purpose` (from signatures/docstrings) for the high-centrality set.
   Leave the durable `why` and `# Sessions` empty — `document` authors those on first real touch.
3. **Reconstruct the spec.** Dispatch `research` to read the existing `CLAUDE.md`/docs and the
   orchestration-central files, and reconstruct the `spec` (audience, purpose, screens, features, data model).
   Tag every reconstructed element `unspecified` — existing behaviour carries no recorded intent until a human
   confirms it.
4. **Reconcile.** Route to a blocking `checkpoint`: present the reconstructed understanding — what the app does,
   its stack, its core flows — for the human to confirm or correct, and lock the load-bearing invariants they
   name (those flip `unspecified → locked`). Corrections rewrite the spec before the loop starts.
5. Hand to the normal loop.

## Rules
- **Never infer product intent from code alone** — structure is generated, intent comes from the existing docs
  + the human. The import graph's most-*central* file is not the app's *core*; keep the two apart.
- **Default the reconstructed spec to `unspecified`, not `provisional`** — provisional spawns a finalize-later
  item per element and floods the backlog on a large repo.
- **Never hand-edit `graph.json`** — regenerate it. `ingest` writes durable prose (the spec + node seeds), not
  structure.
- **Adopt an existing `docs/`**: write to known subpaths, never clobber; namespace ours on a name collision.

## Output
A populated `docs/knowledge/` (graph + seeded nodes) + a reconstructed, commitment-tagged `spec` + the
reconciliation `verdict`.

## Calls
`research` (read code + existing docs) · `checkpoint` (the reconciliation gate). *(`ingest` **seeds** the nodes
itself, per step 2; `document` authors the durable `why` / `# Sessions` later, on first real touch — it is
**not** called during ingest.)*

## Route
reconcile pass → the normal loop (`prioritize`). corrections → rewrite the spec, re-present.

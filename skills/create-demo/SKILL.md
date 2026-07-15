---
name: create-demo
description: Build a throwaway, low-fidelity sandbox of a user-facing change so the user can approve the look and behaviour before it is really built. Use only when the sandbox gate passes — a user-owned, visible, under-determined change. Skip for backend work, refactors, or anything the spec already pins down.
---

# Create-demo — throwaway product-alignment sandbox

Core principle: a throwaway alignment artifact, surfaced as a checkpoint, that de-risks the **product**
question ("did we agree *what* to build?") — never the engineering question.

## When — build a demo only if ALL hold
1. an open product decision the **user** owns (system-discovered work never gets a demo);
2. it changes what the user sees or touches (not backend / refactor / internal);
3. the look/behaviour is **under-determined** — a new interaction pattern with no precedent, OR a competent
   build could ship two materially-different versions the user would care between.

Default = **no demo**. A genuine fence on (3) → a one-line yes/no to the user. The gate is evaluated per
work-item, not just at inception.

## Inputs
The visual/behavioural slice of the `spec`.

## Workflow
1. Generate a **minimal, non-integrated** sandbox of that slice — no backend, no real data — as a
   **build-free, self-contained static bundle** (see *Sandbox format*). Write it to
   **`.workflow/demos/<item-id>/`** (gitignored runtime) via atomic write (`os.replace`).
2. **Fidelity matches the question:** low-fi first (validate scope/flow), high-fi only when the look itself
   is the decision.
3. Surface it via `checkpoint` (kind=demo); the checkpoint record carries the demo path. The bus daemon
   serves the bundle under a **`sandbox`-directive CSP opaque origin** beside the verdict form — **demo = look,
   form = verdict** (the demo is read-only, no POST, no token).
4. On "change X": edit the **spec**, then **regenerate in place** — never hand-edit the demo. Repeat until
   approved, **capped at `config.demo.max_refine_rounds` (default 3) regenerations**. At the cap, **do not
   auto-proceed** — **escalate to a live `discuss` session**, carrying the refine history.

## Sandbox format
- **Self-contained, no external hosts, no `eval`** — every asset local; renders identically local and over the
  tunnel, offline. Deliverable: `index.html` + at most a couple of sibling local assets in the same dir.
- **Vanilla JS + `<template>` + hash routing** by default; **htm + preact vendored locally** (~10 KB, tagged
  templates — not JSX) when component/state ergonomics help — the same zero-build idiom as the console.
- **Banned:** CDN `<script src=https://…>` / `<link href=https://…>`, `@babel/standalone` or
  `type="text/babel"` JSX (needs `unsafe-eval`), npm/bundlers/`node_modules`.

## Rules
- **Throwaway** — never reused as the real scaffold. The bundle lives in gitignored `.workflow/demos/<item-id>/`
  and is **pruned on checkpoint-resolve** (the locked *spec* is the durable artifact, not the demo bytes).
- The spec state that produced the approved demo is what gets **locked**.
- Each `provisional` item in the approved spec spawns a `create-issue` (kind=debt) — tracked debt. **The
  sandbox gate (the `When` conditions) is evaluated once and owns which path runs**, so the debt is filed by
  **exactly one** of {`discuss` on the no-demo path · `create-demo` here on approval} — never both, never
  neither.

## Output
An approved demo → spec commitment levels recorded.

## Route
→ `planner:decompose` (inception path) · → `execute` (per-item demo approved).

## Calls
`checkpoint` (kind=demo) · `create-issue` (kind=debt — one per `provisional` item on the approval path).

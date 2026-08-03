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
2a. **Lint the bundle before you park it:** run `check_demo_bundle.py .workflow/demos/<item-id>/`. The serving
   isolation is a CSP the daemon enforces; the *self-contained* discipline (no external hosts, no `eval`,
   build-free) is **not** — a CDN reference renders fine locally and then blanks over the tunnel, silently. The
   lint is the mechanical floor: on a violation it names the file+line — **fix and regenerate**, never park a
   bundle that fails it.
3. Surface it via `checkpoint` (kind=demo); the checkpoint record carries the demo path. The bus daemon
   serves the bundle under a **`sandbox`-directive CSP opaque origin** beside the verdict form — **demo = look,
   form = verdict** (the demo is read-only, no POST, no token).
4. On "change X": **edit the `spec` FIRST, then regenerate the bundle FROM it** — never hand-edit the demo, and
   never regenerate without moving the spec (re-run the lint, step 2a). Repeat until approved, **capped at
   `config.demo.max_refine_rounds` (default 3) regenerations**, **counted plainly** (a circuit-breaker, not a
   fairness meter). At the cap, **do not auto-proceed** — **escalate to a live `discuss` session**, carrying the
   refine history.
   - **Spec first is not bookkeeping — it is the only durable copy.** A terminal `approve` **deletes the bundle**
     (step 3 of `checkpoint`'s demo route). A decision that lives only in the demo bytes is therefore destroyed at
     the exact moment it is approved, leaving a locked spec that never learned it. The human said yes to something
     that no longer exists anywhere.
   - **The ledger has a durable home:** `.workflow/demos/<item-id>/.refine.json` — inside the bundle dir (a dotfile,
     so the daemon never serves it), read-and-incremented on each regeneration. The refine loop spans park → resume
     → possibly a fresh relaunched session, and nothing accumulates in the orchestrator's context across those, so
     the count **cannot** live in memory or the parked record (deleted on resolve): it lives on disk beside the
     bundle, whose lifetime is exactly the refine loop. Its shape is declared in `shared/schemas.md`:
     `{ round: N, rounds: [{ round, spec_ref: { path, sha256 }, note? }] }` — each round naming the spec file it was
     regenerated **from** and that file's hash at the time.
   - **`check_demo_bundle.py` enforces both**, so neither is a promise: it refuses a round whose `spec_ref` is
     missing, whose latest hash does not match the spec on disk, or **whose hash is unchanged from the previous
     round** (a regeneration that did not move the spec), and it refuses a `round` over the cap. Run it before every
     park — the same call as step 2a.
   - **The ledger's summary outlives it.** Because the bundle is deleted on a terminal verdict, `checkpoint`'s demo
     route runs `check_demo_bundle.py --promote` first, folding `{item_id, approved_at, rounds, spec_ref}` into the
     committed `demo-approvals.json`. Nothing here changes — it is stated so the ledger does not read as a file whose
     evidence simply vanishes.

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
→ `planner:decompose` (inception path) · → `execute` (per-item demo approved) · → `discuss` (refine cap
exhausted → live realignment, carrying the refine history).

## Calls
`checkpoint` (kind=demo) · `create-issue` (kind=debt — one per `provisional` item on the approval path) ·
`discuss` (escalation when the refine cap `config.demo.max_refine_rounds` is hit).

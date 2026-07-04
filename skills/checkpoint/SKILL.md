---
name: checkpoint
description: Pause autonomous work to get a human verdict on the live app, then resume on the answer. Three kinds — demo (approve a sandbox), qa (test a built feature), setup (perform a manual external action). Blocks on the local bus; routes pass→continue, fail→debug.
---

# Checkpoint — the human-in-the-loop gate

Core principle: the human counterpart of `verify` — where verify checks artifacts, the checkpoint asks a
person to confirm the live app, the real "does it work" signal in MVP (autonomous testing is out of scope).

## Kinds
- **demo** — approve a `create-demo` sandbox.
- **qa** — test a built feature against its acceptance criteria.
- **setup** — perform a manual external action; calls `setup-guide` for precise steps.
- **reconcile** — confirm a brownfield-reconstructed `spec` before the build loop starts (from `ingest`).

## Inputs
A `checkpoint.request` `{ kind: demo|qa|setup|reconcile, what, expected, how?(←setup-guide), blocking: true }`.

## Workflow
1. Assemble the `request`.
2. Post it to the console and **block on the local bus** — an explicit wait step, not a hook exit-code
   trick.
3. Receive the `verdict` `{ pass, notes }`.

## Output
A `checkpoint.verdict` `{ pass, notes }`.

## Route
- **pass** → `document` / `commit` (kind=demo → lock the spec state instead; kind=reconcile → `prioritize`).
- **fail — by kind** (a rejection is not always a defect, so `debug` is not the universal sink):
  - **qa** → `debug` (behaviour ≠ intent) → `refine`.
  - **demo** → `create-demo` (refine the sandbox / spec — a product-fit rejection, not a bug).
  - **setup** → re-attempt the `checkpoint` (it re-guides via `setup-guide`) or escalate to the human (an
    external step can't be debugged).
  - **reconcile** → `ingest` (re-run) / `discuss`.

## Calls
`setup-guide` (kind=setup).

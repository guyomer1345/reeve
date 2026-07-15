---
name: checkpoint
description: Pause autonomous work to get a human verdict on the live app, then resume on the answer. Four kinds — demo (approve a sandbox), qa (test a built feature), setup (perform a manual external action), reconcile (confirm a brownfield-reconstructed spec). Blocks on the local bus; routes by kind on both pass and fail (see Route).
---

# Checkpoint — the human-in-the-loop gate

Core principle: the human counterpart of `verify` — where verify checks artifacts, the checkpoint asks a
person to confirm the live app, the real "does it work" signal in MVP (autonomous testing is out of scope).

## Kinds
Two boundary types. **Judgment** — the human gives an opinion:
- **demo** — approve a `create-demo` sandbox.
- **qa** — test a built feature against its acceptance criteria.
- **reconcile** — confirm a brownfield-reconstructed `spec` before the build loop starts (from `ingest`).

**Action** — the human does something the loop can't reach, then the loop *verifies* it worked:
- **setup** — perform a manual external action (create an account, add a key, configure a webhook); calls
  `setup-guide` for precise steps. Carries a `tasks[]` set (a lone setup is one element); the orchestrator coalesces a
  plan's foreseeable setups into one checkpoint at first-setup-contact.

## Inputs
A `checkpoint.request` `{ kind: demo|qa|setup|reconcile, what, expected, how?(←setup-guide), tasks?[], blocking: true }`.

## Workflow
1. Assemble the `request`.
2. Post it to the console and **block on the local bus** — an explicit wait step, not a hook exit-code
   trick. A **timeout re-surfaces + reminds; it never auto-proceeds.**
3. Receive the `verdict` `{ outcome: approve|changes|reject, notes, returns? }` (`pass` ≡ approve; setup carries a
   per-task outcome).

## Output
A `checkpoint.verdict` `{ outcome, notes, returns? }`.

## Route
Routing keys off `outcome`, **per kind** (a rejection is not always a defect, so `debug` is not the universal sink):
- **demo** — approve → lock the spec state · changes → `create-demo` (refine the sandbox/spec) · reject → `discuss`.
- **qa** — approve → `document`/`commit` · reject → `debug` (behaviour ≠ intent) → `refine` (`changes` ≡ reject here).
- **setup** — approve|changes → **verify the external precondition actually works** (probe the key/webhook) before
  proceeding; a failed probe re-guides via `setup-guide` (an external step can't be `debug`ged); reject → replan or
  escalate to the human. A `sensitive` `returns` value → the gitignored secret store, never logged.
- **reconcile** — approve → `prioritize` · else → `ingest` (re-run) / `discuss`.

## Calls
`setup-guide` (kind=setup).

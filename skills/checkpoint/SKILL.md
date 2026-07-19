---
name: checkpoint
description: Pause autonomous work to get a human verdict on the live app, then resume on the answer. Four kinds — demo (approve a sandbox), qa (test a built feature), setup (perform a manual external action), reconcile (confirm a brownfield-reconstructed spec). Parks the ticket durably and yields — never a live wait; routes by kind on both pass and fail (see Route).
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
1. Assemble the `request` + its correlation `token`.
2. **Park — never wait.** Write the `parked-ticket` record (token, kind, request, and a `deadline` stamped as
   *now + `config.checkpoint.deadline_hours`*), then **yield**. There is no blocking wait step and no hook
   exit-code trick: nothing in the loop can sit and wait for a person.
3. **Don't send the alert.** You do not notify anyone — writing the parked record *is* the signal. The always-alive
   console daemon watches for it and raises the alert (and the reminders, and the overdue escalation), because it
   is the only process still running when the loop is busy on another ticket, whole-parked, or dead.
4. The verdict arrives on the bus later and is consumed at a **scheduler-boundary drain** — not in this turn, and
   not by this skill. A **deadline re-surfaces + reminds; it never auto-proceeds** (a missing credential cannot be
   skipped).

## Output
A **parked ticket** (this turn). The `checkpoint.verdict` `{ outcome, notes, returns? }` (`pass` ≡ approve; setup
carries a per-task outcome) is what the drain later matches to the token and routes below.

## Route
Routing keys off `outcome`, **per kind** (a rejection is not always a defect, so `debug` is not the universal sink):
- **demo** — approve → lock the spec state · changes → `create-demo` (refine the sandbox/spec) · reject → `discuss`.
  On a **terminal** outcome (approve|reject) the sandbox has done its job, so **delete `.workflow/demos/<item-id>/`
  as part of applying the verdict** (the locked *spec* is the durable artifact, not the demo bytes; the retention
  audit is only the straggler backstop for a crash between resolve and delete). On **changes** the loop is still
  refining, so **keep** the bundle (and its `.refine.json` counter).
- **qa** — approve → `document`/`commit` · reject → `debug` (behaviour ≠ intent) → `refine` (`changes` ≡ reject here).
- **setup** — approve|changes → **verify the external precondition actually works** (probe the key/webhook) before
  proceeding; a failed probe re-guides via `setup-guide` (an external step can't be `debug`ged); reject → replan or
  escalate to the human. A `sensitive` `returns` value is written to **`.workflow/secrets/`** (gitignored, `0600` /
  restricted ACL, atomic write), **never logged and never echoed to `state.json`**; the inbox record that carried it
  is then **unlinked immediately** — the single case where the loop deletes an inbox file, so a credential's
  lifetime on disk outside the store is as short as possible. These are **live credentials, not memory**: the
  retention/`audit` prune never sweeps them.
- **reconcile** — approve → `prioritize` · else → `ingest` (re-run) / `discuss`.

## Calls
`setup-guide` (kind=setup).

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
**A `setup` `tasks[]` entry is `{ id, what, secrets?[] }`** — `secrets[]` naming the credential **key names** that
task will hand back (`POLAR_WEBHOOK_SECRET`), never values. Fill it whenever the task returns a credential: it is
what makes the console render a labelled input per key instead of asking a human to hand-compose a payload, and it
is where `config.json`'s `secrets_required[]` gets its names. A task you leave un-named still works — the human just
gets a generic entry — but the declared-loss report can then only say "the store is gone", never *which* keys.

## Workflow
1. Assemble the `request` + its correlation `token`.
2. **Park — never wait. `bus.py park` is the writer; you compose the record, it does the rest.**
   Pipe the `parked-ticket` record **per its schema (`schemas.md § parked-ticket`)** — don't re-derive the shape —
   to the runner on stdin, through a **quoted** heredoc — `<<'JSON'` disables every shell expansion, so a request
   body carrying quotes, `$`, backticks or newlines arrives byte-exact instead of being mangled by the shell:
   ```
   python3 .claude/scripts/bus.py park --workflow-dir .workflow <<'JSON'
   { …the parked-ticket record… }
   JSON
   ```
   You compose the **judgment**: `{ ticket_id, token, loop_position, checkpoint: {kind, request, demo_id?},
   predicted_outcome }` (a pre-build `demo`/`reconcile` park carries no `worktree`/`branch`). The runner does the
   **arithmetic** — it resolves the runtime root, stamps `deadline` as *now + `config.checkpoint.deadline_hours`*
   and `opened_at`, writes the record atomically at `0600`, and projects the `<!-- parked:begin -->` mirror block
   onto `handoff.md`. **Do not write `parked/<id>.json` yourself and do not hand-write the mirror**: the runtime
   root has exactly one owner and the mirror is generated, so a second copy of either rule is a copy that drifts.
   A refused park exits non-zero and says why — fix the record, don't route around it.
   Then **yield**. There is no blocking wait step and no hook exit-code trick: nothing in the loop can sit and wait
   for a person.
3. **Don't send the alert.** You do not notify anyone — writing the parked record *is* the signal. The always-alive
   console daemon watches for it and raises the alert (and the reminders, and the overdue escalation), because it
   is the only process still running when the loop is busy on another ticket, whole-parked, or dead.
4. The verdict arrives on the bus later and is consumed at a **scheduler-boundary drain** — not in this turn, and
   not by this skill. A **deadline re-surfaces + reminds; it never auto-proceeds** (a missing credential cannot be
   skipped).

## Output
A **parked ticket** (this turn). The `checkpoint.verdict` `{ outcome, notes, returns? }` (`pass` ≡ approve; a setup
reply carries `tasks[] {id, outcome, returns?}` instead of the single `outcome`) is what the drain later matches to
the token and routes below. **`returns` is a name-keyed map — `{ "<KEY_NAME>": { value } }`, and `returns` MEANS
credential** (there is no `sensitive` marker: protection comes from the field, not from a flag a composer must
remember). A non-credential value the task hands back goes in **`artifacts`** — same shape, never redacted, never
stored. The key *is* the credential name, task identity already lives at `tasks[].id`, and the bus `400`s any other
shape.
You never compose a verdict yourself: the human answers it in the console, and it arrives on the bus.

## Route
Routing keys off `outcome`, **per kind** (a rejection is not always a defect, so `debug` is not the universal sink):
- **demo** — approve → lock the spec state · changes → `create-demo` (refine the **spec**, then the sandbox from it)
  · reject → `discuss`.
  On a **terminal** outcome (approve|reject) the sandbox has done its job, so **delete `.workflow/demos/<item-id>/`
  as part of applying the verdict** (the locked *spec* is the durable artifact, not the demo bytes; the retention
  audit is only the straggler backstop for a crash between resolve and delete). On **changes** the loop is still
  refining, so **keep** the bundle (and its `.refine.json` ledger).
  - **Before you delete anything on approve, lock the spec `.refine.json` names.** Read the ledger's last
    `spec_ref.path` and confirm the spec on disk actually carries what was approved. The delete is what makes this
    ordering load-bearing: a decision that reached only the bundle dies with it, and the lock then records a spec
    the human never agreed to. `check_demo_bundle.py` refuses a refine round that did not move the spec, so this
    should already hold — treat a mismatch here as evidence a round bypassed the lint, and fold the decision in
    **before** locking rather than approving over it.
- **qa** — approve → `document`/`commit` · reject → `debug` (behaviour ≠ intent) → `refine` (`changes` ≡ reject here).
- **setup** — approve|changes → **verify the external precondition actually works** (probe the key/webhook) before
  proceeding; a failed probe re-guides via `setup-guide` (an external step can't be `debug`ged); reject → replan or
  escalate to the human. Every `returns` value is written to **`.workflow/secrets/`** (gitignored, `0600` /
  restricted ACL, atomic write), **never logged and never echoed to `state.json`**; the inbox record that carried it
  is then **unlinked immediately** — the single case where the loop deletes an inbox file, so a credential's
  lifetime on disk outside the store is as short as possible. These are **live credentials, not memory**: the
  retention/`audit` prune never sweeps them.
  **Declare the key name at elicitation.** When a setup task asks for a credential, name it in that task's
  `secrets[]` **and** add it to `config.json`'s `secrets_required[]` (idempotent — never a duplicate) — the task's
  `secrets[]` is the source, `secrets_required[]` the project-wide running projection of every such ask, and the
  console's labelled input is keyed off the former. **Names only, never values**: `config.json`
  is committed, and a value there is the exact leak the store exists to prevent. This is what makes absence
  *provable* — an empty `secrets/` is otherwise indistinguishable from a project that needs no credentials, so a
  machine move could only report "the store is gone, work out what was in it". `/rebind` diffs the declared set
  against the store and itemizes what is missing. It is **early warning, not a gate**: point-of-use fail-closed
  (the thing that needs the key failing loudly when it is absent) stays the floor.
- **reconcile** — approve → `prioritize` · else → `ingest` (re-run) / `discuss`.

## Calls
`setup-guide` (kind=setup).

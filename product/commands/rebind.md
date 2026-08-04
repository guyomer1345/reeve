---
description: Bind this project's runtime half to THIS machine. Run it when the project has moved to another machine, or the machine it was on was rebuilt — the symptom is a tool refusing to start because the runtime root does not exist. Repairs the pointer, recovers a surviving tree where one exists, and itemizes what did not survive.
argument-hint: "(no arguments)"
---

# /rebind — bind the runtime half to this machine

`/start` initialises a project **once**. `/update` moves it onto a new package version, **per release**.
`/rebind` is the third sibling on a third axis: **this machine is not the machine that installed** — per
machine move. Three orthogonal questions, three commands.

**Why the project breaks at all.** A workflow project spans two halves. The **durable** half — `handoff.md`,
`backlog.md`, `config.json`, `items/`, `docs/`, the package under `.claude/` — is committed, holds no absolute
paths, and travels for free. The **runtime** half — `state.json`, the bus record and locks, `parked/`, `inbox/`,
`outbox/`, `secrets/`, the remote token — is machine-local and deliberately gitignored, and it lives at an
absolute path recorded in `.workflow/runtime.json`. That pointer is gitignored *on purpose*: committing an
absolute path would hand every clone a **wrong** root, which is worse than none. So a machine move leaves a
project that is fully initialised and whose entire runtime tree is unreachable.

**`/rebind` is interactive-only**, like `/start` and `/update`, and for one more reason than they have: it is a
decision **with loss**, so it needs a human. Running it interactively also re-grants the workspace trust that
`~/.claude.json` records per-machine — which a moved project silently lost, and which `claude -p` and the
relaunch runner both stall on. That closes itself; there is nothing to do about it but run this here.

## 0. Look, before touching anything
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/rebind.py" check --project-root "${CLAUDE_PROJECT_DIR}"
```
Read-only and non-interactive: it classifies, prints what it *would* do, and writes nothing.

**Run it from the plugin root, not the project's `.claude/scripts/`** — the same deliberate exception `/update`
makes, for a stronger reason. `/start`'s never-invoke-in-place rule exists because `${CLAUDE_PLUGIN_ROOT}` is
replaced on every plugin update, which is a hazard for a long-lived reference; this is a one-shot, stateless read
inside an interactive command, so it is not exposed to that. And the project copy is exactly what a rebind cannot
rely on: **the projects that most need this command are the ones whose `.claude/` predates it.** A project
stranded on an old version would otherwise be told to `/update` first — inverting the order that makes the update
diagnosable at all.

Show the human the report before applying. What the classification means:

| | What it found | What `apply` does |
|---|---|---|
| **`HEALTHY`** | already bound to this machine | nothing — `apply` is a no-op |
| **`RE-POINT`** | a surviving runtime tree | **lossless**: fixes the pointer, moves no data |
| **`ADOPT-IN-PLACE`** | no pointer, runtime files under `.workflow/` on a filesystem that does not honour `0600` | relocates the tree off that mount and writes the pointer |
| **`RE-CREATE`** | nothing survived | rebuilds the shape; itemizes the real losses |
| **`NOT-STARTED`** | no `.workflow/` | wrong command — this is `/start` |

The `RE-POINT` probe order is worth reading out loud when it fires, because the second rule is the one that
usually saves the day: the pointer's literal path → **the same path with this machine's `$HOME` swapped in** →
the canonical derived location. A rebuild that renames the user (`/home/guy` → `/home/guyo`) leaves the tree
completely intact and unreachable only by its prefix.

## 1. Apply
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/rebind.py" apply --project-root "${CLAUDE_PROJECT_DIR}"
```
It never overwrites an existing runtime file — it creates what is absent and repoints what is dead — so it is
safe to re-run and a healthy install is a fixed point. **It can take minutes**: after the repair it runs the
project's real mechanical gate once, to answer whether this machine can commit at all (step 6 below). `--no-probe`
skips that if you already know the answer. Exit `2` means it refused: either there is no
`.workflow/` (wrong command), or the derived location is itself on a filesystem that does not honour file modes,
in which case do **not** work around it by creating the tree yourself. That refusal is the whole point — landing
`secrets/` and the capability token where every user on the machine can read them is the exposure the relocation
exists to prevent. Point `XDG_STATE_HOME` at a local filesystem and re-run.

## 2. The judgment half — this is your job, not the runner's
The runner does the arithmetic. What the loss *means* needs a conversation.

1. **Reconcile the loop position.** On `RE-CREATE` the runner writes a `state.json` that says, in its own
   `note`, that the position was not recovered: `status: idle`, no `current_item`. That is deliberate — a
   confidently wrong `current_item` is worse than an admitted gap. Read `.workflow/handoff.md` and
   `git log <base_sha>..HEAD`, work out where the loop actually was, and **rewrite `state.json` yourself**.
   Do this before anything resumes: an `idle` state lets `prioritize` re-pick work the handoff says is parked.
2. **Re-open every parked checkpoint the handoff names.** `parked/<id>.json` bodies are gone. `handoff.md`'s
   `<!-- parked:begin -->` block is the only surviving trace (on an older install, the hand-written `## Parked`
   prose), and by design it carries the id, kind, summary and opened-at but **not** the checkpoint's own question,
   deadline, or any answer already returned — a body is exactly what must not be committed. Re-raise each one with
   `bus.py park` (a **fresh** `token`; the old one died with the tree) and tell the human what it is now missing.
3. **Re-elicit the secrets.** If `config.json` declares `secrets_required[]`, the runner has already diffed it
   against the store and filed the missing keys **by name** — work that list, and re-elicit each one through a
   `setup` checkpoint (never by having the human paste a value into a file the loop reads). If the project declares
   nothing, that is *"we cannot tell"*, not *"nothing is missing"*: absence is undetectable by inspection — an
   empty `secrets/` is indistinguishable from a project that needs none — so fall back to walking the handoff and
   the item history for setup checkpoints that handed over a credential, and **add the names to
   `secrets_required[]` as you go** so the next move is itemized. Point-of-use failure is the only other signal,
   and it fires at the worst moment.
   If the filed loss also reports entries that **could not be read for credential names**, do not treat those as
   gone: the store predates the declared `returns` shape and may still hold live keys. Confirm at point of use
   before re-eliciting — sending a human to replace a credential they already have is how this report gets ignored.
4. **Say what will never fire.** Anything that was queued in `outbox/` (a push, a `gh issue create`) is gone.
   Nothing ran twice; the queue simply emptied. Name what the backlog still expects.
5. **Check the bootstrap ledger.** If `.workflow/handoff.md` has no `bootstrap:` line at all, this install
   predates the ledger. A demonstrably finished project with no line reads to `/start` §0 as
   *bootstrap-incomplete*, which would send it to re-ingest the whole codebase. If the project's history shows
   the bootstrap plainly finished (a reconcile-approved ingest, a populated `docs/knowledge/`, items that have
   run the loop), write `bootstrap: complete` into `handoff.md` now.
6. **Read the bindability line, and do not talk past it.** After the repair the runner runs
   `bash .workflow/checks.sh --check` from the repo root — the exact command, cwd and shell the pre-commit hook
   uses — and reports `bindable: YES|NO`. On **NO** the project is correctly bound and *still cannot commit*: the
   gate is the loop's floor and the hook blocks on it. That is the class the portability audit never enumerated —
   the durable half is portable, but the toolchain `.workflow/checks.env` names is machine-local and correctly did
   not travel — the file itself is committed and arrived fine; the tools it names are what is missing. **The probe reports an observable and does not diagnose it**, so read the tail it
   prints: commands that cannot *run* (not found, no such module) mean the stack is missing on this machine;
   commands that run and *fail* mean something is genuinely red. Say which one you think it is and why, and
   **say plainly if you cannot fix it here** — on a mount that cannot `chmod` (Windows-interop, some network
   mounts) an installer will fail on package bins, so the install has to happen on the side of the machine that
   owns the toolchain, by a human. That is a blockage class the loop provably cannot clear itself; naming it is
   the whole job. The loss is already filed, so do not re-file it — route it.
7. **Re-assert the git backstop.** `.git/hooks/` is not part of the repository, so it never travels — a moved or
   re-cloned project arrives with the mechanical gate silently missing from every out-of-loop commit. Run
   `python3 .claude/hooks/session_start.py --assert-hook`. It installs the hook when absent, is silent when it is
   already the package's, and **never clobbers a foreign one** (it warns instead). Surface whatever it prints.
8. **Start the console.** `bus.json`, `bus.lock` and `orchestrator.lock` are liveness artifacts, not state —
   the runner deliberately does not fabricate them, because a stale bus record advertises a dead daemon and a
   stale lock blocks a live orchestrator. Just start it:
   `python3 .claude/scripts/bus.py ensure --workflow-dir .workflow`. If this project uses the remote socket,
   the token is re-minted on that start: the phone must be **re-paired** and any tunnel re-pointed, because the
   machine — and therefore the URL — changed.

## 3. Report and commit
Losses are already filed into `.workflow/backlog.md` as typed `issue` entries by the runner. That is on purpose:
a printed report is a durability that depends on a human remembering, and `backlog.md` is the committed live
OPEN queue the loop already reads. They are local issues with no `github_ref`, so each one closes on its
backlog done-flip and `prioritize` collects it — the backlog does not accumulate machine-move sediment.

Commit `backlog.md` (and `handoff.md` if you touched it) with a message naming the move. The runtime paths are
gitignored and stay out of it, as they must — that is the property this whole command exists to preserve.

Then tell the human to `/clear` and resume from `handoff.md` in a fresh session.

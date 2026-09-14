# Shared Artifact Schemas — the runtime substrate

A sibling of [`schemas.md`](schemas.md). That file owns the artifacts the **loop** produces and consumes — a
plan, a changelog, a verdict, a parked ticket. This file owns the records the package's own **processes** own:
written and read by `/start`, `/update`, `rebind.py`, the bus daemon and the `SessionStart` hook, and never
authored or consumed by a skill as work. **Nothing here is meant to be hand-edited** — the knobs an operator
does turn live in [`schemas-config.md`](schemas-config.md), which was split out of this file for exactly that
reason. Same conventions as its siblings — on-disk paths are fixed, and each schema notes its **write-mode** and
**tier** (see `shared/memory-model.md`).

*Split out of `schemas.md` when that file crossed the 25 000-token Read ceiling, per the split-and-pointer
convention in `shared/memory-model.md`. A reference of the form `schemas.md § <name>` for any section below
resolves here — the name is the anchor, and the parts are one schema.*

## dispatch_return.py  · a `PostToolUse(Agent|Task)` detector, run by the harness after every dispatch · *writes nothing; its whole output is a warning in the caller's transcript*
The mechanical half of `schemas.md § dispatch-return`, which owns the contract itself and is where the reasoning
lives. **The contract is advisory; this is a detector, not its enforcement** — and the distance between those two
words is the whole reason this section exists rather than a sentence claiming the rule is gated.

- **It cannot block, and does not pretend to.** The harness runs `PostToolUse` *after* the tool returns, so there
  is nothing left to prevent. The available act — and it is worth doing — is to tell the caller, in its own
  transcript at the moment it happens, not to carry the payload forward, and to leave a mark rather than have the
  breach absorbed silently. It exits 2 with the reason on stderr, which the harness shows to the model as a
  warning and which blocks nothing.
- **It is an ABSURDITY CEILING, not a budget,** and it is measured in **characters** because a shipped hook cannot
  assume a tokenizer. No distribution of return *sizes* has ever been measured here; what has been measured is
  that a dispatched node's median contribution to the caller's window is 0.0k against an inline node's 12.0k — so
  returns are already small at the median, and a threshold placed near one would strangle the normal case to catch
  nothing. The ceiling sits where the only plausible way to reach it is a file body, a diff, or raw tool output
  pasted back. The number lives in the hook, its one owner; if it ever fires on a legitimate return the honest
  fix is to measure and move it, not to soften the wording.
- **Two silences are deliberate.** A dispatch to anything that is not one of the five package agents is ignored —
  the contract is this package's, and warning about an ordinary search dispatch would train the caller to skip
  the warning that matters. (The complementary PreToolUse rule, *a loop node never goes to a general worker*, is
  `dispatch_guard.py`'s.) And any `tool_response` whose text it cannot positively extract is **not measured**: the
  documented schema does not pin down that shape for a subagent dispatch, so an unknown shape must read as
  silence. A detector that guesses a size emits a warning its reader cannot falsify.
- **The gap, stated rather than papered over.** The expensive half of the contract — what a worker *read, printed
  or redirected inside its own window*, the half that costs ~4.1× — is invisible from outside the worker and is
  not checkable by anything. This hook watches returns only. A reader who takes "there is a hook" to mean the
  discipline is covered has been misled, which is why the limit is written here next to the mechanism.

## runtime.json  · written by `rebind.py` (`bind` at `/start` step 3, `apply` at `/rebind`), read by every process that touches a runtime path · *`.workflow/runtime.json`; RUNTIME, gitignored, atomic write; deliberately NOT on a native filesystem — it is the pointer TO it*
- `{ runtime_root }` — an absolute path. The workflow tree spans **two filesystems** whenever the repo lives on a
  mount whose file-mode or `rename` guarantees are weak: the atomicity- and mode-sensitive runtime paths are
  relocated to a native filesystem, while committed artifacts stay in the repo by construction. This pointer is what
  makes that relocation **findable** — without it nothing could locate the relocated half, since the daemon's own
  discovery record lives inside it.
- **Absent ⇒ no relocation happened ⇒ the workflow dir IS the runtime root.** That is the common case and costs zero
  indirection; the file exists only on a relocated install.
- **Never committed, never pinned.** The path is machine-specific, so committing it would hand another machine a
  wrong root; and it cannot itself be relocated, since it is the thing that says where the relocation went — it must
  sit at a fixed, known spot on the repo mount.
- A pointer naming a **missing** root is a hard error, never a fallback to the repo mount: falling back silently
  would land the capability token and the inbox on the very filesystem the relocation exists to avoid. The error
  **names `/rebind`** — a detector that does not route is a dead end, since the operator on a new machine has no
  other way to learn the cure exists.
- **The root's location is DERIVED, never chosen** — `bus.runtime_root_for(project_path)` →
  `$XDG_STATE_HOME/reeve/<slug>-<sha256(abspath)[:8]>`. It used to be prose, which meant a
  model picked it, and two projects with the same basename in different parents derived the *same* root and
  cross-bound two live installs. The hash kills the collision; the determinism is also what lets `/rebind` guess a
  canonical location from the project path alone when the pointer is lost.
- **Absent pointer + a mount that does not honour file modes is ALSO a hard error** (the *silent* mis-bind). A
  fresh clone under a Windows-interop or network mount has no pointer — it is gitignored by design — so "absent ⇒
  no relocation" would hand back the repo mount and land the capability token and `secrets/` on a `0600`-ignoring
  filesystem, saying nothing. The path resolver, not `/start`'s prose, owns *may this filesystem hold the runtime
  tree*; the probe **measures** (`0600` create, then `stat`) rather than sniffing a mount type, and its third
  value — *undecidable* — never stops, because a false positive would break a working install.

## .workflow-runtime  · written by `rebind.py`, verified by `bus.Paths` on every resolution · *inside the runtime root; RUNTIME, never committed (it lives with the tree it identifies); atomic write, `0600`*
The runtime root's **identity**. Present only on a **relocated** root — inside `.workflow/` the binding is true by
construction, so there is nothing to verify and no gitignore entry to earn.
- `{ project_path, bound_at, bound_host }` — the absolute path of the project this tree belongs to, when it was
  bound, and to which host.
- **Why it exists:** `isdir()` is not identity. A restored backup, a second WSL distro, or any stray directory at
  the pointed path binds clean and starts writing one project's state into another's. `Paths` therefore fails on
  **mismatch**, not merely on absence.
- **Tolerant read / strict write.** An absent stamp is an install made before stamps existed — legacy, not wrong:
  it is adopted **and
  then stamped**, so the next resolution is a real check. That is what let the mechanism land without breaking a
  single live install. A corrupt or unreadable stamp reads as absent (it is evidence of nothing), and a failed
  stamp write never breaks a resolution that already worked.

## install-set.json  · written by `/start` step 7 and rewritten by every `/update`, read by `/update` · *`.workflow/install-set.json`; **committed** (its paths are repo-relative and machine-independent, unlike `runtime.json`); atomic write; produced only by `update_reconcile.py record|apply` — never hand-authored*
The **install ledger**: what this package wrote into this project, and the hash it wrote.
- `{ plugin, workflow_version, files: { "<repo-relative dest>": "<sha256>" } }` — one entry per file the
  install actually landed (manifest `install[]` directory entries expanded **file-by-file**, so a retired
  file *inside* an installed directory is detectable too), plus the pseudo-entry **`CLAUDE.md#brief`**
  holding the hash of the orchestrator brief's managed-block **body**.
- **It exists to make two questions answerable that are otherwise unanswerable at update time:**
  *is this file ours?* (recorded ⇒ ours; unrecorded ⇒ the human's, never touched) and *is it pristine?*
  (hash matches ⇒ safe to overwrite; differs ⇒ hand-edited, surfaced — and for the two human-facing files
  it **blocks** the overwrite until confirmed). A **proven orphan** is `recorded-old − new-manifest`, which is
  the only removal `/update` may make.
- **Absent ⇒ unknown-old install** (predates the ledger; an absent `config.workflow_version` says the same).
  Then nothing is provable: everything is still refreshed, nothing is ever removed, and the confirm-required
  files need explicit confirmation. The update writes the ledger, so the *next* one is precise.
- Rewritten whole on every `apply` — it describes the install as it is **now**, never a history. Version
  history is git's job.

## orchestrator-brief managed block  · written by `/start` step 4 (both modes), replaced by `/update` · *inside the target's root `CLAUDE.md`*
The orchestrator brief is delimited by two **byte-stable** markers:
```
<!-- reeve:brief:begin -->
<!-- managed block: /update replaces everything between these markers. Put project notes OUTSIDE them. -->
…the filled orchestrator-CLAUDE.md template…
<!-- reeve:brief:end -->
```
- **Both modes wrap.** Greenfield writes a fresh `CLAUDE.md` and still wraps: the file accumulates the
  human's own notes over the project's life exactly as a brownfield one does, and the markers are what let a
  later `/update` refresh the brief while leaving those notes untouched. One shape, both modes, so `/update`
  has exactly one thing to find.
- **These strings are a cross-version compatibility contract** — an install stamped by *any* version must be
  findable by *every* later one. Changing them orphans every existing install's brief, so they never change.
- **No block found ⇒ flag only.** An install predating the markers is reported, never guessed at: `/update`
  will not infer where a brief starts and ends inside a file it does not own.

## statusline.delegate  · written by `/start` when it finds a pre-existing user statusline, read by the shipped statusline every render · *`.workflow/statusline.delegate`; RUNTIME, gitignored, plain text; lives on the repo mount (no atomicity/mode sensitivity — it is a command string, not a runtime path)*
A single line: the **shell command of a statusline that already existed** when `/start` ran (the
user's global `~/.claude/settings.json` `statusLine.command`, or a brownfield project's prior one).
The shipped statusline **composes, never clobbers**: it runs this delegate with the same status JSON
on stdin, takes its stdout as the base line, and appends the budget banner only when over
`config.context.warn_pct`. Absent ⇒ no pre-existing statusline ⇒ the shipped statusline renders its
own minimal `model · dir · ctx N%` base. **Gitignored and machine-specific** (the delegate command
names paths that exist only on the machine that ran `/start`); a clone re-derives it on its own
`/start`, so committing it would hand another machine a wrong command.

## bus.lock  · created and held by the bus daemon for its process lifetime · *`.workflow/bus.lock`; RUNTIME, gitignored, created-never-replaced; kept on a native filesystem*
The daemon's **singleton election**. Holding it *is* the liveness claim: the kernel releases it when the holder dies,
which is what makes it immune to the PID reuse a pidfile would suffer. Contains the holder's pid for humans; nothing
reads that value as authority.
- **It is a separate file from `bus.json`, and that is load-bearing, not tidy.** `bus.json` is republished by atomic
  rename, and a rename **swaps the inode out from under a held lock** — the next daemon opens the *new* inode, finds
  it unlocked, and starts. Two daemons, no error. (Measured true on ext4 *and* on the WSL 9p mount; a fixture test
  pins it, so a platform change is a loud failure rather than a silent regression.) A lock file is therefore only
  ever created and written in place — **never renamed over**.
- Liveness = **the held lock plus a token'd `/health`**: the lock proves *someone* is alive, the health check proves
  it is ours. A free lock means any `bus.json` is stale, whatever pid it names.

## orchestrator.lock  · held by an orchestrator launch for its session lifetime, probed by the daemon's relaunch-runner · *`.workflow/orchestrator.lock`; RUNTIME, gitignored, created-never-replaced; kept on a native filesystem*
The **single-orchestrator liveness marker** the relaunch-runner checks before it spawns, so it never launches a
duplicate alongside a live orchestrator (the single-orchestrator run-constraint's honest residual would become the
runner's own defect). **Distinct from `bus.lock`** — that is the *daemon's* election; this is the *orchestrator's* liveness.
- **Both launch paths hold it via an `flock`.** A human starts the orchestrator through the shipped **`loop.sh`**
  launcher (`exec flock -n .workflow/orchestrator.lock claude …`), which holds the lock across the `exec` for the
  session's whole life; a **runner-launched `claude -p`** is spawned as `flock -n .workflow/orchestrator.lock claude -p …`,
  so it holds it too. The runner probes the lock (a non-blocking `flock`); **held ⇒ someone is driving ⇒ back off**.
- **The kernel drops it on death**, so it never goes stale the way a pidfile would — the same property that makes
  `bus.lock` trustworthy. A `flock -n` probe is the whole liveness test; a free lock means no orchestrator is live.
- **The runner's own spawn goes through `flock -n`,** so even if a human starts in the probe→spawn window the launch
  aborts rather than doubling — the latch is the lock, not a flag. **Why not a `/proc` scan for a live `claude`:**
  measured unsound — Claude Code runs a constellation of claude-named helper processes (`claude daemon`, `bg-pty-host`,
  `bg-spare`, a versioned session process) sharing the repo cwd, so it cannot separate a driving orchestrator from a
  helper or a casual session.
- **The bare-`claude` bypass is the one operator residual** (same footing as the single-orchestrator run-constraint): a human who enables `config.runner` but
  starts bare `claude` instead of `loop.sh` is invisible to the runner, which may then spawn a duplicate. Documented,
  not fenced — the same footing as the single-orchestrator run-constraint itself.

## wave-build slot  · taken by `checks.sh --check` around the repo-wide stack gate · *`<git-common-dir>/reeve-wave-build.lock` + `reeve-wave-build.json`; RUNTIME, uncommittable by construction; lock = `flock`, marker = atomic write. Rationale and fail-direction: `scripts/wave_build.py`*
**"Build once per wave", mechanically.** A fanned-out wave puts N workers in N worktrees at the gate a commit
hangs on, whose stack half runs **repo-wide** over one shared cache, port set and fixture set. The slot makes
that gate **exclusive** (one at a time across every worktree — the common git dir is the one path they all
resolve to identically) and **deduplicated** (never re-run for a tree state this same wave already passed).
**The line:** a worker testing **its own** work in its own worktree is not this and is never blocked by it.
- **`.lock`** — `flock`'d around the stack commands only. **The kernel drops it on death**, so a dead worker
  cannot wedge the wave: `orchestrator.lock`'s property, reused rather than a second locking discipline.
- **`.json`** — `{ wave, passed: { <fingerprint>: { at, pid } } }`. `wave` is `state.json`'s id, never a second
  notion of it; a different one drops the memo whole. The fingerprint is `git ls-files -s` plus a hash of each
  worktree/untracked delta. **Only a PASS is written**, and every unknown (no wave, no lock, an unreadable
  marker) **falls toward building** — so a wave of one builds every time, exactly as before.

## bus.json  · written by the bus daemon at boot, read by `/start` + the browser · *`.workflow/bus.json`; RUNTIME, gitignored, atomic write; kept on a native filesystem*
- `{ pid, port, token, started_at, remote_port?, remote_token? }` — the daemon's discovery + auth record. `port` =
  a dynamic **loopback** port (bind `127.0.0.1:0`, read back — the port is **not** a secret). `token` = the CSPRNG
  **capability token** required as a header on every request (authentication; **distinct** from a checkpoint
  correlation `token`). `/start` health-checks `port`+`token` to **adopt-or-spawn** the daemon; the daemon holds the
  `bus.lock` (above) for its lifetime as the liveness authority — **never a lock on this file**, which it renames.
- **The token file is created 0600 and then `stat`'d to confirm it.** A mode is a request, not a guarantee: on the
  WSL repo mount a 0600 create silently returns 0777, so the token would be readable by other users on the machine
  with nothing reporting a failure. This is the primary reason this path is pinned. If the achieved mode is looser
  than asked, the daemon **surfaces it to the human** rather than pretending the file is protected.
- `remote_port` / `remote_token` — present **only** when `config.remote` declares an identity transport. This is
  the **reduced remote surface** (reads · opinion verdicts · the static demo); the operator points their
  `cloudflared` / `tailscale serve` at `remote_port`, and **never** at `port` — `port` is the full-surface loopback
  socket (outward `release`, returns-bearing `setup` verdicts) that must never be fronted. **Both are echoed here for
  discovery but SOURCED from durable state, not minted per boot:** `remote_port` is `config.remote.port`
  (fixed), and `remote_token` is read from the persisted `.workflow/remote_token` file (below). This is the load-
  bearing difference from the loopback `port`/`token`, which are freshly minted each boot — a phone paired once must
  keep working across restarts. `remote_token` is a **separate** CSPRNG secret, never the loopback `token`, paired to
  the phone by a copy-paste link (a QR is a scoped fast-follow) whose URL fragment never leaves the browser.

## remote_token  · minted once by the bus daemon on first remote-enabled boot, read on every boot thereafter · *`.workflow/remote_token`; RUNTIME, gitignored, atomic `0600`-create + `stat`-verify; kept on a native filesystem*
- A single CSPRNG line — the **stable second factor** gating Socket A, over the transport identity. **Distinct from
  the loopback `token`** in `bus.json` (the loopback token is never reused remotely), and unlike it
  **persisted, not per-boot**: a phone pairs against this token once and the operator points a tunnel once, so a
  token reminted each boot would go stale on **every restart** — routine on WSL, the platform the away channel most
  needs to survive. Minted only on first use; every later boot reuses the file. `bus.json` echoes its current value
  for discovery, but this file is the source of truth.
- **Never served on the surface it gates.** The remote page carries no token in its HTML — it would hand the surface
  to anyone past the transport in one GET. The token reaches the phone only through the pairing fragment (loopback
  `/api/pairing` → a copy-paste link), which never leaves the browser.
- **Same atomic-`0600`-create + `stat`-verify discipline as the loopback token and the secret store** (a mount that
  ignores mode returns `0777` silently). **Deleting the file re-pairs everyone** — the only rotation path, and a
  deliberately visible, owner-level act.

## context.json  · published by `statusline.py` every turn, read by `context_band.py` · *`.workflow/context.json`; RUNTIME, gitignored, atomic write (temp + `os.replace`); kept on a native filesystem*
- `{ used, window, mono }` — absolute tokens and the monotonic clock at publication. **Absolute, not a
  percentage**, because the consumer's unit is *work*: a 200k and a 1M window at the same fraction full leave
  5 and 25 nodes of runway, which are not the same situation.
**This file is the one crossing of a real wall.** The statusline is the **only** surface Claude Code exposes a
running token count to — hooks and the model receive none. So the statusline can **see** and not act, while the
loop can **act** and not see. Before this, nothing crossed: the banner went to a human's eyes and a human typed
`/dispatch`, which is a channel with no machine end at all.
**Read through `context_band.py`, never directly.** A reading older than its staleness window resolves to
*absent* — it describes a session that has probably already ended, and a verdict about a dead session's window is
worse than no verdict.
**Published best-effort and never fatally:** it is written from inside the status line, and a status line that
raises blanks itself. A lost reading degrades the band to `unknown`, which is the safe direction — `unknown` is
never `hold`, because a wrong `hold` tells a session to keep filling a window it should be leaving.

## spec-approval.json  · written by `checkpoint` on an approve that crosses the autonomy floor, read by `checks.sh --check` · *`.workflow/spec-approval.json`; **COMMITTED** — it must ride the commit it authorises, the same law as `commit-receipt`; atomic write; rewrite-in-place (one live approval, history in git)*
- `{ spec_sha256, ticket_id, spec_path }` — the digest of `docs/spec.md` **as approved**.
**There is deliberately NO `token` field, and the absence is load-bearing.** This file is committed, and
`guard.sh`'s secret scan blocks any staged `token:` followed by 12+ key-shaped characters — a checkpoint ticket
string is comfortably longer. A receipt carrying one **could never be staged**, which would leave two package
rules with no reachable compliant state (found on a live drive, not reasoned about). The fix sits here rather
than in the scan: a false positive on a token-shaped field is far cheaper than a missed credential, so the scan
does not move. `ticket_id` already carries the provenance, and the correlation token is the *drain's* key —
meaningless once the verdict has been applied.
**It is what turns the autonomy floor from a consultation into an enforcement.** The floor is run at decision
time by the orchestrator, which means a loop that does not run it is unchecked — and that is exactly the case the
floor exists for, since a loop grading its own decisions drifts toward "not fundamental". `checks.sh --check` now
runs the floor at **commit** time. **The receipt is the escape**, and a gate with no escape is a gate that gets
switched off: a change that crosses the floor commits only when a human approved it.
**BOUND TO CONTENT, NOT TO A LABEL — this is the whole mechanism.** A receipt that merely said *approved* would
licence every later spec change, and worse, would licence **editing the spec after approval**, which is the exact
move the floor exists to catch. So the digest must match the spec **as staged**: approve v1 and commit v2 and it
blocks again, with no way to talk it round. The fix for a blocked commit is to **re-route**, never to re-record.
*(The same trick as `forecast.py freeze`: a digest is what makes an approval real rather than a label.)*
**Staged, not worktree** — a gate reading the working tree could be satisfied by a file the commit does not
contain. **Fail-closed**, like the floor: an unreadable receipt, an unreadable spec, or a floor that will not run
all land on BLOCKED, because an escape hatch that opens when the mechanism malfunctions is not an escape hatch.

## control.json  · written by `drain.py record` when a `control` pause/resume is applied, read by `drain.py paused` and the session driver · *`.workflow/control.json`; RUNTIME, gitignored, atomic write; kept on a native filesystem*
- `{ paused: bool, at, by }` — `by` is the `message_id` of the control message that last set it.
**The state `pause` did not have.** The op was validated and delivered, and then honoured only by whichever
session read it — so a pause expired at that session's exit, which is exactly when an unattended driver decides
whether to start another one, and exactly when a human who paused expects it to hold.
**Why the drain writes it rather than the orchestrator.** The drain's own split is *apply is judgment,
bookkeeping is arithmetic*, and that line was drawn from measurement, not taste. `reprioritize` is judgment —
which item matters more is not a function of the inputs. `pause`/`resume` are a **flag**, so they belong to the
arithmetic half; leaving them on the judgment side meant the one control a human most expects to be absolute was
the one depending on a model remembering it.
**Written BEFORE the watermark** in `record`, deliberately: a crash between the two leaves the control honoured
and the message merely redelivered (a no-op by construction). The reverse order loses the pause outright — the
message reads as consumed and the latch never moved.
**RUNTIME, like `state.json`.** It is operational intent about a live machine, not project history, and a
rebuilt machine has nothing to stay paused about.

## session driver  · `scripts/loop.sh --drive` + `scripts/drive.py`, holding `orchestrator.lock` across sessions · *no artifact of its own — every decision is read from durable state written by something else*
`loop.sh` without `--drive` is unchanged: one `exec claude`, and the human drives. With `--drive` it holds the
lock, runs a session, and starts the next against the same goal until a stop predicate fires.
- **A fresh process is the reset.** `/clear` cannot be self-invoked, so a new session is not a second-best — and
  it starts from the anchor a cold start already rebuilds from (`handoff.md` + git).
- **The driver decides; the session does not report.** Every predicate is computed from state the session did not
  author for the purpose — the pause latch, the goal ledger, git, the item anchors. A session that crashed, was
  killed, or ran out of context writes nothing, and a driver that needed a report could not tell that apart from
  a clean stop.
- **Stop predicates, in precedence order:** `paused` · goal `met` · goal `STALLED` · `MAX_NOPROGRESS` consecutive
  sessions that moved no anchor. Anything that cannot be computed **also stops** — this half spawns processes, so
  it fails closed where `converge.py` (which only reports) may not.
- **Progress is the ANCHOR SET, not `HEAD` alone.** An item bigger than one session advances through nodes
  without committing, and a HEAD-only driver would call that a stall. So it fingerprints `HEAD` **plus** the
  per-item anchors, reusing the forecast anchor table's rule. Presence only — hashing bodies would let an edited
  draft read as a node having run.
- **The drop-in window** between sessions releases the lock for `REEVE_DROPIN_SECONDS` (default 5). Anyone who
  takes it in the gap — a human's own `loop.sh`, or the daemon's relaunch-runner — keeps it, and the driver
  finds out by **losing the re-acquire** and exiting. The handover needs no flag and no signal; it is the same
  `flock` that already prevents two orchestrators, used as a handshake.
- **The session-side stop discipline rides the PROMPT** (`REEVE_DRIVE_PROMPT`), not the always-loaded brief:
  it is the driver's instruction to its own sessions, a human session must never auto-stop, and a per-session
  instruction costs the always-loaded budget nothing.

## alerts.json  · written and read by the bus daemon alone, to record which checkpoints it has already alerted on · *`.workflow/alerts.json`; RUNTIME, gitignored, atomic write; kept on a native filesystem*
- `{ checkpoints: { "<ticket_id>|<deadline>": { first_alert, last_alert, escalated } }, dead_letters: { "<message_id>": { at } } }`
  — the daemon's own away-alert bookkeeping. It **cannot** live in `parked/` (the orchestrator's single-writer
  partition, not the daemon's) nor in the boot-scoped `bus.json` (rewritten at boot, so it would be destroyed at
  exactly the restart it must survive), so it is a **fourth daemon-owned path**. Loaded at daemon start, so a
  routine restart — frequent on WSL — does **not** re-alert every open checkpoint (which would train the human to
  ignore the channel). **A lost or unparseable file re-alerts rather than going silent** — a missed alert is the
  failure this exists to prevent, so the safe direction is noise. Delivery failure is a *channel* property: a
  failing webhook backs off the whole channel (doubling, capped at `reminder_hours`) and does **not** mark the
  checkpoint alerted, so the reminder path retries it once the channel recovers. Keys are pruned when the
  checkpoint resolves / the dead-letter clears, which bounds the file and is what makes a re-park re-alert.

## session-start warn-once markers  · written and read by `hooks/session_start.py` alone · *`.git/hooks/.disciplined-builder-assert` + `.git/hooks/.disciplined-builder-stale`; MACHINE-LOCAL, never committed, plain overwrite (no atomicity needed — a torn or lost file re-warns, which is the safe direction)*
- `.disciplined-builder-assert` — a bare sha256 line: the hash of the **foreign** `.git/hooks/pre-commit`
  already warned about. A *different* foreign hook is new information and warns again; installing our
  backstop deletes the file, so a project that removes the foreign hook is told rather than staying silent.
- `.disciplined-builder-stale` — `{ reinstall: "<installed>..<anchor>", update: "<old>..<new>" }`, the
  staleness detector's warn-once state, keyed on the **SHA pair** per hop. New drift is a new key and
  warns again; a fix needs no clearing, because the condition simply stops holding.
- **Why `.git/hooks/` and not `.workflow/`** — all three requirements point there and only there. The facts
  recorded are about **this machine** (which install is present, which foreign hook is on this clone), so
  committing them would let one machine silence another's warning; `.git/` is untrackable **by
  construction**, needing no `.gitignore` entry — which matters because the installs these must reach are
  precisely the ones too stale to have a new ignore line. They must also survive `/rebind` (they are not in
  the relocatable runtime tree) and be readable before a project is bootstrapped. **Nothing prunes them**
  and nothing needs to: one small file per project, rewritten in place, and `retention.py`'s remit is
  `.workflow/` artifacts. A project with no `.git/` **directory** (including a worktree, whose `.git` is a
  file) gets neither marker and both features stay silent there — a detector that cannot remember having
  warned becomes noise, which is the failure mode it exists to avoid.

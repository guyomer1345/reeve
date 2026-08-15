# Shared Artifact Schemas — the runtime substrate

The sibling half of [`schemas.md`](schemas.md). That file owns the artifacts the **loop** produces and
consumes — a plan, a changelog, a verdict, a parked ticket. This file owns the records the package's own
**processes** own: written and read by `/start`, `/update`, `rebind.py`, the bus daemon and the `SessionStart`
hook, and never authored or consumed by a skill as work. Same conventions as its sibling — on-disk paths are
fixed, and each schema notes its **write-mode** and **tier** (see `shared/memory-model.md`).

*Split out of `schemas.md` when that file crossed the 25 000-token Read ceiling, per the split-and-pointer
convention in `shared/memory-model.md`. A reference of the form `schemas.md § <name>` for any section below
resolves here — the name is the anchor, and the two files are one schema.*

## config.json  · written once by `/start`, read on demand · *rewrite-in-place · static after init (committed)*
- `project` — the project's **name**, as `/start` filled `<project>` in the brief. Load-bearing rather than
  cosmetic: `/update` re-renders that managed block, and with no name to read it fell back to the checkout
  directory's basename — which for any project whose directory is named something else made every update
  report the brief as a `LOCAL-EDIT` ("local edit would be LOST") over a difference the package itself had
  invented, then rename the project on apply. Absent ⇒ the basename fallback, unchanged.
- `project_root` — `./project` (greenfield) | `.` (brownfield **and org**); makes code-touching skills path-agnostic
- `docs_root` — where the workflow's **derived** docs live (`docs/spec.md`, `docs/architecture.md`,
  `docs/knowledge/`, `docs/decisions/`, `rules/`). Absent → **`project_root`**, which is every mode but org, so
  the split is invisible unless a mode asks for it. **Org mode sets `.workflow`**, and the reason is the leak
  boundary rather than tidiness: there the tree *is* a clone of a repo the workflow does not own, which very
  likely already has its own `docs/` — writing derived IP about proprietary code into it would both clobber the
  owner's files and reduce the review bundle's exclusion list from two directories to a per-file list that has to
  stay correct forever. Namespaced, the brain owns exactly **`.workflow/` + `.claude/`** and nothing else, so the
  exclusion is structural. Adopted as its **own key with its own owner** rather than overloading `project_root`,
  which would then mean "where the code is" to one reader and "where the docs are" to another.
- `workflow_version` — the installed package version, stamped by `/start` step 7 and restamped by every
  `/update`; the migration key `/update` diffs against (an install that cannot say which snapshot it holds
  cannot be migrated). Equal old/new ⇒ a **no-op** update; **absent** ⇒ unknown-old ⇒ full reconcile +
  stamp, with removals disabled (see `install-set.json`). **In practice a commit SHA, not a semver:** the
  package ships no `version` field, so Claude Code names the install cache by the source commit and that
  is the value. It is resolved by `update_reconcile.py version` — the single owner of the chain
  (`plugin.json` pin → the resolved cache-dir basename → the source repo's `HEAD` → `unknown`) — never by
  reading `plugin.json`, which no longer has the field. **Nothing orders this value**: it is used for an
  equality test, a display string, and an absent-check only; every migration decision is content-hash
  driven through `install-set.json`. `unknown` is never a no-op. If `/update` ever needs true ordering,
  the escape hatch is a product-owned `schema_version` in a shipped file — a *different* field from the
  delivery cache key, adopted deliberately
- `run` — per-project run config (model/effort routing, wave caps — fields grow as those land)
- `context` — the interactive context-governor knob, **read by the shipped statusline** (the one
  surface the running token count reaches — hooks and the model receive none): `warn_pct` (the
  context-usage **percentage** past which the statusline shows the persistent "run /dispatch, then
  /clear" banner). A percentage, never a token count, so it is model-window-agnostic — a 200k and a
  1M window warn at the same fraction full. Absent → shipped default (`warn_pct` 30).
- `retention` — the memory-bound knobs the `audit` pass reads: `sessions_k` (per-node `# Sessions` cap — the
  retention script's only knob) + the scheduling thresholds `prioritize` trips on (`decisions_superseded_n` —
  **superseded** decision bodies awaiting GC, the count retention actually lowers, not the active count;
  `items_closed_m`; `every_p_items`). Absent → shipped defaults (sessions_k 10, decisions_superseded_n 30,
  items_closed_m 10, every_p_items 15). The Sessions trigger fires with a **margin** above `sessions_k` (the cap
  restores headroom), so a single append can't re-trip the audit.
- `doc_budget` — the context-budget knobs read by `check_doc_budget.py` (the gate) and `prioritize` (the
  trigger). **Budgets are per ROLE and in TOKENS** — model-window-agnostic, the same reason `context.warn_pct`
  is a percentage — and **two-tier per role**: `always_hard` / `always_advisory` for the always-loaded set
  (root `CLAUDE.md`, `.workflow/loop.md` — rent paid every turn, every session) and `ondemand_hard` /
  `ondemand_advisory` for the on-demand set (`docs/spec.md`, `docs/architecture.md`, `rules/**`,
  `docs/knowledge/**`, `docs/decisions/**`, `backlog.md`). **The hard tier FAILS `checks.sh`; the advisory tier
  only schedules a trim.** Both tiers exist because an aggressive-only budget would be red on a clean install —
  and a gate that fires on a fresh bootstrap is one a human learns to skip. `ondemand_hard` is not a
  preference: it is the **Read tool's own 25 000-token ceiling**, past which a file cannot be loaded in one
  call at all. `chars_per_token` is the estimator's divisor — there is no tokenizer in the standard library, so
  the count is estimated from length and **deliberately errs high**, since under-reporting is what lets an
  unreadable file pass. Lower it for a project whose docs are dense in fenced code. Absent → shipped defaults
  (`chars_per_token` 3.2, `always_hard` 4000, `always_advisory` 1200, `ondemand_hard` 25000,
  `ondemand_advisory` 15000, `every_p_items` 15). **Decoupled from `retention` and `align`** — doc size is not
  memory pressure and not drift risk, so it gets its own threshold, the same shape those two already use.
  The **VOLATILE tier is deliberately out of scope**: `handoff.md` is already capped mechanically at injection
  time by the SessionStart hook, and a second budget for one bound is a second owner
- `align` — the drift-scan knobs, read by `prioritize` (trigger) + `align` (budget): `every_n_commits` (commits
  since `.workflow/align/anchor.json`'s `base_sha` before an `align` item is injected) + `max_agents` (hard cap
  on the semantic pass's fan-out; deferred surface rides the next scan). **Decoupled from `retention`** (drift
  risk ≠ memory pressure). Absent → shipped defaults (every_n_commits 20, max_agents 6).
- `demo` — the demo-sandbox knob read by `create-demo`: `max_refine_rounds` (the cap on demo regenerations
  before the refine loop stops auto-proceeding and **escalates to a live `discuss`**). Absent → shipped default
  (`max_refine_rounds` 3).
- `thread` — the conversation-thread knobs read by the `answer` skill (`schemas.md § conversation-thread`):
  `rotate_at_tokens` (the estimated context past which the thread hands off and starts a fresh session) and
  `max_turns_rendered` (how many turns the console panel shows; the rest stay on disk until rotation). Absent →
  shipped defaults (`rotate_at_tokens` 200000, `max_turns_rendered` 50). **Decoupled from `retention` and
  `doc_budget`, and it is the odd one out on purpose:** every other retention knob bounds *bytes on disk*, while
  this one bounds *spend* — `--resume` re-sends the whole thread on every message, so length is priced per
  question. It borrows `doc_budget.chars_per_token` as its estimator rather than declaring a second divisor.
- `checkpoint` — the park-deadline knobs, **read by the console daemon** (the only always-alive process, so the
  only one that can own a timer): `deadline_hours` (the orchestrator stamps an *absolute* `deadline` onto the
  parked record as *now + this*; once passed, the daemon escalates — a **deadline never auto-proceeds**, it only
  raises the alarm) + `reminder_hours` (how often the daemon re-alerts while the checkpoint is open and not yet
  overdue). Absent → shipped defaults (`deadline_hours` 24, `reminder_hours` 4).
- `secrets_required` — the **key NAMES** (never values) of the live credentials this project needs, appended by
  the `setup` checkpoint at elicitation (from that checkpoint's `request.tasks[].secrets[]`, which is the fact's
  source) and idempotent on the name. It exists because absence is otherwise
  **undetectable by inspection**: an empty `secrets/` is indistinguishable from a project that needs none, so a
  machine move could only report "the store is gone" and never *which* keys. `/rebind` diffs this against the store
  and files `required − present` as an itemized loss. **Early warning, not a gate** — point-of-use fail-closed
  stays the floor, because a manifest can only say what *should* be there. Absent → no itemization, and the generic
  store-lost entry still covers the move. Committed, which is exactly why it holds names only.
- `notify` — the away-channel, **read by the console daemon**: `webhook` `{ url, kind: generic|slack }` +
  `desktop` (bool). The **webhook is the real away channel** — it reaches a phone and works from a detached
  daemon; a desktop toast is **best-effort only** (Linux `notify-send`, and it needs a notification daemon to own
  the `org.freedesktop.Notifications` bus name — absent on a headless/WSL box even though the session bus itself
  exists, so the toast fails there — and it reaches only someone already at the machine, who is by definition not
  away). Absent → desktop best-effort and **no away alerting at all**: the human polls the console. That
  degradation is deliberate and must be stated plainly rather than papered over — an alert channel that silently
  reaches nobody is worse than a documented absence, so the daemon reports away-channel readiness in `status`.
- `outward` — the standing-pre-authorization allowlist for outward actions, in Claude Code's own
  `permissions.{allow, ask, deny}` shape (deny→ask→allow, first-match-wins), **coarse per-action-class**
  (`push` / `issue-create` / `issue-close` / later `deploy` / `send`). Absent → **all `ask`** (MVP-safe:
  every outward action gated per-action, queued to `outbox/`). This is Layer 2 (human approval); it never waives
  Layer 1 (`guard.sh`). Optional `outbox_ttl` sets the pending-action expiry.
  **This key is the sole owner of the outward allow/ask policy.** The harness's own `settings.json` deliberately
  carries **no competing `ask`** for the outbox-covered classes: an outward action is approved through the outbox +
  a console `release` and fired *later*, at a scheduler boundary — a static harness prompt would fire into a
  terminal nobody is watching and block the very away-release the model exists to serve. So the harness stays out
  of the outward path, and the gate is: **skill self-gate (this key) → outbox/release (the human) → `guard.sh`
  (the floor)**. The consequence is deliberate: a *mis-coded skill* that runs an outward command directly is no
  longer caught by a prompt — only by the floor. That trade buys the away-release; a bug in first-party skills is
  fixed, not fenced.
  **Fine-grained scoping** (never auto-push `main`) belongs in `guard.sh`, **not** a config allow-pattern (Claude
  Code documents arg-constraining patterns as fragile → use deny + hooks) — see `guard` below.
- `runner` — the relaunch-runner, read by the daemon that hosts it as a **job**: `{ enabled }`. When on, the
  daemon relaunches `claude` (a fresh `claude -p` process per ticket = a clean context window for free — this retires
  the manual-`/clear` stopgap) whenever there is **applicable** unconsumed work and **no orchestrator is live** — the
  last link that lets an away verdict actually *resume* the loop rather than sit in the inbox until someone reaches the
  terminal. Absent → off: the console still works, but nothing resumes a whole-parked loop without a human at the
  terminal. The behaviour is fixed (no user knobs in MVP); the load-bearing rules:
  - **Trigger = applicable work only.** It spawns only for a pending `verdict` or `intake` (the kinds that advance a
    dead/parked loop) via `drain.py list` — never for a lone `control` (nothing to drive) and never for a `release`
    (loopback-only, so a human was present to approve it). A message that can't resume anything doesn't spawn a loop
    that would immediately re-park.
  - **Liveness precondition** = the `orchestrator.lock` `flock` probe (above): a duplicate orchestrator would be the
    package's own defect rather than operator error — the single exception to the otherwise operator-assumed
    one-orchestrator run-constraint. The runner's own spawn goes through `flock -n`, which is also the double-launch latch.
  - **The launch** = `flock -n orchestrator.lock claude -p "<resume prompt>"`, detached (`setsid`, DEVNULL stdio),
    cwd = the launch root (so it loads the project's `CLAUDE.md` + `.claude/settings.json`), on the user's own
    `~/.claude` auth. **Never `--dangerously-skip-permissions`** — that would bypass the settings `ask` floor
    (deploy/network); `guard.sh` still gates it. The resume prompt forces the boundary drain rather than
    relying on the "drive only if state.json shows an active run" guard.
  - **Trust precondition (MEASURED) — a SPAWN GATE.** A `claude -p` in a workspace Claude Code has not
    trusted **ignores `settings.json`'s allowlist** and then proceeds **read-only**: it composes a complete, correct
    answer, silently fails to persist a byte of it, and **exits 0 in seconds**. It does *not* hang, so the stall
    timeout below never engages — the launch scores no-progress and the away path burns `RUNNER_MAX_ATTEMPTS` full
    answers before an unactionable hard-stop. So the runner **refuses to spawn** into one and fires **one** alert
    naming the fix. `/start` establishes trust by recording `projects["<abs path>"].hasTrustDialogAccepted: true`
    in `~/.claude.json` (the manual path for when the WSL trust dialog does not render — equivalent to accepting
    it), so a properly-started project is trusted well before the runner could fire.
    - **The read is exact-path and fails OPEN.** Trust does **not** inherit from a trusted parent (MEASURED), and
      `claude -p` does **not** create a project record — so an **absent** entry is the *ordinary* untrusted case,
      not an unknown one. Absence may only be read as untrusted while the file still proves it speaks the schema
      (it parsed, `projects` is a dict, some entry still carries the flag); if that probe fails, the answer is
      *unknown* and the runner spawns exactly as before. This reads an **undocumented platform-internal file**, and
      a format change must never be the reason a human's questions stop being answered.
  - **Crash-loop + stall safety.** A relaunch that exits **without advancing the watermark** backs off (doubling) and,
    after a cap, **hard-stops and fires an away alert** — closing the notifier's deferred thrash/crash alert arm. A relaunch
    that **hangs without draining** is killed after a stall timeout and scored the same
    way, so it can't pin the runner in-flight forever. (That timeout covers a *hung* launch only — an untrusted one
    exits cleanly and never reaches it, which is why trust is gated up front, above.) A relaunch that *drains* is doing real work and runs freely.
  - **WSL:** the runner is the overnight mechanism, but the daemon hosting it dies with the last terminal unless
    `.wslconfig` sets `vmIdleTimeout=-1` — surfaced in `status`, never implied.
- `remote` — opt-in remote (phone) access, read by the daemon: `{ enabled, transport: access | tailscale, port?,
  public_url? }`. **Absent / `enabled: false` / no transport → the remote socket is not served at all** (loopback
  only). The transport is a **declaration**: the operator stands up Cloudflare Access or `tailscale serve` in front of
  `bus.json`'s `remote_port` and is responsible for it being real — the same operator-responsibility stance as the
  single-orchestrator run-constraint. It is *not* a free-text URL: the value picks what the daemon will serve.
  `transport: tailscale` additionally unlocks **credential-bearing `setup` verdicts** on the remote surface,
  because WireGuard is **end-to-end encrypted**; `transport: access` does **not** — Cloudflare terminates TLS, so a
  returned key would transit their edge in plaintext. Everything else on the remote surface is identical.
  - `port` — the **fixed loopback port** the remote socket binds (default `8799`). Fixed, not daemon-chosen: the
    operator points a tunnel at it once and the phone is paired against it once, so a per-boot port would break the
    away channel every restart. Bind-in-use degrades to no-remote with a warning, never a dead daemon.
  - `public_url` — the tunnel's `https://` origin. **Load-bearing for the transport, not just the pairing link:**
    the daemon builds the copy-paste pairing URL from it (`<public_url>/#t=<remote_token>`), *and* adds
    its host to Socket A's Host-allowlist — a proxy that forwards the original Host would otherwise have all its
    traffic rejected. Absent → the pairing link and the forwarded-Host allowlist are both unavailable (surfaced in
    `status`); only loopback-Host proxy traffic (Host-rewriting proxies) still reaches A.
- `guard` — the Layer-1 floor's two knobs:
  - `protected_branches` (**add-only**) — *adds* names to the protected set (e.g. `release`, `prod`).
  - `allow_protected_push` (`true` lowers the default floor) — drops `main`/`master` from the set for **this
    project only**. Names in `protected_branches` are still honoured, so a project can opt out of the
    `main`/`master` floor while keeping `release` protected. Strict read: only real JSON `true` counts (the
    string `"true"` does not), and the guard **fails closed** — an unreadable/malformed `config.json`, or no
    `python3`, keeps the floor. When it does lower the floor the guard says so on stderr, so a permitted push
    to `main` is never silent.
  - Absent → `{main, master}`.
  - **Still non-overridable by any config:** the outgoing-range secret scan. No push ships a secret, regardless
    of `outward` or `allow_protected_push`.
  - **Why this became a toggle.** It deliberately was not one: the rule used to be that disabling a safety floor
    should cost an edit to `guard.sh` itself, as a visible owner-level act. That reasoning assumed a team, where
    "a human moves `main`" names a *different* human than the loop. On a **solo repo the owner is the only
    pusher**, so the floor bought no separation of duties — it just forced a feature-branch detour, or an
    out-of-band `git push` that bypassed the outgoing-range secret scan entirely. Making it an explicit,
    committed, default-OFF config key is strictly safer than the workaround it was producing. The floor still
    defaults ON, so a fresh `/start` is unchanged.
- `org` — **org mode. Its PRESENCE is the mode; absent ⇒ wholly inert**, and there is deliberately **no
  `enabled` flag**. That is the one place this key breaks the shape `runner`/`remote` use, and the break is the
  point: switching a live project's git topology is a **migration, not a setting**, so the mode is chosen once at
  `/start` and a config edit must never be able to flip it. Org mode runs the workflow against a product the
  operator does **not own** — the tree is a private clone with no push path to the owner, and the operator's own
  checkout of that product is a **separate directory the workflow never reads or writes at all**.
  - `checkout` — absolute path to the operator's own checkout, recorded so the bundle hand-off can name it
    concretely (`cd <checkout> && git apply …`). **Never read from and never written to** — it is a string for a
    human-facing message, not a second working tree. Absent → the hand-off names the bundle and lets the human
    place it.
  - `archive_remote_ack` — a **reason string** acknowledging that the private tree has been given a remote.
    Absent (the default) → **no remote is permitted**, because the tree concentrates derived IP about someone
    else's proprietary code and pushing it anywhere is a governance act, not a backup preference. Present → the
    remote is allowed *and the console shows a standing badge for as long as one is configured*, so the
    acknowledgement is a visible recorded fact rather than a sentence someone once read.
  - **What the mode changes** is subtraction, not new machinery: `docs_root` namespaces the brain (above); the
    brief goes to **`.claude/CLAUDE.md`** so the owner's root `CLAUDE.md` is never written (it is still read, as
    the ingest intent-seed); `checks.env` declares `STACK_GATE_NONE`, because the tree's own code must never be
    executed here; `create-issue`/`close-issue` stay **local-only** (never the owner's tracker); no hooks, no
    installs and no `.gitignore` edits reach the owner's checkout; and `verify` degrades to **artifact
    conformance**, with all runtime checking moved to a human `qa` checkpoint in the operator's own checkout.

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

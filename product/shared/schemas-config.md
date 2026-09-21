# Shared Artifact Schemas — the operator's control surface

The knobs. [`schemas.md`](schemas.md) owns what the **loop** produces, and its
[`schemas-runtime.md`](schemas-runtime.md) sibling owns the records the package's own **processes** write and
read. This file owns the one thing in that family a **human** turns: every setting this package exposes, what
turning it costs, and what it is safe to leave alone — **and the one standing instruction they write in prose
rather than in JSON, `directive`** (moved here 2026-09-21: an operator telling the loop how to behave is the
control surface, whatever its syntax).

*Physical location is deliberately not the boundary.* Most of these are fields in `.workflow/config.json`, but a
knob that lives in `.claude/settings.json` is still a knob, and an operator asking *"what can I change here?"*
should find one file rather than learn which file a setting happens to be stored in. What unites this file is
that everything in it is **meant to be edited**; what unites its runtime sibling is that hand-editing anything
there would corrupt it.

*Split out of `schemas-runtime.md` when the operator-facing half and the machinery half proved to grow at
different rates — knobs accumulate with every slice, locks and pointers only when new machinery appears, and one
file carrying both reached 99.7% of the Read ceiling. Same conventions as its siblings — on-disk paths are fixed,
and each schema notes its **write-mode** and **tier** (see `shared/memory-model.md`). A reference of the form
`schemas.md § <name>` or `schemas-runtime.md § <name>` for any section below resolves here — the name is the
anchor, and the parts are one schema.*

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
- `run` — per-project run config (model/effort routing — fields grow as those land), plus `drive` and `wave`:
  - `drive.gate_turns` — **arm the turn gate for an operator who drives some other way.** The gate
    (`hooks/turn_gate.py` → `scripts/turn_check.py`) is scoped to an UNATTENDED drive at the maintainer's word,
    and it normally detects that from the driver's own environment (`REEVE_DRIVE` / `REEVE_SUPERVISE`, exported
    by `loop.sh`). Absent → off, which is the right default for a human sitting there planning: a gate that
    demanded a `continue` from an interactive session would be the same nuisance in the opposite direction, and
    the first thing they would do is switch it off — taking the unattended case with it. Set it and every
    `Stop` runs the ladder regardless of environment. *(Documented here because this file owns the config keys:
    it shipped with its only description in a docstring and a `loop-detail.md` aside, and a fact with two
    part-owners and no real one is exactly what this file exists to prevent.)*
  - `wave` — the fan-out caps read by `prioritize` (how many to plan), `check_wave_independence.py` (how many
    may run at once) and `plan_freshness.py` (when to stop patching a plan):
    - `plan_max` — items planned per wave. Planning ahead is what makes fan-out possible at all: the independence
      predicate reads `files_touched` from a plan, and a backlog row has none until it is picked. Surplus plans are
      **not waste** — a plan is durable and an unbuilt item walks into the next wave already eligible, so the pool
      of provably-independent work grows monotonically. Only the first wave pays full price.
    - `execute_max` — workers dispatched at once. This is a **review** bound, not a machine one: it is how many
      simultaneous writers a human can still meaningfully read afterwards. Raise it knowing that is the dial.
    - `refresh_max` — in-place refreshes a plan may take before it is re-planned from scratch. Each refresh is
      locally correct and a stack of them is not, the same way repeated patches to a document drift.
    - Absent → shipped defaults (`plan_max` 10, `execute_max` 5, `refresh_max` 2).
- `context` — the interactive context-governor knob, **read by the shipped statusline** (the one
  surface the running token count reaches — hooks and the model receive none): `warn_pct`, a
  context-usage **percentage**. **Absent → there is no ceiling, and the BAND governs**
  (`context_band.py`): hold while there is runway, hand off at the next boundary in the middle,
  hand off now once what is left is needed to finish the item and publish a complete anchor —
  measured in *nodes of runway*, `(window − used) ÷ per-node cost`, because a fraction makes a
  200k and a 1M window read identically while leaving them 5 and 25 nodes of room.
  **Set it and it becomes an EXPLICIT OPERATOR CEILING that outranks the arithmetic**: a human
  saying "warn me at 30%" is giving a standing instruction, and a governor that quietly
  overruled it would reproduce the failure the directive channel exists to stop. So the knob is
  no longer the default — it is the override — and the shipped default is *no ceiling*.
  *(It still governs alone in one case: when the harness reports no window size, runway in nodes
  is not computable and the statusline degrades to the fraction rule at 30. A percentage is the
  wrong unit, not a wrong signal.)*
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
  (`chars_per_token` 3.2, `always_hard` 4000, `always_advisory` 3200, `always_total_hard` 8000,
  `always_total_advisory` 6400, `ondemand_hard` 25000, `ondemand_advisory` 15000, `every_p_items` 15). **Decoupled from `retention` and `align`** — doc size is not
  memory pressure and not drift risk, so it gets its own threshold, the same shape those two already use.
  The **VOLATILE tier is deliberately out of scope**: `handoff.md` is already capped mechanically at injection
  time by the SessionStart hook, and a second budget for one bound is a second owner.
  **The always-loaded tier carries a SECOND, set-wide bound: `always_total_hard` /
  `always_total_advisory`, over the SUM of the always-loaded files.** The per-file cap is a *shape* check —
  it says one file has outgrown its role — and it structurally cannot see the bill, because two files each a
  token under cap cost the same rent as one file at twice the cap and only the second is caught. The total is
  the number that describes what a session pays before a word is typed; it fails `checks.sh` exactly as a
  per-file breach does, and it is set far below (slots x `always_hard`) or it would ratify the accumulation it
  exists to stop. The on-demand set is deliberately **not** totalled — nothing loads it until something needs
  it, so a sum over it would fail a project for owning documentation.
  **Every advisory sits proportionally under its hard bound (~80%), not at an aspirational floor** — an
  advisory below what a file can structurally be fires on every run forever, and a tier tripped since day one
  is a tier nobody reads. Changing any of these follows one standing rule: **a cap is set to a value the
  shipped package already meets, and is never raised to accommodate what the package happens to weigh**
- `align` — the drift-scan knobs, read by `prioritize` (trigger) + `align` (budget): `every_n_commits` (commits
  since `.workflow/align/anchor.json`'s `base_sha` before an `align` item is injected) + `max_agents` (hard cap
  on the semantic pass's fan-out; deferred surface rides the next scan). **Decoupled from `retention`** (drift
  risk ≠ memory pressure). Absent → shipped defaults (every_n_commits 20, max_agents 6).
- `demo` — the demo-sandbox knob read by `create-demo`: `max_refine_rounds` (the cap on demo regenerations
  before the refine loop stops auto-proceeding and **escalates to a live `discuss`**). Absent → shipped default
  (`max_refine_rounds` 3).
- `review` — the cold-context reviewer's knob, read by the orchestrator at `review`'s route: `max_rounds` (how
  many times one item may come back gating before the loop stops routing to `refine` and **escalates to a
  `checkpoint`** — a change that cannot be got right in N rounds is a design question, not a defect). Absent →
  shipped default (`max_rounds` 2). Lower than `demo`'s 3 on purpose: a demo round is cheap and regenerates a
  sandbox, a review round re-runs plan→execute→verify on real code.
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

## subagentPromptCacheTtl  · a HARNESS setting a project MAY set, deliberately NOT set by this package · *`.claude/settings.json` (or `CLAUDE_CODE_SUBAGENT_PROMPT_CACHE_TTL`, or a per-agent `experimental.cacheTtl` in an agent's frontmatter)*
Recorded here because it looks like free money and is not, and because the arithmetic that decides it is
**workload-specific** — so a project that measures differently from this package's reference workload should set
it, and one that does not should leave it alone.

**What it does.** A dispatched worker's prompt prefix is cached; when the worker idles longer than the cache TTL
its whole prefix is re-written on the next turn. The subagent bucket defaults to **5 minutes regardless of plan**
(measured: across ten thousand-plus subagent cache-creation turns on the reference workload, every single one was
a 5-minute write and not one was an hour-long write). Raising it to `"1h"` makes those stall re-writes rarer.

**Why it is not on by default — the break-even test, stated so it can be re-run rather than re-argued.** A 1h
cache write costs **2.0×** base input against a 5m write's **1.25×**; a cache *read* is **0.1×** either way. So
the longer TTL trades a permanent 60% premium on **every** write for the removal of **some** re-writes, and it
wins only when stall re-writes exceed roughly **39%** of all cache writes. On the reference workload they are
**40%** — one point over the line, which measured out as a **−0.4%** total saving. That is inside the error bar,
and it is *optimistic*: it assumes every idle gap would fit inside an hour, while a third of the stalled
dispatches ran longer than an hour overall, so some gaps would expire at 1h anyway and be paid for at 2×.

**And it moves the wrong way as the rest of the discipline works.** The `dispatch-return` contract
(`schemas.md`) exists to keep bulk out of a worker's window. A smaller window is a smaller prefix, so it is a
smaller stall re-write — which is the only thing the longer TTL recovers — while the 2× write premium is
unchanged. A default that has to be re-examined the moment the neighbouring rule takes effect is not a default.

**To decide it for a real project:** take that project's own share of cache writes that are stall re-writes. Over
~39% → `"1h"` pays; under → it costs. Set it per-agent (`experimental.cacheTtl` on the one agent that actually
stalls) before setting it globally, because the premium applies to every worker and the stalls usually do not.

## directive  · written by a human (or by the orchestrator on their instruction), validated by `check_directives.py` · *`.workflow/directives.md`; **COMMITTED** and **ALWAYS-LOADED**, so it is budgeted in the always-loaded set and inside its TOTAL ceiling (§ commit-receipt's sibling law in `memory-model.md`); PROJECT-OWNED — `/start` seeds it and no update ever overwrites it*
**A standing operator instruction about how the LOOP behaves.** Neither `docs/decisions/` (build decisions,
append-only, on-demand — a directive the loop does not see every turn is not in force) nor `rules/**` (about
product CODE, each carrying an `— enforced by:` tag). Without this file such an instruction lives in the
conversation and dies at the next `/clear`, which is why it is re-typed every session.

**MECHANICAL-FIRST IS THE ENTRY RULE, and it is decidable rather than a matter of taste.** One question decides
the type: *does the directive name a condition a script could evaluate?* A threshold, a file state, an event —
then it is mechanizable, and it **is wired** as a hook, a `config.json` knob, a gate or a daemon term. Only a
directive with no observable trigger stays as text. Prose is the fallback, never the default: an always-loaded
file that accepts anything is unbounded growth in the most expensive place in the system.

- `type` ∈ `{ mechanized, behavioural }` · `entered` — `YYYY-MM-DD` · `retire` — see below ·
  `mechanism` — **required iff `type: mechanized`, forbidden otherwise**: the path or config key where the rule
  actually lives.
- **A `mechanized` entry states what it ACHIEVES and never restates the rule.** This is the second-copy hazard at
  its sharpest, on a file whose whole purpose is to be obeyed — a directive written once here as prose and once
  there as a hook gives the loop two masters that drift apart. The entry is an **index row**: a pointer, not a
  copy, which is exactly what the one-owner law permits and what a restatement violates. It
  is held to that mechanically — a `mechanized` body is capped at **one line**, and a one-line body cannot be a
  second copy of a hook's logic. The mechanism is also checked to EXIST; a dangling pointer is how an index rots.
- **Every entry carries a retire path, and none of them is "a human remembers":**
  - `on:YYYY-MM-DD` — expires. `check_directives.py` FAILS once the date has passed, so an expired directive
    stops the build rather than quietly staying in force.
  - `when:<path>` — retires when that mechanism exists. The gate fails once the path is present, which is what
    makes mechanical-first hold *over time* rather than only at entry: the prose is a placeholder that is
    forced out the day its hook lands.
  - `standing` — no expiry. Permitted, and deliberately the least convenient: standing entries are listed on
    every `--report` so they are re-confirmed rather than accumulated.
- **Why not `state.json` or `handoff.md`:** `handoff.md` is prose for a stranger, rewritten whole at every
  `/dispatch`, so nothing in it survives as an instruction; `state.json` is volatile and gitignored, and a
  standing instruction that does not survive a crash is not standing.

### the autonomy floor  · read by the orchestrator before taking a decision, computed by `check_autonomy_floor.py`
> **Consulted at decision time, ENFORCED at commit time (2026-09-13).** `loop.md` asks the orchestrator to run
> this before acting on a goal-affecting decision — which is a consultation, and *a loop that simply does not run
> it is precisely the case the floor exists for*. `checks.sh --check` now runs it as a gate, with
> `spec_approval.py`'s receipt as the escape: a change that crosses the floor commits only when a human approved
> **this exact spec content**. The receipt is bound to a **digest**, not a label, so approving one version and
> committing another blocks again — see `schemas-runtime.md § spec-approval.json`.
**The loop takes every decision that does not change the goal, and routes anything that may.** That criterion is
sharper than reversibility × blast-radius, which grades *how carefully to decide* rather than *whose decision it
is*, and it already has an owner: the spec's commitment model. *Goal-affecting* ≈ *would change a `locked`
element, or change what an acceptance criterion demands.*

**The judgment does not stand alone, because a loop grading its own decisions drifts toward "not fundamental" —
that is the direction that lets it keep working.** So there is a mechanical floor, and judgment may escalate
above it and never below it. The floor is computed from the **spec diff**:
- a changed hunk in `docs/spec.md` whose enclosing block carries a `locked` commitment marker;
- a hunk that removes or weakens a `locked` marker;
- a changed hunk inside an `acceptance_criteria` region — editing a criterion's text *is* altering what it demands.
Either condition ⇒ **auto-route to the human, regardless of the model's read.**
**A spec the change CREATES is clear, and says so** (`created: true`): every rule asks what the change does to
an *existing* demand, and a criterion that did not exist has none. The first spec always arrives through a
capability that already gates on a human — `charter`'s founding conversation, `discuss`'s requirements
conversation, `ingest`'s `reconcile` checkpoint — so routing it stops the human for a decision they just made. Failures to *compute* are untouched
by this: a created spec that also trips path drift still routes.

**Its limit is stated rather than implied, because a floor that is really a judgment in a gate's clothes is worse
than no floor.** This is a *spec-diff* floor: it catches a change that rewrites the goal **in the spec**. A code
change that quietly abandons a locked behaviour **without touching the spec** is not caught here — that is
`align`'s drift scan and `verify`'s conformance check, and it is exactly the case judgment is expected to
escalate on. The floor is a minimum, not a cap.

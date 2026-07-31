# 07 — Open Questions Register

Deliberately deferred — known unknowns, to close during build or later.

## Must close before build
- **Rest of the macro-loop** — **CLOSED**: the spine lives in `10` + renders as `.workflow/loop.md` (D47);
  the **orchestrator `CLAUDE.md` driver** is specced in `01` (D46); checkpoint = `04`, reset = the
  handoff/resume model (D48). *Intake stage closed in `09`.*
- **Intake follow-ons** (`09`) — engineering-feasibility pass **designed as the proportional-rigor decision gate
  (D69); implementation deferred to `11`** — **D88 recorded the wiring requirement (P3): the triage grades by
  `risk_class` × blast-radius, not code-centrality alone**; **demo-skill mechanics CLOSED (D102–D104 —
  serving/format · refine cap · on-disk location, `09`)**; **commitment-status storage CLOSED (D106, Phase-2 E1 —
  spec-inline, human-owned; never node frontmatter; drift check reads code→intent)** — but its **resolver
  *mechanism* is OPEN (JF5)**: *how* the drift check resolves a changed code node → its spec element is **judgment**
  (over the eager `[G]` graph + decision records + the STABLE spec), **not** the keyed `purpose.intent` lookup D106's
  prose implied — `intent` is `06`'s tier-`[D]` layer, *authored on touch*, so an untouched node carries none, and
  `purpose.actual` can't stand in (it is extracted *from* the code — circular). **Not a Phase-3 blocker** (none of
  the six increments builds the drift check); settle it when the semantic layer is on the critical path, with
  dogfooding evidence rather than ahead of it. *(Interrupt model closed: pure queue, D26.)*
- **`init` / bootstrap capability** (`10`, D28) — greenfield is straightforward; brownfield **ingest**
  (build the knowledge base + reconstructed spec from existing code) is **DESIGNED (D68) and the `ingest` skill
  is AUTHORED** (`skills/ingest/SKILL.md`) — the ingest *mechanics* (own per-stack generator, two lenses,
  three-tier seed, `CLAUDE.md`-seeded intent, unspecified-default + reconciliation checkpoint) are closed; the
  **code-map arm build thread is CLOSED (D77/D79)** — five precise arms built + ground-truth-measured (Python,
  JS/TS, Go, Java, C#); C++/Rust/PHP stay on the tier-0 floor by design. The runtime residual **closed**:
  brownfield `/start` was driven (D130) and then **lived** in a real onboarding (2026-07-20) — correctness held;
  the first-run *experience* did not, opening **Phase 6 (D131–D135, `11`)**: one-motion `/start` · console
  front-door · bootstrap progress · bootstrap context law — decided + BUILT 2026-07-21; RE-DRIVEN 2026-07-27 (D138).
- **Commit-message convention** — **CLOSED (D32):** Conventional Commits + `Refs:`/`Closes:` trailers.
  Remaining sliver: whether the workflow's own generated commits carry the `Co-Authored-By` trailer.
- **Agent roster v1** — **CLOSED in `10`** (names, I/O contracts, skill-vs-agent, topology). Remaining
  sliver: the collision-model **independence test** (`02`) — waves decided the grouping (D36); the
  `prioritize` interrupt model is closed (pure queue, D26).
- **What a checkpoint is** (`04`) — **closed (D96–D98):** the judgment/action taxonomy + trigger rule, the
  verb-enum verdict + plural machine-verified setup gate (`shared/schemas.md`), and the MVP help set (contextual
  steps + verified deep-links + breadcrumbs; screenshots/screen-share/agent-automation deferred).
- **Outward-action permission model** (`04`, D35) — **CLOSED (D105, Phase-2 E2):** it is **not** a checkpoint kind —
  an outward action doesn't park the ticket, so it rides a **transactional-outbox** queue (`.workflow/outbox/`), not
  the checkpoint gate. Two layers: `guard.sh` (non-overridable floor) + a coarse **`config.outward` allow|ask**
  allowlist (standing pre-auth, default all `ask`); the loop **defers + continues**, and a console **`kind: release`**
  batch-approval (explicit `action_ids`) drains the queue. State-bound + TTL'd + no durable ledger. **D60 resolved:**
  `.workflow/checkpoints/` is **retired → `outbox/`** (setup lives in `parked/`, publish in `outbox/`; the external
  consequence is the audit, so no ledger). Affects `commit`'s deferred push, `create-issue`, `close-issue`.
  *Surfaced 2026-06-29 (live: the harness gated a push to `main`).*
- **Website screen list** (`03`) — **CLOSED (D99):** a read-only supervision cockpit (home) · checkpoint console ·
  "my requests" · roadmap/backlog; the map is a **tab, not the home, not the first cut**; snapshot-poll refresh
  (no SSE in MVP); the contact-UX = verdict + intake forms + the "my requests" async-feedback surface.
- **Disk layout** (`05`) — the full file tree + read/write protocols. *(Docs-root unified under
  `<project_root>/docs/` — spec + architecture + knowledge + decisions — D62; diagrams inline, D41.)*
- **Orchestrator hooks** (D58) — `hooks/guard.sh` enforces **secret-scan** + **verify-before-commit** (hard
  blocks), **hardened D87** (fails *closed* without python3, expanded secret patterns, missing-verdict block, and
  it fires under bypassPermissions). D87's claimed "robust `git … commit` match" was **false as built and is now
  real (D110)** — the flags-only regex missed any git global option taking a *separate value*, so
  `git -c core.pager=cat commit` slipped past with a secret staged; both gates now key off a **parsed
  subcommand**. **D87 closed the command-chaining gap
  at the guard level** — an obscured `cd x && git push` / `$(…)` is now hard-blocked so it must run directly
  (D110 revised *why*: not so a settings `ask` can fire — that `ask` is gone for the outbox classes — but so the
  guard's own **push floor** can parse the refspec); `pre-commit.sh` is the git-native backstop (secret + verify +
  staged-diff). **The push floor is BUILT (D110)** — resolve the refspec (incl. `HEAD:main`, leading `+`,
  `--all`/`--mirror`, bare `git push` via upstream/`push.default`), **block any push to a protected branch**
  (`{main, master}` always + `config.guard.protected_branches` add-only), and secret-scan the outgoing range;
  fails closed on an unparseable refspec.
  Still open: **build-once-per-wave** (a wave-coordinator, not a command gate). The fuller **outward-action queue**
  (batching / standing pre-auth beyond the `ask`+guard pair) is **CLOSED — the D105 outbox model** (`config.outward`
  allow|ask + `.workflow/outbox/` + a `release` batch-approval; `guard.sh` stays the non-overridable floor), with
  **D110** binding it: the harness leaves the outward path entirely, so `config.outward` is the sole policy owner.
- **First-launch workspace trust** (D58) — the shipped `settings.json` + hooks are **ignored until the folder
  is trusted**, and the trust **dialog doesn't render in some terminals (e.g. WSL)**; `/start` + setup docs must
  give the manual `hasTrustDialogAccepted` flag method, not just "accept the dialog." (Validated: after trust,
  the dogfood run took **zero** local permission prompts.)
- **`@import`-survives-`/compact`** — a one-session test; if it re-resolves, the brownfield install (D50) can
  switch from the inline marked block to a cleaner `@import`.
- **Console + comms bus** (`03`/`05`) — the **critical-path runtime dependency**. **Cluster A is now CLOSED:** the
  block/resume mechanism (D90/D91), the **A2 bus contract** (D93 — single-writer ownership + atomic-publish + a
  two-mechanism protocol [sync reads · async commands] + one typed inbox; the orchestrator is never an HTTP
  responder), the **A3 lifecycle** (D94 — a session-independent detached daemon, ensure-running via lock-authority,
  HTTP-stop + idle-janitor), and the **A4 trust** model (D95 — capability token + Host-allowlist + loopback bind).
  **Cluster B (the console) is now CLOSED (D99–D101):** the console model + screen list + snapshot-poll + "my requests"
  surface (D99), the stack (D100), and the two-event attention taxonomy (D101). **Cluster D (the demo skill) is now
  CLOSED (D102–D104 — serving/format + sandbox-CSP isolation · refine cap · on-disk location).** **Cluster E
  (cross-cutting) is now CLOSED (D105–D107 — the outward-action outbox · commitment-status storage · project-map
  residuals + loopback-only-release), so the Phase-2 DESIGN is COMPLETE (next = Phase 3, `11`).**
- **Real dispatch validation** — **RESOLVED (D128).** The first real end-to-end greenfield loop drove both leaf
  agents through the Task tool with a real model (`research` via `decision-engineer`, `setup-guide` via a setup
  checkpoint) — structured returns intact, orchestrator context stayed clean (hub-and-spoke holds). The agents
  resolve only **namespaced** (`dev-autonomous-workflow:<name>`), not bare.
- **Package install** — **plugin packaging BUILT (D125):** the repo self-markets (`.claude-plugin/marketplace.json`,
  `source: ./product`) and installs via `claude plugin install`; `/start` copies the shipped scripts/hooks out per
  `product/MANIFEST.json`'s `install` map, resolved from `${CLAUDE_PLUGIN_ROOT}`. Loose `.claude/` files remain the
  manual-install fallback (D57). Open follow-on: the **version-update/migration skill** (below).
- **Adoption follow-ons (D38–D51)** — the **retention & archival law** is **CLOSED**: Layer 0 write-law leak
  closures (D59–D60) + Layer 1 cap-and-archive read law (D61). What remains under it: **Sessions distillation**
  (deferred *mechanism* — lossy/model-authored; **D88 captured the rule (P2)** that a postmortem distills to a
  one-line Lessons pointer *before* drop, so retention never evicts an "avoid" raw) and `K`/threshold tuning
  against real runs. Also: whether `verify` samples the real `git diff` vs trusts the `changelog` (#8).
- **Rules baseline + `/start` enforcement wiring (D40) + two-tier drift defense (D65/D67) — AUTHORED
  2026-07-01.** The `rules/*.md` baseline (enforced-by tags), the `shared/format.md` rules convention, the
  `/start` step-4 enforcement wiring, the `commit` mechanical-gate step, and the `prioritize` drift-ticket note
  are written. **RESOLVED (D127):** `checks.sh` ships as a **fixed runner** (`templates/checks.sh`, copied verbatim)
  + a generated `.workflow/checks.env` data file — the `--fix`/`--check` dispatch + the coverage-gate loop are no
  longer LLM-freehand (refines D67), and it was driven end-to-end on a real greenfield bootstrap (`~/p5-test`).
  Residual: stack-enforcer wiring (`checks.env` commands + the `rules/` `enforced by:` tags) is **deferred to
  `tech_stack` lock** — a faithful greenfield has no stack to detect at `/start` (D127). **That deferral had no owner
  (F2, D128) — now RESOLVED (D129):** the **stack-wiring step** is deferred by greenfield `/start` and **the
  orchestrator re-runs it at `tech_stack` lock** (a router-owned one-time transition, `loop.md`); and the
  load-bearing half — `checks.sh --check` now **fails closed when `project_root` holds source but no stack gate is
  wired** — makes a forgotten trigger a loud block, not a silent skip. (F3's shared `verify_check.py` and F1's
  interactive-only `/start` + post-install verification gate landed in the same slice — D129.)

- **`handoff.md`'s durability mandate (raised by D117) — RESOLVED (D128): the premise was largely false.** The
  worry was that the orchestrator's text-writing tool "cannot express a rename" so the prose anchor could tear on
  crash. Reproduced before deciding: the harness **`Write`/`Edit` tools are atomic** — they publish via temp +
  `rename` (verified, the inode changes on overwrite), so a session killed mid-write leaves the **previous** file
  whole, never torn (a naive in-place truncate-write, by contrast, tore a copy to a fragment on the same kill — so
  the harness provides the guarantee the model can't *express*). The one real rule: **never rewrite `handoff.md`
  via a `Bash` `>`/`tee` redirect** (in-place truncate — would tear); use the tools. Residual is only power-loss
  `fsync` durability, which **git already backstops** (committed each item; a cold start rebuilds from
  `handoff.md + git log`). **The call:** downgrade the `schemas.md` claim to the real guarantee + the no-redirect
  rule — **no shipped publisher** (it would re-buy only what git backstops, at the cost of a new must-call-it
  discipline, i.e. another F2/F3-class fail-open surface). `drain.py` still writes its machine block fully durably.

- **The console page's legibility is now reviewed (D120), one nit left.** The twice-carried "nobody has rendered
  the page in a browser" residual is **closed** — the live cockpit was rendered in headless Chrome and read as
  legible (the pending-checkpoint card + verdict form, outward/release, request-work, "my requests"; overdue
  checkpoints get a red bold "OVERDUE —"). **Remaining nit:** the deadline renders as a raw ISO string
  (`2999-01-01T00:00:00+00:00`) where a human reads relative time ("due in 3 days") far better — a small
  client-side formatting polish, non-blocking.

- **The away-alert dedup key collides on a same-second re-park (D120) — accepted bound.** The daemon keys alert
  state on `ticket_id` + the parked record's absolute `deadline` (`parked_seq` was removed as a field with no
  writer). A ticket that resolves and re-parks within the same `deadline` second would be treated as
  already-alerted. Accepted, not open: a re-park almost always yields a later `deadline` (a fresh `now +
  deadline_hours`), so the collision needs two parks inside one second — and the failure is one missed *second*
  alert on the same ticket, not a lost verdict. Revisit only if a real run shows sub-second re-parks.

## Deferred (post-MVP or later)
- **Knowledge graph regenerate-vs-incremental** (`06`) — **RESOLVED (D78):** static layer regenerates + the durable
  *observed* layer is merged on regenerate. New open follow-ons from D78: node-ID stability across renames;
  observed-edge staleness/decay (couples with retention D71); the non-Python runtime-capture mechanism (per stack).
- **Model + effort routing** map (`01`).
- **Collision-model independence test** (`01`/`02`) — waves grouping decided (D36).
- **Arbiter** batch-vs-one input contract (`01`).
- **Local relaunch "runner"** (`01`, D90/D92/D113) — **BUILT as Phase-3 increment 6 (D123).** Hosted on the D94
  daemon as a job (`config.runner.enabled`); it **retires** the manual-`/clear`-and-re-`/start` stopgap and is the
  **last link** of the away-channel. The liveness marker had to be *published* (a `/proc` scan is unsound), so a
  human starts via the shipped `loop.sh` launcher and the runner spawns `flock -n orchestrator.lock claude -p …`.
  Driven end-to-end on a real model: the runner-spawned `claude` drains a durable verdict and advances the watermark.
  *Residuals now tracked here:* (a) the **bare-`claude` bypass** — a human who enables the runner but starts bare
  `claude` is invisible to it (D109-consistent operator responsibility, documented not fenced); (b) an **up-front
  trust gate** was deliberately NOT built — an untrusted workspace is a *warning* in `status`, not a spawn-block, so
  a misread can't silently disable the runner (the stall-timeout is the real backstop); (c) a possible **`/start`-time
  nudge** when `config.runner` is on but the current session doesn't hold the lock (it cannot retro-acquire, so a
  nudge is the ceiling) — a fast-follow, not built. Auth (subscription vs API key) confirmed: it runs on the user's
  own `~/.claude`.
- **Website stack** (`03`) — **CLOSED (D100):** a stdlib-Python detached HTTP daemon (`http.server.ThreadingHTTPServer`)
  + a zero-build, CSP-clean static page (vanilla default, Preact+htm escape hatch); the daemon serves a strict
  `script-src 'self'` CSP. No install/build step; `python3` is the only added dependency (already required).
- **Project map + flow view (`03`, D70) — feature + architecture decided, these bits open.** (1) Map as its
  **own tab vs the console home/overview** — **DECIDED (D99): a tab, not the home, and not the first console cut**
  (it is Mode B *explore*; the MVP is Mode A *supervise*). (2) A captured flow as a **first-class knowledge artifact**
  (versioned, regenerable, `06`) vs
  **ephemeral** (on-demand, discarded — but D78 leans **durable [D] layer**). (3) The **runtime-capture mechanism**
  — **decided (D78):** `verify` is the observer (it already runs the affected flow); mechanism = `sys.monitoring`
  fire-once (Py 3.12+, measured 1.0×) with coverage-harvest (~1.5×) as the universal fallback; trigger selectively
  where an arm's `known_gaps` flag dynamism. Open: the per-stack mechanism for non-Python (reasoned, not measured).
  (4) **Remote-control auth** — **CLOSED (D112):** the unauthed warning-only tunnel was unbuildable (D95's
  "the loopback token is never tunnel auth" contradicts D107's "read/verdict ride the tunnel", since those
  endpoints are token-gated), and D107 under-rated verdicts — D90 makes a verdict an *authoritative prompt*, so a
  forged one is **agent control**. Now: a **structural two-socket split** (loopback socket = full surface incl.
  `release` + credential-bearing setup verdicts, never fronted; a reduced remote socket = reads · opinion verdicts ·
  static demo) served **only** behind a **declared identity transport** (Cloudflare Access | Tailscale), with a
  distinct remote token (QR + URL-fragment pairing) as the second factor. Auth moved from *reserved* to
  **required-for-any-remote-surface**. The other three residuals are confirmed correctly parked (tab-not-home D99;
  durable-flow ≈ D78; capture-mechanism D78, non-Python open). *Project-map residuals CLOSED as E3.*
- **Automated testing**, **test-from-anywhere**, **paid device/QA platform** (`04`) — designed-for,
  not built.
- **Target OS/FS portability family (D89 + D93/D94/D95)** — a cluster of "the target isn't POSIX-ext4" gaps, tracked
  together:
  - **Shipped-glue interpreter (D89)** — the shipped bash glue (`guard.sh`, the fixed `checks.sh` + generated
    `codemap.sh`) assumes a **bash interpreter on the target OS**; unverified on **native Windows** (git-invoked `pre-commit.sh`
    likely survives via Git-Bash; the Claude-Code-invoked glue is the risk). Fix later with a targeted fallback (a
    thin Python launcher — `python3` is already a hard dependency — or a documented Git-Bash/WSL requirement),
    **not** a `.sh→.py` refactor (the D71 bash-glue/python-logic split stands).
  - **Runtime coordination on a native FS (D93; measured + resolved — D115)** — atomic `rename`/`fsync`/`inotify`
    are weak-to-broken on network-style mounts (NFS; WSL2 `/mnt/c` DrvFs/9p). The runtime paths `05`'s layout tree
    marks **`pin`** are relocated to a native-FS path (the tree owns that set — D114; this register does not restate
    it, which is how this copy sat stale, missing `secrets/`, from D111 until D114); `/start` detects a
    DrvFs/network mount and relocates-or-warns, recording where via the gitignored `runtime.json` pointer. **What
    was measured (D115): file *mode* is the guarantee that actually fails on 9p (a 0600 create returns 0777,
    silently) — `flock` does not fail at all, so "flock is unreliable on DrvFs" is retired as a reason to pin.**
    **DRIVEN on the real 9p mount (D130):** the relocation *step* (unexercised until Wave 2) works — a real model
    detects the mount and relocates; the runtime half lands native ext4 at `0600`, the daemon keys per-project via
    `runtime.json`, `probe_mode` warns on 9p / silent on ext4, and the D129 verify gate fails closed on a genuinely
    relocated `state.json`. Residual is the **native-Windows** path (no WSL 9p), still unexercised.
  - **WSL2 bus lifecycle (D94)** — a detached daemon can't hold the distro VM open; the bus dies ~8s after the
    last terminal closes and re-spawns on the next `/start` (owner-accepted; `enable-linger` / `vmIdleTimeout=-1`
    the opt-in upgrade).
  - **Restricted file modes are not portable (D95; widened by D115 from "Windows" to "any mount that ignores
    mode")** — native Windows has no `0600` (the bus token needs explicit `icacls` ACLs), **and the WSL `/mnt/c`
    mount ignores the mode outright** — measured, from Linux, silently, returning `0777`. The shipped rule is
    therefore *verify, never assume*: create with the mode, then `stat` it, and surface a filesystem that ignored it
    instead of reporting a protection that does not exist. The daemon does this today; the residual is the Windows
    ACL path, still unexercised.
  Validate the family together when a real target-OS decision is forced.
- **Brownfield bootstrap vs freshly-adopted gates (D130, deferred) — surfaced 2026-07-20.** A brownfield `/start`
  wires the stack gates at step 5, then step 7's bootstrap commit runs them **repo-wide on the adopted, unmodified
  code**. If that code does not pass the freshly-adopted lint/typecheck/test — or the deps (`node_modules`/venv)
  are not installed in the working tree — the bootstrap commit could **wedge init** (the F2 fail-closed backstop
  firing on code the human did not write). Mitigated in principle by *adopt existing **passing** gates* (a project's
  own configs, which its code already passes), but the deps-availability and does-adopted-code-actually-pass cases
  are untested (Wave-2 stripped the venv/`node_modules`, so the real brownfield gate-run was not exercised). Surface
  when a real deps-present brownfield build is driven — or, most likely, in first dogfooding.
- **Project-state view (`03`/`05`/`06`) — user-raised 2026-06-30.** No single synthesized "where is this
  project" surface — *what's done · how the pieces connect · what's left*. The data exists but is scattered
  (`00–11` + `08` decisions + this register + `handoff.md` + `backlog.md` + the `docs/knowledge/` graph). The user
  feels the gap **in this spec project itself**, and it bites harder on code projects — and it's a prerequisite
  for eventually **self-hosting** (driving this project's development with this project). Likely a **generated**
  view (D38 — not a hand-maintained doc that rots): a `status`/`map` skill or a console screen synthesizing
  roadmap + backlog + decisions + graph on demand. **The `graph.json` cluster map (D70) is its "how the pieces
  connect" face** — the structural half of this surface.
- **Public-facing repo identity + onboarding (`00`) — user-raised 2026-07-18; CLOSED 2026-07-20 (D125).**
  The one-repo-vs-two fork is **decided: ONE transparent repo.** The shipped plugin lives under **`product/`**
  (the plugin root; boundary = `product/MANIFEST.json`, which the leak gate, `/start`'s install step, and the
  release build all derive from); the construction record — the numbered docs + the decision log + `reviews/` —
  moved to **`docs/design/`**; a product front-door `README.md` replaced the spec-index (the hardcoded local
  "Home" path dropped); and the skill `description:` fields were scrubbed of construction vocabulary. The
  **distilled-package** arm was rejected — a sync seam + lost dogfooding, the exact drift this project exists to
  kill (the construction record IS the workflow's own output). Full record: D125. **Still open (below):** the
  **framework version-update skill** (keeping *installed* copies fresh — promoted into Phase 6, D135) and the
  **project-state view** (self-hosting prereq); `/start`'s full bootstrap runtime has since been **driven
  (D128/D130) and lived (2026-07-20)** — the experience findings are the tracked **Phase 6** slice (D131–D135, `11`).
- **Framework version-update skill (`10`, D57) — user-raised 2026-06-30.** The package is now a **public
  repo**; consuming projects install a snapshot (`.claude/` skills/agents/commands + `templates`/`shared`/
  `hooks`). As the framework evolves (fixes, new skills, schema/format changes) installed copies go **stale**,
  and stale references mislead the loop. Need an `/update` skill that pulls the latest package and re-applies
  it, **reconciling local customizations + migrating schema/format changes** (a version bump can change
  `state.json`/`schemas` shapes — not a blind overwrite). The natural follow-on to packaging (D57); the
  framework-level analogue of the retention/freshness law. **PROMOTED into Phase 6 (D135, 2026-07-21)** — the
  first real out-of-tree install (`idea testing`) now exists and will go stale; constraints pinned by that run:
  **version-stamped installs** (nothing in a target records its package snapshot — no migration key today) ·
  **regenerate `[G]`/`graph.json` under a new schema, never clobber `[D]`/adopted docs** (D39/D50 + D130's
  case-variant adoptees) · **diff against the manifest `install[]` map** — real targets carry a pre-existing
  `.claude/` the skill must not treat as its own. **Design SETTLED (D137, 2026-07-26):** a 3-way file taxonomy
  (package-refresh · target-preserve · regenerate-from-code), version-stamp-driven, + four calls — a **command**
  (sibling of `/start`, interactive-only) · **package owns `.claude/settings.json`** (user owns `settings.local.json`)
  · **record the install-set** → remove only proven orphans (flag-only when unrecorded) · **unify greenfield onto the
  sentinel-marked block**. Build sequenced **after the Phase-6 re-drive** (two small `/start` tweaks ride it).
- **Interaction-model expectation vs the locked terminal/bus split (D132) — surfaced 2026-07-20; maintainer's call
  now MADE (2026-07-26): he wants browser-primary conversation; async-chat is the frontrunner; build DEFERRED behind
  a proper re-drive.** D132 ruled the first-onboarding confusion a *surfacing* defect and reaffirmed the lock (D93
  dialogue = terminal, bus = requests + bounded clarifications; D99 console = read-only cockpit + contact-UX; the
  orchestrator is a batch consumer — a browser chat would sit in Claude's request path, D3). Pressed on the open
  sliver, the maintainer confirmed he genuinely wants to **talk to the project and get responses through the
  website**, not merely file intake. The resolution that honours the master rule is **async chat**: the browser
  writes to `inbox/` (D99/D108 — already the intake path), the running loop drains it at a turn boundary and appends
  free-text replies to a durable conversation thread the console renders — **the daemon never calls Claude** (no
  request-path component), so it is mostly a presentation layer over the D108 drain + D123 runner. The irreducible
  cost is inherent to the master rule: a **cold-start (spawn + rehydrate, real tokens) per message whenever no loop
  is live** (warm/piggyback when one is); an **always-on runner** (D123, off by default; dies with the terminal on
  WSL — D94); the **terminal-only first bootstrap** (D131/F1); and **D90/D112 auth** the moment it is reachable
  beyond localhost (a redirecting message is *agent control*). **The call: do NOT build it yet** — the maintainer
  first *experiences a proper re-drive* of the current Phase-6 website (front-door + progress + intake), because the
  async-chat gap may read differently once the built-but-undriven surface is actually seen, and building
  conversational replies on an unverified progress/intake layer is the "reasoned, not driven" trap. Revisit
  immediately after the re-drive (roadmap Phase-6 sequence). *(True sync streaming chat stays off the table — it
  requires the daemon to become a Claude proxy, overturning the founding premise.)*
- **Phase-6 re-drive follow-ups (D138, 2026-07-27) — three package findings LOGGED, not yet fixed.** The
  re-drive confirmed D131/D132/D133/D134 and fixed the sharp one (the `verify_check.py` bootstrap-commit
  contradiction, in-commit), leaving three: (1) **mid-flow human questions** — the bootstrap interrupted the human
  for clarifications instead of resolving them (`research`/`decision-engineer`) or batching them to the reconcile
  gate; `ingest` should default `unspecified` and defer confirmation to reconcile, so a mid-flow interrupt breaks
  the one-motion-to-the-first-gate principle (route-fix: decidable → `decision-engineer`, judgment → the reconcile
  question set). (2) **the `--check` stack lint scoped over the vendored `.claude/scripts/`** (143 findings on the
  workflow's own code) — the stack gates must scope to `project_root`, never `.claude/` (extends D127). (3)
  **`xdg-open` hung ~2 min on WSL** before the `explorer.exe` fallback — the `/start` step-5 browser-open chain
  needs a per-attempt timeout. Also confirmed live: the **brownfield-adopted-gates** question (above) — the repo
  failed its own gates and the model scoped `checks.env` to the staged diff + filed the debt rather than wedging
  the bootstrap; confirm that as the intended behaviour when the fixes land. These ride the next Phase-6 slice
  (bundle with `/update` or a quick fix pass). → `08` D138.
- **Doc-authoring agent (reserved — D65; trigger fired, still not added — D68).** A specialized
  heavy-doc-reconstruction worker (e.g. brownfield `ingest` building a spec from code — a generative task that
  doesn't fit `execute`'s plan-driven model). The "revisit when building brownfield `ingest`" trigger **fired
  (D68)** and the call held: **`ingest` is a thin skill over the existing leaves** (`research` read →
  `document` write), **no new agent** — reserved still, added only if the generic workers prove insufficient in
  a real ingest run. Cousin of the open "engineer agent?" slot (`02`).

## Drive-found, logged not fixed (D138 re-drive, 2026-07-27)
Two of the four D138 findings were fixed in D139 (the `verify_check.py` bootstrap carve-out; the `xdg-open` WSL
hang). These two stay open because each is a design change, not a patch:
- **Mid-flow human questions have no route.** During the bootstrap motion the model asks the human things that
  are really *decisions* or *reconcile* material, and they land in free conversation — outside the machinery that
  is supposed to durably hold a question until it is answered. They should route to `decision-engineer` (a real
  open build decision) or to the reconcile gate (an understanding gap). Open: which of the two is the default,
  and whether a mid-motion question should be allowed to park at all or must always defer to the reconcile
  checkpoint. Touches `loop.md` + the orchestrator brief, so it is not a `/start` tweak.
- **`checks.sh --check` stack-lint scoping over the vendored `.claude/scripts/`.** The stack gates are scoped to
  `project_root` (D127), but on a brownfield install where `project_root` is `.`, the workflow's own installed
  `.claude/scripts/` sits *inside* that scope — so a repo-wide linter lints the package we vendored in. Related
  to, but not the same as, the greenfield leak D127 already fixed. Open: exclude the workflow's own paths in
  `checks.env` generation, or teach `checks.sh` a standing exclusion (a fixed-runner change, so it needs the
  D127 care).

## Machine-move remediation (D140 audit) — **the five design questions are CLOSED by D141; all of 7b is BUILT (D144), DRIVEN (D146), and the one question that drive opened is CLOSED by D147**
All five retired: the re-bind capability is a `/rebind` command with four routing arms (detectors route, none
heals); re-binding is neither recovery nor re-creation but a **three-case probe** the runner classifies;
`handoff.parked[]` becomes a machine block only by giving parking a code writer (`bus.py park` — **and, the build
found, an `unpark` sibling: prose was accidentally self-correcting because the whole file was rewritten each
handoff, so a persisted block with no remover would report answered checkpoints as open forever**); the git hook is
re-asserted from `SessionStart`, non-clobbering (and `07`'s "same scrutiny as F3" is corrected there — the gate is
already disarmed on every clone, so re-asserting can only arm it); secrets get a declared `config.json`
`secrets_required[]`, with point-of-use fail-closed kept as the floor. The build items live in `11` (Phase 7a/7b).

~~**OPEN — what shape is a `setup` verdict's `returns`?**~~ **CLOSED by D147 — a name-keyed map, and the question
turned out to sit downstream of a bigger one: `returns` had no PRODUCER.** Nothing in the package could emit one —
the console's verdict form posted `{outcome, notes}` and nothing else, there was no CLI verb, and no document
described the POST — so the shape was re-invented per invocation by whoever hand-wrote the request, which is the
real reason "whether the feature works is luck". D99 had *specified* the form to carry `returns`/`tasks[]` plus the
setup steps and deep-links; increment 3 shipped a strict subset and was tagged BUILT, the component COMPLETE, with
only a *legibility* residual stated — so a capability gap read as polish. The candidate `name` field was **rejected**:
task identity already lives at `tasks[].id`, so a second identifier on the same entry is a silent-failure generator,
and the driven `[{id, …}]` shape was the wrong *slot* rather than a mis-keyed field. The declaration also flips the
matcher — generosity was only a virtue while the shape was undeclared. Full call, and the three things the build
forced, in D147.
**Both residuals are DISCHARGED by the D142 build** — and one of them fired:
- ~~**What counts as a "weak mount", portably.**~~ **Closed: it is measured, not classified.** `bus.probe_mode()`
  already did the only correct thing — a `0600` create then a `stat`, which asks the question directly instead of
  keeping a `9p`/`drvfs`/`cifs`/`nfs` table that would be wrong on the next platform. The build split it into a
  tri-state `mount_honours_modes()` → **True / False / None**, and `Paths` stops **only** on a measured `False`.
  The undecidable arm is what made the fallback unnecessary: `/rebind` ships **fail-closed**, not loud-warn.
- ~~**Does `prioritize`'s GC retire a local `issue` with no `github_ref`?**~~ **Closed — and the answer was no.**
  `schemas.md` said a local item closes on its backlog done-flip and `prioritize` collects it; `prioritize/SKILL.md`
  step 1 named only two rules and the issue rule was `github_ref`-only. The owner and the skill disagreed, and the
  skill is what the model reads. Extended to *any entry `commit` flipped done*, naming local issues explicitly.

**The D143 drive then opened the class the audit never enumerated — the ENVIRONMENT, not the files. Both questions
are CLOSED by the D144 build.**
- ~~**Where the bindability probe reports from.**~~ **Closed: `rebind.py apply`, plus one routing clause on the
  pre-commit hook.** The mechanism was never in doubt (run `checks.sh --check` the way the hook runs it — same
  command, cwd and shell — and report whether it exits clean; never a toolchain-detection heuristic, which would
  need to know which side of the WSL/Windows boundary each command belongs to). The *placement* was, and the
  standing `SessionStart` probe lost on its own merits: it runs the project's whole test suite before a session can
  begin, which is **the master rule inverted**; a harness timeout kills a slow suite and a killed probe is
  indistinguishable from a failing one; ~~it is invisible to `claude -p`~~ (**retracted by the D146 drive** —
  `additionalContext` does reach a `-p` session; the placement call stands on its other three legs); and
  making it cheap requires a
  cache-invalidation rule that is a toolchain heuristic wearing a different hat. `check` was ruled out too — its
  contract is "writes nothing", and a `TEST` command writes caches. The machine transition is the one moment the
  answer changed and nobody has committed yet; **a toolchain that rots later is caught by the hook, which already
  ran the gate and simply never named the other possible cause.**
- ~~**Whether the package should detect and route the host's limits.**~~ **Closed: detect and route — the
  `/rebind` shape, as suspected.** One limitation explains a family (**DrvFs cannot `chmod`**: a `0600` create
  comes back `0777`, `git remote set-url` fails on its lockfile, `npm install` fails on package bins), and the
  consequence stands — **on such a mount a WSL-side agent cannot install the toolchain, so there is a blockage
  class the loop provably cannot clear itself.** The package now says so rather than staying silent: the probe
  reports it, the loss is filed as a typed backlog issue, and `commands/rebind.md` instructs the judgment half to
  **name it as unfixable-from-here** when it is. Two rules the build fixed in place: the probe **reports an
  observable and does not diagnose** (missing toolchain vs. genuinely-red test is the reader's call — inventing
  that distinction is the rejected heuristic), and the gate's **output tail never enters the committed loss**,
  because `backlog.md` is committed and the one control that would catch a secret in arbitrary subprocess output
  is the staged-diff scan in the very gate that just failed to run.

**One residual OPENS from the D142 build** (noted, not fixed — deliberately):
- **`hooks/verify_check.py` carries its own copy of the runtime resolver** and degrades to the workflow dir on a
  dead pointer, so it neither routes to `/rebind` nor sees the weak-mount rule. It is not one of D141's four arms
  and it fails **closed** on the gate it guards regardless — but it is now a second, diverging resolver. Either it
  earns a shared read-only helper or the duplication gets stated as intended. Touching the verify gate to add a
  warning a `pre-commit` hook cannot usefully display is the trade that kept it out of 7a.

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
  trust gate** was deliberately NOT built — **REVERSED and BUILT (D173)**: that call rested on "the stall-timeout is
  the real backstop", and the backstop was **measured inert** (an untrusted `claude -p` answers and exits 0, so it
  never reaches a timeout that only reaps a launch still *running*). The gate now blocks the spawn and alerts once;
  the "a misread must not silently disable the runner" worry survives as the **fail-open rule on the read**, not as
  the absence of a gate; (c) a possible **`/start`-time
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
  feels the gap **in this spec project itself**, and it bites harder on code projects — ~~and it's a prerequisite
  for eventually **self-hosting**~~. **SCHEDULED 2026-08-05 as Phase 10c (D175), on the FIRST of those two reasons
  only:** self-hosting is dropped, so the prereq argument is gone, but "the gap is felt reading a project, and it
  bites harder on code projects" is independent and survives. **Consequence — it is built for a TARGET project**,
  not to read this repo's `docs/design/` (the D125 boundary; also the only form dogfooding can validate). Likely a **generated**
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
  **project-state view** (no longer a self-hosting prereq — re-argued and scheduled as Phase 10c, D175);
  `/start`'s full bootstrap runtime has since been **driven
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
- **~~Interaction-model expectation vs the locked terminal/bus split (D132)~~ — CLOSED 2026-08-04 (D169): 8b is
  BUILT + browser-driven (`ad9d910`), and Phase 8 is complete. The history below is kept because it owns the three
  researched build constraints (which held) and records an error in scale worth not re-making; the resolution of all
  three open calls is at the end of this entry.** *Surfaced 2026-07-20; maintainer's call
  MADE (2026-07-26): he wants browser-primary conversation; async-chat was the frontrunner; build DEFERRED behind
  a proper re-drive.* D132 ruled the first-onboarding confusion a *surfacing* defect and reaffirmed the lock (D93
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
  **The re-drive HAPPENED (D138, 2026-07-27), so the deferral has expired and 8b is the Phase-8 live pointer.**
  **Three constraints researched 2026-08-04 against live docs, before any build — none of them a decision, all of
  them things a build must not re-derive:**
  - **The persistent-conversation route is CLOSED.** The Agent SDK's `ClaudeSDKClient` is exactly "a long-lived
    process accepting new input across turns", but it is a third-party dependency and this package is **stdlib-only
    by construction** (the same rule that killed a pip tokenizer in D167). So async chat is a `claude -p --resume
    <session-id>` subprocess per message, as the D123 runner already does. The lever is `--resume` plus prompt
    caching, **not** process persistence, and per-message cost grows with thread length because resume re-sends the
    accumulated history. Sessions are `cwd`-keyed on disk (`~/.claude/projects/<encoded-cwd>/<id>.jsonl`) and local
    to the machine — a resume from the wrong directory silently starts a *fresh* session.
  - **The master rule is looser than D132's phrasing.** `00`'s rule prohibits a **hosted** program that injects into
    or routes the Claude session *on behalf of users*; everything local is clean. D132's "the daemon never calls
    Claude" is therefore stricter than the rule requires — a **local** daemon spawning a **local** CLI on the user's
    own auth is exactly what the D123 runner does today. This does not overturn D3; it removes an option D132's
    wording had foreclosed, and the reply mechanism should be chosen on cost and liveness, not on a rule that does
    not actually bite.
  - **The WSL precondition is a one-line opt-in, NOT an open engineering problem.** The bus daemon dies ~8s after the
    last terminal closes (D94), which would leave a browser-primary surface with nothing to talk to whenever the
    human is away — but D94 records the caveat as **owner-accepted** with two documented upgrades (`loginctl
    enable-linger`, `.wslconfig vmIdleTimeout=-1`), and D123 already **surfaces it in `status`, never implied**.
    "Carried not solved" means the package does not solve it *for* you. A first pass of this analysis read it as a
    blocker and proposed deferring 8b behind fixing it; that was **wrong in scale** and is recorded here so the next
    session does not re-make the error.
  **All three remaining calls are CLOSED by the build (D169, 2026-08-04; 8b is BUILT + browser-driven, `ad9d910`).**
  They were settled in design, before code, as this entry demanded:
  - **Storage — RUNTIME, not committed.** A committed transcript is a **second copy of every decision it contains**
    (a straight D80 violation — the spec, backlog and decision record already own those facts), and the argument
    for committing collapsed on a finding: the conversation Claude actually resumes lives in **its own session
    file**, machine-local and cwd-keyed, so committing buys a readable log and **not** a resumable conversation.
    Durable outcomes land with their existing owner. Retention is the odd one out in this package — it governs
    **spend, not bytes** (resume re-sends the thread), so the knob is a **rotation** at
    `config.thread.rotate_at_tokens` (default 200 000, owner's call) that hands off and starts a fresh session,
    which is D92's disposable-conversation law applied to the thread.
  - **Classification — the HUMAN, at the console.** Two affordances, no model in the routing path. **The premise in
    the paragraph above was INVERTED, and that is the finding that sized the whole slice:** "a question wants the
    knowledge base" assumed a knowledge-base *query* capability existed. It did not — all 18 shipped skills
    *write* the KB or read it as input to work, and **nothing answered a human's question**. So the *request* arm
    was the one already served end-to-end (intake → ticket → "my requests"), and the **question arm was the entire
    net-new substance of 8b**. Pressure-testing also found a **third** bucket the two-way split hid: *status*
    ("is the deploy done?"), which the cockpit already answers for free with no spawn at all — deliberately given
    no new affordance.
  - **Loopback-only — yes, and it cost no code.** `REMOTE_KINDS` is a *positive* allowlist, so a new kind is
    loopback-only by default; the call was to decline to relax it, pinned by a test. A question is run into
    `claude -p` verbatim, so it clears the D112 "authoritative prompt" bar **more easily than a forged verdict** —
    a verdict's `notes` is free text bolted to a bounded decision, a question IS the whole prompt. The console
    *reads* the conversation remotely (a read is what Socket A serves) and the **composer** is loopback-only.
    If it ever goes remote it rides the **Tailscale-only** carve-out, never a TLS-terminating proxy.
  **One constraint above is CORRECTED by measurement (D169):** the WSL opt-in is one line *in general* but **not on
  this machine** — there is no `.wslconfig`, and `pid1` is `init(Ubuntu)` with **no systemd**, so the
  `loginctl enable-linger` arm requires enabling systemd in `/etc/wsl.conf` plus a `wsl --shutdown` first. The
  `.wslconfig vmIdleTimeout=-1` arm is still genuinely one line. **Neither is taken**, so until one is, an `Ask`
  with no live loop waits for a terminal. Still owner-accepted, still not an engineering blocker — the daemon
  warns about it on boot.
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

~~**OPEN (D148) — is the composer-supplied `sensitive` marker load-bearing enough to be the only thing protecting a
returned value?**~~ **CLOSED by D152 — no, and the marker is DELETED rather than defaulted.** `returns` now *means*
credential (structural `_is_sensitive`, nothing to forget to set) and `artifacts` is the declared non-credential
half. Inverting the default was rejected: it improves the direction of a mistake but keeps one composer boolean as
the sole gate, which is the thing being questioned. The leak was reproduced with a canary first, and one nuance the
statement below did not have — redaction is **all-or-nothing per message**, so an unmarked entry beside a marked one
was protected by accident; the exposure is a message where *nothing* is marked. Full call in D152. *Original
statement:* Driving 3b found that an unmarked `returns` entry — **fully conforming**, because D147 made
"the same entry minus the marker" the way to express a non-credential artifact — is printed **verbatim, key and
value**, by `drain.py list` into the surface the orchestrator reads; is refused by `drain.py secret`; and therefore
is never shredded or moved to the store. One composer-supplied boolean is the sole trigger for all three
protections at once. The shipped console form cannot produce this (`collectVerdict` always marks `sensitive: true`),
so it is reachable only from a hand-composed POST — which is exactly what every pre-form `returns` was. The options
are roughly: treat every `returns` value as sensitive unless explicitly marked *non*-sensitive (inverting the
default); keep the marker but redact all values regardless and let the marker drive only routing; or declare
non-credential artifacts a different field entirely, so `returns` means "credential" and nothing else. **Not a
regression from D147 — a boundary its declaration made reachable, stated before someone rediscovers it with a real
key.**

~~**OPEN (D148) — should the REQUEST side of a checkpoint be validated the way the reply side is?**~~ **CLOSED by
D152 — the reply's FIELDS are refused on a request; nothing else is.** `park` now rejects `outcome` and `returns` on
a request task and stays permissive otherwise. Full symmetry was rejected on availability grounds: **a park that
hard-fails is a checkpoint that never opens**, which is a worse failure than an extra field. The asymmetry is
principled — the reply crosses a trust boundary from a human or a browser, the request is composed by the loop
itself — but that trust does not extend to fields belonging to the other side. `returns` turned out to be the
sharper of the two (it carries a VALUE, and the whole `request` reaches the console without ever passing
`check_returns`). *Original statement:* `bus.py park`
accepted a request task carrying `outcome: null`, a reply-side `returns` map, *and* an invented field, while
`check_returns` `400`s the reply on a single unknown entry key — on the stated reasoning that "quietly accepting an
extra field is how the next undeclared shape gets in". The asymmetry is not academic: the live parked record carries
an undeclared `outcome` on every request task, written by a hand-reconstruction copying the reply shape. **The
consequences are contained today** (`parked/` is gitignored, the mirror projects four fields, the console ignores
what it does not name), so this is hygiene, not a leak — the question is whether `park` should be strict, or whether
one-sided strictness is the right trade for a producer that is always the loop itself.
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

**CLOSED (D151 → D155 → D158 → D164, 2026-08-03) — how does a released install learn it is stale, when the version
never moves?** The design is settled and **unbuilt**; it is Phase 8a and the next thing scheduled (`11`).
**Owner: D164** — which *re-designed* the answer rather than refining it, so the D155/D158 shape (bump the `version`
per release + a sixth meta-gate to make the bump un-forgettable) is **superseded and must not be built**. In short:
the plugin `version` is **deleted, not disciplined** (omitting it makes the platform key delivery on the commit SHA,
so the sixth gate has no ritual left to guard); `config.workflow_version` becomes that SHA, which the code permits
because `/update` never orders it; and because the automatic delivery path is CLI-side and broken, a staleness
**preventer** is replaced by a two-hop **detector** on the existing `SessionStart` hook. Sequencing is settled with
it: `8a → drive 9a → 9b`. The measurements, the verbatim platform contract, the issue state and the rejected
alternatives all live in **D164**; nothing is duplicated here.
**Both items deferred to build are now CLOSED by the build (D165, owner, 2026-08-03 — 8a is BUILT).**
(1) The **warn-once state** is `.git/hooks/.disciplined-builder-stale`, **not** under `.workflow/` as this question
assumed: the facts are machine-local (committing them would let one machine silence another's warning), `.git/` is
untrackable by construction so it needs no `.gitignore` line — which matters because the installs it must reach are
exactly the ones too stale to have one — and **nothing prunes it** (one small file rewritten in place;
`retention.py`'s remit is `.workflow/`). It adopts the convention the same hook already used for the foreign-hook
marker, and `shared/schemas.md` now owns **both**. (2) The `--plugin-dir` **edge** closed as a four-rung chain
(pin → resolved cache-dir basename → the source repo's `HEAD` → `unknown`), with basename deliberately *ahead* of
git so a user who versions their dotfiles is not told their dotfiles' HEAD is the package version.
**A third thing closed that this block never asked, because only a build could find it:** the SessionStart hook
receives **no `CLAUDE_PLUGIN_ROOT`** (it is wired from the *project's* settings, the third layer D164 identified),
so hop B reads the resolved key from `installed_plugins.json` instead. Anything the package installs into a project
cannot assume plugin-scoped environment — the general form is worth remembering.

## Newly designed — Phase 9 (D159–D163, 2026-08-03) — sub-questions deferred to build
**All three capabilities' sub-questions are now closed** — 9a's by its build (D163), the context-budget law's by
D167, and org mode's in design by D171 (2026-08-04) and **then by its build + drive, D174 (2026-08-05)**. **9c is
BUILT and DRIVEN**, so both the calls and the evidence are in — and building it **corrected its own recorded
design** (D161's `project_root`) before any code was written. A fourth ask — a
console **config tab** — was **DROPPED** (D161): writing `config.json` from the browser makes the bus a second writer
(D93 violation), switching a project's git topology is a migration not a setting, and its "change credentials over
Cloudflare" arm violated D112 (Cloudflare terminates TLS; the credential-away case is Tailscale-only). What stays open
*inside* the three, to settle at build:
- **The chain-forecast (D159) — CLOSED by the build (D163, 2026-08-03).** The layout call was taken while building:
  a `#fc-list` panel (separate from the card, as D162 narrowed it — the card is gone once the orchestrator unparks,
  and the frozen forecast has to keep rendering after that), **one shared chain renderer** used by both card and
  panel, per-event state badges, and a divergence banner. **The browser residual is CLOSED (D166, 2026-08-03):**
  rendered in real headless Chrome against a live daemon, and the D147/D156 shape held a ninth time — the logic was
  fine and **both** defects were in the interaction shell (event numbers drawn twice; the reality probe not
  item-scoped, which raised a false structural divergence off another change's checkpoint and would therefore have
  paid for needless re-forecasts). Both fixed. **Still open from that drive — three shell judgment calls,
  deliberately not fixed:** the panel prints a raw ISO `frozen <stamp>` while the card humanizes ("due in 24h"),
  though the page's own `humanGap` helper exists and its comment argues against exactly this; the credential
  **prefill hint ("Optional — …") renders *after* the inputs**, so a human meets two credential boxes before the
  sentence saying they may skip them; and while a forecast checkpoint is open the **card and the panel render the
  same chain twice** on one page, so the page is longest and most repetitive at the moment the human is being asked
  to act (D162's separation is right — the artifact outlives the question — but the open-checkpoint overlap is its
  cost, and a collapsed panel entry while the card is live may be the answer). Two
  further things the build deliberately did **not** do, worth a look once it has run for real:
  - **A per-ITEM forecast** on the `planner:plan-one` path. 9a is **intake-only** — the forecast gate is stated for a
    "change", not for a backlog item. `/create-forecast` is available by hand anywhere, so this is a convenience and
    a trigger question, not a capability gap.
  - **The `unknown` column may read as mostly-unknown.** `discuss`, `prioritize`, `align`, `close-issue` and `ingest`
    have no anchor-table entry, and `commit` is deliberately unanchored (D163) — all render `unknown`. That is
    *honest* (D163's fourth state exists precisely so "I can't tell" never renders as "did not happen"), but it is
    thin, and if a real chain's reality column comes back mostly blank the fix is a **genuine anchor per node**, not
    a looser probe.
- **~~Org mode (D161) — the three design questions~~ — CLOSED 2026-08-04 in design (D171) and 2026-08-05 by the
  build + drive (D174, owner).** All three shipped as settled: (1) the bundle is a **per-item squashed diff** + a
  sidecar outside it (branch rejected — `git push` is the wrong path of least resistance; `format-patch` an opt-in,
  never the default), and the producer now **verifies its own output** rather than merely applying the exclusion;
  (2) the read-only hazard was **re-anchored** from `ingest` (which runs no gates) onto the **commit gate**, and
  shipped as the third stack-gate state **`STACK_GATE_NONE`** — off *by declaration*, refusing rather than obeying
  any command set alongside it, so a re-run of `/start`'s stack adoption cannot silently re-arm `eval` on foreign
  code; (3) archive-to-git stays local-only and **visible** — `guard.sh` gates the act on `org.archive_remote_ack`
  and the console badges the state, rendered in a real browser with a real remote configured.
  **Two corrections the build made to the record, worth keeping because they are the pattern, not the exception:**
  D161's `project_root` ("an absolute path to the checkout") was **incoherent** with three shipped invariants — the
  brain IS the clone, `project_root: "."`, and there is no third `project_root` value; and D171's stated reason for
  the third state (an empty `checks.env` *deadlocks*) is **topology-dependent** — under D161's literal wording the
  backstop cannot fire at all, which is the worse failure. Both were caught by checking the premise before building
  on it. The remaining honest limit is unchanged and is **not** an open question: the private tree still
  concentrates derived IP about someone else's code on personal infrastructure, and zero footprint on their repo is
  not compliance with their data policy — that is now badged rather than merely stated.
- **The context-budget law (D160) — CLOSED by the build (D167, owner, 2026-08-03; 9b is BUILT).** The defaults were
  derived by measuring, and measuring forced a call D160 had not foreseen: the budget is **two-tier per role**
  (hard fails `checks.sh`, advisory schedules a trim) because the package's own always-loaded templates are
  3.3–3.4× the sub-1k target D160 cited, so an aggressive-only budget would be red on every clean install — and a
  gate that fires on a fresh bootstrap is one a human learns to skip. Shipped: `chars_per_token` 3.2,
  `always_hard` 4000 / `always_advisory` 1200, `ondemand_hard` **25000** (the Read ceiling, not a preference) /
  `ondemand_advisory` 15000. The estimator is calibrated on this repo's own paging failure (85 083 chars at the 25k
  ceiling ⇒ ≤3.40 chars/token), which **kills `chars/4`**. `K`/threshold tuning stays folded into the retention
  `K` open above; Sessions **distillation is no longer deferred** (`memory-model.md`).
- **Cross-cutting — the dogfooding call: ~~HALF CLOSED (D162)~~ FULLY CLOSED 2026-08-05 (D175), by DECISION rather
  than by build.** **9a was built BY HAND** (D163), and self-hosting was then held as "a separate later experiment
  on a clone". **That experiment is cancelled: self-hosting is DROPPED — driving this project's own implementation
  with the product is not the right thing for this repo.** So the last question here — *whether 9b/9c self-host* —
  is answered **no**, and so is the general case; it is not deferred, it is closed. **The sequencing decision vs
  Phase 8 stays CLOSED (D164): `8a → drive 9a → 9b`.**
  **⚠ Read the boundary exactly — this repo uses two words and only one is dropped.** *Self-hosting* = driving
  **this** project's development with the product → **dropped**. *Dogfood-validation* = driving the product against
  throwaway or foreign repos as **evidence** (D52, D125, `scripts/drive-org-mode.sh` vs pallets/click) → **kept
  intact — it is the entire evidence discipline of this repo**, and the maintainer confirmed he intends to keep
  dogfooding whenever needed. Do not sweep the second when reading a reference to the first.

## Newly open from the Phase-8a / 9a-drive / 9b builds (2026-08-03 — D165 / D166 / D167)
Small, all found by building or driving rather than by reasoning, and none blocking.
- **~~`product/shared/schemas.md` is past the hard wall~~ — RESOLVED 2026-08-04 (D168).** Split into a survivor
  (18 670 tok) plus the live sibling `shared/schemas-runtime.md` (10 832 tok); the convention gained a second marker
  form and a machine-followable pointer. **Two residuals from it stay open, and both outlived the fix:**
  - **The package's own docs still have no budget gate `[small]`.** `check_doc_budget.py` ships scanning a *target
    project's* docs, so it would never have flagged `schemas.md` by itself — `07` did, by hand. Deliberate as far as
    it goes (D164 had just *deleted* a meta-gate, and adding one back needs a better reason than symmetry), but the
    asymmetry is now load-bearing: the package is the only tree that has actually crossed the wall.
  - **This repo's grounding instruction points at files no session can read `[core-ish]`.** `CLAUDE.md` tells every
    session to ground itself in `08-decision-log.md` (**~209k estimated tokens**) and `11-roadmap.md` (**~37k**) — both past
    the 25 000-token Read ceiling, so the instruction is literally unfollowable and every session silently
    substitutes targeted greps (this one did). Now the **next split-and-pointer customer**, and unlike `schemas.md`
    it is meta-repo-only, so it never touches the ship boundary. The roadmap/git split this repo already does by
    hand is the shape.
- **`--project-root` means two different things in two shipped scripts `[small]`.** In `update_reconcile.py` it is
  the **repo** root; in `retention.py` it is the **product** root (`./project` on greenfield), with `--workflow-dir`
  carrying the repo-relative part. Both are internally coherent and documented, and renaming a shipped flag is a
  breaking change with no forcing need — but it cost a wrong test harness during 9b (retention silently read no
  config and capped at the default `K`), so it will cost a caller eventually. Either rename at a natural breaking
  point or state the divergence where both are documented.
- **The always-loaded advisory is deliberately red on the package's own templates `[expected, not a bug]`.** The
  shipped brief and `loop.md` sit at ~3.3k/3.4k tokens against a 1 200 advisory, so a fresh install schedules a trim
  ticket on day one. That is the design (green *gate*, tracked *aspiration*), but nobody has yet asked whether those
  two files can actually reach 1k without losing the routing table — if they cannot, the advisory is the wrong
  number rather than the trim being overdue, and the honest fix is to move the target, not to carry a permanent
  ticket.

## Newly open from the Phase-8b build (2026-08-04 — D169)
All found by building or driving. None blocks; the first is the one with teeth.
- **~~The thread ROTATION is specified and wired but never executed~~ — CLOSED 2026-08-04 (D170): it EXECUTED.**
  Proven by shrinking `config.thread.rotate_at_tokens` in the fixture and driving a real question, which exercises
  the **whole** path (estimate → decide → distil → write → clear → increment), not a part of it. Asserted
  mechanically: `session_id` `None`, `rotations: 1`, `turns: 0`, `thread/handoff.md` written. **The "cheap partial"
  proposed here was based on a false premise and is recorded because the check is the lesson:** there is **no
  estimate-and-decide half in code** to unit-test — `rotate_at_tokens` appears only in `answer/SKILL.md` prose and
  the two schema docs, and `bus.py` merely *displays* `rotations`. The whole rotation is model behaviour with **no
  seam**. Driving it was both cheaper and total.
- **~~Answer QUALITY is unmeasured~~ — CLOSED 2026-08-04 (D170): measured on the shipped path, and good.** Four
  uncontaminated runs (the real `flock … claude -p "$RUNNER_ANSWER_PROMPT"` argv, so the answering context is cold
  and the away-path is exercised at the same time). Both designed traps passed — a debug report that **exists** but
  holds only the placeholder `root cause` drew "the record does not say" plus an enumeration of where it looked, and
  an undecided TTL drew "undecided, deliberately" citing the forecast branch. It also flagged a **fabrication it did
  not author** in existing thread history, and found two unplanted record inconsistencies without repairing either.
  D170 owns the detail.

## Newly open from the Phase-8b DRIVE (2026-08-04 — D170)
Three defects, all found by driving what a green suite had already passed. The first is a shipped correctness bug.
**All three are CLOSED 2026-08-04 (D172); the away-path item below is CLOSED 2026-08-04 (D173), after measurement
corrected the remedy D172 had recorded for it.**
- **~~`answer`'s own prescribed step order can DOUBLE-ANSWER~~ — CLOSED 2026-08-04 (D172).** Steps 5 and 6 are
  swapped: **append → record → rotate**. The append→record window the anchor was written for is provably
  **unchanged** (nothing was inserted into it — asserted, not assumed), and the previously-unsaid half is now
  written down: **post-rotation the anchor is unreachable and idempotency rests on the drain watermark alone**,
  which is correct precisely because rotation now runs *after* the record. Guarded mechanically by
  `test_answer_skill.py` — it parses the numbered steps out of the shipped file and refuses an order that puts a
  `turns`-clearing step ahead of the record. D172 owns the honest ceiling of that guard.
- **~~Rotation LAUNDERS a fabrication into durable memory~~ — CLOSED 2026-08-04 (D172), structurally.** The call:
  the handoff keeps only what is **not re-derivable** and carries **no project prose answer at all** — every answer
  came from the project's own record by construction, so it is re-derivable, and an answer that is *not*
  re-derivable is exactly the invented one. Carrying provenance was **rejected on evidence**: the fabricated claim
  *already carried a citation*, so provenance-forwarding would have made the invention look better-sourced. The
  general rule — **a distillation may drop, point and quote; it may never restate** — is stated **once** in
  `memory-model.md § the distillation law`, and `schemas.md § conversation-thread` owns the carry-list.
- **~~A rotated thread renders as a COLD START~~ — CLOSED 2026-08-04 (D172).** The panel now reads *"conversation
  handed off (rotation N) — the earlier turns are distilled into thread/handoff.md, and the next question starts
  fresh from it"*. Verified in real headless Chrome against a genuinely rotated fixture, and covered by tests that
  run the **real shipped `renderThread`** under node — including the opposite direction, so a project nobody has
  asked still says "nothing asked yet".
- **~~The away path computes an answer, then discards it, then pays to recompute it~~ — CLOSED 2026-08-04 (D173).**
  The runner now **refuses to spawn** into an untrusted workspace and fires **one** alert naming the fix the
  platform itself prints. Two things recorded here were wrong and were corrected by measurement before building:
  - the **`is False` predicate was too narrow**. `claude -p` does **not create** a project record, so the ordinary
    untrusted case — a project never opened interactively — has **no entry at all**. The "12 of 26 are `false`"
    figure was real but was not the signal; the signal is **not `True`**, and the older `status`/`/start` warnings
    (which keyed on `is False`) could not fire on the common case they existed to warn about.
  - the fear of **parent-dir inheritance** was unfounded: a fresh directory under a `true`-recorded parent is still
    untrusted (MEASURED), so trust is **exact-path** and there is no ancestor chain to walk.
  Fail-open is preserved where it belongs — on the read, not by omitting the gate: absence counts as untrusted only
  while a **schema-health probe** shows the file still speaks the format, and any unreadable/renamed/reshaped record
  returns *unknown* and spawns as before. Driven against a genuinely untrusted workspace with the **real** `claude`
  on `PATH` and the **real** `~/.claude.json`: no spawn, one actionable alert, the question left queued.
- **~~A dead-lettered question renders as "waiting" until the bus GCs it~~ — CLOSED 2026-08-04 (D172).** It now
  renders *"dead-lettered — no answer is coming"*, dimmed and dotted rather than styled as a live question. The
  **reason** is deliberately not carried into the panel: the "my requests" surface owns it, and a second copy in a
  second panel is the drift the one-owner rule exists to stop.
- **`schemas.md` gave back ~1.1k tokens of the margin D168 won `[watch]`.** It sat at ~19.8k after Phase 8b and is
  **~20.6k** after D172 (ceiling 25 000; ~4.4k of headroom left). Measured by hand, not by the gate — the budget
  gate still does not scan the package's own docs (the residual above), which is why every slice that touches this
  file has to check the number rather than assume the split solved it permanently.

## Newly open from the Phase-10 scoping premise re-check (2026-08-05 — D175)
Only the genuine **design question** is filed here; the rest of the re-check produced *work items* (owned by `11`'s
Phase 10) and *corrections* (already applied to `11`). Six of the ten candidates were stale — the standing lesson is
now seven phases old and did not weaken.
- **~~Where does `commitment` actually live — one owner, or two?~~ CLOSED 2026-08-05 (D176) — it was neither.**
  The build found the node field had **no producer and no consumer**: `graph.json` is structural and has no
  commitment to supply, the seeder emits `path`/`type`/`lang`/`tier`/both signals and never a commitment, and
  nothing anywhere reads one off a node. So there was no second owner to reconcile — only a phantom field. **Then
  the sweep found it was worse: D106 had already decided this in Phase 2** — *"the spec is the sole owner … nodes
  never store a commitment value"*, with node frontmatter under its **Rejected** line as a D80 violation — and
  `schemas.md` shipped the refused field anyway, while citing that schema as evidence for the opposite call. The
  field is **deleted** and the spec element confirmed sole owner. *(Original framing below, kept because the
  re-ask is what found it.)* The recorded question was
  "spec **vs** node frontmatter", read for two months as an open fork. **It is stale as worded: the tree shipped
  both.** `shared/schemas.md` tags `commitment` ∈ `{locked, provisional, unspecified}` per spec element *and* lists
  it in knowledge-node frontmatter beside `seeded_by`. The live question is a **D80** one, and sharper: is the node
  copy **derived** from the spec (one owner, a projection — fine), or independently authored (two owners for one
  fact — the exact drift D80 exists to stop)? `align` classifies drift *by* commitment and `document` reads it, so
  a silent divergence between the two copies would mis-route drift rather than fail loudly. **Decide the owner, then
  make the second copy provably derived or delete it.**
- **The observed-layer over-claim is scheduled, not open** — `codemap.py` and `verify/SKILL.md` both assert
  `graph.observed.json`, which no product code produces. The *layer's* tier is settled `[stageable]` (D175); the
  *claims* are retracted in Phase 10a. Filed here only so the next reader does not re-open the tier.
- **`11-roadmap.md` is ~37.5k tokens — 1.5× the 25k Read ceiling, and it is the CANONICAL STATUS doc `[watch]`.**
  Measured by hand at D175 capture (119 932 chars ÷ 3.2); it was ~34k before this phase and this capture added
  ~3.5k. The doc every reader is told to ground on **cannot be read whole**, so grounding is grep-shaped by
  necessity — which is exactly the condition that let six by-space items rot unnoticed until D175 grepped them.
  D168's `schemas.md` precedent is the obvious remedy (split off a live sibling, leave a survivor + a
  machine-followable pointer), and the natural seam here is **live status vs the historical phase record**, which
  is most of the file's bulk. **Not scheduled into Phase 10** — it is doc surgery on the one doc Phase 10 is
  actively editing, and doing both at once would make the diff unreviewable. Revisit at Phase 10's close.
  *(This register: **23.2k estimated** (74.4k chars ÷ 3.2), ~1.8k of estimated headroom. Still measured by hand —
  the budget gate does not scan the package's own docs. **And the estimator itself is now in question:** this
  file's true count is **~28.0k**, so it is already ~3k PAST the 25 000 ceiling and reads as green only because
  `chars_per_token` is too high — see `reviews/post-phase10/doc-review-register.md` JF1, unresolved. **This line
  is its own evidence:** it was written at 22.3k one day earlier and was stale before it was merged, which is the
  argument for JF3 (the package's own docs have no budget gate) stated as a fact rather than a prediction.)*

## Newly open from the Phase-10 BUILD (2026-08-05 — D176)
- **Native Windows is still UNVERIFIED where it matters most `[open — the 10b residual]`.** What was measured on
  the stock Windows PATH: `python3` is the Microsoft Store stub (empty stdout, advert on stderr, **exit 49**) and
  `bash` is the WSL launcher (`uname -s` = Linux). Both fail-closed paths hold against the stub. What was **not**
  measured, and is the realistic case: execution under **Git for Windows' bash**, which is what actually runs a
  git hook on a Windows dev box. It is not installed on this machine and installing it is a system change, so the
  question stands. **What would close it:** a Windows box with Git for Windows, running `/start` → a commit
  (exercising `pre-commit.sh` + `guard.sh` + `checks.sh`) and `loop.sh`. Concrete known hazards to check there:
  CRLF on the shipped `.sh` files, and `flock`'s absence (now correctly *diagnosed*, but the launcher still
  refuses — meaning **`loop.sh` cannot start a loop under Git-Bash at all**, which may deserve a real fallback
  rather than a good error message).
- **The contract linter reads only the FIRST line of `loop.md`'s "Side doors" paragraph `[small]`.** Adding
  `status` on a continuation line left it unrouted, and the linter caught it as an advisory — so it is not
  silent, but the layout constraint is invisible in the file. A comment now warns the next editor. The parser
  could take the whole paragraph instead; not done because the gate already reports the failure it would prevent.

## Drive-found, logged not fixed — the first long interactive drive of a real project (2026-08-06, `agentic cyber`)
Found by a human driving a real greenfield through its design phase, not by a gate. Both are legibility defects
of the same shape as D148/D149 — **the mechanism worked and the human learned nothing** — which is the class no
green suite catches.
- **The staleness detector is DELIVERED but not LEGIBLE, and warn-once makes each miss PERMANENT `[real, reproduced]`.**
  `hooks/session_start.py` composes its two-hop warning into `hookSpecificOutput.additionalContext` and records
  the SHA pair in `.git/hooks/.disciplined-builder-stale`. `additionalContext` reaches the **model** only, and
  **nothing instructs the model to relay it** — `templates/orchestrator-CLAUDE.md` carries no rule about
  surfacing SessionStart warnings. So the human is never told, the warn-once budget is spent, and the detector is
  silent forever after for that pair. *Reproduced twice on the real harness:* hop B fired at 13:33:36 writing
  `{"update": "d8c14604cfcf..9e4dcb6c1d71"}`; the human deleted the record to re-arm and ran `/clear`; it was
  rewritten at 13:37 with the same pair — and both times the session said nothing. The project sat three phases
  behind (10a/10b/10c) with no visible signal. **Why it was missed:** `session_start.py:31-36` records this as
  driven, but what was driven is **deliverability** on `claude -p` ("is handed the warning and *can* quote it back
  verbatim"). *Can*, not *does*. Legibility was never tested on an interactive session, where a model with no
  instruction has no reason to volunteer it mid-way through a 6.9k-char handoff injection.
  *Proposed, NOT applied:* a mandatory-relay rule in the orchestrator brief — a SessionStart-injected warning
  must be surfaced to the human in that session's first response. Open beyond that: whether **hop B** should be
  exempt from warn-once entirely, since it is the hop where a stale install **propagates** old code through
  `/update` while reporting success (D164's whole argument), which is a bad thing to say exactly once.
- **A cleared session looks identical to a broken one `[small, real]`.** `/clear` rehydrates correctly —
  `additionalContext` carries `handoff.md` verbatim — but because that injection is invisible, the human sees an
  empty window and reasonably concludes the resume failed. The maintainer reported exactly this ("i ran /clear and
  ofc nothing happens it cant resume on its own"). Nothing is wrong with the mechanism; the *absence* of any
  confirmation is what reads as failure. Cousin of the item above: the same fix (relay on first response) would
  cover both, since a session that opens by saying where it is proves the rehydrate landed.

## Newly open from the dispatch-fidelity measurement (2026-08-07 — D178)
Found by *measuring* a real drive (`agentic cyber`), not by reading — the class that reading cannot reach. The
finding itself is decided (D178) and scheduled (`11`'s `### Phase 11`); what stays open is the tension the fix
creates and the question it defers.

- **An inline `verify` reads a 191k–300k-token item's diff in the orchestrator's own window `[real, unmeasured]`.**
  D84's rule holds that `verify` must stay an inline skill — it is a fan-out controller and a leaf cannot spawn —
  and D178 keeps it there. But the same measurement that justified moving `execute` out of the hub shows what
  `verify` is then asked to read *inside* it. D84's stated answer is **authoring-thinness**: push the heavy reads
  into workers `verify` spawns, hold only thin summaries inline. `verify/SKILL.md` already licenses that ("Lean:
  for small changes, judge directly without fanning out workers"), so the mechanism exists — **it has simply never
  been measured under a large diff**, and the skill gives no threshold for when to fan out. Open: does inline
  `verify` actually stay thin at this item size, and if not, is the fix a stated fan-out threshold in the skill, or
  a hub-mediated split that reopens D27's two-level-agent topology? *Do not settle this by reasoning — it is a
  measurement, and the tooling that would take it now EXISTS (`11`'s **11d**, built D179): a drive's per-node
  read/write split is one command away. Still unmeasured, because the one item driven so far had a small diff —
  the question is now cheap to answer, not answered.*
- **`planner` has no sizing rule at all `[real, deferred by decision]`.** `decompose` emits phases, `plan-one`
  emits "ordered verifiable steps" + `files_touched`, and **nothing anywhere bounds how big a plan may be**. Plan
  size is whatever the backlog item happened to be, which is how a single `execute` dispatch reaches ~300k. This is
  **deliberately not answered yet** (`11`'s **11f**): the attribution must be taken against the fixed system,
  because a scoped `execute` agent with no web tools may burn materially less, and because measuring the current
  system would measure a paraphrase. *The fixed system's first measurement is in (D179) and it reads
  **read-dominated** — `execute` 335.6k fed in against 24.1k written — i.e. the first of the two diagnoses below.
  One item is not a sample, so this stays open; what changed is that it is a measurement question with a tool
  now, not a reasoning question.* Two diagnoses with opposite fixes — read-dominated burn ⇒ `planner`
  under-supplies context (D134's resolution: mechanical seeds, and splitting would make it *worse*);
  write-dominated burn ⇒ a plan-size budget splitting on the D91 predicate, serially.
- **The loop has no cold-context correctness reviewer `[real, promotion-gated]`.** `verify` is artifact conformance
  by design, `debug` is on-fail only, `align` is periodic and not per-item — so a change that is logically wrong
  but passes its own tests and matches its own changelog goes straight to `commit`. Cognition's Code-Review-Loop is
  the measured counter-pattern (~2 bugs/PR, ~58% severe) and is **read-only**, so it does not touch the
  single-writer rule D178 upheld; it fits as a leaf agent. Held out of Phase 11 on purpose — a reviewer is worth
  nothing while the workers are not running their own instructions. **That condition is now met: `11e` is green
  (D179), so this is promotable** — the next phase's first candidate, alongside `11f`.

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
  JS/TS, Go, Java, C#); C++/Rust/PHP stay on the tier-0 floor by design. Residual is **runtime**: brownfield
  `/start` is unexercised until a real bootstrap (validation-blocked).
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
- **Real dispatch validation** — the dogfood *simulated* the `research` agent dispatch; the orchestrator→agent
  call + structured return is validated in the harness-real run.
- **Package install** — loose `.claude/` files are MVP (D57); plugin packaging + `shared/` resolution open.
- **Adoption follow-ons (D38–D51)** — the **retention & archival law** is **CLOSED**: Layer 0 write-law leak
  closures (D59–D60) + Layer 1 cap-and-archive read law (D61). What remains under it: **Sessions distillation**
  (deferred *mechanism* — lossy/model-authored; **D88 captured the rule (P2)** that a postmortem distills to a
  one-line Lessons pointer *before* drop, so retention never evicts an "avoid" raw) and `K`/threshold tuning
  against real runs. Also: whether `verify` samples the real `git diff` vs trusts the `changelog` (#8).
- **Rules baseline + `/start` enforcement wiring (D40) + two-tier drift defense (D65/D67) — AUTHORED
  2026-07-01.** The `rules/*.md` baseline (enforced-by tags), the `shared/format.md` rules convention, the
  `/start` step-4 enforcement wiring, the `commit` mechanical-gate step, and the `prioritize` drift-ticket note
  are written. **Remaining sliver:** `/start`'s per-stack **`checks.sh` generator** (detect the stack → emit
  the concrete `--fix`/`--check` runner + configs) — a `/start` runtime detail, not yet exercised in a real
  bootstrap.

- **`handoff.md`'s durability mandate is met at the drain and nowhere else (raised by D117).** D93 calls it "the one
  file where crash-durability, not just atomicity, is mandatory" (write-temp → `fsync` → `rename` → `fsync(dir)`).
  `drain.py record` does exactly that for the machine block. But the **handoff step** — the orchestrator rewriting
  the prose anchor at session end — is a model with a text-writing tool, which **physically cannot express a
  rename**, let alone a directory `fsync`. So the mandate is unmet on the very write it was authored for.
  **Bounded, not open-ended:** `handoff.md` is committed, so a torn or unflushed copy is recoverable from git — the
  last good anchor is a `git show` away. The fix's *shape* is the open part: a CLI taking a markdown blob is poor
  ergonomics, and a "model writes the prose → a script republishes it atomically" two-step is plausible but needs
  design. Deliberately **not** folded into Phase-3 increment 3 (it touches the handoff step and the brief, not the
  drain).

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
  - **Shipped-glue interpreter (D89)** — the shipped bash glue (`guard.sh`, generated `checks.sh`/`codemap.sh`)
    assumes a **bash interpreter on the target OS**; unverified on **native Windows** (git-invoked `pre-commit.sh`
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
- **Project-state view (`03`/`05`/`06`) — user-raised 2026-06-30.** No single synthesized "where is this
  project" surface — *what's done · how the pieces connect · what's left*. The data exists but is scattered
  (`00–11` + `08` decisions + this register + `handoff.md` + `backlog.md` + the `docs/knowledge/` graph). The user
  feels the gap **in this spec project itself**, and it bites harder on code projects — and it's a prerequisite
  for eventually **self-hosting** (driving this project's development with this project). Likely a **generated**
  view (D38 — not a hand-maintained doc that rots): a `status`/`map` skill or a console screen synthesizing
  roadmap + backlog + decisions + graph on demand. **The `graph.json` cluster map (D70) is its "how the pieces
  connect" face** — the structural half of this surface.
- **Public-facing repo identity + onboarding (`00`) — user-raised 2026-07-18; owned now, scheduled Phase 4 (D121).**
  The end goal is a *public* repo others install and integrate, but the repo today is a dense construction record:
  the numbered docs `00–11`, the `D<N>` vocabulary, and internal codenames ("the drain", "the notifier", "waves",
  "away becomes triggerable") are the design scaffolding, not a product front door. The current public surface is a
  spec-navigation `README.md` that even hardcodes the maintainer's local path — there is no getting-started, no
  separation of construction-record from shipped product, and the skill `description:` fields (the one internal
  vocabulary that ships *inside* the package) are still partly in design terms. **The open fork is one-repo-vs-two:**
  (a) a **transparent monorepo** — publish as-is, design docs + decision log included (the reasoning trail is an
  asset, but the front door must redirect "use it" away from `08`); or (b) a **distilled package** — publish only the
  package + clean docs, keeping the spec/log as a `docs/design/` or private construction record (clean surface, but a
  sync seam and the "shows its work" credibility is lost). **Deferred, not ignored (D121):** the *concern* is owned
  now (this entry + the `11` cross-cutting item); the *work* — the fork call, a product front-door README +
  getting-started, the construction-vs-product reframe of `00–11`/`08`, and a user-language pass over skill
  descriptions — rides Phase 4, because onboarding prose written against a still-moving Phase-3 product churns. The
  one cheap thing done incrementally: keep skill `description:` fields honest as they're touched. Overlaps but is
  distinct from the **project-state view** (a *navigation* surface + self-hosting prereq) and the **framework
  version-update skill** (keeping *installed* copies fresh), both below.
- **Framework version-update skill (`10`, D57) — user-raised 2026-06-30.** The package is now a **public
  repo**; consuming projects install a snapshot (`.claude/` skills/agents/commands + `templates`/`shared`/
  `hooks`). As the framework evolves (fixes, new skills, schema/format changes) installed copies go **stale**,
  and stale references mislead the loop. Need an `/update` skill that pulls the latest package and re-applies
  it, **reconciling local customizations + migrating schema/format changes** (a version bump can change
  `state.json`/`schemas` shapes — not a blind overwrite). The natural follow-on to packaging (D57); the
  framework-level analogue of the retention/freshness law.
- **Doc-authoring agent (reserved — D65; trigger fired, still not added — D68).** A specialized
  heavy-doc-reconstruction worker (e.g. brownfield `ingest` building a spec from code — a generative task that
  doesn't fit `execute`'s plan-driven model). The "revisit when building brownfield `ingest`" trigger **fired
  (D68)** and the call held: **`ingest` is a thin skill over the existing leaves** (`research` read →
  `document` write), **no new agent** — reserved still, added only if the generic workers prove insufficient in
  a real ingest run. Cousin of the open "engineer agent?" slot (`02`).

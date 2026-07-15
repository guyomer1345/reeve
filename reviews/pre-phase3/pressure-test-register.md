# Pre-Phase-3 Pressure-Test Register

**Autonomous design interrogation of the whole six-space design, weighted to Phase-2 (D90–D107).**
Substance only (is the design right / complete / coherent / buildable) — **not** a doc↔artifact coherence pass
(that is the separate doc-review). No spec docs, `shared/`, `skills/`, or `08` were edited producing this.

- **Base commit:** `63e9c1d` (Phase-2 DESIGN complete; D90–D107 closed). Branch `main`.
- **Method (three adversarial layers):** a Workflow fan-out ran **11 adversarial finders** across the 7
  pressure-test dimensions × 6 spaces (weighted to D90–D107) → **58 raw findings** → each was **independently
  refutation-tested by a high-effort verifier** told to default-REFUTE unless the failure scenario genuinely
  survives (the project's 0-false-positive discipline) → **I then adjudicated every verdict against the actual
  artifacts as a third layer**, rescuing/reframing findings where a refutation conceded a load-bearing residual
  or over-refuted a fact I independently confirmed, and dropping genuine misreads.
- **Funnel:** 58 raw → 8 verifier-CONFIRMED → **13 substance findings + 1 scoping finding** after adjudication
  (the delta is residuals the verifiers conceded while refuting an overstated headline, plus 3 verifier
  over-refutations I overrode from `guard.sh` / `settings.json` / `start.md` / `loop.md` / `retention.py` reads).
  50 raw were refuted; the ~30 with **no material residual** are listed under *Examined & found solid* for
  coverage honesty.
- **IDs are `F#`, not D-numbers** (per the autonomy contract — assigning a real D-number would trip the
  status-coherence gate and pre-empt the maintainer's lock). "Proposed resolution" = a suggestion, not a decision.

---

## Synthesis — read this first

**Headline: the D1–D89 foundations substantially HOLD under the Phase-2 load.** The gaps are almost entirely in
the **new Phase-2 seams (D90–D107) and their wiring back into the foundations** — the async bus-consume model,
the outward-permission composition, the away-notification path, and the tunnel trust model. The substance of the
design is coherent; what is missing is a set of **load-bearing mechanisms that were named but not pinned**, which
Phase 3 will hit immediately.

**Must resolve before Phase 3 (C1 console → C2 bus):**
1. **F1 — the inbox consume/idempotency mechanism** (consumed-marker / dedup key / lifecycle). The entire async
   model asserts "idempotent, single-shot" but only *implies* the mechanism. This is the #1 buildability item for
   C2 — corroborated by 5 independent finders.
2. **F2 — the orchestrator has no single-writer election.** D93 deleted `flock` "because single-writer," but
   nothing *elects* the single orchestrator; two `claude --resume`/`/start` processes clobber state.
3. **F3 — `config.outward=allow` is inert** against the shipped `settings.json` `ask` rules — standing pre-auth
   can't waive the human, and worse, *breaks* the unattended path it exists for. Its fix drags in the empty
   `guard.sh` push-floor.
4. **F4 — the away-alert has no working trigger.** The console's one MVP job (alert an away human that a verdict
   is needed) relies on a passive `Notification` hook that doesn't fire while D91 interleaving keeps the
   orchestrator busy, has no reachable-away default, and has no live process to fire reminders while whole-parked.
5. **F6 — the tunnel trust model is internally inconsistent** (D95 strict-Host-allowlist-on-every-endpoint vs
   D102/D107 serving read/verdict over the tunnel; release-loopback-only has no specified enforcement).
6. **F14 (scoping) — be clear-eyed that MVP "away autonomy" is bounded to the interleaving-alive window;** whole-park
   or a dead session needs a human at the terminal until the deferred runner lands. C1-without-C2 doesn't deliver
   the critical-path verdict job.

**Coverage map (what each finder examined):**

| Area | Finders | Net result |
|---|---|---|
| A1 park / interleave / context (D90–92) | 1 | F5 + F8 (interleaving invariants); rest solid |
| A2 bus protocol (D93) | 1 | folds into F1; snapshot/promotion races solid |
| A3 daemon lifecycle (D94) | 1 | F10 + F11; flock/adopt/stale-bus solid |
| A4 security / trust (D95, D70, D107, D97-secret) | 1 | F6 + F12; DNS-rebind, demo-form-reach, token-in-git solid |
| C checkpoints (D96–98) | 1 | folds into F4/F8; verdict routing, secret-shred, deep-link solid |
| B console (D99–101) | 1 | F4 core; my-requests/poll/ETag solid |
| D demo skill (D102–104) | 1 | F7 + F12; native-FS/bundle-atomicity/away-view solid |
| E outbox / commitment / map (D105–107) | 1 | F3 + F13; commitment-read, release-order, TTL-drop solid |
| Cross-decision composition (D76 lens) | 1 | F2 core; notification-process → F4; secret-store → F9 |
| Foundations re-examine (D1–89) | 1 | guard.sh → F3; inbox-retention → F1; rest hold |
| Buildability / MVP / gaps | 1 | F14 + the completeness list; boundary/checks.sh decided-but-unwired |

---

## CONFIRMED substance findings (ranked most-severe first)

### F1 — The inbox consume/idempotency mechanism is asserted, not realized *(HIGH · needs new decision)*
- **Area:** D93 / `shared/schemas.md` (inbox-message) / `05` — the async substrate.
- **Dimension:** failure-modes / crash-recovery / buildability.
- **The gap (concrete):** the inbox is `append-only, durable, at-least-once`, and consumption is asserted to be
  "matched idempotently, single-shot (duplicate → no-op)" — but the schema names an idempotency anchor only for
  **verdict** (parked-token) and **release** (outbox `executed`). **intake** (`{ticket, ask}`) and **control**
  (`{ticket, op}`) have **no dedup anchor**, and the promoted backlog item does not record its source inbox id.
  On a routine cold start (D92's MVP stopgap is `/clear` + re-run `/start`) the orchestrator must re-read `inbox/`
  to recover messages the bus wrote while it was down — and re-promotes an already-consumed intake → **duplicate
  backlog item**; re-fires a `control reprioritize`. The consume model itself (delete-on-consume? cursor? bus-side
  ack?) is only *implied* — from the secret-shred precedent and "rebuild from parked/ + inbox/" — never stated;
  and D93's single-writer rule (bus is the sole `inbox/` writer) leaves *who legally removes a consumed message*
  ambiguous.
- **Why it matters:** silent duplicate work + repeated control commands on every restart/redelivery break the
  single-shot guarantee the whole console→orchestrator contract advertises. It is the correctness backbone of C2.
- **Corroboration:** found independently by **5 finders** (A2, foundations×2, buildability, E-outbox); the
  buildability instance was verifier-CONFIRMED. The refutations that fired all conceded the residual ("delete-on-
  consume is implied rather than stated"; "intake lacks an explicit dedup key" — a "one-sentence completeness
  nit"). Aggregated, the nit is the load-bearing seam.
- **Proposed resolution:** pin the consume mechanism explicitly (a durable consumed-watermark or per-message ack
  the orchestrator legally owns, reconciled with D93 single-writer — likely a consumed-set in orchestrator-owned
  state, *not* the bus partition); give **intake/control** an explicit bus-assigned dedup key checked before
  apply; state the general (non-secret) delete-after-consume lifecycle and the inbox's own retention story
  (`retention.py` sweeps only Sessions/decisions/items today — `inbox/` is outside it by design, so its bound must
  live with the consumer).

### F2 — The single-writer invariant is unenforced: two live resume/restart processes clobber state *(HIGH · needs new decision)*
- **Area:** D93 ↔ D90/D92 · `05` (single-writer) · `01` (session lifecycle).
- **Dimension:** cross-decision composition / data-loss.
- **The gap (concrete):** D93 removed `flock` for the orchestrator on the premise "single-writer removes the
  write-conflict class" — but **nothing elects the single orchestrator.** Only the *bus* has a `flock` singleton
  (D94). A human in a second terminal (or an away human firing `claude --resume <id> -p "<verdict>"` while the
  interleaving session is still alive at a prompt) yields **two `claude` processes both believing they are the
  sole writer.** Atomic-publish prevents a torn *read* but not a **lost update**: A advances item 5 and renames
  `state.json`; B (resumed) advances item 3 and renames over it → item 5's progress + its parked record are
  silently clobbered, or a ticket double-executes.
- **Why it matters:** silent data loss / double-execution of an autonomous executor, with zero mechanical guard —
  the entire lock-free coordination substrate rests on an assumption two other Phase-2 decisions can break.
- **Adjudication note:** the D92 "`/clear` + re-run `/start`" arm is same-session (one process) — not a second
  writer; the live vector is a second terminal / a second `--resume`. Whether the harness itself locks a live
  session against a second `--resume` is unverified and the design neither claims nor relies on it — which is the
  gap. **CONFIRMED** (verifier corrected critical→high; I concur).
- **Proposed resolution:** give the orchestrator its own singleton election (a held `flock` on
  `.workflow/orchestrator.lock` at `/start`, mirroring D94's bus pattern); a second `/start`/`--resume` that
  can't acquire it delivers its verdict to the inbox and exits rather than advancing the loop.

### F3 — `config.outward=allow` is inert against the shipped `ask` rules; its fix exposes the empty `guard.sh` push-floor *(HIGH · needs new decision)*
- **Area:** D105 / `config.outward` (`shared/schemas.md`) ↔ `templates/settings.json` ↔ `hooks/guard.sh`.
- **Dimension:** cross-decision composition / security.
- **The gap (concrete):** a user sets `config.outward push:allow` for an overnight run. The `commit` skill
  self-gates, sees `allow`, runs `git push`. `guard.sh` passes. Then the harness evaluates
  `settings.json`, whose **static** `ask` list contains `Bash(git push:*)` → it prompts → **blocks away-from-
  terminal.** The push never happens *despite* the standing pre-auth. `/start` only *copies* `settings.json`
  verbatim (no projection from `config.outward`), and `start.md:75` even tells the user "outward actions will
  still ask — by design." So D105's load-bearing promise "standing pre-auth waives the human, never the checks"
  is **unrealizable as built**, and the only workaround (hand-edit `settings.json` too) creates a **second owner**
  for the same allow/ask fact (a D80 violation). **Linked:** if the fix is "make the skill + `guard.sh` the sole
  gate" (drop the static `git push` ask), then `guard.sh` becomes the *only* thing between an autonomous loop and
  a force-push of `main` — and `guard.sh` today has **no branch/refspec logic at all** (its secret/verify gates
  live only in the `git … commit` branch; a plain `git push --force origin main` hits only the obscured-chain
  check and passes). D105 delegates "never auto-push `main`" to `guard.sh` in three places; the mechanism does not exist.
- **Why it matters:** the outward-permission model — a Phase-3 build target — has an unreconciled two-layer
  ownership conflict at its center, and the safety rule it leans on (protected-branch / force-push / outgoing-
  range secret-scan) is un-designed. Either standing pre-auth silently doesn't work, or resolving it opens an
  ungated autonomous push path.
- **Adjudication note:** the `config.outward` inertness is **CONFIRMED** (I verified `settings.json` directly).
  The bare `guard.sh`-has-no-branch-logic finding was refuted as "specced-but-not-yet-built" (fair on its own —
  D105 is DESIGN, build deferred); I fold it here because F3's own resolution makes the push-floor load-bearing,
  not deferrable.
- **Proposed resolution:** decide the binding — either `/start` **projects** `config.outward` into the generated
  `settings.json` (config becomes the single owner), or drop the static `push`/`gh` `ask` rules and make skill +
  `guard.sh` the sole gate — and in the latter case, **design the `guard.sh` push-content floor** (parse the
  refspec incl. `HEAD:main` and `push.default`, block force-push + a protected-branch set, secret-scan the
  outgoing range) as a Phase-3 prerequisite, not a "sub-detail."

### F4 — The away-alert path is under-specified end-to-end (no fire point · no reachable-away default · no timer process) *(HIGH · needs new decision)*
- **Area:** D90 / D101 / D97 · `skills/checkpoint` · `templates/settings.json` · `03`.
- **Dimension:** cross-decision composition / MVP-critical-path.
- **The gap (concrete), three composed facets:**
  1. **No fire point at checkpoint-raise.** `skills/checkpoint` posts the request and parks — there is **no alert
     step.** D101 assumes "the `Notification` hook" fires, but that harness hook is event-bound (permission-prompt
     / ~60 s idle), and D91 interleaving keeps the orchestrator **busy** on the next ticket at the raise instant,
     so neither trigger occurs. `settings.json` wires **no `Notification` hook at all**. *(verifier-CONFIRMED.)*
  2. **No reachable-away default.** The MVP default is desktop-native — a toast on the machine running the loop
     reaches no one. The documented escape is an "opt-in Slack/HTTP webhook," but there is **no `config.notify`
     key** and **no shipped hook stanza** to hang it on. *(refuted as "staged/opt-in" — but the verifier conceded
     "the opt-in webhook tier lacks a specified seam.")*
  3. **No live process for time-based reminders.** D97/D101 promise the deadline "re-surfaces + reminds" via
     aging — but the only always-alive process (the detached Python bus) **cannot invoke Claude Code hooks**, and
     a whole-parked/idle/dead orchestrator runs no timers. So a stale-deadline escalation fires **only** if the
     loop happens to still be interleaving in a live turn. *(refuted as "the raise notification already fired +
     D90 defers autonomous wake" — but the reminder/escalation half genuinely has no owner in the parked state.)*
- **Why it matters:** this is the console's raison d'être (D99: "the dogfood's one critical-path job"). All three
  facets degrade "unattended autonomy" to "the human must keep polling."
- **Proposed resolution:** make the alert an **explicit action the `checkpoint` skill fires at park-time** (before
  yield, once per raise, idempotent) rather than relying on the passive hook; **assign the deadline/aging timer to
  the always-alive bus daemon** (let it send the desktop/webhook notification directly, decoupling "notification"
  from "the Claude `Notification` hook"); and **spec the away seam** (`config.notify` webhook + a default hook
  stanza in `templates/settings.json`), or state plainly that MVP away-alerting is BYO-webhook-only.

### F5 — Interleaving's file-disjoint invariant breaks under execute-divergence/under-prediction; no autonomous rebase-conflict handler *(MEDIUM · needs new decision)*
- **Area:** D91 ↔ D66 · `05` (worktree resume) · `shared/schemas.md` (`files_touched`, `divergences`).
- **Dimension:** cross-decision composition / failure-modes.
- **The gap (concrete):** the interleaving safety argument rests on `file-disjoint from every parked ticket` — but
  `files_touched[]` is a **plan-time prediction**, and D66 explicitly sanctions `execute` touching **unplanned**
  files (a `prerequisite-repair` divergence, committed separately). Nothing re-evaluates disjointness against the
  parked set after a divergence. Ticket B (disjoint at start) diverges to edit `foo.py`, which parked ticket A
  also touches; when A resumes (un-WIP → rebase onto a trunk that merged B's `foo.py`) git hits a **real textual
  conflict**, and `rerere` only replays a *previously-seen* resolution — useless first-time. **The spec defines no
  autonomous behavior on a rebase/merge conflict during resume.** The same hole opens with zero divergence when
  `planner` simply under-predicts `files_touched` for an exploratory/refactor plan.
- **Why it matters:** the one invariant that makes concurrent worktrees safe is never enforced after plan time.
- **Adjudication note:** **CONFIRMED**, but git *halts* on the conflict (no silent corruption) — the finder's
  "silent clobber" was overstated; worst realistic case is a safe stall + a narrowly-possible unsupervised merge
  edit the escalate-don't-auto-resolve culture disfavors but never names. Medium, not high.
- **Proposed resolution:** re-validate file-disjointness against the live parked set when `execute` records any
  non-cosmetic divergence (serialize/abort B or escalate), and **explicitly define escalate-to-human on a rebase
  conflict during autonomous resume (never auto-resolve)**; treat `files_touched` as a lower bound `execute` must
  widen-and-recheck. (Also folds the refuted "file-disjoint uncomputable at prioritize time": the natural build is
  plan-the-candidate as park-safe read-only work → gate at the write boundary — decided-but-unwired in `prioritize`.)

### F6 — The tunnel trust model is internally inconsistent and its release-loopback-only enforcement is unspecified *(MEDIUM · needs new decision · security)*
- **Area:** D95 ↔ D107 / D102 · `05` (trust) · `03` (remote control).
- **Dimension:** security / cross-decision composition / buildability.
- **The gap (concrete) — this is a verifier over-refutation I overrode:** two verifiers refuted the release-
  loopback-only and token-bootstrap findings by invoking the capability token ("a tunnel client lacks the 0600
  token"). But that argument fails: **for read/verdict to work over the tunnel (D102/D107, owner-accepted), a
  remote browser must present the token** — so a verdict-capable remote client **holds the token**, and the token
  therefore **cannot be what distinguishes verdict (allowed remote) from release (loopback-only).** The real
  discriminator must be the **Host header** — but D95 mandates a strict allowlist of `127.0.0.1`/`localhost`
  **only, on every endpoint.** That collides head-on with serving read/verdict over the tunnel:
  - if `cloudflared` forwards the real tunnel Host → D95's allowlist rejects **all** tunnel traffic (read/verdict
    included) → the tunnel doesn't function;
  - if `cloudflared` rewrites Host to `127.0.0.1` → tunnel traffic is byte-indistinguishable from loopback → the
    release endpoint **cannot** refuse it → D107 unenforceable.
  The only resolution is a **per-endpoint Host policy** (read/verdict admit the tunnel host; release admits
  loopback only) — which is neither specified nor consistent with D95's "every endpoint." Separately, the **local
  browser's token-bootstrap path** (how the page obtains the capability token without that path being tunnel-
  reachable) is unspecified (a verifier conceded this). And D107's "verdict = local, low-consequence" **under-rates
  setup verdicts**, which write credentials to the secret store and trigger a machine-verify probe to a
  caller-chosen endpoint (SSRF-lite + credential substitution).
- **Why it matters:** release is the *one* interaction D107 explicitly tried to wall off (a forged release fires an
  irreversible push/deploy), and its enforcement mechanism doesn't close. The tunnel is opt-in/off-by-default/
  owner-accepted, which caps the *live* blast radius — but the D95↔D107 inconsistency must be resolved before the
  tunnel + release are built.
- **Proposed resolution:** specify the per-endpoint Host policy (and reconcile it with D95's blanket rule), or a
  transport-level split (serve `/release` only on a second loopback-only socket the tunnel never fronts); specify
  the loopback-Host-gated token-bootstrap; add returns-bearing setup verdicts to D107's risk taxonomy (gate them
  loopback-only until real tunnel auth lands).

### F7 — The demo refine-round counter has no durable home; the D103 cap can't survive the park boundary *(MEDIUM · needs new decision)*
- **Area:** D103 / D104 ↔ D92.
- **Dimension:** completeness / cross-decision composition.
- **The gap (concrete):** D103 caps demo regenerations at 3 ("counted plainly") but names **no durable store** for
  the count. Each refine round is a full park → verdict → `claude --resume` cycle, and D92 makes the resumed
  conversation disposable. A count held only in orchestrator context **resets to 0 on every resume** → the cap-of-3
  never trips → the refine loop is effectively unbounded and the auto-escalate-to-`discuss` safety valve never
  fires. `parked/<id>` carries only a demo-path pointer today.
- **Why it matters:** D103's entire value is surviving the async park boundary the demo loop is built around.
- **Adjudication note:** **CONFIRMED**; downgraded high→medium because a human is in every round (not an
  autonomous runaway) — only the non-convergence safety valve is silently lost.
- **Proposed resolution:** pin the running count to the durable `parked/<id>` record (incremented by `create-demo`
  on each regenerate, read back on resume), and state the reset rule (reset only on full checkpoint-resolve).

### F8 — The ≤3 concurrent cap counts awaiting-human parks against the autonomous-work budget *(MEDIUM · needs new decision)*
- **Area:** D91 (≤3 parked+active cap) ↔ D97 (never auto-proceed).
- **Dimension:** intra-decision soundness / liveness.
- **The gap (concrete) — a rescue of the *surviving* half of a refuted finding:** the "escalate contradicts
  never-auto-proceed / deadlock" framing was **correctly refuted** (D101 defines "escalate" = a notification, not
  auto-proceed — no contradiction). But the substance survives and the verifier conceded it: **three tickets
  parked on human checkpoints (away human offline for a weekend) consume the entire ≤3 concurrency budget**, so a
  fully-independent **no-human-needed** ticket (dependency-ready, file-disjoint, pure code) **cannot start** — the
  dead parks freeze autonomous throughput until the human returns. Read-only fill-work (plan/research) is finite.
- **Why it matters:** an awaiting-human park (which may sit for days) shouldn't hold a slot in the *same* budget as
  autonomous-work concurrency. It's recoverable (not a deadlock) and ≤3 is deliberate — but the cap *semantics* are
  a real design question for unattended runs.
- **Proposed resolution:** decide whether checkpoint-parked-awaiting-human tickets **spill off-budget** (still
  resumable when a verdict arrives) so autonomous tickets keep the ≤3 slots — or explicitly accept the throughput
  bound and document it. Not a defect; a scoping call.

### F9 — The "gitignored secret store" (D97) has no location, D80 owner, or gitignore/disk-layout entry *(MEDIUM · needs new decision)*
- **Area:** D97 ↔ D80 / D53 / D93 · `04` · `05` (disk layout) · `shared/schemas.md`.
- **Dimension:** completeness / D80 single-source.
- **The gap (concrete):** the "gitignored secret store" is referenced **4×** (`04:70`, `schemas.md:126,142`,
  `checkpoint/SKILL.md:41`, D97) and **located 0×** — absent from the `05` disk layout, the commit-policy
  gitignore enumeration, the D93 native-FS pin list, and the `start.md` gitignore scaffold, with **no D80 owner
  declared.** A load-bearing runtime artifact holding live credentials with no declared home directly violates the
  project's own single-source law (every runtime artifact declares owner + location).
- **Why it matters:** the *leak* headline was correctly refuted (`pre-commit.sh`'s secret-scan is a fail-closed
  backstop, and D97 names it *gitignored*), but the D80 adoption gap is real and the verifier conceded it: "the
  store wants a fixed path + a D80 owner + D93 pin-set membership."
- **Proposed resolution:** adopt the store under D80 — fixed path (e.g. `.workflow/secrets/` on the D93 native-FS
  pin), owner = orchestrator writes / audit-prune deletes, add it to the `start.md` gitignore scaffold + the `05`
  layout + a schema entry with 0600/ACL creation (reuse the D95 token-file discipline).

### F10 — The bus daemon has no provenance; per-project keying (shared vs per-project copy) is unspecified *(MEDIUM · needs new decision)*
- **Area:** D94 · `commands/start.md` · `05` (disk layout).
- **Dimension:** buildability / completeness.
- **The gap (concrete) — verifier gave a non-answer ("see above"); I confirmed it independently:** D94 requires a
  daemon script on disk to `setsid`, but `start.md` step 3 (which enumerates every file the package copies —
  `retention.py`, the three coverage gates, `check_contracts.py`, the codemap engine) **does not include a bus
  daemon**; `scripts/` contains no daemon file; the `05` layout lists `bus.json` (the record) but no daemon-script
  path; and step 5 "Launch the local console" is an explicit ⛔ STUB. So Phase 3 has no stated answer to **where
  the daemon lives** (shared `~/.claude/scripts/bus.py <project_root>` vs a per-project copy under `.workflow/`) —
  and that choice **binds the `flock` path, the loopback bind, and cross-project collision differently.**
- **Why it matters:** two projects' daemons can collide (or share a lock) depending on an undecided keying
  question; the daemon can't be built without it.
- **Proposed resolution:** add the daemon script to `start.md`'s copy list (or declare it a shared
  `~/.claude/scripts/` script invoked with a project-path arg), record its path in the `05` layout, and state the
  per-project keying (lock path, `bus.json` path, bind) so two projects can't collide.

### F11 — The daemon's idle-shutdown vs an open parked away-checkpoint is undefined ("heartbeat-aware" is never defined) *(MEDIUM · needs new decision)*
- **Area:** D94 · `05` (lifecycle) · `03` (launch).
- **Dimension:** failure-modes / intra-decision soundness.
- **The gap (concrete):** the daemon's only non-HTTP stop is a "heartbeat-aware idle-timeout self-shutdown (the
  orphan janitor)," but **nothing defines what "idle"/"heartbeat" measures, the timeout, or (the load-bearing
  rule) that an open parked away-checkpoint SUPPRESSES shutdown.** If "idle" = no HTTP activity, an away human who
  hasn't yet opened the console lets the timer expire → the daemon self-shuts → the away-channel is gone when they
  finally submit the verdict (re-spawn needs a local `/start` they don't have). If "idle" keys off an orchestrator
  heartbeat, then "orchestrator dead" — the exact state D94 says the daemon exists for — starves the heartbeat →
  same result.
- **Why it matters:** the daemon could reap the away-channel out from under an awaited verdict. No data is lost
  (the inbox is durable) — it's an availability gap — but it defeats the daemon's purpose in the precise scenario
  it was built for.
- **Adjudication note:** refuted as "one clarifying sentence would tighten it / away-channel already owner-accepted
  degraded on WSL" — but the verifier explicitly named "the real heartbeat-vs-survive-orchestrator-death tension"
  as a genuine residual. Rescued as a small but real safety rule.
- **Proposed resolution:** the daemon reads `parked/` and **never idle-shuts while any parked ticket has an open,
  within-deadline away-checkpoint**; define "idle" concretely (no pending parked checkpoint AND no HTTP activity
  for T) and a default T.

### F12 — The demo CSP over-claims network-egress enforcement *(MEDIUM · partly coherence)*
- **Area:** D102 · `09` · `skills/create-demo`.
- **Dimension:** security / intra-decision soundness.
- **The gap (concrete):** D102 states self-contained/no-external-hosts are "the two invariants a **CSP actually
  enforces**." False for the egress half: the demo response carries **only** `Content-Security-Policy: sandbox
  allow-scripts allow-forms` — the `sandbox` directive controls origin/scripts/forms, **not** `connect-src`/
  `default-src`/`form-action`. A `create-demo` bundle (an LLM generating from repo-derived context — prompt-
  injection surface) can `fetch()`/`sendBeacon`/form-POST to any external host; "never phones home" is guaranteed
  **only** by `create-demo`'s soft self-discipline, not the CSP.
- **Why it matters:** the load-bearing enforcement claim is factually wrong; the demo is an unmonitored exfiltration
  surface (bounded — first-party content the pipeline already has shell access as; the *opaque-origin isolation*
  the CSP genuinely provides is intact).
- **Adjudication note:** **CONFIRMED** (severity high→medium — defense-in-depth, not a broken core flow). Partly a
  coherence fix (`09` words it correctly as format-discipline; D102's rationale line mis-attributes it to the CSP).
- **Proposed resolution:** either correct D102's wording (no-external-hosts is enforced by format discipline + a
  `create-demo` lint, not the CSP), **or** add real directives (`default-src 'none'; connect-src 'none';
  form-action 'none'; img-src data:` alongside `sandbox`) and **drop `allow-forms`** (the demo is read-only,
  no-POST). Note the trap: under the opaque origin, `'self'` is `null`, so `script-src 'self'` would block the
  demo's own inline scripts — enforcement means inlining + explicit `connect-src 'none'`.

### F13 — `issue-create` is non-idempotent across a crash; no dedup key *(LOW · needs new decision)*
- **Area:** D105 / release consumer · `create-issue`.
- **Dimension:** failure-modes / at-least-once idempotency.
- **The gap (concrete):** a `release` fires `gh issue create` → GitHub opens #42; the process crashes **before**
  the outbox entry flips to `executed` / `github_ref` is written back. On restart the still-`pending` entry (or a
  redelivered release) re-fires → **duplicate issue #43.** Unlike `push` (re-scan) and `issue-close` (idempotent),
  `create` has no natural idempotency and the outbox status enum has no in-flight state. The inbox's "idempotent
  single-shot" dedups the *message*, not the external side-effect (the classic dual-write problem).
- **Why it matters:** duplicate GitHub issues on a crash — narrow window, human-recoverable, not data-loss.
- **Proposed resolution:** add an idempotency key (a client dedup token in the issue body the consumer checks-
  then-creates, or treat a present `github_ref` as "already fired"), and specify the fire→mark-executed ordering.

---

## MVP scoping (dimension 4 — must be acknowledged, not necessarily a new decision)

### F14 — MVP "away autonomy" is bounded to the interleaving-alive window; C1-without-C2 doesn't deliver the verdict job *(MEDIUM · scoping · no new decision)*
- **Area:** D90 / D91 / D92 · `11` (C1→C2 sequence) · `03`.
- **Dimension:** MVP scoping.
- **The point (honest framing — the spec IS internally clear about the pieces, but the *composite* consequence
  deserves an explicit lock before Phase 3):** the console's headline value ("supervise + deliver a verdict away
  from the terminal, unattended overnight") is real **only while the single orchestrator session stays alive and
  interleaving** — then an away verdict resumes the parked ticket autonomously at a scheduler boundary. The moment
  the loop **whole-parks** (nothing independent left) or the **session dies**, MVP requires a human **at the
  terminal** to `/clear` + re-run `/start` (or `--resume`); the local relaunch-runner that would close this is
  **deferred** (D90/D92). Separately, the roadmap sequences **C1 (read-only console, "no bus needed") before C2
  (bus)** — but the console's one critical-path job (deliver a verdict) **requires C2**, so **C1 alone does not
  achieve the stated MVP goal** (it delivers visibility only).
- **Why it matters:** this isn't a defect (the spec is honest about each piece), but the *aggregate* — "how much
  unattended autonomy does the pure-config MVP actually deliver, and is C1→C2 the right order for the critical-
  path job?" — is exactly the kind of scoping the maintainer should lock, eyes open, before committing Phase 3
  build order. Consider whether the thin relaunch-runner is closer to critical-path than "deferred."
- **Proposed resolution:** state the MVP away-autonomy boundary plainly at the D90/D99 sites (unattended = the
  interleaving-alive window; whole-park/dead needs a manual restart until the runner lands), and re-examine the
  C1→C2 order against the critical-path goal (a read-only C1 may not be the "quickest *useful* payoff" if the
  verdict path is the point).

---

## Lower-severity / completeness — hand to the doc-review (Chat 2) pass

These are cases where the **design is decided** but the artifact/schema/driver hasn't caught up, or a default is
unpinned. They will mislead a Phase-3 builder reading only the artifact, but they need **no new decision** — they
are doc-coherence / mechanical fills for the doc-review pass (flagged here so it doesn't miss them):

- **The inbox-drain step is absent from the driver artifacts.** D91/D93/D26 decide the scheduler boundary
  (item-level, `resume-parked-first → start-new → sleep`) and which kind is honored where — but
  `templates/orchestrator-CLAUDE.md`'s read→place→advance and `templates/loop.md`'s routing table contain **no
  inbox-drain step or node.** Wire it into both + confirm the drain cadence per kind. *(mostly coherence; the
  cadence-per-kind is a small design confirmation.)*
- **`config.demo.max_refine_rounds` (D103) is absent from the `config.json` schema** (`schemas.md` lists
  `project_root/run/retention/align/outward`). Add a `demo` bullet; enumerate the decided `run` sub-fields (the
  ≤3 wave cap is named under `run` but not broken out).
- **`checks.sh` per-stack generator:** the contract *is* specced at prose level (`start.md` step 4, D67); the
  per-stack tool-map is the tracked build task. Confirm it as a Phase-3 prerequisite (nothing enforces
  verify/coverage/discharge until it exists).
- **Timeout deadline default + reminder cadence are unpinned** (`parked-ticket.deadline` has no default; D97 names
  aging but no interval). Pin `config.checkpoint.deadline_*` + a cadence in the shipped-default pattern.
- **"my requests" intake correlation:** verdict (parked-token) and release (outbox status) are legible; **intake**
  loses its bus `Location` ticket when promoted to a backlog item (the promoted item doesn't carry the source
  ticket). Stamp the bus ticket into the promoted item's `source`.
- **Enumeration completeness:** `outbox/` is not in D93's illustrative served-read list (though `03`/`schemas`
  state the console reads it 4×); `outbox/` + the secret store aren't in the D93 native-FS pin list. Either make
  the enumerations explicit or add a "all atomicity-sensitive runtime dirs follow the D93 pin / all `.workflow`
  files are served from disk" rule so new dirs inherit by default.
- **`parked-ticket` schema** lists `worktree, branch` as required, but intake-stage parks (demo/reconcile,
  pre-plan) have neither — mark them `?`-optional (D104 designs the worktree-less park; the schema over-states
  requiredness).
- **D106 "via the node's `purpose.intent`"** is looser than the actual `align` resolver (it resolves changed code
  → spec element via the eager `[G]` graph + decision records + the STABLE spec as **LLM judgment**, not a keyed
  lookup). Tighten the D106/`09` wording so a builder doesn't hunt for a structured foreign key that isn't there.
- **`refine`'s Route lacks an explicit escalate-to-`discuss` edge** — the "wrong feature discovered at qa" and
  "cap exhausted" paths rely on the terminal-`discuss` escape + the D24 bounded-loop pattern being understood.
  A one-line edge would close the seam.

---

## Examined & found SOLID (adversarially attacked, no material residual — coverage honesty)

The anti-FP layer earned its keep: ~30 raw findings were refuted with the refutation holding on inspection. The
design is genuinely sound on these — recorded so the maintainer sees what was attacked and survived:

- **Bus protocol:** cross-file console snapshot inconsistency (cosmetic on a read-only lazy-poll cockpit;
  decisions key off token/action-id snapshots → dead-letter, never a wrong apply); concurrent intake promotion
  (single sequential consumer, no race); `flock` removal under single-writer; the atomic-publish recipe + native-FS
  pinning (a thorough D89-family treatment).
- **Park/resume durability:** `parked/<id>.json` is the single authority, `handoff.parked[]` a derived mirror
  rebuilt from it (stated 3×), stray verdicts hit dead-letter+surface — no silent drop; crash-mid-resume primitives
  (git-log-as-truth + durable parked record + idempotent matching) are all decided (residual = spell out
  re-entrant ordering, implementation-altitude).
- **Secret handling:** the shred-crash-window (×3 finders) sits inside D95's explicitly-accepted `.env`-level
  envelope (same-UID is a disclaimed threat model; secret is durable-by-design in the store regardless);
  shred-is-last-step is stated 3×. *(Micro-nit only: "shred" connotes secure-erase; the mechanism is unlink.)*
- **Daemon lifecycle:** stale `bus.json` / PID-reuse / port-squat (handled — liveness is the held `flock` +
  token'd `/health`, not the PID); `flock` on DrvFs (pinned to native-FS + health-check is the real singleton, not
  `flock` alone); adopt-or-spawn ordering (the "race-free / never-spawn-fresh / idempotent" contract pins the
  implementation); WSL away-channel death (owner-accepted; machine-off kills everything on any OS).
- **Security:** DNS-rebinding (Host-allowlist + token-on-reads); the demo's `allow-forms` cannot reach token-gated
  endpoints (opaque-origin form can't set the custom header/token, trips `Sec-Fetch-Site`); `bus.json` token not
  committed/logged (gitignored + secret-scan on the commit path); forged-setup-verdict's *outward* propagation
  re-enters the release + `guard.sh` + `config.outward` gates (the local secret poison is reversible).
- **Checkpoints:** verdict token correlation / dead-letter / duplicate-no-op; per-task mixed setup routing;
  qa `changes≡reject` (deliberate per-kind; the wrong-feature path routes to terminal-`discuss`, not a bus
  checkpoint); execute-discovered setups park serially (un-batchable by nature; the spec doesn't over-claim); the
  setup re-guide loop is human-gated (not an autonomous spin; `reject` is the escape). *(Nice-to-haves only: a
  D24-style config cap on the re-guide loop; document the serial-repark.)*
- **Console:** my-requests cross-device (all load-bearing surfaces render from server-side files; only the
  convenience *filter* is browser-local — trivially fixable by surfacing all tickets, single-user); whole-state
  poll payload (tens of KB, gzip, `document.hidden` pause); `version/ETag` suppression (`state.json` republishes
  each iteration, so a parked/ change coincides with a state change; self-heals on the next poll).
- **Demo:** native-FS/repo-mount placement (the demo is the deliberately-unpinned static app-shell class; torn read
  is cosmetic + self-healing on a throwaway); bundle atomicity (file-atomicity is all D102 promises; re-checkpoint
  fires *after* regenerate); away-demo-view over WSL (D102 explicitly disclaims durability; owner-accepted D94).
- **Outbox:** TTL-drop is non-destructive (work stays local in git; outbox `status:dropped` is a durable record;
  git-derived console shows ahead-of-origin); release inter-action ordering (causal — `issue-close` is only queued
  *after* `issue-create` fired and wrote `github_ref`); `outbox/` on the repo mount (single-process write-then-fire
  + re-validate-on-release).
- **Commitment read (D106):** the drift check resolves code→spec via the eager `[G]` graph + decisions + STABLE
  spec as LLM judgment through the precision-biased `align` panel (re-caught next scan) — not a missing FK.
- **Foundations:** `create-demo`-inline-heavy (D84 already classifies it heavy + targets a leaf-agent move,
  deferred + tracked in 3 owners); the append-only inbox volume is human-interaction-paced (the autonomous loop
  never writes it) — the retention concern is the *consume-lifecycle* (F1), not runaway volume.

---

## Closing

**58 raw findings → 13 substance findings + 1 scoping finding after triple-adversarial review.** The Phase-2
design is substantively sound and the D1–D89 foundations hold under it; the gaps are **named-but-unpinned
mechanisms** clustered at the new async/permission/notification/tunnel seams. **F1–F4 + F6 + F14** are the
must-resolve-before-Phase-3 set — each will block or mislead the C1→C2 build. None require abandoning a Phase-2
decision; all are closable with a targeted follow-on decision or a mechanism spec.

*Register produced autonomously; spec left untouched (no numbered docs / `shared/` / `skills/` / `08` edited). IDs
are `F#` placeholders — real D-numbers and any spec capture are the maintainer's to assign.*

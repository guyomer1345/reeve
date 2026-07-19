# 05 — Shared State + Comms Bus (Space 5)

## Why it's its own space **[DECIDED]**
Because agents are persistent but the orchestrator stays lean, and the website is local-only, every
connection between spaces runs through **disk artifacts + a local bus**. Designed deliberately so it
doesn't grow ad hoc.

## The comms bus **[DECIDED — D90/D91 + D93/D94/D95]**
A **local HTTP loopback service** (the website's backend) is the message channel. Its contract closes on four
pieces — **ownership · protocol · lifecycle · trust** (message + `bus.json` schemas live in `shared/schemas.md`).

**Ownership — a single-writer partition, zero co-written files (D93).** Each file has exactly one writer process:
the **orchestrator** solely writes `state.json` / `handoff.md` / `backlog.md` / `parked/` / `items/` + git; the
**bus** solely writes `inbox/`; everyone else reads. UI-originated work **never** writes the backlog directly (that
would make it two-writer) — it lands in the bus-owned inbox and the orchestrator **promotes** it into `backlog.md`
at a boundary (D69 triage). No `flock` — single-writer removes the write-conflict class. Every file that crosses the
process boundary is **published atomically** (write-temp → `fsync` → `rename` → `fsync(dir)`) so a reader never
catches a torn file — `state.json` included; `handoff.md` additionally fsyncs the dir for crash-durability.

**One orchestrator is an operator-guaranteed invariant, not an enforced one (D109).** Nothing *elects* the single
orchestrator: two concurrent `/start`/`--resume` processes would each believe they are the sole writer, and
atomic-publish prevents a torn read but **not** a lost update. The package deliberately does **not** defend against
that — it is a documented **run-constraint** (*run a single orchestrator per repo*), on the same footing as D93's
own single-writer premise, which was always an asserted invariant rather than a mechanism. **The one exception is
the relaunch-runner (D113):** because the runner is itself a spawner, a duplicate would be *our* defect rather than
operator error, so the runner checks a liveness marker before it spawns — the marker exists solely as the runner's
precondition, not as a general lock.

**Consume = record, never delete (D108).** Since the bus solely writes `inbox/`, the orchestrator **never removes a
consumed message**. It keeps a durable **consumed-set** of bus-assigned `message_id`s (+ a `consumed_through`
low-watermark) on `handoff.md`, skipping ids already in the set at each boundary drain; the **bus** GCs inbox files
at-or-below the published watermark, so neither partition gains a second writer and both the inbox and the set stay
bounded. The consumed-set alone is not sufficient — apply-then-record has a crash window, so **every kind also
carries an effect-level anchor** (verdict → the parked token · release → the outbox `executed` status · intake →
the source `message_id` stamped on the promoted item · control → the standing rule that control ops are
idempotent). The **sole** carve-out to never-delete: a consumed record carrying a **sensitive** payload is unlinked
by the orchestrator immediately after the credential is extracted to the secret store (D111), so a secret never
waits on a janitor — and the extraction, unlink and record are **one scripted step** (`drain.py secret`), so the
value never passes through a context window or a log (D119).

**The drain is split; only its judgment half is prose (D117).** The bookkeeping — which ids are new, their order,
the watermark, the prune, and `handoff.md`'s atomic+durable republish — is `scripts/drain.py` (`list` → apply →
`record`). Applying is judgment and stays in the driver artifacts. The split is measured: driven against real
sessions the apply half was right every time while the bookkeeping half silently produced an **unbounded**
consumed-set, because the rule lived in the decision log and never reached the consumer. `handoff.md` therefore
carries a **machine block** `drain.py` owns (`consumed[]` / `consumed_through` / `dead_letters[]`) beside the
orchestrator's prose; neither author rewrites the other's half (`shared/schemas.md`).

**The watermark rests on an ordering guarantee the bus must provide (D118).** GC-at-or-below-the-mark is safe only
because ids are issued in **visibility order** (name allocated + published under one lock, floored above both the
newest name on disk and the published watermark). Without it a message becomes visible beneath the mark and the
janitor deletes something nobody consumed — **measured**, and silent.

**Protocol — two mechanisms, no third (D93).** (1) Synchronous **reads** the bus serves straight from disk — no
orchestrator involvement. The bus is **not a static file server**: the console polls one *synthesized*, ETag'd
snapshot document (D99/D100), so the load-bearing fact is which paths the bus **reads**, not which URLs it exposes.
Those paths are the ones the layout tree marks **`bus:read`** (D114) — enumerated there, never here; the D102
static class (the page, its assets, the demo bundle) is marked `bus:static`. (2) Asynchronous
**commands**: the bus returns `202 Accepted` + a `Location` ticket and appends the message to the **inbox**; the
orchestrator consumes it at a scheduler boundary; any result surfaces via orchestrator-written state the console
re-reads by ticket (Async Request-Reply). **The orchestrator is never an HTTP responder** (D90) — a synchronous
request→orchestrator→response path cannot exist. Messages are **one typed inbox** — `kind: verdict|intake|control|release` —
single-consumer, idempotent, single-shot. File-watching stays **rejected for control-flow** (fragile, races); an
optional inotify/SSE signal only ever means "re-read", never carries the load.
- **`verdict`** resumes a parked ticket via `claude --resume <id> -p "<verdict>"` (D90); the checkpoint `token`
  matches a parked ticket; unknown/closed token → **dead-letter + surface** (never a silent resume); stale deadline →
  **escalate**. This is the correlation half of continue-while-parked interleaving (D91).
- **`intake`** becomes a D69-triaged backlog item — the `node/subgraph → ticket` project-map action (D70) is just an
  `intake` message (payload: node ID(s) + the ask), never a privileged fast-path. Node IDs are the code-map's stable
  keys (today relpath/module; symbol-level later).
- **`control`** is a non-preemptive loop command (reprioritize / pause), honored at the next boundary (D26).
- **`release`** is a human **batch-approval** of pending outward actions (D105) — `{ action_ids[] }`; the orchestrator
  fires each named `outbox/` entry (re-run through `guard.sh`) at the next boundary. It resumes **no** parked ticket
  (an outward action never parked the loop): a deferred side-effect, not a checkpoint verdict.
- **Conversation vs command (D93):** the console is **not** a real-time chat — the loop is a batch consumer.
  New-feature **dialogue** happens at the terminal (the live `discuss` session); the bus carries only *requests*
  (intake) + *bounded clarifications* (an orchestrator-parked checkpoint question). A future console chat would be
  async-turn-based (latency = the boundary cadence), never live.

**Lifecycle — a session-independent detached daemon (D94; BUILT — D115/D116).** Because the bus must receive
verdicts *while the orchestrator is parked or dead*, its lifecycle is **decoupled** from the orchestrator
conversation. It is spawned **detached in a new session** (`setsid` — survives `/clear` / `--resume` / session
death, since Claude Code doesn't reap children), binds a dynamic **loopback** port, and publishes
`{pid, port, token, started_at}` to `bus.json`. `/start` is **ensure-running (adopt-or-spawn), idempotent** —
liveness authority is a held `flock` **on its own `bus.lock`** + a token'd `/health`, **never spawn-fresh** (that
drops in-flight verdicts). The lock is a separate file *by necessity*, not tidiness (D115): a lock held on the
atomically-renamed `bus.json` is silently defeated by the next publish. Stop = an authenticated `POST /shutdown` +
an **idle-timeout self-shutdown** whose definition is D116's (an open checkpoint suppresses it; the heartbeat is
never the orchestrator's). **WSL2:** a detached daemon can't hold the distro VM open, so the bus dies ~8s after the
last terminal closes and re-spawns on the next `/start` (the durable inbox loses nothing already-written);
`loginctl enable-linger` / `.wslconfig vmIdleTimeout=-1` is the opt-in upgrade.

**The daemon is also the notifier (D111) — notification was never the Claude hook's job.** D90/D101 hung the alert
on the harness `Notification` hook, which is the one mechanism that structurally *cannot* do it: it is event-bound
(permission-prompt / ~60 s idle), so it does not fire at checkpoint-raise while D91 interleaving keeps the
orchestrator **busy** on the next ticket; it reaches only the machine running the loop, which is not where an away
human is; and it is dead precisely when the orchestrator is **whole-parked or crashed**. The three F4 facets (no
fire point · no reachable-away default · no timer owner) are all that one root error. The only process alive across
every one of those states is **this daemon**, so it owns notification end-to-end: it watches `parked/`, alerts on a
new open checkpoint, re-alerts every `config.checkpoint.reminder_hours`, and **escalates** once a `deadline` passes
(never auto-proceeding — D97). The `checkpoint` skill sends nothing: **writing the parked record *is* the trigger.**
Channel = `config.notify` — the **webhook is the real away channel** (reaches a phone, works from a detached
daemon); a desktop toast is best-effort (no session bus on WSL/headless, and it only reaches someone already at the
machine). **No webhook configured ⇒ no away alerting** — the human polls the console; stated plainly, because a
channel that silently reaches nobody is worse than a documented absence. Consequence: `templates/settings.json`
needs **no `Notification` hook at all**. This keeps D101's two-event taxonomy (checkpoint-raised · loop
hard-stop/escalation) intact and changes only the mechanism under it; the daemon likewise raises the hard-stop
event off an orchestrator-written marker. It is a deliberate widening of the daemon's role, and the justified one —
D94 already gave it janitor duty, and being always-alive is exactly the property the job requires.

**Trust — the browser/network is the untrusted caller, not same-UID (D95).** Loopback ≠ authenticated, and a forged
command drives an autonomous executor. The loopback stack (all mandatory): a **capability token** (in `bus.json`,
0600 atomic-create **whose achieved mode is then verified, never assumed** — D115, **header-only**, required on reads too, no cookie), a **strict Host-header allowlist** on every
endpoint (the DNS-rebinding defense), **JSON-only + a custom header** (forces the CSRF-defeating preflight), explicit
`127.0.0.1` bind. The **served page additionally carries a strict `Content-Security-Policy: script-src 'self'`** — the
console-side teeth of this posture; it forces the zero-build vanilla/Preact+htm frontend (no `unsafe-eval`), owned by
D100/`03`. The **port is not a secret**; the **bus token (auth) is distinct from the checkpoint token
(correlation)**. **A mode is a request, not a guarantee (D115 — measured):** Windows lacks 0600 (→ token-file ACLs),
*and* the WSL repo mount silently returns **0777** for a 0600 create — from Linux, with no error. So the create-with-
the-mode discipline is necessary but **not sufficient**: the achieved mode is **stat'd after creation**, and a
filesystem that ignored it is surfaced to the human rather than trusted. This is why `bus.json` is pinned **first for
mode, second for atomicity** — and it is the same rule the secret store leans on (the D89 OS/FS family, widened from
"Windows" to "any mount that ignores mode"). **Remote access — a structural two-socket split
(D112, superseding the D70/D107 unauthed warning-only tunnel):** the unauthed tunnel could not be built (D95's
"the loopback token is never tunnel auth" and D107's "read/verdict ride the tunnel" are mutually exclusive, since
those endpoints are token-gated), and a `Host`-header policy is no boundary at all — it hands a security decision
to a header the proxy controls. So: **socket B** is loopback-only and never fronted (full surface: outward
`release` + returns-bearing `setup` verdicts — the blanket Host-allowlist above stands here unmodified), while
**socket A** carries the reduced remote surface (reads · opinion verdicts · the static demo) and is served **only**
when `config.remote` declares an **identity transport** (Cloudflare Access | Tailscale). "Loopback-only" thus
becomes a fact about the **port topology**, not a promise about a header; A's own Host-allowlist is
anti-DNS-rebinding only. A **distinct remote token** (never the loopback one — D95 respected) is the second factor,
paired by QR + a **URL fragment** (which never leaves the browser — the precise amendment to "never in a URL",
whose target was the log-leaking `?token=` query param). The bar is set by D90: a verdict rides as an
*authoritative prompt*, so a forged one is **agent control**, not merely "local work".
**Built (D122 — increment 5); building sharpened four points.** (1) The remote token is **never served in the
remote page** — injecting it (as the loopback page does its own via the meta tag) would hand the surface to anyone
past the transport in a single GET, killing the "a misconfigured Access does not instantly expose it" property; it
rides the pairing fragment only. (2) The remote coordinates are **stable, not per-boot**: `remote_token` is persisted
(`.workflow/remote_token`, 0600-verified, minted once) and `remote_port` is **config-declared and fixed** — a
reminted token/port would break the phone pairing and the operator's tunnel on every WSL restart, the platform the
away channel most needs to survive. (3) The A/B credential boundary is the **structural presence of a `returns`/
`tasks` payload**, never the shallow `_is_sensitive` heuristic — a false negative there is a live key on a plaintext
edge, exactly the silent failure a structural boundary exists to prevent. (4) A's Host-allowlist must **add the
declared public host**, or a proxy that forwards the original Host has all its traffic 403'd — so
`config.remote.public_url` is load-bearing for the transport itself, not only the pairing link. **Pairing ships as a
copy-paste link** (the token in the fragment, which never leaves the browser); a hand-rolled QR is a **scoped
fast-follow** (no stdlib encoder, and an unscannable one cannot be verified in-harness).
**Two serving classes (D102 clarification):** the token gates the **sensitive data/command class** (state reads +
POSTs); the **static app-shell class** — the console page, its assets, and the **demo sandbox** (`/demo/*`) — is
served **token-free under the Host-allowlist**, because a browser can't attach a token header to a document/iframe
*navigation* and these files carry no secrets. So "token required on reads too" scopes to the sensitive *data*
reads; the demo (served under a `sandbox`-directive opaque origin — D102) joins the static class.

## Disk layout **[layout DECIDED — D53/D62; read/write protocols EXPAND]**
`init` (`commands/start.md`) scaffolds this layout in a target project.

**The tree is the OWNER of three per-path properties (D114)** — commit-class (`committed` / `RUNTIME`+gitignored),
**`bus:`** (what the bus daemon does with the path: `read` = it feeds the console read-model, token-gated ·
`static` = the D102 static class, raw bytes served token-free · `write` = the bus is the writer · `none` = the bus
never touches it), and **`pin`/`no-pin`** (native-FS-pinned — RUNTIME paths only; a committed file lives on the repo
mount by construction). **No prose below restates these sets** — every list that did drifted (D114); each points
here, and `scripts/check_enum_coherence.py` holds the two shipped consumers to the tree.
```
<launch root>      # where Claude runs = orchestrator home (process / machinery)
  CLAUDE.md         # orchestrator brief (greenfield: here; brownfield: a marked block in the existing one)
  .workflow/
    config.json     # project_root (./project | .) + run config; the daemon reads notify/checkpoint for the away channel — committed, so read across the repo mount (static after init; a parse failure ⇒ no away channel, surfaced) · bus:read
    runtime.json    # RUNTIME — the pointer to the pinned runtime root; absent ⇒ this dir IS the runtime root (the no-relocation case). Machine-specific absolute path ⇒ never committed. NEVER pinned itself: it is *how* the pinned tree is found, so it must sit at a fixed spot on the repo mount — D115, gitignored · bus:none · no-pin
    loop.md         # routing graph + diagram (fixed topology)      (committed) · bus:none
    checks.sh       # mechanical-gate runner (generated per-stack; --fix / --check)  (committed) · bus:none
    codemap.sh      # code-map generator (generated per-stack; writes docs/knowledge/graph.json)  (committed) · bus:none
    state.json      # live position (item/phase/wave) — RUNTIME (atomic-publish, D93), gitignored · bus:read · pin
    handoff.md      # durable resume anchor: the orchestrator's PROSE + a drain.py-owned machine block (consumed[]/consumed_through/dead_letters[]) — two authors, neither rewriting the other's half — D108/D117  (committed) · bus:read (the consumed_through watermark — the bus GCs the inbox on it; and dead_letters[]/consumed[] — the console's "my requests" surface resolves a ticket off them)
    backlog.md      # live OPEN queue: issues + roadmap (closed leave) (committed) · bus:read
    outbox/         # RUNTIME — pending-outward-action queue (push/issue/deploy the orchestrator deferred, awaiting a console `release`) — D105 (retires the D60-reserved checkpoints/), gitignored · bus:read (the console's release panel) · pin
    bus.json        # RUNTIME — the bus daemon's {pid,port,token,started_at,remote_port?,remote_token?} discovery record — D94/D122, gitignored · bus:write · pin (for the 0600-honouring mount FIRST, atomicity second — D115)
    bus.lock        # RUNTIME — the daemon's singleton-election lock, held for process lifetime. A SEPARATE file from bus.json by necessity: bus.json is republished by rename, and a rename swaps the inode out from under a held lock, so a second daemon would find the new inode unlocked and start (measured, both filesystems) — D115, gitignored · bus:write · pin (co-location with the record it guards; flock itself does NOT require it — D115)
    alerts.json     # RUNTIME — the daemon's away-alert bookkeeping (which checkpoints/dead-letters it has already alerted on). Cannot live in parked/ (not the daemon's partition) nor boot-scoped bus.json; a fourth daemon-owned path, loaded at start so a restart does not re-alert; lost ⇒ re-alert, never silent — D120, gitignored · bus:write · pin
    parked/<id>.json # RUNTIME — a parked ticket's resume record (token, state, predicted_outcome, deadline) — D91, gitignored · bus:read · pin
    inbox/          # RUNTIME — append-only TYPED command queue (verdict|intake|control|release) the bus writes; matched at boundaries — D90/D91/D93/D105, gitignored · bus:write · pin
    secrets/        # RUNTIME — live credentials returned at a setup checkpoint; 0600/ACL, atomic write; orchestrator writes+reads; NEVER retention-swept — D111, gitignored · bus:none · pin (for the 0600-honouring mount, not for atomicity)
    remote_token    # RUNTIME — the remote socket's STABLE second-factor token, persisted (0600, verified) so a phone paired once survives restarts; a per-boot token would re-pair every WSL restart. Minted once by the daemon, delete-to-rotate. Distinct from bus.json's loopback token — never reused — D122, gitignored · bus:none · pin (for the 0600-honouring mount)
    items/<id>/     # per-item artifacts (mkdir on demand; pruned once closed — D61)  (committed) · bus:none
    align/          # anchor.json — the drift-scan base_sha (align mkdir's it on first run) — committed · bus:none
    demos/<id>/     # RUNTIME — throwaway demo-sandbox bundle the bus daemon serves under a sandbox-CSP opaque origin; pruned on checkpoint-resolve — D102/D104, gitignored · bus:static · no-pin (write-once-then-serve, atomicity-light — D104)
  <worktrees>/      # RUNTIME — one git worktree per in-flight ticket (D91); raw `git worktree`, gitignored · bus:none · no-pin
  <project_root>/   # the product (greenfield: project/ ; brownfield: the repo root)
    CLAUDE.md       # the product's own brief
    llms.txt        # thin agent entry point → points into docs/knowledge/  (committed)
    docs/           # ← the DOCS-ROOT — durable product knowledge (D62)
      spec/         # the product spec (discuss fills it)           (committed)
      architecture.md  # inline Mermaid-C4 L1/L2 (document-owned)   (committed)
      knowledge/    # code map — Space 6 (index.md, graph.json, nodes/)  (committed) · bus:read (graph.json — the map tab, post-MVP)
      decisions/    # decision-records = ADRs (append-only, global) (committed)
    <product code>
```
**Commit policy:** everything durable is committed; everything the tree marks **RUNTIME** is gitignored. (The set
is the tree's, not a second list here — `commands/start.md`'s gitignore scaffold is its one shipped restatement,
gate-held to the tree.)

**Runtime coordination on a native FS (D93; the *reasons* corrected by measurement — D115).** The atomic-publish +
inbox guarantees (POSIX `rename` atomicity, `fsync`, `inotify`) hold on a **local** filesystem and are weak-to-broken
on network-style mounts (NFS; and on WSL2 the repo's `/mnt/c` DrvFs/9p mount — the same class). So every runtime path
the tree marks **`pin`** is relocated to a **native-FS path** (e.g. under `$HOME` on ext4), not the repo mount;
`/start` detects a DrvFs/network mount and relocates-or-warns. The pinned set is **not restated here** (D114): a
hand-kept second copy is precisely how `outbox/` never reached it and how `secrets/` reached one copy of it and not
the other.

**Which guarantee actually fails, measured on the real 9p mount (D115) — the pin stands, two of its three stated
reasons did not.** The pin was justified by a *bundle* of "weak-to-broken" guarantees, and the bundle is wrong:
- **File mode — FAILS, silently and open.** A 0600 create returns **0777**. This is the pin's *strongest* reason and
  it was previously filed under "Windows", so it read as a portability footnote rather than a live exposure on the
  maintainer's own machine. It is why `bus.json` and `secrets/` cannot sit on the repo mount.
- **`rename` atomicity — the pin's real second reason** (unchanged; a torn read across the mount is the D93 concern).
- **`flock` — DOES NOT fail.** It excludes a second holder correctly and the kernel releases it on death, on 9p
  exactly as on ext4. **"`flock` is unreliable on DrvFs" is false as stated** and must not be repeated as the reason
  to pin anything: the lock is Linux-kernel-mediated within one distro, which is precisely the only case that
  matters (the daemon and `/start` are both Linux processes there). It would not coordinate with a *Windows* process
  — a real limit, and a different claim.

**How a pinned path is found — the resolver (D115).** The marker was declared but never made *actionable*: nothing
recorded where a relocation went, and nothing could compute it. `bus.json` is itself pinned, so the discovery record
lived inside the tree you needed it to discover. The resolution is a **gitignored `runtime.json` pointer** on the
repo mount (`{runtime_root}`), written by `/start`; **absent ⇒ `.workflow/` is the runtime root** — the common
non-WSL case, at zero indirection. A pointer naming a missing root **fails loudly**: silently falling back to the
repo mount would put the token and the inbox on the exact filesystem the relocation exists to avoid.

The **committed** durable artifacts stay in the repo and are therefore **never pinned** — a committed file lives on
the repo mount by construction, so `pin` is a RUNTIME-only question. **This is not because "git doesn't need
rename-atomicity"** (D114 corrects that reasoning — it was a non-sequitur): three committed files are `bus:read`
(`handoff.md`, `backlog.md`, `graph.json`), so the **bus** reads them across the weak mount even though git doesn't
care. The exposure is **bounded and accepted**, not overlooked: a torn read interleaves old and new bytes, so it
cannot fabricate a `consumed_through` *higher* than one the orchestrator actually published — inbox GC can only
**lag, never over-collect** (and D108 already scopes GC as hygiene, not a hot path); a torn `backlog.md`/`graph.json`
render is cosmetic and self-heals on the next 2–5 s poll. `.workflow/` is therefore **split across two filesystems**
whenever `/start` relocates — the tree is one logical layout, not one mount. Same "target OS/FS isn't POSIX-ext4"
family as the D89 shipped-glue gap.

**Continue-while-parked isolation (D91):** each in-flight ticket develops in its own **git worktree** on its own
branch; a checkpoint parks it with a `WIP:` commit + a `parked/<id>` record, and the loop interleaves to the next
independent ticket (≤3 concurrent, prefer-serial). `handoff.parked[]` lists every parked ticket so a cold start
rebuilds them all from `parked/` + `inbox/`. Resume = un-WIP → `rebase` onto trunk (`rerere`) → `verify` → final
commit → merge → `worktree remove`.

**Memory tiers (D38 — `shared/memory-model.md`):** every durable file is **volatile** (rewrite freely:
`state.json`, `handoff.md`, and `backlog.md` — a live *open* queue, closed items leave, D59), **stable**
(change only with the code that changes it, CI-gated: `docs/spec/`, the inline Mermaid-C4 `docs/architecture.md`
— D41, *not* a separate `diagrams/`), or **append-only** (supersede, never edit: `docs/decisions/`, the
per-file `# Sessions` sections). Skills key off location + filename to know their rights.

**Resume model (D48).** `state.json` is the volatile live pointer (rewritten in place); `handoff.md` is the
durable resume anchor (program counter — current item + loop position + parked work); **git history is the
append-only completed-step log** (each item ends in a `commit`). Mid-run the orchestrator reads `state.json`;
a cold start reads `handoff.md` + `git log` and rebuilds. **Bounded by construction (D51):** every
always-read file (`CLAUDE.md`, `state.json`, `handoff.md`, `loop.md`) holds current state only — never history.

## Outward-action permission — the outbox **[DECIDED — D105/D35]**
Local/reversible work runs autonomously; every **outward, side-effecting** action (`git push`, `gh issue create`,
`gh issue close`, later deploys / message-sends) is gated — but **the loop never stalls** (D35). An outward action is
**not** a checkpoint: it doesn't park the ticket (the commit is already local, the ticket completes, the loop
advances). It is the **transactional-outbox** pattern:
- **Defer, don't block.** The skill self-gates against **`config.outward`** (Claude Code's `permissions.{allow,ask,deny}`
  shape, deny→ask→allow, coarse per-action-class, default all `ask`). Match `allow` → run the command (still through
  `guard.sh`); else **append a record to `.workflow/outbox/` and continue** — never attempt-and-let-the-harness-`ask`
  (that blocks + can't work away-from-terminal).
- **The harness is out of the outward path entirely (D110).** `settings.json` carries **no `ask`** for the
  outbox-covered classes (`git push`, `gh issue`), because the release fires the command *later*, at a boundary:
  a static prompt would land in a terminal nobody is watching and block the away-release the whole model exists to
  serve. So the harness `ask` **cannot** be the backstop D105 assumed — the two are mutually exclusive, and
  away-release wins. `config.outward` is therefore the **sole owner** of the outward allow/ask fact (closing the
  D80 two-owner conflict), and the gate reads: **skill self-gate → outbox/release → `guard.sh` floor**. Accepted
  cost: a *mis-coded* skill running an outward command directly is caught only by the floor, not a prompt — a
  first-party bug to fix, not fence. (Un-queued outward commands — deploy/publish/cloud — keep their `ask`.)
- **Release drains it.** The console renders the pending `outbox/`; the human approves a batch → a **`kind: release`**
  inbox message (explicit `action_ids`) → the orchestrator fires each at a boundary (re-run through `guard.sh`), marks
  it `executed`. One approval releases a batch (D35).
- **Two layers.** `guard.sh` = the non-overridable mechanical floor (Layer 1); `config.outward` = the overridable
  human-approval layer (Layer 2). Standing pre-auth waives the human, never the checks. Fine-grained scoping (never
  auto-push `main`) lives in `guard.sh`, not fragile config allow-patterns.
- **The push floor (D110) — the mechanism the "never auto-push `main`" promise was leaning on, now built.** On any
  `git push` the floor resolves the target refspec (`origin main`, `HEAD:main`, a leading `+`, `--force`,
  `--all`/`--mirror`, and a bare `git push` via upstream/`push.default`) and **blocks *any* push to a protected
  branch — not merely a force-push**, then secret-scans the **outgoing range** (a commit can reach a branch by a
  path the commit-time gate never saw). Protected = `{main, master}` **always**, `config.guard.protected_branches`
  **adds** to it and can never subtract. So the loop ships feature branches autonomously and a **human** moves
  `main` — the highest-blast-radius action stays a deliberate human act. This is *absolute*: there is no
  approved-release exception, which is precisely why it needs no release-authorization marker to distinguish an
  approved main-push from a stray one. The refspec parse fails **closed** (unparseable → blocked).
- **Safety** (the outbox anti-patterns, closed up front): each entry is **state-bound** and re-validated on release
  (divergent history invalidates + re-surfaces, never silently fires — TOCTOU); a **TTL** drops a stale entry (never
  fires late); release is **always by explicit `action_id`** (batch snapshot). **No notification** (D101 — a pull
  surface on the D99 cockpit, not a ping) and **no durable ledger** (the external consequence is the audit — D60).
  Schema: `shared/schemas.md` *outbox* + *inbox-message* (`release`) + `config.outward`.

Still to close: symbol-level knowledge paths. *(Read/write ownership + the request/response protocol closed — D93
[single-writer + the two-mechanism protocol]; bus lifecycle — D94; bus trust — D95; **outward-action mechanics — D105**;
retention/read law — D61; docs-root unified under `<project_root>/docs/` — D62.)*

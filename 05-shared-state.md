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
waits on a janitor.

**Protocol — two mechanisms, no third (D93).** (1) Synchronous **reads** the bus serves straight from disk
(`state.json` / `backlog.md` / `parked/` / `graph.json`) — no orchestrator involvement. (2) Asynchronous
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

**Lifecycle — a session-independent detached daemon (D94).** Because the bus must receive verdicts *while the
orchestrator is parked or dead*, its lifecycle is **decoupled** from the orchestrator conversation. It is spawned
**detached in a new session** (`setsid` — survives `/clear` / `--resume` / session death, since Claude Code doesn't
reap children), binds a dynamic **loopback** port, and publishes `{pid, port, token, started_at}` to
`.workflow/bus.json`. `/start` is **ensure-running (adopt-or-spawn), idempotent** — liveness authority is a held
`flock` + a token'd `/health`, **never spawn-fresh** (that drops in-flight verdicts). Stop = an authenticated
`POST /shutdown` + a heartbeat-aware idle-timeout self-shutdown (the orphan janitor). **WSL2:** a detached
daemon can't hold the distro VM open, so the bus dies ~8s after the last terminal closes and re-spawns on the next
`/start` (the durable inbox loses nothing already-written); `loginctl enable-linger` / `.wslconfig vmIdleTimeout=-1`
is the opt-in upgrade.

**Trust — the browser/network is the untrusted caller, not same-UID (D95).** Loopback ≠ authenticated, and a forged
command drives an autonomous executor. The loopback stack (all mandatory): a **capability token** (in `bus.json`,
0600 atomic-create, **header-only**, required on reads too, no cookie), a **strict Host-header allowlist** on every
endpoint (the DNS-rebinding defense), **JSON-only + a custom header** (forces the CSRF-defeating preflight), explicit
`127.0.0.1` bind. The **served page additionally carries a strict `Content-Security-Policy: script-src 'self'`** — the
console-side teeth of this posture; it forces the zero-build vanilla/Preact+htm frontend (no `unsafe-eval`), owned by
D100/`03`. The **port is not a secret**; the **bus token (auth) is distinct from the checkpoint token
(correlation)**. Windows lacks 0600 → token-file ACLs (the D89 OS/FS family). **Tunnel (D70, owner-accepted):** opt-in
/ warning-only / no auth — with the one rule that the loopback token is **never** reused as tunnel auth.
**Two serving classes (D102 clarification):** the token gates the **sensitive data/command class** (state reads +
POSTs); the **static app-shell class** — the console page, its assets, and the **demo sandbox** (`/demo/*`) — is
served **token-free under the Host-allowlist**, because a browser can't attach a token header to a document/iframe
*navigation* and these files carry no secrets. So "token required on reads too" scopes to the sensitive *data*
reads; the demo (served under a `sandbox`-directive opaque origin — D102) joins the static class.

## Disk layout **[layout DECIDED — D53/D62; read/write protocols EXPAND]**
`init` (`commands/start.md`) scaffolds this layout in a target project:
```
<launch root>      # where Claude runs = orchestrator home (process / machinery)
  CLAUDE.md         # orchestrator brief (greenfield: here; brownfield: a marked block in the existing one)
  .workflow/
    config.json     # project_root (./project | .) + run config    (committed)
    loop.md         # routing graph + diagram (fixed topology)      (committed)
    checks.sh       # mechanical-gate runner (generated per-stack; --fix / --check)  (committed)
    codemap.sh      # code-map generator (generated per-stack; writes docs/knowledge/graph.json)  (committed)
    state.json      # live position (item/phase/wave) — RUNTIME (atomic-publish, D93), gitignored
    handoff.md      # durable resume anchor                         (committed)
    backlog.md      # live OPEN queue: issues + roadmap (closed leave) (committed)
    outbox/         # RUNTIME — pending-outward-action queue (push/issue/deploy the orchestrator deferred, awaiting a console `release`) — D105 (retires the D60-reserved checkpoints/), gitignored
    bus.json        # RUNTIME — the bus daemon's {pid,port,token,started_at} discovery record — D94, gitignored
    parked/<id>.json # RUNTIME — a parked ticket's resume record (token, state, predicted_outcome, deadline) — D91, gitignored
    inbox/          # RUNTIME — append-only TYPED command queue (verdict|intake|control|release) the bus writes; matched at boundaries — D90/D91/D93/D105, gitignored
    items/<id>/     # per-item artifacts (mkdir on demand; pruned once closed — D61)  (committed)
    align/          # anchor.json — the drift-scan base_sha (align mkdir's it on first run) — committed
    demos/<id>/     # RUNTIME — throwaway demo-sandbox bundle the bus daemon serves under a sandbox-CSP opaque origin; pruned on checkpoint-resolve — D102/D104, gitignored
  <worktrees>/      # RUNTIME — one git worktree per in-flight ticket (D91); raw `git worktree`, gitignored
  <project_root>/   # the product (greenfield: project/ ; brownfield: the repo root)
    CLAUDE.md       # the product's own brief
    llms.txt        # thin agent entry point → points into docs/knowledge/  (committed)
    docs/           # ← the DOCS-ROOT — durable product knowledge (D62)
      spec/         # the product spec (discuss fills it)           (committed)
      architecture.md  # inline Mermaid-C4 L1/L2 (document-owned)   (committed)
      knowledge/    # code map — Space 6 (index.md, graph.json, nodes/)  (committed)
      decisions/    # decision-records = ADRs (append-only, global) (committed)
    <product code>
```
**Commit policy:** everything durable is committed; the **runtime** view (`state.json`, `bus.json`, `outbox/`,
`parked/`, `inbox/`, `demos/`, the per-ticket worktrees) is gitignored.

**Runtime coordination on a native FS (D93).** The atomic-publish + inbox guarantees (POSIX `rename` atomicity,
`fsync`, `inotify`) hold on a **local** filesystem and are weak-to-broken on network-style mounts (NFS; and on WSL2
the repo's `/mnt/c` DrvFs/9p mount — the same class). So the atomicity-sensitive runtime subtree (`state.json`,
`bus.json`, `parked/`, `inbox/`) is pinned to a **native-FS path** (e.g. under `$HOME` on ext4), not the repo mount;
`/start` detects a DrvFs/network mount and relocates-or-warns. The **committed** durable artifacts stay in the repo
(git doesn't need rename-atomicity). Same "target OS/FS isn't POSIX-ext4" family as the D89 shipped-glue gap.

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

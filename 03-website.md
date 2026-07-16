# 03 — Website (Space 3: local console)

## Role **[DECIDED]**
A LOCAL web app that is (a) a **visualization of the project** (roadmap, knowledge graph, current
activity, checkpoints) and (b) **the human's channel to the orchestrator**. It talks to the
orchestrator only via the local bus + files — never by routing Claude.

## Comms **[DECIDED — bus contract owned by `05` (D93/D94/D95)]**
- Hosts the **local HTTP loopback bus** (its own backend). The full contract — ownership, protocol, lifecycle,
  trust — is owned by `05`; the console side is only a **client** of it.
- **Two mechanisms (D93):** the console **reads** live state synchronously from the files the bus serves
  (`state.json` + the knowledge base), and **commands** are async — a POST gets `202 Accepted` + a ticket, lands in
  the durable **typed inbox** (`verdict|intake|control|release`), and the orchestrator consumes it at a boundary. **The
  orchestrator never responds synchronously** (D90), so the console is a state-reader + command-sender, **not a
  chat**; a result surfaces as state the console re-reads by ticket.
- **Verdict delivery (D90/D91):** a verdict POSTs → durable inbox keyed by the checkpoint **token** → the parked
  orchestrator matches it at a boundary and resumes via `claude --resume`.

## Launch **[DECIDED — D94; BUILT — D115/D116]**
The bus is a **session-independent detached daemon**, not a session child — it must receive verdicts while the
orchestrator is parked or dead. `/start` **ensures it is running** (adopt-or-spawn, idempotent: a held `flock` on its
own `bus.lock` + a token'd `/health` is the liveness authority; it publishes `{pid, port, token, started_at}` to
`bus.json` on a dynamic loopback port). Spawned **detached in a new session** (`setsid`) so it survives `/clear` /
`--resume` / session death — **verified end-to-end** (own session leader; outlives the terminal that spawned it).
Stop = an authenticated `POST /shutdown` + an idle-timeout self-shutdown that an **open checkpoint suppresses**
(D116). **On WSL2** the bus dies ~8s after the last terminal closes and re-spawns on the next `/start` (the durable
inbox loses nothing already written). It ships as **`.claude/scripts/bus.py`**, a per-project copy like every other
shipped script — which is also what keys it per project (D116). Full lifecycle + the runtime-path resolver in `05`.

## Project map + flow view **[DECIDED — D70; placement = a tab, D99; build deferred to Phase 2/3]**
A **project-map screen** renders the code-map `graph.json` (D68) as a cluster diagram — nodes sized by the
**impact lens**, clustered by the **directory tree**, semantic-zoom (cluster → file → [later] symbol). It is the
structural face of the deferred **project-state view** (`07`). **Placement resolved (D99): a tab, not the console
home, and not the first cut** — it is Mode B (explore), whereas the MVP is Mode A (supervise). Two complementary layers:
- **Static skeleton** — always available, no run needed.
- **Flow overlay** — a **highlighted subgraph** ("watch a message get sent") captured by *observing an actual
  run* (differential trace; noise-filter + mechanism are a direction, OPEN — see D70/`07`), laid over the skeleton.
- **Reserved data-contract seam:** the renderer accepts a **flow-overlay layer** (a labelled list of node IDs +
  edges to highlight) from day one, even though capture is later.
- **Interaction:** clicking a node emits a **scoped intake ticket** via the bus (`05`) — an ordinary D69-triaged
  backlog item, **not** a live edit channel (a *scoping aid for intake*, never a backdoor around it).

## Remote control **[DECIDED — D112 (supersedes the D70/D95/D107 "unauthed warning-only tunnel")]**
Local-served by default; opt-in **remote access** puts the console on a phone. The old model (an unauthed tunnel
that *warns*) **could not be built as specced**, for two independent reasons D112 resolves:

**(1) The unauthed tunnel was self-contradictory.** D95 says the loopback token is **never** reused as tunnel auth;
D107 says read+verdict ride the tunnel — but every one of those endpoints is token-gated, so a verdict-capable
remote browser **must** hold the token. Both cannot be true: either the token goes over the wire (violating D95) or
the tunnel serves nothing useful. **(2) A `Host`-header policy is not a boundary.** Distinguishing "loopback" from
"the tunnel" by `Host` makes a security decision out of a header the untrusted proxy controls — it fails *silently*
if `cloudflared` rewrites it. **A boundary must be structural.**

**A forged verdict is agent control, not "local work" (the finding that sets the bar).** D107 rated verdicts
low-consequence because "a forged verdict drives *local* work". But D90 makes the verdict ride as
`claude --resume -p "<verdict>"` — an **authoritative prompt** — and `notes` is free text. So anyone who can POST a
verdict injects arbitrary authoritative instructions into an autonomous code agent. D107's rating is wrong **twice**:
once for credential-bearing setup verdicts (below), and once for *every* verdict, via `notes`. A bare bearer token
on a public URL is therefore **not** an adequate gate.

**The model — a structural two-socket split + a declared identity transport:**
- **Socket B — loopback-only, never fronted.** The full surface: **outward `release`** and **returns-bearing
  `setup` verdicts**. Unreachable remotely as a fact about the network, not a promise about a header. D95's blanket
  Host-allowlist stands here **unmodified**.
- **Socket A — the reduced remote surface:** reads · **opinion verdicts** (`demo`/`qa`/`reconcile` — an opinion, no
  payload) · the static demo. Served **only** when `config.remote` declares an **identity transport**:
  **Cloudflare Access** or **Tailscale `serve`**. Declared `none`/absent → **A is not served at all** (loopback
  only). Both transports cost the same in code — the daemon just serves A; the operator puts the gate in front.
- **A distinct remote token** gates A as a **second factor** on top of the transport identity (D95's "never reuse
  the loopback token" respected; its "three independent failures" logic applied) — so a misconfigured Access does
  not instantly expose the surface.
- **Pairing = QR + URL fragment.** The local console renders a QR of `https://<host>/#t=<remote-token>`; the phone
  scans, stores it in `localStorage`, strips the fragment. **This amends D95's "never in a URL"**: that rule
  targeted the Jupyter **`?token=` query param** (server-logged, `Referer`-leaked). A **fragment never leaves the
  browser** — not sent to the server, not in the proxy's logs, not in `Referer`. So: *never in query/path; the
  fragment is the pairing channel.*
- **A keeps a Host-allowlist, but its role changes** — A is loopback-bound (the proxy connects to it), so a local
  browser could hit it directly: the allowlist is **anti-DNS-rebinding**, **not** the loopback-vs-remote boundary.
  The port topology is the boundary.
- **We do not own the tunnel lifecycle.** The operator runs `cloudflared` / `tailscale serve` against the port
  `bus.json` publishes, and is responsible for the declared transport being real — the same operator-responsibility
  stance as the single-orchestrator run-constraint (D109). This is what collapses the build cost to: a second
  socket, a second token, a QR, one config key.
- **No JWT library** (D100 stdlib-only holds): we do not verify the Access assertion — A is loopback-bound and only
  the proxy reaches it.

**The risk taxonomy — what may ride A** (correcting D107): a verdict carrying only an **opinion** may; a verdict
carrying a **payload** may not. **Release** never rides A. **Returns-bearing setup verdicts** are loopback-only by
default — they write live credentials *and* trigger a machine-verify probe to a caller-chosen endpoint (SSRF-lite +
credential substitution). **One transport-confidentiality carve-out:** a credential may ride an **end-to-end
encrypted** private transport (**Tailscale** — WireGuard; nobody in the middle sees it) but **never** a
**TLS-terminating proxy** (**Cloudflare Access** — the edge sees plaintext, so a Stripe key would transit a third
party). This matters because `setup` is the *hardest* away-blocker (D97: a missing credential cannot be skipped) —
so the carve-out is what makes Tailscale the recommended transport: no domain, E2E, and strictly more capable.

## Console model + screens **[DECIDED — D99 (closes B1/B2/B3)]**
**MVP = a read-only supervision cockpit, not a project explorer.** The console has two latent modes — *supervise a
live run* and *explore the project* — and only supervision is MVP (the dogfood's one critical-path job: deliver a
checkpoint verdict + status away from the terminal).
- **Home = a run-status cockpit:** current item · wave/parked tickets · **pending checkpoints** · recent activity —
  rendered from a **subset** of the bus's read-model inputs (the paths `05`'s layout tree marks `bus:read`, plus
  `git log` for recent activity — a computed input, not a served file; D93/D114). Which paths the bus reads is the
  tree's fact; which of them feed *this tab* is the UI's, and they are not the same list — the home leans on
  `state.json` / `parked/` / `backlog.md` / `handoff.md` / git, while `graph.json` feeds the later map tab and
  `outbox/` the release panel below.
- **Screen list (MVP → later):** cockpit (home) · checkpoint console · **"my requests"** · roadmap/backlog
  (read-only) → *later* tabs: the project map (above), knowledge exploration. **The map is a tab, not the home, and
  not the first cut** — resolves the `07` tab-vs-home question: **tab** (D70 is stageable; its value needs the
  deferred flow-overlay + later arms).
- **Refresh = snapshot polling, no SSE in MVP** (B2): one chained-`setTimeout` loop (~2–5 s) reads the whole state
  JSON; a monotonic `version`/`ETag` → `304` skips the re-render; polling pauses on `document.hidden`. inotify→SSE is
  the reserved "re-read" ergonomics hint (D93), never load-bearing — safe because urgency rides the **daemon's
  out-of-band alert** (below), not the page.
- **Contact-orchestrator UX** (B3 — the D93 principle made concrete) **[BUILT — D117/D118/D119]** = POST forms + a
  feedback surface: a
  **verdict** form (D97 `{outcome, notes, returns?}` / plural `tasks[]`; renders the D98 steps + verified deep-links +
  breadcrumbs for `setup`), an **intake** form (the D70 node→ticket click is a pre-filled intake), a **release** form
  (D105 — the pending-outbox panel: the queued outward actions, batch-approved by explicit `action_ids` → a
  `kind: release` POST), and the **"my requests" view** — each POST returns `202` + a `Location` ticket saved to
  `localStorage`; the view is the polled state *filtered* by those ticket ids, so `pending→consumed→resolved` is
  legible with **no new endpoint**. This is what keeps the async, not-a-chat model (D93) usable instead of a void.
  **As built:** `POST /api/{verdict,intake,control,release}` → validate (a bad message is refused with a reason at
  POST time, while a caller is still listening — once it is on the inbox the only reader is a batch consumer that
  can answer nobody) → atomic append → `202` + `Location: /api/requests/<message_id>`. **The ticket IS the
  `message_id`** (D119) — no second id — and "my requests" resolves off the **per-kind effect anchors D108 already
  required**, so it still answers after the message is GC'd and the set pruned (an intake reads *became item-9*, a
  dead-letter reads its reason). `control` is a closed enum; a `sensitive` verdict is redacted from the drain's
  output and moved by `drain.py secret` (D119).
- **Pending outward actions (D105)** ride the cockpit as a **pull** surface (a count + the release form), **not** a
  notification (D101 excluded outward-gate pings) — an outward action doesn't block the loop, so it doesn't interrupt.

## Stack **[DECIDED — D100 (closes B4)]**
A **daemon process + a static page it serves**, not a web app — the shape is forced by A2/A3/A4 + the pure-config
master rule, so B4 was *more* constrained than "deferred" implied.
- **Backend:** a single-file **stdlib-Python** daemon on `http.server.ThreadingHTTPServer` + a custom
  `BaseHTTPRequestHandler` — no vendored dependency, no framework (it *is* the D94 detached daemon). Build-contract
  footguns: `POST /shutdown` calls `server.shutdown()` from a **spawned thread** (never inline → deadlock); cap the
  body at `Content-Length` + set `handler.timeout` (`413` on oversize); keep `protocol_version` at HTTP/1.0.
- **Frontend:** **zero-build static files** — vanilla JS (`<template>` + `textContent`) by default, **Preact+htm**
  (~4.5 KB ESM, no eval) the one pre-vetted escape hatch.
- **CSP:** the daemon serves a strict **`Content-Security-Policy: script-src 'self'`** — the page-side teeth of D95,
  and the reason Alpine-standard/petite-vue (both need `unsafe-eval`) are out.
- **Why this and not a framework:** the pure-config package has no install/build step we control, `python3` is already
  the one hard dependency (D71), and the D95 CSP rules out CDNs — every comparable local-first tool
  (Syncthing/Ollama/Jupyter) uses its language's built-in HTTP server for exactly this reason.

## Attention / notification **[DECIDED — D101 taxonomy; mechanism corrected by D111]**
MVP **event taxonomy** (D101, unchanged) = fire on exactly **(1) a checkpoint being raised** and **(2) the loop
hard-stopping / an escalation** (a D92 thrash-stop, or a D91/D97 dead-letter / stale-deadline escalation).
Reminders are **not** a new event — they ride D97's timeout-resurfacing + D91 aging. Per-step progress /
per-item-done / outward-gate pings are out of MVP (false-positive noise trains the human to ignore the channel).

**Mechanism — the daemon, not the `Notification` hook (D111).** D90/D101 assumed the harness `Notification` hook;
it structurally cannot do the job — event-bound (permission-prompt / idle) so it doesn't fire at raise-instant
while D91 interleaving keeps the orchestrator busy, unable to reach anyone *away*, and dead exactly when the
orchestrator is whole-parked or crashed. **The always-alive daemon owns notification instead** (`05`): it watches
`parked/`, alerts on a new open checkpoint, re-alerts every `config.checkpoint.reminder_hours`, escalates past the
absolute `deadline` (never auto-proceeding), and raises the hard-stop event off an orchestrator-written marker.
The `checkpoint` skill sends nothing — writing the parked record *is* the trigger. Channel = `config.notify`: the
**webhook is the away channel** (a phone, from a headless daemon), desktop toast is best-effort, and **no webhook
⇒ no away alerting** (the human polls the console) — stated plainly, not implied. So the shipped `settings.json`
needs **no `Notification` hook at all**.

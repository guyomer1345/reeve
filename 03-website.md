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

## Launch **[DECIDED — D94]**
The bus is a **session-independent detached daemon**, not a session child — it must receive verdicts while the
orchestrator is parked or dead. `/start` **ensures it is running** (adopt-or-spawn, idempotent: a held `flock` +
a token'd `/health` is the liveness authority; it publishes `{pid, port, token, started_at}` to `.workflow/bus.json`
on a dynamic loopback port). Spawned **detached in a new session** (`setsid`) so it survives `/clear` / `--resume` /
session death. Stop = an authenticated `POST /shutdown` + an idle-timeout self-shutdown. **On WSL2** the bus dies
~8s after the last terminal closes and re-spawns on the next `/start` (the durable inbox loses nothing already
written). Full lifecycle in `05`.

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

## Remote control **[DECIDED — D70]**
Local-served by default; opt-in **"remote control"** serves the console over a temporary **Cloudflare tunnel**
(same tunnel capability as `00`'s QA phone-ping). Off by default + ships an explicit **"unsafe" warning** now
(tunneling breaks the loopback trust model); **auth is a reserved future requirement**, not built now. **D70 stands
(owner-accepted risk, D95):** warning-only / no auth for now — with the one hard rule that the loopback capability
token is **never** reused as tunnel auth (over the wire there is no 0600 file to gate it). Real tunnel auth
(Cloudflare Access / HMAC) is the reserved upgrade for when the risk is no longer acceptable.

**Outward-release is loopback-only over an unauthed tunnel (D107).** The E2 outbox (D105) adds the highest-consequence
console interaction: a forged *verdict* drives *local* work, but a forged **release** fires an *outward, irreversible*
effect (push/deploy). So over the owner-accepted unauthed tunnel, **the release form is served/accepted on loopback
only**; read + verdict inherit the pre-existing owner-accepted caveat (as demo-viewing did, D102). Real tunnel auth
moves from *reserved-optional* to **required-before-remote-release** — the tunnel carries low-consequence interactions
at owner-accepted risk, but not "authorize an outward side-effect" until auth lands.

## Console model + screens **[DECIDED — D99 (closes B1/B2/B3)]**
**MVP = a read-only supervision cockpit, not a project explorer.** The console has two latent modes — *supervise a
live run* and *explore the project* — and only supervision is MVP (the dogfood's one critical-path job: deliver a
checkpoint verdict + status away from the terminal).
- **Home = a run-status cockpit:** current item · wave/parked tickets · **pending checkpoints** · recent activity —
  rendered from the files the bus serves synchronously (`state.json` / `backlog.md` / `parked/` / `handoff.md` / git; D93).
- **Screen list (MVP → later):** cockpit (home) · checkpoint console · **"my requests"** · roadmap/backlog
  (read-only) → *later* tabs: the project map (above), knowledge exploration. **The map is a tab, not the home, and
  not the first cut** — resolves the `07` tab-vs-home question: **tab** (D70 is stageable; its value needs the
  deferred flow-overlay + later arms).
- **Refresh = snapshot polling, no SSE in MVP** (B2): one chained-`setTimeout` loop (~2–5 s) reads the whole state
  JSON; a monotonic `version`/`ETag` → `304` skips the re-render; polling pauses on `document.hidden`. inotify→SSE is
  the reserved "re-read" ergonomics hint (D93), never load-bearing — safe because urgency rides the Notification hook
  (below), not the page.
- **Contact-orchestrator UX** (B3 — the D93 principle made concrete) = POST forms + a feedback surface: a
  **verdict** form (D97 `{outcome, notes, returns?}` / plural `tasks[]`; renders the D98 steps + verified deep-links +
  breadcrumbs for `setup`), an **intake** form (the D70 node→ticket click is a pre-filled intake), a **release** form
  (D105 — the pending-outbox panel: the queued outward actions, batch-approved by explicit `action_ids` → a
  `kind: release` POST), and the **"my requests" view** — each POST returns `202` + a `Location` ticket saved to
  `localStorage`; the view is the polled state *filtered* by those ticket ids, so `pending→consumed→resolved` is
  legible with **no new endpoint**. This is what keeps the async, not-a-chat model (D93) usable instead of a void.
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

## Attention / notification **[DECIDED — D101 (closes B5)]**
Mechanism settled in D90 (the `Notification` hook → desktop-native + opt-in Slack/HTTP webhook; phone/tunnel later).
MVP **event taxonomy** = fire on exactly **(1) a checkpoint being raised** and **(2) the loop hard-stopping / an
escalation** (a D92 thrash-stop, or a D91/D97 dead-letter / stale-deadline escalation). Reminders are **not** a new
event — they ride D97's timeout-resurfacing + D91 aging. Per-step progress / per-item-done / outward-gate pings are
out of MVP (false-positive noise trains the human to ignore the channel).

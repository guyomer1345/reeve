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
  the durable **typed inbox** (`verdict|intake|control`), and the orchestrator consumes it at a boundary. **The
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

## Project map + flow view **[DECIDED — D70; build deferred to Phase 2/3]**
A **project-map screen** renders the code-map `graph.json` (D68) as a cluster diagram — nodes sized by the
**impact lens**, clustered by the **directory tree**, semantic-zoom (cluster → file → [later] symbol). It is the
structural face of the deferred **project-state view** (`07`). Two complementary layers:
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

## To close **[OPEN — cluster B]**
- **B1 — the screen list** (candidate set: project dashboard, roadmap/todos, **project map — specified, D70**,
  checkpoint console, activity/agent log, handoff/restart prompt) — and whether the map is a **tab or the
  home/overview** (`07`).
- **B3 — the "contact the orchestrator" UX** — resolved *in principle* (D93): dialogue is a terminal activity;
  the console sends **intake** requests + answers **checkpoint** verdicts (the `node→ticket` action is an `intake`
  message, D70/`05`). What's left is the concrete screen/affordance.
- **B2 — stream vs snapshot** — informed by D93: snapshot-reads are the baseline (the bus serves state from disk);
  an optional inotify/SSE "re-read" hint is an ergonomics add, never load-bearing. Final call open.
- **B4 — Stack** **[DEFERRED]**.

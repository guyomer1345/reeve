# 03 — Website (Space 3: local console)

## Role **[DECIDED]**
A LOCAL web app that is (a) a **visualization of the project** (roadmap, knowledge graph, current
activity, checkpoints) and (b) **the human's channel to the orchestrator**. It talks to the
orchestrator only via the local bus + files — never by routing Claude.

## Comms **[DECIDED — see 05]**
- Hosts the **local HTTP loopback bus** (its own backend) for website→orchestrator messages.
- Reads `state.json` (and the knowledge base) to render live state.
- **Verdict delivery (D90/D91):** a human verdict POSTs to the bus, which appends it to a durable **append-only
  inbox** (`.workflow/inbox/`) keyed by the checkpoint **token**; the parked orchestrator matches it at a boundary
  and resumes via `claude --resume`. The block/resume *mechanism* is decided; the rest of the bus contract +
  console screens are the open Phase-2 design (`11` agenda).

## Launch **[DECIDED]**
The orchestrator's start command boots the website as a local background process.

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
(tunneling breaks the loopback trust model); **auth is a reserved future requirement**, not built now.

## To close **[OPEN]**
- The screen list (candidate set: project dashboard, roadmap/todos, **project map — specified, D70**, checkpoint
  console, activity/agent log, handoff/restart prompt) — and whether the map is a **tab or the home/overview** (`07`).
- The "contact the orchestrator" UX (how you send a message / answer / verdict) — the **node→ticket** action is
  reserved (D70/`05`).
- Whether it streams live agent activity or shows state snapshots.
- Stack **[DEFERRED]**.

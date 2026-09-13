# Shared Artifact Schemas — the loop's own working set

The third sibling of [`schemas.md`](schemas.md). Those files own **artifacts**: `schemas.md` what the build
loop *produces and consumes*, [`schemas-bus.md`](schemas-bus.md) what crosses the console↔orchestrator
boundary, [`schemas-runtime.md`](schemas-runtime.md) the records the package's own processes own. This file
owns something different in kind — not an artifact the loop emits, but **where the loop keeps its own working
set**: the live pointer that says where it is, the durable anchor it resumes from, and the on-disk layout of
the per-item scratch space it works in.

That is the belonging, and it is why these three travel together: nothing here is *output*. `state.json` is
the loop's position, `handoff.md` is that position made durable across a `/clear` or a crash, and the
per-item layout is the desk the work happens on. A reader who wants to know **what the loop makes** never
needs this file; a reader who wants to know **how the loop survives being interrupted** needs only this one.

Same conventions as its siblings — on-disk paths are fixed, and each schema notes its **write-mode** and
**tier** (see `shared/memory-model.md`). These are the package's two VOLATILE-tier files plus the item-dir
layout table, so the `handoff.md` bound is owned by the `SessionStart` hook rather than by the doc budget.

*Split out of `schemas.md` when that file reached the 25 000-token Read ceiling, per the split-and-pointer
convention in `shared/memory-model.md`. A reference of the form `schemas.md § <name>` for any section below
resolves here — the name is the anchor, and the four files are one schema.*

## state.json  · the live loop pointer (volatile, gitignored) · *`.workflow/state.json`; published atomically each iteration (write-temp → `fsync` → `rename`) — logically in-place, physically a rename so a bus reader never catches a torn file; RUNTIME, kept on a native filesystem*
- `status` ∈ `{ intake, building, idle }` — the loop's **MODE, never item occupancy**. `intake` is gathering
  requirements, `building` is the autonomous loop driving, `idle` is **backlog empty, awaiting steering** (owned
  by `loop.md`'s `prioritize | backlog empty | idle (await steering)` row). So **`building` with
  `current_item: null` is a legal and expected pair** at a scheduler boundary — at `prioritize` with a full
  backlog the loop is driving and has not yet picked, and `idle` is not available as a synonym for it. Publishing
  `idle` there would tell the console a human must act while a wave is in flight. Nothing may flip this field to
  obtain a commit: see § commit-receipt.
- `phase` — **present only during the `/start` bootstrap motion**, value `bootstrap`; absent once the loop
  drives. It is not a second mode field: `status` already carries the mode, so there is no `phase: normal-ops`
  or any other steady-state value, and the orchestrator does not write one. A second, redundant mode field that
  no consumer reads is how the next invented value gets depended on. With it, `node` carries the bootstrap stage (`start:<step>` / `ingest:<stage>`) and `note` the
  human-readable step marker (`"seeding knowledge nodes 40/95"`) — the console's "Now" panel renders these, so
  the motion is visible from the first minute. Written at every stage boundary, same atomic publish.
- `node` — current loop node; value ∈ the `loop.md` node labels (e.g. `planner:plan-one`, `verify`)
- `current_item` — backlog id or `null` · `wave` — wave id or `null` · `note` — human-readable cursor.
  `current_item` (top-level) is the canonical active-item key. **The verify-before-commit gate does not depend on
  it:** it derives the item(s) under commit from the staged `.workflow/items/<id>/` diff and reads state.json only
  runtime-resolved (via `runtime.json`) and tolerantly (`current_item` **or** a nested `position.item`), and it
  fails **closed** — so neither a state.json shape slip nor a relocated runtime tree can silently disarm it.

## handoff.md  · the durable resume anchor (committed) · *`.workflow/handoff.md`; rewritten whole each handoff, never appended. **Atomicity is real but harness-provided:** the orchestrator rewrites the prose with the `Write`/`Edit` tools, which publish via a temp-file + `rename` (the inode changes on overwrite), so a session killed mid-write leaves the **previous** file whole, never torn. The model cannot *express* the atomic `rename`/`fsync`, but the tool provides it — the one thing it must never do is rewrite this file via a `Bash` `>`/`tee` redirect, which truncates in place and **would** tear. **Durable floor = git:** the file is committed each item, so the one case a bare `rename` may not survive — power-loss/kernel-panic before the pages flush — recovers from `git show HEAD:.workflow/handoff.md`, the same `handoff.md + git log` a cold start already rebuilds from. Committed, so it stays on the repo mount (never relocated); `drain.py` writes its own machine block fully durably (write-temp → `fsync` → `rename` → `fsync(dir)`); the bus reads the file for the `consumed_through` watermark, and a torn read can only make inbox GC lag, never over-collect*
- `bootstrap` ∈ `{ installed, ingesting, discussing, reconcile-parked, complete }` — the bootstrap-motion
  ledger `/start` §0 keys its re-run guard on ("initialised" = bootstrap-complete, not install-complete).
  Written at each phase boundary: step 7 writes `installed`; §2/§3 advance it; the session that consumes the
  reconcile verdict (brownfield) or lands the spec (greenfield) writes `complete`. Absent = an older install —
  treated as bootstrap-incomplete, resume the motion.
- `current_item`, `loop_position`, `base_sha` — the commit it was written against; a cold start
  reads this + `git log <base_sha>..HEAD` (bounded to one session's delta) and rebuilds position. **Prose, written
  by the orchestrator.**
- **Two machine blocks** — fenced, delimited regions a SCRIPT owns, each rewritten independently of the prose and
  of each other. **Three authors, one file:** each writer rewrites only its own region, and none touches another's.
  The orchestrator **never hand-writes or deletes either block**.
  - `<!-- drain:begin -->` … `<!-- drain:end -->` (**`drain.py`**) — `consumed[]`, `consumed_through`,
    `dead_letters[]`. A session that rewrites the file wholesale and drops it loses the *set* — recoverable only in
    the sense that each kind's effect anchor then catches the re-application; the block structure itself is rebuilt.
  - `<!-- parked:begin -->` … `<!-- parked:end -->` (**`bus.py park`/`unpark`/`mirror`**) — `parked[]` as
    `{ ticket_id, kind, summary, opened_at }` plus `projected_at`, capped at 50 with the overflow reported as
    `not_mirrored`. This replaces the prose `parked[]` a session used to write by hand. It is a **PROJECTION of
    `parked/`, re-derived on every mutation**, never patched: prose was accidentally self-correcting (the whole file
    was rewritten each handoff, so a resolved checkpoint simply stopped being written) and a persisted block is
    not. It carries **ids + kind + summary + opened-at ONLY — never a `request` body and never the `token`**,
    because a `setup` checkpoint's body is exactly where a credential appears and this file is **committed**. The
    record does not *move* to the committed half, it *projects* onto it. (Which is also why `parked/` itself stays
    uncommitted: committing it would put that body in git, and the runtime tree exists for `rename`/`0600` reasons
    committing does not satisfy.) **`bus.py mirror` re-projects on demand** — `/dispatch` runs it before writing
    the anchor, which is what makes the block *exist* on an install that parked a checkpoint before the block did.
    An **empty** block is a positive statement ("nothing is parked"); an **absent** one means only that nothing has
    projected yet, which is why `/dispatch` projects rather than assuming.
- `consumed[]` + `consumed_through` — the inbox **consumed-set** (bus-assigned `message_id`s already applied) and
  its low-watermark. Lives here because this is the durable anchor a cold start rebuilds from — exactly the moment
  the set is load-bearing (it makes the post-restart inbox re-read a no-op). Ids only, never message bodies, so it
  stays small and carries no secret; **pruned to ids above `consumed_through`** — which is what bounds it, and is
  the rule a prose brief demonstrably did not carry. **An id at or below the mark counts as consumed even though the
  set no longer lists it** — that is what the mark means, and a walk that reads only the set freezes the watermark
  permanently the first time pruning drops an id beneath it.
- `dead_letters[]` — `{ message_id, reason, at }` for a message that applied to nothing (a verdict whose token is
  unknown or already closed). **Capped (20) and deliberately NOT pruned by the watermark**: this is the one message
  a human most needs told about, and collecting it when the mark passes would erase the notice before it was read.
  It is a defined field precisely because it wasn't — every driven session improvised its own section here, in a
  committed file.

## per-item artifacts  · on disk
**The filenames are FIXED, because they are anchors, not just storage.** Under `.workflow/items/<id>/`:
`plan.md` · `promises.json` · `changelog.md` · `verify-verdict.md` · `debug-report.md` · `plan-delta.md` ·
`promoted.json`. Two mechanisms read them by name and neither can guess: the coverage gates key off
`promises.json`, and the **forecast anchor table** (below) derives "did this event happen?" from the *presence*
of the artifact its node produces. An artifact written under a different name is an event that silently reads as
never having happened.

### scratch  · written by whichever dispatched agent is working the item, read by nobody but its writer
`.workflow/items/<id>/scratch/` — the **heavy working material** the dispatch-return contract (`schemas.md § dispatch-return`) exists to
keep out of a context window: raw command output, intermediate dumps, long drafts, gathered source text. Created
on demand by its writer; nothing scaffolds it.

**RUNTIME and gitignored**, unlike every other name under the item dir — raw material, not a record, and
committing it would put back into the repo exactly the bulk the contract keeps out of a window, then hand it to
every later reader of that item's history. **Not** relocated to the native-filesystem runtime tree the way
`parked/` and `secrets/` are: it holds no credential and needs no atomic rename, so it stays under the item dir
on the repo mount where its writer already is.

**It inherits promote-then-prune rather than getting a TTL of its own.** `retention.py`'s `prune_items` removes
the whole item directory — `scratch/` with it — once `document` has written `promoted.json`, and skips the
directory entirely until then. So scratch lives exactly as long as its item, an un-promoted item never has its
working material collected out from under it, and there is no second deletion rule to keep correct forever.
**Not an anchor** (below): its presence proves nothing about which node ran, which is why the directory name is
fixed and the names *inside* it are the only free ones here.

### the forecast ANCHOR TABLE  · read by `forecast.py reality`, written by nobody
Reality is **derived**, never recorded — there is no second ledger to keep in step, and no writer to forget. Each
`loop.md` node is resolved through the durable effect it leaves behind:

| node | anchor | proves |
|---|---|---|
| `planner` | `items/<id>/plan.md` | the item was planned |
| `execute` | `items/<id>/changelog.md` | the plan was carried out |
| `verify` | `items/<id>/verify-verdict.md` | the artifacts were checked |
| `debug` | `items/<id>/debug-report.md` | something failed and was diagnosed |
| `refine` | `items/<id>/plan-delta.md` | a correction was routed |
| `document` | `items/<id>/promoted.json` | the essence was folded into knowledge |
| `create-demo` | `demos/<id>/` | a sandbox was built |
| `create-forecast` | this record's `frozen_at` | the chain itself was approved |
| `checkpoint:<kind>` | a `parked/` record of that kind — `answered_at` set ⇒ **done**, unset ⇒ **open** | the human was asked |

This table is **exhaustive**: a node not listed here has no anchor and resolves to `unknown` (below). In
particular **`commit` is deliberately unanchored** — it is divergence-exempt, so a probe would buy one column
cell and never a signal; `document`'s `promoted.json` runs *before* it and already says the item reached its
tail; and every anchor here is a pure presence check in a module the console daemon imports, which a `git`
subprocess is not. If it is ever wanted, the exact probe is `git log --grep='^Refs: item #<id>$'` — the trailer
`commit` actually pins, not the subject.

- **`state.json` is deliberately NOT the source.** It is volatile and holds only the *current* node — never a
  history — so "which events have happened" is not a question it can answer at all.
- **Four states, and the fourth is the honest one.** `done` (the anchor is there) · `open` (a checkpoint is parked
  and unanswered) · `pending` (the node has an anchor and it is absent — it has not happened yet) · **`unknown`**
  (the node has *no* anchor in this table, e.g. `decision-engineer`, whose output is a global decision record that
  cannot be tied to one item). `unknown` renders as unknown and never as "did not happen".
- **Divergence is the same table read the other way.** An anchor that fired for a node the forecast never
  named is a **structural divergence** — the machine took a turn nobody saw coming. It does not silently
  continue: the tail is re-forecast and re-shown. The item-complete tail (`commit`, `document`, `close-issue`,
  `prioritize`) is exempt, because it runs for every item and its absence from a chain is the horizon talking,
  not a surprise.
- **The check fires at the SCHEDULER BOUNDARY only, never mid-item** — which is what keeps non-preemption and
  never-stall intact, and is why it is plain control-flow in `loop.md` rather than a routing edge.

`plan` / `changelog` / `verify-verdict` / `debug-report` live under `.workflow/items/<id>/` — `planner`
`mkdir`s the dir on demand when it writes `plan.md`; the dir is **item-scoped**, committed while the item
is open (crash-survival) and **pruned once closed** by the `audit` pass — but **only** after `document` folds
its essence and writes a `promoted.json` (`{ "promoted": true }`) marker into the dir; without it the prune
skips the dir, so retention never deletes un-promoted memory. `decision-record`s stay global +
append-only under `<project_root>/docs/decisions/`, with a VOLATILE `index.md` + superseded bodies GC'd to git;
the previously-reserved `checkpoints/` is **retired → `outbox/`** (the pending-outward-action queue). Rule: per-item
ephemeral artifacts are item-scoped; cross-item memory is type-scoped.

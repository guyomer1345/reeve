---
description: Write a complete, current handoff.md right now so a /clear is safe — the interactive context-reset step. Run it when the statusline shows the context-budget warning, then /clear, then a bare `continue` — the SessionStart hook re-injects the handoff, so that one word is all the next session needs.
---

# /dispatch — checkpoint context to disk, then it is safe to /clear

The statusline carries a **two-sided band** (`context_band.py`), not a one-way warning: it says
**hold** while there is runway, **hand off at the next boundary** in the middle, and **hand off
now** once what remains is needed to finish the item in hand and publish a complete anchor. The
unit is *work* — nodes of runway, `(window − used) ÷ per-node cost` — rather than a fraction,
because a 200k and a 1M window at the same percentage full leave very different amounts of room.
**A `hold` is a real verdict:** running `/dispatch` early is not free, it pays a cold rebuild for
a window that still had work in it. Ask any time with
`python3 .claude/scripts/context_band.py --workflow-dir .workflow`.
**The band is now acted on, not only shown.** `--gate` adds the two verdicts a driver needs — whether an
anchor is owed (`needs_handoff`) and whether a reset is safe (`clear_safe`) — the loop reads it at every
scheduler boundary (`loop.md § Scheduler boundary`), and a `Stop` hook blocks a turn from ending while an
anchor is owed. Running `/dispatch` at the boundary is how you meet that gate before it fires.
`/dispatch` is the manual reset step: it writes a **complete, current** `.workflow/handoff.md` so that a `/clear` loses
no build state. The SessionStart hook re-injects that anchor on `/clear`, so the next prompt
resumes from it — **but a cleared session does not start on its own.** It sits idle until you
prompt it, and a bare `continue` is enough. The hook removes the need to *re-explain* where the
build was; it does not remove the need to *ask*. Run `/dispatch`, confirm it reports the handoff is written, then run `/clear`.

You (the orchestrator) do this now, in this turn:

1. **Rewrite `.workflow/handoff.md` whole**, as the durable resume anchor for a session that
   knows *nothing* — write it for a stranger. Use the `handoff.md` schema (`shared/schemas.md § handoff.md`).
   Capture the live state as it is **right now**:
   - the `bootstrap:` ledger line if the bootstrap motion is still in progress (`installed` /
     `ingesting` / `discussing` / `reconcile-parked` / `complete`) — omit only once the loop drives;
   - `current_item` and `loop_position` (which `loop.md` node you are at). **Not `parked[]`** — the
     `<!-- parked:begin -->` block is machine-owned and already mirrors every open ticket;
     hand-writing a second copy is how the two disagree. **First run
     `python3 .claude/scripts/bus.py mirror --workflow-dir .workflow`**, which re-projects that
     block from `parked/`. It is idempotent, and it is what makes the block *exist* on a project
     that parked a checkpoint before the block did — otherwise you would publish an anchor naming
     no open checkpoint while one is genuinely open. **If it fails**, the runtime half is
     unreachable (that is what `parked/` lives on): say so plainly in the prose, name the open
     work you can still see, and route the human to `/rebind` — do not paper over it by
     hand-writing a `parked[]` you cannot verify;
   - `base_sha` = the current `HEAD` (`git rev-parse HEAD`) — the commit the resume reads
     `git log <base_sha>..HEAD` against;
   - in prose: what is **committed** vs what is **uncommitted in the working tree** right now
     (`/clear` wipes the conversation, not the filesystem — uncommitted edits and this handoff
     survive), what the next action is, and any in-flight decision or open question. A resumed
     session must be able to continue without guessing.
2. **Write it with the `Write`/`Edit` tools — never a `Bash` `>`/`tee` redirect.** The tools
   publish atomically (temp + rename); a shell redirect truncates in place and can tear the file
   on a kill.
3. **Do not touch either machine block** — the fenced `<!-- drain:begin -->` … `<!-- drain:end -->`
   region is `drain.py`'s (the inbox consumed-set + watermark) and `<!-- parked:begin -->` …
   `<!-- parked:end -->` is `bus.py park`'s (the open-checkpoint mirror). Leave both exactly as they
   are; if the file has neither yet, do not fabricate one. Rewrite only the prose around them.
   "Rewrite the file whole" means the **prose** whole — preserve both regions byte for byte.
4. **Do not commit and do not run `verify`/`document`** — `/dispatch` is a mid-session context
   snapshot, not an item-close. If you happen to be at a clean item boundary you may follow the
   normal tail, but `/dispatch` itself only writes the anchor.
5. **Tell the human plainly:** the handoff is written and it is now safe to `/clear` — and that the
   cleared session needs a bare `continue`, because it **does not start on its own**. `SessionStart`
   re-injects the anchor as context, and context is not a turn. (This step said "resumes
   automatically" for as long as the claim was believed; it was the sixth copy of it.)

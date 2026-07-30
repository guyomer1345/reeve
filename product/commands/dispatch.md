---
description: Write a complete, current handoff.md right now so a /clear is safe — the interactive context-reset step. Run it when the statusline shows the context-budget warning, then /clear (the session auto-rehydrates from the handoff).
---

# /dispatch — checkpoint context to disk, then it is safe to /clear

The statusline warns when this session's context is filling up. `/dispatch` is the manual
reset step: it writes a **complete, current** `.workflow/handoff.md` so that a `/clear` loses
no build state — a cleared session auto-rehydrates from that anchor (the SessionStart hook
re-injects it). Run `/dispatch`, confirm it reports the handoff is written, then run `/clear`.

You (the orchestrator) do this now, in this turn:

1. **Rewrite `.workflow/handoff.md` whole**, as the durable resume anchor for a session that
   knows *nothing* — write it for a stranger. Use the `handoff.md` schema (`shared/schemas.md`).
   Capture the live state as it is **right now**:
   - the `bootstrap:` ledger line if the bootstrap motion is still in progress (`installed` /
     `ingesting` / `discussing` / `reconcile-parked` / `complete`) — omit only once the loop drives;
   - `current_item` and `loop_position` (which `loop.md` node you are at). **Not `parked[]`** — the
     `<!-- parked:begin -->` block is machine-owned (`bus.py park`) and already mirrors every open
     ticket; hand-writing a second copy is how the two disagree;
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
5. **Tell the human plainly:** the handoff is written and it is now safe to `/clear`; on the next
   session the loop resumes automatically from the anchor.

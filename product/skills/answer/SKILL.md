---
name: answer
description: Answer a human's question about this project from its own knowledge base, spec and decision record, and append the reply to the conversation thread the console renders. Runs when a `question` message is drained — the read-side counterpart of intake, which asks for work rather than for prose.
---

# Answer — the project explains itself

Core principle: **a question is a read.** It changes no build state, promotes nothing, plans nothing and
touches no code. Answering is the whole job, and stopping is part of it.

The split from `intake` is made **by the human at the console**, not classified here: a question wants prose
back, a request wants a ticket. If a drained `question` is plainly a work request that came through the wrong
box, say so in the answer and tell the human to send it as a request — do **not** promote it yourself. The
inverse is what a misfiled message costs cheaply; silently starting work off a question is what it costs
expensively.

## When
At a boundary drain, when `drain.py list` shows a pending `kind: question`. Two callers, one behaviour:
- a **live loop** drains it at its next boundary, alongside every other kind (the common, cheap case — no
  spawn, no cold start);
- with **no loop live**, the daemon's relaunch-runner spawns a session whose only instruction is to run this
  skill and stop.

## Inputs
- the pending `question` message(s) from `drain.py list` — `{ question }`
- `.workflow/thread/thread.json` — the conversation so far and its `session_id` (`schemas.md § conversation-thread`)
- the project's own record: `docs/knowledge/` (nodes + `graph.json`), `docs/spec.md`, `docs/decisions/`,
  `.workflow/backlog.md`, `.workflow/state.json`, and git history.

## Workflow
1. **Read the thread first.** A follow-up ("why that one?") is meaningless without it, and the thread is also
   where the idempotency anchor lives.
2. **Skip anything already answered.** A turn already carrying this `message_id` means a previous run appended
   the reply and died before `drain.py record` — the answer stands, so record it and move on. Never answer twice.
   **The anchor covers exactly one window — *append* (4) to *record* (5) — and nothing else.** After a rotation
   the thread has **no turns**, so the anchor is unreachable and idempotency rests on the **drain watermark
   alone**. That is correct, because rotation runs only *after* the record (6): a rotated message is already
   consumed and can never come back pending. It is also why no step that clears `turns` may ever be moved ahead
   of step 5 — doing so leaves the message unrecorded *and* unanchored at the same time, and the retry answers
   it twice.
3. **Answer from the project's own record, not from general knowledge.** The question is about *this* project.
   Cite where the answer came from — a node, a decision id, a spec section, a commit. If the record does not
   say, **say that it does not say**: an invented answer about your own project is worse than none, because
   it is indistinguishable from a real one. Where the honest answer is "nobody decided this yet", that is a
   finding — offer to file it, do not file it unasked.
4. **Append the turns** to `.workflow/thread/thread.json` — the human's question and your reply, each stamped
   with the source `message_id` — and record the `session_id` this ran under so the next question resumes it.
5. **`drain.py record`** the message ids, exactly as any other kind. **Record before you rotate, always.**
   Rotation clears `turns`, and the turns carry step 2's anchor — so rotating first opens a crash window in which
   the message is unrecorded *and* the anchor is destroyed, and the retry answers it a second time, the one
   outcome the anchor exists to prevent. Recording first cannot lose an answer: a crash after this point costs at
   most a **deferred rotation**, which the next question performs because the thread is still over budget.
6. **Rotate if the thread is over budget.** Estimate the thread's context with `config.doc_budget.chars_per_token`;
   if it exceeds `config.thread.rotate_at_tokens`, write `.workflow/thread/handoff.md`, clear `session_id` and
   `turns`, and increment `rotations`. The next question starts fresh from that handoff. This is the
   orchestrator's own disposable-conversation law applied to the thread — resume re-sends the whole history, so
   length is a per-question *cost*, not just disk.
   **Write the handoff to the carry-list in `shared/schemas.md § conversation-thread`, which is a floor, not an
   example: drop, point and quote — never restate** (`shared/memory-model.md § the distillation law`). Keep the
   human's turns verbatim, the open threads, the pointers to outcomes that landed with a real owner, and any
   contradiction stated as the two pointers that contradict. Carry **none of your own prose answers**: you
   answered from this project's record (step 3), so they are re-derivable from it — and an answer that is *not*
   re-derivable is exactly an invented one. This is the only distillation here whose source is **destroyed**
   rather than archived, so what you restate becomes the next session's established fact with no evidence left
   to check it against.

## Rules
- **Never promote, plan, execute, or edit code.** If answering surfaces real work, name it and let the human
  send a request — routing it yourself would let a question start an unattended build.
- **Answer, then stop.** A runner-spawned answerer must not continue into the loop; the prompt that launched it
  says so, and this is the second place it is said.
- **Durable outcomes land with their existing owner, never in the thread.** If an exchange settles something,
  it belongs in the spec, the backlog or a decision node — the thread is RUNTIME and keeps the *conversation*,
  so a decision left only there is a decision that is gone.
- **The thread is single-writer (this skill).** The bus only reads it, exactly as with `outbox/`.
- **No credential ever enters the thread.** It is free prose on a durable file; a value from the secret store
  is referenced by name, never quoted.

## Output
One `project` turn per answered question on the conversation thread, rendered by the console's Conversation
panel, and the message recorded as consumed.

## Route
→ nothing. Answering is terminal: the loop resumes on its own schedule, and a question never advances it.

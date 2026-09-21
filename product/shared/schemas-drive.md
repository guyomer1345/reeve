# Shared Artifact Schemas — the unattended drive's governors

A sibling of [`schemas-runtime.md`](schemas-runtime.md), split out of it when that file crossed its context
budget. Same belonging rule as the rest of the family: this one owns the records that decide **whether a
session may keep going, be reset, or be typed at** — the context band, the two gates, the heartbeat and the
supervisor's own ledger. Nothing here is authored by a skill as work and **nothing here is hand-edited**; the
knobs an operator does turn live in [`schemas-config.md`](schemas-config.md).

They are one mechanism and that is why they are one file: the statusline publishes a reading → the band turns
it into a verdict → the `Stop` gates demand an anchor and refuse a stop-for-nothing → the heartbeat watches
the session a `Stop` hook cannot see → the supervisor resets or nudges. **Every one of them was corrected by
DRIVING rather than by reading**, and the corrections are recorded here because each is a premise that stopped
holding rather than a coding error.

*A reference of the form `schemas.md § <name>` or `schemas-runtime.md § <name>` for any section below resolves
here — the name is the anchor, and the parts are one schema.*

## context.json  · published by `statusline.py` every turn, read by `context_band.py` · *`.workflow/context.json`; RUNTIME, gitignored, atomic write (temp + `os.replace`); kept on a native filesystem*
- `{ used, window, mono }` — absolute tokens and the monotonic clock at publication. **Absolute, not a
  percentage**, because the consumer's unit is *work*: a 200k and a 1M window at the same fraction full leave
  5 and 25 nodes of runway, which are not the same situation.
**This file is the one crossing of a real wall.** The statusline is the **only** surface Claude Code exposes a
running token count to — hooks and the model receive none. So the statusline can **see** and not act, while the
loop can **act** and not see. Before this, nothing crossed: the banner went to a human's eyes and a human typed
`/dispatch`, which is a channel with no machine end at all.
**Read through `context_band.py`, never directly.** A reading older than its staleness window resolves to
*absent* — it describes a session that has probably already ended, and a verdict about a dead session's window is
worse than no verdict.
**Published best-effort and never fatally:** it is written from inside the status line, and a status line that
raises blanks itself. A lost reading degrades the band to `unknown`, which is the safe direction — `unknown` is
never `hold`, because a wrong `hold` tells a session to keep filling a window it should be leaving.
**The acting end of that crossing is `handoff-gate.json` below** — for its first life this reading was still
read by nobody but a human, which made the band a better banner rather than a control.

## handoff-gate.json  · latched by `context_band.py` (`demand`/`gate`), counted by `hooks/handoff_gate.py` · *`.workflow/handoff-gate.json`; RUNTIME, gitignored, atomic write (temp + `os.replace`); lives beside `context.json` on the repo mount, deliberately NOT on the runtime half*
- `{ armed_handoff_mtime, demands }` — the mtime `handoff.md` had at the instant the band **entered**
  `handoff-now`, and how many times the `Stop` hook has demanded an anchor since.
**It exists to give "freshly written" a moment to be fresh relative to.** Both consumers of the gate need that
word: the `Stop` hook must stop demanding once the anchor exists, and the supervisor must not reset a session
whose anchor predates the demand. A TTL or a "recently" would have been a guess; the latched mtime is a fact.
**Armed and disarmed by asking.** The first `demand()`/`gate()` call that sees `handoff-now` writes it; the first
that sees anything else removes it — in practice the turn after a `/clear`, which is what makes the demand
once-per-fill-cycle rather than a nag. `--no-arm` asks without latching, for inspection only.
**`demands` is a loop stop, not a metric.** Claude Code's `Stop` payload carries no `stop_hook_active`, so the
count lives here; past `MAX_DEMANDS` the hook gives up and lets the turn end. A hook that blocks forever wedges
the session it was protecting.
**On the repo mount on purpose.** A project whose runtime root has gone missing still needs its anchor written —
that is precisely when it needs it most — so nothing in this path may require resolving `runtime.json`.

## turn-gate.json  · written by `hooks/turn_gate.py` (`Stop`), judged by `scripts/turn_check.py` · *`.workflow/turn-gate.json`; RUNTIME, gitignored, atomic write (temp + `os.replace`); repo mount, beside the rest of the gate state*
- `{ fingerprint, satisfied, demands, rung }` — the loop fingerprint at the **previous** stop, the report digest
  this session last satisfied, and the demand counter with the rung it is counting.
**It exists because two of the three questions a turn-end gate asks are only answerable ACROSS turns.** *Did this
turn move anything?* needs the fingerprint the last turn ended on — `drive.py`'s, reused rather than reinvented,
so the driver that decides whether to spawn and the gate that decides whether a turn may stop share one
definition of "the loop moved". *Has the human already been given this report?* needs the digest that was last
satisfied, and it is what stops an unchanged loop being asked for the same block twice — the nuisance objection
that would otherwise get the gate switched off inside a day.
**`satisfied` is a digest of the report's CONTENT, never of when it was written** (`status_report.py § digest`):
goal, progress, parked tickets, in-flight items and their nodes, discharged and outstanding acceptance. A digest
that moved on its own would make every report stale on arrival.
**Written on every stop, including the ones that BLOCK.** Otherwise the first block would poison the fingerprint
comparison for the second, and a session already being told it moved nothing would be told it again for the
wrong reason.
**`demands` is a loop stop, not a metric**, exactly as in `handoff-gate.json`, and it is keyed by `rung`: moving
from *continue the loop* to *leave a report* is progress and resets the count, because they are different
demands and a session that satisfied the first should not inherit the second's patience.

## monitor.json  · written by `scripts/monitor.py` (driven by `supervise.sh`), read by `bus.py`'s steer floor · *`.workflow/monitor.json`; RUNTIME, gitignored, atomic write; repo mount*
- `{ at, state, action, why, fingerprint, pulse, quiet_for, nudges, nudges_total, escalations_total, quiet_periods, watching_since, owed_served, owed_pulse, owed_misses }`
  — `state` ∈ `{ moving, quiet, stopped, stalled, waiting, unknown }`, `action` ∈ `{ none, nudge, escalate }`.
  The `owed_*` trio is the give-up breadcrumb's ledger: which one was served, the pulse when it was, and how
  many served ones moved nothing (three ⇒ escalate, so the shortcut cannot become a keystroke loop).
**It exists for the one failure a `Stop` hook cannot see: the session that never ends a turn.** The turn gate
catches every stop-for-nothing at the instant it happens; a session that idles, or sits in a dialog, never
reaches it. That residue is a poller's job and nothing else's.
**The pulse is the newest write the LOOP made**, which needs no new hook and no cooperation from the session: a
driving loop writes `state.json` every iteration, item artifacts as nodes complete, and a worker-budget
breadcrumb on every tool call. So *"the loop has written nothing for ten minutes"* is an observation that the
machine stopped touching its own state, not a guess about a model's intentions.
**It is an ALLOW-LIST, not all of `.workflow/`, and a test found the reason rather than anyone reasoning to it:**
the supervisor's own gate call writes there — `context_band.py --gate` arms or disarms `handoff-gate.json` on
every poll — so a monitor watching the whole directory would watch a dead session and see its own heartbeat
reflected back for ever. The observers' files (`context.json`, `handoff-gate.json`, `turn-gate.json`,
`monitor.json`, `supervise.log`) are excluded by not being listed, which is the safe direction: a new observer is
silently fine, a new loop artifact is silently missed, and only the second failure is quiet rather than wrong.
**WAITING IS NOT STALLING.** A parked checkpoint, an open dialog, the pause latch — and a session that is not at
an idle prompt — all mean the drive is not in a state a keystroke helps, so the state is `waiting` and the action
is always `none`. The last of those lives HERE and not in `supervise.sh`: put in the transport as a veto it let
the judge say `nudge`, the shell decline, and the one-nudge budget be spent anyway on a nudge that never left the
process (observed 2026-09-20, with a durable `steer` park as the next rung). Its one exception is the stall
window — a working loop writes constantly, so quiet for the full window AND not at the prompt means wedged, and
the escalation still fires where the nudge is withheld.
**`stopped` is the cheap rung and it does not wait ten minutes.** `turn-gate.json`'s `owed` breadcrumb says the
turn gate gave up on a stop that owed a `continue` — known at the instant of the stop, where waiting for
`QUIET_SECONDS` rediscovers it at a cost of ten minutes (measured: work → stop → 10 min → nudge → work → stop,
and the nudge worked every time). It outranks a parked checkpoint, because the turn ladder has already weighed
that — a checkpoint parks the ITEM — and it never outranks a dialog or the operator's pause.
**One nudge, then a checkpoint.** `nudge` sends a bare `continue` (what a session that quietly ended a turn
needs; a working session just queues it). Only a still-quiet drive escalates, and it escalates by parking a
`steer` — the same argument `drive.py` makes for its own terminal stops: a checkpoint is what the away channel
already alerts on, so raising one buys the notification through the machinery that owns it.
**A WINDOW NOBODY WATCHED IS NOT EVIDENCE — `watching_since`.** The pulse is an mtime, so quiet time accrues
while this process is not running and a restart reads its own downtime as a case against the loop (observed: a
supervisor restarted and a `steer` parked *seventeen seconds later* for a 251-minute gap it had not watched; the
park is durable, so the drive stopped until a human deleted a ticket asking nothing). A tick more than
`GAP_SECONDS` after the previous one re-baselines and drops the nudge count. The **nudge** still runs on mtime
quiet — cheap, and what a session idle since a deploy needs; only the **escalation** waits for an observed
window.
**It is the second evidence the STEER FLOOR accepts, and only while CURRENT.** `bus.py`'s floor refuses a
`steer` park the goal's own verdict does not support; *"the drive has stopped moving"* is a claim `converge.py`
cannot make, so this record stands in — but the stall must name the fingerprint the loop is still sitting on. A
session cannot talk its way through the floor; it can only be observed through it.
**`nudges_total` / `escalations_total` / `quiet_periods` are the counters that turn *"it pauses a lot"* into a
number.** Advisory, monotone within a run, and never read by any gate.

## awaiting-input.json  · written by `hooks/awaiting_input.py` (`Notification`), removed by `hooks/handoff_gate.py` (`Stop`), read through `context_band.py` · *`.workflow/awaiting-input.json`; RUNTIME, gitignored, atomic write; repo mount, beside the rest of the gate*
- `{ kind, session_id }` — which dialog is open (`permission_prompt` · `elicitation_dialog` ·
  `elicitation_url_dialog` · `agent_needs_input`).
**"Waiting on a human" turned out to be two things, and the second was found by probing.** The reset gate asked
whether a checkpoint was parked; a live probe drove a real session into a **permission prompt**, where it sat —
invisible to `parked/`. A supervisor on the old gate would have cleared a screen somebody was looking at.
**`idle_prompt` is deliberately NOT a dialog kind.** It means the session is idle waiting for a prompt, which is
exactly the state a reset exists to act on. Listing it would disable the supervisor precisely when it should
fire, and nothing would say why — so the exclusion carries its own test.
**Cleared by `Stop`, never by a TTL.** A dialog blocks the turn, so a turn that ended is proof the dialog is
gone — approved, denied or cancelled alike. A guessed expiry would clear the flag while a person was still
looking at the prompt.
**Present, unreadable, or torn ⇒ still open.** A file nobody can read is not evidence that nobody is waiting.
**A hook and not a screen-scrape.** The alternative was matching dialog chrome out of `tmux capture-pane` — a
gate whose correctness depended on the wording of a UI this package does not control.
**Its twin is `session-idle.json`, below, written by the same hook from the same event stream and read with the
opposite polarity.** Never both at once: a session cannot be idle at the prompt and sitting in a dialog.

## session-idle.json  · written by `hooks/awaiting_input.py` (`Notification`, `idle_prompt`) and by `hooks/session_start.py` (`startup`/`resume`/`clear`), removed by `hooks/prompt_submit.py` (`UserPromptSubmit`), read through `context_band.py` · *`.workflow/session-idle.json`; RUNTIME, gitignored, atomic write; repo mount, beside the rest of the gate*
- `{ kind, session_id }` — the body is for humans. **PRESENCE is the fact**, which is why an unreadable file
  still counts as idle: one hook writes it, another removes it, and refusing to read a torn scratch file as idle
  would disable the supervisor over bookkeeping. (The dialog flag fails the other way for the same reason —
  each fails towards *do not type into this pane*.)
**The FOURTH `clear_safe` condition, and the only one stated in the positive** — the other three are reasons to
hold, this one is a permission. Absent ⇒ not idle ⇒ no reset.
**It exists because the first three were all true at the instant they were most wrong.** `handoff.md` is written
*during* a turn, so the moment the anchor lands the band says `handoff-now`, the anchor is fresh, nothing is
parked and no dialog is open — while the model is still working. Every reset the supervisor had ever sent went
into a running turn. The design absorbed that with the transport probe's claim that mid-turn keys queue in the
pty and are read intact at the end of the turn. **They do not.** They land in the prompt box as literal text,
never submitted, and the next poll adds more — OBSERVED 2026-09-19 as a stack of `/clear continue /clear
continue` that only Esc could flush, and Esc then ran the `/clear` with no `continue` behind it.
**A bracket, not a timer.** The harness says when idleness begins (`idle_prompt`, after
`messageIdleNotifThresholdMs`, default 60s) and a submitted prompt is the only thing that ends it. A TTL would
guess at model latency and fail unrecoverably; `PreToolUse` proves busy-ness too late, and the gap is exactly
where the second send lands. **MEASURED:** the hook is dispatched *before* the branch on
`preferredNotifChannel`, so OS notifications being off still produces the flag.
**Necessary and NOT sufficient — see `in-flight/` below.** It fires while a backgrounded worker runs, because
the parent genuinely is at the prompt.
**`SessionStart` WRITES it, and used to remove it — which was backwards.** A started, resumed or cleared
session is idle by definition, and the harness cannot say so: `idle_prompt` arms off the last message
timestamp, so a cleared session, having none, never arms it (measured: 11 minutes idle, no flag). A reset whose
`/clear` lands and whose `continue` does not then leaves a session only a human can restart. `compact` is
excluded and that exclusion is the load-bearing half — auto-compact fires mid-turn and the turn resumes after
it.

## in-flight/<tool_use_id>.json  · written by `hooks/dispatch_guard.py` (`PreToolUse` on `Agent|Task`), removed by `hooks/dispatch_return.py` (`PostToolUse` on the same) and by `hooks/session_start.py`, read through `context_band.py` · *`.workflow/in-flight/`; RUNTIME, gitignored, atomic write*
- `{ agent, description, session_id }` — **presence is the fact**; the body is for humans, so a torn file
  still counts as a running worker. Reading one as "nothing is running" is how the worker gets thrown away.
**Read by both gates, because the harness auto-backgrounds agents** and neither gate could previously tell a
backgrounded worker from a stopped session: `turn_check.may_end` called every background dispatch a stop for
nothing, and `clear_safe` would have cleared a session **mid-dispatch** (`session-idle` fires while a worker
runs — the parent genuinely is at the prompt). `turn_gate.py` resets `demands` on the may-end path, so getting
this right also re-arms that gate — which is why the counter symptom needed no separate fix. Measured on a real drive before any of this existed: 35 consecutive demands against a budget of 2, every one a false alarm on an ordinary dispatch.
**Two ordering rules, both load-bearing.** `dispatch_guard` marks BEFORE its own gates can block — a blocked
dispatch never reaches `PostToolUse`, so its entry orphans, and an orphan costs a held reset and ages out
where the opposite costs the worker. `dispatch_return` retires BEFORE its own early returns — it skips a
general dispatch, while `dispatch_guard` marks every one.
**The age-out is a BACKSTOP, not a timeout.** The ordinary end is `PostToolUse`; a session that died
mid-dispatch is cleared wholesale at `SessionStart`. What remains is a worker vanishing inside a session that
keeps running. One hour ≈ 4× the longest dispatch observed on a real drive (16m02s), so it cannot fire on a
working worker.

## supervisor.json  · written by `scripts/supervise.sh` through `scripts/supervisor.py` (publish at start, retire on every exit), read by `statusline.py`, `hooks/turn_gate.py`, `bus.py`'s steer floor and `loop.sh --supervise`'s preflight · *`.workflow/supervisor.json`; RUNTIME, gitignored, atomic write; repo mount*
- `{ pid, pane, since }` — and **presence is NOT the fact here**, unlike every other record in this file. The
  answer is `alive()`'s: `running` | `gone` | `none` | `unknown`, and it is a LIVENESS CHECK, not a read. The pid
  must still exist *and* (where `/proc` is available) still be a `supervise.sh`, because pid reuse means the
  shell that died at 02:00 can be a compiler at 02:05.
**`gone` and `none` are different answers and the difference is the whole record.** Nothing was ever armed here,
versus something was armed and is not there any more. The second is the eleven-hour failure: on 2026-09-19 two
drives ran on with their supervisors stopped for a deploy, hit their own stops, and sat idle overnight with
**nothing anywhere** saying so — not the console, not the status line, not the loop, not the turn gate. The
heartbeat that exists to catch a dead loop (`monitor.py`) runs INSIDE `supervise.sh`, so it dies with the thing
it would have reported.
**Why a record with a liveness check where the orchestrator uses an flock.** The orchestrator lock is held by
the process that becomes `claude`, so the kernel releases it on death and a stale lock is impossible. A
supervisor is a bash poller: it cannot exec into what it supervises, and an flock held by a shell loop says
nothing about WHICH pane it drives.
**Three consumers, one answer.** The status line shows `⛨ supervised` or the alarm (and only when
`REEVE_SUPERVISE` is in the environment, which is proof the session was *launched* supervised). `turn_gate.py`
parks `steer-supervisor-gone` — once, guarded by the ticket's existence, because `write_park` restamps the
alert-dedup key. `loop.sh --supervise`'s preflight REFUSES to arm a second supervisor over a live one.
**`--once` publishes nothing**, deliberately: a cron-style driver that announced itself for a second and
vanished would leave every reader flapping between `running` and `gone`.

## supervise-latch.json  · written by `scripts/supervise.sh`, `gave_up` also read by `scripts/monitor.py` · *`.workflow/supervise-latch.json`; RUNTIME, gitignored, atomic write*
- `{ attempts, used, gave_up }` — consecutive resets sent, the context reading at the first of them, and
  whether the cap has been hit. **`gave_up` is a FACT about that process, not a judgement**: what to do about
  it — park a `steer` so the away channel alerts someone — is `monitor.py`'s call, because that is where every
  other escalation here is decided and where the steer floor reads its evidence. It used to reach
  `supervise.log` and nothing else, so an operator who did not read that file learned of it by noticing the
  drive had stopped.
**The attempt cap every other actuator here already had.** `send-keys` exiting 0 means tmux accepted the
keystroke, never that the TUI submitted it, so a send that does not land changes nothing the gate can see and
the gate — still true — fires again every poll, forever. Three (`REEVE_SUPERVISE_MAX_RESETS`) that leave the
reading where it was and the supervisor stops and says what a human can do. Cf. `RUNNER_MAX_ATTEMPTS`,
`MAX_DEMANDS`, `STALL_LIMIT`.
**Graded on a DERIVED effect** — a `/clear` that lands collapses the context reading — which is the forecast
anchor table's law applied where it was missing. **Retired on every tick**, not only when the gate is true, or
three *successful* resets would trip a cap meant for three failed ones. A file rather than a variable because
`--once` is a whole process; unreadable ⇒ zero.

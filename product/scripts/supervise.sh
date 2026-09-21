#!/usr/bin/env bash
# The self-clearing supervisor — a poller that resets a full interactive session, so a drive
# does not stop at the first full context window.
#
# WHAT IT IS. One bash process per orchestrator, running BESIDE an ordinary interactive Claude
# Code session in a tmux pane. Every `interval` seconds it asks one question — may this session
# be reset right now? — and when the answer is yes it sends two keystroke injections:
# `/clear`, then a bare `continue`.
#
# WHY IT IS NOT `claude -p`. The first attempt at this shipped a shell loop around headless
# `claude -p`, which self-clears and has no UI, no live tool calls and no status line. Autonomy
# was never meant to be paid for with the thing being made autonomous. This drives the real
# session instead, and the real session is what the operator is already looking at — from a
# terminal, or from Claude Code in the Claude app, which is a full interactive session too.
#
# WHY IT DOES NOT WRITE THE HANDOFF. Writing a complete resume anchor needs the context to know
# what a complete one says; a poller does not have it. The orchestrator writes its own anchor
# when the band tells it to, and a `Stop` hook makes that non-optional. This process's whole job
# is the RESET, and it waits for an anchor it did not write.
#
# WHY `/clear` AND THEN `continue`, as two sends. A cleared session does NOT start on its own.
# `SessionStart` re-injects `handoff.md` as additional CONTEXT, and context is not a turn — the
# session sits idle until it is prompted. The package claimed otherwise in five shipped places
# and it was false; a supervisor built on that claim would send `/clear` and wait forever.
#
# THE GATE IS ONE CALL AND IT IS NOT THIS FILE'S JUDGEMENT. `context_band.py --gate` answers
# `clear_safe`, which is FOUR things at once: the band says hand off now, an anchor has been
# written since it started saying so, nothing is waiting on a human — neither a parked checkpoint
# nor an OPEN DIALOG — and the session is IDLE. Neither of the last two is theoretical; both were
# found by driving rather than by reading. A live probe drove a real session into a permission
# prompt, where it sat, invisible to every other signal. And a real drive, 2026-09-19, found the
# fourth: every reset this file had ever sent went into a RUNNING TURN.
#
# TRANSPORT: `tmux send-keys`, probed rather than assumed — and the probe's conclusion was too
# strong. A real interactive session was driven end to end this way: a prompt ran, `/clear`
# cleared the transcript, a bare `continue` started a turn in the cleared session. What that did
# NOT establish is the mid-turn case, which this file then assumed: keys sent while the TUI is
# mid-turn do **not** queue into the turn and get read at the end of it. They land in the prompt
# box as literal text and are never submitted. The observed result was a stack of
# `/clear continue /clear continue` that only Esc could flush — and Esc then ran the `/clear`
# with no `continue` behind it, which is the one outcome this whole file exists to prevent.
# Hence the idle precondition in the gate, and hence the attempt cap below.
#
# THE ATTEMPT CAP, which every other actuator in this package already had and this one did not.
# `send-keys` exiting 0 means tmux accepted the keystroke, never that the TUI submitted it, so a
# send that does not land changes nothing the gate can see — and the gate, still true, fires
# again on the next poll, forever. The relaunch-runner has `RUNNER_MAX_ATTEMPTS`, `turn_gate.py`
# has `MAX_DEMANDS`, `converge.py` has `STALL_LIMIT`, `drive.py` has its no-progress streak.
# This file now has `MAX_RESETS`, and it is checked against a DERIVED effect rather than its own
# report of success: a `/clear` that lands collapses the context reading, and one that does not
# leaves it where it was. A supervisor that gives up costs a session that stops where it would
# have stopped anyway; one that retries into a corrupted prompt box costs the conversation.
#
# FAIL DIRECTION, THROUGHOUT: do nothing. Every unreadable file, missing tool, absent pane and
# unexpected exit code leaves the session alone. A supervisor that fails by not resetting costs
# a session that stops where it would have stopped anyway; one that fails by resetting wrongly
# destroys a conversation somebody was having.
set -uo pipefail

INTERVAL="${REEVE_SUPERVISE_INTERVAL:-60}"
WORKFLOW=".workflow"
PANE=""
PROJECT="."
ONESHOT=0
SETTLE="${REEVE_SUPERVISE_SETTLE:-8}"   # seconds between `/clear` and `continue`
# Consecutive sends that left the context reading where it was before giving up. Three, not one:
# a single send can fail to land for a reason that clears on its own (the TUI repainting, a
# window resize), and a supervisor that surrenders to the first of those is a supervisor nobody
# keeps switched on. Three that all fail to move a number that a landed `/clear` collapses is not
# a transient.
MAX_RESETS="${REEVE_SUPERVISE_MAX_RESETS:-3}"
# How far the reading must fall to count as "the reset landed". One node's worth — a real clear
# drops an order of magnitude more, and anything smaller is ordinary turn-to-turn noise.
DROP_TOKENS=12000

usage() {
  cat <<'USAGE'
supervise.sh --pane <tmux-target> [--project <dir>] [--interval <seconds>] [--once]

  --pane      the tmux target of the session to supervise (e.g. `reeve:0.0`), REQUIRED —
              there is no discovery and there deliberately is not: guessing which pane holds
              the orchestrator is how a supervisor clears the wrong window.
  --project   the project root holding .workflow/ (default: the current directory)
  --interval  seconds between gate checks (default 60, or $REEVE_SUPERVISE_INTERVAL)
  --once      evaluate the gate exactly once and exit; the exit code is the verdict
              (0 = reset performed, 1 = held). For testing and for cron-style drivers.
USAGE
}

while [ $# -gt 0 ]; do
  case "$1" in
    --pane) PANE="${2:-}"; shift 2 ;;
    --project) PROJECT="${2:-}"; shift 2 ;;
    --interval) INTERVAL="${2:-}"; shift 2 ;;
    --once) ONESHOT=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "supervise.sh: unknown argument $1" >&2; usage >&2; exit 64 ;;
  esac
done

[ -n "$PANE" ] || { echo "supervise.sh: --pane is required" >&2; usage >&2; exit 64; }
command -v tmux >/dev/null 2>&1 || {
  echo "supervise.sh: tmux is not installed. It is the transport — a supervisor cannot put" >&2
  echo "  keystrokes into a running session's stdin without one." >&2; exit 69; }

GATE="$PROJECT/.claude/scripts/context_band.py"
[ -f "$GATE" ] || { echo "supervise.sh: $GATE not found — is this an initialised project?" >&2; exit 66; }

log() { printf '%s supervise: %s\n' "$(date -u +%H:%M:%SZ)" "$*" >&2; }

# THE HEARTBEAT. `context_band.py` answers "may this session be reset"; it says nothing about
# whether the session is still ALIVE. A session that idles, or sits in a dialog, never ends a
# turn — so the `Stop` gate that catches every other stop-for-nothing cannot see it, and the
# supervisor is the only process left watching. Judgement lives in `monitor.py` (testable, and
# runnable by a human); this file is transport, as it is for the gate.
#   action `nudge`    -> send a bare `continue`, which is what a session that quietly ended a
#                        turn needs. The monitor has ALREADY established that the session is at
#                        an idle prompt; this file does not re-decide it. It briefly did, as a
#                        veto here, and that cost the thing the veto was protecting: the judge
#                        spent its one-nudge budget on a nudge the transport silently dropped,
#                        and the next rung up is a durable `steer` park (OBSERVED 2026-09-20).
#   action `escalate` -> monitor.py has already parked a `steer`; the daemon's away channel
#                        takes it from there. Nothing to send.
MONITOR="$PROJECT/.claude/scripts/monitor.py"

heartbeat() {
  # `local`, because `tick` holds its own `why` (the gate's `blocked_by`) across this call and
  # a bare assignment here would print the monitor's reason under the gate's label.
  local action why
  [ -f "$MONITOR" ] || return 0
  action="$(python3 "$MONITOR" tick --workflow-dir "$PROJECT/$WORKFLOW" \
              --project-root "$PROJECT" --json 2>/dev/null \
            | python3 -c 'import json,sys
try:
    r = json.load(sys.stdin); print("%s\t%s" % (r.get("action","none"), r.get("why","")))
except Exception: print("none\t")' )"
  why="${action#*$'\t'}"; action="${action%%$'\t'*}"
  case "$action" in
    nudge)
      log "no motion — $why; nudging $PANE"
      tmux has-session -t "$PANE" >/dev/null 2>&1 || { log "pane $PANE is gone"; return 0; }
      tmux send-keys -t "$PANE" "continue" Enter || log "nudge failed; holding"
      ;;
    escalate) log "STALLED — $why; a steer checkpoint was parked" ;;
  esac
  return 0
}

# The loop is PAUSED. The latch is durable precisely so that an unattended driver sees it, and
# a paused loop must not be reset out from under the person who paused it.
paused() {
  [ -f "$PROJECT/.claude/scripts/drain.py" ] || return 1
  python3 "$PROJECT/.claude/scripts/drain.py" --workflow-dir "$PROJECT/$WORKFLOW" paused \
    >/dev/null 2>&1
}

# One question, one owner, and ONE CALL. The gate arms its own freshness latch, so asking it
# twice per tick — once for the verdict and once for the reason — made the poll a writer as well
# as a reader. Emitted as tab-separated fields rather than JSON for the reason `drive.py` gives:
# a supervisor that needs `jq` has a new way to fail at 3am.
#   field 1  safe   `1` when every condition holds
#   field 2  used   the context reading, the derived effect a landed `/clear` collapses
#   field 3  why    `blocked_by`, joined, for the log
# There is deliberately no `idle` field: the heartbeat used to take one and veto itself with it,
# which is the judgement this file does not own.
ask_gate() {
  python3 "$GATE" --workflow-dir "$PROJECT/$WORKFLOW" --project-root "$PROJECT" --gate 2>/dev/null \
    | python3 -c 'import json,sys
try:
    g = json.load(sys.stdin)
except Exception:
    print("0\x1f\x1fthe gate did not answer"); raise SystemExit
print("%s\x1f%s\x1f%s" % (
    "1" if g.get("clear_safe") else "0",
    (g.get("used") if isinstance(g.get("used"), int) else ""),
    "; ".join(g.get("blocked_by") or []) or "no reason given"))'
}

# The attempt ledger. Deliberately a file rather than a shell variable: `--once` is a whole
# process, and a cron-style driver calling it every minute must carry the same memory a
# long-running poller does, or the cap it is protected by does not exist.
LATCH="$PROJECT/$WORKFLOW/supervise-latch.json"

# Attempts so far whose effect never showed up, given the reading NOW. A reading that has fallen
# by a node or more means the last `/clear` landed after all, so the ledger is retired and the
# count starts over. An absent or unreadable ledger is zero — it can only ever cost one extra
# send, and the alternative (refusing to send because a scratch file will not parse) is a
# supervisor disabled by its own bookkeeping.
attempts_so_far() {
  [ -f "$LATCH" ] || { echo 0; return 0; }
  python3 -c '
import json, sys
try:
    with open(sys.argv[1], encoding="utf-8") as fh:
        rec = json.load(fh)
    was, now, drop = int(rec.get("used") or 0), sys.argv[2], int(sys.argv[3])
    if now.isdigit() and was and int(now) < was - drop:
        print(-1)                      # the reset landed; retire the ledger
    else:
        print(int(rec.get("attempts") or 0))
except Exception:
    print(0)' "$LATCH" "${1:-}" "$DROP_TOKENS" 2>/dev/null || echo 0
}

remember_attempt() {
  python3 -c '
import json, os, sys
path, used, n = sys.argv[1], sys.argv[2], int(sys.argv[3])
tmp = path + ".tmp"
try:
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump({"attempts": n, "used": int(used) if used.isdigit() else 0}, fh, sort_keys=True)
    os.replace(tmp, path)
except OSError:
    pass' "$LATCH" "${1:-}" "${2:-1}" 2>/dev/null || true
}

reset_session() {
  tmux has-session -t "$PANE" >/dev/null 2>&1 || { log "pane $PANE is gone; holding"; return 1; }
  log "clear_safe — resetting $PANE"
  tmux send-keys -t "$PANE" "/clear" Enter || { log "send of /clear failed; holding"; return 1; }
  sleep "$SETTLE"
  # The second send is not optional and is not a retry: the cleared session is idle, holding an
  # injected anchor and no turn to read it with.
  tmux send-keys -t "$PANE" "continue" Enter || { log "send of continue failed"; return 1; }
  log "sent /clear then continue"
  return 0
}

tick() {
  if paused; then log "loop is paused; holding"; return 1; fi

  IFS=$'\x1f' read -r safe used why <<<"$(ask_gate)"

  # Retire the ledger FIRST, on every tick, whatever the gate says. A landed reset collapses
  # the reading and then the gate is false for a long while — so a ledger only inspected on the
  # true branch would still be holding the previous cycle's count when the window next fills,
  # and three SUCCESSFUL resets in a row would trip a cap meant for three failed ones.
  n="$(attempts_so_far "$used")"
  if [ "$n" = "-1" ]; then rm -f "$LATCH"; n=0; fi

  if [ "$safe" != "1" ]; then
    # The reset gate held. That is the normal state, and it is also what a dead session looks
    # like — so this is exactly where the heartbeat belongs, rather than beside it.
    heartbeat
    log "holding — ${why:-no reason given}"; return 1
  fi

  if [ "$n" -ge "$MAX_RESETS" ] 2>/dev/null; then
    # Everything the gate can see says reset; the one thing it cannot see — whether the keys
    # were ever submitted — says the last $MAX_RESETS did nothing. Sending again is how a
    # prompt box fills with `/clear continue /clear continue`. Stop, and keep saying so: the
    # heartbeat still runs, and `monitor.py` still owns the escalation to a `steer`.
    heartbeat
    log "GIVING UP on resetting $PANE — $n sends left the context reading at ${used:-unknown}."
    log "  The keys are reaching tmux and not reaching the session. Look at the pane: if the"
    log "  prompt box holds unsubmitted text, clear it (Esc), then send \`continue\` yourself."
    log "  Delete $LATCH to let the supervisor try again."
    return 1
  fi

  if reset_session; then
    remember_attempt "$used" "$((n + 1))"
    return 0
  fi
  return 1
}

if [ "$ONESHOT" -eq 1 ]; then tick; exit $?; fi

log "supervising $PANE every ${INTERVAL}s (project: $PROJECT)"
while true; do
  tick || true
  sleep "$INTERVAL"
done

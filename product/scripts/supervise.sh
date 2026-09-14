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
# `clear_safe`, which is three things at once: the band says hand off now, an anchor has been
# written since it started saying so, and nothing is waiting on a human — neither a parked
# checkpoint nor an OPEN DIALOG. That last one is not theoretical: a live probe drove a real
# session into a permission prompt, where it sat, invisible to every other signal.
#
# TRANSPORT: `tmux send-keys`, probed rather than assumed. A real interactive session was driven
# end to end this way — a prompt ran, `/clear` cleared the transcript, a bare `continue` started
# a turn in the cleared session. Keys sent mid-turn queue: the pty buffers them while the TUI is
# not reading and hands them over intact, in order, on the next read.
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

# The loop is PAUSED. The latch is durable precisely so that an unattended driver sees it, and
# a paused loop must not be reset out from under the person who paused it.
paused() {
  [ -f "$PROJECT/.claude/scripts/drain.py" ] || return 1
  python3 "$PROJECT/.claude/scripts/drain.py" --workflow-dir "$PROJECT/$WORKFLOW" paused \
    >/dev/null 2>&1
}

# One question, one owner. Exit 0 means every condition holds.
clear_safe() {
  python3 "$GATE" --workflow-dir "$PROJECT/$WORKFLOW" --project-root "$PROJECT" --gate \
    >/dev/null 2>&1
}

why_held() {
  python3 "$GATE" --workflow-dir "$PROJECT/$WORKFLOW" --project-root "$PROJECT" --gate 2>/dev/null \
    | python3 -c 'import json,sys
try: print("; ".join(json.load(sys.stdin).get("blocked_by") or []) or "no reason given")
except Exception: print("the gate did not answer")'
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
  if clear_safe; then reset_session; else
    log "holding — $(why_held)"; return 1
  fi
}

if [ "$ONESHOT" -eq 1 ]; then tick; exit $?; fi

log "supervising $PANE every ${INTERVAL}s (project: $PROJECT)"
while true; do
  tick || true
  sleep "$INTERVAL"
done

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
# A PANE ID IS NOT AN IDENTITY, which is the defect this file shipped with and the reason for
# the claim below. `--pane %0` was treated as naming the session it was armed against, and it
# does not: pane ids are assigned by the tmux SERVER, and when the last session closes the
# server dies and the next one starts numbering at `%0` again (verified, not reasoned about).
# Worse, nothing reaped a supervisor whose pane vanished — `reset_session` logged
# `pane %0 is gone; holding` and held forever. So a supervisor armed for project A, long after
# A's session ended, would see `%0` exist again and send `/clear` into project B's brand-new
# session, gated on A's context reading and A's anchor. OBSERVED 2026-09-22: four live
# supervisors on one machine, three of them pinned to `%0` across two different projects, the
# oldest orphaned for a day and a half.
#
# The fix is that a supervisor CLAIMS its pane and proves the claim before every send. At start
# it stamps `@reeve_token` (its own pid and start time) and `@reeve_project` on the pane; every
# tick re-reads the stamp. Three outcomes, and each is decidable rather than inferred:
#   the stamp is OURS     -> this is the session we were armed for; proceed.
#   the pane is GONE      -> that session is over. Hold for a few ticks in case tmux is briefly
#                            unreachable, then EXIT. Holding forever is what turns a finished
#                            supervisor into a hazard for the next one.
#   the stamp is NOT ours -> the pane exists and belongs to something else: the id was recycled.
#                            Stand down immediately. There is no reading of this in which
#                            typing is correct.
# The claim is also the duplicate guard the preflight could never be: `supervisor.py` reads THIS
# project's record, so it is blind to another project's supervisor holding the same pane, and
# the hazard is machine-wide. A pane already claimed by a LIVE supervisor refuses at startup.
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
# THE GIVE-UP IS RECORDED WHERE SOMETHING CAN ACT ON IT (`gave_up` on the latch). It used to be a
# log line and nothing else, so an operator who was not reading `supervise.log` learned about it
# by noticing the drive had stopped — the failure mode the away channel exists to abolish.
# `monitor.py` reads the flag and parks a `steer`; the judgement stays there, this file only
# records its own state.
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
# Consecutive ticks with NO pane at all before this process gives up and exits. Not a timeout on
# the session: a missing pane is already proof the session is over. It is slack for tmux being
# momentarily unreachable, and three ticks of it (three minutes at the default interval) is more
# than that ever needs. Past it, exiting is the safe direction — an orphan that keeps polling is
# the thing that ends up typing into somebody else's window.
MAX_PANE_MISSING="${REEVE_SUPERVISE_MAX_PANE_MISSING:-3}"
# Consecutive missing-pane ticks, held in a shell variable because the poller is ONE process and
# this is a fact about its own life. `--once` therefore always starts at zero, which is correct:
# a cron-style driver re-arms from scratch every time and has no orphan to become.
PANE_MISSING=0

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

Exit codes: 0 reset performed · 1 held · 3 stood down (the pane is gone for good, or its id
was recycled and now belongs to something else) · 64 bad arguments · 66 uninitialised project ·
69 no tmux · 75 the pane is already claimed by a live supervisor, or cannot be stamped.
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

# ----------------------------------------------------------------- the pane claim
#
# The identity this process types against. `--pane` names a TARGET, which tmux is free to hand
# to somebody else the moment our session ends; the token names THIS SUPERVISOR, and the pane
# carries it only for as long as the pane is the one we claimed. pid first so a reader (and the
# takeover check below) can find the owner without parsing anything.
PROJECT_ABS="$(cd "$PROJECT" 2>/dev/null && pwd -P || printf '%s' "$PROJECT")"
TOKEN="$$:$(date -u +%s)"

# Is `$1` a live supervisor? The same two questions `supervisor.py` asks of its record, for the
# same reason: pid reuse means existence alone is not enough, and where the command line cannot
# be read the answer must be the CAUTIOUS one (assume it is, and refuse) rather than the
# convenient one.
owner_is_supervisor() {
  kill -0 "$1" 2>/dev/null || return 1
  [ -r "/proc/$1/cmdline" ] || return 0
  grep -qa "supervise.sh" "/proc/$1/cmdline"
}

# `ours` | `gone` | `theirs` — one decidable answer, asked before every keystroke this file
# sends. Note `gone` and `theirs` are NOT the same condition and must not be collapsed: the
# first is a session that ended, the second is somebody else's session wearing its pane id.
pane_state() {
  local cur
  tmux has-session -t "$PANE" >/dev/null 2>&1 || { echo gone; return 0; }
  cur="$(tmux show-options -pv -t "$PANE" @reeve_token 2>/dev/null || true)"
  if [ "$cur" = "$TOKEN" ]; then echo ours; else echo theirs; fi
}

# Stamp the pane, or refuse. Called once, at start.
#
# A pane that does not exist YET is not a refusal — `--once` drivers and the tests arm against
# a target that may be absent, and the tick loop already has a considered answer for it. What
# refuses is a pane already claimed by a supervisor that is still running: that is the
# three-on-one-pane failure, and it is the case `supervisor.py preflight` structurally cannot
# see, because its record is per-project and this hazard is per-machine.
claim_pane() {
  local existing owner
  tmux has-session -t "$PANE" >/dev/null 2>&1 || {
    log "pane $PANE does not exist yet — nothing claimed; the tick loop owns that case"
    return 0
  }
  existing="$(tmux show-options -pv -t "$PANE" @reeve_token 2>/dev/null || true)"
  if [ -n "$existing" ] && [ "$existing" != "$TOKEN" ]; then
    owner="${existing%%:*}"
    if owner_is_supervisor "$owner"; then
      log "REFUSING: pane $PANE is already claimed by supervisor pid $owner (project: $(tmux show-options -pv -t "$PANE" @reeve_project 2>/dev/null || echo unknown))."
      log "  Two supervisors on one pane send /clear on two schedules into one conversation."
      log "  Stop that one first, or arm this project in its own tmux session."
      exit 75
    fi
    log "pane $PANE carried a stale claim from pid $owner, which is not running — taking it over"
  fi
  tmux set-option -p -t "$PANE" @reeve_token "$TOKEN" 2>/dev/null || {
    log "REFUSING: cannot stamp pane $PANE (tmux set-option -p failed — pane options need"
    log "  tmux >= 3.0). Without the stamp a recycled pane id cannot be told apart from the"
    log "  session this supervisor was armed for, and a process that cannot prove which pane"
    log "  is its own must not type into one."
    exit 75
  }
  tmux set-option -p -t "$PANE" @reeve_project "$PROJECT_ABS" 2>/dev/null || true
  log "claimed pane $PANE (token $TOKEN, project $PROJECT_ABS)"
}

# The end of this process's usefulness, and therefore the end of the process. THE FAIL DIRECTION
# ARGUMENT CUTS BOTH WAYS and the original only followed it one step: "do nothing" is right
# about the tick in hand, and wrong as a way to spend the rest of a life, because the nothing
# accumulates into an orphan that acts wrongly later against a session it was never armed for.
stand_down() {
  log "STANDING DOWN — $*"
  log "  A pane id is not an identity: tmux restarts numbering at %0 with every new server, so"
  log "  a supervisor that outlived its session would eventually type into a different"
  log "  project's window. There is nothing here to supervise; exiting rather than holding."
  exit 3
}

# PUBLISH, BECAUSE THERE IS NO AMBIENT SIGNAL TO READ. The heartbeat that catches a dead loop
# runs INSIDE this process, so it is hosted by something that can simply not be there — and when
# it was not (supervisors stopped for a deploy and never restarted, 2026-09-19) NOTHING anywhere
# said so: not the console, not the status line, not the loop, not the turn gate. Both drives ran
# until they stopped on their own and then sat idle for eleven hours. The same argument `loop.sh`
# makes for the orchestrator lock applies here: a live process must say so. `supervisor.py` owns
# the record and the liveness check; this file only states its own existence.
SUPERVISOR="$PROJECT/.claude/scripts/supervisor.py"
publish_self() {
  [ -f "$SUPERVISOR" ] || return 0
  python3 "$SUPERVISOR" publish --workflow-dir "$PROJECT/$WORKFLOW" --pid "$$" --pane "$PANE" \
    >/dev/null 2>&1 || true
}
# Retired on EVERY exit, because a record left by a supervisor that stopped cleanly reads as
# `gone` — an alarm rather than a fact. A kill -9 leaves it behind and the liveness check is what
# makes that harmless: the pid is not there, so the answer is `gone`, which is true.
retire_self() {
  [ -f "$SUPERVISOR" ] || return 0
  python3 "$SUPERVISOR" retire --workflow-dir "$PROJECT/$WORKFLOW" >/dev/null 2>&1 || true
}

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

# `$3` is the give-up flag, and it is the one thing on this ledger a second process reads.
# RECORDING A FACT, NOT MAKING A JUDGEMENT: "my sends stopped changing anything and I have
# stopped trying" is this process's own state, the same way `attempts` is. What to DO about it —
# park a `steer` so the away channel alerts somebody — is `monitor.py`'s, because that is where
# every other escalation in this package is decided and where the steer floor's evidence is read
# from. A give-up that only ever reached `supervise.log` was a stop nobody outside this terminal
# could learn about, which is the failure the away channel exists to abolish.
remember_attempt() {
  python3 -c '
import json, os, sys
path, used, n = sys.argv[1], sys.argv[2], int(sys.argv[3])
tmp = path + ".tmp"
try:
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump({"attempts": n, "used": int(used) if used.isdigit() else 0,
                   "gave_up": sys.argv[4] == "1"}, fh, sort_keys=True)
    os.replace(tmp, path)
except OSError:
    pass' "$LATCH" "${1:-}" "${2:-1}" "${3:-0}" 2>/dev/null || true
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
  # BEFORE ANYTHING ELSE, because both keystroke paths below this line — the reset AND the
  # heartbeat's nudge — are equally capable of typing into the wrong session, and the nudge
  # used to be guarded by nothing but `has-session`.
  case "$(pane_state)" in
    ours)
      PANE_MISSING=0
      ;;
    gone)
      # Fall through while the count is under the cap: the gate, the ledger and the existing
      # `pane ... is gone` logging all still have something true to say, and a pane that is
      # missing for one tick is not yet evidence of anything. Past the cap it is.
      PANE_MISSING=$((PANE_MISSING + 1))
      if [ "$PANE_MISSING" -ge "$MAX_PANE_MISSING" ]; then
        stand_down "pane $PANE has been gone for $PANE_MISSING consecutive checks — the session it was armed for is over"
      fi
      ;;
    theirs)
      stand_down "pane $PANE exists and does not carry this supervisor's claim — its id was recycled and it now belongs to something else"
      ;;
  esac

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
    remember_attempt "$used" "$n" 1
    heartbeat
    log "GIVING UP on resetting $PANE — $n sends left the context reading at ${used:-unknown}."
    log "  The keys are reaching tmux and not reaching the session. Look at the pane: if the"
    log "  prompt box holds unsubmitted text, clear it (Esc), then send \`continue\` yourself."
    log "  Delete $LATCH to let the supervisor try again."
    return 1
  fi

  if reset_session; then
    remember_attempt "$used" "$((n + 1))" 0
    return 0
  fi
  return 1
}

# `--once` is a whole process and deliberately publishes nothing: a cron-style driver that
# announced itself for a second and vanished would leave every reader flapping between `running`
# and `gone`. The long-running poller below is the thing that can honestly claim to be watching.
claim_pane

if [ "$ONESHOT" -eq 1 ]; then tick; exit $?; fi

# A TRAPPED SIGNAL MUST STILL KILL, and this file's did not. `trap retire_self EXIT INT TERM`
# ran the handler and then RESUMED THE LOOP -- bash does not exit on its own after a signal
# trap -- so an ordinary `kill` or `pkill` retired the record and left the poller running. The
# supervisor was un-killable by the one command an operator reaches for, and it had just
# deleted the only evidence it was there: `supervisor.py alive()` reads that record, so both
# the status line and the preflight then reported `none` over a live process still typing into
# a pane. FOUND BY A `pkill` THAT DID NOT WORK, 2026-09-22 -- two of four orphans survived it.
#
# So the signal handler exits, and `EXIT` stays separate for the ordinary paths (a `stand_down`,
# a refusal, falling off the end). 130/143 are the shell's own conventions for "died of SIGINT /
# SIGTERM", which is what actually happened.
trap 'retire_self; exit 130' INT
trap 'retire_self; exit 143' TERM
trap retire_self EXIT
publish_self
log "supervising $PANE every ${INTERVAL}s (project: $PROJECT)"
while true; do
  tick || true
  # Backgrounded and waited on, so a signal is handled the instant it arrives rather than at the
  # end of the interval: bash defers a trap until the running foreground command returns, and a
  # `kill` that appears to do nothing for up to a minute is one an operator repeats, then
  # escalates to -9 -- which skips the handler and leaves the record behind.
  sleep "$INTERVAL" & wait $! || true
done

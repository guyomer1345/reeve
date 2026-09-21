#!/usr/bin/env bash
# The orchestrator launcher — start the disciplined-builder loop THROUGH THIS, not bare
# `claude`.
#
# WHY: the always-alive console daemon hosts a relaunch-runner (config.runner.enabled)
# that resumes a whole-parked or dead loop when a verdict lands from a phone. Before it
# spawns, it must know no orchestrator is already live — else two would drive the same
# .workflow/ and silently clobber each other's state (the single-orchestrator run-constraint's
# honest residual, which it is the runner's job not to CAUSE). There is no ambient signal to read (Claude Code
# runs many claude-named helper processes; a state.json mtime lies both ways), so a live
# orchestrator must PUBLISH itself. This launcher does that: it holds an flock on the
# orchestrator-lock for the session's whole lifetime. The kernel drops it when the session
# dies, so there is never a stale lock to clean up (unlike a pidfile).
#
# A runner-launched `claude -p` holds the same lock via `flock` directly; this launcher is
# the HUMAN half. Start bare `claude` instead and the runner cannot see you — if the runner
# is on, it may spawn a duplicate. That bypass is the one operator-responsibility residual,
# on the same footing as the single-orchestrator run-constraint.
#
# Pass-through: every argument goes to `claude` unchanged (`loop.sh --resume …`, etc.).
#
# `--supervise` (must be the FIRST argument) is THE ONE COMMAND: it preflights the project,
# puts itself inside tmux if it is not already, starts the self-clearing supervisor beside the
# session, and prints what it armed. From there the operator types `continue` once and the run
# is supervised. It used to be three commands plus four things you had to know to check by hand
# (`pgrep` for duplicate supervisors, `parked/` for a stale ticket, `config.json` for a ceiling,
# the log to confirm any of it took) — and every failure of the week that produced this came
# from that list rather than from the loop: three supervisors on one pane and none on the other,
# supervisors stopped for a deploy and never restarted, a false park nobody could see without
# reading JSON. It REFUSES rather than hand back a half-armed state, and it reports everything
# it cannot refuse over.
#
# `--drive` (must be the FIRST argument) turns this launcher into a session DRIVER: hold the
# lock, run a session, and when it exits start the next one against the same goal until the
# goal is met, the operator pauses, or nothing is moving. Everything it decides between
# sessions lives in `drive.py`, not here — a bash script making those calls is untestable
# exactly where being wrong costs a whole unattended night. Without `--drive` this file
# behaves exactly as it always has: one `exec claude`, and the human drives.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WF="${WORKFLOW_DIR:-.workflow}"

# THE tmux BOOTSTRAP, AND IT RUNS BEFORE THE LOCK IS TAKEN — which is the whole reason it can
# exist at all. The refusal it replaces was right about the hazard: if THIS process took the
# orchestrator lock and then started tmux, the lock would belong to the tmux CLIENT, and
# detaching (the normal thing to do with tmux) would release it while the orchestrator ran on.
# So this branch re-enters the same script INSIDE the pane, before touching the lock: the inner
# instance is the one that takes it and execs `claude`, exactly as a hand-started session does.
# Nothing is held across the exec below, so there is no window in which the lock is dropped.
if [ "${1:-}" = "--supervise" ] && [ -z "${TMUX:-}" ]; then
  if ! command -v tmux >/dev/null 2>&1; then
    echo "loop.sh --supervise: tmux is not installed. It is the transport — a supervisor" >&2
    echo "         cannot put keystrokes into a running session's stdin without one." >&2
    exit 69
  fi
  SESSION="${REEVE_TMUX_SESSION:-reeve}"
  if tmux has-session -t "$SESSION" 2>/dev/null; then
    echo "loop.sh --supervise: a tmux session named '$SESSION' already exists. Attach to it" >&2
    echo "         (tmux attach -t $SESSION) — or pick another name:" >&2
    echo "             REEVE_TMUX_SESSION=other .claude/scripts/loop.sh --supervise" >&2
    echo "         Refusing to guess: starting a second orchestrator against one .workflow/" >&2
    echo "         is the hazard this launcher exists to prevent." >&2
    exit 1
  fi
  # The preflight runs HERE, where its output is on a terminal the operator is still looking at.
  # Inside the pane the TUI paints over everything within a second of starting.
  if [ -f "$HERE/supervisor.py" ]; then
    python3 "$HERE/supervisor.py" preflight --project . || exit 1
  fi
  shift
  # Re-entered under a DIFFERENT flag, so the inner instance cannot bootstrap a second time if
  # `$TMUX` is somehow still unset inside the pane — a launcher that can recurse into tmux is a
  # fork bomb with a friendly name.
  inner="$(printf '%q' "$HERE/loop.sh") --supervise-inner"
  for arg in "$@"; do inner="$inner $(printf '%q' "$arg")"; done
  # The pane dies with its command, so a launch that fails inside it would close the window
  # before anyone read why. Hold it open on failure only; a successful launch execs `claude`
  # and never reaches this.
  exec tmux new-session -s "$SESSION" \
    "$inner || { printf '\n[loop.sh: the supervised launch failed — press Enter to close] '; read x; }"
fi
if [ "${1:-}" = "--supervise-inner" ]; then set -- "--supervise" "${@:2}"; fi

# Resolve the lock path through bus.py's Paths — the single owner of runtime-path
# resolution — so a relocated runtime tree (runtime.json) is honoured automatically.
LOCK="$(python3 -c "import sys; sys.path.insert(0, '$HERE'); from bus import Paths; print(Paths('$WF').orchestrator_lock)")"
mkdir -p "$(dirname "$LOCK")"

# `flock` MUST be probed separately from taking the lock. Without this, a missing flock
# exits 127, `if ! flock` inverts that into the "already held" branch, and the operator is
# told another orchestrator is running — sending them to hunt a session that does not exist,
# on a machine where the launcher can never work. Same refusal either way (the duplicate-
# orchestrator hazard this file exists to prevent is not worth trading for convenience);
# what changes is that the diagnosis is true. Git for Windows' bash ships no flock.
if ! command -v flock >/dev/null 2>&1; then
  echo "loop.sh: 'flock' is not available on this system, so the orchestrator lock cannot" >&2
  echo "         be published. The relaunch-runner would not be able to see this session and" >&2
  echo "         could spawn a second orchestrator against the same ${WF}. Refusing to start." >&2
  echo "         This is NOT 'another orchestrator is running' — nothing is holding the lock." >&2
  echo "         Git for Windows' bash ships no flock: run from WSL, or install util-linux." >&2
  exit 1
fi

# Open the lock on fd 9 and hold it. A bash redirection fd is NOT close-on-exec, so it
# survives the `exec claude` below and the lock is held for claude's whole lifetime.
exec 9>"$LOCK"
if ! flock -n 9; then
  holder="$(cat "$LOCK" 2>/dev/null || true)"
  echo "loop.sh: an orchestrator already holds ${LOCK}${holder:+ (pid ${holder})}." >&2
  echo "         Not starting a second — two would silently clobber each other's state." >&2
  echo "         If that session is actually dead or stuck, end it (or kill the pid) and retry." >&2
  exit 1
fi
# Record the holder pid for humans. After `exec claude` this process keeps the same pid,
# so the file names claude's real pid. The flock — not this value — is the authority.
echo "$$" >&9

# `--supervise` (first argument): start the self-clearing supervisor beside this session, then
# launch normally. The supervisor polls `context_band.py --gate` and, when a reset is safe,
# sends `/clear` then `continue` into THIS pane.
#
# IT RUNS INSIDE tmux, and the bootstrap at the top of this file is what puts it there — before
# the lock is taken, and by re-entering this same script in the new pane. That ordering is the
# whole design, and it is why this used to be a flat refusal. The lock above is held on fd 9 by
# the process that becomes `claude`, for claude's whole lifetime — that is what the relaunch-
# runner probes. If the OUTER process took the lock and then started tmux, the lock would belong
# to the tmux CLIENT, and detaching (the normal thing to do with tmux) would release it while
# the orchestrator was still running. Two orchestrators against one `.workflow/` is the exact
# hazard this file exists to prevent. So tmux is still the terminal claude is started IN and
# never something started for it — the launcher simply walks into that terminal first.
if [ "${1:-}" = "--supervise" ]; then
  shift
  # Unreachable by the ordinary path — the bootstrap at the top of this file puts a supervised
  # launch inside tmux itself. It stays as the floor: `$TMUX` set without `$TMUX_PANE` is a
  # shell that inherited the environment without being in a pane, and typing into a pane that
  # does not exist is how a supervisor clears the wrong window.
  if [ -z "${TMUX:-}" ] || [ -z "${TMUX_PANE:-}" ]; then
    echo "loop.sh --supervise: \$TMUX is set but \$TMUX_PANE is not, so there is no pane to" >&2
    echo "         supervise. Run this from a real tmux pane." >&2
    exit 78
  fi
  # Already inside tmux (either the bootstrap above put us here, or the operator was). The
  # preflight is re-run rather than trusted from the outer process: between the two there is an
  # exec and a new pane, and the one fatal it can catch — a supervisor already running — is
  # exactly the race that produced three supervisors on one pane.
  if [ -f "$HERE/supervisor.py" ]; then
    python3 "$HERE/supervisor.py" preflight --project . --pane "$TMUX_PANE" >&2 || exit 1
  fi
  if [ -x "$HERE/supervise.sh" ]; then
    # Detached and best-effort: a supervisor that fails to start must never stop the session
    # it was going to supervise. It logs to the runtime tree, not to this pane, which the TUI
    # is about to take over.
    nohup "$HERE/supervise.sh" --pane "$TMUX_PANE" --project . \
      >>"$WF/supervise.log" 2>&1 &
    echo "loop.sh: supervisor started on pane $TMUX_PANE (log: $WF/supervise.log)" >&2
  else
    echo "loop.sh: supervise.sh not found beside this script; starting unsupervised." >&2
  fi
  # The turn gate reads this. It is exported HERE rather than written to a file because the fact
  # it marks is about THIS PROCESS — a session nobody is watching — and a durable flag would
  # outlive the session that set it and gate the human's next interactive run.
  export REEVE_SUPERVISE=1
  exec claude "$@"
fi

if [ "${1:-}" != "--drive" ]; then
  exec claude "$@"
fi
shift

# ---------------------------------------------------------------- the session driver
#
# WHY A FRESH PROCESS RATHER THAN `/clear`. `/clear` cannot be self-invoked at all, so this is
# not a second-best: a new session IS the reset, and it starts from the same durable anchor a
# cold start already rebuilds from (`handoff.md` + git). The session-side discipline — stop at
# a scheduler boundary, never mid-item, with the handoff written — is carried in the PROMPT
# below rather than in the always-loaded brief, deliberately: it is the driver's instruction to
# its own sessions, not a standing rule, and a human session must never auto-stop. It also
# costs the always-loaded budget nothing.
DRIVE_PROMPT="${REEVE_DRIVE_PROMPT:-Continue the loop. Work items to completion, committing \
each as normal. STOP AT A SCHEDULER BOUNDARY — between items, never mid-item — and before you \
stop, rewrite .workflow/handoff.md whole so a session that knows nothing can continue. Do not \
run /clear and do not ask the human anything you can decide; park a checkpoint if you truly \
need them.}"
WF="${WORKFLOW_DIR:-.workflow}"
# The drop-in window: seconds between sessions with the lock RELEASED, so a human can take the
# machine simply by starting their own `loop.sh` — no flag to set, no signal to send. Whoever
# takes the lock wins, and the driver finds out by losing the race rather than by being told.
DROPIN="${REEVE_DROPIN_SECONDS:-5}"

drive() { python3 "$HERE/drive.py" --workflow-dir "$WF" "$@"; }

DRIVE_FINGERPRINT=""; DRIVE_STREAK=0; SESSIONS=0
while true; do
  # `eval` of KEY=VALUE, not JSON — a driver that needs `jq` has a new way to fail at 3am.
  set +e; verdict="$(drive tick --prev-fingerprint "$DRIVE_FINGERPRINT" \
                          --streak "$DRIVE_STREAK" --shell)"; rc=$?; set -e
  eval "$verdict"
  if [ "${DRIVE_CONTINUE}" != "1" ]; then
    echo "loop.sh --drive: stopping after ${SESSIONS} session(s) — ${DRIVE_REASON}" >&2
    exit 0
  fi
  SESSIONS=$((SESSIONS + 1))
  echo "loop.sh --drive: session ${SESSIONS} (${DRIVE_REASON})" >&2
  # A non-zero session is NOT a driver failure: a crashed or killed session is exactly the case
  # the fingerprint exists to judge, and it gets judged on what it left behind, not on its exit
  # code. `set -e` must not turn that into an abort.
  set +e; REEVE_DRIVE=1 claude -p "$DRIVE_PROMPT" "$@"; set -e

  # The drop-in window. Releasing and re-taking is the whole handover protocol: if anyone else
  # (a human launcher, or the daemon's relaunch-runner) takes the lock in the gap, the
  # re-acquire fails and this driver steps aside rather than racing a second orchestrator
  # against the same .workflow/ — the one hazard the lock exists to prevent.
  if [ "$DROPIN" -gt 0 ]; then
    flock -u 9
    sleep "$DROPIN"
    if ! flock -n 9; then
      echo "loop.sh --drive: another orchestrator took the lock during the drop-in window —" >&2
      echo "                 handing over and exiting. This is the intended way to take over." >&2
      exit 0
    fi
    echo "$$" >&9
  fi
done

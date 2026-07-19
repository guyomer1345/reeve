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
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WF="${WORKFLOW_DIR:-.workflow}"

# Resolve the lock path through bus.py's Paths — the single owner of runtime-path
# resolution — so a relocated runtime tree (runtime.json) is honoured automatically.
LOCK="$(python3 -c "import sys; sys.path.insert(0, '$HERE'); from bus import Paths; print(Paths('$WF').orchestrator_lock)")"
mkdir -p "$(dirname "$LOCK")"

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

exec claude "$@"

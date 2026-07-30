#!/usr/bin/env bash
# Git-native pre-commit backstop for the disciplined-builder loop.
#
# Fires on EVERY commit, including paths the PreToolUse guard.sh never sees
# (a human `git commit`, an editor/IDE commit, a `make` target). So it carries
# the same never-want-irreversible hard blocks as guard.sh — secret-scan +
# verify-before-commit — plus the mechanical check runner (`.workflow/checks.sh`,
# installed fixed by /start; per-stack commands in `.workflow/checks.env`). It validates the STAGED diff, not the whole
# working tree, so a two-commit split (a prerequisite-repair committed separately
# from the planned change) stays atomic.
#
# Installed by /start to `.git/hooks/pre-commit`. Fails OPEN only for the
# mechanical runner (none wired yet → proceed); the secret + verify gates always run.
set -uo pipefail

# --- isolate the staged diff: stash unstaged changes, always restore on exit ---
stashed=0
restore() { [ "$stashed" = 1 ] && git stash pop -q 2>/dev/null || true; }
trap restore EXIT
if ! git diff --quiet 2>/dev/null; then
  git stash push -q --keep-index -m disciplined-builder-precommit 2>/dev/null && stashed=1
fi

block() { echo "BLOCKED by disciplined-builder pre-commit: $1" >&2; exit 1; }

# --- secret-scan on the staged diff (git-native mirror of guard.sh) ---
if git diff --cached 2>/dev/null | grep -Eiq \
  '(AKIA[0-9A-Z]{16}|gh[pousr]_[A-Za-z0-9]{36}|xox[baprs]-[A-Za-z0-9-]{10,}|AIza[A-Za-z0-9_-]{35}|[sr]k_live_[A-Za-z0-9]{20,}|-----BEGIN [A-Z ]*PRIVATE KEY-----|(api[_-]?key|secret|password|token)["'"'"' ]*[:=]["'"'"' ]*[A-Za-z0-9/+_-]{12,})'; then
  block "possible secret in the staged diff (secret-scan). Remove it or use a placeholder."
fi

# --- verify-before-commit (git-native backstop) ---
# Delegated to the shared helper both hooks call, so guard.sh and this file enforce it IDENTICALLY.
# It fails CLOSED and does not trust a single state.json key/path: it derives the item(s) from the
# staged diff (immune to state.json shape/path drift) and cross-checks a runtime-resolved state.json.
# CONTRACT (shared/schemas.md · verify): `.workflow/items/<id>/verify-verdict.md`, first line
# exactly `pass: true|false`.
vmsg="$(python3 .claude/hooks/verify_check.py 2>&1)"; vrc=$?
[ "$vrc" -eq 0 ] || block "${vmsg:-verify-before-commit could not run (python3?). Failing closed.}"

# --- mechanical check runner in CHECK-ONLY mode (never rewrites the tree here) ---
runner=".workflow/checks.sh"
if [ -f "$runner" ]; then
  # The second clause is a ROUTE, not a diagnosis. A gate that fails because its
  # commands cannot RUN looks identical here to one that fails because a test is red,
  # and this hook has no business guessing which — that guess is exactly what went
  # wrong on the real machine move. It names the other possibility and the cure, and
  # lets the reader decide. This is the standing half of the bindability check:
  # `/rebind` probes once at the transition, and this catches a toolchain that rots
  # later, at the moment it actually matters, and visibly to `claude -p`.
  bash "$runner" --check || block "mechanical checks failed. Run the commit skill (auto-fixes) or 'bash $runner --fix', then re-stage.
  If the check COMMANDS themselves could not run (not found / no such module), this machine never got the toolchain that
  '.workflow/checks.env' names — it is gitignored and does not travel between machines. Install it, or run /rebind."
fi

exit 0

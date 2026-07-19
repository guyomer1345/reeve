#!/usr/bin/env bash
# Git-native pre-commit backstop for the disciplined-builder loop.
#
# Fires on EVERY commit, including paths the PreToolUse guard.sh never sees
# (a human `git commit`, an editor/IDE commit, a `make` target). So it carries
# the same never-want-irreversible hard blocks as guard.sh — secret-scan +
# verify-before-commit — plus the mechanical check runner (`.workflow/checks.sh`,
# generated per-stack by /start). It validates the STAGED diff, not the whole
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
item="$(python3 -c 'import json; print(json.load(open(".workflow/state.json")).get("current_item") or "")' 2>/dev/null || true)"
if [ -n "$item" ]; then
  verdict=".workflow/items/$item/verify-verdict.md"
  [ -f "$verdict" ] || block "item $item has no verify-verdict; run verify before committing."
  grep -Eiq 'pass[^[:alnum:]]{1,8}false' "$verdict" && block "item $item has a failing verify-verdict; debug -> refine -> verify first."
fi

# --- mechanical check runner in CHECK-ONLY mode (never rewrites the tree here) ---
runner=".workflow/checks.sh"
if [ -f "$runner" ]; then
  bash "$runner" --check || block "mechanical checks failed. Run the commit skill (auto-fixes) or 'bash $runner --fix', then re-stage."
fi

exit 0

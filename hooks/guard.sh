#!/usr/bin/env bash
# PreToolUse(Bash) guard for the disciplined-builder loop.
#
# Enforces the gates that are legitimate HARD blocks — operations you never *want*
# to perform, so there is no approve-and-proceed path:
#   - secret-scan          : never commit a secret staged in the diff
#   - verify-before-commit : never commit an item whose verify-verdict is a fail
#   - obscured outward act  : an outward action hidden in a chain/subshell is forced
#                             to run directly, so the settings.json `ask` rule can fire
#
# Plain outward actions (a direct `git push` / `gh`) are NOT blocked here — they are
# `ask` rules in settings.json (a deliberate human prompt), not a forbid. This guard
# only stops ones OBSCURED so the literal-prefix `ask` matcher can't see them.
#
# Exit 2 blocks the tool call (message on stderr), overrides allow rules, and fires
# under bypassPermissions mode. Exit 0 lets the call proceed.
#
# Fail-CLOSED on the gated operations: if python3 is unavailable we match against the
# raw hook payload instead of the parsed command, so removing python3 cannot disable
# the gate. The git-native pre-commit hook is the backstop for wrapper paths
# (make / editor / IDE) whose top-level command this PreToolUse hook never sees.
set -uo pipefail

payload="$(cat)"
cmd="$(printf '%s' "$payload" \
  | python3 -c 'import sys,json; print(json.load(sys.stdin).get("tool_input",{}).get("command",""))' \
  2>/dev/null || true)"
# Fallback: python3 absent (cmd empty) → match against the raw payload, not nothing.
hay="$cmd"; [ -z "$hay" ] && hay="$payload"

block() { echo "BLOCKED by disciplined-builder guard: $1" >&2; exit 2; }

# --- commit gates: robust `git … commit` detection (any -c/--flag before `commit`) ---
if printf '%s' "$hay" | grep -Eq '(^|[^[:alnum:]/])git([[:space:]]+-[^[:space:]]+)*[[:space:]]+commit([^[:alnum:]]|$)'; then
  # secret-scan on the staged diff
  staged="$(git diff --cached 2>/dev/null || true)"
  if printf '%s' "$staged" | grep -Eiq \
    '(AKIA[0-9A-Z]{16}|gh[pousr]_[A-Za-z0-9]{36}|xox[baprs]-[A-Za-z0-9-]{10,}|AIza[A-Za-z0-9_-]{35}|[sr]k_live_[A-Za-z0-9]{20,}|-----BEGIN [A-Z ]*PRIVATE KEY-----|(api[_-]?key|secret|password|token)["'"'"' ]*[:=]["'"'"' ]*[A-Za-z0-9/+_-]{12,})'; then
    block "possible secret in the staged diff (secret-scan). Remove it or use a placeholder before committing."
  fi

  # verify-before-commit: a set item must have a PASSING verdict on disk
  item="$(python3 -c 'import json; print(json.load(open(".workflow/state.json")).get("current_item") or "")' 2>/dev/null || true)"
  if [ -n "$item" ]; then
    verdict=".workflow/items/$item/verify-verdict.md"
    [ -f "$verdict" ] || block "item $item has no verify-verdict; run verify before committing."
    if grep -Eiq 'pass[^[:alnum:]]{1,8}false' "$verdict"; then
      block "item $item has a failing verify-verdict; run debug -> refine -> verify before committing."
    fi
  fi
fi

# --- obscured outward actions: force a direct invocation so the settings `ask` fires ---
outward='git[[:space:]]+push|gh[[:space:]]+(issue|pr|release|repo|api)|(npm|yarn|pnpm)[[:space:]]+(publish|run[[:space:]]+deploy)|(docker|cargo|gem|twine)[[:space:]]+(push|publish|upload)|(vercel|netlify|fly|flyctl|serverless|pulumi)[[:space:]]|terraform[[:space:]]+apply'
chain='&&|\|\||;|\$\(|`'
if printf '%s' "$hay" | grep -Eq "$outward" && printf '%s' "$hay" | grep -Eq "$chain"; then
  block "outward action hidden in a chain/subshell — run it as a single direct command so it prompts for approval (the outward-action gate)."
fi

exit 0

#!/usr/bin/env bash
# .workflow/checks.sh — the per-item mechanical gate.
#
# SHIPPED FIXED. /start copies this file VERBATIM from templates/checks.sh; the only
# per-project input is .workflow/checks.env, a data file /start writes from stack
# detection. Do NOT hand-edit this file — re-running /start (or a plugin update)
# re-copies it, and any local edit is lost. Per-project variation belongs in checks.env.
#
# Two modes:
#   --fix [files...]  zero-judgment fixers (formatter + linter --fix) over the passed
#                     files only. The commit skill scopes these to the item's staged
#                     files — never a repo-wide sweep. Not a gate (always exits 0); the
#                     authoritative check is --check, re-run afterwards.
#   --check           the gate: format-check + lint + typecheck + test (whichever the
#                     stack defines), then the plan-coverage gates over EVERY open item's
#                     promises.json. Exits non-zero on any drift — used by the git
#                     pre-commit hook and by the commit skill after --fix.
#
# checks.env contract (all optional; empty/unset = skip that check):
#   FMT_FIX   formatter, write mode   — a command PREFIX; the staged file list is appended
#   LINT_FIX  linter, --fix mode      — a command PREFIX; the staged file list is appended
#   FMT_CHECK formatter, check mode   — runs repo-wide (carries its own path, e.g. `.`)
#   LINT      linter, check mode      — runs repo-wide
#   TYPECHECK typechecker             — runs repo-wide (omit for languages without one)
#   TEST      test runner             — runs repo-wide
# The coverage gates below are stack-AGNOSTIC (they read only .workflow/) and ship fixed
# in .claude/scripts/ — they are never part of checks.env.
set -uo pipefail

MODE="${1:-}"; shift 2>/dev/null || true
[ -n "$MODE" ] || { echo "usage: checks.sh --fix [files...] | --check" >&2; exit 2; }

# Per-project stack commands (data written by /start). Sourced, so it is trusted project
# config at the same level as this file — it is committed alongside it.
[ -f .workflow/checks.env ] && . .workflow/checks.env

SCRIPTS=".claude/scripts"
fail=0

case "$MODE" in
  --fix)
    # Fixers run only over the passed (staged) files, never repo-wide. FMT_FIX/LINT_FIX are
    # prefixes; `"$@"` appends the file list, each token quoted. Best-effort — --check gates.
    # Each runs in a SUBSHELL so a `cd`-ing command cannot leak its CWD into this runner.
    if [ "$#" -gt 0 ]; then
      [ -n "${FMT_FIX:-}" ]  && { echo "+ $FMT_FIX $*" >&2;  ( eval "$FMT_FIX \"\$@\"" )  || true; }
      [ -n "${LINT_FIX:-}" ] && { echo "+ $LINT_FIX $*" >&2; ( eval "$LINT_FIX \"\$@\"" ) || true; }
    fi
    exit 0
    ;;
  --check)
    # Fail-CLOSED stack-gate backstop: source under project_root with NO stack check wired is the
    # silent-defeat state. A greenfield stack locks in decision-engineer, but if nothing then fills
    # checks.env (the stack-wiring step at tech_stack lock), --check would run ONLY the coverage
    # gates and a failing test would wave through the commit. So: if no --check stack command is set
    # AND the product tree already holds source, block. The positive path (filling checks.env at
    # lock) makes the common case work; THIS makes forgetting it loud instead of silent. Skips
    # cleanly on the empty bootstrap tree (no source yet) and once checks.env is wired.
    if [ -z "${FMT_CHECK:-}${LINT:-}${TYPECHECK:-}${TEST:-}" ]; then
      proot="$(python3 -c 'import json; print(json.load(open(".workflow/config.json")).get("project_root") or ".")' 2>/dev/null || echo .)"
      if git ls-files -- "$proot" 2>/dev/null | grep -Eiq '\.(py|pyi|js|jsx|ts|tsx|mjs|cjs|go|java|cs|rb|rs|c|cc|cpp|cxx|h|hpp|hh|php|swift|kt|kts|scala|m|mm|clj|ex|exs|dart|lua|sh)$'; then
        echo "BLOCKED: source under '$proot' but .workflow/checks.env wires no stack gate" >&2
        echo "  (FMT_CHECK/LINT/TYPECHECK/TEST all unset). The stack must be wired when tech_stack" >&2
        echo "  locks: specialize rules + fill checks.env (the stack-wiring step — /start step 5)." >&2
        fail=1
      fi
    fi

    # Each stack command runs in a SUBSHELL. This is load-bearing, not tidiness: a natural
    # command like `cd project && pytest` would otherwise `cd` THIS shell, and the coverage-gate
    # loop below (paths relative to CWD) would then find zero items and SILENTLY skip every gate.
    [ -n "${FMT_CHECK:-}" ] && { echo "+ $FMT_CHECK" >&2; ( eval "$FMT_CHECK" ) || fail=1; }
    [ -n "${LINT:-}" ]      && { echo "+ $LINT" >&2;      ( eval "$LINT" )      || fail=1; }
    [ -n "${TYPECHECK:-}" ] && { echo "+ $TYPECHECK" >&2; ( eval "$TYPECHECK" ) || fail=1; }
    [ -n "${TEST:-}" ]      && { echo "+ $TEST" >&2;      ( eval "$TEST" )      || fail=1; }

    # Plan-coverage gates over every OPEN item (its dir is committed while open). Stack-
    # agnostic, shipped fixed. A missing promises.json means the planner has not written one
    # yet — skip it; a malformed one fails loudly (a broken manifest SHOULD block a commit).
    shopt -s nullglob
    for m in .workflow/items/*/promises.json; do
      echo "+ coverage gates: $m" >&2
      python3 "$SCRIPTS/check_promise_coverage.py"   "$m" || fail=1
      python3 "$SCRIPTS/check_criterion_discharge.py" "$m" || fail=1
      python3 "$SCRIPTS/check_decision_coverage.py"   "$m" || fail=1
    done

    exit "$fail"
    ;;
  *)
    echo "usage: checks.sh --fix [files...] | --check" >&2; exit 2
    ;;
esac

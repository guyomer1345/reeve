#!/usr/bin/env bash
# Fail if any shipped package file carries a spec-internal reference.
#
# The package states behaviour in plain language; decision IDs (Dxx), design-doc
# numbers, and "Space N" labels are provenance that lives ONLY in the numbered
# design docs + decision log — which point *down* to the file, never the reverse.
# Wire this at commit time (pre-commit hook / CI) so the rule can't silently regress.
#
# The "D-001" style decision-RECORD id (a product artifact, hyphenated) is allowed
# and does not match the Dxx pattern below.
set -uo pipefail

dirs=(skills agents shared commands templates hooks rules scripts/codemap scripts/retention.py scripts/check_promise_coverage.py scripts/test_check_promise_coverage.py scripts/check_criterion_discharge.py scripts/test_check_criterion_discharge.py scripts/check_decision_coverage.py scripts/test_check_decision_coverage.py scripts/check_contracts.py scripts/test_check_contracts.py)

# Dxx decision IDs · "Space N"/"Space-N" labels · backtick-wrapped design-doc numbers 00-11.
pattern='\bD[0-9]{1,2}\b|Space[ -][0-9]|`0[0-9]`|`1[01]`'

hits="$(grep -rnE "$pattern" "${dirs[@]}" 2>/dev/null || true)"
if [ -n "$hits" ]; then
  echo "BLOCKED: spec-internal references found in the shipped package (see shared/format.md):" >&2
  printf '%s\n' "$hits" >&2
  exit 1
fi
echo "OK: no spec-internal references in ${dirs[*]}"

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

dirs=(skills agents shared commands templates hooks rules scripts/codemap scripts/retention.py scripts/check_promise_coverage.py scripts/test_check_promise_coverage.py scripts/check_criterion_discharge.py scripts/test_check_criterion_discharge.py scripts/check_decision_coverage.py scripts/test_check_decision_coverage.py scripts/check_contracts.py scripts/test_check_contracts.py scripts/bus.py scripts/test_bus.py scripts/drain.py scripts/test_drain.py scripts/loop.sh)

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# The design-doc slugs are DERIVED from the docs that actually exist, never listed
# here: a hand-kept copy is a second owner that goes stale the day a doc is added
# or renamed (the drift class D114 exists to stop). Add `12-foo.md` and this gate
# covers it on the next run, with no edit.
slugs="$(ls "$root" | grep -oE '^[0-9]{2}-[a-z0-9-]+\.md$' | sed 's/\.md$//' | paste -sd'|' -)"
if [ -z "$slugs" ]; then
  echo "BLOCKED: no NN-slug design docs found in $root — the gate's own anchor moved," >&2
  echo "         and an empty alternation would silently match everything." >&2
  exit 1
fi

# Dxx decision IDs (1-3 digits — the log crossed D100) · "Space N"/"Space-N" labels · backtick-wrapped
# design-doc numbers 00-11. The hyphenated "D-001" decision-RECORD id still won't match (hyphen breaks \b).
pattern='\bD[0-9]{1,3}\b|Space[ -][0-9]|`0[0-9]`|`1[01]`'
# Prose doc-slug references ("see 08-decision-log.md", "07-open-questions") — the
# most natural way a leak actually gets written, and invisible to the backtick
# patterns above. `.md` optional; the leading \b keeps `0600-honouring` clean
# (a slug needs a letter after the hyphen, so dates/modes can't match).
pattern="${pattern}|\\b(${slugs})(\\.md)?\\b"

hits="$(grep -rnE "$pattern" "${dirs[@]}" 2>/dev/null || true)"
if [ -n "$hits" ]; then
  echo "BLOCKED: spec-internal references found in the shipped package (see shared/format.md):" >&2
  printf '%s\n' "$hits" >&2
  exit 1
fi
echo "OK: no spec-internal references in ${dirs[*]}"

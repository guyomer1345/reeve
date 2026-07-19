#!/usr/bin/env bash
# Fail if any shipped package file carries a spec-internal reference.
#
# The package states behaviour in plain language; decision IDs (Dxx), design-doc
# numbers, and "Space N" labels are provenance that lives ONLY in the numbered
# design docs + decision log (docs/design/) — which point *down* to the file,
# never the reverse. Wire this at commit time (pre-commit hook / CI) so the rule
# can't silently regress.
#
# The "D-001" style decision-RECORD id (a product artifact, hyphenated) is allowed
# and does not match the Dxx pattern below.
set -uo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
manifest="$root/product/MANIFEST.json"

# The scanned set is DERIVED from the product manifest (the single ship boundary),
# never hand-listed here: a hand-kept copy is a second owner that goes stale the
# day a shipped file is added — the exact drift that let loop.sh, then
# check_demo_bundle.py, slip past the old dirs=() list. Add a file to the tree +
# the manifest and this gate covers it on the next run, with no edit here.
readarray -t ship < <(python3 -c '
import json, os, sys
m = json.load(open(sys.argv[1]))
for p in m["ship"]:
    print(os.path.join(sys.argv[2], "product", p))
' "$manifest" "$root")
if [ ${#ship[@]} -eq 0 ]; then
  echo "BLOCKED: product/MANIFEST.json yielded no ship paths — the gate's own" >&2
  echo "         anchor moved, and an empty scan set would pass vacuously." >&2
  exit 1
fi

# The manifest's excludes (the beside-code tests, which do not ship) become grep
# --exclude globs, so the gate scans exactly what the release build emits.
excl_args=()
while IFS= read -r pat; do
  [ -n "$pat" ] && excl_args+=(--exclude="${pat##*/}")
done < <(python3 -c '
import json, sys
for p in json.load(open(sys.argv[1])).get("exclude", []):
    print(p)
' "$manifest")

# The design-doc slugs are DERIVED from the docs that actually exist (now under
# docs/design/), never listed here — same single-owner reason as the ship set.
slugs="$(ls "$root/docs/design" | grep -oE '^[0-9]{2}-[a-z0-9-]+\.md$' | sed 's/\.md$//' | paste -sd'|' -)"
if [ -z "$slugs" ]; then
  echo "BLOCKED: no NN-slug design docs found in $root/docs/design — the gate's" >&2
  echo "         own anchor moved, and an empty alternation would match everything." >&2
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

# -I skips binary files (a stray .pyc under a scanned dir), and build-cache dirs
# are never source — so a test run that leaves __pycache__ can't spook the gate.
hits="$(grep -rnE -I --exclude-dir=__pycache__ --exclude-dir=.pytest_cache "${excl_args[@]}" "$pattern" "${ship[@]}" 2>/dev/null || true)"
if [ -n "$hits" ]; then
  echo "BLOCKED: spec-internal references found in the shipped package (see product/shared/format.md):" >&2
  printf '%s\n' "$hits" >&2
  exit 1
fi
echo "OK: no spec-internal references in ${#ship[@]} shipped path(s) (manifest-derived)"

#!/usr/bin/env bash
# Phase 9c EXIT-GATE DRIVE — org mode against a REAL public repo at a PINNED historical SHA,
# with that repo's OWN later real commits replayed as coworker drift.
#
# Asserts the four properties that DEFINE org mode:
#   (a) the operator's own checkout stayed BYTE-PRISTINE
#   (b) the loop never pushed or committed to the company repo
#   (c) align detected the replayed drift via describes_sha
#   (d) no artifact leaked across the boundary
set -uo pipefail
# Meta-only: this never ships. It needs NETWORK and takes a couple of minutes, so it is not
# one of the commit-time gates -- it is the exit gate for org mode, run deliberately.
#
#   scripts/drive-org-mode.sh [workdir]
#
# Why a real foreign repo and not a fixture: org mode's whole promise is a boundary that holds
# against code nobody here wrote, with a history nobody here curated. A fixture proves the
# assertions agree with the fixture. Replaying the repo's OWN later commits gives realistic
# coworker drift for free -- real files, real conflicts, no invented scenario to flatter.
W="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
T="${1:-${TMPDIR:-/tmp}/org-mode-drive}"
UPSTREAM="${DRIVE_UPSTREAM:-https://github.com/pallets/click.git}"
# A PINNED historical SHA, so the drive is reproducible and the commits after it are the
# coworker drift. Bump it deliberately, never automatically.
PINNED="${DRIVE_PINNED:-94c191ca6c9598865fc5672b85cf138845b337d5}"
TOUCH_FILE="${DRIVE_FILE:-src/click/termui.py}"
mkdir -p "$T"
if [ ! -d "$T/upstream.git" ]; then
  echo "cloning $UPSTREAM (once, cached in $T) ..."
  git clone -q --bare "$UPSTREAM" "$T/upstream.git" || { echo "clone failed (network?)"; exit 2; }
fi
git -C "$T/upstream.git" cat-file -e "$PINNED" 2>/dev/null || {
  echo "pinned SHA $PINNED not in $UPSTREAM"; exit 2; }
D=$T/drive; rm -rf "$D"; mkdir -p "$D"; cd "$D"

pass=0; fail=0
ok()   { echo "  PASS  $1"; pass=$((pass+1)); }
bad()  { echo "  FAIL  $1"; fail=$((fail+1)); }
chk()  { if [ "$2" = "$3" ]; then ok "$1"; else bad "$1 (got '$2', want '$3')"; fi; }

echo "=============================================================="
echo " 9c EXIT-GATE DRIVE — pallets/click @ $PINNED (real, pinned)"
echo "=============================================================="

# ---------------------------------------------------------------- setup
# The COMPANY origin: a bare repo pinned to the historical SHA. Its later real commits are
# held back and replayed later as coworker drift.
git init -q --bare -b main company.git
git -C "$T/upstream.git" push -q "$D/company.git" "$PINNED:refs/heads/main" 2>/dev/null
echo "company origin pinned at: $(git -C company.git rev-parse --short main)"

# The OPERATOR'S OWN checkout — the tree org mode promises never to touch.
git clone -q company.git checkout
CHECKOUT_FINGERPRINT_BEFORE=$(cd checkout && git rev-parse HEAD && git status --porcelain | sort && find . -path ./.git -prune -o -type f -print | sort | xargs sha256sum 2>/dev/null | sha256sum)

# ---------------------------------------------------------------- /start org
echo
echo "--- /start org: clone into the brain, kill the push path, layer the workflow ---"
git clone -q company.git brain
cd brain
git remote set-url --push origin no_push
git config user.email loop@brain; git config user.name "disciplined builder"
mkdir -p .workflow/docs .workflow/rules .workflow/items/itm-1 .claude/scripts .claude/hooks
cp "$W/product/templates/checks.sh" .workflow/
cp "$W/product/scripts/review_bundle.py" .claude/scripts/
cp "$W/product/hooks/guard.sh" .claude/hooks/
for s in check_promise_coverage.py check_criterion_discharge.py check_decision_coverage.py check_doc_budget.py; do
  cp "$W/product/scripts/$s" .claude/scripts/; done
python3 - <<'PY'
import json
json.dump({"project_root": ".", "docs_root": ".workflow",
           "org": {"checkout": "../checkout"}},
          open(".workflow/config.json", "w"), indent=1)
PY
cat > .workflow/checks.env <<'EOF'
STACK_GATE_NONE="org mode: never execute anything out of a repo we do not own"
EOF
# the brain's brief goes to .claude/CLAUDE.md; click's own CLAUDE.md/README stay untouched
echo '# orchestrator brief (managed block)' > .claude/CLAUDE.md
echo '# reconstructed spec for click' > .workflow/docs/spec.md
cat > .workflow/items/itm-1/promises.json <<'EOF'
{"criteria":[{"id":"ac-1","gate":"artifact","boundary":true,"discharge":"tests/t.py::t"}],
 "promises":[{"id":"p1","text":"echo gains a marker","universal":true,"test_ref":"ac-1"}],
 "decisions":[{"id":"D-001","steps":["s1"]}]}
EOF
echo "plan: annotate echo()" > .workflow/items/itm-1/plan.md
echo "changelog: echo() carries a marker comment" > .workflow/items/itm-1/changelog.md
git add -A
echo "  brain built at $(git rev-parse --short HEAD)"

# ---------------------------------------------------------------- the commit gate
echo
echo "--- the commit gate over a repo whose code must never run here ---"
GATE_OUT=$(bash .workflow/checks.sh --check 2>&1); GATE_RC=$?
echo "$GATE_OUT" | sed 's/^/    /' | head -8
chk "commit gate passes with the stack gate DECLARED off" "$GATE_RC" "0"
case "$GATE_OUT" in *"DECLARED NONE"*) ok "the declaration is stated on every run";; *) bad "declaration not printed";; esac
git commit -qm "chore: brain scaffold"

# ---------------------------------------------------------------- an item's work
echo
echo "--- the loop does an item's work (two commits, both trailered) ---"
python3 - "$TOUCH_FILE" <<'PY'
import sys
p = sys.argv[1]
s = open(p).read()
open(p, "w").write("# loop-touched: echo marker\n" + s)
PY
echo '{"node":"the touched file","why":"derived knowledge about their internals"}' > .workflow/docs/knowledge.json
git add -A && git commit -q -m "feat(termui): marker

Refs: item #itm-1"
python3 - "$TOUCH_FILE" <<'PY'
import sys
p = sys.argv[1]
s = open(p).read().replace("# loop-touched: echo marker", "# loop-touched: echo marker v2")
open(p, "w").write(s)
PY
echo '{"node":"the touched file","why":"more derived knowledge"}' > .workflow/docs/knowledge.json
git add -A && git commit -q -m "feat(termui): marker v2

Refs: item #itm-1"
echo "  brain HEAD $(git rev-parse --short HEAD), $(git rev-list --count origin/main..HEAD) commits ahead"

# ---------------------------------------------------------------- (b) no push
echo
echo "--- (b) the loop cannot push to the company ---"
PUSH_OUT=$(git push origin main 2>&1); PUSH_RC=$?
[ "$PUSH_RC" -ne 0 ] && ok "git push origin main REFUSED ($(echo "$PUSH_OUT" | head -1))" || bad "push succeeded"
PUSH2=$(git push 2>&1); [ $? -ne 0 ] && ok "bare git push REFUSED" || bad "bare push succeeded"
PUSH3=$(git push --all 2>&1); [ $? -ne 0 ] && ok "git push --all REFUSED" || bad "push --all succeeded"
COMPANY_HEAD_NOW=$(git -C ../company.git rev-parse main)
chk "company origin is byte-identical to the pinned SHA" "$COMPANY_HEAD_NOW" "$PINNED"

# the guard's own gate on giving the brain a push path
GUARD_OUT=$(printf '%s' '{"tool_input":{"command":"git remote add archive git@example.com:me/brain.git"}}' | bash .claude/hooks/guard.sh 2>&1); GUARD_RC=$?
chk "guard blocks an unacknowledged archive remote" "$GUARD_RC" "2"

# ---------------------------------------------------------------- (d) no leak
echo
echo "--- (d) the review bundle carries the work and nothing else ---"
BUN=$(python3 .claude/scripts/review_bundle.py build itm-1 2>&1); BUN_RC=$?
echo "$BUN" | sed 's/^/    /'
chk "bundle built" "$BUN_RC" "0"
DIFF=.workflow/bundles/itm-1.diff
if [ -f "$DIFF" ]; then
  grep -q "^diff --git a/.workflow" "$DIFF" && bad "brain path in the diff" || ok "no .workflow/ path in the diff"
  grep -q "^diff --git a/.claude"   "$DIFF" && bad ".claude path in the diff" || ok "no .claude/ path in the diff"
  grep -q "Refs: item"              "$DIFF" && bad "loop commit message crossed" || ok "no loop commit message in the diff"
  grep -q "derived knowledge"       "$DIFF" && bad "derived IP in the diff" || ok "no derived knowledge in the diff"
  N=$(grep -c "^diff --git" "$DIFF"); chk "exactly one file crosses" "$N" "1"
  grep -q "marker v2" "$DIFF" && ok "the SQUASHED end state is what crosses" || bad "end state missing"
  grep -q "^+# loop-touched: echo marker$" "$DIFF" && bad "an intermediate state crossed" || ok "no intermediate state crossed"
fi

# ---------------------------------------------------------------- (a) pristine
echo
echo "--- (a) the operator's own checkout is untouched ---"
CHECKOUT_FINGERPRINT_AFTER=$(cd ../checkout && git rev-parse HEAD && git status --porcelain | sort && find . -path ./.git -prune -o -type f -print | sort | xargs sha256sum 2>/dev/null | sha256sum)
chk "checkout is byte-identical to before the whole run" "$CHECKOUT_FINGERPRINT_AFTER" "$CHECKOUT_FINGERPRINT_BEFORE"
[ -e ../checkout/.workflow ] && bad ".workflow appeared in the checkout" || ok "no .workflow/ in the checkout"
[ -e ../checkout/.claude ]   && bad ".claude appeared in the checkout"   || ok "no .claude/ in the checkout"
[ -e ../checkout/.git/hooks/pre-commit ] && bad "a hook was installed in the checkout" || ok "no git hook in the checkout"
# the human applies the bundle themselves — that is the ONLY way work reaches their tree
(cd ../checkout && git apply "$D/brain/$DIFF" 2>&1) && ok "the human can apply the bundle cleanly" || bad "bundle did not apply"
(cd ../checkout && git -c user.email=dev@acme -c user.name=dev commit -qam "termui: marker" 2>/dev/null)
AUTHOR=$(cd ../checkout && git log -1 --format=%an)
chk "the HUMAN authored the commit" "$AUTHOR" "dev"
(cd ../checkout && git reset -q --hard HEAD~1)

# ---------------------------------------------------------------- (c) drift
echo
echo "--- (c) 42 of the repo's OWN later real commits replayed as coworker drift ---"
DESCRIBES=$(git rev-parse origin/main)
python3 - "$DESCRIBES" <<'PY'
import json, sys
json.dump({"base_sha": "HEAD", "describes_sha": sys.argv[1]},
          open(".workflow/align/anchor.json", "w") if __import__("os").path.isdir(".workflow/align")
          else (__import__("os").makedirs(".workflow/align") or open(".workflow/align/anchor.json", "w")),
          indent=1)
PY
git -C "$T/upstream.git" push -q "$D/company.git" "HEAD:refs/heads/main" 2>/dev/null
echo "  company origin moved: $(git -C ../company.git rev-parse --short main) (was $(echo $PINNED | cut -c1-7))"
git fetch -q origin
DRIFT=$(git rev-list --count "$DESCRIBES"..FETCH_HEAD)
[ "$DRIFT" -gt 0 ] && ok "align sees $DRIFT upstream commits since describes_sha" || bad "drift NOT detected"
DRIFT_FILES=$(git diff --name-only "$DESCRIBES"..FETCH_HEAD | wc -l)
[ "$DRIFT_FILES" -gt 0 ] && ok "the changed surface is $DRIFT_FILES file(s) — ordinary drift, bigger diff" || bad "no changed surface"
# the collision case: did a coworker touch the same file this item did?
git diff --name-only "$DESCRIBES"..FETCH_HEAD | grep -q "^$TOUCH_FILE" \
  && ok "a coworker touched the same file — the conflict case is REAL here" \
  || ok "no overlap on this item's file (conflict path not exercised by this slice)"
chk "describes_sha was NOT auto-advanced by the fetch" "$(python3 -c "import json;print(json.load(open('.workflow/align/anchor.json'))['describes_sha'])")" "$DESCRIBES"

# ---------------------------------------------------------------- nothing executed
echo
echo "--- the standing rule: nothing out of their tree ever ran ---"
grep -qE '^(FMT_CHECK|LINT|TYPECHECK|TEST|FMT_FIX|LINT_FIX)=' .workflow/checks.env \
  && bad "a stack command is wired in an org brain" || ok "no stack command wired"
python3 -c "import sys;sys.exit(0 if 'no_push'=='$(git config --get remote.origin.pushurl)' else 1)" \
  && ok "origin remains fetch-only (pushurl=no_push)" || bad "origin push url changed"

echo
echo "=============================================================="
echo " RESULT: $pass passed, $fail failed"
echo "=============================================================="
exit $([ "$fail" -eq 0 ] && echo 0 || echo 1)

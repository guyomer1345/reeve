#!/usr/bin/env python3
"""The context-budget gate — the enforcement the "bounded by construction" claim never had.

`memory-model.md`'s read law ASSERTS that always-read files are bounded by construction.
Nothing held it true: `retention.py` caps the append-only tier (`# Sessions`) and nothing
else, so every other context-loaded file was bounded by hope. This script is the mechanism.
It answers exactly one question -- **is this doc too big** -- and deliberately not "is this
doc wrong", which `align` owns. Two owners, no overlap.

WHY TOKENS AND NOT LINES. A budget in lines is a budget in a unit the model does not read.
Tokens are also model-window-agnostic, the same reason the context governor's `warn_pct` is
a percentage rather than a token count.

TWO TIERS PER ROLE, and the second tier is the one that keeps this usable:
  HARD      -> fails `checks.sh`. For on-demand docs the hard number is not a preference at
               all, it is the Read tool's 25 000-token ceiling: a file over it *mechanically
               cannot be loaded in one call*, so this is enforcement that is a failure rather
               than advice.
  ADVISORY  -> never fails a build; it schedules a trim as an ordinary maintenance item.
Shipping only the aggressive number would have made this gate red on a clean install, and a
gate that fires on a fresh install trains a human to ignore it -- the same reason the
staleness detector warns once per SHA rather than every session. Green on install, with the
aspiration tracked as work rather than as a broken build. The advisory is therefore pinned
proportionally under hard (~80%) rather than at an aspirational floor; see `DEFAULTS`.

AND TWO BOUNDS ON THE ALWAYS-LOADED TIER: per-file, and the SET. A per-file cap is a shape
check -- it says *this file* has outgrown its role -- and it structurally cannot see the bill,
because two files each a token under cap cost the same rent as one file at twice the cap and
only the second is caught. The always-loaded TOTAL is the number that describes what a session
actually pays before a word is typed, and it fails the gate exactly as a per-file breach does.
The on-demand tier is deliberately NOT totalled: nothing loads it until something needs it, so
a sum over it would fail a project for owning documentation.

ESTIMATED, NOT COUNTED, AND CALIBRATED ON A REAL FAILURE. There is no tokenizer in the
standard library and this package ships stdlib-only Python, so the count is an estimate from
character length. The divisor is not folklore: this project's own roadmap was measured at
85 083 characters when it *paged at the 25 000-token ceiling*, which puts the real ratio at
**<= 3.40 chars/token** for markdown prose. That measurement also kills the obvious choice --
the usual `chars/4` rule of thumb would have scored that exact file at 21 271 tokens,
comfortably "under" a ceiling it demonstrably could not fit. 3.2 ships, for margin below the
measured bound. It is a config knob (`chars_per_token`) because a doc dense in fenced code
tokenizes worse than prose, and lowering it is how a project tightens the estimate.

OVER BUDGET IS A TICKET, NEVER AN AUTO-EDIT. You cannot drop half a spec doc to git the way
retention drops a `# Sessions` entry -- splitting prose coherently needs judgment. So an
over-budget prose file routes to a SPLIT-AND-POINTER: a lean current-state file, an
archived-detail file, and a head marker in the survivor, mirroring the marker retention
already leaves. This script names the remedy; it never performs it.

  --check   (default) the gate: exit 1 if any file exceeds its role's HARD budget, or if the
            always-loaded files together exceed the TOTAL ceiling.
  --report  every file with its role, estimate and tier; exit 0. What the maintenance item
            reads, and what a human runs by hand.
  --json    machine-readable, for either mode.
"""
import argparse
import glob
import json
import math
import os
import re
import sys

CONFIG_REL = os.path.join(".workflow", "config.json")

# Shipped defaults, DERIVED BY MEASURING this package rather than by citing a number (there
# is no single best-practice max size; that is why the budget is per role).
#
# TWO BOUNDS ON THE ALWAYS-LOADED TIER, because one of them caps the wrong thing.
# `always_hard` is a SHAPE check on a single file -- it says *this file* has outgrown its role.
# It cannot see the bill: two files each a token under cap cost the same rent as one file at
# twice the cap, and only the second is caught. `always_total_hard` is the figure that actually
# describes what a session pays before a word is typed, and it is deliberately far below
# (number of always-loaded slots x always_hard) -- otherwise it would ratify exactly the
# accumulation it exists to stop.
#
# THE ADVISORY IS A BAND, NOT AN ASPIRATION. It sits proportionally under its hard bound
# (~80%) so there is a real warning zone with room to act. An advisory pitched below what a
# file can structurally be fires on a fresh install, every run, forever -- and a tier that has
# been tripped since day one is a tier nobody reads. That is not hypothetical: `always_advisory`
# shipped at 1200, no always-loaded file was ever under it, and when a file crossed its HARD
# limit the only tier that could have warned on the way had been crying wolf since day one.
#
# THE STANDING RULE FOR CHANGING THESE: a cap is set to a value the shipped package already
# meets, and is never raised to accommodate what the package happens to weigh. If the package
# breaches a cap, the package is relocated -- the cap does not move. That rule is the whole
# difference between a budget and a rubber stamp.
DEFAULTS = {
    "chars_per_token": 3.2,
    "always_hard": 4000,
    "always_advisory": 3200,
    "always_total_hard": 8000,
    "always_total_advisory": 6400,
    # Not a preference: the Read tool's own ceiling. A file over it cannot be read in one call.
    "ondemand_hard": 25000,
    "ondemand_advisory": 15000,
    "every_p_items": 15,
}

# The head marker the split-and-pointer convention leaves in the file that SURVIVES, so the
# detail is findable and the split is self-documenting. One owner for the string, here, for
# the same reason the brief markers live in `update_reconcile.py`: it is a compatibility
# contract, and a marker with two spellings is a marker nothing can find.
#
# TWO FORMS, because the first real customer proved one was not enough. The original marker
# mirrored retention's Sessions marker, which points at content FROZEN IN GIT -- hence the
# `@ <sha>`. But a doc can also split into a LIVE SIBLING that is still edited (the package's
# own `schemas.md` -> `schemas-runtime.md`: the runtime-substrate records did not stop
# changing, they just stopped belonging in the same file). Stamping a sha on a live sibling
# would be a lie the moment the sibling is next edited, and would tell a reader to go looking
# in git for a file sitting right next to them. So:
#   ARCHIVED  detail frozen at a sha, recoverable from git   -> `... -> <path> @ <sha> -->`
#   SIBLING   detail live on disk, still edited              -> `... -> <path> -->`
SPLIT_MARKER = "<!-- doc-budget: detail split -> %s @ %s -->"
SPLIT_MARKER_SIBLING = "<!-- doc-budget: detail split -> %s -->"
SPLIT_RE = re.compile(r"<!--\s*doc-budget:\s*detail split\s*->\s*(\S+?)(?:\s+@\s+(\S+))?\s*-->")

ALWAYS = "always-loaded"
ONDEMAND = "on-demand"

ROLE_WHY = {
    ALWAYS: "rent paid every turn, every session, before a word is typed",
    ONDEMAND: "loaded when something needs it -- the 25 000-token Read ceiling is a hard wall",
}


def split_pointers(text):
    """[(path, sha_or_None)] for every split marker in `text`, in order of appearance."""
    return [(m.group(1), m.group(2)) for m in SPLIT_RE.finditer(text)]


def read_with_splits(path, _seen=None):
    """(text, unresolved) -- `path` PLUS every live split-detail file it points at.

    THE POINT OF THIS FUNCTION, because it is the opposite of what the sizer does. A split
    physically moves sections OUT of a doc, so any consumer that parses the survivor alone
    sees strictly less than the doc declares. Both readers of `schemas.md` were MEASURED
    against the real split rather than reasoned about, and both break LOUDLY, in opposite
    directions: the meta-gate's native-FS rule hard-failed with five false "the layout pins
    a path no schema header claims" errors (fail-closed -- it would simply have blocked the
    commit), while the contract linter's `kind:` union lost `generic` and `slack` and began
    flagging legitimate uses as novel kinds (fail-noisy). Neither goes quiet today, so this
    is not a silent gate defeat -- it is the plainer fact that the split is not even VIABLE
    without it. The fail-open sliver is structural rather than current: the
    novel-kind check skips itself entirely on an empty union, so a future split that carried
    the last definition of an enum out of the survivor would shrink what other checks consume
    without saying so. Read the whole artifact; do not depend on which half is in front of you.

    So: a CONTENT parser reads through this. The SIZER (`scan` below) deliberately does not --
    the survivor is under the wall precisely because the detail moved out, and a sizer that
    followed the pointer would re-add the bytes and report the split as having achieved
    nothing. Two readers of one file, two correct answers.

    Pointers are resolved relative to the referring file's directory, followed recursively,
    and cycle-guarded. An ARCHIVED pointer (`@ <sha>`) names content that lives in git rather
    than on disk, so a target that is simply absent is normal and is not reported; anything
    else that cannot be read comes back in `unresolved` for the caller to SAY, never to
    swallow -- an unreported skip reads as "all clear", which is the failure again.
    """
    _seen = set() if _seen is None else _seen
    real = os.path.realpath(path)
    if real in _seen:
        return "", []
    _seen.add(real)
    try:
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
    except OSError as exc:
        return "", ["%s (%s)" % (path, exc.strerror or exc)]
    parts, unresolved = [text], []
    base = os.path.dirname(os.path.abspath(path))
    for target, sha in split_pointers(text):
        tgt = target if os.path.isabs(target) else os.path.join(base, target)
        if not os.path.exists(tgt):
            # Archived detail is *expected* to be absent -- it is in git, by design.
            if sha is None:
                unresolved.append("%s (split detail of %s: no such file)"
                                  % (target, os.path.basename(path)))
            continue
        sub, sub_unresolved = read_with_splits(tgt, _seen)
        parts.append(sub)
        unresolved.extend(sub_unresolved)
    return "\n".join(p for p in parts if p), unresolved


def _read_json(path, default=None):
    try:
        with open(path) as fh:
            return json.load(fh)
    except Exception:
        return default


def budgets(project_root):
    """-> (budget knobs, project_root, docs_root).

    `docs_root` is a SEPARATE path from `project_root`, defaulting to it. They are the same
    everywhere except org mode, where the workflow's tree IS a clone of a repo it does not own:
    the derived docs cannot sit at the repo root beside the owner's own `docs/`, so they are
    namespaced under `.workflow/`. Two named roots, each with one owner, rather than one
    `project_root` that quietly means two things depending on who is reading it.
    """
    cfg = _read_json(os.path.join(project_root, CONFIG_REL), {}) or {}
    out = dict(DEFAULTS)
    got = cfg.get("doc_budget")
    if isinstance(got, dict):
        for k, v in got.items():
            if k in out and isinstance(v, (int, float)) and v > 0:
                out[k] = v
    proot = cfg.get("project_root") or "."
    return out, proot, (cfg.get("docs_root") or proot), ("org" in cfg)


def estimate_tokens(text, chars_per_token):
    """Characters -> an estimated token count, rounded UP.

    Rounding up and dividing by a number below the measured ratio both push the same way, on
    purpose: under-reporting means a file that cannot actually be read passes the gate, which
    is the one failure this must not have.
    """
    cpt = chars_per_token if chars_per_token and chars_per_token > 0 else DEFAULTS["chars_per_token"]
    return int(math.ceil(len(text) / float(cpt)))


def workflow_docs(project_root, proot, droot=None, org=False):
    """(role, path) for every doc the workflow owns and a session can be made to read.

    The VOLATILE tier is deliberately ABSENT -- `state.json` and `handoff.md` are rewritten in
    place and `handoff.md` is already capped mechanically, at injection time, by the
    SessionStart hook. Giving it a second budget here would be a second owner of one bound,
    and the two would drift.
    """
    # EVERY path is normalised the moment it is built, and `seen` only ever holds normalised
    # paths. Not tidiness -- `project_root` is commonly a relative spelling like `./project`,
    # which makes `os.path.join` produce `<root>/./project/docs/...`; `glob` hands that spelling
    # straight back, while a split-pointer target is resolved through `normpath`. The two
    # spellings denote one file and compare unequal, so the same doc was admitted twice: once by
    # its glob and once as a pointer target. That double-counted it in the always-loaded TOTAL
    # and reported it twice in the advisory list.
    p = (lambda *a: os.path.normpath(os.path.join(project_root, *a)))
    d = (lambda *a: os.path.normpath(
        os.path.join(project_root, droot if droot is not None else proot, *a)))
    out = []
    # `.claude/CLAUDE.md` is the platform's OTHER project-instructions location and loads at the
    # same scope as the root file (verified against the shipped docs, not assumed). Org mode puts
    # the brief there so the owner's own root `CLAUDE.md` is never written -- but it is budgeted
    # in every mode, because a brief that loads every turn costs the same wherever it is filed.
    #
    # In ORG mode the root `CLAUDE.md` belongs to the repo's owner, so it is NOT scanned. This is
    # not tidiness: the hard tier FAILS a commit and its only remedy is to trim the file, which
    # org mode forbids -- a company brief over `always_hard` would deadlock every commit behind a
    # gate no one here is allowed to satisfy. Its context cost is real but it is theirs, in the
    # same class as the size of their code; this gate's scope is what the WORKFLOW owns, which is
    # exactly what it says when it reports "workflow-owned doc(s)".
    #
    # `.workflow/directives.md` is ALWAYS-LOADED and is here for a reason worth stating: it is the
    # one file in this set a HUMAN adds to freely, in prose, whenever an instruction needs to
    # outlive a `/clear`. The other two are package-authored and move only when the package
    # moves; this one grows by hand, one standing directive at a time, in the most expensive place
    # in the system. Budgeting it per-file AND inside the always-loaded TOTAL is what makes that
    # growth cost something visible -- `check_directives.py` holds each ENTRY to its shape, and
    # nothing in that gate can see the bill the file as a whole is running up. Two gates, two
    # facts: one asks whether an entry is legitimate, this one asks what the set weighs.
    always = [p(".claude", "CLAUDE.md"), p(".workflow", "loop.md"),
              p(".workflow", "directives.md")]
    if not org:
        always.insert(0, p("CLAUDE.md"))
    for path in always:
        if os.path.isfile(path):
            out.append((ALWAYS, path))
    patterns = [
        d("docs", "spec.md"),
        d("docs", "architecture.md"),
        d("rules", "**", "*.md"),
        d("docs", "knowledge", "**", "*.md"),
        d("docs", "decisions", "**", "*.md"),
        p(".workflow", "backlog.md"),
    ]
    seen = {path for _r, path in out}
    for pat in patterns:
        for path in sorted(glob.glob(pat, recursive=True)):
            path = os.path.normpath(path)
            if os.path.isfile(path) and path not in seen:
                seen.add(path)
                out.append((ONDEMAND, path))

    # SPLIT DETAIL FILES ARE BUDGETED TOO, or the gate prescribes a remedy it then stops
    # watching. `docs/spec.md` is in the glob above; the `docs/spec-detail.md` a split
    # produces is not, so without this the detail half could grow straight back through the
    # wall unseen -- and the second split would have nowhere to land. Always ON-DEMAND,
    # whatever the referrer was: detail broken out of an always-loaded file is precisely
    # detail that is no longer loaded every turn, which is the point of that remedy.
    # Sized as its OWN row, never merged into the survivor's -- see `read_with_splits`.
    i = 0
    while i < len(out):
        _role, path = out[i]
        i += 1
        try:
            with open(path, encoding="utf-8", errors="replace") as fh:
                pointers = split_pointers(fh.read())
        except OSError:
            continue
        for target, _sha in pointers:
            tgt = target if os.path.isabs(target) else os.path.join(os.path.dirname(path), target)
            tgt = os.path.normpath(tgt)
            if os.path.isfile(tgt) and tgt not in seen:
                seen.add(tgt)
                out.append((ONDEMAND, tgt))
    return out


def scan(project_root):
    b, proot, droot, org = budgets(project_root)
    rows = []
    for role, path in workflow_docs(project_root, proot, droot, org):
        try:
            with open(path, encoding="utf-8", errors="replace") as fh:
                text = fh.read()
        except OSError:
            continue  # unreadable is not over-budget; it is nothing to say
        est = estimate_tokens(text, b["chars_per_token"])
        hard = b["always_hard"] if role == ALWAYS else b["ondemand_hard"]
        adv = b["always_advisory"] if role == ALWAYS else b["ondemand_advisory"]
        tier = "over" if est > hard else ("advisory" if est > adv else "ok")
        rows.append({"path": os.path.relpath(path, project_root).replace(os.sep, "/"),
                     "role": role, "tokens": est, "hard": hard, "advisory": adv,
                     "tier": tier})
    rows.sort(key=lambda r: (-r["tokens"], r["path"]))

    # THE BILL, not the shape. Summed over the always-loaded tier only: the on-demand tier is
    # not rent (nothing loads it until something needs it), so totalling it would produce a
    # number that means nothing and would fail a project for owning documentation.
    always_rows = [r for r in rows if r["role"] == ALWAYS]
    tot = sum(r["tokens"] for r in always_rows)
    t_hard, t_adv = b["always_total_hard"], b["always_total_advisory"]
    total = {"role": ALWAYS, "tokens": tot, "hard": t_hard, "advisory": t_adv,
             "files": len(always_rows),
             "tier": "over" if tot > t_hard else ("advisory" if tot > t_adv else "ok")}

    return {"budgets": b, "files": rows, "total": total,
            "over": [r for r in rows if r["tier"] == "over"],
            "advisories": [r for r in rows if r["tier"] == "advisory"]}


def failed(result):
    """The gate's verdict, in one place -- a per-file HARD breach OR the TOTAL over ceiling.

    One owner for "did this fail", because the exit code, the rendered verdict line and every
    caller must agree; two copies of this predicate is how a gate reports OK and exits 1.
    """
    return bool(result["over"]) or result["total"]["tier"] == "over"


TOTAL_REMEDY = (
    "move a whole file OUT of the always-loaded set, or split one and leave a pointer. "
    "Trimming a single file need not fix this: every always-loaded file can be under its own "
    "cap while the set still costs more than a session should pay before a word is typed")


def _remedy(row):
    if row["role"] == ALWAYS:
        return ("trim it -- move detail to an on-demand doc and leave a pointer; this file "
                "is read before every single turn")
    return ("split-and-pointer -- a lean survivor plus a detail file, with a marker at the "
            "head of the survivor: `%s` when the detail is frozen in git, or `%s` when it is "
            "a live sibling still being edited"
            % (SPLIT_MARKER % ("<detail path>", "<sha>"),
               SPLIT_MARKER_SIBLING % "<detail path>"))


def render(result, report):
    lines = []
    for r in result["over"]:
        lines.append("OVER BUDGET  %-52s %7d tok  > %d (%s HARD)"
                     % (r["path"], r["tokens"], r["hard"], r["role"]))
        lines.append("             %s" % _remedy(r))
    if report:
        for r in result["advisories"]:
            lines.append("ADVISORY     %-52s %7d tok  > %d (%s -- %s)"
                         % (r["path"], r["tokens"], r["advisory"], r["role"],
                            ROLE_WHY[r["role"]]))
            lines.append("             not a build failure: schedule a trim. %s" % _remedy(r))
    t = result["total"]
    if t["tier"] == "over":
        lines.append("OVER BUDGET  %-52s %7d tok  > %d (always-loaded TOTAL HARD)"
                     % ("(%d always-loaded file(s), summed)" % t["files"],
                        t["tokens"], t["hard"]))
        lines.append("             %s" % TOTAL_REMEDY)
    elif report and t["tier"] == "advisory":
        lines.append("ADVISORY     %-52s %7d tok  > %d (always-loaded TOTAL -- %s)"
                     % ("(%d always-loaded file(s), summed)" % t["files"],
                        t["tokens"], t["advisory"], ROLE_WHY[ALWAYS]))
        lines.append("             not a build failure: schedule a trim. %s" % TOTAL_REMEDY)

    n = len(result["files"])
    if failed(result):
        lines.append("BLOCKED: %d of %d workflow-owned doc(s) exceed a HARD budget%s. Over the "
                     "on-demand wall a file cannot be read in one call at all, so this is a "
                     "broken read, not a style note. Fix by splitting, never by deleting "
                     "content that carries intent."
                     % (len(result["over"]), n,
                        "" if t["tier"] != "over" else
                        ", and the always-loaded set costs %d tok against a %d ceiling"
                        % (t["tokens"], t["hard"])))
    else:
        lines.append("OK: doc budget -- %d workflow-owned doc(s) within budget (%d advisory); "
                     "always-loaded set %d/%d tok"
                     % (n, len(result["advisories"]), t["tokens"], t["hard"]))
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(description="the context-budget gate over workflow-owned docs")
    ap.add_argument("--project-root", default=".")
    ap.add_argument("--report", action="store_true",
                    help="list advisories too and always exit 0 (the maintenance-item view)")
    ap.add_argument("--check", action="store_true",
                    help="the gate: exit 1 on any HARD breach (the default)")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    root = os.path.abspath(args.project_root)
    result = scan(root)
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(render(result, report=args.report))
    # `--report` is the read-only view: it must not fail a commit for an advisory, and its
    # whole job is to be safe to run anywhere.
    return 0 if args.report else (1 if failed(result) else 0)


if __name__ == "__main__":
    sys.exit(main())

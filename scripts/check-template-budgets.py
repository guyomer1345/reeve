#!/usr/bin/env python3
"""check-template-budgets.py — the context budget, enforced AT SOURCE (D184).

THE HOLE THIS CLOSES. `product/scripts/check_doc_budget.py` is the context-budget gate, and
it is a good one — but it walks an *installed* project's `.workflow/` docs. The package's own
`product/templates/*.md`, the files that BECOME those installed docs, are invisible to it.
So this repo shipped a package that fails its own gate with every meta gate green: the 4219
that broke `loop.md` was found by *installing*, not by any gate here. Until a gate measures
the templates at source, in this repo, no cap here is real — it is a cap on other people's
copies.

Meta-only. This never ships: it reads `product/templates/` as SOURCE rather than as installed
state, and it exists to bind the packager, not the driven project. Same class as
`check_enum_coherence.py` and `check-status-coherence.sh` — it rides the meta-repo pre-commit,
not `checks.sh`, and it is deliberately absent from `product/MANIFEST.json`.

TWO FACTS, TWO OWNERS, NEITHER RESTATED HERE (D80).

  1. WHERE A TEMPLATE LANDS is owned by `product/scripts/update_reconcile.py`: its `TEMPLATES`
     list (`templates/loop.md` -> `.workflow/loop.md`, and so on), its `SEEDS` list (shipped
     once, then project-owned — budgeted here all the same, because what `/update` does to a
     file later says nothing about what it costs a session), plus the orchestrator brief,
     which that module handles separately because it is a managed BLOCK inside the target's
     root `CLAUDE.md` rather than a whole-file copy. `TEMPLATES` is imported. The brief pair is
     *parsed* out of `render_brief`'s source, and the reason is worth stating rather than
     apologising for: its destination is a function (`brief_paths`) and can simply be called,
     but its SOURCE path is a literal inside a function body, not a module constant — there is
     no value to import. Parsing the one owner beats declaring a second copy of the fact, and
     if the parse ever stops matching this gate FAILS rather than quietly budgeting one file
     fewer.

  2. HOW BIG IS TOO BIG, and what role a file has, are owned by `check_doc_budget.py`:
     `estimate_tokens`, `DEFAULTS`, the role constants, and `workflow_docs`. All imported. The
     whole point of this gate is that the source-side and installed-side measurements AGREE,
     and a second estimator — or a second copy of "which paths are always-loaded" — would
     drift apart from the thing it is supposed to predict.

HOW THE ROLE IS DERIVED, since this is the part that could most easily have become a
re-implementation. Rather than restate "root `CLAUDE.md`, `.claude/CLAUDE.md` and
`.workflow/loop.md` are always-loaded, and a split-pointer target is on-demand whatever its
referrer was", this materialises each template AT ITS INSTALLED DESTINATION in a scratch tree
and asks `workflow_docs()` — the shipped classifier itself — what role it gets. That gets the
split-and-pointer rule for free and exactly: `templates/loop-detail.md` comes back on-demand
because the real `loop.md` really does carry a pointer to it, not because this file says so.
No `.workflow/config.json` is written into the scratch tree on purpose — a template is
measured against the SHIPPED defaults, because a knob some target project sets is theirs and
cannot excuse what the package weighs.

BOTH BOUNDS, because one of them caps the wrong thing (D184): each template against its role's
HARD budget, AND the sum of the always-loaded ones against `always_total_hard`. Either one over
exits 1. Advisories print and never fail.

AN UNMAPPED TEMPLATE FAILS. A new `product/templates/*.md` that no owner maps to a destination
is not skipped — being silently skipped is how the next always-loaded file ships unmeasured,
which is this gate's own defect one level up. `checks.sh` and `settings.json` are not markdown
and are out of scope; the sweep is `*.md`.

  --check   (default) the gate: exit 1 on any HARD breach, on the always-loaded TOTAL over its
            ceiling, or on a template no owner maps.
  --report  every template with its role, estimate and tier; exit 0. The read-only view.
  --json    machine-readable, for either mode.
"""
import argparse
import glob
import inspect
import json
import os
import re
import shutil
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # scripts/ -> repo root

sys.path.insert(0, os.path.join(ROOT, "product", "scripts"))
import check_doc_budget as db          # noqa: E402  the sizer, the roles, the numbers
import update_reconcile as ur          # noqa: E402  the template -> destination mapping

TEMPLATE_DIR_REL = os.path.join("product", "templates")
# The shared contracts ship as a plugin glob and are read IN PLACE, on demand, by relative
# path -- there is no `install[]` entry to derive a destination from, so they are their own row
# source rather than a mapping.
SHARED_DIR_REL = os.path.join("product", "shared")

# The brief's SOURCE path is a literal inside `render_brief`, not a module constant, so it is
# read out of that function's own source rather than copied. Anchored on `plugin_root` and the
# `templates` segment so it cannot drift onto some other join.
_BRIEF_SRC_RE = re.compile(
    r"""os\.path\.join\(\s*plugin_root\s*,\s*["']templates["']\s*,\s*["']([^"']+)["']\s*\)""")


class MappingError(RuntimeError):
    """The owner could not be read. Loud, never a silently shorter mapping."""


def _posix(path):
    return path.replace(os.sep, "/")


def template_map():
    """[(template_rel, installed_rel)] for every package-owned template, from its owner.

    `template_rel` is relative to the repo root (`product/templates/...`); `installed_rel` is
    relative to a driven project's root, which is the form `workflow_docs()` classifies.
    """
    # `TEMPLATES` AND `SEEDS`, because for THIS gate they are the same fact. The two differ in
    # what `/update` does to them afterwards -- a template is refreshed, a seed is written once
    # and then belongs to the operator -- and that difference is invisible here: both are
    # markdown this package ships into a project, so both are context the package causes every
    # driven session to pay for. Budgeting only the refreshed half would have let
    # `.workflow/directives.md`, an ALWAYS-LOADED file, install unmeasured -- the exact defect
    # this gate exists to close, one category further along.
    pairs = [(_posix(os.path.join("product", src)), _posix(dest))
             for src, dest in list(ur.TEMPLATES) + list(getattr(ur, "SEEDS", []))]

    m = _BRIEF_SRC_RE.search(inspect.getsource(ur.render_brief))
    if not m:
        raise MappingError(
            "cannot read the orchestrator brief's template path out of "
            "update_reconcile.render_brief — the owner moved and this gate would otherwise "
            "budget one always-loaded file fewer, in silence")
    brief_dest = ur.brief_paths("")  # the owner's own answer for "where does the brief live"
    if not brief_dest:
        raise MappingError("update_reconcile.brief_paths('') returned nothing")
    pairs.append((_posix(os.path.join("product", "templates", m.group(1))), _posix(brief_dest)))
    return pairs


def _markdown(pairs):
    return [(s, d) for s, d in pairs if s.endswith(".md")]


def roles_for(pairs, repo_root):
    """{installed_rel: role} — asked of the SHIPPED classifier, never decided here.

    Each template is written to its installed destination in a scratch project and
    `check_doc_budget.workflow_docs()` is run over it. A destination the classifier does not
    return has no role and therefore no budget, which is a finding, not a pass.
    """
    tmp = tempfile.mkdtemp(prefix="template-budgets-")
    try:
        for src_rel, dest_rel in pairs:
            src = os.path.join(repo_root, src_rel.replace("/", os.sep))
            if not os.path.isfile(src):
                continue
            dest = os.path.join(tmp, dest_rel.replace("/", os.sep))
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            shutil.copyfile(src, dest)
        # No config.json: DEFAULTS, project_root ".", docs_root ".", org False. A template is
        # measured against what the package ships, not against a knob a target might set.
        found = db.workflow_docs(tmp, ".", ".", False)
        return {_posix(os.path.relpath(path, tmp)): role for role, path in found}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def scan(repo_root=ROOT, budgets=None):
    b = dict(db.DEFAULTS) if budgets is None else dict(budgets)
    pairs = _markdown(template_map())
    mapped_sources = {s for s, _d in pairs}

    problems = []  # coverage failures: a template with no budget is the defect, not a pass
    on_disk = sorted(_posix(os.path.relpath(p, repo_root))
                     for p in glob.glob(os.path.join(repo_root, TEMPLATE_DIR_REL, "*.md")))
    for src in on_disk:
        if src not in mapped_sources:
            problems.append({"template": src, "kind": "unmapped",
                             "why": "no installed destination — no owner in "
                                    "update_reconcile maps it"})

    # THE SHARED DOCS ARE MEASURED TOO, and their absence here was the same hole one level over.
    # `product/shared/*.md` ships as a plugin glob with no `install[]` entry: capabilities read it
    # in place, on demand, by relative path. So nothing in the shipped budget gate can see it --
    # `check_doc_budget.py` walks an installed `.workflow/` and these files never land there -- and
    # nothing here saw it either, because this gate was scoped to `templates/`. The consequence was
    # measured, not imagined: `shared/schemas.md` sat at 94% of the ceiling and one slice's edits
    # pushed it 404 tokens OVER while all six meta-gates reported green.
    #
    # For these the hard number is not a preference at all -- it is the Read tool's 25 000-token
    # wall, past which a capability CANNOT load its own contract in one call. That makes this a
    # correctness gate, not a style note.
    #
    # WHY HERE AND NOT IN THE SHIPPED GATE: widening the shipped classifier would start failing
    # `checks.sh` in every target project over PACKAGE files that project cannot edit -- the same
    # deadlock `check_doc_budget.py` already reasons about for an org-mode `CLAUDE.md`. Measuring
    # at source, in the meta-repo, costs a target nothing and catches it before it ships.
    shared_rel = _posix(os.path.join(SHARED_DIR_REL))
    shared_rows = []
    for path in sorted(glob.glob(os.path.join(repo_root, SHARED_DIR_REL, "*.md"))):
        rel = _posix(os.path.relpath(path, repo_root))
        try:
            with open(path, encoding="utf-8", errors="replace") as fh:
                text = fh.read()
        except OSError:
            problems.append({"template": rel, "kind": "missing",
                             "why": "a shared doc that cannot be read is one no capability can "
                                    "load either"})
            continue
        est = db.estimate_tokens(text, b["chars_per_token"])
        shared_rows.append({"template": rel, "installs_to": "(read in place from %s)" % shared_rel,
                            "role": db.ONDEMAND, "tokens": est,
                            "hard": b["ondemand_hard"], "advisory": b["ondemand_advisory"],
                            "tier": "over" if est > b["ondemand_hard"]
                                    else ("advisory" if est > b["ondemand_advisory"] else "ok")})

    roles = roles_for(pairs, repo_root)
    rows = list(shared_rows)
    for src_rel, dest_rel in sorted(pairs):
        path = os.path.join(repo_root, src_rel.replace("/", os.sep))
        try:
            with open(path, encoding="utf-8", errors="replace") as fh:
                text = fh.read()
        except OSError:
            problems.append({"template": src_rel, "kind": "missing",
                             "why": "an owner maps it to %s, but it is not on disk"
                                    % dest_rel})
            continue
        role = roles.get(dest_rel)
        if role is None:
            problems.append({"template": src_rel, "kind": "unclassified",
                             "why": "installs to %s, which the shipped classifier gives no "
                                    "role and so no budget" % dest_rel})
            continue
        est = db.estimate_tokens(text, b["chars_per_token"])
        hard = b["always_hard"] if role == db.ALWAYS else b["ondemand_hard"]
        adv = b["always_advisory"] if role == db.ALWAYS else b["ondemand_advisory"]
        rows.append({"template": src_rel, "installs_to": dest_rel, "role": role,
                     "tokens": est, "hard": hard, "advisory": adv,
                     "tier": "over" if est > hard else ("advisory" if est > adv else "ok")})
    rows.sort(key=lambda r: (-r["tokens"], r["template"]))

    always_rows = [r for r in rows if r["role"] == db.ALWAYS]
    tot = sum(r["tokens"] for r in always_rows)
    t_hard, t_adv = b["always_total_hard"], b["always_total_advisory"]
    total = {"role": db.ALWAYS, "tokens": tot, "hard": t_hard, "advisory": t_adv,
             "files": len(always_rows),
             "tier": "over" if tot > t_hard else ("advisory" if tot > t_adv else "ok")}

    return {"budgets": b, "files": rows, "total": total, "unmapped": problems,
            "over": [r for r in rows if r["tier"] == "over"],
            "advisories": [r for r in rows if r["tier"] == "advisory"]}


def failed(result):
    """The verdict. `check_doc_budget.failed` owns the budget half — this adds coverage.

    A template no owner maps is a template with no budget, and a gate that passes over one is
    the very defect this file exists to close, so it fails here exactly as a breach does.
    """
    return db.failed(result) or bool(result["unmapped"])


PROBLEM_LABEL = {"unmapped": "UNMAPPED", "missing": "MISSING", "unclassified": "NO ROLE"}

# A template with no budget is a template that installs unmeasured, and an unmeasured
# always-loaded file is exactly the defect this gate exists to close -- so each of these
# names the one thing that puts the file back under a budget.
PROBLEM_REMEDY = {
    "unmapped": ("map it in update_reconcile.py, or it ships to a destination nothing "
                 "measures -- the next always-loaded file would land unbudgeted, in silence"),
    "missing": ("restore it, or drop its entry from update_reconcile.py -- a mapping whose "
                "source is gone is a broken install, not a smaller package"),
    "unclassified": ("check_doc_budget.workflow_docs() does not reach that path -- either the "
                     "destination is wrong, or the referring doc lost the split pointer that "
                     "made it findable"),
}


def _remedy(row):
    if row["role"] == db.ALWAYS:
        return ("trim it -- move detail to an on-demand sibling and leave a split pointer; "
                "every driven project reads this file before every single turn")
    return ("split-and-pointer -- a lean survivor plus a detail file, marker at the head of "
            "the survivor")


def render(result, report):
    lines = []
    for r in result["over"]:
        lines.append("OVER BUDGET  %-56s %7d tok  > %d (%s HARD)"
                     % ("%s -> %s" % (r["template"], r["installs_to"]),
                        r["tokens"], r["hard"], r["role"]))
        lines.append("             %s" % _remedy(r))
    if report:
        for r in result["advisories"]:
            lines.append("ADVISORY     %-56s %7d tok  > %d (%s -- %s)"
                         % ("%s -> %s" % (r["template"], r["installs_to"]),
                            r["tokens"], r["advisory"], r["role"], db.ROLE_WHY[r["role"]]))
            lines.append("             not a build failure: schedule a trim. %s" % _remedy(r))
    t = result["total"]
    if t["tier"] == "over":
        lines.append("OVER BUDGET  %-56s %7d tok  > %d (always-loaded TOTAL HARD)"
                     % ("(%d always-loaded template(s), summed)" % t["files"],
                        t["tokens"], t["hard"]))
        lines.append("             %s" % db.TOTAL_REMEDY)
    elif report and t["tier"] == "advisory":
        lines.append("ADVISORY     %-56s %7d tok  > %d (always-loaded TOTAL -- %s)"
                     % ("(%d always-loaded template(s), summed)" % t["files"],
                        t["tokens"], t["advisory"], db.ROLE_WHY[db.ALWAYS]))
        lines.append("             not a build failure: schedule a trim. %s" % db.TOTAL_REMEDY)
    for p in result["unmapped"]:
        lines.append("%-12s %-56s %s"
                     % (PROBLEM_LABEL[p["kind"]], p["template"], p["why"]))
        lines.append("             %s" % PROBLEM_REMEDY[p["kind"]])

    if report:
        for r in result["files"]:
            if r["tier"] == "ok":
                lines.append("ok           %-56s %7d tok  <= %d (%s)"
                             % ("%s -> %s" % (r["template"], r["installs_to"]),
                                r["tokens"], r["advisory"], r["role"]))

    n = len(result["files"])
    if failed(result):
        why = []
        if result["over"]:
            why.append("%d of %d template(s) exceed a HARD budget" % (len(result["over"]), n))
        if t["tier"] == "over":
            why.append("the always-loaded set costs %d tok against a %d ceiling"
                       % (t["tokens"], t["hard"]))
        if result["unmapped"]:
            why.append("%d template(s) carry no budget (%s)"
                       % (len(result["unmapped"]),
                          ", ".join(sorted(set(p["kind"] for p in result["unmapped"])))))
        lines.append("BLOCKED: %s. Measured at SOURCE -- these are the files the package "
                     "installs, so this is what every driven project will pay. Fix by "
                     "relocating content, never by raising the cap." % "; ".join(why))
    else:
        lines.append("OK: template budget -- %d package template(s) within budget (%d "
                     "advisory); always-loaded set %d/%d tok across %d template(s)"
                     % (n, len(result["advisories"]), t["tokens"], t["hard"], t["files"]))
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="the context-budget gate over product/templates, measured at source")
    ap.add_argument("--repo-root", default=ROOT,
                    help="repo whose product/templates to measure (the mapping and the sizer "
                         "always come from this checkout's own owners)")
    ap.add_argument("--report", action="store_true",
                    help="list advisories and every in-budget template too; always exit 0")
    ap.add_argument("--check", action="store_true",
                    help="the gate: exit 1 on any HARD breach or unmapped template (default)")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    result = scan(os.path.abspath(args.repo_root))
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(render(result, report=args.report))
    return 0 if args.report else (1 if failed(result) else 0)


if __name__ == "__main__":
    sys.exit(main())

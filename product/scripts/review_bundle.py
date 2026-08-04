#!/usr/bin/env python3
"""Produce the ORG-MODE review bundle: one item -> one squashed diff -> one human commit.

Org mode runs the loop against a product the operator does not own, from a private clone
with no push path. The loop's own git history exists to serve RESUME, and that is served
entirely inside the private clone -- nothing about resume requires the owner's repo to ever
see a loop commit. So the boundary the work crosses is a GOVERNANCE one, not a history one,
and what crosses it is a plain diff the human applies, reviews, and commits themselves.

Three properties, each structural rather than remembered:

  * SQUASHED, so the human is the author BY CONSTRUCTION. A branch would have been better
    tooling, but its path of least resistance (`git push`) is exactly the wrong act; a
    `format-patch` series carries loop authorship and is easy to `git am` unreviewed.
  * NO LOOP COMMIT MESSAGES CROSS. They quote ticket ids and knowledge prose ABOUT the
    owner's proprietary code -- derived IP flowing back in, and noise their reviewer cannot
    interpret. A squashed diff has no message at all.
  * THE SIDECAR IS OUTSIDE THE DIFF. Item id, base sha and the plan/changelog summary are
    what the OPERATOR needs to review their own work; they are not what the owner's history
    should carry. Keeping them in a second file means they cannot land upstream by accident.

And the leak boundary is VERIFIED, not merely applied. The brain owns exactly two
directories (`.workflow/` and `.claude/`), so the exclusion is two entries -- but a bundle
is refused outright if its own bytes still mention one, because an exclusion that is only
ever applied is a policy, while one that is checked afterwards is a gate.

Stdlib only. Exit 0 = bundle written; 1 = refused (reasons printed); 2 = usage.

  review_bundle.py build <item-id> [--project-root DIR] [--base SHA] [--head REF]
  review_bundle.py verify <bundle.diff>
"""
import json
import os
import re
import subprocess
import sys

WORKFLOW = ".workflow"
BUNDLE_DIR = os.path.join(WORKFLOW, "bundles")

# The brain. Everything the workflow owns lives under these two, which is the entire reason
# `docs_root` is namespaced in org mode -- it keeps this list two entries long and auditable
# instead of a per-file list that has to stay correct forever.
BRAIN = (".workflow", ".claude")

DIFF_HEADER = re.compile(r"^diff --git a/(.+?) b/(.+)$")


def _run(args, cwd, check=True):
    p = subprocess.run(args, cwd=cwd, capture_output=True, text=True)
    if check and p.returncode != 0:
        raise RuntimeError("%s failed: %s" % (" ".join(args), (p.stderr or "").strip()))
    return p.stdout


def _read_json(path, default=None):
    try:
        with open(path) as fh:
            return json.load(fh)
    except Exception:
        return default


def is_org(project_root):
    cfg = _read_json(os.path.join(project_root, WORKFLOW, "config.json"), {}) or {}
    return "org" in cfg


def item_commits(project_root, item_id, head="HEAD"):
    """Commits carrying this item's `Refs: item #<id>` trailer, oldest first.

    The trailer is the commit skill's own always-present link, so this reads the loop's
    existing discipline rather than introducing a second way to say the same thing. A
    prerequisite-repair rides its own preceding commit and carries the same trailer -- it is
    part of the item's work, so including it is correct, not a leak.
    """
    out = _run(["git", "log", "--reverse", "--format=%H",
                "--grep=Refs: item #%s$" % re.escape(item_id), "--extended-regexp", head],
               project_root)
    return [l.strip() for l in out.splitlines() if l.strip()]


def resolve_base(project_root, item_id, base=None, head="HEAD"):
    """-> (base_sha, how). Explicit wins; else the parent of the item's FIRST commit.

    Falling back to `FETCH_HEAD` would be wrong for the per-item unit: it is the base the
    knowledge was described against, not the point this item started from, so a bundle built
    on it would carry every item since. `how` is recorded in the sidecar because a base
    nobody can account for is a diff nobody can review.
    """
    if base:
        return _run(["git", "rev-parse", base], project_root).strip(), "explicit"
    commits = item_commits(project_root, item_id, head)
    if not commits:
        raise RuntimeError(
            "no commit carries `Refs: item #%s` up to %s -- nothing to bundle. The commit "
            "skill writes that trailer on every item commit; an item with none has not been "
            "committed yet." % (item_id, head))
    parents = _run(["git", "rev-list", "--parents", "-n", "1", commits[0]],
                   project_root).split()
    if len(parents) < 2:
        raise RuntimeError(
            "item %s starts at a ROOT commit (%s) with no parent, so there is no base to diff "
            "against. Pass --base explicitly." % (item_id, commits[0][:12]))
    return parents[1], "item-first-commit-parent"


UPSTREAM_REFS = ("FETCH_HEAD", "origin/HEAD", "origin/main", "origin/master")


def upstream_base(project_root, head="HEAD"):
    """The newest commit this work descends from that the OWNER's repo actually HAS.

    The item's own base is a BRAIN-local sha: the brain carries scaffold and per-item commits
    the owner's repo has never seen, so quoting it at the human is quoting a commit they
    cannot resolve. The merge-base against the fetched upstream is the last shared point and
    is the only sha in this bundle that means anything on their side. None resolvable (never
    fetched) -> None, reported honestly rather than guessed.
    """
    for ref in UPSTREAM_REFS:
        try:
            sha = _run(["git", "rev-parse", "--verify", "--quiet", ref], project_root).strip()
        except RuntimeError:
            continue
        if not sha:
            continue
        try:
            return _run(["git", "merge-base", head, sha], project_root).strip(), ref
        except RuntimeError:
            continue
    return None, None


def squashed_diff(project_root, base, head="HEAD"):
    """The item's whole change as ONE diff, with the brain excluded at the git level."""
    excludes = [":(exclude)%s" % d for d in BRAIN] + [":(exclude)%s/**" % d for d in BRAIN]
    return _run(["git", "diff", "--binary", base, head, "--"] + excludes, project_root)


def diff_paths(diff_text):
    """Every path the diff touches, read back off its OWN headers.

    Deliberately parsed from the produced bytes rather than trusted from the pathspec: this
    is the check that the exclusion actually held, so it must not share a source with it.
    """
    paths = []
    for line in diff_text.splitlines():
        m = DIFF_HEADER.match(line)
        if m:
            paths.extend(p for p in m.groups() if p != "/dev/null")
    return paths


def leaks(diff_text):
    """-> [reason]. Non-empty means the bundle MUST NOT be written."""
    bad = []
    for path in diff_paths(diff_text):
        top = path.split("/", 1)[0]
        if top in BRAIN:
            bad.append("brain path in the diff: %s" % path)
    # Content-level, and deliberately only a REFUSAL for our own paths appearing as added
    # lines in the owner's files -- a loop comment citing `.workflow/...` is derived-IP
    # plumbing that means nothing to their reviewer and should never have been written.
    for line in diff_text.splitlines():
        if line.startswith("+") and not line.startswith("+++"):
            for d in BRAIN:
                if d + "/" in line:
                    bad.append("added line references the brain (%s): %s"
                               % (d, line[1:].strip()[:80]))
    return sorted(set(bad))


def summary_for(project_root, item_id):
    """Plan/changelog one-liners for the sidecar. Absent files are not an error -- the
    sidecar is for the operator's own review, so it reports what exists and says so."""
    item_dir = os.path.join(project_root, WORKFLOW, "items", item_id)
    out = {}
    for key, name in (("plan", "plan.md"), ("changelog", "changelog.md")):
        path = os.path.join(item_dir, name)
        try:
            with open(path, encoding="utf-8", errors="replace") as fh:
                head = [l.strip() for l in fh.read().splitlines() if l.strip()][:1]
            out[key] = head[0] if head else ""
        except OSError:
            out[key] = None
    return out


def build(project_root, item_id, base=None, head="HEAD"):
    if not is_org(project_root):
        raise RuntimeError(
            "review bundles are an ORG-MODE mechanism (`org` is absent from "
            ".workflow/config.json). Outside org mode the loop owns its repo and commits "
            "directly -- there is no governance boundary for a bundle to cross, and the "
            "brain-exclusion that makes a bundle safe would strip the project's own docs.")
    base_sha, how = resolve_base(project_root, item_id, base, head)
    head_sha = _run(["git", "rev-parse", head], project_root).strip()
    diff = squashed_diff(project_root, base_sha, head)
    reasons = leaks(diff)
    if reasons:
        return None, reasons
    if not diff.strip():
        return None, ["the squashed diff is EMPTY -- every file this item touched is inside "
                      "the brain, so there is nothing for the owner's repo to receive."]

    out_dir = os.path.join(project_root, BUNDLE_DIR)
    os.makedirs(out_dir, exist_ok=True)
    diff_path = os.path.join(out_dir, "%s.diff" % item_id)
    meta_path = os.path.join(out_dir, "%s.json" % item_id)
    with open(diff_path, "w", encoding="utf-8") as fh:
        fh.write(diff)
    files = sorted(set(diff_paths(diff)))
    cfg = _read_json(os.path.join(project_root, WORKFLOW, "config.json"), {}) or {}
    up_sha, up_ref = upstream_base(project_root, head)
    meta = {
        "item_id": item_id,
        # BRAIN-local: the diff's true two endpoints, for the operator's own audit. Neither
        # resolves in the owner's repo, so neither is ever quoted at the human.
        "base": base_sha,
        "base_resolved_by": how,
        "head": head_sha,
        # The one sha here that exists on THEIR side.
        "upstream_base": up_sha,
        "upstream_ref": up_ref,
        "files": files,
        "excluded": list(BRAIN),
        "summary": summary_for(project_root, item_id),
        "checkout": (cfg.get("org") or {}).get("checkout"),
    }
    with open(meta_path, "w", encoding="utf-8") as fh:
        json.dump(meta, fh, indent=2, sort_keys=True)
        fh.write("\n")
    return meta, []


def verify(diff_path):
    with open(diff_path, encoding="utf-8", errors="replace") as fh:
        return leaks(fh.read())


def _apply_hint(meta, diff_path):
    """What the HUMAN does. Never quotes a brain sha -- they cannot resolve one."""
    where = meta.get("checkout") or "<your own checkout>"
    up = meta.get("upstream_base")
    lines = ["  cd %s" % where,
             "  git apply %s" % os.path.abspath(diff_path),
             "  # review it, then commit in your own name -- the bundle carries no message"]
    if up:
        lines.append("  # descends from upstream %s (%s), plus any earlier bundles you have "
                     "already applied" % (up[:12], meta.get("upstream_ref")))
    else:
        lines.append("  # NOTE: no upstream ref has been fetched here, so the upstream commit "
                     "this descends from is unknown -- `git fetch` in the brain first")
    return "\n".join(lines)


def main(argv):
    if len(argv) < 2:
        sys.stderr.write(__doc__.rsplit("\n\n", 1)[-1])
        return 2
    cmd = argv[1]
    project_root = "."
    for i, a in enumerate(argv):
        if a == "--project-root" and i + 1 < len(argv):
            project_root = argv[i + 1]

    if cmd == "verify":
        rest = [a for a in argv[2:] if not a.startswith("--")]
        if len(rest) != 1:
            sys.stderr.write("usage: review_bundle.py verify <bundle.diff>\n")
            return 2
        reasons = verify(rest[0])
        if reasons:
            sys.stderr.write("REFUSED: this bundle crosses the org-mode boundary:\n")
            for r in reasons:
                sys.stderr.write("  " + r + "\n")
            return 1
        print("OK: bundle touches no brain path")
        return 0

    if cmd == "build":
        rest = [a for a in argv[2:] if not a.startswith("--")]
        rest = [a for a in rest if a != project_root]
        base = head = None
        for i, a in enumerate(argv):
            if a == "--base" and i + 1 < len(argv):
                base = argv[i + 1]
            if a == "--head" and i + 1 < len(argv):
                head = argv[i + 1]
        rest = [a for a in rest if a not in (base, head)]
        if len(rest) != 1:
            sys.stderr.write("usage: review_bundle.py build <item-id> [--project-root DIR] "
                             "[--base SHA] [--head REF]\n")
            return 2
        try:
            meta, reasons = build(project_root, rest[0], base, head or "HEAD")
        except RuntimeError as exc:
            sys.stderr.write("REFUSED: %s\n" % exc)
            return 1
        if reasons:
            sys.stderr.write("REFUSED: this bundle would cross the org-mode boundary:\n")
            for r in reasons:
                sys.stderr.write("  " + r + "\n")
            return 1
        print("BUNDLE %s -- %d file(s), squashed from %s..%s (%s)"
              % (meta["item_id"], len(meta["files"]), meta["base"][:12],
                 meta["head"][:12], meta["base_resolved_by"]))
        for f in meta["files"]:
            print("  " + f)
        print("hand off to the human:")
        print(_apply_hint(meta, os.path.join(project_root, BUNDLE_DIR,
                                             meta["item_id"] + ".diff")))
        return 0

    sys.stderr.write("usage: review_bundle.py build|verify …\n")
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))

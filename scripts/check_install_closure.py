#!/usr/bin/env python3
"""Every installed script's local imports must be installed too.

A script that ships is not the same thing as a script that RUNS where it lands. The manifest's
`install` list is what reaches a driven project's `.claude/scripts/`, and a module that is not
on it is simply absent there -- so an installed script importing a sibling that was never
installed works perfectly in this repo, where every file sits together, and dies the first time
a real project runs it. That is the worst shape of bug this package can ship: invisible in
every test, guaranteed in production, and discoverable only by installing.

It happened. `check_wave_independence.py` learned to read plan freshness, `plan_freshness.py`
was added beside it, and the manifest was not touched -- 1116 green tests and a gate that
`ModuleNotFoundError`s on any real install.

WHY THE EXISTING GATES DID NOT CATCH IT. The leak check and the release build both police the
same direction: nothing may ship that should not. Nothing polices the other direction -- that
what ships is COMPLETE. A closure is not a boundary, and it needs its own check.

The saving grace, and the reason this is a gate rather than an incident: the crash exits 1, and
1 is that gate's conservative answer, so a caller branching on status still stayed serial. That
is luck standing in for design. Luck is not a fail-direction.
"""
import ast
import json
import os
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
PRODUCT = os.path.join(ROOT, "product")


def _local_imports(path):
    """Top-level module names imported by `path` that resolve to a sibling .py file.

    Read from the AST rather than by regex, so a name inside a string or a comment is not
    mistaken for a dependency -- and DEFERRED imports count, since an import inside a function
    is exactly the one that survives every test and fails in the field.
    """
    with open(path, encoding="utf-8") as fh:
        tree = ast.parse(fh.read(), filename=path)
    here = os.path.dirname(path)
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            names.add(node.module.split(".")[0])
    return {n for n in names if os.path.isfile(os.path.join(here, n + ".py"))}


def main():
    manifest = json.load(open(os.path.join(PRODUCT, "MANIFEST.json"), encoding="utf-8"))
    installed = {e["src"] for e in manifest.get("install", [])}
    problems = []
    for src in sorted(installed):
        if not src.endswith(".py"):
            continue
        path = os.path.join(PRODUCT, src)
        if not os.path.isfile(path):
            problems.append("%s is on the install list but not in the tree" % src)
            continue
        for mod in sorted(_local_imports(path)):
            need = os.path.join(os.path.dirname(src), mod + ".py")
            if need not in installed:
                problems.append(
                    "%s imports `%s`, but %s is NOT installed -- it will be absent from "
                    "`.claude/scripts/` and the import will fail on a real project"
                    % (src, mod, need))
    if problems:
        sys.stderr.write("BLOCKED: install set is not closed under imports\n")
        for p in problems:
            sys.stderr.write("  %s\n" % p)
        sys.stderr.write("  Add the missing module to `install` in product/MANIFEST.json.\n")
        return 1
    n = sum(1 for s in installed if s.endswith(".py"))
    print("OK: install closure -- %d installed python file(s), every local import installed" % n)
    return 0


if __name__ == "__main__":
    sys.exit(main())

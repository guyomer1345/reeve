"""Tests for check_codemap_fresh.py — is the committed code map still this tree's map?

The cases that matter are the two the real drives produced: a map with nothing in it over a
tree with ten source files (greenfield, which never ran the generator at all), and a wrapper
that IGNORES the arguments the gate would like to pass it (brownfield, whose `codemap.sh` was
written without `"$@"`). Both are pinned here, because both were found in the wild rather than
reasoned about.
"""
import json
import os
import shutil
import subprocess
import sys

import pytest

import check_codemap_fresh as cf

HERE = os.path.dirname(os.path.abspath(__file__))
ENGINE = os.path.join(HERE, "codemap")

FORWARDING = '#!/usr/bin/env bash\nset -euo pipefail\ncd "$(dirname "$0")/.."\nexec python3 .claude/scripts/codemap/codemap.py %s "$@"\n'
FIXED_ARGV = '#!/usr/bin/env bash\nset -euo pipefail\ncd "$(dirname "$0")/.."\nexec python3 .claude/scripts/codemap/codemap.py %s\n'


def _project(tmp_path, project_root=".", wrapper=FORWARDING, source=True):
    root = str(tmp_path)
    os.makedirs(os.path.join(root, ".workflow"), exist_ok=True)
    shutil.copytree(ENGINE, os.path.join(root, ".claude", "scripts", "codemap"))
    with open(os.path.join(root, ".workflow", "config.json"), "w") as fh:
        json.dump({"project_root": project_root}, fh)
    w = os.path.join(root, ".workflow", "codemap.sh")
    with open(w, "w") as fh:
        fh.write(wrapper % project_root)
    os.chmod(w, 0o755)
    if source:
        pkg = os.path.normpath(os.path.join(root, project_root, "app"))
        os.makedirs(pkg, exist_ok=True)
        with open(os.path.join(pkg, "core.py"), "w") as fh:
            fh.write("VALUE = 1\n")
        with open(os.path.join(pkg, "cli.py"), "w") as fh:
            fh.write("from app.core import VALUE\n")
    return root


def _generate(root):
    subprocess.run(["bash", ".workflow/codemap.sh"], cwd=root, check=True, capture_output=True)


def _map_path(root):
    return cf.graph_path(root)


def test_a_freshly_generated_map_is_clear(tmp_path):
    root = _project(tmp_path)
    _generate(root)
    res = cf.run(root)
    assert res["status"] == "clear", res


def test_an_EMPTY_map_over_a_tree_with_source_is_stale(tmp_path):
    """The greenfield failure, verbatim: the generator never ran, so the map has no nodes while
    the tree has real files. *Empty is not clean* — an assertion that cannot tell "mapped
    nothing forbidden" from "mapped nothing" would stay green through a map that stopped working.
    """
    root = _project(tmp_path)
    _generate(root)
    path = _map_path(root)
    g = json.load(open(path))
    g["nodes"], g["edges"] = [], []
    json.dump(g, open(path, "w"))
    res = cf.run(root)
    assert res["status"] == "stale"
    assert any(p.endswith("core.py") for p in res["missing"]), res


def test_a_missing_map_over_a_tree_with_source_is_stale(tmp_path):
    root = _project(tmp_path)
    _generate(root)
    os.remove(_map_path(root))
    res = cf.run(root)
    assert res["status"] == "stale" and "missing or unreadable" in res["detail"]


def test_a_new_source_file_makes_the_map_stale(tmp_path):
    """The brownfield failure: a map built once at bootstrap and never rebuilt as code lands."""
    root = _project(tmp_path)
    _generate(root)
    with open(os.path.join(root, "app", "extra.py"), "w") as fh:
        fh.write("import app.core\n")
    res = cf.run(root)
    assert res["status"] == "stale"
    assert any(p.endswith("extra.py") for p in res["missing"]), res


def test_a_deleted_source_file_makes_the_map_stale(tmp_path):
    root = _project(tmp_path)
    _generate(root)
    os.remove(os.path.join(root, "app", "cli.py"))
    res = cf.run(root)
    assert res["status"] == "stale"
    assert any(p.endswith("cli.py") for p in res["extra"]), res


def test_a_wrapper_that_IGNORES_arguments_is_still_handled(tmp_path):
    """Two trees from the SAME package version were found with different wrappers — one
    forwarding `"$@"`, one with a fixed argv. A gate that passed `--out` and trusted it would
    compare the map against itself and report fresh forever."""
    root = _project(tmp_path, wrapper=FIXED_ARGV)
    _generate(root)
    assert cf.run(root)["status"] == "clear"

    path = _map_path(root)
    g = json.load(open(path))
    g["nodes"], g["edges"] = [], []
    json.dump(g, open(path, "w"))
    assert cf.run(root)["status"] == "stale", "the fixed-argv wrapper hid the staleness"


def test_the_map_is_RESTORED_when_the_wrapper_writes_in_place(tmp_path):
    """`graph.json` is committed. A gate that left a regenerated map behind would stage a
    change nobody asked for, so the clean verdict must leave the tree byte-identical."""
    root = _project(tmp_path, wrapper=FIXED_ARGV)
    _generate(root)
    path = _map_path(root)
    before = open(path, "rb").read()
    g = json.loads(before.decode())
    g["nodes"] = []
    json.dump(g, open(path, "w"))
    stale = open(path, "rb").read()
    assert cf.run(root)["status"] == "stale"
    assert open(path, "rb").read() == stale, "the gate rewrote a committed file"


def test_no_source_at_all_is_not_a_failure(tmp_path):
    """A greenfield project before any code. A map of nothing is the correct map of nothing —
    and an absent file is not yet a defect."""
    root = _project(tmp_path, source=False)
    res = cf.run(root)
    assert res["status"] == "clear" and "recognizes" in res["detail"]


def test_no_wrapper_at_all_is_not_a_failure(tmp_path):
    root = _project(tmp_path)
    os.remove(os.path.join(root, ".workflow", "codemap.sh"))
    assert cf.run(root)["status"] == "clear"


def test_a_broken_wrapper_is_UNDETERMINED_and_still_blocks(tmp_path):
    """A generator that will not run is not a stale map, and saying so is the difference
    between "regenerate it" and "go and look at why". Both block."""
    root = _project(tmp_path)
    with open(os.path.join(root, ".workflow", "codemap.sh"), "w") as fh:
        fh.write("#!/usr/bin/env bash\nexit 3\n")
    res = cf.run(root)
    assert res["status"] == "undetermined"
    assert cf.main(["--project-root", root]) == 1


def test_the_cli_exit_code_is_the_verdict(tmp_path):
    root = _project(tmp_path)
    _generate(root)
    assert cf.main(["--project-root", root]) == 0
    path = _map_path(root)
    g = json.load(open(path))
    g["nodes"] = []
    json.dump(g, open(path, "w"))
    assert cf.main(["--project-root", root]) == 1


def test_a_nested_project_root_resolves_like_the_engine(tmp_path):
    """`./project` is the greenfield spelling, and the map lives under it, not at the repo root."""
    root = _project(tmp_path, project_root="./project")
    _generate(root)
    assert os.path.exists(os.path.join(root, "project", "docs", "knowledge", "graph.json"))
    assert cf.run(root)["status"] == "clear"

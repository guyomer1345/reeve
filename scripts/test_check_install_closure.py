"""Tests for check_install_closure.py — is the install set closed under imports?

The gate exists because of a bug it would have caught: an installed script grew an import on a
sibling that was never added to the manifest, which is invisible in this repo (every file sits
together) and fatal on any real install. So the test that matters most is the one that proves
the gate SEES that shape, not the one that proves it is quiet when all is well.
"""
import ast
import importlib.util
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
GATE = os.path.join(HERE, "check_install_closure.py")
MANIFEST = os.path.join(ROOT, "product", "MANIFEST.json")

_spec = importlib.util.spec_from_file_location("cic", GATE)
cic = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cic)


def _gate():
    return subprocess.run([sys.executable, GATE], capture_output=True, text=True)


def test_the_tree_is_closed_today():
    r = _gate()
    assert r.returncode == 0, r.stderr


def test_removing_a_required_module_reddens_it():
    """The negative control, run against the real manifest and restored afterwards. A gate that
    cannot go red is a green light with extra steps."""
    orig = open(MANIFEST, encoding="utf-8").read()
    try:
        m = json.loads(orig)
        m["install"] = [e for e in m["install"] if e["src"] != "scripts/plan_freshness.py"]
        with open(MANIFEST, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(m, indent=2) + "\n")
        r = _gate()
        assert r.returncode == 1
        assert "plan_freshness" in r.stderr
        assert "check_wave_independence.py" in r.stderr     # it names the importer, not just the gap
    finally:
        with open(MANIFEST, "w", encoding="utf-8") as fh:
            fh.write(orig)
    assert _gate().returncode == 0


def test_a_deferred_import_still_counts(tmp_path):
    """An import inside a function is exactly the one that survives every test and dies in the
    field — the real bug was one of these — so the AST walk must not stop at module level."""
    src = tmp_path / "a.py"
    src.write_text("def f():\n    import b\n    return b\n")
    (tmp_path / "b.py").write_text("x = 1\n")
    assert cic._local_imports(str(src)) == {"b"}


def test_a_stdlib_import_is_not_a_local_one(tmp_path):
    src = tmp_path / "a.py"
    src.write_text("import os, json\nfrom pathlib import Path\n")
    assert cic._local_imports(str(src)) == set()


def test_a_name_in_a_string_is_not_an_import(tmp_path):
    """Read the AST, not the text: a regex over source would score this as a dependency."""
    (tmp_path / "b.py").write_text("x = 1\n")
    src = tmp_path / "a.py"
    src.write_text('MSG = "run import b to continue"\n# import b\n')
    assert cic._local_imports(str(src)) == set()

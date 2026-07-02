#!/usr/bin/env python3
"""Regression + property tests for the code-map extractor (stdlib unittest, zero-dep).

Run:  python3 -m unittest scripts.codemap.test_codemap   (or: python3 scripts/codemap/test_codemap.py)

The load-bearing test here is `test_floor_invariant_never_nothing`: it draws its inputs
from OUTSIDE the tool's edge-extraction set (languages with no import regex) and asserts
the floor still nodes them. That is the property an earlier build violated silently — it
supported only the ~15 languages it could extract edges for, so exotic-language repos got
zero nodes, and every happy-path test passed because they all used in-scope languages.
A single in-scope example can never catch that; a property test whose input is the
complement of the build's own enumeration can. Keep that test drawing from the tail.
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_CODEMAP = os.path.join(_HERE, "codemap.py")


def run_codemap(files):
    """Write {relpath: content} into a temp dir, run codemap from it, return the graph."""
    with tempfile.TemporaryDirectory() as root:
        for rel, content in files.items():
            path = os.path.join(root, rel)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(content)
        out = os.path.join(root, "graph.json")
        subprocess.run([sys.executable, _CODEMAP, ".", "--out", out],
                       cwd=root, check=True, capture_output=True)
        with open(out, encoding="utf-8") as fh:
            return json.load(fh)


def nodes(graph):
    return {n["path"] for n in graph["nodes"]}


def edges(graph):
    return {(e["from"], e["to"]) for e in graph["edges"]}


class FloorInvariant(unittest.TestCase):
    def test_floor_invariant_never_nothing(self):
        """Every recognized SOURCE file gets a node — including languages with NO edge
        regex (the tail the floor exists for). Inputs drawn from outside the edge set."""
        src = {  # none of these languages has an import regex -> pure node-only (tier-0 tail)
            "lib/app.ex": "defmodule App do\nend\n",        # Elixir
            "lib/Main.hs": "module Main where\n",            # Haskell
            "lib/init.lua": "return {}\n",                   # Lua
            "src/analysis.r": "x <- 1\n",                    # R
            "cmd/tool.go": "package main\n",                 # Go (has a regex, but still a node)
            "app/user.rb": "class User; end\n",              # Ruby
        }
        graph = run_codemap(src)
        got = nodes(graph)
        for rel in src:
            self.assertIn(rel, got, f"floor dropped a recognized source file: {rel}")

    def test_graphless_artifacts_excluded(self):
        """Data / markup / config / doc artifacts are NOT nodes (no import graph)."""
        graph = run_codemap({
            "lib/app.ex": "defmodule App do\nend\n",
            "config.json": '{"a": 1}\n',
            "README.md": "# hi\n",
            "style.css": "body{}\n",
            "data.yaml": "a: 1\n",
        })
        got = nodes(graph)
        self.assertIn("lib/app.ex", got)
        for artifact in ("config.json", "README.md", "style.css", "data.yaml"):
            self.assertNotIn(artifact, got, f"graphless artifact leaked as a node: {artifact}")


class Resolution(unittest.TestCase):
    def test_python_arm_resolves_intraproject(self):
        graph = run_codemap({
            "pkg/__init__.py": "",
            "pkg/util.py": "def x(): return 1\n",
            "app.py": "from pkg.util import x\n",
        })
        self.assertIn(("app.py", "pkg/util.py"), edges(graph))

    def test_jsts_tsconfig_alias_beats_floor(self):
        """The JS/TS arm resolves a tsconfig path alias the tier-0 floor would drop."""
        graph = run_codemap({
            "tsconfig.json": '{\n  // jsonc\n  "compilerOptions": {\n'
                             '    "baseUrl": "./src",\n    "paths": {"@/*": ["*"]},\n  },\n}\n',
            "src/app.ts": "import {u} from '@/util';\nimport ext from 'react';\n",
            "src/util.ts": "export const u = 1;\n",
        })
        e = edges(graph)
        self.assertIn(("src/app.ts", "src/util.ts"), e)            # alias resolved
        self.assertFalse(any("react" in t for _, t in e))          # bare external dropped

    def test_no_phantom_edges_cross_language(self):
        """Cross-language false-edge guard: a Ruby require must NOT resolve to a same-named
        file in another language. Resolution is family-scoped (intra-language)."""
        graph = run_codemap({
            "app.rb": "require 'utils'\n",
            "utils.rb": "def real; end\n",
            "utils.lua": "return 1\n",       # node-only, must never be an edge target
            "utils.go": "package x\n",        # armed but different family
        })
        self.assertEqual(edges(graph), {("app.rb", "utils.rb")})

    def test_no_edge_to_missing_or_external(self):
        """Unresolved specifier yields NO edge (the floor misses before it invents)."""
        graph = run_codemap({
            "main.js": "import a from './present';\nimport b from './absent';\nimport c from 'lodash';\n",
            "present.js": "export const a = 1;\n",
        })
        e = edges(graph)
        self.assertIn(("main.js", "present.js"), e)
        self.assertEqual(len(e), 1)  # absent + lodash both dropped


class JsTsPromises(unittest.TestCase):
    """Locked property test for the JS/TS arm from the elicited promise — confirms what it
    meets (barrels, .js->.ts, baseUrl-bare, no-false-positive) and documents the residual
    (bare-but-internal workspace packages) as a visible gap, not a silent one."""

    def test_handled_relative_barrel_nodenext_and_baseurl(self):
        g = run_codemap({
            "tsconfig.json": '{"compilerOptions":{"baseUrl":"./src"}}',   # baseUrl, no paths
            "src/app.ts": ("import {b} from './b';\n"                     # relative
                           "export * from './c';\n"                       # barrel re-export (P12)
                           "import x from './d.js';\n"                     # NodeNext .js -> .ts (P11)
                           "import ext from 'react';\n"),                  # bare external -> drop
            "src/b.ts": "export const b=1;\n",
            "src/c.ts": "export const c=1;\n",
            "src/d.ts": "export const d=1;\n",
            "src/react.ts": "export const r=1;\n",                         # P17: must NOT match bare 'react'
            "src/feature.ts": "import {btn} from 'components/Button';\n",  # baseUrl-bare (P3)
            "src/components/Button.ts": "export const btn=1;\n",
        })
        e = edges(g)
        self.assertIn(("src/app.ts", "src/b.ts"), e)
        self.assertIn(("src/app.ts", "src/c.ts"), e)                      # barrel
        self.assertIn(("src/app.ts", "src/d.ts"), e)                      # .js -> .ts
        self.assertIn(("src/feature.ts", "src/components/Button.ts"), e)  # baseUrl-bare
        self.assertFalse(any("react" in t for _, t in e))                # bare external not fabricated

    def test_workspace_bare_import_is_a_KNOWN_RESIDUAL(self):
        # A bare `@acme/core` that resolves to a LOCAL workspace package — a real intra-repo
        # edge this arm does NOT yet capture (bare = external). Asserted as a visible residual.
        g = run_codemap({
            "package.json": '{"workspaces":["packages/*"]}',
            "packages/app/x.ts": "import {db} from '@acme/core';\n",
            "packages/core/package.json": '{"name":"@acme/core","main":"index.ts"}',
            "packages/core/index.ts": "export const db=1;\n",
        })
        self.assertNotIn(("packages/app/x.ts", "packages/core/index.ts"), edges(g))


class Fidelity(unittest.TestCase):
    """Every language carries an honest `fidelity` + `known_gaps`; `tier` is not trust."""

    def test_languages_carry_fidelity_and_gaps(self):
        g = run_codemap({"pkg/__init__.py": "", "app.py": "import pkg\n"})
        py = g["languages"]["python"]
        self.assertEqual(py["fidelity"], "high")
        self.assertIn("known_gaps", py)
        self.assertIsInstance(py["known_gaps"], list)

    def test_node_only_language_reports_nodes_only(self):
        g = run_codemap({"lib/app.ex": "defmodule App do\nend\n"})  # Elixir: no edge regex
        self.assertEqual(g["languages"]["elixir"]["fidelity"], "nodes-only")


if __name__ == "__main__":
    unittest.main(verbosity=2)

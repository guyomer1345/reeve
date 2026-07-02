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

    def test_workspace_bare_import_resolves_to_local_package(self):
        # A bare `@acme/core` matching a local workspace package's name resolves to its source
        # entry (exact name-match ground truth, not a heuristic). Self-name too.
        g = run_codemap({
            "package.json": '{"name":"root","workspaces":["packages/*"]}',
            "packages/app/x.ts": "import {db} from '@acme/core';\nimport r from 'root';\n",
            "packages/core/package.json": '{"name":"@acme/core","module":"src/index.ts"}',
            "packages/core/src/index.ts": "export const db=1;\n",
            "index.ts": "export const root=1;\n",  # root package self-name entry
        })
        e = edges(g)
        self.assertIn(("packages/app/x.ts", "packages/core/src/index.ts"), e)  # workspace
        self.assertIn(("packages/app/x.ts", "index.ts"), e)                    # self-name (root)

    def test_workspace_name_collision_is_not_fabricated(self):
        # An external package whose name is NOT a local package stays external (soundness).
        g = run_codemap({
            "package.json": '{"workspaces":["packages/*"]}',
            "packages/app/x.ts": "import React from 'react';\n",
            "packages/app/react.ts": "export default 1;\n",  # coincidental local file, different name
        })
        self.assertFalse(any("react" in t for _, t in edges(g)))

    def test_dts_declaration_file_resolves(self):
        # `import './x'` resolves to x.d.ts (TS extension resolution) — the audit recall gap.
        # A concrete x.ts still wins over x.d.ts (setdefault: real source before declaration).
        g = run_codemap({
            "src/a.ts": "import {t} from './types';\nimport {u} from './util';\n",
            "src/types.d.ts": "export type t = number;\n",
            "src/util.d.ts": "export const u: number;\n",   # only a .d.ts
            "src/util.ts": "export const u = 1;\n",          # ...and a real source: source must win
        })
        e = edges(g)
        self.assertIn(("src/a.ts", "src/types.d.ts"), e)     # .d.ts resolved
        self.assertIn(("src/a.ts", "src/util.ts"), e)        # concrete source preferred over .d.ts
        self.assertNotIn(("src/a.ts", "src/util.d.ts"), e)

    def test_node_modules_package_is_not_a_workspace(self):
        # SOUNDNESS: a package.json inside an excluded dir (node_modules) must NOT be picked up
        # as a workspace package by the `packages/**` glob — else a bare `import 'lodash'` would
        # fabricate an edge to the installed copy. The workspace walk prunes DEFAULT_EXCLUDE.
        g = run_codemap({
            "pnpm-workspace.yaml": "packages:\n  - 'packages/**'\n",
            "packages/app/x.ts": "import _ from 'lodash';\n",
            "packages/app/node_modules/lodash/package.json": '{"name":"lodash","main":"index.js"}',
            "packages/app/node_modules/lodash/index.js": "module.exports = {};\n",
        })
        self.assertFalse(any("lodash" in t for _, t in edges(g)))


class JsTsExportsSubpath(unittest.TestCase):
    """Closing the exports/imports subpath residual (hono/jsx class) for LOCAL packages."""

    def test_exact_and_wildcard_exports_subpath(self):
        g = run_codemap({
            "package.json": '{"name":"root","workspaces":["packages/*"]}',
            "packages/core/package.json": '{"name":"@acme/core","exports":{'
                '"./jsx":"./src/jsx/index.ts","./features/*":"./src/features/*.ts"}}',
            "packages/core/src/jsx/index.ts": "export const jsx=1;\n",
            "packages/core/src/features/auth.ts": "export const a=1;\n",
            "packages/app/x.ts": "import {jsx} from '@acme/core/jsx';\n"
                                 "import {a} from '@acme/core/features/auth';\n",
        })
        e = edges(g)
        self.assertIn(("packages/app/x.ts", "packages/core/src/jsx/index.ts"), e)          # exact
        self.assertIn(("packages/app/x.ts", "packages/core/src/features/auth.ts"), e)      # wildcard *

    def test_conditional_dist_target_derives_to_source(self):
        # exports point ONLY at unbuilt dist -> derive the src path (hono's real shape).
        g = run_codemap({
            "package.json": '{"name":"hono","exports":{"./basic-auth":{'
                '"types":"./dist/types/middleware/basic-auth/index.d.ts",'
                '"import":"./dist/middleware/basic-auth/index.js"}}}',
            "src/middleware/basic-auth/index.ts": "export const b=1;\n",
            "src/app.ts": "import {b} from 'hono/basic-auth';\n",
        })
        self.assertIn(("src/app.ts", "src/middleware/basic-auth/index.ts"), edges(g))

    def test_subpath_of_external_package_not_fabricated(self):
        # `react-dom/client` — react-dom is NOT a local package -> stays external (soundness).
        g = run_codemap({
            "package.json": '{"name":"root","workspaces":["packages/*"]}',
            "packages/app/x.ts": "import c from 'react-dom/client';\n",
            "packages/app/client.ts": "export default 1;\n",  # coincidental local file
        })
        self.assertFalse(any("client" in t for _, t in edges(g)))

    def test_hash_imports_internal_specifier(self):
        g = run_codemap({
            "package.json": '{"name":"@acme/core","imports":{"#db/*":"./src/db/*.ts"}}',
            "src/db/client.ts": "export const c=1;\n",
            "src/service.ts": "import {c} from '#db/client';\n",
        })
        self.assertIn(("src/service.ts", "src/db/client.ts"), edges(g))


class GoArmTests(unittest.TestCase):
    def test_multi_package_fanout_and_test_exclusion(self):
        g = run_codemap({
            "go.mod": "module example.com/app\n",
            "main.go": 'package main\nimport (\n\tbar "example.com/app/bar"\n\t_ "example.com/app/baz"\n)\n',
            "bar/a.go": "package bar\n",
            "bar/b.go": "package bar\n",
            "bar/bar_test.go": "package bar\n",   # never an edge target
            "baz/baz.go": "package baz\n",         # blank import still an edge
        })
        e = edges(g)
        self.assertIn(("main.go", "bar/a.go"), e)
        self.assertIn(("main.go", "bar/b.go"), e)          # whole-package fan-out
        self.assertIn(("main.go", "baz/baz.go"), e)        # blank import
        self.assertNotIn(("main.go", "bar/bar_test.go"), e)  # _test.go excluded as target

    def test_soundness_stdlib_and_thirdparty_dropped(self):
        # The old floor bug: `import "errors"` fabricated an edge to a local errors.go. Gone.
        g = run_codemap({
            "go.mod": "module m\n",
            "context.go": 'package m\nimport (\n\t"errors"\n\t"context"\n\t"github.com/x/y"\n)\n',
            "errors.go": "package m\n",
        })
        self.assertEqual(edges(g), set())  # stdlib + third-party never edge

    def test_prefix_boundary_precision(self):
        g = run_codemap({
            "go.mod": "module github.com/me/proj\n",
            "x.go": 'package x\nimport (\n\t"github.com/me/project/util"\n\t"github.com/me/proj/util"\n)\n',
            "util/util.go": "package util\n",
        })
        # only the real-prefix import resolves; `project` is not a boundary prefix of `proj`
        self.assertEqual(edges(g), {("x.go", "util/util.go")})


class JavaArmTests(unittest.TestCase):
    def test_same_package_reference_no_import(self):
        # The core ~24% gap: same-package types need no import statement.
        g = run_codemap({
            "src/com/ex/A.java": "package com.ex;\nclass A { B b; void m(){ new B(); } "
                                 "String s = \"B not real here\"; }\n",
            "src/com/ex/B.java": "package com.ex;\nclass B { }\n",
        })
        e = edges(g)
        self.assertIn(("src/com/ex/A.java", "src/com/ex/B.java"), e)
        self.assertNotIn(("src/com/ex/B.java", "src/com/ex/A.java"), e)  # B never names A

    def test_inline_fqn_no_import(self):
        g = run_codemap({
            "src/com/ex/Client.java": "package com.ex;\nclass Client { void m(){ com.ex.util.Helper.run(); } }\n",
            "src/com/ex/util/Helper.java": "package com.ex.util;\npublic class Helper { public static void run(){} }\n",
        })
        self.assertIn(("src/com/ex/Client.java", "src/com/ex/util/Helper.java"), edges(g))

    def test_wildcard_import_resolves_used_types_only(self):
        g = run_codemap({
            "src/com/app/Main.java": "package com.app;\nimport com.app.model.*;\nclass Main { User u; }\n",
            "src/com/app/model/User.java": "package com.app.model;\npublic class User {}\n",
            "src/com/app/model/Ghost.java": "package com.app.model;\npublic class Ghost {}\n",
        })
        e = edges(g)
        self.assertIn(("src/com/app/Main.java", "src/com/app/model/User.java"), e)
        self.assertNotIn(("src/com/app/Main.java", "src/com/app/model/Ghost.java"), e)  # unused

    def test_soundness_jdk_and_unknown_dropped(self):
        g = run_codemap({
            "src/com/ex/Svc.java": "package com.ex;\nimport java.util.List;\nimport org.unknown.Widget;\n"
                                   "class Svc { List<String> xs; Widget w; Foo local; }\n",
        })
        self.assertEqual(edges(g), set())  # nothing declared in-repo -> no edge


class CSharpArmTests(unittest.TestCase):
    def test_using_resolves_with_intersection_precision(self):
        # `using App.Models` edges only to the type actually referenced (Order), not Customer.
        g = run_codemap({
            "Services/OrderService.cs": "namespace App.Services {\n using App.Models;\n"
                                        " public class OrderService { public Order Get() => new Order(); } }\n",
            "Models/Order.cs": "namespace App.Models {\n public class Order { } }\n",
            "Models/Customer.cs": "namespace App.Models {\n public class Customer { } }\n",
        })
        e = edges(g)
        self.assertIn(("Services/OrderService.cs", "Models/Order.cs"), e)
        self.assertNotIn(("Services/OrderService.cs", "Models/Customer.cs"), e)  # in ns, not used

    def test_same_namespace_no_using_and_file_scoped(self):
        g = run_codemap({
            "Handler.cs": "namespace App.Web;\nusing App.Data;\npublic class Handler { public Repo R; }\n",
            "Repo.cs": "namespace App.Data;\npublic class Repo { }\n",
            "Sibling.cs": "namespace App.Web;\npublic class Sibling { public Handler H; }\n",
        })
        e = edges(g)
        self.assertIn(("Handler.cs", "Repo.cs"), e)          # cross-ns via file-scoped using
        self.assertIn(("Sibling.cs", "Handler.cs"), e)       # same namespace, no using

    def test_soundness_system_and_unused_dropped(self):
        g = run_codemap({
            "Thing.cs": "using System;\nusing System.Collections.Generic;\nnamespace App;\n"
                        "public class Thing { public List<String> Names; public Guid Id; }\n",
            "Other.cs": "namespace App;\npublic class Other { }\n",
        })
        e = edges(g)
        self.assertEqual(e, set())  # System* not declared -> no edge; Other not referenced

    def test_partial_type_edges_to_all_parts(self):
        g = run_codemap({
            "Widget.Core.cs": "namespace UI;\npublic partial class Widget { public void Init() { } }\n",
            "Widget.Events.cs": "namespace UI;\npublic partial class Widget { public void Fire() { } }\n",
            "Screen.cs": "namespace UI;\npublic class Screen { public Widget W = new Widget(); }\n",
        })
        e = edges(g)
        self.assertIn(("Screen.cs", "Widget.Core.cs"), e)
        self.assertIn(("Screen.cs", "Widget.Events.cs"), e)   # partial -> all declaring files


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

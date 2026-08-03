#!/usr/bin/env python3
"""Fixture tests for the contract linter (stdlib unittest, zero-dep)."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_contracts as c  # noqa: E402

SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "check_contracts.py")


def _write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


def _skills(root, bodies):
    for name, body in bodies.items():
        _write(os.path.join(root, name, "SKILL.md"), body)

LOOP = """\
| node | on output | next |
|---|---|---|
| `discuss` | spec drafted | `execute` |
| `execute` | changelog | `idle` |

Side doors (callable from anywhere): `create-issue` → backlog · `research` (service).
"""

SCHEMAS = """\
- `commitment` ∈ `{ locked, provisional, unspecified }` — tagged per element
- `request` — `{ kind: demo|qa|setup, blocking: true }`
- `{ title, kind: bug|feature|debt, description }`
"""

# a minimal, fully-consistent skill set for the LOOP above
CLEAN = {"discuss": "body", "execute": "body", "create-issue": "body"}


class ParseLoop(unittest.TestCase):
    def test_nodes_targets_sidedoors(self):
        nodes, targets, doors = c.parse_loop(LOOP)
        self.assertEqual(nodes, {"discuss", "execute"})
        self.assertEqual(targets, {"execute", "idle"})
        self.assertEqual(doors, {"create-issue", "research"})

    def test_optional_marker_normalized(self):
        nodes, targets, _ = c.parse_loop("| `close-issue?` | x | `prioritize` |")
        self.assertIn("close-issue", nodes)


class ParseEnums(unittest.TestCase):
    def test_commitment_and_kind_union(self):
        commitment, kinds = c.parse_enums(SCHEMAS)
        self.assertEqual(commitment, {"locked", "provisional", "unspecified"})
        self.assertEqual(kinds, {"demo", "qa", "setup", "bug", "feature", "debt"})


class HardChecks(unittest.TestCase):
    def test_clean_graph_passes(self):
        hard, adv = c.check(LOOP, CLEAN, SCHEMAS)
        self.assertEqual(hard, [])
        self.assertEqual(adv, [])

    def test_dangling_target_blocks(self):
        loop = LOOP.replace("`idle`", "`nowhere`")
        hard, _ = c.check(loop, CLEAN, SCHEMAS)
        self.assertTrue(any("nowhere" in h for h in hard))

    def test_unrouted_mode_ref_blocks(self):
        skills = dict(CLEAN, document="injects a `document:audit` item")
        hard, _ = c.check(LOOP, skills, SCHEMAS)
        self.assertTrue(any("document:audit" in h for h in hard))

    def test_routed_mode_ref_ok(self):
        loop = LOOP.replace("| `execute` | changelog | `idle` |",
                            "| `execute` | changelog | `idle` |\n| `document:audit` | done | `idle` |")
        skills = dict(CLEAN, document="injects a `document:audit` item")
        hard, _ = c.check(loop, skills, SCHEMAS)
        self.assertEqual(hard, [])


class Advisories(unittest.TestCase):
    def test_coverage_gap_is_advisory_not_hard(self):
        skills = dict(CLEAN, ingest="brownfield entry")
        hard, adv = c.check(LOOP, skills, SCHEMAS)
        self.assertEqual(hard, [])
        self.assertTrue(any("ingest" in a for a in adv))

    def test_base_skill_exempt_from_coverage_gap(self):
        # an abstract base skill is specialized, not routed → not a coverage gap
        skills = dict(CLEAN, adjudicate="Base procedure ... Not invoked directly — specialized by verify.")
        _, adv = c.check(LOOP, skills, SCHEMAS)
        self.assertFalse(any("adjudicate" in a for a in adv))

    def test_commitment_hyphen_drift(self):
        skills = dict(CLEAN, discuss="tag flow to *locked-candidate*")
        _, adv = c.check(LOOP, skills, SCHEMAS)
        self.assertTrue(any("locked-candidate" in a for a in adv))

    def test_novel_kind_flagged(self):
        skills = dict(CLEAN, checkpoint="raise checkpoint(kind=reconcile)")
        # checkpoint is uncovered here too, but we only assert the kind advisory
        _, adv = c.check(LOOP, skills, SCHEMAS)
        self.assertTrue(any("reconcile" in a for a in adv))

    def test_known_kind_not_flagged(self):
        skills = dict(CLEAN, execute="raise checkpoint(kind=demo) and kind=debt")
        _, adv = c.check(LOOP, skills, SCHEMAS)
        self.assertFalse(any("kind=" in a for a in adv))


FORECAST = {
    "forecast_id": "item-1",
    "status": "draft",
    "events": [
        {"n": 1, "node": "discuss", "what": "settle the spec"},
        {"n": 2, "node": "execute", "what": "build it",
         "branch": [{"if": "the plan is wrong", "then": "discuss"}]},
        {"n": 3, "node": "idle", "what": "await steering"},
    ],
}


class ForecastGraph(unittest.TestCase):
    """`--forecast` — the GRAPH half of the forecast lint (D162 splits it by fact-domain:
    "does this event name a real node" is a loop.md question, so it lives here; the
    lifecycle half is forecast.py's). The whole point of D159's "every event NAMES a real
    loop.md node" is that it makes the forecast lintable — a prediction over the existing
    graph, never a second one."""

    def test_a_clean_forecast_passes(self):
        self.assertEqual(c.check_forecast(LOOP, FORECAST), [])

    def test_an_event_naming_no_node_blocks(self):
        fc = json.loads(json.dumps(FORECAST))
        fc["events"][1]["node"] = "summon-a-genie"
        hard = c.check_forecast(LOOP, fc)
        self.assertTrue(any("summon-a-genie" in h for h in hard), hard)

    def test_a_branch_target_naming_no_node_blocks(self):
        fc = json.loads(json.dumps(FORECAST))
        fc["events"][1]["branch"][0]["then"] = "nowhere"
        hard = c.check_forecast(LOOP, fc)
        self.assertTrue(any("nowhere" in h for h in hard), hard)

    def test_side_doors_and_terminals_resolve(self):
        fc = {"events": [{"n": 1, "node": "create-issue"}, {"n": 2, "node": "idle"}]}
        self.assertEqual(c.check_forecast(LOOP, fc), [])

    def test_a_node_mode_resolves_by_its_base(self):
        # `discuss:something` is not a row in LOOP, but `discuss` is a node — a mode of a
        # real node is a real place in the graph, the same rule `check` already uses.
        self.assertEqual(c.check_forecast(LOOP, {"events": [{"node": "discuss:refine"}]}), [])

    def test_an_event_with_no_node_is_itself_a_finding(self):
        hard = c.check_forecast(LOOP, {"events": [{"n": 1, "what": "something happens"}]})
        self.assertTrue(hard, "an event that names no node is unlintable, not clean")


class ForecastCli(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.loop = os.path.join(self.tmp, "loop.md")
        _write(self.loop, LOOP)

    def _run(self, obj, raw=None):
        p = os.path.join(self.tmp, "fc.json")
        _write(p, raw if raw is not None else json.dumps(obj))
        return subprocess.run([sys.executable, SCRIPT, "--forecast", p, "--loop", self.loop],
                              capture_output=True, text=True)

    def test_clean_forecast_exits_zero(self):
        r = self._run(FORECAST)
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_broken_forecast_exits_one(self):
        fc = json.loads(json.dumps(FORECAST))
        fc["events"][0]["node"] = "nope"
        r = self._run(fc)
        self.assertEqual(r.returncode, 1, r.stderr)
        self.assertIn("nope", r.stderr)

    def test_unparseable_forecast_is_a_usage_error_not_a_traceback(self):
        r = self._run(None, raw="{not json")
        self.assertNotIn("Traceback", r.stderr)
        self.assertEqual(r.returncode, 2, r.stderr)

    def test_forecast_mode_needs_no_skills_or_schemas(self):
        # the graph half is answerable from loop.md alone, so `--forecast` must not
        # inherit the package-wiring inputs (which an installed layout may not resolve).
        r = self._run(FORECAST)
        self.assertNotIn("NOT CHECKED", r.stderr)


class DefaultLayouts(unittest.TestCase):
    """`main()`'s zero-argument path — the one `align` actually uses.

    Both real layouts are exercised end-to-end as a SUBPROCESS from a copy of the
    script, because the defaults resolve off `__file__`: importing the module in
    place would test the source tree's location, never the installed one.
    """

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def _run(self, cwd, script, env=None, args=()):
        e = dict(os.environ)
        e.pop("CLAUDE_PLUGIN_ROOT", None)
        e.update(env or {})
        return subprocess.run([sys.executable, script, *args], cwd=cwd, env=e,
                              capture_output=True, text=True)

    def _installed(self, loop=LOOP):
        """`<project>/.claude/scripts/` + `<project>/.workflow/loop.md` + a plugin root."""
        proj = os.path.join(self.tmp, "proj")
        plugin = os.path.join(self.tmp, "plugin")
        script = os.path.join(proj, ".claude", "scripts", "check_contracts.py")
        os.makedirs(os.path.dirname(script))
        shutil.copy(SCRIPT, script)
        _write(os.path.join(proj, ".workflow", "loop.md"), loop)
        _skills(os.path.join(plugin, "skills"), CLEAN)
        _write(os.path.join(plugin, "shared", "schemas.md"), SCHEMAS)
        return proj, plugin, script


    # ---------------------------------------------- the split resolver
    # `schemas.md` is split, so the enum union must be taken across both halves. These pin
    # the two things that must stay true of that: it is FOLLOWED when it can be, and its
    # absence degrades with a message rather than the traceback this suite exists to prevent.

    def test_a_split_schema_is_read_across_both_halves(self):
        root, script = self._package()
        shared = os.path.join(root, "shared")
        _write(os.path.join(shared, "schemas.md"),
               SCHEMAS + "\n<!-- doc-budget: detail split -> schemas-runtime.md -->\n")
        _write(os.path.join(shared, "schemas-runtime.md"),
               "## config.json\n- `notify` — `kind: generic|slack`\n")
        shutil.copy(os.path.join(os.path.dirname(SCRIPT), "check_doc_budget.py"),
                    os.path.join(root, "scripts", "check_doc_budget.py"))
        _skills(os.path.join(root, "skills"), dict(CLEAN, extra="---\nname: extra\n---\nkind=slack\n"))
        r = self._run(root, script)
        # `slack` lives ONLY in the detail half — unfollowed, it would be a novel kind.
        self.assertNotIn("kind='slack'", r.stderr)

    def test_a_missing_split_resolver_degrades_loudly_never_tracebacks(self):
        root, script = self._package()      # copied WITHOUT check_doc_budget.py beside it
        _write(os.path.join(root, "shared", "schemas.md"),
               SCHEMAS + "\n<!-- doc-budget: detail split -> schemas-runtime.md -->\n")
        r = self._run(root, script)
        self.assertNotIn("Traceback", r.stderr)
        self.assertIn("could not be followed", r.stderr)

    def test_an_unsplit_schema_stays_quiet_without_the_resolver(self):
        """The degrade must not nag every project that never split anything."""
        root, script = self._package()
        r = self._run(root, script)
        self.assertNotIn("could not be followed", r.stderr)

    def _package(self):
        """`<root>/scripts/` + `<root>/templates/loop.md` — the meta-repo / plugin root."""
        root = os.path.join(self.tmp, "product")
        script = os.path.join(root, "scripts", "check_contracts.py")
        os.makedirs(os.path.dirname(script))
        shutil.copy(SCRIPT, script)
        _write(os.path.join(root, "templates", "loop.md"), LOOP)
        _skills(os.path.join(root, "skills"), CLEAN)
        _write(os.path.join(root, "shared", "schemas.md"), SCHEMAS)
        return root, script

    # --- the regression: align's exact invocation in a real install --------------
    def test_installed_layout_defaults_resolve(self):
        proj, plugin, script = self._installed()
        r = self._run(proj, script, {"CLAUDE_PLUGIN_ROOT": plugin})
        self.assertNotIn("Traceback", r.stderr)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("OK", r.stderr)

    def test_installed_layout_reads_workflow_loop_not_claude_templates(self):
        # the fact under test: the graph it lints is `.workflow/loop.md`, the copy the
        # orchestrator actually routes from — a break there must still block.
        proj, plugin, script = self._installed(loop=LOOP.replace("`idle`", "`nowhere`"))
        r = self._run(proj, script, {"CLAUDE_PLUGIN_ROOT": plugin})
        self.assertNotIn("Traceback", r.stderr)
        self.assertEqual(r.returncode, 1, r.stderr)
        self.assertIn("nowhere", r.stderr)

    def test_installed_layout_without_plugin_root_degrades_LOUDLY(self):
        # No plugin root ⇒ the package-wiring half is unreadable. `align` must not halt
        # (its own rule), but silence would read as "all clear" — so it must say so.
        proj, _plugin, script = self._installed()
        r = self._run(proj, script)
        self.assertNotIn("Traceback", r.stderr)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("NOT CHECKED", r.stderr)

    def test_installed_layout_missing_loop_is_a_clean_usage_error(self):
        proj, plugin, script = self._installed()
        os.remove(os.path.join(proj, ".workflow", "loop.md"))
        r = self._run(proj, script, {"CLAUDE_PLUGIN_ROOT": plugin})
        self.assertNotIn("Traceback", r.stderr)
        self.assertEqual(r.returncode, 2, r.stderr)
        self.assertIn(".workflow/loop.md", r.stderr)

    # --- the guard: the meta-repo pre-commit invocation keeps working ------------
    def test_package_layout_defaults_still_resolve(self):
        root, script = self._package()
        r = self._run(root, script)
        self.assertNotIn("Traceback", r.stderr)
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_explicit_paths_win_over_both_layouts(self):
        proj, plugin, script = self._installed()
        other = os.path.join(self.tmp, "other-loop.md")
        _write(other, LOOP.replace("`idle`", "`nowhere`"))
        r = self._run(proj, script, {"CLAUDE_PLUGIN_ROOT": plugin}, args=("--loop", other))
        self.assertEqual(r.returncode, 1, r.stderr)
        self.assertIn("nowhere", r.stderr)

    def test_explicit_missing_path_is_a_usage_error_not_a_traceback(self):
        proj, plugin, script = self._installed()
        r = self._run(proj, script, {"CLAUDE_PLUGIN_ROOT": plugin},
                      args=("--loop", os.path.join(self.tmp, "nope.md")))
        self.assertNotIn("Traceback", r.stderr)
        self.assertEqual(r.returncode, 2, r.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)

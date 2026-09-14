"""Tests for the documented-invocation gate.

The gate exists because the first smoke drive found `prioritize/SKILL.md` instructing the
orchestrator to run `converge.py status --workflow-dir .workflow`, which errors — `--workflow-dir`
is top-level and the subcommand comes last. A shipped instruction to run a command that cannot
run, invisible to 1,298 unit tests because every test calls these tools the way the tool itself
does.

The negative control is the test that matters, and it is here because the FIRST version of this
gate was a false green: it used a probe flag and its own logic swallowed the very error it was
looking for. A gate is not a gate until it has been seen to fail.
"""
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
GATE = os.path.join(HERE, "check_documented_invocations.py")


def _run():
    return subprocess.run([sys.executable, GATE], capture_output=True, text=True, cwd=ROOT)


class DocumentedInvocations(unittest.TestCase):
    def test_the_package_as_it_stands_is_clean(self):
        r = _run()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_it_catches_a_subcommand_after_a_toplevel_option(self):
        """The exact defect the live drive found, reintroduced and required to go red."""
        doc = os.path.join(ROOT, "product", "skills", "prioritize", "SKILL.md")
        original = open(doc, encoding="utf-8").read()
        broken = original.replace(
            "`python3 .claude/scripts/converge.py --workflow-dir .workflow status`",
            "`python3 .claude/scripts/converge.py status --workflow-dir .workflow`", 1)
        self.assertNotEqual(broken, original, "the anchor moved; update this test")
        try:
            with open(doc, "w", encoding="utf-8") as fh:
                fh.write(broken)
            r = _run()
            self.assertEqual(r.returncode, 1, "the gate stayed green on a broken invocation")
            self.assertIn("unrecognized arguments", r.stdout)
        finally:
            with open(doc, "w", encoding="utf-8") as fh:
                fh.write(original)

    def test_it_catches_a_documented_script_that_is_not_shipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            doc = os.path.join(ROOT, "product", "shared", "_gate_probe.md")
            try:
                with open(doc, "w", encoding="utf-8") as fh:
                    fh.write("Run `python3 .claude/scripts/no_such_tool.py status`.\n")
                r = _run()
                self.assertEqual(r.returncode, 1)
                self.assertIn("does not ship", r.stdout)
            finally:
                if os.path.exists(doc):
                    os.remove(doc)


if __name__ == "__main__":
    unittest.main()

"""The smoke drive's negative controls, in the routine suite.

The drive itself never runs here — it spends real model calls and takes about forty minutes.
What runs is the half that makes the other half worth trusting: every seam assertion is exercised
against a tree that satisfies it and against a tree that breaks it, and each break must turn
exactly one seam red. A forty-minute green light nobody has seen go red is not evidence.

The release gate gets the same treatment, because it is the thing that will actually make the
drive happen: an emit with no current receipt must be refused, and `--no-smoke` must be the only
way past it.
"""
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import smoke_drive as sd  # noqa: E402


class Seams(unittest.TestCase):
    def test_a_good_tree_passes_every_seam(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = sd._good_tree(os.path.join(tmp, "good"))
            red = [n for n, ok in sd._verdicts(repo).items() if not ok]
            self.assertEqual(red, [], "a tree with every seam intact went red")

    def test_every_seam_can_go_red_and_trips_nothing_else(self):
        for target, breaker in sd.BREAKS:
            with self.subTest(seam=target), tempfile.TemporaryDirectory() as tmp:
                repo = sd._good_tree(os.path.join(tmp, "broken"))
                breaker(repo)
                red = {n for n, ok in sd._verdicts(repo).items() if not ok}
                self.assertIn(target, red, "breaking `%s` did not turn it red" % target)
                self.assertEqual(red, {target},
                                 "breaking `%s` also tripped %s" % (target, red - {target}))

    def test_every_seam_has_a_break(self):
        """A seam with no negative control is a seam nobody has proved measures anything."""
        self.assertEqual(sorted(n for n, _ in sd.SEAMS), sorted(n for n, _ in sd.BREAKS))


class ReleaseGate(unittest.TestCase):
    def _emit(self, *extra):
        out = os.path.join(tempfile.mkdtemp(prefix="rel-"), "tree")
        return subprocess.run(
            [sys.executable, os.path.join(HERE, "build-release.py"), "--out", out, *extra],
            capture_output=True, text=True)

    def test_an_emit_without_a_current_receipt_is_refused(self):
        r = self._emit()
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("smoke", (r.stderr + r.stdout).lower())

    def test_no_smoke_is_the_explicit_way_past(self):
        """Named rather than silent: cutting a release without ever running the package as an
        installed whole should be a thing somebody typed."""
        r = self._emit("--no-smoke")
        self.assertEqual(r.returncode, 0, r.stderr)


if __name__ == "__main__":
    unittest.main()

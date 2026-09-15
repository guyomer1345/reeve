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

    def test_every_seam_can_go_red_and_trips_nothing_unexpected(self):
        """A break names the seam it must turn red, and may name others it is ALLOWED to trip.

        The allowance covers one honest case rather than serving as a general escape: a break
        that removes or rewrites a shipped file is supposed to be caught by `install closed`
        too — it compares bytes against the manifest — and calling its correct answer a false
        positive would train exactly the wrong reflex. Every other break still names one seam.
        """
        for target, breaker in sd.BREAKS:
            expected = {target} if isinstance(target, str) else set(target)
            primary = target if isinstance(target, str) else target[0]
            with self.subTest(seam=primary), tempfile.TemporaryDirectory() as tmp:
                repo = sd._good_tree(os.path.join(tmp, "broken"))
                breaker(repo)
                red = {n for n, ok in sd._verdicts(repo).items() if not ok}
                self.assertIn(primary, red, "breaking `%s` did not turn it red" % primary)
                self.assertEqual(red - expected, set(),
                                 "breaking `%s` also tripped %s" % (primary, red - expected))

    def test_every_seam_has_a_break(self):
        """A seam with no negative control is a seam nobody has proved measures anything."""
        covered = set()
        for target, _ in sd.BREAKS:
            covered |= {target} if isinstance(target, str) else set(target)
        self.assertEqual({n for n, _ in sd.SEAMS}, covered,
                         "a seam with no negative control, or a break for no seam")


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


# --- a resume is ONE tree, and a tree is ONE mode ----------------------------
# `--resume DIR` inherited the default `--mode both` and drove the single given tree twice, once
# under each label, then attested both. That is not a lost run: it is a receipt asserting that a
# bootstrap path was proven when that path never executed — and `build-release.py --out` trusts
# the receipt. Found by reading the first four lines of a real resume, which announced
# `=== greenfield ===` over a brownfield tree.

def test_a_seeded_tree_records_which_mode_built_it(tmp_path):
    repo = str(tmp_path / "anonymous-name")
    sd.seed(repo, "brownfield")
    assert sd.tree_mode(repo) == "brownfield", "the marker, not the directory name"


def test_the_marker_is_not_committed_into_the_repo_under_test(tmp_path):
    """Under `.git/`, or `git add -A` would put harness metadata into the diffs the seams read."""
    repo = str(tmp_path / "r")
    sd.seed(repo, "greenfield")
    tracked = subprocess.run(["git", "-C", repo, "ls-files"], capture_output=True, text=True)
    assert "smoke-mode" not in tracked.stdout


def test_an_old_tree_without_a_marker_falls_back_to_its_name(tmp_path):
    repo = tmp_path / "reeve-smoke-brownfield-abc123"
    (repo / ".git").mkdir(parents=True)
    assert sd.tree_mode(str(repo)) == "brownfield"


def test_a_tree_that_cannot_say_what_it_is_gets_REFUSED_not_guessed(tmp_path, capsys):
    repo = tmp_path / "some-tree"
    (repo / ".git").mkdir(parents=True)
    assert sd.tree_mode(str(repo)) is None
    assert sd.main(["--resume", str(repo)]) == 2
    assert "will not guess" in capsys.readouterr().out


def test_resume_does_not_inherit_mode_both(tmp_path, monkeypatch):
    """The defect itself: one tree, two modes, two attestations."""
    repo = str(tmp_path / "reeve-smoke-brownfield-xyz")
    os.makedirs(os.path.join(repo, ".git"))
    ran = []
    monkeypatch.setattr(sd.shutil, "which", lambda _n: "/usr/bin/claude")
    monkeypatch.setattr(sd, "run_mode", lambda m, *a, **k: ran.append(m) or False)
    sd.main(["--resume", repo])
    assert ran == ["brownfield"], "drove the same tree as both modes: %r" % ran


def test_a_contradicting_mode_flag_is_refused(tmp_path, capsys):
    repo = str(tmp_path / "reeve-smoke-brownfield-xyz")
    os.makedirs(os.path.join(repo, ".git"))
    assert sd.main(["--resume", repo, "--mode", "greenfield"]) == 2
    assert "contradicts the tree" in capsys.readouterr().out

"""The smoke drive's negative controls, in the routine suite.

The drive itself never runs here — it spends real model calls and takes about forty minutes.
What runs is the half that makes the other half worth trusting: every seam assertion is exercised
against a tree that satisfies it and against a tree that breaks it, and each break must turn
exactly one seam red. A forty-minute green light nobody has seen go red is not evidence.

The release gate gets the same treatment, because it is the thing that will actually make the
drive happen: an emit with no current receipt must be refused, and `--no-smoke` must be the only
way past it.
"""
import json
import os
import subprocess
import sys
import tempfile
import time
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
    # The plugin-currency guard is a different refusal and has its own tests; this one is about
    # which MODE a resume drives, and it must not depend on the state of a cache on this disk.
    monkeypatch.setattr(sd, "stale_plugin", lambda _repo=None: None)
    monkeypatch.setattr(sd, "run_mode", lambda m, *a, **k: ran.append(m) or False)
    sd.main(["--resume", repo])
    assert ran == ["brownfield"], "drove the same tree as both modes: %r" % ran


def test_a_contradicting_mode_flag_is_refused(tmp_path, capsys):
    repo = str(tmp_path / "reeve-smoke-brownfield-xyz")
    os.makedirs(os.path.join(repo, ".git"))
    assert sd.main(["--resume", repo, "--mode", "greenfield"]) == 2
    assert "contradicts the tree" in capsys.readouterr().out


class PluginCurrency(unittest.TestCase):
    """The hole a paid-for run found: the tree gets its scripts from the manifest at HEAD, but
    the SKILLS, COMMANDS and AGENTS come from the plugin cache, pinned at whatever was last
    installed. The first Phase-13 run drove `/reeve:start` from a plugin five commits old that
    predated every decision under test — and every seam stayed green, because they grade the
    tree and the tree was fine. A receipt that reads as proof while measuring a mixture is the
    exact failure this whole harness exists to prevent, one level up."""

    def _state(self, tmp, shas):
        path = os.path.join(tmp, "installed_plugins.json")
        with open(path, "w") as fh:
            json.dump({"plugins": {"reeve@reeve": [
                {"scope": "user", "gitCommitSha": s} for s in shas]}}, fh)
        return path

    def _with_state(self, path):
        old = sd.PLUGIN_STATE
        sd.PLUGIN_STATE = path
        self.addCleanup(setattr, sd, "PLUGIN_STATE", old)

    def _head(self):
        return subprocess.run(["git", "-C", sd.ROOT, "rev-parse", "HEAD"],
                              capture_output=True, text=True).stdout.strip()

    def test_a_plugin_at_HEAD_is_not_stale(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._with_state(self._state(tmp, [self._head()]))
            self.assertIsNone(sd.stale_plugin())

    def test_an_OLDER_plugin_is_refused_and_says_both_shas(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._with_state(self._state(tmp, ["0fdac78c024df8fc1032235f93097bc2ba07f45a"]))
            why = sd.stale_plugin()
            self.assertIn("0fdac78c024d", why)
            self.assertIn(self._head()[:12], why)

    def test_UNKNOWABLE_is_refused_too(self):
        """The failure being prevented is a receipt that reads as proof while measuring
        something else, so "cannot tell" must refuse exactly like "stale" does."""
        with tempfile.TemporaryDirectory() as tmp:
            self._with_state(os.path.join(tmp, "nothing-here.json"))
            self.assertIn("unreadable", sd.stale_plugin())

    def test_NO_reeve_plugin_at_all_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "installed_plugins.json")
            with open(path, "w") as fh:
                json.dump({"plugins": {"something-else@x": [{"gitCommitSha": "abc"}]}}, fh)
            self._with_state(path)
            self.assertIn("no `reeve` plugin", sd.stale_plugin())


class PluginCurrencyScope(unittest.TestCase):
    """The gate `D226` built deadlocked on its own exhaust, and it took one reinstall to see it.

    Every drive leaves a permanent `scope: local` registration for its throwaway `/tmp` tree,
    pinned at whatever was installed that day, and nothing removes it — seven had piled up. The
    gate compared the WHOLE record against HEAD, so from the second run onwards a correct
    reinstall could never satisfy it: the operator does exactly what the refusal instructs, is
    refused again, and the only door left is `--allow-stale`, which is the mixture the gate
    exists to refuse. A control whose only reachable outcome is its own override is worse than
    no control, because it reads as one."""

    def _write(self, tmp, rows):
        path = os.path.join(tmp, "installed_plugins.json")
        with open(path, "w") as fh:
            json.dump({"plugins": {"reeve@reeve": rows}}, fh)
        old = sd.PLUGIN_STATE
        sd.PLUGIN_STATE = path
        self.addCleanup(setattr, sd, "PLUGIN_STATE", old)

    def _head(self):
        return subprocess.run(["git", "-C", sd.ROOT, "rev-parse", "HEAD"],
                              capture_output=True, text=True).stdout.strip()

    OLD = "0fdac78c024df8fc1032235f93097bc2ba07f45a"

    def test_a_DEAD_local_registration_does_not_make_a_current_install_stale(self):
        """The measured deadlock: user-scope at HEAD, local-scope leftovers at an old sha."""
        with tempfile.TemporaryDirectory() as tmp:
            self._write(tmp, [
                {"scope": "local", "projectPath": "/tmp/reeve-smoke-greenfield-gone",
                 "gitCommitSha": self.OLD},
                {"scope": "user", "gitCommitSha": self._head()},
            ])
            self.assertIsNone(sd.stale_plugin())

    def test_a_local_registration_for_ANOTHER_LIVE_tree_is_still_out_of_scope(self):
        """Not an is-it-on-disk question. A local entry reaches exactly one directory, so a
        kept tree that this run is not driving cannot supply its skills either way."""
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as other:
            self._write(tmp, [
                {"scope": "local", "projectPath": other, "gitCommitSha": self.OLD},
                {"scope": "user", "gitCommitSha": self._head()},
            ])
            self.assertIsNone(sd.stale_plugin())

    def test_a_RESUME_into_a_tree_pinned_to_an_old_plugin_IS_refused(self):
        """The other half, and the reason this is scoping rather than filtering: the kept trees
        from the red run really are bound to the plugin that produced them, and `--resume` walks
        straight back into it. Dropping local entries wholesale would have gone quiet here."""
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as tree:
            self._write(tmp, [
                {"scope": "local", "projectPath": tree, "gitCommitSha": self.OLD},
                {"scope": "user", "gitCommitSha": self._head()},
            ])
            why = sd.stale_plugin(tree)
            self.assertIn("0fdac78c024d", why)

    def test_an_UNRECOGNISED_scope_still_governs_so_cannot_tell_refuses(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._write(tmp, [{"gitCommitSha": self.OLD}])
            self.assertIn("0fdac78c024d", sd.stale_plugin())

    def test_ONLY_local_entries_for_other_trees_reads_as_not_installed(self):
        """A fresh `/tmp` tree resolves nothing from another directory's local registration, so
        the honest answer is the same one an empty record gives — not a silent pass."""
        with tempfile.TemporaryDirectory() as tmp:
            self._write(tmp, [{"scope": "local", "projectPath": "/tmp/reeve-smoke-gone",
                               "gitCommitSha": self._head()}])
            self.assertIn("would not resolve", sd.stale_plugin())


class InstallLeak(unittest.TestCase):
    def test_a_directory_entry_HONOURS_the_manifest_exclude(self):
        """`scripts/codemap/test_codemap.py` landed in every tree this harness built, and the
        drive's own session found it at `/start` step 7 and could not delete it. The leak was
        the measuring instrument's, not the package's — `/start` gets this right in prose."""
        with tempfile.TemporaryDirectory() as tmp:
            repo = os.path.join(tmp, "t")
            os.makedirs(repo)
            sd.install_package(repo)
            leaked = []
            for root, dirs, files in os.walk(os.path.join(repo, ".claude")):
                dirs[:] = [d for d in dirs if d != "__pycache__"]
                leaked += [f for f in files if f.startswith("test_") and f.endswith(".py")]
            self.assertEqual(leaked, [], "an excluded file was installed into the tree")


class TimeoutDiagnosis(unittest.TestCase):
    """A timeout says nothing about WHICH failure it was, and the two want opposite fixes."""

    def test_a_quiet_tree_is_reported_as_STOPPED(self):
        with tempfile.TemporaryDirectory() as tmp:
            wf = os.path.join(tmp, ".workflow")
            os.makedirs(wf)
            with open(os.path.join(wf, "state.json"), "w") as fh:
                fh.write("{}")
            old = time.time() - 3600
            os.utime(os.path.join(wf, "state.json"), (old, old))
            self.assertIn("STOPPED", sd._was_it_moving(tmp))

    def test_a_LIVE_tree_is_reported_as_still_writing(self):
        with tempfile.TemporaryDirectory() as tmp:
            wf = os.path.join(tmp, ".workflow")
            os.makedirs(wf)
            with open(os.path.join(wf, "state.json"), "w") as fh:
                fh.write("{}")
            self.assertIn("still writing", sd._was_it_moving(tmp))

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
import shutil
import subprocess
import sys
import tempfile
import time
from unittest import mock
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
    exact failure this whole harness exists to prevent, one level up.

    The gate compares the PACKAGE, not `HEAD` — see `test_a_meta_only_commit_...` below for why
    the first version of it had to be rewritten."""

    CURRENT = os.path.join(sd.ROOT, "product")     # by construction, this repo's own package
    OLD_SHA = "0fdac78c024df8fc1032235f93097bc2ba07f45a"

    def _state(self, tmp, rows):
        path = os.path.join(tmp, "installed_plugins.json")
        with open(path, "w") as fh:
            json.dump({"plugins": {"reeve@reeve": rows}}, fh)
        old = sd.PLUGIN_STATE
        sd.PLUGIN_STATE = path
        self.addCleanup(setattr, sd, "PLUGIN_STATE", old)
        return path

    def _head(self):
        return subprocess.run(["git", "-C", sd.ROOT, "rev-parse", "HEAD"],
                              capture_output=True, text=True).stdout.strip()

    def _user(self, path=None, sha=None):
        return {"scope": "user", "gitCommitSha": sha or self._head(),
                "installPath": path or self.CURRENT}

    def _divergent(self, tmp):
        """A real install copy whose CONTENT differs by one shipped byte."""
        dst = os.path.join(tmp, "installed")
        shutil.copytree(self.CURRENT, dst)
        target = os.path.join(dst, "MANIFEST.json")
        with open(target, "a") as fh:
            fh.write("\n")
        return dst

    def test_an_install_carrying_this_package_is_not_stale(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._state(tmp, [self._user()])
            self.assertIsNone(sd.stale_plugin())

    def test_an_install_with_DIFFERENT_CONTENT_is_refused_and_names_both_digests(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._state(tmp, [self._user(path=self._divergent(tmp), sha=self.OLD_SHA)])
            why = sd.stale_plugin()
            self.assertIn("0fdac78c024d", why)
            self.assertIn(sd.package_digest()[:12], why)

    def test_a_META_ONLY_commit_does_NOT_invalidate_a_current_install(self):
        """THE REWRITE, in one test. Keying on `HEAD` was `D220`'s already-rejected mistake
        reappearing one layer up: the receipt is keyed on the shipped file set precisely because
        a commit that cannot change behaviour must not invalidate an attestation about
        behaviour. A gate keyed on `HEAD` refused after a fix to this very harness, and on a
        `--resume` the prescribed remedy cannot help — `dev-reinstall.sh` updates the user-scope
        install and cannot reach a kept tree's own local registration. That left `--allow-stale`
        as the only door, which is the deadlock this gate had already been rewritten once to
        escape. Measured: two installs, two commits apart, digesting identically."""
        with tempfile.TemporaryDirectory() as tmp:
            self._state(tmp, [self._user(sha="0" * 40)])   # same bytes, different commit
            self.assertIsNone(sd.stale_plugin())

    def test_an_install_MISSING_a_shipped_file_never_compares_equal(self):
        """An old install predating a file that now ships must not digest to "close enough"."""
        with tempfile.TemporaryDirectory() as tmp:
            dst = os.path.join(tmp, "partial")
            shutil.copytree(self.CURRENT, dst)
            os.remove(os.path.join(dst, "MANIFEST.json"))
            self._state(tmp, [self._user(path=dst)])
            self.assertIn("unreadable", sd.stale_plugin())

    def test_UNKNOWABLE_is_refused_too(self):
        """The failure being prevented is a receipt that reads as proof while measuring
        something else, so "cannot tell" must refuse exactly like "stale" does."""
        with tempfile.TemporaryDirectory() as tmp:
            old = sd.PLUGIN_STATE
            sd.PLUGIN_STATE = os.path.join(tmp, "nothing-here.json")
            self.addCleanup(setattr, sd, "PLUGIN_STATE", old)
            self.assertIn("unreadable", sd.stale_plugin())

    def test_NO_reeve_plugin_at_all_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "installed_plugins.json")
            with open(path, "w") as fh:
                json.dump({"plugins": {"something-else@x": [{"gitCommitSha": "abc"}]}}, fh)
            old = sd.PLUGIN_STATE
            sd.PLUGIN_STATE = path
            self.addCleanup(setattr, sd, "PLUGIN_STATE", old)
            self.assertIn("no `reeve` plugin", sd.stale_plugin())


class PluginCurrencyScope(PluginCurrency):
    """The gate deadlocked on its own exhaust, and it took one reinstall to see it.

    Every drive leaves a permanent `scope: local` registration for its throwaway `/tmp` tree,
    and nothing removes it — seven had piled up. The gate read the WHOLE record, so from the
    second run onwards a correct reinstall could never satisfy it: the operator does exactly
    what the refusal instructs, is refused again, and the only door left is `--allow-stale`,
    which is the mixture the gate exists to refuse. A control whose only reachable outcome is
    its own override is worse than no control, because it reads as one."""

    def test_a_DEAD_local_registration_does_not_make_a_current_install_stale(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._state(tmp, [
                {"scope": "local", "projectPath": "/tmp/reeve-smoke-greenfield-gone",
                 "gitCommitSha": self.OLD_SHA, "installPath": self._divergent(tmp)},
                self._user(),
            ])
            self.assertIsNone(sd.stale_plugin())

    def test_a_local_registration_for_ANOTHER_LIVE_tree_is_still_out_of_scope(self):
        """Not an is-it-on-disk question. A local entry reaches exactly one directory, so a
        kept tree that this run is not driving cannot supply its skills either way."""
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as other:
            self._state(tmp, [
                {"scope": "local", "projectPath": other, "gitCommitSha": self.OLD_SHA,
                 "installPath": self._divergent(tmp)},
                self._user(),
            ])
            self.assertIsNone(sd.stale_plugin())

    def test_a_RESUME_into_a_tree_pinned_to_an_older_PACKAGE_is_refused(self):
        """The other half, and the reason this is scoping rather than filtering: a kept tree is
        bound to the plugin that produced it, and `--resume` walks straight back into it."""
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as tree:
            self._state(tmp, [
                {"scope": "local", "projectPath": tree, "gitCommitSha": self.OLD_SHA,
                 "installPath": self._divergent(tmp)},
                self._user(),
            ])
            self.assertIn("0fdac78c024d", sd.stale_plugin(tree))

    def test_a_RESUME_into_a_tree_pinned_to_the_SAME_package_is_allowed(self):
        """The measured false refusal: the kept tree's local install was two commits old and
        byte-identical. Refusing there is what made the remedy unreachable."""
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as tree:
            self._state(tmp, [
                {"scope": "local", "projectPath": tree, "gitCommitSha": "0" * 40,
                 "installPath": self.CURRENT},
                self._user(),
            ])
            self.assertIsNone(sd.stale_plugin(tree))

    def test_an_UNRECOGNISED_scope_still_governs_so_cannot_tell_refuses(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._state(tmp, [{"gitCommitSha": self.OLD_SHA,
                               "installPath": self._divergent(tmp)}])
            self.assertIn("0fdac78c024d", sd.stale_plugin())

    def test_ONLY_local_entries_for_other_trees_reads_as_not_installed(self):
        """A fresh `/tmp` tree resolves nothing from another directory's local registration, so
        the honest answer is the same one an empty record gives — not a silent pass."""
        with tempfile.TemporaryDirectory() as tmp:
            self._state(tmp, [{"scope": "local", "projectPath": "/tmp/reeve-smoke-gone",
                               "installPath": self.CURRENT}])
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


class PreconditionsAreEvidence(unittest.TestCase):
    """Two steps that claimed more than they checked, and propped each other up doing it.

    A drive whose loop was blocked at intake reported `one item went round` as a PASS — `claude
    -p` exits 0 whenever the model finishes its turn, including the turn that explains it is
    blocked — and that PASS was exactly the evidence a reader needed to accept the worker-budget
    seam's unchecked precondition. The seam then declared the hook `a permanent no-op`, about a
    mechanism the other mode proved working on the same package digest an hour later. A false
    diagnosis in the fail direction is not the safe kind: it costs the next session a hunt for a
    bug that is not there, and it discredits the seam that was right."""

    def _wb(self, repo, *outcomes):
        d = os.path.join(repo, ".workflow", "worker-budget")
        os.makedirs(d, exist_ok=True)
        for o in outcomes:
            with open(os.path.join(d, o + ".json"), "w") as fh:
                json.dump({"outcome": o, "pct": 17.6, "used": 35172, "count": 70,
                           "fired": False}, fh)

    def _item(self, repo, ident, promoted=True):
        d = os.path.join(repo, ".workflow", "items", ident)
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "promoted.json"), "w") as fh:
            json.dump({"promoted": promoted}, fh)

    # -- the seam --------------------------------------------------------------------------

    def test_no_worker_ran_is_NOT_reported_as_a_broken_hook(self):
        """The measured false diagnosis. `no-agent-id` is the hook's NORMAL exit on the
        orchestrator's own tool calls; alone it is evidence of nothing."""
        with tempfile.TemporaryDirectory() as repo:
            self._wb(repo, "no-agent-id")
            with mock.patch.object(sd, "workers_ran", return_value=(0, "0 transcripts")):
                ok, why = sd.seam_worker_budget_saw_a_real_worker(repo)
            self.assertFalse(ok)
            self.assertIn("NO WORKER EVER RAN", why)
            self.assertNotIn("permanent no-op", why)

    def test_a_worker_that_DID_run_unseen_is_still_the_permanent_no_op_verdict(self):
        """The other half: scoping the claim must not cost the finding it was built for."""
        with tempfile.TemporaryDirectory() as repo:
            self._wb(repo, "no-agent-id")
            with mock.patch.object(sd, "workers_ran", return_value=(4, "4 transcripts")):
                ok, why = sd.seam_worker_budget_saw_a_real_worker(repo)
            self.assertFalse(ok)
            self.assertIn("permanent no-op", why)

    def test_CANNOT_TELL_refuses_rather_than_guessing_either_way(self):
        with tempfile.TemporaryDirectory() as repo:
            self._wb(repo, "no-agent-id")
            with mock.patch.object(sd, "workers_ran", return_value=(None, "no transcript dir")):
                ok, why = sd.seam_worker_budget_saw_a_real_worker(repo)
            self.assertFalse(ok)
            self.assertIn("cannot say", why)

    def test_located_still_passes_and_reads_the_worker(self):
        with tempfile.TemporaryDirectory() as repo:
            self._wb(repo, "no-agent-id", "located")
            ok, why = sd.seam_worker_budget_saw_a_real_worker(repo)
            self.assertTrue(ok, why)
            self.assertIn("17.6", why)

    # -- the step --------------------------------------------------------------------------

    def test_a_clean_session_exit_with_no_promoted_item_is_RED(self):
        with tempfile.TemporaryDirectory() as repo:
            ok, why = sd.an_item_actually_completed(repo, "all done!")
            self.assertFalse(ok)
            self.assertIn("no item dir was ever created", why)
            self.assertIn("all done!", why, "the session's own words must survive into the detail")

    def test_an_item_that_STARTED_but_never_promoted_is_RED_and_says_so(self):
        with tempfile.TemporaryDirectory() as repo:
            self._item(repo, "B-1", promoted=False)
            ok, why = sd.an_item_actually_completed(repo, "…")
            self.assertFalse(ok)
            self.assertIn("items started: B-1", why)

    def test_a_promoted_item_passes_and_names_it(self):
        with tempfile.TemporaryDirectory() as repo:
            self._item(repo, "B-1")
            ok, why = sd.an_item_actually_completed(repo, "…")
            self.assertTrue(ok, why)
            self.assertIn("B-1 promoted", why)


class PerModeWindow(unittest.TestCase):
    """One window could only ever be right for one mode. Greenfield was killed at exactly 1800s
    INSIDE `document`, with verify already passed on 18 tests, and took two more seams down with
    it — `document` owns the code-map rebuild and the resume anchor is written at turn end. Three
    reds, one event, and none of them a product defect."""

    def test_greenfield_gets_the_longer_window(self):
        self.assertGreater(sd.mode_timeout("greenfield"), sd.mode_timeout("brownfield"),
                           "greenfield builds from nothing; brownfield starts with code")

    def test_an_explicit_timeout_overrides_both(self):
        self.assertEqual(sd.mode_timeout("greenfield", 900), 900)
        self.assertEqual(sd.mode_timeout("brownfield", 900), 900)

    def test_an_unknown_mode_falls_back_rather_than_raising(self):
        self.assertEqual(sd.mode_timeout("nonesuch"), sd.DEFAULT_TIMEOUT)

    def test_the_brownfield_window_is_NOT_raised_to_match(self):
        """The window is also how fast a STALL is reported. Raising both would make a genuinely
        stopped brownfield session take twice as long to say so, for no gain."""
        self.assertEqual(sd.mode_timeout("brownfield"), sd.DEFAULT_TIMEOUT)

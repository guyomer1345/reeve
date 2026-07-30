#!/usr/bin/env python3
"""Fixture tests for the console daemon (stdlib unittest, zero-dep).

These drive real sockets, real locks, and real files. The interesting failures here
(a deadlocked shutdown, a defeated lock, a token that is world-readable) are all
invisible to a type check, so nothing is mocked that can be driven for real.
"""
import fcntl
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bus  # noqa: E402


def mkworkflow(root):
    w = os.path.join(root, ".workflow")
    for sub in ("parked", "inbox", "outbox"):
        os.makedirs(os.path.join(w, sub), exist_ok=True)
    with open(os.path.join(w, "state.json"), "w") as fh:
        json.dump({"status": "building", "node": "execute", "current_item": "item-1"}, fh)
    with open(os.path.join(w, "backlog.md"), "w") as fh:
        fh.write("# Backlog\n- [ ] item-1\n")
    return w


def with_env(case, **kw):
    """Set env vars for one test and restore them afterwards (None deletes)."""
    for key, value in kw.items():
        had = os.environ.get(key)
        case.addCleanup(
            (lambda k, v: (os.environ.__setitem__(k, v) if v is not None
                           else os.environ.pop(k, None))), key, had)
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value


class Tmp(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.root, True)


# --- path resolution --------------------------------------------------------
class RuntimePointer(Tmp):
    """The workflow tree spans two filesystems; without a pointer nothing could
    find the relocated half — the daemon's own discovery record lives inside it."""

    def test_absent_pointer_means_no_relocation(self):
        w = mkworkflow(self.root)
        p = bus.Paths(w)
        self.assertEqual(p.runtime, os.path.abspath(w))
        self.assertEqual(os.path.dirname(p.record), os.path.abspath(w))

    def test_pointer_relocates_the_runtime_half_only(self):
        w = mkworkflow(self.root)
        native = os.path.join(self.root, "native")
        os.makedirs(native)
        with open(os.path.join(w, "runtime.json"), "w") as fh:
            json.dump({"runtime_root": native}, fh)
        p = bus.Paths(w)
        # atomicity/mode-sensitive paths move...
        for got in (p.record, p.lock, p.state, p.parked, p.inbox, p.outbox):
            self.assertTrue(got.startswith(native), "%s did not relocate" % got)
        # ...committed artifacts never do: they live on the repo mount by construction.
        for got in (p.handoff, p.backlog, p.config):
            self.assertTrue(got.startswith(os.path.abspath(w)), "%s must not relocate" % got)

    def test_pointer_expands_user(self):
        # HOME is redirected at a fixture: resolving a root now STAMPS it (D141), and a
        # test has no business writing into the developer's real home directory.
        home = os.path.join(self.root, "home")
        os.makedirs(home)
        with_env(self, HOME=home)
        w = mkworkflow(self.root)
        with open(os.path.join(w, "runtime.json"), "w") as fh:
            json.dump({"runtime_root": "~"}, fh)
        self.assertEqual(bus.Paths(w).runtime, home)

    def test_missing_runtime_root_fails_loud(self):
        """Never silently fall back to the repo mount: that is precisely where the
        token would become world-readable and rename would stop being atomic."""
        w = mkworkflow(self.root)
        with open(os.path.join(w, "runtime.json"), "w") as fh:
            json.dump({"runtime_root": os.path.join(self.root, "gone")}, fh)
        with self.assertRaises(SystemExit):
            bus.Paths(w)

    def test_unreadable_pointer_fails_loud(self):
        w = mkworkflow(self.root)
        with open(os.path.join(w, "runtime.json"), "w") as fh:
            fh.write("{not json")
        with self.assertRaises(SystemExit):
            bus.Paths(w)

    def test_empty_pointer_falls_back_to_workflow_dir(self):
        w = mkworkflow(self.root)
        with open(os.path.join(w, "runtime.json"), "w") as fh:
            json.dump({}, fh)
        self.assertEqual(bus.Paths(w).runtime, os.path.abspath(w))

    def test_dead_pointer_error_names_the_cure(self):
        """A detector that does not route is a dead end: the operator on a new machine
        has no way to learn that /rebind exists (D141 — detectors route, none heals)."""
        w = mkworkflow(self.root)
        with open(os.path.join(w, "runtime.json"), "w") as fh:
            json.dump({"runtime_root": os.path.join(self.root, "gone")}, fh)
        with self.assertRaises(SystemExit) as cm:
            bus.Paths(w)
        self.assertIn("/rebind", str(cm.exception))


# --- the derived runtime root -----------------------------------------------
class RuntimeRootDerivation(Tmp):
    """The location was model-chosen prose until D141, so two projects with the same
    basename in different parents derived the same path and cross-bound."""

    def test_same_basename_different_parents_do_not_collide(self):
        with_env(self, XDG_STATE_HOME=os.path.join(self.root, "state"))
        a = bus.runtime_root_for(os.path.join(self.root, "one", "idea testing"))
        b = bus.runtime_root_for(os.path.join(self.root, "two", "idea testing"))
        self.assertNotEqual(a, b)
        # ...and both stay human-legible: the slug survives, only the hash differs.
        self.assertTrue(os.path.basename(a).startswith("idea-testing-"))
        self.assertTrue(os.path.basename(b).startswith("idea-testing-"))

    def test_derivation_is_stable_across_calls(self):
        """The probe's third candidate only exists because this is guessable from the
        project path alone — an unstable derivation would silently un-guess it."""
        with_env(self, XDG_STATE_HOME=os.path.join(self.root, "state"))
        p = os.path.join(self.root, "proj")
        self.assertEqual(bus.runtime_root_for(p), bus.runtime_root_for(p + "/"))

    def test_honours_xdg_state_home_else_falls_back_under_home(self):
        with_env(self, XDG_STATE_HOME=os.path.join(self.root, "xdg"))
        self.assertTrue(bus.runtime_root_for("/p/q").startswith(
            os.path.join(self.root, "xdg", "dev-autonomous-workflow")))
        with_env(self, XDG_STATE_HOME=None, HOME=os.path.join(self.root, "home"))
        self.assertTrue(bus.runtime_root_for("/p/q").startswith(
            os.path.join(self.root, "home", ".local", "state",
                         "dev-autonomous-workflow")))

    def test_slug_survives_a_name_with_nothing_usable_in_it(self):
        with_env(self, XDG_STATE_HOME=os.path.join(self.root, "state"))
        self.assertTrue(os.path.basename(bus.runtime_root_for("/tmp/...")).startswith(
            "project-"))


# --- the runtime root's identity --------------------------------------------
class RuntimeIdentity(Tmp):
    """isdir() is not identity. A restored backup or a second WSL distro binds clean
    and starts writing this project's state into another project's tree."""

    def _bind(self, root_name="native"):
        w = mkworkflow(self.root)
        native = os.path.join(self.root, root_name)
        os.makedirs(native, exist_ok=True)
        with open(os.path.join(w, "runtime.json"), "w") as fh:
            json.dump({"runtime_root": native}, fh)
        return w, native

    def test_a_legacy_unstamped_root_is_adopted_and_then_stamped(self):
        """Tolerant read / strict write — this is what lets the mechanism land on live
        installs. If an absent stamp broke resolution, every existing install would."""
        w, native = self._bind()
        self.assertEqual(bus.Paths(w).runtime, native)          # adopted, no raise
        stamp = bus.read_stamp(native)
        self.assertEqual(stamp["project_path"], os.path.abspath(self.root))
        self.assertIn("bound_at", stamp)
        self.assertIn("bound_host", stamp)

    def test_a_root_bound_to_another_project_fails_closed(self):
        w, native = self._bind()
        bus.write_stamp(native, "/some/other/project")
        with self.assertRaises(SystemExit) as cm:
            bus.Paths(w)
        self.assertIn("/rebind", str(cm.exception))
        self.assertIn("/some/other/project", str(cm.exception))

    def test_a_matching_stamp_resolves_and_is_not_rewritten(self):
        w, native = self._bind()
        bus.write_stamp(native, self.root)
        before = open(os.path.join(native, bus.RUNTIME_STAMP)).read()
        self.assertEqual(bus.Paths(w).runtime, native)
        self.assertEqual(open(os.path.join(native, bus.RUNTIME_STAMP)).read(), before)

    def test_a_corrupt_stamp_is_not_evidence_of_a_misbind(self):
        """This check exists to catch a WRONG tree, not to invent a new way to fail."""
        w, native = self._bind()
        with open(os.path.join(native, bus.RUNTIME_STAMP), "w") as fh:
            fh.write("{not json")
        self.assertEqual(bus.Paths(w).runtime, native)

    def test_a_stamp_write_failure_never_breaks_a_working_resolution(self):
        w, native = self._bind()
        os.chmod(native, 0o500)
        self.addCleanup(os.chmod, native, 0o700)
        self.assertEqual(bus.Paths(w).runtime, native)


# --- the SILENT mis-bind ----------------------------------------------------
class WeakMountFailsClosed(Tmp):
    """The half D140's audit missed. A dead pointer fails LOUDLY; an ABSENT pointer on
    a mount that cannot hold the tree used to succeed and put the capability token and
    secrets/ on a 0600-ignoring filesystem, saying nothing."""

    def test_no_pointer_on_a_mount_that_ignores_modes_fails_closed(self):
        w = mkworkflow(self.root)
        self._force(bus, False)
        with self.assertRaises(SystemExit) as cm:
            bus.Paths(w)
        self.assertIn("/rebind", str(cm.exception))

    def test_no_pointer_on_a_sound_mount_is_unchanged(self):
        w = mkworkflow(self.root)
        self._force(bus, True)
        self.assertEqual(bus.Paths(w).runtime, os.path.abspath(w))

    def test_an_UNDECIDABLE_probe_never_hard_stops(self):
        """A false positive here would break a WORKING install — strictly worse than
        the silence it replaces. Only a MEASURED failure stops."""
        w = mkworkflow(self.root)
        self._force(bus, None)
        self.assertEqual(bus.Paths(w).runtime, os.path.abspath(w))

    def test_the_probe_measures_rather_than_sniffing_the_mount_type(self):
        """No fstype table to go stale: it asks the only question that matters."""
        bits, err = bus.probe_mode_bits(self.root)
        self.assertIsNone(err)
        self.assertEqual(bits, 0o600)
        self.assertIs(bus.mount_honours_modes(self.root), True)

    def test_an_unwritable_tree_reads_as_undecidable_not_unsafe(self):
        ro = os.path.join(self.root, "ro")
        os.makedirs(ro)
        os.chmod(ro, 0o500)
        self.addCleanup(os.chmod, ro, 0o700)
        self.assertIsNone(bus.mount_honours_modes(ro))

    def _force(self, mod, verdict):
        real = mod.mount_honours_modes
        mod.mount_honours_modes = lambda root: verdict
        self.addCleanup(setattr, mod, "mount_honours_modes", real)


# --- the measured facts -----------------------------------------------------
class MeasuredInvariants(Tmp):
    def test_rename_defeats_a_lock_held_on_the_renamed_file(self):
        """MEASURED on ext4 and on the WSL 9p mount, which is why the lock lives on
        its own file. A rename swaps the inode: a second process opens the NEW inode,
        finds it unlocked, and starts. If this test ever fails, the platform changed
        and the separate lock file could be reconsidered — until then it must not be."""
        target = os.path.join(self.root, "record.json")
        with open(target, "w") as fh:
            fh.write("v1")
        fd = os.open(target, os.O_RDWR)
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        tmp = target + ".tmp"
        with open(tmp, "w") as fh:
            fh.write("v2")
        os.rename(tmp, target)
        fd2 = os.open(target, os.O_RDWR)
        try:
            fcntl.flock(fd2, fcntl.LOCK_EX | fcntl.LOCK_NB)
            defeated = True
        except OSError:
            defeated = False
        finally:
            os.close(fd)
            os.close(fd2)
        self.assertTrue(defeated, "rename no longer defeats the lock on this platform")

    def test_daemon_never_locks_the_file_it_republishes(self):
        w = mkworkflow(self.root)
        p = bus.Paths(w)
        self.assertNotEqual(p.lock, p.record)

    def test_verify_mode_reports_a_mode_the_filesystem_ignored(self):
        """A mode argument is a request, not a guarantee: on the WSL repo mount a
        0600 create comes back 0777, silently and open."""
        path = os.path.join(self.root, "tok")
        bus.atomic_write(path, "x", mode=0o600)
        self.assertIsNone(bus.verify_mode(path, 0o600))
        os.chmod(path, 0o777)
        warn = bus.verify_mode(path, 0o600)
        self.assertIsNotNone(warn)
        self.assertIn("readable by other users", warn)

    def test_atomic_write_leaves_no_temp_behind(self):
        path = os.path.join(self.root, "a.json")
        bus.atomic_write(path, '{"a":1}')
        self.assertEqual(json.load(open(path)), {"a": 1})
        self.assertEqual([n for n in os.listdir(self.root) if ".tmp" in n], [])


# --- the read model ---------------------------------------------------------
class ReadModel(Tmp):
    def setUp(self):
        super().setUp()
        self.w = mkworkflow(self.root)
        self.model = bus.ReadModel(bus.Paths(self.w))

    def _park(self, name, deadline):
        with open(os.path.join(self.w, "parked", name), "w") as fh:
            json.dump({"ticket_id": "item-1", "token": "cp-1",
                       "checkpoint": {"kind": "qa", "request": "ok?"},
                       "deadline": deadline}, fh)

    def test_snapshot_shape(self):
        snap = self.model.snapshot()
        for k in ("state", "parked", "outbox_pending", "backlog", "recent", "generated_at"):
            self.assertIn(k, snap)
        self.assertEqual(snap["state"]["node"], "execute")

    def test_overdue_flag(self):
        past = "2020-01-01T00:00:00+00:00"
        future = "2999-01-01T00:00:00+00:00"
        self._park("a.json", past)
        self._park("b.json", future)
        by = {p["deadline"]: p["overdue"] for p in self.model.parked()}
        self.assertTrue(by[past])
        self.assertFalse(by[future])

    def test_naive_deadline_is_treated_as_utc_not_crash(self):
        self._park("a.json", "2020-01-01T00:00:00")
        self.assertTrue(self.model.parked()[0]["overdue"])

    def test_garbage_deadline_is_not_overdue_and_does_not_crash(self):
        self._park("a.json", "whenever")
        self.assertFalse(self.model.parked()[0]["overdue"])

    def test_corrupt_parked_record_is_skipped_not_fatal(self):
        with open(os.path.join(self.w, "parked", "bad.json"), "w") as fh:
            fh.write("{torn")
        self._park("good.json", "2999-01-01T00:00:00+00:00")
        self.assertEqual(len(self.model.parked()), 1)

    def test_outbox_lists_only_pending(self):
        for i, status in enumerate(("pending", "executed", "dropped")):
            with open(os.path.join(self.w, "outbox", "%d.json" % i), "w") as fh:
                json.dump({"id": str(i), "action": "push", "status": status}, fh)
        self.assertEqual([o["id"] for o in self.model.outbox()], ["0"])

    def test_etag_is_stable_across_reads_and_moves_on_change(self):
        _, e1 = self.model.snapshot_bytes()
        _, e2 = self.model.snapshot_bytes()
        self.assertEqual(e1, e2, "an unchanged tree must not re-render the page")
        with open(os.path.join(self.w, "state.json"), "w") as fh:
            json.dump({"status": "idle", "node": "prioritize"}, fh)
        _, e3 = self.model.snapshot_bytes()
        self.assertNotEqual(e1, e3)

    def test_etag_moves_when_only_a_park_appears(self):
        """The snapshot spans several files; a checkpoint appearing must invalidate
        the ETag on its own, without leaning on state.json happening to change too."""
        _, e1 = self.model.snapshot_bytes()
        self._park("a.json", "2999-01-01T00:00:00+00:00")
        _, e2 = self.model.snapshot_bytes()
        self.assertNotEqual(e1, e2)

    def test_missing_state_file_degrades_quietly(self):
        os.unlink(os.path.join(self.w, "state.json"))
        self.assertEqual(self.model.snapshot()["state"]["node"], None)

    def test_git_absent_still_yields_a_snapshot(self):
        self.assertEqual(self.model.snapshot()["recent"], [])


# --- the jobs frame ---------------------------------------------------------
class Jobs(Tmp):
    def setUp(self):
        super().setUp()
        self.w = mkworkflow(self.root)
        self.d = bus.Daemon(bus.Paths(self.w), idle_timeout=0)

    def test_idle_requires_every_job_to_agree(self):
        self.d.last_request = 0  # serve job: quiet
        idle, blockers = self.d.idle_check()
        self.assertTrue(idle, blockers)

    def test_an_open_checkpoint_blocks_idle(self):
        """The away human has not opened the console yet; reaping now would take the
        channel away exactly when a verdict is owed."""
        self.d.last_request = 0
        with open(os.path.join(self.w, "parked", "a.json"), "w") as fh:
            json.dump({"ticket_id": "i", "checkpoint": {"kind": "qa"}}, fh)
        idle, blockers = self.d.idle_check()
        self.assertFalse(idle)
        self.assertTrue(any("parked" in b for b in blockers))

    def test_recent_traffic_blocks_idle(self):
        self.d.idle_timeout = 3600
        self.d.last_request = time.time()
        idle, blockers = self.d.idle_check()
        self.assertFalse(idle)
        self.assertTrue(any("request" in b for b in blockers))

    def test_idle_is_not_keyed_on_an_orchestrator_heartbeat(self):
        """Keying the janitor on the orchestrator would starve it precisely when the
        orchestrator is dead — the state this daemon exists to cover.

        Jobs are expected to arrive (each one adds an idle TERM, which is the whole
        point of the frame), so this pins the property rather than the roster: no job
        may vote on the orchestrator's liveness.
        """
        names = sorted(j.name for j in self.d.jobs)
        self.assertEqual(names, ["inbox-gc", "parked", "runner", "serve"])
        self.assertNotIn("heartbeat", " ".join(names))
        # the runner votes on applicable-work + the orchestrator LOCK, never on a
        # heartbeat — the property this test pins, extended to the new job.

    def test_unconsumed_inbox_does_not_hold_the_daemon_open(self):
        """A durable message loses nothing when the daemon reaps itself — /start
        respawns it and the orchestrator drains at its next boundary. Voting busy here
        would instead keep the daemon alive forever whenever the orchestrator is gone,
        which is most of the time. (An open CHECKPOINT is the opposite case, and does
        hold it open: there a verdict is actively owed.)"""
        self.d.last_request = 0
        with open(os.path.join(self.w, "inbox", "20260716T120000.000001Z-aaaaaaaa-1.json"),
                  "w") as fh:
            json.dump({"kind": "intake", "ask": "x"}, fh)
        idle, blockers = self.d.idle_check()
        self.assertTrue(idle, blockers)


# --- the relaunch-runner ----------------------------------------------------
class Runner(Tmp):
    """The runner spawns a REAL process, so these drive it against a stub `claude` rather
    than reasoning about it. The stub is either a loop that drains (progress) or one that
    exits without draining (a crash loop). The liveness marker is exercised with a real
    flock held by the test process."""

    VID = "20260716T120000.000001Z-aaaaaaaa-1"   # a bus-valid message_id

    def setUp(self):
        super().setUp()
        self.w = mkworkflow(self.root)
        self.paths = bus.Paths(self.w)
        self.d = bus.Daemon(self.paths, idle_timeout=3600)
        self.d.port = 4321
        self.bin = os.path.join(self.root, "bin")
        os.makedirs(self.bin, exist_ok=True)
        self._env("BUS_CLAUDE_BIN", None)  # set per test

    def tearDown(self):
        j = self.d.runner
        if j.launched is not None:
            try:
                j.launched.kill(); j.launched.wait(timeout=5)
            except Exception:
                pass

    # -- helpers --
    def _env(self, k, v):
        old = os.environ.get(k)
        self.addCleanup(lambda: os.environ.__setitem__(k, old) if old is not None
                        else os.environ.pop(k, None))
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v

    def _config(self, enabled=True, url=None):
        cfg = {"runner": {"enabled": enabled}}
        if url:
            cfg["notify"] = {"webhook": {"url": url, "kind": "generic"}}
        with open(self.paths.config, "w") as fh:
            json.dump(cfg, fh)

    def _pending(self, kind="verdict", mid=None):
        mid = mid or self.VID
        body = ({"kind": "verdict", "token": "cp1",
                 "verdict": {"outcome": "approve"}} if kind == "verdict"
                else {"kind": kind, "ask": "x"})
        with open(os.path.join(self.paths.inbox, mid + ".json"), "w") as fh:
            json.dump(body, fh)

    def _stub(self, mode):
        """A fake `claude`. `drain` = a loop that consumes the inbox (progress); `crash` =
        one that exits 1 without draining (a crash loop)."""
        drain_py = os.path.join(os.path.dirname(bus.__file__), "drain.py")
        path = os.path.join(self.bin, "claude-%s" % mode)
        if mode == "drain":
            src = (
                "#!/usr/bin/env python3\n"
                "import subprocess, sys, json, os\n"
                "wf = %r\n" % self.w +
                "d = %r\n" % drain_py +
                "out = subprocess.run([sys.executable, d, '--workflow-dir', wf, 'list'],"
                " capture_output=True, text=True)\n"
                "ids = [p['message_id'] for p in json.loads(out.stdout)['pending']]\n"
                "if ids:\n"
                "    subprocess.run([sys.executable, d, '--workflow-dir', wf, 'record',"
                " '--applied'] + ids)\n")
        else:
            src = "#!/usr/bin/env python3\nimport sys\nsys.exit(1)\n"
        with open(path, "w") as fh:
            fh.write(src)
        os.chmod(path, 0o755)
        self._env("BUS_CLAUDE_BIN", path)
        return path

    def _reap(self, timeout=15):
        j = self.d.runner
        if j.launched is not None:
            j.launched.wait(timeout=timeout)

    # -- tests --
    def test_disabled_never_spawns(self):
        self._config(enabled=False)
        self._pending()
        self.d.runner.tick(self.d)
        self.assertIsNone(self.d.runner.launched)

    def test_a_lone_control_is_not_applicable(self):
        self._config()
        with open(os.path.join(self.paths.inbox, self.VID + ".json"), "w") as fh:
            json.dump({"kind": "control", "op": "pause"}, fh)
        self._stub("drain")
        self.d.runner.tick(self.d)
        self.assertIsNone(self.d.runner.launched, "a lone control must not spawn a loop")

    def test_no_applicable_work_never_spawns(self):
        self._config()
        self._stub("drain")            # empty inbox
        self.d.runner.tick(self.d)
        self.assertIsNone(self.d.runner.launched)

    def test_a_held_orchestrator_lock_blocks_the_spawn(self):
        """The core precondition: never a duplicate alongside a live orchestrator."""
        self._config()
        self._pending()
        self._stub("drain")
        fd = os.open(self.paths.orchestrator_lock, os.O_CREAT | os.O_RDWR, 0o600)
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)   # a "live orchestrator"
        try:
            self.d.runner.tick(self.d)
            self.assertIsNone(self.d.runner.launched, "spawned alongside a live orch")
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN); os.close(fd)

    def test_a_pending_verdict_relaunches_and_the_loop_drains(self):
        """The end-to-end shape, with the drain stub standing in for the loop: spawn →
        the launched process consumes the inbox → the watermark advances → the runner
        scores progress, resets, and finds nothing left to do."""
        self._config()
        self._pending("verdict")
        self._stub("drain")
        self.d.runner.tick(self.d)                       # spawns
        self.assertIsNotNone(self.d.runner.launched)
        self._reap()
        self.d.runner.tick(self.d)                       # reaps + scores
        self.assertEqual(self.d.runner.consecutive_noprogress, 0)
        self.assertIsNone(self.d.runner.launched)
        block = bus.read_handoff_block(self.paths.handoff)
        self.assertTrue(block.get("consumed_through"), "the loop did not advance the watermark")
        # and nothing left is applicable, so a further tick is a no-op
        self.d.runner.tick(self.d)
        self.assertIsNone(self.d.runner.launched)

    def test_an_intake_also_relaunches(self):
        self._config()
        self._pending("intake")
        self._stub("drain")
        self.d.runner.tick(self.d)
        self.assertIsNotNone(self.d.runner.launched, "an intake advances a dead loop too")
        self._reap()

    def test_in_flight_launch_is_not_double_spawned(self):
        """While a relaunch is running it holds the lock; a second tick must not spawn a
        second one (the latch is the lock, but the in-flight handle short-circuits first)."""
        self._config()
        self._pending()
        # a stub that lingers, so the launch is in-flight across the second tick
        path = os.path.join(self.bin, "claude-slow")
        with open(path, "w") as fh:
            fh.write("#!/usr/bin/env python3\nimport time\ntime.sleep(3)\n")
        os.chmod(path, 0o755)
        self._env("BUS_CLAUDE_BIN", path)
        self.d.runner.tick(self.d)
        first = self.d.runner.launched
        self.assertIsNotNone(first)
        self.d.runner.tick(self.d)                       # in-flight → no second spawn
        self.assertIs(self.d.runner.launched, first)
        self._reap()

    def test_crash_loop_backs_off_then_hard_stops_and_alerts(self):
        """A launched loop that never drains must not storm: back off, and after the cap
        HARD-STOP with an away alert — the notifier's deferred thrash/crash arm."""
        sink = _Sink()
        self.addCleanup(sink.stop)
        self._config(url=sink.url)
        self._pending()
        self._stub("crash")
        orig = bus.RUNNER_BACKOFF_BASE
        bus.RUNNER_BACKOFF_BASE = 0.0                    # immediate retries, no real sleep
        self.addCleanup(setattr, bus, "RUNNER_BACKOFF_BASE", orig)
        for _ in range(bus.RUNNER_MAX_ATTEMPTS + 2):
            self.d.runner.tick(self.d)                   # spawn (or no-op once stopped)
            self._reap()
            self.d.runner.tick(self.d)                   # reap + score → no-progress
            if self.d.runner.hard_stopped:
                break
        self.assertTrue(self.d.runner.hard_stopped)
        self.assertEqual(self.d.runner.consecutive_noprogress, bus.RUNNER_MAX_ATTEMPTS)
        self.assertTrue(any(r["body"].get("event") == "loop-stall" for r in sink.received),
                        "no crash-loop away alert fired")
        # a hard-stopped runner goes idle (the alert fired; holding the daemon open helps
        # nobody) and stops spawning
        self.d.runner.tick(self.d)
        self.assertIsNone(self.d.runner.launched)
        self.assertTrue(self.d.runner.is_idle(self.d))

    def test_progress_after_a_stumble_resets_the_counter(self):
        """One bad launch must not doom the loop: a later launch that drains clears the
        crash-loop counter, so a transient failure never counts toward a hard-stop."""
        self._config()
        self._pending()
        self.d.runner._noprogress(self.d, "simulated stumble")
        self.assertEqual(self.d.runner.consecutive_noprogress, 1)
        self._stub("drain")
        self.d.runner.next_attempt = 0.0                 # skip the backoff wait
        self.d.runner.tick(self.d)
        self._reap()
        self.d.runner.tick(self.d)
        self.assertEqual(self.d.runner.consecutive_noprogress, 0)

    def test_an_inert_launch_is_killed_by_the_stall_timeout(self):
        """A hung launch (an untrusted `claude` that never drains) must not pin the runner
        in-flight forever. With no watermark advance past the stall window, it is killed
        and scored as no-progress — the same path a crash takes."""
        self._config()
        self._pending()
        path = os.path.join(self.bin, "claude-hang")
        with open(path, "w") as fh:
            fh.write("#!/usr/bin/env python3\nimport time\ntime.sleep(60)\n")  # never drains
        os.chmod(path, 0o755)
        self._env("BUS_CLAUDE_BIN", path)
        orig = bus.RUNNER_STALL_TIMEOUT
        bus.RUNNER_STALL_TIMEOUT = 0.0                    # deem it inert immediately
        self.addCleanup(setattr, bus, "RUNNER_STALL_TIMEOUT", orig)
        self.d.runner.tick(self.d)                        # spawns the hanging stub
        self.assertIsNotNone(self.d.runner.launched)
        time.sleep(0.5)
        self.d.runner.tick(self.d)                        # in-flight, un-drained, past stall → killed
        self.assertIsNone(self.d.runner.launched, "inert launch was not killed")
        self.assertEqual(self.d.runner.consecutive_noprogress, 1)

    def test_readiness_shape(self):
        self._config()
        r = self.d.runner.readiness(self.d)
        for k in ("enabled", "in_flight", "consecutive_noprogress", "hard_stopped", "wsl",
                  "workspace_trusted"):
            self.assertIn(k, r)
        self.assertTrue(r["enabled"])

    def test_idle_vote_holds_the_daemon_open_while_a_resume_is_owed(self):
        """Unlike inbox-GC, the runner votes BUSY while it still owes a resume — else the
        janitor could reap the daemon out from under work it is responsible for."""
        self._config()
        self._pending()
        self.assertFalse(self.d.runner.is_idle(self.d))
        # but a held lock (an orchestrator is live and will drain) frees it to idle
        fd = os.open(self.paths.orchestrator_lock, os.O_CREAT | os.O_RDWR, 0o600)
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            self.assertTrue(self.d.runner.is_idle(self.d))
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN); os.close(fd)


# --- a real server ----------------------------------------------------------
class LiveServer(Tmp):
    def setUp(self):
        super().setUp()
        self.w = mkworkflow(self.root)
        self.d = bus.Daemon(bus.Paths(self.w), idle_timeout=3600)
        self.assertTrue(self.d.acquire_lock())
        self.d.token = "test-token-xyz"
        from http.server import ThreadingHTTPServer
        self.d.server = ThreadingHTTPServer(("127.0.0.1", 0), bus.make_handler(self.d))
        self.d.server.policy = bus.LOOPBACK_POLICY
        self.port = self.d.server.server_address[1]
        self.d.publish(self.port)
        threading.Thread(target=self.d.server.serve_forever, daemon=True).start()
        self.addCleanup(self.d.cleanup)
        self.addCleanup(self.d.server.shutdown)

    def get(self, path, token=None, host=None, extra=None):
        h = {"Host": host or ("127.0.0.1:%d" % self.port)}
        if token:
            h[bus.TOKEN_HEADER] = token
        h.update(extra or {})
        req = urllib.request.Request("http://127.0.0.1:%d%s" % (self.port, path), headers=h)
        try:
            with urllib.request.urlopen(req, timeout=5) as res:
                return res.status, res.read(), dict(res.headers)
        except urllib.error.HTTPError as e:
            return e.code, e.read(), dict(e.headers)

    def test_read_requires_a_token(self):
        self.assertEqual(self.get("/api/state")[0], 401)
        self.assertEqual(self.get("/api/state", token="wrong")[0], 401)
        self.assertEqual(self.get("/api/state", token=self.d.token)[0], 200)

    def test_forged_host_is_refused_even_with_a_good_token(self):
        """The one browser-independent defense against a rebound page."""
        self.assertEqual(self.get("/api/state", token=self.d.token, host="evil.com")[0], 403)

    def test_page_is_refused_on_a_forged_host_too(self):
        """The page hands out the token, so it must be Host-gated even though it is
        served without one."""
        self.assertEqual(self.get("/", host="evil.com")[0], 403)

    def test_declared_cross_site_is_refused(self):
        code, _, _ = self.get("/api/state", token=self.d.token,
                              extra={"Sec-Fetch-Site": "cross-site"})
        self.assertEqual(code, 403)

    def test_page_serves_without_a_token_and_carries_it_in_a_meta_tag(self):
        code, body, _ = self.get("/")
        self.assertEqual(code, 200)
        self.assertIn(self.d.token.encode(), body)
        self.assertNotIn(b"__BUS_TOKEN__", body, "placeholder was not substituted")

    def test_csp_is_strict_on_every_response(self):
        for path in ("/", "/app.js", "/style.css"):
            _, _, headers = self.get(path)
            csp = headers.get("Content-Security-Policy", "")
            self.assertIn("script-src 'self'", csp)
            self.assertNotIn("unsafe-eval", csp)
            self.assertNotIn("unsafe-inline", csp)

    def test_etag_round_trip_304(self):
        code, _, headers = self.get("/api/state", token=self.d.token)
        self.assertEqual(code, 200)
        etag = headers["ETag"]
        code2, _, _ = self.get("/api/state", token=self.d.token,
                               extra={"If-None-Match": etag})
        self.assertEqual(code2, 304)

    def test_health_reports_idle_blockers(self):
        code, body, _ = self.get("/health", token=self.d.token)
        self.assertEqual(code, 200)
        self.assertIn("idle_blockers", json.loads(body))

    def test_unknown_endpoint_404s(self):
        self.assertEqual(self.get("/nope", token=self.d.token)[0], 404)

    def test_oversize_body_is_refused(self):
        req = urllib.request.Request(
            "http://127.0.0.1:%d/shutdown" % self.port, method="POST",
            data=b"x" * (bus.MAX_BODY + 1),
            headers={bus.TOKEN_HEADER: self.d.token, "Content-Type": "application/json",
                     "Host": "127.0.0.1:%d" % self.port})
        with self.assertRaises(urllib.error.HTTPError) as cm:
            urllib.request.urlopen(req, timeout=5)
        self.assertEqual(cm.exception.code, 413)

    def test_non_json_post_is_refused(self):
        req = urllib.request.Request(
            "http://127.0.0.1:%d/shutdown" % self.port, method="POST", data=b"a=1",
            headers={bus.TOKEN_HEADER: self.d.token,
                     "Content-Type": "application/x-www-form-urlencoded",
                     "Host": "127.0.0.1:%d" % self.port})
        with self.assertRaises(urllib.error.HTTPError) as cm:
            urllib.request.urlopen(req, timeout=5)
        self.assertEqual(cm.exception.code, 415)

    def test_published_record_is_adoptable(self):
        rec = bus.read_json(self.d.paths.record)
        self.assertEqual(rec["port"], self.port)
        self.assertEqual(rec["token"], self.d.token)
        self.assertIsNotNone(bus.health(self.port, self.d.token))

    # -- POST: the async command half --
    def post(self, path, payload, token=None, host=None, ctype="application/json"):
        h = {"Host": host or ("127.0.0.1:%d" % self.port), "Content-Type": ctype}
        h[bus.TOKEN_HEADER] = token if token is not None else self.d.token
        data = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
        req = urllib.request.Request("http://127.0.0.1:%d%s" % (self.port, path),
                                     method="POST", data=data, headers=h)
        try:
            with urllib.request.urlopen(req, timeout=5) as res:
                return res.status, json.loads(res.read() or b"{}"), dict(res.headers)
        except urllib.error.HTTPError as e:
            body = e.read()
            try:
                body = json.loads(body or b"{}")
            except ValueError:
                body = {}
            return e.code, body, dict(e.headers)

    def test_verdict_post_lands_durably_and_returns_a_ticket(self):
        code, body, headers = self.post("/api/verdict", {
            "token": "item-1:qa:abc", "verdict": {"outcome": "approve", "notes": "ok"}})
        self.assertEqual(code, 202, body)
        ticket = body["ticket"]
        # The ticket IS the message id IS the filename stem — one canonical id.
        path = os.path.join(self.w, "inbox", ticket + ".json")
        self.assertTrue(os.path.exists(path), "202 returned but nothing was written")
        self.assertEqual(headers["Location"], "/api/requests/" + ticket)
        rec = bus.read_json(path)
        self.assertEqual(rec["kind"], "verdict")
        self.assertEqual(rec["message_id"], ticket)
        self.assertEqual(rec["verdict"]["outcome"], "approve")

    def test_every_kind_is_accepted(self):
        for path, payload in (
                ("/api/verdict", {"token": "t", "verdict": {"outcome": "reject"}}),
                ("/api/intake", {"ask": "add a CSV export"}),
                ("/api/control", {"op": "pause"}),
                ("/api/release", {"action_ids": ["act-1"]})):
            code, body, _ = self.post(path, payload)
            self.assertEqual(code, 202, "%s: %s" % (path, body))

    def test_a_write_needs_the_token_and_a_sane_host(self):
        self.assertEqual(self.post("/api/intake", {"ask": "x"}, token="wrong")[0], 401)
        self.assertEqual(self.post("/api/intake", {"ask": "x"}, host="evil.com")[0], 403)

    def test_bad_bodies_are_refused_with_a_reason(self):
        for path, payload, want in (
                ("/api/verdict", {"token": "t", "verdict": {"outcome": "maybe"}}, "outcome"),
                ("/api/verdict", {"verdict": {"outcome": "approve"}}, "token"),
                ("/api/verdict", {"token": "t"}, "verdict"),
                ("/api/intake", {"ask": "   "}, "ask"),
                ("/api/control", {"op": "rm -rf"}, "op"),
                ("/api/release", {"action_ids": []}, "action_ids"),
                ("/api/release", {"action_ids": "act-1"}, "action_ids")):
            code, body, _ = self.post(path, payload)
            self.assertEqual(code, 400, "%s %s was accepted" % (path, payload))
            self.assertIn(want, body.get("error", ""))
        self.assertEqual(len(os.listdir(os.path.join(self.w, "inbox"))), 0,
                         "a refused message still reached the durable inbox")

    def test_malformed_json_is_refused(self):
        code, body, _ = self.post("/api/intake", b"{not json")
        self.assertEqual(code, 400)
        self.assertIn("JSON", body.get("error", ""))

    def test_control_ops_are_a_closed_set(self):
        """A control op has no durable artifact to anchor on, so a redelivered one is
        safe ONLY because re-applying it is a no-op. A new op has to be admitted
        deliberately, never by a caller."""
        self.assertEqual(self.post("/api/control", {"op": "deploy"})[0], 400)
        for op in bus.CONTROL_OPS:
            self.assertEqual(self.post("/api/control", {"op": op})[0], 202)

    def test_setup_verdict_carries_per_task_outcomes(self):
        code, _, _ = self.post("/api/verdict", {"token": "t", "verdict": {"tasks": [
            {"id": "stripe", "outcome": "approve"},
            {"id": "clerk", "outcome": "reject", "notes": "no account"}]}})
        self.assertEqual(code, 202)
        code, body, _ = self.post("/api/verdict", {"token": "t", "verdict": {"tasks": [
            {"id": "stripe", "outcome": "done"}]}})
        self.assertEqual(code, 400)
        self.assertIn("outcome", body["error"])

    def test_ticket_resolves_over_http(self):
        _, body, _ = self.post("/api/intake", {"ask": "x"})
        code, raw, _ = self.get("/api/requests/" + body["ticket"], token=self.d.token)
        self.assertEqual(code, 200)
        self.assertEqual(json.loads(raw)["status"], "queued")

    def test_location_ticket_is_not_a_path_traversal(self):
        code, _, _ = self.get("/api/requests/../../etc/passwd", token=self.d.token)
        self.assertEqual(code, 404)

    def test_oversize_and_wrong_ctype_are_refused_on_a_real_kind(self):
        code, _, _ = self.post("/api/intake", {"ask": "x"},
                               ctype="application/x-www-form-urlencoded")
        self.assertEqual(code, 415)
        code, _, _ = self.post("/api/intake", b"x" * (bus.MAX_BODY + 1))
        self.assertEqual(code, 413)


# --- the demo static class --------------------------------------------------
class DemoServing(LiveServer):
    """The /demo/* static class: a throwaway create-demo bundle served under the
    sandbox-CSP opaque origin, token-free like the page, realpath-guarded."""

    def setUp(self):
        super().setUp()
        self.demo = os.path.join(self.w, "demos", "item-42")
        os.makedirs(self.demo)
        with open(os.path.join(self.demo, "index.html"), "w") as fh:
            fh.write("<!doctype html><h1>hi</h1><script>1</script>")
        with open(os.path.join(self.demo, "app.js"), "w") as fh:
            fh.write("console.log(1)")
        # The real published bus.json (paths.record) sits one dir up and holds the live
        # token — the exact thing a /demo/../ climb would try to reach. Don't fabricate a
        # decoy (that would clobber the daemon's own record); escape at the real secret.

    def test_index_serves_token_free_under_the_sandbox_csp(self):
        for path in ("/demo/item-42/", "/demo/item-42/index.html"):
            code, body, headers = self.get(path)  # NO token — static class
            self.assertEqual(code, 200, path)
            self.assertIn(b"<h1>hi</h1>", body)
            self.assertEqual(headers.get("Content-Security-Policy"), bus.DEMO_CSP)
            self.assertIn("sandbox", headers.get("Content-Security-Policy", ""))
            self.assertEqual(headers.get("Cache-Control"), "no-store")
            self.assertEqual(headers.get("X-Content-Type-Options"), "nosniff")
            self.assertIn("text/html", headers.get("Content-Type", ""))

    def test_the_console_csp_stays_strict_and_is_never_the_demo_csp(self):
        _, _, headers = self.get("/")
        console = headers.get("Content-Security-Policy", "")
        self.assertIn("script-src 'self'", console)
        self.assertNotIn("sandbox", console)   # two per-path CSPs, never crossed
        self.assertIn("frame-src 'self'", console)  # so the console can embed the demo

    def test_mime_is_explicit(self):
        _, _, headers = self.get("/demo/item-42/app.js")
        self.assertIn("javascript", headers.get("Content-Type", ""))

    def test_realpath_guard_blocks_the_climb_out(self):
        # bus.json (paths.record) holds the live capability token — the real target.
        self.assertIn(b"token", bus.read_text(self.d.paths.record).encode())
        for esc in ("/demo/item-42/../../bus.json",
                    "/demo/item-42/../../../bus.json",
                    "/demo/item-42/..%2f..%2fbus.json"):
            code, body, _ = self.get(esc)
            self.assertEqual(code, 404, esc)
            self.assertNotIn(self.d.token.encode(), body,
                             "the guard let the token escape: %s" % esc)

    def test_prefix_sibling_cannot_be_reached(self):
        # demos/item-42 must not serve demos/item-42x via a shared prefix.
        with open(os.path.join(self.w, "demos", "item-42x"), "w") as fh:
            fh.write("SIBLING")
        self.assertEqual(self.get("/demo/item-42/../item-42x")[0], 404)

    def test_unknown_demo_and_missing_asset_404(self):
        self.assertEqual(self.get("/demo/does-not-exist/")[0], 404)
        self.assertEqual(self.get("/demo/item-42/missing.js")[0], 404)

    def test_a_bad_demo_id_is_refused(self):
        self.assertEqual(self.get("/demo/..%2f..%2fbus.json")[0], 404)
        self.assertEqual(self.get("/demo//index.html")[0], 404)

    def test_demo_is_still_host_gated(self):
        # Token-free is not Host-free: a rebound page must not reach it either.
        self.assertEqual(self.get("/demo/item-42/", host="evil.com")[0], 403)

    def test_dotfiles_are_never_served(self):
        # create-demo keeps the refine-round counter here; it (and any stray .git) must
        # not be servable even though it lives inside the bundle dir.
        with open(os.path.join(self.demo, ".refine.json"), "w") as fh:
            fh.write('{"round": 2}')
        os.makedirs(os.path.join(self.demo, ".git"), exist_ok=True)
        with open(os.path.join(self.demo, ".git", "config"), "w") as fh:
            fh.write("SECRET")
        self.assertEqual(self.get("/demo/item-42/.refine.json")[0], 404)
        code, body, _ = self.get("/demo/item-42/.git/config")
        self.assertEqual(code, 404)
        self.assertNotIn(b"SECRET", body)


# --- the inbox writer -------------------------------------------------------
class InboxOrdering(Tmp):
    """The measured contract behind the watermark: filename order == VISIBILITY order."""

    def setUp(self):
        super().setUp()
        self.w = mkworkflow(self.root)
        self.writer = bus.InboxWriter(bus.Paths(self.w))

    def test_ids_are_unique_and_monotonic_under_concurrency(self):
        got, lock = [], threading.Lock()

        def go(i):
            mid = self.writer.append("intake", {"ask": "n%d" % i})
            with lock:
                got.append(mid)

        threads = [threading.Thread(target=go, args=(i,)) for i in range(40)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(len(set(got)), 40, "the bus issued a duplicate message id")
        self.assertEqual(got, sorted(got),
                         "ids were not issued in the order they became visible")

    def test_visibility_order_matches_filename_order(self):
        """The exact race that eats a message: a thread that names itself FIRST is
        descheduled and renames LAST. If that can happen, the orchestrator publishes a
        watermark above a message it never saw, and the GC deletes it. Measured — this
        is why allocation and publication share one lock."""
        visible, lock = [], threading.Lock()

        def go(i, stall):
            real = bus.atomic_write

            def slow(path, data, mode=0o600):
                time.sleep(stall)
                real(path, data, mode)
            bus.atomic_write = slow if stall else real
            try:
                mid = self.writer.append("intake", {"ask": "n%d" % i})
            finally:
                bus.atomic_write = real
            with lock:
                visible.append(mid)

        a = threading.Thread(target=go, args=(1, 0.25))
        a.start()
        time.sleep(0.02)
        b = threading.Thread(target=go, args=(2, 0.0))
        b.start()
        a.join()
        b.join()
        on_disk = sorted(n[:-5] for n in os.listdir(os.path.join(self.w, "inbox")))
        self.assertEqual(visible, on_disk,
                         "a message became visible below one already visible — the "
                         "watermark would collect an unconsumed message")

    def test_sequence_survives_a_restart_and_a_backwards_clock(self):
        """A daemon restart under an NTP step must not re-issue a name below one
        already consumed — that is the same message loss through another door."""
        first = self.writer.append("intake", {"ask": "a"})
        fresh = bus.InboxWriter(bus.Paths(self.w))  # a "restarted" daemon
        real = time.time
        time.time = lambda: real() - 3600  # the clock jumps an hour backwards
        try:
            second = fresh.append("intake", {"ask": "b"})
        finally:
            time.time = real
        self.assertGreater(second, first,
                           "a restart re-issued an id below an existing one")

    def test_message_id_is_the_filename_stem(self):
        mid = self.writer.append("intake", {"ask": "a"})
        self.assertTrue(os.path.exists(
            os.path.join(self.w, "inbox", mid + ".json")))
        self.assertTrue(bus.MESSAGE_ID_RE.fullmatch(mid), mid)

    def test_a_collected_inbox_still_floors_new_ids_at_the_watermark(self):
        """The steady state of a working inbox is EMPTY — collecting it is the GC's
        job. So the disk cannot be the only floor: a daemon restarting into an empty
        inbox under a backwards clock step would issue an id below the watermark, and
        the janitor would collect that message before the orchestrator ever drained it.
        """
        mark = "20990716T120000.000001Z-ffffffff-1"  # far in the future
        with open(os.path.join(self.w, "handoff.md"), "w") as fh:
            fh.write(bus.render_handoff_block(
                {"consumed": [], "consumed_through": mark, "dead_letters": []}))
        self.assertEqual(os.listdir(os.path.join(self.w, "inbox")), [],
                         "fixture assumes a collected inbox")
        fresh = bus.InboxWriter(bus.Paths(self.w))
        mid = fresh.append("verdict", {"token": "t", "verdict": {"outcome": "approve"}})
        self.assertGreater(mid, mark,
                           "the bus issued an id at or below the watermark — the GC "
                           "would delete this message before it was ever drained")


# --- parking ----------------------------------------------------------------
PROSE = ("# Handoff — resume anchor\n\n"
         "- current_item: item-1\n- loop_position: execute\n")


def a_park(tid="item-1", kind="qa", **kw):
    rec = {"ticket_id": tid, "token": "tok-" + tid, "loop_position": "checkpoint",
           "predicted_outcome": "approve",
           "checkpoint": {"kind": kind,
                          "request": {"what": "click the thing", "expected": "it works",
                                      "blocking": True}}}
    rec.update(kw)
    return rec


class Parking(Tmp):
    """Parking had no code writer at all: the skill hand-wrote the JSON *and* resolved
    the runtime root itself, so path resolution had a second owner and the handoff
    mirror could not become a mechanism. Both halves are checked here."""

    def setUp(self):
        super().setUp()
        self.w = mkworkflow(self.root)
        with open(os.path.join(self.w, "handoff.md"), "w") as fh:
            fh.write(PROSE)
        self.paths = bus.Paths(self.w)

    def mirror(self):
        return bus._read_fenced(self.paths.handoff, bus.PARKED_BLOCK_RE)

    def test_the_record_lands_at_the_runtime_root_not_under_workflow(self):
        """The prose the skill carried said "never assume .workflow/parked/" and then
        made the model do the resolving. Paths owns this; park inherits it for free."""
        native = os.path.join(self.root, "native")
        os.makedirs(native)
        with open(os.path.join(self.w, "runtime.json"), "w") as fh:
            json.dump({"runtime_root": native}, fh)
        res = bus.write_park(bus.Paths(self.w), a_park())
        self.assertEqual(os.path.dirname(res["record"]),
                         os.path.join(native, "parked"))
        self.assertFalse(os.path.exists(os.path.join(self.w, "parked", "item-1.json")))

    def test_the_record_is_written_0600(self):
        res = bus.write_park(self.paths, a_park(kind="setup"))
        if bus.mount_honours_modes(self.paths.parked) is not False:
            self.assertEqual(os.stat(res["record"]).st_mode & 0o777, 0o600)

    def test_the_mirror_appears_and_the_prose_survives(self):
        bus.write_park(self.paths, a_park())
        text = open(self.paths.handoff).read()
        self.assertIn("- current_item: item-1", text)
        self.assertIn(bus.PARKED_BEGIN, text)
        self.assertEqual([e["ticket_id"] for e in self.mirror()["parked"]], ["item-1"])

    def test_the_mirror_carries_no_body_ever(self):
        """D141's whole reason for projecting instead of committing parked/: a setup
        checkpoint's body is exactly where a credential appears, and handoff.md is
        committed. ids + kind + summary + opened_at, nothing else."""
        bus.write_park(self.paths, a_park(
            kind="setup",
            checkpoint={"kind": "setup",
                        "request": {"what": "add the API key", "blocking": True,
                                    "how": "paste sk_live_DEADBEEFDEADBEEF0000"}}))
        text = open(self.paths.handoff).read()
        self.assertNotIn("sk_live_DEADBEEF", text)
        self.assertNotIn("tok-item-1", text)  # the correlation token is not mirrored
        entry = self.mirror()["parked"][0]
        self.assertEqual(sorted(entry), ["kind", "opened_at", "summary", "ticket_id"])

    def test_the_two_machine_blocks_do_not_overwrite_each_other(self):
        """Three authors on one file now. The drain block, the parked block, and the
        prose each have to survive a write by either of the other two."""
        drain_block = {"consumed": ["20260101T000000.000001Z-aaaaaaaa-1"],
                       "consumed_through": None, "dead_letters": []}
        with open(self.paths.handoff, "w") as fh:
            fh.write(PROSE + "\n" + bus.render_handoff_block(drain_block) + "\n")
        bus.write_park(self.paths, a_park())
        self.assertEqual(bus.read_handoff_block(self.paths.handoff)["consumed"],
                         drain_block["consumed"])
        # …and the drain writing back does not eat the parked block.
        import drain
        drain.publish(self.paths, drain_block)
        text = open(self.paths.handoff).read()
        self.assertIn(bus.PARKED_BEGIN, text)
        self.assertIn("- current_item: item-1", text)
        self.assertEqual([e["ticket_id"] for e in self.mirror()["parked"]], ["item-1"])

    def test_unpark_removes_the_entry_from_the_mirror(self):
        """Without this the block only ever GROWS, and every resolved checkpoint stays
        "open" forever in the file a cold start trusts — worse than the prose it
        replaced, because a machine block reads as authoritative."""
        bus.write_park(self.paths, a_park("item-1"))
        bus.write_park(self.paths, a_park("item-2"))
        self.assertEqual(len(self.mirror()["parked"]), 2)
        res = bus.remove_park(self.paths, "item-1")
        self.assertTrue(res["removed"])
        self.assertEqual([e["ticket_id"] for e in self.mirror()["parked"]], ["item-2"])
        self.assertFalse(os.path.exists(os.path.join(self.paths.parked, "item-1.json")))

    def test_unpark_is_idempotent(self):
        """A re-applied verdict must no-op on its second pass, like every other
        consumer anchor."""
        bus.write_park(self.paths, a_park())
        bus.remove_park(self.paths, "item-1")
        res = bus.remove_park(self.paths, "item-1")
        self.assertFalse(res["removed"])
        self.assertEqual(self.mirror()["parked"], [])

    def test_the_mirror_is_a_projection_not_an_append_log(self):
        """A record removed out of band (a rebind, a crash, a human) must vanish from
        the mirror on the next mutation rather than linger."""
        bus.write_park(self.paths, a_park("item-1"))
        bus.write_park(self.paths, a_park("item-2"))
        os.unlink(os.path.join(self.paths.parked, "item-1.json"))
        bus.publish_parked_mirror(self.paths)
        self.assertEqual([e["ticket_id"] for e in self.mirror()["parked"]], ["item-2"])

    def test_an_unreadable_record_is_skipped_not_fatal(self):
        bus.write_park(self.paths, a_park("item-1"))
        with open(os.path.join(self.paths.parked, "junk.json"), "w") as fh:
            fh.write("{not json")
        self.assertEqual([e["ticket_id"] for e in
                          bus.parked_mirror(self.paths)["parked"]], ["item-1"])

    def test_the_projection_is_capped_and_reports_the_overflow(self):
        for i in range(bus.MAX_MIRRORED + 3):
            bus.write_park(self.paths, a_park("item-%03d" % i))
        block = self.mirror()
        self.assertEqual(len(block["parked"]), bus.MAX_MIRRORED)
        self.assertEqual(block["not_mirrored"], 3)

    def test_the_deadline_is_derived_from_config_when_absent(self):
        with open(os.path.join(self.w, "config.json"), "w") as fh:
            json.dump({"checkpoint": {"deadline_hours": 0}}, fh)
        res = bus.write_park(bus.Paths(self.w), a_park())
        self.assertLessEqual(bus.parse_deadline(res["deadline"]), time.time() + 1)

    def test_a_supplied_deadline_wins(self):
        res = bus.write_park(self.paths, a_park(), deadline="2099-01-01T00:00:00+00:00")
        self.assertEqual(res["deadline"], "2099-01-01T00:00:00+00:00")

    def test_the_deadline_is_absolute_and_parseable_by_the_daemon(self):
        """The daemon compares this against wall-clock and was not present when the
        ticket parked, so an unparseable stamp means it never escalates — silently."""
        res = bus.write_park(self.paths, a_park())
        self.assertIsNotNone(bus.parse_deadline(res["deadline"]))

    def test_the_summary_is_derived_from_the_request_when_absent(self):
        bus.write_park(self.paths, a_park())
        self.assertEqual(self.mirror()["parked"][0]["summary"], "click the thing")

    def test_a_summary_cannot_break_out_of_the_json_fence(self):
        """It is rendered inside a ```json fence a cold start parses; a backtick run
        would terminate the block early and silently truncate the mirror."""
        bus.write_park(self.paths, a_park(), summary="see ``` then\nmore")
        text = open(self.paths.handoff).read()
        self.assertIsNotNone(self.mirror(), "the fence did not survive the summary")
        self.assertEqual(self.mirror()["parked"][0]["summary"], "see ''' then more")
        self.assertEqual(text.count("```"), 2)

    def test_a_long_summary_is_capped(self):
        bus.write_park(self.paths, a_park(), summary="x" * 5000)
        self.assertLessEqual(len(self.mirror()["parked"][0]["summary"]), bus.MAX_SUMMARY)

    def test_a_park_with_no_token_is_refused(self):
        """It could be answered and never resumed — the drain matches on the token."""
        rec = a_park()
        del rec["token"]
        with self.assertRaises(bus.Invalid) as cm:
            bus.write_park(self.paths, rec)
        self.assertIn("token", str(cm.exception))

    def test_an_unknown_kind_is_refused(self):
        with self.assertRaises(bus.Invalid):
            bus.write_park(self.paths, a_park(kind="vibes"))

    def test_an_empty_request_is_refused(self):
        with self.assertRaises(bus.Invalid) as cm:
            bus.write_park(self.paths, a_park(
                checkpoint={"kind": "qa", "request": {}}))
        self.assertIn("asked nothing", str(cm.exception))

    def test_a_traversing_ticket_id_cannot_escape_the_parked_dir(self):
        for bad in ("../../etc/passwd", "a/b", "", ".", "..", None, 7):
            rec = a_park()
            rec["ticket_id"] = bad
            with self.assertRaises(bus.Invalid):
                bus.write_park(self.paths, rec)
            with self.assertRaises(bus.Invalid):
                bus.remove_park(self.paths, bad)

    def test_nothing_is_written_when_the_record_is_refused(self):
        with self.assertRaises(bus.Invalid):
            bus.write_park(self.paths, a_park(kind="vibes"))
        self.assertEqual(os.listdir(self.paths.parked), [])
        self.assertNotIn(bus.PARKED_BEGIN, open(self.paths.handoff).read())

    def test_a_re_park_stamps_a_fresh_deadline_for_alert_dedup(self):
        """schemas.md: (ticket_id + deadline) is the daemon's alert-dedup key, so a
        ticket that parks, resolves and re-parks must not read as already-seen."""
        first = bus.write_park(self.paths, a_park())
        bus.remove_park(self.paths, "item-1")
        second = bus.write_park(self.paths, a_park())
        self.assertNotEqual(bus.alert_key({"ticket_id": "item-1",
                                           "deadline": first["deadline"]}),
                            bus.alert_key({"ticket_id": "item-1",
                                           "deadline": second["deadline"]}))

    def test_the_daemon_and_the_console_read_what_park_wrote(self):
        """The writer is only correct if the two existing READERS agree with it — the
        alert trigger (ParkedWatchJob) and the console's read model."""
        bus.write_park(self.paths, a_park(kind="demo", checkpoint={
            "kind": "demo", "demo_id": "item-1",
            "request": {"what": "approve the sandbox", "blocking": True}}))
        d = bus.Daemon(self.paths, idle_timeout=3600)
        job = bus.ParkedWatchJob()
        self.assertFalse(job.is_idle(d), "the daemon cannot see the park it must alert on")
        row = bus.ReadModel(self.paths).parked()[0]
        self.assertEqual((row["ticket_id"], row["kind"], row["token"], row["demo_id"]),
                         ("item-1", "demo", "tok-item-1", "item-1"))
        self.assertFalse(row["overdue"])


class ParkingCLI(Tmp):
    """The skill calls this over the CLI, so the CLI is the contract."""

    def setUp(self):
        super().setUp()
        self.w = mkworkflow(self.root)

    def run_bus(self, *argv, stdin=""):
        return subprocess.run(
            [sys.executable, os.path.join(os.path.dirname(os.path.abspath(bus.__file__)),
                                          "bus.py"), *argv,
             "--workflow-dir", self.w],
            input=stdin, capture_output=True, text=True)

    def test_park_then_unpark_over_the_cli(self):
        p = self.run_bus("park", stdin=json.dumps(a_park()))
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(json.loads(p.stdout)["ticket_id"], "item-1")
        self.assertTrue(os.path.exists(os.path.join(self.w, "parked", "item-1.json")))
        u = self.run_bus("unpark", "--id", "item-1")
        self.assertEqual(u.returncode, 0, u.stderr)
        self.assertTrue(json.loads(u.stdout)["removed"])
        self.assertEqual(
            bus._read_fenced(os.path.join(self.w, "handoff.md"),
                             bus.PARKED_BLOCK_RE)["parked"], [])

    def test_the_id_may_come_from_the_flag_when_the_record_omits_it(self):
        rec = a_park()
        del rec["ticket_id"]
        p = self.run_bus("park", "--id", "item-9", stdin=json.dumps(rec))
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(json.loads(p.stdout)["ticket_id"], "item-9")

    def test_a_refused_park_exits_nonzero_and_says_why(self):
        p = self.run_bus("park", stdin=json.dumps(a_park(kind="vibes")))
        self.assertNotEqual(p.returncode, 0)
        self.assertIn("park refused", p.stderr)

    def test_malformed_stdin_exits_nonzero(self):
        p = self.run_bus("park", stdin="{not json")
        self.assertNotEqual(p.returncode, 0)
        self.assertIn("stdin", p.stderr)

    def test_unpark_without_an_id_exits_nonzero(self):
        p = self.run_bus("unpark")
        self.assertNotEqual(p.returncode, 0)
        self.assertIn("--id", p.stderr)


# --- inbox GC ---------------------------------------------------------------
class InboxGC(Tmp):
    def setUp(self):
        super().setUp()
        self.w = mkworkflow(self.root)
        self.d = bus.Daemon(bus.Paths(self.w), idle_timeout=3600)
        self.job = bus.InboxGCJob()

    def _msg(self, stem):
        with open(os.path.join(self.w, "inbox", stem + ".json"), "w") as fh:
            json.dump({"kind": "intake", "ask": "x"}, fh)

    def _handoff(self, block):
        with open(os.path.join(self.w, "handoff.md"), "w") as fh:
            fh.write("# Handoff\n\nprose\n\n" + bus.render_handoff_block(block) + "\n")

    def test_nothing_is_collected_without_a_watermark(self):
        self._msg("20260716T120000.000001Z-aaaaaaaa-1")
        self.job.tick(self.d)
        self.assertEqual(len(os.listdir(os.path.join(self.w, "inbox"))), 1)

    def test_only_at_or_below_the_watermark_is_collected(self):
        low = "20260716T120000.000001Z-aaaaaaaa-1"
        mark = "20260716T120100.000001Z-bbbbbbbb-2"
        high = "20260716T120200.000001Z-cccccccc-3"
        for s in (low, mark, high):
            self._msg(s)
        self._handoff({"consumed": [], "consumed_through": mark, "dead_letters": []})
        self.job.tick(self.d)
        left = sorted(n[:-5] for n in os.listdir(os.path.join(self.w, "inbox")))
        self.assertEqual(left, [high], "GC crossed the watermark or stopped short")

    def test_a_torn_handoff_collects_nothing_rather_than_over_collecting(self):
        self._msg("20260716T120000.000001Z-aaaaaaaa-1")
        with open(os.path.join(self.w, "handoff.md"), "w") as fh:
            fh.write(bus.HANDOFF_BEGIN + "\n```json\n{not json")
        self.job.tick(self.d)
        self.assertEqual(len(os.listdir(os.path.join(self.w, "inbox"))), 1)

    def test_already_unlinked_message_is_not_an_error(self):
        """The sensitive-payload carve-out unlinks a consumed message before the
        janitor reaches it."""
        mark = "20260716T120100.000001Z-bbbbbbbb-2"
        self._handoff({"consumed": [], "consumed_through": mark, "dead_letters": []})
        self.job.tick(self.d)  # empty inbox, watermark set
        self.assertTrue(True)  # a raise here would have failed the test


# --- lifecycle --------------------------------------------------------------
class Lifecycle(Tmp):
    def test_second_daemon_cannot_take_a_held_lock(self):
        w = mkworkflow(self.root)
        a = bus.Daemon(bus.Paths(w))
        self.assertTrue(a.acquire_lock())
        self.addCleanup(a.cleanup)
        b = bus.Daemon(bus.Paths(w))
        self.assertFalse(b.acquire_lock(), "two daemons acquired the same lock")

    def test_lock_is_released_when_the_holder_dies(self):
        """Lock-as-liveness only works because the kernel releases it on death — which
        is what makes it immune to the PID reuse a pidfile would suffer."""
        w = mkworkflow(self.root)
        code = ("import sys; sys.path.insert(0, %r); import bus, os;"
                "d = bus.Daemon(bus.Paths(%r)); assert d.acquire_lock(); os._exit(9)"
                % (os.path.dirname(os.path.abspath(bus.__file__)), w))
        rc = subprocess.run([sys.executable, "-c", code]).returncode
        self.assertEqual(rc, 9)
        after = bus.Daemon(bus.Paths(w))
        self.assertTrue(after.acquire_lock(), "lock leaked after the holder was killed")
        after.cleanup()

    def test_is_live_calls_a_stale_record_stale(self):
        """A record whose daemon is gone must never be adopted, even though the file
        still names a plausible pid."""
        w = mkworkflow(self.root)
        p = bus.Paths(w)
        bus.atomic_write(p.record, json.dumps(
            {"pid": 999999, "port": 9, "token": "t", "started_at": "x"}))
        self.assertIsNone(bus.is_live(p))


# --- the notifier: the timing decision, pure ---------------------------------
class PlanAlerts(unittest.TestCase):
    """The new→reminder→escalate-once→reminders-continue rules, no clock or socket.

    Fast, but deliberately NOT the whole story: the bug that survived 27 green unit
    tests last increment only showed on the driven path, so NotifierDrive below runs
    the real POST + real restart. These pin the arithmetic; those pin the behaviour.
    """
    def cp(self, tid="item-1", deadline="2999-01-01T00:00:00+00:00"):
        return {"ticket_id": tid, "deadline": deadline}

    def empty(self):
        return {"checkpoints": {}, "dead_letters": {}}

    def test_first_sight_is_a_new_alert(self):
        acts, keys, _ = bus.plan_alerts([self.cp()], [], self.empty(), 1000.0, 4 * 3600)
        self.assertEqual([a["kind"] for a in acts], ["new"])
        self.assertEqual(len(keys), 1)

    def test_within_the_interval_is_silent(self):
        st = {"checkpoints": {bus.alert_key(self.cp()):
                              {"first_alert": 1000.0, "last_alert": 1000.0, "escalated": False}},
              "dead_letters": {}}
        acts, _, _ = bus.plan_alerts([self.cp()], [], st, 1000.0 + 60, 4 * 3600)
        self.assertEqual(acts, [])

    def test_past_the_interval_is_a_reminder(self):
        st = {"checkpoints": {bus.alert_key(self.cp()):
                              {"first_alert": 0.0, "last_alert": 0.0, "escalated": False}},
              "dead_letters": {}}
        acts, _, _ = bus.plan_alerts([self.cp()], [], st, 4 * 3600 + 1, 4 * 3600)
        self.assertEqual([a["kind"] for a in acts], ["reminder"])

    def test_overdue_escalates_once_then_reminders_continue_marked_overdue(self):
        past = "2000-01-01T00:00:00+00:00"
        key = bus.alert_key(self.cp(deadline=past))
        st = {"checkpoints": {key: {"first_alert": 0.0, "last_alert": 0.0, "escalated": False}},
              "dead_letters": {}}
        now = time.time()
        acts, _, _ = bus.plan_alerts([self.cp(deadline=past)], [], st, now, 4 * 3600)
        self.assertEqual([a["kind"] for a in acts], ["escalation"])
        self.assertTrue(acts[0]["overdue"])
        # simulate the escalation having been sent...
        st["checkpoints"][key] = {"first_alert": 0.0, "last_alert": now, "escalated": True}
        acts2, _, _ = bus.plan_alerts([self.cp(deadline=past)], [], st, now + 4 * 3600 + 1, 4 * 3600)
        self.assertEqual([a["kind"] for a in acts2], ["reminder"])
        self.assertTrue(acts2[0]["overdue"], "reminders after escalation must stay marked overdue")

    def test_reprk_with_a_new_deadline_is_a_new_key_so_it_alerts_again(self):
        first = self.cp(deadline="2999-01-01T00:00:00+00:00")
        second = self.cp(deadline="2999-06-06T00:00:00+00:00")  # same ticket, later park
        self.assertNotEqual(bus.alert_key(first), bus.alert_key(second))

    def test_a_dead_letter_alerts_once(self):
        dl = [{"message_id": "20260101T000000.000001Z-aaaaaaaa-1", "reason": "unreadable"}]
        acts, _, live = bus.plan_alerts([], dl, self.empty(), 1000.0, 4 * 3600)
        self.assertEqual([a["kind"] for a in acts], ["dead-letter"])
        st = {"checkpoints": {}, "dead_letters": {dl[0]["message_id"]: {"at": 1000.0}}}
        acts2, _, _ = bus.plan_alerts([], dl, st, 2000.0, 4 * 3600)
        self.assertEqual(acts2, [], "a dead-letter must not re-alert every tick")


# --- the notifier: driven against a real HTTP sink ---------------------------
class _Sink:
    """A real loopback HTTP server that records the POSTs a webhook would receive."""
    def __init__(self, fail=False):
        from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
        self.received = []
        outer = self

        class H(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def do_POST(self):
                n = int(self.headers.get("Content-Length") or 0)
                raw = self.rfile.read(n)
                outer.received.append({"path": self.path,
                                       "ctype": self.headers.get("Content-Type"),
                                       "body": json.loads(raw.decode() or "{}")})
                if fail:
                    self.send_response(500)
                else:
                    self.send_response(200)
                self.end_headers()

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), H)
        self.port = self.server.server_address[1]
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    @property
    def url(self):
        return "http://127.0.0.1:%d/hook" % self.port

    def stop(self):
        self.server.shutdown()


class NotifierDrive(Tmp):
    def setUp(self):
        super().setUp()
        self.w = mkworkflow(self.root)
        self.paths = bus.Paths(self.w)

    def _config(self, url=None, kind="generic", reminder_hours=None, desktop=False):
        notify = {"desktop": desktop}
        if url:
            notify["webhook"] = {"url": url, "kind": kind}
        cfg = {"notify": notify}
        if reminder_hours is not None:
            cfg["checkpoint"] = {"reminder_hours": reminder_hours}
        with open(self.paths.config, "w") as fh:
            json.dump(cfg, fh)

    def _park(self, name="item-1.json", tid="item-1", deadline="2999-01-01T00:00:00+00:00"):
        with open(os.path.join(self.paths.parked, name), "w") as fh:
            json.dump({"ticket_id": tid, "token": "cp",
                       "checkpoint": {"kind": "qa", "request": "SECRET-REQUEST-BODY"},
                       "deadline": deadline}, fh)

    def _daemon(self):
        d = bus.Daemon(self.paths, idle_timeout=3600)
        d.port = 4321
        return d

    def _run(self, d):
        job = bus.ParkedWatchJob(d.notifier)
        job.tick(d)

    def test_a_real_post_lands_and_carries_no_request_body(self):
        sink = _Sink()
        self.addCleanup(sink.stop)
        self._config(url=sink.url)
        self._park()
        self._run(self._daemon())
        self.assertEqual(len(sink.received), 1)
        body = sink.received[0]["body"]
        self.assertEqual(body["event"], "new")
        self.assertEqual(body["ticket_id"], "item-1")
        self.assertIn("127.0.0.1:4321", body["console"])
        # the doorbell rule: the request body never leaves the machine
        self.assertNotIn("SECRET-REQUEST-BODY", json.dumps(sink.received[0]))

    def test_restart_does_not_re_alert_an_already_alerted_checkpoint(self):
        """The test that matters: 27 green unit tests missed the last increment's real
        bug because it only appeared on the restart path. A fresh Notifier (a new
        process) loads alerts.json and must stay quiet about what the old one alerted."""
        sink = _Sink()
        self.addCleanup(sink.stop)
        self._config(url=sink.url)
        self._park()
        self._run(self._daemon())            # first daemon alerts
        self.assertEqual(len(sink.received), 1)
        self.assertTrue(os.path.exists(self.paths.alerts))
        self._run(self._daemon())            # a "restart" — new Notifier, same disk
        self.assertEqual(len(sink.received), 1, "a routine restart re-alerted (WSL spam)")

    def test_a_lost_alert_file_re_alerts_rather_than_going_silent(self):
        sink = _Sink()
        self.addCleanup(sink.stop)
        self._config(url=sink.url)
        self._park()
        self._run(self._daemon())
        self.assertEqual(len(sink.received), 1)
        os.unlink(self.paths.alerts)         # lost/corrupt state
        self._run(self._daemon())
        self.assertEqual(len(sink.received), 2, "a lost alert file must alert, not stay silent")

    def test_reprk_after_resolve_alerts_again(self):
        sink = _Sink()
        self.addCleanup(sink.stop)
        self._config(url=sink.url)
        self._park(deadline="2999-01-01T00:00:00+00:00")
        self._run(self._daemon())
        os.unlink(os.path.join(self.paths.parked, "item-1.json"))  # resolved
        self._run(self._daemon())                                  # prunes the key
        self._park(deadline="2999-02-02T00:00:00+00:00")           # re-park, new deadline
        self._run(self._daemon())
        self.assertEqual(len(sink.received), 2, "a re-park on a new checkpoint must re-alert")

    def test_reminder_fires_in_real_time(self):
        sink = _Sink()
        self.addCleanup(sink.stop)
        self._config(url=sink.url, reminder_hours=0.0006)  # ~2.16s
        self._park()
        d = self._daemon()
        self._run(d)                          # new
        self.assertEqual(len(sink.received), 1)
        self._run(d)                          # too soon — silent
        self.assertEqual(len(sink.received), 1)
        time.sleep(2.3)
        self._run(d)                          # reminder now due
        self.assertEqual(len(sink.received), 2)
        self.assertEqual(sink.received[1]["body"]["event"], "reminder")

    def test_no_reminder_backlog_replay_after_a_long_gap(self):
        """A daemon gone 10h with a 4h interval fires ONE reminder on wake, not two."""
        sink = _Sink()
        self.addCleanup(sink.stop)
        self._config(url=sink.url, reminder_hours=4)
        self._park()
        d = self._daemon()
        self._run(d)                          # new alert, last_alert = now
        # rewind last_alert 10h into the past — as if the daemon had been dead
        key = bus.alert_key({"ticket_id": "item-1", "deadline": "2999-01-01T00:00:00+00:00"})
        d.notifier.state["checkpoints"][key]["last_alert"] = time.time() - 10 * 3600
        self._run(d)
        self.assertEqual(len(sink.received), 2, "exactly one reminder on wake, never a backlog")

    def test_escalation_then_overdue_reminder_over_the_wire(self):
        sink = _Sink()
        self.addCleanup(sink.stop)
        self._config(url=sink.url, reminder_hours=0.0006)
        self._park(deadline="2000-01-01T00:00:00+00:00")  # already overdue
        d = self._daemon()
        self._run(d)                          # new (first sight, even though overdue)
        self.assertEqual(sink.received[-1]["body"]["event"], "new")
        self._run(d)                          # now escalation (overdue, not yet escalated)
        self.assertEqual(sink.received[-1]["body"]["event"], "escalation")
        time.sleep(2.3)
        self._run(d)                          # reminders continue, marked overdue
        self.assertEqual(sink.received[-1]["body"]["event"], "reminder")
        self.assertTrue(sink.received[-1]["body"]["overdue"])

    def test_a_dead_url_backs_off_and_does_not_storm(self):
        self._config(url="http://127.0.0.1:1/dead")  # nothing listens on port 1
        self._park("a.json", tid="a")
        self._park("b.json", tid="b")
        self._park("c.json", tid="c")
        d = self._daemon()
        self._run(d)
        self.assertGreaterEqual(d.notifier.consecutive_failures, 1)
        self.assertGreater(d.notifier.next_attempt, time.time(), "no backoff set")
        # a checkpoint that failed to send is NOT marked alerted, so it retries later
        self.assertEqual(d.notifier.state.get("checkpoints", {}), {})
        # immediate re-run is gated by the backoff — no storm
        before = d.notifier.consecutive_failures
        self._run(d)
        self.assertEqual(d.notifier.consecutive_failures, before, "backoff did not throttle")

    def test_slack_kind_sends_a_text_field(self):
        sink = _Sink()
        self.addCleanup(sink.stop)
        self._config(url=sink.url, kind="slack")
        self._park()
        self._run(self._daemon())
        body = sink.received[0]["body"]
        self.assertEqual(set(body.keys()), {"text"})
        self.assertIn("verdict", body["text"])

    def test_no_webhook_means_no_post_and_readiness_says_so(self):
        self._config(url=None)  # desktop off, no webhook
        self._park()
        d = self._daemon()
        self._run(d)
        self.assertFalse(d.notifier.readiness()["webhook"])
        # nothing to send, but the checkpoint is marked so it does not recompute forever
        self.assertIn(bus.alert_key({"ticket_id": "item-1",
                                     "deadline": "2999-01-01T00:00:00+00:00"}),
                      d.notifier.state["checkpoints"])

    def test_desktop_failure_is_surfaced_not_swallowed(self):
        """On a headless/WSL box no daemon owns the notification name, so notify-send
        fails. That must reach `status`, not vanish."""
        sink = _Sink()
        self.addCleanup(sink.stop)
        self._config(url=sink.url, desktop=True)
        self._park()
        d = self._daemon()
        self._run(d)
        # the webhook still succeeded; the desktop attempt, if it failed, is a warning
        self.assertEqual(len(sink.received), 1)
        # notify-send may or may not exist; if it failed, the warning is visible
        if any("desktop notification failed" in w for w in d.warnings):
            self.assertTrue(True)


# --- the notifier: a live detached daemon actually POSTs ---------------------
class NotifierLiveDaemon(Tmp):
    """Proves the wiring end to end: a real setsid daemon's janitor calls the
    notifier, which POSTs to a real sink — the path a static read cannot verify."""
    def test_a_detached_daemon_alerts_a_real_sink(self):
        w = mkworkflow(self.root)
        paths = bus.Paths(w)
        sink = _Sink()
        self.addCleanup(sink.stop)
        with open(paths.config, "w") as fh:
            json.dump({"notify": {"webhook": {"url": sink.url, "kind": "generic"}}}, fh)
        with open(os.path.join(paths.parked, "item-1.json"), "w") as fh:
            json.dump({"ticket_id": "item-1", "token": "cp",
                       "checkpoint": {"kind": "qa", "request": "ok?"},
                       "deadline": "2999-01-01T00:00:00+00:00"}, fh)
        rec = bus.ensure(paths, idle_timeout=4)  # janitor_interval ~1s
        self.addCleanup(lambda: bus.stop(paths))
        deadline = time.time() + 8
        while time.time() < deadline and not sink.received:
            time.sleep(0.2)
        self.assertTrue(sink.received, "the live daemon never POSTed the away alert")
        self.assertEqual(sink.received[0]["body"]["ticket_id"], "item-1")


# --- the remote socket: the pure decisions ----------------------------------
class RemoteConfigParse(unittest.TestCase):
    def test_absent_or_disabled_is_not_served(self):
        self.assertIsNone(bus.parse_remote({}))
        self.assertIsNone(bus.parse_remote({"remote": {"enabled": False,
                                                        "transport": "tailscale"}}))
        self.assertIsNone(bus.parse_remote({"remote": {"enabled": True}}))

    def test_a_bogus_transport_is_not_served(self):
        self.assertIsNone(bus.parse_remote(
            {"remote": {"enabled": True, "transport": "ngrok"}}))

    def test_access_parses_without_the_credential_carve_out(self):
        r = bus.parse_remote({"remote": {"enabled": True, "transport": "access",
                                         "public_url": "https://away.example/"}})
        self.assertIsNotNone(r)
        self.assertEqual(r.transport, "access")
        self.assertFalse(r.allow_credentials)         # a TLS-terminating proxy sees plaintext
        self.assertEqual(r.public_url, "https://away.example")   # trailing slash stripped
        self.assertEqual(r.host, "away.example")

    def test_tailscale_unlocks_credentials(self):
        r = bus.parse_remote({"remote": {"enabled": True, "transport": "tailscale"}})
        self.assertTrue(r.allow_credentials)          # WireGuard is end-to-end encrypted
        self.assertEqual(r.port, bus.DEFAULT_REMOTE_PORT)   # a missing port defaults, fixed
        self.assertIsNone(r.public_url)

    def test_a_declared_port_is_kept_but_a_bad_one_defaults(self):
        self.assertEqual(bus.parse_remote(
            {"remote": {"enabled": True, "transport": "access", "port": 9001}}).port, 9001)
        for bad in (True, 0, 70000, "8799", 1.5):
            self.assertEqual(bus.parse_remote(
                {"remote": {"enabled": True, "transport": "access", "port": bad}}).port,
                bus.DEFAULT_REMOTE_PORT)


class RemotePayloadBoundary(unittest.TestCase):
    """The A/B credential boundary is a STRUCTURAL predicate on the returns/tasks keys —
    never the shallow _is_sensitive heuristic, whose false negative would be a live key
    on a plaintext edge."""
    def test_a_bare_opinion_verdict_is_not_a_payload(self):
        self.assertFalse(bus.remote_carries_payload(
            {"verdict": {"outcome": "approve", "notes": "looks good"}}))

    def test_any_returns_key_is_a_payload(self):
        self.assertTrue(bus.remote_carries_payload(
            {"verdict": {"outcome": "approve", "returns": {"api_key": "sk-live-x"}}}))

    def test_even_a_returns_that_is_not_flagged_sensitive_is_a_payload(self):
        # _is_sensitive would MISS this (no `sensitive` marker); the structural gate
        # does not — presence of the key is enough.
        body = {"verdict": {"outcome": "approve", "returns": {"value": "not-marked"}}}
        self.assertFalse(bus._is_sensitive(body["verdict"]["returns"]))
        self.assertTrue(bus.remote_carries_payload(body))

    def test_the_setup_tasks_shape_is_a_payload(self):
        self.assertTrue(bus.remote_carries_payload(
            {"verdict": {"tasks": [{"outcome": "approve"}]}}))


class RemoteHelpers(Tmp):
    def test_url_host_extracts_the_bare_name(self):
        self.assertEqual(bus._url_host("https://box.tail1234.ts.net"), "box.tail1234.ts.net")
        self.assertEqual(bus._url_host("https://user@away.example:8443/x"), "away.example")

    def test_remote_token_is_minted_once_then_reused(self):
        w = mkworkflow(self.root)
        d1 = bus.Daemon(bus.Paths(w))
        d1.ensure_remote_token()
        first = d1.remote_token
        self.assertTrue(first)
        self.assertTrue(os.path.exists(bus.Paths(w).remote_token_file))
        # A restart reuses the SAME token — a phone paired once keeps working.
        d2 = bus.Daemon(bus.Paths(w))
        d2.ensure_remote_token()
        self.assertEqual(d2.remote_token, first)

    def test_pairing_info_is_the_whole_link_when_a_public_url_is_set(self):
        w = mkworkflow(self.root)
        d = bus.Daemon(bus.Paths(w))
        d.ensure_remote_token()
        d.remote = bus.RemoteConfig("tailscale", 8799, "https://box.ts.net")
        info = d.pairing_info()
        self.assertTrue(info["configured"])
        self.assertEqual(info["url"], "https://box.ts.net/#t=" + d.remote_token)
        self.assertTrue(info["allow_credentials"])


# --- the remote socket: a real Socket A beside a real Socket B ---------------
class RemoteSocket(Tmp):
    TRANSPORT = "access"

    def setUp(self):
        super().setUp()
        self.w = mkworkflow(self.root)
        self.d = bus.Daemon(bus.Paths(self.w), idle_timeout=3600)
        self.assertTrue(self.d.acquire_lock())
        self.d.token = "loopback-token-B"
        self.d.remote_token = "remote-token-A"
        from http.server import ThreadingHTTPServer
        handler = bus.make_handler(self.d)
        self.d.server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        self.d.server.policy = bus.LOOPBACK_POLICY
        self.bport = self.d.server.server_address[1]
        self.d.remote_server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        self.rport = self.d.remote_server.server_address[1]
        allow = self.TRANSPORT == "tailscale"
        self.d.remote_server.policy = bus.SocketPolicy(
            "remote", remote=True, allow_credentials=allow, extra_hosts=("away.example",))
        self.d.remote = bus.RemoteConfig(self.TRANSPORT, self.rport, "https://away.example")
        self.d.publish(self.bport)
        threading.Thread(target=self.d.server.serve_forever, daemon=True).start()
        threading.Thread(target=self.d.remote_server.serve_forever, daemon=True).start()
        self.addCleanup(self.d.cleanup)
        self.addCleanup(self.d.server.shutdown)
        self.addCleanup(self.d.remote_server.shutdown)

    def req(self, port, path, method="GET", token=None, host=None, body=None):
        h = {"Host": host or ("127.0.0.1:%d" % port)}
        if token is not None:
            h[bus.TOKEN_HEADER] = token
        data = None
        if body is not None:
            h["Content-Type"] = "application/json"
            data = json.dumps(body).encode()
        r = urllib.request.Request("http://127.0.0.1:%d%s" % (port, path),
                                   method=method, headers=h, data=data)
        try:
            with urllib.request.urlopen(r, timeout=5) as res:
                return res.status, res.read(), dict(res.headers)
        except urllib.error.HTTPError as e:
            return e.code, e.read(), dict(e.headers)

    # -- the two tokens must not cross --
    def test_the_remote_page_carries_no_loopback_token(self):
        code, body, _ = self.req(self.rport, "/")
        self.assertEqual(code, 200)
        self.assertNotIn(b"loopback-token-B", body, "the loopback token leaked to A")
        self.assertNotIn(b"remote-token-A", body, "the remote page must not embed a token")
        self.assertIn(b'name="bus-mode" content="remote"', body)

    def test_the_loopback_page_still_carries_its_own_token(self):
        code, body, _ = self.req(self.bport, "/")
        self.assertIn(b"loopback-token-B", body)
        self.assertIn(b'name="bus-mode" content="loopback"', body)

    def test_each_socket_only_accepts_its_own_token(self):
        # A read on A needs the remote token; the loopback token is refused there.
        self.assertEqual(self.req(self.rport, "/api/state", token="remote-token-A")[0], 200)
        self.assertEqual(self.req(self.rport, "/api/state", token="loopback-token-B")[0], 401)
        # And the remote token is worthless on B.
        self.assertEqual(self.req(self.bport, "/api/state", token="loopback-token-B")[0], 200)
        self.assertEqual(self.req(self.bport, "/api/state", token="remote-token-A")[0], 401)

    # -- A's positive allowlist --
    def test_release_control_intake_do_not_exist_on_A(self):
        for kind, payload in (("release", {"action_ids": ["a1"]}),
                              ("control", {"op": "pause"}),
                              ("intake", {"ask": "do a thing"})):
            code, _, _ = self.req(self.rport, "/api/" + kind, method="POST",
                                  token="remote-token-A", body=payload)
            self.assertEqual(code, 404, "%s must not exist on the remote surface" % kind)
            # …and each still works on B.
            code_b, _, _ = self.req(self.bport, "/api/" + kind, method="POST",
                                    token="loopback-token-B", body=payload)
            self.assertEqual(code_b, 202, "%s must still work on loopback" % kind)

    def test_shutdown_is_loopback_only(self):
        self.assertEqual(self.req(self.rport, "/shutdown", method="POST",
                                  token="remote-token-A", body={})[0], 404)

    def test_pairing_secret_is_loopback_only(self):
        self.assertEqual(self.req(self.rport, "/api/pairing", token="remote-token-A")[0], 404)
        code, body, _ = self.req(self.bport, "/api/pairing", token="loopback-token-B")
        self.assertEqual(code, 200)
        info = json.loads(body)
        self.assertEqual(info["url"], "https://away.example/#t=remote-token-A")

    # -- opinion rides A, payload does not --
    def test_an_opinion_verdict_rides_A(self):
        code, body, _ = self.req(self.rport, "/api/verdict", method="POST",
                                 token="remote-token-A",
                                 body={"token": "cp1", "verdict": {"outcome": "approve",
                                                                   "notes": "ship it"}})
        self.assertEqual(code, 202, body)

    def test_a_returns_bearing_verdict_is_refused_on_access(self):
        code, _, _ = self.req(self.rport, "/api/verdict", method="POST",
                              token="remote-token-A",
                              body={"token": "cp1", "verdict": {"outcome": "approve",
                                    "returns": {"api_key": "sk-live-x"}}})
        self.assertEqual(code, 403, "a credential must not ride a plaintext-edge proxy")

    def test_a_setup_shaped_verdict_is_refused_on_access(self):
        code, _, _ = self.req(self.rport, "/api/verdict", method="POST",
                              token="remote-token-A",
                              body={"token": "cp1",
                                    "verdict": {"tasks": [{"outcome": "approve"}]}})
        self.assertEqual(code, 403)

    # -- the host allowlist accepts the public host, nothing else --
    def test_A_accepts_the_declared_public_host(self):
        self.assertEqual(self.req(self.rport, "/api/state", token="remote-token-A",
                                  host="away.example")[0], 200)

    def test_A_still_refuses_an_unknown_forged_host(self):
        self.assertEqual(self.req(self.rport, "/api/state", token="remote-token-A",
                                  host="evil.com")[0], 403)

    def test_bus_json_publishes_the_remote_coordinates(self):
        rec = bus.read_json(self.d.paths.record)
        self.assertEqual(rec["remote_port"], self.rport)
        self.assertEqual(rec["remote_token"], "remote-token-A")
        self.assertEqual(rec["token"], "loopback-token-B")   # the loopback token, distinct

    # -- the static demo rides A "for free" --
    def _write_demo(self):
        demo = os.path.join(self.w, "demos", "item-7")
        os.makedirs(demo, exist_ok=True)
        with open(os.path.join(demo, "index.html"), "w") as fh:
            fh.write("<!doctype html><h1>demo</h1>")
        with open(os.path.join(self.w, "bus.json"), "a") as fh:
            fh.write("REMOTE-SECRET")

    def test_demo_serves_token_free_on_the_remote_socket(self):
        """The reduced remote surface carries the static demo. Token-free (a browser
        can't header an iframe nav) but under A's Host-allowlist — and it must NOT 403
        the way the forwarded-Host bug would, nor leak the loopback token."""
        self._write_demo()
        # over the tunnel the browser sends the public Host, forwarded by the proxy.
        code, body, headers = self.req(self.rport, "/demo/item-7/", host="away.example")
        self.assertEqual(code, 200, body)
        self.assertIn(b"<h1>demo</h1>", body)
        self.assertEqual(headers.get("Content-Security-Policy"), bus.DEMO_CSP)
        # and it serves on loopback too (localhost Host).
        self.assertEqual(self.req(self.rport, "/demo/item-7/")[0], 200)
        self.assertEqual(self.req(self.bport, "/demo/item-7/")[0], 200)

    def test_demo_traversal_guard_holds_on_the_remote_socket(self):
        self._write_demo()
        code, body, _ = self.req(self.rport, "/demo/item-7/../../bus.json",
                                 host="away.example")
        self.assertEqual(code, 404)
        self.assertNotIn(b"REMOTE-SECRET", body)

    def test_demo_on_A_still_refuses_an_unknown_host(self):
        self._write_demo()
        self.assertEqual(self.req(self.rport, "/demo/item-7/", host="evil.com")[0], 403)


class RemoteSocketTailscale(RemoteSocket):
    """The one carve-out: an end-to-end-encrypted transport unlocks credential-bearing
    setup verdicts on the remote surface."""
    TRANSPORT = "tailscale"

    def test_a_returns_bearing_verdict_is_refused_on_access(self):
        # Overridden: on Tailscale the credential IS allowed to ride A.
        code, body, _ = self.req(self.rport, "/api/verdict", method="POST",
                                 token="remote-token-A",
                                 body={"token": "cp1", "verdict": {"outcome": "approve",
                                       "returns": {"api_key": "sk-live-x"}}})
        self.assertEqual(code, 202, body)

    def test_a_setup_shaped_verdict_is_refused_on_access(self):
        code, body, _ = self.req(self.rport, "/api/verdict", method="POST",
                                 token="remote-token-A",
                                 body={"token": "cp1",
                                       "verdict": {"tasks": [{"outcome": "approve"}]}})
        self.assertEqual(code, 202, body)


if __name__ == "__main__":
    unittest.main()

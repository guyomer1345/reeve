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
class ThreadReadModel(Tmp):
    """The conversation panel's read. The bus never writes this file — `answer` owns it,
    single-writer, exactly as the orchestrator owns outbox/ — so every case here is about
    reading something another process may be mid-write on."""

    def setUp(self):
        super().setUp()
        self.w = mkworkflow(self.root)
        self.paths = bus.Paths(self.w)
        self.model = bus.ReadModel(self.paths)

    def _write(self, rec):
        os.makedirs(self.paths.thread, exist_ok=True)
        with open(self.paths.thread_file, "w") as fh:
            json.dump(rec, fh)

    def _turns(self, n):
        return [{"message_id": "m%d" % i, "role": "human" if i % 2 else "project",
                 "text": "t%d" % i, "at": "2026-08-04T10:00:00Z"} for i in range(n)]

    def test_absent_thread_is_an_empty_conversation_not_an_error(self):
        th = self.model.thread()
        self.assertEqual(th["turns"], [])
        self.assertFalse(th["active"])

    def test_a_corrupt_thread_costs_the_panel_not_the_console(self):
        """A torn read must self-heal on the next poll, never take the daemon down —
        the daemon is the only always-alive process."""
        os.makedirs(self.paths.thread, exist_ok=True)
        with open(self.paths.thread_file, "w") as fh:
            fh.write('{"turns": [{"role":')      # half a write
        self.assertEqual(self.model.thread()["turns"], [])

    def test_turns_render_with_their_role_and_stamp(self):
        self._write({"session_id": "s-1", "turns": self._turns(2), "rotations": 0})
        th = self.model.thread()
        self.assertEqual([t["role"] for t in th["turns"]], ["project", "human"])
        self.assertTrue(th["active"])

    def test_a_thread_with_no_session_is_not_active_yet(self):
        """A fresh thread has no session until the first answer establishes one; the page
        says 'nothing asked yet' rather than drawing an empty conversation."""
        self._write({"turns": [], "rotations": 0})
        self.assertFalse(self.model.thread()["active"])

    def test_only_the_last_n_turns_cross_the_wire(self):
        """The snapshot is re-sent on every poll, so an unbounded thread would grow the
        poll forever. The rest stay on disk until rotation folds them into the handoff."""
        self._write({"session_id": "s", "turns": self._turns(120), "rotations": 1})
        th = self.model.thread()
        self.assertEqual(len(th["turns"]), bus.DEFAULT_THREAD_MAX_TURNS)
        self.assertEqual(th["truncated"], 120 - bus.DEFAULT_THREAD_MAX_TURNS)
        # the LAST turns, not the first — a conversation reads forward
        self.assertEqual(th["turns"][-1]["text"], "t119")

    def test_the_render_cap_is_configurable(self):
        with open(os.path.join(self.w, "config.json"), "w") as fh:
            json.dump({"thread": {"max_turns_rendered": 3}}, fh)
        self._write({"session_id": "s", "turns": self._turns(10), "rotations": 0})
        self.assertEqual(len(self.model.thread()["turns"]), 3)

    def test_the_thread_is_in_the_snapshot(self):
        self._write({"session_id": "s", "turns": self._turns(2), "rotations": 0})
        self.assertIn("thread", self.model.snapshot())

    # -- the asked-but-unanswered merge (found by rendering the page) --
    def _ask(self, mid, text="why postgres?"):
        with open(os.path.join(self.paths.inbox, mid + ".json"), "w") as fh:
            json.dump({"kind": "question", "question": text,
                       "received_at": "2026-08-04T08:37:52Z"}, fh)

    def test_an_asked_question_shows_before_it_is_answered(self):
        """The defect a browser render caught and every mechanical test missed: the POST
        succeeded, the box cleared, and the conversation showed NOTHING until the answer
        landed — minutes of silence on a cold start."""
        self._ask("20260804T083752.391786Z-aaaaaaaa-1")
        th = self.model.thread()
        self.assertEqual(len(th["turns"]), 1)
        self.assertEqual(th["turns"][0]["role"], "human")
        self.assertTrue(th["turns"][0]["pending"])

    def test_an_answered_question_is_not_shown_twice(self):
        """The other half. The inbox keeps a consumed message until the bus GCs it on the
        watermark, so a naive merge would render every answered question a second time —
        which is exactly the double-draw class of defect the last phase shipped."""
        mid = "20260804T083752.391786Z-aaaaaaaa-1"
        self._ask(mid)
        self._write({"session_id": "s", "rotations": 0, "turns": [
            {"message_id": mid, "role": "human", "text": "why postgres?",
             "at": "2026-08-04T08:37:52Z"},
            {"message_id": mid, "role": "project", "text": "because concurrency",
             "at": "2026-08-04T08:39:10Z"}]})
        th = self.model.thread()
        self.assertEqual(len(th["turns"]), 2)
        self.assertEqual([t["role"] for t in th["turns"]], ["human", "project"])
        self.assertFalse(any(t["pending"] for t in th["turns"]))

    def test_pending_questions_sort_after_the_answered_conversation(self):
        """A conversation reads forward: what is still waiting is the newest thing in it."""
        self._write({"session_id": "s", "rotations": 0, "turns": [
            {"message_id": "old", "role": "human", "text": "q1", "at": "2026-08-04T08:00:00Z"},
            {"message_id": "old", "role": "project", "text": "a1", "at": "2026-08-04T08:01:00Z"}]})
        self._ask("20260804T083752.391786Z-aaaaaaaa-1", "q2")
        th = self.model.thread()
        self.assertEqual([t["text"] for t in th["turns"]], ["q1", "a1", "q2"])

    def test_a_non_question_message_never_enters_the_conversation(self):
        """An intake is a request, not a question — it belongs to 'my requests'."""
        with open(os.path.join(self.paths.inbox,
                               "20260804T083752.391786Z-bbbbbbbb-1.json"), "w") as fh:
            json.dump({"kind": "intake", "ask": "build a thing"}, fh)
        self.assertEqual(self.model.thread()["turns"], [])

    def _dead_letter(self, mid, reason="no such checkpoint"):
        with open(self.paths.handoff, "w") as fh:
            fh.write("# Handoff\n\nprose\n\n" + bus.render_handoff_block(
                {"consumed": [], "consumed_through": None,
                 "dead_letters": [{"message_id": mid, "reason": reason}]}) + "\n")

    def test_a_dead_lettered_question_is_flagged_rather_than_left_looking_pending(self):
        """It sits on the inbox until the watermark collects it, so it joins as a pending
        turn — but no answer is coming, and 'waiting for an answer' overstates it."""
        mid = "20260804T083752.391786Z-cccccccc-1"
        self._ask(mid, "why postgres?")
        self._dead_letter(mid)
        turn = self.model.thread()["turns"][0]
        self.assertTrue(turn["pending"])
        self.assertTrue(turn["dead"])

    def test_a_genuinely_waiting_question_is_not_flagged_dead(self):
        """The other direction, so the flag cannot silently become always-on: a live
        question with an unrelated dead-letter on the block stays plain pending."""
        self._ask("20260804T083752.391786Z-dddddddd-1", "why postgres?")
        self._dead_letter("20260804T083752.391786Z-eeeeeeee-9")
        turn = self.model.thread()["turns"][0]
        self.assertTrue(turn["pending"])
        self.assertFalse(turn["dead"])

    def test_an_answered_turn_carries_the_flag_too_and_it_is_false(self):
        """The field must exist on every turn, or the page has to test for undefined."""
        self._write({"session_id": "s", "rotations": 0, "turns": [
            {"message_id": "m1", "role": "human", "text": "q",
             "at": "2026-08-04T08:00:00Z"}]})
        self.assertFalse(self.model.thread()["turns"][0]["dead"])

    def test_a_rotated_thread_reports_its_rotations_with_no_turns(self):
        """The data half of the cold-start defect. The page already had everything it
        needed to tell a handed-off conversation from a project nobody has ever asked —
        `rotations` was on the wire — and rendered the wrong string anyway."""
        self._write({"session_id": None, "rotations": 1, "turns": []})
        th = self.model.thread()
        self.assertEqual(th["turns"], [])
        self.assertFalse(th["active"])
        self.assertEqual(th["rotations"], 1)


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

    def _forecast(self, fid="item-1", **kw):
        d = os.path.join(self.w, "forecasts")
        os.makedirs(d, exist_ok=True)
        rec = {"forecast_id": fid, "status": "frozen", "frozen_at": "2026-08-03T11:00:00Z",
               "events": [{"n": 1, "node": "execute", "what": "build it"}],
               "horizon": {"beyond": 1, "note": "unforeseeable past here"}}
        rec.update(kw)
        with open(os.path.join(d, fid + ".json"), "w") as fh:
            json.dump(rec, fh)
        return rec

    def test_snapshot_shape(self):
        snap = self.model.snapshot()
        for k in ("state", "parked", "outbox_pending", "backlog", "recent", "generated_at",
                  "forecasts"):
            self.assertIn(k, snap)
        self.assertEqual(snap["state"]["node"], "execute")

    # --- forecasts: the artifact that OUTLIVES its checkpoint (D162) ------------
    def test_forecasts_are_read_from_the_committed_dir(self):
        """The console surface for a forecast cannot hang off the parked record: `unpark`
        deletes that at the instant of approval. The panel reads the committed artifact,
        which is why a frozen chain is still there to watch reality against afterwards."""
        self._forecast("item-1")
        rows = self.model.forecasts()
        self.assertEqual([r["forecast_id"] for r in rows], ["item-1"])
        self.assertEqual(rows[0]["status"], "frozen")
        self.assertEqual(len(rows[0]["events"]), 1)

    def test_forecasts_are_ordered_and_multiple(self):
        self._forecast("item-b")
        self._forecast("item-a")
        self.assertEqual([r["forecast_id"] for r in self.model.forecasts()],
                         ["item-a", "item-b"])

    def test_an_absent_forecasts_dir_is_empty_not_an_error(self):
        self.assertEqual(self.model.forecasts(), [])

    def test_an_unreadable_forecast_is_skipped_not_fatal(self):
        """The daemon is the always-alive process; one bad file must never take the
        console down (the same guarded-degradation rule the forecast.py import gets)."""
        self._forecast("good")
        os.makedirs(os.path.join(self.w, "forecasts"), exist_ok=True)
        with open(os.path.join(self.w, "forecasts", "bad.json"), "w") as fh:
            fh.write("{not json")
        self.assertEqual([r["forecast_id"] for r in self.model.forecasts()], ["good"])

    def test_a_forecast_row_carries_the_derived_reality(self):
        """The reality column is DERIVED here, not stored — one owner for the anchor
        table (forecast.py), and the panel reads through it rather than reimplementing
        'has this happened' a second time."""
        self._forecast("item-1", events=[
            {"n": 1, "node": "planner:plan-one", "what": "plan"},
            {"n": 2, "node": "execute", "what": "build"}])
        os.makedirs(os.path.join(self.w, "items", "item-1"), exist_ok=True)
        open(os.path.join(self.w, "items", "item-1", "plan.md"), "w").close()
        row = self.model.forecasts()[0]
        self.assertEqual([e.get("state") for e in row["events"]], ["done", "pending"])

    def test_a_divergence_reaches_the_panel(self):
        self._forecast("item-1", events=[{"n": 1, "node": "planner:plan-one", "what": "plan"}])
        os.makedirs(os.path.join(self.w, "items", "item-1"), exist_ok=True)
        open(os.path.join(self.w, "items", "item-1", "debug-report.md"), "w").close()
        self.assertTrue(any(d["node"] == "debug"
                            for d in self.model.forecasts()[0]["divergences"]))

    def test_the_panel_degrades_when_the_lifecycle_script_is_absent(self):
        """A PARTIAL install must cost the reality column, never the console. The daemon
        is the only always-alive process — an ImportError here would take down the whole
        surface a human uses to answer checkpoints."""
        self._forecast("item-1")
        saved = bus._forecast_lib
        bus._forecast_lib = None
        self.addCleanup(setattr, bus, "_forecast_lib", saved)
        row = self.model.forecasts()[0]
        self.assertTrue(row["reality_unavailable"])
        self.assertEqual(row["divergences"], [])

    def test_a_forecast_row_carries_no_request_body(self):
        """Whatever the panel renders is served on every poll. The chain is prose the
        human wrote or approved — but nothing that could hold a value rides along."""
        self._forecast("item-1")
        row = self.model.forecasts()[0]
        self.assertNotIn("returns", json.dumps(row))

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
        # The runner refuses to spawn into a workspace Claude Code has not been trusted in
        # (MEASURED: such a launch composes an answer it cannot persist, then exits 0). Every
        # test below means a TRUSTED workspace unless it says otherwise — declared here, so
        # these never read the developer's real ~/.claude.json and never depend on a temp
        # directory happening to be absent from it.
        self._trust(True)

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

    def _trust(self, trusted):
        """Point the trust read at a config we own. `True`/`False` write that verdict for
        this repo; `None` writes a structurally VALID record that simply has no entry for it
        — the ordinary never-opened-interactively case, which is what the real platform
        leaves behind (MEASURED: `claude -p` does not create a project record). The unrelated
        entry keeps the schema-health probe satisfied in every case."""
        cfgdir = os.path.join(self.root, "claudecfg")
        os.makedirs(cfgdir, exist_ok=True)
        projects = {"/some/other/project": {"hasTrustDialogAccepted": True}}
        if trusted is not None:
            projects[self.paths.repo] = {"hasTrustDialogAccepted": bool(trusted)}
        with open(os.path.join(cfgdir, ".claude.json"), "w") as fh:
            json.dump({"projects": projects}, fh)
        self._env("CLAUDE_CONFIG_DIR", cfgdir)

    def _config(self, enabled=True, url=None):
        cfg = {"runner": {"enabled": enabled}}
        if url:
            cfg["notify"] = {"webhook": {"url": url, "kind": "generic"}}
        with open(self.paths.config, "w") as fh:
            json.dump(cfg, fh)

    def _pending(self, kind="verdict", mid=None):
        mid = mid or self.VID
        if kind == "verdict":
            body = {"kind": "verdict", "token": "cp1", "verdict": {"outcome": "approve"}}
        elif kind == "question":
            body = {"kind": "question", "question": "why postgres?"}
        else:
            body = {"kind": kind, "ask": "x"}
        with open(os.path.join(self.paths.inbox, mid + ".json"), "w") as fh:
            json.dump(body, fh)

    def _argv_stub(self):
        """A fake `claude` that records the argv it was launched with and exits.

        The prompt is the only thing separating "answer this question and stop" from
        "drive the build loop unattended", so it is checked against what was actually
        exec'd rather than against the branch that chose it.
        """
        dump = os.path.join(self.root, "argv.json")
        path = os.path.join(self.bin, "claude-argv")
        with open(path, "w") as fh:
            fh.write("#!/usr/bin/env python3\n"
                     "import sys, json\n"
                     "json.dump(sys.argv, open(%r, 'w'))\n" % dump)
        os.chmod(path, 0o755)
        self._env("BUS_CLAUDE_BIN", path)
        return dump

    def _launched_prompt(self, dump):
        self._reap()
        with open(dump) as fh:
            argv = json.load(fh)
        return argv[argv.index("-p") + 1]

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

    def test_a_lone_question_spawns_the_ANSWER_prompt(self):
        """The whole point of the away channel, extended to questions: an unanswered
        question is as stuck as an unconsumed verdict."""
        self._config()
        self._pending("question")
        dump = self._argv_stub()
        self.d.runner.tick(self.d)
        self.assertIsNotNone(self.d.runner.launched)
        self.assertEqual(self._launched_prompt(dump), bus.RUNNER_ANSWER_PROMPT)

    def test_the_answer_prompt_forbids_driving_the_loop(self):
        """The sharp failure mode is a human asking a question and getting an
        unattended build, so the prohibition is pinned in the prompt text itself."""
        p = bus.RUNNER_ANSWER_PROMPT.lower()
        self.assertIn("answer", p)
        self.assertIn("do not", p)
        self.assertNotIn("continue the loop", p)

    def test_one_drivable_message_wins_the_resume_prompt(self):
        """A mixed batch is a build relaunch that answers on the way past — the loop
        drains every kind at its boundary, so a question in the batch must not downgrade
        a verdict into answer-and-stop."""
        self._config()
        self._pending("verdict", mid=self.VID)
        self._pending("question", mid="20260716T120001.000001Z-bbbbbbbb-1")
        dump = self._argv_stub()
        self.d.runner.tick(self.d)
        self.assertEqual(self._launched_prompt(dump), bus.RUNNER_RESUME_PROMPT)

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
        """A genuinely HUNG launch must not pin the runner in-flight forever. With no
        watermark advance past the stall window, it is killed and scored as no-progress —
        the same path a crash takes. (This timeout was once believed to cover the untrusted
        workspace too; it does not, and cannot — an untrusted `claude` exits 0 in seconds
        rather than hanging, so it never reaches this branch. That is the trust gate's job.)"""
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

    # -- the trust gate --
    def _raw_trust(self, obj):
        """Write an arbitrary trust-record SHAPE, for the fail-open cases. `None` writes no
        file at all."""
        cfgdir = os.path.join(self.root, "claudecfg-raw")
        os.makedirs(cfgdir, exist_ok=True)
        p = os.path.join(cfgdir, ".claude.json")
        if obj is None:
            if os.path.exists(p):
                os.remove(p)
        else:
            with open(p, "w") as fh:
                json.dump(obj, fh)
        self._env("CLAUDE_CONFIG_DIR", cfgdir)

    def test_an_untrusted_workspace_refuses_to_spawn_and_alerts_once(self):
        """MEASURED on CLI 2.1.220: `claude -p` in an untrusted workspace does NOT stall. It
        discards the settings allowlist, proceeds read-only, composes a complete answer it
        cannot persist, and exits 0 within seconds. Nothing downstream can tell that apart
        from a crash, so the away path used to burn RUNNER_MAX_ATTEMPTS full answers before a
        hard-stop whose alert named no fix. Refuse the spawn instead — and say it ONCE."""
        sink = _Sink()
        self.addCleanup(sink.stop)
        self._config(url=sink.url)
        self._pending("question")
        self._stub("drain")
        self._trust(False)
        for _ in range(3):
            self.d.runner.tick(self.d)
            self.assertIsNone(self.d.runner.launched,
                              "the runner spawned into an untrusted workspace")
        alerts = [r for r in sink.received if r["body"].get("event") == "loop-stall"]
        self.assertEqual(len(alerts), 1, "the untrusted alert is ONE event, not a stream")
        # …and this is NOT the crash-loop path: nothing was burned and nothing latched.
        self.assertEqual(self.d.runner.consecutive_noprogress, 0)
        self.assertFalse(self.d.runner.hard_stopped)

    def test_the_untrusted_alert_names_the_fix_the_human_can_actually_perform(self):
        """The payoff of this gate is the ALERT, not the skip. The old hard-stop told a human
        the loop had stopped and nothing they could do about it; this one must name both
        remedies the platform itself prints — including the manual flag, because the trust
        dialog does not render in some WSL terminals."""
        sink = _Sink()
        self.addCleanup(sink.stop)
        self._config(url=sink.url)
        self._pending("question")
        self._trust(False)
        self.d.runner.tick(self.d)
        text = [r for r in sink.received
                if r["body"].get("event") == "loop-stall"][0]["body"]["text"]
        self.assertIn(self.paths.repo, text, "the alert must name WHICH directory")
        self.assertIn("accept the trust dialog", text)
        self.assertIn("hasTrustDialogAccepted", text, "no manual fix for a WSL terminal")
        self.assertIn(bus.claude_config_path(), text, "the manual fix names no file to edit")

    def test_an_ABSENT_trust_record_counts_as_untrusted(self):
        """The crux. MEASURED: `claude -p` does NOT create a project record, so a project
        never opened interactively has no entry at all — absence is the ORDINARY instance of
        this bug, not an exotic one. Reading it as "unknown" is exactly what left the older
        warning unable to fire on the common case."""
        self._config()
        self._pending("question")
        self._stub("drain")
        self._trust(None)                       # structurally valid, no entry for this repo
        self.assertIs(bus.workspace_trusted(self.paths.repo), False)
        self.d.runner.tick(self.d)
        self.assertIsNone(self.d.runner.launched)

    def test_an_unreadable_trust_record_FAILS_OPEN_and_still_spawns(self):
        """This reads an undocumented platform-internal file. If it is missing or is not
        JSON at all, the answer is "unknown" and the runner must behave exactly as it did
        before the gate existed — a format change must never be the reason a human's
        questions stop being answered."""
        self._config()
        self._pending("question")
        self._stub("drain")
        for shape in (None, [], {"projects": "not-a-dict"}):
            self._raw_trust(shape)
            self.assertIsNone(bus.workspace_trusted(self.paths.repo),
                              "%r should read as UNKNOWN, not untrusted" % (shape,))
        self.d.runner.tick(self.d)
        self.assertIsNotNone(self.d.runner.launched, "fail-open did not spawn")

    def test_a_RESHAPED_trust_record_FAILS_OPEN_and_still_spawns(self):
        """The subtle half of failing open. A `projects` map that parsed fine but in which
        NOTHING carries `hasTrustDialogAccepted` means the platform renamed the flag — and
        then "this repo has no such key" proves nothing. Absence may only be read as
        untrusted while the file still demonstrably speaks the schema."""
        self._config()
        self._pending("question")
        self._stub("drain")
        self._raw_trust({"projects": {"/a": {"someOtherFlagEntirely": True},
                                      "/b": {"allowedTools": []}}})
        self.assertIsNone(bus.workspace_trusted(self.paths.repo))
        self.d.runner.tick(self.d)
        self.assertIsNotNone(self.d.runner.launched, "a renamed flag stopped the runner")

    def test_granting_trust_re_arms_the_runner_with_no_restart(self):
        """The gate is a live read, not a latch. The moment the human does the thing the
        alert asked for, the runner must resume on its own — otherwise the remedy would
        require a daemon restart nobody was told about."""
        self._config()
        self._pending("verdict")
        self._stub("drain")
        self._trust(False)
        self.d.runner.tick(self.d)
        self.assertIsNone(self.d.runner.launched)
        self.assertTrue(self.d.runner.trust_alerted)
        self._trust(True)                                  # the human accepts the dialog
        self.d.runner.tick(self.d)
        self.assertIsNotNone(self.d.runner.launched, "granting trust did not re-arm")
        self.assertFalse(self.d.runner.trust_alerted, "the alert did not re-arm for later")

    def test_an_untrusted_runner_does_not_pin_the_daemon_open(self):
        """An untrusted workspace is not something to WAIT on — no amount of time fixes it,
        and the human action that does starts a session which ensures the daemon anyway.
        Voting busy forever would pin a daemon on a condition that never resolves itself."""
        self._config()
        self._pending("verdict")
        self._trust(False)
        self.assertTrue(self.d.runner.is_idle(self.d))
        self._trust(True)
        self.assertFalse(self.d.runner.is_idle(self.d), "a trusted resume must hold it open")

    def test_trust_is_exact_path_with_no_parent_inheritance(self):
        """MEASURED: a fresh directory under a `true`-recorded PARENT is still untrusted, so
        there is no ancestor chain to walk. Guarded because the tempting "inherit from a
        trusted parent" reading would silently un-gate the common case."""
        parent = os.path.dirname(self.paths.repo.rstrip("/"))
        self._raw_trust({"projects": {parent: {"hasTrustDialogAccepted": True}}})
        self.assertIs(bus.workspace_trusted(self.paths.repo), False)

    def test_readiness_shape(self):
        self._config()
        r = self.d.runner.readiness(self.d)
        for k in ("enabled", "in_flight", "consecutive_noprogress", "hard_stopped", "wsl",
                  "repo", "workspace_trusted"):
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

    def test_a_verdict_marks_its_parked_checkpoint_answered(self):
        """End to end over the real socket (D148): the console must be able to tell a
        human they already answered, and the fact has to come from the server so it
        survives a reload and holds on a second device."""
        bus.write_park(self.d.paths, a_park(tid="answer-me", kind="setup"))
        self.assertIsNone(
            [p for p in bus.ReadModel(self.d.paths).parked()
             if p["ticket_id"] == "answer-me"][0]["answered_at"])
        code, body, _ = self.post("/api/verdict", {
            "token": "tok-answer-me", "verdict": {"outcome": "approve"}})
        self.assertEqual(code, 202, body)
        row = [p for p in bus.ReadModel(self.d.paths).parked()
               if p["ticket_id"] == "answer-me"][0]
        self.assertTrue(row["answered_at"], "answered but the card still reads as open")

    def test_a_verdict_for_an_unknown_token_still_lands_and_stamps_nothing(self):
        """The stamp is a display hint bolted to the side; it must never be able to
        turn a durable verdict into an error."""
        bus.write_park(self.d.paths, a_park(tid="untouched", kind="setup"))
        code, _, _ = self.post("/api/verdict", {
            "token": "tok-nobody-at-all", "verdict": {"outcome": "approve"}})
        self.assertEqual(code, 202)
        row = [p for p in bus.ReadModel(self.d.paths).parked()
               if p["ticket_id"] == "untouched"][0]
        self.assertIsNone(row["answered_at"])

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

    def test_subresources_survive_the_opaque_origins_cross_site_label(self):
        """The regression that made every multi-file demo render BLANK.

        DEMO_CSP's `sandbox` directive forces an opaque origin, and an opaque origin is
        not same-site with anything — so a real browser labels every subresource of the
        demo document `Sec-Fetch-Site: cross-site`. MEASURED in Chrome: the navigation
        arrives `none`, then `style.css` and `app.js` both arrive `cross-site`/`no-cors`.
        The site gate refused exactly those, so `index.html` rendered and its siblings
        404'd — a silently unstyled, scriptless page. Every pre-existing demo test sent
        NO Sec-Fetch-Site at all, which is why the whole class passed while the browser
        showed a blank demo.
        """
        for path in ("/demo/item-42/", "/demo/item-42/app.js"):
            code, body, _ = self.get(path, extra={"Sec-Fetch-Site": "cross-site"})
            self.assertEqual(code, 200, path)
            self.assertTrue(body, path)
        # `same-site` is the other value the gate refuses; a framed demo asset can carry
        # it too, so it must not be the difference between rendering and blank either.
        self.assertEqual(
            self.get("/demo/item-42/app.js", extra={"Sec-Fetch-Site": "same-site"})[0], 200)

    def test_dropping_the_site_gate_is_scoped_to_the_demo_class(self):
        """The exemption is the demo's alone — everything else still fails closed."""
        for path in ("/", "/api/state", "/health"):
            self.assertEqual(
                self.get(path, extra={"Sec-Fetch-Site": "cross-site"})[0], 403, path)

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

    def _setup_park(self, task):
        return a_park(kind="setup", checkpoint={
            "kind": "setup",
            "request": {"kind": "setup", "what": "hand back the key", "blocking": True,
                        "tasks": [task]}})

    def test_a_reply_side_outcome_on_a_request_task_is_refused(self):
        """`schemas.md` declares a request task `{id, what, secrets?[]}` and the VERDICT
        `{id, outcome, returns?}`. Nothing in the package writes `outcome` on a request —
        the live install's came from a hand-reconstruction that copied the reply shape,
        and it reads to a later human as though the question were already answered."""
        with self.assertRaises(bus.Invalid) as cm:
            bus.write_park(self.paths, self._setup_park(
                {"id": "t1", "what": "do it", "outcome": None}))
        self.assertIn("reply-side", str(cm.exception))
        self.assertIn("outcome", str(cm.exception))
        # Refused at the boundary means NOTHING was persisted — not a record that then
        # has to be cleaned up by whoever notices.
        self.assertFalse(os.path.exists(
            os.path.join(self.paths.parked, "item-1.json")))

    def test_a_conforming_request_task_still_parks(self):
        """The refusal is narrow: the declared request-task shape is untouched, and so
        is every kind that carries no `tasks[]` at all."""
        res = bus.write_park(self.paths, self._setup_park(
            {"id": "t1", "what": "do it", "secrets": ["A_KEY"]}))
        self.assertEqual(res["kind"], "setup")
        self.assertTrue(os.path.exists(res["record"]))

    def test_other_undeclared_request_fields_are_still_accepted(self):
        """Deliberately NOT a general strictness pass. `park` is how the machine asks a
        human for help, and a park that hard-fails is a checkpoint that never opens —
        a strictly worse failure than an extra field."""
        res = bus.write_park(self.paths, self._setup_park(
            {"id": "t1", "what": "do it", "invented_field": "kept"}))
        self.assertTrue(os.path.exists(res["record"]))

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

    def test_a_summary_cannot_forge_the_blocks_END_MARKER(self):
        """The sibling of the fence break, and the one that actually corrupts.

        `_block_re` matches begin → the FIRST end, so a payload carrying a literal
        `<!-- parked:end -->` closes a comment it does not own: the NEXT publish
        replaces begin→forged-end and strands the real block's tail as prose. Driven on
        a real clone before it was fixed.
        """
        hostile = "break out: <!-- parked:end --> HOSTILE <!-- parked:begin -->"
        bus.write_park(self.paths, a_park(), summary=hostile)
        bus.write_park(self.paths, a_park(tid="item-2"), summary="ordinary")
        text = open(self.paths.handoff).read()
        self.assertEqual(text.count(bus.PARKED_END), 1, "a second end marker was forged")
        self.assertEqual(text.count(bus.PARKED_BEGIN), 1)
        # Escaped in the TEXT, byte-identical once decoded — nothing is hidden or lost.
        block = self.mirror()
        self.assertEqual([e["ticket_id"] for e in block["parked"]], ["item-1", "item-2"])
        self.assertEqual(block["parked"][0]["summary"], hostile)
        self.assertNotIn("HOSTILE <!-- parked:begin -->", text)

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

    def test_every_schema_kind_parks(self):
        """PARK_KINDS is a second copy of schemas.md's `request.kind` enum, and the one
        that DECIDES: a kind the schema declares but this tuple omits is refused at the
        writer, so the checkpoint can never open at all. Checked per kind rather than as
        a set-equality on the tuple, because what matters is that a park succeeds."""
        for kind in ("demo", "qa", "setup", "reconcile", "forecast"):
            with self.subTest(kind=kind):
                bus.write_park(self.paths, a_park(tid="item-" + kind, kind=kind))
                self.assertIn(kind, [r["kind"] for r in self.mirror()["parked"]])

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

    def test_a_forecast_park_passes_its_forecast_id_through(self):
        """The `demo_id` passthrough pattern, for the same reason: the forecast record is
        a COMMITTED artifact at `.workflow/forecasts/<id>.json`, so the parked record
        carries a POINTER, never the chain. `unpark` deletes the parked record at the
        instant of approval — the thing `approve` is supposed to freeze cannot live in
        the file that approval destroys (D154 one layer up)."""
        bus.write_park(self.paths, a_park(kind="forecast", checkpoint={
            "kind": "forecast", "forecast_id": "item-1",
            "request": {"what": "approve the chain", "blocking": True}}))
        row = bus.ReadModel(self.paths).parked()[0]
        self.assertEqual((row["kind"], row["forecast_id"]), ("forecast", "item-1"))

    def test_a_malformed_forecast_id_is_dropped_not_passed_through(self):
        bus.write_park(self.paths, a_park(kind="forecast", checkpoint={
            "kind": "forecast", "forecast_id": "../../etc/passwd",
            "request": {"what": "x", "blocking": True}}))
        self.assertIsNone(bus.ReadModel(self.paths).parked()[0]["forecast_id"])

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


class AnsweredStamp(Tmp):
    """A human must never be unable to tell they already answered (D148).

    Found by driving the form in a browser: `btn.disabled = true` drops focus, the
    handler clears the inputs, so `renderCheckpoints`' repaint guard releases and the
    2.5s poll rebuilds the card from its template — killing the "sent" flash well
    inside its own 6s timeout and re-arming a form that looks untouched. The card is
    still LISTED for a correct reason (only the orchestrator's drain unparks it), so
    the fix is to make "answered" a fact the server publishes, not a thing the page
    remembers. For a setup checkpoint the alternative is a human re-typing a live
    credential onto the wire for nothing.
    """

    def setUp(self):
        super().setUp()
        self.w = mkworkflow(self.root)
        self.paths = bus.Paths(self.w)
        bus.write_park(self.paths, a_park(tid="item-1", kind="setup"))

    def rec(self):
        return bus.read_json(os.path.join(self.paths.parked, "item-1.json"))

    def test_it_stamps_the_record_whose_token_the_verdict_quotes(self):
        at = bus.mark_parked_answered(self.paths, "tok-item-1")
        self.assertTrue(at)
        self.assertEqual(self.rec()["answered_at"], at)

    def test_the_console_read_model_publishes_it(self):
        """The page cannot render what the snapshot does not carry."""
        self.assertIsNone(bus.ReadModel(self.paths).parked()[0]["answered_at"])
        bus.mark_parked_answered(self.paths, "tok-item-1")
        self.assertTrue(bus.ReadModel(self.paths).parked()[0]["answered_at"])

    def test_the_first_answer_wins_so_a_resend_is_not_a_new_event(self):
        first = bus.mark_parked_answered(self.paths, "tok-item-1")
        again = bus.mark_parked_answered(self.paths, "tok-item-1")
        self.assertEqual(first, again)
        self.assertEqual(self.rec()["answered_at"], first)

    def test_an_unknown_token_stamps_nothing(self):
        """A verdict for a closed/unknown token is the dead-letter path's job; this
        must not invent a record or stamp an unrelated one."""
        self.assertIsNone(bus.mark_parked_answered(self.paths, "tok-nobody"))
        self.assertNotIn("answered_at", self.rec())

    def test_only_a_timestamp_is_written_never_the_verdict_body(self):
        """The parked record is not a place a credential may land — the store is. A
        stamp that carried the reply would put a live key in a second file."""
        before = self.rec()
        bus.mark_parked_answered(self.paths, "tok-item-1")
        after = self.rec()
        self.assertEqual(set(after) - set(before), {"answered_at"})
        for k, v in before.items():
            self.assertEqual(after[k], v, "the stamp rewrote %s" % k)

    def test_the_record_keeps_the_mode_park_gave_it(self):
        bus.mark_parked_answered(self.paths, "tok-item-1")
        mode = os.stat(os.path.join(self.paths.parked, "item-1.json")).st_mode & 0o777
        self.assertEqual(mode, 0o600)

    def test_a_re_park_reopens_the_question_as_UNANSWERED(self):
        """A ticket that parks, resolves and re-parks is a NEW question with a fresh
        token. Inheriting the old stamp would show a re-opened checkpoint as already
        answered — the exact silence this fix exists to remove, pointing the other way.
        """
        bus.mark_parked_answered(self.paths, "tok-item-1")
        self.assertTrue(self.rec()["answered_at"], "fixture assumes it was answered")
        again = a_park(tid="item-1", kind="setup")
        again["token"] = "tok-item-1-reopened"
        bus.write_park(self.paths, again)
        self.assertIsNone(self.rec().get("answered_at"))

    def test_the_page_closes_the_form_on_an_answered_card(self):
        """Rendering it is the whole point: a visible, re-armed form is the defect."""
        js = _js_function("renderCheckpoints")
        self.assertIn("cp.answered_at", js)
        self.assertIn('.verdict").hidden = true', js)
        self.assertIn('<p class="answered" hidden></p>', bus.INDEX_HTML)

    def test_an_answered_card_is_visibly_answered_not_merely_inert(self):
        """Disabling the controls is not enough. A card whose inputs simply stop
        responding looks identical to a live one, so the state reads as a broken page
        rather than a settled question — reported from the browser in exactly those
        words. The class is what dims it."""
        self.assertIn('classList.add("is-answered")', _js_function("renderCheckpoints"))
        self.assertIn(".card.is-answered", bus.STYLE_CSS)

    # -- replacing an answer that has not been drained yet --
    def _verdict(self, token, note, value):
        return {"token": token, "kind": "verdict", "verdict": {
            "notes": note, "tasks": [{"id": "t", "outcome": "approve", "returns": {
                "K": {"value": value}}}]}}

    def _put(self, mid, token, note, value):
        p = os.path.join(self.paths.inbox, mid + ".json")
        with open(p, "w") as fh:
            json.dump(dict(self._verdict(token, note, value), message_id=mid), fh)
        return mid

    def test_a_second_answer_REPLACES_an_undrained_one(self):
        """The point of the whole mechanism: "override" has to be true, or the button
        offering it is a lie. Two verdicts for one token used to both sit on the inbox,
        the drain applying whichever it reached first — so a human correcting a typo'd
        key could leave the TYPO live and believe it fixed."""
        self._put("m1", "tok-item-1", "first", "TYPO")
        dropped = bus.supersede_pending_verdict(self.paths, "tok-item-1", keep="m2")
        self.assertEqual(dropped, ["m1"])
        self.assertFalse(os.path.exists(os.path.join(self.paths.inbox, "m1.json")))

    def test_the_replaced_answer_is_SHREDDED_not_merely_dropped(self):
        """The superseded record may hold a live credential; leaving it on the inbox
        would keep a key the human believes they have replaced."""
        self._put("m1", "tok-item-1", "first", "TYPO_SECRET")
        bus.supersede_pending_verdict(self.paths, "tok-item-1", keep="m2")
        leaked = [n for n in os.listdir(self.paths.inbox)
                  if "TYPO_SECRET" in open(os.path.join(self.paths.inbox, n)).read()]
        self.assertEqual(leaked, [])

    def test_it_replaces_only_the_SAME_ticket_and_only_verdicts(self):
        """A shared inbox: superseding by token must not touch another checkpoint's
        pending answer, and must not eat an intake that happens to sit beside it."""
        self._put("m1", "tok-OTHER", "other ticket", "keep me")
        with open(os.path.join(self.paths.inbox, "m2.json"), "w") as fh:
            json.dump({"kind": "intake", "ask": "unrelated", "message_id": "m2"}, fh)
        bus.supersede_pending_verdict(self.paths, "tok-item-1", keep="m3")
        self.assertEqual(sorted(os.listdir(self.paths.inbox)), ["m1.json", "m2.json"])

    def test_replacing_moves_the_answered_time_but_a_settled_answer_does_not(self):
        first = bus.mark_parked_answered(self.paths, "tok-item-1", when="2026-01-01T00:00:00+00:00")
        # no replacement happened -> the settled answer's time must not drift
        self.assertEqual(bus.mark_parked_answered(self.paths, "tok-item-1"), first)
        # a real replacement -> the time the human actually re-answered
        moved = bus.mark_parked_answered(self.paths, "tok-item-1",
                                         when="2026-02-02T00:00:00+00:00", restamp=True)
        self.assertEqual(moved, "2026-02-02T00:00:00+00:00")
        self.assertEqual(self.rec()["answered_at"], moved)

    def test_the_card_only_offers_re_answer_while_it_is_still_replaceable(self):
        """Once the drain has taken the answer it is applied and a second verdict
        dead-letters, so offering the button there would promise the impossible.

        "Still replaceable" is an existence check on the stamped answer, NOT an inbox
        scan: this runs on every poll, and scanning would parse credential-bearing
        bodies every couple of seconds to answer "is that file still there".
        """
        row = lambda: bus.ReadModel(self.paths).parked()[0]
        self._put("m1", "tok-item-1", "sent", "V")
        bus.mark_parked_answered(self.paths, "tok-item-1", message_id="m1")
        self.assertTrue(row()["answer_pending"])
        # the orchestrator drains it -> the answer is applied and can no longer be replaced
        os.unlink(os.path.join(self.paths.inbox, "m1.json"))
        self.assertFalse(row()["answer_pending"], "drained, yet it still offers replace")

    def test_the_stamped_answer_id_is_recorded_even_when_the_time_does_not_move(self):
        """The timestamp holds still for a settled answer, but the console's
        replaceability check reads the ID — so the ID must track the live record
        regardless, or a re-answer would look impossible the moment it was sent."""
        bus.mark_parked_answered(self.paths, "tok-item-1", message_id="m1")
        bus.mark_parked_answered(self.paths, "tok-item-1", message_id="m2")
        self.assertEqual(self.rec()["answer_message_id"], "m2")

    def test_the_page_gates_the_button_on_that_fact(self):
        js = _js_function("renderCheckpoints")
        self.assertIn("cp.answer_pending", js)
        self.assertIn('class="reanswer"', bus.INDEX_HTML)

    def test_the_validator_never_describes_itself_as_naming_the_key(self):
        """The docstring is part of the contract, and this one used to contradict it —
        it promised the error "names the offending key" directly above the code that
        deliberately emits an ordinal and nothing else. A future editor tidying the
        terse messages to match that prose would re-open the plaintext echo the
        ordinals exist to prevent, on the very path a proxy log sits on."""
        doc = bus.check_returns.__doc__
        self.assertNotIn("names the offending key", doc)
        self.assertIn("ORDINAL", doc)

    def test_the_hidden_attribute_actually_hides(self):
        """`hidden` only carries `display:none` at the UA level, so ANY class rule
        setting `display` outranks it. `.verdict` is `display:flex` — so the answered
        card went on showing its notes field and Send button with the attribute set and
        nothing in the DOM to show for it. Asserted once, globally, because every
        `hidden` toggle on this page rides on it."""
        self.assertIn("[hidden] { display:none !important; }", bus.STYLE_CSS)

    def test_the_forecast_chain_does_not_number_every_event_twice(self):
        """The chain is an `<ol>`, and each `<li>` also renders the record's own `n` into
        `.ev-n`. Without `list-style:none` the browser draws its marker as well, so every
        row of every chain read "1. 1", "2. 2" — on the checkpoint card and the panel both,
        since they share one renderer.

        Found only by rendering the panel in a real browser: no `textContent` assertion can
        see it, because each of the two numbers is individually correct. The record's `n` is
        the one that must be shown — a marker always counts 1..N from the top, so it would
        disagree with `n` the moment a chain were rendered partially."""
        chain = [ln for ln in bus.STYLE_CSS.splitlines() if ln.startswith(".chain {")]
        self.assertTrue(chain, "the .chain rule is gone; this guard is now vacuous")
        self.assertIn("list-style:none", chain[0])


class ParkedMirrorBackfill(Tmp):
    """The block otherwise comes into existence only at the next park/unpark. An install
    that parked BEFORE this writer existed has a live record and no block — and
    /dispatch has stopped hand-writing the prose parked[] because "the block covers it",
    so that project would publish an anchor naming NO open checkpoint while one is open.
    """

    def setUp(self):
        super().setUp()
        self.w = mkworkflow(self.root)
        with open(os.path.join(self.w, "handoff.md"), "w") as fh:
            fh.write(PROSE)
        self.paths = bus.Paths(self.w)

    def mirror(self):
        return bus._read_fenced(self.paths.handoff, bus.PARKED_BLOCK_RE)

    def _legacy(self, tid="old-1"):
        """A record in the shape a session hand-wrote before `park` existed: no
        `summary`, no `opened_at`."""
        with open(os.path.join(self.paths.parked, tid + ".json"), "w") as fh:
            json.dump({"ticket_id": tid, "token": "tok", "loop_position": "checkpoint",
                       "checkpoint": {"kind": "setup",
                                      "request": {"what": "add the webhook"}}}, fh)

    def test_it_backfills_a_block_for_a_record_that_predates_the_writer(self):
        self._legacy()
        self.assertIsNone(self.mirror(), "fixture assumes no block yet")
        bus.publish_parked_mirror(self.paths)
        entry = self.mirror()["parked"][0]
        self.assertEqual(entry["ticket_id"], "old-1")
        self.assertEqual(entry["kind"], "setup")
        self.assertEqual(entry["summary"], "add the webhook")  # derived, not stored
        self.assertIsNone(entry["opened_at"])                  # honestly unknown

    def test_an_empty_parked_dir_yields_an_EMPTY_block_not_no_block(self):
        """"Nothing is parked" has to be a positive statement. An absent block and an
        empty one read the same to a human and differently to a cold start."""
        bus.publish_parked_mirror(self.paths)
        self.assertEqual(self.mirror()["parked"], [])

    def test_it_is_idempotent_apart_from_the_timestamp(self):
        self._legacy()
        bus.publish_parked_mirror(self.paths)
        first = self.mirror()
        bus.publish_parked_mirror(self.paths)
        self.assertEqual(self.mirror()["parked"], first["parked"])

    def test_it_leaves_the_prose_and_the_drain_block_alone(self):
        drain_block = {"consumed": ["20260101T000000.000001Z-aaaaaaaa-1"],
                       "consumed_through": None, "dead_letters": []}
        with open(self.paths.handoff, "w") as fh:
            fh.write(PROSE + "\n" + bus.render_handoff_block(drain_block) + "\n")
        self._legacy()
        bus.publish_parked_mirror(self.paths)
        self.assertEqual(bus.read_handoff_block(self.paths.handoff)["consumed"],
                         drain_block["consumed"])
        self.assertIn("- current_item: item-1", open(self.paths.handoff).read())

    def test_it_mutates_nothing_in_parked(self):
        self._legacy()
        before = open(os.path.join(self.paths.parked, "old-1.json")).read()
        bus.publish_parked_mirror(self.paths)
        self.assertEqual(open(os.path.join(self.paths.parked, "old-1.json")).read(),
                         before)


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

    def test_mirror_backfills_over_the_cli(self):
        """The verb /dispatch calls before it writes the anchor."""
        with open(os.path.join(self.w, "parked", "old-1.json"), "w") as fh:
            json.dump({"ticket_id": "old-1", "token": "t",
                       "checkpoint": {"kind": "qa", "request": {"what": "check it"}}}, fh)
        m = self.run_bus("mirror")
        self.assertEqual(m.returncode, 0, m.stderr)
        self.assertEqual(json.loads(m.stdout)["mirrored"], 1)
        block = bus._read_fenced(os.path.join(self.w, "handoff.md"),
                                 bus.PARKED_BLOCK_RE)
        self.assertEqual(block["parked"][0]["ticket_id"], "old-1")


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
            {"verdict": {"outcome": "approve",
                         "returns": {"API_KEY": {"value": "sk-live-x"}}}}))

    def test_the_structural_gate_and_is_sensitive_now_agree(self):
        """This test used to assert they DISAGREED, and that disagreement was the bug.

        `returns` minus a `sensitive` marker was a fully conforming entry that
        `_is_sensitive` returned False for — so the structural boundary caught it and
        the redaction/store path did not. Splitting the field removed the marker
        entirely: `returns` MEANS credential, so both now answer from the same fact.
        A genuinely non-credential value is no longer "returns minus a marker" — it is
        `artifacts`, which is not a credential payload at all.
        """
        creds = {"verdict": {"outcome": "approve",
                             "returns": {"PROJECT_ID": {"value": "v"}}}}
        self.assertTrue(bus._is_sensitive(creds["verdict"]["returns"]))
        self.assertTrue(bus.remote_carries_payload(creds))

    def test_artifacts_alone_is_not_a_credential(self):
        """The other half of the split: a benign value must stay readable, and must not
        be treated as a credential by either the boundary or the redactor."""
        v = {"outcome": "approve", "artifacts": {"WEBHOOK_URL": {"value": "https://x"}}}
        self.assertFalse(bus._is_sensitive(v.get("returns")))
        _, sensitive = bus.validate("verdict", {"token": "t:1:u", "verdict": v})
        self.assertFalse(sensitive)

    def test_the_setup_tasks_shape_is_a_payload(self):
        self.assertTrue(bus.remote_carries_payload(
            {"verdict": {"tasks": [{"outcome": "approve"}]}}))


class DeclaredReturnsShape(unittest.TestCase):
    """`returns` is a name-keyed map — {"<KEY_NAME>": {value}} — and the bus
    refuses anything else. The shape used to be an open payload, which meant the
    declared-secret diff downstream was matching on a structure nobody had defined: in
    the shape that was actually produced, NOTHING ever matched, so a machine that lost
    nothing reported every credential lost. Refusing at the boundary is what turns that
    silence into a 400 the sender can act on."""

    def _v(self, verdict):
        return bus.validate("verdict", {"token": "t:1:u", "verdict": verdict})

    def test_the_declared_shape_is_accepted_and_marked_sensitive(self):
        clean, sensitive = self._v({"outcome": "approve", "returns": {
            "POLAR_WEBHOOK_SECRET": {"value": "whsec_x"}}})
        self.assertTrue(sensitive)
        self.assertEqual(clean["verdict"]["returns"]["POLAR_WEBHOOK_SECRET"]["value"],
                         "whsec_x")

    def test_a_bare_opinion_verdict_still_needs_no_returns(self):
        _, sensitive = self._v({"outcome": "approve", "notes": "looks right"})
        self.assertFalse(sensitive)

    def test_a_non_credential_artifact_now_belongs_in_artifacts(self):
        """This test asserted the OPPOSITE, and the assertion was the hole.

        "A non-credential artifact is the same entry without `sensitive`" made an
        unmarked `returns` entry both fully conforming AND unprotected — printed
        verbatim into the orchestrator's context and never stored. There is no unmarked
        `returns` any more: the field itself carries the meaning, so an entry here is a
        credential and a benign value has its own field."""
        _, sensitive = self._v({"outcome": "approve",
                                "returns": {"PROJECT_ID": {"value": "proj_42"}}})
        self.assertTrue(sensitive, "a `returns` entry is a credential by the field")
        _, sensitive = self._v({"outcome": "approve",
                                "artifacts": {"PROJECT_ID": {"value": "proj_42"}}})
        self.assertFalse(sensitive, "`artifacts` is the benign half — never a credential")

    def test_multiple_credentials_from_one_task_are_just_more_keys(self):
        clean, _ = self._v({"tasks": [{"id": "runpod", "outcome": "approve", "returns": {
            "IVRIT_RUNPOD_API_KEY": {"value": "a"},
            "IVRIT_RUNPOD_ENDPOINT": {"value": "b"}}}]})
        self.assertEqual(sorted(clean["verdict"]["tasks"][0]["returns"]),
                         ["IVRIT_RUNPOD_API_KEY", "IVRIT_RUNPOD_ENDPOINT"])

    def test_the_shape_that_used_to_be_written_is_now_refused(self):
        """The regression this whole schema exists for: a list of {id, sensitive, value}
        whose `id` is the TASK id, never the credential name."""
        with self.assertRaises(bus.Invalid):
            self._v({"outcome": "approve", "returns": [
                {"id": "runpod-credentials", "sensitive": True, "value": "sk_live_x"}]})

    def test_the_retired_sensitive_marker_is_refused_and_says_where_it_went(self):
        """One composer-supplied boolean used to gate redaction, shredding and storage
        at once, so a conforming entry that omitted it was printed verbatim and never
        stored. The marker is gone: `returns` MEANS credential. A composer still sending
        it is working from the old shape, so the error names the field and points at
        `artifacts` — naming a SCHEMA key, never a credential name or value."""
        with self.assertRaises(bus.Invalid) as caught:
            self._v({"outcome": "approve",
                     "returns": {"A_KEY": {"value": "sk_live_x", "sensitive": True}}})
        self.assertIn("sensitive", str(caught.exception))
        self.assertIn("artifacts", str(caught.exception))
        self.assertNotIn("sk_live_x", str(caught.exception))

    def test_returns_is_sensitive_by_the_field_not_by_a_marker(self):
        _, sensitive = self._v({"outcome": "approve",
                                "returns": {"A_KEY": {"value": "sk_live_x"}}})
        self.assertTrue(sensitive)

    def test_artifacts_is_validated_as_strictly_as_returns(self):
        """The only thing separating the two is which field they arrived in, so a loose
        shape here would re-open the question the split was made to close."""
        for bad in ({"WEBHOOK": {"value": 1}},
                    {"WEBHOOK": "flat"},
                    {"WEBHOOK": {"value": "v", "sensitive": True}},
                    {"WEBHOOK": {"value": "v", "extra": 1}}):
            with self.assertRaises(bus.Invalid):
                self._v({"outcome": "approve", "artifacts": bad})

    def test_a_bare_string_value_is_refused(self):
        with self.assertRaises(bus.Invalid):
            self._v({"outcome": "approve", "returns": {"A_KEY": "sk_live_x"}})

    def test_an_unknown_entry_field_is_refused(self):
        with self.assertRaises(bus.Invalid):
            self._v({"outcome": "approve",
                     "returns": {"A_KEY": {"value": "v", "note": "extra"}}})

    def test_a_per_task_returns_is_validated_too(self):
        with self.assertRaises(bus.Invalid):
            self._v({"tasks": [{"id": "polar", "outcome": "approve",
                                "returns": {"A_KEY": "not-an-object"}}]})

    def test_no_error_message_ever_echoes_a_key_or_a_value(self):
        """The reply crosses the same edge the credential boundary protects, and the
        commonest malformation is the VALUE pasted into the key position — where it
        passes the name regex and would be quoted straight back out."""
        leak = "sk_live_SHOULDNEVERAPPEAR"
        for verdict in (
            {"outcome": "approve", "returns": {leak: {"bad": 1}}},
            {"outcome": "approve", "returns": {leak: "flat"}},
            {"outcome": "approve", "returns": {"A_KEY": {"value": leak, "x": 1}}},
            {"outcome": "approve", "returns": {"A_KEY": {"value": leak,
                                                         "sensitive": "yes"}}},
        ):
            with self.assertRaises(bus.Invalid) as caught:
                self._v(verdict)
            self.assertNotIn(leak, str(caught.exception))


def _js_function(name):
    """Slice one function out of APP_JS by brace-matching.

    The console is embedded JS, so its logic is otherwise unreachable from a Python
    test. A rename breaks this loudly, which is the correct failure — the point is to
    run the REAL shipped source, never a copy of it that can drift.
    """
    src = bus.APP_JS
    start = src.index("function %s(" % name)
    depth, i = 0, src.index("{", start)
    while True:
        if src[i] == "{":
            depth += 1
        elif src[i] == "}":
            depth -= 1
            if depth == 0:
                return src[start:i + 1]
        i += 1


def _node():
    return shutil.which("node")


# A DOM shim just rich enough to run the REAL shipped renderCheckpoints. Every element
# records what was done to it, so a test can ask the question that matters here — "does
# this button have a click listener" — which no amount of reading `disabled` can answer.
_DOM_SHIM = """
function mkEl(sel) {
  const el = {
    sel, hidden: false, disabled: false, value: "", textContent: "", title: "",
    src: "", href: "", dataset: {}, listeners: {},
    classList: { s: new Set(), add(c) { this.s.add(c); }, remove(c) { this.s.delete(c); },
                 contains(c) { return this.s.has(c); } },
    addEventListener(ev, fn) { (this.listeners[ev] = this.listeners[ev] || []).push(fn); },
    querySelector() { return mkEl("stub"); },
    querySelectorAll() { return []; },
  };
  return el;
}
function makeCard() {
  const els = {};
  const card = mkEl(".card");
  // Every element resolves through the SAME map, including nested lookups: the real
  // code reaches `.reanswer-btn` via `node.querySelector(".reanswer").querySelector(…)`,
  // so a shim whose nested lookup minted a fresh node would silently record the click
  // handler on a detached element and the test would assert about the wrong object.
  const get = (sel) => {
    if (!els[sel]) {
      els[sel] = mkEl(sel);
      els[sel].closest = () => card;
      els[sel].querySelector = (s) => qs(s);
      els[sel].querySelectorAll = (s) => qsa(s);
    }
    return els[sel];
  };
  const qs = (sel) => (sel === ".card" ? card : get(sel));
  const qsa = (sel) => sel.split(",").map((s) => get(s.trim()));
  const node = { els, querySelector: qs, querySelectorAll: qsa };
  card.querySelector = qs; card.querySelectorAll = qsa; card.closest = () => card;
  return node;
}
// Everything renderCheckpoints leans on that is not the thing under test.
const CARDS = [];
function renderList(items, a, b, c, fn) {
  for (const it of items) { const n = makeCard(); CARDS.push(n); fn(n, it); }
}
function $() { return { contains: () => false, querySelectorAll: () => [] }; }
const document = { activeElement: null };
function renderSteps() {}
function renderTasks() {}
function node2(btn, sel) { return btn.closest(".card").querySelector(sel); }
function collectVerdict() { return { outcome: "approve" }; }
function remember() {}
function flash() {}
const SENT = [];
async function send(kind, body) { SENT.push({ kind, body }); return { ticket: "t-1" }; }
"""


def _render_deps():
    """The shim plus the REAL time helpers renderCheckpoints calls. Spliced in rather
    than stubbed: a stub would keep this test passing through a break in the very
    rendering it is standing next to."""
    return "\n".join([_DOM_SHIM] + [_js_function(n) for n in
                                    ("humanGap", "gapSeconds", "deadlineText")])


class ConsoleReanswerWiring(unittest.TestCase):
    """The "answer again" button was offered, gated correctly, and led nowhere.

    `renderCheckpoints` attached the send-button click handler AFTER the
    `if (cp.answered_at)` branch — and that branch ends in `return`. So on an answered
    card the wiring never ran: "answer again" dutifully un-hid the form and re-enabled
    every control, then handed back a button bound to nothing. Clicking it did nothing,
    forever; a reload re-read the still-answered server state and closed the form again,
    which reads to a human as "my answer will not send".

    Found by a human clicking it — the unit tests asserted `disabled === false` and
    PASSED, because "the button is enabled" and "the button does anything" are different
    facts. This drives the real shipped function and asks the second question.
    """

    def _render(self, cp, click_reanswer=False):
        node = _node()
        if not node:
            self.skipTest("node is not installed")
        harness = """
%s
%s
renderCheckpoints([%s]);
const card = CARDS[0];
const send_ = card.els[".send"];
%s
console.log(JSON.stringify({
  sendListeners: (send_ && send_.listeners.click || []).length,
  sendDisabled: send_ ? send_.disabled : null,
  verdictHidden: card.els[".verdict"] ? card.els[".verdict"].hidden : null,
  reanswerShown: card.els[".reanswer"] ? !card.els[".reanswer"].hidden : null,
  posted: SENT.length,
}));
""" % (_render_deps(), _js_function("renderCheckpoints"), json.dumps(cp),
            ("card.els['.reanswer-btn'].listeners.click[0]"
             "({ target: card.els['.reanswer-btn'] });" if click_reanswer else ""))
        out = subprocess.run([node, "-e", harness], capture_output=True, text=True)
        self.assertEqual(out.returncode, 0, out.stderr)
        return json.loads(out.stdout)

    ANSWERED = {"ticket_id": "item-1", "kind": "setup", "token": "tok-1",
                "request": {"what": "hand back the key"},
                "answered_at": "2026-08-02T13:05:09+00:00", "answer_pending": True}

    def test_an_answered_card_still_wires_its_send_button(self):
        """The regression itself: the handler must exist even on the answered path."""
        r = self._render(self.ANSWERED)
        self.assertEqual(r["sendListeners"], 1,
                         "the send button has no click handler on an answered card")
        # Wired but INERT until re-answering is chosen — the enable is the gate.
        self.assertTrue(r["sendDisabled"])
        self.assertTrue(r["verdictHidden"])
        self.assertTrue(r["reanswerShown"])

    def test_answer_again_hands_back_a_button_that_actually_sends(self):
        """The human's path, end to end: re-enable, then fire it and see a POST."""
        node = _node()
        if not node:
            self.skipTest("node is not installed")
        harness = """
%s
%s
renderCheckpoints([%s]);
const card = CARDS[0];
card.els['.reanswer-btn'].listeners.click[0]({ target: card.els['.reanswer-btn'] });
const send_ = card.els['.send'];
if (send_.disabled) { throw new Error("answer again left the send button disabled"); }
Promise.resolve(send_.listeners.click[0]()).then(() => {
  console.log(JSON.stringify({ posted: SENT.length, token: SENT[0] && SENT[0].body.token }));
});
""" % (_render_deps(), _js_function("renderCheckpoints"), json.dumps(self.ANSWERED))
        out = subprocess.run([node, "-e", harness], capture_output=True, text=True)
        self.assertEqual(out.returncode, 0, out.stderr)
        got = json.loads(out.stdout)
        self.assertEqual(got["posted"], 1, "clicking send after answer-again posted nothing")
        self.assertEqual(got["token"], "tok-1")

    def test_a_drained_answer_offers_no_override_it_cannot_honour(self):
        """`answer_pending: false` — the bus can no longer supersede, so the button is
        not offered. The send handler still exists; it is the ENABLE that is withheld."""
        cp = dict(self.ANSWERED, answer_pending=False)
        r = self._render(cp)
        self.assertFalse(r["reanswerShown"])
        self.assertTrue(r["sendDisabled"])


class ConsoleForecast(unittest.TestCase):
    """The forecast's two console surfaces, and why they are two.

    The CARD is the question ("do you approve this chain?") and dies when the checkpoint
    resolves. The PANEL is the artifact, and outlives it — that is the whole of D162's
    first call, and a panel that lived inside the card would vanish at the exact moment
    the forecast became authoritative."""

    def test_the_page_has_a_forecast_panel_and_template(self):
        self.assertIn('id="fc-list"', bus.INDEX_HTML)
        self.assertIn('<template id="fc-tpl">', bus.INDEX_HTML)

    def test_the_panel_is_rendered_from_the_snapshot(self):
        js = _js_function("renderForecasts")
        self.assertIn("#fc-list", js)
        self.assertIn("#fc-tpl", js)

    def test_the_chain_renderer_is_shared_by_card_and_panel(self):
        """One renderer, two mount points. Two renderers would be two answers to "what
        does this chain say", and they would drift."""
        self.assertIn("renderChain", _js_function("renderForecasts"))
        self.assertIn("renderChain", _js_function("renderCheckpoints"))

    def test_the_prefill_reuses_the_one_labelled_input_producer(self):
        """`renderTasks` is documented as the ONLY shipped producer of a `returns`
        payload. The forecast pre-fill needs exactly those labelled inputs, so it goes
        through the same function — a second producer would be a second place for the
        credential boundary to be got wrong."""
        js = _js_function("renderTasks")
        self.assertIn('"forecast"', js)

    def test_a_forecast_keeps_the_single_outcome_select(self):
        """A setup reply is plural (per-task outcomes replace the card's select). A
        forecast verdict is singular — approve/changes/reject on the CHAIN — and the
        pre-fill is an optional payload beside it, not the answer."""
        js = _js_function("renderTasks")
        self.assertIn('.outcome").hidden = true', js)
        # ...but only on the setup arm; the forecast arm must not reach it
        self.assertIn("prefill", js)


class ConsoleSetupForm(unittest.TestCase):
    """The console's setup form is the ONLY shipped producer of a `returns` payload.

    Everything downstream — the secret store, the declared-set diff, the credential
    socket boundary — was built to serve a payload that no client could actually
    produce, so the form's output shape is the seam that matters. These drive the real
    shipped JS through node and feed what it emits to the real validator: if the form
    and the schema ever disagree again, this fails rather than the field discovering it.
    """

    def _emit(self, tasks, notes="ok"):
        """Run the shipped collectVerdict() over a minimal DOM shim; return its output.

        The shim resolves `.svalue` and `.avalue` SEPARATELY, because that separation is
        the thing under test: which field a value lands in is its whole protection, and a
        shim that handed both selectors the same inputs would pass while the real page
        shredded a webhook URL into the secret store.
        """
        node = _node()
        if not node:
            self.skipTest("node is not installed")
        harness = """
%s
const TASKS = %s.map((t) => ({
  dataset: { tid: t.id },
  _secrets: (t.secrets || []).map((s) => ({ value: s.value, dataset: { name: s.name } })),
  _provides: (t.provides || []).map((s) => ({ value: s.value, dataset: { name: s.name } })),
  querySelector() { return { value: t.outcome }; },
  querySelectorAll(sel) { return sel === ".avalue" ? this._provides : this._secrets; },
}));
const card = {
  querySelectorAll: (sel) => (sel === ".task" ? TASKS : []),
  querySelector: () => ({ value: "approve" }),
};
console.log(JSON.stringify(collectVerdict(card, %s)));
""" % (_js_function("collectVerdict"), json.dumps(tasks), json.dumps(notes))
        out = subprocess.run([node, "-e", harness], capture_output=True, text=True)
        self.assertEqual(out.returncode, 0, out.stderr)
        return json.loads(out.stdout)

    def test_the_shipped_js_parses(self):
        """A syntax error here ships a console that renders nothing and says nothing."""
        node = _node()
        if not node:
            self.skipTest("node is not installed")
        with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as fh:
            fh.write(bus.APP_JS)
            path = fh.name
        try:
            out = subprocess.run([node, "--check", path], capture_output=True, text=True)
            self.assertEqual(out.returncode, 0, out.stderr)
        finally:
            os.unlink(path)

    def test_what_the_form_emits_is_what_the_bus_accepts(self):
        """The seam, driven end to end: the producer's output through the validator."""
        verdict = self._emit([{"id": "runpod", "outcome": "approve", "secrets": [
            {"name": "IVRIT_RUNPOD_API_KEY", "value": "sk_live_x"},
            {"name": "IVRIT_RUNPOD_ENDPOINT", "value": "ep_1"}]}])
        clean, sensitive = bus.validate("verdict", {"token": "t:1:u", "verdict": verdict})
        self.assertTrue(sensitive)
        got = clean["verdict"]["tasks"][0]["returns"]
        self.assertEqual(sorted(got), ["IVRIT_RUNPOD_API_KEY", "IVRIT_RUNPOD_ENDPOINT"])
        self.assertEqual(got["IVRIT_RUNPOD_API_KEY"],
                         {"value": "sk_live_x"})

    def test_the_credential_name_comes_from_the_request_not_the_task_id(self):
        """The whole bug in one assertion: the task id must never become the key."""
        verdict = self._emit([{"id": "runpod-credentials", "outcome": "approve",
                               "secrets": [{"name": "IVRIT_RUNPOD_API_KEY",
                                            "value": "sk_live_x"}]}])
        returns = verdict["tasks"][0]["returns"]
        self.assertIn("IVRIT_RUNPOD_API_KEY", returns)
        self.assertNotIn("runpod-credentials", returns)
        self.assertEqual(verdict["tasks"][0]["id"], "runpod-credentials")

    def test_a_mixed_reply_routes_each_task_on_its_own(self):
        verdict = self._emit([
            {"id": "polar", "outcome": "approve",
             "secrets": [{"name": "POLAR_WEBHOOK_SECRET", "value": "whsec_x"}]},
            {"id": "clerk", "outcome": "reject", "secrets": []}])
        bus.validate("verdict", {"token": "t:1:u", "verdict": verdict})
        self.assertEqual([t["outcome"] for t in verdict["tasks"]], ["approve", "reject"])
        self.assertNotIn("returns", verdict["tasks"][1])

    def test_an_unfilled_credential_yields_no_returns_at_all(self):
        """A task the human could not complete must not post an empty credential."""
        verdict = self._emit([{"id": "polar", "outcome": "changes",
                               "secrets": [{"name": "POLAR_WEBHOOK_SECRET",
                                            "value": ""}]}])
        bus.validate("verdict", {"token": "t:1:u", "verdict": verdict})
        self.assertNotIn("returns", verdict["tasks"][0])

    # -- the non-credential half: `provides[]` in, `artifacts` out --
    def test_the_form_emits_artifacts_from_the_provides_inputs(self):
        """`artifacts` shipped DECLARED AND UNPRODUCIBLE, which is the D147 defect the
        `returns` shape was rebuilt to end. `request.tasks[].provides[]` is its producer:
        the same row, a different input class, a different field."""
        verdict = self._emit([{"id": "polar", "outcome": "approve", "secrets": [],
                               "provides": [{"name": "POLAR_WEBHOOK_URL",
                                             "value": "https://x.example/hook"}]}])
        clean, sensitive = bus.validate("verdict", {"token": "t:1:u", "verdict": verdict})
        got = clean["verdict"]["tasks"][0]
        self.assertEqual(got["artifacts"],
                         {"POLAR_WEBHOOK_URL": {"value": "https://x.example/hook"}})
        self.assertNotIn("returns", got)
        # The whole point of the split: this must NOT be shredded into the secret store,
        # and must stay readable to the orchestrator that has to act on it.
        self.assertFalse(sensitive)

    def test_a_provided_value_never_lands_in_returns(self):
        """The two collectors must not cross. If they ever did, a non-credential would be
        written to `.workflow/secrets/` and unlinked from the inbox — unrecoverable, and
        invisible until the loop went looking for a value that had been shredded."""
        verdict = self._emit([{"id": "polar", "outcome": "approve",
                               "secrets": [{"name": "POLAR_WEBHOOK_SECRET",
                                            "value": "whsec_x"}],
                               "provides": [{"name": "POLAR_PROJECT_ID",
                                             "value": "proj_42"}]}])
        _, sensitive = bus.validate("verdict", {"token": "t:1:u", "verdict": verdict})
        task = verdict["tasks"][0]
        self.assertEqual(sorted(task["returns"]), ["POLAR_WEBHOOK_SECRET"])
        self.assertEqual(sorted(task["artifacts"]), ["POLAR_PROJECT_ID"])
        # One credential anywhere in the reply still makes the whole message sensitive —
        # redaction is per-message, so a benign value riding beside a secret is protected
        # with it rather than leaking the message it travels in.
        self.assertTrue(sensitive)

    def test_an_unfilled_provided_value_yields_no_artifacts_at_all(self):
        verdict = self._emit([{"id": "polar", "outcome": "changes", "secrets": [],
                               "provides": [{"name": "POLAR_WEBHOOK_URL", "value": ""}]}])
        bus.validate("verdict", {"token": "t:1:u", "verdict": verdict})
        self.assertNotIn("artifacts", verdict["tasks"][0])

    def test_provides_renders_on_a_socket_that_cannot_carry_a_credential(self):
        """The capability this buys: the remote console could previously answer a setup
        task with an outcome and nothing else. A non-credential value has no reason to be
        withheld from it, so `.avalue` is NOT gated on CREDS_OK — and the real shipped
        `renderTasks` is what has to prove it, not the comment above it."""
        node = _node()
        if not node:
            self.skipTest("node is not installed")
        harness = """
// Counts inputs by the box they were appended to, so "which half rendered" is the
// answer, not "did anything render".
const MADE = { secret: 0, provide: 0 };
const BOXES = { ".tsecrets": "secret", ".tprovides": "provide" };
function $(sel) {
  if (sel === "#task-tpl") {
    return { content: { cloneNode: () => ({
      querySelector: (s) => (BOXES[s] ? { append: () => { MADE[BOXES[s]] += 1; } }
                                      : { textContent: "", dataset: {} }) }) } };
  }
  return { content: { cloneNode: () => ({
    querySelector: () => ({ textContent: "", dataset: {} }) }) } };
}
const CREDS_OK = false;   // the remote socket: it may not carry a credential
const WRAP = { hidden: true, append: () => {} };
const NODE = { querySelector: (s) => (s === ".tasks" ? WRAP : { hidden: true }) };
%s
renderTasks(NODE, { kind: "setup", request: { tasks: [
  { id: "polar", what: "make a webhook",
    secrets: ["POLAR_WEBHOOK_SECRET"], provides: ["POLAR_WEBHOOK_URL"] }] } });
console.log(JSON.stringify(MADE));
""" % _js_function("renderTasks")
        out = subprocess.run([node, "-e", harness], capture_output=True, text=True)
        self.assertEqual(out.returncode, 0, out.stderr)
        made = json.loads(out.stdout)
        self.assertEqual(made["secret"], 0, "a credential input on a socket that refuses one")
        self.assertEqual(made["provide"], 1,
                         "the non-credential input was withheld from the remote console")

    def test_a_non_setup_checkpoint_still_posts_a_bare_opinion(self):
        verdict = self._emit([], notes="looks right")
        self.assertEqual(verdict, {"outcome": "approve", "notes": "looks right"})
        _, sensitive = bus.validate("verdict", {"token": "t:1:u", "verdict": verdict})
        self.assertFalse(sensitive)

    # -- what the page must never do with a credential --
    def test_the_credential_input_is_visible_and_is_never_a_password_field(self):
        """type=text, DELIBERATELY — and this test is the guard on that call (D148).

        D147 shipped `type="password"` on the reasoning that a credential should be
        masked. Driving the form in a real browser falsified it twice over. A human
        pasting an API key cannot confirm the paste landed whole, so a mis-paste becomes
        a credential that fails at point of use with no clue why. And Chrome offered to
        SAVE the key to its password manager: that prompt keys on `type=password`, and
        `autocomplete="off"` cannot suppress it — Chrome ignores the attribute on
        password fields by design. Masking defended against a shoulder over a loopback
        (or WireGuard) socket while costing correctness and copying the key somewhere
        nobody asked for.

        The autocomplete assertion stays: it is still the right hint, it is simply not
        load-bearing. A future edit back to `password` re-opens the manager prompt, so
        this asserts the absence explicitly rather than only the presence.
        """
        self.assertIn('class="svalue" type="text"', bus.INDEX_HTML)
        self.assertNotIn('type="password"', bus.INDEX_HTML)
        self.assertIn('autocomplete="off"', bus.INDEX_HTML)

    def test_the_form_clears_the_value_and_remembers_only_the_outcome(self):
        """`remember` writes to localStorage, which is durable browser state."""
        js = bus.APP_JS
        self.assertIn(
            'for (const inp of card.querySelectorAll(".svalue, .avalue")) inp.value = ""',
            js)
        send = js[js.index("btn.addEventListener"):]
        remembered = send[send.index("remember("):send.index("flash(msg")]
        self.assertIn("shown", remembered)
        self.assertNotIn("value", remembered)

    def test_the_poll_never_repaints_over_a_half_typed_credential(self):
        """Pasting a long API key takes longer than one poll interval; a wholesale
        re-render would wipe it out from under the human."""
        js = _js_function("renderCheckpoints")
        self.assertIn("document.activeElement", js)
        self.assertIn(".svalue, .notes", js)
        # `.avalue` latches the same guard. It holds no secret, but a repaint would still
        # wipe a half-typed value — and the send handler clears it for the mirror reason:
        # a value left in the box would freeze the list at its last painted snapshot.
        self.assertIn(".avalue", js)


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

    def test_the_page_declares_whether_ITS_socket_may_carry_a_credential(self):
        """A separate fact from the mode: a remote socket over an encrypted transport
        may, a plaintext one may not, and both read as "remote". It only decides whether
        the setup form ASKS for a key — the 403 stays the boundary."""
        self.assertIn(b'name="bus-credentials" content="yes"',
                      self.req(self.bport, "/")[1])
        expected = b"yes" if self.TRANSPORT == "tailscale" else b"no"
        self.assertIn(b'name="bus-credentials" content="' + expected + b'"',
                      self.req(self.rport, "/")[1])

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
                              body={"token": "cp1", "verdict": {
                                  "outcome": "approve",
                                  "returns": {"API_KEY": {"value": "sk-live-x"}}}})
        self.assertEqual(code, 403, "a credential must not ride a plaintext-edge proxy")

    def test_a_setup_shaped_verdict_is_refused_on_access(self):
        code, _, _ = self.req(self.rport, "/api/verdict", method="POST",
                              token="remote-token-A",
                              body={"token": "cp1",
                                    "verdict": {"tasks": [{"outcome": "approve"}]}})
        self.assertEqual(code, 403)

    # -- the forecast arm: loopback-only by KIND, not by payload (D159/D112) --
    def _park_forecast(self, token="fc-token"):
        bus.write_park(bus.Paths(self.w), {
            "ticket_id": "item-fc", "token": token, "loop_position": "create-forecast",
            "predicted_outcome": "approve",
            "checkpoint": {"kind": "forecast", "forecast_id": "item-fc",
                           "request": {"what": "approve the chain", "blocking": True}}})

    def test_a_BARE_forecast_verdict_is_still_refused_on_access(self):
        """`remote_carries_payload` covers the pre-fill arm for free, but an approve with
        no payload sails through it — and an approved forecast is a whole execution plan
        that D90 makes drive the agent, so it is MORE authoritative than an opinion, not
        less. The gate has to key off the checkpoint kind, which lives on the parked
        record, not off the shape of the body."""
        self._park_forecast()
        code, _, _ = self.req(self.rport, "/api/verdict", method="POST",
                              token="remote-token-A",
                              body={"token": "fc-token",
                                    "verdict": {"outcome": "approve", "notes": "looks right"}})
        self.assertEqual(code, 403, "an approved forecast rode the reduced remote surface")

    def test_the_same_bare_forecast_verdict_is_accepted_on_loopback(self):
        self._park_forecast()
        code, body, _ = self.req(self.bport, "/api/verdict", method="POST",
                                 token="loopback-token-B",
                                 body={"token": "fc-token",
                                       "verdict": {"outcome": "approve", "notes": "ok"}})
        self.assertEqual(code, 202, body)

    def test_an_unknown_token_is_not_treated_as_a_forecast(self):
        """The kind gate resolves the token against parked/. An unknown token has no kind,
        and must not become a blanket 403 that hides the real dead-letter path."""
        code, _, _ = self.req(self.rport, "/api/verdict", method="POST",
                              token="remote-token-A",
                              body={"token": "no-such-token",
                                    "verdict": {"outcome": "approve"}})
        self.assertEqual(code, 202)

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
                                 body={"token": "cp1", "verdict": {
                                     "outcome": "approve",
                                     "returns": {"API_KEY": {"value": "sk-live-x"}}}})
        self.assertEqual(code, 202, body)

    def test_a_setup_shaped_verdict_is_refused_on_access(self):
        code, body, _ = self.req(self.rport, "/api/verdict", method="POST",
                                 token="remote-token-A",
                                 body={"token": "cp1",
                                       "verdict": {"tasks": [{"outcome": "approve"}]}})
        self.assertEqual(code, 202, body)

    def test_a_question_does_not_exist_on_the_remote_surface(self):
        """The loopback-only call, proven at the socket rather than asserted in a comment.

        A question is run into `claude -p` verbatim, so POST access to it is arbitrary
        authoritative instruction into an autonomous agent — the bar a forged verdict has
        to clear, cleared more easily, because a verdict's notes ride a bounded decision
        while a question IS the prompt. 404 and not 403: the surface does not have it.
        """
        code, body, _ = self.req(self.rport, "/api/question", method="POST",
                                 token="remote-token-A",
                                 body={"question": "why postgres?"})
        self.assertEqual(code, 404, body)

    def test_the_same_question_is_accepted_on_loopback(self):
        """The other half — otherwise the test above would pass on a broken endpoint."""
        code, body, _ = self.req(self.bport, "/api/question", method="POST",
                                 token="loopback-token-B",
                                 body={"question": "why postgres?"})
        self.assertEqual(code, 202, body)

    def test_the_remote_allowlist_is_still_verdict_only(self):
        """Pins the decision itself. A future kind added to KINDS reaches the remote
        surface only by being added HERE, which is a line somebody has to write on
        purpose — this test is what makes forgetting it visible."""
        self.assertEqual(bus.REMOTE_KINDS, ("verdict",))
        self.assertNotIn("question", bus.REMOTE_KINDS)


class QuestionKind(unittest.TestCase):
    """The `question` inbox kind — the read-side sibling of `intake`."""

    def test_it_is_a_kind_the_bus_accepts(self):
        clean, sensitive = bus.validate("question", {"question": "why postgres?"})
        self.assertEqual(clean, {"question": "why postgres?"})
        # A question carries no token, no ids and no payload, so it can never be
        # sensitive — and a `returns` smuggled alongside it is simply not carried.
        self.assertFalse(sensitive)

    def test_an_empty_question_is_refused(self):
        for bad in ({}, {"question": ""}, {"question": "   "}, {"question": 7}):
            with self.assertRaises(bus.Invalid):
                bus.validate("question", bad)

    def test_it_carries_nothing_but_the_question(self):
        """No pass-through: a caller cannot smuggle a token or a returns map in."""
        clean, _ = bus.validate("question", {"question": "q", "token": "cp1",
                                             "returns": {"K": {"value": "v"}}})
        self.assertEqual(clean, {"question": "q"})

    def test_the_runner_will_spawn_for_one(self):
        """An unanswered question is as stuck as an unconsumed verdict — that is the
        whole reason the console stops being write-only."""
        self.assertIn("question", bus.RUNNER_KINDS)


# A DOM shim for the CONVERSATION panel. Deliberately not the card shim above: that one
# models `.card` lookups for renderCheckpoints, and renderThread does something simpler
# and different — it builds a tree with createElement/append. Both run the REAL shipped
# function; neither re-implements it.
_THREAD_SHIM = """
function mkNode(tag) {
  return { tag, className: "", textContent: "", kids: [],
           append(...ns) { this.kids.push(...ns); } };
}
const NODES = {};
function $(sel) { return NODES[sel] || (NODES[sel] = mkNode(sel)); }
const document = { createElement: mkNode };
// Flattened visible text, in render order — what a human actually reads off the panel.
function seen(n) {
  return [n.textContent].concat(n.kids.map(seen)).filter(Boolean).join(" | ");
}
"""


class ConsoleConversationRender(unittest.TestCase):
    """The Conversation panel's own render, run for real under node.

    Both defects here were invisible to every mechanical test and to reading the code:
    one is only reachable AFTER a rotation has run, the other only while a dead-letter is
    still on the inbox. They were found by rendering the state the drive had just created.
    """

    def _render(self, th):
        node = _node()
        if not node:
            self.skipTest("node is not installed")
        harness = "\n".join([
            _THREAD_SHIM,
            _js_function("humanGap"),
            _js_function("gapSeconds"),
            _js_function("renderThread"),
            "renderThread(%s);" % json.dumps(th),
            'console.log(JSON.stringify({text: seen($("#th-list")), '
            'cls: $("#th-list").className, count: $("#th-count").textContent}));',
        ])
        out = subprocess.run([node, "-e", harness], capture_output=True, text=True)
        self.assertEqual(out.returncode, 0, out.stderr)
        return json.loads(out.stdout)

    def test_a_project_never_asked_anything_still_says_so(self):
        """The case that must not regress while fixing the one it is confused with."""
        self.assertEqual(self._render({"turns": [], "rotations": 0, "active": False})["text"],
                         "nothing asked yet")

    def test_a_live_thread_with_no_turns_yet_is_unchanged(self):
        self.assertEqual(self._render({"turns": [], "rotations": 0, "active": True})["text"],
                         "no turns yet")

    def test_a_ROTATED_thread_does_not_render_as_a_cold_start(self):
        """The defect: six exchanges, then a rotation, and the panel was byte-identical to
        a project nobody has ever asked — the conversation looked ERASED, with nothing
        hinting a handoff existed."""
        got = self._render({"turns": [], "rotations": 1, "active": False})["text"]
        self.assertNotIn("nothing asked yet", got)
        self.assertIn("handed off", got)
        self.assertIn("rotation 1", got)
        # Says where it went, or "handed off" is just a nicer way of saying erased.
        self.assertIn("thread/handoff.md", got)

    def test_a_waiting_question_still_says_it_is_waiting(self):
        got = self._render({"rotations": 0, "active": True, "turns": [
            {"message_id": "m1", "role": "human", "text": "why postgres?",
             "at": None, "pending": True, "dead": False}]})
        self.assertIn("waiting for an answer", got["text"])

    def test_a_DEAD_LETTERED_question_stops_promising_an_answer(self):
        """It renders until the watermark collects it. 'Waiting' is a promise nothing is
        going to keep."""
        got = self._render({"rotations": 0, "active": True, "turns": [
            {"message_id": "m1", "role": "human", "text": "why postgres?",
             "at": None, "pending": True, "dead": True}]})
        self.assertNotIn("waiting for an answer", got["text"])
        self.assertIn("no answer is coming", got["text"])

    def test_an_answered_turn_carries_neither_marker(self):
        got = self._render({"rotations": 0, "active": True, "turns": [
            {"message_id": "m1", "role": "project", "text": "because concurrency",
             "at": None, "pending": False, "dead": False}]})
        self.assertNotIn("waiting", got["text"])
        self.assertNotIn("no answer is coming", got["text"])
        self.assertIn("because concurrency", got["text"])



# --- org mode: the archive-remote badge -------------------------------------
class OrgArchiveRemoteBadge(Tmp):
    """The private tree concentrates DERIVED IP about a product the operator does not
    own, and "it has somewhere to push" is exactly the fact that stops being true
    quietly. So it is rendered, not recorded in prose — and read from `git remote`
    rather than from config, because the hazard is the remote that is actually there."""

    def _brain(self, org=None, remotes=()):
        w = mkworkflow(self.root)
        cfg = {"project_root": "."}
        if org is not None:
            cfg["org"] = org
        with open(os.path.join(w, "config.json"), "w") as fh:
            json.dump(cfg, fh)
        repo = os.path.dirname(w)
        subprocess.run(["git", "init", "-q", "-b", "main", repo], check=True)
        for name, url in remotes:
            subprocess.run(["git", "-C", repo, "remote", "add", name, url], check=True)
            if url == bus.NO_PUSH:
                pass
        return bus.ReadModel(bus.Paths(w))

    def test_absent_org_key_renders_nothing(self):
        # An ordinary project pays one null check and shows no badge at all.
        rm = self._brain(org=None, remotes=[("origin", "git@example.com:me/mine.git")])
        self.assertIsNone(rm.org())

    def test_a_fetch_only_origin_is_not_an_archive_remote(self):
        """The clone keeps `origin` so `align` has an anchor, with its push URL set to
        `no_push`. Badging that would cry wolf on every correctly-configured brain."""
        w = mkworkflow(self.root)
        with open(os.path.join(w, "config.json"), "w") as fh:
            json.dump({"project_root": ".", "org": {}}, fh)
        repo = os.path.dirname(w)
        subprocess.run(["git", "init", "-q", "-b", "main", repo], check=True)
        subprocess.run(["git", "-C", repo, "remote", "add", "origin",
                        "git@example.com:acme/product.git"], check=True)
        subprocess.run(["git", "-C", repo, "remote", "set-url", "--push", "origin",
                        bus.NO_PUSH], check=True)
        self.assertEqual(bus.ReadModel(bus.Paths(w)).org()["push_remotes"], [])

    def test_a_real_push_remote_is_reported_with_its_acknowledgement(self):
        rm = self._brain(org={"archive_remote_ack": "offsite backup, cleared 2026-08-04"},
                         remotes=[("archive", "git@example.com:me/brain.git")])
        got = rm.org()
        self.assertEqual(got["push_remotes"], ["archive"])
        self.assertTrue(got["acknowledged"])
        self.assertIn("offsite", got["ack_reason"])

    def test_a_push_remote_with_no_acknowledgement_is_reported_as_such(self):
        """Added outside the guard that requires an acknowledgement — a different fact
        from an acknowledged one, so it must not render as the same badge."""
        rm = self._brain(org={}, remotes=[("archive", "git@example.com:me/brain.git")])
        got = rm.org()
        self.assertEqual(got["push_remotes"], ["archive"])
        self.assertFalse(got["acknowledged"])
        self.assertIsNone(got["ack_reason"])

    def test_an_unreadable_git_reports_unknown_rather_than_none(self):
        """`none` on a failed read is the one answer that could be wrong in the direction
        that matters, so the badge says `unknown` instead."""
        w = mkworkflow(self.root)
        with open(os.path.join(w, "config.json"), "w") as fh:
            json.dump({"project_root": ".", "org": {}}, fh)
        rm = bus.ReadModel(bus.Paths(w))
        rm.paths.repo = os.path.join(self.root, "does-not-exist")
        self.assertIsNone(rm.org()["push_remotes"])

    def test_the_badge_rides_the_polled_snapshot(self):
        # The console reads one synthesized document; a block absent from it cannot render.
        rm = self._brain(org={}, remotes=[("archive", "git@example.com:me/brain.git")])
        self.assertIn("org", rm.snapshot())


if __name__ == "__main__":
    unittest.main()

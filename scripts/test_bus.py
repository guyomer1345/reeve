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
        w = mkworkflow(self.root)
        with open(os.path.join(w, "runtime.json"), "w") as fh:
            json.dump({"runtime_root": "~"}, fh)
        self.assertEqual(bus.Paths(w).runtime, os.path.expanduser("~"))

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
        orchestrator is dead — the state this daemon exists to cover."""
        names = [j.name for j in self.d.jobs]
        self.assertEqual(sorted(names), ["parked", "serve"])


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


if __name__ == "__main__":
    unittest.main()

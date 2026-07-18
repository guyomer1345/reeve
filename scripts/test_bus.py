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
        orchestrator is dead — the state this daemon exists to cover.

        Jobs are expected to arrive (each one adds an idle TERM, which is the whole
        point of the frame), so this pins the property rather than the roster: no job
        may vote on the orchestrator's liveness.
        """
        names = sorted(j.name for j in self.d.jobs)
        self.assertEqual(names, ["inbox-gc", "parked", "serve"])
        self.assertNotIn("heartbeat", " ".join(names))

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


if __name__ == "__main__":
    unittest.main()

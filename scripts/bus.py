#!/usr/bin/env python3
"""The console daemon — a detached, session-independent local HTTP bus.

It serves the supervision cockpit and is the channel a human uses to reach the
loop while the orchestrator is busy, parked, or dead. Its lifetime is deliberately
decoupled from any Claude session: it is spawned into a NEW SESSION (setsid), so
it survives /clear, --resume, and session death.

Stdlib only. python3 is the one hard dependency; there is no install or build step.

  ensure   adopt-or-spawn, idempotent — the bootstrap calls this
  serve    run the daemon in the foreground (what `ensure` spawns)
  stop     authenticated shutdown of a running daemon
  status   report what's running, for a human

THE JOBS FRAME
--------------
The daemon is not a file server with features bolted on. It owns a set of JOBS,
and each job answers two questions: what to do on a tick, and whether it is idle.
The daemon self-shuts only when EVERY job votes idle. Jobs land over time (serving
the console, alerting an away human, relaunching the loop) and each one adds its
own idle term rather than rewriting the janitor.

"Idle" deliberately does NOT mean "the orchestrator is quiet". Keying the janitor
on an orchestrator heartbeat would starve it exactly when the orchestrator is dead
— which is the state this daemon exists to cover. Idle means every job this daemon
owns has nothing outstanding.

MEASURED BUILD CONTRACT (these are not style preferences)
--------------------------------------------------------
1. NEVER hold the lock on a file that is atomically republished. A rename swaps the
   inode out from under a held flock: the next process opens the NEW inode, sees no
   contention, and wins. Two daemons, silently. Measured true on ext4 AND on the
   WSL 9p mount. Hence a separate lock file, created and never replaced.
2. A requested file mode is not an achieved file mode. On the WSL /mnt/c mount, a
   file created with mode 0600 comes back 0777 — it fails OPEN and silently. So the
   token's mode is VERIFIED after creation, never assumed.
3. Shutdown calls server.shutdown() from a one-shot thread, never inline on the
   serving thread (documented deadlock).
4. The request body is not size-capped by default: read at most Content-Length and
   refuse oversize, and set a socket timeout so a slow client cannot pin a worker.
5. protocol_version stays HTTP/1.0 — connection-per-request is trivially correct at
   this concurrency and removes a class of keep-alive hangs.

TRUST
-----
The untrusted caller is the browser and the network, not same-UID code (a same-UID
process can already read these files; defending against it is theater). So, on every
sensitive endpoint: a capability token in a header (never a query param, never a
cookie), a strict Host allowlist (the DNS-rebinding defense), JSON + a custom header
on writes (forcing a preflight a form-CSRF cannot satisfy), and a loopback bind.

The console page itself is served WITHOUT a token, because a browser cannot attach a
header to a document navigation. It carries the token to its own scripts in a meta
tag. This is a real and deliberate concession: whoever can GET the page from an
allowlisted Host obtains the token. That audience is a local browser, which is the
token's intended audience anyway — the Host check, not the token, is what stops a
rebound page from reaching this far.
"""
import argparse
import errno
import fcntl
import hashlib
import html
import json
import os
import secrets
import shutil
import socket
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

# --- tunables ---------------------------------------------------------------
MAX_BODY = 64 * 1024          # generous for a verdict; refuse anything larger
SOCKET_TIMEOUT = 10           # seconds a worker will wait on a slow client
DEFAULT_IDLE_TIMEOUT = 72 * 3600
GIT_CACHE_TTL = 10            # seconds; the poll runs every few seconds
RECENT_COMMITS = 10
TOKEN_HEADER = "X-Bus-Token"  # a custom header: forces the CSRF-defeating preflight
HEALTH_TIMEOUT = 3


# --- path resolution --------------------------------------------------------
# The workflow tree spans two filesystems whenever the repo lives on a mount whose
# rename/mode guarantees are weak (the WSL /mnt/c case). The atomicity- and
# mode-sensitive runtime paths are relocated to a native filesystem; the committed
# artifacts stay in the repo by construction. A gitignored pointer records where
# the runtime half went — without it, nothing could FIND the relocated tree, since
# the daemon's own discovery record lives inside it.
#
# Absent pointer => no relocation happened => the workflow dir IS the runtime root.
# That is the common (non-WSL) case and costs zero indirection.
class Paths:
    def __init__(self, workflow_dir):
        self.workflow = os.path.abspath(workflow_dir)
        self.runtime = self._resolve_runtime_root()
        # runtime half (relocated when pinned)
        self.lock = os.path.join(self.runtime, "bus.lock")
        self.record = os.path.join(self.runtime, "bus.json")
        self.state = os.path.join(self.runtime, "state.json")
        self.parked = os.path.join(self.runtime, "parked")
        self.inbox = os.path.join(self.runtime, "inbox")
        self.outbox = os.path.join(self.runtime, "outbox")
        # committed half (always on the repo mount, never relocated)
        self.handoff = os.path.join(self.workflow, "handoff.md")
        self.backlog = os.path.join(self.workflow, "backlog.md")
        self.config = os.path.join(self.workflow, "config.json")
        self.repo = os.path.dirname(self.workflow)

    def _resolve_runtime_root(self):
        pointer = os.path.join(self.workflow, "runtime.json")
        try:
            with open(pointer) as fh:
                root = json.load(fh).get("runtime_root")
        except FileNotFoundError:
            return self.workflow
        except (OSError, ValueError) as exc:
            raise SystemExit("runtime pointer %s is unreadable: %s" % (pointer, exc))
        if not root:
            return self.workflow
        root = os.path.abspath(os.path.expanduser(root))
        if not os.path.isdir(root):
            # Fail loudly. Silently falling back to the repo mount would put the
            # token and the inbox on the very filesystem the relocation avoided.
            raise SystemExit("runtime_root %s does not exist (pointer: %s)" % (root, pointer))
        return root

    def load_config(self):
        try:
            with open(self.config) as fh:
                return json.load(fh)
        except (OSError, ValueError):
            return {}


# --- small file helpers -----------------------------------------------------
def atomic_write(path, data, mode=0o600):
    """Publish a file so a reader never catches it torn."""
    d = os.path.dirname(path)
    os.makedirs(d, exist_ok=True)
    tmp = os.path.join(d, ".%s.%s.tmp" % (os.path.basename(path), os.getpid()))
    fd = os.open(tmp, os.O_CREAT | os.O_WRONLY | os.O_EXCL, mode)
    try:
        with os.fdopen(fd, "w") as fh:
            fh.write(data)
            fh.flush()
            os.fsync(fh.fileno())
        os.rename(tmp, path)
        dfd = os.open(d, os.O_RDONLY)
        try:
            os.fsync(dfd)
        finally:
            os.close(dfd)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def verify_mode(path, want=0o600):
    """Return None if the achieved mode is at least as tight as `want`, else a warning.

    A mode argument is a request, not a guarantee: on the WSL /mnt/c mount every file
    comes back 0777 no matter what was asked for. That failure is silent and open, so
    the only honest check is to stat the result.
    """
    try:
        got = os.stat(path).st_mode & 0o777
    except OSError as exc:
        return "cannot stat %s: %s" % (path, exc)
    if got & ~want:
        return ("%s is mode %s, not %s — this filesystem does not honour it, so the "
                "capability token is readable by other users on this machine"
                % (path, oct(got), oct(want)))
    return None


def read_text(path, limit=256 * 1024):
    try:
        with open(path, "r", errors="replace") as fh:
            return fh.read(limit)
    except OSError:
        return None


def read_json(path):
    try:
        with open(path) as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# --- the jobs ---------------------------------------------------------------
class Job:
    name = "job"

    def tick(self, daemon):
        """Periodic work. Must never raise; the daemon outliving a job bug matters more."""

    def is_idle(self, daemon):
        return True

    def idle_reason(self, daemon):
        return None


class ServeJob(Job):
    """Serving the console. Idle when nobody has asked for anything in a long while."""
    name = "serve"

    def is_idle(self, daemon):
        return (time.time() - daemon.last_request) > daemon.idle_timeout

    def idle_reason(self, daemon):
        if not self.is_idle(daemon):
            age = int(time.time() - daemon.last_request)
            return "a request arrived %ss ago (timeout %ss)" % (age, daemon.idle_timeout)
        return None


class ParkedWatchJob(Job):
    """Watching for parked checkpoints.

    Today this job exists for its idle vote alone, and that vote is the point: an
    away human who has not opened the console yet must not have the away channel
    reaped out from under the verdict they are about to deliver. A daemon that
    self-shuts while a checkpoint is open defeats its own purpose in precisely the
    scenario it was built for.

    Alerting hangs off this same scan later; the scan is deliberately here now so
    the janitor is correct from the first line rather than retrofitted.
    """
    name = "parked"

    def open_checkpoints(self, daemon):
        out = []
        try:
            names = sorted(os.listdir(daemon.paths.parked))
        except OSError:
            return out
        for n in names:
            if not n.endswith(".json"):
                continue
            rec = read_json(os.path.join(daemon.paths.parked, n))
            if isinstance(rec, dict):
                out.append(rec)
        return out

    def is_idle(self, daemon):
        return not self.open_checkpoints(daemon)

    def idle_reason(self, daemon):
        n = len(self.open_checkpoints(daemon))
        return "%d parked checkpoint(s) still open" % n if n else None


# --- the read model ---------------------------------------------------------
class ReadModel:
    """Synthesizes the one snapshot document the console polls.

    The daemon is not a static file server for state: the page polls a single
    synthesized document, so what matters is which paths are READ, not which URLs
    exist. Recent activity is computed from git rather than read from a file.
    """

    def __init__(self, paths):
        self.paths = paths
        self._git_cache = (0.0, [])

    def git_recent(self):
        age, cached = self._git_cache
        if (time.time() - age) < GIT_CACHE_TTL:
            return cached
        out = []
        try:
            proc = subprocess.run(
                ["git", "-C", self.paths.repo, "log", "-n", str(RECENT_COMMITS),
                 "--format=%h%x1f%s%x1f%cr"],
                capture_output=True, text=True, timeout=5,
            )
            if proc.returncode == 0:
                for line in proc.stdout.strip().splitlines():
                    parts = line.split("\x1f")
                    if len(parts) == 3:
                        out.append({"sha": parts[0], "subject": parts[1], "when": parts[2]})
        except (OSError, subprocess.SubprocessError):
            pass  # a console without an activity feed still supervises
        self._git_cache = (time.time(), out)
        return out

    def parked(self):
        out = []
        try:
            names = sorted(os.listdir(self.paths.parked))
        except OSError:
            return out
        for n in names:
            if not n.endswith(".json"):
                continue
            rec = read_json(os.path.join(self.paths.parked, n))
            if not isinstance(rec, dict):
                continue
            cp = rec.get("checkpoint") or {}
            out.append({
                "ticket_id": rec.get("ticket_id"),
                "token": rec.get("token"),
                "kind": cp.get("kind"),
                "request": cp.get("request"),
                "deadline": rec.get("deadline"),
                "overdue": self._overdue(rec.get("deadline")),
            })
        return out

    @staticmethod
    def _overdue(deadline):
        if not deadline:
            return False
        try:
            dt = datetime.fromisoformat(str(deadline).replace("Z", "+00:00"))
        except ValueError:
            return False
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) > dt

    def outbox(self):
        out = []
        try:
            names = sorted(os.listdir(self.paths.outbox))
        except OSError:
            return out
        for n in names:
            if not n.endswith(".json"):
                continue
            rec = read_json(os.path.join(self.paths.outbox, n))
            if isinstance(rec, dict) and rec.get("status") == "pending":
                out.append({"id": rec.get("id"), "action": rec.get("action"),
                            "item_ref": rec.get("item_ref"), "created_at": rec.get("created_at")})
        return out

    def snapshot(self):
        state = read_json(self.paths.state) or {}
        backlog = read_text(self.paths.backlog)
        return {
            "generated_at": now_iso(),
            "state": {
                "status": state.get("status"),
                "node": state.get("node"),
                "current_item": state.get("current_item"),
                "wave": state.get("wave"),
                "note": state.get("note"),
            },
            "parked": self.parked(),
            "outbox_pending": self.outbox(),
            "backlog": backlog,
            "recent": self.git_recent(),
        }

    def snapshot_bytes(self):
        """Return (body, etag).

        The ETag is a hash of the synthesized body. There is no monotonic version on
        disk to gate against, and a content hash is honest about what actually
        changed — it cannot claim staleness the reader would not have seen anyway.
        At one user and a poll every few seconds, the 304 saves bandwidth, not work.
        """
        snap = self.snapshot()
        body = json.dumps(snap, indent=1, sort_keys=True).encode()
        # generated_at changes every call; hash everything else so an unchanged tree
        # keeps a stable ETag and the page stops re-rendering.
        stable = dict(snap)
        stable.pop("generated_at", None)
        etag = '"%s"' % hashlib.sha256(
            json.dumps(stable, sort_keys=True).encode()).hexdigest()[:32]
        return body, etag


# --- the page ---------------------------------------------------------------
# Embedded rather than shipped as loose assets: it keeps the daemon a single file to
# copy, and removes a whole class of "where did my assets go" resolution bugs. The
# page is served under a strict script-src 'self' policy, so app.js is its own
# response rather than an inline script.
INDEX_HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>loop console</title>
<!-- The page cannot be token-gated (a browser cannot set a header on a document
     navigation), so it hands the token to its own scripts here. Whoever can load
     this page from an allowlisted Host holds the token; that is a local browser. -->
<meta name="bus-token" content="__BUS_TOKEN__">
<link rel="stylesheet" href="/style.css">
</head>
<body>
<header>
  <h1>loop console</h1>
  <span id="conn" class="pill">connecting</span>
</header>

<section id="now">
  <h2>Now</h2>
  <dl id="state-dl"></dl>
</section>

<section id="checkpoints">
  <h2>Pending checkpoints <span id="cp-count" class="count"></span></h2>
  <div id="cp-list" class="empty">none open</div>
</section>

<section id="outward">
  <h2>Pending outward actions <span id="ob-count" class="count"></span></h2>
  <div id="ob-list" class="empty">none queued</div>
</section>

<section id="activity">
  <h2>Recent activity</h2>
  <ol id="log" class="empty"></ol>
</section>

<template id="cp-tpl">
  <article class="card">
    <div class="row"><strong class="kind"></strong><span class="ticket mono"></span></div>
    <p class="request"></p>
    <div class="row"><span class="deadline"></span></div>
  </article>
</template>

<template id="ob-tpl">
  <article class="card">
    <div class="row"><strong class="action"></strong><span class="oid mono"></span></div>
    <div class="row"><span class="item"></span></div>
  </article>
</template>

<script src="/app.js"></script>
</body>
</html>
"""

APP_JS = r"""// Vanilla, no build step, no eval: cloned <template> + textContent only.
// textContent (never innerHTML) is what keeps loop-authored strings — a commit
// subject, a checkpoint request — from being parsed as markup.
const TOKEN = document.querySelector('meta[name="bus-token"]').content;
let etag = null;
let timer = null;

const $ = (s) => document.querySelector(s);

function setConn(text, ok) {
  const el = $("#conn");
  el.textContent = text;
  el.className = "pill" + (ok ? " ok" : " bad");
}

function renderState(s) {
  const dl = $("#state-dl");
  dl.textContent = "";
  const rows = [["status", s.status], ["node", s.node],
                ["item", s.current_item], ["wave", s.wave], ["note", s.note]];
  for (const [k, v] of rows) {
    if (v === null || v === undefined || v === "") continue;
    const dt = document.createElement("dt");
    dt.textContent = k;
    const dd = document.createElement("dd");
    dd.textContent = String(v);
    dl.append(dt, dd);
  }
  if (!dl.children.length) dl.textContent = "no state published yet";
}

function renderList(items, listSel, countSel, tplSel, fill, emptyText) {
  const list = $(listSel);
  $(countSel).textContent = items.length ? String(items.length) : "";
  list.textContent = "";
  if (!items.length) {
    list.className = "empty";
    list.textContent = emptyText;
    return;
  }
  list.className = "";
  const tpl = $(tplSel);
  for (const it of items) {
    const node = tpl.content.cloneNode(true);
    fill(node, it);
    list.append(node);
  }
}

function renderCheckpoints(items) {
  renderList(items, "#cp-list", "#cp-count", "#cp-tpl", (node, cp) => {
    node.querySelector(".kind").textContent = cp.kind || "checkpoint";
    node.querySelector(".ticket").textContent = cp.ticket_id || "";
    node.querySelector(".request").textContent =
      typeof cp.request === "string" ? cp.request : JSON.stringify(cp.request ?? "");
    const d = node.querySelector(".deadline");
    d.textContent = cp.deadline ? (cp.overdue ? "OVERDUE — " : "due ") + cp.deadline : "";
    if (cp.overdue) d.classList.add("overdue");
  }, "none open");
}

function renderOutbox(items) {
  renderList(items, "#ob-list", "#ob-count", "#ob-tpl", (node, ob) => {
    node.querySelector(".action").textContent = ob.action || "action";
    node.querySelector(".oid").textContent = ob.id || "";
    node.querySelector(".item").textContent = ob.item_ref || "";
  }, "none queued");
}

function renderLog(items) {
  const log = $("#log");
  log.textContent = "";
  log.className = items.length ? "" : "empty";
  for (const c of items) {
    const li = document.createElement("li");
    const sha = document.createElement("span");
    sha.className = "mono sha";
    sha.textContent = c.sha;
    const subj = document.createElement("span");
    subj.textContent = c.subject;
    const when = document.createElement("time");
    when.textContent = c.when;
    li.append(sha, subj, when);
    log.append(li);
  }
}

async function poll() {
  try {
    const headers = { "X-Bus-Token": TOKEN };
    if (etag) headers["If-None-Match"] = etag;
    const res = await fetch("/api/state", { headers, cache: "no-store" });
    if (res.status === 304) { setConn("live", true); return; }
    if (res.status === 401 || res.status === 403) { setConn("not authorized", false); return; }
    if (!res.ok) { setConn("error " + res.status, false); return; }
    etag = res.headers.get("ETag");
    const snap = await res.json();
    renderState(snap.state || {});
    renderCheckpoints(snap.parked || []);
    renderOutbox(snap.outbox_pending || []);
    renderLog(snap.recent || []);
    setConn("live", true);
  } catch (e) {
    setConn("daemon unreachable", false);
  }
}

// A chained timeout, not setInterval: a slow response must never stack requests.
// Polling pauses when the tab is hidden and resumes with an immediate read.
async function loop() {
  if (!document.hidden) await poll();
  timer = setTimeout(loop, 2500);
}
document.addEventListener("visibilitychange", () => {
  if (!document.hidden) { clearTimeout(timer); loop(); }
});
loop();
"""

STYLE_CSS = """:root { color-scheme: light dark; --fg:#111; --dim:#666; --line:#ddd; --bad:#b00020; --ok:#0a7c2f; }
@media (prefers-color-scheme: dark) { :root { --fg:#e8e8e8; --dim:#999; --line:#333; --bad:#ff6b6b; --ok:#4ade80; } }
* { box-sizing: border-box; }
body { margin:0 auto; padding:1.5rem; max-width:52rem; color:var(--fg);
  font:15px/1.5 system-ui,-apple-system,Segoe UI,sans-serif; }
header { display:flex; align-items:center; gap:.75rem; border-bottom:1px solid var(--line); padding-bottom:.75rem; }
h1 { font-size:1.1rem; margin:0; letter-spacing:.02em; }
h2 { font-size:.8rem; text-transform:uppercase; letter-spacing:.08em; color:var(--dim); margin:2rem 0 .5rem; }
.pill { font-size:.75rem; padding:.15rem .5rem; border-radius:999px; border:1px solid var(--line); color:var(--dim); }
.pill.ok { color:var(--ok); border-color:var(--ok); }
.pill.bad { color:var(--bad); border-color:var(--bad); }
.count { color:var(--dim); font-weight:400; }
.empty { color:var(--dim); font-style:italic; }
dl { display:grid; grid-template-columns:auto 1fr; gap:.25rem 1rem; margin:0; }
dt { color:var(--dim); }
dd { margin:0; }
.card { border:1px solid var(--line); border-radius:6px; padding:.6rem .75rem; margin-bottom:.5rem; }
.row { display:flex; gap:.5rem; align-items:baseline; justify-content:space-between; }
.request { margin:.35rem 0; }
.mono, .sha { font-family:ui-monospace,SFMono-Regular,Menlo,monospace; font-size:.85em; color:var(--dim); }
.deadline { font-size:.8rem; color:var(--dim); }
.deadline.overdue { color:var(--bad); font-weight:600; }
ol#log { list-style:none; padding:0; margin:0; }
ol#log li { display:grid; grid-template-columns:5rem 1fr auto; gap:.75rem;
  padding:.3rem 0; border-bottom:1px solid var(--line); }
ol#log time { color:var(--dim); font-size:.8rem; white-space:nowrap; }
"""


# --- the daemon -------------------------------------------------------------
class Daemon:
    def __init__(self, paths, idle_timeout=DEFAULT_IDLE_TIMEOUT):
        self.paths = paths
        self.idle_timeout = idle_timeout
        self.token = None
        self.lock_fd = None
        self.server = None
        self.model = ReadModel(paths)
        self.jobs = [ServeJob(), ParkedWatchJob()]
        self.last_request = time.time()
        self.warnings = []
        self._stopping = threading.Event()

    # -- singleton election --
    def acquire_lock(self):
        """Hold a lock for the process lifetime; the kernel releases it on death.

        The lock lives on its own file, NEVER on bus.json. bus.json is republished by
        atomic rename, and a rename swaps the inode: a second daemon would open the
        new inode, find it unlocked, and start. Measured true on both ext4 and 9p.
        A lock file is therefore created-and-updated-in-place, never renamed over.
        """
        os.makedirs(os.path.dirname(self.paths.lock), exist_ok=True)
        fd = os.open(self.paths.lock, os.O_CREAT | os.O_RDWR, 0o600)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            os.close(fd)
            if exc.errno in (errno.EACCES, errno.EAGAIN):
                return False
            raise
        os.ftruncate(fd, 0)
        os.write(fd, str(os.getpid()).encode())
        self.lock_fd = fd
        return True

    # -- discovery record --
    def publish(self, port):
        rec = {"pid": os.getpid(), "port": port, "token": self.token,
               "started_at": now_iso()}
        atomic_write(self.paths.record, json.dumps(rec, indent=1) + "\n", mode=0o600)
        warn = verify_mode(self.paths.record, 0o600)
        if warn:
            self.warnings.append(warn)
            log("WARNING: " + warn)
        return rec

    # -- the janitor --
    def idle_check(self):
        blockers = [j.idle_reason(self) for j in self.jobs]
        blockers = [b for b in blockers if b]
        if blockers:
            return False, blockers
        return True, []

    @property
    def janitor_interval(self):
        # Cheap enough to run often (a dir scan), so tie it to the timeout rather
        # than a constant: a real 72h timeout checks every 30s, and a test with a
        # 2s timeout is actually exercisable rather than needing a 30s sleep.
        return min(30, max(0.25, self.idle_timeout / 4.0))

    def janitor(self):
        while not self._stopping.wait(self.janitor_interval):
            for job in self.jobs:
                try:
                    job.tick(self)
                except Exception as exc:  # a job bug must not take the daemon down
                    log("job %s tick failed: %r" % (job.name, exc))
            idle, _ = self.idle_check()
            if idle:
                log("idle for %ss with no open checkpoint — shutting down" % self.idle_timeout)
                self.stop()
                return

    def stop(self):
        self._stopping.set()
        if self.server:
            # From a one-shot thread, never inline: shutdown() blocks until the
            # serving loop exits, so calling it on that loop deadlocks.
            threading.Thread(target=self.server.shutdown, daemon=True).start()

    def cleanup(self):
        for p in (self.paths.record,):
            try:
                os.unlink(p)
            except OSError:
                pass
        if self.lock_fd is not None:
            try:
                os.close(self.lock_fd)
            except OSError:
                pass

    def serve(self):
        if not self.acquire_lock():
            raise SystemExit("another daemon holds %s — refusing to start a second"
                             % self.paths.lock)
        self.token = secrets.token_urlsafe(32)
        handler = make_handler(self)
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        self.server.daemon_threads = True
        port = self.server.server_address[1]
        self.publish(port)
        log("serving on http://127.0.0.1:%d (pid %d, runtime %s)"
            % (port, os.getpid(), self.paths.runtime))
        threading.Thread(target=self.janitor, daemon=True).start()
        try:
            self.server.serve_forever(poll_interval=0.5)
        finally:
            self.cleanup()
            log("stopped")


# --- the request handler ----------------------------------------------------
def make_handler(daemon):
    class Handler(BaseHTTPRequestHandler):
        # Connection-per-request. Trivially correct here, and it removes a class of
        # keep-alive Content-Length hangs.
        protocol_version = "HTTP/1.0"
        server_version = "loop-bus"
        sys_version = ""
        timeout = SOCKET_TIMEOUT

        # -- plumbing --
        def log_message(self, fmt, *args):
            pass  # the access log is noise; real events go through log()

        def _send(self, code, body=b"", ctype="application/json", extra=None):
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            # The page-side teeth of the trust posture: no inline scripts, no eval,
            # no third-party anything. This is what forces a zero-build frontend.
            self.send_header("Content-Security-Policy",
                             "default-src 'none'; script-src 'self'; style-src 'self'; "
                             "connect-src 'self'; img-src 'self' data:; base-uri 'none'; "
                             "form-action 'none'; frame-ancestors 'none'")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            for k, v in (extra or {}).items():
                self.send_header(k, v)
            self.end_headers()
            if self.command != "HEAD" and body:
                self.wfile.write(body)

        def _err(self, code, msg):
            self._send(code, json.dumps({"error": msg}).encode())

        # -- trust checks --
        def _host_ok(self):
            """The one browser-independent DNS-rebinding defense.

            A rebound page reaches this port with an attacker-controlled Host. Only
            the literal loopback names are ever legitimate here.
            """
            host = self.headers.get("Host", "")
            name = host.rsplit(":", 1)[0].strip("[]") if host else ""
            return name in ("127.0.0.1", "localhost", "::1")

        def _token_ok(self):
            got = self.headers.get(TOKEN_HEADER, "")
            return bool(got) and secrets.compare_digest(got, daemon.token or "")

        def _cross_site(self):
            # Fail closed only when the browser positively tells us it is cross-site.
            return self.headers.get("Sec-Fetch-Site", "") in ("cross-site", "same-site")

        def _guard(self, need_token=True):
            daemon.last_request = time.time()
            if not self._host_ok():
                self._err(403, "host not allowed")
                return False
            if self._cross_site():
                self._err(403, "cross-site request refused")
                return False
            if need_token and not self._token_ok():
                self._err(401, "capability token required")
                return False
            return True

        def _read_body(self):
            """Read at most Content-Length. Unbounded by default; 413 over the cap."""
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                self._err(400, "bad Content-Length")
                return None
            if length > MAX_BODY:
                self._err(413, "body too large")
                return None
            if length <= 0:
                return b""
            return self.rfile.read(length)

        # -- routes --
        def do_GET(self):
            path = self.path.split("?", 1)[0]

            # The static app-shell class: no token, because a browser cannot attach a
            # header to a document navigation. Host-gated, and carries no secret other
            # than the token it must hand to its own scripts.
            if path in ("/", "/index.html"):
                if not self._guard(need_token=False):
                    return
                page = INDEX_HTML.replace("__BUS_TOKEN__", html.escape(daemon.token or ""))
                return self._send(200, page.encode(), "text/html; charset=utf-8")
            if path == "/app.js":
                if not self._guard(need_token=False):
                    return
                return self._send(200, APP_JS.encode(), "text/javascript; charset=utf-8")
            if path == "/style.css":
                if not self._guard(need_token=False):
                    return
                return self._send(200, STYLE_CSS.encode(), "text/css; charset=utf-8")

            # The sensitive data class: token required, on reads too. A rebound page
            # must not be able to scrape state.
            if path == "/health":
                if not self._guard():
                    return
                idle, blockers = daemon.idle_check()
                return self._send(200, json.dumps({
                    "ok": True, "pid": os.getpid(), "started_at": daemon_started,
                    "idle": idle, "idle_blockers": blockers,
                    "warnings": daemon.warnings,
                }).encode())

            if path == "/api/state":
                if not self._guard():
                    return
                body, etag = daemon.model.snapshot_bytes()
                if self.headers.get("If-None-Match") == etag:
                    return self._send(304, b"", extra={"ETag": etag})
                return self._send(200, body, extra={"ETag": etag})

            return self._err(404, "no such endpoint")

        def do_HEAD(self):
            self.do_GET()

        def do_POST(self):
            path = self.path.split("?", 1)[0]
            if not self._guard():
                return
            # JSON + a custom header forces a CORS preflight that a form-CSRF cannot
            # satisfy. The token header does double duty as that custom header.
            ctype = (self.headers.get("Content-Type") or "").split(";")[0].strip()
            if ctype and ctype != "application/json":
                return self._err(415, "application/json only")
            body = self._read_body()
            if body is None:
                return

            if path == "/shutdown":
                self._send(200, json.dumps({"stopping": True}).encode())
                log("shutdown requested over http")
                daemon.stop()
                return

            return self._err(404, "no such endpoint")

    return Handler


daemon_started = now_iso()


def log(msg):
    sys.stderr.write("[bus %s] %s\n" % (now_iso(), msg))
    sys.stderr.flush()


# --- adopt-or-spawn ---------------------------------------------------------
def health(port, token, timeout=HEALTH_TIMEOUT):
    """Ask a candidate daemon whether it is really ours and really alive."""
    import urllib.error
    import urllib.request
    req = urllib.request.Request("http://127.0.0.1:%d/health" % port,
                                 headers={TOKEN_HEADER: token, "Host": "127.0.0.1:%d" % port})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as res:
            return json.loads(res.read().decode())
    except (urllib.error.URLError, OSError, ValueError):
        return None


def is_live(paths):
    """Liveness authority = a held lock plus an authenticated health check.

    Never a pidfile: a PID is reused, and a stale record then names somebody else's
    process. The lock cannot lie — the kernel drops it when the holder dies.
    """
    rec = read_json(paths.record)
    if not rec or not rec.get("port") or not rec.get("token"):
        return None
    # If we can take the lock, nothing is holding it, so any record is stale.
    probe = os.open(paths.lock, os.O_CREAT | os.O_RDWR, 0o600)
    try:
        try:
            fcntl.flock(probe, fcntl.LOCK_EX | fcntl.LOCK_NB)
            fcntl.flock(probe, fcntl.LOCK_UN)
            return None  # lock was free => no live daemon => stale record
        except OSError:
            pass  # held: somebody is alive, now prove it is ours
    finally:
        os.close(probe)
    return rec if health(rec["port"], rec["token"]) else None


def ensure(paths, idle_timeout):
    """Adopt-or-spawn, idempotent. NEVER spawn-fresh: that drops in-flight messages."""
    rec = is_live(paths)
    if rec:
        log("adopted running daemon on port %d (pid %s)" % (rec["port"], rec.get("pid")))
        return rec
    # A new session, so the daemon outlives the terminal, /clear, --resume, and
    # session death. Claude Code does not reap background children; nohup/disown
    # stay in the session's process group and die with it.
    cmd = [sys.executable, os.path.abspath(__file__), "serve",
           "--workflow-dir", paths.workflow, "--idle-timeout", str(idle_timeout)]
    proc = subprocess.Popen(cmd, start_new_session=True,
                            stdin=subprocess.DEVNULL,
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL)
    deadline = time.time() + 10
    while time.time() < deadline:
        time.sleep(0.15)
        rec = is_live(paths)
        if rec:
            log("spawned daemon on port %d (pid %s)" % (rec["port"], rec.get("pid")))
            return rec
        if proc.poll() is not None:
            raise SystemExit("daemon exited immediately (rc=%s); run `serve` in the "
                             "foreground to see why" % proc.returncode)
    raise SystemExit("daemon did not become healthy within 10s")


def stop(paths):
    import urllib.error
    import urllib.request
    rec = read_json(paths.record)
    if not rec:
        log("no bus record; nothing to stop")
        return 0
    req = urllib.request.Request(
        "http://127.0.0.1:%d/shutdown" % rec["port"], method="POST", data=b"{}",
        headers={TOKEN_HEADER: rec["token"], "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=5) as res:
            res.read()
    except (urllib.error.URLError, OSError) as exc:
        log("shutdown request failed: %s" % exc)
        return 1
    log("stopped")
    return 0


# --- cli --------------------------------------------------------------------
def main(argv=None):
    ap = argparse.ArgumentParser(description="the console daemon (local bus)")
    ap.add_argument("cmd", choices=["ensure", "serve", "stop", "status"])
    ap.add_argument("--workflow-dir", default=".workflow")
    ap.add_argument("--idle-timeout", type=int, default=DEFAULT_IDLE_TIMEOUT,
                    help="seconds with no request AND no open checkpoint before self-shutdown")
    args = ap.parse_args(argv)

    paths = Paths(args.workflow_dir)
    if args.cmd == "serve":
        Daemon(paths, args.idle_timeout).serve()
        return 0
    if args.cmd == "ensure":
        rec = ensure(paths, args.idle_timeout)
        print("http://127.0.0.1:%d/" % rec["port"])
        return 0
    if args.cmd == "stop":
        return stop(paths)
    if args.cmd == "status":
        rec = is_live(paths)
        if not rec:
            print("not running")
            return 1
        h = health(rec["port"], rec["token"]) or {}
        print("running  pid=%s  port=%s  idle=%s" % (rec.get("pid"), rec["port"], h.get("idle")))
        for b in h.get("idle_blockers", []):
            print("  holding open: %s" % b)
        for w in h.get("warnings", []):
            print("  WARNING: %s" % w)
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())

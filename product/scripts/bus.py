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
import re
import secrets
import shutil
import signal
import socket
import subprocess
import sys
import threading
import time
import uuid
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

# --- tunables ---------------------------------------------------------------
MAX_BODY = 64 * 1024          # generous for a verdict; refuse anything larger
SOCKET_TIMEOUT = 10           # seconds a worker will wait on a slow client
DEFAULT_IDLE_TIMEOUT = 72 * 3600
GIT_CACHE_TTL = 10            # seconds; the poll runs every few seconds
RECENT_COMMITS = 10
TOKEN_HEADER = "X-Bus-Token"  # a custom header: forces the CSRF-defeating preflight
HEALTH_TIMEOUT = 3
DEFAULT_REMINDER_HOURS = 4    # how often an open checkpoint re-alerts while not overdue
WEBHOOK_TIMEOUT = 5           # seconds; an away-alert POST must never pin the janitor
TOAST_TIMEOUT = 5            # seconds; a desktop toast is best-effort, never blocking
BACKOFF_BASE = 30            # seconds; a failing away channel backs off, doubling from here
DEFAULT_REMOTE_PORT = 8799   # the fixed loopback port the remote socket binds; operator-overridable
REMOTE_KINDS = ("verdict",)  # Socket A's positive POST allowlist — everything else is loopback-only

# --- the demo static class --------------------------------------------------
# A throwaway create-demo sandbox served under /demo/<id>/. It joins the token-free
# STATIC serving class (a browser cannot attach a header to a document/iframe
# navigation), and its isolation is a per-path CSP, not a token: the `sandbox`
# DIRECTIVE forces an opaque origin SERVER-SIDE, so the demo is isolated from the
# console even at top-level navigation (the deep-link / away-tab case an iframe
# sandbox attribute alone misses) — it can neither read the console's localStorage
# nor reach its token-gated /api/*. Distinct from the console's own strict
# `script-src 'self'`, which stays intact: two per-path CSPs from one daemon.
DEMO_CSP = "sandbox allow-scripts allow-forms"
# The console page's CSP. Pulled out as a constant so /demo/* can send DEMO_CSP
# instead. frame-src 'self' is the one addition this slice makes: it lets the
# console EMBED the same-origin demo in a sandboxed iframe (belt-and-suspenders
# beside the top-level case); default-src 'none' would otherwise block every frame.
CONSOLE_CSP = ("default-src 'none'; script-src 'self'; style-src 'self'; "
               "connect-src 'self'; img-src 'self' data:; frame-src 'self'; "
               "base-uri 'none'; form-action 'none'; frame-ancestors 'none'")
# Explicit MIME map + nosniff (below): a demo asset is raw first-party bytes, and a
# guessed/omitted type either fails to execute a real asset or, worse, lets a
# mis-served one sniff into something executable. Unknown extension ⇒ octet-stream,
# which nosniff then refuses to run — fail-closed.
DEMO_MIME = {
    ".html": "text/html; charset=utf-8", ".htm": "text/html; charset=utf-8",
    ".js": "text/javascript; charset=utf-8", ".mjs": "text/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8", ".json": "application/json",
    ".svg": "image/svg+xml", ".png": "image/png", ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg", ".gif": "image/gif", ".webp": "image/webp",
    ".ico": "image/x-icon", ".woff2": "font/woff2", ".woff": "font/woff",
    ".txt": "text/plain; charset=utf-8", ".map": "application/json",
}
# A demo id is a work-item id — the dir name under demos/. Kept strict so it can never
# contribute a path segment that climbs out of the demo root (the realpath guard is the
# real defense; this refuses the obvious junk before a filesystem call).
DEMO_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")

# --- the relaunch-runner ----------------------------------------------------
# Only these kinds ADVANCE a dead/whole-parked loop, so only these are worth spawning a
# fresh session for. A verdict resumes a parked ticket; an intake starts new work. A
# lone control (pause/resume/reprioritize) has nothing to drive if the loop is gone, and
# release is loopback-only — by construction a human was present to approve it, so it is
# not an away-resume case (excluded for MVP).
RUNNER_KINDS = ("verdict", "intake")
RUNNER_MAX_ATTEMPTS = 5      # consecutive no-progress relaunches before a hard-stop + alert
RUNNER_BACKOFF_BASE = 30     # seconds; a crash-looping relaunch backs off, doubling from here
RUNNER_BACKOFF_CAP = 1800    # seconds; the backoff ceiling (30 min)
# A relaunch that HANGS is a distinct failure from one that crashes: an inert `claude`
# (e.g. an untrusted workspace, where the allowlist is ignored and the session stalls —
# MEASURED) never exits, so it would pin the runner in-flight forever, never scoring, never
# alerting. So a launch that has not DRAINED (advanced the watermark, which the loop does
# first thing) within this window is killed and scored as no-progress. A launch that HAS
# drained is doing real ticket work and may run as long as it likes.
RUNNER_STALL_TIMEOUT = 300   # seconds an un-drained relaunch may run before it is killed as inert
# The prompt the runner launches a fresh `claude -p` with. It must FORCE the boundary
# drain regardless of the CLAUDE.md "drive only if state.json shows an active run" guard —
# the runner only ever launches when there IS applicable unconsumed work, so an ambiguous
# "is this a casual session?" read is exactly the wrong outcome. An explicit instruction
# overrides the conditional guidance; the CLAUDE.md brief supplies the how.
RUNNER_RESUME_PROMPT = (
    "You are the disciplined-builder orchestrator, relaunched by the console daemon's "
    "relaunch-runner to resume an unattended run. There is unconsumed work in "
    ".workflow/inbox/ that advances a parked or ready build loop. Do NOT wait for "
    "confirmation and do NOT treat this as a casual session: run the boundary drain now "
    "(the drain→read→place→advance step in your CLAUDE.md — `drain.py list`, apply each "
    "message, `drain.py record`), which resumes any parked ticket whose verdict has "
    "arrived, then continue the loop from .workflow/loop.md until you park or run out of "
    "ready work, and write the handoff."
)


# --- path resolution --------------------------------------------------------
# The workflow tree spans two filesystems whenever the repo lives on a mount whose
# rename/mode guarantees are weak (the WSL /mnt/c case). The atomicity- and
# mode-sensitive runtime paths are relocated to a native filesystem; the committed
# artifacts stay in the repo by construction. A gitignored pointer records where
# the runtime half went — without it, nothing could FIND the relocated tree, since
# the daemon's own discovery record lives inside it.
#
# Absent pointer => no relocation happened => the workflow dir IS the runtime root.
# That is the common (non-WSL) case and costs zero indirection — but only on a
# filesystem that can actually hold the tree; see _unrelocated_root.

# The runtime root's IDENTITY, written inside the root itself. isdir() is not
# identity: a restored backup, a second WSL distro, or any stray directory at the
# pointed path binds clean and starts writing this project's state into a tree that
# belongs to something else. The stamp makes that a MISMATCH rather than a silent
# adoption. Read tolerantly (absent => a pre-stamp install, which is legacy, not
# wrong) and written strictly (accept it once, then stamp it, so the NEXT resolution
# is checked) — that is what lets it land on live installs without breaking one.
RUNTIME_STAMP = ".workflow-runtime"


def slugify(name, cap=32):
    """A filesystem-safe, stable fragment of a project name (for humans reading `ls`)."""
    s = re.sub(r"[^a-z0-9]+", "-", (name or "").lower()).strip("-")
    return s[:cap].rstrip("-") or "project"


def runtime_root_for(project_path):
    """Where a project's relocated runtime tree BELONGS — derived, not chosen.

    This was prose until now ("create a runtime tree on a local filesystem, under the
    user's home"), which meant a model picked the path. Two projects with the same
    basename in different parents therefore derived the SAME path and cross-bound two
    live installs — silent, two-project corruption. The abspath hash kills the
    collision; the determinism is also what makes `/rebind`'s third probe candidate
    exist at all (a canonical location can be guessed from the project alone).
    """
    project = os.path.abspath(os.path.expanduser(project_path))
    base = os.environ.get("XDG_STATE_HOME") or os.path.join(
        os.path.expanduser("~"), ".local", "state")
    digest = hashlib.sha256(project.encode("utf-8")).hexdigest()[:8]
    return os.path.join(os.path.abspath(os.path.expanduser(base)),
                        "dev-autonomous-workflow",
                        "%s-%s" % (slugify(os.path.basename(project)), digest))


def read_stamp(root):
    """The runtime root's identity, or None when it has none / cannot be read.

    An unreadable or corrupt stamp is NOT evidence of a mis-bind, so it reads as
    absent: this check exists to catch a wrong tree, not to invent a new way to fail.
    """
    try:
        with open(os.path.join(root, RUNTIME_STAMP)) as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def write_stamp(root, project_path):
    """Stamp a runtime root with the project it is bound to. Best effort by design:
    failing to record an identity must never break a resolution that already worked."""
    try:
        atomic_write(os.path.join(root, RUNTIME_STAMP), json.dumps({
            "project_path": os.path.abspath(os.path.expanduser(project_path)),
            "bound_at": now_iso(),
            "bound_host": socket.gethostname(),
        }, indent=2) + "\n", mode=0o600)
    except OSError:
        return False
    return True


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
        # The daemon's own away-alert bookkeeping (which open checkpoints it has
        # already alerted on). It cannot live in parked/ (single-writer, not the
        # daemon's) nor in the boot-scoped discovery record, so it is a fourth path
        # the daemon alone writes. A lost or corrupt copy re-alerts rather than going
        # silent — a missed alert is the failure this exists to prevent.
        self.alerts = os.path.join(self.runtime, "alerts.json")
        # Pinned for the same measured reason as the token: these are live credentials
        # on a tree whose mount may ignore 0600 and say nothing. The bus never touches
        # this path — it is here because path resolution has one owner.
        self.secrets = os.path.join(self.runtime, "secrets")
        # A STABLE remote-socket credential, unlike the per-boot loopback token. The
        # phone pairs once and the operator points a tunnel once; a token reminted every
        # boot would go stale on every restart — routine on WSL, the platform the away
        # channel most needs to survive. So it is persisted here (0600, verified) and
        # reused; delete-to-rotate = un-pair. Pinned for the loopback token's reason.
        self.remote_token_file = os.path.join(self.runtime, "remote_token")
        # The single-orchestrator LIVENESS marker. A human session (via the loop.sh
        # launcher) and a runner-launched `claude -p` both hold an flock on this file for
        # their whole lifetime; the runner probes it before spawning, so it never launches
        # a duplicate alongside a live orchestrator. A separate file from bus.lock: that
        # one is the DAEMON's election, this is the ORCHESTRATOR's. The kernel drops it on
        # death, so it never goes stale (unlike a pidfile). Pinned for co-location with the
        # rest of the runtime tree, not for correctness — flock is sound on the WSL 9p mount.
        self.orchestrator_lock = os.path.join(self.runtime, "orchestrator.lock")
        # committed half (always on the repo mount, never relocated)
        self.handoff = os.path.join(self.workflow, "handoff.md")
        self.backlog = os.path.join(self.workflow, "backlog.md")
        self.config = os.path.join(self.workflow, "config.json")
        self.repo = os.path.dirname(self.workflow)
        # The throwaway demo sandboxes. RUNTIME + gitignored, but NOT relocated to the
        # native FS like the rest of the runtime tree: it is marked no-pin
        # (write-once-then-serve, atomicity-light), so it stays under .workflow/ on the
        # repo mount — a torn render self-heals on the next poll and carries no secret.
        # It is the served root the /demo/* realpath guard is anchored to.
        self.demos = os.path.join(self.workflow, "demos")

    def _resolve_runtime_root(self):
        pointer = os.path.join(self.workflow, "runtime.json")
        try:
            with open(pointer) as fh:
                root = json.load(fh).get("runtime_root")
        except FileNotFoundError:
            return self._unrelocated_root()
        except (OSError, ValueError) as exc:
            raise SystemExit("runtime pointer %s is unreadable: %s" % (pointer, exc))
        if not root:
            return self._unrelocated_root()
        root = os.path.abspath(os.path.expanduser(root))
        if not os.path.isdir(root):
            # Fail loudly. Silently falling back to the repo mount would put the
            # token and the inbox on the very filesystem the relocation avoided.
            raise SystemExit(
                "runtime_root %s does not exist (pointer: %s). This project was bound "
                "on another machine, or its runtime tree was deleted — the durable half "
                "is intact and the runtime half is unreachable. Run /rebind to bind it "
                "to this machine; it is the only thing that repairs this." % (root, pointer))
        self._check_identity(root, pointer)
        return root

    def _unrelocated_root(self):
        """No pointer means "no relocation happened" — RIGHT on a filesystem that can
        hold the runtime tree, and WRONG on one that cannot.

        The wrong case is not hypothetical: a fresh clone under /mnt/c has no pointer
        (it is gitignored, by design — a committed absolute path would hand another
        machine a wrong root), so this resolver would hand back the repo mount and the
        capability token plus secrets/ would land on the very 0600-ignoring filesystem
        the relocation exists to avoid. Nothing would say so. The mount check that
        would have caught it lives in /start step 3 PROSE, and a clone never runs
        /start; the daemon's existing mode warning fires after the fact, which is a
        notification that the control already failed.

        So the path resolver — not a prose step — owns "may this filesystem hold the
        runtime tree", and it fails closed with the same error the dead pointer gets.
        Only a MEASURED failure stops: undecidable (a read-only tree, a missing dir)
        returns the old answer, because a false positive here would hard-stop a
        working install, which is worse than the silence it replaces.
        """
        if mount_honours_modes(self.workflow) is False:
            raise SystemExit(
                "%s has no runtime pointer, and this filesystem does not honour file "
                "modes (a 0600 create comes back world-readable). Binding the runtime "
                "tree here would put the console's capability token, the inbox, and "
                "secrets/ where any user on this machine can read them. This is the "
                "signature of a clone made on a Windows-interop or network mount. Run "
                "/rebind to bind the runtime tree to a filesystem that can hold it."
                % self.workflow)
        return self.workflow

    def _check_identity(self, root, pointer):
        """A pointed-at directory is not proof it is OUR directory."""
        project = os.path.dirname(self.workflow)
        stamp = read_stamp(root)
        if stamp is None:
            # Tolerant read: an install made before stamps existed is legacy, not
            # wrong. Adopt it, then stamp it — strict write — so the next resolution
            # is a real check. This is what makes the mechanism land without breaking
            # a single live install.
            write_stamp(root, project)
            return
        bound = stamp.get("project_path")
        if bound and os.path.abspath(bound) != os.path.abspath(project):
            raise SystemExit(
                "runtime_root %s is bound to a DIFFERENT project (%s), not %s (pointer: "
                "%s). Writing here would corrupt two installs at once. Run /rebind."
                % (root, bound, project, pointer))

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


_IS_WSL = None


def is_wsl():
    """True on WSL, measured once from /proc/version.

    It matters to the away channel specifically: on WSL the VM (and this daemon with
    it) is torn down by the Windows host ~8s after the last terminal closes, and no
    setting inside the distro can veto that — it is a `.wslconfig` question on the
    Windows side, which this package cannot reach. So the daemon that must alert an
    away human can itself be gone in exactly the away scenario, and the honest move is
    to say so rather than imply an alert will arrive.
    """
    global _IS_WSL
    if _IS_WSL is None:
        _IS_WSL = "microsoft" in (read_text("/proc/version", limit=4096) or "").lower()
    return _IS_WSL


def workspace_trusted(repo):
    """Best-effort read of whether Claude Code trusts this workspace — True / False, or
    None when it cannot be determined.

    MEASURED: a headless `claude -p` in an UNtrusted workspace ignores the settings.json
    allowlist entirely ("Ignoring N permissions.allow entries … not trusted"), so a
    relaunched loop cannot run its own tools and simply stalls. In practice `/start` is run
    interactively and accepts the trust dialog, so a real project is trusted by the time
    the runner could fire — but a project with `runner.enabled` set and trust never granted
    would spawn inert sessions, and that is worth SAYING. This is a warning signal only,
    never a spawn gate: a format change here must not silently disable the runner (the
    stall-timeout is the real backstop for an inert launch)."""
    cfgpath = os.path.join(os.path.expanduser(
        os.environ.get("CLAUDE_CONFIG_DIR", "~")), ".claude.json")
    data = read_json(cfgpath)
    if not isinstance(data, dict):
        return None
    proj = data.get("projects")
    entry = proj.get(repo) if isinstance(proj, dict) else None
    if not isinstance(entry, dict) or "hasTrustDialogAccepted" not in entry:
        return None
    return bool(entry["hasTrustDialogAccepted"])


def probe_mode_bits(root):
    """MEASURE what mode a 0600 create actually achieves under `root`.

    Returns `(bits, None)` on a real measurement and `(None, reason)` when the
    filesystem would not let us measure at all. The two cases are kept apart on
    purpose: "measured, and it is wrong" is grounds to stop, "could not measure" is
    not — a read-only checkout must never be mistaken for an unsafe mount.

    Measuring beats sniffing the mount type. `9p` / `drvfs` / `cifs` / `nfs` is an
    open-ended list that would need a per-platform table (and would be wrong on the
    next one); a create-then-stat is one syscall pair and is correct on WSL, macOS
    and Linux by construction, because it asks the only question that matters.
    """
    probe = os.path.join(root, ".mode-probe.%d" % os.getpid())
    try:
        fd = os.open(probe, os.O_CREAT | os.O_WRONLY | os.O_EXCL, 0o600)
        os.close(fd)
    except OSError as exc:
        return None, "cannot probe file mode under %s: %s" % (root, exc)
    try:
        got = os.stat(probe).st_mode & 0o777
    except OSError as exc:
        return None, "cannot stat the mode probe under %s: %s" % (root, exc)
    finally:
        try:
            os.unlink(probe)
        except OSError:
            pass
    return got, None


def mount_honours_modes(root):
    """True / False / **None when undecidable**. The third value is the whole point:
    every caller that acts on `False` must decline to act on "could not tell"."""
    bits, _ = probe_mode_bits(root)
    if bits is None:
        return None
    return not (bits & ~0o600)


def probe_mode(root):
    """Ask the filesystem whether it honours a file mode at all, by measuring it.

    A mode is a request, not a guarantee: the WSL repo mount returns 0777 for a 0600
    create, from Linux, with no error. That matters far past the capability token —
    this same tree holds inbox messages carrying credentials a human returned at a
    setup checkpoint, and the secret store. So probe the tree once and say what is
    exposed, rather than discovering it per-file or, worse, never.
    """
    got, err = probe_mode_bits(root)
    if err:
        return err
    if got & ~0o600:
        return ("%s does not honour file modes (a 0600 create came back %s). The "
                "capability token, any credential returned at a setup checkpoint while "
                "it sits on the inbox, and the secret store are all readable by other "
                "users on this machine. Relocate the runtime root to a native "
                "filesystem and point .workflow/runtime.json at it." % (root, oct(got)))
    return None


# --- the handoff machine block ----------------------------------------------
# handoff.md is prose the orchestrator writes for the next session to read, but two
# machine facts live on it — the inbox consumed-set and its watermark — because it is
# the durable cold-start anchor, which is exactly the moment they are load-bearing.
# Prose and machine state therefore share one file, so the machine half lives in a
# fenced, delimited block that drain.py owns and rewrites without touching a byte of
# the surrounding prose.
#
# It is parsed HERE rather than in drain.py because both sides read it: the bus needs
# the watermark to GC its own partition. drain.py is the only writer.
# --- machine-owned blocks on handoff.md -------------------------------------
# handoff.md has more than one author. The orchestrator owns the PROSE; a fenced,
# delimited region is owned by a SCRIPT, which rewrites only its own block and never
# touches a byte outside it. That idiom is what lets one committed, human-readable
# resume anchor also carry machine state without the two halves overwriting each other.
#
# There are two such blocks. They exist for the same reason at different moments:
#   drain   — the inbox consumed-set + watermark            (drain.py)
#   parked  — the open-checkpoint mirror, a PROJECTION of parked/  (bus.py park)
#
# The markers are generated from ONE function so a third block cannot invent a third
# spelling of the same idiom. The two names are load-bearing literals: a handoff.md
# already in the field carries `drain:begin` exactly, so the generated string must
# reproduce it byte for byte.
def block_markers(name, owner):
    return ("<!-- %s:begin — machine-owned (%s). Do not hand-edit. -->" % (name, owner),
            "<!-- %s:end -->" % name)


def _block_re(begin, end):
    return re.compile(re.escape(begin) + r".*?" + re.escape(end), re.DOTALL)


HANDOFF_BEGIN, HANDOFF_END = block_markers("drain", "drain.py")
HANDOFF_BLOCK_RE = _block_re(HANDOFF_BEGIN, HANDOFF_END)
PARKED_BEGIN, PARKED_END = block_markers("parked", "bus.py park")
PARKED_BLOCK_RE = _block_re(PARKED_BEGIN, PARKED_END)
_FENCE_RE = re.compile(r"```json\s*(.*?)\s*```", re.DOTALL)


def _read_fenced(path, block_re):
    """The raw object inside a machine block, or None when there is not one.

    EVERY failure — no file, no block, no fence, bad JSON, not an object — returns None
    instead of raising, because each caller's safe default is different and only the
    caller knows it. The drain's is "no watermark, so GC nothing"; the parked mirror's
    is "no mirror", which is harmless because the mirror is re-derived rather than read.
    """
    text = read_text(path)
    if not text:
        return None
    m = block_re.search(text)
    if not m:
        return None
    fence = _FENCE_RE.search(m.group(0))
    if not fence:
        return None
    try:
        block = json.loads(fence.group(1))
    except ValueError:
        return None
    return block if isinstance(block, dict) else None


def _render_fenced(begin, end, block):
    return "%s\n```json\n%s\n```\n%s" % (
        begin, json.dumps(block, indent=2, sort_keys=True), end)


def _upsert_fenced(text, begin, end, block_re, block):
    """`text` with this one block set, every other byte — prose and any OTHER machine
    block — left alone. Appends when absent, which covers a first run and a session
    that rewrote handoff.md wholesale and dropped the block."""
    rendered = _render_fenced(begin, end, block)
    if text is None:
        return ("# Handoff — resume anchor\n\n"
                "_No prose anchor written yet._\n\n" + rendered + "\n")
    if block_re.search(text):
        return block_re.sub(lambda _: rendered, text, count=1)
    return text.rstrip("\n") + "\n\n" + rendered + "\n"


def empty_block():
    return {"consumed": [], "consumed_through": None, "dead_letters": []}


def read_handoff_block(path):
    """Return the drain's machine block, or an empty one if handoff.md has none.

    A missing or unparseable block degrades to empty rather than raising: on the bus
    side that means "no watermark, so GC nothing", which is the safe direction — a
    torn read can make collection lag, never over-collect.
    """
    block = _read_fenced(path, HANDOFF_BLOCK_RE)
    out = empty_block()
    if block:
        out.update({k: v for k, v in block.items() if k in out})
    if not isinstance(out["consumed"], list):
        out["consumed"] = []
    if not isinstance(out["dead_letters"], list):
        out["dead_letters"] = []
    return out


def render_handoff_block(block):
    return _render_fenced(HANDOFF_BEGIN, HANDOFF_END, block)


def upsert_handoff_block(text, block):
    """Return `text` with the drain block set to `block`, prose untouched.

    The dropped-block case cannot recover the SET (it is gone), only the structure;
    that is survivable precisely because every kind carries an effect anchor of its
    own, so a re-applied message is caught on its second layer rather than
    double-applied.

    The format lives here, beside its parser, so the two cannot drift apart. drain.py
    owns deciding what goes in it and writing the file.
    """
    return _upsert_fenced(text, HANDOFF_BEGIN, HANDOFF_END, HANDOFF_BLOCK_RE, block)


# --- parking a checkpoint ---------------------------------------------------
# `parked/<id>.json` is the alert trigger AND the loop's durable record that a ticket is
# waiting on a person. Until now it had no code writer at all: checkpoint/SKILL.md told
# the model to hand-write the JSON *and* to resolve the runtime root itself. Two things
# followed from that, both measured on a real machine move rather than reasoned:
#
#   Path resolution gained a second owner. `Paths` owns "where does the runtime tree
#   live", and a prose copy of that rule in a skill is a copy that drifts — the same
#   class of bug as the model-chosen runtime root that made two projects cross-bind.
#
#   The mirror could not become a mechanism. `handoff.parked[]` was PROSE, so when a
#   machine rebuild destroyed the runtime tree the open checkpoint survived only because
#   a human had written it into the prose by hand and another human read it back.
#   Durability that depends on somebody remembering is not durability.
#
# So parking gets a writer, and the mirror becomes a machine block — drain.py's proven
# two-authors-one-file idiom, unchanged.
#
# The mirror carries ids + kind + summary + opened_at and NOTHING else. Never the
# request body: a `setup` checkpoint's body is exactly where a credential appears, and
# handoff.md is COMMITTED. The record does not MOVE to the committed half, it PROJECTS
# onto it — which is what keeps the projection small, bounded, and safe to read back.
DEFAULT_DEADLINE_HOURS = 24
PARK_KINDS = ("demo", "qa", "setup", "reconcile")
# A ticket id becomes a FILENAME, so this is a path-safety check before it is a format
# check: one component, no separator, and it cannot be `.`/`..` because it must open on
# an alphanumeric.
TICKET_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
# handoff.md is read whole by every cold start, so the mirror is bounded like every
# other surface on it. A summary is a one-line label; a body is what it must never be.
MAX_SUMMARY = 200
# More open checkpoints than this is not a state the loop reaches by working — it parks
# one ticket and yields. It is a state it reaches by LEAKING, so the projection caps and
# reports the overflow instead of growing the anchor without bound.
MAX_MIRRORED = 50


def deadline_seconds(cfg):
    """config.checkpoint.deadline_hours → seconds (float, so a test can use ~0s)."""
    cp = cfg.get("checkpoint") if isinstance(cfg.get("checkpoint"), dict) else {}
    try:
        hours = float(cp.get("deadline_hours", DEFAULT_DEADLINE_HOURS))
    except (TypeError, ValueError):
        hours = DEFAULT_DEADLINE_HOURS
    return max(0.0, hours) * 3600.0


def stamp_deadline(paths, given=None):
    """The absolute deadline. Supplied wins; otherwise now + the configured hours.

    Deriving it here is not convenience — it is arithmetic that was being done by hand.
    `schemas.md` states the rule (now + `config.checkpoint.deadline_hours`) and every
    park was re-implementing it in a model's head, where a wrong answer is invisible:
    the daemon compares this value against wall-clock and simply never escalates.
    """
    if isinstance(given, str) and given.strip():
        return given.strip()
    dt = datetime.now(timezone.utc) + timedelta(seconds=deadline_seconds(paths.load_config()))
    # MICROSECONDS, not seconds — and that is the alert-dedup key, not cosmetics.
    # `alert_key` is (ticket_id + deadline), and its docstring accepted a same-second
    # collision on the reasoning that "a re-park almost always yields a later deadline".
    # That reasoning was sound while a MODEL hand-stamped the deadline at human speed.
    # Deriving it here makes two parks of one ticket inside a single second reachable at
    # machine speed (a retried /rebind re-opening the same checkpoint is the real path),
    # and the failure is the daemon reading the re-park as already-alerted and going
    # SILENT. Sub-second precision costs nothing and removes the collision.
    return dt.isoformat(timespec="microseconds")


def park_summary(rec, given=None):
    """The mirror's one-line label, sanitized hard — for two unrelated reasons.

    It is rendered inside a ```json fence that a cold start parses, so a backtick run in
    it could terminate the fence early and silently truncate the block (json.dumps
    escapes control characters, but it emits a backtick verbatim). And it lands in a
    COMMITTED file, so it is length-capped: a summary is a label, never a body.
    """
    text = given
    if text is None:
        req = (rec.get("checkpoint") or {}).get("request")
        text = req.get("what") if isinstance(req, dict) else None
    if not isinstance(text, str):
        text = ""
    text = " ".join(text.split()).replace("`", "'")
    if len(text) > MAX_SUMMARY:
        text = text[:MAX_SUMMARY - 1].rstrip() + "…"
    return text or "(no summary)"


def validate_park(rec):
    """The parked-ticket record's CHECKABLE half (`schemas.md § parked-ticket`).

    Judgment stays with the caller: `request`, `predicted_outcome`, `loop_position` and
    `worktree`/`branch` are the orchestrator's to compose, and this never invents one.
    What it refuses is a record that cannot do its job —
      no id     → nothing to name the file or key the mirror on;
      no token  → the drain matches a verdict to its ticket ON the token, so a tokenless
                  park is a checkpoint that can be answered but never resumed;
      bad kind  → the router has four arms and no default;
      no request→ the human is being asked nothing.
    """
    if not isinstance(rec, dict):
        raise Invalid("the parked-ticket record must be a JSON object")
    tid = rec.get("ticket_id")
    if not isinstance(tid, str) or not TICKET_ID_RE.match(tid):
        raise Invalid("ticket_id %r is not a safe single path component" % (tid,))
    tok = rec.get("token")
    if not isinstance(tok, str) or not tok.strip():
        raise Invalid("a park with no token can never be RESUMED — the drain matches a "
                      "verdict to its ticket on the token")
    cp = rec.get("checkpoint")
    if not isinstance(cp, dict):
        raise Invalid("checkpoint must be an object {kind, request}")
    if cp.get("kind") not in PARK_KINDS:
        raise Invalid("checkpoint.kind %r is not one of %s"
                      % (cp.get("kind"), ", ".join(PARK_KINDS)))
    if not cp.get("request"):
        raise Invalid("checkpoint.request is empty — the human is being asked nothing")
    return rec


def parked_mirror(paths):
    """The committed mirror of `parked/` — ids + kind + summary + opened_at, no bodies.

    A PROJECTION, recomputed from the directory on every mutation rather than patched
    incrementally. That is what keeps it honest. Prose `handoff.parked[]` was
    accidentally self-correcting — the orchestrator rewrote the whole file at each
    handoff, so a resolved checkpoint simply stopped being written — and a PERSISTED
    machine block is not: an incrementally-patched one would only ever gain entries, and
    every resolved checkpoint would stay "open" forever in the one file a cold start
    trusts. Re-deriving means an entry disappears the moment its record does.
    """
    entries = []
    try:
        names = sorted(os.listdir(paths.parked))
    except OSError:
        names = []
    for n in names:
        if not n.endswith(".json"):
            continue
        rec = read_json(os.path.join(paths.parked, n))
        if not isinstance(rec, dict):
            continue
        cp = rec.get("checkpoint") if isinstance(rec.get("checkpoint"), dict) else {}
        entries.append({
            "ticket_id": rec.get("ticket_id") or n[:-5],
            "kind": cp.get("kind"),
            "summary": park_summary(rec, rec.get("summary")),
            "opened_at": rec.get("opened_at"),
        })
    entries.sort(key=lambda e: (e.get("opened_at") or "", str(e.get("ticket_id"))))
    block = {"parked": entries[:MAX_MIRRORED], "projected_at": now_iso()}
    if len(entries) > MAX_MIRRORED:
        block["not_mirrored"] = len(entries) - MAX_MIRRORED
    return block


def publish_parked_mirror(paths):
    """Rewrite ONLY the parked block on handoff.md, durably.

    Same contract as `drain.publish`: write-temp → fsync → rename → fsync(dir), with the
    prose and the drain block untouched. That durability is the point of moving this off
    a text-writing tool — this is the half of the anchor that says a person is being
    waited on, and a torn copy loses the fact that the loop is BLOCKED, not merely where
    it had got to.
    """
    block = parked_mirror(paths)
    try:
        with open(paths.handoff) as fh:
            text = fh.read()
    except OSError:
        text = None
    atomic_write(paths.handoff,
                 _upsert_fenced(text, PARKED_BEGIN, PARKED_END, PARKED_BLOCK_RE, block),
                 mode=0o644)
    return block


def write_park(paths, rec, summary=None, deadline=None):
    """Park a ticket: the durable record, then the committed projection of it.

    Record first. It is the alert trigger the always-alive daemon watches, so until it
    exists nobody has been told; the mirror only helps a cold start that has not
    happened yet. Writing the mirror first would open a window where handoff.md claims a
    checkpoint that no daemon can see.
    """
    validate_park(rec)
    rec = json.loads(json.dumps(rec))  # never mutate the caller's object
    rec["summary"] = park_summary(rec, summary)
    rec["deadline"] = stamp_deadline(paths, deadline or rec.get("deadline"))
    rec.setdefault("opened_at", now_iso())
    dest = os.path.join(paths.parked, rec["ticket_id"] + ".json")
    atomic_write(dest, json.dumps(rec, indent=1, sort_keys=True) + "\n", mode=0o600)
    # A park can carry a credential-adjacent body, so the mode is checked the way the
    # token's is: asked-for is not achieved on a mount that ignores modes.
    warn = verify_mode(dest, 0o600)
    block = publish_parked_mirror(paths)
    out = {"ticket_id": rec["ticket_id"], "kind": rec["checkpoint"]["kind"],
           "record": dest, "deadline": rec["deadline"],
           "opened_at": rec["opened_at"], "mirrored": len(block["parked"])}
    if warn:
        out["warning"] = warn
    return out


def remove_park(paths, ticket_id):
    """Resolve a park: drop the record, then re-project the mirror.

    The mirror's other half, and not optional. `park` alone would give handoff.md a
    machine block that only ever GROWS — every resolved checkpoint staying "open"
    forever in the file a cold start rebuilds position from, which is worse than the
    prose it replaced, because a machine block reads as authoritative.

    Idempotent: an already-removed record is not an error. A re-applied verdict must
    no-op on its second pass, the same way every other consumer anchor does.
    """
    if not isinstance(ticket_id, str) or not TICKET_ID_RE.match(ticket_id):
        raise Invalid("ticket_id %r is not a safe single path component" % (ticket_id,))
    dest = os.path.join(paths.parked, ticket_id + ".json")
    removed = True
    try:
        os.unlink(dest)
    except FileNotFoundError:
        removed = False
    except OSError as exc:
        raise Invalid("cannot remove %s: %s" % (dest, exc))
    block = publish_parked_mirror(paths)
    return {"ticket_id": ticket_id, "removed": removed, "record": dest,
            "mirrored": len(block["parked"])}


# --- the inbox writer -------------------------------------------------------
# The bus is the SOLE writer of inbox/. The orchestrator never writes it and never
# deletes from it (one carve-out: a consumed message that carried a credential is
# unlinked by the orchestrator the moment that value reaches the secret store, so a
# secret's latency-to-zero does not wait on this janitor).
TS_FMT = "%Y%m%dT%H%M%S.%fZ"
_STEM_TS_RE = re.compile(r"^(\d{8}T\d{6}\.\d{6}Z)-")
# <ts>-<uuid>-<pid>. Recognizable on sight in a backlog `source` cell, which is how a
# promoted item is traced back to the request that asked for it.
MESSAGE_ID_RE = re.compile(r"\d{8}T\d{6}\.\d{6}Z-[0-9a-f]{8}-\d+")

VERDICT_OUTCOMES = ("approve", "changes", "reject")
# A CLOSED set, and that is load-bearing rather than tidy: a control op leaves no
# durable artifact to anchor on, so the ONLY thing making a redelivered control
# message safe is that re-applying it is a no-op by construction. Adding a
# non-idempotent op here would silently break the drain's crash-window safety, so an
# op has to be admitted deliberately — reprioritize re-orders the same backlog to the
# same order; pause and resume each re-set a flag.
CONTROL_OPS = ("reprioritize", "pause", "resume")


def stem_micros(stem):
    """The microseconds encoded in a message_id, or 0 if it is not one."""
    m = _STEM_TS_RE.match(stem or "")
    if not m:
        return 0
    try:
        dt = datetime.strptime(m.group(1), TS_FMT).replace(tzinfo=timezone.utc)
    except ValueError:
        return 0
    return int(dt.timestamp() * 1_000_000)


class Invalid(Exception):
    """A message the bus refuses to append. Rejected at POST time, while there is
    still a caller listening to be told why — once it is on the inbox the only reader
    is a batch consumer that cannot answer anybody."""


def _req_str(body, field, maxlen=8192):
    v = body.get(field)
    if not isinstance(v, str) or not v.strip():
        raise Invalid("%s must be a non-empty string" % field)
    if len(v) > maxlen:
        raise Invalid("%s is too long (max %d)" % (field, maxlen))
    return v


def _is_sensitive(returns):
    """Does this verdict hand back a credential?

    Deliberately shallow and permissive: `returns` is an open payload, and the cost of
    a false positive is a tighter mode plus an unlink the orchestrator would do anyway,
    while the cost of a false negative is a live key left lying on the inbox.
    """
    if isinstance(returns, dict):
        if returns.get("sensitive"):
            return True
        return any(_is_sensitive(v) for v in returns.values())
    if isinstance(returns, list):
        return any(_is_sensitive(v) for v in returns)
    return False


def validate(kind, body):
    """Return (clean_body, sensitive). Raises Invalid with a reason a human can act on."""
    if not isinstance(body, dict):
        raise Invalid("body must be a JSON object")

    if kind == "verdict":
        token = _req_str(body, "token", 512)
        v = body.get("verdict")
        if not isinstance(v, dict):
            raise Invalid("verdict must be an object")
        tasks = v.get("tasks")
        if tasks is None:
            if v.get("outcome") not in VERDICT_OUTCOMES:
                raise Invalid("verdict.outcome must be one of %s"
                              % ", ".join(VERDICT_OUTCOMES))
        else:
            # A setup checkpoint is plural: one reply carries a per-task outcome so a
            # mixed answer (this key works, that one I could not get) routes each on
            # its own.
            if not isinstance(tasks, list) or not tasks:
                raise Invalid("verdict.tasks must be a non-empty array when present")
            for t in tasks:
                if not isinstance(t, dict) or t.get("outcome") not in VERDICT_OUTCOMES:
                    raise Invalid("every verdict.tasks[] entry needs an outcome in %s"
                                  % ", ".join(VERDICT_OUTCOMES))
        clean = {"token": token, "verdict": v}
        return clean, _is_sensitive(v.get("returns")) or any(
            _is_sensitive(t.get("returns")) for t in (tasks or []) if isinstance(t, dict))

    if kind == "intake":
        clean = {"ask": _req_str(body, "ask")}
        nodes = body.get("node_ids")
        if nodes is not None:
            if not isinstance(nodes, list) or not all(isinstance(n, str) for n in nodes):
                raise Invalid("node_ids must be an array of strings")
            clean["node_ids"] = nodes
        return clean, False

    if kind == "control":
        op = body.get("op")
        if op not in CONTROL_OPS:
            raise Invalid("op must be one of %s" % ", ".join(CONTROL_OPS))
        return {"op": op}, False

    if kind == "release":
        ids = body.get("action_ids")
        if not isinstance(ids, list) or not ids or not all(
                isinstance(a, str) and a.strip() for a in ids):
            raise Invalid("action_ids must be a non-empty array of strings")
        # Always an explicit id-set — a snapshot of what the human actually looked at.
        # An action queued after their glance is simply not in the set, which is why
        # there is no approve-all-pending wildcard to offer.
        return {"action_ids": ids}, False

    raise Invalid("unknown kind %r" % kind)


class InboxWriter:
    """Appends typed messages to inbox/, in an order the watermark can trust.

    THE MEASURED CONTRACT: filename order must equal VISIBILITY order.

    The GC rule is "collect every inbox file at or below the watermark the
    orchestrator published", and the orchestrator computes that watermark from what it
    can SEE. So if a message can ever become visible carrying a timestamp lower than
    one already visible, the watermark can be published over a message nobody has
    consumed, and the janitor deletes it. A human's verdict, silently dropped.

    That is not hypothetical: stamp the name from the clock and then write+rename, and
    two concurrent POSTs race — the thread that names itself FIRST can be descheduled
    and rename LAST. Measured: the second drain publishes a watermark above the
    stalled message, and GC eats it. This server is threaded, so the race is live.

    Two rules close it, and both are needed:
      1. Allocate the name AND publish it under ONE lock, so the interval where a name
         exists but is not yet visible cannot overlap another allocation.
      2. Never re-issue a name at or below the last one, even if the clock moves
         backwards (NTP) or the daemon restarts — so the sequence is monotonic across
         a process boundary, not only within one.
    """

    def __init__(self, paths):
        self.paths = paths
        self._lock = threading.Lock()
        self._last_us = self._prime()

    def _prime(self):
        """Resume the sequence above everything that has ever been issued.

        The floor is the higher of two things, and BOTH are needed:

          - the newest name still on the inbox, and
          - the watermark the orchestrator has published.

        The disk alone is not enough, and the hole is not exotic: the GC's whole job is
        to empty this directory, so the steady state is an inbox with nothing in it to
        prime from. A daemon restarting there under a backwards clock step (NTP, a
        suspended laptop) would issue an id BELOW the watermark, and the janitor would
        collect that message on its next tick — before the orchestrator ever drained it.
        The watermark is the durable high-water record of what has already been issued
        and consumed, so it is the honest floor.
        """
        floor = 0
        try:
            names = os.listdir(self.paths.inbox)
        except OSError:
            names = []
        for n in names:
            if n.endswith(".json"):
                floor = max(floor, stem_micros(n[:-5]))
        floor = max(floor, stem_micros(
            read_handoff_block(self.paths.handoff).get("consumed_through") or ""))
        return floor

    def append(self, kind, body, sensitive=False):
        """Publish one message; return its bus-assigned message_id.

        The message_id IS the filename stem — one canonical id, so the ticket the
        console holds, the id the consumed-set records, and the stamp that lands on a
        promoted backlog item are all the same string.
        """
        record = dict(body)
        record["kind"] = kind
        with self._lock:
            now_us = int(time.time() * 1_000_000)
            us = max(now_us, self._last_us + 1)
            ts = datetime.fromtimestamp(us / 1_000_000, timezone.utc).strftime(TS_FMT)
            message_id = "%s-%s-%d" % (ts, uuid.uuid4().hex[:8], os.getpid())
            record["message_id"] = message_id
            record["received_at"] = now_iso()
            atomic_write(os.path.join(self.paths.inbox, message_id + ".json"),
                         json.dumps(record, indent=1) + "\n", mode=0o600)
            self._last_us = us
        return message_id

    def pending(self):
        try:
            return sorted(n[:-5] for n in os.listdir(self.paths.inbox)
                          if n.endswith(".json"))
        except OSError:
            return []


# --- the notifier -----------------------------------------------------------
# The daemon is the only process alive across every state the away-channel exists
# for — the orchestrator busy on the next ticket, whole-parked, or dead — so it is
# the one that can own alerting. Writing a parked record IS the trigger: the parking
# skill sends nothing. The daemon watches parked/, alerts on a new open checkpoint,
# re-alerts every reminder interval, and escalates once past the record's absolute
# deadline (never auto-proceeding). It also raises the second event — the loop
# hard-stop/escalation — off the sources that exist today: a dead-lettered console
# message (handoff's machine block). A thrash/crash hard-stop needs an orchestrator
# liveness signal that does not exist yet, so that arm waits for the runner.
#
# The away channel is BYO-webhook, stated plainly: the webhook reaches a phone and
# works from a detached daemon; a desktop toast is best-effort (Linux-only, and needs
# a notification daemon to own the D-Bus name — absent on a headless/WSL box). With
# no webhook configured there is NO away alerting, and the daemon says so rather than
# implying an alert that reaches nobody.
class ConfigCache:
    """Re-reads config.json only when its mtime changes.

    So adding a webhook to a running project takes effect within a poll interval
    instead of needing a restart, without re-parsing on every janitor tick. config is
    committed (repo mount); a parse failure degrades to {} — i.e. no away channel —
    which is the safe direction: a silent miss is the one outcome to avoid, and this
    surfaces as away-channel-not-ready rather than a crash.
    """
    def __init__(self, path):
        self.path = path
        self._mtime = None
        self._cfg = {}

    def get(self):
        try:
            mtime = os.stat(self.path).st_mtime
        except OSError:
            self._mtime, self._cfg = None, {}
            return self._cfg
        if mtime != self._mtime:
            self._mtime = mtime
            cfg = read_json(self.path)
            self._cfg = cfg if isinstance(cfg, dict) else {}
        return self._cfg


def reminder_seconds(cfg):
    """config.checkpoint.reminder_hours → seconds (float, so a test can use ~2s)."""
    cp = cfg.get("checkpoint") if isinstance(cfg.get("checkpoint"), dict) else {}
    try:
        hours = float(cp.get("reminder_hours", DEFAULT_REMINDER_HOURS))
    except (TypeError, ValueError):
        hours = DEFAULT_REMINDER_HOURS
    return max(0.0, hours) * 3600.0


def parse_deadline(value):
    """An absolute ISO deadline → epoch seconds, or None if absent/unparseable.

    Unparseable degrades to None (never overdue) rather than raising: a missing
    deadline must not stop the new-checkpoint alert from firing.
    """
    try:
        return datetime.fromisoformat(value).timestamp()
    except (TypeError, ValueError):
        return None


def alert_key(rec):
    """Identity of a checkpoint for alert-dedup.

    ticket_id alone is not enough: a ticket can park, resolve, and re-park on a
    DIFFERENT checkpoint, and keying on the ticket would suppress the second alert.
    The absolute deadline is the discriminator — it has stated semantics and a new
    park stamps a fresh one. `bus.py park` derives it at MICROSECOND precision for
    exactly this reason, so two machine-speed re-parks of one ticket cannot collide.
    The residual bound is now narrower and is the caller's own doing: a park that
    SUPPLIES a deadline identical to the previous one reads as already-alerted.
    """
    return "%s|%s" % (rec.get("ticket_id") or "?", rec.get("deadline"))


def plan_alerts(open_cps, dead_letters, state, now, reminder_secs):
    """Pure decision: what to send this tick, and which keys are still live.

    Returns (actions, live_checkpoint_keys, live_dead_letter_ids). Kept side-effect
    free so the timing rules — new → reminder → escalate-once → reminders-continue —
    are unit-testable without a clock, a webhook, or disk.
    """
    actions = []
    cpt_state = state.get("checkpoints", {})
    live_keys = set()
    for rec in open_cps:
        key = alert_key(rec)
        live_keys.add(key)
        deadline = parse_deadline(rec.get("deadline"))
        overdue = bool(deadline is not None and now > deadline)
        entry = cpt_state.get(key)
        base = {"key": key, "ticket_id": rec.get("ticket_id"),
                "deadline": rec.get("deadline"), "overdue": overdue}
        if not entry or entry.get("last_alert") is None:
            actions.append(dict(base, kind="new"))
        elif overdue and not entry.get("escalated"):
            actions.append(dict(base, kind="escalation"))
        elif (now - entry["last_alert"]) >= reminder_secs:
            actions.append(dict(base, kind="reminder"))
    live_dl = set()
    dl_state = state.get("dead_letters", {})
    for entry in dead_letters:
        mid = (entry or {}).get("message_id")
        if not mid:
            continue
        live_dl.add(mid)
        if mid not in dl_state:
            actions.append({"kind": "dead-letter", "message_id": mid,
                            "reason": (entry or {}).get("reason")})
    return actions, live_keys, live_dl


class Notifier:
    """Owns the away channel: config, alert bookkeeping, and delivery.

    Alert state (which checkpoints/dead-letters have been alerted) is loaded from disk
    at construction, so a restart does not re-alert everything already open — which on
    WSL, where restarts are routine, would train the human to ignore the channel.

    Delivery failure is a CHANNEL property, not a per-checkpoint one, so a failing
    webhook backs off the whole channel (doubling from BACKOFF_BASE, capped at the
    reminder interval) rather than storming a dead URL once per open checkpoint. A
    failed send does not mark the checkpoint alerted, so the existing reminder path
    retries it for free once the channel recovers.
    """
    def __init__(self, paths):
        self.paths = paths
        self.config = ConfigCache(paths.config)
        self.state = self._load(paths.alerts)
        self.port = None
        self.consecutive_failures = 0
        self.next_attempt = 0.0
        self.last_error = None

    def _load(self, path):
        data = read_json(path)
        if not isinstance(data, dict):
            return {"checkpoints": {}, "dead_letters": {}}
        for k in ("checkpoints", "dead_letters"):
            if not isinstance(data.get(k), dict):
                data[k] = {}
        return data

    def _persist(self):
        try:
            atomic_write(self.paths.alerts,
                         json.dumps(self.state, indent=1) + "\n", mode=0o600)
        except OSError as exc:
            log("could not persist alert state: %s" % exc)

    def run_once(self, daemon, open_cps):
        if daemon.port:
            self.port = daemon.port
        cfg = self.config.get()
        reminder_secs = reminder_seconds(cfg)
        dead = read_handoff_block(daemon.paths.handoff).get("dead_letters") or []
        now = time.time()
        changed = False
        if now >= self.next_attempt:
            actions, live_keys, live_dl = plan_alerts(
                open_cps, dead, self.state, now, reminder_secs)
            for action in actions:
                ok, detail = self.deliver(daemon, cfg, action)
                if detail.get("desktop"):
                    daemon.warn("desktop notification failed (best-effort, so the "
                                "away channel is the webhook): %s" % detail["desktop"])
                if not ok:
                    self._backoff(daemon, now, reminder_secs, detail.get("webhook"))
                    break
                self.consecutive_failures = 0
                self.last_error = None
                self._record_success(action, now)
                changed = True
        else:
            live_keys = {alert_key(r) for r in open_cps}
            live_dl = {m for m in ((d or {}).get("message_id") for d in dead) if m}
        changed = self._prune(live_keys, live_dl) or changed
        if changed:
            self._persist()

    def _backoff(self, daemon, now, reminder_secs, err):
        self.consecutive_failures += 1
        cap = reminder_secs or 3600.0
        delay = min(cap, BACKOFF_BASE * (2 ** (self.consecutive_failures - 1)))
        self.next_attempt = now + delay
        self.last_error = err
        daemon.warn("away webhook failed (%d in a row, retrying in ~%ds): %s"
                    % (self.consecutive_failures, int(delay), err))

    def _record_success(self, action, now):
        if action["kind"] == "dead-letter":
            self.state.setdefault("dead_letters", {})[action["message_id"]] = {"at": now}
            return
        cps = self.state.setdefault("checkpoints", {})
        entry = cps.setdefault(action["key"],
                               {"first_alert": None, "last_alert": None, "escalated": False})
        if entry["first_alert"] is None:
            entry["first_alert"] = now
        entry["last_alert"] = now
        if action["kind"] == "escalation":
            entry["escalated"] = True

    def _prune(self, live_keys, live_dl):
        """Drop state for checkpoints/dead-letters no longer present.

        This is what makes a resolved-then-re-parked ticket alert again (its new
        deadline is a new key), and it bounds the file. The one bound: a re-park that
        lands the same deadline second collides — accepted, since a re-park almost
        always yields a later deadline.
        """
        changed = False
        for bucket, live in (("checkpoints", live_keys), ("dead_letters", live_dl)):
            store = self.state.get(bucket, {})
            for key in [k for k in store if k not in live]:
                del store[key]
                changed = True
        return changed

    # -- delivery --
    def deliver(self, daemon, cfg, action):
        """Send one alert. Returns (ok, detail).

        ok is the WEBHOOK's health (the real away channel): False only when a
        configured webhook POST fails, so a failure backs the channel off. A desktop
        toast is best-effort — its failure is reported but never fails the send or
        blocks the channel. No webhook configured ⇒ ok=True (nothing to retry; the
        documented degradation), and the human polls the console.
        """
        notify = cfg.get("notify") if isinstance(cfg.get("notify"), dict) else {}
        text, payload = self._shape(daemon, action)
        detail = {}
        if notify.get("desktop"):
            detail["desktop"] = self._toast(text)
        webhook = notify.get("webhook") if isinstance(notify.get("webhook"), dict) else {}
        url = webhook.get("url")
        if not url:
            return True, detail
        detail["webhook"] = self._post(url, webhook.get("kind"), payload, text)
        return detail["webhook"] is None, detail

    def _shape(self, daemon, action):
        """The doorbell payload — enough to know a verdict is owed and where to give
        it, never the request body or notes. Project content (and any credential a
        request field might carry) does not leave the machine for a third party.
        """
        port = self.port or daemon.port
        console = "http://127.0.0.1:%s/" % (port if port else "?")
        kind = action["kind"]
        if kind == "dead-letter":
            reason = action.get("reason") or "unspecified"
            text = ("Loop escalation: a console message could not be applied "
                    "(%s). Open %s" % (reason, console))
            return text, {"event": "dead-letter", "message_id": action["message_id"],
                          "reason": reason, "console": console, "text": text}
        verb = {"new": "A checkpoint needs your verdict",
                "reminder": "Still waiting on your verdict",
                "escalation": "OVERDUE — a checkpoint passed its deadline"}[kind]
        tid = action.get("ticket_id") or "?"
        text = "%s (ticket %s, deadline %s). Open %s" % (
            verb, tid, action.get("deadline") or "—", console)
        return text, {"event": kind, "ticket_id": tid,
                      "deadline": action.get("deadline"),
                      "overdue": bool(action.get("overdue")),
                      "console": console, "text": text}

    def _post(self, url, kind, payload, text):
        import urllib.error
        import urllib.request
        body = {"text": text} if kind == "slack" else payload
        req = urllib.request.Request(
            url, data=json.dumps(body).encode(), method="POST",
            headers={"Content-Type": "application/json", "User-Agent": "loop-bus"})
        try:
            with urllib.request.urlopen(req, timeout=WEBHOOK_TIMEOUT) as res:
                res.read()
            return None
        except (urllib.error.URLError, OSError, ValueError) as exc:
            return str(exc)

    def _toast(self, text):
        try:
            subprocess.run(["notify-send", "Claude loop", text], timeout=TOAST_TIMEOUT,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            return None
        except (OSError, subprocess.SubprocessError) as exc:
            return str(exc)

    def deliver_event(self, daemon, event, text, extra=None):
        """A one-off away alert NOT tied to an open checkpoint — the runner's crash-loop
        hard-stop (the notifier's deferred thrash/crash alert arm, which waited for the
        runner's liveness signal). Best-effort and single-shot: it always surfaces via daemon.warn
        (so a dead webhook still leaves a trace in `status`), posts once to the webhook if
        configured, and is neither backed off nor retried — a hard-stop is one event, and
        the reminder machinery exists for open checkpoints, not for this. Returns the
        webhook error string, or None on success / no webhook.
        """
        daemon.warn(text)
        cfg = self.config.get()
        notify = cfg.get("notify") if isinstance(cfg.get("notify"), dict) else {}
        if notify.get("desktop"):
            self._toast(text)
        webhook = notify.get("webhook") if isinstance(notify.get("webhook"), dict) else {}
        url = webhook.get("url")
        if not url:
            return None
        console = "http://127.0.0.1:%s/" % (self.port or daemon.port or "?")
        payload = dict(extra or {}, event=event, console=console, text=text)
        return self._post(url, webhook.get("kind"), payload, text)

    def readiness(self):
        """The away-channel state a human reads in `status` — configured y/n, whether
        it is currently failing, and the WSL death caveat. A notifier that cannot
        notify must be VISIBLE, not silent.
        """
        cfg = self.config.get()
        notify = cfg.get("notify") if isinstance(cfg.get("notify"), dict) else {}
        webhook = notify.get("webhook") if isinstance(notify.get("webhook"), dict) else {}
        out = {"webhook": bool(webhook.get("url")), "desktop": bool(notify.get("desktop")),
               "consecutive_failures": self.consecutive_failures,
               "last_error": self.last_error, "wsl": is_wsl()}
        return out


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

    Alerting now hangs off this same scan: the idle vote and the alert read the same
    open-checkpoint set, so the janitor cannot reap the daemon while a verdict it is
    still trying to alert about is owed. The notifier is a TERM on this job, not a
    rewrite of the frame.
    """
    name = "parked"

    def __init__(self, notifier=None):
        self.notifier = notifier

    def tick(self, daemon):
        notifier = self.notifier or daemon.notifier
        if notifier is not None:
            notifier.run_once(daemon, self.open_checkpoints(daemon))

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


class InboxGCJob(Job):
    """Bounds the inbox, without either partition gaining a second writer.

    The orchestrator publishes `consumed_through` — a low-watermark it only advances
    once every message at or below it is consumed. The bus, which is the sole writer
    of inbox/, is therefore the one that deletes. The consumer never does.

    This job never votes the daemon busy. Unconsumed messages are durable on disk, so
    a daemon that reaps itself loses nothing: /start re-spawns it and the orchestrator
    drains at its next boundary. Voting busy here would instead keep the daemon alive
    forever whenever the orchestrator is gone — which is most of the time.
    """
    name = "inbox-gc"

    def tick(self, daemon):
        watermark = read_handoff_block(daemon.paths.handoff).get("consumed_through")
        if not watermark:
            return
        try:
            names = os.listdir(daemon.paths.inbox)
        except OSError:
            return
        for n in names:
            if not n.endswith(".json") or n[:-5] > watermark:
                continue
            try:
                os.unlink(os.path.join(daemon.paths.inbox, n))
            except FileNotFoundError:
                pass  # the sensitive-payload carve-out got there first
            except OSError as exc:
                log("inbox GC could not remove %s: %s" % (n, exc))


class RunnerJob(Job):
    """The relaunch-runner — the last link of the away channel.

    A verdict submitted from a phone lands DURABLY in the inbox, but nothing inside Claude
    self-wakes: a whole-parked or dead loop never drains it until a human reaches the
    terminal. This job closes that gap. When there is unconsumed work that would advance
    the loop AND no orchestrator is live, it spawns a FRESH `claude -p` — a clean context
    window per ticket, which also retires the manual-`/clear` stopgap. It carries NO
    verdict as a prompt: the verdict is already durable, and the existing drain applies it
    when the fresh loop cold-starts. The runner is GENERIC — it kicks the loop; the drain
    and the loop do the rest.

    Two things make it safe to spawn a process:

    LIVENESS. It must never launch a duplicate alongside a live orchestrator — that would
    silently clobber state (the single-orchestrator run-constraint's honest residual, but
    OUR defect here since the runner caused it). There is no ambient signal to read: Claude
    Code runs a constellation of claude-named helper processes, and a state.json mtime is
    stale-recent on a hung loop and absent on an idle-parked one. So liveness is an flock a
    launch EXPLICITLY holds — a human's via the loop.sh launcher, a runner-launched
    `claude -p` via `flock` itself. The runner probes that lock; held ⇒ someone is driving
    ⇒ back off. Its own spawn goes through `flock -n`, so even if a human starts in the
    probe→spawn window, the launch aborts rather than doubling (the latch is the lock, not
    a flag).

    NO CRASH-STORM. A launched loop that dies without advancing the watermark leaves the
    same work pending — relaunch it blindly and it storms. So a launch that makes no
    progress (watermark unmoved AND no applicable id consumed) backs off, doubling, and
    after RUNNER_MAX_ATTEMPTS HARD-STOPS and fires an away alert (the notifier's thrash arm).
    """
    name = "runner"

    def __init__(self, paths, notifier=None):
        self.paths = paths
        self.notifier = notifier
        self.config = ConfigCache(paths.config)
        self.launched = None          # Popen of an in-flight relaunch, or None
        self.launch_snapshot = None   # {through, ids} captured at launch, for progress
        self.consecutive_noprogress = 0
        self.next_attempt = 0.0       # backoff gate (epoch)
        self.hard_stopped = False
        self.last_launch_at = None
        self.last_error = None

    # -- config --
    def _enabled(self):
        runner = self.config.get().get("runner")
        return bool(isinstance(runner, dict) and runner.get("enabled"))

    def _claude_bin(self):
        # BUS_CLAUDE_BIN is the test seam and a legitimate escape hatch for a claude at a
        # nonstandard path; otherwise resolve on the daemon's own PATH (inherited from the
        # /start session that spawned it), falling back to a bare name.
        return os.environ.get("BUS_CLAUDE_BIN") or shutil.which("claude") or "claude"

    # -- the three preconditions --
    def _applicable(self, daemon):
        """The unconsumed inbox messages that would advance the loop, via the drain's own
        list logic (single owner — never re-derived here). Lazy import to avoid a cycle
        (drain imports bus)."""
        try:
            import drain
            res = drain.cmd_list(self.paths, None)
        except Exception as exc:  # a drain bug must not take the daemon down
            log("runner: could not list inbox: %r" % exc)
            return []
        return [p for p in res.get("pending", []) if p.get("kind") in RUNNER_KINDS]

    def _orchestrator_live(self, daemon):
        """True iff something holds the orchestrator lock. A free lock is provable (we can
        take it); a held one means a human session (via loop.sh) or a prior runner launch
        is driving. Never a pidfile read — the flock cannot lie, and the kernel drops it on
        death."""
        try:
            fd = os.open(self.paths.orchestrator_lock, os.O_CREAT | os.O_RDWR, 0o600)
        except OSError:
            return False  # cannot even open it ⇒ treat as free; the flock -n spawn is the real guard
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            fcntl.flock(fd, fcntl.LOCK_UN)
            return False
        except OSError:
            return True
        finally:
            os.close(fd)

    # -- the tick --
    def tick(self, daemon):
        if not self._enabled():
            return
        # 1. Reap an in-flight launch and score its progress before deciding anything.
        if self.launched is not None:
            if self.launched.poll() is None:
                # A launch that has drained is productively working (a resumed ticket can
                # run for a long time) — leave it. One that has NOT drained within the
                # stall window is inert (an untrusted/hung `claude`) — kill and score it,
                # so it feeds the same backoff→hard-stop→alert path a crash does.
                if (not self._drained_since_launch()
                        and time.time() - (self.last_launch_at or 0) > RUNNER_STALL_TIMEOUT):
                    log("runner: a relaunch ran >%ds without draining — killing it as inert"
                        % RUNNER_STALL_TIMEOUT)
                    self._kill(self.launched)
                    self._score(daemon, "killed: no drain within the stall timeout")
                    self.launched = None
                return  # still running; the lock it holds also blocks a double
            self._score(daemon, self.launched.returncode)
            self.launched = None
        if self.hard_stopped or time.time() < self.next_attempt:
            return
        # 2. Only spawn for work that would actually advance the loop.
        pending = self._applicable(daemon)
        if not pending:
            return
        # 3. Never alongside a live orchestrator.
        if self._orchestrator_live(daemon):
            return
        self._spawn(daemon, pending)

    def _spawn(self, daemon, pending):
        lock = self.paths.orchestrator_lock
        os.makedirs(os.path.dirname(lock), exist_ok=True)
        block = read_handoff_block(self.paths.handoff)
        self.launch_snapshot = {"through": block.get("consumed_through"),
                                "ids": {p["message_id"] for p in pending}}
        # `flock -n LOCK claude -p …` acquires the lock, forks claude holding it, and
        # releases on claude's exit. -n means a race-in orchestrator aborts THIS launch
        # rather than doubling. NO --dangerously-skip-permissions: that would bypass the
        # settings.json `ask` floor (deploy/network/gh-pr) — a runner-launched loop must
        # never fire those unattended. guard.sh still fires regardless. Detached
        # into its own session with DEVNULL stdio; cwd = the launch root, so it loads the
        # project's CLAUDE.md + .claude/settings.json; auth = the daemon's inherited ~/.claude.
        cmd = ["flock", "-n", lock, self._claude_bin(), "-p", RUNNER_RESUME_PROMPT]
        try:
            self.launched = subprocess.Popen(
                cmd, cwd=self.paths.repo, start_new_session=True,
                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL)
        except OSError as exc:
            self.launched = None
            self._noprogress(daemon, "spawn failed: %s" % exc)
            return
        self.last_launch_at = time.time()
        log("runner: relaunched the loop (pid %d) for %d applicable message(s)"
            % (self.launched.pid, len(pending)))

    def _drained_since_launch(self):
        """Has the in-flight launch advanced the watermark past where it started? The loop
        drains first thing, so this flips true within the launch's first minute if it is
        alive at all — which is exactly what separates a working launch from an inert one."""
        snap = self.launch_snapshot or {}
        through = read_handoff_block(self.paths.handoff).get("consumed_through")
        return (through or "") > (snap.get("through") or "")

    def _kill(self, proc):
        """Kill the whole launch group. start_new_session makes proc the group leader, so
        this reaps the `flock` wrapper AND the `claude` it forked together — killing only
        the wrapper would orphan a claude that keeps the lock (MEASURED)."""
        for sig in (signal.SIGTERM, signal.SIGKILL):
            try:
                os.killpg(proc.pid, sig)
            except OSError:
                return
            try:
                proc.wait(timeout=5)
                return
            except Exception:
                continue

    def _score(self, daemon, rc):
        """Did the finished launch move the loop forward? Progress = the watermark
        advanced OR at least one message this launch was spawned for is no longer
        applicable (it was consumed). Anything else is a launch that did nothing, which is
        what a crash loop looks like."""
        snap = self.launch_snapshot or {}
        through = read_handoff_block(self.paths.handoff).get("consumed_through")
        still = {p["message_id"] for p in self._applicable(daemon)}
        advanced = (through or "") > (snap.get("through") or "")
        consumed_some = bool(snap.get("ids") and (snap["ids"] - still))
        if advanced or consumed_some:
            if self.consecutive_noprogress or self.next_attempt:
                log("runner: relaunch made progress; crash-loop counter reset")
            self.consecutive_noprogress = 0
            self.next_attempt = 0.0
            self.last_error = None
        else:
            self._noprogress(daemon, "relaunch exited (rc=%s) without advancing the loop" % rc)

    def _noprogress(self, daemon, reason):
        self.consecutive_noprogress += 1
        self.last_error = reason
        if self.consecutive_noprogress >= RUNNER_MAX_ATTEMPTS:
            self.hard_stopped = True
            text = ("Loop escalation: the relaunch-runner hard-stopped after %d "
                    "consecutive relaunches made no progress (%s). The loop cannot "
                    "self-resume — a human must intervene." %
                    (self.consecutive_noprogress, reason))
            log("runner: HARD-STOP — %s" % reason)
            if self.notifier is not None:
                self.notifier.deliver_event(
                    daemon, "loop-stall", text,
                    {"attempts": self.consecutive_noprogress})
        else:
            delay = min(RUNNER_BACKOFF_CAP,
                        RUNNER_BACKOFF_BASE * (2 ** (self.consecutive_noprogress - 1)))
            self.next_attempt = time.time() + delay
            log("runner: no progress (%d/%d), backing off ~%ds — %s"
                % (self.consecutive_noprogress, RUNNER_MAX_ATTEMPTS, int(delay), reason))

    # -- idle vote + readiness --
    def is_idle(self, daemon):
        # Busy while a launch is in flight, or while we still owe a resume for applicable
        # work and no orchestrator is live — so the janitor cannot reap the daemon out from
        # under a resume it is responsible for. A hard-stop goes idle (the alert has fired;
        # holding the daemon open on a stuck loop helps nobody).
        if not self._enabled() or self.hard_stopped:
            return True
        if self.launched is not None and self.launched.poll() is None:
            return False
        return not (self._applicable(daemon) and not self._orchestrator_live(daemon))

    def idle_reason(self, daemon):
        if self.is_idle(daemon):
            return None
        if self.launched is not None and self.launched.poll() is None:
            return "a relaunched loop (pid %s) is running" % self.launched.pid
        return "unconsumed work awaits a relaunch"

    def readiness(self, daemon):
        return {"enabled": self._enabled(),
                "in_flight": bool(self.launched is not None
                                  and self.launched.poll() is None),
                "consecutive_noprogress": self.consecutive_noprogress,
                "hard_stopped": self.hard_stopped,
                "last_error": self.last_error, "wsl": is_wsl(),
                "workspace_trusted": workspace_trusted(self.paths.repo)}


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
            # A demo checkpoint carries the id of its served bundle so the console can
            # embed /demo/<id>/. Passed through only when it matches the served-id shape,
            # so a malformed record can never make the page build a junk iframe src.
            demo_id = cp.get("demo_id")
            if not (isinstance(demo_id, str) and DEMO_ID_RE.match(demo_id)):
                demo_id = None
            out.append({
                "ticket_id": rec.get("ticket_id"),
                "token": rec.get("token"),
                "kind": cp.get("kind"),
                "request": cp.get("request"),
                "deadline": rec.get("deadline"),
                "overdue": self._overdue(rec.get("deadline")),
                "demo_id": demo_id,
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

    def promoted(self):
        """message_id → the backlog item it became.

        The intake anchor and the "my requests" correlation key are the same field:
        promotion stamps the source message_id onto the item, which both makes a
        re-promotion a no-op AND tells the human what their request turned into. One
        field, two jobs — so this surface needs no mechanism of its own.
        """
        out = {}
        for line in (read_text(self.paths.backlog) or "").splitlines():
            m = MESSAGE_ID_RE.search(line)
            if not m:
                continue
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if cells:
                out[m.group(0)] = cells[0]
        return out

    def requests(self):
        """What the console needs to resolve the status of a ticket it remembers.

        The page holds its own ticket ids in localStorage; the bus cannot know which
        requests belong to this browser, so it publishes the index and the page looks
        itself up. Everything here is an effect anchor that already had to exist.
        """
        block = read_handoff_block(self.paths.handoff)
        return {
            "queued": self.inbox_pending(),
            "consumed": block.get("consumed") or [],
            "consumed_through": block.get("consumed_through"),
            "dead_letters": block.get("dead_letters") or [],
            "promoted": self.promoted(),
        }

    def inbox_pending(self):
        try:
            return sorted(n[:-5] for n in os.listdir(self.paths.inbox)
                          if n.endswith(".json"))
        except OSError:
            return []

    def snapshot(self):
        state = read_json(self.paths.state) or {}
        backlog = read_text(self.paths.backlog)
        return {
            "generated_at": now_iso(),
            "state": {
                "status": state.get("status"),
                "phase": state.get("phase"),
                "node": state.get("node"),
                "current_item": state.get("current_item"),
                "wave": state.get("wave"),
                "note": state.get("note"),
            },
            "parked": self.parked(),
            "outbox_pending": self.outbox(),
            "backlog": backlog,
            "recent": self.git_recent(),
            "requests": self.requests(),
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
<!-- loopback | remote. The remote page's bus-token is deliberately EMPTY (the token
     rides the pairing fragment, never the served surface it gates); the mode drives
     which sections app.js shows. -->
<meta name="bus-mode" content="__BUS_MODE__">
<link rel="stylesheet" href="/style.css">
</head>
<body>
<header>
  <h1>loop console</h1>
  <span id="conn" class="pill">connecting</span>
  <span id="mode" class="pill" hidden></span>
</header>

<section id="pairing" hidden>
  <h2>Pair a phone</h2>
  <p class="hint">Open this link on your phone (over your tunnel) to pair it. The token
    rides the URL fragment — it never reaches the server or its logs. Pair once; the
    phone remembers it.</p>
  <div id="pair-url" class="mono"></div>
  <div class="row">
    <button id="pair-copy" type="button">Copy pairing link</button>
    <span id="pair-msg" class="msg"></span>
  </div>
</section>

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
  <div id="ob-actions" hidden>
    <button id="ob-release" type="button">Release selected</button>
    <span id="ob-msg" class="msg"></span>
  </div>
</section>

<section id="ask">
  <h2>Request work</h2>
  <textarea id="ask-text" rows="3" placeholder="What needs doing? It lands in the backlog through triage, not straight onto the queue."></textarea>
  <div class="row">
    <button id="ask-send" type="button">Send request</button>
    <span id="ask-msg" class="msg"></span>
  </div>
</section>

<section id="requests">
  <h2>My requests <span id="rq-count" class="count"></span></h2>
  <div id="rq-list" class="empty">nothing sent from this browser yet</div>
</section>

<section id="activity">
  <h2>Recent activity</h2>
  <ol id="log" class="empty"></ol>
</section>

<template id="cp-tpl">
  <article class="card">
    <div class="row"><strong class="kind"></strong><span class="ticket mono"></span></div>
    <p class="request"></p>
    <div class="demo-wrap" hidden>
      <!-- The sandbox attribute is belt-and-suspenders beside the server's sandbox-CSP
           opaque origin; NEVER allow-same-origin (that would hand the demo this page's
           origin). app.js sets .src; the demo is read-only, the verdict is this form. -->
      <iframe class="demo-frame" sandbox="allow-scripts allow-forms" title="demo sandbox"></iframe>
      <a class="demo-open" target="_blank" rel="noopener noreferrer">open the demo full-screen ↗</a>
    </div>
    <div class="row"><span class="deadline"></span></div>
    <div class="verdict">
      <select class="outcome">
        <option value="approve">approve</option>
        <option value="changes">changes</option>
        <option value="reject">reject</option>
      </select>
      <input class="notes" type="text" placeholder="notes (what you saw, what to change)">
      <button class="send" type="button">Send verdict</button>
      <span class="msg"></span>
    </div>
  </article>
</template>

<template id="ob-tpl">
  <article class="card">
    <div class="row">
      <label><input class="pick" type="checkbox"> <strong class="action"></strong></label>
      <span class="oid mono"></span>
    </div>
    <div class="row"><span class="item"></span></div>
  </article>
</template>

<template id="rq-tpl">
  <article class="card">
    <div class="row"><strong class="rkind"></strong><span class="rstatus pill"></span></div>
    <p class="rsummary"></p>
    <div class="row"><span class="rticket mono"></span><span class="rdetail"></span></div>
  </article>
</template>

<script src="/app.js"></script>
</body>
</html>
"""

APP_JS = r"""// Vanilla, no build step, no eval: cloned <template> + textContent only.
// textContent (never innerHTML) is what keeps loop-authored strings — a commit
// subject, a checkpoint request — from being parsed as markup.
const $ = (s) => document.querySelector(s);

const META = (n) => (document.querySelector('meta[name="' + n + '"]') || {}).content || "";
const MODE = META("bus-mode") || "loopback";
const REMOTE = MODE === "remote";
const TOKEN_KEY = "bus.token";

// Token bootstrap. The loopback page carries its token in the meta tag. The REMOTE page
// carries none — it was paired out-of-band, so it reads the token from the pairing
// fragment on first visit (then stores it and strips the fragment so it never lingers
// in history) and from localStorage thereafter. A / B are different origins, so their
// stored tokens never cross.
function consumeFragment() {
  const m = (location.hash || "").match(/(?:^#|&)t=([^&]*)/);
  if (!m || !m[1]) return null;
  const tok = decodeURIComponent(m[1]);
  try { localStorage.setItem(TOKEN_KEY, tok); } catch (e) { /* private mode */ }
  history.replaceState(null, "", location.pathname + location.search);
  return tok;
}
function readToken() {
  const fromFragment = consumeFragment();
  let stored = null;
  try { stored = localStorage.getItem(TOKEN_KEY); } catch (e) { /* blocked store */ }
  return fromFragment || stored || META("bus-token") || "";
}
const TOKEN = readToken();
let etag = null;
let timer = null;

function setConn(text, ok) {
  const el = $("#conn");
  el.textContent = text;
  el.className = "pill" + (ok ? " ok" : " bad");
}

function renderState(s) {
  const dl = $("#state-dl");
  dl.textContent = "";
  const rows = [["status", s.status], ["phase", s.phase], ["node", s.node],
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

// --- sending -----------------------------------------------------------------
// Every write is JSON + the token header, which is what forces a preflight a form
// POST cannot satisfy. Nothing here is a real <form> submission: the CSP sets
// form-action 'none', so a stray submit fails closed rather than navigating away.
async function send(kind, body) {
  const res = await fetch("/api/" + kind, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-Bus-Token": TOKEN },
    body: JSON.stringify(body),
    cache: "no-store",
  });
  let data = {};
  try { data = await res.json(); } catch (e) { /* an error body is optional */ }
  if (res.status !== 202) throw new Error(data.error || ("HTTP " + res.status));
  return data;
}

// The loop is a batch consumer, so nothing here can report what HAPPENED — only that
// the request landed durably. Remembering the ticket is what turns that into an
// answer later, and localStorage is the only place that knows which requests are
// this browser's.
const MINE_KEY = "bus.myrequests";

function mine() {
  try { return JSON.parse(localStorage.getItem(MINE_KEY)) || []; }
  catch (e) { return []; }
}

function remember(ticket, kind, summary) {
  const all = mine();
  all.unshift({ ticket, kind, summary, at: new Date().toISOString() });
  try { localStorage.setItem(MINE_KEY, JSON.stringify(all.slice(0, 50))); }
  catch (e) { /* a full or blocked store costs the history, not the request */ }
  renderRequests(lastSnapshot);
}

function flash(el, text, ok) {
  el.textContent = text;
  el.className = "msg " + (ok ? "ok" : "bad");
  setTimeout(() => { el.textContent = ""; }, 6000);
}

function renderCheckpoints(items) {
  renderList(items, "#cp-list", "#cp-count", "#cp-tpl", (node, cp) => {
    node.querySelector(".kind").textContent = cp.kind || "checkpoint";
    node.querySelector(".ticket").textContent = cp.ticket_id || "";
    node.querySelector(".request").textContent =
      typeof cp.request === "string" ? cp.request : JSON.stringify(cp.request ?? "");
    // A demo checkpoint shows its sandbox inline (look), with the verdict form below it
    // (approve → lock · changes → refine · reject → discuss). The demo id is validated
    // server-side to the served-id shape; encodeURIComponent guards the URL we build.
    if (cp.kind === "demo" && cp.demo_id) {
      const wrap = node.querySelector(".demo-wrap");
      const src = "/demo/" + encodeURIComponent(cp.demo_id) + "/";
      node.querySelector(".demo-frame").src = src;
      node.querySelector(".demo-open").href = src;
      wrap.hidden = false;
    }
    const d = node.querySelector(".deadline");
    d.textContent = cp.deadline ? (cp.overdue ? "OVERDUE — " : "due ") + cp.deadline : "";
    if (cp.overdue) d.classList.add("overdue");
    const msg = node.querySelector(".msg");
    const btn = node.querySelector(".send");
    btn.addEventListener("click", async () => {
      btn.disabled = true;
      try {
        const outcome = node2(btn, ".outcome").value;
        const notes = node2(btn, ".notes").value;
        const r = await send("verdict", { token: cp.token, verdict: { outcome, notes } });
        remember(r.ticket, "verdict", (cp.kind || "checkpoint") + " " +
                 (cp.ticket_id || "") + " → " + outcome);
        flash(msg, "sent — the loop applies it at its next boundary", true);
      } catch (e) {
        flash(msg, String(e.message || e), false);
        btn.disabled = false;
      }
    });
  }, "none open");
}

// The card is cloned from a <template>, so a handler cannot close over a live node
// reference taken before insertion — walk up from the button instead.
function node2(btn, sel) { return btn.closest(".card").querySelector(sel); }

function renderOutbox(items) {
  renderList(items, "#ob-list", "#ob-count", "#ob-tpl", (node, ob) => {
    node.querySelector(".action").textContent = ob.action || "action";
    node.querySelector(".oid").textContent = ob.id || "";
    node.querySelector(".item").textContent = ob.item_ref || "";
    node.querySelector(".pick").value = ob.id || "";
  }, "none queued");
  // The remote surface can SEE pending outward actions (a read) but never release them
  // (release is loopback-only). The list shows; the release control never does.
  $("#ob-actions").hidden = REMOTE || !items.length;
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

// Resolve one remembered ticket against the anchors the snapshot publishes. This
// mirrors resolve_request() on the server deliberately: the page must render the
// answer with no extra round-trip per ticket, off the poll it already makes.
function resolve(rq, ticket) {
  const dl = (rq.dead_letters || []).find((d) => d && d.message_id === ticket);
  if (dl) return { status: "dead-letter", detail: dl.reason || "not applied" };
  const item = (rq.promoted || {})[ticket];
  if (item) return { status: "applied", detail: "became " + item };
  if ((rq.consumed || []).includes(ticket)) return { status: "applied", detail: "" };
  if ((rq.queued || []).includes(ticket)) return { status: "queued", detail: "waiting for the next boundary" };
  // Below the watermark it is consumed AND collected AND pruned — the most finished
  // state there is. Absence here means done, not lost.
  if (rq.consumed_through && ticket <= rq.consumed_through)
    return { status: "applied", detail: "" };
  return { status: "sent", detail: "not seen by the loop yet" };
}

function renderRequests(snap) {
  const rq = (snap && snap.requests) || {};
  const items = mine();
  renderList(items, "#rq-list", "#rq-count", "#rq-tpl", (node, m) => {
    const r = resolve(rq, m.ticket);
    node.querySelector(".rkind").textContent = m.kind;
    const st = node.querySelector(".rstatus");
    st.textContent = r.status;
    if (r.status === "applied") st.classList.add("ok");
    if (r.status === "dead-letter") st.classList.add("bad");
    node.querySelector(".rsummary").textContent = m.summary || "";
    node.querySelector(".rticket").textContent = m.ticket;
    node.querySelector(".rdetail").textContent = r.detail;
  }, "nothing sent from this browser yet");
}

let lastSnapshot = null;

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
    lastSnapshot = snap;
    renderState(snap.state || {});
    renderCheckpoints(snap.parked || []);
    renderOutbox(snap.outbox_pending || []);
    renderRequests(snap);
    renderLog(snap.recent || []);
    setConn("live", true);
  } catch (e) {
    setConn("daemon unreachable", false);
  }
}

$("#ask-send").addEventListener("click", async () => {
  const box = $("#ask-text");
  const msg = $("#ask-msg");
  const ask = box.value.trim();
  if (!ask) { flash(msg, "say what you want done first", false); return; }
  try {
    const r = await send("intake", { ask });
    remember(r.ticket, "intake", ask);
    box.value = "";
    flash(msg, "queued — it reaches the backlog through triage", true);
  } catch (e) {
    flash(msg, String(e.message || e), false);
  }
});

$("#ob-release").addEventListener("click", async () => {
  const msg = $("#ob-msg");
  const ids = [...document.querySelectorAll("#ob-list .pick:checked")].map((c) => c.value);
  if (!ids.length) { flash(msg, "pick the actions to release", false); return; }
  try {
    const r = await send("release", { action_ids: ids });
    remember(r.ticket, "release", "release " + ids.join(", "));
    flash(msg, "approved " + ids.length + " action(s) — they fire at the next boundary", true);
  } catch (e) {
    flash(msg, String(e.message || e), false);
  }
});

renderRequests(null);

// The pairing card is the local console's job alone: it fetches the pairing secret (a
// loopback-only endpoint) and shows the link to move to a phone. On the remote surface
// the endpoint 404s and the intake form is gone, because neither belongs there.
async function initPairing() {
  try {
    const res = await fetch("/api/pairing", {
      headers: { "X-Bus-Token": TOKEN }, cache: "no-store" });
    if (!res.ok) return;
    const p = await res.json();
    if (!p.configured) return;
    const box = $("#pair-url");
    box.textContent = p.url || (p.token + "  (set config.remote.public_url for a full link)");
    $("#pairing").hidden = false;
    $("#pair-copy").addEventListener("click", async () => {
      const text = p.url || p.token;
      try { await navigator.clipboard.writeText(text); flash($("#pair-msg"), "copied", true); }
      catch (e) { flash($("#pair-msg"), "select the link above and copy it", false); }
    });
  } catch (e) { /* pairing is a convenience; its absence is not an error */ }
}

function setupMode() {
  const pill = $("#mode");
  if (REMOTE) {
    pill.textContent = "remote"; pill.hidden = false;
    // Not part of A's surface: intake posts and outward release are loopback-only.
    $("#ask").hidden = true;
    $("#pairing").hidden = true;
  } else {
    initPairing();
  }
}
setupMode();

// A chained timeout, not setInterval: a slow response must never stack requests.
// Polling pauses when the tab is hidden and resumes with an immediate read.
async function loop() {
  if (REMOTE && !TOKEN) {
    setConn("not paired — open the pairing link from the local console", false);
    return;  // nothing to poll for until a token is paired in
  }
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
.demo-wrap { margin:.5rem 0; }
.demo-frame { width:100%; height:26rem; border:1px solid var(--line); border-radius:6px;
  background:#fff; display:block; }
.demo-open { display:inline-block; margin-top:.35rem; font-size:.8rem; color:var(--dim); }
.verdict { display:flex; gap:.4rem; align-items:center; margin-top:.5rem;
  padding-top:.5rem; border-top:1px solid var(--line); flex-wrap:wrap; }
.verdict .notes { flex:1; min-width:12rem; }
input, select, textarea, button { font:inherit; color:var(--fg); background:transparent;
  border:1px solid var(--line); border-radius:5px; padding:.3rem .5rem; }
textarea { width:100%; resize:vertical; }
button { cursor:pointer; border-color:var(--dim); }
button:hover:enabled { border-color:var(--fg); }
button:disabled { opacity:.5; cursor:default; }
label { display:inline-flex; align-items:center; gap:.4rem; }
.msg { font-size:.8rem; }
.msg.ok { color:var(--ok); }
.msg.bad { color:var(--bad); }
.hint { color:var(--dim); font-size:.85rem; margin:.25rem 0 .5rem; }
#pair-url { word-break:break-all; padding:.4rem .5rem; border:1px solid var(--line);
  border-radius:5px; margin-bottom:.5rem; }
#ask .row, #ob-actions { margin-top:.5rem; display:flex; gap:.75rem;
  align-items:center; justify-content:flex-start; }
#rq-list .card .row { gap:.75rem; }
.rdetail { font-size:.8rem; color:var(--dim); }
ol#log { list-style:none; padding:0; margin:0; }
ol#log li { display:grid; grid-template-columns:5rem 1fr auto; gap:.75rem;
  padding:.3rem 0; border-bottom:1px solid var(--line); }
ol#log time { color:var(--dim); font-size:.8rem; white-space:nowrap; }
"""


# --- the remote socket (Socket A) -------------------------------------------
# Remote access is a STRUCTURAL two-socket split, not a per-request Host guess
# (a Host is a header the untrusted proxy controls, and a Host boundary fails SILENTLY
# when the proxy rewrites it). Socket B — the loopback socket above — is the full
# surface and is never fronted. Socket A is this reduced surface, served ONLY when
# config.remote declares an identity transport, and the operator stands the transport
# (Cloudflare Access | Tailscale) up in front of it. The boundary is the port topology.
def _url_host(url):
    """The bare hostname of a public URL, for Socket A's Host-allowlist."""
    from urllib.parse import urlparse
    try:
        net = urlparse(url).netloc
    except (ValueError, AttributeError):
        return None
    return (net.rsplit("@", 1)[-1].rsplit(":", 1)[0].strip("[]") or None)


class RemoteConfig:
    """The parsed, validated config.remote — or None means Socket A is not served."""
    def __init__(self, transport, port, public_url):
        self.transport = transport
        self.port = port
        self.public_url = public_url

    @property
    def allow_credentials(self):
        """Only an END-TO-END-ENCRYPTED transport may carry a returned credential. A
        TLS-terminating proxy (Cloudflare Access) sees plaintext at its edge, so a
        returned key would transit a third party — structurally refused. WireGuard
        (Tailscale) has nobody in the middle, so it unlocks the setup carve-out."""
        return self.transport == "tailscale"

    @property
    def host(self):
        return _url_host(self.public_url) if self.public_url else None


def parse_remote(cfg):
    """config.remote → a RemoteConfig, or None when the remote socket is not served.

    Absent / disabled / no valid transport → None (loopback only). The port is
    config-declared and FIXED (defaulting), not daemon-chosen: the operator points a
    tunnel at it once and the phone is paired against it once, so a per-boot port would
    break the very away channel this exists for.
    """
    r = cfg.get("remote") if isinstance(cfg.get("remote"), dict) else {}
    if not r.get("enabled"):
        return None
    transport = r.get("transport")
    if transport not in ("access", "tailscale"):
        return None
    port = r.get("port")
    if not isinstance(port, int) or isinstance(port, bool) or not (0 < port < 65536):
        port = DEFAULT_REMOTE_PORT
    pub = r.get("public_url")
    public_url = pub.rstrip("/") if isinstance(pub, str) and pub.strip() else None
    return RemoteConfig(transport, port, public_url)


class SocketPolicy:
    """What ONE listening socket is allowed to serve, decided at bind and read per
    request via self.server.policy. A per-server fact, never a per-request guess — the
    structural boundary the remote split requires.

      remote            this is the reduced remote surface (Socket A)
      allow_credentials a returns-bearing setup verdict may land here (Tailscale only)
      extra_hosts       Host names the anti-DNS-rebinding allowlist also accepts (the
                        public tunnel host, so forwarded-Host proxy traffic is not
                        rejected; loopback names are always accepted)
    """
    def __init__(self, name, remote, allow_credentials=False, extra_hosts=()):
        self.name = name
        self.remote = remote
        self.allow_credentials = allow_credentials
        self.extra_hosts = tuple(h for h in extra_hosts if h)


# Socket B's policy is a constant: the full surface, credentials allowed, loopback host
# only. Socket A's policy is built per-serve from the transport (below).
LOOPBACK_POLICY = SocketPolicy("loopback", remote=False, allow_credentials=True)


def remote_carries_payload(clean):
    """Structural: does this verdict write a payload or gate a setup?

    THE credential boundary for Socket A, and it is deliberately NOT _is_sensitive():
    that helper is "shallow and permissive" by design, and a boundary built on a
    heuristic false-negatives silently — which here means a live key crossing a
    plaintext proxy edge, exactly the silent failure a structural boundary prevents. The crisp,
    false-negative-proof predicate is the PRESENCE of the returns/tasks keys: a bare
    opinion verdict ({outcome, notes}) has neither, anything setup-shaped has one.
    """
    v = clean.get("verdict")
    if not isinstance(v, dict):
        return False
    return "tasks" in v or "returns" in v


# --- the daemon -------------------------------------------------------------
class Daemon:
    def __init__(self, paths, idle_timeout=DEFAULT_IDLE_TIMEOUT):
        self.paths = paths
        self.idle_timeout = idle_timeout
        self.token = None
        self.port = None
        self.lock_fd = None
        self.server = None
        # Socket A — the reduced remote surface. None until serve() reads config.remote
        # and finds a declared transport; then a second server binds a fixed port and
        # a stable, persisted remote token gates it.
        self.remote = None            # a RemoteConfig, or None (not served)
        self.remote_token = None
        self.remote_server = None
        self.model = ReadModel(paths)
        self.inbox = InboxWriter(paths)
        self.notifier = Notifier(paths)
        self.runner = RunnerJob(paths, self.notifier)
        self.jobs = [ServeJob(), ParkedWatchJob(self.notifier), InboxGCJob(), self.runner]
        self.last_request = time.time()
        self.warnings = []
        self._stopping = threading.Event()

    def warn(self, msg):
        if msg and msg not in self.warnings:
            self.warnings.append(msg)
            log("WARNING: " + msg)

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
        if self.remote_server is not None:
            # The operator points cloudflared / tailscale serve at remote_port, and
            # NEVER at port (the full-surface loopback socket). remote_token is the
            # separate second factor, paired to the phone out-of-band.
            rec["remote_port"] = self.remote.port
            rec["remote_token"] = self.remote_token
        atomic_write(self.paths.record, json.dumps(rec, indent=1) + "\n", mode=0o600)
        self.warn(verify_mode(self.paths.record, 0o600))
        return rec

    # -- the remote socket's stable credential --
    def ensure_remote_token(self):
        """Read-or-create the persisted remote token; verify its achieved mode.

        Stable across restarts by construction — a phone paired once must keep working
        through the routine WSL restarts the away channel exists to survive. Minted only
        on first use; every later boot reuses the file. Deleting it re-pairs everyone.
        """
        tok = read_text(self.paths.remote_token_file)
        if tok and tok.strip():
            self.remote_token = tok.strip()
        else:
            self.remote_token = secrets.token_urlsafe(32)
            atomic_write(self.paths.remote_token_file,
                         self.remote_token + "\n", mode=0o600)
        self.warn(verify_mode(self.paths.remote_token_file, 0o600))

    def pairing_info(self):
        """What the LOCAL console renders to pair a phone. Loopback-only by the handler
        — the remote token is a secret that must never ride the surface it gates. When
        public_url is set, url is the whole pairing link (token in the fragment, which
        never leaves the browser); absent, the human still gets the token to place by
        hand once they know their tunnel host.
        """
        if self.remote is None:
            return {"configured": False}
        out = {"configured": True, "transport": self.remote.transport,
               "public_url": self.remote.public_url, "token": self.remote_token,
               "allow_credentials": self.remote.allow_credentials}
        if self.remote.public_url:
            out["url"] = "%s/#t=%s" % (self.remote.public_url, self.remote_token)
        return out

    def remote_status(self):
        """The remote-channel state a human reads in `status`/`/health`."""
        if self.remote is None:
            return {"enabled": False}
        return {"enabled": True, "bound": self.remote_server is not None,
                "transport": self.remote.transport, "port": self.remote.port,
                "public_url": bool(self.remote.public_url),
                "allow_credentials": self.remote.allow_credentials}

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
        # From a one-shot thread, never inline: shutdown() blocks until the serving
        # loop exits, so calling it on that loop deadlocks. Both sockets go down together.
        for srv in (self.server, self.remote_server):
            if srv:
                threading.Thread(target=srv.shutdown, daemon=True).start()

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
        # Measure the tree's mode behaviour once, up front. This is not only about the
        # token: from this increment on, a setup verdict carrying a live credential
        # lands in inbox/ under the same root.
        os.makedirs(self.paths.inbox, exist_ok=True)
        self.warn(probe_mode(self.paths.runtime))
        self.token = secrets.token_urlsafe(32)
        handler = make_handler(self)
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        self.server.daemon_threads = True
        self.server.policy = LOOPBACK_POLICY
        port = self.server.server_address[1]
        self.port = port
        # Socket A — the reduced remote surface, bound ONLY when config.remote declares
        # an identity transport. A distinct, persisted token gates it; the operator
        # fronts it with Cloudflare Access / Tailscale. A bind failure (port in use)
        # degrades to no-remote with a warning rather than taking the whole daemon down.
        self.remote = parse_remote(self.paths.load_config())
        if self.remote is not None:
            self.ensure_remote_token()
            try:
                self.remote_server = ThreadingHTTPServer(
                    ("127.0.0.1", self.remote.port), handler)
            except OSError as exc:
                self.remote_server = None
                self.warn("remote socket could not bind 127.0.0.1:%d (%s); remote "
                          "access is OFF this run." % (self.remote.port, exc))
            else:
                self.remote_server.daemon_threads = True
                self.remote_server.policy = SocketPolicy(
                    "remote", remote=True,
                    allow_credentials=self.remote.allow_credentials,
                    extra_hosts=(self.remote.host,))
                if not self.remote.public_url:
                    self.warn("config.remote has no public_url: the pairing link and "
                              "the forwarded-Host allowlist both need it — set it to "
                              "your tunnel's https URL.")
        self.publish(port)
        # The away channel is only as alive as this process. On WSL the Windows host
        # tears the VM (and this daemon) down shortly after the last terminal closes,
        # and nothing inside the distro can veto it, so say so — an alert that silently
        # reaches nobody is worse than a documented absence.
        if is_wsl():
            self.warn("platform is WSL: this daemon dies shortly after the last "
                      "terminal closes, taking the away channel with it, unless "
                      ".wslconfig sets vmIdleTimeout=-1 on the Windows side (this "
                      "package cannot set it for you).")
            if self.runner._enabled():
                self.warn("runner is enabled but this is WSL: the daemon that hosts it "
                          "dies with the last terminal, so an OVERNIGHT resume will not "
                          "happen unless .wslconfig sets vmIdleTimeout=-1.")
        if self.runner._enabled() and workspace_trusted(self.paths.repo) is False:
            self.warn("runner is enabled but this workspace is not trusted by Claude Code: "
                      "a relaunched `claude` would ignore .claude/settings.json's allowlist "
                      "and stall, so nothing would resume. Run /start (or `claude`) "
                      "interactively here once and accept the trust dialog.")
        if not self.notifier.readiness()["webhook"]:
            self.warn("no away webhook configured (config.notify.webhook.url): there "
                      "is no away alerting — a human must poll the console.")
        log("serving on http://127.0.0.1:%d (pid %d, runtime %s)"
            % (port, os.getpid(), self.paths.runtime))
        threading.Thread(target=self.janitor, daemon=True).start()
        if self.remote_server is not None:
            log("remote socket on http://127.0.0.1:%d (transport=%s, credentials=%s)"
                % (self.remote.port, self.remote.transport,
                   "yes" if self.remote.allow_credentials else "no"))
            threading.Thread(target=self.remote_server.serve_forever,
                             kwargs={"poll_interval": 0.5}, daemon=True).start()
        try:
            self.server.serve_forever(poll_interval=0.5)
        finally:
            if self.remote_server is not None:
                try:
                    self.remote_server.shutdown()
                except Exception:
                    pass
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

        def _send(self, code, body=b"", ctype="application/json", extra=None, csp=CONSOLE_CSP):
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            # The page-side teeth of the trust posture: the console's is no inline
            # scripts, no eval, no third-party anything (what forces a zero-build
            # frontend). A demo response instead carries the `sandbox` directive
            # (opaque origin) — two per-path CSPs from one daemon.
            if csp:
                self.send_header("Content-Security-Policy", csp)
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
            """The browser-independent DNS-rebinding defense.

            On Socket B (loopback), only the literal loopback names are ever legitimate.
            On Socket A the allowlist ALSO accepts the declared public host, because a
            proxy that forwards the original Host would otherwise have all its traffic
            rejected — here the port topology is the boundary and this is anti-rebinding
            defense-in-depth, not the boundary itself.
            """
            host = self.headers.get("Host", "")
            name = host.rsplit(":", 1)[0].strip("[]") if host else ""
            if name in ("127.0.0.1", "localhost", "::1"):
                return True
            return name in self.server.policy.extra_hosts

        def _token_ok(self):
            # Each socket authenticates against its OWN token. The remote token is a
            # distinct secret (the loopback token is never reused remotely), and it
            # is what makes a misconfigured proxy not instantly expose the surface.
            want = daemon.remote_token if self.server.policy.remote else daemon.token
            got = self.headers.get(TOKEN_HEADER, "")
            return bool(got) and bool(want) and secrets.compare_digest(got, want)

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

        # -- the demo static class --
        def _serve_demo(self, path):
            """Serve one file from a throwaway demo bundle under the sandbox-CSP opaque
            origin. The path is /demo/<id>/<relpath>; <relpath> defaults to index.html.

            The realpath guard is the security boundary, not the DEMO_ID_RE prefilter: it
            resolves symlinks and `..` on the CONCRETE path and requires the result to sit
            under the real demo root. So /demo/x/../../bus.json (or a relocated runtime
            path, or a symlink out) cannot escape to the token or the inbox — the escape
            resolves outside demos/ and is refused. The root itself is realpath'd once so a
            symlinked .workflow doesn't defeat the startswith.
            """
            rest = path[len("/demo/"):]
            demo_id, _, rel = rest.partition("/")
            if not DEMO_ID_RE.match(demo_id or ""):
                return self._err(404, "no such demo")
            root = os.path.realpath(daemon.paths.demos)
            base = os.path.join(root, demo_id)
            rel = rel or "index.html"
            if rel.endswith("/"):
                rel += "index.html"
            # Never serve a dotfile from a bundle. Bundle assets are never dot-prefixed,
            # and create-demo keeps its own bookkeeping there (the refine-round counter in
            # .refine.json, which survives park/resume/relaunch), plus it fends off a stray
            # .git/.DS_Store. A leading-dot segment anywhere in the path is refused.
            if any(seg.startswith(".") for seg in rel.replace("\\", "/").split("/") if seg):
                return self._err(404, "not found")
            target = os.path.realpath(os.path.join(base, rel))
            # startswith the base + os.sep so /demo/<id>/ can't be tricked by a sibling
            # dir sharing a prefix (demos/foo vs demos/foobar), and the base itself is a
            # dir not a file, so a bare base never matches a real file to serve.
            if target != base and not target.startswith(base + os.sep):
                return self._err(404, "not found")
            # MEASURED on the 9p repo mount: while `create-demo` refines in place
            # (write-temp → os.replace), a concurrent open of the target transiently
            # fails with ENODATA even though the rename is atomic and never tears the
            # CONTENT. A genuinely-absent file (ENOENT/FileNotFoundError) 404s at once;
            # a transient error retries briefly so a refine is invisible to a viewer
            # rather than flashing a 404, then 404s if it never resolves.
            body = None
            for attempt in range(4):
                try:
                    with open(target, "rb") as fh:
                        body = fh.read()
                    break
                except (FileNotFoundError, IsADirectoryError):
                    return self._err(404, "not found")
                except OSError as exc:
                    if attempt == 3:
                        log("demo serve failed for %s: %s" % (target, exc))
                        return self._err(404, "not found")
                    time.sleep(0.02)
            ctype = DEMO_MIME.get(os.path.splitext(target)[1].lower(),
                                  "application/octet-stream")
            # DEMO_CSP (opaque origin) instead of the console's script-src 'self';
            # no-store so a refine that overwrites index.html is never served stale.
            return self._send(200, body, ctype, csp=DEMO_CSP)

        # -- routes --
        def do_GET(self):
            path = self.path.split("?", 1)[0]

            # The static app-shell class: no token, because a browser cannot attach a
            # header to a document navigation. Host-gated, and carries no secret other
            # than the token it must hand to its own scripts.
            if path in ("/", "/index.html"):
                if not self._guard(need_token=False):
                    return
                # The remote page carries NO server-injected token: injecting it would
                # hand the surface to anyone who breaches the transport in one GET,
                # nullifying the second factor. It bootstraps its token from the pairing
                # fragment / localStorage instead. Only the loopback page uses the meta
                # tag, and only there is the token safe to embed.
                remote = self.server.policy.remote
                tok = "" if remote else (daemon.token or "")
                mode = "remote" if remote else "loopback"
                page = (INDEX_HTML.replace("__BUS_TOKEN__", html.escape(tok))
                                  .replace("__BUS_MODE__", mode))
                return self._send(200, page.encode(), "text/html; charset=utf-8")
            if path == "/app.js":
                if not self._guard(need_token=False):
                    return
                return self._send(200, APP_JS.encode(), "text/javascript; charset=utf-8")
            if path == "/style.css":
                if not self._guard(need_token=False):
                    return
                return self._send(200, STYLE_CSS.encode(), "text/css; charset=utf-8")

            # The demo static class: a throwaway create-demo bundle, served token-free
            # (like the page — a browser cannot header an iframe/document navigation)
            # under the DEMO_CSP opaque-origin isolation. Host-gated and realpath-guarded.
            # Serves on BOTH sockets: on Socket A it is exactly the "static demo" the
            # reduced remote surface is meant to carry.
            if path.startswith("/demo/"):
                if not self._guard(need_token=False):
                    return
                return self._serve_demo(path)

            # The sensitive data class: token required, on reads too. A rebound page
            # must not be able to scrape state.
            if path == "/health":
                if not self._guard():
                    return
                idle, blockers = daemon.idle_check()
                return self._send(200, json.dumps({
                    "ok": True, "pid": os.getpid(), "started_at": daemon_started,
                    "idle": idle, "idle_blockers": blockers,
                    "away": daemon.notifier.readiness(),
                    "remote": daemon.remote_status(),
                    "runner": daemon.runner.readiness(daemon),
                    "warnings": daemon.warnings,
                }).encode())

            if path == "/api/state":
                if not self._guard():
                    return
                body, etag = daemon.model.snapshot_bytes()
                if self.headers.get("If-None-Match") == etag:
                    return self._send(304, b"", extra={"ETag": etag})
                return self._send(200, body, extra={"ETag": etag})

            # The status resource the 202's Location header names. The console does not
            # need it (it resolves tickets off the polled snapshot), but a Location
            # that 404s is a lie, and this is what makes the async request-reply shape
            # honest for anything else that reads it.
            if path.startswith("/api/requests/"):
                if not self._guard():
                    return
                ticket = path[len("/api/requests/"):]
                if not MESSAGE_ID_RE.fullmatch(ticket):
                    return self._err(404, "no such ticket")
                return self._send(200, json.dumps(
                    resolve_request(daemon.model.requests(), ticket)).encode())

            # The pairing secret lives here, and only the local console may read it — so
            # this endpoint does not exist on the remote surface it gates. Structural, not
            # a Host guess: the remote page could never obtain the token it hands out.
            if path == "/api/pairing":
                if self.server.policy.remote:
                    return self._err(404, "no such endpoint")
                if not self._guard():
                    return
                return self._send(200, json.dumps(daemon.pairing_info()).encode())

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
                # Bringing the daemon down is a control op — not part of A's surface.
                if self.server.policy.remote:
                    return self._err(404, "no such endpoint")
                self._send(200, json.dumps({"stopping": True}).encode())
                log("shutdown requested over http")
                daemon.stop()
                return

            # The async command half of the protocol. There is no synchronous path to
            # offer here even if it were wanted: the orchestrator is a batch consumer
            # at a scheduler boundary, not an HTTP responder, so nothing can answer
            # "and what happened?" within this request. The honest reply is 202 plus a
            # ticket to ask about later.
            if path.startswith("/api/") and path[len("/api/"):] in KINDS:
                kind = path[len("/api/"):]
                # Socket A's positive allowlist: release / control / intake simply do not
                # exist on the remote surface (it is reads · opinion verdicts · static
                # demo). 404, not 403: the surface does not have them.
                if self.server.policy.remote and kind not in REMOTE_KINDS:
                    return self._err(404, "no such endpoint")
                try:
                    payload = json.loads(body or b"{}")
                except ValueError:
                    return self._err(400, "body must be valid JSON")
                try:
                    clean, sensitive = validate(kind, payload)
                except Invalid as exc:
                    return self._err(400, str(exc))
                # The remote credential boundary. A returns-bearing / setup-shaped verdict
                # is loopback-only unless the transport is end-to-end encrypted — a
                # structural check on the returns/tasks keys, never the _is_sensitive
                # heuristic (whose false negative would be a live key on a plaintext edge).
                if (self.server.policy.remote
                        and not self.server.policy.allow_credentials
                        and remote_carries_payload(clean)):
                    return self._err(403, "returns-bearing / setup verdicts are "
                                     "loopback-only; deliver this from the local console "
                                     "or over a Tailscale transport")
                try:
                    message_id = daemon.inbox.append(kind, clean, sensitive=sensitive)
                except OSError as exc:
                    log("inbox append failed for kind=%s: %s" % (kind, exc))
                    return self._err(500, "could not durably record the message")
                if sensitive:
                    # Never log the body. The mode is checked because this file now
                    # holds a live credential until the orchestrator moves it to the
                    # secret store and unlinks it.
                    daemon.warn(verify_mode(os.path.join(
                        daemon.paths.inbox, message_id + ".json"), 0o600))
                    log("accepted %s %s (carries a sensitive value)" % (kind, message_id))
                else:
                    log("accepted %s %s" % (kind, message_id))
                return self._send(202, json.dumps(
                    {"ticket": message_id, "kind": kind}).encode(),
                    extra={"Location": "/api/requests/" + message_id})

            return self._err(404, "no such endpoint")

    return Handler


KINDS = ("verdict", "intake", "control", "release")


def resolve_request(index, ticket):
    """Where one ticket has got to, from the anchors alone.

    Note the watermark case: a consumed message is eventually GC'd off the inbox AND
    pruned out of the consumed-set, so an id that has fallen below the watermark is
    absent from both while being the most thoroughly consumed of all. Reading that
    absence as "unknown" would tell a human their verdict vanished.
    """
    for dl in index.get("dead_letters") or []:
        if (dl or {}).get("message_id") == ticket:
            return {"ticket": ticket, "status": "dead-letter",
                    "reason": dl.get("reason")}
    item = (index.get("promoted") or {}).get(ticket)
    if item:
        return {"ticket": ticket, "status": "applied", "item_ref": item}
    if ticket in (index.get("consumed") or []):
        return {"ticket": ticket, "status": "applied"}
    if ticket in (index.get("queued") or []):
        return {"ticket": ticket, "status": "queued"}
    through = index.get("consumed_through")
    if through and ticket <= through:
        return {"ticket": ticket, "status": "applied"}
    return {"ticket": ticket, "status": "unknown"}


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
    ap.add_argument("cmd", choices=["ensure", "serve", "stop", "status", "park", "unpark"])
    ap.add_argument("--workflow-dir", default=".workflow")
    ap.add_argument("--idle-timeout", type=int, default=DEFAULT_IDLE_TIMEOUT,
                    help="seconds with no request AND no open checkpoint before self-shutdown")
    # park/unpark only. The record itself arrives on STDIN as JSON rather than as a wall
    # of flags: `request` is a nested, judgment-rich object the orchestrator composes, and
    # flattening it into argv would both mangle it and put a checkpoint body in a process
    # listing. What stays a flag is what this script decides rather than carries.
    ap.add_argument("--id", help="park/unpark: the ticket id (park: only if the record omits it)")
    ap.add_argument("--summary", help="park: the one-line mirror label "
                                      "(default: derived from checkpoint.request.what)")
    ap.add_argument("--deadline", help="park: absolute ISO deadline "
                                       "(default: now + config.checkpoint.deadline_hours)")
    args = ap.parse_args(argv)

    paths = Paths(args.workflow_dir)
    # Neither park nor unpark touches the daemon: writing the record IS the signal, and
    # the daemon discovers it on its own next scan.
    if args.cmd == "park":
        try:
            rec = json.load(sys.stdin)
        except ValueError as exc:
            raise SystemExit("park reads the parked-ticket record from stdin as JSON: %s" % exc)
        if isinstance(rec, dict) and args.id and not rec.get("ticket_id"):
            rec["ticket_id"] = args.id
        try:
            res = write_park(paths, rec, args.summary, args.deadline)
        except Invalid as exc:
            raise SystemExit("park refused: %s" % exc)
        print(json.dumps(res, indent=1))
        return 0
    if args.cmd == "unpark":
        if not args.id:
            raise SystemExit("unpark needs --id <ticket_id>")
        try:
            res = remove_park(paths, args.id)
        except Invalid as exc:
            raise SystemExit("unpark refused: %s" % exc)
        print(json.dumps(res, indent=1))
        return 0
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
        away = h.get("away") or {}
        if away:
            chan = "webhook" if away.get("webhook") else (
                "desktop-only (best-effort)" if away.get("desktop") else "NONE — poll the console")
            print("  away channel: %s" % chan)
            if away.get("consecutive_failures"):
                print("  away channel FAILING: %d in a row (%s)"
                      % (away["consecutive_failures"], away.get("last_error")))
        runner = h.get("runner") or {}
        if runner.get("enabled"):
            state = ("HARD-STOPPED — a human must intervene" if runner.get("hard_stopped")
                     else "relaunch in flight" if runner.get("in_flight")
                     else "armed")
            print("  runner: enabled (%s)" % state)
            if runner.get("consecutive_noprogress"):
                print("  runner NO-PROGRESS: %d relaunch(es) in a row (%s)"
                      % (runner["consecutive_noprogress"], runner.get("last_error")))
            if runner.get("workspace_trusted") is False:
                print("  runner WARNING: workspace NOT trusted — a relaunch would ignore "
                      "the allowlist and stall; run /start interactively once to trust it")
            if runner.get("wsl"):
                print("  runner WARNING: WSL kills the daemon with the last terminal — "
                      "no overnight resume unless .wslconfig vmIdleTimeout=-1")
        remote = h.get("remote") or {}
        if remote.get("enabled"):
            print("  remote socket: %s on port %s (transport=%s, credentials=%s)"
                  % ("BOUND" if remote.get("bound") else "NOT BOUND",
                     remote.get("port"), remote.get("transport"),
                     "yes" if remote.get("allow_credentials") else "no"))
            if not remote.get("public_url"):
                print("  remote WARNING: no public_url set (pairing link + host "
                      "allowlist need it)")
        for w in h.get("warnings", []):
            print("  WARNING: %s" % w)
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())

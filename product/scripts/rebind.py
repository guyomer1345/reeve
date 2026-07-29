#!/usr/bin/env python3
"""Bind a project's RUNTIME half to THIS machine — the arithmetic behind `/rebind`.

A workflow project spans two halves. The durable half (`handoff.md`, `backlog.md`,
`config.json`, `items/`, `docs/`) is committed, carries no absolute paths, and moves
between machines for free. The runtime half — `state.json`, the bus record and locks,
`parked/`, `inbox/`, `outbox/`, `secrets/`, the remote token — is deliberately
gitignored and lives at a machine-local absolute path recorded in
`.workflow/runtime.json`. Move the project to another machine (or rebuild the one it
was on) and that pointer names a directory that no longer exists. Every detector in
the system reports this correctly; until now, nothing repaired it.

This runner is the repair's arithmetic — probe, validate, classify, write the pointer,
stamp the root, enumerate what was lost. The JUDGMENT half (what the loss means, what
to re-elicit from the human, how to reconcile the loop position) belongs to
`commands/rebind.md`, because it needs a conversation. Same split as `/start`'s
install step and `/update`'s reconcile: anything mechanical and error-prone ships
FIXED and unit-tested rather than described to a model in prose.

  check    read-only dry run — classify and report, touch nothing
  apply    re-bind a moved project — and a NO-OP on a healthy install
  bind     the FIRST bind, for `/start` step 3 — same arithmetic, no loss accounting

Six classifications:

  NOT-STARTED       no `.workflow/` — this is a `/start` situation, not a rebind
  HEALTHY           already bound to this machine; `apply` writes nothing
  RE-POINT          a surviving tree was found — LOSSLESS, just fix the pointer
  ADOPT-IN-PLACE    no pointer, runtime files under `.workflow/` — confirm or relocate
  RE-CREATE         nothing survived — rebuild the shape, itemize the real losses
  BIND              `bind` only: a project being started, so nothing was ever here

`bind` and `apply` differ in exactly one place, and it is not mechanical: on a fresh
scaffold there is nothing to have lost and no loop position to recover, so filing
"lost in a machine move" issues against a project on its first minute would be a lie
the backlog then carries. Same probe, same derivation, same mount floor, same stamp.

`apply` never overwrites an existing runtime file. That is what makes it idempotent
and safe to re-run: it creates what is absent and repoints what is dead, and a healthy
install is a fixed point.

Stdlib only, like everything else that ships.
"""
import argparse
import json
import os
import re
import shutil
import socket
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bus  # noqa: E402

# What makes a directory look like a runtime tree rather than an empty coincidence.
# `isdir()` alone is how a stray directory gets adopted; this is the second question.
RUNTIME_MEMBERS = ("state.json", "bus.json", "alerts.json", "remote_token",
                   "parked", "inbox", "outbox", "secrets", bus.RUNTIME_STAMP)

# The runtime tree's shape, recreated when nothing survived. `bus.json`, `bus.lock`
# and `orchestrator.lock` are deliberately NOT here: they are liveness artifacts a
# running daemon and a live session create for themselves, and a stale copy of either
# is worse than an absent one.
RUNTIME_DIRS = ("parked", "inbox", "outbox", "secrets")

HOME_PREFIX_RE = re.compile(r"^(/home/[^/]+|/Users/[^/]+|/root)(/.*)?$")

BACKLOG_SECTION = "## Rebind losses (machine move)"


# --- probing ----------------------------------------------------------------
def rehome(path):
    """The old path with THIS machine's `$HOME` swapped in for the old one.

    This one rule is the whole difference between a lossless re-point and a lossy
    re-create for the most common machine move there is — a rebuild that renames the
    user. The incident that opened Phase 7 was exactly this shape
    (`/home/guy` -> `/home/guyo`): same tree, same layout, unreachable only because of
    the prefix. Had the rebuild renamed the home rather than destroying it, this
    candidate alone would have recovered it with nothing lost.
    """
    m = HOME_PREFIX_RE.match(path or "")
    if not m:
        return None
    home = os.path.abspath(os.path.expanduser("~"))
    if m.group(1) == home:
        return None  # already this machine's home — the literal candidate covers it
    tail = (m.group(2) or "").lstrip("/")
    return os.path.join(home, tail) if tail else home


def runtime_members(root):
    return [m for m in RUNTIME_MEMBERS if os.path.exists(os.path.join(root, m))]


def validate(root, project_root):
    """Is `root` a runtime tree THIS project may bind to? -> (ok, why)."""
    if not root or not os.path.isdir(root):
        return False, "does not exist"
    stamp = bus.read_stamp(root)
    bound = (stamp or {}).get("project_path")
    if bound and os.path.abspath(bound) != os.path.abspath(project_root):
        return False, "bound to another project (%s)" % bound
    found = runtime_members(root)
    if not found:
        return False, "exists but holds no runtime files"
    if bus.mount_honours_modes(root) is False:
        return False, "on a filesystem that does not honour file modes"
    return True, "carries %s" % ", ".join(found)


# --- classification ---------------------------------------------------------
def plan(project_root, fresh=False):
    """Read-only. Returns the whole verdict as data; `check` prints it, `apply` acts
    on it. Keeping them one function is what makes the dry run TRUSTWORTHY — `check`
    cannot report a different classification than `apply` will use."""
    project_root = os.path.abspath(os.path.expanduser(project_root))
    workflow = os.path.join(project_root, ".workflow")
    out = {
        "project_root": project_root,
        "workflow_dir": workflow,
        "host": socket.gethostname(),
        "classification": None,
        "pointer": {"present": False, "runtime_root": None, "exists": False},
        "candidates": [],
        "target": None,
        "write_pointer": False,
        "relocate_from": None,
        "actions": [],
        "losses": [],
        "reelicit": [],
        "notes": [],
    }
    if not os.path.isdir(workflow):
        out["classification"] = "NOT-STARTED"
        out["notes"].append(
            "no .workflow/ under %s — this project was never started here. The command "
            "is /start, not /rebind." % project_root)
        return out

    canonical = bus.runtime_root_for(project_root)
    pointer_path = os.path.join(workflow, "runtime.json")
    old = None
    try:
        with open(pointer_path) as fh:
            old = json.load(fh).get("runtime_root")
    except FileNotFoundError:
        pass
    except (OSError, ValueError) as exc:
        out["notes"].append("runtime.json is unreadable (%s) — treated as absent." % exc)
    if old:
        old = os.path.abspath(os.path.expanduser(old))
        out["pointer"] = {"present": True, "runtime_root": old,
                          "exists": os.path.isdir(old)}

    if old:
        return _plan_with_pointer(out, project_root, workflow, old, canonical, fresh)
    return _plan_without_pointer(out, project_root, workflow, canonical, fresh)


def _plan_with_pointer(out, project_root, workflow, old, canonical, fresh):
    """A pointer exists. Either it still resolves, or we go looking."""
    ok, why = validate(old, project_root)
    if ok:
        out["classification"] = "HEALTHY"
        out["target"] = old
        out["notes"].append("runtime tree at %s is intact and bound to this project "
                            "(%s)." % (old, why))
        if bus.read_stamp(old) is None:
            out["actions"].append("stamp %s with this project's identity (an install "
                                  "made before stamps existed)" % old)
        return out

    # Probe, in order. Cheapest and most likely first; the canonical path last,
    # because a project that was never bound by this package version has none.
    seen = []
    for path, source in ((old, "the pointer's literal path"),
                         (rehome(old), "the pointer's path with this machine's $HOME"),
                         (canonical, "the canonical derived location")):
        if not path or path in seen:
            continue
        seen.append(path)
        cok, cwhy = validate(path, project_root)
        out["candidates"].append({"path": path, "source": source,
                                  "valid": cok, "why": cwhy})
        if cok and out["target"] is None:
            out["target"] = path

    if out["target"]:
        out["classification"] = "RE-POINT"
        out["write_pointer"] = out["target"] != workflow
        out["actions"].append("point .workflow/runtime.json at %s" % out["target"])
        out["actions"].append("stamp %s with this project's identity" % out["target"])
        out["notes"].append(
            "LOSSLESS — a surviving runtime tree was found; only the pointer was wrong.")
        return out

    # Nothing survived. The pointer's existence is itself evidence that /start judged
    # this repo's mount unable to hold the tree, so re-create relocated, not in place.
    return _plan_recreate(out, project_root, workflow, canonical, True, fresh)


def _plan_without_pointer(out, project_root, workflow, canonical, fresh):
    """No pointer. Absent means "no relocation happened" — true on a filesystem that
    can hold the tree, and the SILENT mis-bind on one that cannot."""
    honours = bus.mount_honours_modes(workflow)
    present = runtime_members(workflow)
    if present and honours is not False:
        out["classification"] = "HEALTHY"
        out["target"] = workflow
        out["notes"].append(
            "no pointer and the runtime tree sits under .workflow/ on a filesystem "
            "that honours file modes — the local case. Correct as-is; nothing to write.")
        if honours is None:
            out["notes"].append(
                "the mount could not be measured (unwritable tree?), so this is "
                "'no evidence of a problem', not 'proven sound'.")
        return out

    if present and honours is False:
        out["classification"] = "ADOPT-IN-PLACE"
        out["target"] = canonical
        out["relocate_from"] = workflow
        out["write_pointer"] = True
        out["actions"].append(
            "move the runtime files out of .workflow/ to %s and write the pointer"
            % canonical)
        out["notes"].append(
            "the runtime tree is on a filesystem that does NOT honour file modes: a "
            "0600 create comes back world-readable. The capability token, inbox "
            "messages carrying credentials, and secrets/ are exposed to every user on "
            "this machine. This is the silent mis-bind — a clone under a "
            "Windows-interop or network mount gets it with no pointer and no warning.")
        return out

    # No pointer and no runtime files: a fresh scaffold, a fresh clone, or a tree that
    # was never here.
    return _plan_recreate(out, project_root, workflow, canonical,
                          honours is False, fresh)


def _plan_recreate(out, project_root, workflow, canonical, relocated, fresh):
    out["classification"] = "BIND" if fresh else "RE-CREATE"
    out["target"] = canonical if relocated else workflow
    out["write_pointer"] = relocated
    out["actions"].append("create the runtime tree at %s (0700)" % out["target"])
    if relocated:
        out["actions"].append("stamp it with this project's identity and point "
                              ".workflow/runtime.json at it")
    out["actions"].append("create %s/ and alerts.json" % "/, ".join(RUNTIME_DIRS))
    if fresh:
        out["notes"].append(
            "FIRST BIND — the project is being started, so nothing was ever here to "
            "lose. state.json is left alone: the /start motion publishes it at every "
            "stage boundary, which is a position this runner has no business guessing.")
        return out
    out["actions"].append(
        "write a PLACEHOLDER state.json — status=idle, no current_item, and a note "
        "saying the position was not recovered")

    out["reelicit"] = [
        "The loop position. state.json is a placeholder: reconcile it against "
        ".workflow/handoff.md and `git log <base_sha>..HEAD` before resuming, and "
        "rewrite it. An idle state.json will otherwise let prioritize re-pick work "
        "the handoff says is parked.",
        "The console daemon. bus.json / bus.lock / orchestrator.lock are liveness "
        "artifacts, not state — restart the daemon rather than reconstructing them "
        "(`python3 .claude/scripts/bus.py ensure --workflow-dir .workflow`).",
        "The remote pairing token, IF this project uses the remote socket. It is "
        "re-minted on the next daemon start, so the phone must be re-paired and any "
        "tunnel re-pointed — the URL changed with the machine.",
        "`.workflow/statusline.delegate`, if /start ever found a pre-existing user "
        "statusline to delegate to. It is gitignored and did not travel.",
    ]
    out["losses"] = [
        {
            "title": "rebind: parked checkpoints lost in a machine move",
            "kind": "bug", "severity": "high",
            "description":
                "parked/<id>.json did not survive the move to %s. Every open "
                "checkpoint's body is gone — its question, its deadline, and any "
                "credential or payload a human had already returned. handoff.md's "
                "prose Parked section is the only surviving trace; re-open each "
                "checkpoint it names from that prose." % out["host"],
        },
        {
            "title": "rebind: outbox lost in a machine move",
            "kind": "bug", "severity": "medium",
            "description":
                "outbox/ did not survive the move to %s. Any outward action queued "
                "and not yet released (a push, a `gh issue create`) is gone. Nothing "
                "was executed twice — the queue simply emptied — but a pending "
                "action will never fire; re-queue anything the backlog still expects."
                % out["host"],
        },
        {
            "title": "rebind: secret store lost in a machine move",
            "kind": "bug", "severity": "high",
            "description":
                "secrets/ did not survive the move to %s. Credentials a human handed "
                "over at a setup checkpoint are gone and must be re-elicited. Absence "
                "is not detectable by inspection (an empty secrets/ is indistinguishable "
                "from a project that needs none), so this entry IS the record — "
                "point-of-use failure is the only other signal." % out["host"],
        },
    ]
    out["notes"].append(
        "LOSSY — no surviving runtime tree was found. The durable half (handoff, "
        "backlog, config, items, docs) is committed and intact; what follows is "
        "everything that was runtime-only.")
    return out


# --- applying ---------------------------------------------------------------
def apply(project_root, fresh=False):
    """Act on the plan. A no-op on a healthy install, and never an overwrite."""
    p = plan(project_root, fresh=fresh)
    cls = p["classification"]
    p["applied"] = []
    if cls == "NOT-STARTED":
        return p, 2
    if cls == "HEALTHY":
        if (p["target"] != p["workflow_dir"] and bus.read_stamp(p["target"]) is None):
            bus.write_stamp(p["target"], p["project_root"])
            p["applied"].append("stamped %s (an install made before stamps existed)"
                                % p["target"])
        return p, 0

    target = p["target"]
    os.makedirs(target, exist_ok=True)
    try:
        os.chmod(target, 0o700)
    except OSError:
        pass

    # Refuse to land the tree somewhere that cannot hold it. This is the same floor
    # Paths enforces on resolution; a repair that re-creates the original exposure is
    # not a repair.
    if bus.mount_honours_modes(target) is False:
        p["error"] = ("%s does not honour file modes — refusing to put the capability "
                      "token and secrets/ there. Set XDG_STATE_HOME to a local "
                      "filesystem and re-run." % target)
        return p, 2

    if p["relocate_from"]:
        for name in runtime_members(p["relocate_from"]):
            src = os.path.join(p["relocate_from"], name)
            dst = os.path.join(target, name)
            if os.path.exists(dst):
                p["applied"].append("kept existing %s (never overwritten)" % dst)
                continue
            shutil.move(src, dst)
            p["applied"].append("moved %s -> %s" % (src, dst))

    for name in RUNTIME_DIRS:
        d = os.path.join(target, name)
        if not os.path.isdir(d):
            os.makedirs(d, exist_ok=True)
            p["applied"].append("created %s/" % d)
        try:
            os.chmod(d, 0o700)
        except OSError:
            pass

    alerts = os.path.join(target, "alerts.json")
    if not os.path.exists(alerts):
        bus.atomic_write(alerts, "{}\n", mode=0o600)
        p["applied"].append("created %s" % alerts)

    state = os.path.join(target, "state.json")
    if cls != "BIND" and not os.path.exists(state):
        bus.atomic_write(state, json.dumps({
            "status": "idle",
            "node": "prioritize",
            "current_item": None,
            "wave": None,
            "note": ("placeholder written by /rebind on %s at %s — the loop position "
                     "was NOT recovered; reconcile against .workflow/handoff.md before "
                     "resuming" % (p["host"], bus.now_iso())),
        }, indent=2) + "\n", mode=0o600)
        p["applied"].append("wrote placeholder %s" % state)

    # Only a RELOCATED root needs an identity. When the tree lives inside .workflow/
    # the binding is true by construction — there is no pointer to be wrong, nothing
    # else can be at that path, and a stamp there would only be one more gitignore
    # entry and one more committed-tree surprise for every install on a native FS.
    if target != p["workflow_dir"]:
        bus.write_stamp(target, p["project_root"])
        p["applied"].append("stamped %s" % target)

    pointer = os.path.join(p["workflow_dir"], "runtime.json")
    if p["write_pointer"]:
        bus.atomic_write(pointer, json.dumps({"runtime_root": target}) + "\n",
                         mode=0o600)
        p["applied"].append("pointed %s at %s" % (pointer, target))
    elif os.path.exists(pointer) and target == p["workflow_dir"]:
        os.unlink(pointer)
        p["applied"].append("removed the stale pointer %s (the runtime tree is "
                            "in-place)" % pointer)

    filed = file_losses(p)
    p["applied"].extend(filed)
    return p, 0


def file_losses(p):
    """Record each loss as a typed `issue` entry in `backlog.md`.

    A printed loss report is the same failure mode as a prose parked mirror: a
    durability that depends on a human remembering. `backlog.md` is already the live
    OPEN queue and is committed, so nothing new is adopted as a source. The entries go
    in through the `issue` SHAPE on purpose — a local issue with no `github_ref` is
    closed by its backlog done-flip, which is a shape `prioritize` already collects.
    Free prose would match neither GC rule and every machine move would leave permanent
    sediment.

    Idempotent on the title while an entry is still OPEN, so a re-run of `apply` does
    not duplicate — and a genuinely second machine move, after the first was closed,
    files again.
    """
    if not p["losses"]:
        return []
    backlog = os.path.join(p["workflow_dir"], "backlog.md")
    try:
        with open(backlog) as fh:
            text = fh.read()
    except OSError:
        return ["could not read %s — losses NOT filed; report them to the human"
                % backlog]
    lines, filed = [], []
    for loss in p["losses"]:
        if ("- [ ] **%s**" % loss["title"]) in text:
            continue
        lines.append(
            "- [ ] **%s** — `kind=%s` · `severity=%s` · `source=rebind:%s:%s`\n  %s"
            % (loss["title"], loss["kind"], loss["severity"], p["host"],
               bus.now_iso(), loss["description"]))
        filed.append("filed backlog issue: %s" % loss["title"])
    if not lines:
        return ["backlog already carries every loss entry — nothing re-filed"]
    if BACKLOG_SECTION in text:
        text = text.replace(BACKLOG_SECTION,
                            BACKLOG_SECTION + "\n" + "\n".join(lines), 1)
    else:
        text = text.rstrip("\n") + "\n\n" + BACKLOG_SECTION + "\n" + "\n".join(lines) + "\n"
    bus.atomic_write(backlog, text, mode=0o644)
    return filed


# --- reporting --------------------------------------------------------------
def render(p, mode):
    L = []
    L.append("%s  %s" % (p["classification"], p["project_root"]))
    ptr = p["pointer"]
    if ptr["present"]:
        L.append("  pointer: %s  (%s)"
                 % (ptr["runtime_root"], "exists" if ptr["exists"] else "GONE"))
    else:
        L.append("  pointer: none")
    if p["target"]:
        L.append("  target:  %s" % p["target"])
    for c in p["candidates"]:
        L.append("  probe %-8s %s\n           %s — %s"
                 % ("OK" if c["valid"] else "no", c["path"], c["source"], c["why"]))
    for n in p["notes"]:
        L.append("  note: %s" % n)
    if p.get("error"):
        L.append("  ERROR: %s" % p["error"])
    for a in (p["applied"] if mode == "apply" else p["actions"]):
        L.append("  %s %s" % ("did:" if mode == "apply" else "would:", a))
    for r in p["reelicit"]:
        L.append("  re-elicit: %s" % r)
    for loss in p["losses"]:
        L.append("  LOST [%s/%s] %s\n           %s"
                 % (loss["kind"], loss["severity"], loss["title"], loss["description"]))
    return "\n".join(L)


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="bind a project's runtime half to this machine")
    ap.add_argument("cmd", choices=["check", "apply", "bind"])
    ap.add_argument("--project-root", default=".")
    ap.add_argument("--json", action="store_true",
                    help="emit the plan as JSON instead of prose")
    args = ap.parse_args(argv)

    if args.cmd == "check":
        p, code = plan(args.project_root), 0
        p["applied"] = []
        if p["classification"] == "NOT-STARTED":
            code = 2
    else:
        p, code = apply(args.project_root, fresh=(args.cmd == "bind"))

    print(json.dumps(p, indent=2) if args.json
          else render(p, "check" if args.cmd == "check" else "apply"))
    return code


if __name__ == "__main__":
    sys.exit(main())

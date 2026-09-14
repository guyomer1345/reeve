#!/usr/bin/env python3
"""The receipt that turns the autonomy floor from a CONSULTATION into an enforcement.

`check_autonomy_floor.py` answers whether a spec change crosses the goal-preserving floor, and
`loop.md` tells the orchestrator to run it before acting on a goal-affecting decision. That is a
consultation: the whole premise of the floor is that a loop grading its own decisions drifts
toward "not fundamental", so **a loop that simply does not run the floor is precisely the case
the floor exists for.** Nothing downstream noticed.

WHY THE OBVIOUS BACKSTOP WAS NOT ENOUGH. A commit-time run of the floor blocks every commit that
crosses it -- including the legitimate ones, where a human WAS asked and DID approve. A gate with
no escape gets switched off, so the escape is the design problem, not the gate. This file is the
escape: a durable receipt saying *a human approved this*.

BOUND TO CONTENT, NOT TO A LABEL, WHICH IS THE WHOLE MECHANISM. A receipt that merely said
"approved" could be written once and would then licence every later spec change forever -- and
worse, it would licence editing the spec AFTER approval, which is the exact move the floor
exists to catch. So the receipt stamps a **digest of the approved spec**, and the gate accepts it
only when the digest matches the spec **as staged**. Approve v1 and commit v2 and it blocks
again, correctly, with no way to talk it round. This is `forecast.py freeze`'s trick applied to a
second artifact: a digest is what makes an approval real rather than a label.

WHAT IT DOES NOT CLAIM. It proves a human saw and approved *this text*. It does not prove they
understood it, and it says nothing about a code change that abandons a locked behaviour without
touching the spec -- the floor's own stated blind spot, which belongs to the alignment scan.

FAIL DIRECTION. Every failure to compute -- an unreadable receipt, a spec that cannot be read,
a digest that will not resolve -- lands on BLOCKED. The floor already fails closed for the same
reason, and an escape hatch that opens when it malfunctions is not an escape hatch.
"""
import argparse
import hashlib
import json
import os
import secrets
import subprocess
import sys

RECEIPT_REL = os.path.join(".workflow", "spec-approval.json")
SPEC_REL = os.path.join("docs", "spec.md")


def spec_digest(text):
    """The approved-content digest. Over BYTES of the whole file, deliberately: a digest of
    "just the locked parts" would need the same parser the floor uses, and two parsers that must
    agree forever is how a gate acquires a silent disagreement."""
    if isinstance(text, str):
        text = text.encode("utf-8")
    return hashlib.sha256(text).hexdigest()


def _spec_path(project_root, spec_rel=None):
    return os.path.join(project_root, spec_rel or SPEC_REL)


def staged_spec(project_root, spec_rel=None):
    """The spec as it will be COMMITTED (the staged blob), not as it sits in the tree.

    The distinction is the point: a gate reading the worktree could be satisfied by a file the
    commit does not contain. Falls back to the worktree only when nothing is staged for the
    path, which is the ordinary case where the spec is unchanged.
    """
    rel = spec_rel or SPEC_REL
    try:
        p = subprocess.run(["git", "-C", project_root, "show", ":" + rel.replace(os.sep, "/")],
                           capture_output=True)
        if p.returncode == 0:
            return p.stdout
    except OSError:
        return None
    try:
        with open(_spec_path(project_root, spec_rel), "rb") as fh:
            return fh.read()
    except OSError:
        return None


def read_receipt(project_root):
    try:
        with open(os.path.join(project_root, RECEIPT_REL), encoding="utf-8") as fh:
            val = json.load(fh)
    except (OSError, ValueError):
        return None
    return val if isinstance(val, dict) else None


def record(project_root, ticket_id, spec_rel=None):
    """Write the receipt for a spec the human has just approved.

    Stamps the digest of the spec AS IT IS NOW. Run it at the moment the approval is applied and
    not before: a receipt written ahead of the edit would licence whatever the edit turns out to
    be, which is the failure this file is built to prevent.
    """
    body = staged_spec(project_root, spec_rel)
    if body is None:
        return None
    # NO `token` FIELD, and its absence is load-bearing rather than tidy. This file is
    # COMMITTED -- it must ride the commit it authorises -- and `guard.sh`'s secret scan blocks
    # any staged `token:` followed by 12+ key-shaped characters. A checkpoint ticket string is
    # comfortably longer, so a receipt carrying one could never be staged: two package rules
    # with no reachable compliant state, found on a live drive. The fix is here rather than in
    # the scan, deliberately -- a false positive on a token-shaped field is far cheaper than a
    # missed credential, so the scan does not move. `ticket_id` already carries the provenance;
    # the correlation token is the DRAIN's key and is meaningless once the verdict is applied.
    rec = {"spec_sha256": spec_digest(body), "ticket_id": ticket_id,
           "spec_path": (spec_rel or SPEC_REL).replace(os.sep, "/")}
    path = os.path.join(project_root, RECEIPT_REL)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(rec, fh, indent=1, sort_keys=True)
        fh.write("\n")
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)
    return rec


def _floor_crosses(project_root, scripts_dir):
    """(crossed, ok). `ok` False ⇒ the floor could not be run, which the caller treats as
    crossed -- the floor's own fail-closed rule, not re-decided here."""
    gate = os.path.join(scripts_dir, "check_autonomy_floor.py")
    if not os.path.isfile(gate):
        return True, False
    try:
        p = subprocess.run([sys.executable, gate, "--project-root", project_root],
                           capture_output=True, text=True)
    except OSError:
        return True, False
    return p.returncode != 0, True


def check(project_root, scripts_dir, do_park=False):
    """The commit gate. Returns (ok, message).

    `do_park` is opt-in rather than always-on so the gate stays READ-ONLY for every other
    caller -- `align`, a dry run, a test -- and the one caller that wants the side effect
    (`checks.sh`, the commit path) asks for it at the call site where it is visible.
    """
    crossed, ran = _floor_crosses(project_root, scripts_dir)
    if not crossed:
        return True, "autonomy floor: clear — no approval receipt needed"
    if not ran:
        return False, ("autonomy floor could not be run, so this commit cannot be shown to be "
                       "goal-preserving. Fix the gate or route the change to a human.")

    body = staged_spec(project_root)
    if body is None:
        return False, "the floor fired but the staged spec could not be read — blocking"
    want = spec_digest(body)

    rec = read_receipt(project_root)
    if not rec:
        msg = (
            "BLOCKED: this change crosses the autonomy floor (it touches a `locked` element, "
            "weakens a commitment marker, or alters an acceptance criterion) and carries no "
            "approval receipt.\n"
            "  This is not a formality: the floor exists because a loop grading its own "
            "decisions drifts toward 'not fundamental'.")
        return False, msg + _routed(project_root, scripts_dir, want, do_park)
    got = rec.get("spec_sha256")
    if got != want:
        msg = (
            "BLOCKED: an approval receipt exists but it is for DIFFERENT spec content "
            "(approved %s…, staging %s…).\n"
            "  The spec changed after it was approved, so the approval does not cover this "
            "commit — editing after approval is exactly what the digest is here to catch."
            % (str(got)[:12], want[:12]))
        return False, msg + _routed(project_root, scripts_dir, want, do_park)
    return True, ("autonomy floor: crossed, and covered by the approval receipt for ticket %s"
                  % rec.get("ticket_id", "?"))


# ============================================================== the park

# The gate BLOCKS and has always routed nowhere. Its message said "raise a checkpoint, get a
# verdict" -- prose, addressed to whatever was running, and a real unattended drive read it,
# wrote the withheld change to `items/<id>/spec-delta.md`, left a note in `backlog.md` and
# carried on. The ask had no durable owner: `parked/` is what `clear_safe`, the console and the
# `handoff.md` mirror all read, and none of them knew a human was needed. So the gate raises the
# park itself. It cannot be skipped, because it happens inside the refusal.
PARK_KIND = "spec"
PARKED_REL = os.path.join(".workflow", "parked")


def park_id(digest):
    """Keyed on the SPEC DIGEST, which makes re-parking idempotent for free.

    `checks.sh` runs on every commit attempt, so a change that is blocked and retried would
    otherwise open a checkpoint per attempt and bury the human in identical cards. Keying on
    content also gets the other half right without a second rule: edit the spec and it is a
    DIFFERENT ask, correctly opening its own ticket, because the text a human would be
    approving is not the text the last ticket quoted.
    """
    return "SPEC-%s" % digest[:12]


def already_parked(project_root, ticket_id):
    return os.path.exists(os.path.join(project_root, PARKED_REL, ticket_id + ".json"))


def park(project_root, scripts_dir, digest, item=None):
    """-> (ticket_id, problem). Composes the record and hands it to `bus.py park`, which owns
    the runtime root, the deadline and the mirror -- this file does not learn those.

    FAIL SOFT, and that direction is the opposite of everything else in here. The gate's job is
    to BLOCK, and it has already decided to; parking is how the block reaches a person. If the
    runtime root is unreachable -- the `/rebind` case -- a park that raised would convert a
    clear, actionable refusal into a crash, and the commit would still be blocked but nobody
    would be told why. So a failure to park is reported beside the refusal, never instead of it.
    """
    tid = park_id(digest)
    if already_parked(project_root, tid):
        return tid, None
    runner = os.path.join(scripts_dir, "bus.py")
    if not os.path.isfile(runner):
        return tid, "bus.py is not installed beside this gate"
    rec = {
        "ticket_id": tid,
        "token": secrets.token_urlsafe(16),
        "loop_position": "blocked at the commit gate by the autonomy floor",
        "checkpoint": {
            "kind": PARK_KIND,
            "request": {
                "kind": PARK_KIND,
                "what": ("A spec change crosses the autonomy floor and needs your approval"
                         + (" (item %s)" % item if item else "")
                         + ". The change is staged in `docs/spec.md`; approve it, edit it, or "
                           "reject it."),
                "expected": ("approve → the change stands and the receipt is recorded · "
                             "changes → your edits become the change · "
                             "reject → the change is discarded and the item continues under "
                             "the spec as it stands"),
                "blocking": True,
            },
        },
        "predicted_outcome": "approve",
    }
    try:
        run = subprocess.run([sys.executable, runner, "park", "--workflow-dir",
                              os.path.join(project_root, ".workflow")],
                             input=json.dumps(rec), capture_output=True, text=True, timeout=60)
    except Exception as exc:
        return tid, "bus.py park could not be run (%s)" % exc
    if run.returncode != 0:
        tail = (run.stderr or run.stdout or "").strip().splitlines()
        return tid, "bus.py park refused (%s)" % (tail[-1] if tail else "no output")
    return tid, None


def current_item(project_root):
    try:
        with open(os.path.join(project_root, ".workflow", "state.json"), encoding="utf-8") as fh:
            return (json.load(fh) or {}).get("current_item")
    except (OSError, ValueError, AttributeError):
        return None


def _routed(project_root, scripts_dir, digest, do_park):
    """The refusal's tail: what is being done about it, in the same breath as the block.

    Both blocked paths share this because they are the same situation to a human -- a spec
    change nobody has approved -- and they differed only in how they got there.
    """
    if not do_park:
        return ("\n  Route it — raise a `spec` checkpoint, get a verdict, and record it with "
                "`spec_approval.py record --ticket <id>`.")
    tid, problem = park(project_root, scripts_dir, digest, current_item(project_root))
    if problem:
        return ("\n  A `spec` checkpoint could NOT be parked (%s), so this block has not "
                "reached anybody. Raise it by hand, or run /rebind if the runtime root is "
                "gone." % problem)
    return ("\n  Parked as `spec` checkpoint %s — a human has been asked. Answer it at the "
            "console; the verdict resumes the item." % tid)


def _common(ap):
    """The flags that must work on BOTH sides of the subcommand.

    Declared twice on purpose. argparse binds a top-level flag only BEFORE the subcommand, so
    `… check --scripts-dir X` is an error while `… --scripts-dir X check` is fine -- a CLI that
    works in one argument order and not the other is a trap, and this one caught its own caller:
    `checks.sh` wrote the natural order, argparse rejected it, and the gate failed closed on
    every commit. The unit tests missed it because they happened to use the other order, which
    is exactly how a CLI-shaped bug survives a green suite. A shared parent makes both legal.
    """
    ap.add_argument("--project-root", default=argparse.SUPPRESS)
    ap.add_argument("--scripts-dir", default=argparse.SUPPRESS,
                    help="where check_autonomy_floor.py lives (default: beside this file)")
    return ap


def main(argv=None):
    ap = argparse.ArgumentParser(description="The autonomy floor's approval receipt.")
    _common(ap)
    sub = ap.add_subparsers(dest="cmd", required=True)
    rec = _common(sub.add_parser("record", help="stamp the approved spec's digest"))
    rec.add_argument("--ticket", required=True)
    chk = _common(sub.add_parser("check", help="the commit gate (exit 2 = blocked)"))
    chk.add_argument("--park", action="store_true",
                     help="on a block, raise the `spec` checkpoint that asks a human (the "
                          "commit path passes this; every other caller stays read-only)")
    args = ap.parse_args(argv)
    # SUPPRESS keeps an unset flag out of the namespace entirely, so a value given on either
    # side survives instead of the subparser's default overwriting the top-level one with None.
    if not hasattr(args, "project_root"):
        args.project_root = "."
    if not hasattr(args, "scripts_dir"):
        args.scripts_dir = None

    scripts = args.scripts_dir or os.path.dirname(os.path.abspath(__file__))
    if args.cmd == "record":
        r = record(args.project_root, args.ticket)
        if r is None:
            print("spec-approval: cannot read the spec — nothing recorded", file=sys.stderr)
            return 2
        print("spec-approval: recorded %s… for ticket %s"
              % (r["spec_sha256"][:12], r["ticket_id"]), file=sys.stderr)
        return 0

    ok, msg = check(args.project_root, scripts, do_park=getattr(args, "park", False))
    print(msg, file=sys.stderr)
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main())

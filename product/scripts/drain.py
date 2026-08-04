#!/usr/bin/env python3
"""The inbox drain's bookkeeping — the half of the boundary drain that is arithmetic.

The drain is not one thing, and the split matters:

  APPLY is judgment, and stays in the orchestrator's brief. Which parked ticket a
  verdict resumes, whether an ask is worth promoting and at what priority, how a
  rejection routes — none of that is a function of the inputs, and a script that tried
  would be guessing.

  BOOKKEEPING is a pure function of (what is in inbox/, what handoff.md says is
  already consumed). Which messages are new, in what order they apply, what the
  watermark is now, and what may be pruned. There is exactly one right answer, and it
  is checkable.

That line was not drawn by taste. It was measured: driving real sessions against the
brief, the apply half was right every time — ordering, the skip, the dead-letter, every
per-kind anchor — while the bookkeeping half silently produced an UNBOUNDED
consumed-set in two runs of three, because the brief names the watermark once in
passing and never mentions the prune at all. The third run got it right and flagged the
spec as ambiguous. A rule stated only in a decision log is not a rule the consumer
follows; this file is where that rule becomes an artifact a test can hold.

It also does something the orchestrator physically cannot. handoff.md is the durable
resume anchor, and it must be published write-temp → fsync → rename → fsync(dir): a
model holding a text-writing tool has no way to express that, so the durability the
anchor is supposed to have was never actually there.

  list     what to apply, in order, with already-consumed messages skipped
  record   mark ids applied; recompute the watermark; prune; republish handoff.md
  secret   move a returned credential to the secret store without it passing through
           anybody's context, then unlink the message that carried it

Stdlib only. Never deletes an inbox file (that partition belongs to the bus) — with
the one carve-out `secret` implements.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bus import (MESSAGE_ID_RE, Paths, atomic_write, empty_block,  # noqa: E402
                 now_iso, read_handoff_block, read_json, upsert_handoff_block,
                 verify_mode)

# The order is not a preference. Control first, because a reprioritize must be honored
# by the pick this boundary is about to make. Verdicts next, because resuming parked
# work outranks starting new work. Intake before release only so a promoted item exists
# before anything fires against it. Question LAST, and for the same kind of reason: it is
# the only kind that changes no build state, so answering it must never sit in front of
# resuming a parked ticket — a human waiting on an answer is waiting on prose, while a
# loop waiting on a verdict is stopped.
KIND_ORDER = ("control", "verdict", "intake", "release", "question")

# handoff.md is read whole by every cold start, so the dead-letter surface has to be
# bounded like everything else on it. It is NOT pruned by the watermark, though: a
# dead-lettered verdict is the one message a human most needs to be told about, and
# collecting it the moment the watermark passes would erase the notice before it was
# read.
MAX_DEAD_LETTERS = 20


def _stem(path):
    return os.path.basename(path)[:-5]


def list_inbox(paths):
    """Every message currently visible, oldest first.

    Only *.json: an in-flight atomic write is a dot-prefixed .tmp in this same
    directory, and treating one as a message would read a half-written file.
    """
    try:
        names = os.listdir(paths.inbox)
    except OSError:
        return []
    return sorted(n[:-5] for n in names if n.endswith(".json"))


def compute_watermark(visible, consumed, previous):
    """The low-watermark: every message at or below it is consumed.

    Walk the candidates in order and stop at the first unconsumed one — everything
    before it is safely collectable, and nothing at or after it is. A gap is what makes
    this a watermark rather than a cursor: a cursor would skip the gap forever, and the
    bus would delete a message nobody applied.

    The candidates are the visible ids UNION the ones already known consumed, not the
    visible ids alone. A message can legitimately be consumed and already off the disk
    — the sensitive carve-out unlinks one the moment its value reaches the store — and
    computing over the directory alone would let that hole stall the mark permanently
    beneath it.

    An id at or below the CURRENT mark counts as consumed without being in the set,
    and that is not a detail — it is the whole reason the mark is durable. The set is
    pruned against the mark on every pass, so a consumed id lives in `consumed` only
    until the mark passes it and is then dropped as redundant. Reading the set alone
    would therefore find those ids "unconsumed", stop the walk dead on the first one,
    and freeze the watermark forever at the value it already had — the inbox would
    never be collected again. (Found by driving a real session, which records ids one
    at a time exactly as the brief asks: every batch-at-once test passed.)

    It never regresses. Lowering it would un-collect files the bus has already removed,
    and nothing can be waiting below it: the bus issues ids in visibility order and
    floors new ids above this very mark.
    """
    mark = previous or ""
    for mid in sorted(set(visible) | set(consumed)):
        if mid <= mark:
            continue  # implied by the mark; the set has legitimately forgotten it
        if mid not in consumed:
            break
        mark = mid
    return mark or None


def load(paths):
    block = read_handoff_block(paths.handoff)
    visible = list_inbox(paths)
    return block, visible


def cmd_list(paths, args):
    block, visible = load(paths)
    consumed = set(block.get("consumed") or [])
    through = block.get("consumed_through")

    pending = []
    for mid in visible:
        if mid in consumed:
            continue
        # Below the watermark and not in the set means it was applied and pruned; the
        # bus simply has not collected it yet. Re-applying it is exactly the
        # double-promotion the consumed-set exists to stop.
        if through and mid <= through:
            continue
        body = read_json(os.path.join(paths.inbox, mid + ".json"))
        if not isinstance(body, dict):
            pending.append({"message_id": mid, "kind": "unreadable", "body": None,
                            "note": "could not parse — dead-letter it"})
            continue
        kind = body.get("kind")
        entry = {"message_id": mid, "kind": kind}
        sensitive = _sensitive(body)
        entry["sensitive"] = sensitive
        if sensitive:
            # Redact rather than print. The whole point of the secret store is that a
            # returned credential never reaches a log or a transcript, and stdout here
            # is read straight into a model's context. `drain.py secret` moves the
            # value without anybody looking at it.
            entry["body"] = _redact(body)
            entry["note"] = ("carries a sensitive value — apply with "
                             "`drain.py secret --id %s`, never by reading the file" % mid)
        else:
            entry["body"] = body
        pending.append(entry)

    pending.sort(key=lambda e: (KIND_ORDER.index(e["kind"])
                                if e["kind"] in KIND_ORDER else len(KIND_ORDER),
                                e["message_id"]))
    return {
        "pending": pending,
        "pending_count": len(pending),
        "consumed_through": through,
        "consumed_count": len(consumed),
        "visible_count": len(visible),
    }


def _sensitive(body):
    """Does this message carry a credential? Answered by SHAPE, not by a marker.

    This used to walk the payload looking for a `sensitive: true` a composer had to
    remember to set — one boolean gating redaction, the shred/store path, and removal
    from the inbox, all three at once. An entry that conformed perfectly but omitted it
    was printed verbatim into the orchestrator's context and never stored. `returns` now
    MEANS credential, so a non-empty one is the whole answer and no producer can forget
    to say so. `artifacts` is the declared non-credential field and is deliberately NOT
    consulted here — it is meant to be readable.
    """
    v = body.get("verdict")
    if not isinstance(v, dict):
        return False
    if _has_returns(v):
        return True
    return any(_has_returns(t) for t in (v.get("tasks") or []) if isinstance(t, dict))


def _has_returns(obj):
    r = obj.get("returns")
    return isinstance(r, dict) and bool(r)


def _redact(body):
    """Blank every `returns`, and leave `artifacts` alone — that is the point of the
    split. A benign value the orchestrator needs to act on (a webhook URL, a project id)
    stays readable; a credential never is."""
    out = json.loads(json.dumps(body))  # cheap deep copy of plain JSON
    v = out.get("verdict")
    if isinstance(v, dict):
        if v.get("returns") is not None:
            v["returns"] = "<redacted — credential>"
        for t in v.get("tasks") or []:
            if isinstance(t, dict) and t.get("returns") is not None:
                t["returns"] = "<redacted — credential>"
    return out


def publish(paths, block):
    """Rewrite ONLY the machine block, leaving every byte of the prose alone.

    The prose is the orchestrator's message to the next session; these are two authors
    on one file, which works precisely because neither rewrites the other's half.

    The write is atomic AND durable (temp → fsync → rename → fsync(dir)). That is not
    polish: this file is the anchor a cold start rebuilds position from, so a torn or
    unflushed copy is the one failure that loses the loop's place. It is also something
    the orchestrator cannot do for itself — a tool that writes text cannot express a
    rename, let alone a directory fsync.
    """
    try:
        with open(paths.handoff, "r") as fh:
            text = fh.read()
    except OSError:
        text = None
    atomic_write(paths.handoff, upsert_handoff_block(text, block), mode=0o644)


def cmd_record(paths, args):
    block, visible = load(paths)
    consumed = set(block.get("consumed") or [])
    dead = list(block.get("dead_letters") or [])

    applied = list(args.applied or [])
    for spec in args.dead_letter or []:
        mid, _, reason = spec.partition("=")
        mid = mid.strip()
        if not mid:
            raise SystemExit("--dead-letter needs ID=reason")
        applied.append(mid)
        dead = [d for d in dead if (d or {}).get("message_id") != mid]
        dead.append({"message_id": mid, "reason": reason.strip() or "unspecified",
                     "at": now_iso()})

    for mid in applied:
        if not MESSAGE_ID_RE.fullmatch(mid):
            raise SystemExit("%r is not a bus-assigned message id" % mid)
        consumed.add(mid)

    through = compute_watermark(visible, consumed, block.get("consumed_through"))
    # Prune to ids ABOVE the watermark. Everything at or below it is implied by the
    # mark itself, so keeping it would grow this file without bound for no information
    # — this is the step the brief never stated and two of three real runs skipped.
    kept = sorted(m for m in consumed if not through or m > through)

    out = empty_block()
    out["consumed"] = kept
    out["consumed_through"] = through
    out["dead_letters"] = dead[-MAX_DEAD_LETTERS:]
    publish(paths, out)
    return {"recorded": sorted(set(applied)), "consumed_through": through,
            "consumed_kept": len(kept), "dead_letters": len(out["dead_letters"]),
            "pruned": len(consumed) - len(kept)}


def cmd_secret(paths, args):
    """The one place the consumer may delete an inbox message.

    A credential must not sit on a durable queue waiting for a janitor, and it must not
    pass through a context window on its way to the store. So the move and the unlink
    and the record happen here, in one step, with the value never printed.
    """
    mid = args.id
    if not MESSAGE_ID_RE.fullmatch(mid):
        raise SystemExit("%r is not a bus-assigned message id" % mid)
    src = os.path.join(paths.inbox, mid + ".json")
    body = read_json(src)
    if not isinstance(body, dict):
        raise SystemExit("cannot read %s" % src)
    if not _sensitive(body):
        raise SystemExit("%s carries no `returns` — it hands back no credential, so "
                         "apply it normally" % mid)

    v = body.get("verdict") or {}
    payload = {"token": body.get("token"), "message_id": mid, "stored_at": now_iso(),
               "returns": v.get("returns"),
               "tasks": [{"id": t.get("id"), "returns": t.get("returns")}
                         for t in (v.get("tasks") or []) if isinstance(t, dict)]}
    dest = os.path.join(paths.secrets, mid + ".json")
    atomic_write(dest, json.dumps(payload, indent=1) + "\n", mode=0o600)
    warn = verify_mode(dest, 0o600)

    os.unlink(src)  # the carve-out: latency-to-zero must not wait on the bus's GC

    args.applied = [mid]
    args.dead_letter = []
    res = cmd_record(paths, args)
    res.update({"stored": dest, "unlinked": src})
    if warn:
        res["warning"] = warn
    return res


def main(argv=None):
    ap = argparse.ArgumentParser(description="the inbox drain's bookkeeping")
    ap.add_argument("--workflow-dir", default=".workflow")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("list", help="what to apply, in order (already-consumed skipped)")

    rec = sub.add_parser("record", help="mark applied; recompute the watermark; prune")
    rec.add_argument("--applied", nargs="*", default=[], metavar="ID")
    rec.add_argument("--dead-letter", nargs="*", default=[], metavar="ID=reason",
                     help="applied, but it resolved to nothing — surfaced to the human")

    sec = sub.add_parser("secret", help="move a returned credential to the store")
    sec.add_argument("--id", required=True)

    args = ap.parse_args(argv)
    paths = Paths(args.workflow_dir)
    fn = {"list": cmd_list, "record": cmd_record, "secret": cmd_secret}[args.cmd]
    print(json.dumps(fn(paths, args), indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())

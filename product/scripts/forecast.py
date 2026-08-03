#!/usr/bin/env python3
"""Chain-forecast lifecycle — the `create-forecast` artifact's mechanical owner.

A chain-forecast is the loop's **prediction of its own routing** for a change: an ordered
chain of events, each naming a real `loop.md` node, shown to the human before the machine
walks it. It is a **committed** artifact at `.workflow/forecasts/<id>.json` with the
item-dir lifecycle — committed while the change is open, pruned when it closes, history in
git. It has to be committed rather than runtime because the frozen chain is the anchor
reality is compared against for the *life of the change*: across sessions, cold starts, and
a `/rebind` to a machine where the runtime tree explicitly may not survive.

LINT OWNERSHIP IS SPLIT BY FACT-DOMAIN (one owner per domain):
  * **graph facts** — "does this event name a real `loop.md` node?" — belong to
    `check_contracts.py --forecast`, which already owns `loop.md` parsing.
  * **lifecycle facts** — this file: the record's shape, the freeze, and the
    **names-only invariant** that is the whole reason a forecast is safe to commit.
  * **the prune** is deliberately NOT here: every other prune in the package lives in
    `retention.py` (the audit pass), and a second pruner is a second owner. `retention.py`
    prunes a forecast off the *same* `promoted.json` marker that closes its item dir —
    which is what "copies the item-dir lifecycle exactly" means in practice.

WHY THE NAMES-ONLY INVARIANT IS LINTED AND NOT PROMISED
A forecast front-loads the setup *elicitation*: "this chain needs `IVRIT_API_KEY` at event 5 —
hand it over now, or be asked then." The key NAME rides the card; the VALUE never does (it
goes to the secret store, and the machine-verify probe still runs at the gate). That is the
same class as `config.json`'s `secrets_required[]`, and a committed file is exactly where a
promise is worth nothing — so the shape that would carry a value is refused here.

Usage:  forecast.py lint <path>      — exit 0 clean · 1 findings · 2 unreadable
        forecast.py freeze <path>    — draft → frozen, in place (refuses a record that
                                       does not lint: freezing a broken chain makes a bad
                                       anchor permanent)
"""
import argparse
import hashlib
import json
import os
import re
import sys

STATUSES = ("draft", "frozen")
# the id becomes a FILENAME under `forecasts/` — a path-safety check before it is a format
# check, the same rule `bus.py` applies to a ticket id.
ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
# a credential/artifact KEY NAME, never a value: `IVRIT_API_KEY`, `POLAR_WEBHOOK_URL`.
KEY_NAME_RE = re.compile(r"[A-Z][A-Z0-9_]{0,63}$")
# fields that have no business existing in a committed forecast at any depth
FORBIDDEN_KEYS = ("value", "values", "secret", "secrets_values", "token", "password")


class Invalid(Exception):
    """The record could not be read at all — distinct from "it read fine and is wrong"."""


def load(path):
    try:
        with open(path, encoding="utf-8") as fh:
            fc = json.load(fh)
    except OSError as exc:
        raise Invalid("%s: %s" % (path, exc.strerror))
    except ValueError as exc:
        raise Invalid("%s is not valid JSON: %s" % (path, exc))
    if not isinstance(fc, dict):
        raise Invalid("%s: a forecast is an object, not %s" % (path, type(fc).__name__))
    return fc


def events_digest(events):
    """A stable sha256 over the chain — key order and whitespace cannot move it, so the
    digest tracks the PREDICTION and not its formatting."""
    canon = json.dumps(events, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()


def _walk(obj, path="$"):
    """Every (json-path, key, value) in the record, depth-first."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield path, k, v
            yield from _walk(v, "%s.%s" % (path, k))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from _walk(v, "%s[%d]" % (path, i))


def _check_names_only(fc):
    """The invariant that makes a COMMITTED forecast safe. Two independent teeth."""
    out = []
    # 1. the shape that would carry a value: a name list must hold plain KEY NAMES.
    for where, key, val in _walk(fc):
        if key not in ("secrets", "provides"):
            continue
        if not isinstance(val, list):
            out.append("%s.%s must be a list of key NAMES" % (where, key))
            continue
        for i, entry in enumerate(val):
            if not isinstance(entry, str):
                out.append("%s.%s[%d] is a %s — a name list holds key NAMES (strings), "
                           "and an object is how a VALUE gets into a committed file"
                           % (where, key, i, type(entry).__name__))
            elif not KEY_NAME_RE.match(entry):
                out.append("%s.%s[%d] = %r is not a key NAME (expected UPPER_SNAKE) — "
                           "the forecast carries names, never values"
                           % (where, key, i, entry))
    # 2. belt-and-braces: no field anywhere that a value would naturally be spelled into.
    for where, key, _val in _walk(fc):
        if key.lower() in FORBIDDEN_KEYS:
            out.append("%s.%s: a committed forecast carries no field named %r "
                       "(names only — the value belongs in the secret store)"
                       % (where, key, key))
    return out


def _check_events(fc):
    out = []
    events = fc.get("events")
    if not isinstance(events, list) or not events:
        return ["events[] is missing or empty — there is no chain to show anyone"]
    for i, ev in enumerate(events):
        label = "events[%d]" % i
        if not isinstance(ev, dict):
            out.append("%s is not an object" % label)
            continue
        if ev.get("n") != i + 1:
            out.append("%s has n=%r — the chain is an ORDER, so n runs 1..N in sequence "
                       "(a human reads it as 'then', and reality is matched against it "
                       "position by position)" % (label, ev.get("n")))
        for field in ("node", "what"):
            if not isinstance(ev.get(field), str) or not ev[field].strip():
                out.append("%s.%s is missing — %s" % (
                    label, field,
                    "every event names a real loop.md node (the forecast is a prediction "
                    "over the existing graph, never a second one)" if field == "node"
                    else "an event with no description is not something a human can judge"))
    return out


def lint(fc):
    """Returns a list of findings — empty means the record is a well-formed forecast.

    This is the LIFECYCLE half only. `check_contracts.py --forecast` answers whether the
    nodes named here actually exist in `loop.md`; both run before a forecast is parked.
    """
    out = []
    if not isinstance(fc, dict):
        return ["a forecast is an object"]

    fid = fc.get("forecast_id")
    if not isinstance(fid, str) or not ID_RE.match(fid):
        out.append("forecast_id %r is not a safe single path component (it becomes the "
                   "filename under forecasts/)" % (fid,))

    status = fc.get("status")
    if status not in STATUSES:
        out.append("status %r is not one of %s" % (status, ", ".join(STATUSES)))

    out += _check_events(fc)

    # The forecast MARKS ITS OWN BLIND SPOT, and that is not optional. Execute-discovered
    # needs are unforecastable by definition, so a chain that does not say where it stops
    # reads as "the whole change is planned" — the silent-cap failure `align`'s
    # honest-truncation rule exists to prevent ("do not read this as unattended").
    horizon = fc.get("horizon")
    if not isinstance(horizon, dict):
        out.append("horizon is missing — a forecast must state where it stops being able "
                   "to see, or it silently reads as complete")
    else:
        if not isinstance(horizon.get("beyond"), int):
            out.append("horizon.beyond must be the event number past which this is guesswork")
        if not isinstance(horizon.get("note"), str) or not horizon["note"].strip():
            out.append("horizon.note must say plainly that the tail is unforeseeable")

    out += _check_names_only(fc)

    if status == "frozen":
        if not fc.get("frozen_at"):
            out.append("a frozen forecast carries frozen_at")
        got, want = fc.get("events_sha256"), events_digest(fc.get("events") or [])
        if got != want:
            out.append("events_sha256 %r does not match the chain (%r) — a frozen forecast "
                       "that was edited is not the thing the human approved" % (got, want))
    return out


# --- the reality half: an ANCHOR TABLE, not a ledger --------------------------
#
# Reality is DERIVED. Nothing writes it, so nothing can forget to. Each `loop.md` node is
# resolved through the durable effect it leaves behind — the artifact the node produces is
# the proof the node ran.
#
# `state.json` is deliberately NOT the source, and this is not a preference. It is
# volatile and holds only the CURRENT node, never a history, so "which events have
# happened" is not a question it can answer at all.
#
# node base -> (probe, argument). A node absent from this table resolves `unknown` — see
# `reality()` for why that fourth state has to exist.
ANCHOR_TABLE = {
    "planner":         ("item_file", "plan.md"),
    "execute":         ("item_file", "changelog.md"),
    "verify":          ("item_file", "verify-verdict.md"),
    "debug":           ("item_file", "debug-report.md"),
    "refine":          ("item_file", "plan-delta.md"),
    "document":        ("item_file", "promoted.json"),
    "create-demo":     ("workflow_path", "demos"),
    "create-forecast": ("frozen", None),
    "checkpoint":      ("parked", None),
}

# The item-complete tail. Exempt from DIVERGENCE (not from the reality column): these run
# for every item, so their absence from a chain is the horizon talking, not a surprise —
# and a signal that fires on every finished item is not a signal.
DIVERGENCE_EXEMPT = ("commit", "document", "close-issue", "prioritize")


def _base(node):
    return node.split(":")[0] if isinstance(node, str) else ""


def _parked_records(workflow_dir):
    out = []
    try:
        names = sorted(os.listdir(os.path.join(workflow_dir, "parked")))
    except OSError:
        return out
    for n in names:
        if not n.endswith(".json"):
            continue
        try:
            with open(os.path.join(workflow_dir, "parked", n), encoding="utf-8") as fh:
                rec = json.load(fh)
        except (OSError, ValueError):
            continue
        if isinstance(rec, dict):
            out.append(rec)
    return out


def _probe(node, fc, workflow_dir):
    """One node -> done | open | pending | unknown."""
    probe = ANCHOR_TABLE.get(_base(node))
    if probe is None:
        return "unknown"
    kind, arg = probe
    item = fc.get("forecast_id") or ""
    if kind == "item_file":
        return "done" if os.path.exists(
            os.path.join(workflow_dir, "items", item, arg)) else "pending"
    if kind == "workflow_path":
        return "done" if os.path.exists(
            os.path.join(workflow_dir, arg, item)) else "pending"
    if kind == "frozen":
        return "done" if fc.get("frozen_at") else "pending"
    if kind == "parked":
        # `checkpoint:<kind>` — an unanswered record is the one genuinely live state the
        # column can show, and it is the most useful thing on it: "the machine is waiting
        # on YOU, here."
        #
        # SCOPED TO THIS ITEM, like every other probe here. `parked/` is a project-wide
        # directory, and without the `ticket_id` test this arm answered from ANY open
        # checkpoint in the project — so a `qa` gate parked for a different change made
        # this chain's `checkpoint:qa` read `open` ("the machine is waiting on YOU, here")
        # when nothing about this change was waiting, and worse, a chain predicting NO
        # checkpoint at all collected a structural DIVERGENCE from somebody else's
        # checkpoint. That one is not cosmetic: a structural divergence re-forecasts the
        # tail, and since `prioritize` emits parallel items, an open checkpoint somewhere
        # is the NORMAL state — so the false positive would have fired most of the time.
        want = node.split(":", 1)[1] if ":" in node else None
        for rec in _parked_records(workflow_dir):
            if rec.get("ticket_id") != item:
                continue
            cp = rec.get("checkpoint") or {}
            if want and cp.get("kind") != want:
                continue
            return "done" if rec.get("answered_at") else "open"
        return "pending"
    return "unknown"


def reality(fc, workflow_dir):
    """The derived reality column + the divergences, for one forecast.

    Returns `{events: [{n, node, state}], divergences: [{node, state}]}`.

    FOUR states, and the fourth is the honest one:
      `done`    — the anchor is there.
      `open`    — a checkpoint is parked and unanswered (the machine is waiting on a human).
      `pending` — the node HAS an anchor and it is absent: it has not happened yet.
      `unknown` — the node has NO anchor in the table. `decision-engineer`'s output is a
                  global decision record that cannot be tied to one item, so this column
                  must say it cannot tell rather than claim the step did not happen. A
                  column that renders "not done" for "I don't know" is worse than one
                  that admits the gap, because a human cannot see the difference.
    """
    events = [ev for ev in (fc.get("events") or []) if isinstance(ev, dict)]
    rows = [{"n": ev.get("n"), "node": ev.get("node"),
             "state": _probe(ev.get("node"), fc, workflow_dir)} for ev in events]

    # The same table read the other way: an effect that fired for a node the chain never
    # named. That is the STRUCTURAL tier — the machine took a turn nobody saw coming — and
    # it is why the boundary re-forecasts the tail instead of walking on.
    named = {_base(ev.get("node")) for ev in events}
    divergences = []
    for node in sorted(ANCHOR_TABLE):
        if node in named or node in DIVERGENCE_EXEMPT:
            continue
        state = _probe(node, fc, workflow_dir)
        if state in ("done", "open"):
            divergences.append({"node": node, "state": state})
    return {"forecast_id": fc.get("forecast_id"), "status": fc.get("status"),
            "events": rows, "divergences": divergences}


def freeze(fc, now):
    """draft → frozen, as a NEW record (the caller owns the write).

    IDEMPOTENT on `frozen_at`: `approve` freezes, and a re-run of the verdict-apply path
    must be a no-op. Moving the timestamp would silently re-baseline the anchor reality is
    later compared against — the same class of quiet damage as re-parking under a stale
    deadline."""
    out = dict(fc)
    out["status"] = "frozen"
    out.setdefault("frozen_at", now)
    out["events_sha256"] = events_digest(out.get("events") or [])
    return out


def _write_atomic(path, obj):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)


def _report(findings, what):
    for x in findings:
        print("  - %s" % x, file=sys.stderr)
    print("BLOCKED: %s" % what, file=sys.stderr)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Chain-forecast lifecycle (lint / freeze).")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name, helptext in (("lint", "check a forecast record's shape and invariants"),
                           ("freeze", "mark an approved forecast frozen, in place")):
        p = sub.add_parser(name, help=helptext)
        p.add_argument("path")
    sub.choices["freeze"].add_argument(
        "--now", default=None, help="ISO timestamp to stamp (default: now, UTC)")
    p_real = sub.add_parser("reality", help="derive what has actually happened so far")
    p_real.add_argument("path")
    p_real.add_argument("--workflow-dir", default=".workflow")
    p_real.add_argument("--json", action="store_true")
    p_real.add_argument("--check", action="store_true",
                        help="exit 1 on a structural divergence — what the scheduler "
                             "boundary gates on before it walks the tail")
    args = ap.parse_args(argv)

    try:
        fc = load(args.path)
    except Invalid as exc:
        ap.error(str(exc))

    if args.cmd == "reality":
        # Deliberately NOT gated on lint: reality is a read, and a human whose forecast has
        # gone malformed still needs to see where the loop actually got to.
        out = reality(fc, args.workflow_dir)
        if args.json:
            print(json.dumps(out, indent=2))
        else:
            for row in out["events"]:
                print("  %-4s %-24s %s" % (row["n"], row["node"], row["state"]))
        if out["divergences"]:
            print("DIVERGED: the loop did something this chain never predicted:",
                  file=sys.stderr)
            for d in out["divergences"]:
                print("  - %s (%s) — re-forecast the tail before walking on"
                      % (d["node"], d["state"]), file=sys.stderr)
            if args.check:
                return 1
        return 0

    findings = lint(fc)

    if args.cmd == "lint":
        if findings:
            _report(findings, "the forecast record is malformed:")
            return 1
        print("forecast: OK (%d event(s), status=%s)"
              % (len(fc.get("events") or []), fc.get("status")), file=sys.stderr)
        return 0

    # freeze
    if findings:
        _report(findings, "refusing to freeze a forecast that does not lint — freezing is "
                          "what makes it authoritative, so a broken chain frozen here is a "
                          "bad anchor for the life of the change:")
        return 1
    now = args.now
    if now is None:
        import datetime
        now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    frozen = freeze(fc, now)
    _write_atomic(args.path, frozen)
    print("forecast: frozen at %s (%d event(s), sha256 %s)"
          % (frozen["frozen_at"], len(frozen["events"]), frozen["events_sha256"][:12]),
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())

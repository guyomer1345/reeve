#!/usr/bin/env python3
"""The directive gate — shape enforcement for `.workflow/directives.md`.

WHAT THIS FILE IS FOR, because that decides everything below. `.workflow/directives.md` is the
one owner of a **standing operator instruction about how the LOOP behaves** — the thing that
otherwise lives in the conversation and dies at the next `/clear`, which is why it was being
re-typed every session. It is COMMITTED and ALWAYS-LOADED, so every entry in it is rent the
project pays before a word is typed, every turn, forever. `shared/schemas.md` § directive owns
the schema; this script is the mechanism that holds a hand-written file to it.

AN ALWAYS-LOADED FILE THAT ACCEPTS ANYTHING IS UNBOUNDED GROWTH IN THE MOST EXPENSIVE PLACE IN
THE SYSTEM. That is the whole reason the file is gated rather than merely conventional. Three
of the four checks here are that one idea in different clothes:

  MECHANICAL-FIRST IS HELD MECHANICALLY.  `type: mechanized` says the rule really lives in a
      hook, a gate or a config knob, and the entry is an INDEX ROW pointing at it. So a
      mechanized body is capped at ONE line. That cap is not a style rule -- it is the
      mechanical proxy for the STATED-TWICE hazard, on the one file whose entire purpose is to
      be obeyed: a directive written once here as prose and once there as a hook gives the loop
      two masters that drift, and a one-line body cannot be a second copy of a hook's logic.
      One fact, one owner (`shared/memory-model.md`) -- an index row is what that rule permits,
      a second copy is what it forbids.

  A POINTER IS CHECKED TO RESOLVE.  `mechanism` must EXIST. A dangling pointer is how an index
      rots -- the row keeps claiming a mechanism is in force long after the file moved.

  EVERY ENTRY HAS A RETIRE PATH, AND NONE OF THEM IS "A HUMAN REMEMBERS".  `on:<date>` fails
      once the date passes, so an expired directive stops the build instead of quietly staying
      in force. `when:<path>` fails once that path EXISTS -- which is what makes mechanical-
      first hold OVER TIME rather than only at entry: a behavioural placeholder is forced out
      the day its hook lands, by the arrival of the hook itself. `standing` is legal and
      deliberately the least convenient: it never fails, and it is listed on every `--report`
      so standing entries are re-confirmed rather than accumulated.

THE FILE FORMAT IS MARKDOWN A HUMAN HAPPILY HAND-EDITS, because an operator adding to it by
hand is the entire point -- a format that needs a tool to write is a format that goes back to
being re-typed in the conversation. So: `## <title>`, a short `- key: value` list, a body.
Where the schema left a detail genuinely open, the choice went to whichever option made hand-
editing more forgiving while keeping the parse unambiguous; each of those is marked CHOSEN
below with the reason.

A MISSING `directives.md` IS NOT A FAILURE -- a project may simply have no standing directives
-- but it is reported DISTINCTLY rather than as a pass. "0 directives, all valid" and "no such
file" are different facts, and a gate that renders them identically is a gate that cannot tell
you it never ran.

  --check   (default) the gate: exit 1 on any schema breach or any fired retire condition.
  --report  every entry with its fields, plus every standing entry called out for
            re-confirmation; exit 0. The read-only view, safe to run anywhere.
  --json    machine-readable, for either mode.
"""
import argparse
import datetime
import json
import os
import re
import sys

DIRECTIVES_REL = os.path.join(".workflow", "directives.md")

TYPES = ("mechanized", "behavioural")
KEYS = ("type", "entered", "retire", "mechanism")

# Comments are stripped BEFORE parsing, and the substitution preserves the newline count so
# every reported line number still points at the real line. The seeded file carries its own
# how-to-add guide in a comment; without this the guide's `type  mechanized | behavioural`
# crib would be parsed as content of whatever entry it sat under.
_COMMENT_RE = re.compile(r"<!--.*?-->", re.S)

# An entry starts at an H2 and only at an H2. Deeper headings are ordinary body text -- which
# is the forgiving read: a `###` inside a behavioural body is prose, not a malformed entry.
_HEADING_RE = re.compile(r"^##\s+(\S.*?)\s*$")

# TWO field spellings, CHOSEN for hand-editing. The bulleted form is what the seed shows and
# what markdown makes natural, and it accepts ANY key so a typo (`- retires:`) is caught as an
# unknown field rather than silently demoted to body text and re-reported as a missing
# required field two errors later. The unbulleted form is accepted too -- people drop the dash
# -- but ONLY for the four known keys, because `word: value` with an arbitrary key is
# indistinguishable from an ordinary prose line and would start eating bodies.
_FIELD_RE = re.compile(r"^\s*[-*]\s*([A-Za-z_][\w-]*)\s*:\s*(.*?)\s*$")
_BARE_FIELD_RE = re.compile(r"^\s*(%s)\s*:\s*(.*?)\s*$" % "|".join(KEYS), re.I)

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

# `mechanism` is "the path or config key where the rule actually lives". One spelling covers
# both without ambiguity: a path, optionally followed by `#` and a dotted key INTO that file.
# CHOSEN over bare dotted keys (`doc_budget.always_hard`) because a bare key names no file, so
# the existence check -- the one thing that keeps an index from rotting -- would have nothing
# to open.
_MECHANISM_RE = re.compile(r"^(?P<path>[^#]+?)(?:#(?P<key>[A-Za-z_][\w.-]*))?$")


def _strip_comments(text):
    return _COMMENT_RE.sub(lambda m: "\n" * m.group(0).count("\n"), text)


def parse(text):
    """-> [entry]. Structure only; validation is `validate`. Never raises on bad input.

    Two owners, no overlap: this function decides WHAT the file says, `validate` decides
    whether that is allowed. A parser that also judged would have to invent a verdict for
    input it could not read, and the shape errors are more useful reported as a list.
    """
    lines = _strip_comments(text).splitlines()
    starts = [i for i, ln in enumerate(lines) if _HEADING_RE.match(ln)]
    entries = []
    for n, i in enumerate(starts):
        end = starts[n + 1] if n + 1 < len(starts) else len(lines)
        title = _HEADING_RE.match(lines[i]).group(1)
        entries.append(_parse_entry(title, i + 1, lines[i + 1:end]))
    return entries


def _parse_entry(title, offset, lines):
    """The field block, then the body. Blank lines inside the field block are fine."""
    fields, errors, j = {}, [], 0
    while j < len(lines):
        raw = lines[j]
        if not raw.strip():
            j += 1
            continue
        m = _FIELD_RE.match(raw) or _BARE_FIELD_RE.match(raw)
        if not m:
            break
        key, val = m.group(1).lower(), m.group(2).strip()
        if key not in KEYS:
            errors.append("unknown field `%s` (known: %s)" % (key, ", ".join(KEYS)))
        elif key in fields:
            errors.append("field `%s` given twice" % key)
        else:
            fields[key] = val
        j += 1

    body = lines[j:]
    # A field line BELOW the body is the other natural hand-edit slip -- appending
    # `- retire: standing` at the end of an entry. Silently treating it as prose would report
    # "missing required field: retire" while the retire is sitting right there in the file, so
    # it is named for what it is.
    for k, raw in enumerate(body):
        m = _FIELD_RE.match(raw) or _BARE_FIELD_RE.match(raw)
        if m and m.group(1).lower() in KEYS:
            errors.append("field `%s` appears below the body (line %d) -- every field must "
                          "come before it" % (m.group(1).lower(), offset + j + k + 1))
    return {"title": title, "line": offset, "fields": fields,
            "body": [b.rstrip() for b in body if b.strip()], "errors": errors}


def _check_mechanism(project_root, value):
    """-> None if the pointer resolves, else the reason it does not."""
    m = _MECHANISM_RE.match(value.strip())
    if not m or not m.group("path").strip():
        return "not a `<path>` or `<path>#<dotted.key>`"
    rel = m.group("path").strip()
    path = os.path.join(project_root, rel)
    if not os.path.exists(path):
        return "no such path `%s` (relative to the project root)" % rel
    key = m.group("key")
    if key is None:
        return None
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except Exception as exc:
        return "`%s` is not readable JSON, so `#%s` cannot resolve (%s)" % (rel, key, exc)
    node = data
    for part in key.split("."):
        if not isinstance(node, dict) or part not in node:
            return "`%s` has no config key `%s`" % (rel, key)
        node = node[part]
    return None


def _parse_retire(value):
    """-> (kind, payload, error). `kind` in {on, when, standing}."""
    v = value.strip()
    if v == "standing":
        return "standing", None, None
    for prefix in ("on:", "when:"):
        if v.startswith(prefix):
            rest = v[len(prefix):].strip()
            if not rest:
                return None, None, "`retire: %s` names nothing" % prefix.rstrip(":")
            if prefix == "on:":
                if not _DATE_RE.match(rest):
                    return None, None, "`retire: on:%s` is not a YYYY-MM-DD date" % rest
                try:
                    return "on", datetime.date(*(int(p) for p in rest.split("-"))), None
                except ValueError:
                    return None, None, "`retire: on:%s` is not a real date" % rest
            return "when", rest, None
    return None, None, ("`retire: %s` is not one of `on:YYYY-MM-DD`, `when:<path>`, `standing`"
                        % v)


def validate(entry, project_root, today):
    """-> (errors, retired) for one entry. Both are lists of human-readable reasons.

    `retired` is kept SEPARATE from `errors` even though both fail the gate, because they are
    different events with different remedies: a shape error means the entry was written wrong,
    while a fired retire means the entry was written right and its time is simply up. Telling
    an operator to "fix" a directive whose hook just landed would be exactly backwards -- the
    remedy is to delete it.
    """
    errors, retired = list(entry["errors"]), []
    f = entry["fields"]

    typ = f.get("type")
    if typ is None:
        errors.append("missing required field `type`")
    elif typ not in TYPES:
        errors.append("`type: %s` is not one of %s" % (typ, " | ".join(TYPES)))

    entered = f.get("entered")
    if entered is None:
        errors.append("missing required field `entered`")
    elif not _DATE_RE.match(entered):
        errors.append("`entered: %s` is not a YYYY-MM-DD date" % entered)
    else:
        try:
            datetime.date(*(int(p) for p in entered.split("-")))
        except ValueError:
            errors.append("`entered: %s` is not a real date" % entered)

    mech = f.get("mechanism")
    # Required IFF mechanized. The `forbidden otherwise` half matters as much as the required
    # half: a behavioural entry carrying a mechanism is a mechanized entry that dodged the
    # one-line cap, which is the second-copy hazard walking in through the side door.
    if typ == "mechanized":
        if mech is None:
            errors.append("`type: mechanized` requires `mechanism` -- the path or config key "
                          "where the rule actually lives. If there is no such place, the rule "
                          "was not mechanized and the type is `behavioural`")
        else:
            why = _check_mechanism(project_root, mech)
            if why:
                errors.append("`mechanism: %s` does not resolve: %s. A dangling pointer is how "
                              "an index rots -- the row keeps claiming a mechanism is in force "
                              "after it moved" % (mech, why))
    elif typ == "behavioural" and mech is not None:
        errors.append("`mechanism` is forbidden on a `behavioural` entry -- a directive that "
                      "names where it is enforced IS mechanized, and must take the type (and "
                      "the one-line cap) that goes with it")

    n = len(entry["body"])
    if n == 0:
        errors.append("no body -- an entry that states nothing is rent with no instruction in it")
    elif typ == "mechanized" and n > 1:
        errors.append(
            "a `mechanized` body is capped at ONE line and this one has %d. The cap is the "
            "mechanical proxy for the STATED-TWICE hazard: the rule lives in "
            "`%s`, and prose here restating it gives the loop two masters that drift. A "
            "one-line body cannot be a second copy of a hook's logic -- say what the "
            "mechanism ACHIEVES and stop" % (n, mech or "<mechanism>"))

    retire = f.get("retire")
    if retire is None:
        errors.append("missing required field `retire` -- every entry carries a retire path, "
                      "and none of them is \"a human remembers\" "
                      "(`on:YYYY-MM-DD` | `when:<path>` | `standing`)")
    else:
        kind, payload, err = _parse_retire(retire)
        if err:
            errors.append(err)
        elif kind == "on" and today > payload:
            retired.append("`retire: on:%s` has passed (today is %s). An expired directive "
                           "stops the build rather than quietly staying in force: delete it, "
                           "or re-enter it with a new date and a reason it is still true"
                           % (payload.isoformat(), today.isoformat()))
        elif kind == "when" and os.path.exists(os.path.join(project_root, payload)):
            retired.append("`retire: when:%s` has fired -- that path now EXISTS, so the "
                           "mechanism this prose was standing in for has landed. Delete the "
                           "entry; the hook is the directive now" % payload)
    return errors, retired


def scan(project_root, today=None):
    today = today or datetime.date.today()
    path = os.path.join(project_root, DIRECTIVES_REL)
    rel = DIRECTIVES_REL.replace(os.sep, "/")
    if not os.path.isfile(path):
        return {"present": False, "path": rel, "entries": [], "failures": []}
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            text = fh.read()
    except OSError as exc:
        return {"present": True, "path": rel, "entries": [],
                "failures": [{"title": rel, "line": 0, "errors": [str(exc)], "retired": []}]}

    entries, failures = [], []
    for e in parse(text):
        errors, retired = validate(e, project_root, today)
        row = {"title": e["title"], "line": e["line"], "type": e["fields"].get("type"),
               "entered": e["fields"].get("entered"), "retire": e["fields"].get("retire"),
               "mechanism": e["fields"].get("mechanism"), "body_lines": len(e["body"]),
               "errors": errors, "retired": retired}
        entries.append(row)
        if errors or retired:
            failures.append(row)
    return {"present": True, "path": rel, "entries": entries, "failures": failures}


def failed(result):
    """The gate's verdict, in one place -- the exit code, the rendered line and every caller
    must agree, and two copies of this predicate is how a gate reports OK and exits 1."""
    return bool(result["failures"])


def render(result, report):
    rel = result["path"]
    if not result["present"]:
        # Reported DISTINCTLY, never as a silent pass: "no directives" and "all directives
        # valid" are different facts, and a gate that renders them identically cannot tell you
        # it never ran.
        return ("OK: no directives -- %s does not exist. Nothing standing is in force; a "
                "standing operator instruction goes there (`shared/schemas.md` § directive)"
                % rel)

    lines = []
    for e in result["failures"]:
        head = "%s:%d  %s" % (rel, e["line"], e["title"])
        for why in e["errors"]:
            lines.append("INVALID      %s" % head)
            lines.append("             %s" % why)
        for why in e["retired"]:
            lines.append("RETIRED      %s" % head)
            lines.append("             %s" % why)

    if report:
        for e in result["entries"]:
            lines.append("%-12s %-44s %s · entered %s · retire %s%s"
                         % ("directive", e["title"], e["type"] or "?",
                            e["entered"] or "?", e["retire"] or "?",
                            "" if not e["mechanism"] else " -> %s" % e["mechanism"]))
        # Standing entries are listed on EVERY report, by design. `standing` never fails, so
        # this listing is the only pressure on it -- re-confirmed each time it is read, rather
        # than accumulated because nothing ever asked about it again.
        standing = [e for e in result["entries"] if (e["retire"] or "").strip() == "standing"]
        if standing:
            lines.append("STANDING     %d entry(s) with no expiry -- re-confirm each is still "
                         "true, or give it a retire path: %s"
                         % (len(standing), ", ".join(e["title"] for e in standing)))

    n = len(result["entries"])
    if failed(result):
        bad = len(result["failures"])
        lines.append("BLOCKED: %d of %d directive(s) in %s are invalid or have retired. This "
                     "file is ALWAYS-LOADED -- every entry is rent the project pays before a "
                     "word is typed, so an entry that cannot be validated does not get to keep "
                     "costing that. Fix or delete each one above." % (bad, n, rel))
    else:
        lines.append("OK: directives -- %d entry(s) in %s valid and in force" % (n, rel))
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="the schema gate over .workflow/directives.md (standing loop directives)")
    ap.add_argument("--project-root", default=".")
    ap.add_argument("--report", action="store_true",
                    help="list every entry and every standing one, and always exit 0")
    ap.add_argument("--check", action="store_true",
                    help="the gate: exit 1 on a schema breach or a fired retire (the default)")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    result = scan(os.path.abspath(args.project_root))
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(render(result, report=args.report))
    # `--report` is the read-only view: its whole job is to be safe to run anywhere, so it
    # never fails a commit -- the same rule as the sibling doc-budget gate.
    return 0 if args.report else (1 if failed(result) else 0)


if __name__ == "__main__":
    sys.exit(main())

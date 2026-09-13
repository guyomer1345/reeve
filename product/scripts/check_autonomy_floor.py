#!/usr/bin/env python3
"""The autonomy floor — the mechanical minimum under "route anything that may change the goal".

The loop takes every decision that does not change the goal and routes anything that may.
That criterion is a judgement, and a loop grading its own decisions drifts toward "not
fundamental" because that is the direction that lets it keep working. So the judgement is
floored: this script answers ONE question about a proposed change —

    does it cross the goal-preserving floor, and therefore auto-route to a human
    REGARDLESS of the model's read?

It answers it from the SPEC DIFF (`<project_root>/docs/spec.md`), and it fires on any of:

  1. LOCKED BLOCK        a changed hunk whose enclosing block carries a `locked` commitment
                         marker. Touching the text of a locked element is, by definition,
                         editing something the project promised not to move unilaterally.
  2. LOCKED MARKER LOST  a hunk that removes or weakens a `locked` marker — `locked` ->
                         `provisional` / `unspecified`, or the marker deleted outright.
                         Downgrading a commitment is the single cheapest way to make a
                         goal change look like an ordinary edit, so it is its own rule.
  3. ACCEPTANCE CRITERIA a changed hunk inside an `acceptance_criteria` region. Editing a
                         criterion's text IS altering what it demands; there is no version
                         of "reworded the criterion" that leaves the demand untouched.

WHAT THIS IS NOT, STATED RATHER THAN IMPLIED — a floor that is really a judgement in a
gate's clothes is worse than no floor. This is a **spec-diff** floor. It sees a change that
rewrites the goal *in the spec*. A code change that quietly abandons a locked behaviour
**without touching the spec is not caught here, at all** — that is the drift scan's job in
the alignment pass and the conformance check's job in verify, and it is exactly the case
judgement is expected to escalate on. Nothing here licenses "the floor was clear, so it was
not goal-affecting". The floor is a MINIMUM that judgement rises above, never a cap.

OVER-ROUTING IS THE CORRECT FAILURE DIRECTION; UNDER-ROUTING IS NOT. Every ambiguity in
this file is resolved toward ROUTE, and the deliberate ones are:
  * A MIXED marker (`` — commitment: `locked` (existence) / `provisional` (layout) ``)
    fires on any edit to its block. Which *aspect* of a mixed-commitment element a prose
    edit touches is not mechanically decidable — that half of the rule genuinely cannot be
    made mechanical, and the honest move is to route and say why, not to guess.
  * A nested bullet INHERITS its ancestor list items' markers: a sub-bullet of a locked
    element is part of that element. It does NOT inherit across paragraphs or headings —
    a section-wide rule would fire on every edit anywhere in the spec, and a gate that
    always fires is a gate a human learns to skip.
  * Anything undetermined — an unreadable spec, a diff that will not compute, a block whose
    extent runs off the end of what could be read — is a ROUTE, never a "proceed".

FAIL CLOSED. There are exactly two exit codes and no third one for "something went wrong",
because a caller that can distinguish an error from a clear result will eventually treat the
error as clear:
    0  CLEAR  — nothing in this change crosses the floor.
    1  ROUTE  — the floor is crossed, OR it could not be computed. Both are a human's call.
The report and `--json` DO distinguish the two (`findings` vs `undetermined`), so an operator
can act on the difference; the exit code deliberately does not.

  --project-root PATH   where `.workflow/config.json` lives (default `.`).
  (default)             diff the STAGED change, the thing about to become a commit.
  --ref REF             diff against an arbitrary ref (`main`, `HEAD~3`, or `A..B`).
  --stdin               read a unified diff from stdin instead of asking git.
  --json                machine-readable verdict for the orchestrator.
"""
import argparse
import json
import os
import re
import subprocess
import sys

CONFIG_REL = os.path.join(".workflow", "config.json")
SPEC_RELDIR = ("docs", "spec.md")

# The commitment enum, and the one value that is the floor. `provisional` and `unspecified`
# are NOT floor values by design: the loop is supposed to settle those, and a floor that
# caught them would route the ordinary work it exists to leave alone.
COMMITMENTS = ("locked", "provisional", "unspecified")
FLOOR_MARKER = "locked"

# --- marker recognition ------------------------------------------------------------------
# The markers are semi-structured INLINE PROSE, not a field, and the shapes below are the
# ones a real spec actually uses:
#     `— commitment: `locked``
#     `— `locked``
#     `— commitment: `locked` (existence) / `provisional` (layout, styling)`
#     `— `locked` (triad) / business-logic + others `unspecified`(deferred)`
# So a marker is an INTRODUCER plus a commitment token in the rest of that line. Two
# introducers, with deliberately different strictness:
#   * a DASH introducer requires the token to be BACKTICKED. Not fussiness — prose is full
#     of dashes and full of the word "locked" ("8 gates A–H, locked 2026-08-06" is a real
#     line in a real spec), and an unbackticked match there would mark a whole header block
#     as locked forever. The backtick is what the spec convention actually writes.
#   * an explicit `commitment:` introducer accepts a BARE token too, because someone writing
#     `commitment: locked` has stated a commitment as plainly as it can be stated and a
#     missed marker is an UNDER-route.
# Scanned per LINE (introducer -> end of that line), never per block: a block-wide scan would
# let a stray dash early in a long bullet claim every commitment word after it.
MARKER_TOKEN_RE = re.compile(r"`(%s)`" % "|".join(COMMITMENTS))
BARE_TOKEN_RE = re.compile(r"\b(%s)\b" % "|".join(COMMITMENTS))
DASH_INTRO_RE = re.compile(r"[—–]|(?<=\s)--(?=\s)")
COMMITMENT_INTRO_RE = re.compile(r"(?i)commitment\s*:")

# --- acceptance_criteria regions ----------------------------------------------------------
# Two spellings, because specs write criteria both ways: as a heading over a list, and as a
# labelled field on a feature. Both require the COLON (or the heading form), which is what
# keeps the schema's own descriptive mention -- `{ name, purpose, acceptance_criteria,
# commitment }` -- from marking the whole features section as a criteria region.
AC_WORD = r"acceptance[_ ]criteria"
AC_HEADING_RE = re.compile(r"(?i)" + AC_WORD)
AC_LABEL_RE = re.compile(r"(?i)" + AC_WORD + r"`?\*{0,2}\s*:")

HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")
ITEM_RE = re.compile(r"^(\s*)([-*+]|\d{1,9}[.)])(\s+)(\S.*)$")
FENCE_RE = re.compile(r"^\s*(```+|~~~+)")
HTML_COMMENT_ONLY_RE = re.compile(r"^<!--.*-->$")
HUNK_RE = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")
SPEC_PATH_RE = re.compile(r"(^|/)docs/spec\.md$")

RULE_LOCKED_BLOCK = "locked-block"
RULE_MARKER_LOST = "locked-marker-lost"
RULE_ACCEPTANCE = "acceptance-criteria"
RULE_TITLES = {
    RULE_LOCKED_BLOCK: "locked element edited",
    RULE_MARKER_LOST: "locked marker removed/weakened",
    RULE_ACCEPTANCE: "acceptance criterion edited",
}


# ============================================================== reading the world

def _read_json(path):
    """-> (obj, problem). A MISSING config is not a problem (a project may simply not have
    one yet, and the defaults locate the spec fine); an UNREADABLE one is, because then the
    spec path this gate is about to trust is a guess."""
    if not os.path.exists(path):
        return None, None
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh), None
    except (OSError, ValueError) as exc:
        return None, "%s could not be read (%s)" % (path, exc)


def resolve_spec(project_root):
    """-> (spec path, problem).

    `project_root` and `docs_root` are resolved exactly as the doc-budget gate resolves
    them, including the NORMALISATION. That is not tidiness: `project_root` is commonly the
    relative spelling `./project`, which makes `os.path.join` produce `<root>/./project/docs/
    spec.md`. The un-normalised spelling denotes the same file and compares unequal to every
    other spelling of it, and in the sibling gate that exact slip double-counted a document.
    Here it would break the git-relative path and the drift check below, so it is killed at
    the point the path is built rather than at each use.
    """
    cfg, problem = _read_json(os.path.join(project_root, CONFIG_REL))
    cfg = cfg if isinstance(cfg, dict) else {}
    proot = cfg.get("project_root") or "."
    # `docs_root` differs from `project_root` only in org mode, where the derived docs cannot
    # sit beside a repo owner's own `docs/`. One named root per meaning, same as the sibling.
    droot = cfg.get("docs_root") or proot
    path = os.path.normpath(os.path.join(project_root, droot, *SPEC_RELDIR))
    return path, problem


def _git(args, cwd):
    """-> (ok, stdout). Never raises: a git that is absent, slow or angry is an
    undetermined answer, and undetermined routes."""
    try:
        out = subprocess.run(["git"] + list(args), capture_output=True, text=True,
                             timeout=30, cwd=cwd)
    except Exception:
        return False, ""
    return out.returncode == 0, out.stdout


def git_toplevel(cwd):
    ok, out = _git(["rev-parse", "--show-toplevel"], cwd)
    return out.strip() if ok and out.strip() else None


def git_relpath(top, path):
    return os.path.relpath(os.path.abspath(path), top).replace(os.sep, "/")


def _blob(top, rev, rel):
    """-> (text, ok). `rev=""` means the INDEX (`git show :path`).

    A rev that genuinely does not carry the file is `("", True)`: an ADDED spec has no old
    side, and that is a fact rather than a failure. Anything else that fails is `ok=False`,
    which the caller turns into an UNDETERMINED — we do not get to treat "could not read the
    committed spec" as "the committed spec was empty", because that reads every locked
    element as newly added and then as nothing at all.
    """
    spec = "%s:%s" % (rev, rel)
    ok, out = _git(["show", spec], top)
    if ok:
        return out, True
    exists, _ = _git(["cat-file", "-e", spec], top)
    return ("", True) if not exists else ("", False)


# ============================================================== the diff

class Hunk(object):
    __slots__ = ("old_start", "new_start", "lines", "path")

    def __init__(self, old_start, new_start, path):
        self.old_start, self.new_start, self.path = old_start, new_start, path
        self.lines = []  # [(tag, text)] with tag in " +-"

    def numbered(self, tag):
        """[(line number on that side, text)] for the ' ' + `tag` lines of this hunk."""
        out, old, new = [], self.old_start, self.new_start
        for t, text in self.lines:
            if t == tag:
                out.append((old if tag == "-" else new, text))
            if t in " -":
                old += 1
            if t in " +":
                new += 1
        return out

    def window(self, side):
        """The hunk's own view of one side: (lines, first line number). Used only when the
        whole file is not available — see `Side.complete`."""
        keep = " -" if side == "old" else " +"
        return ([text for t, text in self.lines if t in keep],
                self.old_start if side == "old" else self.new_start)


def parse_diff(text, path_filter=None):
    """Unified diff -> [Hunk]. `path_filter(path) -> bool` keeps only the files we care
    about; a diff handed in on stdin is routinely a whole-commit diff."""
    hunks, path, keep = [], None, True
    for raw in text.splitlines():
        if raw.startswith("diff --git "):
            path, keep = None, True
            parts = raw.split(" b/", 1)
            if len(parts) == 2:
                path = parts[1].strip()
                keep = path_filter(path) if path_filter else True
            continue
        if raw.startswith("+++ "):
            name = raw[4:].strip()
            if name != "/dev/null":
                path = name[2:] if name.startswith("b/") else name
                keep = path_filter(path) if path_filter else True
            continue
        if raw.startswith("--- "):
            continue
        m = HUNK_RE.match(raw)
        if m:
            if keep:
                hunks.append(Hunk(int(m.group(1)), int(m.group(3)), path))
            else:
                hunks.append(None)
            continue
        if not hunks or hunks[-1] is None:
            continue
        if raw.startswith("\\"):          # "\ No newline at end of file"
            continue
        if raw[:1] in ("+", "-", " "):
            hunks[-1].lines.append((raw[0], raw[1:]))
        elif raw == "":
            # A context line that is genuinely empty loses its leading space in some tools.
            hunks[-1].lines.append((" ", ""))
    return [h for h in hunks if h is not None]


def significant(text):
    """False for the changes that cannot alter what the spec DEMANDS: blank/whitespace-only
    lines, and lines that are nothing but an HTML comment. Everything else counts."""
    s = text.strip()
    return bool(s) and not HTML_COMMENT_ONLY_RE.match(s)


def _norm(text):
    return " ".join(text.split())


def cosmetic(hunk):
    """True when the hunk's two sides are the same content differently spaced/wrapped.

    A re-indent or a re-wrap of a locked element is not a change to what it demands, and
    routing on it would train an operator to wave the gate through — the failure mode that
    kills a gate. Compared on SIGNIFICANT lines only, so an inserted blank line is cosmetic
    while an inserted sentence is not.

    Compared as ONE normalised string rather than line-by-line, because a re-wrap moves the
    line boundaries — that is what re-wrapping IS — and a list comparison calls a one-line
    paragraph split across two lines a change. Reordering is still a change: joining preserves
    order, so two bullets swapped compare unequal.
    """
    minus = " ".join(_norm(t) for tag, t in hunk.lines if tag == "-" and significant(t))
    plus = " ".join(_norm(t) for tag, t in hunk.lines if tag == "+" and significant(t))
    return _norm(minus) == _norm(plus)


# ============================================================== the markdown side

class Block(object):
    """One markdown construct: a list item (with its continuation lines), a paragraph, or a
    heading. Deliberately NOT a section — see the module docstring on inheritance."""
    __slots__ = ("kind", "start", "end", "indent", "content_indent", "parent")

    def __init__(self, kind, start, indent, content_indent, parent):
        self.kind, self.start, self.end = kind, start, start
        self.indent, self.content_indent, self.parent = indent, content_indent, parent


class Side(object):
    """One side of the diff, parsed: the text, where it starts, and whether it is the WHOLE
    file or only what a hunk happened to show.

    `complete=False` is the honest half. When only a hunk window is available, a block that
    runs off the edge of the window may carry a marker we cannot see — and a marker we
    cannot see is exactly the under-route this gate must not have. So a truncated block with
    no marker found is reported as UNDETERMINED, which routes.
    """

    def __init__(self, text, offset=1, complete=True):
        self.lines = text.splitlines() if isinstance(text, str) else list(text)
        self.offset = offset
        self.complete = complete
        self._parse()

    # -- parsing ---------------------------------------------------------------------------
    def _parse(self):
        n = len(self.lines)
        self.owner = [None] * n          # block index per line (None = blank / structural)
        self.heads = [()] * n            # heading stack per line, for the operator-facing label
        self.blocks = []
        self.in_ac = [False] * n

        stack, para, fence, hstack, blank = [], None, None, [], True
        ac_stops = []                    # [(from_index, until_predicate)] resolved after

        for i, line in enumerate(self.lines):
            stripped = line.strip()
            indent = len(line) - len(line.lstrip(" "))

            if fence is not None:
                # Inside a fence everything is continuation of whatever was open; the fence
                # body never opens or closes a block of its own.
                if FENCE_RE.match(line) and stripped.startswith(fence):
                    fence = None
                owner = stack[-1] if stack else para
                if owner is None:
                    para = self._open("paragraph", i, indent, indent, None)
                    owner = para
                self._attach(owner, i)
                self.heads[i] = tuple(hstack)
                blank = False
                continue

            self.heads[i] = tuple(hstack)

            if not stripped:
                para = None
                blank = True
                continue

            fm = FENCE_RE.match(line)
            if fm:
                fence = fm.group(1)[:3]
                owner = stack[-1] if (stack and not blank) else None
                if owner is None:
                    stack = []
                    para = self._open("paragraph", i, indent, indent, None)
                    owner = para
                self._attach(owner, i)
                blank = False
                continue

            hm = HEADING_RE.match(line)
            if hm:
                level, title = len(hm.group(1)), hm.group(2).strip()
                while hstack and hstack[-1][0] >= level:
                    hstack.pop()
                stack, para = [], None
                idx = self._open("heading", i, indent, indent, None)
                self._attach(idx, i)
                hstack.append((level, title))
                self.heads[i] = tuple(hstack)
                if AC_HEADING_RE.search(title):
                    ac_stops.append(("heading", i, level, indent))
                blank = False
                continue

            im = ITEM_RE.match(line)
            if im:
                content_indent = len(im.group(1)) + len(im.group(2)) + len(im.group(3))
                while stack and indent < self.blocks[stack[-1]].content_indent:
                    stack.pop()
                parent = stack[-1] if stack else None
                idx = self._open("item", i, indent, content_indent, parent)
                self._attach(idx, i)
                stack.append(idx)
                para = None
                blank = False
            elif stack and para is None and not blank:
                # Lazy continuation: a wrapped line directly under an item line belongs to
                # that item however it is indented. This is the shape that matters most here
                # — the commitment marker routinely lands on a bullet's LAST wrapped line.
                self._attach(stack[-1], i)
                blank = False
            else:
                while stack and indent < self.blocks[stack[-1]].content_indent:
                    stack.pop()
                if stack:
                    self._attach(stack[-1], i)
                else:
                    if para is None:
                        para = self._open("paragraph", i, indent, indent, None)
                    self._attach(para, i)
                blank = False

            if AC_LABEL_RE.search(line):
                ac_stops.append(("label", i, None, indent))

        self._mark_ac(ac_stops)

    def _open(self, kind, i, indent, content_indent, parent):
        self.blocks.append(Block(kind, i, indent, content_indent, parent))
        return len(self.blocks) - 1

    def _attach(self, idx, i):
        self.owner[i] = idx
        self.blocks[idx].end = i

    def _mark_ac(self, stops):
        """An acceptance_criteria REGION, resolved by the structure that actually delimits
        it: a heading runs to the next heading of the same or higher level; a label runs to
        the next non-blank line indented at or left of the label. Indentation, not block
        descent, because the common shape is a bare `acceptance_criteria:` line followed by
        a list that is a sibling construct rather than a child of it."""
        n = len(self.lines)
        for kind, start, level, indent in stops:
            self.in_ac[start] = True
            for j in range(start + 1, n):
                line = self.lines[j]
                if not line.strip():
                    self.in_ac[j] = True
                    continue
                hm = HEADING_RE.match(line)
                if kind == "heading":
                    if hm and len(hm.group(1)) <= level:
                        break
                else:
                    if hm:
                        break
                    if len(line) - len(line.lstrip(" ")) <= indent:
                        break
                self.in_ac[j] = True

    # -- queries ---------------------------------------------------------------------------
    def index(self, lineno):
        i = lineno - self.offset
        return i if 0 <= i < len(self.lines) else None

    def chain(self, block_idx):
        """The block plus every ANCESTOR LIST ITEM, deepest first. A sub-bullet of a locked
        element is part of that element, so the ancestors' markers govern it too."""
        out, idx = [], block_idx
        while idx is not None:
            out.append(idx)
            idx = self.blocks[idx].parent
        return out

    def markers(self, block_idx):
        """The commitment tokens written on this block's OWN lines.

        Own lines only: every line belongs to exactly one (deepest) block, so a parent's
        markers are read from the parent's own text and a child's marker never leaks upward.

        A MARKER WRAPS, and the wrap is not hypothetical — a real spec writes
        `` — commitment: `locked` (existence) / `` on one line and `` `provisional` (layout,
        styling) `` on the next, so a strictly per-line read sees a locked-only marker where
        the author wrote a mixed one. So once an introducer has been seen in this block, the
        block's later own-lines contribute their BACKTICKED tokens too. That can only widen
        the set, which is the safe direction on both counts: a wider set can add `locked`
        (route, correct) and can turn a locked-only marker into the MIXED one it really is
        (which is the detail that tells an operator why the gate could not decide for them).
        """
        b = self.blocks[block_idx]
        found, tail = set(), False
        for i in range(b.start, b.end + 1):
            if self.owner[i] != block_idx:
                continue
            line = self.lines[i]
            found |= markers_in_line(line)
            if tail:
                found |= set(MARKER_TOKEN_RE.findall(line))
            if COMMITMENT_INTRO_RE.search(line) or DASH_INTRO_RE.search(line):
                tail = True
        return found

    def truncated(self, block_idx):
        """True when this block touches an edge of a partial read, so its real extent — and
        any marker out there — is unknown."""
        if self.complete:
            return False
        b = self.blocks[block_idx]
        return b.start == 0 or b.end == len(self.lines) - 1

    def headline(self, block_idx):
        """The block's own first line, normalised — its identity, independent of how much of
        the document the reader could see."""
        head = _norm(self.lines[self.blocks[block_idx].start])
        return head[:120]

    def label(self, block_idx):
        """The operator-facing name of the element: its heading path plus the head of its own
        text. The whole point is that a human can act on the report without re-running
        anything, so the report must name WHICH element, not just a line number."""
        b = self.blocks[block_idx]
        path = " > ".join(t for _lvl, t in self.heads[b.start])
        head = _norm(self.lines[b.start])
        if len(head) > 72:
            head = head[:69] + "..."
        return ("%s > %s" % (path, head)) if path and b.kind != "heading" else (path or head)


def markers_in_line(line):
    """The commitment tokens this LINE asserts. See the MARKER_* constants for why the two
    introducers have different strictness."""
    found = set()
    for m in COMMITMENT_INTRO_RE.finditer(line):
        found |= set(BARE_TOKEN_RE.findall(line[m.end():]))
    for m in DASH_INTRO_RE.finditer(line):
        found |= set(MARKER_TOKEN_RE.findall(line[m.end():]))
    return found


# ============================================================== the rules

def _finding(rule, side_name, lineno, element, detail, key=None):
    """`key` is the finding's IDENTITY for de-duplication, and it is deliberately not the
    `element` label. The label carries the heading path, which a hunk-window read cannot
    see — so the same element found on the old side and the new side would otherwise be
    reported as two things for an operator to go and look at, when it is one. The key is the
    element's own headline, which both reads agree on."""
    return {"rule": rule, "side": side_name, "line": lineno,
            "element": element, "detail": detail, "key": key if key is not None else element}


def scan_side(side, side_name, changed, findings, undetermined):
    """Rules 1 and 3 over one side of the diff. `changed` is [(lineno, text)]."""
    seen = set()
    for lineno, text in changed:
        if not significant(text):
            continue
        i = side.index(lineno)
        if i is None:
            undetermined.append(
                "%s side line %d falls outside the text that could be read, so its "
                "commitment is unknown" % (side_name, lineno))
            continue
        if side.in_ac[i] and ("ac", i) not in seen:
            seen.add(("ac", i))
            block = side.owner[i]
            findings.append(_finding(
                RULE_ACCEPTANCE, side_name, lineno,
                side.label(block) if block is not None else "(acceptance_criteria region)",
                "inside an acceptance_criteria region — editing a criterion is editing what "
                "it demands",
                key=side.headline(block) if block is not None else "acceptance_criteria"))
        block = side.owner[i]
        if block is None:
            continue
        chain = side.chain(block)
        if ("blk", chain[0]) in seen:
            continue
        carrier = None
        for idx in chain:
            if FLOOR_MARKER in side.markers(idx):
                carrier = idx
                break
        if carrier is not None:
            seen.add(("blk", chain[0]))
            mix = sorted(side.markers(carrier))
            findings.append(_finding(
                RULE_LOCKED_BLOCK, side_name, lineno, side.label(chain[0]),
                "enclosing block carries `locked`%s%s"
                % ("" if carrier == chain[0] else " (inherited from the enclosing element)",
                   "" if mix == [FLOOR_MARKER] else
                   " — marker is MIXED (%s); which aspect this edit touches is not "
                   "mechanically decidable, so it routes"
                   % ", ".join("`%s`" % m for m in mix)),
                key=side.headline(chain[0])))
        elif any(side.truncated(idx) for idx in chain):
            seen.add(("blk", chain[0]))
            undetermined.append(
                "%s side line %d sits in a block that runs past the edge of the diff, so a "
                "`locked` marker outside the window cannot be ruled out" % (side_name, lineno))


def scan_marker_loss(hunk, old_side, findings):
    """Rule 2, read off the hunk itself rather than off either parsed side.

    Deliberately hunk-local: the question is whether THIS edit took a `locked` away, and the
    two sides of one hunk are the before and after of the same passage. A `locked` in the
    removed lines with no `locked` in the added lines is a downgrade or a deletion — the
    cheapest way to make a goal change look routine — whichever of the two it is.
    """
    minus, plus, at = set(), set(), None
    for lineno, text in hunk.numbered("-"):
        found = markers_in_line(text)
        if FLOOR_MARKER in found and at is None:
            at = lineno
        minus |= found
    for _n, text in hunk.numbered("+"):
        plus |= markers_in_line(text)
    if FLOOR_MARKER not in minus or FLOOR_MARKER in plus:
        return
    weaker = sorted(plus & set(COMMITMENTS))
    # NAME THE ELEMENT, not the hunk. A line number alone sends the operator back to the diff
    # to work out what they are being asked about, which is the re-run this report exists to
    # avoid; the hunk coordinates are the fallback for when the old side could not be parsed.
    lineno = at if at is not None else hunk.old_start
    idx = old_side.index(lineno)
    block = old_side.owner[idx] if idx is not None else None
    element = (old_side.label(block) if block is not None
               else "hunk at old line %d / new line %d" % (hunk.old_start, hunk.new_start))
    findings.append(_finding(
        RULE_MARKER_LOST, "old", lineno, element,
        "`locked` was removed from this element; what replaced it: %s"
        % (", ".join("`%s`" % m for m in weaker) if weaker else "no commitment marker"),
        key=old_side.headline(block) if block is not None else element))


# ============================================================== the run

def load_sides(mode, ref, top, rel, spec_path, undetermined):
    """-> (old Side or None, new Side or None). None means "fall back to the hunk windows",
    which is a narrower read, not a failure — `Side.complete` carries that distinction."""
    def _side(text):
        return Side(text)

    if mode == "staged":
        # HEAD vs the INDEX, which is exactly what `git diff --cached` compared. Reading the
        # worktree for the new side instead would answer about a file the commit will not
        # contain, on any tree with unstaged edits.
        old_text, ok_old = _blob(top, "HEAD", rel)
        new_text, ok_new = _blob(top, "", rel)
        if not ok_old:
            undetermined.append("the committed (HEAD) spec could not be read")
            return None, (_side(new_text) if ok_new else None)
        if not ok_new:
            undetermined.append("the staged spec could not be read")
            return _side(old_text), None
        return _side(old_text), _side(new_text)

    if mode == "ref":
        left, right = (ref.split("..", 1) + [""])[:2] if ".." in ref else (ref, "")
        left = left.strip() or "HEAD"
        old_text, ok_old = _blob(top, left, rel)
        if not ok_old:
            undetermined.append("the spec at %s could not be read" % left)
            old_text = None
        if right.strip():
            new_text, ok_new = _blob(top, right.strip(), rel)
            if not ok_new:
                undetermined.append("the spec at %s could not be read" % right.strip())
                new_text = None
        else:
            new_text = _read_text(spec_path)
            if new_text is None:
                undetermined.append("the working-tree spec (%s) could not be read" % spec_path)
        return (_side(old_text) if old_text is not None else None,
                _side(new_text) if new_text is not None else None)

    return None, None  # stdin: anchored below, or hunk windows


def _read_text(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return fh.read()
    except OSError:
        return None


def anchor(side, hunks):
    """True when every hunk's new-side content really is at those line numbers in `side`.

    Used for `--stdin`, where the diff arrives without either blob. If the working-tree spec
    matches the diff's new side, the whole file is the better read and block detection stops
    being window-limited. If it does not match, the file is NOT the diff's new side and using
    it would answer a question about a different document.
    """
    for h in hunks:
        lines, start = h.window("new")
        for k, text in enumerate(lines):
            i = side.index(start + k)
            if i is None or side.lines[i].rstrip() != text.rstrip():
                return False
    return True


def evaluate(hunks, old_side, new_side):
    findings, undetermined = [], []
    for h in hunks:
        if cosmetic(h):
            continue
        o = old_side or Side(h.window("old")[0], h.window("old")[1], complete=False)
        n = new_side or Side(h.window("new")[0], h.window("new")[1], complete=False)
        scan_marker_loss(h, o, findings)
        scan_side(n, "new", h.numbered("+"), findings, undetermined)
        scan_side(o, "old", h.numbered("-"), findings, undetermined)
    # One row per (rule, element): an operator needs the list of elements, and the same
    # element edited on four lines is one thing to go and look at.
    deduped, seen = [], set()
    for f in findings:
        key = (f["rule"], f["key"])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(f)
    return deduped, undetermined


def run(project_root, mode="staged", ref=None, diff_text=None):
    """-> the result dict. Every path out of here that is not a confident CLEAR carries
    something in `undetermined`, and anything in `undetermined` routes."""
    root = os.path.abspath(project_root)
    spec_path, cfg_problem = resolve_spec(root)
    undetermined = [cfg_problem] if cfg_problem else []
    # Reported RELATIVE to the project root, the way the sibling budget gate reports paths:
    # the operator reads this beside the repo, and an absolute scratch path is noise.
    shown = os.path.relpath(spec_path, root).replace(os.sep, "/")
    result = {"status": "route", "spec": shown,
              "source": ref if mode == "ref" else mode,
              "findings": [], "undetermined": undetermined, "hunks": 0}

    top = git_toplevel(root)
    rel = git_relpath(top, spec_path) if top else None

    if mode == "stdin":
        text = diff_text or ""
        changed_names = [m for m in re.findall(r"(?m)^\+\+\+ b/(.+)$", text)]
    else:
        if top is None:
            undetermined.append(
                "this is not a git worktree, so the spec diff cannot be computed; pass "
                "--stdin with a diff, or --project-root pointing into the repo")
            return _finish(result)
        args = (["diff", "--cached", "--name-only", "--diff-filter=d"] if mode == "staged"
                else ["diff", "--name-only", "--diff-filter=d", ref])
        ok, names = _git(args, top)
        if not ok:
            undetermined.append("git could not list the changed paths (%s)"
                                % (" ".join(args)))
            return _finish(result)
        changed_names = [ln.strip() for ln in names.splitlines() if ln.strip()]
        dargs = (["diff", "--cached", "-U5", "--", rel] if mode == "staged"
                 else ["diff", "-U5", ref, "--", rel])
        ok, text = _git(dargs, top)
        if not ok:
            undetermined.append("git could not diff %s (%s)" % (rel, " ".join(dargs)))
            return _finish(result)

    # PATH DRIFT IS A FAIL-CLOSED CASE, not a miss. If a file that is plainly a spec changed
    # and it is NOT the one config points at, this gate just read the wrong document and
    # would have reported CLEAR with total confidence. Same class of failure as a safety gate
    # skipping itself because the path it hardcoded had moved.
    strays = [n for n in changed_names
              if SPEC_PATH_RE.search(n) and (rel is None or n != rel)]
    if strays:
        undetermined.append(
            "a spec changed at %s, but this project's config points at %s — which one owns "
            "the goal is not something this gate may guess"
            % (", ".join(sorted(strays)), rel or spec_path))

    # A DELETED SPEC IS NOT AN ORDINARY HUNK. The three rules all ask what a block says, and
    # a spec that no longer exists says nothing — so the rules would report on the old side
    # and fall silent about the fact that the document defining the goal is gone. That is the
    # fail-closed case, stated as one: the floor cannot be computed against an absent spec.
    if re.search(r"(?m)^\+\+\+ /dev/null$", text or ""):
        undetermined.append(
            "this change DELETES the spec, so there is no goal definition left to compute a "
            "floor against")

    hunks = parse_diff(text, path_filter=(lambda p: bool(SPEC_PATH_RE.search(p)))
                       if mode == "stdin" else None)
    result["hunks"] = len(hunks)
    if not hunks:
        return _finish(result)

    if mode == "stdin":
        old_side, new_side = None, None
        tree = _read_text(spec_path)
        if tree is not None:
            candidate = Side(tree)
            if anchor(candidate, hunks):
                new_side = candidate
    else:
        old_side, new_side = load_sides(mode, ref, top, rel, spec_path, undetermined)

    findings, more = evaluate(hunks, old_side, new_side)
    result["findings"] = findings
    undetermined.extend(more)
    return _finish(result)


def _finish(result):
    result["status"] = "route" if (result["findings"] or result["undetermined"]) else "clear"
    result["counts"] = {rule: sum(1 for f in result["findings"] if f["rule"] == rule)
                        for rule in RULE_TITLES}
    return result


# ============================================================== output

LIMIT = (
    "The floor reads the SPEC DIFF only. A code change that abandons a locked behaviour "
    "without touching the spec is NOT caught here — that is the alignment drift scan and "
    "verify's conformance check. This is a minimum judgement rises above, never a cap: a "
    "clear result is not a finding that the change is goal-preserving.")


def render(result):
    lines = []
    if result["status"] == "clear":
        lines.append("CLEAR: the autonomy floor is not crossed — %s"
                     % ("%s is unchanged" % result["spec"] if not result["hunks"]
                        else "%d changed hunk(s) in %s, none in a locked element or an "
                             "acceptance_criteria region" % (result["hunks"], result["spec"])))
        lines.append("       %s" % LIMIT)
        return "\n".join(lines)

    lines.append("ROUTE REQUIRED: this change crosses the goal-preserving autonomy floor.")
    lines.append("")
    for f in result["findings"]:
        lines.append("  %-31s %s:%d (%s side)"
                     % (RULE_TITLES[f["rule"]], result["spec"], f["line"], f["side"]))
        lines.append("  %-31s %s" % ("", f["element"]))
        lines.append("  %-31s %s" % ("", f["detail"]))
    for u in result["undetermined"]:
        lines.append("  %-31s %s" % ("UNDETERMINED", u))
    lines.append("")
    if result["undetermined"] and not result["findings"]:
        lines.append("Nothing was found to cross the floor, but the floor could not be "
                     "COMPUTED, and an uncomputed floor is not a clear one. Fix the cause "
                     "above, or take the change to the human.")
    else:
        lines.append("%d element(s) crossed the floor. This is not the model's call to make "
                     "and not overridable by the loop: take it to the human who owns the "
                     "goal, naming the elements above." % len(result["findings"]))
    lines.append(LIMIT)
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="the goal-preserving autonomy floor, computed from the spec diff")
    ap.add_argument("--project-root", default=".")
    src = ap.add_mutually_exclusive_group()
    src.add_argument("--ref", help="diff against this ref (`main`, `HEAD~3`, or `A..B`) "
                                   "instead of the staged change")
    src.add_argument("--stdin", action="store_true",
                     help="read a unified diff from stdin; pass generous context (-U5 or "
                          "more) unless the working-tree spec is the diff's new side")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    mode = "stdin" if args.stdin else ("ref" if args.ref else "staged")
    diff_text = sys.stdin.read() if args.stdin else None
    try:
        result = run(args.project_root, mode=mode, ref=args.ref, diff_text=diff_text)
    except Exception as exc:  # fail CLOSED: an exception is an unanswered question
        result = _finish({"status": "route", "spec": "", "source": mode, "findings": [],
                          "hunks": 0,
                          "undetermined": ["the floor could not be computed (%s: %s)"
                                           % (type(exc).__name__, exc)]})
    print(json.dumps(result, indent=2, sort_keys=True) if args.json else render(result))
    return 0 if result["status"] == "clear" else 1


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Did closing a slice sweep the OTHER owners, or only the two that are easy to remember?

META-ONLY. Never ships; it reads this repo's construction record.

WHY THIS EXISTS. `CLAUDE.md` prescribes a blast-radius sweep on capture: change a fact, update
its owner, repoint the rest. `check-status-coherence.sh` is the mechanical backstop for that --
but it covers roster counts, `D1–DN` ranges and roadmap status tags, and nothing else. So the
sweep was exactly as reliable as whoever remembered to run it, and four stale entries were found
in one sitting: a queue item that a decision had already built, a section header contradicting
its own contents, and two `07` questions closed by decisions that `07` never heard about.

That is the same defect `D214` found one level up. There, a REQUEST had no owner, so five asks
of ten closed while unmet. Here, an owner has no SWEEP, so a fact moves and its other homes keep
the old answer. Both are invisible without a gate, and both look like tidy bookkeeping right up
until someone re-reads the source and finds the work missing.

THREE INVARIANTS, AND THEY ARE ALL DECIDABLE -- which is the whole reason these two and not the
others. A gate that needed to judge whether prose was stale would be a judgement wearing a gate's
clothes, and this repo has a name for that.

  1. A SETTLED QUESTION IS STRUCK. A decision whose text claims to settle / close / answer /
     discharge something in `07` must be NAMED in `07`. The claim is the decision's own, in its
     own words, so this asks only that the two records agree about a thing one of them already
     asserts. Measured on the tree it was written against: 14 decisions make such a claim, 13
     were swept, 1 was not -- which is the signal-to-noise this needs to be worth having.
  2. AN ASK HAS ONE ENTRY. In the roadmap's queue, an `[ask #N]` tag must not appear on both a
     CLOSED heading and an open one. `D214`'s ledger catches an ask with no item; this catches
     its mirror, an ask with TWO -- one of them a ghost that a later reader would build again
     having already built it.
  3. AN ASK HAS SOMETHING AGAINST IT. Every numbered row of an ACCEPTANCE LEDGER table must be
     claimed by a `[ask #N]` queue heading or name a discharger in its own cell, and a cell that
     cites `D<k>` must cite one that exists. This is `D214`'s own defect, mechanized: there,
     five asks of ten closed while unmet because the request had no owner and nothing could
     notice an ask with nothing built against it. The ledger gave it an owner; this makes the
     owner check itself, because a ledger that is only read by whoever remembers to read it is
     the same class of control as the sweep that produced invariants 1 and 2. Note it is the
     exact MIRROR of invariant 2 and neither implies the other -- one ask two entries, one ask
     no entry, and only a human reading both tables end to end would have caught either.

WHAT IS DELIBERATELY NOT GATED, so nobody reads a green run as more than it is: a section HEADER
that contradicts the items beneath it (`Space 3` said "unbuilt" over a list of BUILT tags). Prose
agreeing with prose is not mechanically decidable, and inventing a heuristic for it would produce
exactly the false confidence this file is arguing against. It is named here as a known blind spot
and left to the human sweep.
"""
import argparse
import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG = os.path.join(ROOT, "docs", "design", "08-decision-log.md")
OQ = os.path.join(ROOT, "docs", "design", "07-open-questions.md")
ROADMAP = os.path.join(ROOT, "docs", "design", "11-roadmap.md")

# The claim, in the decision's OWN words, on the same line as a reference to `07`. Bounded to
# one line and 60 characters between verb and reference so a paragraph that happens to contain
# both does not read as a claim about that document.
CLAIM_RE = re.compile(r"(?i)(settles|closes|answers|discharges)\b[^.\n]{0,60}`07`")
HEADING_RE = re.compile(r"^## (D\d+)")
ASK_RE = re.compile(r"\[ask #(\d+)\]")
CLOSED_RE = re.compile(r"(?i)\bCLOSED\b|✅")


def _read(path):
    with io.open(path, encoding="utf-8") as fh:
        return fh.read()


def settled_questions_are_struck(log_text, oq_text):
    """-> list of findings. A decision that says it settled an `07` question, which `07` has
    never heard of."""
    current, claimed = None, []
    for line in log_text.splitlines():
        m = HEADING_RE.match(line)
        if m:
            current = m.group(1)
        if current and CLAIM_RE.search(line):
            claimed.append(current)
    out = []
    for d in sorted(set(claimed), key=lambda x: int(x[1:])):
        if not re.search(r"\b%s\b" % d, oq_text):
            out.append("%s says it settles a question in `07`, and `07` never names it — so the "
                       "question still reads as open. Strike the entry (the convention is "
                       "`**CLOSED (%s)**`) or drop the claim." % (d, d))
    return out


def one_entry_per_ask(roadmap_text):
    """-> list of findings. The mirror of the acceptance ledger's rule: an ask with TWO items."""
    seen = {}
    for line in roadmap_text.splitlines():
        if not line.startswith("#### "):
            continue
        for n in ASK_RE.findall(line):
            seen.setdefault(n, []).append((bool(CLOSED_RE.search(line)), line.strip()))
    out = []
    for n, rows in sorted(seen.items(), key=lambda kv: int(kv[0])):
        if len({closed for closed, _ in rows}) > 1:
            closed = [h for c, h in rows if c]
            opened = [h for c, h in rows if not c]
            out.append(
                "ask #%s has both a CLOSED entry and an open one — the open one is a ghost that "
                "would be built a second time.\n      closed: %s\n      open:   %s"
                % (n, closed[0][:110], opened[0][:110]))
    return out


LEDGER_HEADING_RE = re.compile(r"^#{2,4} .*ACCEPTANCE LEDGER")
LEDGER_ROW_RE = re.compile(r"^\|\s*(\d+)\s*\|")


def ledger_asks(roadmap_text):
    """-> {ask number: (row, discharge cell)}. Rows of any ACCEPTANCE LEDGER table.

    Scoped to the table under a ledger heading rather than to every pipe-row in the document,
    because the roadmap carries other tables and a bare `| 3 |` in one of them is not an ask.
    The scope ends at the next heading of the same level or shallower, which is what closes it.
    """
    out, depth = {}, None
    for line in roadmap_text.splitlines():
        if line.startswith("#"):
            level = len(line) - len(line.lstrip("#"))
            if LEDGER_HEADING_RE.match(line):
                depth = level
                continue
            if depth is not None and level <= depth:
                depth = None
            continue
        if depth is None:
            continue
        m = LEDGER_ROW_RE.match(line)
        if m:
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            out[m.group(1)] = (line.strip(), cells[2] if len(cells) > 2 else "")
    return out


EMPTY_CELL = {"", "-", "—", "–", "tbd", "?", "n/a", "none"}


def every_ask_has_an_entry(roadmap_text, log_text):
    """-> list of findings. `D214` mechanized: an ask with NOTHING against it.

    WHAT IT ASKS, and why it is not "every ask has a queue entry". The `[ask #N]` tag postdates
    the first five asks, and two of the ten were discharged by a disposition rather than a slice
    (`answered -- they do`, `parked`). Requiring a tagged entry would therefore fire on seven
    rows that are not defects, and a gate whose green state needs seven exemptions is a gate
    nobody keeps. So the decidable question is the one `D214` actually asks: **does anything at
    all claim this ask?** A tagged queue heading, or a non-empty `Discharged by` cell. An empty
    cell on a row nobody built is precisely the state that lost five of ten.

    It also refuses a DANGLING citation: a cell naming `D<k>` that the decision log does not
    contain. A discharge that cites a decision nobody wrote reads exactly like a discharge.
    """
    built = set()
    for line in roadmap_text.splitlines():
        if line.startswith("#### "):
            built.update(ASK_RE.findall(line))
    have = set(re.findall(r"^## (D\d+)", log_text, re.M))
    out = []
    for n, (row, cell) in sorted(ledger_asks(roadmap_text).items(), key=lambda kv: int(kv[0])):
        if n not in built and cell.strip("* `").lower() in EMPTY_CELL:
            out.append("ask #%s is in an ACCEPTANCE LEDGER with NOTHING against it — no queue "
                       "entry tagged `[ask #%s]` and no discharger named. An ask with no item is "
                       "work that has gone missing, which is how five of ten were lost "
                       "(`D214`).\n      row: %s" % (n, n, row[:140]))
            continue
        for d in set(re.findall(r"\bD\d+\b", cell)) - have:
            out.append("ask #%s is discharged by `%s`, and the decision log has no such entry — "
                       "a citation to a decision nobody wrote reads exactly like a "
                       "discharge.\n      row: %s" % (n, d, row[:140]))
    return out


def run():
    log, oq, roadmap = _read(LOG), _read(OQ), _read(ROADMAP)
    findings = (settled_questions_are_struck(log, oq)
                + one_entry_per_ask(roadmap)
                + every_ask_has_an_entry(roadmap, log))
    return findings


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.parse_args(argv)
    findings = run()
    if findings:
        print("BLOCKED: a slice closed without sweeping its other owners:", file=sys.stderr)
        for f in findings:
            print("  - %s" % f, file=sys.stderr)
        print("         status is derived and has ONE owner per fact; a second copy left behind "
              "is how five of ten asks went missing.", file=sys.stderr)
        return 1
    print("OK: owner sweep — settled `07` questions are struck; no ask carries two queue "
          "entries; every ledger ask has something against it")
    return 0


if __name__ == "__main__":
    sys.exit(main())

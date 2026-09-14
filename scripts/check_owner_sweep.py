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

TWO INVARIANTS, AND THEY ARE BOTH DECIDABLE -- which is the whole reason these two and not the
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


def run():
    log, oq, roadmap = _read(LOG), _read(OQ), _read(ROADMAP)
    findings = settled_questions_are_struck(log, oq) + one_entry_per_ask(roadmap)
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
    print("OK: owner sweep — settled `07` questions are struck; every ask has one queue entry")
    return 0


if __name__ == "__main__":
    sys.exit(main())

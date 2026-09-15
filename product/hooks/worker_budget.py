#!/usr/bin/env python3
"""PostToolUse, inside a WORKER: tell it to yield before its window runs out.

THE HALF THAT WAS CALLED IMPOSSIBLE. The standing objection to bounding a worker's context was
that a subagent cannot spawn its own successor. That is true and it is beside the point: it does
not have to. It only has to **yield** — return `status: continue` with its state in `scratch/` —
and the orchestrator, which can dispatch, starts a fresh one. So the missing piece was never a
spawn primitive; it was something that tells a running worker it is time. This is that.

THE SIGNAL IS REAL AND IT IS THE WORKER'S OWN TRANSCRIPT. Measured over 364 subagent runs: the
per-agent JSONL is **appended during the run** (files were found ending mid-flight on a
`tool_result`, one 236 lines deep — a flush-at-completion writer cannot leave that), and every
assistant line carries full `usage`. Occupancy is `cache_read + cache_creation + input_tokens`
of the last assistant line. Nothing is needed from the parent, which is what makes this a
worker-side hook rather than a poller the orchestrator has to run.

IT ADVISES, IT DOES NOT TRUNCATE, AND THAT IS THE CEILING — stated here rather than discovered.
`PostToolUse` can add context; it cannot stop a worker, cannot rewrite a tool result, and cannot
make a model return anything. A worker that ignores this runs to its real limit and dies the way
it did before. What changes is that the yield point is now *reachable*: the worker is told, in
its own transcript, with the exact shape of the return it should produce. The same trade as
`dispatch_return.py` and named the same way — a detector that can do one useful thing, doing it.

WHY NOT A HARD NUMBER FROM THE MEASUREMENT. The `execute` median is 194.1k and 21% of runs pass
300k — a tail, not a median. A threshold at the median would yield constantly and turn every
ordinary item into two dispatches; a threshold at the tail fires too late to be acted on. So this
is a FRACTION of the window the worker actually has, defaulting high, with the operator able to
move it — the same shape as the context band's `warn_pct`, for the same reason.

ONCE, NOT EVERY TURN. A worker past the threshold is past it for the rest of its life, so an
un-latched hook would repeat the instruction on every remaining tool call — which is both noise
and a growing share of the very window it is trying to protect. The latch lives beside the
worker's own transcript, keyed on its agent id.

FAIL DIRECTION IS SILENCE, always. An unreadable payload, a transcript it cannot positively
locate, a usage block it does not recognise, a torn latch: every one exits 0 saying nothing. This
runs after every tool call of every worker in the loop. Being wrong and loud here costs more than
being absent — and unlike the context band, nothing downstream depends on this having spoken.

BUT SILENT IS NOT THE SAME AS UNOBSERVABLE, and conflating the two is what made this hook the
weakest ✅ in the acceptance ledger. Every exit above is a *guess-free* exit, and exactly one of
them — `no-agent-id` — is also the NORMAL path, because this hook is registered on PostToolUse
with no matcher and therefore fires on the orchestrator's own tool calls too. So "it said nothing"
carried no information at all: a healthy run and a permanently dead trigger look identical from
outside. Note the asymmetry with `handoff_gate.py`, which reads `agent_id` as a *skip-if-present*
guard and is therefore safe whether or not the key exists; this one reads it as a *required*
condition, so a missing key does not degrade it, it disables it.

The breadcrumb below fixes that and nothing else: each exit drops one small file under
`.workflow/worker-budget/`, so absence becomes a thing you can read rather than a thing you assume.
It does NOT change any verdict, does not speak to the model, and is not a second detector. READ IT
THIS WAY, and the ordering matters:
  · `located.json` present  -> the reading half RAN INSIDE A REAL WORKER. The trigger is reachable.
    This is the only file that proves anything on its own, and it is the one the smoke drive asserts.
  · `no-transcript.json`    -> an agent id arrived and the transcript could not be found. Broken,
    and the recorded `tried` paths say where to look.
  · `no-agent-id.json`      -> EXPECTED, and on its own it proves NOTHING; it is what every
    orchestrator tool call produces. It becomes a finding only in the company of a missing
    `located.json` after a run that is KNOWN to have dispatched workers — which is a fact the drive
    holds and this hook cannot. That is why the assertion lives there and the evidence lives here.
Existence is the signal and existence is monotone, which is what makes it safe under a parallel
wave: one file per outcome, so no outcome can clobber another, and concurrent writers to the same
outcome can lose a `count` increment but can never un-write the file. The count is advisory and
says so on disk. The extra cost is one small atomic write per tool call; the alternative was an
ask discharged by a mechanism nobody could show had ever run.
"""
import json
import os
import sys

# The fraction of a worker's window at which it should start wrapping up. High by design: the
# cost of yielding early is a whole extra dispatch, the cost of yielding late is the work.
DEFAULT_YIELD_PCT = 75
ENV_PCT = "REEVE_WORKER_YIELD_PCT"

# Claude Code does not publish a per-agent window on the payload, so the denominator has to come
# from somewhere. This is the conservative floor across the models the package runs on; a worker
# with a larger window simply yields earlier than it had to, which is the safe direction.
ASSUMED_WINDOW = 200_000

INSTRUCTION = (
    "WORKER BUDGET — you are at roughly %d%% of your context window (%s of ~%s tokens).\n\n"
    "Do not start new work. Bring what you have to a clean stopping point and RETURN NOW, using "
    "the `continue` form of the dispatch-return contract:\n"
    "1. Write everything a successor needs into your item's `scratch/` directory — what you "
    "finished, what you were part-way through, what you had decided and why. Write it with "
    "`Write`; do not print it.\n"
    "2. Return with `status: continue` on line 1, a one-line `summary:`, and `resume:` naming "
    "that scratch path.\n"
    "This is NOT a failure and you should not report it as one: the orchestrator will dispatch a "
    "fresh worker from your notes. Stopping cleanly now is worth more than a few more turns."
)


# --- the breadcrumb: one file per exit, so "it said nothing" stops being unreadable ----------
# Only ever written into a `.workflow/` that ALREADY EXISTS. A hook that creates directories to
# record its own presence is a hook that litters every tree a worker happens to be cwd'd into.
BREADCRUMB_DIR = "worker-budget"
BREADCRUMB_KEY_CAP = 24


def breadcrumb_root(payload):
    """-> the directory to drop breadcrumbs in, or None. Never creates `.workflow/` itself."""
    cwd = payload.get("cwd") or os.environ.get("CLAUDE_PROJECT_DIR")
    if not isinstance(cwd, str) or not cwd:
        return None
    workflow = os.path.join(cwd, ".workflow")
    if not os.path.isdir(workflow):
        return None
    return os.path.join(workflow, BREADCRUMB_DIR)


def note(payload, outcome, **detail):
    """Record that this exit was reached. Best-effort by construction: any failure is dropped.

    `count` is ADVISORY and the file says so — two workers of one wave writing the same outcome
    can lose an increment. Existence cannot be lost that way, and existence is the whole signal.
    """
    try:
        root = breadcrumb_root(payload)
        if root is None:
            return
        os.makedirs(root, exist_ok=True)
        path = os.path.join(root, "%s.json" % outcome)
        count = 0
        try:
            with open(path) as fh:
                prev = json.load(fh)
            if isinstance(prev, dict) and isinstance(prev.get("count"), int):
                count = prev["count"]
        except (OSError, ValueError):
            count = 0
        rec = {
            "outcome": outcome,
            "count": count + 1,
            "count_is": "advisory — concurrent workers can lose an increment; existence cannot",
            "tool": payload.get("tool_name") or payload.get("toolName"),
            "payload_keys": sorted(payload.keys())[:BREADCRUMB_KEY_CAP],
        }
        rec.update(detail)
        tmp = path + ".tmp-%d" % os.getpid()
        with open(tmp, "w") as fh:
            json.dump(rec, fh, indent=1, sort_keys=True)
        os.replace(tmp, path)
    except Exception:
        return


def _payload():
    try:
        obj = json.load(sys.stdin)
    except (ValueError, OSError):
        return None
    return obj if isinstance(obj, dict) else None


def agent_id(payload):
    """A WORKER's id, or None when this is the orchestrator's own turn.

    The orchestrator has its own governor (`context_band.py` + the `Stop` hook) and a different
    remedy — write a handoff and clear. Telling it to `return status: continue` would be advice
    it cannot take, so the two are kept strictly apart, the same way `handoff_gate.py` keeps
    them apart from its side.
    """
    for key in ("agent_id", "agentId", "subagent_id"):
        val = payload.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    return None


def is_worker_transcript(path, aid):
    """The invariant that makes mis-attribution structurally impossible.

    A candidate counts as THIS worker's transcript only if it lives under a `subagents/`
    directory AND its filename names this agent. Everything the locator proposes is filtered
    through here, so no future route can quietly reintroduce the defect this replaced: the
    original route accepted the payload's `transcript_path` on the sole evidence that it was a
    file, and the real payload shape makes that the SESSION transcript — measured on a kept
    smoke tree, that handed back the orchestrator's 122,955 tokens as the worker's 55,791, i.e.
    61% instead of 28%. Not silence: a spurious yield on every worker of every wave, arriving
    sooner the fuller the parent got.
    """
    parts = os.path.normpath(path).split(os.sep)
    if "subagents" not in parts[:-1]:
        return False
    return aid in os.path.basename(path)


def tried_paths(payload, aid):
    """Every candidate this hook would accept, in order, WHETHER OR NOT it exists.

    Split out from `transcript_path` so the two can never drift: the locator returns the first
    of these that is a real file, and the `no-transcript` breadcrumb records the whole list. A
    breadcrumb that said only "not found" would send the next reader back to re-derive the
    candidate set by reading this function; this one hands them the paths that were missed.

    THE SESSION DIRECTORY IS THE TRANSCRIPT PATH MINUS ITS EXTENSION, which is the other half of
    the defect above and the half that was the suspected no-op. Verified on disk:
        <project>/<session-id>.jsonl                       <- the session transcript
        <project>/<session-id>/subagents/agent-<aid>.jsonl  <- the worker's own
    so `dirname(session)` is the PROJECT directory, one level too high, and the old fallback
    looked for `<project>/subagents/...` — a path that cannot exist. It never mattered, because
    the mis-attributing route above shadowed it and returned first. Fixing either one alone
    leaves the mechanism broken: tightening the first without this turns a wrong answer into no
    answer, and this without the first is never reached.
    """
    out = []
    for key in ("transcript_path", "transcriptPath"):
        val = payload.get(key)
        if isinstance(val, str) and val:
            out.append(val)
    session = payload.get("transcript_path") or payload.get("session_transcript")
    if isinstance(session, str) and session:
        bases = [os.path.splitext(session)[0]]     # the real layout, confirmed on disk
        bases.append(os.path.dirname(session))     # kept only because the filter makes it safe
        for base in bases:
            for name in ("agent-%s.jsonl" % aid, "%s.jsonl" % aid):
                out.append(os.path.join(base, "subagents", name))
    # Dedupe, order-preserving: the two bases coincide for a path with no extension.
    seen = set()
    return [c for c in out if not (c in seen or seen.add(c))]


def transcript_path(payload, aid):
    """Where this worker's own JSONL is, or None if it cannot be located POSITIVELY.

    Several routes, because the payload shape is not pinned down by the documented schema and
    guessing is how a detector starts lying. Every one of them is filtered through
    `is_worker_transcript`, so "positively" is now enforced rather than asserted: a candidate
    must sit under `subagents/` and be named for this agent. If nothing survives both that and
    an `isfile`, this hook says nothing at all — and the `no-transcript` breadcrumb records
    every path it tried, so the silence is diagnosable.
    """
    for cand in tried_paths(payload, aid):
        if is_worker_transcript(cand, aid) and os.path.isfile(cand):
            return cand
    return None


def occupancy(path):
    """-> tokens in this worker's window, or None.

    The LAST assistant line with a usage block wins: the file is appended during the run, so the
    tail is the present. `cache_read + cache_creation + input` is the whole occupancy — leaving
    out the cache terms would report a fraction of the truth, and they are the majority of it.
    """
    try:
        with open(path, "rb") as fh:
            lines = fh.readlines()[-400:]
    except OSError:
        return None
    for raw in reversed(lines):
        try:
            rec = json.loads(raw.decode("utf-8", "replace"))
        except ValueError:
            continue
        usage = rec.get("usage")
        if usage is None:
            msg = rec.get("message")
            usage = msg.get("usage") if isinstance(msg, dict) else None
        if not isinstance(usage, dict):
            continue
        total = 0
        seen = False
        for key in ("cache_read_input_tokens", "cache_creation_input_tokens", "input_tokens"):
            val = usage.get(key)
            if isinstance(val, int):
                total += val
                seen = True
        if seen:
            return total
    return None


def yield_pct():
    raw = os.environ.get(ENV_PCT)
    try:
        val = int(str(raw).strip())
    except (TypeError, ValueError):
        return DEFAULT_YIELD_PCT
    return val if 1 <= val <= 99 else DEFAULT_YIELD_PCT


def latch_path(transcript, aid):
    return os.path.join(os.path.dirname(transcript), ".reeve-budget-%s" % aid)


def already_told(path):
    return os.path.exists(path)


def mark_told(path):
    try:
        with open(path, "w") as fh:
            fh.write("1")
    except OSError:
        pass


def main():
    payload = _payload()
    if not payload:
        return 0
    aid = agent_id(payload)
    if not aid:
        # The orchestrator's turn — it has its own governor. Also the shape a worker would take
        # if the harness never puts an id on the payload, and the two are indistinguishable from
        # in here; the breadcrumb records the keys that DID arrive so the question is answerable
        # from outside. See the module docstring for how to read it.
        note(payload, "no-agent-id")
        return 0
    path = transcript_path(payload, aid)
    if not path:
        note(payload, "no-transcript", agent_id=aid, tried=tried_paths(payload, aid))
        return 0                      # not positively located — silence, never a guess
    used = occupancy(path)
    if used is None:
        note(payload, "no-usage", agent_id=aid, transcript=path)
        return 0
    pct = 100.0 * used / float(ASSUMED_WINDOW)
    # The ONE breadcrumb that proves something on its own: the reading half just ran, inside a
    # real worker, against a real transcript. Written before the threshold test on purpose —
    # a live mechanism that has not yet had reason to fire must not look like a dead one.
    note(payload, "located", agent_id=aid, transcript=path,
         used=used, pct=round(pct, 1), yield_pct=yield_pct(),
         fired=pct >= yield_pct())
    if pct < yield_pct():
        return 0
    latch = latch_path(path, aid)
    if already_told(latch):
        return 0
    mark_told(latch)
    text = INSTRUCTION % (int(pct), "{:,}".format(used), "{:,}".format(ASSUMED_WINDOW))
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": text,
        },
    }))
    sys.stderr.write(text + "\n")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception:
        sys.exit(0)

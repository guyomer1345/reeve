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


def transcript_path(payload, aid):
    """Where this worker's own JSONL is, or None if it cannot be located POSITIVELY.

    Two routes, tried in order, because the payload shape is not pinned down by the documented
    schema and guessing is how a detector starts lying. If the harness names the transcript,
    that is the answer. Otherwise the per-agent file sits under the session directory as
    `subagents/agent-<id>.jsonl`, which is where the measurement found them. If neither
    resolves to a real file, this hook says nothing at all.
    """
    for key in ("transcript_path", "transcriptPath"):
        val = payload.get(key)
        if isinstance(val, str) and os.path.isfile(val):
            return val
    session = payload.get("transcript_path") or payload.get("session_transcript")
    if isinstance(session, str) and session:
        base = os.path.dirname(session)
        for name in ("agent-%s.jsonl" % aid, "%s.jsonl" % aid):
            cand = os.path.join(base, "subagents", name)
            if os.path.isfile(cand):
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
        return 0                      # the orchestrator's turn; it has its own governor
    path = transcript_path(payload, aid)
    if not path:
        return 0                      # not positively located — silence, never a guess
    used = occupancy(path)
    if used is None:
        return 0
    pct = 100.0 * used / float(ASSUMED_WINDOW)
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

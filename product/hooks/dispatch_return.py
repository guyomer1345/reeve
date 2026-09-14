#!/usr/bin/env python3
"""PostToolUse(Agent/Task): notice when a dispatched worker returns bulk instead of a pointer.

WHY THIS IS A HOOK AT ALL, GIVEN IT CANNOT BLOCK
By the time this runs the worker has finished and the payload is already on its way into the
caller's context, so there is nothing to prevent — PostToolUse is documented as unable to block,
and pretending otherwise would be a judgement wearing a gate's clothes. What it CAN do is the
useful half: say, at the moment it happens and in the caller's own transcript, that the return
broke its contract, so the caller drops it to a path instead of carrying it for the rest of the
item and so the breach leaves a mark rather than being absorbed silently. The contract itself
(`shared/schemas.md` § dispatch-return) stays an agent-brief rule; this is a detector, not its
enforcement, and the brief says so in those words.

WHAT IT MEASURES, AND WHY IN CHARACTERS
The size of the text the dispatch handed back, in characters, because a hook that ships with the
package cannot assume a tokenizer. The ceiling below is an ABSURDITY CEILING, not a budget. No
distribution of return SIZES has ever been measured in this package — what has been measured is
the caller-side effect, and a dispatched node's median contribution to the caller's window is
0.0k against an inline node's 12.0k, i.e. returns are already tiny at the median. A threshold set
anywhere near a median strangles the normal case to catch nothing; this one is placed where the
only plausible way to reach it is that a file body, a diff, or raw tool output was pasted back.
If that ever stops being true, the honest fix is to measure and move it, not to soften the text.

WHAT IT DELIBERATELY IGNORES
  - dispatches to anything that is not one of this package's own agents. The contract is this
    package's; an ordinary search dispatch to a general worker never agreed to it, and warning
    about it would train the caller to ignore the warning that matters. (The complementary rule
    — a LOOP NODE may not go to a general worker at all — is `dispatch_guard.py`'s, at PreToolUse.)
  - any payload whose text this cannot positively extract. The shape of `tool_response` for a
    subagent dispatch is not pinned down by the documented schema, so an unrecognised shape means
    "not measured", and not-measured must read as silence. A detector that guesses a size is
    worse than one that is quiet: the warning it emits is unfalsifiable by the reader.
It also never writes a file and never touches loop state. A detector that can corrupt the thing
it observes has made the trade backwards.

FAILURE MODES, ON PURPOSE
Every one of them exits 0 and says nothing: unreadable stdin, a payload shape it does not know,
a missing field. This hook runs after every single dispatch in the loop; the one behaviour it
must never have is noise, and the one thing it must never do is interfere with a return that is
already fine.
"""
import json
import re
import sys

PLUGIN = "reeve"
DISPATCH_TOOLS = {"Agent", "Task"}
# The dispatched capabilities, per the orchestrator brief's "How to run a node". Bare names are
# accepted alongside the namespaced spelling because a dispatch may be written either way.
DISPATCHED = {"execute", "document", "create-demo", "research", "setup-guide"}
# ~20k characters is ~5k tokens at the usual 4-chars-per-token rule of thumb — several times any
# condensed-result-plus-pointers return, and about the size of one medium source file pasted whole.
CEILING_CHARS = 20000


def read_payload():
    try:
        return json.load(sys.stdin)
    except (ValueError, OSError):
        return None


def is_package_agent(subagent_type):
    """True only for this package's own dispatched capabilities."""
    if not isinstance(subagent_type, str):
        return False
    if ":" in subagent_type:
        namespace, name = subagent_type.split(":", 1)
        if namespace.strip() != PLUGIN:
            return False
    else:
        name = subagent_type
    return name.strip() in DISPATCHED


def extract_text(response):
    """Flatten a tool_response to the text it carries, or None if the shape is unknown.

    None is a first-class answer here and is returned rather than an empty string, so the caller
    can tell "nothing came back" (measurable, and fine) apart from "this is not a shape I can
    read" (not measurable, and must stay silent).
    """
    if isinstance(response, str):
        return response
    if isinstance(response, dict):
        for key in ("text", "content", "output", "result"):
            if key in response:
                nested = extract_text(response[key])
                if nested is not None:
                    return nested
        return None
    if isinstance(response, list):
        parts = [extract_text(block) for block in response]
        found = [p for p in parts if p is not None]
        return "".join(found) if found else None
    return None


# Line 1 of a return is `status: done|continue|question|blocked`. Read leniently — leading
# whitespace, a bold or fenced spelling, any case — because a return that MEANT to declare its
# status and spelled it oddly is not the failure worth reporting. What is worth reporting is a
# return that declares nothing, because the caller then has to read prose to find out what
# happened, which is the habit the typed envelope exists to end.
STATUSES = ("done", "continue", "question", "blocked")
STATUS_RE = re.compile(r"(?im)^\W{0,4}status\W{0,4}\s*(%s)\b" % "|".join(STATUSES))


def declared_status(text):
    """The status this return declares, or None. Searched over the HEAD of the payload only —
    a `status:` line 400 lines down is prose about a status, not a declaration of one."""
    if not isinstance(text, str):
        return None
    m = STATUS_RE.search("\n".join(text.splitlines()[:5]))
    return m.group(1).lower() if m else None


def main():
    payload = read_payload()
    if not isinstance(payload, dict):
        return 0
    if payload.get("tool_name") not in DISPATCH_TOOLS:
        return 0
    tool_input = payload.get("tool_input")
    if not isinstance(tool_input, dict):
        return 0
    agent = tool_input.get("subagent_type")
    if not is_package_agent(agent):
        return 0
    text = extract_text(payload.get("tool_response"))
    if text is None:
        return 0

    status = declared_status(text)
    if status is None:
        # Not a size complaint, and deliberately reported even when the return is small: an
        # untyped return is not too big, it is UNROUTABLE. The caller is told once, here, rather
        # than working it out from prose every time.
        sys.stderr.write(
            "dispatch-return is UNTYPED: `%s` returned no `status:` line, so there is nothing to "
            "route on. Line 1 of a return is `status: done|continue|question|blocked` "
            "(`shared/schemas.md` section dispatch-return).\n"
            "The tool call succeeded and nothing is being undone. Read the return and decide "
            "which of the four it was before you act on it — and if you re-dispatch for this "
            "item, say in the prompt that line 1 must carry the status.\n" % agent)
        return 2

    if len(text) <= CEILING_CHARS:
        return 0

    # Exit 2 on PostToolUse shows stderr to the model as a warning and blocks nothing — which is
    # the whole available action, and the right one: the work is done, so the only thing left
    # worth changing is what the caller carries forward from it.
    sys.stderr.write(
        "dispatch-return over contract: `%s` returned %d characters against a %d ceiling. The "
        "contract is a condensed result plus pointers; a return this size is a file body, a diff "
        "or raw tool output pasted back.\n"
        "The tool call succeeded and nothing is being undone. What to do with it:\n"
        "  - Do NOT carry this payload forward. Take the paths, ids and the verdict out of it and "
        "work from those; re-read the files when you need them.\n"
        "  - Heavy raw material belongs in `.workflow/items/<id>/scratch/`, written there by the "
        "worker and left there — not handed back.\n"
        "  - If you re-dispatch for this item, say so in the prompt: the return is a pointer, the "
        "bulk goes to scratch. See `shared/schemas.md` section dispatch-return.\n"
        % (agent, len(text), CEILING_CHARS)
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())

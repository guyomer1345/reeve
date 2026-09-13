#!/usr/bin/env python3
"""Interactive context governor — the statusline half.

Claude Code invokes this every turn with a status JSON on stdin. The statusline is
the ONLY surface the running token count is exposed to (hooks and the model receive
no token metrics), so the context-budget warning MUST originate here. This script:

  1. Renders the BASE status line — delegating to a pre-existing user statusline if
     `/start` captured one into `.workflow/statusline.delegate` (compose, never
     clobber); otherwise a minimal `model · dir · ctx N%` line.
  2. PUBLISHES the reading to `.workflow/context.json`. This is the one crossing of a
     real wall: the statusline can SEE the token count and cannot act on it, while the
     loop can act and cannot see it. Until this existed nothing crossed — the banner
     went to a human's eyes and that was the whole channel. `context_band.py` is the
     arithmetic over the published reading; this script is only its sensor.
  3. Appends a banner carrying the BAND verdict (`context_band.py`) — two-sided, in
     units of work rather than a fraction: hold while there is runway, hand off at the
     next clean boundary in the middle, hand off now once what is left is needed to
     finish the item and write a complete anchor. The old rule was a one-sided
     `pct >= config.context.warn_pct`, which could say "go" and never "not yet", so
     under-use was invisible and unpriced.

It never crashes the status line: any failure degrades to the best line it can print
and always exits 0 (a non-zero exit blanks the status line entirely).
"""
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

WARN_PCT_DEFAULT = 30


def _project_dir(status):
    ws = status.get("workspace") or {}
    return ws.get("project_dir") or ws.get("current_dir") or status.get("cwd") or "."


def _warn_pct_configured(project_dir):
    """config.context.warn_pct as the operator SET it, or None when they did not.

    Distinct from `_warn_pct` below, and the distinction is load-bearing: an explicitly set
    percentage is a standing instruction that outranks the band's arithmetic, while an ABSENT
    one must not be silently materialised into a ceiling nobody asked for — that would make the
    band unreachable, since a default 30% ceiling fires long before runway ever runs low.
    """
    try:
        with open(os.path.join(project_dir, ".workflow", "config.json")) as fh:
            cfg = json.load(fh)
        pct = (cfg.get("context") or {}).get("warn_pct")
        if isinstance(pct, (int, float)) and 0 < pct <= 100:
            return float(pct)
    except Exception:
        pass
    return None


def _warn_pct(project_dir):
    """The percentage to use when runway is NOT computable (no window size reported). Absent →
    the shipped default, because in that degraded path a coarse signal beats none."""
    try:
        with open(os.path.join(project_dir, ".workflow", "config.json")) as fh:
            cfg = json.load(fh)
        pct = (cfg.get("context") or {}).get("warn_pct")
        if isinstance(pct, (int, float)) and 0 < pct <= 100:
            return float(pct)
    except Exception:
        pass
    return float(WARN_PCT_DEFAULT)


def _tokens(status):
    """(used, window) in tokens, or (None, None). The band needs ABSOLUTE numbers: a fraction
    makes a 200k and a 1M window read the same while leaving them 5 and 25 nodes of runway."""
    cw = status.get("context_window") or {}
    used = cw.get("total_input_tokens")
    size = cw.get("context_window_size")
    if isinstance(used, (int, float)) and isinstance(size, (int, float)) and size > 0:
        return float(used), float(size)
    # Only a percentage available: reconstruct against the reported size if there is one.
    p = cw.get("used_percentage")
    if isinstance(p, (int, float)) and isinstance(size, (int, float)) and size > 0:
        return float(size) * float(p) / 100.0, float(size)
    return None, None


def _used_pct(status):
    """Prefer the pre-computed percentage; fall back to token math; None if unknown."""
    cw = status.get("context_window") or {}
    p = cw.get("used_percentage")
    if isinstance(p, (int, float)):
        return float(p)
    used = cw.get("total_input_tokens")
    size = cw.get("context_window_size")
    if isinstance(used, (int, float)) and isinstance(size, (int, float)) and size > 0:
        return 100.0 * used / size
    return None


def _delegate_line(project_dir, raw_stdin):
    """Run a captured user statusline with the same stdin; its stdout is the base.
    Returns None when there is no delegate or it fails (caller renders a minimal base)."""
    path = os.path.join(project_dir, ".workflow", "statusline.delegate")
    try:
        with open(path) as fh:
            cmd = fh.read().strip()
    except Exception:
        return None
    if not cmd:
        return None
    try:
        r = subprocess.run(
            cmd, shell=True, input=raw_stdin,
            capture_output=True, text=True, timeout=5,
        )
    except Exception:
        return None
    out = (r.stdout or "").rstrip("\n")
    return out if out else None


def _minimal_base(status, pct):
    model = (status.get("model") or {}).get("display_name") or "claude"
    project_dir = _project_dir(status)
    where = os.path.basename(os.path.normpath(project_dir)) or project_dir
    parts = [model, where]
    if pct is not None:
        parts.append("ctx %d%%" % round(pct))
    return " · ".join(parts)


# Colour by urgency rather than one alarm state: a band that shouts at every reading is one a
# human stops reading, and `hold` is a real verdict that must not look like a warning.
_BAND_STYLE = {"handoff-now": "1;31", "handoff-at-boundary": "1;33"}


def _banner(verdict):
    """The band's line, or None when there is nothing to say. `hold` prints NOTHING — the
    runway figure is already on the base line, and a persistent "you are fine" banner is how a
    status line teaches someone to ignore it."""
    style = _BAND_STYLE.get(verdict.get("verdict"))
    if not style:
        return None
    lead = "⚠ hand off NOW" if verdict["verdict"] == "handoff-now" else "◆ hand off at the next boundary"
    return "\033[%sm%s — %s\033[0m" % (style, lead, verdict["reason"])


def main():
    raw = ""
    try:
        raw = sys.stdin.read()
    except Exception:
        print("")
        return 0
    try:
        status = json.loads(raw) if raw.strip() else {}
    except Exception:
        status = {}

    project_dir = _project_dir(status)
    pct = _used_pct(status)

    base = _delegate_line(project_dir, raw)
    if base is None:
        base = _minimal_base(status, pct)

    lines = [base]
    # Publish first, render second. The published reading is what everything OTHER than this
    # human's eyes depends on, so it must not be lost to a rendering failure below it.
    verdict = None
    try:
        import time
        import context_band
        used, window = _tokens(status)
        if used is not None:
            context_band.publish(os.path.join(project_dir, ".workflow"), used, window,
                                 time.monotonic())
            verdict = context_band.band(used, window, _warn_pct_configured(project_dir))
    except Exception:
        verdict = None
    if verdict is None and pct is not None and pct >= _warn_pct(project_dir):
        # No absolute token counts, so runway in nodes is not computable. Degrade to the
        # fraction rule rather than going quiet: a percentage is the wrong UNIT, not a wrong
        # signal, and a silent status line is worse than a coarse one.
        verdict = {"verdict": "handoff-now",
                   "reason": "context %d%% ≥ %d%% — run /dispatch then /clear to reset (no "
                             "window size reported, so runway in nodes is not computable)"
                             % (round(pct), round(_warn_pct(project_dir)))}
    if verdict:
        line = _banner(verdict)
        if line:
            lines.append(line)
        runway = verdict.get("runway_nodes")
        if runway is not None and pct is not None:
            lines[0] = lines[0] + " · ~%.0f nodes left" % runway

    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        # Last-resort: never blank the line into a traceback / non-zero exit.
        print("")
        sys.exit(0)

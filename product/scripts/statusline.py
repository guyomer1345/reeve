#!/usr/bin/env python3
"""Interactive context governor — the statusline half.

Claude Code invokes this every turn with a status JSON on stdin. The statusline is
the ONLY surface the running token count is exposed to (hooks and the model receive
no token metrics), so the context-budget warning MUST originate here. This script:

  1. Renders the BASE status line — delegating to a pre-existing user statusline if
     `/start` captured one into `.workflow/statusline.delegate` (compose, never
     clobber); otherwise a minimal `model · dir · ctx N%` line.
  2. Appends a persistent banner once context usage crosses `config.context.warn_pct`
     (a PERCENTAGE, so it is model-window-agnostic — a 200k and a 1M window warn at
     the same fraction full), telling the human to run `/dispatch` then `/clear`.

It never crashes the status line: any failure degrades to the best line it can print
and always exits 0 (a non-zero exit blanks the status line entirely).
"""
import json
import os
import subprocess
import sys

WARN_PCT_DEFAULT = 75


def _project_dir(status):
    ws = status.get("workspace") or {}
    return ws.get("project_dir") or ws.get("current_dir") or status.get("cwd") or "."


def _warn_pct(project_dir):
    """Read config.context.warn_pct (committed, never relocated). Absent → default."""
    try:
        with open(os.path.join(project_dir, ".workflow", "config.json")) as fh:
            cfg = json.load(fh)
        pct = (cfg.get("context") or {}).get("warn_pct")
        if isinstance(pct, (int, float)) and 0 < pct <= 100:
            return float(pct)
    except Exception:
        pass
    return float(WARN_PCT_DEFAULT)


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


def _banner(pct, warn):
    # Bold red so it stands out against any base line. Persistent while over threshold.
    return ("\033[1;31m⚠ context %d%% ≥ %d%% — run /dispatch then /clear to reset\033[0m"
            % (round(pct), round(warn)))


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
    if pct is not None and pct >= _warn_pct(project_dir):
        lines.append(_banner(pct, _warn_pct(project_dir)))

    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        # Last-resort: never blank the line into a traceback / non-zero exit.
        print("")
        sys.exit(0)

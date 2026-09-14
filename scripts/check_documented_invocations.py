#!/usr/bin/env python3
"""Every `.claude/scripts/<tool>` invocation the package DOCUMENTS must actually parse.

WHY THIS EXISTS. The first smoke drive found `prioritize/SKILL.md` telling the orchestrator to
run `converge.py status --workflow-dir .workflow`, which **errors**: `--workflow-dir` is a
top-level option and the subcommand comes last. A shipped instruction to run a command that
cannot run. No unit test saw it — every test calls these tools with the argument order the tool
itself uses — and no reader saw it either, because both orders look equally plausible in prose.

A live drive found it in minutes, which is the argument for live drives. This gate is the
argument for not needing one twice: it extracts every documented invocation of a shipped script
and asks that script's OWN parser whether it would accept it.

WHAT IT CHECKS, and what it deliberately does not. It parses arguments only — `--help`-level
validation through `argparse`, with no side effects and nothing executed. It cannot tell whether
a documented invocation is the RIGHT one to run at that moment; it can only tell that it is not
a command that dies on contact. That is the defect class it is here for.

Placeholders (`<id>`, `<ids…>`, `…`) are substituted with harmless stand-ins, because a document
that spells out a real id would be worse.
"""
import argparse
import glob
import importlib
import os
import re
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
PRODUCT = os.path.join(ROOT, "product")
SCRIPTS = os.path.join(PRODUCT, "scripts")
sys.path.insert(0, SCRIPTS)

# `python3 .claude/scripts/<name>.py <args…>` inside a backticked span.
INVOCATION = re.compile(r"`python3 \.claude/scripts/([A-Za-z_][\w.]*\.py)([^`]*)`")
PLACEHOLDER = re.compile(r"<[^>]+>|…")


class _Captured(Exception):
    def __init__(self, parser):
        self.parser = parser


def parser_for(script):
    """The script's OWN parser, fully built, without running a line of its work.

    NOTHING IS EXECUTED, and that is the whole design. Running a documented invocation to see
    whether it parses would run it — `drain.py record --applied x` would actually record. So
    `parse_args` is intercepted: every one of these scripts builds its parser and then calls it,
    so the interception fires with the parser complete and the body untouched.
    """
    mod = importlib.import_module(script[:-3])
    if not hasattr(mod, "main"):
        return None
    real = argparse.ArgumentParser.parse_args

    def capture(self, *a, **kw):
        raise _Captured(self)

    argparse.ArgumentParser.parse_args = capture
    try:
        mod.main([])
    except _Captured as c:
        return c.parser
    except BaseException:
        return None
    finally:
        argparse.ArgumentParser.parse_args = real
    return None


def documented():
    for path in sorted(glob.glob(os.path.join(PRODUCT, "**", "*.md"), recursive=True)):
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
        for m in INVOCATION.finditer(text):
            yield os.path.relpath(path, ROOT), m.group(1), m.group(2).strip()


def main():
    errs, checked, unchecked = [], 0, set()
    cache = {}
    for doc, script, args in documented():
        if not os.path.exists(os.path.join(SCRIPTS, script)):
            errs.append("%s documents %s, which the package does not ship" % (doc, script))
            continue
        argv = [PLACEHOLDER.sub("x", a) for a in args.split()]
        if not argv or any(a in ("|", "&&", ">", ">>") for a in argv):
            continue
        if script not in cache:
            cache[script] = parser_for(script)
        parser = cache[script]
        if parser is None:
            unchecked.add(script)
            continue
        checked += 1
        buf, real_err, real_exit = [], parser.error, parser.exit

        def _err(message, _buf=buf):
            _buf.append(message)
            raise _Captured(None)

        def _exit(status=0, message=None, _buf=buf):
            if status:
                _buf.append(message or "exit %s" % status)
            raise _Captured(None)

        parser.error, parser.exit = _err, _exit
        try:
            parser.parse_args(argv)
        except _Captured:
            pass
        except BaseException as exc:
            buf.append(repr(exc))
        finally:
            parser.error, parser.exit = real_err, real_exit
        if buf:
            errs.append("%s: `%s %s` — %s" % (doc, script, args, buf[0].strip()))

    if errs:
        print("documented-invocation check: INVALID — the package documents a command that "
              "cannot run")
        for e in errs:
            print("  - %s" % e)
        return 1
    print("OK: documented invocations — %d checked, all parse%s"
          % (checked, (" (%d script(s) not argparse-based, skipped)" % len(unchecked))
             if unchecked else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())

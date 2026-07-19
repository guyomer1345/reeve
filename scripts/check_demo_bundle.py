#!/usr/bin/env python3
"""Lint a throwaway demo-sandbox bundle for the format discipline the serving CSP does
NOT enforce.

The bundle is served under `Content-Security-Policy: sandbox allow-scripts allow-forms`.
That directive buys ISOLATION — an opaque origin the demo cannot escape — and nothing
else: measured in a real browser, `eval`, `new Function`, and external hosts all still
run/load under it. So "self-contained, no external hosts, no eval" — the invariants that
make a demo render identically offline and over a tunnel, never phoning home — are not a
CSP fact. They are a create-demo authoring rule, and this is their mechanical floor: a
cheap, deterministic scan run before the demo is parked, so a slip fails LOUDLY at
generation instead of shipping a demo that quietly depends on a CDN and blanks over the
tunnel.

Stdlib only. Exit 0 = clean; exit 1 = violations (printed one per line); exit 2 = usage.

  check_demo_bundle.py <bundle-dir>
"""
import os
import re
import sys

# Text asset extensions worth scanning. Binary local assets (png/woff2/…) are fine by
# being local; an external font/image is a URL inside CSS/HTML, caught below.
TEXT_EXT = {".html", ".htm", ".js", ".mjs", ".css", ".json", ".svg", ".txt", ".map"}

# The XML/SVG namespace URIs are identifiers, never fetched — the one legitimate http(s)
# literal in a self-contained bundle. Everything else that looks like a URL is a network
# dependency that breaks offline / over the tunnel.
_NS_OK = "http://www.w3.org/"

CHECKS = (
    # (label, compiled regex, a note the fixer can act on)
    ("external-host",
     re.compile(r"https?://(?!www\.w3\.org/)[^\s\"')]+", re.I),
     "an http(s) resource — vendor it locally or inline it (the demo must render offline)"),
    ("protocol-relative-url",
     re.compile(r"""(?:src|href)\s*=\s*["']//|url\(\s*["']?//""", re.I),
     "a //host URL — same as an external host; make it local"),
    ("eval",
     re.compile(r"\beval\s*\(|\bnew\s+Function\s*\(", re.I),
     "eval / new Function — not needed for a low-fi demo, and a code smell"),
    ("babel-jsx",
     re.compile(r"""type\s*=\s*["']text/babel["']|@babel/standalone|@babel""", re.I),
     "runtime JSX/Babel — huge and needs unsafe-eval; write vanilla or vendored htm+preact"),
    ("bundler-dep",
     re.compile(r"\bnode_modules\b|\brequire\s*\(", re.I),
     "an npm/bundler dependency — the bundle must be build-free and self-contained"),
)


def scan_text(path, text):
    """Yield (lineno, label, snippet, note) for every violation in one file."""
    for lineno, line in enumerate(text.splitlines(), 1):
        for label, rx, note in CHECKS:
            m = rx.search(line)
            if m:
                snippet = m.group(0)
                if len(snippet) > 80:
                    snippet = snippet[:77] + "..."
                yield lineno, label, snippet, note


def lint(bundle_dir):
    """Return a list of violation strings (empty => clean)."""
    violations = []
    if not os.path.isdir(bundle_dir):
        return ["%s: not a directory" % bundle_dir]
    if not os.path.exists(os.path.join(bundle_dir, "index.html")):
        violations.append("%s: no index.html (a bundle's entry point is index.html)"
                          % bundle_dir)
    for root, _dirs, files in os.walk(bundle_dir):
        for name in sorted(files):
            ext = os.path.splitext(name)[1].lower()
            full = os.path.join(root, name)
            rel = os.path.relpath(full, bundle_dir)
            if ext not in TEXT_EXT:
                continue
            try:
                with open(full, "r", errors="replace") as fh:
                    text = fh.read()
            except OSError as exc:
                violations.append("%s: cannot read (%s)" % (rel, exc))
                continue
            for lineno, label, snippet, note in scan_text(full, text):
                violations.append("%s:%d: %s: %s — %s"
                                  % (rel, lineno, label, snippet, note))
    return violations


def main(argv):
    if len(argv) != 2:
        sys.stderr.write("usage: check_demo_bundle.py <bundle-dir>\n")
        return 2
    violations = lint(argv[1])
    if violations:
        sys.stderr.write("BLOCKED: demo bundle is not self-contained "
                         "(the serving CSP will not catch this):\n")
        for v in violations:
            sys.stderr.write("  " + v + "\n")
        return 1
    print("OK: demo bundle is self-contained (no external hosts, no eval, build-free)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

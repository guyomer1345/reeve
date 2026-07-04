#!/usr/bin/env python3
"""Code-map extractor — emits the structural knowledge layer as graph.json.

Multi-language engine: one shared driver (discover -> dispatch -> resolve -> PageRank ->
emit) over pluggable per-language ARMS. What varies by language is only *edge resolution*;
the node set + directory clusters are identical everywhere, so the cost of a language is
its resolver, not its parser. Ships five precise arms + the floor:

  - PythonArm   (tier 2) — stdlib `ast`, zero-dep, precise dotted-module resolution.
  - JsTsArm     (tier 2) — JS/TS: tsconfig/jsconfig `paths`+`baseUrl` aliases, TS/JS extension
                           + index/barrel resolution, workspace packages (npm/pnpm/yarn) by
                           exact name, and package.json exports/imports subpath maps (incl.
                           dist->src derivation for unbuilt monorepos). Ground-truth measured on
                           express/vue/vite/hono: 0 fabricated edges, ~87-100% relative + ~95-100%
                           workspace recall. Zero extra dep; no tsconfig -> == the floor.
  - GoArm       (tier 2) — package==directory: reads go.mod module paths, resolves module-prefixed
                           imports to the target dir, edges to every non-test .go file. 100% intra
                           recall + 0 fabrication on gin/cobra. (The old floor got 0% AND fabricated
                           stdlib edges — `import "errors"` hitting a local errors.go.)
  - JavaArm     (tier 2) — two-pass: pass 1 indexes top-level types -> FQN; pass 2 resolves imports
                           + same-package simple names + inline FQNs (the ~24% of edges that carry
                           NO import statement, measured on gson). Unknown Capitalized tokens never
                           edge (java.*/third-party drop out). Same-package precision measured ~100%
                           on commons-lang (976 same-pkg edges) + okhttp — Java's camelCase members
                           make a type/member name collision rare.
  - CSharpArm   (tier 2) — namespace-aware two-pass; namespace decoupled from dir AND file. Resolves
                           `using` (to the intersection of the namespace's types with the file's used
                           HEAD tokens), same-namespace refs, inline FQNs, `using static`. A member-
                           access token (`x.Order`, `.Include<>()`, `MemberList.Source`) is filtered
                           out of the type channels. Intersection precision measured 98.9% (AutoMapper,
                           fluent-DSL worst case) / ~99.5% harmful (eShopOnWeb app code).
  - GenericArm  (tier 0) — the generic floor: NODES any recognized source language, and adds
                           shallow-regex import edges for the subset that has them. The long-tail
                           safety net so a repo in ANY recognized language gets at least nodes +
                           directory clusters + both centrality lenses, never nothing.

More precise arms (C++, …) plug into the same contract: a new arm is a `class Arm` with
`extensions`, `index()`, and `edges()` — the driver below is untouched.

Standing rule — BIAS PRECISION over recall for the static arms. A fabricated edge is sticky:
nothing the loop does can retract it (runtime observation only ADDS missed edges — "not
exercised" != "not a dependency"), so a false positive persists and misleads blast-radius /
orchestration reads forever. A missed edge self-heals: the durable observed layer accretes the
recall the arms leave on the table where the code is actually exercised. So when a channel
measures noisy, tighten toward precision (a type-position anchor, stricter matching) and accept
the recall loss — e.g. the C# arm filters member-access tokens out of its type channels.

Rust (`mod`) and PHP (`require`) stay on the tier-0 floor deliberately: the floor's relative /
sibling resolution is the sound subset, and a precise arm is built only when a real repo needs
one (build set by prevalence, not ease). C++ likewise stays on the floor — a precise arm needs
`compile_commands.json`; the quoted-`#include` relative resolution is the sound subset.

Two centrality signals per file fall out of the one import graph for free:
  - impact        (forward PageRank: most-depended-upon)  -> change blast-radius
  - orchestration (reverse PageRank: composes many)       -> where behaviour lives
Neither is "importance." This is the GENERATED structural layer: regenerable, never
authoritative prose, never hand-edited. The durable per-file `why` / `# Sessions` live in
the node .md files and are authored on touch by `document`; this tool never writes those.

Usage:  codemap.py [ROOT] [--out PATH] [--exclude a,b,c]
  ROOT      directory to scan (default: .). Run from the import root so module names
            match import statements (e.g. repo root for `from pkg.mod import x`).
  --out     output path (default: docs/knowledge/graph.json).

graph.json per-node: path, type, lang, tier, impact, orchestration, in_degree, out_degree.
The top-level `languages` map reports, per language, file/edge counts + a **`fidelity`** level
(high / medium / low / nodes-only) and **`known_gaps`** — the honest trust signal a consumer
must weight edges by. `tier` is only WHICH arm produced the edges; it is NOT a completeness
claim (a tier-2 arm can still be a poor approximation — measure fidelity, don't infer it).
"""
import argparse
import ast
import collections
import fnmatch
import json
import os
import re
import sys

DEFAULT_EXCLUDE = (
    ".git", ".hg", ".svn",
    ".venv", "venv", "env", "node_modules", "bower_components", "__pycache__",
    "migrations", "dist", "build", "out", "target", "vendor", "Pods",
    ".next", ".nuxt", ".gradle", "bin", "obj",
    ".mypy_cache", ".pytest_cache", ".ruff_cache", ".tox", ".idea", ".vscode",
)


# --------------------------------------------------------------------------- #
# Python arm (tier 2) — stdlib ast, precise dotted-module resolution.
# --------------------------------------------------------------------------- #
def _module_name(path):
    """Module dotted-name relative to cwd (the import root)."""
    rel = os.path.relpath(path).replace(os.sep, ".")
    if rel.endswith(".py"):
        rel = rel[:-3]
    if rel.endswith(".__init__"):
        rel = rel[: -len(".__init__")]
    return rel


def _py_resolve(mod, mod2file):
    """Resolve a dotted module (or a prefix of it) to a known project file, else None."""
    cand = mod
    while cand:
        if cand in mod2file:
            return mod2file[cand]
        cand = cand.rsplit(".", 1)[0] if "." in cand else ""
    return None


def _py_import_targets(tree, self_mod):
    """Yield dotted module names this file imports (absolute + relative resolved).

    For `from M import n1, n2` yield the most-specific `M.n1`, `M.n2` and let _py_resolve
    walk up: an imported submodule resolves to itself, a name defined in M walks up to M.
    Yielding the specific target first avoids a spurious edge to M's package `__init__` on
    `from pkg import submodule` (which would inflate `__init__` centrality).
    """
    self_pkg = self_mod.rsplit(".", 1)[0] if "." in self_mod else ""
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.level:  # relative: climb `level` packages from self
                base = self_pkg
                for _ in range(node.level - 1):
                    base = base.rsplit(".", 1)[0] if "." in base else ""
                mod = f"{base}.{node.module}" if node.module else base
            else:
                mod = node.module or ""
            if mod:
                names = [a.name for a in node.names if a.name != "*"]
                if names:
                    for name in names:
                        yield f"{mod}.{name}"
                else:  # `from mod import *`
                    yield mod
        elif isinstance(node, ast.Import):
            for alias in node.names:
                yield alias.name


class PythonArm:
    name = "python"
    tier = 2
    node_type = "module"
    extensions = frozenset({".py"})
    fidelity = "high"  # explicit-import language + real parser (ast); edges ARE imports.
                       # Ground-truth re-confirmed on flask: 40/40 sampled edges are real resolved
                       # imports (0 fabricated); both gaps below present (8 dynamic-import files, 5 __init__).
    known_gaps = ("dynamic imports (importlib/__import__)", "__init__ re-export aliasing")

    def lang_of(self, path):
        return "python"

    def index(self, files):
        return {_module_name(p): p for p in files}

    def edges(self, path, source, index):
        tree = ast.parse(source, filename=path)  # SyntaxError -> caught by driver
        self_mod = _module_name(path)
        out = set()
        for mod in _py_import_targets(tree, self_mod):
            target = _py_resolve(mod, index)
            if target and target != path:
                out.add(target)
        return out


# --------------------------------------------------------------------------- #
# Generic arm (tier 0) — the floor. Shallow-regex imports + best-effort resolution.
# --------------------------------------------------------------------------- #
# ext -> (language, resolution-mode, [regexes]); each regex captures group "spec".
# Resolution mode encodes the language family's import semantics (precision > recall):
#   rel      relative-only (JS/TS/PHP-esque ESM/Node): resolve iff spec starts with "." —
#            a bare/subpath specifier is an EXTERNAL package, never an intra-repo file.
#   include  C/C++ quoted #include: resolve relative to the including file, else a unique
#            basename match anywhere (a quoted include IS a project file).
#   pkg      package-path (Java/C#/Kotlin/Scala): dotted spec -> path-suffix match of >=2
#            segments (package + name), so a stdlib import can't collide on a bare name.
#   path     path-or-relative (Ruby/Go/Dart): try relative-to-dir (require_relative 'x'),
#            else a >=2-segment slashed suffix match; a bare token is external -> dropped.
#   mod      Rust `mod foo;`: a sibling `foo.rs` or `foo/mod.rs`.
_JS_PATTERNS = [
    re.compile(r"""\bimport\s+[^'";]*?\bfrom\s*['"](?P<spec>[^'"]+)['"]"""),  # import x from '...'
    re.compile(r"""\bimport\s*['"](?P<spec>[^'"]+)['"]"""),                    # import '...'
    re.compile(r"""\bexport\s+[^'";]*?\bfrom\s*['"](?P<spec>[^'"]+)['"]"""),   # export ... from '...'
    re.compile(r"""\brequire\s*\(\s*['"](?P<spec>[^'"]+)['"]\s*\)"""),          # require('...')
    re.compile(r"""\bimport\s*\(\s*['"](?P<spec>[^'"]+)['"]\s*\)"""),           # import('...') dynamic
]
_JS_EXTS = (".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx", ".mts", ".cts")
_TS_EXTS = (".ts", ".tsx", ".mts", ".cts")
_C_PATTERNS = [re.compile(r'^[^\S\n]*#[^\S\n]*include[^\S\n]*"(?P<spec>[^"]+)"', re.MULTILINE)]  # "..." only; <...>=system
_CPP_EXTS = (".cc", ".cpp", ".cxx", ".hpp", ".hh", ".hxx", ".inl")
_C_EXTS = (".c", ".h") + _CPP_EXTS
_LANGUAGES = {
    ".go": ("go", "path", [
        re.compile(r'^\s*import\s+(?:[A-Za-z_.]+\s+)?"(?P<spec>[^"]+)"', re.MULTILINE),  # import "path"
        re.compile(r'^\s*(?:[A-Za-z_.]+\s+)?"(?P<spec>[^"]+)"\s*$', re.MULTILINE),       # inside import ( ... )
    ]),
    ".rs": ("rust", "mod", [
        re.compile(r'^\s*(?:pub(?:\([^)]*\))?\s+)?mod\s+(?P<spec>[A-Za-z0-9_]+)\s*;', re.MULTILINE),  # mod foo;
    ]),
    ".java": ("java", "pkg", [re.compile(r'^\s*import\s+(?:static\s+)?(?P<spec>[\w.]+)\s*;', re.MULTILINE)]),
    ".kt": ("kotlin", "pkg", [re.compile(r'^\s*import\s+(?P<spec>[\w.]+)', re.MULTILINE)]),
    ".scala": ("scala", "pkg", [re.compile(r'^\s*import\s+(?P<spec>[\w.]+)', re.MULTILINE)]),
    ".cs": ("csharp", "pkg", [re.compile(r'^\s*using\s+(?:static\s+)?(?P<spec>[\w.]+)\s*;', re.MULTILINE)]),
    ".rb": ("ruby", "path", [
        re.compile(r'\brequire_relative\s+["\'](?P<spec>[^"\']+)["\']'),
        re.compile(r'\brequire\s+["\'](?P<spec>[^"\']+)["\']'),
    ]),
    ".php": ("php", "path", [
        re.compile(r'\b(?:require|include)(?:_once)?\s*\(?\s*["\'](?P<spec>[^"\']+)["\']'),
    ]),
    ".swift": ("swift", "pkg", [re.compile(r'^\s*import\s+(?P<spec>[\w.]+)', re.MULTILINE)]),
    ".dart": ("dart", "path", [re.compile(r'''\bimport\s+["'](?P<spec>[^"']+)["']''')]),
}
for _e in _JS_EXTS:
    _LANGUAGES[_e] = ("typescript" if _e in _TS_EXTS else "javascript", "rel", _JS_PATTERNS)
for _e in _C_EXTS:
    _LANGUAGES[_e] = ("cpp" if _e in _CPP_EXTS else "c", "include", _C_PATTERNS)

# The floor NODES a broad set of programming-language source files but EXTRACTS edges only
# for the `_LANGUAGES` subset above that has an import regex. Separating the two is what makes
# tier-0 a true long-tail net: an un-armed language (no regex) still gets a node + directory
# cluster (edges empty), never nothing — the floor's whole reason to exist. Data / markup /
# config / doc artifacts (json, yaml, md, html, css, sql, lockfiles, …) are deliberately left
# out: they have no import graph and would flood the node set (graphless artifacts).
_NODE_ONLY = {  # source languages we node but don't yet extract edges for (ext -> language)
    ".ex": "elixir", ".exs": "elixir", ".erl": "erlang", ".hrl": "erlang",
    ".hs": "haskell", ".lhs": "haskell", ".ml": "ocaml", ".mli": "ocaml",
    ".fs": "fsharp", ".fsx": "fsharp", ".fsi": "fsharp", ".vb": "vbnet",
    ".clj": "clojure", ".cljs": "clojure", ".cljc": "clojure",
    ".lua": "lua", ".jl": "julia", ".r": "r", ".pl": "perl", ".pm": "perl",
    ".groovy": "groovy", ".gradle": "groovy", ".m": "objc", ".mm": "objc",
    ".zig": "zig", ".nim": "nim", ".cr": "crystal", ".d": "dlang", ".hx": "haxe",
    ".elm": "elm", ".purs": "purescript", ".res": "rescript", ".sol": "solidity",
    ".sh": "shell", ".bash": "shell", ".zsh": "shell", ".ps1": "powershell", ".psm1": "powershell",
}
# node-recognition (broad) = edge-capable langs + node-only langs; lang labels are best-effort
# (a few extensions collide across languages, e.g. .m objc/matlab — the common repo case wins).
_NODE_LANGS = {ext: meta[0] for ext, meta in _LANGUAGES.items()}
_NODE_LANGS.update(_NODE_ONLY)


def _family(lang):
    """Resolution family — imports stay intra-language, except C/C++ share headers."""
    return "c" if lang in ("c", "cpp") else lang


def _noext(rel):
    root, _ = os.path.splitext(rel)
    return root.replace(os.sep, "/")


class GenericArm:
    """Tier-0 floor. **Nodes** any recognized source language (the broad `_NODE_LANGS` set —
    an un-armed language still gets a node + directory cluster, the floor's whole point);
    **extracts edges** only for the `_LANGUAGES` subset with an import regex, resolved within
    the importer's family (intra-language, C/C++ sharing). An unresolved specifier yields NO
    edge (intra-project only) — so over-broad regex is harmless: guessing wrong drops the edge
    rather than inventing one. Precise where relative-path imports dominate (C/C++, Ruby) and
    where package==path (Java); weak for package-graph languages (Go bare imports, C#
    namespaces) — those earn a precise arm later. The floor, not the strategy.
    """
    name = "generic"
    tier = 0
    node_type = "module"
    extensions = frozenset(_NODE_LANGS)  # broad: every recognized source language gets a node
    fidelity = "low"  # best-effort shallow-regex; package-graph languages under-resolve
    known_gaps = ("best-effort regex resolution", "no same-package / no-import edges")

    def lang_of(self, path):
        return _NODE_LANGS.get(os.path.splitext(path)[1].lower(), "unknown")

    def fidelity_of(self, path):
        ext = os.path.splitext(path)[1].lower()
        if ext not in _LANGUAGES:  # recognized source language with no import regex
            return ("nodes-only", ("no edges — nodes + directory clusters only",))
        return (self.fidelity, self.known_gaps)

    @staticmethod
    def _flat_index(files):
        # by_noext: normalized path-without-ext -> relpath (unique key for path resolution)
        # by_base:  basename-without-ext -> [relpaths] (candidate set for suffix resolution)
        by_noext, by_base = {}, collections.defaultdict(list)
        for f in files:
            ne = _noext(f)
            by_noext[ne] = f
            by_base[ne.rsplit("/", 1)[-1]].append(f)
        return {"by_noext": by_noext, "by_base": by_base}

    def index(self, files):
        # One resolution sub-index PER FAMILY, over edge-capable files only. Node-only
        # languages are nodes but never edge targets; families keep imports intra-language
        # (so a Ruby `require 'utils'` can't resolve to an unrelated utils.lua), C/C++ sharing.
        fams = collections.defaultdict(list)
        for f in files:
            ext = os.path.splitext(f)[1].lower()
            if ext in _LANGUAGES:
                fams[_family(_NODE_LANGS[ext])].append(f)
        return {fam: self._flat_index(fs) for fam, fs in fams.items()}

    @staticmethod
    def _join(base, spec):
        return os.path.normpath(os.path.join(base, spec)).replace(os.sep, "/")

    def _match_pathish(self, cand, idx):
        """Resolve a filesystem-ish path (already anchored) to a project file, else None."""
        cand = cand.replace(os.sep, "/").strip("/")
        by = idx["by_noext"]
        if cand in ("", "."):  # spec resolved to the import root -> its index/main entry
            return by.get("index") or by.get("main")
        for key in (cand, _noext(cand), cand + "/index", _noext(cand) + "/index"):
            if key in by:
                return by[key]
        return None

    def _match_suffix(self, spec, idx, min_k):
        """Resolve a dotted/slashed spec by the longest UNIQUE path-suffix of >= min_k segs."""
        segs = [s for s in re.split(r"[./\\]", spec) if s and s != "*"]
        if len(segs) < min_k:
            return None
        cands = idx["by_base"].get(segs[-1])
        if not cands:
            return None
        for k in range(len(segs), min_k - 1, -1):  # longest match wins
            hit = [f for f in cands if _noext(f).split("/")[-k:] == segs[-k:]]
            if len(hit) == 1:
                return hit[0]
            if len(hit) > 1:
                return None  # ambiguous at the most-specific length -> refuse to guess
        return None

    def _resolve(self, spec, importer, mode, idx):
        spec = spec.strip()
        if not spec or ":" in spec:  # empty or a scheme (package:/dart:/http:) -> external
            return None
        base = os.path.dirname(importer)
        if mode == "rel":  # JS/TS/ESM: only "." specs are intra-repo; bare = external package
            return self._match_pathish(self._join(base, spec), idx) if spec.startswith(".") else None
        if mode == "include":  # C/C++ quoted include: relative to dir, else unique basename
            return self._match_pathish(self._join(base, spec), idx) or self._match_suffix(spec, idx, 1)
        if mode == "mod":  # Rust `mod foo;` -> sibling foo.rs or foo/mod.rs
            return self._match_pathish(self._join(base, spec), idx) \
                or self._match_pathish(self._join(base, spec + "/mod"), idx)
        if mode == "pkg":  # Java/C#/... dotted -> package+name suffix (>=2 segs, no bare collision)
            return self._match_suffix(spec, idx, 2)
        if mode == "path":  # Ruby/Go/Dart: relative-to-dir, else >=2-seg slashed suffix
            hit = self._match_pathish(self._join(base, spec), idx)
            if hit:
                return hit
            return self._match_suffix(spec, idx, 2) if "/" in spec else None
        return None

    def edges(self, path, source, index):
        lang, mode, patterns = _LANGUAGES.get(os.path.splitext(path)[1].lower(), ("", "", []))
        sub = index.get(_family(lang)) if patterns else None
        if not sub:  # node-only language, or no edge-capable siblings in its family
            return set()
        out = set()
        for pat in patterns:
            for m in pat.finditer(source):
                target = self._resolve(m.group("spec"), path, mode, sub)
                if target and target != path:
                    out.add(target)
        return out


# --------------------------------------------------------------------------- #
# JS/TS arm (tier 2) — the floor's extraction + a resolver that understands what the
# floor cannot: tsconfig/jsconfig `paths`+`baseUrl` aliases, TS/JS extension resolution
# (.ts/.tsx/.d.ts/.js/…), and index/barrel dirs. Zero extra dependency — the win over the
# floor is *resolution* (alias/baseUrl edges the floor drops), not parsing. Subclasses the
# floor so a repo with no tsconfig degrades exactly to the floor's relative-import behaviour.
# --------------------------------------------------------------------------- #
def _strip_jsonc(s):
    """Strip // and /* */ comments (outside strings) and trailing commas -> parseable JSON.
    tsconfig.json is JSONC in the wild; stdlib json can't read it."""
    out, i, n, instr, q = [], 0, len(s), False, ""
    while i < n:
        c = s[i]
        if instr:
            out.append(c)
            if c == "\\" and i + 1 < n:
                out.append(s[i + 1]); i += 2; continue
            if c == q:
                instr = False
            i += 1; continue
        if c in "\"'":
            instr, q = True, c; out.append(c); i += 1; continue
        if c == "/" and i + 1 < n and s[i + 1] == "/":
            i += 2
            while i < n and s[i] != "\n":
                i += 1
            continue
        if c == "/" and i + 1 < n and s[i + 1] == "*":
            i += 2
            while i + 1 < n and not (s[i] == "*" and s[i + 1] == "/"):
                i += 1
            i += 2; continue
        out.append(c); i += 1
    return re.sub(r",(\s*[}\]])", r"\1", "".join(out))


class JsTsArm(GenericArm):
    name = "jsts"
    tier = 2
    extensions = frozenset(_JS_EXTS)  # inherits lang_of (typescript vs javascript) from _LANGUAGES
    # ground-truth measured (call _resolve per specifier vs package.json): 0 fabricated edges on
    # express/vue/vite/hono; relative recall ~87-100%, workspace ~95-100%. tsconfig paths+baseUrl,
    # workspace names, and exports/imports subpaths (incl. dist->src for unbuilt monorepos) resolve.
    # Residual: computed/dynamic specifiers, per-runtime-only export conditions, and non-source
    # asset imports (.css/.svg/.json) which are intentionally not nodes.
    fidelity = "high"
    known_gaps = ("computed require()/dynamic specifiers",
                  "per-runtime-only export conditions (node/browser/deno)")

    @staticmethod
    def _flat_index(files):
        idx = GenericArm._flat_index(files)
        # TS declaration files resolve by the name BEFORE `.d` (import './x' -> x.d.ts). Register
        # that key too, without clobbering a real x.ts/x.js (setdefault -> concrete source wins).
        for f in files:
            low = f.lower()
            for dext in (".d.ts", ".d.mts", ".d.cts"):
                if low.endswith(dext):
                    idx["by_noext"].setdefault(f[: -len(dext)].replace(os.sep, "/"), f)
                    break
        return idx

    def _read_jsonc(self, path):
        if not os.path.isfile(path):
            return None
        try:
            return json.loads(_strip_jsonc(open(path, encoding="utf-8", errors="replace").read()))
        except Exception:
            return None

    def _load_tsconfig(self):
        """Return (baseUrl, [(pattern, has_star, prefix, suffix, [targets])]) from the root
        ts/jsconfig. Follows one `extends` when the child declares no paths of its own."""
        for fn in ("tsconfig.json", "jsconfig.json"):
            data = self._read_jsonc(fn)
            if data is None:
                continue
            co = (data.get("compilerOptions") or {})
            raw = co.get("paths") or {}
            base = co.get("baseUrl")
            if not raw and isinstance(data.get("extends"), str):  # one level of inheritance
                parent = self._read_jsonc(os.path.normpath(os.path.join(os.path.dirname(fn), data["extends"])))
                if parent:
                    pco = (parent.get("compilerOptions") or {})
                    raw = pco.get("paths") or raw
                    base = base if base is not None else pco.get("baseUrl")
            base_url = base if base is not None else "."  # TS>=4.1 allows paths without baseUrl
            rules = []
            for pat, targets in raw.items():
                star = "*" in pat
                prefix, suffix = (pat.split("*", 1) if star else (pat, ""))
                rules.append((pat, star, prefix, suffix, list(targets)))
            return base_url, rules
        return ".", []

    def _pkg_entry(self, pkg_dir, pj, idx):
        """Resolve a package's SOURCE entry file (prefer source over an absent dist), else None."""
        exp = pj.get("exports")
        if exp is not None:  # the '.' main via the exports map (source-preferring + dist->src)
            tgt, star = self._exports_target(exp, ".")
            hit = self._resolve_target(pkg_dir, tgt, star, idx)
            if hit and not isinstance(hit, tuple):
                return hit
        for c in ("source", "module", "types", "main"):  # top-level entry fields
            v = pj.get(c)
            if isinstance(v, str):
                hit = self._match_pathish(self._join(pkg_dir, v), idx) or self._dist_to_src(pkg_dir, v, idx)
                if hit:
                    return hit
        for c in ("src/index", "index", "src/main"):  # conventional fallbacks
            hit = self._match_pathish(self._join(pkg_dir, c), idx)
            if hit:
                return hit
        return None

    @staticmethod
    def _pnpm_workspace_globs():
        """Read the `packages:` block of pnpm-workspace.yaml (minimal YAML — block list only)."""
        if not os.path.isfile("pnpm-workspace.yaml"):
            return []
        globs, in_pkgs = [], False
        for line in open("pnpm-workspace.yaml", encoding="utf-8", errors="replace"):
            if re.match(r"^packages:", line):
                in_pkgs = True
            elif in_pkgs and re.match(r"\s*-\s", line):
                m = re.match(r"\s*-\s*['\"]?([^'\"#\n]+?)['\"]?\s*$", line)
                if m:
                    globs.append(m.group(1).strip())
            elif in_pkgs and line.strip() and not line[0].isspace():
                in_pkgs = False
        return globs

    @classmethod
    def _glob_match(cls, pat_segs, path_segs):
        """npm/pnpm workspace-glob match: `*` = one path segment, `**` = zero or more."""
        if not pat_segs:
            return not path_segs
        head = pat_segs[0]
        if head == "**":
            return any(cls._glob_match(pat_segs[1:], path_segs[i:]) for i in range(len(path_segs) + 1))
        if not path_segs:
            return False
        if fnmatch.fnmatchcase(path_segs[0], head):
            return cls._glob_match(pat_segs[1:], path_segs[1:])
        return False

    @classmethod
    def _pkg_dirs_matching(cls, globs):
        """Dirs (excluding root) that hold a package.json AND match a workspace glob, found with
        an EXCLUDE-pruned walk. NOT glob.glob: that descends node_modules/dist/... (slow on an
        installed repo, and would read node_modules package.json — false workspace packages)."""
        pats = [g.rstrip("/").split("/") for g in globs]
        hits = []
        for dp, dns, fns in os.walk("."):
            dns[:] = [d for d in dns if d not in DEFAULT_EXCLUDE]
            if "package.json" not in fns:
                continue
            rel = os.path.relpath(dp).replace(os.sep, "/")
            if rel == "." or rel.startswith(".."):
                continue
            segs = rel.split("/")
            if any(cls._glob_match(p, segs) for p in pats):
                hits.append(dp)
        return hits

    def _load_workspaces(self, idx):
        """{package_name: (pkg_dir, entry_relpath, package_json)} for local workspace packages +
        the root package — a bare specifier matching one of these names is intra-repo, not external.
        Names come from package.json (exact ground truth), so this is precise, not heuristic.
        The parsed package.json rides along so subpath imports can consult its exports/imports map."""
        globs, root = [], self._read_jsonc("package.json")
        if root:
            ws = root.get("workspaces")
            ws = ws.get("packages") if isinstance(ws, dict) else ws
            globs += [g for g in ws if isinstance(g, str)] if isinstance(ws, list) else []
        globs += self._pnpm_workspace_globs()
        pos = [g for g in globs if not g.startswith("!")]  # exclusion globs left for the resolver
        dirs = self._pkg_dirs_matching(pos) if pos else []
        if root:
            dirs.append(".")  # the root package itself (self-name imports)
        out = {}
        for d in dirs:
            pj = self._read_jsonc(os.path.join(d, "package.json"))
            if pj and isinstance(pj.get("name"), str):
                # Register even when the main entry doesn't resolve (subpaths-only exports, or an
                # imports-map-only package): the bare-name import yields None, but subpath/# imports
                # of the package must still resolve. Entry may be None.
                pkg_dir = "." if d == "." else os.path.relpath(d).replace(os.sep, "/")
                out.setdefault(pj["name"], (pkg_dir, self._pkg_entry(d, pj, idx), pj))
        return out

    def index(self, files):
        idx = self._flat_index(files)  # JS+TS resolve together -> one flat index, not per-family
        idx["baseUrl"], idx["paths"] = self._load_tsconfig()
        idx["workspaces"] = self._load_workspaces(idx)
        return idx

    # exports/imports condition order — source-preferring so an unbuilt monorepo resolves to
    # src, not an absent dist. The existence gate in _resolve_target skips a missing dist target.
    _SRC_CONDS = ("source", "types", "typings", "import", "module", "browser", "require", "default")

    @staticmethod
    def _subpath_map(exp):
        """Normalize an exports/imports value to a subpath map. Sugar (a bare string, or a
        conditions object with no './'|'#' keys) means the '.' main entry only."""
        if isinstance(exp, str):
            return {".": exp}
        if isinstance(exp, dict):
            if exp and not any(k[:1] in ("." "#") for k in exp):  # bare conditions object
                return {".": exp}
            return exp
        return {}

    def _exports_target(self, exp, subkey):
        """(target, star_capture) for subkey — exact key wins, else the longest-prefix `*` key."""
        m = self._subpath_map(exp)
        if subkey in m:
            return m[subkey], None
        best = None
        for k, v in m.items():
            if k.count("*") == 1:
                pre, suf = k.split("*", 1)
                if subkey.startswith(pre) and subkey.endswith(suf) and len(subkey) >= len(pre) + len(suf):
                    mid = subkey[len(pre): len(subkey) - len(suf)] if suf else subkey[len(pre):]
                    if best is None or len(pre) > best[2]:
                        best = (v, mid, len(pre))
        return (best[0], best[1]) if best else (None, None)

    _BUILD_DIRS = ("dist", "build", "lib", "out", "es", "esm", "cjs", "umd", "types", "typings")

    def _dist_to_src(self, pkg_dir, target, idx):
        """An exports target points at a BUILT artifact (`./dist/x/y.js`) absent from an unbuilt
        checkout. Derive the source: strip leading build dir(s), prepend `src/`, drop the ext
        (by_noext resolves .ts/.tsx/.d.ts). Bounded — must resolve to a real repo file, else None."""
        rel = target[2:] if target.startswith("./") else target
        segs = rel.split("/")
        while len(segs) > 1 and segs[0] in self._BUILD_DIRS:  # dist/ , dist/types/ , dist/cjs/ ...
            segs = segs[1:]
        noext = re.sub(r"\.(d\.[mc]?ts|[mc]?[jt]sx?)$", "", "/".join(segs))
        for cand in ("src/" + noext, noext):
            hit = self._match_pathish(self._join(pkg_dir, cand), idx)
            if hit:
                return hit
        return None

    def _resolve_target(self, pkg_dir, target, star, idx):
        """Resolve an exports target: a `./`-string (with optional `*`), a conditions object
        (source-preferring), or a fallback array. Returns None (encapsulated/absent) or a file."""
        if isinstance(target, str):
            if not target.startswith("."):
                return ("bare", target)  # imports-map bare specifier — caller re-resolves
            t = target.replace("*", star) if (star is not None and "*" in target) else target
            hit = self._match_pathish(self._join(pkg_dir, t), idx)
            if hit:
                return hit
            return self._dist_to_src(pkg_dir, t, idx)  # unbuilt dist -> derive the source path
        if isinstance(target, dict):
            for c in self._SRC_CONDS:
                if c in target:
                    hit = self._resolve_target(pkg_dir, target[c], star, idx)
                    if hit:
                        return hit
        elif isinstance(target, list):
            for el in target:
                hit = self._resolve_target(pkg_dir, el, star, idx)
                if hit:
                    return hit
        return None

    def _resolve(self, spec, importer, mode, idx):  # mode unused (single JS/TS scheme)
        spec = spec.strip()
        ws = idx.get("workspaces") or {}
        if spec.startswith("#"):  # subpath imports — the importer's own package `imports` map
            best = None
            for pkg_dir, _entry, pj in ws.values():
                pref = "" if pkg_dir == "." else pkg_dir + "/"
                if pj.get("imports") and (pkg_dir == "." or importer.replace(os.sep, "/").startswith(pref)):
                    if best is None or len(pkg_dir) > len(best[0]):
                        best = (pkg_dir, pj)
            if best:
                tgt, star = self._exports_target(best[1]["imports"], spec)
                hit = self._resolve_target(best[0], tgt, star, idx)
                if isinstance(hit, tuple):  # bare specifier -> re-resolve as a fresh import
                    return self._resolve(hit[1], importer, None, idx)
                return hit
            return None
        if not spec or ":" in spec:  # empty or a scheme (node:, http:, data:) -> external
            return None
        if spec.startswith("."):  # relative — extension/index resolution via by_noext
            return self._match_pathish(self._join(os.path.dirname(importer), spec), idx)
        for pat, star, prefix, suffix, targets in idx["paths"]:  # tsconfig path aliases
            if star:
                if not (spec.startswith(prefix) and spec.endswith(suffix)
                        and len(spec) >= len(prefix) + len(suffix)):
                    continue
                mid = spec[len(prefix): len(spec) - len(suffix)] if suffix else spec[len(prefix):]
                cands = [t.replace("*", mid, 1) if "*" in t else t for t in targets]
            elif spec == pat:
                cands = list(targets)
            else:
                continue
            for cand in cands:
                hit = self._match_pathish(self._join(idx["baseUrl"], cand), idx)
                if hit:
                    return hit
        if spec in ws:  # bare @scope/pkg (or self-name) -> local package main entry
            return ws[spec][1]
        for name, (pkg_dir, entry, pj) in ws.items():
            if spec.startswith(name + "/"):  # @scope/pkg/subpath -> resolve within the package
                sub = "./" + spec[len(name) + 1:]
                exp = pj.get("exports")
                if exp is not None:  # exports map handles wildcards + source conditions precisely
                    tgt, star = self._exports_target(exp, sub)
                    hit = self._resolve_target(pkg_dir, tgt, star, idx)
                    if hit and not isinstance(hit, tuple):
                        return hit
                # exports absent, OR pointed at an unbuilt dist / didn't declare the subpath:
                # fall back to the src convention. A code map wants the real intra-repo dependency
                # for a LOCAL package we control, not Node's runtime encapsulation. Bounded to
                # pkg_dir/{sub, src/sub} -> never fabricates an external edge (must be a repo file).
                bare = sub[2:]
                return (self._match_pathish(self._join(pkg_dir, bare), idx)
                        or self._match_pathish(self._join(pkg_dir, "src/" + bare), idx))
        # baseUrl-bare resolution, but ONLY for path-shaped specifiers ("/" present, not "@scope"):
        # a bare package token (`react`, `lodash`) must stay external even if a same-named local
        # file exists — resolving it would FABRICATE an edge (soundness > the rare baseUrl completeness).
        if idx["baseUrl"] not in (None, "") and "/" in spec and not spec.startswith("@"):
            hit = self._match_pathish(self._join(idx["baseUrl"], spec), idx)
            if hit:
                return hit
        return None  # otherwise external (node_modules) -> no edge

    def edges(self, path, source, index):
        out = set()
        for pat in _JS_PATTERNS:
            for m in pat.finditer(source):
                target = self._resolve(m.group("spec"), path, None, index)
                if target and target != path:
                    out.add(target)
        return out


# --------------------------------------------------------------------------- #
# Go arm (tier 2) — package == directory. Zero-dep: read go.mod module paths, resolve
# module-prefixed imports to their target directory, edge to every non-test .go file in
# that package. Replaces the broken tier-0 floor for Go (which resolved 0% of intra-repo
# imports AND fabricated edges — `import "errors"`/"context" hitting a same-named local
# file). Only module-path-prefixed imports resolve, so stdlib/third-party never edge.
# --------------------------------------------------------------------------- #
class GoArm:
    name = "go"
    tier = 2
    node_type = "module"
    extensions = frozenset({".go"})
    fidelity = "high"  # package==dir makes cross-package resolution compiler-grade from text
    known_gaps = ("intra-package sibling refs need no import -> no edge (import graph only)",
                  "build-constraint / GOOS-suffixed files over-included (all non-test .go)",
                  "cgo (import \"C\"), generated files, and go.mod `replace` not resolved")

    def lang_of(self, path):
        return "go"

    def index(self, files):
        # modules: (module_path, module_root_dir), longest path first for nested-module match
        modules = []
        for dp, dns, fns in os.walk("."):
            dns[:] = [d for d in dns if d not in DEFAULT_EXCLUDE]
            if "go.mod" in fns:
                for line in open(os.path.join(dp, "go.mod"), encoding="utf-8", errors="replace"):
                    m = re.match(r"\s*module\s+(\S+)", line)
                    if m:
                        modules.append((m.group(1), os.path.relpath(dp).replace(os.sep, "/")))
                        break
        modules.sort(key=lambda mr: -len(mr[0]))
        # dir -> non-test .go files (the package's edge targets; _test.go are importers only)
        dir2files = collections.defaultdict(list)
        for f in files:
            if not f.endswith("_test.go"):
                dir2files[os.path.dirname(f).replace(os.sep, "/") or "."].append(f)
        return {"modules": modules, "dir2files": dir2files}

    _BLOCK = re.compile(r'\bimport\s*\((.*?)\)', re.S)
    _ONE = re.compile(r'^[^\S\n]*import\s+(?:[A-Za-z_.]+[^\S\n]+)?"([^"]+)"', re.M)

    def _specs(self, source):
        specs = set()
        for b in self._BLOCK.finditer(source):
            body = re.sub(r'//[^\n]*', '', b.group(1))
            specs.update(re.findall(r'"([^"]+)"', body))
        specs.update(self._ONE.findall(source))
        return specs

    def edges(self, path, source, index):
        modules, dir2files = index["modules"], index["dir2files"]
        self_dir = os.path.dirname(path).replace(os.sep, "/") or "."
        out = set()
        for spec in self._specs(source):
            if spec == "C" or ":" in spec:  # cgo pseudo-import / scheme -> not a package
                continue
            for mpath, mroot in modules:  # longest-prefix first
                if spec == mpath or spec.startswith(mpath + "/"):
                    rel = spec[len(mpath):].lstrip("/")
                    tdir = mroot if not rel else \
                        os.path.normpath(os.path.join(mroot, rel)).replace(os.sep, "/")
                    if tdir != self_dir:
                        out.update(dir2files.get(tdir, ()))
                    break
        return out


# --------------------------------------------------------------------------- #
# Java arm (tier 2) — two-pass symbol resolution. Explicit `import` statements are only
# ~three-quarters of intra-repo type edges (measured 24% no-import on gson; more in
# same-package-heavy code): Java needs NO import for same-package types or inline
# fully-qualified refs. Pass 1 indexes every top-level type -> FQN; pass 2 resolves three
# channels (imports, same-package simple names, inline FQNs) against that index, so an
# unknown Capitalized token never edges (java.*/third-party drop out).
# --------------------------------------------------------------------------- #
class JavaArm:
    name = "java"
    tier = 2
    node_type = "module"
    extensions = frozenset({".java"})
    fidelity = "high"  # after channels b+c; explicit-import-only would be ~medium
    known_gaps = ("same-package channel matches known type names -> a same-named local/field can over-edge",
                  "var-inferred types, reflection/string-loaded classes, and nested/inner types missed",
                  "all top-level types indexed (no #if/build-profile evaluation)")

    _PKG = re.compile(r'^\s*package\s+([\w.]+)\s*;', re.M)
    _TYPE = re.compile(r'\b(?:class|interface|enum|record|@interface)\s+([A-Za-z_]\w*)')
    _IMPORT = re.compile(r'^\s*import\s+(static\s+)?([\w.]+(?:\.\*)?)\s*;', re.M)
    _INLINE_FQN = re.compile(r'\b([a-z]\w*(?:\.[a-z]\w*)*\.[A-Z]\w*)\b')
    _CAP = re.compile(r'\b([A-Z]\w*)\b')

    def lang_of(self, path):
        return "java"

    @staticmethod
    def _strip(s):
        s = re.sub(r'/\*.*?\*/', ' ', s, flags=re.S)
        s = re.sub(r'//[^\n]*', ' ', s)
        s = re.sub(r'"(?:\\.|[^"\\\n])*"', '""', s)
        s = re.sub(r"'(?:\\.|[^'\\\n])*'", "''", s)
        return s

    def _toplevel_types(self, clean):
        """Type decls at brace-depth 0 (top-level; nested/inner types excluded)."""
        out = []
        for m in self._TYPE.finditer(clean):
            if clean.count("{", 0, m.start()) == clean.count("}", 0, m.start()):
                out.append(m.group(1))
        return out

    def index(self, files):
        fqn2file, pkg2types, meta = {}, collections.defaultdict(dict), {}
        for f in files:
            clean = self._strip(open(f, encoding="utf-8", errors="replace").read())
            mp = self._PKG.search(clean)
            pkg = mp.group(1) if mp else ""
            meta[f] = (pkg, clean)
            for t in self._toplevel_types(clean):
                fqn2file.setdefault((pkg + "." + t) if pkg else t, f)
                pkg2types[pkg].setdefault(t, f)
        return {"fqn2file": fqn2file, "pkg2types": pkg2types, "meta": meta}

    def edges(self, path, source, index):
        fqn2file, pkg2types = index["fqn2file"], index["pkg2types"]
        pkg, clean = index["meta"][path]
        used = set(self._CAP.findall(clean))  # Capitalized simple names referenced in the body
        out = set()
        for static, fq in self._IMPORT.findall(clean):  # (a) explicit imports
            if fq.endswith(".*"):
                base = fq[:-2]
                if static and base in fqn2file:        # import static Type.*
                    out.add(fqn2file[base])
                else:                                   # import pkg.* -> only types actually used
                    out.update(f for t, f in pkg2types.get(base, {}).items() if t in used)
                continue
            f = fqn2file.get(fq)
            if f is None and static:                    # import static pkg.Type.member
                f = fqn2file.get(fq.rsplit(".", 1)[0])
            if f is None:                               # nested-type import: strip Capitalized tail
                parts = fq.split(".")
                while f is None and len(parts) > 2 and parts[-1][:1].isupper() and parts[-2][:1].isupper():
                    parts = parts[:-1]
                    f = fqn2file.get(".".join(parts))
            if f:
                out.add(f)
        for m in self._INLINE_FQN.finditer(clean):      # (c) inline fully-qualified refs
            f = fqn2file.get(m.group(1))
            if f:
                out.add(f)
        for t, f in pkg2types.get(pkg, {}).items():     # (b) same-package simple-name refs
            if f != path and t in used:
                out.add(f)
        out.discard(path)
        return out


# --------------------------------------------------------------------------- #
# C# arm (tier 2) — two-pass, namespace-aware. Harder than Java: a namespace is decoupled
# from directory AND file (one namespace spans many files; one file holds many types;
# `partial` splits a type across files). Pass 1 tracks a namespace stack (file-scoped `;`
# and block-scoped `{`) to index top-level types -> (namespace, name) -> {files}. Pass 2
# resolves `using` (to the INTERSECTION of the namespace's types with the HEAD simple names the
# file uses — never the whole namespace, which would make a hairball; a member-access token like
# `x.Order` is NOT a type ref, so head-only), same-namespace refs, inline FQNs, and `using static`.
# Replaces a near-useless floor (945 files -> 107 edges).
# --------------------------------------------------------------------------- #
class CSharpArm:
    name = "csharp"
    tier = 2
    node_type = "module"
    extensions = frozenset({".cs"})
    fidelity = "medium"  # measured 98.9% intersection precision (AutoMapper) after the head-token
                         # filter; namespace != dir/file; residual declaration-name collisions; partial/gen
    known_gaps = ("source-generated / build-time partial types have no file -> missing edges",
                  "`using X.Y` resolves to used simple names only; nameof/reflection/attribute-only missed",
                  "member-access tokens (x.Order/.Include<>()/MemberList.Source) are filtered out, but a "
                  "property/enum-member DECLARED with a same-namespace type's name (public string Source) "
                  "still over-edges (~1% on AutoMapper); all #if branches kept")

    _KEYWORDS = frozenset({"where", "class", "struct", "interface", "enum", "record", "new", "default"})
    _TOKEN = re.compile(
        r'namespace\s+(?P<ns>[\w.]+)\s*(?P<term>[;{])'
        r'|(?P<kind>class|struct|interface|enum|record)\b(?:\s+(?:class|struct))?\s+(?P<name>[A-Za-z_]\w*)'
        r'|(?P<brace>[{}])')
    _USING = re.compile(r'^\s*(global\s+)?using\s+(static\s+)?(?:([A-Za-z_]\w*)\s*=\s*)?([\w.]+)\s*;', re.M)
    _CAP = re.compile(r'\b([A-Z]\w*)\b')
    _DOTTED = re.compile(r'\b([A-Za-z_]\w*(?:\.[A-Za-z_]\w*)+)\b')

    def lang_of(self, path):
        return "csharp"

    @staticmethod
    def _strip(s):
        s = re.sub(r'/\*.*?\*/', ' ', s, flags=re.S)
        s = re.sub(r'//[^\n]*', ' ', s)
        s = re.sub(r'@"(?:[^"]|"")*"', '""', s)
        s = re.sub(r'"(?:\\.|[^"\\\n])*"', '""', s)
        s = re.sub(r"'(?:\\.|[^'\\\n])*'", "''", s)
        return s

    def _head_used(self, clean):
        """Capitalized tokens with >= 1 occurrence NOT immediately preceded by a
        member-access dot. Precision anchor for the collision-prone same-namespace /
        using-intersection channels: a token that appears ONLY as `x.Order` (property),
        `.Include<..>()` (fluent method), or `MemberList.Source` (enum member) is a member
        reference, not a type reference, so it must not edge to a same-named type. A
        genuine type is referenced at least once as a head token (`new Order`, `Order x`,
        `: Order`, `<Order>`); qualified `Ns.Type` type-refs are still caught by the inline
        FQN channel. Measured: drops ~2-3% same-namespace false positives (fluent-DSL /
        PascalCase-property collisions) with no observed genuine-type recall loss on
        AutoMapper + eShopOnWeb."""
        head = set()
        for m in self._CAP.finditer(clean):
            i = m.start() - 1
            while i >= 0 and clean[i] in " \t":  # bounded back-scan over whitespace only (not O(n) slice)
                i -= 1
            if i < 0 or clean[i] != ".":
                head.add(m.group(1))
        return head

    def _scan(self, clean):
        """(declared_namespaces, [(namespace, typename)]) for top-level types (brace-depth aware)."""
        depth, stack, file_ns = 0, [], None
        types, namespaces = [], set()
        for m in self._TOKEN.finditer(clean):
            if m.group("ns") is not None:
                if m.group("term") == ";":  # file-scoped namespace (whole file, content depth 0)
                    file_ns = m.group("ns")
                    namespaces.add(file_ns)
                else:                        # block-scoped (may nest)
                    namespaces.add(".".join([n for n, _ in stack] + [m.group("ns")]))
                    stack.append((m.group("ns"), depth))
                    depth += 1
            elif m.group("kind") is not None:
                name = m.group("name")
                if name in self._KEYWORDS:  # `where T : class where ...` false match
                    continue
                if file_ns is not None:
                    cur, content_depth = file_ns, 0
                else:
                    cur, content_depth = ".".join(n for n, _ in stack), len(stack)
                if depth == content_depth:  # top-level only (nested types excluded)
                    types.append((cur, name))
            else:
                if m.group("brace") == "{":
                    depth += 1
                else:
                    depth -= 1
                    while stack and depth <= stack[-1][1]:
                        stack.pop()
        return namespaces, types

    def index(self, files):
        ns_types = collections.defaultdict(lambda: collections.defaultdict(set))
        fqn, declared, globals_ = collections.defaultdict(set), set(), set()
        meta = {}
        for f in files:
            clean = self._strip(open(f, encoding="utf-8", errors="replace").read())
            namespaces, types = self._scan(clean)
            declared |= namespaces
            file_ns = set()
            for ns, name in types:
                ns_types[ns][name].add(f)
                fqn[(ns + "." + name) if ns else name].add(f)
                file_ns.add(ns)
            for g, static, alias, target in self._USING.findall(clean):
                if g:  # `global using` applies to every file in the compilation
                    globals_.add((static, alias, target))
            meta[f] = (clean, file_ns)
        return {"ns_types": ns_types, "fqn": fqn, "declared": declared,
                "globals": globals_, "meta": meta}

    def edges(self, path, source, index):
        ns_types, fqn = index["ns_types"], index["fqn"]
        declared, meta = index["declared"], index["meta"]
        clean, file_ns_set = meta[path]
        used = self._head_used(clean)  # type-position anchor for the intersection channels
        out, plain_ns = set(), []
        usings = self._USING.findall(clean) + [("",) + u for u in index["globals"]]
        for g, static, alias, target in usings:
            if alias:                                  # using A = X.Y(.Type)
                out.update(fqn.get(target, ())) if target in fqn else plain_ns.append(target)
            elif static:                               # using static X.Y.Type -> the enclosing type
                out.update(fqn.get(target, ()))
            else:                                      # plain using X.Y (a namespace)
                plain_ns.append(target)
        for ns in plain_ns:                            # (a) using -> intersection with used names
            if ns in declared:
                for name, files in ns_types.get(ns, {}).items():
                    if name in used:
                        out.update(files)
        for ns in file_ns_set:                         # (b) same-namespace refs (no using needed)
            for name, files in ns_types.get(ns, {}).items():
                if name in used:
                    out.update(files)
        for m in self._DOTTED.finditer(clean):         # (c) inline fully-qualified refs
            segs = m.group(1).split(".")
            for k in range(len(segs) - 1, 0, -1):      # longest namespace prefix first
                if segs[k][:1].isupper():
                    key = ".".join(segs[: k + 1])
                    if key in fqn:
                        out.update(fqn[key])
                        break
        out.discard(path)
        return out


ARMS = [PythonArm(), JsTsArm(), GoArm(), JavaArm(), CSharpArm(), GenericArm()]  # order = precedence


def _arm_fidelity(arm, path):
    """(level, known_gaps) for the file — the honest coverage of the arm that produced it."""
    fn = getattr(arm, "fidelity_of", None)
    return fn(path) if fn else (arm.fidelity, tuple(arm.known_gaps))


def _ext_to_arm():
    mapping = {}
    for arm in ARMS:
        for ext in arm.extensions:
            mapping.setdefault(ext, arm)  # first arm wins (PythonArm claims .py)
    return mapping


# --------------------------------------------------------------------------- #
# Shared driver — language-agnostic.
# --------------------------------------------------------------------------- #
def pagerank(nodes, out_edges, damping=0.85, iterations=60):
    n = len(nodes)
    if n == 0:
        return {}
    pr = {x: 1.0 / n for x in nodes}
    for _ in range(iterations):
        nxt = {x: (1 - damping) / n for x in nodes}
        dangling = damping * sum(pr[x] for x in nodes if not out_edges.get(x)) / n
        for x in nodes:
            nxt[x] += dangling
        for src, dsts in out_edges.items():
            if dsts:
                share = damping * pr[src] / len(dsts)
                for dst in dsts:
                    nxt[dst] += share
        pr = nxt
    return pr


def discover(root, exclude, ext2arm):
    files = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in exclude]
        for fn in filenames:
            if os.path.splitext(fn)[1].lower() in ext2arm:
                files.append(os.path.normpath(os.path.join(dirpath, fn)))
    return sorted(files)


def main():
    ap = argparse.ArgumentParser(description="Multi-language code-map extractor -> graph.json")
    ap.add_argument("root", nargs="?", default=".")
    ap.add_argument("--out", default=None,
                    help="graph.json path (default: <project_root>/docs/knowledge/graph.json, "
                         "project_root read from .workflow/config.json, else ./docs/knowledge/graph.json)")
    ap.add_argument("--exclude", default="")
    args = ap.parse_args()

    # Default the output under <project_root>/docs, not the repo root — a greenfield
    # project lives in ./project, so its docs belong there, not at the launch root.
    if args.out is None:
        project_root = "."
        try:
            with open(os.path.join(".workflow", "config.json"), encoding="utf-8") as fh:
                project_root = json.load(fh).get("project_root", ".")
        except (FileNotFoundError, ValueError):
            project_root = "."
        args.out = os.path.join(project_root, "docs", "knowledge", "graph.json")

    exclude = set(DEFAULT_EXCLUDE) | {e for e in args.exclude.split(",") if e}
    ext2arm = _ext_to_arm()
    files = discover(args.root, exclude, ext2arm)

    # group files by their arm, build each arm's resolution index once
    by_arm = collections.defaultdict(list)
    for p in files:
        by_arm[ext2arm[os.path.splitext(p)[1].lower()]].append(p)
    indexes = {arm: arm.index(paths) for arm, paths in by_arm.items()}

    key = {p: os.path.relpath(p) for p in files}
    arm_of = {p: ext2arm[os.path.splitext(p)[1].lower()] for p in files}

    fwd = collections.defaultdict(set)
    parse_failures = []
    for path in files:
        arm = arm_of[path]
        try:
            source = open(path, encoding="utf-8", errors="replace").read()
            for target in arm.edges(path, source, indexes[arm]):
                if target in key and target != path:
                    fwd[key[path]].add(key[target])
        except SyntaxError as exc:
            parse_failures.append((path, str(exc)))
        except Exception as exc:  # a floor arm must never sink the whole run
            parse_failures.append((path, f"{type(exc).__name__}: {exc}"))

    nodes = sorted(key[p] for p in files)
    fwd_edges = {a: sorted(bs) for a, bs in fwd.items()}
    rev_edges = collections.defaultdict(list)
    in_deg = collections.Counter()
    for a, bs in fwd_edges.items():
        for b in bs:
            rev_edges[b].append(a)
            in_deg[b] += 1

    impact = pagerank(nodes, fwd_edges)
    orchestration = pagerank(nodes, {k: list(v) for k, v in rev_edges.items()})

    lang_of = {key[p]: arm_of[p].lang_of(p) for p in files}
    tier_of = {key[p]: arm_of[p].tier for p in files}
    fidelity_of = {key[p]: _arm_fidelity(arm_of[p], p) for p in files}
    node_records = [
        {
            "path": p,
            "type": "module",
            "lang": lang_of[p],
            "tier": tier_of[p],
            "impact": round(impact.get(p, 0.0), 6),
            "orchestration": round(orchestration.get(p, 0.0), 6),
            "in_degree": in_deg.get(p, 0),
            "out_degree": len(fwd_edges.get(p, [])),
        }
        for p in nodes
    ]
    edge_records = sorted(
        ({"from": a, "to": b, "kind": "import"} for a, bs in fwd_edges.items() for b in bs),
        key=lambda e: (e["from"], e["to"]),
    )

    # per-language coverage summary — `fidelity` (+ `known_gaps`) is the honest trust signal a
    # consumer must weight edges by; `tier` is only which arm produced them, NOT a completeness claim.
    languages = {}
    for p in nodes:
        lvl, gaps = fidelity_of[p]
        lg = languages.setdefault(lang_of[p], {"tier": tier_of[p], "fidelity": lvl,
                                               "known_gaps": sorted(set(gaps)), "files": 0, "edges": 0})
        lg["files"] += 1
        lg["edges"] += len(fwd_edges.get(p, []))

    graph = {
        "generated_by": "codemap",
        "root": os.path.relpath(args.root),
        "node_count": len(node_records),
        "edge_count": len(edge_records),
        "languages": dict(sorted(languages.items())),
        "nodes": node_records,
        "edges": edge_records,
    }
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(graph, fh, indent=2)
        fh.write("\n")

    summary = ", ".join(f"{lg}:{d['files']}(t{d['tier']})" for lg, d in graph["languages"].items())
    print(
        f"codemap: {len(node_records)} nodes, {len(edge_records)} edges, "
        f"{len(parse_failures)} parse failures -> {args.out}  [{summary}]",
        file=sys.stderr,
    )
    for path, err in parse_failures[:10]:
        print(f"  parse-fail: {path}: {err}", file=sys.stderr)


if __name__ == "__main__":
    main()

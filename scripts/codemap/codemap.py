#!/usr/bin/env python3
"""Code-map extractor — emits the structural knowledge layer as graph.json.

Multi-language engine: one shared driver (discover -> dispatch -> resolve -> PageRank ->
emit) over pluggable per-language ARMS. What varies by language is only *edge resolution*;
the node set + directory clusters are identical everywhere, so the cost of a language is
its resolver, not its parser. Ships three arms today:

  - PythonArm   (tier 2) — stdlib `ast`, zero-dep, precise dotted-module resolution.
  - JsTsArm     (tier 2) — JS/TS: the floor's extraction + a resolver that reads tsconfig/
                           jsconfig `paths`+`baseUrl` aliases, TS/JS extension resolution,
                           and index/barrel dirs. Zero extra dep; beats the floor on the
                           alias/baseUrl edges the floor drops. No tsconfig -> = the floor.
  - GenericArm  (tier 0) — the generic floor: NODES any recognized source language, and
                           adds shallow-regex import edges for the subset that has them. The
                           long-tail safety net so a repo in ANY recognized language gets at
                           least nodes + directory clusters + both centrality lenses, never nothing.

More precise arms (Java, C#, C++, Go, …) plug into the same contract later: a new arm is a
`class Arm` with `extensions`, `index()`, and `edges()` — the driver below is untouched.

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
import glob
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
    fidelity = "high"  # explicit-import language + real parser (ast); edges ARE imports
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
    # measured on real repos: ~99-100% of intra-repo specifiers resolved where cross-package
    # imports go via tsconfig `paths`, relative paths, or a workspace/self package name. The
    # residual is exports/imports SUBPATH maps (`pkg/subpath`) and computed/dynamic specifiers —
    # exports-subpath-heavy repos are the low case.
    fidelity = "high"
    known_gaps = ("package.json exports/imports subpath maps (pkg/subpath)",
                  "computed require()/dynamic specifiers")

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
        cands = []
        exp = pj.get("exports")
        if isinstance(exp, str):
            cands.append(exp)
        elif isinstance(exp, dict):
            dot = exp.get(".")
            if isinstance(dot, str):
                cands.append(dot)
            elif isinstance(dot, dict):
                cands += [dot[k] for k in ("source", "types", "import", "module", "default")
                          if isinstance(dot.get(k), str)]
        cands += [pj[f] for f in ("source", "module", "types", "main") if isinstance(pj.get(f), str)]
        cands += ["src/index", "index", "src/main"]  # conventional fallbacks
        for c in cands:
            hit = self._match_pathish(self._join(pkg_dir, c), idx)
            if hit:
                return hit
        return None

    def _load_workspaces(self, idx):
        """{package_name: (pkg_dir, entry_relpath)} for local workspace packages + the root
        package itself — a bare specifier matching one of these names is intra-repo, not external.
        Names come from package.json (exact ground truth), so this is precise, not heuristic."""
        globs, root = [], self._read_jsonc("package.json")
        if root:
            ws = root.get("workspaces")
            ws = ws.get("packages") if isinstance(ws, dict) else ws
            globs += [g for g in ws if isinstance(g, str)] if isinstance(ws, list) else []
        if os.path.isfile("pnpm-workspace.yaml"):  # minimal YAML: read the `packages:` list
            in_pkgs = False
            for line in open("pnpm-workspace.yaml", encoding="utf-8", errors="replace"):
                if re.match(r"^packages:", line):
                    in_pkgs = True
                elif in_pkgs and re.match(r"\s*-\s", line):
                    m = re.match(r"\s*-\s*['\"]?([^'\"#\n]+?)['\"]?\s*$", line)
                    if m and not m.group(1).startswith("!"):
                        globs.append(m.group(1).strip())
                elif in_pkgs and line.strip() and not line[0].isspace():
                    in_pkgs = False
        dirs = []
        for g in globs:
            dirs += [d for d in glob.glob(g.rstrip("/"), recursive=True) if os.path.isdir(d)]
        if root:
            dirs.append(".")  # the root package itself (self-name imports)
        out = {}
        for d in dirs:
            pj = self._read_jsonc(os.path.join(d, "package.json"))
            if pj and isinstance(pj.get("name"), str):
                entry = self._pkg_entry(d, pj, idx)
                if entry:
                    out.setdefault(pj["name"], (d.replace(os.sep, "/").lstrip("./") or ".", entry))
        return out

    def index(self, files):
        idx = self._flat_index(files)  # JS+TS resolve together -> one flat index, not per-family
        idx["baseUrl"], idx["paths"] = self._load_tsconfig()
        idx["workspaces"] = self._load_workspaces(idx)
        return idx

    def _resolve(self, spec, importer, mode, idx):  # mode unused (single JS/TS scheme)
        spec = spec.strip()
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
        ws = idx.get("workspaces") or {}   # bare @scope/pkg (or self-name) -> local package entry
        if spec in ws:
            return ws[spec][1]
        for name, (pkg_dir, entry) in ws.items():
            if spec.startswith(name + "/"):  # @scope/pkg/subpath -> resolve within the package
                sub = spec[len(name) + 1:]
                return (self._match_pathish(self._join(pkg_dir, sub), idx)
                        or self._match_pathish(self._join(pkg_dir, "src/" + sub), idx))
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


ARMS = [PythonArm(), JsTsArm(), GenericArm()]  # order = precedence; specific arms before the floor


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
    ap.add_argument("--out", default="docs/knowledge/graph.json")
    ap.add_argument("--exclude", default="")
    args = ap.parse_args()

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

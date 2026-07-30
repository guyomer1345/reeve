#!/usr/bin/env python3
"""`/update`'s mechanical half — the fixed reconcile runner.

`/update` refreshes an installed workflow package onto a newer one. Its judgment half
(confirm the plan with the human, regenerate the code-map, preserve `[D]` bodies, write the
change summary) belongs to the model and lives in `commands/update.md`. Its ARITHMETIC half
lives here and ships FIXED, for the same reason `checks.sh` does: a set difference over an
install ledger, an exclude-filtered copy, and a "was this file hand-edited?" hash check are
invariant, error-prone, and must never be re-derived per run from prose.

The 3-way file taxonomy this enforces:
  (a) PACKAGE-OWNED  -> refresh. The manifest `install[]` entries plus the copied templates
      (`loop.md`, `checks.sh`, `settings.json`, the orchestrator brief's marked block).
      These are the ONLY paths this script may write.
  (b) TARGET-OWNED   -> never touched. Everything else, by construction: `[D]` bodies, adopted
      docs, the spec, decision records, human-set `config.json` knobs, and all live loop state
      (`backlog`/`handoff`/`state`/`items`/`parked`/`outbox`/`secrets`/`checks.env`). The write
      allowlist below is the mechanical guarantee, not a promise in prose.
  (c) REGENERATE     -> not this script's job. `graph.json` + `[G]` frontmatter come from
      `codemap.sh`; the command drives that so the `[D]` bodies are preserved and re-attached.

The install LEDGER (`.workflow/install-set.json`) is what makes an orphan PROVEN. It records
every path this package wrote plus the hash it wrote, so:
  - recorded-old - new-expected  => a proven orphan, removable (and printed);
  - a path NOT in the ledger     => never touched, whoever put it there;
  - on-disk hash != recorded     => hand-edited, surfaced (and for the two human-facing files,
    `settings.json` and the brief block, it BLOCKS the overwrite until confirmed).
No ledger at all (an install from before this existed, e.g. an unstamped `workflow_version`)
=> orphans are flag-only and the confirm-required files always need confirmation. First update
writes the ledger for next time.

Run the NEW package's copy of this script (`${CLAUDE_PLUGIN_ROOT}/scripts/update_reconcile.py`),
not the target's installed one -- an update is driven by the version being installed, which is
the one that knows how to reach itself. That is a deliberate exception to `/start`'s
never-invoke-in-place rule and is safe: this script holds no state.

Subcommands:
  plan    -- print what would change; writes nothing. `--json` for machine consumption.
  apply   -- perform it: copies, proven-orphan removal, ledger + version stamp.
  record  -- write the ledger for an install that just landed (`/start` step 7).
"""
import argparse
import fnmatch
import hashlib
import json
import os
import sys

LEDGER_REL = os.path.join(".workflow", "install-set.json")
CONFIG_REL = os.path.join(".workflow", "config.json")

# The orchestrator brief is a MANAGED BLOCK inside the target's root CLAUDE.md: /update replaces
# only what is between these markers, so project notes around it are never touched. Both /start
# modes write them (greenfield wraps its whole brief in them too) so /update has one shape to
# find. `shared/schemas.md` owns these strings -- they are a compatibility contract and must
# stay byte-stable across versions.
BRIEF_BEGIN = "<!-- dev-autonomous-workflow:brief:begin -->"
BRIEF_END = "<!-- dev-autonomous-workflow:brief:end -->"
BRIEF_NOTE = ("<!-- managed block: /update replaces everything between these markers. "
              "Put project notes OUTSIDE them. -->")
BRIEF_KEY = "CLAUDE.md#brief"

# Package-owned template copies that are not manifest `install[]` entries.
TEMPLATES = [
    (os.path.join("templates", "loop.md"), os.path.join(".workflow", "loop.md")),
    (os.path.join("templates", "checks.sh"), os.path.join(".workflow", "checks.sh")),
    (os.path.join("templates", "settings.json"), os.path.join(".claude", "settings.json")),
]

# Package-owned but HUMAN-FACING: an overwrite that would discard local edits blocks until
# confirmed, rather than trusting the driver to remember to ask.
CONFIRM_REQUIRED = {os.path.join(".claude", "settings.json"), BRIEF_KEY}

EXEC_BITS = {os.path.join(".workflow", "checks.sh")}


# ---------------------------------------------------------------- small helpers

def _sha(path):
    h = hashlib.sha256()
    try:
        with open(path, "rb") as fh:
            for chunk in iter(lambda: fh.read(65536), b""):
                h.update(chunk)
    except OSError:
        return None
    return h.hexdigest()


def _sha_text(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _excluded(name, patterns):
    return any(fnmatch.fnmatch(name, os.path.basename(p)) for p in patterns)


def _read_json(path, default=None):
    try:
        with open(path) as fh:
            return json.load(fh)
    except Exception:
        return default


_chmod_unsupported_warned = False


def _atomic_write(path, data, mode=None):
    """Temp + rename, so a killed update never leaves a half-written package file.

    `chmod` is BEST-EFFORT. A repo checkout can live on a filesystem that does not honour
    file modes -- a WSL `/mnt/c` DrvFs mount without metadata, a CIFS/SMB share, some
    container bind mounts -- where `os.chmod` raises EPERM even though the write itself
    succeeds. The mode is cosmetic for this package in any case: every installed hook and
    script is invoked through its interpreter (`bash .claude/hooks/guard.sh`,
    `python3 .claude/scripts/bus.py`), never executed directly, so no exec bit is load-
    bearing. Aborting the whole update over an unenforceable permission bit would strand
    exactly the checkouts that most need updating, so warn once and carry on.

    The temp file is cleaned up on ANY failure -- a raise here used to leave a
    `<name>.tmp.update` beside the real file, which then reads as mysterious debris.
    """
    global _chmod_unsupported_warned
    parent = os.path.dirname(path) or "."
    os.makedirs(parent, exist_ok=True)
    tmp = path + ".tmp.update"
    flags = "wb" if isinstance(data, bytes) else "w"
    try:
        with open(tmp, flags) as fh:
            fh.write(data)
        if mode is not None:
            try:
                os.chmod(tmp, mode)
            except OSError as exc:
                if not _chmod_unsupported_warned:
                    _chmod_unsupported_warned = True
                    sys.stderr.write(
                        "NOTE: chmod is unsupported on this filesystem (%s); installed file "
                        "modes left as-is. Harmless -- every script is run via its interpreter, "
                        "so no exec bit is required.\n" % exc.strerror
                    )
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


# ---------------------------------------------------------------- expected set

def expected_files(plugin_root, project_root):
    """dest(rel) -> src(abs) for every path THIS package owns and may write.

    Manifest `install[]` directory entries are expanded file-by-file with the manifest
    `exclude` globs honoured, so a retired file inside an installed directory (a dropped
    code-map arm) is detectable as an orphan exactly like a top-level one.
    """
    manifest = _read_json(os.path.join(plugin_root, "MANIFEST.json"))
    if not manifest:
        raise SystemExit("cannot read %s/MANIFEST.json" % plugin_root)
    exclude = manifest.get("exclude", [])
    out = {}
    for entry in manifest.get("install", []):
        src = os.path.join(plugin_root, entry["src"])
        dest = entry["dest"]
        if os.path.isdir(src):
            for root, _dirs, files in os.walk(src):
                for f in sorted(files):
                    if _excluded(f, exclude):
                        continue
                    abs_src = os.path.join(root, f)
                    rel = os.path.relpath(abs_src, src)
                    out[os.path.join(dest, rel)] = abs_src
        elif os.path.isfile(src):
            out[dest] = src
        else:
            raise SystemExit("manifest install src missing in package: %s" % entry["src"])
    for src_rel, dest in TEMPLATES:
        src = os.path.join(plugin_root, src_rel)
        if os.path.isfile(src):
            out[dest] = src
    return out


def plugin_version(plugin_root):
    meta = _read_json(os.path.join(plugin_root, ".claude-plugin", "plugin.json"), {})
    return meta.get("version")


# ---------------------------------------------------------------- the brief block

def brief_paths(project_root):
    return os.path.join(project_root, "CLAUDE.md")


def read_brief_block(project_root):
    """(body, found). `body` is what sits between the markers, markers excluded."""
    path = brief_paths(project_root)
    try:
        with open(path) as fh:
            text = fh.read()
    except OSError:
        return None, False
    i = text.find(BRIEF_BEGIN)
    j = text.find(BRIEF_END)
    if i == -1 or j == -1 or j < i:
        return None, False
    return text[i + len(BRIEF_BEGIN):j], True


def render_brief(plugin_root, project_root):
    """The new brief body, placeholders filled from the target's own config."""
    src = os.path.join(plugin_root, "templates", "orchestrator-CLAUDE.md")
    try:
        with open(src) as fh:
            body = fh.read()
    except OSError:
        return None
    cfg = _read_json(os.path.join(project_root, CONFIG_REL), {}) or {}
    name = os.path.basename(os.path.abspath(project_root)) or "project"
    body = body.replace("<project_root>", cfg.get("project_root") or ".")
    body = body.replace("<project>", name)
    return "\n" + BRIEF_NOTE + "\n" + body.strip("\n") + "\n"


def write_brief_block(project_root, new_body):
    path = brief_paths(project_root)
    with open(path) as fh:
        text = fh.read()
    i = text.find(BRIEF_BEGIN)
    j = text.find(BRIEF_END)
    if i == -1 or j == -1 or j < i:
        raise SystemExit("no managed brief block in CLAUDE.md — refusing to guess where it goes")
    _atomic_write(path, text[:i + len(BRIEF_BEGIN)] + new_body + text[j:])


# ---------------------------------------------------------------- ledger

def load_ledger(project_root):
    return _read_json(os.path.join(project_root, LEDGER_REL))


def build_ledger(project_root, dests, version, plugin):
    """Hash what is on disk NOW at each package-owned path."""
    files = {}
    for dest in sorted(dests):
        h = _sha(os.path.join(project_root, dest))
        if h:
            files[dest] = h
    body, found = read_brief_block(project_root)
    if found:
        files[BRIEF_KEY] = _sha_text(body)
    return {"plugin": plugin, "workflow_version": version, "files": files}


def write_ledger(project_root, ledger):
    _atomic_write(os.path.join(project_root, LEDGER_REL),
                  json.dumps(ledger, indent=2, sort_keys=True) + "\n")


# ---------------------------------------------------------------- planning

def compute_plan(plugin_root, project_root):
    expected = expected_files(plugin_root, project_root)
    ledger = load_ledger(project_root)
    recorded = (ledger or {}).get("files", {})
    cfg = _read_json(os.path.join(project_root, CONFIG_REL), {}) or {}
    old_version = cfg.get("workflow_version")
    new_version = plugin_version(plugin_root)

    actions = []
    for dest in sorted(expected):
        abs_dest = os.path.join(project_root, dest)
        src_hash = _sha(expected[dest])
        cur_hash = _sha(abs_dest)
        rec_hash = recorded.get(dest)
        if cur_hash is None:
            kind = "ADD"
        elif cur_hash == src_hash:
            kind = "SAME"
        elif rec_hash is not None and cur_hash != rec_hash:
            kind = "LOCAL-EDIT"      # differs from what we wrote => a human changed it
        elif rec_hash is None:
            kind = "REFRESH?"        # unknown provenance (no ledger) => cannot prove pristine
        else:
            kind = "REFRESH"
        actions.append({"kind": kind, "path": dest,
                        "confirm": dest in CONFIRM_REQUIRED and kind in ("LOCAL-EDIT", "REFRESH?")})

    # The orchestrator brief's managed block.
    new_body = render_brief(plugin_root, project_root)
    cur_body, found = read_brief_block(project_root)
    if new_body is None:
        pass
    elif not found:
        actions.append({"kind": "BRIEF-UNMARKED", "path": BRIEF_KEY, "confirm": False})
    else:
        rec_hash = recorded.get(BRIEF_KEY)
        cur_hash = _sha_text(cur_body)
        if cur_hash == _sha_text(new_body):
            kind = "SAME"
        elif rec_hash is not None and cur_hash != rec_hash:
            kind = "LOCAL-EDIT"
        elif rec_hash is None:
            kind = "REFRESH?"
        else:
            kind = "REFRESH"
        actions.append({"kind": kind, "path": BRIEF_KEY,
                        "confirm": kind in ("LOCAL-EDIT", "REFRESH?")})

    # Orphans: only what WE recorded and no longer ship is provable.
    expected_keys = set(expected) | {BRIEF_KEY}
    for dest in sorted(set(recorded) - expected_keys):
        abs_dest = os.path.join(project_root, dest)
        if not os.path.exists(abs_dest):
            continue
        if _sha(abs_dest) != recorded[dest]:
            actions.append({"kind": "ORPHAN-EDITED", "path": dest, "confirm": False})
        else:
            actions.append({"kind": "ORPHAN", "path": dest, "confirm": False})

    return {
        "old_version": old_version,
        "new_version": new_version,
        "has_ledger": ledger is not None,
        "noop": bool(old_version and new_version and old_version == new_version),
        "actions": actions,
    }


def render_plan(plan):
    lines = []
    if not plan["has_ledger"]:
        lines.append("LEDGER   absent — unknown-old install: orphans are FLAG-ONLY, "
                     "package-owned files cannot be proven pristine, confirmation required.")
    counts = {}
    for a in plan["actions"]:
        counts[a["kind"]] = counts.get(a["kind"], 0) + 1
        if a["kind"] == "SAME":
            continue
        note = {
            "ADD": "new in this version",
            "REFRESH": "package file changed",
            "REFRESH?": "unknown provenance — no ledger to prove it pristine",
            "LOCAL-EDIT": "differs from what this package wrote — local edit would be LOST",
            "ORPHAN": "recorded-old − new manifest — removable",
            "ORPHAN-EDITED": "retired but locally modified — FLAG ONLY, never removed",
            "BRIEF-UNMARKED": "no managed block in CLAUDE.md — flag only, not modified",
        }.get(a["kind"], "")
        flag = "  [CONFIRM]" if a["confirm"] else ""
        lines.append("%-14s %-46s (%s)%s" % (a["kind"], a["path"], note, flag))
    old = plan["old_version"] or "unknown"
    new = plan["new_version"] or "unknown"
    lines.append("STAMP    %s -> %s%s" % (old, new, "   (same version — no-op)" if plan["noop"] else ""))
    lines.append("SUMMARY  " + ", ".join("%s %d" % (k, v) for k, v in sorted(counts.items())))
    return "\n".join(lines)


# ---------------------------------------------------------------- apply

def do_apply(plugin_root, project_root, confirm):
    plan = compute_plan(plugin_root, project_root)
    blocked = [a for a in plan["actions"] if a["confirm"] and not confirm]
    if blocked:
        print("BLOCKED — these package-owned files hold local edits (or cannot be proven "
              "pristine) and would be overwritten. Show the human the diff, then re-run with "
              "--confirm-overwrite:")
        for a in blocked:
            print("  %s  %s" % (a["kind"], a["path"]))
        return 2

    expected = expected_files(plugin_root, project_root)
    written, removed = [], []
    for a in plan["actions"]:
        kind, dest = a["kind"], a["path"]
        if dest == BRIEF_KEY:
            continue
        if kind in ("ADD", "REFRESH", "REFRESH?", "LOCAL-EDIT"):
            src = expected[dest]
            abs_dest = os.path.join(project_root, dest)
            with open(src, "rb") as fh:
                data = fh.read()
            mode = 0o755 if (dest in EXEC_BITS or dest.endswith(".sh")
                             or os.access(src, os.X_OK)) else None
            _atomic_write(abs_dest, data, mode)
            written.append(dest)
        elif kind == "ORPHAN":
            abs_dest = os.path.join(project_root, dest)
            try:
                os.remove(abs_dest)
                removed.append(dest)
            except OSError as exc:
                print("WARN could not remove orphan %s: %s" % (dest, exc))

    brief_action = next((a for a in plan["actions"] if a["path"] == BRIEF_KEY), None)
    if brief_action and brief_action["kind"] in ("REFRESH", "REFRESH?", "LOCAL-EDIT"):
        write_brief_block(project_root, render_brief(plugin_root, project_root))
        written.append(BRIEF_KEY)

    # Prune now-empty package directories left by orphan removal.
    for dest in removed:
        d = os.path.dirname(os.path.join(project_root, dest))
        while d and os.path.isdir(d) and not os.listdir(d):
            os.rmdir(d)
            d = os.path.dirname(d)

    # Stamp the version IN PLACE — every other config key is human-set and target-owned.
    cfg_path = os.path.join(project_root, CONFIG_REL)
    cfg = _read_json(cfg_path, {}) or {}
    cfg["workflow_version"] = plan["new_version"]
    _atomic_write(cfg_path, json.dumps(cfg, indent=2) + "\n")

    write_ledger(project_root, build_ledger(project_root, expected.keys(),
                                            plan["new_version"], _plugin_name(plugin_root)))
    for p in written:
        print("wrote   %s" % p)
    for p in removed:
        print("removed %s  (proven orphan)" % p)
    print("stamped workflow_version = %s; ledger written (%d files)"
          % (plan["new_version"], len(expected) + 1))
    return 0


def _plugin_name(plugin_root):
    return _read_json(os.path.join(plugin_root, ".claude-plugin", "plugin.json"), {}).get("name")


def do_record(plugin_root, project_root):
    """`/start` step 7: the install just landed — record what it wrote, for a future /update."""
    expected = expected_files(plugin_root, project_root)
    version = plugin_version(plugin_root)
    ledger = build_ledger(project_root, expected.keys(), version, _plugin_name(plugin_root))
    write_ledger(project_root, ledger)
    print("install-set recorded: %d files at workflow_version %s" % (len(ledger["files"]), version))
    if BRIEF_KEY not in ledger["files"]:
        print("WARN no managed orchestrator-brief block found in CLAUDE.md "
              "(expected the %s / %s markers) — /update will flag it instead of refreshing it."
              % (BRIEF_BEGIN, BRIEF_END))
    return 0


# ---------------------------------------------------------------- cli

def main(argv=None):
    ap = argparse.ArgumentParser(description="the /update reconcile runner")
    ap.add_argument("mode", choices=["plan", "apply", "record"])
    ap.add_argument("--plugin-root", required=True, help="${CLAUDE_PLUGIN_ROOT} of the NEW package")
    ap.add_argument("--project-root", default=".", help="${CLAUDE_PROJECT_DIR}")
    ap.add_argument("--json", action="store_true", help="plan: emit the plan as JSON")
    ap.add_argument("--confirm-overwrite", action="store_true",
                    help="apply: proceed over locally-edited package-owned files")
    args = ap.parse_args(argv)

    plugin_root = os.path.abspath(args.plugin_root)
    project_root = os.path.abspath(args.project_root)
    if not os.path.isdir(os.path.join(project_root, ".workflow")):
        print("no .workflow/ under %s — this project is not initialised; run /start, not /update."
              % project_root)
        return 1

    if args.mode == "plan":
        plan = compute_plan(plugin_root, project_root)
        print(json.dumps(plan, indent=2) if args.json else render_plan(plan))
        return 0
    if args.mode == "apply":
        return do_apply(plugin_root, project_root, args.confirm_overwrite)
    return do_record(plugin_root, project_root)


if __name__ == "__main__":
    sys.exit(main())

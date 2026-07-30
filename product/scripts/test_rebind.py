#!/usr/bin/env python3
"""Fixture tests for the rebind runner (stdlib unittest, zero-dep).

Everything here drives real directories, a real pointer, and a real backlog file. The
failures that matter — adopting another project's tree, re-creating when a lossless
re-point was available, landing secrets/ back on the mount that exposed them, filing a
loss entry no GC will ever collect — are all invisible to a type check, so nothing is
mocked that can be driven for real. The one exception is the mount probe, which cannot
be driven for real on an arbitrary CI filesystem; its own measurement is tested in
test_bus.py against the real tmpdir.
"""
import json
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bus  # noqa: E402
import rebind  # noqa: E402

HANDOFF = "# Handoff\n\nbootstrap: complete\n"
BACKLOG = "# Backlog — live OPEN queue\n\n- [ ] **something-else**\n"


class Fixture(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.root, True)
        self.home = os.path.join(self.root, "home")
        self.state = os.path.join(self.root, "xdgstate")
        os.makedirs(self.home)
        self._env(HOME=self.home, XDG_STATE_HOME=self.state)
        self.project = os.path.join(self.root, "proj")
        self.workflow = os.path.join(self.project, ".workflow")
        os.makedirs(self.workflow)
        self._write(os.path.join(self.workflow, "handoff.md"), HANDOFF)
        self._write(os.path.join(self.workflow, "backlog.md"), BACKLOG)

    # -- helpers
    def _env(self, **kw):
        for key, value in kw.items():
            had = os.environ.get(key)
            self.addCleanup(
                (lambda k, v: (os.environ.__setitem__(k, v) if v is not None
                               else os.environ.pop(k, None))), key, had)
            os.environ[key] = value

    def _write(self, path, text):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as fh:
            fh.write(text)

    def _pointer(self, root):
        self._write(os.path.join(self.workflow, "runtime.json"),
                    json.dumps({"runtime_root": root}))

    def _tree(self, path, stamp_to=None):
        """A directory that LOOKS like a live runtime tree."""
        os.makedirs(os.path.join(path, "parked"), exist_ok=True)
        self._write(os.path.join(path, "state.json"),
                    json.dumps({"status": "building", "current_item": "item-1"}))
        if stamp_to:
            bus.write_stamp(path, stamp_to)
        return path

    def _mount(self, verdict, only_under=None):
        """Stub the mount probe. `only_under` scopes the verdict to one subtree, which
        is what a real machine looks like: the repo mount is weak, the state dir the
        tree relocates TO is not. A global stub would also condemn the target."""
        real = bus.mount_honours_modes

        def stub(root):
            if only_under and not os.path.abspath(root).startswith(only_under):
                return real(root)
            return verdict
        bus.mount_honours_modes = stub
        self.addCleanup(setattr, bus, "mount_honours_modes", real)

    def _backlog(self):
        with open(os.path.join(self.workflow, "backlog.md")) as fh:
            return fh.read()


# --- the dry run is the same arithmetic as the apply ------------------------
class DryRunIsTrustworthy(Fixture):
    def test_check_touches_nothing(self):
        self._pointer(os.path.join(self.root, "gone"))
        before = sorted(os.listdir(self.workflow))
        p = rebind.plan(self.project)
        self.assertEqual(p["classification"], "RE-CREATE")
        self.assertEqual(sorted(os.listdir(self.workflow)), before)
        self.assertEqual(self._backlog(), BACKLOG)

    def test_check_and_apply_cannot_disagree_on_the_classification(self):
        """They share one plan() by construction — a dry run that could report a
        different verdict than the apply uses would be worse than no dry run."""
        old = self._tree(os.path.join(self.root, "old"))
        self._pointer(old)
        self.assertEqual(rebind.plan(self.project)["classification"], "HEALTHY")
        p, code = rebind.apply(self.project)
        self.assertEqual((p["classification"], code), ("HEALTHY", 0))


# --- classification ---------------------------------------------------------
class Classification(Fixture):
    def test_no_workflow_dir_is_a_start_situation_not_a_rebind(self):
        shutil.rmtree(self.workflow)
        p, code = rebind.apply(self.project)
        self.assertEqual(p["classification"], "NOT-STARTED")
        self.assertEqual(code, 2)
        self.assertIn("/start", " ".join(p["notes"]))

    def test_a_live_pointer_is_healthy_and_apply_is_a_no_op(self):
        old = self._tree(os.path.join(self.root, "old"), stamp_to=self.project)
        self._pointer(old)
        before = sorted(os.listdir(old))
        p, code = rebind.apply(self.project)
        self.assertEqual((p["classification"], code), ("HEALTHY", 0))
        self.assertEqual(sorted(os.listdir(old)), before)
        self.assertEqual(self._backlog(), BACKLOG)

    def test_a_legacy_unstamped_but_live_tree_is_healthy_and_gets_stamped(self):
        old = self._tree(os.path.join(self.root, "old"))
        self._pointer(old)
        p, code = rebind.apply(self.project)
        self.assertEqual((p["classification"], code), ("HEALTHY", 0))
        self.assertEqual(bus.read_stamp(old)["project_path"], self.project)

    def test_a_renamed_home_re_points_LOSSLESSLY(self):
        """The rule that would have recovered the incident that opened Phase 7 with
        nothing lost: same tree, same layout, only the $HOME prefix changed."""
        survivor = self._tree(os.path.join(self.home, ".local", "state",
                                           "dev-autonomous-workflow", "proj"))
        self._pointer("/home/someone-who-is-gone/.local/state/"
                      "dev-autonomous-workflow/proj")
        p, code = rebind.apply(self.project)
        self.assertEqual((p["classification"], code), ("RE-POINT", 0))
        self.assertEqual(p["target"], survivor)
        self.assertEqual(p["losses"], [])
        with open(os.path.join(self.workflow, "runtime.json")) as fh:
            self.assertEqual(json.load(fh)["runtime_root"], survivor)
        # the surviving state is exactly as it was — a re-point moves nothing
        with open(os.path.join(survivor, "state.json")) as fh:
            self.assertEqual(json.load(fh)["current_item"], "item-1")

    def test_the_canonical_derived_path_is_the_last_candidate(self):
        canonical = self._tree(bus.runtime_root_for(self.project))
        self._pointer("/nowhere/at/all")
        p, _ = rebind.apply(self.project)
        self.assertEqual((p["classification"], p["target"]), ("RE-POINT", canonical))

    def test_probe_order_prefers_the_literal_path_over_a_rehomed_one(self):
        literal = self._tree(os.path.join(self.home, "literal"))
        self._tree(os.path.join(self.home, "other"))
        self._pointer(literal)
        # literal is live, so this is HEALTHY and never reaches the probe at all
        self.assertEqual(rebind.plan(self.project)["classification"], "HEALTHY")

    def test_a_tree_bound_to_another_project_is_never_adopted(self):
        """isdir() is not identity. Adopting here corrupts two installs at once."""
        stray = self._tree(os.path.join(self.home, ".local", "state",
                                        "dev-autonomous-workflow", "proj"),
                           stamp_to="/somewhere/else")
        self._pointer("/home/gone/.local/state/dev-autonomous-workflow/proj")
        p, _ = rebind.apply(self.project)
        self.assertEqual(p["classification"], "RE-CREATE")
        self.assertNotEqual(p["target"], stray)
        rejected = [c for c in p["candidates"] if c["path"] == stray]
        self.assertTrue(rejected and not rejected[0]["valid"])
        self.assertIn("bound to another project", rejected[0]["why"])

    def test_an_empty_directory_is_not_a_surviving_runtime_tree(self):
        empty = os.path.join(self.home, ".local", "state",
                             "dev-autonomous-workflow", "proj")
        os.makedirs(empty)
        self._pointer("/home/gone/.local/state/dev-autonomous-workflow/proj")
        p, _ = rebind.apply(self.project)
        self.assertEqual(p["classification"], "RE-CREATE")

    def test_no_pointer_on_a_sound_mount_with_runtime_files_is_the_local_case(self):
        self._tree(self.workflow)
        self._mount(True)
        p, code = rebind.apply(self.project)
        self.assertEqual((p["classification"], code), ("HEALTHY", 0))
        self.assertFalse(os.path.exists(os.path.join(self.workflow, "runtime.json")))

    def test_no_pointer_on_a_weak_mount_relocates_the_tree_out(self):
        """The silent mis-bind: a clone under /mnt/c has no pointer (it is gitignored
        by design) and lands the token and secrets/ on a 0600-ignoring filesystem."""
        self._tree(self.workflow)
        self._write(os.path.join(self.workflow, "secrets", "runpod"), "sk-live")
        self._mount(False, only_under=self.project)
        p, code = rebind.apply(self.project)
        self.assertEqual((p["classification"], code), ("ADOPT-IN-PLACE", 0))
        target = bus.runtime_root_for(self.project)
        self.assertEqual(p["target"], target)
        with open(os.path.join(self.workflow, "runtime.json")) as fh:
            self.assertEqual(json.load(fh)["runtime_root"], target)
        # the data MOVED — it was not copied and left exposed, nor dropped
        with open(os.path.join(target, "secrets", "runpod")) as fh:
            self.assertEqual(fh.read(), "sk-live")
        self.assertFalse(os.path.exists(os.path.join(self.workflow, "secrets")))
        self.assertFalse(os.path.exists(os.path.join(self.workflow, "state.json")))

    def test_a_fresh_clone_with_nothing_runtime_re_creates(self):
        p, code = rebind.apply(self.project)
        self.assertEqual((p["classification"], code), ("RE-CREATE", 0))


# --- the FIRST bind (what /start step 3 runs) --------------------------------
class FirstBind(Fixture):
    """`bind` is `apply` minus the two things that would be lies on a fresh scaffold."""

    def test_a_fresh_scaffold_on_a_sound_mount_binds_in_place_with_no_pointer(self):
        p, code = rebind.apply(self.project, fresh=True)
        self.assertEqual((p["classification"], code), ("BIND", 0))
        self.assertEqual(p["target"], self.workflow)
        self.assertFalse(os.path.exists(os.path.join(self.workflow, "runtime.json")))
        for name in rebind.RUNTIME_DIRS:
            self.assertTrue(os.path.isdir(os.path.join(self.workflow, name)), name)

    def test_a_fresh_scaffold_on_a_weak_mount_relocates_and_points(self):
        self._mount(False, only_under=self.project)
        p, code = rebind.apply(self.project, fresh=True)
        target = bus.runtime_root_for(self.project)
        self.assertEqual((p["classification"], p["target"], code), ("BIND", target, 0))
        with open(os.path.join(self.workflow, "runtime.json")) as fh:
            self.assertEqual(json.load(fh)["runtime_root"], target)
        self.assertEqual(bus.read_stamp(target)["project_path"], self.project)

    def test_it_files_NOTHING_against_a_project_on_its_first_minute(self):
        """Three "lost in a machine move" issues against a project being started would
        be a lie the backlog then carries until a human closes it by hand."""
        rebind.apply(self.project, fresh=True)
        self.assertEqual(self._backlog(), BACKLOG)

    def test_it_never_writes_a_state_json(self):
        """The /start motion publishes state.json at every stage boundary — a position
        this runner has no business guessing."""
        rebind.apply(self.project, fresh=True)
        self.assertFalse(os.path.exists(os.path.join(self.workflow, "state.json")))

    def test_an_in_place_root_is_not_stamped(self):
        """Identity is true by construction inside .workflow/: there is no pointer to
        be wrong. A stamp there is one more gitignore entry earning nothing."""
        rebind.apply(self.project, fresh=True)
        self.assertFalse(os.path.exists(
            os.path.join(self.workflow, bus.RUNTIME_STAMP)))

    def test_it_still_refuses_a_mount_that_cannot_hold_the_tree(self):
        self._mount(False)
        p, code = rebind.apply(self.project, fresh=True)
        self.assertEqual(code, 2)
        self.assertIn("refusing", p["error"])

    def test_bind_is_idempotent(self):
        rebind.apply(self.project, fresh=True)
        p, code = rebind.apply(self.project, fresh=True)
        self.assertEqual((p["classification"], code), ("HEALTHY", 0))


# --- re-creation ------------------------------------------------------------
class ReCreate(Fixture):
    def setUp(self):
        super(ReCreate, self).setUp()
        self._pointer("/home/guy/.local/state/dev-autonomous-workflow/proj")

    def test_it_rebuilds_the_shape_and_binds_the_pointer(self):
        p, code = rebind.apply(self.project)
        self.assertEqual((p["classification"], code), ("RE-CREATE", 0))
        target = bus.runtime_root_for(self.project)
        for name in rebind.RUNTIME_DIRS:
            self.assertTrue(os.path.isdir(os.path.join(target, name)), name)
        self.assertTrue(os.path.exists(os.path.join(target, "alerts.json")))
        self.assertEqual(bus.read_stamp(target)["project_path"], self.project)
        with open(os.path.join(self.workflow, "runtime.json")) as fh:
            self.assertEqual(json.load(fh)["runtime_root"], target)

    def test_it_does_NOT_reconstruct_liveness_artifacts(self):
        """A stale bus.json or orchestrator.lock is worse than an absent one: the
        first advertises a dead daemon, the second blocks a live orchestrator."""
        rebind.apply(self.project)
        target = bus.runtime_root_for(self.project)
        for name in ("bus.json", "bus.lock", "orchestrator.lock"):
            self.assertFalse(os.path.exists(os.path.join(target, name)), name)

    def test_the_state_it_writes_is_marked_as_a_placeholder(self):
        """The runner owns the arithmetic; recovering a loop position from prose is
        judgment, and a confidently-wrong current_item is worse than an admitted gap."""
        p, _ = rebind.apply(self.project)
        with open(os.path.join(bus.runtime_root_for(self.project), "state.json")) as fh:
            st = json.load(fh)
        self.assertEqual(st["status"], "idle")
        self.assertIsNone(st["current_item"])
        self.assertIn("NOT recovered", st["note"])
        self.assertTrue(any("handoff.md" in r for r in p["reelicit"]))

    def test_it_refuses_to_land_the_tree_on_a_mount_that_cannot_hold_it(self):
        """A repair that re-creates the original exposure is not a repair."""
        self._mount(False)
        p, code = rebind.apply(self.project)
        self.assertEqual(code, 2)
        self.assertIn("refusing", p["error"])

    def test_the_result_is_healthy_and_a_second_apply_changes_nothing(self):
        rebind.apply(self.project)
        target = bus.runtime_root_for(self.project)
        with open(os.path.join(target, "state.json")) as fh:
            first = fh.read()
        p, code = rebind.apply(self.project)
        self.assertEqual((p["classification"], code), ("HEALTHY", 0))
        with open(os.path.join(target, "state.json")) as fh:
            self.assertEqual(fh.read(), first)

    def test_the_rebound_tree_then_resolves_through_Paths(self):
        """The end-to-end contract: after a rebind, the thing that was raising stops."""
        with self.assertRaises(SystemExit):
            bus.Paths(self.workflow)
        rebind.apply(self.project)
        self.assertEqual(bus.Paths(self.workflow).runtime,
                         bus.runtime_root_for(self.project))


# --- loss is filed, durably AND boundedly ------------------------------------
class LossIsFiled(Fixture):
    def setUp(self):
        super(LossIsFiled, self).setUp()
        self._pointer("/home/guy/.local/state/dev-autonomous-workflow/proj")

    def test_every_loss_lands_in_the_backlog(self):
        """A printed report is durability that depends on a human remembering."""
        rebind.apply(self.project)
        text = self._backlog()
        for word in ("parked", "outbox", "secret store"):
            self.assertIn(word, text)
        self.assertIn(rebind.BACKLOG_SECTION, text)

    def test_entries_are_in_the_shape_prioritize_can_RETIRE(self):
        """D59 bounds backlog.md by CLOSABILITY. Free prose matches neither GC rule,
        so every machine move would leave permanent sediment; a local issue with no
        github_ref closes on its backlog done-flip, which is a shape the GC collects."""
        rebind.apply(self.project)
        entries = [ln for ln in self._backlog().splitlines()
                   if ln.startswith("- [ ] **rebind:")]
        self.assertEqual(len(entries), 3)
        for ln in entries:
            self.assertIn("`kind=", ln)
            self.assertIn("`severity=", ln)
            self.assertIn("`source=rebind:", ln)
            self.assertNotIn("github_ref", ln)

    def test_it_never_touches_the_backlog_the_project_already_had(self):
        rebind.apply(self.project)
        self.assertIn("- [ ] **something-else**", self._backlog())
        self.assertTrue(self._backlog().startswith("# Backlog — live OPEN queue"))

    def test_re_running_does_not_duplicate_an_open_entry(self):
        rebind.apply(self.project)
        first = self._backlog()
        os.unlink(os.path.join(self.workflow, "runtime.json"))
        shutil.rmtree(bus.runtime_root_for(self.project))
        self._pointer("/home/guy/.local/state/dev-autonomous-workflow/proj")
        rebind.apply(self.project)
        self.assertEqual(self._backlog().count("**rebind: outbox lost"), 1)
        self.assertEqual(len(self._backlog().splitlines()),
                         len(first.splitlines()))

    def test_a_CLOSED_entry_does_not_block_a_later_machine_move(self):
        rebind.apply(self.project)
        closed = self._backlog().replace("- [ ] **rebind:", "- [x] **rebind:")
        self._write(os.path.join(self.workflow, "backlog.md"), closed)
        os.unlink(os.path.join(self.workflow, "runtime.json"))
        shutil.rmtree(bus.runtime_root_for(self.project))
        self._pointer("/home/guy/.local/state/dev-autonomous-workflow/proj")
        rebind.apply(self.project)
        self.assertEqual(self._backlog().count("- [ ] **rebind: outbox lost"), 1)

    def test_a_LOSSLESS_re_point_files_nothing(self):
        self._tree(os.path.join(self.home, ".local", "state",
                                "dev-autonomous-workflow", "proj"))
        rebind.apply(self.project)
        self.assertEqual(self._backlog(), BACKLOG)

    def test_an_unwritable_backlog_reports_rather_than_swallowing(self):
        os.chmod(os.path.join(self.workflow, "backlog.md"), 0o000)
        self.addCleanup(os.chmod, os.path.join(self.workflow, "backlog.md"), 0o644)
        p, code = rebind.apply(self.project)
        self.assertEqual(code, 0)
        self.assertTrue(any("NOT filed" in a for a in p["applied"]))


# --- the declared secret set ---------------------------------------------------
class DeclaredSecrets(Fixture):
    """An empty `secrets/` is indistinguishable from a project that needs none, so a
    machine move could only ever say "the store is gone, work out what was in it".
    `secrets_required[]` turns that into a list."""

    def _config(self, **kw):
        self._write(os.path.join(self.workflow, "config.json"), json.dumps(kw))

    def _store(self, root, payloads):
        for i, payload in enumerate(payloads):
            self._write(os.path.join(root, "secrets", "m%d.json" % i),
                        json.dumps(payload))

    def _entries(self):
        return [ln for ln in self._backlog().splitlines()
                if ln.startswith("- [ ] **rebind:")]

    def test_a_recreate_itemizes_every_declared_key(self):
        self._config(secrets_required=["POLAR_WEBHOOK_SECRET", "CLERK_SECRET_KEY"])
        self._pointer("/home/guy/.local/state/dev-autonomous-workflow/proj")
        p, _ = rebind.apply(self.project, probe=False)
        text = self._backlog()
        self.assertIn("POLAR_WEBHOOK_SECRET", text)
        self.assertIn("CLERK_SECRET_KEY", text)
        self.assertEqual(len(self._entries()), 4)  # 3 generic + the itemized one

    def test_no_declaration_means_no_itemization_not_no_loss(self):
        """Absent is "we cannot tell", not "nothing is missing" — the generic
        store-lost entry still has to cover the move."""
        self._pointer("/home/guy/.local/state/dev-autonomous-workflow/proj")
        rebind.apply(self.project, probe=False)
        self.assertEqual(len(self._entries()), 3)
        self.assertIn("secret store", self._backlog())

    def test_a_surviving_store_reports_nothing_missing(self):
        surviving = self._tree(os.path.join(
            self.home, ".local", "state", "dev-autonomous-workflow", "proj"))
        self._store(surviving, [{"returns": {"POLAR_WEBHOOK_SECRET": "whsec_x",
                                             "sensitive": True}}])
        self._config(secrets_required=["POLAR_WEBHOOK_SECRET"])
        self._pointer("/home/guy/.local/state/dev-autonomous-workflow/proj")
        p, _ = rebind.apply(self.project, probe=False)
        self.assertEqual(p["classification"], "RE-POINT")
        self.assertEqual(self._backlog(), BACKLOG)

    def test_a_partial_survival_names_only_what_is_gone(self):
        surviving = self._tree(os.path.join(
            self.home, ".local", "state", "dev-autonomous-workflow", "proj"))
        self._store(surviving, [{"returns": {"KEPT_KEY": "v", "sensitive": True}}])
        self._config(secrets_required=["KEPT_KEY", "GONE_KEY"])
        self._pointer("/home/guy/.local/state/dev-autonomous-workflow/proj")
        rebind.apply(self.project, probe=False)
        text = self._backlog()
        self.assertIn("GONE_KEY", text.split("does not hold:")[1])
        self.assertNotIn("KEPT_KEY", text.split("does not hold:")[1])

    def test_no_secret_VALUE_ever_reaches_the_committed_backlog(self):
        """config.json and backlog.md are both committed. Names only, always."""
        surviving = self._tree(os.path.join(
            self.home, ".local", "state", "dev-autonomous-workflow", "proj"))
        self._store(surviving, [{"returns": {"A_KEY": "sk_live_NEVERCOMMITTHIS",
                                             "sensitive": True}}])
        self._config(secrets_required=["A_KEY", "MISSING_KEY"])
        self._pointer("/home/guy/.local/state/dev-autonomous-workflow/proj")
        p, _ = rebind.apply(self.project, probe=False)
        self.assertNotIn("sk_live_NEVERCOMMITTHIS", self._backlog())
        self.assertNotIn("sk_live_NEVERCOMMITTHIS", rebind.render(p, "apply"))
        self.assertNotIn("sk_live_NEVERCOMMITTHIS", json.dumps(p))

    def test_the_dry_run_reports_it_without_touching_anything(self):
        """Pure reads, so unlike the bindability probe this one belongs in `check`."""
        self._config(secrets_required=["SOME_KEY"])
        self._pointer(os.path.join(self.root, "gone"))
        text = _capture(["check", "--project-root", self.project])[0]
        self.assertIn("SOME_KEY", text)
        self.assertEqual(self._backlog(), BACKLOG)

    def test_a_malformed_declaration_is_ignored_not_fatal(self):
        for bad in ("not-a-list", {"a": 1}, [1, 2, None], []):
            self._config(secrets_required=bad)
            self.assertEqual(rebind.required_secrets(self.workflow), [])

    def test_the_sensitive_marker_is_not_mistaken_for_a_key_name(self):
        store = os.path.join(self.root, "s")
        self._store(store, [{"returns": {"sensitive": True, "REAL": "v"}}])
        found = rebind.present_secrets(os.path.join(store, "secrets"))
        self.assertIn("REAL", found)
        self.assertNotIn("sensitive", found)

    def test_an_unreadable_store_entry_is_skipped_not_fatal(self):
        store = os.path.join(self.root, "s")
        self._store(store, [{"returns": {"GOOD": "v"}}])
        self._write(os.path.join(store, "secrets", "junk.json"), "{not json")
        self.assertIn("GOOD", rebind.present_secrets(os.path.join(store, "secrets")))

    def test_a_first_bind_declares_nothing_and_loses_nothing(self):
        self._config(secrets_required=["SOME_KEY"])
        p, _ = rebind.apply(self.project, fresh=True, probe=False)
        self.assertEqual(p["losses"], [])
        self.assertEqual(self._backlog(), BACKLOG)


# --- the bindability probe ---------------------------------------------------
class Bindability(Fixture):
    """A correctly re-bound project can still be unable to make a single commit: the
    committed `checks.env` names a toolchain that is machine-local and gitignored. The
    probe runs the real gate the real way rather than guessing at a toolchain — so
    these drive a real `checks.sh` and a real subprocess."""

    def setUp(self):
        super(Bindability, self).setUp()
        self._pointer("/home/guy/.local/state/dev-autonomous-workflow/proj")

    def _checks(self, body):
        path = os.path.join(self.workflow, "checks.sh")
        self._write(path, "#!/usr/bin/env bash\n" + body + "\n")
        os.chmod(path, 0o755)
        return path

    def _entries(self):
        return [ln for ln in self._backlog().splitlines()
                if ln.startswith("- [ ] **rebind:")]

    def test_a_project_with_no_checks_runner_is_simply_not_probed(self):
        p, _ = rebind.apply(self.project)
        self.assertFalse(p["bindability"]["ran"])
        self.assertEqual(len(self._entries()), 3)  # the three real losses, no fourth

    def test_a_clean_gate_reports_bindable_and_files_nothing(self):
        self._checks("exit 0")
        p, _ = rebind.apply(self.project)
        self.assertTrue(p["bindability"]["clean"])
        self.assertEqual(len(self._entries()), 3)

    def test_a_failing_gate_is_filed_as_a_typed_loss(self):
        """127 is what a missing toolchain actually exits — but the probe files it
        without claiming to know that, which is the whole point."""
        self._checks("echo 'sh: npm: not found' >&2; exit 127")
        p, _ = rebind.apply(self.project)
        self.assertFalse(p["bindability"]["clean"])
        self.assertEqual(p["bindability"]["exit_code"], 127)
        entries = self._entries()
        self.assertEqual(len(entries), 4)
        gate = [e for e in entries if "mechanical commit gate" in e][0]
        self.assertIn("`kind=bug`", gate)
        self.assertIn("`severity=high`", gate)
        self.assertIn("`source=rebind:", gate)
        self.assertNotIn("github_ref", gate)

    def test_the_gate_output_reaches_the_human_but_never_the_committed_file(self):
        """backlog.md is COMMITTED and the gate's output is arbitrary subprocess text.
        The one control that would catch a secret in it is the staged-diff scan in the
        very gate that just failed to run, so the tail goes to stdout only."""
        self._checks("echo 'FAILED: token=sk_live_HAHAHAHAHAHAHAHA'; exit 1")
        p, _ = rebind.apply(self.project)
        self.assertNotIn("sk_live_HAHAHA", self._backlog())
        self.assertIn("sk_live_HAHAHA", rebind.render(p, "apply"))

    def test_it_runs_the_gate_the_way_the_pre_commit_hook_runs_it(self):
        """Same command, same cwd — that identity is what makes the answer mean
        anything. A probe run from somewhere else answers a different question."""
        self._checks("pwd > '%s/where'; exit 0" % self.root)
        rebind.apply(self.project)
        with open(os.path.join(self.root, "where")) as fh:
            self.assertEqual(os.path.realpath(fh.read().strip()),
                             os.path.realpath(self.project))

    def test_check_is_a_dry_run_and_does_not_run_the_gate(self):
        """`check`'s verified contract is that it writes nothing, and the gate runs the
        project's tests — which write caches and build artifacts."""
        self._checks("touch '%s/ran'; exit 0" % self.root)
        text = _capture(["check", "--project-root", self.project])[0]
        self.assertFalse(os.path.exists(os.path.join(self.root, "ran")))
        self.assertIn("NOT PROBED", text)

    def test_no_probe_skips_it(self):
        self._checks("touch '%s/ran'; exit 1" % self.root)
        out, code = _capture(["apply", "--project-root", self.project, "--no-probe"])
        self.assertEqual(code, 0)
        self.assertFalse(os.path.exists(os.path.join(self.root, "ran")))
        self.assertEqual(len(self._entries()), 3)

    def test_a_first_bind_is_not_probed(self):
        """At /start step 3 the stack is not wired yet, so the gate would be answering
        a question nobody asked."""
        self._checks("touch '%s/ran'; exit 1" % self.root)
        p, _ = rebind.apply(self.project, fresh=True)
        self.assertIsNone(p["bindability"])
        self.assertFalse(os.path.exists(os.path.join(self.root, "ran")))

    def test_a_healthy_install_is_not_probed(self):
        """`apply` is a fixed point on a healthy install, and running a project's whole
        test suite is not a no-op."""
        old = self._tree(os.path.join(self.root, "live"))
        self._pointer(old)
        self._checks("touch '%s/ran'; exit 1" % self.root)
        p, _ = rebind.apply(self.project)
        self.assertEqual(p["classification"], "HEALTHY")
        self.assertIsNone(p["bindability"])
        self.assertFalse(os.path.exists(os.path.join(self.root, "ran")))

    def test_a_hung_gate_does_not_hang_the_repair(self):
        self._checks("sleep 30")
        real = rebind.CHECKS_TIMEOUT
        rebind.CHECKS_TIMEOUT = 1
        self.addCleanup(setattr, rebind, "CHECKS_TIMEOUT", real)
        p, code = rebind.apply(self.project)
        self.assertEqual(code, 0)
        self.assertTrue(p["bindability"]["timed_out"])
        self.assertFalse(p["bindability"]["clean"])
        self.assertEqual(len(self._entries()), 4)

    def test_the_report_does_not_diagnose_the_cause(self):
        """It reports an OBSERVABLE. Classifying "missing toolchain" vs "failing test"
        would need to know which side of a WSL/Windows boundary a command belongs to —
        exactly the guess that went wrong on the real machine move."""
        self._checks("exit 1")
        rebind.apply(self.project)
        self.assertIn("does not diagnose", self._backlog())

    def test_a_failing_gate_entry_is_not_duplicated_on_a_re_run(self):
        self._checks("exit 1")
        rebind.apply(self.project)
        os.unlink(os.path.join(self.workflow, "runtime.json"))
        shutil.rmtree(bus.runtime_root_for(self.project))
        self._pointer("/home/guy/.local/state/dev-autonomous-workflow/proj")
        rebind.apply(self.project)
        self.assertEqual(
            self._backlog().count("**rebind: the mechanical commit gate"), 1)


# --- the $HOME re-prefix rule ------------------------------------------------
class Rehome(unittest.TestCase):
    def setUp(self):
        self.had = os.environ.get("HOME")
        os.environ["HOME"] = "/home/newuser"
        self.addCleanup(lambda: (os.environ.__setitem__("HOME", self.had)
                                 if self.had is not None
                                 else os.environ.pop("HOME", None)))

    def test_it_swaps_a_linux_home(self):
        self.assertEqual(rebind.rehome("/home/guy/.local/state/x"),
                         "/home/newuser/.local/state/x")

    def test_it_swaps_a_macos_home(self):
        self.assertEqual(rebind.rehome("/Users/guy/Library/x"),
                         "/home/newuser/Library/x")

    def test_it_swaps_root(self):
        self.assertEqual(rebind.rehome("/root/state/x"), "/home/newuser/state/x")

    def test_a_path_outside_any_home_yields_no_candidate(self):
        self.assertIsNone(rebind.rehome("/var/lib/dev-autonomous-workflow/x"))

    def test_a_path_already_under_this_home_yields_no_duplicate_candidate(self):
        self.assertIsNone(rebind.rehome("/home/newuser/.local/state/x"))


# --- the cli ----------------------------------------------------------------
class Cli(Fixture):
    def test_check_emits_json_on_request(self):
        self._pointer(os.path.join(self.root, "gone"))
        out = _capture(["check", "--project-root", self.project, "--json"])
        self.assertEqual(json.loads(out[0])["classification"], "RE-CREATE")
        self.assertEqual(out[1], 0)

    def test_not_started_exits_nonzero_so_a_caller_can_branch(self):
        shutil.rmtree(self.workflow)
        self.assertEqual(_capture(["check", "--project-root", self.project])[1], 2)

    def test_the_prose_report_names_the_losses(self):
        self._pointer("/home/guy/.local/state/dev-autonomous-workflow/proj")
        text = _capture(["check", "--project-root", self.project])[0]
        self.assertIn("RE-CREATE", text)
        self.assertIn("LOST [bug/high]", text)
        self.assertIn("would:", text)


def _capture(argv):
    import io
    import contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = rebind.main(argv)
    return buf.getvalue(), code


if __name__ == "__main__":
    unittest.main()

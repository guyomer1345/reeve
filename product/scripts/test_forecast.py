#!/usr/bin/env python3
"""Fixture tests for the chain-forecast lifecycle owner (stdlib unittest, zero-dep)."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import forecast as f  # noqa: E402

SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "forecast.py")


def a_forecast(**kw):
    fc = {
        "forecast_id": "item-1",
        "created_at": "2026-08-03T10:00:00Z",
        "status": "draft",
        "for": {"what": "add hebrew transcription", "item_id": "item-1"},
        "events": [
            {"n": 1, "node": "planner:plan-one", "what": "plan the change",
             "likely": "a plan with 4 steps", "fallback": "open decisions → decision-engineer"},
            {"n": 2, "node": "checkpoint:setup", "what": "you hand over the API key",
             "likely": "you paste it",
             "gate": {"kind": "setup", "prefill": {"secrets": ["IVRIT_API_KEY"]}}},
            {"n": 3, "node": "execute", "what": "build it", "likely": "a changelog"},
        ],
        "horizon": {"beyond": 3,
                    "note": "unforeseeable past here — do not read this as unattended"},
    }
    fc.update(kw)
    return fc


def _write(path, obj, raw=None):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(raw if raw is not None else json.dumps(obj))
    return path


class Lint(unittest.TestCase):
    def test_a_clean_draft_passes(self):
        self.assertEqual(f.lint(a_forecast()), [])

    def test_an_unsafe_id_is_refused(self):
        # the id becomes a FILENAME under forecasts/ — same path-safety class as a ticket id
        for bad in ("../../etc/passwd", "a/b", "", ".", "..", None, 7):
            with self.subTest(bad=bad):
                self.assertTrue(f.lint(a_forecast(forecast_id=bad)))

    def test_an_unknown_status_is_refused(self):
        self.assertTrue(any("status" in x for x in f.lint(a_forecast(status="pending"))))

    def test_an_empty_chain_is_refused(self):
        self.assertTrue(f.lint(a_forecast(events=[])))

    def test_out_of_order_events_are_refused(self):
        fc = a_forecast()
        fc["events"][1]["n"] = 5
        self.assertTrue(any("order" in x or "n=" in x for x in f.lint(fc)), f.lint(fc))

    def test_an_event_missing_its_node_is_refused(self):
        fc = a_forecast()
        del fc["events"][0]["node"]
        self.assertTrue(f.lint(fc))

    # --- the horizon: D159's "mark your own blind spots" made mechanical -------
    def test_a_forecast_with_no_horizon_is_refused(self):
        """A forecast that does not say where it stops reads as complete. Execute-
        discovered needs are unforecastable BY DEFINITION, so the absence of a stated
        horizon is the silent-cap failure `align`'s honest-truncation rule exists for."""
        fc = a_forecast()
        del fc["horizon"]
        self.assertTrue(any("horizon" in x for x in f.lint(fc)), f.lint(fc))

    # --- the names-only invariant (D162): a LINTED invariant, not a promise ----
    def test_a_credential_NAME_is_allowed(self):
        self.assertEqual(f.lint(a_forecast()), [])

    def test_a_credential_VALUE_shaped_entry_is_refused(self):
        """The forecast is COMMITTED. It is safe to commit only because it carries key
        NAMES — the same class as config.json's secrets_required[]. A dict entry is how
        a value gets in, so the shape itself is refused."""
        fc = a_forecast()
        fc["events"][1]["gate"]["prefill"]["secrets"] = [{"IVRIT_API_KEY": "sk-live-abc123"}]
        self.assertTrue(any("name" in x.lower() for x in f.lint(fc)), f.lint(fc))

    def test_a_lowercase_non_keyname_secret_is_refused(self):
        fc = a_forecast()
        fc["events"][1]["gate"]["prefill"]["secrets"] = ["sk-live-abc123"]
        self.assertTrue(f.lint(fc))

    def test_a_value_key_anywhere_in_the_record_is_refused(self):
        """Belt-and-braces over the shape check: nothing in a committed forecast has any
        business carrying a field called `value`."""
        fc = a_forecast()
        fc["events"][1]["gate"]["value"] = "sk-live-abc123"
        self.assertTrue(any("value" in x for x in f.lint(fc)), f.lint(fc))

    def test_provides_takes_names_too(self):
        fc = a_forecast()
        fc["events"][1]["gate"]["prefill"]["provides"] = ["POLAR_WEBHOOK_URL"]
        self.assertEqual(f.lint(fc), [])


class Freeze(unittest.TestCase):
    def test_freeze_stamps_status_time_and_digest(self):
        frozen = f.freeze(a_forecast(), now="2026-08-03T11:00:00Z")
        self.assertEqual(frozen["status"], "frozen")
        self.assertEqual(frozen["frozen_at"], "2026-08-03T11:00:00Z")
        self.assertEqual(frozen["events_sha256"], f.events_digest(frozen["events"]))
        self.assertEqual(f.lint(frozen), [])

    def test_freeze_does_not_mutate_the_chain(self):
        fc = a_forecast()
        before = json.dumps(fc["events"], sort_keys=True)
        f.freeze(fc, now="2026-08-03T11:00:00Z")
        self.assertEqual(json.dumps(fc["events"], sort_keys=True), before)

    def test_refreezing_keeps_the_original_freeze_time(self):
        """`approve` freezes. A re-run of the apply path must be a no-op, not a new
        anchor — the frozen forecast is what reality is compared against, and moving its
        timestamp would silently re-baseline the comparison."""
        once = f.freeze(a_forecast(), now="2026-08-03T11:00:00Z")
        twice = f.freeze(once, now="2026-08-03T12:00:00Z")
        self.assertEqual(twice["frozen_at"], "2026-08-03T11:00:00Z")

    def test_an_edited_frozen_forecast_fails_lint(self):
        """The digest is what makes the freeze real rather than a label: a frozen
        forecast that was edited is not the thing the human approved."""
        frozen = f.freeze(a_forecast(), now="2026-08-03T11:00:00Z")
        frozen["events"][2]["what"] = "quietly build something else"
        self.assertTrue(any("sha256" in x or "edited" in x for x in f.lint(frozen)),
                        f.lint(frozen))

    def test_digest_ignores_key_order(self):
        a = [{"n": 1, "node": "execute", "what": "x"}]
        b = [{"what": "x", "node": "execute", "n": 1}]
        self.assertEqual(f.events_digest(a), f.events_digest(b))


class Cli(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def _run(self, *args):
        return subprocess.run([sys.executable, SCRIPT, *args],
                              capture_output=True, text=True, cwd=self.tmp)

    def test_lint_clean_exits_zero(self):
        p = _write(os.path.join(self.tmp, "fc.json"), a_forecast())
        self.assertEqual(self._run("lint", p).returncode, 0)

    def test_lint_dirty_exits_one_and_names_the_problem(self):
        fc = a_forecast()
        del fc["horizon"]
        p = _write(os.path.join(self.tmp, "fc.json"), fc)
        r = self._run("lint", p)
        self.assertEqual(r.returncode, 1)
        self.assertIn("horizon", r.stderr)

    def test_unreadable_input_is_a_usage_error_not_a_traceback(self):
        p = _write(os.path.join(self.tmp, "fc.json"), None, raw="{not json")
        r = self._run("lint", p)
        self.assertNotIn("Traceback", r.stderr)
        self.assertEqual(r.returncode, 2)

    def test_freeze_writes_the_record_back(self):
        p = _write(os.path.join(self.tmp, "fc.json"), a_forecast())
        self.assertEqual(self._run("freeze", p).returncode, 0)
        with open(p) as fh:
            got = json.load(fh)
        self.assertEqual(got["status"], "frozen")
        self.assertTrue(got.get("frozen_at"))
        self.assertEqual(got["events_sha256"], f.events_digest(got["events"]))

    def test_freeze_refuses_a_record_that_does_not_lint(self):
        """Freezing is what makes a forecast authoritative, so it is the wrong moment to
        let a broken one through — an unlintable frozen record is a bad anchor forever."""
        fc = a_forecast()
        del fc["horizon"]
        p = _write(os.path.join(self.tmp, "fc.json"), fc)
        r = self._run("freeze", p)
        self.assertEqual(r.returncode, 1)
        with open(p) as fh:
            self.assertEqual(json.load(fh)["status"], "draft", "it wrote anyway")


# --- the reality half: derived from anchors, never from state.json -------------

class Reality(unittest.TestCase):
    """Reality is DERIVED. There is no writer, no second ledger, and nothing to keep in
    step — each node is resolved through the durable effect it leaves behind. `state.json`
    is deliberately not the source: it is volatile and holds only the CURRENT node, never
    a history, so "which events have happened" is not a question it can answer."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.w = os.path.join(self.tmp, ".workflow")
        os.makedirs(os.path.join(self.w, "items", "item-1"))
        os.makedirs(os.path.join(self.w, "parked"))

    def _item(self, name):
        open(os.path.join(self.w, "items", "item-1", name), "w").close()

    def _park(self, kind, answered=False, ticket="item-1"):
        rec = {"ticket_id": ticket, "token": "t", "checkpoint": {"kind": kind}}
        if answered:
            rec["answered_at"] = "2026-08-03T11:00:00Z"
        with open(os.path.join(self.w, "parked", ticket + "-" + kind + ".json"), "w") as fh:
            json.dump(rec, fh)

    def _fc(self, nodes, **kw):
        fc = a_forecast(**kw)
        fc["events"] = [{"n": i + 1, "node": n, "what": "x"} for i, n in enumerate(nodes)]
        fc["horizon"] = {"beyond": len(nodes), "note": "unforeseeable past here"}
        return fc

    def _reality(self, fc):
        return f.reality(fc, workflow_dir=self.w)

    def _states(self, fc):
        return {r["node"]: r["state"] for r in self._reality(fc)["events"]}

    def test_an_absent_anchor_is_PENDING_not_done(self):
        st = self._states(self._fc(["planner:plan-one", "execute"]))
        self.assertEqual(st["planner:plan-one"], "pending")
        self.assertEqual(st["execute"], "pending")

    def test_a_present_anchor_is_DONE(self):
        self._item("plan.md")
        st = self._states(self._fc(["planner:plan-one", "execute"]))
        self.assertEqual(st["planner:plan-one"], "done")
        self.assertEqual(st["execute"], "pending")

    def test_the_chain_fills_in_as_the_loop_walks_it(self):
        fc = self._fc(["planner:plan-one", "execute", "verify"])
        self._item("plan.md"); self._item("changelog.md")
        st = self._states(fc)
        self.assertEqual([st[n] for n in ("planner:plan-one", "execute", "verify")],
                         ["done", "done", "pending"])

    def test_an_open_checkpoint_reads_OPEN_and_an_answered_one_DONE(self):
        fc = self._fc(["checkpoint:setup", "checkpoint:qa"])
        self._park("setup")
        self._park("qa", answered=True)
        st = self._states(fc)
        self.assertEqual(st["checkpoint:setup"], "open")
        self.assertEqual(st["checkpoint:qa"], "done")

    def test_a_checkpoint_parked_for_a_DIFFERENT_change_is_not_this_chains(self):
        """`parked/` is project-wide, and every other probe here is item-scoped.

        Unscoped, this row read `open` — whose whole meaning is "the machine is waiting on
        YOU, here" — off a checkpoint belonging to some other change, pointing the human at
        a step that was not waiting on them at all. And since `prioritize` emits parallel
        items, an open checkpoint somewhere is the NORMAL state, so it would have been
        wrong most of the time. Caught by rendering the panel in a real browser.
        """
        fc = self._fc(["checkpoint:qa"])
        self._park("qa", ticket="some-other-change")
        self.assertEqual(self._states(fc)["checkpoint:qa"], "pending")

    def test_this_changes_OWN_checkpoint_still_reads_open(self):
        """The other side of the scoping: it must not have gone blind."""
        fc = self._fc(["checkpoint:qa"])
        self._park("qa")
        self.assertEqual(self._states(fc)["checkpoint:qa"], "open")

    def test_a_node_with_NO_anchor_is_unknown_never_pending(self):
        """The honest fourth state. `decision-engineer`'s output is a global decision
        record that cannot be tied to one item, so this column must not claim it did not
        happen — it must say it cannot tell."""
        st = self._states(self._fc(["decision-engineer"]))
        self.assertEqual(st["decision-engineer"], "unknown")

    def test_a_frozen_forecast_marks_its_own_event_done(self):
        fc = self._fc(["create-forecast", "execute"])
        self.assertEqual(self._states(fc)["create-forecast"], "pending")
        frozen = f.freeze(fc, now="2026-08-03T11:00:00Z")
        self.assertEqual(self._states(frozen)["create-forecast"], "done")


class Divergence(unittest.TestCase):
    """The same anchor table read the other way: an effect that fired for a node the
    forecast never named. That is the structural tier — the machine took a turn nobody
    saw coming — and it must not silently continue."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.w = os.path.join(self.tmp, ".workflow")
        os.makedirs(os.path.join(self.w, "items", "item-1"))
        os.makedirs(os.path.join(self.w, "parked"))

    def _item(self, name):
        open(os.path.join(self.w, "items", "item-1", name), "w").close()

    def _fc(self, nodes):
        fc = a_forecast()
        fc["events"] = [{"n": i + 1, "node": n, "what": "x"} for i, n in enumerate(nodes)]
        fc["horizon"] = {"beyond": len(nodes), "note": "unforeseeable past here"}
        return fc

    def _div(self, fc):
        return f.reality(fc, workflow_dir=self.w)["divergences"]

    def _park(self, kind, ticket):
        with open(os.path.join(self.w, "parked", ticket + "-" + kind + ".json"), "w") as fh:
            json.dump({"ticket_id": ticket, "token": "t",
                       "checkpoint": {"kind": kind}}, fh)

    def test_another_changes_checkpoint_is_NOT_a_divergence(self):
        """The expensive half of the same project-wide leak.

        A structural divergence RE-FORECASTS the tail, so an unscoped read meant a chain
        that predicts no checkpoint got re-forecast because some *other* change happened to
        be waiting on a human — and with parallel items that is the ordinary state, not an
        edge case.
        """
        self._item("plan.md"); self._item("changelog.md")
        self._park("forecast", ticket="some-other-change")
        self.assertEqual(self._div(self._fc(["planner:plan-one", "execute"])), [])

    def test_this_changes_OWN_unforecast_checkpoint_IS_a_divergence(self):
        """Scoping must not have disarmed the real signal: a checkpoint opening for THIS
        change that the chain never predicted is exactly the turn nobody saw coming."""
        self._item("plan.md"); self._item("changelog.md")
        self._park("qa", ticket="item-1")
        div = self._div(self._fc(["planner:plan-one", "execute"]))
        self.assertTrue(any(d["node"] == "checkpoint" for d in div), div)

    def test_a_forecast_chain_walked_as_predicted_does_not_diverge(self):
        self._item("plan.md"); self._item("changelog.md")
        self.assertEqual(self._div(self._fc(["planner:plan-one", "execute"])), [])

    def test_an_unforecast_effect_IS_a_divergence(self):
        """`debug` fired: something failed that the chain never predicted."""
        self._item("plan.md"); self._item("changelog.md"); self._item("debug-report.md")
        div = self._div(self._fc(["planner:plan-one", "execute"]))
        self.assertTrue(any(d["node"] == "debug" for d in div), div)

    def test_the_item_complete_TAIL_is_exempt(self):
        """`commit`/`document` run for every item. Their absence from a chain is the
        horizon talking, not a surprise, and flagging them would make every finished
        item diverge — a signal that fires always is not a signal."""
        self._item("plan.md"); self._item("promoted.json")
        self.assertEqual(self._div(self._fc(["planner:plan-one"])), [])

    def test_a_node_mode_in_the_forecast_covers_its_base(self):
        self._item("plan.md")
        self.assertEqual(self._div(self._fc(["planner:decompose"])), [])


class RealityCli(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.w = os.path.join(self.tmp, ".workflow")
        os.makedirs(os.path.join(self.w, "items", "item-1"))
        self.p = os.path.join(self.w, "forecasts", "item-1.json")
        fc = a_forecast()
        fc["events"] = [{"n": 1, "node": "planner:plan-one", "what": "plan"},
                        {"n": 2, "node": "execute", "what": "build"}]
        fc["horizon"] = {"beyond": 2, "note": "unforeseeable past here"}
        _write(self.p, fc)

    def _run(self, *args):
        return subprocess.run([sys.executable, SCRIPT, "reality", self.p,
                               "--workflow-dir", self.w, *args],
                              capture_output=True, text=True)

    def test_reality_emits_json_and_exits_zero(self):
        r = self._run("--json")
        self.assertEqual(r.returncode, 0, r.stderr)
        out = json.loads(r.stdout)
        self.assertEqual([e["state"] for e in out["events"]], ["pending", "pending"])

    def test_check_exits_one_on_a_divergence(self):
        """The scheduler boundary gates on this: a non-zero exit is what tells it to
        re-forecast the tail rather than walk on."""
        open(os.path.join(self.w, "items", "item-1", "debug-report.md"), "w").close()
        r = self._run("--check")
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("debug", r.stderr)

    def test_check_exits_zero_when_the_chain_holds(self):
        self.assertEqual(self._run("--check").returncode, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)

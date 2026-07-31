#!/usr/bin/env python3
"""Fixture tests for the drain's bookkeeping (stdlib unittest, zero-dep).

Every case here is a rule that used to live only in prose. The headline one —
`test_the_consumed_set_is_pruned_to_the_watermark` — is a defect measured against real
sessions, not an invented edge: two of three runs driven against the brief produced an
unbounded consumed-set, because the brief named the watermark once in passing and never
mentioned the prune. This file is what makes that rule fail loudly instead of silently.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bus  # noqa: E402
import drain  # noqa: E402
import rebind  # noqa: E402

ID_A = "20260716T100000.000001Z-aaaaaaaa-9001"
ID_B = "20260716T100500.000001Z-bbbbbbbb-9002"
ID_C = "20260716T101000.000001Z-cccccccc-9003"
ID_D = "20260716T101500.000001Z-dddddddd-9004"


class Drain(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.root, True)
        self.w = os.path.join(self.root, ".workflow")
        for sub in ("inbox", "parked", "outbox"):
            os.makedirs(os.path.join(self.w, sub))
        self.paths = bus.Paths(self.w)
        self.prose = "# Handoff — resume anchor\n\n- current_item: item-1\n\n## parked[]\n- none\n"
        self.write_handoff(self.prose)

    def write_handoff(self, text):
        with open(self.paths.handoff, "w") as fh:
            fh.write(text)

    def msg(self, mid, kind="intake", **body):
        body.setdefault("ask", "do a thing")
        body["kind"] = kind
        body["message_id"] = mid
        with open(os.path.join(self.w, "inbox", mid + ".json"), "w") as fh:
            json.dump(body, fh)
        return mid

    def block(self):
        return bus.read_handoff_block(self.paths.handoff)

    def record(self, applied=(), dead=()):
        return drain.main(["--workflow-dir", self.w, "record"]
                          + (["--applied"] + list(applied) if applied else [])
                          + (["--dead-letter"] + list(dead) if dead else []))

    # -- listing + ordering --
    def test_pending_is_ordered_by_kind_then_age(self):
        """Control first so a reprioritize is honored by the pick this boundary is
        about to make — even though it arrived LAST."""
        self.msg(ID_A, "release", action_ids=["act-1"])
        self.msg(ID_B, "intake")
        self.msg(ID_C, "verdict", token="t", verdict={"outcome": "approve"})
        self.msg(ID_D, "control", op="pause")
        out = drain.cmd_list(self.paths, None)
        self.assertEqual([e["kind"] for e in out["pending"]],
                         ["control", "verdict", "intake", "release"])

    def test_two_of_a_kind_apply_oldest_first(self):
        self.msg(ID_C, "verdict", token="c", verdict={"outcome": "approve"})
        self.msg(ID_B, "verdict", token="b", verdict={"outcome": "reject"})
        out = drain.cmd_list(self.paths, None)
        self.assertEqual([e["message_id"] for e in out["pending"]], [ID_B, ID_C])

    def test_consumed_ids_are_skipped(self):
        self.msg(ID_A)
        self.msg(ID_B)
        self.record(applied=[ID_A])
        out = drain.cmd_list(self.paths, None)
        self.assertEqual([e["message_id"] for e in out["pending"]], [ID_B])

    def test_a_cold_start_re_read_is_a_no_op(self):
        """The whole point: a restart re-lists the inbox and must promote nothing
        twice. The bus never deleted the message, so only the set stops it."""
        self.msg(ID_A)
        self.record(applied=[ID_A])
        self.assertEqual(drain.cmd_list(self.paths, None)["pending"], [])
        self.assertTrue(os.path.exists(os.path.join(self.w, "inbox", ID_A + ".json")),
                        "the consumer deleted an inbox file — that partition is the bus's")

    def test_an_unreadable_message_is_surfaced_not_skipped(self):
        with open(os.path.join(self.w, "inbox", ID_A + ".json"), "w") as fh:
            fh.write("{torn")
        out = drain.cmd_list(self.paths, None)
        self.assertEqual(out["pending"][0]["kind"], "unreadable")

    def test_an_in_flight_tmp_file_is_not_a_message(self):
        with open(os.path.join(self.w, "inbox", ".%s.json.1.tmp" % ID_A), "w") as fh:
            fh.write("{half")
        self.assertEqual(drain.cmd_list(self.paths, None)["pending"], [])

    # -- the watermark --
    def test_watermark_advances_over_a_contiguous_consumed_prefix(self):
        for mid in (ID_A, ID_B, ID_C):
            self.msg(mid)
        self.record(applied=[ID_A, ID_B, ID_C])
        self.assertEqual(self.block()["consumed_through"], ID_C)

    def test_watermark_stops_at_a_gap(self):
        """A watermark, not a cursor. If it jumped the gap the bus would collect ID_B
        — a message nobody applied — and the human would never know."""
        for mid in (ID_A, ID_B, ID_C):
            self.msg(mid)
        self.record(applied=[ID_A, ID_C])
        self.assertEqual(self.block()["consumed_through"], ID_A)
        self.assertIn(ID_C, self.block()["consumed"],
                      "an id above the gap must stay in the set to stop a re-apply")

    def test_watermark_advances_when_ids_are_recorded_ONE_AT_A_TIME(self):
        """The brief tells the orchestrator to record each id the moment its apply
        succeeds — smallest crash window — so this, not the batch, is the real path.

        It is also where the watermark froze. Pruning drops an id from the set as soon
        as the mark passes it, so on the NEXT pass that id is no longer "in consumed";
        a walk that reads the set alone stops dead on it and the mark never moves
        again. The inbox then grows forever, which is the exact bound the watermark
        exists to provide. Every batch-at-once test passed while this was broken — it
        took driving a real session to find it.
        """
        for mid in (ID_A, ID_B, ID_C):
            self.msg(mid)
        for mid in (ID_A, ID_B, ID_C):
            self.record(applied=[mid])
        blk = self.block()
        self.assertEqual(blk["consumed_through"], ID_C,
                         "the watermark froze: incremental recording stalled it")
        self.assertEqual(blk["consumed"], [])

    def test_watermark_advances_when_applies_arrive_out_of_order(self):
        """A verdict applies before an intake that arrived earlier, so the ids are
        recorded out of order. The mark must still end up at the top."""
        for mid in (ID_A, ID_B, ID_C):
            self.msg(mid)
        for mid in (ID_C, ID_A, ID_B):
            self.record(applied=[mid])
        self.assertEqual(self.block()["consumed_through"], ID_C)

    def test_watermark_never_regresses(self):
        self.msg(ID_A)
        self.record(applied=[ID_A])
        os.unlink(os.path.join(self.w, "inbox", ID_A + ".json"))  # the bus collected it
        self.record()
        self.assertEqual(self.block()["consumed_through"], ID_A)

    def test_empty_inbox_keeps_the_watermark(self):
        self.msg(ID_A)
        self.record(applied=[ID_A])
        os.unlink(os.path.join(self.w, "inbox", ID_A + ".json"))
        self.record()
        self.assertEqual(self.block()["consumed_through"], ID_A)

    # -- THE MEASURED DEFECT --
    def test_the_consumed_set_is_pruned_to_the_watermark(self):
        """MEASURED: 2 of 3 real sessions driven against the brief kept every id here,
        producing an unbounded consumed-set on a file every cold start reads whole.
        The brief states the watermark once, in passing, and never states this prune.
        Ids at or below the mark are implied BY the mark, so keeping them is pure growth.
        """
        for mid in (ID_A, ID_B, ID_C):
            self.msg(mid)
        self.record(applied=[ID_A, ID_B, ID_C])
        blk = self.block()
        self.assertEqual(blk["consumed_through"], ID_C)
        self.assertEqual(blk["consumed"], [],
                         "the consumed-set grew without bound: every id here is already "
                         "implied by consumed_through")

    def test_pruning_never_loses_an_id_above_the_watermark(self):
        for mid in (ID_A, ID_B, ID_C):
            self.msg(mid)
        self.record(applied=[ID_A, ID_C])
        self.assertEqual(self.block()["consumed"], [ID_C])

    def test_a_pruned_id_is_still_not_re_applied(self):
        """The set forgets it, so the WATERMARK has to remember it — otherwise pruning
        would reopen the double-promotion it exists alongside."""
        self.msg(ID_A)
        self.record(applied=[ID_A])
        self.assertEqual(self.block()["consumed"], [])
        self.assertEqual(drain.cmd_list(self.paths, None)["pending"], [],
                         "a pruned-but-uncollected message came back as pending")

    # -- dead letters --
    def test_dead_letter_is_recorded_consumed_and_surfaced(self):
        self.msg(ID_A, "verdict", token="gone", verdict={"outcome": "approve"})
        self.record(dead=["%s=unknown token" % ID_A])
        blk = self.block()
        self.assertEqual(blk["dead_letters"][0]["message_id"], ID_A)
        self.assertEqual(blk["dead_letters"][0]["reason"], "unknown token")
        self.assertEqual(drain.cmd_list(self.paths, None)["pending"], [],
                         "a dead-lettered message must not be applied again")

    def test_dead_letters_survive_the_watermark_but_stay_bounded(self):
        """The one message a human most needs told about must not be collected the
        moment the mark passes it — but handoff.md is read whole by every cold start,
        so it is capped instead."""
        self.msg(ID_A, "verdict", token="gone", verdict={"outcome": "approve"})
        self.record(dead=["%s=unknown token" % ID_A])
        self.assertEqual(self.block()["consumed_through"], ID_A)
        self.assertEqual(len(self.block()["dead_letters"]), 1, "surfaced notice was pruned")
        for i in range(drain.MAX_DEAD_LETTERS + 5):
            mid = "20260716T20%04d.000001Z-eeeeeeee-1" % i
            self.msg(mid, "verdict", token="x", verdict={"outcome": "approve"})
            self.record(dead=["%s=unknown token" % mid])
        self.assertEqual(len(self.block()["dead_letters"]), drain.MAX_DEAD_LETTERS)

    def test_a_dead_letter_reason_cannot_forge_the_blocks_END_MARKER(self):
        """The highest-stakes instance of the forged-marker bug, and the reason it is
        not theoretical: a dead-letter `reason` is written when a verdict quotes an
        unknown/closed token, and that token comes from the CONSOLE. Echo it into the
        reason and the next publish matches begin → the forged end, so the block it
        writes back is the degraded `empty_block()` — `consumed_through` drops to None
        and every already-consumed inbox message becomes pending again, which is the
        re-promoted intake / re-fired control op the consumed-set exists to prevent.
        Driven on a real clone: one publish took a live watermark to null.
        """
        self.msg(ID_A, "verdict", token="gone", verdict={"outcome": "approve"})
        hostile = "unknown token <!-- drain:end --> INJECTED"
        self.record(dead=["%s=%s" % (ID_A, hostile)])
        self.record()  # the second publish is the one that used to corrupt
        text = open(self.paths.handoff).read()
        self.assertEqual(text.count(bus.HANDOFF_END), 1, "a second end marker was forged")
        blk = self.block()
        self.assertEqual(blk["consumed_through"], ID_A, "the watermark was destroyed")
        self.assertEqual(blk["dead_letters"][0]["reason"], hostile)

    # -- the block on handoff.md --
    def test_prose_is_untouched(self):
        """Two authors, one file. It only works because neither rewrites the other."""
        self.msg(ID_A)
        self.record(applied=[ID_A])
        text = open(self.paths.handoff).read()
        self.assertIn("- current_item: item-1", text)
        self.assertIn("## parked[]", text)

    def test_the_block_is_rewritten_in_place_not_appended_each_time(self):
        for mid in (ID_A, ID_B):
            self.msg(mid)
            self.record(applied=[mid])
        text = open(self.paths.handoff).read()
        self.assertEqual(text.count(bus.HANDOFF_BEGIN), 1,
                         "handoff.md grew a second machine block")

    def test_a_dropped_block_is_rebuilt(self):
        """A session that rewrites handoff.md wholesale can drop the block. It cannot
        be recovered — which is exactly why each kind carries an effect anchor too."""
        self.msg(ID_A)
        self.record(applied=[ID_A])
        self.write_handoff(self.prose)
        self.record(applied=[ID_B])
        self.assertIn(ID_B, str(self.block()["consumed"]) + str(self.block()["consumed_through"]))

    def test_missing_handoff_is_created(self):
        os.unlink(self.paths.handoff)
        self.msg(ID_A)
        self.record(applied=[ID_A])
        self.assertEqual(self.block()["consumed_through"], ID_A)

    def test_block_round_trips(self):
        blk = {"consumed": [ID_A], "consumed_through": ID_B,
               "dead_letters": [{"message_id": ID_C, "reason": "x", "at": "now"}]}
        self.write_handoff("prose\n\n" + bus.render_handoff_block(blk) + "\ntail\n")
        self.assertEqual(self.block(), blk)

    def test_a_garbage_block_degrades_to_empty(self):
        self.write_handoff(bus.HANDOFF_BEGIN + "\n```json\n{oops\n```\n" + bus.HANDOFF_END)
        self.assertEqual(self.block(), bus.empty_block())

    def test_record_refuses_an_id_the_bus_never_issued(self):
        with self.assertRaises(SystemExit):
            self.record(applied=["nonsense"])

    # -- the secret carve-out --
    def test_secret_moves_the_value_out_and_unlinks_without_printing_it(self):
        self.msg(ID_A, "verdict", token="item-1:setup:x",
                 verdict={"outcome": "approve",
                          "returns": {"A_KEY": {
                              "sensitive": True,
                              "value": "canary-value-must-never-be-printed"}}})
        out = drain.cmd_secret(self.paths, _Args(id=ID_A))
        self.assertFalse(os.path.exists(os.path.join(self.w, "inbox", ID_A + ".json")),
                         "the credential is still sitting on the durable inbox")
        stored = json.load(open(out["stored"]))
        self.assertEqual(stored["returns"]["A_KEY"]["value"],
                         "canary-value-must-never-be-printed")
        self.assertNotIn("canary-value-must-never-be-printed", json.dumps(out),
                         "the secret was echoed back to the caller's context")
        self.assertEqual(self.block()["consumed_through"], ID_A)

    def test_secret_store_entry_is_0600(self):
        self.msg(ID_A, "verdict", token="t",
                 verdict={"outcome": "approve",
                          "returns": {"A_KEY": {"sensitive": True, "value": "k"}}})
        out = drain.cmd_secret(self.paths, _Args(id=ID_A))
        self.assertIsNone(bus.verify_mode(out["stored"], 0o600), out.get("warning"))

    def test_list_redacts_a_sensitive_value(self):
        self.msg(ID_A, "verdict", token="t",
                 verdict={"outcome": "approve",
                          "returns": {"A_KEY": {
                              "sensitive": True,
                              "value": "canary-value-must-never-be-printed"}}})
        out = drain.cmd_list(self.paths, None)
        self.assertTrue(out["pending"][0]["sensitive"])
        self.assertNotIn("canary-value-must-never-be-printed", json.dumps(out),
                         "the drain printed a credential into the caller's context")

    def test_the_store_it_writes_is_readable_by_the_declared_secret_diff(self):
        """THE regression, driven across the whole chain rather than at one end.

        Every link here passed its own unit test while the chain was broken: the drain
        stored `returns` verbatim, the diff read credential names out of it, and the two
        never agreed on what `returns` was — so a machine that lost nothing reported
        every declared secret lost, forever. This asserts the two ends against each
        other, which is the only place that failure was ever visible.
        """
        self.msg(ID_A, "verdict", token="item-1:setup:x", verdict={"tasks": [
            {"id": "runpod-credentials", "outcome": "approve", "returns": {
                "IVRIT_RUNPOD_API_KEY": {"value": "sk_live_x", "sensitive": True}}}]})
        out = drain.cmd_secret(self.paths, _Args(id=ID_A))
        found, unreadable = rebind.present_secrets(os.path.dirname(out["stored"]))
        self.assertIn("IVRIT_RUNPOD_API_KEY", found)
        self.assertEqual(unreadable, 0)
        # The task id is the one thing that must NOT be read as a credential name.
        self.assertNotIn("runpod-credentials", found)

    def test_a_non_sensitive_message_is_not_shreddable(self):
        self.msg(ID_A, "verdict", token="t", verdict={"outcome": "approve"})
        with self.assertRaises(SystemExit):
            drain.cmd_secret(self.paths, _Args(id=ID_A))
        self.assertTrue(os.path.exists(os.path.join(self.w, "inbox", ID_A + ".json")),
                        "the carve-out deleted a message that carried no secret")

    # -- it runs as a real program --
    def test_cli_round_trip(self):
        self.msg(ID_A, "control", op="pause")
        env = dict(os.environ)
        script = os.path.join(os.path.dirname(os.path.abspath(drain.__file__)), "drain.py")
        out = subprocess.run([sys.executable, script, "--workflow-dir", self.w, "list"],
                             capture_output=True, text=True, env=env)
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual(json.loads(out.stdout)["pending"][0]["kind"], "control")
        rec = subprocess.run([sys.executable, script, "--workflow-dir", self.w,
                              "record", "--applied", ID_A],
                             capture_output=True, text=True, env=env)
        self.assertEqual(rec.returncode, 0, rec.stderr)
        self.assertEqual(json.loads(rec.stdout)["consumed_through"], ID_A)


class _Args:
    def __init__(self, **kw):
        self.__dict__.update(kw)


if __name__ == "__main__":
    unittest.main()

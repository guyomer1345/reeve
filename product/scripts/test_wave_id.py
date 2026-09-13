"""Tests for `wave_build.py mint` — the id a wave is known by.

The wave-build slot shipped with only half of it live: exclusion (one authoritative build at a
time) was mechanical from day one, while dedup (do not re-gate a tree this wave already passed)
could never fire, because nothing in the package wrote a non-null `wave`. Minting is what wakes
that half up, so what these pin is the property the memo depends on — that the id is DERIVED
from the batch and the commit, not allocated by anything that could hand out two.
"""
import wave_build as wb


def test_same_batch_same_tree_is_the_same_wave(monkeypatch):
    """Order-independent, because a batch is a set. If ids arrived in a different order and
    produced a different wave, the memo would miss and the build would run twice."""
    monkeypatch.setattr(wb, "git", lambda *a: "abc1234\n")
    assert wb.mint_wave_id(["b", "a"]) == wb.mint_wave_id(["a", "b"])
    assert wb.mint_wave_id(["a"]).startswith("w-")


def test_a_different_batch_is_a_different_wave(monkeypatch):
    monkeypatch.setattr(wb, "git", lambda *a: "abc1234\n")
    assert wb.mint_wave_id(["a", "b"]) != wb.mint_wave_id(["a", "c"])


def test_the_same_batch_at_a_new_commit_is_a_new_wave(monkeypatch):
    """Two waves collide only if they dispatch the same items at the same commit — which is one
    wave. Move HEAD and the memo must not carry over."""
    monkeypatch.setattr(wb, "git", lambda *a: "aaaaaaa\n")
    first = wb.mint_wave_id(["a", "b"])
    monkeypatch.setattr(wb, "git", lambda *a: "bbbbbbb\n")
    assert wb.mint_wave_id(["a", "b"]) != first


def test_a_git_that_cannot_answer_still_mints(monkeypatch):
    """Same floor as the rest of this file: never raise. The alternative to a degraded id is no
    id at all, which puts the dedup half straight back to sleep."""
    monkeypatch.setattr(wb, "git", lambda *a: None)
    assert wb.mint_wave_id(["a"]).startswith("w-")


def test_the_cli_prints_it(capsys, monkeypatch):
    monkeypatch.setattr(wb, "git", lambda *a: "abc1234\n")
    assert wb.main(["mint", "a", "b"]) == 0
    assert capsys.readouterr().out.strip() == wb.mint_wave_id(["a", "b"])

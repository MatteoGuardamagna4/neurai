"""Offline tests for the §5.4 contradiction judge: the transport is monkeypatched, no server is needed."""
import json

import pytest

from neurotutorsim import judge


def test_parse_reads_the_three_verdicts_and_their_reasons():
    r = judge.parse("CONTRADICTION: no - matches the reference\n"
                    "UNSUPPORTED: yes - asserts a growth rate the inputs do not give\n"
                    "CAUSAL: no - no causal claim")
    assert r["parsed"] and r["flags"] == {"contradiction": False, "unsupported": True, "causal": False}
    assert r["reasons"]["unsupported"].startswith("asserts a growth rate")


def test_an_empty_reason_does_not_swallow_the_next_verdict():
    """The separator must not match a newline, or `UNSUPPORTED: no -` eats the CAUSAL line and hides a flag."""
    r = judge.parse("CONTRADICTION: no - fine\nUNSUPPORTED: no -\nCAUSAL: yes - claims discounting causes value")
    assert r["flags"]["causal"] is True, "the causal flag must survive an empty reason above it"
    assert r["reasons"]["causal"] == "claims discounting causes value"
    assert r["reasons"]["unsupported"] == ""
    assert r["parsed"]


def test_a_bare_verdict_without_a_reason_still_parses():
    r = judge.parse("CONTRADICTION: no\nUNSUPPORTED: no\nCAUSAL: no")
    assert r["parsed"] and not any(r["flags"].values())


def test_an_unanswered_check_is_none_not_no():
    """An unparsed reply must reach the review queue, never pass by default."""
    r = judge.parse("CONTRADICTION: no\nI am not sure about the rest.")
    assert r["flags"]["contradiction"] is False
    assert r["flags"]["unsupported"] is None and r["flags"]["causal"] is None
    assert not r["parsed"]
    assert judge.flagged([{"parsed": False, "contradiction": False, "unsupported": None, "causal": None}])


def test_flagged_and_summarize_count_what_goes_to_manual_review():
    rows = [
        {"stimulus_id": "a", "condition": "traditional", "parsed": True, "contradiction": False, "unsupported": False, "causal": False},
        {"stimulus_id": "b", "condition": "traditional", "parsed": True, "contradiction": True, "unsupported": False, "causal": False},
        {"stimulus_id": "c", "condition": "ai_scaffolding", "parsed": False, "contradiction": None, "unsupported": None, "causal": None},
    ]
    assert sorted(r["stimulus_id"] for r in judge.flagged(rows)) == ["b", "c"]
    s = judge.summarize(rows)
    assert s["n_texts"] == 3 and s["n_review_queue"] == 2 and s["n_unparsed"] == 1 and s["n_contradiction"] == 1
    assert s["by_condition"]["traditional"] == {"n": 2, "flagged": 1}


def test_prompt_carries_the_reference_and_the_whole_text_but_asks_for_no_arithmetic(units, stimuli):
    unit = units["npv_001"]
    stim = stimuli[("npv_001", "ai_scaffolding")]
    p = judge.prompt_for(unit, stim)
    assert unit.problem.render(unit.problem.answer) in p, "the judge needs the authoritative answer"
    assert unit.misconception.split()[0] in p, "the documented misconception must be excusable, not flagged"
    assert stim.sections["Explanation"].split()[0] in p and "Hints" not in p.split("Authoritative")[0][:40]
    assert "do not re-derive" in judge.SYSTEM.lower(), "corpus.py owns the arithmetic; the judge must not duplicate it"


def test_judge_one_builds_a_row_from_a_canned_reply(monkeypatch, units, stimuli):
    class FakeTutor:
        def chat(self, system, user):
            assert "reviewer" in system
            return ("CONTRADICTION: no\nUNSUPPORTED: no\nCAUSAL: yes - overstated",
                    {"model": "judge-x", "prompt_sha256": "abc", "seconds": 1.0})

    row = judge.judge_one(FakeTutor(), units["npv_001"], stimuli[("npv_001", "traditional")])
    assert row["stimulus_id"] == "npv_001_traditional" and row["condition"] == "traditional"
    assert row["causal"] is True and row["causal_reason"] == "overstated" and row["parsed"]
    assert row["model"] == "judge-x" and row["variant"] == "primary"


def test_read_cache_keys_on_stimulus_and_prompt(tmp_path):
    p = tmp_path / "verdicts.jsonl"
    p.write_text(json.dumps({"stimulus_id": "a", "prompt_sha256": "h1", "causal": False}) + "\n"
                 + json.dumps({"stimulus_id": "a", "prompt_sha256": "h2", "causal": True}) + "\n", encoding="utf-8")
    cache = judge.read_cache(p)
    assert len(cache) == 2, "a changed prompt must not reuse the old verdict"
    assert cache[("a", "h2")]["causal"] is True
    assert judge.read_cache(tmp_path / "missing.jsonl") == {}


def test_main_refuses_the_fake_tutor(tmp_path, capsys):
    import shutil

    from tests.conftest import ROOT

    for folder in ("config", "data/units", "stimuli"):
        shutil.copytree(ROOT / folder, tmp_path / folder)
    cfg = tmp_path / "config" / "default.yaml"
    cfg.write_text(cfg.read_text(encoding="utf-8").replace("provider: openai", "provider: fake"), encoding="utf-8")
    assert judge.main(["--config", str(cfg)]) == 2
    assert "needs a real server" in capsys.readouterr().err

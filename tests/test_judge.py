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


def test_judge_one_makes_both_calls_and_reads_each(units, stimuli):
    """Call 1 is the validated answer comparison, call 2 the two unvalidated claim checks."""
    seen = []

    class FakeTutor:
        cfg = {"model": "judge-x"}

        def chat(self, system, user):
            seen.append(system)
            if "reference answer" in system:
                return ("FINAL_ANSWER_IN_TEXT: 2,400 units" + chr(10) + "MATCHES_REFERENCE: no",
                        {"model": "judge-x", "seconds": 1.0})
            return "UNSUPPORTED: no" + chr(10) + "CAUSAL: yes - overstated", {"model": "judge-x", "seconds": 1.0}

    row = judge.judge_one(FakeTutor(), units["npv_001"], stimuli[("npv_001", "traditional")])
    assert len(seen) == 2
    assert row["contradiction"] is True and row["answer_in_text"] == "2,400 units"
    assert "2,400 units" in row["contradiction_reason"] and "EUR 10,000" in row["contradiction_reason"]
    assert row["causal"] is True and row["unsupported"] is False and row["parsed"]


def test_the_contradiction_check_is_extract_then_compare_not_an_abstract_question(units, stimuli):
    """Measured: a 3B judge answers `no` to the abstract §5.4 questions and missed all 30 incorrect texts; asked to
    read off the answer and compare it, the same model got 8 of 8. The prompt must keep that shape."""
    p = judge.answer_prompt(units["be_001"], stimuli[("be_001", "traditional")])
    assert "FINAL_ANSWER_IN_TEXT" in p and "MATCHES_REFERENCE" in p
    assert units["be_001"].problem.render(units["be_001"].problem.answer) in p
    assert "CONTRADICTION" not in p, "the contradiction verdict is derived from the comparison, not asked directly"
    c = judge.claims_prompt(units["be_001"], stimuli[("be_001", "traditional")])
    assert "UNSUPPORTED" in c and "CAUSAL" in c and "FINAL_ANSWER" not in c


def test_prompt_hash_covers_both_calls(units, stimuli):
    a = judge.prompt_hash(units["be_001"], stimuli[("be_001", "traditional")])
    b = judge.prompt_hash(units["be_001"], stimuli[("be_001", "ai_scaffolding")])
    assert a != b and len(a) == 64


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


def test_a_hung_text_is_skipped_and_queued_not_fatal(tmp_path, monkeypatch, capsys):
    """One unreachable text must not cost the other 89, and must never be recorded as having passed."""
    import shutil

    from neurotutorsim import tutor as T
    from tests.conftest import ROOT

    for folder in ("config", "data/units", "stimuli"):
        shutil.copytree(ROOT / folder, tmp_path / folder)
    calls = {"n": 0}

    def fake_chat(self, system, user):
        calls["n"] += 1
        if calls["n"] == 3:
            raise T.TutorError("read timed out")
        if "reference answer" in system:  # call 1 of 2: the answer comparison
            return "FINAL_ANSWER_IN_TEXT: 6,000 units\nMATCHES_REFERENCE: yes", {"model": "m", "seconds": 1.0}
        return "UNSUPPORTED: no\nCAUSAL: no", {"model": "m", "seconds": 1.0}

    monkeypatch.setattr(T.Tutor, "chat", fake_chat)
    assert judge.main(["--config", str(tmp_path / "config" / "default.yaml"), "--limit", "4"]) == 0
    assert calls["n"] >= 6, "the pass continued past the failing text"
    out = json.loads((tmp_path / "data" / "processed" / "judge" / "judge_summary.json").read_text(encoding="utf-8"))
    assert out["n_texts"] == 4 and out["n_errors"] == 1
    queue = json.loads((tmp_path / "data" / "processed" / "judge" / "review_queue.json").read_text(encoding="utf-8"))
    assert len(queue) == 1 and queue[0]["parsed"] is False and "timed out" in queue[0]["error"]
    assert all(queue[0][c] is None for c in judge.CHECKS), "a text that could not be judged has no verdicts"


def test_the_answer_check_is_skipped_where_the_condition_withholds_the_answer(units, stimuli):
    """ai_scaffolding may not state the final answer (corpus.ANSWER_ALLOWED_IN), so there is nothing to compare.
    Measured: asked anyway, all six scaffolding texts came back false contradictions against zero elsewhere."""
    from neurotutorsim.corpus import ANSWER_ALLOWED_IN

    assert not ANSWER_ALLOWED_IN["ai_scaffolding"]
    assert judge.answer_check_applies(stimuli[("be_001", "traditional")])
    assert judge.answer_check_applies(stimuli[("be_001", "ai_substitution")])
    assert not judge.answer_check_applies(stimuli[("be_001", "ai_scaffolding")])

    calls = []

    class FakeTutor:
        cfg = {"model": "m"}

        def chat(self, system, user):
            calls.append(system)
            return "UNSUPPORTED: no" + chr(10) + "CAUSAL: no", {"model": "m", "seconds": 1.0}

    row = judge.judge_one(FakeTutor(), units["be_001"], stimuli[("be_001", "ai_scaffolding")])
    assert len(calls) == 1, "no answer call is made where the check cannot apply"
    assert row["contradiction"] is None and row["contradiction_applicable"] is False
    assert row["parsed"] is True, "not applicable is not the same as unanswered"
    assert not judge.flagged([row]), "a not-applicable check must not queue the text"
    # and the hash differs from the two-call form, so a row cached under the old logic is not reused
    assert judge.prompt_hash(units["be_001"], stimuli[("be_001", "ai_scaffolding")]) \
        != judge.prompt_hash(units["be_001"], stimuli[("be_001", "traditional")])

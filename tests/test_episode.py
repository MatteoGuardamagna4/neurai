import copy
import shutil
from dataclasses import replace

import numpy as np
import pytest

from neurotutorsim import corpus, simulate
from neurotutorsim.engines import Decision, explanation_of
from neurotutorsim.episode import FREE, run_episode
from neurotutorsim.tutor import FakeTutor, Tutor, TutorError, unit_facts
from tests.conftest import ROOT
from tests.test_learners import make_learner


class ScriptedEngine:
    """Answers with the scripted option kinds, in order ('help' picks the help option)."""
    name = "scripted"

    def __init__(self, kinds):
        self.kinds = list(kinds)

    def choose(self, trial, learner, rng):
        kind = self.kinds.pop(0)
        option = next(o for o in trial.options if o.kind == kind)
        return Decision(option.key, option.kind, option.value, 0.5, {}, explanation=explanation_of(option),
                        meta={"kind": "choice"})

    def confidence(self, trial, decision, learner, rng):
        decision.rating = 3
        return 0.5


def episode(cfg, units, stimuli, condition, kinds, tutor=None, learner=None):
    unit = units["be_001"]
    by_condition = {c: stimuli[(unit.unit_id, c)] for c in corpus.CONDITIONS}
    return run_episode(learner or make_learner(), unit, by_condition, condition, 0,
                       ScriptedEngine(kinds), tutor or FakeTutor(), cfg, np.random.default_rng(1))


def test_traditional_ladder_with_help_request_and_reveal(cfg, units, stimuli):
    rec = episode(cfg, units, stimuli, "traditional", ["misconception", "help", "distractor", "misconception", "correct"])
    assert [t["stage"] for t in rec.turns] == ["first", "supported", "supported", "supported", "transfer"]
    assert (rec.first_correct, rec.answer_provided, rec.hint_depth, rec.help_requests, rec.attempts) == (0, 1, 3, 1, 3)
    assert rec.transfer_correct == 1 and rec.resolved == 0 and rec.resolution == 0
    assert rec.proxies["explanation"] == 0.0 and rec.proxies["offloading"] == 1.0 and rec.proxies["support_used"] == 1.0
    assert rec.learner_after["n_episodes"] == 1 and rec.learner_after["n_help"] == 1
    history = rec.learner_after["history"][0]
    assert "Lesson:" not in history and "Hint 1 was shown." in history and "The solution was shown to you." in history
    # brief §7.3: prior answers, errors, hint usage and confidence are all in the observable transcript
    assert history.count("You press <<3>>.") == 2 and "How confident are you" in history and "That was incorrect." in history
    assert rec.turns[0]["explanation"] == "misconception: fixed_costs / price"
    assert rec.turns[1]["requested_support"] == 1 and rec.turns[1]["explanation"] == "requested support"
    assert rec.learner_after["rating_n"] == 2 and "average confidence 3.0 of 5" in make_learner(
        n_episodes=1, rating_sum=6, rating_n=2).record_line()


def test_traditional_resolved_after_first_hint(cfg, units, stimuli):
    rec = episode(cfg, units, stimuli, "traditional", ["misconception", "correct", "distractor"])
    assert (rec.hint_depth, rec.resolved, rec.answer_provided, rec.attempts, rec.resolution) == (1, 1, 0, 2, 1)
    assert rec.proxies["correct_after_error"] == 1.0 and rec.transfer_correct == 0


def test_scaffolding_three_tutor_turns_then_reveal(cfg, units, stimuli):
    tutor = FakeTutor()
    rec = episode(cfg, units, stimuli, "ai_scaffolding", ["misconception", "distractor", "misconception", "distractor", "correct"], tutor)
    assert tutor.calls == 3 and len(rec.tutor_turns) == 3 and rec.answer_provided == 1 and rec.hint_depth == 3
    assert not any(t["leaked"] for t in rec.tutor_turns)
    layouts = [t["layout"] for t in rec.turns]
    assert "help" in layouts[1] and "help" in layouts[2] and "help" not in layouts[3]  # no help option on the last rung
    assert rec.proxies["adaptation"] == cfg["support"]["adaptation"]["ai_scaffolding"]


def test_substitution_single_call_and_one_reanswer(cfg, units, stimuli):
    tutor = FakeTutor()
    rec = episode(cfg, units, stimuli, "ai_substitution", ["misconception", "correct", "distractor"], tutor)
    assert tutor.calls == 1 and [t["stage"] for t in rec.turns] == ["first", "supported", "transfer"]
    assert (rec.answer_provided, rec.attempts, rec.resolved, rec.resolution) == (1, 1, 1, 0)
    assert rec.proxies["support_used"] == 1.0 and rec.proxies["explanation"] == 0.0


def test_free_choice_arm_reads_the_question_then_picks_a_protocol(cfg, units, stimuli):
    tutor = FakeTutor()
    rec = episode(cfg, units, stimuli, FREE, ["ai_substitution", "misconception", "correct", "correct"], tutor)
    assert rec.condition == FREE and rec.protocol == "ai_substitution" and tutor.calls == 1
    assert [t["stage"] for t in rec.turns] == ["approach", "first", "supported", "transfer"]
    a = rec.turns[0]
    assert a["kind"] == "ai_substitution" and a["correct"] is None and a["requested_support"] == 0
    assert a["explanation"] == "approach: ai_substitution" and a["layout"].count(":") == 3
    lines = rec.learner_after["history"][0]
    assert lines.index("Question:") < lines.index("How do you want to approach"), "the question is read before the choice"
    assert "Ask the AI for the complete solution" in lines and "The tutor sent you a message." in lines
    assert "That took you about" in lines and "Lesson:" not in lines
    assert rec.proxies["adaptation"] == cfg["support"]["adaptation"]["ai_substitution"]
    assert rec.learner_after["choice_record"] == {"ai_substitution": [1, 1]}
    record = make_learner(n_episodes=1, choice_record={"ai_substitution": [3, 1]}).record_line()
    assert "Looking back at what worked: after the AI's complete solution" in record
    assert "correctly 1 of 3 times (33%)" in record, "payoff stated first and as a rate"
    # the assigned arms keep the lesson before the question and remember no choice
    rec = episode(cfg, units, stimuli, "traditional", ["correct", "correct"])
    assert rec.protocol == "traditional" and rec.learner_after["choice_record"] == {}
    h = rec.learner_after["history"][0]
    assert "How do you want to approach" not in h and h.index("Question:") < h.index("Options:")


def test_free_choice_lesson_is_the_chosen_conditions_stimulus(cfg, units, stimuli):
    seen = {}
    for pick in ("traditional", "ai_scaffolding", "ai_substitution"):
        kinds = [pick, "correct", "correct"]
        unit = units["be_001"]
        by_condition = {c: stimuli[(unit.unit_id, c)] for c in corpus.CONDITIONS}
        eng = ScriptedEngine(kinds)
        # capture the lesson the engine saw on the first answer trial
        shown = {}
        orig = eng.choose
        def choose(trial, learner, rng, orig=orig, shown=shown):
            if trial.stage == "first":
                shown["lesson"] = next(l for l in trial.lines if l.startswith("Lesson:"))
            return orig(trial, learner, rng)
        eng.choose = choose
        run_episode(make_learner(), unit, by_condition, FREE, 0, eng, FakeTutor(), cfg, np.random.default_rng(1))
        seen[pick] = shown["lesson"]
    for pick, lesson in seen.items():
        assert lesson == "Lesson: " + stimuli[("be_001", pick)].explanation
    assert len(set(seen.values())) == 3


def test_first_correct_skips_intervention(cfg, units, stimuli):
    rec = episode(cfg, units, stimuli, "ai_scaffolding", ["correct", "correct"])
    assert len(rec.turns) == 2 and rec.hint_depth == 0 and rec.attempts == 1 and rec.proxies["retrieval"] == 1.0
    assert rec.learner_after["streak"] == 1 and rec.proxies["adaptation"] == 0.0


def test_immediate_withdrawal_gives_no_help(cfg, units, stimuli):
    c = copy.deepcopy(cfg)
    c["support"]["persistence_policy"] = "immediate_withdrawal"
    rec = episode(c, units, stimuli, "traditional", ["misconception", "correct"], learner=make_learner(streak=5))
    assert rec.help_cap == 0 and [t["stage"] for t in rec.turns] == ["first", "transfer"]
    assert rec.proxies["support_faded"] == 1.0 and rec.answer_provided == 0


def test_scaffolding_leak_is_regenerated_then_replaced_by_the_prewritten_hint(cfg, units, monkeypatch, tmp_path):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    tutor = Tutor(cfg["tutor"], ROOT / "config" / "prompts", tmp_path / "log.jsonl")
    monkeypatch.setattr(tutor, "chat", lambda system, user: ("So you need 6,000 units. What is the margin?", {}))
    turn = tutor.scaffold(units["be_001"], ["Attempt 1: the learner answered 2,400 units (incorrect)."], 2)
    assert turn.fallback and turn.leaked and turn.text == units["be_001"].hints[1]
    assert tutor.leaks == 1 and tutor.fallbacks == 1
    monkeypatch.setattr(tutor, "chat", lambda system, user: ("Which number did you divide by? Hint: subtract first.", {}))
    turn = tutor.scaffold(units["be_001"], [], 1)
    assert not turn.leaked and turn.asks_question and not turn.fallback
    assert len((tmp_path / "log.jsonl").read_text(encoding="utf-8").splitlines()) == 2


def test_simulate_end_to_end_with_logistic_engine_and_resume(tmp_path):
    for folder in ("config", "data/units", "stimuli"):
        shutil.copytree(ROOT / folder, tmp_path / folder)
    args = ["--config", str(tmp_path / "config" / "default.yaml"), "--engine", "logistic", "--tutor", "fake",
            "--learners", "4", "--episodes", "3"]
    assert simulate.main(args) == 0
    processed = tmp_path / "data" / "processed" / "logistic"
    lines = (processed / "episodes.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 4 * 3 * 4  # 4 learners x 3 episodes x 4 arms
    assert (processed / "responses.csv").exists() and (processed / "learner_state.parquet").exists()
    assert len((processed / "checkpoints.jsonl").read_text(encoding="utf-8").splitlines()) == 4 * 4
    assert simulate.main(args) == 2  # refuses to overwrite silently
    assert simulate.main(args + ["--resume"]) == 0
    assert len((processed / "episodes.jsonl").read_text(encoding="utf-8").splitlines()) == len(lines)
    assert simulate.main(["--summarize", str(processed)]) == 0
    assert simulate.main(args + ["--tag", "second"]) == 0  # a second engine/tag runs beside the first (§10.2)
    # a resumed run may not change the population: make_population redraws every learner when n changes
    assert simulate.main(args[:-1] + ["6", "--resume"]) == 2


def test_worked_solution_is_withheld_until_after_the_first_attempt(cfg, units, stimuli):
    """Both the traditional and the substitution stimulus carry a '# Worked solution' block. The runner
    hands the learner the Explanation only, so none of it is readable before the first answer."""
    unit = units["be_001"]
    for condition in ("traditional", "ai_substitution"):
        by_condition = {c: stimuli[(unit.unit_id, c)] for c in corpus.CONDITIONS}
        eng, seen = ScriptedEngine(["misconception", "correct", "correct"]), {}
        orig = eng.choose

        def choose(trial, learner, rng, orig=orig, seen=seen):
            seen.setdefault(trial.stage, "\n".join(trial.lines))
            return orig(trial, learner, rng)

        eng.choose = choose
        run_episode(make_learner(), unit, by_condition, condition, 0, eng, FakeTutor(), cfg, np.random.default_rng(1))
        before = seen["first"]
        assert by_condition[condition].sections["Worked solution"] not in before
        assert unit.worked_solution not in before
        assert not corpus.contains_number(before, unit.problem.answer), f"{condition} shows the answer too early"


def test_scaffolding_prompt_names_the_turn_and_fills_the_distractor_notes(cfg, units, monkeypatch, tmp_path):
    """The hint level is an explicit `$turn` in the system prompt, not something to infer, and
    `$distractor_notes` comes from the unit JSON."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    tutor = Tutor(cfg["tutor"], ROOT / "config" / "prompts", tmp_path / "log.jsonl")
    seen = {}
    monkeypatch.setattr(tutor, "chat",
                        lambda system, user: (seen.update(system=system, user=user), ("Which divisor?", {}))[1])
    for level in (1, 2, 3):
        tutor.scaffold(units["be_001"], [], level)
        assert f"This is tutor turn {level} of 3" in seen["system"] and f"hint level {level}" in seen["system"]
        assert f"level-{level} hint" in seen["user"]
    assert "2,400 units: the documented misconception" in seen["system"]  # $distractor_notes, never blank


def test_blank_distractor_note_fails_loudly_instead_of_an_empty_prompt(units):
    problem = units["be_001"].problem
    (value, rule, _), other = problem.distractors
    blanked = replace(units["be_001"], problem=replace(problem, distractors=((value, rule, "   "), other)))
    with pytest.raises(TutorError, match="distractor_notes"):
        unit_facts(blanked)


def test_resume_refuses_a_different_parameter_arm(tmp_path):
    """The §7.2 arms are exactly where a careless --resume blends two parameterisations into one
    episodes.jsonl with nothing to tell the rows apart, so the guard must refuse the knobs that change
    the physics, not only the ones that change the population."""
    for folder in ("config", "data/units", "stimuli"):
        shutil.copytree(ROOT / folder, tmp_path / folder)
    args = ["--config", str(tmp_path / "config" / "default.yaml"), "--engine", "logistic", "--tutor", "fake",
            "--learners", "3", "--episodes", "2", "--tag", "arms"]
    assert simulate.main(args + ["--setting", "medium"]) == 0
    assert simulate.main(args + ["--setting", "low", "--resume"]) == 2
    assert simulate.main(args + ["--setting", "high", "--resume"]) == 2
    assert simulate.main(args + ["--policy", "immediate_withdrawal", "--resume"]) == 2
    assert simulate.main(args + ["--setting", "medium", "--resume"]) == 0  # the original arm still resumes

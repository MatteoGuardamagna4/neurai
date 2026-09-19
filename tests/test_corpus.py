import copy
import json

import pytest

from neurotutorsim import corpus
from tests.conftest import ROOT


def test_unit_validates(units):
    u = units["be_001"]
    assert u.problem.answer == 6000
    assert u.problem.distractors[0][0] == 2400  # the documented misconception comes first
    assert u.problem.method == "break_even_quantity" and u.problem.distractors[0][1] == "fixed_costs / price"
    assert u.near_transfer.answer == 9000 and u.far_transfer.answer == 80


def test_expression_validator_and_safety():
    params = {"fixed_costs": 180000, "price": 75, "variable_cost": 45}
    problem = {"validator": "expression", "expression": "fixed_costs / (price - variable_cost)", "params": params}
    assert corpus.expected_answer(problem) == 6000
    with pytest.raises(ValueError):
        corpus.evaluate("__import__('os').system('echo')", {})


def test_parse_unit_reports_wrong_answer_and_bad_distractor():
    raw = json.loads((ROOT / "data" / "units" / "be_001.json").read_text(encoding="utf-8"))
    bad = copy.deepcopy(raw)
    bad["problem"]["answer"] = 6001
    bad["near_transfer"]["distractors"][0]["value"] = 9000  # equals the answer
    _, errors = corpus.parse_unit(bad)
    assert any("validator" in e for e in errors)
    assert any("equals the answer" in e for e in errors)


def test_contains_number():
    assert corpus.contains_number("you need 6,000 units", 6000)
    assert corpus.contains_number("break even at 6000.0", 6000)
    assert not corpus.contains_number("you need 60,000 units", 6000)


def test_stimuli_structure_and_answer_placement(units, stimuli):
    assert set(stimuli) == {(uid, c) for uid in units for c in corpus.CONDITIONS}
    for (_, condition), stim in stimuli.items():
        assert tuple(stim.sections) == corpus.SECTIONS[condition]
    assert not corpus.contains_number(stimuli[("be_001", "ai_scaffolding")].body, 6000)
    assert corpus.contains_number(stimuli[("be_001", "traditional")].sections["Worked solution"], 6000)


def test_check_stimulus_flags_leak(units, stimuli):
    stim = stimuli[("be_001", "ai_scaffolding")]
    leaky = corpus.Stimulus(stim.stimulus_id, stim.unit_id, stim.condition, stim.variant,
                            {**stim.sections, "Hints": stim.sections["Hints"] + " The answer is 6,000 units."}, stim.path)
    assert any("leaks" in e for e in corpus.check_stimulus(leaky, units["be_001"]))


def test_tables_and_duration_caliper(units, stimuli, tmp_path):
    result = corpus.build_tables(units, stimuli, tmp_path)
    assert (tmp_path / "units.csv").exists() and (tmp_path / "stimuli.csv").exists()
    assert len(result["rows"]) == 3 * len(units)
    assert all(c["passed"] for c in result["caliper"].values())


def test_curriculum_order_puts_prerequisites_first():
    raw = json.loads((ROOT / "data" / "units" / "be_001.json").read_text(encoding="utf-8"))
    advanced = copy.deepcopy(raw)
    advanced.update(unit_id="be_000", concept="target_profit", difficulty=1, prerequisites=["break_even_quantity"])
    units = {u.unit_id: u for u, errs in (corpus.parse_unit(raw), corpus.parse_unit(advanced)) if not errs}
    assert [u.unit_id for u in corpus.curriculum_order(units)] == ["be_001", "be_000"]


def test_initial_reading_never_carries_the_worked_solution(units, stimuli):
    """What the runner delivers before the first attempt is `Stimulus.explanation` and nothing else
    (`episode.run_episode`), so the '# Worked solution' block of the traditional and substitution
    stimuli cannot be read early. Locked here for every unit and every condition."""
    for (uid, condition), stim in stimuli.items():
        reading = stim.explanation
        assert not corpus.contains_number(reading, units[uid].problem.answer), f"{uid}/{condition} leaks the answer"
        assert stim.sections.get("Worked solution", "<absent>") not in reading


def test_diagnostic_questions_must_cover_every_documented_distractor(units, stimuli):
    stim = stimuli[("be_001", "ai_scaffolding")]
    thin = corpus.Stimulus(stim.stimulus_id, stim.unit_id, stim.condition, stim.variant,
                           {**stim.sections, "Diagnostic questions": "Let me say one thing about your result."},
                           stim.path)
    assert any("Diagnostic questions asks 0" in e for e in corpus.check_stimulus(thin, units["be_001"]))


def test_text_controls_are_complete_and_their_checks_bite(units, stimuli):
    controls = corpus.load_text_controls(ROOT / "stimuli", units, stimuli, require_all=True)
    assert len(controls) == len(units) * (len(corpus.CONDITIONS) * len(corpus.REWORDED) + 1)
    variant, primary = controls[("be_001", "traditional", "reworded_1")], stimuli[("be_001", "traditional")]
    changed = corpus.Stimulus(variant.stimulus_id, variant.unit_id, variant.condition, variant.variant,
                              {**variant.sections, "Explanation": variant.explanation.replace("24,000", "25,000")}, variant.path)
    assert any("stated numbers differ" in e for e in corpus.check_text_control(changed, primary, units["be_001"]))
    wrong = controls[("be_001", "traditional", "incorrect")]
    leaked = corpus.Stimulus(wrong.stimulus_id, wrong.unit_id, wrong.condition, wrong.variant,
                             {**wrong.sections, "Hints": wrong.sections["Hints"] + " The answer is 6,000 units."}, wrong.path)
    assert any("must not appear" in e for e in corpus.check_text_control(leaked, primary, units["be_001"]))

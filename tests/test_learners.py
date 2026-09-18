import copy
import json
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from neurotutorsim import corpus, simulate
from neurotutorsim import learners as L
from neurotutorsim.engines import LogisticEngine, find_latent_leaks
from neurotutorsim.episode import run_episode
from neurotutorsim.tutor import FakeTutor

GOLDEN = Path(__file__).parent / "data" / "phase3_golden.json"


def phase3_states(cfg, units, stimuli, n_learners=5, n_episodes=10) -> dict:
    """Learners 0..n-1 through all four arms with the logistic engine and the fake tutor, exactly as
    simulate.main sequences them; the fixture that pins Phase III while learners.py grows (PLAN.md S4)."""
    order = corpus.curriculum_order(units)
    master = int(cfg["seeds"]["master"])
    pop = L.make_population(cfg["population"], n_learners, master)
    L.seed_prior_records(pop, cfg)
    engine = LogisticEngine(cfg["response"], cfg["population"]["theta_slope"])
    out = {}
    for condition in simulate.RUN_CONDITIONS:
        for base in pop:
            learner = L.Learner.restore(base.snapshot())
            for ep in range(n_episodes):
                unit = order[ep % len(order)]
                rec = run_episode(learner, unit, {c: stimuli[(unit.unit_id, c)] for c in corpus.CONDITIONS}, condition,
                                  ep, engine, FakeTutor(), cfg, np.random.default_rng([master, learner.learner_id, ep]))
                out[f"{condition}|{learner.learner_id}|{ep}"] = {k: round(v, 12) for k, v in rec.state_after.items()}
    return out


def make_learner(**kw):
    base = dict(learner_id=0, stratum=1, K=0.4, M=0.3, R=0.3, C=0.5, D=0.4, alpha=0.1, delta=0.01,
                confidence_bias=0.0, speed=1.0)
    return L.Learner(**{**base, **kw})


def proxies(**kw):
    base = dict(attempt=0.5, retrieval=0.5, explanation=0.5, answer_provided=0.0, offloading=0.5,
                correct_after_error=0.0, transfer_success=1.0, support_used=0.5, support_faded=0.0,
                independent_success=0.0, adaptation=0.5, mismatch=0.2, coverage=1.0, correctness=1.0)
    return L.Proxies(**{**base, **kw})


def test_resolve_selects_arm():
    node = {"a": {"low": 1, "medium": 2, "high": 3}, "b": [{"low": 1, "medium": 2, "high": 3}], "c": 9}
    assert L.resolve(node, "high") == {"a": 3, "b": [3], "c": 9}


def test_population_is_deterministic_and_bounded(cfg):
    pop = L.make_population(cfg["population"], 60, 1)
    again = L.make_population(cfg["population"], 60, 1)
    assert [l.K for l in pop] == [l.K for l in again]
    assert all(0.0 <= getattr(l, k) <= 1.0 for l in pop for k in L.STATE)
    assert {l.stratum for l in pop} <= {0, 1, 2}
    assert all(l.alpha > 0 and 0 < l.delta < 1 for l in pop)
    high = [l.K for l in pop if l.stratum == 2]
    low = [l.K for l in pop if l.stratum == 0]
    assert sum(high) / len(high) > sum(low) / len(low)


def test_prior_record_carries_the_initial_state_without_revealing_it(cfg):
    """Brief §7.3: the sampled state must reach the first call as observable history, not as latents."""
    pop = L.make_population(cfg["population"], 40, 3)
    L.seed_prior_records(pop, cfg)
    lines = [l.record_line() for l in pop]
    assert all(lines), "the record must exist before any episode has been run"
    assert len(set(lines)) > 1, "learners drawn differently must send different records"
    assert not find_latent_leaks(" ".join(lines))
    strong = max(pop, key=lambda l: l.K + l.M + l.R)
    weak = min(pop, key=lambda l: l.K + l.M + l.R)
    assert strong.prior_first_try > weak.prior_first_try
    assert max(pop, key=lambda l: l.D).prior_help > min(pop, key=lambda l: l.D).prior_help
    # eq. 24 continues from the drawn C instead of restarting from an empty history after episode 1
    n = cfg["population"]["prior_problems"]
    assert all(l.brier_n == n for l in pop)
    assert all(abs((1.0 - l.brier_sum / l.brier_n) - l.C) < 1e-9 for l in pop)


def test_record_line_reports_recent_form_and_topic_experience(cfg):
    """The learner must be able to read its own track record off the prompt (no latents, §7.3)."""
    l = make_learner()
    L.seed_prior_records([l], cfg)
    assert "In your last" in l.record_line("contribution_margin_ratio"), "recent form must exist before episode 1"
    for _ in range(3):
        l.note_episode("contribution_margin_ratio", True)
    line = l.record_line("contribution_margin_ratio")
    assert "You have solved the last 3 in a row." in line
    assert "met this kind of problem 3 times before and solved it on the first try 3" in line
    l.note_episode("contribution_margin_ratio", False)
    assert "in a row" not in l.record_line("contribution_margin_ratio"), "a miss resets the streak"
    assert "met this kind of problem 4 times" in l.record_line("contribution_margin_ratio")
    assert "met this kind" not in l.record_line("wacc"), "an unseen topic claims no experience"
    assert len(l.recent) == L.RECENT_N, "recent form stays bounded"
    assert not find_latent_leaks(l.record_line("contribution_margin_ratio"))


def test_effort_and_effectiveness_directions(cfg):
    e0 = L.effort(proxies(), cfg["effort"])
    assert L.effort(proxies(answer_provided=1.0), cfg["effort"]) < e0
    assert L.effort(proxies(attempt=1.0), cfg["effort"]) > e0
    f0 = L.effectiveness(proxies(), cfg["effectiveness"])
    assert L.effectiveness(proxies(adaptation=1.0), cfg["effectiveness"]) > f0
    assert L.effectiveness(proxies(mismatch=1.0), cfg["effectiveness"]) < f0


def test_update_equations_move_in_the_documented_directions(cfg):
    learner = make_learner()
    clipped = L.update(learner, proxies(support_used=1.0, transfer_success=1.0, offloading=0.0), 0.8, 0.8,
                       [(0.9, 1.0)], cfg["updates"])
    assert learner.K > 0.4 and learner.R > 0.3 and learner.D > 0.4
    assert learner.C == pytest.approx(1.0 - 0.01)  # Brier of a 0.9 forecast on a correct answer
    assert set(clipped) == set(L.STATE) and not any(clipped.values())


def test_clipping_is_counted(cfg):
    learner = make_learner(D=1.0)
    clipped = L.update(learner, proxies(support_used=1.0), 0.8, 0.8, [], cfg["updates"])
    assert clipped["D"] == 1 and learner.D == 1.0


def test_phase3_golden_states_are_reproduced(cfg, units, stimuli):
    """Every Phase III run on disk used these equations; regenerate the fixture only with a deliberate
    physics change (python -m tests.test_learners rewrites it)."""
    assert cfg["updates"]["form"] == "brief"
    golden = json.loads(GOLDEN.read_text(encoding="utf-8"))
    states = phase3_states(cfg, units, stimuli)
    assert states.keys() == golden.keys()
    for key, expected in golden.items():
        for k, v in expected.items():
            assert states[key][k] == pytest.approx(v, abs=1e-11), f"{key} {k}"


def test_bounded_form_never_clips_and_matches_brief_gains_far_from_the_bounds(cfg):
    rng = np.random.default_rng(0)
    n = 10_000
    K, M, R, D = (rng.random(n) for _ in range(4))
    p = L.Proxies(*(rng.random(n) for _ in range(14)))
    p.independent_success = rng.integers(0, 2, n).astype(float)
    rates = {k: rng.random(n) * 0.5 for k in ("eta_M", "eta_C", "eta_R", "eta_O", "eta_D", "eta_F")}
    c = {**rates, "m_decay_scale": 1.0}  # eta_M + eta_C <= 1 keeps the M gain inside the distance to 1
    out = L.step_state(K, M, R, D, rng.random(n), rng.random(n) * 0.05, p, rng.random(n), rng.random(n), c, "bounded")
    for k, v in out.items():
        assert np.all(v >= 0.0) and np.all(v <= 1.0), k
    # the brief form does clip on the same inputs, which is what D3 removes
    brief = L.step_state(K, M, R, D, rng.random(n), rng.random(n) * 0.05, p, rng.random(n), rng.random(n), c, "brief")
    assert any(np.any((v < 0.0) | (v > 1.0)) for v in brief.values())
    with pytest.raises(ValueError):
        L.step_state(0.5, 0.5, 0.5, 0.5, 0.1, 0.01, proxies(), 0.5, 0.5, cfg["updates"], "other")


def test_bounded_dependence_falls_after_any_unaided_success(cfg):
    p = proxies(support_used=0.0, support_faded=0.0, independent_success=1.0)
    brief = L.step_state(0.4, 0.3, 0.3, 0.4, 0.1, 0.01, p, 0.5, 0.5, cfg["updates"], "brief")
    bounded = L.step_state(0.4, 0.3, 0.3, 0.4, 0.1, 0.01, p, 0.5, 0.5, cfg["updates"], "bounded")
    assert brief["D"] == 0.4, "under a persistent policy the brief form never lowers D"
    assert bounded["D"] < 0.4


def test_calendar_scaling_and_break(cfg):
    cal = copy.deepcopy(cfg["calendar"])
    assert L.calendar_delta_scale(cal) == 1.0, "three episodes per week reproduces Phase III exactly"
    cal["episodes_per_week"] = 1
    assert L.calendar_delta_scale(cal) == 3.0
    p, c = proxies(), cfg["updates"]
    base = L.step_state(0.6, 0.5, 0.3, 0.4, 0.1, 0.02, p, 0.0, 0.0, c, "brief")  # E = 0: forgetting only
    weekly = L.step_state(0.6, 0.5, 0.3, 0.4, 0.1, 0.02, p, 0.0, 0.0, c, "brief", delta_scale=3.0)
    assert 0.6 - weekly["K"] == pytest.approx(3 * (0.6 - base["K"]))
    K, M = L.apply_break(0.8, 0.5, 0.02, cfg["calendar"], c)
    assert K == pytest.approx(0.8 * 0.98 ** 9) and M == pytest.approx(0.5 * 0.98 ** 9)
    Ks, _ = L.apply_break(np.array([0.8, 0.4]), np.array([0.5, 0.5]), np.array([0.02, 0.0]), cfg["calendar"], c)
    assert Ks[1] == 0.4 and Ks[0] < 0.8


def test_help_cap_policies(cfg):
    s = copy.deepcopy(cfg["support"])
    learner = make_learner(streak=3)
    assert L.help_cap(learner, s) == 3
    s["persistence_policy"] = "immediate_withdrawal"
    assert L.help_cap(learner, s) == 0
    s["persistence_policy"] = "gradual_fading"
    assert L.help_cap(learner, s) == 2  # ceil(3 * 0.75 ** 3)


def test_snapshot_round_trip():
    learner = make_learner(history=["Problem 1."], last_seen={"be_001": 0})
    assert L.Learner.restore(learner.snapshot()) == learner


def test_calibration_metrics():
    assert L.brier([(1.0, 1.0), (0.0, 1.0)]) == 0.5
    assert L.ece([(0.9, 1.0), (0.9, 1.0)]) == pytest.approx(0.1)
    assert L.brier([]) != L.brier([])  # nan


if __name__ == "__main__":  # rewrite the golden fixture after a deliberate change to the Phase III equations
    from tests.conftest import ROOT

    c = simulate.load_config(ROOT / "config" / "default.yaml")
    c["tutor"]["provider"], c["engine"]["name"] = "fake", "logistic"
    u = corpus.load_units(ROOT / "data" / "units")
    GOLDEN.write_text(json.dumps(phase3_states(c, u, corpus.load_stimuli(ROOT / "stimuli", u)), indent=0), encoding="utf-8")
    print(f"wrote {GOLDEN}")

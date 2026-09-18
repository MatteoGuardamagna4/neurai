"""Phase V tests (PLAN.md S6, T1-T10). T1 is the one that matters: the vectorised step must reproduce the
per-learner reference loop (`episode.run_episode` + `LogisticEngine` + `FakeTutor`) in distribution."""
import copy
import json
import shutil

import numpy as np
import pandas as pd
import pytest
import yaml

from neurotutorsim import corpus, longitudinal as LG, simulate
from neurotutorsim import learners as L
from neurotutorsim.corpus import CONDITIONS
from neurotutorsim.engines import LogisticEngine
from neurotutorsim.episode import run_episode
from neurotutorsim.tutor import FakeTutor
from tests.conftest import ROOT
from tests.test_plasticity import write_fake_tribe


@pytest.fixture(scope="module")
def root(tmp_path_factory, units):
    """A repository root with a synthetic TRIBE run, so `Sim.build` has patterns to accumulate."""
    r = tmp_path_factory.mktemp("root")
    write_fake_tribe(r / "data" / "tribe" / "tribe_main", list(units))
    return r


@pytest.fixture(scope="module")
def raw():
    return yaml.safe_load((ROOT / "config" / "default.yaml").read_text(encoding="utf-8"))


def build(cfg, units, root, scenarios=None, **kw):
    scen = scenarios or LG.scenarios_from_config(cfg["phase5"])
    return LG.Sim.build(cfg, units, scen, root, **kw)


def reference_loop(cfg, units, stimuli, scenarios, n, episodes, master):
    """The Phase III loop, scenario by scenario, on the population `Pop.draw` uses for draw -1."""
    order = corpus.curriculum_order(units)
    pop = L.make_population(cfg["population"], n, master * 1000 - 1)
    L.seed_prior_records(pop, cfg)
    engine = LogisticEngine(cfg["response"], cfg["population"]["theta_slope"])
    out = {}
    for s in scenarios:
        c = copy.deepcopy(cfg)
        c["support"]["persistence_policy"] = s.policy
        rows, finals = [], []
        for base in pop:
            learner = L.Learner.restore(base.snapshot())
            for ep in range(episodes):
                unit = order[ep % len(order)]
                rec = run_episode(learner, unit, {cc: stimuli[(unit.unit_id, cc)] for cc in CONDITIONS}, s.protocol, ep,
                                  engine, FakeTutor(), c, np.random.default_rng([master, learner.learner_id, ep]))
                rows.append({"first": rec.first_correct, "transfer": rec.transfer_correct, "help": rec.help_requests,
                             "reveal": rec.answer_provided, "E": rec.effort, "F": rec.effectiveness, "protocol": rec.protocol})
            finals.append(learner.state())
        out[s.name] = (pd.DataFrame(rows), pd.DataFrame(finals))
    return out


def levels_of(res):
    d = res["simulation_draws"]
    return d[d["kind"] == "level"].reset_index(drop=True)


def contrasts_of(res):
    d = res["simulation_draws"]
    return d[d["kind"] == "contrast"].reset_index(drop=True)


def se_diff(a, b):
    return float(np.sqrt(np.var(a, ddof=1) / len(a) + np.var(b, ddof=1) / len(b)))


def test_t1_vectorised_step_matches_the_reference_loop(cfg, units, stimuli, root):
    n, episodes, master = 200, 30, int(cfg["seeds"]["master"])
    scen = LG.scenarios_from_config(cfg["phase5"])
    sim = build(cfg, units, root, scen, form="brief", epw=3)
    res = LG.run_draw(sim, -1, cfg, n, 1, master, {}, n_episodes=episodes, keep_episodes=True)
    vec = res["episodes_central"]
    ref = reference_loop(cfg, units, stimuli, scen, n, episodes, master)
    failures = []
    for si, s in enumerate(scen):
        r_rows, r_final = ref[s.name]
        v_rows = vec[vec["scenario"] == s.name]
        sl = slice(si * n, (si + 1) * n)
        for k in LG.STATES:  # means at episode 29
            a, b = res["final"][k][sl], r_final[k].to_numpy()
            if abs(a.mean() - b.mean()) > 4 * se_diff(a, b):
                failures.append(f"{s.name} {k}: {a.mean():.4f} vs {b.mean():.4f} (se {se_diff(a, b):.4f})")
        pairs = {"first": "first_correct", "transfer": "transfer_correct", "help": "help_requests", "reveal": "reveal",
                 "E": "effort", "F": "effectiveness"}
        for rk, vk in pairs.items():  # per-episode rates pooled over the 30 episodes
            a, b = v_rows[vk].to_numpy(float), r_rows[rk].to_numpy(float)
            if abs(a.mean() - b.mean()) > 4 * se_diff(a, b):
                failures.append(f"{s.name} {rk}: {a.mean():.4f} vs {b.mean():.4f} (se {se_diff(a, b):.4f})")
        if s.protocol == "free_choice":
            for c in CONDITIONS:
                a, b = (v_rows["protocol"] == c).to_numpy(float), (r_rows["protocol"] == c).to_numpy(float)
                if abs(a.mean() - b.mean()) > 4 * se_diff(a, b):
                    failures.append(f"free-choice share {c}: {a.mean():.3f} vs {b.mean():.3f}")
    assert not failures, "\n".join(failures)


def test_t2_same_seed_same_outputs(cfg, units, root):
    sim = build(cfg, units, root)
    a = LG.run_draw(sim, 3, cfg, 50, 1, 1, {}, subsample=5)
    b = LG.run_draw(sim, 3, cfg, 50, 1, 1, {}, subsample=5)
    assert a["simulation_draws"].equals(b["simulation_draws"])
    assert a["neural_contrasts"].equals(b["neural_contrasts"])
    c = LG.run_draw(sim, 4, cfg, 50, 1, 1, {}, subsample=5)
    assert not a["simulation_draws"].equals(c["simulation_draws"])


def test_t3_common_random_numbers_null(cfg, units, root):
    scen = [LG.Scenario("traditional", "traditional"), LG.Scenario("traditional_copy", "traditional")]
    sim = build(cfg, units, root, scen)
    res = LG.run_draw(sim, 0, cfg, 60, 1, 1, {}, subsample=5)
    contrasts = contrasts_of(res)
    assert len(contrasts) and (contrasts["estimate"] == 0).all() and (contrasts["prsup"] == 0).all()
    assert (res["neural_contrasts"]["mean"] == 0).all()


def test_t4_zero_plasticity_gives_exact_zeros(cfg, units, root):
    sim = build(cfg, units, root, zero_plasticity=True)
    res = LG.run_draw(sim, 0, cfg, 40, 1, 1, {}, subsample=5)
    neural = res["neural_contrasts"]
    assert len(neural) == 4 * 4 * 7  # AI scenarios x mechanisms x networks
    assert (neural["mean"] == 0).all() and (neural["d"] == 0).all()
    yearly = res["yearly_subsample"]
    assert (yearly[[c for c in yearly.columns if c.startswith("N_")]] == 0).all().all()
    on = build(cfg, units, root)
    assert (LG.run_draw(on, 0, cfg, 40, 1, 1, {}, subsample=5)["neural_contrasts"]["mean"] != 0).any()


def test_t5_zero_effort_makes_effort_constant(cfg, units, root):
    sim = build(cfg, units, root, zero_effort=True)
    res = LG.run_draw(sim, -1, cfg, 40, 1, 1, {}, n_episodes=12, keep_episodes=True)
    eps = res["episodes_central"]
    assert np.allclose(eps["effort"], L.logistic(cfg["effort"]["a0"]))


def test_t6_bounded_form_never_clips_over_ten_years(cfg, units, root):
    sim = build(cfg, units, root, form="bounded")
    res = LG.run_draw(sim, 0, cfg, 100, 10, 1, {}, subsample=5)
    levels = levels_of(res)
    assert levels.query("outcome == 'clips'")["estimate"].eq(0).all()
    assert levels["year"].max() == 10
    # the brief form does hit the bounds over the same horizon (why D3 exists)
    brief = levels_of(LG.run_draw(build(cfg, units, root, form="brief"), 0, cfg, 100, 10, 1, {}, subsample=5))
    assert brief.query("outcome == 'clips'")["estimate"].sum() > 0


def test_t7_retention_falls_over_the_break(cfg, units, root):
    sim = build(cfg, units, root)
    res = levels_of(LG.run_draw(sim, 0, cfg, 80, 1, 1, {}, subsample=5)).query("year == 1").set_index(["scenario", "outcome"])["estimate"]
    flat = levels_of(LG.run_draw(sim, 0, cfg, 80, 1, 1, {}, subsample=5, break_scale=0.0)).query("year == 1").set_index(["scenario", "outcome"])["estimate"]
    for s in cfg["phase5"]["scenarios"]:
        assert res[(s, "retention")] < res[(s, "unaided")]
        assert res[(s, "retention_below_share")] == 1.0
        assert flat[(s, "retention")] == pytest.approx(flat[(s, "unaided")])


def test_t8_calendar(cfg, units, root):
    for epw, per_year in ((1, 40), (3, 120), (5, 200)):
        sim = build(cfg, units, root, epw=epw)
        assert sim.episodes_per_year() == per_year
    sim = build(cfg, units, root)
    b0 = sim.difficulty(0, 0, 0.1)
    assert sim.difficulty(0, 1, 0.1) == pytest.approx(b0 + 0.1) and sim.difficulty(0, 5, 0.1) == pytest.approx(b0 + 0.5)
    # at one episode per week each episode carries three times the forgetting, so a year forgets the same
    assert L.calendar_delta_scale({**cfg["calendar"], "episodes_per_week": 1}) == 3.0


def test_t9_parameter_draws(raw):
    leaves = LG.arm_leaves(raw)
    assert "population.mu_alpha" in leaves and "plasticity.half_life_weeks" in leaves and "phase5.ramp_per_year" in leaves
    central, values = LG.draw_parameters(raw, -1, 1)
    medium = L.resolve(raw, "medium")
    medium["parameter_setting"] = central["parameter_setting"]
    assert central == medium
    for b in range(5):
        cfg, vals = LG.draw_parameters(raw, b, 1)
        for k, v in vals.items():
            lo, hi = min(leaves[k]["low"], leaves[k]["high"]), max(leaves[k]["low"], leaves[k]["high"])
            assert lo <= v <= hi, k
    assert LG.draw_parameters(raw, 0, 1)[1] == LG.draw_parameters(raw, 0, 1)[1]
    assert LG.draw_parameters(raw, 0, 1)[1] != LG.draw_parameters(raw, 1, 1)[1]
    uni = LG.draw_parameters(raw, 0, 1, "uniform")[1]
    assert uni != LG.draw_parameters(raw, 0, 1)[1]
    with pytest.raises(ValueError):
        LG.draw_parameters(raw, 0, 1, "normal")


def test_t10_expected_accuracy_by_hand(cfg, units, root):
    sim = build(cfg, units, root)
    pop = LG.Pop(K=np.array([0.3, 0.8]), M=np.array([0.2, 0.6]), R=np.array([0.4, 0.5]), D=np.array([0.5, 0.2]),
                 alpha=np.zeros(2), delta=np.zeros(2), bias=np.zeros(2), stratum=np.array([0, 2]),
                 brier_sum=np.zeros(2), brier_n=np.ones(2, dtype=int))
    ex = sim.expected(pop, 0, 0.0)
    r, cur = cfg["response"], cfg["curriculum"]
    for i in range(2):
        theta = cfg["population"]["theta_slope"] * (pop.K[i] - 0.5)
        ps = [1 / (1 + np.exp(-(theta - cur["b_slope"] * (units[u].difficulty - 3) + r["rho"] * pop.R[i] + r["kappa"] * pop.M[i])))
              for u in sorted(units)]
        assert ex["unaided"][i] == pytest.approx(np.mean(ps))
    assert (ex["support_gap"] > 0).all() and ex["unaided"][1] > ex["unaided"][0]


def test_cli_writes_parts_resumes_and_refuses_a_changed_design(tmp_path, units):
    for folder in ("config", "data/units", "stimuli"):
        shutil.copytree(ROOT / folder, tmp_path / folder)
    write_fake_tribe(tmp_path / "data" / "tribe" / "tribe_main", list(units))
    base = ["--config", str(tmp_path / "config" / "default.yaml"), "--years", "1", "--learners", "30", "--subsample", "4",
            "--flush-every", "2"]
    args = base + ["--tag", "t", "--draws", "2"]
    assert LG.main(args) == 0
    out = tmp_path / "data" / "processed" / "phase5" / "t"
    meta = json.loads((out / "run.json").read_text())
    assert meta["draws_done"] == [-1, 0, 1] and meta["parts"] == ["part-00000", "part-00001"]
    draws = LG.read_table(out, "simulation_draws", with_params=True)
    assert sorted(draws["draw_id"].unique()) == [-1, 0, 1]
    assert set(draws["kind"]) == {"level", "contrast"} and "population.mu_alpha" in draws.columns
    assert len(LG.read_table(out, "episodes_central")) == 30 * 5 * 120, "the central draw keeps year-1 episodes"
    assert set(LG.read_table(out, "yearly_subsample")["draw_id"]) == {-1, 0, 1}
    hist = LG.read_table(out, "contrast_hist")
    assert hist.groupby(["scenario", "year", "outcome"])["count"].sum().eq(3 * 30).all(), "3 draws x 30 learners"
    assert LG.read_arrays(out, "mean_accumulator_diff")["diff"].shape[1:] == (5, 90)
    assert LG.read_arrays(out, "accumulators_subsample")["values"].shape[1:] == (5 * 4, 5, 90)
    assert LG.main(args) == 2, "an existing tag needs --resume"
    assert LG.main(base + ["--tag", "t", "--draws", "3", "--resume"]) == 2, "a resume may not change the design"
    assert LG.main(args + ["--resume"]) == 0  # nothing left to do
    assert json.loads((out / "run.json").read_text())["parts"] == meta["parts"]
    assert LG.main(base + ["--tag", "z", "--draws", "1", "--zero-plasticity", "--scenarios", "traditional", "substitution"]) == 0
    neural = LG.read_table(tmp_path / "data" / "processed" / "phase5" / "z", "neural_contrasts")
    assert len(neural) and (neural["mean"] == 0).all()


def test_mediation_and_per_scenario_comparators(cfg, units, root):
    scen = [LG.Scenario("traditional", "traditional"), LG.Scenario("substitution", "ai_substitution"),
            LG.Scenario("free_choice", "free_choice"),
            LG.Scenario("traditional|hold_E", "traditional", mediate="E"),
            LG.Scenario("traditional|hold_D", "traditional", mediate="D"),
            LG.Scenario("substitution|hold_D", "ai_substitution", mediate="D"),
            LG.Scenario("substitution|hold_F", "ai_substitution", mediate="F"),
            LG.Scenario("free_choice|hold_D", "free_choice", mediate="D"),
            LG.Scenario("traditional_x2", "traditional", forget_scale=2.0),
            LG.Scenario("traditional_x2_copy", "traditional", forget_scale=2.0, comparator="traditional_x2")]
    res = LG.run_draw(build(cfg, units, root, scen), 0, cfg, 80, 1, 1, {}, subsample=5)
    c = contrasts_of(res)
    est = c.set_index(["scenario", "outcome"])["estimate"]
    for held in ("traditional|hold_E", "traditional|hold_D", "traditional_x2_copy"):
        assert (c[c["scenario"] == held]["estimate"] == 0).all(), held  # held at its own value / its own twin
    # substitution never asks for help and never chooses, so holding D there changes nothing ...
    assert (c[c["scenario"] == "substitution|hold_D"].set_index("outcome")["estimate"]
            == c[c["scenario"] == "substitution"].set_index("outcome")["estimate"]).all()
    # ... while holding D in free choice changes the approach picks, and holding F changes the K update
    assert est[("free_choice|hold_D", "K")] != est[("free_choice", "K")]
    assert est[("substitution|hold_F", "K")] != est[("substitution", "K")]
    retention = levels_of(res).query("outcome == 'retention'").set_index("scenario")["estimate"]
    assert retention["traditional_x2"] < retention["traditional"], "double forgetting lowers retention"


def test_frontier_designs_and_the_neural_diagram(cfg, units, root):
    grid, knobs, extra = LG.frontier_scenarios("grid")
    assert len(grid) == 1 + 7 * 7 * 3 and len(knobs) == 147 and extra == {}
    lines, knobs, _ = LG.frontier_scenarios("lines")
    assert sum(k["line"] == "forget" for k in knobs.values()) == 11 and sum(k["line"] == "e" for k in knobs.values()) == 11
    by_name = {s.name: s for s in lines}
    assert by_name["line_forget_0.2500"].comparator == "traditional_forget_0.2500"
    assert by_name["line_f_0.00"].fade_base == 1.0, "f = 0 is the no-fade point"
    scen, _, extra = LG.frontier_scenarios("neural")
    assert [s.name for s in scen] == ["traditional", "substitution"] and extra["half_lives"] == LG.NEURAL_HALF_LIVES
    lam = cfg["plasticity"]["lambda_O"]
    res = LG.run_draw(build(cfg, units, root, scen), 0, cfg, 60, 1, 1, {}, subsample=5,
                      half_lives=(cfg["plasticity"]["half_life_weeks"], 8), lambda_o_grid=(lam, 1.0))
    nd = res["neural_diagram"]
    assert len(nd) == 2 * 2 * 7  # half-lives x lambda_O x networks, one AI scenario, one year
    same = nd[(nd["half_life_weeks"] == cfg["plasticity"]["half_life_weeks"]) & (nd["lambda_O"] == lam)].set_index("network")["mean"]
    main = res["neural_contrasts"].query("mechanism == 'D'").set_index("network")["mean"]
    assert np.allclose(same.reindex(main.index), main, rtol=0, atol=1e-12), "the diagram reproduces the main mechanism-D contrast"


def test_cli_mediation_records_the_design(tmp_path, units):
    for folder in ("config", "data/units", "stimuli"):
        shutil.copytree(ROOT / folder, tmp_path / folder)
    write_fake_tribe(tmp_path / "data" / "tribe" / "tribe_main", list(units))
    args = ["--config", str(tmp_path / "config" / "default.yaml"), "--years", "1", "--learners", "20", "--draws", "1",
            "--tag", "m", "--mediate", "E,F,D", "--no-neural"]
    assert LG.main(args) == 0
    meta = json.loads((tmp_path / "data" / "processed" / "phase5" / "m" / "run.json").read_text())
    assert len(meta["scenarios"]) == 5 + 4 * 3 and len(meta["scenario_knobs"]) == 12 and meta["neural"] is False
    assert LG.main(args[:-5] + ["--tag", "m", "--mediate", "E", "--no-neural", "--resume"]) == 2, "the design may not change"

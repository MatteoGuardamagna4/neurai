import shutil

import numpy as np
import pandas as pd
import pytest

from neurotutorsim import analysis as A, longitudinal as LG
from neurotutorsim.corpus import CONDITIONS
from tests.conftest import ROOT
from tests.test_plasticity import write_fake_rule, write_fake_tribe


def test_smd_tost_and_fdr_on_hand_examples():
    assert A.smd([1, 2, 3], [1, 2, 3]) == 0.0
    assert A.smd([2, 3, 4], [1, 2, 3]) == pytest.approx(1.0)  # difference 1, pooled sd 1
    assert A.paired_tost(np.full(10, 0.01) + np.linspace(-0.001, 0.001, 10), 0.1) < 0.001
    assert A.paired_tost(np.full(10, 0.5) + np.linspace(-0.01, 0.01, 10), 0.1) > 0.99
    # hand computation: sorted p = .01 .03 .04 .2 -> p*m/rank = .04 .06 .0533 .2 -> monotone from the top: .04 .0533 .0533 .2
    assert A.bh_fdr([0.01, 0.04, 0.03, 0.2]) == pytest.approx([0.04, 0.05333333, 0.05333333, 0.2])
    assert np.isnan(A.bh_fdr([np.nan, 0.5])[0])


def test_intervals_bootstrap_and_tipping_points():
    x = np.arange(1, 101, dtype=float)
    iv = A.intervals(x)
    assert iv["median"] == pytest.approx(50.5) and iv["lo90"] == pytest.approx(5.95) and iv["hi95"] == pytest.approx(97.525)
    lo, hi = A.bootstrap_ci(np.random.default_rng(0).normal(3, 1, 200))
    assert lo < 3 < hi
    grid = np.linspace(0, 1, 11)
    assert A.tipping_point(grid, grid - 0.35) == pytest.approx(0.35)  # rising through zero
    assert A.tipping_point(grid, 0.62 - grid) == pytest.approx(0.62)  # falling through zero
    assert np.isnan(A.tipping_point(grid, grid + 1)) and np.isnan(A.tipping_point(grid, -grid - 1))


def test_corpus_balance_on_toy_stimuli():
    units = [f"u{i}" for i in range(20)]
    rng = np.random.default_rng(1)
    rows = []
    for u in units:
        base = rng.normal(500, 40)
        for c, shift in zip(CONDITIONS, (0.0, 40.0, 0.0)):
            rows.append({"unit_id": u, "condition": c, **{f: base + shift for f in A.FEATURES}})
    bal = A.corpus_balance(pd.DataFrame(rows)).set_index("feature")
    assert bal.loc["word_count", "smd_U-T"] == pytest.approx(0.0) and bal.loc["word_count", "smd_S-T"] > 0.5
    assert bal.loc["word_count", "diff_S-T"] == pytest.approx(40.0)
    assert not bal["within_target"].any()


def test_metric_definitions_cover_every_tribe_metric():
    defs = A.metric_definitions()
    for m in ("mean", "auc", "peak", "time_to_peak", "sustained", "dispersion", "entropy", "integration", "differentiation", "N"):
        assert m in set(defs["metric"]), m
    assert defs["direction"].str.len().min() > 20


def test_engine_comparison_of_a_run_with_itself_is_zero(tmp_path):
    from neurotutorsim import simulate

    for folder in ("config", "data/units", "stimuli"):
        shutil.copytree(ROOT / folder, tmp_path / folder)
    assert simulate.main(["--config", str(tmp_path / "config" / "default.yaml"), "--engine", "logistic", "--tutor", "fake",
                          "--learners", "5", "--episodes", "12"]) == 0
    run = tmp_path / "data" / "processed" / "logistic"
    comp = A.engine_comparison(run, run, n_boot=200)
    paired = comp[comp["section"] == "paired difference"]
    assert len(paired) and np.allclose(paired["difference"], 0.0)
    assert {"unaided_ep9", "far_ep11", "K", "help_per_episode"} <= set(paired["outcome"])
    arms = comp[comp["section"] == "arm contrast within centaur"]
    assert set(arms["condition"]) == {"S-T", "U-T", "S-U"}
    shares = A.free_choice_shares(run)
    assert shares.query("K_tercile == 'all'")["share"].sum() == pytest.approx(1.0)


def test_gate18_on_a_tiny_pilot(tmp_path, units):
    for folder in ("config", "data/units", "stimuli"):
        shutil.copytree(ROOT / folder, tmp_path / folder)
    write_fake_tribe(tmp_path / "data" / "tribe" / "tribe_main", list(units))
    write_fake_rule(tmp_path)
    base = ["--config", str(tmp_path / "config" / "default.yaml"), "--years", "1", "--learners", "300", "--draws", "3"]
    assert LG.main(base + ["--tag", "p"]) == 0
    assert LG.main(base + ["--tag", "z", "--zero-plasticity"]) == 0
    assert LG.main(base + ["--tag", "e", "--zero-effort"]) == 0
    assert LG.main(base + ["--tag", "c", "--set", "phase5.scenarios.traditional_copy={protocol: traditional, policy: persistent}"]) == 0
    out = tmp_path / "data" / "processed" / "phase5"
    table = A.gate18(out / "p", out / "z", out / "e", out / "c", run_t1=False).set_index("check")
    assert len(table) == 10 and table.drop(index="G1b prior knowledge at year 1 (PLAN.md S8, informational)")["pass"].map(
        lambda v: isinstance(v, (bool, np.bool_))).all()
    for check in ("G1 prior knowledge monotone (brief §10.2)", "G2 difficulty lowers accuracy", "G3 support helps",
                  "G6 zero plasticity", "G8 common random numbers"):
        assert bool(table.loc[check, "pass"]), (check, table.loc[check, "value"])
    draws = LG.read_table(out / "p", "simulation_draws")
    sc = A.scenario_contrasts(draws, outcomes=["G", "unaided"], years=(1,))
    assert set(sc["scenario"]) == {"scaffolding_rapid", "scaffolding_nofade", "substitution", "free_choice",
                                   "free_choice_centaur"}
    assert (sc["n"] == 3).all() and {"lo90", "hi95", "prsup"} <= set(sc.columns)
    neural = A.neural_contrasts_table(LG.read_table(out / "p", "neural_contrasts"), years=(1,))
    assert len(neural) == 5 * 7


def test_z_permutations_and_the_post_hoc_contrast_are_exact():
    rng = np.random.default_rng(0)
    Z = rng.normal(size=(30 * 3, 6))
    U = A.permute_z(Z, "units", rng).reshape(30, 3, 6)
    blocks = Z.reshape(30, 3, 6)
    for u in range(30):  # a derangement: every unit gets another unit's patterns, conditions stay aligned
        src = [v for v in range(30) if np.array_equal(U[u], blocks[v])]
        assert len(src) == 1 and src[0] != u
    C = A.permute_z(Z, "conditions", rng).reshape(30, 3, 6)
    for u in range(30):
        assert sorted(map(tuple, C[u])) == sorted(map(tuple, blocks[u])) and not np.array_equal(C[u], blocks[u])
    # the post hoc mean contrast equals the mean of per-learner network contrasts (linearity of N in the accumulators)
    from neurotutorsim import plasticity as P

    acc_a, acc_b = rng.random((50, 5, 90)), rng.random((50, 5, 90))
    w, W = np.array([0.3, 0.3, 0.0, 0.4, -0.2]), rng.random((7, 6))
    per_learner = P.network_state(P.neural_state(acc_a, w, Z), W) - P.network_state(P.neural_state(acc_b, w, Z), W)
    assert np.allclose(A.network_contrast((acc_a - acc_b).mean(axis=0)[None], w, Z, W)[0], per_learner.mean(axis=0))


def test_z_controls_and_sign_flips_on_a_tiny_run(tmp_path, units, cfg):
    for folder in ("config", "data/units", "stimuli"):
        shutil.copytree(ROOT / folder, tmp_path / folder)
    write_fake_tribe(tmp_path / "data" / "tribe" / "tribe_main", list(units))
    write_fake_rule(tmp_path)
    assert LG.main(["--config", str(tmp_path / "config" / "default.yaml"), "--years", "1", "--learners", "60",
                    "--draws", "3", "--tag", "c", "--scenarios", "traditional", "substitution"]) == 0
    run = tmp_path / "data" / "processed" / "phase5" / "c"
    zc = A.z_controls(run, cfg, tmp_path, n_perm=20)
    assert len(zc) == 7 and set(zc["scenario"]) == {"substitution"}
    assert zc["permuted_units_median_ratio"].between(0, 1e6).all() and zc["permuted_units_share_as_large"].between(0, 1).all()
    # the main contrast reproduces the in-run neural contrast for mechanism D (mean over draws)
    neural = LG.read_table(run, "neural_contrasts").query("mechanism == 'D' and draw_id >= 0")
    in_run = neural.groupby("network")["mean"].mean()
    assert np.allclose(zc.set_index("network")["main_contrast"].reindex(in_run.index), in_run, atol=1e-9)
    flips = A.sign_flip_null(LG.read_table(run, "yearly_subsample"), "unaided", n_perm=200)
    assert len(flips) == 1 and abs(flips["null_mean"].iloc[0]) < 3 * flips["null_sd"].iloc[0] / np.sqrt(200) + 1e-9


def test_falsification_verdicts_on_constructed_inputs():
    t_plain = pd.DataFrame({"level": "network", "metric": "auc", "key": ["Cont", "Vis"], "contrast": "S-T",
                            "ci_excludes_0": [True, True]})
    t_cov = t_plain.assign(ci_excludes_0=[True, False])  # Vis disappears once duration and words are covariates
    shuffle = pd.DataFrame({"metric": "auc", "control": "sentence", "key": ["Cont", "Vis"], "ratio_shuffle_to_contrast": [0.2, 1.5]})
    draws = pd.DataFrame([{"draw_id": b, "year": 10, "kind": "contrast", "scenario": s, "outcome": o, "estimate": v + 0.001 * b}
                          for b in range(40) for s, o, v in (("scaffolding_nofade", "unaided", 0.05), ("substitution", "unaided", -0.05),
                                                             ("scaffolding_nofade", "far", 0.01), ("substitution", "far", 0.01))]
                         + [{"draw_id": b, "year": 10, "kind": "level", "scenario": "traditional", "outcome": "near_bound_share",
                             "estimate": 0.02} for b in range(40)])
    neural = pd.DataFrame([{"draw_id": b, "year": 10, "scenario": "substitution", "network": "Cont", "mechanism": m,
                            "d": (-1 if m == "B" else 1) * 0.3} for b in range(5) for m in "ABCD"])
    zc = pd.DataFrame({"year": 10, "scenario": "substitution", "network": ["Cont", "Vis"],
                       "permuted_units_median_ratio": [0.1, 0.7], "permuted_conditions_median_ratio": [0.2, 0.1]})
    f = A.falsification(t_plain, t_cov, shuffle, draws, neural, zc).set_index(f"criterion")["verdict"]
    assert f.filter(like="F1").iloc[0].startswith("no claim for 1")
    assert f.filter(like="F2").iloc[0].startswith("not assessable")
    assert f.filter(like="F3").iloc[0].startswith("no claim for 1"), "mechanism B reverses the sign"
    assert f.filter(like="F4").iloc[0] == "claim allowed"
    assert f.filter(like="F5").iloc[0].startswith("no claim for 1")
    assert f.filter(like="F6").iloc[0] == "no claim for far", "far transfer does not separate scaffolding from substitution"

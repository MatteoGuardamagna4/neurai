import shutil

import numpy as np
import pandas as pd
import pytest

from neurotutorsim import analysis as A, longitudinal as LG
from neurotutorsim.corpus import CONDITIONS
from tests.conftest import ROOT
from tests.test_plasticity import write_fake_tribe


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
    base = ["--config", str(tmp_path / "config" / "default.yaml"), "--years", "1", "--learners", "300", "--draws", "3"]
    assert LG.main(base + ["--tag", "p"]) == 0
    assert LG.main(base + ["--tag", "z", "--zero-plasticity"]) == 0
    assert LG.main(base + ["--tag", "e", "--zero-effort"]) == 0
    assert LG.main(base + ["--tag", "c", "--set", "phase5.scenarios.traditional_copy={protocol: traditional, policy: persistent}"]) == 0
    out = tmp_path / "data" / "processed" / "phase5"
    table = A.gate18(out / "p", out / "z", out / "e", out / "c", run_t1=False).set_index("check")
    assert len(table) == 9 and table["pass"].map(lambda v: isinstance(v, (bool, np.bool_))).all()
    for check in ("G2 difficulty lowers accuracy", "G3 support helps", "G6 zero plasticity", "G8 common random numbers"):
        assert bool(table.loc[check, "pass"]), (check, table.loc[check, "value"])
    draws = LG.read_table(out / "p", "simulation_draws")
    sc = A.scenario_contrasts(draws, outcomes=["G", "unaided"], years=(1,))
    assert set(sc["scenario"]) == {"scaffolding_rapid", "scaffolding_nofade", "substitution", "free_choice"}
    assert (sc["n"] == 3).all() and {"lo90", "hi95", "prsup"} <= set(sc.columns)
    neural = A.neural_contrasts_table(LG.read_table(out / "p", "neural_contrasts"), years=(1,))
    assert len(neural) == 4 * 7

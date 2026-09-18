import shutil

import numpy as np
import pytest

from neurotutorsim import choice_rule as CR, simulate
from tests.conftest import ROOT


def test_design_encodes_what_centaur_reads():
    last = np.array([[2, 2, 0], [-1, -1, -1]])
    uses = np.array([[3, 0, 5], [0, 0, 0]], float)
    wins = np.array([[3, 0, 1], [0, 0, 0]], float)
    X = CR.design(last, uses, wins, np.array([0.8, 0.5]))
    f = {name: i for i, name in enumerate(CR.FEATURES)}
    assert X[0, :, f["habit"]] == pytest.approx([1 / 3, 0, 2 / 3])
    assert X[0, :, f["payoff"]] == pytest.approx([(3 + 1) / (3 + 2) - 0.5, 0.0, (1 + 1) / (5 + 2) - 0.5])
    assert X[0, :, f["tried"]].tolist() == [1, 0, 1]
    assert X[0, 2, f["form_x_substitution"]] == pytest.approx(0.3) and X[0, 0, f["form_x_substitution"]] == 0
    assert not X[1, :, 2:].any(), "a first decision has no habit, payoff or form signal beyond the intercepts"
    assert X[:, 1, f["scaffolding"]].tolist() == [1, 1] and X[:, 2, f["substitution"]].tolist() == [1, 1]


def test_fit_recovers_known_parameters_within_bootstrap_error():
    rng = np.random.default_rng(0)
    n = 12000
    last = rng.integers(-1, 3, (n, CR.HABIT_WINDOW))
    uses = rng.integers(0, 8, (n, 3)).astype(float)
    wins = np.floor(uses * rng.random((n, 3)))
    X = CR.design(last, uses, wins, rng.random(n))
    truth = np.array([-0.4, 0.6, 1.5, 2.0, -0.3, 0.8, -1.0])
    P = CR.probabilities(truth, X)
    assert CR.fit(X, P, ridge=0.0) == pytest.approx(truth, abs=1e-3), "soft labels equal to the truth: exact recovery"
    Y = np.eye(3)[[rng.choice(3, p=p) for p in P]]  # hard picks: recovery up to sampling error
    est = CR.fit(X, Y)
    boot = CR.bootstrap(X, Y, np.repeat(np.arange(n // 40), 40), n_boot=80, seed=1)
    sd = boot.std(axis=0, ddof=1)
    assert np.all(sd > 0) and np.all(np.abs(est - truth) < 4 * sd), (est, truth, sd)
    ev = CR.evaluate(est, X, Y, {"constant": np.tile(Y.mean(axis=0), (n, 1))})
    assert ev["cross_entropy"] < ev["cross_entropy_constant"]


def test_softmax_in_d_matches_the_logistic_engine_rule():
    q = CR.softmax_in_d(np.array([0.5, 1.0]), 2.0)
    assert q[0] == pytest.approx([1 / 3] * 3)
    assert q[1, 2] > q[1, 1] > q[1, 0]


def test_decisions_reconstruct_the_state_before_each_pick(tmp_path):
    for folder in ("config", "data/units", "stimuli"):
        shutil.copytree(ROOT / folder, tmp_path / folder)
    assert simulate.main(["--config", str(tmp_path / "config" / "default.yaml"), "--engine", "logistic", "--tutor", "fake",
                          "--learners", "3", "--episodes", "8", "--conditions", "free_choice"]) == 0
    df = CR.decisions(tmp_path / "data" / "processed" / "logistic")
    assert len(df) == 3 * 8 and not df["has_probabilities"].any(), "the logistic engine logs no Centaur probabilities"
    for _, g in df.groupby("learner_id"):
        g = g.sort_values("episode")
        picks = g["pick"].tolist()
        for i, (_, row) in enumerate(g.iterrows()):
            assert row["uses"].tolist() == [picks[:i].count(a) for a in range(3)]
            expected_last = (picks[:i][-3:] + [-1, -1, -1])[:3] if i < 3 else picks[i - 3:i]
            assert list(row["last_picks"]) == expected_last
            assert 0.0 <= row["recent_rate"] <= 1.0
    X, Y, groups = CR.arrays(df)
    assert X.shape == (24, 3, len(CR.FEATURES)) and np.allclose(Y.sum(axis=1), 1) and len(set(groups)) == 3

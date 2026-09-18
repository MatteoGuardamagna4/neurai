import shutil

import numpy as np
import pandas as pd
import pytest

from neurotutorsim import corpus, plasticity as P, simulate, tribe
from tests.conftest import ROOT

PCFG = {"eta": 1.0, "lambda": {"A": 0.5, "PE": 0.3, "R": 0.2}, "lambda_O": 0.25}


def write_fake_tribe(tribe_dir, units, n_parcels=8, seed=0):
    """A synthetic TRIBE run: parcel AUC for every stimulus, parcels over the 7 networks, no model."""
    rng = np.random.default_rng(seed)
    rows = []
    for u in sorted(units):
        for c in corpus.CONDITIONS:
            for p in range(1, n_parcels + 1):
                for metric in ("auc", "mean"):
                    rows.append({"stimulus_id": f"{u}_{c}", "unit_id": u, "condition": c, "level": "parcel",
                                 "key": str(p), "metric": metric, "value": float(rng.normal(10, 3))})
    (tribe_dir / "wpm220").mkdir(parents=True)
    pd.DataFrame(rows).to_parquet(tribe_dir / "wpm220" / "tribe_metrics.parquet", index=False)
    nets = [tribe.NETWORKS[i % 7] for i in range(n_parcels)]
    pd.DataFrame({"parcel_id": range(1, n_parcels + 1), "parcel_name": [f"p{i}" for i in range(n_parcels)],
                  "hemi": "left", "network": nets, "n_vertices": 10, "area": rng.uniform(100, 400, n_parcels)}
                 ).to_csv(tribe_dir / "parcels_schaefer400.csv", index=False)


def write_fake_rule(root, params=(-0.25, 0.08, 0.87, 0.15, 0.26, -0.15, 0.07), n_boot=5, seed=0):
    """A choice_rule.json like `choice_rule.fit_rule` writes, for scenarios that use the Centaur-calibrated rule."""
    import json

    from neurotutorsim import choice_rule as CR

    rng = np.random.default_rng(seed)
    boot = (np.asarray(params) + rng.normal(0, 0.05, (n_boot, len(params)))).tolist()
    path = root / "data" / "processed" / "choice_rule" / "choice_rule.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"features": list(CR.FEATURES), "params": list(params), "bootstrap": boot}), encoding="utf-8")
    return path


def test_standardize_is_eq28_then_global_winsorising():
    A = np.random.default_rng(1).normal(5, 2, (90, 6))
    Z = P.standardize(A, winsorize=None)
    assert np.allclose(Z.mean(axis=0), 0) and np.allclose(Z.std(axis=0, ddof=1), 1)
    Zw = P.standardize(A, winsorize=(0.05, 0.95))
    lo, hi = np.quantile(Z, [0.05, 0.95])
    assert Zw.min() == pytest.approx(lo) and Zw.max() == pytest.approx(hi)
    assert np.all(Zw[(Z > lo) & (Z < hi)] == Z[(Z > lo) & (Z < hi)])


def test_load_z_and_networks(tmp_path, units):
    write_fake_tribe(tmp_path, list(units))
    Z, keys, ids = P.load_z(tmp_path, 220, "auc", (0.01, 0.99))
    assert Z.shape == (90, 8) and ids.tolist() == list(range(1, 9))
    assert keys[:3] == [(sorted(units)[0], c) for c in corpus.CONDITIONS], "unit-major, CONDITIONS order"
    assert P.stimulus_index([keys[4][0]], [keys[4][1]], sorted(units)).tolist() == [4]
    W, nets = P.load_networks(tmp_path, "area")
    assert W.shape == (7, 8) and nets == list(tribe.NETWORKS) and np.allclose(W.sum(axis=1), 1)
    # eq. 7 agrees with the tribe module on the same parcels
    table = pd.read_csv(tmp_path / "parcels_schaefer400.csv")
    N = np.random.default_rng(2).normal(size=(5, 8))
    expected, enets = tribe.aggregate_networks(N, table, "area")
    assert enets == nets and np.allclose(P.network_state(N, W), expected)
    We, _ = P.load_networks(tmp_path, "equal")
    assert np.allclose(We[0, table.network == "Vis"], 1 / (table.network == "Vis").sum())


def test_lazy_accumulator_equals_the_eager_recursion():
    rng = np.random.default_rng(3)
    n, S, T = 6, 9, 40
    acc = P.Accumulator(n, S)
    eager = np.zeros((n, 5, S))
    for t in range(T):
        k, x, decay = rng.integers(0, S, n), rng.random((n, 5)), 0.05
        eager *= 1 - decay
        eager[np.arange(n), :, k] += x
        acc.step(k, x, decay)
        if t == 20:  # a break, and the yearly renormalisation
            eager *= 0.7
            acc.apply_decay(0.7)
            acc.renormalise()
            assert acc.scale == 1.0
    assert np.allclose(acc.values(), eager, atol=1e-6)


def test_mechanisms_match_the_brief_equations_and_zero_plasticity_is_exactly_zero():
    rng = np.random.default_rng(4)
    n, S, Pn, T = 4, 6, 5, 25
    Z = rng.normal(size=(S, Pn))
    acc = P.Accumulator(n, S)
    N = {m: np.zeros((n, Pn)) for m in P.MECHANISMS}
    d = 0.1
    for _ in range(T):
        k = rng.integers(0, S, n)
        E, pe, res, retr, off = rng.random(n), rng.random(n), rng.integers(0, 2, n), rng.choice([0.5, 1.0], n), rng.random(n)
        acc.step(k, P.channel_values(E, pe, res, retr, off), d)
        z = Z[k]  # eq. 29, 31, 32, 33 written out
        N["A"] = (1 - d) * N["A"] + (PCFG["eta"] * E)[:, None] * z
        N["B"] = (1 - d) * N["B"] + (PCFG["eta"] * pe * res)[:, None] * z
        N["C"] = (1 - d) * N["C"] + (PCFG["eta"] * E * retr)[:, None] * z
        lam = PCFG["lambda"]
        N["D"] = (1 - d) * N["D"] + (lam["A"] * E + lam["PE"] * pe * res + lam["R"] * retr - PCFG["lambda_O"] * off)[:, None] * z
    values = acc.values()
    for m in P.MECHANISMS:
        assert np.allclose(P.neural_state(values, P.mechanism_weights(m, PCFG), Z), N[m], atol=1e-5), m
    zero = {**PCFG, "eta": 0.0}  # the zero-plasticity control: eta = 0 zeroes every mechanism, D included (A6)
    for m in P.MECHANISMS:
        assert not P.neural_state(values, P.mechanism_weights(m, zero), Z).any()
    with pytest.raises(ValueError):
        P.mechanism_weights("D", {**PCFG, "lambda": {"A": 0.5, "PE": 0.5, "R": 0.5}})


def test_network_outcomes():
    uniform = np.ones((2, 400))
    single = np.zeros((1, 400))
    single[0, 7] = 3.0
    assert np.allclose(P.concentration(uniform), 0.25) and P.concentration(single)[0] == 1.0
    assert np.isnan(P.concentration(np.zeros((1, 400))))[0]
    # integration from running sums equals the mean |covariance| of the series
    rng = np.random.default_rng(5)
    x = rng.normal(size=(3, 50, 7))  # learners x episodes x networks
    sum_x, sum_xx = x.sum(axis=1), np.einsum("nti,ntj->nij", x, x)
    cov = np.array([np.cov(x[i].T, bias=True) for i in range(3)])
    iu = np.triu_indices(7, 1)
    assert np.allclose(P.integration(sum_x, sum_xx, 50), np.abs(cov[:, iu[0], iu[1]]).mean(axis=1))
    eff = P.efficiency(np.array([0.3, 0.6, 0.8]), np.array([2.0, 2.0, 0.0]))
    assert np.isnan(eff[0]) and eff[1] == pytest.approx(0.3) and np.isnan(eff[2])
    far = rng.random(30)
    Nn = np.column_stack([far * 2 + 1, -far, rng.random(30)])
    al = P.alignment(Nn, far)
    assert al[0] == pytest.approx(1.0) and al[1] == pytest.approx(-1.0) and abs(al[2]) < 1
    # eq. 34 per learner on toy patterns: two concepts with identical within-concept patterns differentiate fully
    units = ["a1", "a2", "b1", "b2"]
    Z = np.zeros((12, 3))
    for i, u in enumerate(units):
        Z[i * 3: i * 3 + 3, 0 if u[0] == "a" else 1] = 1.0
    values = np.ones((2, 5, 12))
    diff = P.differentiation(values, P.mechanism_weights("A", PCFG), Z, units, ["a", "a", "b", "b"])
    # d = 1 - corr: 0 within a concept (identical patterns); the centred one-hot patterns of the two
    # concepts correlate at -0.5 over three parcels, so between = 1.5
    assert diff.shape == (2,) and np.allclose(diff, 1.5)


def test_apply_to_run_on_a_small_logistic_run(tmp_path, units):
    for folder in ("config", "data/units", "stimuli"):
        shutil.copytree(ROOT / folder, tmp_path / folder)
    write_fake_tribe(tmp_path / "data" / "tribe" / "tribe_main", list(units))
    args = ["--config", str(tmp_path / "config" / "default.yaml"), "--engine", "logistic", "--tutor", "fake",
            "--learners", "3", "--episodes", "4"]
    assert simulate.main(args) == 0
    processed = tmp_path / "data" / "processed" / "logistic"
    cfg = simulate.load_config(tmp_path / "config" / "default.yaml")
    cfg["checkpoints"]["episodes"] = [1]
    meta = P.apply_to_run(processed, cfg, tmp_path, subsample_learners=2)
    net = pd.read_parquet(processed / "neural_network.parquet")
    assert len(net) == 3 * 4 * 4 * 7 * 4 == meta["rows"]["neural_network"]  # learners x episodes x arms x networks x mechanisms
    assert set(net.columns) >= {"learner_id", "condition", "protocol", "time", "network", "mechanism", "state_value", "parameter_draw"}
    assert not net.duplicated(["learner_id", "condition", "time", "network", "mechanism"]).any()
    parcels = pd.read_parquet(processed / "neural_state.parquet")
    assert len(parcels) == 2 * 4 * 2 * 8 * 4  # subsample x arms x checkpoints {1, 3} x parcels x mechanisms
    assert set(parcels.columns) >= {"learner_id", "time", "parcel_id", "state_value", "mechanism", "parameter_draw"}
    # the network table is the eq. 7 aggregate of the parcel table at a checkpoint
    W, nets = P.load_networks(tmp_path / "data" / "tribe" / "tribe_main", "area")
    row = parcels.query("learner_id == 0 and condition == 'traditional' and time == 3 and mechanism == 'D'").sort_values("parcel_id")
    expected = P.network_state(row["state_value"].to_numpy()[None, :], W)[0]
    got = net.query("learner_id == 0 and condition == 'traditional' and time == 3 and mechanism == 'D'").set_index("network")["state_value"]
    assert np.allclose(got.reindex(nets).to_numpy(), expected)
    assert (processed / "plasticity.json").exists()
    assert P.main(["--config", str(tmp_path / "config" / "default.yaml"), "--run", str(processed), "--subsample", "1"]) == 0

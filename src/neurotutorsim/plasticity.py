"""Phase IV: model-implied functional adaptation (brief §8), post hoc on any Phase III run and in the Phase V step.

    python -m neurotutorsim.plasticity --run data/processed/population_logistic

Design (PLAN.md S5): N depends on the TRIBE patterns only linearly, and the 90 patterns (30 units x 3
protocols) are fixed, so a learner carries five decayed accumulators per stimulus, one per behavioural channel
(E, PE x Resolution, E x Retrieval, Retrieval, Offloading), A[j, k] <- (1 - delta_N) A[j, k] + x_j 1[k = k_t].
Every mechanism is then N = (w . A) @ Z, so the mechanism (eq. 29-33), the lambdas, the reading speed, the TRIBE
metric, the winsorising, the network weights and every Z control (permuted units, permuted conditions, unit
bootstrap) are post hoc: no rerun. Only delta_N lives inside the accumulator. N is in arbitrary units and is
never a predicted brain state (brief §15): it is standardised predicted-response mass, accumulated and decayed.
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd

from .corpus import CONDITIONS
from .tribe import NETWORKS, differentiation as _differentiation

CHANNELS = ("E", "PE_res", "E_retr", "retr", "off")  # accumulator channels, in this order
MECHANISMS = ("A", "B", "C", "D")
TOP_QUARTILE = 0.25  # §8.7 functional concentration: share of |N| in the top quartile of parcels


# ------------------------------------------------------------------ eq. 28: standardised TRIBE patterns
def standardize(A: np.ndarray, winsorize=(0.01, 0.99)) -> np.ndarray:
    """eq. 28 per column (ddof = 1), then clipped at the global percentiles of the whole Z matrix (§8.2,
    ASSUMPTION A7: global, not per parcel); `winsorize=None` keeps the unwinsorised values."""
    A = np.asarray(A, dtype=np.float64)
    Z = (A - A.mean(axis=0)) / A.std(axis=0, ddof=1)
    if winsorize:
        lo, hi = np.quantile(Z, list(winsorize))
        Z = np.clip(Z, lo, hi)
    return Z


def load_z(tribe_dir: Path, wpm: int = 220, metric: str = "auc", winsorize=(0.01, 0.99)
           ) -> tuple[np.ndarray, list[tuple[str, str]], np.ndarray]:
    """(Z (90, P), keys [(unit_id, condition)] sorted by unit_id x CONDITIONS, parcel_ids) from
    `<tribe_dir>/wpm<wpm>/tribe_metrics.parquet` (level `parcel`, the chosen metric)."""
    return z_from_metrics(pd.read_parquet(Path(tribe_dir) / f"wpm{wpm}" / "tribe_metrics.parquet"), metric, winsorize)


def z_from_metrics(m: pd.DataFrame, metric: str = "auc", winsorize=(0.01, 0.99)
                   ) -> tuple[np.ndarray, list[tuple[str, str]], np.ndarray]:
    """`load_z` on a metrics table already in memory (e.g. one reworded version of the corpus)."""
    m = m[(m["level"] == "parcel") & (m["metric"] == metric)]
    if m.empty:
        raise ValueError(f"no parcel-level {metric!r} rows")
    wide = m.pivot_table(index=["unit_id", "condition"], columns="key", values="value")
    units = sorted(wide.index.get_level_values("unit_id").unique())
    rows = pd.MultiIndex.from_product([units, list(CONDITIONS)], names=["unit_id", "condition"])
    wide = wide.reindex(rows)
    if wide.isna().any().any():
        raise ValueError("every unit needs a parcel pattern for all three conditions")
    parcel_ids = np.array(sorted(int(k) for k in wide.columns))
    A = wide[[str(p) for p in parcel_ids]].to_numpy(np.float64)
    return standardize(A, winsorize), [tuple(r) for r in rows], parcel_ids


def load_networks(tribe_dir: Path, weights: str = "area") -> tuple[np.ndarray, list[str]]:
    """eq. 7 as a row-normalised (n_networks, P) matrix from `parcels_schaefer400.csv`, parcels sorted by id
    (the column order of `load_z`); `weights` = `area` (main) or `equal` (robustness)."""
    table = pd.read_csv(Path(tribe_dir) / "parcels_schaefer400.csv").sort_values("parcel_id")
    if weights not in ("area", "equal"):
        raise ValueError("weights must be 'area' or 'equal'")
    w = table["area"].to_numpy(float) if weights == "area" else np.ones(len(table))
    nets = [n for n in NETWORKS if n in set(table["network"])] + sorted(set(table["network"]) - set(NETWORKS))
    W = np.zeros((len(nets), len(table)))
    for i, n in enumerate(nets):
        sel = (table["network"] == n).to_numpy()
        W[i, sel] = w[sel] / w[sel].sum()
    return W, nets


def stimulus_index(unit_ids, protocols, units: list[str]) -> np.ndarray:
    """Row of Z for each (unit, protocol): unit position x 3 + condition position, matching `load_z` keys."""
    upos = {u: i for i, u in enumerate(units)}
    cpos = {c: i for i, c in enumerate(CONDITIONS)}
    return np.array([upos[u] * len(CONDITIONS) + cpos[p] for u, p in zip(unit_ids, protocols)], dtype=np.int64)


def decay_per_episode(half_life_weeks: float, episodes_per_week: float) -> float:
    """delta_N per episode from a half-life in weeks: (1 - delta) ** (half_life x episodes_per_week) = 1/2."""
    return 1.0 - 0.5 ** (1.0 / (float(half_life_weeks) * float(episodes_per_week)))


# ------------------------------------------------------------------ the accumulator
class Accumulator:
    """Per learner, channel and stimulus: A <- (1 - delta) A + x 1[k = k_t], with the decay applied lazily as
    one global scale so a step costs one scatter-add. `renormalise()` folds the scale back in (once a year)."""

    def __init__(self, n_learners: int, n_stimuli: int, dtype=np.float32):
        self.acc = np.zeros((n_learners, len(CHANNELS), n_stimuli), dtype=dtype)
        self.scale = 1.0
        self.rows = np.arange(n_learners)

    def apply_decay(self, factor: float) -> None:
        self.scale *= float(factor)

    def step(self, k: np.ndarray, values: np.ndarray, decay: float) -> None:
        """`k` (n,) stimulus row per learner, `values` (n, 5) channel inputs of this episode."""
        self.apply_decay(1.0 - decay)
        self.acc[self.rows, :, np.asarray(k)] += np.asarray(values, dtype=self.acc.dtype) / self.scale

    def renormalise(self) -> None:
        self.acc *= self.scale
        self.scale = 1.0

    def values(self) -> np.ndarray:
        return self.acc.astype(np.float64) * self.scale


def channel_values(effort, pe, resolution, retrieval, offloading) -> np.ndarray:
    """The (n, 5) channel inputs of one episode from the learner_state proxies."""
    E, pe, res, retr, off = (np.asarray(x, dtype=np.float64) for x in (effort, pe, resolution, retrieval, offloading))
    return np.column_stack([E, pe * res, E * retr, retr, off])


def mechanism_weights(name: str, pcfg: dict) -> np.ndarray:
    """Channel weights of eq. 29 (A), 31 (B), 32 (C) and 33 (D) over (E, PE x Res, E x Retr, Retr, Off)."""
    eta, lam = float(pcfg["eta"]), pcfg["lambda"]
    if name == "A":
        return np.array([eta, 0.0, 0.0, 0.0, 0.0])
    if name == "B":
        return np.array([0.0, eta, 0.0, 0.0, 0.0])
    if name == "C":
        return np.array([0.0, 0.0, eta, 0.0, 0.0])
    if name == "D":
        pos = np.array([lam["A"], lam["PE"], lam["R"]], dtype=float)
        if (pos < 0).any() or abs(pos.sum() - 1.0) > 1e-6:
            raise ValueError("eq. 33 lambdas must be non-negative and sum to one")
        # eq. 33 has no eta; A6 makes it the common scale of every mechanism, so eta = 0 is the zero-plasticity control for D too
        return eta * np.array([lam["A"], lam["PE"], 0.0, lam["R"], -float(pcfg["lambda_O"])])
    raise ValueError(f"unknown mechanism {name!r}")


def neural_state(values: np.ndarray, w: np.ndarray, Z: np.ndarray) -> np.ndarray:
    """N (n, P) = (w . A) @ Z for accumulator values (n, 5, S) and patterns Z (S, P)."""
    return np.einsum("c,ncs->ns", np.asarray(w, dtype=np.float64), values) @ Z


def network_state(N: np.ndarray, W: np.ndarray) -> np.ndarray:
    """(n, n_networks) from parcel states (n, P) and the eq. 7 weights (n_networks, P)."""
    return N @ W.T


# ------------------------------------------------------------------ §8.7 network-level outcomes
def concentration(N: np.ndarray) -> np.ndarray:
    """Share of sum |N_p| held by the top quartile of parcels, per learner (uniform -> 0.25, one parcel -> 1)."""
    a = np.sort(np.abs(np.asarray(N, dtype=np.float64)), axis=1)[:, ::-1]
    top = max(1, int(round(TOP_QUARTILE * a.shape[1])))
    total = a.sum(axis=1)
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(total > 0, a[:, :top].sum(axis=1) / total, np.nan)


def differentiation(values: np.ndarray, w: np.ndarray, Z: np.ndarray, units: list[str], concepts) -> np.ndarray:
    """eq. 34 per learner: the per-unit state pattern sums the three protocol rows of the unit, then
    `tribe.differentiation` on the (n_units, P) matrix. O(n x units x P): run on a subsample."""
    a = np.einsum("c,ncs->ns", np.asarray(w, dtype=np.float64), values)  # (n, S)
    per_unit = a.reshape(a.shape[0], len(units), len(CONDITIONS))  # S = units x conditions, unit-major
    Zu = Z.reshape(len(units), len(CONDITIONS), -1)
    patterns = np.einsum("nuc,ucp->nup", per_unit, Zu)
    return np.array([_differentiation(patterns[i], concepts)["differentiation"] for i in range(len(patterns))])


def integration(sum_x: np.ndarray, sum_xx: np.ndarray, count: int) -> np.ndarray:
    """Cross-network integration: mean |covariance| over the network pairs, from running sums of the
    network states across episodes (sum_x (n, N), sum_xx (n, N, N))."""
    mean = sum_x / count
    cov = sum_xx / count - mean[:, :, None] * mean[:, None, :]
    iu = np.triu_indices(sum_x.shape[1], 1)
    return np.abs(cov[:, iu[0], iu[1]]).mean(axis=1)


def efficiency(unaided: np.ndarray, N_cont: np.ndarray, floor: float = 0.40) -> np.ndarray:
    """Unaided accuracy per |control-network state|, NaN unless performance is non-trivial (A14)."""
    unaided, N_cont = np.asarray(unaided, float), np.asarray(N_cont, float)
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where((unaided > floor) & (np.abs(N_cont) > 0), unaided / np.abs(N_cont), np.nan)


def alignment(N_net: np.ndarray, far: np.ndarray) -> np.ndarray:
    """Pearson correlation across learners between each network's state and far-transfer performance."""
    x, y = np.asarray(N_net, float), np.asarray(far, float)
    xc, yc = x - x.mean(axis=0), y - y.mean()
    with np.errstate(invalid="ignore", divide="ignore"):
        return (xc * yc[:, None]).sum(axis=0) / np.sqrt((xc ** 2).sum(axis=0) * (yc ** 2).sum())


# ------------------------------------------------------------------ post hoc on a Phase III run
def apply_to_run(processed: Path, cfg: dict, root: Path | None = None, subsample_learners: int = 100) -> dict:
    """Phase IV on `learner_state.parquet`: every episode's network state for mechanisms A-D
    (`neural_network.parquet`) and the parcel-level state of the first `subsample_learners` learners per
    condition at the checkpoint episodes (`neural_state.parquet`, brief §4.2 columns). Learners of one
    condition are advanced together, one episode at a time, because the accumulator step is a scatter-add."""
    p = cfg["plasticity"]
    tribe_dir = Path(p["tribe_dir"]) if root is None else Path(root) / p["tribe_dir"]
    Z, keys, parcel_ids = load_z(tribe_dir, int(p["wpm"]), p["metric"], p["winsorize"])
    W, nets = load_networks(tribe_dir, p["network_weights"])
    units = sorted({u for u, _ in keys})
    decay = decay_per_episode(p["half_life_weeks"], cfg["calendar"]["episodes_per_week"])
    weights = {m: mechanism_weights(m, p) for m in MECHANISMS}
    state = pd.read_parquet(Path(processed) / "learner_state.parquet")
    checkpoints = set(int(e) for e in cfg["checkpoints"]["episodes"]) | {int(state["time"].max())}
    draw = cfg.get("parameter_setting", "medium")
    net_parts, parcel_parts = [], []  # column arrays per (condition, time, mechanism), assembled once at the end
    for condition, g in state.groupby("condition", sort=True):
        g = g.sort_values(["time", "learner_id"])
        learners = np.sort(g["learner_id"].unique())
        acc = Accumulator(len(learners), len(keys))
        sub = np.arange(min(subsample_learners, len(learners)))
        for t, e in g.groupby("time", sort=True):
            e = e.set_index("learner_id").reindex(learners)
            if e.isna().any().any():
                raise ValueError(f"{condition}: every learner needs an episode at time {t}")
            k = stimulus_index(e["unit_id"], e["protocol"], units)
            acc.step(k, channel_values(e["effort"], e["pe"], e["resolution"], e["retrieval"], e["offloading"]), decay)
            values = acc.values()
            protocols = e["protocol"].to_numpy()
            for m, w in weights.items():
                N = neural_state(values, w, Z)
                net_parts.append((condition, int(t), m, np.repeat(learners, len(nets)), np.repeat(protocols, len(nets)),
                                  np.tile(np.arange(len(nets)), len(learners)), network_state(N, W).ravel()))
                if int(t) in checkpoints:
                    parcel_parts.append((condition, int(t), m, np.repeat(learners[sub], len(parcel_ids)),
                                         np.tile(parcel_ids, len(sub)), N[sub].ravel()))

    def column(parts, i, dtype=None):
        return np.concatenate([np.full(len(x[3]), x[i]) if np.ndim(x[i]) == 0 else x[i] for x in parts]).astype(dtype) \
            if dtype else np.concatenate([np.full(len(x[3]), x[i]) if np.ndim(x[i]) == 0 else x[i] for x in parts])

    network = pd.DataFrame({
        "learner_id": column(net_parts, 3, np.int32), "condition": pd.Categorical(column(net_parts, 0)),
        "protocol": pd.Categorical(column(net_parts, 4)), "time": column(net_parts, 1, np.int16),
        "network": pd.Categorical.from_codes(column(net_parts, 5, np.int8), categories=nets),
        "mechanism": pd.Categorical(column(net_parts, 2), categories=list(MECHANISMS)),
        "state_value": column(net_parts, 6, np.float32), "parameter_draw": draw})
    parcels = pd.DataFrame({
        "learner_id": column(parcel_parts, 3, np.int32), "condition": pd.Categorical(column(parcel_parts, 0)),
        "time": column(parcel_parts, 1, np.int16), "parcel_id": column(parcel_parts, 4, np.int16),
        "state_value": column(parcel_parts, 5, np.float32),
        "mechanism": pd.Categorical(column(parcel_parts, 2), categories=list(MECHANISMS)), "parameter_draw": draw})
    network.to_parquet(Path(processed) / "neural_network.parquet", index=False)
    parcels.to_parquet(Path(processed) / "neural_state.parquet", index=False)
    meta = {"tribe_dir": str(tribe_dir), "wpm": int(p["wpm"]), "metric": p["metric"], "winsorize": p["winsorize"],
            "network_weights": p["network_weights"], "half_life_weeks": p["half_life_weeks"],
            "decay_per_episode": decay, "n_parcels": int(len(parcel_ids)), "networks": nets,
            "rows": {"neural_network": int(len(network)), "neural_state": int(len(parcels))},
            "subsample_learners": subsample_learners, "recorded_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    (Path(processed) / "plasticity.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return meta


def main(argv=None) -> int:
    from .simulate import load_config

    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", default="config/default.yaml")
    ap.add_argument("--setting", choices=("low", "medium", "high"))
    ap.add_argument("--run", required=True, help="a Phase III output folder, e.g. data/processed/population_logistic")
    ap.add_argument("--subsample", type=int, default=100, help="learners per condition kept at parcel level")
    args = ap.parse_args(argv)
    cfg = load_config(Path(args.config), args.setting)
    started = time.time()
    meta = apply_to_run(Path(args.run), cfg, Path(args.config).resolve().parent.parent, args.subsample)
    print(json.dumps(meta["rows"]), f"in {time.time() - started:.0f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

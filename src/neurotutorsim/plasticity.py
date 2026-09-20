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
    files = sorted(Path(tribe_dir).glob("parcels_schaefer*.csv"))  # one atlas per run folder (400 main, 200 in the curve)
    if not files:
        raise FileNotFoundError(f"no parcels_schaefer*.csv in {tribe_dir}")
    table = pd.read_csv(files[0]).sort_values("parcel_id")
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
    with np.errstate(invalid="ignore", divide="ignore"):  # a unit not yet seen has a constant (zero) pattern
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


# ------------------------------------------------------------------ §8.7 outcomes on a finished run (post hoc)
def run_metrics(processed: Path, cfg: dict, root: Path | None = None, subsample: int = 100,
                mechanism: str = "D") -> tuple[pd.DataFrame, pd.DataFrame]:
    """The five derived §8.7 outcomes for one Phase III run, from the Phase IV tables it already wrote plus one
    cheap accumulator pass for eq. 34. Returns (learner-level, population-level).

    Concentration and the efficiency proxy come from `neural_state.parquet` / `neural_network.parquet` at the
    checkpoint episodes, integration from the whole episode series, differentiation from a fresh accumulator run
    over the first `subsample` learners per condition (the per-unit patterns are not stored), and alignment is one
    correlation across learners per condition and network. `mechanism` selects eq. 29-33; D is the main one (§8.6).

    Eq. 34 is NaN until a learner has met every unit at least once (an unseen unit has a constant pattern), so
    differentiation is reported at the last checkpoint of a run that covers the curriculum, not at the early ones.
    """
    processed = Path(processed)
    p = cfg["plasticity"]
    tribe_dir = Path(p["tribe_dir"]) if root is None else Path(root) / p["tribe_dir"]
    Z, keys, parcel_ids = load_z(tribe_dir, int(p["wpm"]), p["metric"], p["winsorize"])
    units = sorted({u for u, _ in keys})
    net = pd.read_parquet(processed / "neural_network.parquet", filters=[("mechanism", "==", mechanism)])
    nets = list(net["network"].cat.categories) if hasattr(net["network"], "cat") else sorted(net["network"].unique())
    rows = []

    # cross-network integration: mean |covariance| over network pairs, across every episode of the run
    for (condition,), g in net.groupby(["condition"], observed=True):
        g = g.sort_values(["learner_id", "time", "network"])
        learners = np.sort(g["learner_id"].unique())
        times = np.sort(g["time"].unique())
        x = g["state_value"].to_numpy(np.float64).reshape(len(learners), len(times), len(nets))
        integ = integration(x.sum(axis=1), np.einsum("ltn,ltm->lnm", x, x), len(times))
        rows.append(pd.DataFrame({"condition": condition, "learner_id": learners, "time": -1,
                                  "metric": "integration", "value": integ}))

    # concentration (parcel level) and the efficiency proxy / alignment (control network) at the checkpoints
    parcels = pd.read_parquet(processed / "neural_state.parquet", filters=[("mechanism", "==", mechanism)])
    for (condition, t), g in parcels.groupby(["condition", "time"], observed=True):
        w = g.pivot_table(index="learner_id", columns="parcel_id", values="state_value")
        rows.append(pd.DataFrame({"condition": condition, "learner_id": w.index.to_numpy(), "time": int(t),
                                  "metric": "concentration", "value": concentration(w.to_numpy())}))
    ck = pd.read_csv(processed / "checkpoints.csv") if (processed / "checkpoints.csv").exists() else pd.DataFrame()
    pop = []
    if len(ck):
        cont = net[net["network"] == "Cont"].rename(columns={"time": "checkpoint_episode"})
        m = ck.merge(cont[["condition", "learner_id", "checkpoint_episode", "state_value"]],
                     on=["condition", "learner_id", "checkpoint_episode"], how="inner")
        rows.append(pd.DataFrame({"condition": m["condition"], "learner_id": m["learner_id"],
                                  "time": m["checkpoint_episode"], "metric": "efficiency",
                                  "value": efficiency(m["unaided_accuracy_trained"], m["state_value"])}))
        last = int(ck["checkpoint_episode"].max())
        wide = net[net["time"] == last].pivot_table(index=["condition", "learner_id"], columns="network",
                                                    values="state_value", observed=True)
        far = ck[ck["checkpoint_episode"] == last].set_index(["condition", "learner_id"])["far_transfer_accuracy"]
        for condition, g in wide.groupby("condition", observed=True):
            y = far.reindex(g.index).to_numpy(float)
            pop.append(pd.DataFrame({"condition": condition, "network": list(g.columns), "time": last,
                                     "metric": "alignment", "value": alignment(g.to_numpy(float), y)}))

    # differentiation (eq. 34): one accumulator pass over a subsample, because per-unit patterns are not stored
    unit_csv = next((p for p in (processed.parent / "units.csv", tribe_dir / "units.csv") if p.exists()), None)
    concepts = (pd.read_csv(unit_csv).set_index("unit_id")["concept"].reindex(units).to_numpy() if unit_csv is not None
                else np.array([u.rsplit("_", 1)[0] for u in units]))  # unit ids are <concept>_<nnn> (data/CLAUDE.md)
    state = pd.read_parquet(processed / "learner_state.parquet")
    decay = decay_per_episode(p["half_life_weeks"], cfg["calendar"]["episodes_per_week"])
    w_mech = mechanism_weights(mechanism, p)
    checkpoints = sorted(set(int(e) for e in ck["checkpoint_episode"].unique())) if len(ck) else [int(state["time"].max())]
    for condition, g in state.groupby("condition", sort=True):
        learners = np.sort(g["learner_id"].unique())[:subsample]
        g = g[g["learner_id"].isin(learners)].sort_values(["time", "learner_id"])
        acc = Accumulator(len(learners), len(keys))
        for t, e in g.groupby("time", sort=True):
            e = e.set_index("learner_id").reindex(learners)
            acc.step(stimulus_index(e["unit_id"], e["protocol"], units),
                     channel_values(e["effort"], e["pe"], e["resolution"], e["retrieval"], e["offloading"]), decay)
            if int(t) in checkpoints:
                d = differentiation(acc.values(), w_mech, Z, units, concepts)
                rows.append(pd.DataFrame({"condition": condition, "learner_id": learners, "time": int(t),
                                          "metric": "differentiation", "value": d}))
    learner_level = pd.concat(rows, ignore_index=True)
    learner_level["mechanism"] = mechanism
    population = pd.concat(pop, ignore_index=True) if pop else pd.DataFrame(columns=["condition", "network", "time", "metric", "value"])
    population["mechanism"] = mechanism
    return learner_level, population


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

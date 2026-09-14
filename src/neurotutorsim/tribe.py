"""Phase II adapters for TRIBE v2 (brief §6): reading-time word events (eq. 4), parcel and network
aggregation (eq. 6-7), immediate neural metrics (eq. 8-9), condition contrasts (eq. 10-13) and
representational similarity (eq. 14, 34).

Pure numpy/pandas and deliberately model-free: nothing here loads or runs TRIBE. The notebook
`notebooks/tribe_phase2.ipynb` runs the model (Colab GPU) and hands each stimulus's (T_s x V) prediction
matrix to these functions, so everything downstream of the cached predictions is reproducible offline
and `uv run pytest tests/test_tribe.py` exercises all of it on synthetic arrays.

Conventions: a stimulus is one neuralset *timeline* named by its `stimulus_id`; time is seconds from
stimulus onset and TRIBE predicts one row per second (`time_index`); vertices are fsaverage5, left
hemisphere then right (the model's output order); a "word" for eq. 4 is one whitespace-delimited token.
"""
from __future__ import annotations

import math
import re
from pathlib import Path

import numpy as np
import pandas as pd

from .corpus import CONDITIONS, WORDS_PER_MINUTE, Stimulus

ROBUSTNESS_WPM = (180, 260)  # brief §6.2 robustness reading speeds
CONTRASTS = {  # eq. 10-12: name -> (minuend, subtrahend)
    "S-T": ("ai_scaffolding", "traditional"),
    "U-T": ("ai_substitution", "traditional"),
    "S-U": ("ai_scaffolding", "ai_substitution"),
}
NETWORKS = ("Vis", "SomMot", "DorsAttn", "SalVentAttn", "Limbic", "Cont", "Default")  # Yeo 7, Schaefer order
TR = 1.0  # seconds per predicted time point (TRIBE v2 release config: data.neuro.frequency = 1)


# ------------------------------------------------------------------ eq. 4: reading-time word events
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")


def sentences(text: str) -> list[str]:
    """Sentences of one section with boundaries preserved (§6.2): each line is split after `.`, `!` or `?`
    followed by whitespace, whitespace is normalised, and a line without terminal punctuation (a formula
    on its own line) is one sentence."""
    out: list[str] = []
    for line in text.splitlines():
        line = " ".join(line.split())
        if line:
            out.extend(s for s in _SENTENCE_END.split(line) if s)
    return out


def word_events(sections: dict[str, str], timeline: str, wpm: float = WORDS_PER_MINUTE,
                subject: str = "default") -> tuple[pd.DataFrame, pd.DataFrame]:
    """Reading-time events for one stimulus. eq. 4: onset_j = 60 * (words before j) / r, every token
    lasting 60 / r s, sections read back to back in the file's order.

    Returns (events, sections). `events` has one `Word` row per token with the fields neuralset's
    `AddContextToWords` reads (`sentence`, `sentence_char`, both exact by construction) and one `Text`
    row per section with its verbatim text; `sections` has each section's onset, offset and token count.
    """
    rows, secs, j, seq = [], [], 0, 0
    base = {"timeline": timeline, "subject": subject, "language": "english", "modality": "read"}
    for order, (name, text) in enumerate(sections.items()):
        first = j
        sents = sentences(text)
        for sentence in sents:
            pos = 0
            for token in sentence.split(" "):
                char = sentence.index(token, pos)
                rows.append({"type": "Word", "start": 60.0 * j / wpm, "duration": 60.0 / wpm, "text": token,
                             "sentence": sentence, "sentence_char": char, "sequence_id": seq, "section": name, **base})
                pos = char + len(token)
                j += 1
            seq += 1
        rows.append({"type": "Text", "start": 60.0 * first / wpm, "duration": 60.0 * (j - first) / wpm,
                     "text": " ".join(sents), "section": name, **base})
        secs.append({"timeline": timeline, "section": name, "order": order, "n_words": j - first,
                     "start": 60.0 * first / wpm, "stop": 60.0 * j / wpm})
    events = pd.DataFrame(rows)
    events["stop"] = events["start"] + events["duration"]
    return events, pd.DataFrame(secs)


def stimulus_events(stimuli: dict[tuple[str, str], Stimulus], wpm: float = WORDS_PER_MINUTE
                    ) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Events for every stimulus (one timeline per `stimulus_id`, `unit_id` and `condition` carried as
    columns) and the section table, in corpus order."""
    ev, sec = [], []
    for (uid, condition), stim in stimuli.items():
        e, s = word_events(stim.sections, stim.stimulus_id, wpm)
        for frame in (e, s):
            frame["unit_id"], frame["condition"] = uid, condition
        ev.append(e)
        sec.append(s)
    return pd.concat(ev, ignore_index=True), pd.concat(sec, ignore_index=True)


def expected_timepoints(duration_s: float, tr: float = TR) -> int:
    """Number of 1-TR windows TRIBE keeps for a stimulus: every window that overlaps a word."""
    return int(math.ceil(duration_s / tr - 1e-9))


def shuffled_sections(sections: dict[str, str], how: str, rng: np.random.Generator) -> dict[str, str]:
    """§10.1/§10.3 text controls with identical words and duration: `sentence` permutes the sentence order
    within each section, `word` permutes the tokens within each section."""
    out = {}
    for name, text in sections.items():
        sents = sentences(text)
        if how == "sentence":
            out[name] = "\n".join(sents[i] for i in rng.permutation(len(sents)))
        elif how == "word":
            tokens = [t for s in sents for t in s.split(" ")]
            out[name] = " ".join(tokens[i] for i in rng.permutation(len(tokens)))
        else:
            raise ValueError(f"unknown control {how!r}: use 'sentence' or 'word'")
    return out


# ------------------------------------------------------------------ vertex predictions on disk
def write_vertex(path: Path, preds: np.ndarray, time_index: np.ndarray) -> None:
    """One compressed parquet per stimulus (brief §6.3): one row per vertex (`vertex_id`), one column per
    predicted second (`t000123` = time_index 123). Columns-as-seconds is ~15x faster to read and write than
    columns-as-vertices and a fifth smaller; `read_vertex` returns the (T, V) orientation."""
    import pyarrow as pa
    import pyarrow.parquet as pq

    preds = np.asarray(preds, dtype=np.float32)
    time_index = np.asarray(time_index, dtype=np.int64)
    if preds.shape[0] != len(time_index):
        raise ValueError(f"{preds.shape[0]} rows of predictions but {len(time_index)} time indices")
    arrays = [pa.array(np.arange(preds.shape[1], dtype=np.int32))] + [pa.array(preds[t]) for t in range(preds.shape[0])]
    names = ["vertex_id"] + [f"t{int(t):06d}" for t in time_index]
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(pa.Table.from_arrays(arrays, names=names), str(path), compression="zstd")


def read_vertex(path: Path) -> tuple[np.ndarray, np.ndarray]:
    """Inverse of `write_vertex`: (preds (T, V) float32, time_index (T,))."""
    import pyarrow.parquet as pq

    table = pq.read_table(str(path))
    cols = sorted((int(n[1:]), n) for n in table.column_names if n.startswith("t"))
    time_index = np.array([t for t, _ in cols], dtype=np.int64)
    preds = np.column_stack([table.column(n).to_numpy() for _, n in cols]).T.astype(np.float32)
    return preds, time_index


def vertex_long(stimulus_id: str, preds: np.ndarray, time_index: np.ndarray) -> pd.DataFrame:
    """The brief's §4.2 `tribe_vertex` layout (stimulus_id, time_index, vertex_id, predicted_bold)."""
    T, V = preds.shape
    return pd.DataFrame({"stimulus_id": stimulus_id, "time_index": np.repeat(time_index, V),
                         "vertex_id": np.tile(np.arange(V, dtype=np.int32), T), "predicted_bold": preds.ravel()})


# ------------------------------------------------------------------ eq. 6-7: parcels and networks
def parcellation(labels: dict[str, np.ndarray], names: dict[str, list], area: dict[str, np.ndarray]) -> pd.DataFrame:
    """Vertex table for a FreeSurfer annotation on the mesh TRIBE predicts on: hemispheres concatenated left
    then right, `parcel_id` 0 for the medial wall / unlabelled vertices, `network` parsed from Schaefer names
    (`7Networks_LH_Vis_3` -> `Vis`), `area` per vertex in mm^2 from the mesh (the eq. 7 weight)."""
    frames, next_id = [], 1
    for hemi in ("left", "right"):
        lab = np.asarray(labels[hemi])
        nm = [n.decode() if isinstance(n, bytes) else str(n) for n in names[hemi]]
        ids, nets = {}, {}
        for i, n in enumerate(nm):
            if n.lower().startswith(("background", "medial_wall", "unknown", "???")):
                continue
            parts = n.split("_")
            ids[i] = next_id
            nets[i] = parts[2] if len(parts) >= 4 and parts[0].endswith("Networks") else n
            next_id += 1
        frames.append(pd.DataFrame({
            "hemi": hemi,
            "parcel_id": [ids.get(int(l), 0) for l in lab],
            "parcel_name": [nm[int(l)] if 0 <= int(l) < len(nm) else "unlabelled" for l in lab],
            "network": [nets.get(int(l), "") for l in lab],
            "area": np.asarray(area[hemi], dtype=float),
        }))
    parc = pd.concat(frames, ignore_index=True)
    parc.insert(0, "vertex_id", np.arange(len(parc), dtype=np.int32))
    return parc


def parcel_table(parc: pd.DataFrame) -> pd.DataFrame:
    """One row per parcel (medial wall excluded): parcel_id, parcel_name, hemi, network, n_vertices, area."""
    kept = parc[parc.parcel_id > 0]
    table = kept.groupby(["parcel_id", "parcel_name", "hemi", "network"], as_index=False).agg(
        n_vertices=("vertex_id", "size"), area=("area", "sum"))
    return table.sort_values("parcel_id").reset_index(drop=True)


def aggregate_parcels(preds: np.ndarray, parc: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """eq. 6: mean (and sd) over the vertices of each parcel. Returns (mean (T, P), sd (T, P), parcel_ids)."""
    if preds.shape[1] != len(parc):
        raise ValueError(f"{preds.shape[1]} vertices predicted but the parcellation has {len(parc)}")
    ids = np.sort(parc.parcel_id[parc.parcel_id > 0].unique())
    members = [np.flatnonzero(parc.parcel_id.to_numpy() == p) for p in ids]
    M = np.zeros((preds.shape[1], len(ids)))
    for k, m in enumerate(members):
        M[m, k] = 1.0 / len(m)
    x = np.asarray(preds, dtype=np.float64)
    mean = x @ M
    sd = np.sqrt(np.maximum((x ** 2) @ M - mean ** 2, 0.0))
    return mean, sd, ids


def aggregate_networks(parcel_mean: np.ndarray, table: pd.DataFrame, weights: str = "area"
                       ) -> tuple[np.ndarray, list[str]]:
    """eq. 7: network response = sum_p w_p B_p / sum_p w_p with w_p = parcel area (main) or 1 (robustness).
    `table` is `parcel_table` output in the column order of `parcel_mean`."""
    if weights not in ("area", "equal"):
        raise ValueError("weights must be 'area' or 'equal'")
    w = table["area"].to_numpy(float) if weights == "area" else np.ones(len(table))
    nets = [n for n in NETWORKS if n in set(table.network)] + sorted(set(table.network) - set(NETWORKS))
    W = np.zeros((len(table), len(nets)))
    for k, n in enumerate(nets):
        sel = (table.network == n).to_numpy()
        W[sel, k] = w[sel] / w[sel].sum()
    return np.asarray(parcel_mean, dtype=np.float64) @ W, nets


# ------------------------------------------------------------------ §6.5: immediate neural metrics
def smooth(tc: np.ndarray, window: int = 3) -> np.ndarray:
    """Centred moving average along time (axis 0); the window shrinks at the edges."""
    x = np.asarray(tc, dtype=np.float64)
    if window <= 1 or len(x) == 1:
        return x.copy()
    half = window // 2
    out = np.empty_like(x)
    for t in range(len(x)):
        out[t] = x[max(0, t - half): t + half + 1].mean(axis=0)
    return out


def series_metrics(tc: np.ndarray, keys, dt: float = TR, smooth_window: int = 3,
                   baseline_quantile: float = 0.5) -> pd.DataFrame:
    """Time-course metrics of §6.5 for every column of `tc` (T x K), long format [key, metric, value]:
    `mean` over the instructional window, `peak` and `time_to_peak` (s) after temporal smoothing,
    `auc` (eq. 8, trapezoidal) and `sustained`, the share of time points above the stimulus-specific
    baseline threshold, ASSUMED here to be the `baseline_quantile` of all values in `tc` (one threshold per
    stimulus and aggregation level, so parcels or networks are compared on the same footing)."""
    x = np.asarray(tc, dtype=np.float64)
    if x.ndim != 2 or len(x) == 0:
        raise ValueError("tc must be a (T, K) array with T >= 1")
    sm = smooth(x, smooth_window)
    threshold = np.quantile(x, baseline_quantile)
    trapezoid = getattr(np, "trapezoid", None) or np.trapz  # numpy 2 renamed it
    auc = trapezoid(x, dx=dt, axis=0) if len(x) > 1 else x[0] * 0.0
    rows = {
        "mean": x.mean(axis=0),
        "peak": sm.max(axis=0),
        "time_to_peak": sm.argmax(axis=0) * dt,
        "auc": auc,
        "sustained": (x > threshold).mean(axis=0),
    }
    keys = [str(k) for k in keys]  # parcel ids and network names share one column downstream
    return pd.DataFrame([{"key": k, "metric": m, "value": float(v[i])}
                         for m, v in rows.items() for i, k in enumerate(keys)])


def spatial_metrics(pattern: np.ndarray) -> dict[str, float]:
    """On one parcel pattern (P,), normally the window mean: `dispersion` = variance across parcels and
    `entropy` = eq. 9, the normalised entropy of the non-negative parcel weights (1 = uniform, 0 = one parcel)."""
    q = np.maximum(np.asarray(pattern, dtype=np.float64), 0.0)
    if q.sum() > 0:
        q = q / q.sum()
        nz = q[q > 0]
        entropy = float(-(nz * np.log(nz)).sum() / np.log(len(q))) if len(q) > 1 else 0.0
    else:
        entropy = float("nan")
    return {"dispersion": float(np.var(pattern)), "entropy": entropy}


def integration(tc: np.ndarray) -> tuple[float, np.ndarray]:
    """Network integration: mean pairwise Pearson correlation of the network time courses (T x N) over the
    window, plus the full matrix. NaN when a series is constant."""
    x = np.asarray(tc, dtype=np.float64)
    if len(x) < 3 or x.shape[1] < 2:
        return float("nan"), np.full((x.shape[1], x.shape[1]), np.nan)
    with np.errstate(invalid="ignore", divide="ignore"):
        corr = np.corrcoef(x, rowvar=False)
    upper = corr[np.triu_indices(x.shape[1], 1)]
    return float(np.nanmean(upper)), corr


def stimulus_metrics(parcel_mean: np.ndarray, parcel_ids, network_tc: np.ndarray, networks,
                     dt: float = TR, smooth_window: int = 3, baseline_quantile: float = 0.5) -> pd.DataFrame:
    """All §6.5 metrics of one stimulus, long format [level, key, metric, value]: the time-course metrics per
    parcel and per network, the spatial metrics of the parcel pattern, and network integration."""
    parcels = series_metrics(parcel_mean, parcel_ids, dt, smooth_window, baseline_quantile).assign(level="parcel")
    nets = series_metrics(network_tc, networks, dt, smooth_window, baseline_quantile).assign(level="network")
    spatial = spatial_metrics(parcel_mean.mean(axis=0))
    integ, _ = integration(network_tc)
    whole = pd.DataFrame([{"level": "stimulus", "key": "all", "metric": m, "value": v}
                          for m, v in {**spatial, "integration": integ}.items()])
    return pd.concat([parcels, nets, whole], ignore_index=True)[["level", "key", "metric", "value"]]


# ------------------------------------------------------------------ §6.6: condition contrasts
def paired_contrasts(metrics: pd.DataFrame) -> pd.DataFrame:
    """eq. 10-12 on a long table with columns [unit_id, condition, level, key, metric, value]."""
    wide = metrics.pivot_table(index=["unit_id", "level", "key", "metric"], columns="condition", values="value")
    missing = [c for c in CONDITIONS if c not in wide.columns]
    if missing:
        raise ValueError(f"conditions missing from the metrics table: {missing}")
    for name, (a, b) in CONTRASTS.items():
        wide[name] = wide[a] - wide[b]
    return wide.reset_index()[["unit_id", "level", "key", "metric", *CONTRASTS]]


def fixed_effects(metrics: pd.DataFrame, covariates: pd.DataFrame | None = None, n_boot: int = 2000,
                  seed: int = 0) -> pd.DataFrame:
    """eq. 13, m_uc = alpha_u + beta_1 I(scaffolding) + beta_2 I(substitution) + gamma' x_uc + e, for every
    (level, key, metric) at once by within-unit demeaning, with a cluster bootstrap over units (§6.6) for the
    standard error and the 95% percentile interval. `covariates`, if given, is indexed by (unit_id, condition)
    with one numeric column per matching feature (e.g. word_count, duration). Without covariates the
    estimates are exactly the mean paired differences of eq. 10-12; `S-U` is beta_1 - beta_2."""
    wide = metrics.pivot_table(index=["unit_id", "condition"], columns=["level", "key", "metric"], values="value")
    units = wide.index.get_level_values("unit_id").unique()
    rows = pd.MultiIndex.from_product([units, CONDITIONS], names=["unit_id", "condition"])
    Y = wide.reindex(rows).to_numpy(float)
    if np.isnan(Y).any():
        raise ValueError("every unit needs all three conditions and every metric")
    X = np.column_stack([(rows.get_level_values("condition") == c).astype(float)
                         for c in ("ai_scaffolding", "ai_substitution")])
    if covariates is not None:
        X = np.column_stack([X, covariates.reindex(rows).to_numpy(float)])
        if np.isnan(X).any():
            raise ValueError("covariates must cover every (unit_id, condition)")
    n_units, n_cond = len(units), len(CONDITIONS)

    def demean(A):  # within-unit demeaning: rows are grouped by unit in blocks of n_cond
        blocks = A.reshape(n_units, n_cond, -1)
        return (blocks - blocks.mean(axis=1, keepdims=True)).reshape(A.shape)

    Xd, Yd = demean(X), demean(Y)

    def fit(Xm, Ym):
        beta = np.linalg.lstsq(Xm, Ym, rcond=None)[0]
        return np.vstack([beta[0], beta[1], beta[0] - beta[1]])  # S-T, U-T, S-U

    est = fit(Xd, Yd)
    rng = np.random.default_rng(seed)
    boots = np.empty((n_boot, 3, Y.shape[1]))
    for b in range(n_boot):
        pick = rng.integers(0, n_units, n_units)
        idx = (pick[:, None] * n_cond + np.arange(n_cond)).ravel()
        boots[b] = fit(Xd[idx], Yd[idx])
    se = boots.std(axis=0, ddof=1)
    lo, hi = np.percentile(boots, [2.5, 97.5], axis=0)
    out = []
    for j, (level, key, metric) in enumerate(wide.columns):
        for i, name in enumerate(CONTRASTS):
            out.append({"level": level, "key": key, "metric": metric, "contrast": name, "estimate": est[i, j],
                        "se": se[i, j], "ci_low": lo[i, j], "ci_high": hi[i, j], "n_units": n_units})
    return pd.DataFrame(out)


# ------------------------------------------------------------------ §6.7: representational similarity
def rdm(z: np.ndarray) -> np.ndarray:
    """eq. 14: 1 - corr(z_u, z_u') over rows (units)."""
    return 1.0 - np.corrcoef(np.asarray(z, dtype=np.float64))


def _upper(m: np.ndarray) -> np.ndarray:
    return m[np.triu_indices(len(m), 1)]


def spearman(a, b) -> float:
    a, b = pd.Series(np.asarray(a, float)).rank(), pd.Series(np.asarray(b, float)).rank()
    return float(np.corrcoef(a, b)[0, 1])


def rsa(patterns: dict[str, np.ndarray], n_perm: int = 1000, seed: int = 0) -> pd.DataFrame:
    """Compare RDMs across conditions: Spearman correlation of their upper triangles and a permutation p-value
    from shuffling condition labels within matched units (§6.7). `patterns[condition]` is (U, P) with units in
    the same order for every condition. The p-value is the share of label permutations whose RDM agreement
    is at most the observed one, i.e. a test of whether the two conditions' geometries are less alike than
    exchangeable labels would make them."""
    conds = list(patterns)
    Z = np.stack([np.asarray(patterns[c], float) for c in conds])  # C, U, P
    n_c, n_u, _ = Z.shape

    def stats(Zc):
        rd = [_upper(rdm(Zc[i])) for i in range(n_c)]
        return {(conds[i], conds[j]): spearman(rd[i], rd[j]) for i in range(n_c) for j in range(i + 1, n_c)}

    observed = stats(Z)
    rng = np.random.default_rng(seed)
    exceed = {k: 0 for k in observed}
    for _ in range(n_perm):
        perm = np.empty_like(Z)
        for u in range(n_u):
            perm[:, u] = Z[rng.permutation(n_c), u]
        for k, v in stats(perm).items():
            exceed[k] += v <= observed[k]
    return pd.DataFrame([{"condition_a": a, "condition_b": b, "spearman": v,
                          "p_perm": (exceed[(a, b)] + 1) / (n_perm + 1), "n_perm": n_perm}
                         for (a, b), v in observed.items()])


def differentiation(z: np.ndarray, concepts) -> dict[str, float]:
    """eq. 34 on one condition: mean between-concept distance minus mean within-concept distance, with
    d = 1 - corr (the eq. 14 metric), plus `within_consistency`, the mean correlation between units that
    teach the same concept (§6.5 within-concept consistency)."""
    d = rdm(z)
    concepts = np.asarray(list(concepts))
    same = concepts[:, None] == concepts[None, :]
    iu = np.triu_indices(len(concepts), 1)
    within, between = d[iu][same[iu]], d[iu][~same[iu]]
    return {"differentiation": float(between.mean() - within.mean()) if len(within) and len(between) else float("nan"),
            "within_consistency": float(1.0 - within.mean()) if len(within) else float("nan"),
            "between_distance": float(between.mean()) if len(between) else float("nan")}

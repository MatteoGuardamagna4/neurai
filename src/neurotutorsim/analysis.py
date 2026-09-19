"""Analysis for the brief's §10-§11 and the §13 tables: pure functions, saved outputs in, DataFrames out.

Nothing here simulates or predicts; `report.py` writes the results to outputs/tables and outputs/figures.
Language follows brief §15: "predicted cortical response", "simulated learner", "model-implied",
"scenario contrast (SC)". Intervals across parameter draws are simulation intervals, not confidence intervals,
and p-values on simulated or model-predicted data are descriptive (§11.3).
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from . import tribe
from .corpus import CONDITIONS

FEATURES = ("word_count", "character_count", "sentence_count", "readability", "equation_count", "example_count",
            "lexical_diversity", "duration")  # eq. 1 without semantic coverage (§5.4 not run)
PAIRS = {"S-T": ("ai_scaffolding", "traditional"), "U-T": ("ai_substitution", "traditional"),
         "S-U": ("ai_scaffolding", "ai_substitution")}
SMD_TARGET = 0.10  # §5.3: |SMD| < 0.10 for every continuous matching feature
TABLE4_SERIES = ("auc", "mean", "peak", "time_to_peak", "sustained")  # per network (§6.5)
TABLE4_STIMULUS = ("entropy", "dispersion", "integration")  # one value per stimulus (§6.5)


# ------------------------------------------------------------------ small statistics
def smd(a, b) -> float:
    """eq. 3: (mean_a - mean_b) / sqrt((var_a + var_b) / 2), sample variances; 0 when both are constant and equal."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    pooled = np.sqrt((a.var(ddof=1) + b.var(ddof=1)) / 2.0)
    diff = a.mean() - b.mean()
    if pooled == 0:
        return 0.0 if diff == 0 else float(np.sign(diff) * np.inf)
    return float(diff / pooled)


def paired_tost(diff, bound: float) -> float:
    """Two one-sided paired t-tests of |mean difference| < bound: the larger of the two p-values (§11.1, reported as a
    descriptive diagnostic, never as proof of equivalence)."""
    from scipy import stats

    d = np.asarray(diff, float)
    n, m, sd = len(d), d.mean(), d.std(ddof=1)
    if sd == 0:
        return 0.0 if abs(m) < bound else 1.0
    se = sd / np.sqrt(n)
    p_low = stats.t.sf((m + bound) / se, n - 1)  # H0: mean <= -bound
    p_high = stats.t.cdf((m - bound) / se, n - 1)  # H0: mean >= +bound
    return float(max(p_low, p_high))


def bh_fdr(p) -> np.ndarray:
    """Benjamini-Hochberg adjusted p-values (q-values), in the input order; NaN stays NaN."""
    p = np.asarray(p, float)
    q = np.full_like(p, np.nan)
    ok = ~np.isnan(p)
    if not ok.any():
        return q
    pv = p[ok]
    order = np.argsort(pv)
    ranked = pv[order] * len(pv) / np.arange(1, len(pv) + 1)
    adj = np.minimum.accumulate(ranked[::-1])[::-1].clip(max=1.0)
    out = np.empty_like(pv)
    out[order] = adj
    q[ok] = out
    return q


def normal_p(estimate, se) -> np.ndarray:
    """Two-sided p from z = estimate / se (se from the cluster bootstrap); descriptive only."""
    from scipy import stats

    with np.errstate(divide="ignore", invalid="ignore"):
        z = np.abs(np.asarray(estimate, float) / np.asarray(se, float))
    return 2.0 * stats.norm.sf(z)


def intervals(x, levels=(0.90, 0.95)) -> dict:
    """Median, mean and equal-tailed simulation intervals across draws (§9.5)."""
    x = np.asarray(x, float)
    x = x[~np.isnan(x)]
    out = {"mean": float(x.mean()) if len(x) else np.nan, "median": float(np.median(x)) if len(x) else np.nan, "n": len(x)}
    for lvl in levels:
        lo, hi = (np.quantile(x, [(1 - lvl) / 2, (1 + lvl) / 2]) if len(x) else (np.nan, np.nan))
        out[f"lo{int(lvl * 100)}"], out[f"hi{int(lvl * 100)}"] = float(lo), float(hi)
    return out


def bootstrap_ci(x, n_boot: int = 2000, seed: int = 0) -> tuple[float, float]:
    """95% percentile interval of the mean, resampling units (learners or corpus units)."""
    x = np.asarray(x, float)
    x = x[~np.isnan(x)]
    if len(x) < 2:
        return (np.nan, np.nan)
    rng = np.random.default_rng(seed)
    means = x[rng.integers(0, len(x), (n_boot, len(x)))].mean(axis=1)
    lo, hi = np.percentile(means, [2.5, 97.5])
    return float(lo), float(hi)


def tipping_point(x, g) -> float:
    """eq. 40 along one line of the grid: where G first changes sign, linearly interpolated between the two grid
    points around the change (G can rise with the knob, as with retained effort, or fall, as with substitution).
    NaN when G keeps one sign over the whole line; the share of such draws is reported with the intervals."""
    x, g = np.asarray(x, float), np.asarray(g, float)
    for i in range(1, len(x)):
        if (g[i - 1] < 0) != (g[i] < 0):
            return float(x[i - 1] + (x[i] - x[i - 1]) * (0 - g[i - 1]) / (g[i] - g[i - 1]))
    return np.nan


# ------------------------------------------------------------------ §11.1 corpus balance
def corpus_balance(stimuli: pd.DataFrame, features=FEATURES) -> pd.DataFrame:
    """Per matching feature: mean and SD per condition, and for each condition pair the SMD (eq. 3), the mean
    paired difference over units, and the paired TOST p at +-0.10 pooled SD (descriptive)."""
    wide = stimuli.pivot_table(index="unit_id", columns="condition", values=list(features))
    rows = []
    for f in features:
        row = {"feature": f}
        for c in CONDITIONS:
            row[f"mean_{c}"] = float(wide[(f, c)].mean())
            row[f"sd_{c}"] = float(wide[(f, c)].std(ddof=1))
        for name, (a, b) in PAIRS.items():
            xa, xb = wide[(f, a)].to_numpy(float), wide[(f, b)].to_numpy(float)
            bound = SMD_TARGET * np.sqrt((xa.var(ddof=1) + xb.var(ddof=1)) / 2.0)
            row[f"smd_{name}"] = smd(xa, xb)
            row[f"diff_{name}"] = float((xa - xb).mean())
            row[f"tost_p_{name}"] = paired_tost(xa - xb, bound)
        row["within_target"] = all(abs(row[f"smd_{n}"]) < SMD_TARGET for n in PAIRS)
        rows.append(row)
    return pd.DataFrame(rows)


# ------------------------------------------------------------------ gate 19: what each cortical metric means
def metric_definitions() -> pd.DataFrame:
    """Decision gate 19: the mathematical meaning and direction of every cortical metric, before any is interpreted.
    B is TRIBE's predicted BOLD response (arbitrary units, one row per second of reading); none of these is a
    measured response, and none is learning."""
    rows = [
        ("mean", "parcel, network", "mean_t B_t over the reading window", "a.u.",
         "higher = more predicted response on average; independent of stimulus length"),
        ("auc", "parcel, network", "eq. 8, trapezoidal integral of B over time (dt = 1 s)", "a.u. x s",
         "higher = more predicted response mass; grows with duration, so condition contrasts are also shown with duration and word count as covariates (F1)"),
        ("peak", "parcel, network", "max_t of B after a centred 3-s moving average", "a.u.",
         "higher = a stronger maximum predicted response"),
        ("time_to_peak", "parcel, network", "argmax_t of the smoothed B", "s",
         "larger = the maximum comes later in the text; depends on where the dense content sits"),
        ("sustained", "parcel, network", "share of seconds with B above the stimulus's median over all its keys and seconds (ASSUMED baseline)", "share",
         "higher = the region spends more of the window above the stimulus-wide median"),
        ("dispersion", "stimulus", "variance across parcels of the window-mean pattern", "a.u.^2",
         "higher = a more uneven spatial pattern"),
        ("entropy", "stimulus", "eq. 9, normalised entropy of the positive part of the window-mean parcel pattern", "0-1",
         "1 = predicted response spread evenly over parcels, lower = concentrated in few"),
        ("integration", "stimulus", "mean pairwise Pearson correlation of the 7 network time courses", "-1 to 1",
         "higher = networks co-fluctuate more over the reading window"),
        ("rdm", "units x units per condition", "eq. 14, 1 - corr of window-mean parcel patterns", "0-2",
         "larger = two units' predicted patterns differ more"),
        ("differentiation", "condition", "eq. 34, mean between-concept minus mean within-concept RDM distance", "0-2",
         "higher = units of the same concept look more alike than units of different concepts"),
        ("Z", "unit x condition x parcel", "eq. 28, AUC standardised per parcel over the 90 stimuli, winsorised at the global 1st/99th percentiles", "SD",
         "the input to plasticity eq. 29-33: which parcels a stimulus drives more than the corpus average"),
        ("N", "learner x parcel or network", "eq. 29-33, decayed sum of behaviour-weighted Z", "a.u.",
         "model-implied accumulated functional recruitment, never a predicted future brain state; only contrasts and d (eq. 44) are interpreted"),
    ]
    return pd.DataFrame(rows, columns=["metric", "level", "definition", "units", "direction"])


# ------------------------------------------------------------------ §11.2 immediate cortical contrasts
def table4(metrics: pd.DataFrame, covariates: pd.DataFrame | None = None, n_boot: int = 2000, seed: int = 0) -> pd.DataFrame:
    """Table 4: eq. 13 at network level (area weights, the primary level) for the §6.5 time-course metrics, plus
    the stimulus-level spatial metrics, with cluster-bootstrap intervals over units. p from the bootstrap SE
    (normal approximation, descriptive) and BH-FDR across the 7 networks within each metric x contrast."""
    net = metrics[(metrics["level"] == "network") & metrics["metric"].isin(TABLE4_SERIES)]
    stim = metrics[(metrics["level"] == "stimulus") & metrics["metric"].isin(TABLE4_STIMULUS)]
    fe = tribe.fixed_effects(pd.concat([net, stim]), covariates, n_boot=n_boot, seed=seed)
    fe["p"] = normal_p(fe["estimate"], fe["se"])
    fe["q_fdr"] = np.nan
    for _, idx in fe.groupby(["level", "metric", "contrast"]).groups.items():
        fe.loc[idx, "q_fdr"] = bh_fdr(fe.loc[idx, "p"])
    fe["ci_excludes_0"] = (fe["ci_low"] > 0) | (fe["ci_high"] < 0)
    return fe


def matching_covariates(stimuli: pd.DataFrame, names=("duration", "word_count")) -> pd.DataFrame:
    """(unit_id, condition)-indexed covariates for eq. 13, standardised (F1: do effects survive the matching features?)."""
    x = stimuli.set_index(["unit_id", "condition"])[list(names)].astype(float)
    return (x - x.mean()) / x.std(ddof=1)


def eq42(metrics: pd.DataFrame, units: pd.DataFrame, level: str = "network", metric: str = "auc") -> pd.DataFrame:
    """eq. 42 with a unit random intercept (PLAN.md D8: difficulty and domain are constant within a unit, so unit
    fixed effects would absorb them): value ~ condition + difficulty + domain + region intercepts. Region
    (network or parcel) intercepts are removed by within-region centring, exact here because every region has
    all 90 stimuli. Returns the fixed effects with Wald intervals."""
    import statsmodels.formula.api as smf

    d = metrics[(metrics["level"] == level) & (metrics["metric"] == metric)].copy()
    d = d.merge(units[["unit_id", "difficulty", "domain"]], on="unit_id", how="left")
    d["y"] = d["value"] - d.groupby("key")["value"].transform("mean") + d["value"].mean()
    d["condition"] = pd.Categorical(d["condition"], categories=list(CONDITIONS))
    fit = smf.mixedlm("y ~ C(condition) + difficulty + C(domain)", d, groups=d["unit_id"]).fit(reml=True)
    ci = fit.conf_int()
    out = pd.DataFrame({"term": fit.fe_params.index, "estimate": fit.fe_params.values,
                        "se": fit.bse_fe.values, "ci_low": ci.loc[fit.fe_params.index, 0].values,
                        "ci_high": ci.loc[fit.fe_params.index, 1].values})
    out["level"], out["metric"], out["n_obs"], out["n_units"] = level, metric, len(d), d["unit_id"].nunique()
    out["unit_intercept_var"] = float(fit.cov_re.iloc[0, 0])
    return out


def parcel_contrasts(metrics: pd.DataFrame, metric: str = "auc", n_boot: int = 2000, seed: int = 0) -> pd.DataFrame:
    """Per-parcel eq. 13 contrasts with BH-FDR over all 400 x 3 tests (§11.2 parcel maps)."""
    fe = tribe.fixed_effects(metrics[(metrics["level"] == "parcel") & (metrics["metric"] == metric)], n_boot=n_boot, seed=seed)
    fe["p"] = normal_p(fe["estimate"], fe["se"])
    fe["q_fdr"] = bh_fdr(fe["p"])
    return fe


def unit_patterns(patterns: pd.DataFrame, units: pd.DataFrame) -> tuple[dict, list[str], list[str]]:
    """(condition -> (30, P) window-mean parcel patterns, unit order by concept, concepts in that order)."""
    order = units.sort_values(["concept", "unit_id"])
    ids = order["unit_id"].tolist()
    by_cond = {c: patterns.loc[[f"{u}_{c}" for u in ids]].to_numpy(float) for c in CONDITIONS}
    return by_cond, ids, order["concept"].tolist()


def rsa_summary(patterns: pd.DataFrame, units: pd.DataFrame, n_perm: int = 1000, seed: int = 0) -> tuple[pd.DataFrame, pd.DataFrame]:
    """§6.7: RDM agreement between conditions (Spearman, label permutations within units) and eq. 34 per condition."""
    by_cond, _, concepts = unit_patterns(patterns, units)
    agreement = tribe.rsa(by_cond, n_perm=n_perm, seed=seed)
    diff = pd.DataFrame([{"condition": c, **tribe.differentiation(z, concepts)} for c, z in by_cond.items()])
    return agreement, diff


def shuffle_controls(controls: pd.DataFrame, contrasts: pd.DataFrame) -> pd.DataFrame:
    """§10.1/§10.3: per network and metric, the mean |change| from sentence- and word-shuffling (identical words and
    duration) next to the |condition contrast| of Table 4; ratio > 1 means shuffling moves the prediction more."""
    ctl = controls.groupby(["control", "key", "metric"], as_index=False)["abs_change"].mean()
    con = contrasts[contrasts["level"] == "network"].assign(abs_estimate=lambda d: d["estimate"].abs())
    con = con.groupby(["key", "metric"], as_index=False)["abs_estimate"].max().rename(columns={"abs_estimate": "max_abs_condition_contrast"})
    out = ctl.merge(con, on=["key", "metric"], how="left")
    out["ratio_shuffle_to_contrast"] = out["abs_change"] / out["max_abs_condition_contrast"]
    return out


# ------------------------------------------------------------------ §10.2 engine comparison (S7)
def learner_outcomes(processed: Path) -> pd.DataFrame:
    """One row per (condition, learner): Phase III episode rates, the state after the last episode and the §7.7
    checkpoint accuracies, from learner_state.parquet and checkpoints.csv."""
    st = pd.read_parquet(Path(processed) / "learner_state.parquet")
    g = st.groupby(["condition", "learner_id"])
    out = g.agg(first_try=("correctness", "mean"), transfer=("transfer_correct", "mean"),
                reveal=("answer_provided", "mean"), help_per_episode=("help_requests", "mean"),
                effort=("effort", "mean")).reset_index()
    last = st.sort_values("time").groupby(["condition", "learner_id"]).tail(1)
    out = out.merge(last[["condition", "learner_id", "K", "M", "R", "C", "D"]], on=["condition", "learner_id"])
    ck_path = Path(processed) / "checkpoints.csv"
    if ck_path.exists() and ck_path.stat().st_size:
        ck = pd.read_csv(ck_path)
        for ep, g_ in ck.groupby("checkpoint_episode"):
            g_ = g_[["condition", "learner_id", "unaided_accuracy_trained", "far_transfer_accuracy"]].rename(
                columns={"unaided_accuracy_trained": f"unaided_ep{ep}", "far_transfer_accuracy": f"far_ep{ep}"})
            out = out.merge(g_, on=["condition", "learner_id"], how="left")
    return out


def engine_comparison(a_dir: Path, b_dir: Path, names=("centaur", "logistic"), n_boot: int = 2000, seed: int = 0) -> pd.DataFrame:
    """§10.2: the transcript-model run against the transparent baseline on the same learners (paired by condition
    and learner). Both take correctness from eq. 17-18, so differences come only from help requests, confidence
    and the free-choice approach, and the random streams differ between engines. Descriptive: no pass/fail."""
    a, b = learner_outcomes(a_dir), learner_outcomes(b_dir)
    both = a.merge(b, on=["condition", "learner_id"], suffixes=(f"_{names[0]}", f"_{names[1]}"))
    outcomes = [c for c in a.columns if c not in ("condition", "learner_id") and c in b.columns]
    rows = []
    for cond, g in both.groupby("condition"):
        for o in outcomes:
            d = (g[f"{o}_{names[0]}"] - g[f"{o}_{names[1]}"]).to_numpy(float)
            lo, hi = bootstrap_ci(d, n_boot, seed)
            rows.append({"section": "paired difference", "condition": cond, "outcome": o,
                         names[0]: float(g[f"{o}_{names[0]}"].mean()), names[1]: float(g[f"{o}_{names[1]}"].mean()),
                         "difference": float(np.nanmean(d)), "ci_low": lo, "ci_high": hi, "n_learners": int((~np.isnan(d)).sum())})
    for engine, frame in zip(names, (a, b)):  # eq. 10-12 arm contrasts within each engine
        wide = frame.set_index(["learner_id", "condition"]).unstack("condition")
        for name, (c1, c2) in PAIRS.items():
            for o in outcomes:
                if (o, c1) not in wide.columns or (o, c2) not in wide.columns:
                    continue
                d = (wide[(o, c1)] - wide[(o, c2)]).to_numpy(float)
                lo, hi = bootstrap_ci(d, n_boot, seed)
                rows.append({"section": f"arm contrast within {engine}", "condition": name, "outcome": o,
                             "difference": float(np.nanmean(d)), "ci_low": lo, "ci_high": hi,
                             "n_learners": int((~np.isnan(d)).sum())})
    return pd.DataFrame(rows)


def free_choice_shares(processed: Path) -> pd.DataFrame:
    """Share of each protocol picked in the free-choice arm, overall and by tercile of the learner's K."""
    st = pd.read_parquet(Path(processed) / "learner_state.parquet")
    free = st[st["condition"] == "free_choice"].copy()
    if free.empty:
        return pd.DataFrame()
    free["K_tercile"] = pd.qcut(free["K"], 3, labels=["low", "mid", "high"], duplicates="drop").astype(str)
    overall = free["protocol"].value_counts(normalize=True).rename("share").reset_index().assign(K_tercile="all")
    by = free.groupby("K_tercile")["protocol"].value_counts(normalize=True).rename("share").reset_index()
    return pd.concat([overall, by], ignore_index=True)[["K_tercile", "protocol", "share"]]


# ------------------------------------------------------------------ gate 18 (S8)
def _levels(draws: pd.DataFrame, outcome: str, year: int = 1) -> pd.DataFrame:
    d = draws[(draws["kind"] == "level") & (draws["outcome"] == outcome) & (draws["year"] == year)]
    return d.pivot_table(index="draw_id", columns="scenario", values="estimate")


def gate18(pilot: Path, zero_plasticity: Path | None = None, zero_effort: Path | None = None, crn: Path | None = None,
           breaks: dict | None = None, run_t1: bool = True) -> pd.DataFrame:
    """Decision gate 18 on the one-year pilot runs (PLAN.md S8, G1-G10). `breaks` maps break length in weeks to a
    run directory of the central draw (for the G4 dose-response); `crn` is a run with a relabelled traditional
    scenario. Returns (check, rule, value, pass); a check whose run is missing is `not run`."""
    from .longitudinal import read_table

    from .learners import logistic

    draws = read_table(pilot, "simulation_draws")
    rows = []

    def add(check, rule, value, ok):
        rows.append({"check": check, "rule": rule, "value": value, "pass": ok if isinstance(ok, str) else bool(ok)})

    # G1 as the brief words it (§10.2): higher prior knowledge must not reduce baseline accuracy on average. The
    # stricter year-1 version planned in PLAN.md (S8) is reported but does not gate (user decision 2026-09-18): the
    # strata converge within weeks because eq. 16 draws the learning rate independently of prior knowledge.
    b0, b1, b2 = (_levels(draws, f"unaided_stratum{i}", year=0) for i in range(3))
    add("G1 prior knowledge monotone (brief §10.2)", "baseline unaided accuracy low <= medium <= high on average over draws, every scenario",
        f"mean low / medium / high {b0.mean().mean():.3f} / {b1.mean().mean():.3f} / {b2.mean().mean():.3f}",
        bool(((b0.mean() <= b1.mean()) & (b1.mean() <= b2.mean())).all()))
    s0, s1, s2 = (_levels(draws, f"unaided_stratum{i}") for i in range(3))
    mono = ((s0 < s1) & (s1 < s2)).mean()
    add("G1b prior knowledge at year 1 (PLAN.md S8, informational)", "year-1 unaided accuracy low < medium < high in >= 95% of draws",
        f"min share {mono.min():.3f} ({mono.idxmin()}); mean high - low {(s2 - s0).mean().mean():+.4f}: strata converge within weeks",
        "not met (informational)" if mono.min() < 0.95 else True)
    slope = _levels(draws, "difficulty_slope")
    add("G2 difficulty lowers accuracy", "slope of expected accuracy on difficulty < 0 in 100% of draws",
        f"max slope {slope.max().max():.4f}", (slope < 0).all().all())
    gap = _levels(draws, "support_gap_min")
    add("G3 support helps", "support gap > 0 for every learner-year", f"min gap {gap.min().min():.4f}", (gap > 0).all().all())
    below = _levels(draws, "retention_below_share")
    ok4 = (below >= 0.99).all().all()
    value4 = f"min share of learners forgetting {below.min().min():.3f}"
    if breaks:
        ret = {w: read_table(p, "simulation_draws").query("kind == 'level' and outcome == 'retention' and draw_id == -1 and year == 1")
               .set_index("scenario")["estimate"] for w, p in sorted(breaks.items())}
        weeks = sorted(ret)
        dose = all((ret[weeks[i]] > ret[weeks[i + 1]]).all() for i in range(len(weeks) - 1))
        value4 += f"; retention strictly falls over breaks of {weeks} weeks: {dose}"
        ok4 = ok4 and dose
    else:
        value4 += "; break-length runs not given"
    add("G4 forgetting", "retention < end-of-year accuracy for >= 99% of learners; longer breaks lower retention", value4, ok4)
    dep = _levels(draws, "D")
    if {"scaffolding_rapid", "scaffolding_nofade"} <= set(dep.columns):
        share = (dep["scaffolding_rapid"] < dep["scaffolding_nofade"]).mean()
        add("G5 fading lowers dependence", "year-1 D: rapid fade < no fade in >= 95% of draws", f"share {share:.3f}", share >= 0.95)
    if zero_plasticity is not None:
        nz = read_table(zero_plasticity, "neural_contrasts")
        add("G6 zero plasticity", "every neural contrast exactly 0", f"max |mean| {nz['mean'].abs().max():.3g} over {len(nz)} rows",
            len(nz) > 0 and (nz["mean"] == 0).all() and (nz["d"] == 0).all())
    else:
        add("G6 zero plasticity", "every neural contrast exactly 0", "run not given", "not run")
    if zero_effort is not None:
        ze = read_table(zero_effort, "simulation_draws")
        eff = ze.query("kind == 'level' and outcome == 'effort'")["estimate"]
        e0 = float(logistic(-1.0))
        sc = lambda d: d.query("kind == 'contrast' and outcome == 'K' and scenario == 'substitution' and year == 1")["estimate"].abs().mean()  # noqa: E731
        add("G7 zero effort sensitivity", "E constant at logistic(a0); |SC_K(substitution)| smaller than in the pilot",
            f"E range {eff.min():.6f}-{eff.max():.6f} (logistic(a0) = {e0:.6f}); |SC_K| {sc(ze):.4f} vs {sc(draws):.4f}",
            np.allclose(eff, e0) and sc(ze) < sc(draws))
    else:
        add("G7 zero effort sensitivity", "E constant; |SC_K(substitution)| smaller", "run not given", "not run")
    if crn is not None:
        cc = read_table(crn, "simulation_draws").query("kind == 'contrast' and scenario == 'traditional_copy'")
        add("G8 common random numbers", "traditional vs a relabelled traditional: every contrast exactly 0",
            f"max |SC| {cc['estimate'].abs().max():.3g} over {len(cc)} rows", len(cc) > 0 and (cc["estimate"] == 0).all())
    else:
        add("G8 common random numbers", "relabelled traditional contrasts exactly 0", "run not given", "not run")
    clips = _levels(draws, "clips")
    bound = _levels(draws, "near_bound_share")
    add("G9 no bound effects", "zero clips; < 5% of learners within 0.01 of a bound at year 1",
        f"clips {int(clips.sum().sum())}; max near-bound share {bound.max().max():.3f}",
        clips.sum().sum() == 0 and bound.max().max() < 0.05)
    if run_t1:
        root = Path(__file__).resolve().parents[2]
        r = subprocess.run([sys.executable, "-m", "pytest", "-q", "tests/test_longitudinal.py::test_t1_vectorised_step_matches_the_reference_loop"],
                           cwd=root, capture_output=True, text=True)
        commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=root, capture_output=True, text=True).stdout.strip()
        add("G10 equivalence", "T1 (vectorised step = reference loop) green on the current commit",
            f"commit {commit}: {r.stdout.strip().splitlines()[-1] if r.stdout.strip() else r.returncode}", r.returncode == 0)
    return pd.DataFrame(rows)


# ------------------------------------------------------------------ Table 5: scenario contrasts across draws (§9.4-9.5)
def scenario_contrasts(draws: pd.DataFrame, outcomes=None, years=(1, 5, 10)) -> pd.DataFrame:
    """Per AI scenario x outcome x year: the SC across draws (mean of each draw's mean paired difference), its
    median and 90/95% simulation intervals, and PrSup pooled over learners and draws (eq. 37-38). The central
    draw (-1) is excluded from the intervals."""
    c = draws[(draws["kind"] == "contrast") & (draws["draw_id"] >= 0) & draws["year"].isin(years)]
    if outcomes is not None:
        c = c[c["outcome"].isin(outcomes)]
    rows = []
    for (s, o, y), g in c.groupby(["scenario", "outcome", "year"]):
        rows.append({"scenario": s, "outcome": o, "year": y, **intervals(g["estimate"]),
                     "prsup": float(g["prsup"].mean()), "share_draws_positive": float((g["estimate"] > 0).mean())})
    return pd.DataFrame(rows)


def neural_contrasts_table(neural: pd.DataFrame, mechanism: str = "D", years=(1, 5, 10)) -> pd.DataFrame:
    """Table 5 neural part (§11.4, eq. 44): d per network with simulation intervals across draws and PrSup."""
    n = neural[(neural["mechanism"] == mechanism) & (neural["draw_id"] >= 0) & neural["year"].isin(years)]
    rows = []
    for (s, net, y), g in n.groupby(["scenario", "network", "year"]):
        rows.append({"scenario": s, "network": net, "year": y, "mechanism": mechanism, **{f"d_{k}": v for k, v in intervals(g["d"]).items()},
                     "prsup": float(g["prsup"].mean())})
    return pd.DataFrame(rows)


# ------------------------------------------------------------------ §10.3 negative controls on Z (S12, post hoc)
def permute_z(Z: np.ndarray, how: str, rng: np.random.Generator, n_cond: int = 3) -> np.ndarray:
    """A permuted copy of Z (rows unit-major x condition). `units`: within each condition the units' patterns are
    deranged, so no unit keeps its own (the irrelevant-content control); `conditions`: within each unit the condition
    rows get a random non-identity permutation (the permuted-labels control)."""
    n_units = len(Z) // n_cond
    blocks = np.asarray(Z).reshape(n_units, n_cond, -1).copy()
    if how == "units":
        while True:
            perm = rng.permutation(n_units)
            if not np.any(perm == np.arange(n_units)):
                break
        return blocks[perm].reshape(Z.shape)
    if how == "conditions":
        out = blocks.copy()
        for u in range(n_units):
            while True:
                perm = rng.permutation(n_cond)
                if not np.all(perm == np.arange(n_cond)):
                    break
            out[u] = blocks[u, perm]
        return out.reshape(Z.shape)
    raise ValueError(f"unknown permutation {how!r}")


def network_contrast(mean_diff: np.ndarray, w: np.ndarray, Z: np.ndarray, W: np.ndarray) -> np.ndarray:
    """Mean network contrast (rows, networks) for any Z, exact because N is linear in the accumulators:
    (w . mean dA) @ Z @ W^T, with `mean_diff` (rows, 5, 90) the per-draw mean accumulator difference and `w` one
    weight vector (5,) or one per row (rows, 5), since each parameter draw has its own lambdas."""
    w = np.asarray(w, float)
    spec = "c,rcs->rs" if w.ndim == 1 else "rc,rcs->rs"
    return np.einsum(spec, w, np.asarray(mean_diff, float)) @ Z @ W.T


def z_controls(run: Path, cfg: dict, root: Path, n_perm: int = 200, seed: int = 0, mechanism: str = "D") -> pd.DataFrame:
    """§10.3 on a Phase V run, post hoc: per AI scenario, year and network, the mean over draws of the main network
    contrast, and the same under (a) units permuted within condition, (b) conditions permuted within unit (n_perm
    each: median |control| / |main| and the share of permutations at least as large as the main contrast), and
    (c) harmless variations: 180 and 260 wpm, and unwinsorised Z (change relative to the main contrast)."""
    from . import plasticity as P
    from .longitudinal import read_arrays, read_table

    p = cfg["plasticity"]
    tribe_dir = Path(root) / p["tribe_dir"]
    arr = read_arrays(run, "mean_accumulator_diff")
    if not arr:
        return pd.DataFrame()
    keep = arr["draw_id"] >= 0
    W, nets = P.load_networks(tribe_dir, p["network_weights"])
    params = read_table(run, "parameter_draws").set_index("draw_id")
    lam_o = params["plasticity.lambda_O"] if "plasticity.lambda_O" in params else pd.Series(dtype=float)
    Z, _, _ = P.load_z(tribe_dir, int(p["wpm"]), p["metric"], p["winsorize"])
    variants = {"reading speed 180 wpm": (180, p["winsorize"]), "reading speed 260 wpm": (260, p["winsorize"]),
                "unwinsorised Z": (int(p["wpm"]), None)}
    alt = {}
    for name, (wpm, wins) in variants.items():
        if (tribe_dir / f"wpm{wpm}" / "tribe_metrics.parquet").exists():
            alt[name] = P.load_z(tribe_dir, wpm, p["metric"], wins)[0]
    rng = np.random.default_rng(seed)
    perms = {how: [permute_z(Z, how, rng) for _ in range(n_perm)] for how in ("units", "conditions")}
    rows = []
    groups = pd.DataFrame({"scenario": arr["scenario"][keep], "year": arr["year"][keep]}).groupby(["scenario", "year"]).groups
    diffs, draw_ids = arr["diff"][keep], arr["draw_id"][keep]
    for (s, y), idx in groups.items():
        idx = np.asarray(list(idx))
        d = diffs[idx]
        w = np.stack([P.mechanism_weights(mechanism, {**p, "lambda_O": float(lam_o.get(b, p["lambda_O"]))}) for b in draw_ids[idx]])
        main = network_contrast(d, w, Z, W).mean(axis=0)
        ctl = {how: np.stack([network_contrast(d, w, Zp, W).mean(axis=0) for Zp in zs]) for how, zs in perms.items()}
        other = {name: network_contrast(d, w, Za, W).mean(axis=0) for name, Za in alt.items()}
        for i, net in enumerate(nets):
            row = {"scenario": s, "year": int(y), "network": net, "mechanism": mechanism, "main_contrast": float(main[i])}
            for how, c in ctl.items():
                ratio = np.abs(c[:, i]) / max(abs(main[i]), 1e-12)
                row[f"permuted_{how}_median_ratio"] = float(np.median(ratio))
                row[f"permuted_{how}_share_as_large"] = float((ratio >= 1).mean())
            for name, v in other.items():
                row[f"{name} change ratio"] = float(abs(v[i] - main[i]) / max(abs(main[i]), 1e-12))
            rows.append(row)
    return pd.DataFrame(rows)


def sign_flip_null(yearly: pd.DataFrame, outcome: str, comparator: str = "traditional", n_perm: int = 1000,
                   seed: int = 0) -> pd.DataFrame:
    """§10.3 behavioural label permutation: within each learner the sign of the paired difference is flipped at
    random; the null distribution of the mean SC is centred at 0 by construction, and the observed SC's position in
    it is reported per scenario, year and draw subsample (learner-level rows from `yearly_subsample`)."""
    rng = np.random.default_rng(seed)
    base = yearly[yearly["scenario"] == comparator].set_index(["draw_id", "year", "learner_id"])[outcome]
    rows = []
    for (s, y), g in yearly[yearly["scenario"] != comparator].groupby(["scenario", "year"]):
        d = (g.set_index(["draw_id", "year", "learner_id"])[outcome] - base).dropna().to_numpy(float)
        null = (d[None, :] * rng.choice([-1.0, 1.0], (n_perm, len(d)))).mean(axis=1)
        rows.append({"scenario": s, "year": int(y), "outcome": outcome, "observed_sc": float(d.mean()),
                     "null_mean": float(null.mean()), "null_sd": float(null.std(ddof=1)),
                     "share_null_as_extreme": float((np.abs(null) >= abs(d.mean())).mean()), "n_pairs": len(d)})
    return pd.DataFrame(rows)


# ------------------------------------------------------------------ §10.6 falsification checklist (S12)
def _sc_by_draw(draws: pd.DataFrame, year: int) -> pd.DataFrame:
    c = draws[(draws["kind"] == "contrast") & (draws["draw_id"] >= 0) & (draws["year"] == year)]
    return c.pivot_table(index="draw_id", columns=["scenario", "outcome"], values="estimate")


def falsification(table4_plain: pd.DataFrame, table4_cov: pd.DataFrame, shuffle: pd.DataFrame, draws: pd.DataFrame,
                  neural: pd.DataFrame, zc: pd.DataFrame, uniform_draws: pd.DataFrame | None = None,
                  year: int | None = None) -> pd.DataFrame:
    """The brief's six conditions under which no meaningful difference is claimed (§10.6), one row each with
    the indicator, the threshold (PLAN.md A15), the value and a verdict: `claim allowed`, `no claim` (naming what
    it applies to) or `not assessable` (the evidence does not exist in this study)."""
    year = year or int(draws["year"].max())
    rows = []

    def add(f, criterion, indicator, threshold, value, verdict):
        rows.append({"criterion": f"{f} {criterion}", "indicator": indicator, "threshold": threshold, "value": value,
                     "verdict": verdict})

    def sig(t):
        s = t[(t["level"] == "network") & (t["metric"] == "auc")]
        return set(zip(s["key"], s["contrast"])) - set(zip(s.loc[~s["ci_excludes_0"], "key"], s.loc[~s["ci_excludes_0"], "contrast"]))

    gone = sorted(sig(table4_plain) - sig(table4_cov))
    add("F1", "effects disappear after matching content and duration", "network AUC contrasts whose 95% CI excludes 0 "
        "without covariates but not with duration and word count", "any", ", ".join(f"{k} {c}" for k, c in gone) or "none",
        f"no claim for {len(gone)} network contrasts" if gone else "claim allowed")
    big = shuffle[(shuffle["metric"] == "auc") & (shuffle["control"] == "sentence") & (shuffle["ratio_shuffle_to_contrast"] > 1)]
    add("F2", "TRIBE contrasts smaller than harmless regenerations", "reworded versions were not built (D6); proxy: "
        "sentence-shuffle |change| in AUC larger than the largest condition contrast", "ratio > 1",
        ", ".join(big["key"]) or "none", "not assessable as specified" + (f"; proxy flags {len(big)} networks" if len(big) else ""))
    n = neural[(neural["year"] == year) & (neural["draw_id"] >= 0)]
    med = n.groupby(["scenario", "network", "mechanism"])["d"].median().unstack("mechanism")
    flip = med[(np.sign(med).nunique(axis=1) > 1)] if len(med) else med
    add("F3", "long-term direction reverses across plausible plasticity models", f"sign of the median year-{year} d "
        "across mechanisms A-D, per scenario and network", "any disagreement", f"{len(flip)} of {len(med)} scenario-networks",
        f"no claim for {len(flip)} scenario-networks" if len(flip) else "claim allowed")
    nb = draws[(draws["kind"] == "level") & (draws["outcome"] == "near_bound_share") & (draws["year"] == year) & (draws["draw_id"] >= 0)]
    by_s = nb.groupby("scenario")["estimate"] if len(nb) else None
    worst = by_s.median().max() if len(nb) else np.nan  # the typical draw of the worst scenario
    value = (f"median near-bound share, worst scenario {worst:.3f}; draws with > 10%: "
             + ", ".join(f"{k} {v:.0%}" for k, v in by_s.apply(lambda x: (x > 0.10).mean()).items() if v > 0)
             if len(nb) else "n/a")
    verdict = "no claim" if len(nb) and worst > 0.10 else "claim allowed"
    if uniform_draws is not None:
        a, b = _sc_by_draw(draws, year).median(), _sc_by_draw(uniform_draws, year).median()
        both = a.index.intersection(b.index)
        flips = [f"{s}/{o}" for s, o in both if o in ("G", "unaided", "far", "retention") and np.sign(a[(s, o)]) != np.sign(b[(s, o)])]
        value += f"; sign flips triangular vs uniform: {', '.join(flips) or 'none'}"
        verdict = "no claim" if flips or verdict == "no claim" else verdict
    else:
        value += "; uniform-draw rerun not given"
    add("F4", "result driven by parameter bounds", "learners within 0.01 of a bound; SC sign under uniform draws",
        "> 10% of learners; any sign flip", value, verdict)
    if len(zc):
        z = zc[zc["year"] == zc["year"].max()]
        # the condition-label permutation is the null for a condition contrast; permuting units within a condition
        # keeps each condition's mean text profile, so its ratio is ~1 by construction (a content control, Table 6)
        hit = z[z["permuted_conditions_median_ratio"] >= 0.5]
        add("F5", "negative controls as large as the substantive effects", "median |contrast with condition labels "
            "permuted within unit| / |main|, per scenario and network (mechanism D)", ">= 0.5 (A15)",
            f"{len(hit)} of {len(z)}: " + (", ".join(f"{a}/{b}" for a, b in zip(hit["scenario"], hit["network"])) or "none"),
            f"no claim for {len(hit)} scenario-networks" if len(hit) else "claim allowed")
    else:
        add("F5", "negative controls as large as the substantive effects", "permuted-Z ratios", ">= 0.5", "controls not run", "not assessable")
    sc = _sc_by_draw(draws, year)
    same = []
    for o in ("unaided", "far", "retention"):
        if ("scaffolding_nofade", o) in sc and ("substitution", o) in sc:
            d = (sc[("scaffolding_nofade", o)] - sc[("substitution", o)]).dropna()
            lo, hi = np.quantile(d, [0.025, 0.975])
            if lo <= 0 <= hi:
                same.append(o)
    add("F6", "scaffolding and substitution indistinguishable after support removal", f"95% interval across draws of the "
        f"year-{year} SC(scaffolding, no fade) - SC(substitution)", "includes 0", ", ".join(same) or "none",
        f"no claim for {', '.join(same)}" if same else "claim allowed")
    return pd.DataFrame(rows)


# ------------------------------------------------------------------ §9.6-9.7 frontier, tipping points, neural diagram (S10)
def phase_diagram(draws: pd.DataFrame, knobs: dict, year: int = 10, epsilons=(0.01, 0.02, 0.05)) -> pd.DataFrame:
    """Figure 7a: per frontier cell, the median over draws of the draw's mean G (eq. 39) at `year`, the share of draws
    with G > epsilon, and the class beneficial / neutral / harmful for each epsilon (A8)."""
    g = draws[(draws["kind"] == "contrast") & (draws["outcome"] == "G") & (draws["year"] == year) & (draws["draw_id"] >= 0)]
    rows = []
    for s, grp in g.groupby("scenario"):
        if s not in knobs:
            continue
        med = float(grp["estimate"].median())
        row = {"scenario": s, **knobs[s], "median_G": med, **{k: v for k, v in intervals(grp["estimate"]).items() if k != "median"}}
        for eps in epsilons:
            row[f"share_beneficial_eps{eps}"] = float((grp["estimate"] > eps).mean())
            row[f"class_eps{eps}"] = "beneficial" if med > eps else ("harmful" if med < -eps else "neutral")
        rows.append(row)
    return pd.DataFrame(rows)


def tipping_points(draws: pd.DataFrame, knobs: dict, year: int = 10, outcome: str = "G") -> tuple[pd.DataFrame, pd.DataFrame]:
    """eq. 40 per draw along each one-at-a-time line (e, o, f, forgetting multiplier), then across draws: the median,
    90 and 95% intervals of the tipping point and the share of draws where G never changes sign on the line."""
    g = draws[(draws["kind"] == "contrast") & (draws["outcome"] == outcome) & (draws["year"] == year) & (draws["draw_id"] >= 0)]
    g = g[g["scenario"].isin(knobs)].copy()
    g["line"] = g["scenario"].map(lambda s: knobs[s]["line"])
    g["x"] = g["scenario"].map(lambda s: float(knobs[s]["x"]))
    per_draw = []
    for (line, b), grp in g.groupby(["line", "draw_id"]):
        grp = grp.sort_values("x")
        per_draw.append({"line": line, "draw_id": int(b), "tipping_point": tipping_point(grp["x"], grp["estimate"])})
    per_draw = pd.DataFrame(per_draw)
    summary = []
    for line, grp in per_draw.groupby("line"):
        x = grp["tipping_point"]
        summary.append({"line": line, "year": year, "outcome": outcome, **intervals(x),
                        "share_no_sign_change": float(x.isna().mean()), "n_draws": len(x)})
    return per_draw, pd.DataFrame(summary)


def neural_diagram(nd: pd.DataFrame, year: int = 10) -> pd.DataFrame:
    """Figure 7b: per half-life x lambda_O x network, the median over draws of mechanism D's d (eq. 44) and PrSup."""
    n = nd[(nd["year"] == year) & (nd["draw_id"] >= 0)]
    return n.groupby(["scenario", "half_life_weeks", "lambda_O", "network"]).agg(
        median_d=("d", "median"), prsup=("prsup", "mean"), n_draws=("d", "size")).reset_index()


# ------------------------------------------------------------------ §11.5 mechanism decomposition (S11)
def _contribution_row(full: pd.Series, held: pd.Series, **keys) -> dict:
    """Contribution = 1 - SC_held / SC_full: on the medians across draws (the point estimate) and per draw (its
    interval). `small_full_sc` flags an SC too close to 0 for the ratio to mean anything."""
    full, held = full.align(held, join="inner")
    per_draw = (1 - held / full.where(full.abs() > 1e-12)).replace([np.inf, -np.inf], np.nan)
    med_full, med_held = float(full.median()), float(held.median())
    return {**keys, "sc_full_median": med_full, "sc_held_median": med_held,
            "contribution": 1 - med_held / med_full if abs(med_full) > 1e-12 else np.nan,
            **{f"per_draw_{k}": v for k, v in intervals(per_draw).items() if k not in ("mean", "n")},
            "small_full_sc": abs(med_full) < 1e-3}


def mechanism_decomposition(draws: pd.DataFrame, knobs: dict, neural: pd.DataFrame | None = None, year: int = 10,
                            outcomes=("K", "R", "M", "D", "unaided", "far", "retention", "G")) -> pd.DataFrame:
    """§11.5 from a `--mediate` run: for each AI scenario and mediator held at the paired traditional value (A17),
    the share of the scenario contrast that disappears. Behavioural outcomes use the SC per draw; the neural rows use
    mechanism D's mean network contrast. The shares of different mediators need not add up to 1."""
    c = draws[(draws["kind"] == "contrast") & (draws["draw_id"] >= 0) & (draws["year"] == year)]
    piv = c.pivot_table(index="draw_id", columns=["scenario", "outcome"], values="estimate")
    rows = []
    for s, k in knobs.items():
        for o in outcomes:
            if (k["base"], o) in piv and (s, o) in piv:
                rows.append(_contribution_row(piv[(k["base"], o)], piv[(s, o)], scenario=k["base"], mediator=k["mediator"],
                                              outcome=o, year=year))
    if neural is not None and len(neural):
        n = neural[(neural["mechanism"] == "D") & (neural["draw_id"] >= 0) & (neural["year"] == year)]
        npiv = n.pivot_table(index="draw_id", columns=["scenario", "network"], values="mean")
        for s, k in knobs.items():
            for net in n["network"].unique():
                if (k["base"], net) in npiv and (s, net) in npiv:
                    rows.append(_contribution_row(npiv[(k["base"], net)], npiv[(s, net)], scenario=k["base"],
                                                  mediator=k["mediator"], outcome=f"N_{net}", year=year))
    return pd.DataFrame(rows)


def hold_z_at_comparator(Z: np.ndarray, comparator: int = 0, n_cond: int = 3) -> np.ndarray:
    """The post hoc Z mediator (§11.5): every condition row of a unit replaced by the comparator's pattern, so an AI
    protocol's neural contrast keeps only what comes from behaviour (how much, how, when), not from its text."""
    n_units = len(Z) // n_cond
    blocks = np.asarray(Z).reshape(n_units, n_cond, -1)
    return np.repeat(blocks[:, [comparator]], n_cond, axis=1).reshape(Z.shape)


def z_mediator(run: Path, cfg: dict, root: Path, year: int = 10, mechanism: str = "D") -> pd.DataFrame:
    """§11.5 Z rows per AI scenario and network: the mean network contrast per draw with the real Z and with Z held
    at the traditional text, turned into contributions like `mechanism_decomposition`."""
    from . import plasticity as P
    from .longitudinal import read_arrays, read_table

    p = cfg["plasticity"]
    tribe_dir = Path(root) / p["tribe_dir"]
    arr = read_arrays(run, "mean_accumulator_diff")
    W, nets = P.load_networks(tribe_dir, p["network_weights"])
    Z = P.load_z(tribe_dir, int(p["wpm"]), p["metric"], p["winsorize"])[0]
    Zt = hold_z_at_comparator(Z, list(CONDITIONS).index("traditional"))
    lam = read_table(run, "parameter_draws").set_index("draw_id")["plasticity.lambda_O"]
    rows = []
    keep = (arr["draw_id"] >= 0) & (arr["year"] == year)
    for s in np.unique(arr["scenario"][keep]):
        idx = np.flatnonzero(keep & (arr["scenario"] == s))
        b = arr["draw_id"][idx]
        w = np.stack([P.mechanism_weights(mechanism, {**p, "lambda_O": float(lam.get(i, 0.0))}) for i in b])
        full, held = network_contrast(arr["diff"][idx], w, Z, W), network_contrast(arr["diff"][idx], w, Zt, W)
        for i, net in enumerate(nets):
            rows.append(_contribution_row(pd.Series(full[:, i], index=b), pd.Series(held[:, i], index=b), scenario=str(s),
                                          mediator="Z", outcome=f"N_{net}", year=year))
    return pd.DataFrame(rows)


# ------------------------------------------------------------------ §10.4 specification curve (S13)
def g_by_draw(draws: pd.DataFrame, weights: dict, year: int = 10) -> pd.DataFrame:
    """eq. 39 per draw and AI scenario for any outcome weights: G is linear in the K, R, M, D contrasts, so the
    draw's mean G under new weights is exact from the saved mean contrasts (no rerun)."""
    c = draws[(draws["kind"] == "contrast") & (draws["draw_id"] >= 0) & (draws["year"] == year)
              & draws["outcome"].isin(["K", "R", "M", "D"])]
    piv = c.pivot_table(index=["draw_id", "scenario"], columns="outcome", values="estimate")
    g = weights["K"] * piv["K"] + weights["R"] * piv["R"] + weights["M"] * piv["M"] - weights["D"] * piv["D"]
    return g.rename("G").reset_index()


SPEC_KEYS = ("tag", "form", "forgetting", "epw", "effort")


def spec_curve_g(runs: list[tuple[dict, pd.DataFrame]], weight_sets: dict, weight_ranks: dict, year: int = 10) -> pd.DataFrame:
    """Figure 8a rows: one per rerun specification x outcome weights x AI scenario, with the median and 95% interval
    across draws of the year-`year` G and the tier (the highest rank among the specification's levels)."""
    rows = []
    for spec, draws in runs:
        for wname, w in weight_sets.items():
            for s, grp in g_by_draw(draws, w, year).groupby("scenario"):
                rows.append({**{k: spec[k] for k in SPEC_KEYS}, "outcome_weights": wname, "scenario": s,
                             "tier": max(spec["tier"], weight_ranks[wname]), **intervals(grp["G"])})
    return pd.DataFrame(rows)


def spec_curve_neural(spec: dict, acc: dict, mean_diff: dict, lam_o: pd.Series, run_scenarios: list[str], zs: dict,
                      ws: dict, pcfg: dict, ranks: dict, year: int = 10, scenario: str = "substitution",
                      comparator: str = "traditional", network: str = "Cont") -> pd.DataFrame:
    """Figure 8b rows for one rerun specification: every post hoc level (reading speed x TRIBE metric x winsorising in
    `zs`, network weights in `ws`, mechanisms A-D) gives d for one network, `scenario` vs `comparator`. Per draw,
    d = the draw's mean contrast over all learners (`mean_accumulator_diff`) / the learner-level SD in the draw's
    subsample (`accumulators_subsample`, kept for the first draws only), so the interval is across those draws."""
    from . import plasticity as P

    S = len(run_scenarios)
    si, ci = run_scenarios.index(scenario), run_scenarios.index(comparator)
    md = {int(mean_diff["draw_id"][i]): i for i in range(len(mean_diff["draw_id"]))
          if mean_diff["year"][i] == year and mean_diff["scenario"][i] == scenario}
    sub = [i for i in range(len(acc["draw_id"])) if acc["year"][i] == year and int(acc["draw_id"][i]) >= 0
           and int(acc["draw_id"][i]) in md]
    if not sub:
        return pd.DataFrame()
    draws = [int(acc["draw_id"][i]) for i in sub]
    vals = acc["values"][sub]
    n_sub = vals.shape[1] // S
    dA = vals[:, si * n_sub:(si + 1) * n_sub].astype(float) - vals[:, ci * n_sub:(ci + 1) * n_sub]  # (B, n, 5, 90)
    mean_dA = np.stack([mean_diff["diff"][md[b]] for b in draws]).astype(float)  # (B, 5, 90)
    rows = []
    for mech in ("A", "B", "C", "D"):
        w = np.stack([P.mechanism_weights(mech, {**pcfg, "lambda_O": float(lam_o.get(b, 0.0))}) for b in draws])
        learner = np.einsum("bc,bncs->bns", w, dA)  # (B, n, 90)
        mean = np.einsum("bc,bcs->bs", w, mean_dA)  # (B, 90)
        for (wpm, metric, wins), Z in zs.items():
            for wname, (W, nets) in ws.items():
                proj = Z @ W[nets.index(network)]  # (90,)
                sd = (learner @ proj).std(axis=1, ddof=1)
                d = np.where(sd > 0, (mean @ proj) / np.where(sd > 0, sd, 1.0), 0.0)
                tier = max(spec["tier"], ranks["plasticity_mechanism"][mech], ranks["reading_speed_wpm"][wpm],
                           ranks["tribe_metric"][metric], ranks["winsorize"][wins], ranks["network_weights"][wname])
                rows.append({**{k: spec[k] for k in SPEC_KEYS}, "wpm": wpm, "metric": metric, "winsorize": wins,
                             "network_weights": wname, "mechanism": mech, "scenario": scenario, "network": network,
                             "tier": tier, **intervals(d)})
    return pd.DataFrame(rows)


# ------------------------------------------------------------------ §10.5 variance decomposition (S13, eq. 41)
def nested_variance(y: np.ndarray) -> dict:
    """Method-of-moments components of a balanced nested design y[scenario, draw, learner, replicate] (§10.5):
    V_behavior (between replicates of the same learner), V_learner, V_parameters (between draws) and V_scenario
    (between scenario means, corrected for the draw-level noise in them). Negative estimates are set to 0."""
    y = np.asarray(y, float)
    S, B, I, R = y.shape
    cell, sb = y.mean(axis=3), y.mean(axis=(2, 3))
    s = sb.mean(axis=1)
    ms_r = ((y - cell[..., None]) ** 2).sum() / (S * B * I * (R - 1))
    ms_i = R * ((cell - sb[..., None]) ** 2).sum() / (S * B * (I - 1))
    ms_b = I * R * ((sb - s[:, None]) ** 2).sum() / (S * (B - 1))
    # scenarios are fixed: their component is the population variance of the means, less the draw noise in them
    return {"scenario": max(0.0, float(s.var(ddof=0)) - (S - 1) / S * ms_b / (B * I * R)) if S > 1 else 0.0,
            "parameters": max(0.0, (ms_b - ms_i) / (I * R)), "learner": max(0.0, (ms_i - ms_r) / R),
            "behavior": float(ms_r), "total": float(y.var(ddof=1))}


def paired_learner_values(yearly: pd.DataFrame, gw: dict, network: str = "Cont", comparator: str = "traditional") -> pd.DataFrame:
    """Learner-level AI - comparator differences per draw and year: G (eq. 39 with weights `gw`) and N_<m>_<network>
    for every mechanism column present."""
    key = ["draw_id", "year", "learner_id"]
    base = yearly[yearly["scenario"] == comparator].set_index(key)
    cols = ["K", "R", "M", "D"] + [c for c in yearly.columns if c.startswith("N_") and c.endswith(f"_{network}")]
    out = []
    for s, g in yearly[yearly["scenario"] != comparator].groupby("scenario"):
        d = g.set_index(key)[cols] - base[cols]
        d["G"] = gw["K"] * d["K"] + gw["R"] * d["R"] + gw["M"] * d["M"] - gw["D"] * d["D"]
        out.append(d.assign(scenario=s).reset_index())
    return pd.concat(out, ignore_index=True)


def replicate_array(paired: list[pd.DataFrame], value: str, scenarios: list[str], year: int = 10) -> np.ndarray:
    """y[scenario, draw, learner, replicate] from each replicate's `paired_learner_values` (the same learners in
    every replicate, D19); learners missing in any cell are dropped so the design stays balanced."""
    frames = []
    for r, t in enumerate(paired):
        t = t[(t["year"] == year) & (t["draw_id"] >= 0) & t["scenario"].isin(scenarios)]
        frames.append(t.set_index(["scenario", "draw_id", "learner_id"])[value].rename(r))
    wide = pd.concat(frames, axis=1, join="inner")
    draws_ = sorted(wide.index.get_level_values("draw_id").unique())
    learners = sorted(wide.index.get_level_values("learner_id").unique())
    wide = wide.reindex(pd.MultiIndex.from_product([scenarios, draws_, learners], names=wide.index.names))
    ok = wide.notna().all(axis=1).groupby(level="learner_id").all()
    learners = [i for i in learners if ok[i]]
    wide = wide.reindex(pd.MultiIndex.from_product([scenarios, draws_, learners], names=wide.index.names))
    return wide.to_numpy(float).reshape(len(scenarios), len(draws_), len(learners), len(paired))


def neural_scale(paired: list[pd.DataFrame], column: str, year: int = 10) -> float:
    """Pooled learner-level SD of a neural paired difference (mean over scenario x draw cells): the unit that makes
    mechanisms A-D, whose N scales are arbitrary, comparable (eq. 44 is scale-free for the same reason)."""
    allp = pd.concat([p[(p["year"] == year) & (p["draw_id"] >= 0)] for p in paired])
    return float(allp.groupby(["scenario", "draw_id"])[column].std().mean())


def variance_decomposition(paired: list[pd.DataFrame], scenarios: list[str], year: int = 10, network: str = "Cont",
                           v_stimulus: float | None = None) -> pd.DataFrame:
    """eq. 41 for the year-`year` G and mechanism D's `network` contrast (in units of its pooled learner-level SD).
    V_plasticity: variance across mechanisms A-D of the scenario-mean standardised contrast, averaged over scenarios;
    half-life and lambda_O are drawn per draw and so sit in V_parameters. V_stimulus: the unit bootstrap of Z
    (`stimulus_bootstrap`, same units). G has no neural term, so both are 0 for it. V_residual = total variance of
    the learner-level values - the four nested components; shares are of total + V_plasticity + V_stimulus."""
    rows = []
    for outcome in ("G", f"N_D_{network}"):
        if outcome not in paired[0]:
            continue
        neural = outcome.startswith("N_")
        scale = neural_scale(paired, outcome, year) if neural else 1.0
        y = replicate_array([p.assign(v=p[outcome] / scale) for p in paired], "v", scenarios, year)
        comp = nested_variance(y)
        extra = {"plasticity": 0.0, "stimulus": 0.0}
        if neural:
            allp = pd.concat([p[(p["year"] == year) & (p["draw_id"] >= 0)] for p in paired])
            means = [allp.groupby("scenario")[f"N_{m}_{network}"].mean() / neural_scale(paired, f"N_{m}_{network}", year)
                     for m in "ABCD" if f"N_{m}_{network}" in allp]
            extra["plasticity"] = float(pd.concat(means, axis=1).var(axis=1, ddof=1).mean()) if len(means) > 1 else 0.0
            extra["stimulus"] = float(v_stimulus) if v_stimulus is not None else np.nan
        parts = {k: comp[k] for k in ("scenario", "parameters", "learner", "behavior")}
        parts.update(extra, residual=comp["total"] - sum(parts.values()))
        denom = comp["total"] + extra["plasticity"] + (extra["stimulus"] if np.isfinite(extra["stimulus"]) else 0.0)
        label = "G" if not neural else f"d_{network} (mechanism D)"
        for name, v in parts.items():
            rows.append({"outcome": label, "year": year, "component": name, "variance": v,
                         "share": v / denom if denom > 0 else np.nan, "n_scenarios": y.shape[0], "n_draws": y.shape[1],
                         "n_learners": y.shape[2], "n_replicates": y.shape[3]})
    return pd.DataFrame(rows)


def stimulus_bootstrap(mean_diff: dict, lam_o: pd.Series, Z: np.ndarray, W: np.ndarray, nets: list[str], pcfg: dict,
                       scale: float, year: int = 10, network: str = "Cont", n_boot: int = 200, seed: int = 0,
                       n_cond: int = 3) -> float:
    """V_stimulus (A18): resample the units with replacement (all conditions of a unit together), recompute each
    scenario's mean mechanism-D contrast over draws, divide by `scale` (the neural outcome's learner-level SD) and
    return the bootstrap variance, averaged over scenarios."""
    from . import plasticity as P

    keep = (mean_diff["draw_id"] >= 0) & (mean_diff["year"] == year)
    n_units = Z.shape[0] // n_cond
    proj = (Z @ W[nets.index(network)]).reshape(n_units, n_cond)
    rng = np.random.default_rng(seed)
    out = []
    for s in np.unique(mean_diff["scenario"][keep]):
        idx = np.flatnonzero(keep & (mean_diff["scenario"] == s))
        w = np.stack([P.mechanism_weights("D", {**pcfg, "lambda_O": float(lam_o.get(b, 0.0))}) for b in mean_diff["draw_id"][idx]])
        x = np.einsum("bc,bcs->bs", w, mean_diff["diff"][idx].astype(float)).mean(axis=0).reshape(n_units, n_cond)
        per_unit = (x * proj).sum(axis=1)
        boots = per_unit[rng.integers(0, n_units, (n_boot, n_units))].sum(axis=1) / scale
        out.append(boots.var(ddof=1))
    return float(np.mean(out))

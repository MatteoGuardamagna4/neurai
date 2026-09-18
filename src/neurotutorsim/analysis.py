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

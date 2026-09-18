"""Rebuild every table and figure of the brief's §13 from saved outputs (no simulation, no manual step).

    python -m neurotutorsim.report phase12                 # Tables 1-4, Figures 1-4, gate-19 definitions
    python -m neurotutorsim.report gate18 --pilot v_pilot --zero-plasticity v_pilot_z0 --zero-effort v_pilot_e0
    python -m neurotutorsim.report engines                 # §10.2: centaur_main vs logistic_40 (Figure S1)
    python -m neurotutorsim.report all

Tables go to outputs/tables/*.csv, figures to outputs/figures/*.png and .pdf. Every figure has a CSV twin.
Colours follow the dataviz reference palette (categorical slots in fixed order, validated for these uses):
traditional / scaffolding / substitution are slots 1-3; magnitudes use one blue ramp; signed contrasts use
blue <-> red around a gray midpoint. Labels follow brief §15.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from . import analysis as A
from . import tribe
from .corpus import CONDITIONS

# ------------------------------------------------------------------ style (dataviz reference palette, light surface)
INK, INK2, MUTED, GRID, AXIS, SURFACE = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7", "#fcfcfb"
SERIES = ("#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948")
COND_COLOR = dict(zip(CONDITIONS, SERIES))
COND_LABEL = {"traditional": "Traditional", "ai_scaffolding": "AI scaffolding", "ai_substitution": "AI substitution"}
NETWORK_LABEL = {"Vis": "Visual", "SomMot": "Somatomotor", "DorsAttn": "Dorsal attention",
                 "SalVentAttn": "Salience / ventral attention", "Limbic": "Limbic", "Cont": "Control", "Default": "Default mode"}
BLUE_RAMP = ("#cde2fb", "#b7d3f6", "#9ec5f4", "#86b6ef", "#6da7ec", "#5598e7", "#3987e5", "#2a78d6", "#256abf",
             "#1c5cab", "#184f95", "#104281", "#0d366b")
DIVERGING = ("#2a78d6", "#f0efec", "#e34948")


def plt_setup():
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update({
        "font.family": ["Segoe UI", "DejaVu Sans", "sans-serif"], "font.size": 9, "text.color": INK,
        "axes.edgecolor": AXIS, "axes.linewidth": 0.8, "axes.labelcolor": INK2, "axes.titlecolor": INK,
        "axes.titlesize": 10, "axes.titleweight": "bold", "axes.titlelocation": "left",
        "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "axes.axisbelow": True,
        "grid.color": GRID, "grid.linewidth": 0.8, "grid.linestyle": "-",
        "xtick.color": MUTED, "ytick.color": MUTED, "xtick.labelcolor": INK2, "ytick.labelcolor": INK2,
        "lines.linewidth": 2.0, "lines.solid_capstyle": "round", "lines.solid_joinstyle": "round",
        "legend.frameon": False, "legend.fontsize": 8.5, "legend.labelcolor": INK2,
        "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
        "savefig.dpi": 200, "savefig.bbox": "tight",
    })
    return plt


def save(fig, out: Path, name: str) -> list[Path]:
    out.mkdir(parents=True, exist_ok=True)
    paths = [out / f"{name}.png", out / f"{name}.pdf"]
    for p in paths:
        fig.savefig(p)
    fig.clf()
    return paths


class Paths:
    def __init__(self, root: Path):
        self.root = Path(root)
        cfg = yaml.safe_load((self.root / "config" / "default.yaml").read_text(encoding="utf-8"))
        self.raw = cfg
        self.tribe = self.root / cfg["plasticity"]["tribe_dir"]
        self.processed = self.root / cfg["run"]["processed_dir"]
        self.tables = self.root / "outputs" / "tables"
        self.figures = self.root / "outputs" / "figures"
        self.tables.mkdir(parents=True, exist_ok=True)
        self.figures.mkdir(parents=True, exist_ok=True)

    def table(self, frame: pd.DataFrame, name: str) -> Path:
        p = self.tables / f"{name}.csv"
        frame.to_csv(p, index=False)
        return p


# ------------------------------------------------------------------ Tables 1-3
def table1(stimuli: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    """Instructional conditions and what is held fixed versus what varies (brief §3.3, §13 Table 1)."""
    s = cfg["support"]
    means = stimuli.groupby("condition")[["word_count", "duration", "equation_count", "sentence_count"]].mean()
    rows = {
        "traditional": ("fixed explanation, one worked example, three prewritten hints", "hint k shown after a wrong answer, then answer or ask for the next hint",
                        "after the third hint (worked solution)"),
        "ai_scaffolding": ("explanation written as guided questions", "LLM tutor turn k: diagnosis, one question, a level-k hint; leakage-checked",
                           "after the third tutor turn (worked solution)"),
        "ai_substitution": ("explanation that walks through the complete solution", "one LLM message with the complete solution, then one re-answer",
                            "immediately after the first wrong answer"),
    }
    out = []
    for c in CONDITIONS:
        lesson, help_, reveal = rows[c]
        out.append({"condition": COND_LABEL[c], "lesson": lesson, "help after a wrong answer": help_, "answer provided": reveal,
                    "adaptation (eq. 20)": s["adaptation"][c], "help turns (persistent)": s["max_hints"],
                    "mean words": round(means.loc[c, "word_count"], 1), "mean duration s (220 wpm)": round(means.loc[c, "duration"], 1),
                    "mean equations": round(means.loc[c, "equation_count"], 2), "mean sentences": round(means.loc[c, "sentence_count"], 1),
                    "held fixed across conditions": "unit, concept, domain, difficulty, problem and answer options, near and far transfer items, no help before the first attempt, 3-option format",
                    "varies by design": "explanation style and the support after an error"})
    return pd.DataFrame(out)


COMPONENTS = [
    ("Corpus (Phase I)", "30 authored units (15 concepts x 2) in 4 MBA domains", "90 stimuli, validators, matching features",
     "30 units instead of 120 in two domains; semantic coverage not computed (eq. 20 uses 1.0)", "validators on every answer; calipers; SMD table (§11.1)"),
    ("TRIBE v2 (Phase II)", "stimulus text, eq. 4 word timing at 220 wpm (180/260 robustness)", "predicted BOLD per vertex, Schaefer-400 parcels, 7 networks, §6.5 metrics",
     "text only; fixed lesson texts, never the live tutor turns", "official demo reproduced (gate 17); determinism within 1e-3; shuffled-text controls"),
    ("Synthetic learner (Phase III)", "eq. 15-16 population; observable history", "choices, correctness, confidence, proxies, eq. 19-25 states",
     "every parameter an assumption; Centaur/Minitaur only choose (at chance on arithmetic)", "§10.2 monotonicity, difficulty, support, forgetting, fading; engine comparison"),
    ("Plasticity (Phase IV)", "Z (eq. 28) and per-episode E, PE, resolution, retrieval, offloading", "model-implied N per parcel and network (eq. 29-33)",
     "N is not a brain state; half-life, lambdas, eta are assumptions", "zero-plasticity null; permuted-Z and permuted-condition controls"),
    ("Scenarios (Phase V)", "parameter draws (Triangular within low-high), 5 scenarios, calendar", "1/5/10-year levels, paired SC, PrSup, G, neural d",
     "soft limits (D3); weekly forgetting with breaks (D4); free choice from a softmax in D", "gate 18; T1 equivalence with the Phase III loop; CRN null"),
]


def table2() -> pd.DataFrame:
    return pd.DataFrame(COMPONENTS, columns=["component", "inputs", "outputs", "key assumptions", "validation"])


BRIEF_SOURCED = {  # config paths whose value the brief fixes; everything else is labelled an assumption
    "population.stratum_weights": "brief §7.2", "plasticity.wpm": "brief §6.2", "plasticity.winsorize": "brief §8.2",
    "plasticity.lambda": "brief §8.6 (non-negative, sum to one; equal split assumed)", "calendar.weeks_per_year": "brief §9.1",
    "calendar.episodes_per_week": "brief §9.1", "phase5.years": "brief §9", "phase5.draws": "brief §9.3 (fallback size)",
    "phase5.learners_per_draw": "brief §9.3 (fallback size)", "phase5.G": "brief §9.6 (equal weights)", "support.max_hints": "brief §3.3",
    "population.n_learners": "brief §7.1 (>= 5,000 learner-runs per arm)",
}


def table3(raw: dict) -> pd.DataFrame:
    """Every numeric parameter: low / medium / high or its fixed value, how Phase V draws it, and its source label."""
    rows = []

    def walk(node, path):
        if isinstance(node, dict):
            if set(node) == {"low", "medium", "high"}:
                lo, hi = min(node["low"], node["high"]), max(node["low"], node["high"])
                rows.append({"parameter": path, "low": node["low"], "medium": node["medium"], "high": node["high"],
                             "phase V draw": f"Triangular({lo}, {node['medium']}, {hi})", "source": source(path)})
                return
            for k, v in node.items():
                walk(v, f"{path}.{k}" if path else k)
        elif isinstance(node, (int, float)) and not isinstance(node, bool):
            rows.append({"parameter": path, "low": np.nan, "medium": node, "high": np.nan, "phase V draw": "fixed", "source": source(path)})
        elif isinstance(node, list) and node and all(isinstance(x, (int, float)) for x in node):
            rows.append({"parameter": path, "low": np.nan, "medium": json.dumps(node), "high": np.nan, "phase V draw": "fixed", "source": source(path)})

    def source(path):
        for key, label in BRIEF_SOURCED.items():
            if path == key or path.startswith(key + "."):
                return label
        return "assumption"

    for block in ("population", "curriculum", "response", "effort", "effectiveness", "updates", "calendar", "plasticity",
                  "support", "checkpoints", "phase5"):
        walk(raw[block], block)
    return pd.DataFrame(rows)


# ------------------------------------------------------------------ Figures 1-4
def figure1(plt, out: Path) -> list[Path]:
    """Conceptual pipeline: material -> predicted response -> learner update -> plasticity -> scenario (brief §13)."""
    from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

    W, H = 2.0, 1.0
    fig, ax = plt.subplots(figsize=(11, 3.3))
    ax.set_axis_off()
    ax.set_xlim(0, 11.3)
    ax.set_ylim(0, 3.3)
    boxes = {
        "Educational material": (0.1, 2.05, "30 units x 3 conditions\nmatched length and duration"),
        "TRIBE v2": (2.35, 2.05, "predicted cortical response\nSchaefer-400, 7 networks"),
        "Standardised pattern Z": (4.6, 2.05, "eq. 28, per parcel\nover the 90 stimuli"),
        "Simulated learner": (0.1, 0.25, "choices: Centaur or logistic\ncorrectness: eq. 17-18"),
        "Learner update": (2.35, 0.25, "effort, effectiveness\nK, M, R, C, D (eq. 19-25)"),
        "Plasticity update": (4.6, 0.25, "model-implied N\neq. 29-33"),
        "Ten-year scenarios": (6.95, 1.15, "5 scenarios x parameter draws\nweekly calendar with breaks"),
        "Scenario contrasts": (9.2, 1.15, "SC, PrSup, G (eq. 37-39)\nfrontier, tipping points"),
    }
    for title, (x, y, body) in boxes.items():
        ax.add_patch(FancyBboxPatch((x, y), W, H, boxstyle="round,pad=0.02,rounding_size=0.08", fc="#f0efec", ec=AXIS, lw=0.8))
        ax.text(x + 0.1, y + 0.75, title, fontsize=8.8, fontweight="bold", color=INK, va="center")
        ax.text(x + 0.1, y + 0.33, body, fontsize=7.6, color=INK2, va="center", linespacing=1.35)

    def arrow(p0, p1):
        ax.add_patch(FancyArrowPatch(p0, p1, arrowstyle="-|>", mutation_scale=10, lw=1.2, color=INK2, shrinkA=1, shrinkB=1))

    def right(name, dy=0.5):
        x, y, _ = boxes[name]
        return (x + W, y + dy)

    def left(name, dy=0.5):
        x, y, _ = boxes[name]
        return (x, y + dy)

    def bottom(name):
        x, y, _ = boxes[name]
        return (x + W / 2, y)

    def top(name):
        x, y, _ = boxes[name]
        return (x + W / 2, y + H)

    arrow(right("Educational material"), left("TRIBE v2"))
    arrow(right("TRIBE v2"), left("Standardised pattern Z"))
    arrow(bottom("Educational material"), top("Simulated learner"))
    arrow(right("Simulated learner"), left("Learner update"))
    arrow(right("Learner update"), left("Plasticity update"))
    arrow(bottom("Standardised pattern Z"), top("Plasticity update"))
    arrow(right("Plasticity update", 0.7), left("Ten-year scenarios", 0.3))
    arrow(right("Standardised pattern Z", 0.3), left("Ten-year scenarios", 0.7))
    arrow(right("Ten-year scenarios"), left("Scenario contrasts"))
    ax.set_title("Figure 1. From educational material to long-term scenario (all quantities predicted or model-implied)", fontsize=10)
    return save(fig, out, "fig1_pipeline")


def figure2(plt, balance: pd.DataFrame, stimuli: pd.DataFrame, out: Path) -> list[Path]:
    """Corpus matching diagnostics (§11.1): SMD per feature and pair with the +-0.10 target, and the per-unit
    duration differences against the 10% caliper."""
    fig, (a, b) = plt.subplots(1, 2, figsize=(10, 4.2), gridspec_kw={"width_ratios": [1.4, 1]})
    feats = list(balance["feature"])[::-1]
    y = np.arange(len(feats))
    a.axvspan(-A.SMD_TARGET, A.SMD_TARGET, color=SERIES[0], alpha=0.10, lw=0)
    a.axvline(0, color=AXIS, lw=0.8)
    style = {"S-T": (COND_COLOR["ai_scaffolding"], "o", "AI scaffolding - traditional"),
             "U-T": (COND_COLOR["ai_substitution"], "s", "AI substitution - traditional"),
             "S-U": (MUTED, "D", "AI scaffolding - AI substitution")}
    for i, (pair, (color, marker, label)) in enumerate(style.items()):
        vals = balance.set_index("feature").loc[feats, f"smd_{pair}"].to_numpy(float)
        a.scatter(np.clip(vals, -2, 2), y + (i - 1) * 0.22, s=36, color=color, marker=marker, label=label,
                  edgecolor=SURFACE, linewidth=1.5, zorder=3)
    a.set_yticks(y, [f.replace("_", " ") for f in feats])
    a.set_xlabel("standardised mean difference (eq. 3)")
    a.set_title("SMD per matching feature (shaded: |SMD| < 0.10 target)")
    a.legend(loc="upper left")
    wide = stimuli.pivot_table(index="unit_id", columns="condition", values="duration")
    for j, c in enumerate(("ai_scaffolding", "ai_substitution")):
        rel = 100 * (wide[c] - wide["traditional"]) / wide["traditional"]
        jitter = np.random.default_rng(j).uniform(-0.12, 0.12, len(rel))
        b.scatter(np.full(len(rel), j) + jitter, rel, s=30, color=COND_COLOR[c], edgecolor=SURFACE, linewidth=1.5, zorder=3,
                  label=COND_LABEL[c])
    b.axhspan(-10, 10, color=SERIES[0], alpha=0.10, lw=0)
    b.axhline(0, color=AXIS, lw=0.8)
    b.set_xticks([0, 1], ["AI scaffolding", "AI substitution"])
    b.set_xlim(-0.6, 1.6)
    b.set_ylim(-14, 14)
    b.set_ylabel("duration vs traditional, % (per unit)")
    b.set_title("Duration caliper per unit (shaded: within 10%)")
    b.grid(axis="x", visible=False)
    fig.suptitle("Figure 2. Corpus matching diagnostics (descriptive; semantic coverage not computed)", x=0.01, ha="left",
                 fontsize=10, fontweight="bold", color=INK)
    fig.tight_layout()
    return save(fig, out, "fig2_corpus_balance")


def figure3(plt, metrics: pd.DataFrame, out: Path, metric: str = "auc") -> tuple[list[Path], pd.DataFrame]:
    """Predicted network-level responses per condition (§11.2): thin lines join each unit's three stimuli; the
    coloured points are condition means with 95% bootstrap intervals over units."""
    net = metrics[(metrics["level"] == "network") & (metrics["metric"] == metric)]
    wide = net.pivot_table(index=["key", "unit_id"], columns="condition", values="value")
    fig, axes = plt.subplots(2, 4, figsize=(11, 5.6), sharex=True)
    rows = []
    for ax, key in zip(axes.ravel(), tribe.NETWORKS):
        w = wide.loc[key][list(CONDITIONS)]
        for _, r in w.iterrows():
            ax.plot(range(3), r.to_numpy(float), color=AXIS, lw=0.6, alpha=0.55, zorder=1)
        for i, c in enumerate(CONDITIONS):
            m, (lo, hi) = w[c].mean(), A.bootstrap_ci(w[c].to_numpy(float))
            ax.errorbar(i, m, yerr=[[m - lo], [hi - m]], fmt="o", ms=7, color=COND_COLOR[c], mec=SURFACE, mew=1.5,
                        elinewidth=2, capsize=0, zorder=3)
            rows.append({"network": key, "condition": c, "mean": m, "ci_low": lo, "ci_high": hi, "n_units": len(w)})
        ax.set_title(NETWORK_LABEL[key], fontsize=9)
        ax.set_xticks(range(3), ["Trad.", "Scaff.", "Subst."])
        ax.set_xlim(-0.4, 2.4)
        ax.grid(axis="x", visible=False)
    legend_ax = axes.ravel()[-1]
    legend_ax.set_axis_off()
    for c in CONDITIONS:
        legend_ax.plot([], [], "o", ms=7, color=COND_COLOR[c], label=COND_LABEL[c])
    legend_ax.plot([], [], color=AXIS, lw=0.8, label="one unit (paired)")
    legend_ax.legend(loc="center left", title="mean, 95% bootstrap CI", title_fontsize=8.5)
    for ax in axes[:, 0]:
        ax.set_ylabel(f"predicted response {metric.upper()} (a.u. x s)")
    fig.suptitle(f"Figure 3. Predicted network-level responses by condition (TRIBE v2, 220 wpm, area-weighted {metric.upper()})",
                 x=0.01, ha="left", fontsize=10, fontweight="bold", color=INK)
    fig.tight_layout()
    return save(fig, out, "fig3_network_responses"), pd.DataFrame(rows)


def figure4(plt, patterns: pd.DataFrame, units: pd.DataFrame, differentiation: pd.DataFrame, out: Path) -> tuple[list[Path], pd.DataFrame]:
    """Representational dissimilarity matrices per condition (eq. 14), units ordered by concept."""
    from matplotlib.colors import LinearSegmentedColormap

    by_cond, ids, concepts = A.unit_patterns(patterns, units)
    rdms = {c: tribe.rdm(z) for c, z in by_cond.items()}
    vmax = float(np.quantile(np.concatenate([r[np.triu_indices(len(ids), 1)] for r in rdms.values()]), 0.98))
    cmap = LinearSegmentedColormap.from_list("blue_ramp", BLUE_RAMP)
    fig, axes = plt.subplots(1, 3, figsize=(12.5, 4.6))
    starts = [i for i in range(len(concepts)) if i == 0 or concepts[i] != concepts[i - 1]]
    for ax, c in zip(axes, CONDITIONS):
        im = ax.imshow(rdms[c], cmap=cmap, vmin=0, vmax=vmax, interpolation="nearest")
        for s in starts[1:]:
            ax.axhline(s - 0.5, color=SURFACE, lw=1.2)
            ax.axvline(s - 0.5, color=SURFACE, lw=1.2)
        d = differentiation.set_index("condition").loc[c, "differentiation"]
        ax.set_title(f"{COND_LABEL[c]}  (differentiation {d:.3f})", fontsize=9)
        centers = [(s + (starts[k + 1] if k + 1 < len(starts) else len(concepts))) / 2 - 0.5 for k, s in enumerate(starts)]
        ax.set_xticks(centers, [concepts[s].replace("_", " ") for s in starts], rotation=90, fontsize=6.5)
        ax.set_yticks(centers, [concepts[s].replace("_", " ") for s in starts] if c == CONDITIONS[0] else [], fontsize=6.5)
        ax.grid(False)
        for spine in ax.spines.values():
            spine.set_visible(False)
    cb = fig.colorbar(im, ax=axes, fraction=0.02, pad=0.01)
    cb.set_label("1 - correlation of parcel patterns (eq. 14)", color=INK2)
    cb.outline.set_visible(False)
    fig.suptitle("Figure 4. Representational dissimilarity of predicted parcel patterns by condition (units ordered by concept)",
                 x=0.01, ha="left", fontsize=10, fontweight="bold", color=INK)
    rows = [{"condition": c, "unit_a": ids[i], "unit_b": ids[j], "dissimilarity": float(rdms[c][i, j])}
            for c in CONDITIONS for i in range(len(ids)) for j in range(i + 1, len(ids))]
    return save(fig, out, "fig4_rdm"), pd.DataFrame(rows)


def figure_parcels(plt, parcels: pd.DataFrame, parcel_table: pd.DataFrame, out: Path) -> list[Path]:
    """Supplementary parcel map: per-parcel condition contrasts grouped by network, BH-FDR over 400 x 3 tests
    (a strip plot instead of a brain surface, which would need a new dependency)."""
    p = parcels.merge(parcel_table[["parcel_id", "network"]].assign(key=lambda d: d["parcel_id"].astype(str)), on="key")
    fig, axes = plt.subplots(1, 3, figsize=(12, 4.2), sharey=True)
    colour = {"S-T": COND_COLOR["ai_scaffolding"], "U-T": COND_COLOR["ai_substitution"], "S-U": COND_COLOR["traditional"]}
    title = {"S-T": "AI scaffolding - traditional", "U-T": "AI substitution - traditional", "S-U": "AI scaffolding - AI substitution"}
    for ax, name in zip(axes, ("S-T", "U-T", "S-U")):
        d = p[p["contrast"] == name]
        for i, net in enumerate(tribe.NETWORKS):
            g = d[d["network"] == net]
            x = i + np.random.default_rng(i).uniform(-0.28, 0.28, len(g))
            sig = g["q_fdr"].to_numpy() < 0.05
            ax.scatter(x[~sig], g["estimate"][~sig], s=9, color=AXIS, lw=0, zorder=2)
            ax.scatter(x[sig], g["estimate"][sig], s=12, color=colour[name], lw=0, zorder=3)
        ax.axhline(0, color=INK2, lw=0.8)
        ax.set_xticks(range(7), [NETWORK_LABEL[n].split(" /")[0] for n in tribe.NETWORKS], rotation=35, ha="right")
        ax.set_title(f"{title[name]}  ({int((d['q_fdr'] < 0.05).sum())} of {len(d)} parcels q < 0.05)", fontsize=9)
        ax.grid(axis="x", visible=False)
    axes[0].set_ylabel("per-parcel AUC contrast (eq. 13)")
    axes[0].scatter([], [], s=12, color=INK2, label="q < 0.05 (BH over 1,200 tests)")
    axes[0].scatter([], [], s=9, color=AXIS, label="not significant")
    axes[0].legend(loc="lower left")
    fig.suptitle("Figure S2. Parcel-level contrasts in predicted AUC, grouped by network", x=0.01, ha="left",
                 fontsize=10, fontweight="bold", color=INK)
    fig.tight_layout()
    return save(fig, out, "figS2_parcel_contrasts")


def phase12(paths: Paths, n_boot: int = 2000) -> list[Path]:
    """Everything that needs only the corpus (Phase I) and the TRIBE run (Phase II)."""
    plt = plt_setup()
    written = []
    stimuli = pd.read_csv(paths.processed / "stimuli.csv")
    units = pd.read_csv(paths.processed / "units.csv")
    metrics = pd.read_parquet(paths.tribe / "wpm220" / "tribe_metrics.parquet")
    patterns = pd.read_parquet(paths.tribe / "wpm220" / "tribe_patterns.parquet")
    parcel_table = pd.read_csv(paths.tribe / "parcels_schaefer400.csv")

    written.append(paths.table(table1(stimuli, paths.raw), "table1_conditions"))
    written.append(paths.table(table2(), "table2_components"))
    written.append(paths.table(table3(paths.raw), "table3_parameters"))
    written.append(paths.table(A.metric_definitions(), "gate19_metric_definitions"))
    balance = A.corpus_balance(stimuli)
    written.append(paths.table(balance, "corpus_balance"))
    t4 = A.table4(metrics, n_boot=n_boot)
    written.append(paths.table(t4, "table4_cortical_contrasts"))
    t4c = A.table4(metrics, covariates=A.matching_covariates(stimuli), n_boot=n_boot)
    written.append(paths.table(t4c, "table4_cortical_contrasts_matched_covariates"))
    written.append(paths.table(pd.concat([A.eq42(metrics, units, lvl, m) for lvl in ("network", "parcel") for m in ("auc", "mean")]),
                               "table4_eq42_mixed_model"))
    parcels = A.parcel_contrasts(metrics, "auc", n_boot=n_boot)
    written.append(paths.table(parcels, "parcel_contrasts_auc"))
    agreement, differentiation = A.rsa_summary(patterns, units)
    written.append(paths.table(agreement, "rsa_condition_agreement"))
    written.append(paths.table(differentiation, "rsa_differentiation"))
    controls = pd.read_csv(paths.tribe / "controls" / "tribe_controls_shuffled.csv")
    written.append(paths.table(A.shuffle_controls(controls, t4), "tribe_shuffle_controls"))
    speeds = []
    for wpm in (180, 260):
        other = paths.tribe / f"wpm{wpm}" / "tribe_metrics.parquet"
        if other.exists():
            speeds.append(A.table4(pd.read_parquet(other), n_boot=n_boot).assign(wpm=wpm))
    if speeds:
        written.append(paths.table(pd.concat([t4.assign(wpm=220), *speeds]), "table4_reading_speed_robustness"))

    written += figure1(plt, paths.figures)
    written += figure2(plt, balance, stimuli, paths.figures)
    fig3, fig3_table = figure3(plt, metrics, paths.figures)
    written += fig3 + [paths.table(fig3_table, "fig3_network_responses")]
    fig4, fig4_table = figure4(plt, patterns, units, differentiation, paths.figures)
    written += fig4 + [paths.table(fig4_table, "fig4_rdm")]
    written += figure_parcels(plt, parcels, parcel_table, paths.figures)
    return written


# ------------------------------------------------------------------ S7 and gate 18
def engines(paths: Paths, a_tag: str = "centaur_main", b_tag: str = "logistic_40") -> list[Path]:
    """§10.2 engine comparison table and Figure S1 (paired learner differences per condition)."""
    plt = plt_setup()
    a_dir, b_dir = paths.processed / a_tag, paths.processed / b_tag
    comp = A.engine_comparison(a_dir, b_dir)
    written = [paths.table(comp, "engine_comparison")]
    shares = pd.concat([A.free_choice_shares(d).assign(engine=name) for name, d in (("centaur", a_dir), ("logistic", b_dir))])
    written.append(paths.table(shares, "engine_free_choice_shares"))
    paired = comp[comp["section"] == "paired difference"]
    outcomes = ["first_try", "transfer", "reveal", "help_per_episode", "effort", "K", "D", "C"]
    fig, ax = plt.subplots(figsize=(9, 4.4))
    conds = list(CONDITIONS) + ["free_choice"]
    colours = dict(COND_COLOR, free_choice=SERIES[3])
    for i, c in enumerate(conds):
        d = paired[paired["condition"] == c].set_index("outcome").reindex(outcomes)
        y = np.arange(len(outcomes)) + (i - 1.5) * 0.18
        ax.errorbar(d["difference"], y, xerr=[d["difference"] - d["ci_low"], d["ci_high"] - d["difference"]], fmt="o", ms=6,
                    color=colours[c], mec=SURFACE, mew=1.5, elinewidth=1.6, capsize=0, label=COND_LABEL.get(c, "Free choice"))
    ax.axvline(0, color=INK2, lw=0.8)
    ax.set_yticks(range(len(outcomes)), [o.replace("_", " ") for o in outcomes])
    ax.set_xlabel(f"{a_tag} - {b_tag}, mean paired difference over 40 learners (95% bootstrap CI)")
    ax.legend(loc="lower right")
    ax.set_title("Figure S1. Centaur-chosen behaviour versus the logistic baseline on the same learners (descriptive)")
    return written + save(fig, paths.figures, "figS1_engine_comparison")


def gate18_report(paths: Paths, pilot: str, z0: str | None, e0: str | None, crn: str | None, breaks: list[str]) -> list[Path]:
    base = paths.processed / "phase5"
    brk = {}
    for item in breaks:
        weeks, tag = item.split("=", 1)
        brk[int(weeks)] = base / tag
    table = A.gate18(base / pilot, base / z0 if z0 else None, base / e0 if e0 else None, base / crn if crn else None, brk or None)
    print(table.to_string(index=False))
    return [paths.table(table, "gate18_checks")]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("what", choices=("phase12", "engines", "gate18", "all"))
    ap.add_argument("--root", default=".")
    ap.add_argument("--n-boot", type=int, default=2000, dest="n_boot")
    ap.add_argument("--pilot", default="v_pilot")
    ap.add_argument("--zero-plasticity", default="v_pilot_z0", dest="z0")
    ap.add_argument("--zero-effort", default="v_pilot_e0", dest="e0")
    ap.add_argument("--crn", default=None)
    ap.add_argument("--breaks", nargs="*", default=[], help="WEEKS=TAG runs of the central draw, e.g. 4=v_break4 24=v_break24")
    args = ap.parse_args(argv)
    paths = Paths(Path(args.root).resolve())
    written = []
    if args.what in ("phase12", "all"):
        written += phase12(paths, args.n_boot)
    if args.what in ("engines", "all") and (paths.processed / "centaur_main" / "learner_state.parquet").exists():
        written += engines(paths)
    if args.what in ("gate18", "all") and (paths.processed / "phase5" / args.pilot / "run.json").exists():
        written += gate18_report(paths, args.pilot, args.z0, args.e0, args.crn, args.breaks)
    for p in written:
        print(p.relative_to(paths.root))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

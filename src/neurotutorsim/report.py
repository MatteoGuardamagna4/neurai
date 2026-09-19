"""Rebuild every table and figure of the brief's §13 from saved outputs (no simulation, no manual step).

    python -m neurotutorsim.report phase12                 # Tables 1-4, Figures 1-4, gate-19 definitions
    python -m neurotutorsim.report gate18 --pilot v_pilot --zero-plasticity v_pilot_z0 --zero-effort v_pilot_e0
    python -m neurotutorsim.report engines                 # §10.2: centaur_main vs logistic_40 (Figure S1)
    python -m neurotutorsim.report phase5 --run v_main     # Table 5, Figures 5-6 (+ v_main_fcc's sixth scenario)
    python -m neurotutorsim.report exposure|frontier|mechanisms|controls|spec|variance   # S9-S13 outputs
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


def choice_rule_tables(paths: Paths, calib: str = "centaur_free_calib") -> list[Path]:
    """The fitted choice rule (D18) and its out-of-sample check by episode block, from the saved rule files: the
    rule refitted on both Centaur runs (`choice_rule.json`) and the `centaur_main`-only fit validated on `calib`."""
    from . import choice_rule as CR

    d = paths.processed / "choice_rule"
    if not (d / "choice_rule.json").exists():
        return []
    rule = json.loads((d / "choice_rule.json").read_text(encoding="utf-8"))
    written = [paths.table(pd.DataFrame({"feature": rule["features"], "estimate": rule["params"], "ci_low": rule["ci_low"],
                                         "ci_high": rule["ci_high"]}), "choice_rule_fit")]
    first = d / "choice_rule_centaur_main.json"
    if first.exists() and (paths.processed / calib / "episodes.jsonl").exists():
        params = np.array(json.loads(first.read_text(encoding="utf-8"))["params"])
        written.append(paths.table(CR.by_episode(params, CR.decisions(paths.processed / calib)), "choice_rule_validation_by_episode"))
    return written


def gate18_report(paths: Paths, pilot: str, z0: str | None, e0: str | None, crn: str | None, breaks: list[str]) -> list[Path]:
    base = paths.processed / "phase5"
    brk = {}
    for item in breaks:
        weeks, tag = item.split("=", 1)
        brk[int(weeks)] = base / tag
    table = A.gate18(base / pilot, base / z0 if z0 else None, base / e0 if e0 else None, base / crn if crn else None, brk or None)
    print(table.to_string(index=False))
    return [paths.table(table, "gate18_checks")]


# ------------------------------------------------------------------ Phase V: Table 5, Figures 5-6
SCENARIO_COLOR = {"traditional": SERIES[0], "scaffolding_rapid": SERIES[1], "scaffolding_nofade": SERIES[2],
                  "substitution": SERIES[3], "free_choice": SERIES[4], "free_choice_centaur": SERIES[5]}
SCENARIO_LABEL = {"traditional": "Traditional", "scaffolding_rapid": "Scaffolding, rapid fade",
                  "scaffolding_nofade": "Scaffolding, no fade", "substitution": "Substitution",
                  "free_choice": "Free choice (assumed rule)", "free_choice_centaur": "Free choice (Centaur-calibrated)"}
HEADLINE = ("G", "unaided", "far", "retention", "p_request")  # PLAN.md D7
OUTCOME_LABEL = {"G": "net advantage G (eq. 39)", "unaided": "unaided accuracy", "far": "far transfer",
                 "retention": "retention after the break", "p_request": "P(request help)", "K": "knowledge K",
                 "D": "dependence D"}


def figure5(plt, weekly: pd.DataFrame, levels: pd.DataFrame, out: Path, name: str) -> tuple[list[Path], pd.DataFrame]:
    """Year-1 weekly K, far transfer and D per scenario: mean over parameter draws with the 5-95% band across draws
    (§11.3); a second row with the yearly levels when the run is longer than one year."""
    w = weekly[weekly["draw_id"] >= 0]
    multi_year = levels["year"].max() > 1
    fig, axes = plt.subplots(2 if multi_year else 1, 3, figsize=(12, 7.2 if multi_year else 3.8), squeeze=False)
    rows = []
    scen = [s for s in SCENARIO_COLOR if s in set(w["scenario"])]
    for j, var in enumerate(("K", "far", "D")):
        ax = axes[0, j]
        y1 = w[(w["year"] == 1) & w[var].notna()]
        for s in scen:
            g = y1[y1["scenario"] == s].groupby("week")[var]
            m, lo, hi = g.mean(), g.quantile(0.05), g.quantile(0.95)
            ax.fill_between(m.index, lo, hi, color=SCENARIO_COLOR[s], alpha=0.10, lw=0)
            ax.plot(m.index, m.values, color=SCENARIO_COLOR[s], lw=2, label=SCENARIO_LABEL[s])
            rows += [{"panel": "year 1 weekly", "variable": var, "scenario": s, "time": int(k), "mean": float(m[k]),
                      "p05": float(lo[k]), "p95": float(hi[k])} for k in m.index]
        ax.set_title(f"{OUTCOME_LABEL.get(var, var)}, year 1")
        ax.set_xlabel("instructional week")
        if multi_year:
            ax2 = axes[1, j]
            lv = levels[(levels["kind"] == "level") & (levels["outcome"] == var) & (levels["draw_id"] >= 0)]
            for s in scen:
                g = lv[lv["scenario"] == s].groupby("year")["estimate"]
                m, lo, hi = g.mean(), g.quantile(0.05), g.quantile(0.95)
                ax2.fill_between(m.index, lo, hi, color=SCENARIO_COLOR[s], alpha=0.10, lw=0)
                ax2.plot(m.index, m.values, color=SCENARIO_COLOR[s], lw=2, marker="o", ms=5, mec=SURFACE, mew=1.5)
                rows += [{"panel": "yearly", "variable": var, "scenario": s, "time": int(k), "mean": float(m[k]),
                          "p05": float(lo[k]), "p95": float(hi[k])} for k in m.index]
            ax2.set_title(f"{OUTCOME_LABEL.get(var, var)}, end of each school year")
            ax2.set_xlabel("school year (0 = before the first episode)")
    axes[0, 0].legend(loc="lower right", fontsize=7.5)
    fig.suptitle("Figure 5. Model-implied trajectories per scenario (mean over parameter draws, band: 5-95% of draws)",
                 x=0.01, ha="left", fontsize=10, fontweight="bold", color=INK)
    fig.tight_layout()
    return save(fig, out, f"fig5_trajectories_{name}"), pd.DataFrame(rows)


def figure6(plt, hist: pd.DataFrame, table5: pd.DataFrame, out: Path, name: str, year: int) -> list[Path]:
    """Learner-level paired differences (AI minus traditional, pooled over draws) per scenario and headline outcome at
    one year, with the median across draws of each draw's mean and its 90% simulation interval."""
    h = hist[hist["year"] == year]
    scen = [s for s in SCENARIO_COLOR if s in set(h["scenario"]) and s != "traditional"]
    outs = [o for o in HEADLINE if o in set(h["outcome"])]
    fig, axes = plt.subplots(len(outs), len(scen), figsize=(2.6 * len(scen), 1.9 * len(outs)), squeeze=False, sharey="row")
    for i, o in enumerate(outs):
        g_all = h[h["outcome"] == o]
        nz = g_all[g_all["count"] > 0]
        lo_x, hi_x = (nz["bin_low"].min(), nz["bin_high"].max()) if len(nz) else (-0.1, 0.1)
        half = max(abs(lo_x), abs(hi_x), 1e-3)
        for j, s in enumerate(scen):
            ax = axes[i, j]
            g = g_all[g_all["scenario"] == s].sort_values("bin")
            total = g["count"].sum()
            ax.bar(g["bin_low"], g["count"] / max(total, 1), width=g["bin_high"] - g["bin_low"], align="edge",
                   color=SCENARIO_COLOR[s], lw=0)
            t = table5[(table5["scenario"] == s) & (table5["outcome"] == o) & (table5["year"] == year)]
            if len(t):
                ax.axvspan(t["lo90"].iloc[0], t["hi90"].iloc[0], color=INK2, alpha=0.10, lw=0)
                ax.axvline(t["median"].iloc[0], color=INK, lw=1.2)
            ax.axvline(0, color=AXIS, lw=0.8)
            ax.set_xlim(-half, half)
            ax.grid(axis="x", visible=False)
            if i == 0:
                ax.set_title(SCENARIO_LABEL[s], fontsize=8.5)
            if j == 0:
                ax.set_ylabel(OUTCOME_LABEL.get(o, o), fontsize=8)
            ax.tick_params(labelsize=7)
    fig.suptitle(f"Figure 6. Year-{year} scenario contrasts: learner-level paired differences vs traditional "
                 f"(bars), median across draws (line) and 90% simulation interval (band)", x=0.01, ha="left",
                 fontsize=10, fontweight="bold", color=INK)
    fig.tight_layout()
    return save(fig, out, f"fig6_distributions_{name}")


def load_runs(paths: Paths, tags: list[str], table: str) -> pd.DataFrame:
    """One Phase V table over several runs of the same design (e.g. v_main + v_main_fcc): each later run adds only
    the scenarios the earlier ones lack, so the shared traditional arm (identical under the same seed) is kept once."""
    from .longitudinal import read_table

    frames, seen = [], set()
    for tag in tags:
        run = paths.processed / "phase5" / tag
        if not (run / "run.json").exists():
            continue
        t = read_table(run, table)
        if len(t) and "scenario" in t:
            t = t[~t["scenario"].isin(seen)]
            seen |= set(t["scenario"].unique())
        frames.append(t)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def phase5(paths: Paths, tag: str, extra: list[str] | None = None) -> list[Path]:
    """Table 5 (behavioural and neural scenario contrasts at years 1, 5, 10) and Figures 5-6 for one Phase V run,
    plus the scenarios of `extra` runs with the same design (the sixth scenario, `v_main_fcc`)."""
    plt = plt_setup()
    tags = [tag] + list(extra or [])
    draws = load_runs(paths, tags, "simulation_draws")
    years = sorted(int(y) for y in draws["year"].unique() if y > 0)
    target = [y for y in (1, 5, 10) if y in years] or [max(years)]
    t5 = A.scenario_contrasts(draws, outcomes=list(HEADLINE) + ["K", "R", "M", "D"], years=target)
    written = [paths.table(t5, f"table5_scenario_contrasts_{tag}")]
    neural = load_runs(paths, tags, "neural_contrasts")
    if len(neural):
        written.append(paths.table(A.neural_contrasts_table(neural, "D", target), f"table5_neural_d_{tag}"))
    fig5, fig5_table = figure5(plt, load_runs(paths, tags, "weekly_means"), draws, paths.figures, tag)
    written += fig5 + [paths.table(fig5_table, f"fig5_trajectories_{tag}")]
    hist = load_runs(paths, tags, "contrast_hist")
    if len(hist):
        written += figure6(plt, hist, t5, paths.figures, tag, max(target))
    return written


# ------------------------------------------------------------------ S9 exposure, supplementary
def exposure(paths: Paths, tags: dict) -> list[Path]:
    """Year 1, 5, 10 headline scenario contrasts at 1, 3 and 5 episodes per week (§9.1), one table."""
    frames = []
    for epw, tag in tags.items():
        draws = load_runs(paths, [tag], "simulation_draws")
        if len(draws):
            frames.append(A.scenario_contrasts(draws, outcomes=list(HEADLINE) + ["K", "D"]).assign(episodes_per_week=epw, run=tag))
    return [paths.table(pd.concat(frames, ignore_index=True), "tableS_exposure")] if frames else []


# ------------------------------------------------------------------ S10: Figure 7, tipping points
def figure7(paths: Paths, grid_tag: str = "v_frontier", lines_tag: str = "v_tipping", neural_tag: str = "v_neural") -> list[Path]:
    """Figure 7a (phase diagram of year-10 G over adaptation a x retained effort e, one panel per substitution
    probability o), the §9.7 tipping-point table, and Figure 7b (mechanism D's year-10 d, substitution vs
    traditional, over half-life x lambda_O, one panel per network)."""
    from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm

    plt = plt_setup()
    cmap = LinearSegmentedColormap.from_list("diverging", DIVERGING)
    base = paths.processed / "phase5"
    written = []
    if (base / grid_tag / "run.json").exists():
        knobs = json.loads((base / grid_tag / "run.json").read_text(encoding="utf-8"))["scenario_knobs"]
        pdg = A.phase_diagram(load_runs(paths, [grid_tag], "simulation_draws"), knobs)
        written.append(paths.table(pdg, "fig7a_phase_diagram"))
        os_ = sorted(pdg["o"].unique())
        half = float(pdg["median_G"].abs().max()) or 1.0
        fig, axes = plt.subplots(1, len(os_), figsize=(4.2 * len(os_), 4.0), squeeze=False)
        for ax, o in zip(axes[0], os_):
            g = pdg[pdg["o"] == o].pivot_table(index="a", columns="e", values="median_G")
            cls = pdg[pdg["o"] == o].pivot_table(index="a", columns="e", values="class_eps0.02", aggfunc="first")
            im = ax.imshow(g.to_numpy(), origin="lower", cmap=cmap, norm=TwoSlopeNorm(0, -half, half), aspect="auto")
            for i in range(g.shape[0]):
                for j in range(g.shape[1]):
                    mark = {"beneficial": "+", "harmful": "−", "neutral": "·"}[cls.iat[i, j]]
                    ax.text(j, i, mark, ha="center", va="center", fontsize=9, color=INK)
            ax.set_xticks(range(g.shape[1]), [f"{v:.2f}" for v in g.columns], fontsize=7)
            ax.set_yticks(range(g.shape[0]), [f"{v:.2f}" for v in g.index], fontsize=7)
            ax.set_xlabel("retained effort e")
            ax.set_ylabel("adaptation a")
            ax.set_title(f"substitution probability o = {o:.1f}")
            ax.grid(False)
        fig.colorbar(im, ax=axes[0].tolist(), shrink=0.8, label="median year-10 G vs traditional")
        fig.suptitle("Figure 7a. Robustness frontier: scaffolding cells vs traditional, year 10 "
                     "(+ beneficial, − harmful, · neutral at ε = 0.02)", x=0.01, ha="left", fontsize=10,
                     fontweight="bold", color=INK)
        written += save(fig, paths.figures, "fig7a_phase_diagram")
    if (base / lines_tag / "run.json").exists():
        knobs = json.loads((base / lines_tag / "run.json").read_text(encoding="utf-8"))["scenario_knobs"]
        per_draw, summary = A.tipping_points(load_runs(paths, [lines_tag], "simulation_draws"), knobs)
        written += [paths.table(summary, "tableS_tipping_points"), paths.table(per_draw, "tableS_tipping_points_per_draw")]
    if (base / neural_tag / "run.json").exists():
        nd = A.neural_diagram(load_runs(paths, [neural_tag], "neural_diagram"))
        written.append(paths.table(nd, "fig7b_neural_diagram"))
        nets = [n for n in NETWORK_LABEL if n in set(nd["network"])]
        half = float(nd["median_d"].abs().max()) or 1.0
        fig, axes = plt.subplots(1, len(nets), figsize=(2.3 * len(nets), 3.2), squeeze=False, sharey=True)
        for ax, net in zip(axes[0], nets):
            g = nd[nd["network"] == net].pivot_table(index="half_life_weeks", columns="lambda_O", values="median_d")
            im = ax.imshow(g.to_numpy(), origin="lower", cmap=cmap, norm=TwoSlopeNorm(0, -half, half), aspect="auto")
            ax.set_xticks(range(g.shape[1]), [f"{v:.2f}" for v in g.columns], fontsize=6.5, rotation=90)
            ax.set_yticks(range(g.shape[0]), [f"{int(v)}" for v in g.index], fontsize=7)
            ax.set_xlabel("λ_O")
            ax.set_title(NETWORK_LABEL[net].replace(" / ", " /\n"), fontsize=8.5)
            ax.grid(False)
        axes[0, 0].set_ylabel("half-life (weeks)")
        fig.colorbar(im, ax=axes[0].tolist(), shrink=0.8, label="median year-10 d")
        fig.suptitle("Figure 7b. Model-implied neural contrast, substitution vs traditional (mechanism D, year 10)",
                     x=0.01, ha="left", fontsize=10, fontweight="bold", color=INK)
        written += save(fig, paths.figures, "fig7b_neural_diagram")
    return written


# ------------------------------------------------------------------ S11 mechanism decomposition
def mechanisms(paths: Paths, tag: str = "v_mediation", z_run: str = "v_main") -> list[Path]:
    """§11.5: contributions of E, F, D (reruns with the mediator held at traditional) and Z (post hoc)."""
    run = paths.processed / "phase5" / tag
    if not (run / "run.json").exists():
        return []
    knobs = json.loads((run / "run.json").read_text(encoding="utf-8"))["scenario_knobs"]
    out = A.mechanism_decomposition(load_runs(paths, [tag], "simulation_draws"), knobs,
                                    load_runs(paths, [tag], "neural_contrasts"))
    zrun = paths.processed / "phase5" / z_run
    if (zrun / "run.json").exists():
        out = pd.concat([out, A.z_mediator(zrun, paths.raw, paths.root)], ignore_index=True)
    return [paths.table(out, "tableS_mechanism_decomposition")]


# ------------------------------------------------------------------ S12: Table 6 and the falsification checklist
def table6(paths: Paths, main: list[str], z0: str = "v_z0_10y", e0: str = "v_e0_10y", uniform: str = "v_uniform",
           year: int = 10) -> list[Path]:
    """Table 6 (§10.3 negative controls, one row each with what was expected and what came out), the per-network
    permuted-Z table and the §10.6 falsification checklist."""
    from .longitudinal import read_table

    base = paths.processed / "phase5"
    run = base / main[0]
    draws = load_runs(paths, main, "simulation_draws")
    neural = load_runs(paths, main, "neural_contrasts")
    zc = A.z_controls(run, paths.raw, paths.root)
    written = [paths.table(zc, "tableS_z_controls")]
    zy = zc[zc["year"] == year]
    rows = []

    def add(control, implementation, expected, value, as_expected):
        rows.append({"control": control, "implementation": implementation, "expected": expected, "value": value,
                     "as_expected": as_expected})

    if (base / z0 / "run.json").exists():
        n0 = read_table(base / z0, "neural_contrasts")
        m = float(n0["mean"].abs().max())
        add("zero plasticity", f"{z0}: eta = 0, 10 years, 50 x 500", "every neural contrast exactly 0",
            f"max |mean network contrast| {m:.3g}", m == 0)
    if (base / e0 / "run.json").exists():
        d0 = read_table(base / e0, "simulation_draws")
        eff = d0[(d0["kind"] == "level") & (d0["outcome"] == "effort") & (d0["year"] > 0)]["estimate"]
        k0 = A._sc_by_draw(d0, year).get(("substitution", "K"), pd.Series(dtype=float)).median()
        k1 = A._sc_by_draw(draws, year).get(("substitution", "K"), pd.Series(dtype=float)).median()
        add("zero effort sensitivity", f"{e0}: effort fixed, 10 years, 50 x 500",
            "E constant; effort-mediated contrasts shrink", f"effort range {eff.max() - eff.min():.3g}; "
            f"|SC_K(substitution)| {abs(k0):.4f} vs {abs(k1):.4f} in the main run", bool(eff.max() - eff.min() < 1e-9 and abs(k0) < abs(k1)))
    if len(zy):
        r = zy["permuted_units_median_ratio"]
        add("permuted TRIBE across units (irrelevant content)", f"post hoc on {main[0]}, 200 derangements, mechanism D",
            "network contrasts unchanged (ratio ~ 1): they come from each condition's shared text profile, not from "
            "unit-specific content", f"median ratio {r.median():.2f} (max {r.max():.2f}) over {len(r)} scenario-networks",
            bool(abs(r.median() - 1) < 0.25))
        r = zy["permuted_conditions_median_ratio"]
        add("permuted condition labels within units", f"post hoc on {main[0]}, 200 permutations, mechanism D",
            "|control| well below |main| (ratio < 0.5, A15)", f"median ratio {r.median():.2f} (max {r.max():.2f}); "
            f"{int((r >= 0.5).sum())} of {len(r)} scenario-networks >= 0.5", bool(r.median() < 0.5))
        for col in [c for c in zy.columns if c.endswith("change ratio")]:
            add(f"harmless variation: {col.replace(' change ratio', '')}", f"post hoc on {main[0]}",
                "change small against the condition contrast", f"median |change| / |main| {zy[col].median():.2f}",
                bool(zy[col].median() < 0.5))
    shuffle_p = paths.tables / "tribe_shuffle_controls.csv"
    shuffle = pd.read_csv(shuffle_p) if shuffle_p.exists() else pd.DataFrame()
    for ctl, g in shuffle[shuffle["metric"] == "auc"].groupby("control") if len(shuffle) else []:
        add(f"{ctl}-shuffled texts", "notebook controls, 30 units x 3 conditions, AUC per network",
            "network change below the intact condition contrast", f"median ratio {g['ratio_shuffle_to_contrast'].median():.2f} "
            f"(max {g['ratio_shuffle_to_contrast'].max():.2f})", bool(g["ratio_shuffle_to_contrast"].median() < 1))
    yearly = load_runs(paths, main, "yearly_subsample")
    if len(yearly):
        flips = pd.concat([A.sign_flip_null(yearly[yearly["year"] == year], o) for o in ("unaided", "far", "retention")])
        written.append(paths.table(flips, "tableS_sign_flip_null"))
        add("behavioural label permutation", "sign flips within learner, 1,000, year-10 unaided / far / retention",
            "null SC centred at 0", f"max |null mean| {flips['null_mean'].abs().max():.2g} (null sd up to {flips['null_sd'].max():.2g})",
            bool((flips["null_mean"].abs() < 3 * flips["null_sd"] / np.sqrt(1000)).all()))
    written.append(paths.table(pd.DataFrame(rows), "table6_negative_controls"))
    t4 = paths.tables / "table4_cortical_contrasts.csv"
    t4c = paths.tables / "table4_cortical_contrasts_matched_covariates.csv"
    if t4.exists() and t4c.exists():
        uni = load_runs(paths, [uniform], "simulation_draws")
        fals = A.falsification(pd.read_csv(t4), pd.read_csv(t4c), shuffle, draws, neural, zc,
                               uni if len(uni) else None, year)
        print(fals.to_string(index=False))
        written.append(paths.table(fals, "table6_falsification"))
    return written


# ------------------------------------------------------------------ S13: Figure 8 and the variance decomposition
def spec_rows(paths: Paths) -> tuple[dict, list[dict]]:
    spec = yaml.safe_load((paths.root / "config" / "spec_curve.yaml").read_text(encoding="utf-8"))
    manifest = json.loads((paths.processed / "phase5" / "spec_curve_manifest.json").read_text(encoding="utf-8"))
    return spec, [s for s in manifest["specifications"] if (paths.processed / "phase5" / s["tag"] / "run.json").exists()]


def _spec_panel(fig, gs, frame: pd.DataFrame, dims: list[str], title: str, ylabel: str):
    """One specification curve: estimates sorted, 95% interval, colour by tier, indicator matrix underneath."""
    f = frame.sort_values("median").reset_index(drop=True)
    ax = fig.add_subplot(gs[0])
    tier_color = {1: SERIES[0], 2: SERIES[3], 3: SERIES[7]}
    x = np.arange(len(f))
    for t, g in f.groupby("tier"):
        ax.vlines(g.index, g["lo95"], g["hi95"], color=tier_color[int(t)], alpha=0.25, lw=0.8 if len(f) < 400 else 0.3)
        ax.scatter(g.index, g["median"], s=6 if len(f) < 400 else 1.5, color=tier_color[int(t)], label=f"tier {int(t)}", zorder=3)
    ax.axhline(0, color=INK2, lw=0.8)
    ax.set_xlim(-1, len(f))
    ax.set_xticks([])
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.legend(loc="upper left", markerscale=3)
    mx = fig.add_subplot(gs[1], sharex=ax)
    labels = []
    for i, dim in enumerate(dims):
        for lvl in sorted(f[dim].astype(str).unique()):
            on = np.flatnonzero(f[dim].astype(str) == lvl)
            row = len(labels)
            mx.scatter(on, np.full(len(on), row), s=1.5 if len(f) > 400 else 5, marker="s", color=INK2 if i % 2 else SERIES[6], lw=0)
            labels.append(f"{dim}: {lvl}")
    mx.set_yticks(range(len(labels)), labels, fontsize=6)
    mx.invert_yaxis()
    mx.set_xticks([])
    mx.grid(False)
    return x


def figure8(paths: Paths, year: int = 10) -> list[Path]:
    """Figure 8 (§10.4): (a) year-10 G for every AI scenario, 72 reruns x 3 outcome weights; (b) mechanism d for the
    control network, substitution vs traditional, 72 reruns x 144 post hoc levels."""
    from . import plasticity as P
    from .longitudinal import read_arrays, read_table

    spec, specs = spec_rows(paths)
    if not specs:
        return []
    base = paths.processed / "phase5"
    gw = paths.raw["phase5"]["G"]["weights"]
    weight_sets = {"equal": gw, **paths.raw["phase5"]["stakeholder_weights"]}
    ranks = spec["post_hoc"]
    runs = [(s, read_table(base / s["tag"], "simulation_draws")) for s in specs]
    g = A.spec_curve_g(runs, weight_sets, ranks["outcome_weights"], year)
    written = [paths.table(g, "fig8a_spec_curve_G")]
    p = paths.raw["plasticity"]
    tribe_dir = paths.root / p["tribe_dir"]
    zs = {}
    for wpm in ranks["reading_speed_wpm"]:
        for metric in ranks["tribe_metric"]:
            for wins in ranks["winsorize"]:
                zs[(wpm, metric, wins)] = P.load_z(tribe_dir, int(wpm), metric, p["winsorize"] if wins in (True, "yes") else None)[0]  # YAML reads yes/no as booleans
    ws = {w: P.load_networks(tribe_dir, w) for w in ranks["network_weights"]}
    frames = []
    for s in specs:
        run = base / s["tag"]
        meta = json.loads((run / "run.json").read_text(encoding="utf-8"))
        lam = read_table(run, "parameter_draws").set_index("draw_id")["plasticity.lambda_O"]
        frames.append(A.spec_curve_neural(s, read_arrays(run, "accumulators_subsample"), read_arrays(run, "mean_accumulator_diff"),
                                          lam, meta["scenarios"], zs, ws, p, ranks, year))
    nd = pd.concat(frames, ignore_index=True)
    written.append(paths.table(nd, "fig8b_spec_curve_neural"))
    plt = plt_setup()
    rerun_dims = ["form", "forgetting", "epw", "effort"]
    scen = [s for s in SCENARIO_COLOR if s in set(g["scenario"])]
    fig = plt.figure(figsize=(13, 3.6 * len(scen)))
    outer = fig.add_gridspec(len(scen), 1, hspace=0.45, top=0.96)
    for i, s in enumerate(scen):
        gs = outer[i].subgridspec(2, 1, height_ratios=[1.3, 1], hspace=0.05)
        _spec_panel(fig, gs, g[g["scenario"] == s], rerun_dims + ["outcome_weights"],
                    f"{SCENARIO_LABEL[s]}: {len(g[g['scenario'] == s])} specifications", "year-10 G vs traditional")
    fig.suptitle("Figure 8a. Specification curve: year-10 net advantage G (median and 95% interval across draws)",
                 x=0.01, y=0.995, ha="left", fontsize=10, fontweight="bold", color=INK)
    written += save(fig, paths.figures, "fig8a_spec_curve_G")
    fig = plt.figure(figsize=(13, 7.5))
    gs = fig.add_gridspec(2, 1, height_ratios=[1, 1.4], hspace=0.05, top=0.93)
    _spec_panel(fig, gs, nd, rerun_dims + ["wpm", "metric", "winsorize", "network_weights", "mechanism"],
                f"Control network, substitution vs traditional: {len(nd)} specifications", "year-10 d")
    fig.suptitle("Figure 8b. Specification curve: model-implied control-network contrast (median and 95% interval "
                 "across subsample draws)", x=0.01, y=0.995, ha="left", fontsize=10, fontweight="bold", color=INK)
    written += save(fig, paths.figures, "fig8b_spec_curve_neural")
    return written


def variance(paths: Paths, tags=("v_repl0", "v_repl1", "v_repl2"), year: int = 10) -> list[Path]:
    """§10.5 (eq. 41) from the three replicate runs (same parameters and learners, new behaviour stream, D19)."""
    from . import plasticity as P
    from .longitudinal import read_arrays, read_table

    base = paths.processed / "phase5"
    if not all((base / t / "run.json").exists() for t in tags):
        return []
    gw = paths.raw["phase5"]["G"]["weights"]
    paired = [A.paired_learner_values(read_table(base / t, "yearly_subsample"), gw) for t in tags]
    scen = sorted(set(paired[0]["scenario"]))
    p = paths.raw["plasticity"]
    tribe_dir = paths.root / p["tribe_dir"]
    W, nets = P.load_networks(tribe_dir, p["network_weights"])
    Z = P.load_z(tribe_dir, int(p["wpm"]), p["metric"], p["winsorize"])[0]
    lam = read_table(base / tags[0], "parameter_draws").set_index("draw_id")["plasticity.lambda_O"]
    v_stim = A.stimulus_bootstrap(read_arrays(base / tags[0], "mean_accumulator_diff"), lam, Z, W, nets, p,
                                  A.neural_scale(paired, "N_D_Cont", year), year)
    out = A.variance_decomposition(paired, scen, year, v_stimulus=v_stim)
    print(out.to_string(index=False))
    return [paths.table(out, "tableS_variance_decomposition")]


# ------------------------------------------------------------------ data dictionary (D1 deliverable)
COLUMN_DOC = {
    "draw_id": "parameter draw (-1 = the central draw, every leaf at medium)", "scenario": "Phase V scenario (config phase5.scenarios); in frontier / mediation runs the cell or `base|hold_X` name",
    "year": "school year (0 = before the first episode)", "kind": "`level` (scenario mean) or `contrast` (paired AI - comparator)",
    "outcome": "outcome name (see the outcome rows of this dictionary)", "estimate": "mean over learners (level) or mean paired difference (contrast)",
    "sd": "SD over learners", "median": "median over learners, or across draws in summary tables", "prsup": "PrSup (eq. 38): share of learners with a positive paired difference",
    "share_neg": "share of learners with a negative paired difference", "mechanism": "plasticity mechanism A, B, C or D (eq. 29-33)",
    "network": "Yeo-7 network of the Schaefer-400 parcels", "mean": "mean (over learners, or across draws in summary tables)",
    "d": "standardised neural contrast, mean / SD of the learner-level paired difference (eq. 44)", "week": "instructional week within the year",
    "K": "knowledge (eq. 22)", "M": "metacognitive monitoring (eq. 23)", "R": "retrieval strength (eq. 25)", "C": "calibration (eq. 24)",
    "D": "dependence on support (eq. 26)", "first_try": "first-attempt correctness rate", "far": "far-transfer accuracy (unaided test)",
    "learner_id": "learner index within the draw (the same person across scenarios)", "stratum": "prior-knowledge stratum 0 low, 1 medium, 2 high (eq. 15)",
    "K_after_break": "K after the summer break", "M_after_break": "M after the summer break", "unaided": "unaided accuracy on trained items (end-of-year test)",
    "p_request": "model-implied probability of requesting help after an error", "retention": "accuracy after the break (retention test)",
    "help_rate": "help requests per episode over the year", "bin": "histogram bin index", "bin_low": "lower edge of the bin",
    "bin_high": "upper edge of the bin", "count": "learners in the bin, summed over draws", "episode": "0-based episode index",
    "unit_id": "curriculum unit", "difficulty": "unit difficulty (logit scale, eq. 17)", "protocol": "instructional protocol that actually ran (in free choice: the one chosen)",
    "first_correct": "first answer correct", "transfer_correct": "near-transfer answer correct", "help_requests": "help requests in the episode",
    "reveal": "the answer was provided", "effort": "effort E (eq. 19)", "effectiveness": "effectiveness F (eq. 20)", "p_correct": "eq. 17-18 probability of a correct answer",
    "condition": "assigned arm (traditional, ai_scaffolding, ai_substitution, free_choice)", "time": "episode index (the learner's clock)",
    "support": "support level received", "correctness": "answer correctness (0/1), or unit correctness score in units.csv", "retrieval": "retrieval proxy of the episode (eq. 21)",
    "offloading": "offloading proxy of the episode", "pe": "prediction error of the first answer", "resolution": "error resolved within the episode",
    "answer_provided": "the answer was shown by the protocol", "hint_depth": "deepest hint or tutor turn reached", "attempts": "answer attempts",
    "tutor_calls": "LLM tutor calls", "tutor_leaked": "tutor turns rejected by the leakage check", "episode_id": "unique episode key",
    "stage": "turn stage (approach, first, help, retry, transfer)", "turn": "turn index within the episode", "prompt": "text shown to the learner model",
    "response": "learner model output", "answer": "option chosen", "confidence": "1-5 confidence rating (tracks the record, not the answer; CLAUDE.md)",
    "latency_proxy": "simulated time on task", "token_count": "tokens in the prompt", "requested_support": "help was requested at this turn",
    "explanation": "rule behind the chosen option (options are rule-generated)", "layout": "option order shown", "checkpoint_episode": "episode after which the §7.7 checkpoint ran",
    "unaided_accuracy_trained": "unaided accuracy on trained items", "supported_accuracy_trained": "supported accuracy on trained items",
    "support_gap": "supported - unaided accuracy", "near_transfer_accuracy": "near-transfer accuracy", "far_transfer_accuracy": "far-transfer accuracy",
    "retention_accuracy": "accuracy on items last practised >= retention_interval episodes ago", "n_retention_items": "retention items available",
    "brier_score": "Brier score of confidence (measures the record for Centaur, CLAUDE.md)", "expected_calibration_error": "ECE of confidence",
    "dependence_request_rate": "help requests per opportunity", "domain": "MBA domain", "concept": "concept (15; two units each)",
    "prerequisites": "prerequisite units", "reference_answer": "correct answer", "near_transfer_answer": "near-transfer correct answer",
    "transfer_answer": "far-transfer correct answer", "misconception_answer": "answer produced by the misconception", "misconception": "the misconception rule",
    "coverage": "semantic coverage (not computed, 1.0)", "stimulus_id": "stimulus key (unit x condition)", "variant": "stimulus variant (one per unit and condition)",
    "text": "stimulus text (the TRIBE input)", "modality": "stimulus modality (text)", "example_count": "worked examples", "word_count": "words",
    "sentence_count": "sentences", "character_count": "characters", "readability": "readability score", "equation_count": "equations",
    "lexical_diversity": "type-token ratio", "duration": "reading time in s at 220 wpm (eq. 4)", "level": "`parcel`, `network` or `stimulus`",
    "key": "parcel id or network name", "metric": "TRIBE metric (gate-19 definitions)", "value": "metric value (predicted response, a.u.)",
    "n": "draws (or units) in the summary", "lo90": "5th percentile across draws", "hi90": "95th percentile across draws",
    "lo95": "2.5th percentile across draws", "hi95": "97.5th percentile across draws", "tier": "specification-curve tier (highest rank among its levels)",
}
OUTCOME_DOC = {"G": "net advantage (eq. 39) = wK dK + wR dR + wM dM - wD dD", "near_bound_share": "share of learners within 0.01 of a state bound",
               "clips": "state updates clipped at a bound", "support_gap": "supported - unaided accuracy", "retention_below_share": "share with retention below end-of-year accuracy",
               "difficulty_slope": "slope of expected accuracy on unit difficulty", "share_traditional": "free choice: share of episodes on traditional"}


def data_dictionary(paths: Paths, run: str = "v_main") -> list[Path]:
    """Every column of every table the pipeline writes: the source table, the dtype and what it means."""
    from .longitudinal import read_table

    def doc(col: str) -> str:
        if col in COLUMN_DOC:
            return COLUMN_DOC[col]
        if col.startswith("N_"):
            _, m, net = col.split("_", 2)
            return f"model-implied network state N, mechanism {m}, network {net} (eq. 29-33, 7)"
        if "." in col:
            return f"drawn value of the config leaf `{col}` (A1)"
        return ""

    sources = {}
    run_dir = paths.processed / "phase5" / run
    for t in ("simulation_draws", "parameter_draws", "neural_contrasts", "weekly_means", "yearly_subsample", "contrast_hist", "episodes_central"):
        if (run_dir / "run.json").exists():
            sources[f"data/processed/phase5/<tag>/{t}"] = read_table(run_dir, t)
    p3 = paths.processed / "centaur_main"
    for name in ("learner_state.parquet", "responses.csv", "checkpoints.csv"):
        if (p3 / name).exists():
            sources[f"data/processed/<tag>/{name}"] = pd.read_parquet(p3 / name) if name.endswith(".parquet") else pd.read_csv(p3 / name, nrows=50)
    for name in ("units.csv", "stimuli.csv"):
        if (paths.processed / name).exists():
            sources[f"data/processed/{name}"] = pd.read_csv(paths.processed / name, nrows=50)
    tm = paths.tribe / "wpm220" / "tribe_metrics.parquet"
    if tm.exists():
        sources["data/tribe/<run>/wpm<speed>/tribe_metrics.parquet"] = pd.read_parquet(tm).head(50)
    for f in sorted(paths.tables.glob("*.csv")):
        if f.stem != "data_dictionary":
            sources[f"outputs/tables/{f.name}"] = pd.read_csv(f, nrows=50)
    rows = [{"table": t, "column": c, "dtype": str(df[c].dtype), "description": doc(c)} for t, df in sources.items() for c in df.columns]
    rows += [{"table": "simulation_draws (outcome values)", "column": o, "dtype": "", "description": d} for o, d in OUTCOME_DOC.items()]
    return [paths.table(pd.DataFrame(rows), "data_dictionary")]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("what", choices=("phase12", "engines", "gate18", "phase5", "exposure", "frontier", "mechanisms",
                                     "controls", "spec", "variance", "dictionary", "all"))
    ap.add_argument("--root", default=".")
    ap.add_argument("--n-boot", type=int, default=2000, dest="n_boot")
    ap.add_argument("--pilot", default="g18_pilot")
    ap.add_argument("--zero-plasticity", default="g18_z0", dest="z0")
    ap.add_argument("--zero-effort", default="g18_e0", dest="e0")
    ap.add_argument("--crn", default="g18_crn")
    ap.add_argument("--breaks", nargs="*", default=["4=g18_break4", "12=g18_pilot", "24=g18_break24"],
                    help="WEEKS=TAG runs of the central draw")
    ap.add_argument("--run", default="v_main", help="Phase V tag for `phase5` and `controls`")
    ap.add_argument("--extra", nargs="*", default=["v_main_fcc"], help="runs adding scenarios to --run (same design)")
    args = ap.parse_args(argv)
    paths = Paths(Path(args.root).resolve())
    written = []
    if args.what in ("phase12", "all"):
        written += phase12(paths, args.n_boot)
    if args.what in ("engines", "all") and (paths.processed / "centaur_main" / "learner_state.parquet").exists():
        written += engines(paths) + choice_rule_tables(paths)
    if args.what in ("gate18", "all") and (paths.processed / "phase5" / args.pilot / "run.json").exists():
        written += gate18_report(paths, args.pilot, args.z0, args.e0, args.crn, args.breaks)
    if args.what in ("phase5", "all") and (paths.processed / "phase5" / args.run / "run.json").exists():
        written += phase5(paths, args.run, args.extra)
    if args.what in ("exposure", "all"):
        written += exposure(paths, {1: "v_epw1", 3: args.run, 5: "v_epw5"})
    if args.what in ("frontier", "all"):
        written += figure7(paths)
    if args.what in ("mechanisms", "all"):
        written += mechanisms(paths, z_run=args.run)
    if args.what in ("controls", "all") and (paths.processed / "phase5" / args.run / "run.json").exists():
        written += table6(paths, [args.run] + args.extra)
    if args.what in ("spec", "all"):
        written += figure8(paths)
    if args.what in ("variance", "all"):
        written += variance(paths)
    if args.what in ("dictionary", "all"):
        written += data_dictionary(paths, args.run)
    for p in written:
        print(p.relative_to(paths.root))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

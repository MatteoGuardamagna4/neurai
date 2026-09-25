"""Post hoc check of falsification criterion F4 (parameter bounds), added after the first results (Appendix D.4).

    uv run python scripts/f4_bound_check.py      # writes outputs/tables/tableS_f4_bound_check.csv

F4 withholds a claim when more than 10% of learners end within 0.01 of a bound of the unit scale. It counts those
learners; it does not test whether a contrast depends on them. This script asks that second question, from saved
outputs only (no new simulation):

- `subsample`: in the main run's stored learner subsample at year 10, each AI scenario's net advantage G (eq. 39)
  over all learners, over those whose end state is near a bound, and over the rest, with the near-bound learners'
  share of the total and the share of draws in which G without them keeps the sign of G with them;
- `form`: across the 216 specification runs, the near-bound share and the sign stability of G separately under the
  bounded updates (eq. 22'-25') and the literal ones (eq. 22-25).
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
PHASE5 = ROOT / "data" / "processed" / "phase5"
OUT = ROOT / "outputs" / "tables" / "tableS_f4_bound_check.csv"
STATES = ["K", "M", "R", "D"]
AI = ["scaffolding_rapid", "scaffolding_nofade", "substitution", "free_choice"]


def subsample_rows(weights: dict, year: int = 10) -> list[dict]:
    y = pd.read_parquet(PHASE5 / "v_main" / "yearly_subsample")
    y = y[(y["year"] == year) & (y["draw_id"] >= 0)]
    key = ["draw_id", "learner_id"]
    trad = y[y["scenario"] == "traditional"].set_index(key)[STATES]
    rows = []
    for sc in AI:
        ai = y[y["scenario"] == sc].set_index(key)[STATES].reindex(trad.index)
        diff = ai - trad
        g = weights["K"] * diff["K"] + weights["R"] * diff["R"] + weights["M"] * diff["M"] - weights["D"] * diff["D"]
        near = ((ai < 0.01) | (ai > 0.99)).any(axis=1)
        by_draw = pd.DataFrame({"g": g, "near": near}).groupby(level="draw_id")
        same_sign = by_draw.apply(lambda d: np.sign(d.loc[~d["near"], "g"].mean()) == np.sign(d["g"].mean()))
        stats = {
            "draws": y["draw_id"].nunique(), "learners_per_draw": y["learner_id"].nunique(),
            "near_bound_share": near.mean(), "dependence_floor_share": (ai["D"] < 0.01).mean(),
            "G_all": g.mean(), "G_not_near": g[~near].mean(), "G_near": g[near].mean() if near.any() else np.nan,
            "near_share_of_G": g[near].sum() / g.sum(), "draws_same_sign_without_near": same_sign.mean(),
            "near_K_mean": ai.loc[near, "K"].mean() if near.any() else np.nan,
            "near_D_traditional_median": trad.loc[near, "D"].median() if near.any() else np.nan,
        }
        rows += [{"section": "subsample", "scenario": sc, "form": "bounded", "statistic": k, "value": float(v)}
                 for k, v in stats.items()]
    return rows


def form_rows(year: int = 10) -> list[dict]:
    manifest = json.loads((PHASE5 / "spec_curve_manifest.json").read_text(encoding="utf-8"))
    runs = [s for s in manifest["specifications"] if "_adapt_" in s["tag"] and (PHASE5 / s["tag"] / "run.json").exists()]
    nb = []
    for s in runs:
        d = pd.read_parquet(PHASE5 / s["tag"] / "simulation_draws",
                            filters=[("outcome", "==", "near_bound_share"), ("year", "==", year), ("kind", "==", "level")])
        d = d[d["draw_id"] >= 0]
        nb += [{"form": s["form"], "scenario": sc, "median": g["estimate"].median()} for sc, g in d.groupby("scenario")]
    nb = pd.DataFrame(nb)
    g = pd.read_csv(ROOT / "outputs" / "tables" / "fig8a_spec_curve_G.csv")
    rows = []
    for (form, sc), f in g.groupby(["form", "scenario"]):
        n = nb[(nb["form"] == form) & (nb["scenario"] == sc)]["median"]
        stats = {"specifications": len(f), "near_bound_share_median": n.median(),
                 "sign_constant": float((f["median"] > 0).all() or (f["median"] < 0).all()),
                 "intervals_including_0": ((f["lo95"] <= 0) & (f["hi95"] >= 0)).sum(),
                 "G_median_min": f["median"].min(), "G_median_max": f["median"].max()}
        rows += [{"section": "form", "scenario": sc, "form": form, "statistic": k, "value": float(v)}
                 for k, v in stats.items()]
    return rows


def main() -> None:
    cfg = yaml.safe_load((ROOT / "config" / "default.yaml").read_text(encoding="utf-8"))
    table = pd.DataFrame(subsample_rows(cfg["phase5"]["G"]["weights"]) + form_rows())
    table.to_csv(OUT, index=False)
    print(table.pivot_table(index=["section", "form", "scenario"], columns="statistic", values="value").round(4).to_string())
    print(f"wrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()

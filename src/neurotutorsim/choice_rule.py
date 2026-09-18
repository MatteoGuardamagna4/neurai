"""A transparent approach-choice rule fitted to Centaur's free-choice decisions (user decision 2026-09-18).

    python -m neurotutorsim.choice_rule fit --runs data/processed/centaur_main
    python -m neurotutorsim.choice_rule validate --rule data/processed/choice_rule/choice_rule.json \\
        --runs data/processed/centaur_free_calib

Phase V cannot call Centaur for millions of learner-episodes, and its free-choice scenario otherwise runs on an
assumed softmax in D. This module turns Centaur's own decisions into a rule Phase V can apply: a conditional logit
over the three approaches whose inputs are only what Centaur reads in its prompt (brief §7.3, no latent state):
the share of each approach among the last three picks (the transcript shows three past episodes), the payoff
record per approach (the "Looking back at what worked" line: follow-up questions solved after each approach), whether
an approach has been tried at all, and recent first-try form. It is fitted to Centaur's full probability over the
three options (soft labels), not only to the sampled pick, with a learner-level cluster bootstrap for uncertainty
that Phase V propagates by giving each parameter draw one bootstrap vector. The rule is model-implied behaviour of a
model trained on human choices, not observed student behaviour.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd

APPROACHES = ("traditional", "ai_scaffolding", "ai_substitution")  # alternative order everywhere in this module
FEATURES = ("scaffolding", "substitution", "habit", "payoff", "tried", "form_x_scaffolding", "form_x_substitution")
HABIT_WINDOW = 3  # = engine.history_window: the past episodes Centaur sees
PAYOFF_PRIOR = (1.0, 2.0)  # (wins + 1) / (uses + 2): a flat prior, centred at 0.5


# ------------------------------------------------------------------ features
def design(last_picks: np.ndarray, uses: np.ndarray, wins: np.ndarray, recent_rate: np.ndarray) -> np.ndarray:
    """(n, 3, k) features per decision and approach. `last_picks` (n, HABIT_WINDOW) holds approach indices or -1
    for no pick yet; `uses` / `wins` (n, 3) are the free-choice counts before this decision; `recent_rate` (n,) is the
    share of the last five problems solved on the first try."""
    n = len(uses)
    X = np.zeros((n, 3, len(FEATURES)))
    X[:, 1, 0] = 1.0
    X[:, 2, 1] = 1.0
    for a in range(3):
        X[:, a, 2] = (last_picks == a).sum(axis=1) / HABIT_WINDOW
    tried = uses > 0
    rate = (wins + PAYOFF_PRIOR[0]) / (uses + PAYOFF_PRIOR[1])
    X[:, :, 3] = np.where(tried, rate - 0.5, 0.0)
    X[:, :, 4] = tried
    form = np.asarray(recent_rate, float) - 0.5
    X[:, 1, 5] = form
    X[:, 2, 6] = form
    return X


def probabilities(params: np.ndarray, X: np.ndarray) -> np.ndarray:
    u = X @ np.asarray(params, float)
    u -= u.max(axis=1, keepdims=True)
    e = np.exp(u)
    return e / e.sum(axis=1, keepdims=True)


# ------------------------------------------------------------------ Centaur's decisions from a Phase III run
def decisions(processed: Path, logs: Path | None = None, cfg: dict | None = None) -> pd.DataFrame:
    """One row per free-choice decision: learner, episode, the features' raw inputs before the decision, Centaur's
    probability for each approach (from the call log, matched on the prompt's SHA-256) and the sampled pick."""
    from . import learners as L
    from .simulate import load_config, read_jsonl

    processed = Path(processed).resolve()
    root = processed.parents[2]  # <root>/data/processed/<tag>
    logs = Path(logs) if logs else root / "outputs" / "logs" / processed.name
    cfg = cfg or load_config(root / "config" / "default.yaml")
    probs = {}
    calls = logs / "calls_centaur.jsonl"
    if calls.exists():
        for line in calls.read_text(encoding="utf-8").splitlines():
            rec = json.loads(line)
            probs[rec["prompt_sha256"]] = rec["probabilities"]
    records = sorted((r for r in read_jsonl(processed / "episodes.jsonl") if r["condition"] == "free_choice"),
                     key=lambda r: (r["learner_id"], r["episode"]))
    n_learners = 1 + max(r["learner_id"] for r in read_jsonl(processed / "episodes.jsonl"))
    initial = {l.learner_id: l for l in L.make_population(cfg["population"], n_learners, int(cfg["seeds"]["master"]))}
    L.seed_prior_records(list(initial.values()), cfg)
    rows, state, picks = [], {}, {}
    for r in records:
        lid = r["learner_id"]
        before = state.get(lid) or initial[lid].snapshot()
        last = picks.setdefault(lid, [])
        uses = np.array([before["choice_record"].get(a, [0, 0])[0] for a in APPROACHES], float)
        wins = np.array([before["choice_record"].get(a, [0, 0])[1] for a in APPROACHES], float)
        recent = before["recent"]
        turn = r["turns"][0]
        if turn["stage"] != "approach":
            raise ValueError(f"learner {lid} episode {r['episode']}: the first turn is not the approach choice")
        key_of = dict(item.split(":") for item in turn["layout"].split("|"))  # key -> approach
        p = probs.get(turn["prompt_sha256"])
        row = {"learner_id": lid, "episode": r["episode"], "pick": APPROACHES.index(r["protocol"]),
               "last_picks": (last[-HABIT_WINDOW:] + [-1] * HABIT_WINDOW)[:HABIT_WINDOW] if len(last) < HABIT_WINDOW
               else last[-HABIT_WINDOW:],
               "uses": uses, "wins": wins, "recent_rate": float(np.mean(recent)) if recent else 0.5,
               "transfer_correct": r["transfer_correct"]}
        if p is not None:
            by_approach = {key_of[k]: v for k, v in p.items()}
            row.update({f"p_{a}": by_approach[a] for a in APPROACHES})
        rows.append(row)
        state[lid] = r["learner_after"]
        last.append(APPROACHES.index(r["protocol"]))
    df = pd.DataFrame(rows)
    df["has_probabilities"] = df[[f"p_{a}" for a in APPROACHES]].notna().all(axis=1) if "p_traditional" in df else False
    return df


def arrays(df: pd.DataFrame, soft: bool = True) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """(X (n, 3, k), targets (n, 3), learner ids): targets are Centaur's probabilities when logged, else the pick."""
    last = np.array([list(x) for x in df["last_picks"]], dtype=int)
    X = design(last, np.stack(df["uses"].to_numpy()), np.stack(df["wins"].to_numpy()), df["recent_rate"].to_numpy())
    Y = np.zeros((len(df), 3))
    Y[np.arange(len(df)), df["pick"].to_numpy(int)] = 1.0
    if soft and "p_traditional" in df:
        has = df["has_probabilities"].to_numpy(bool)
        Y[has] = df.loc[has, [f"p_{a}" for a in APPROACHES]].to_numpy(float)
    return X, Y, df["learner_id"].to_numpy()


# ------------------------------------------------------------------ fit, bootstrap, evaluate
def fit(X: np.ndarray, Y: np.ndarray, ridge: float = 1e-4) -> np.ndarray:
    """Soft-label conditional logit: minimise the cross-entropy of Y under the rule. The tiny ridge only keeps a
    near-separable fit finite; 1e-3 already shrank a low-variance coefficient by 13% on synthetic data."""
    from scipy.optimize import minimize

    def loss(b):
        q = probabilities(b, X)
        return -(Y * np.log(np.clip(q, 1e-12, 1))).sum() / len(X) + ridge * (b @ b)

    def grad(b):
        q = probabilities(b, X)
        # d/db of -sum_a y_a log q_a = sum_a (q_a - y_a) x_a, averaged over decisions
        return np.einsum("na,nak->k", q - Y, X) / len(X) + 2 * ridge * b

    res = minimize(loss, np.zeros(X.shape[2]), jac=grad, method="BFGS")
    return res.x


def bootstrap(X: np.ndarray, Y: np.ndarray, groups: np.ndarray, n_boot: int = 500, seed: int = 0) -> np.ndarray:
    """Learner-level cluster bootstrap of the fitted parameters (n_boot, k)."""
    rng = np.random.default_rng(seed)
    ids = np.unique(groups)
    rows = {g: np.flatnonzero(groups == g) for g in ids}
    out = np.empty((n_boot, X.shape[2]))
    for b in range(n_boot):
        pick = np.concatenate([rows[g] for g in rng.choice(ids, len(ids), replace=True)])
        out[b] = fit(X[pick], Y[pick])
    return out


def softmax_in_d(D: np.ndarray, slope: float) -> np.ndarray:
    """The assumed Phase V rule (`LogisticEngine.approach`): logits -s(D - .5), 0, +s(D - .5)."""
    s = slope * (np.asarray(D, float) - 0.5)
    e = np.exp(np.stack([-s, np.zeros_like(s), s], axis=1))
    return e / e.sum(axis=1, keepdims=True)


def evaluate(params: np.ndarray, X: np.ndarray, Y: np.ndarray, baselines: dict | None = None) -> dict:
    """Cross-entropy of Centaur's choices under the rule (lower is better) and under the baselines, the share of
    decisions whose most likely approach agrees, and the mean predicted and Centaur shares."""
    q = probabilities(params, X)
    out = {"n": len(X), "cross_entropy": float(-(Y * np.log(np.clip(q, 1e-12, 1))).sum(axis=1).mean()),
           "argmax_agreement": float((q.argmax(axis=1) == Y.argmax(axis=1)).mean()),
           "centaur_shares": dict(zip(APPROACHES, Y.mean(axis=0).round(4).tolist())),
           "rule_shares": dict(zip(APPROACHES, q.mean(axis=0).round(4).tolist()))}
    for name, qb in (baselines or {}).items():
        out[f"cross_entropy_{name}"] = float(-(Y * np.log(np.clip(qb, 1e-12, 1))).sum(axis=1).mean())
    return out


def fit_rule(runs: list[Path], n_boot: int = 500, seed: int = 0) -> dict:
    """Fit on one or more Phase III runs' free-choice arms and return the rule (point estimate, bootstrap draws,
    in-sample evaluation against constant shares)."""
    frames = [decisions(r).assign(run=Path(r).name) for r in runs]
    df = pd.concat(frames, ignore_index=True)
    df["learner_key"] = df["run"] + ":" + df["learner_id"].astype(str)
    X, Y, _ = arrays(df)
    params = fit(X, Y)
    groups = pd.factorize(df["learner_key"])[0]
    boot = bootstrap(X, Y, groups, n_boot, seed)
    constant = np.tile(Y.mean(axis=0), (len(Y), 1))
    lo, hi = np.percentile(boot, [2.5, 97.5], axis=0)
    return {"features": list(FEATURES), "approaches": list(APPROACHES), "params": params.tolist(),
            "ci_low": lo.tolist(), "ci_high": hi.tolist(), "bootstrap": boot.tolist(),
            "habit_window": HABIT_WINDOW, "payoff_prior": list(PAYOFF_PRIOR),
            "fit": evaluate(params, X, Y, {"constant_shares": constant}),
            "sources": {str(r): {"decisions": int((df["run"] == Path(r).name).sum()),
                                 "learners": int(df.loc[df["run"] == Path(r).name, "learner_id"].nunique()),
                                 "episodes_sha256": hashlib.sha256((Path(r) / "episodes.jsonl").read_bytes()).hexdigest()}
                        for r in runs},
            "recorded_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}


def by_episode(params: np.ndarray, df: pd.DataFrame, block: int = 10) -> pd.DataFrame:
    """Centaur's and the rule's approach shares per block of episodes (the lock-in check)."""
    X, Y, _ = arrays(df)
    q = probabilities(params, X)
    blocks = (df["episode"].to_numpy() // block) * block
    rows = []
    for b in np.unique(blocks):
        m = blocks == b
        for i, a in enumerate(APPROACHES):
            rows.append({"episodes": f"{b}-{b + block - 1}", "approach": a, "centaur": float(Y[m, i].mean()),
                         "rule": float(q[m, i].mean()), "n": int(m.sum())})
    return pd.DataFrame(rows)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("what", choices=("fit", "validate"))
    ap.add_argument("--runs", nargs="+", required=True, help="Phase III output folders with a free-choice arm")
    ap.add_argument("--rule", default="data/processed/choice_rule/choice_rule.json")
    ap.add_argument("--n-boot", type=int, default=500, dest="n_boot")
    args = ap.parse_args(argv)
    rule_path = Path(args.rule)
    tables = Path("outputs/tables")
    tables.mkdir(parents=True, exist_ok=True)
    if args.what == "fit":
        rule = fit_rule([Path(r) for r in args.runs], args.n_boot)
        rule_path.parent.mkdir(parents=True, exist_ok=True)
        rule_path.write_text(json.dumps(rule, indent=2), encoding="utf-8")
        pd.DataFrame({"feature": FEATURES, "estimate": rule["params"], "ci_low": rule["ci_low"], "ci_high": rule["ci_high"]}
                     ).to_csv(tables / "choice_rule_fit.csv", index=False)
        print(json.dumps({k: rule[k] for k in ("features", "params", "ci_low", "ci_high", "fit")}, indent=2))
        return 0
    rule = json.loads(rule_path.read_text(encoding="utf-8"))
    df = pd.concat([decisions(Path(r)) for r in args.runs], ignore_index=True)
    X, Y, _ = arrays(df)
    params = np.array(rule["params"])
    constant = np.tile(np.array([rule["fit"]["centaur_shares"][a] for a in APPROACHES]), (len(Y), 1))
    result = {"out_of_sample": evaluate(params, X, Y, {"fit_sample_shares": constant}), "runs": args.runs}
    (rule_path.parent / "validation.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    by_episode(params, df).to_csv(tables / "choice_rule_validation_by_episode.csv", index=False)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

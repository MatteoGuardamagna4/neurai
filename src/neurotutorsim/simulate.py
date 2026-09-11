"""Run the synthetic learner population through the curriculum (brief §7), with §7.7 checkpoints,
append-only resumable logs, the §4.2 tables and a run log.

    python -m neurotutorsim.simulate --engine logistic --learners 30 --episodes 12 --tutor fake
    python -m neurotutorsim.simulate --engine minitaur --learners 1 --episodes 1 --conditions traditional
    python -m neurotutorsim.simulate --resume            # continue an interrupted run

Source of truth is data/processed/episodes.jsonl (one line per learner x condition x episode, with
the post-episode learner snapshot); every table is derived from it and a resumed run restores from it.
Phase IV/V hooks: learner_state.parquet carries E, PE, retrieval, offloading and resolution per
(unit_id, condition) for the plasticity equations 29-33; the support-persistence policy and the
parameter arms are the §9.2-9.3 scenario knobs. TODO(Phase V): resample concepts with novel surface
forms once the curriculum is exhausted (§9.1); today the unit order simply cycles.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
import time
from dataclasses import asdict
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from . import __version__, corpus
from . import learners as L
from .engines import EngineError, HybridEngine, LogisticEngine, MinitaurEngine, Trial

TRANSCRIPT_ENGINES = ("minitaur", "centaur")  # same protocol, different served model
from .episode import build_options, run_episode, FREE
from .tutor import FakeTutor, Tutor, TutorError

AI_CONDITIONS = ("ai_scaffolding", "ai_substitution")
RUN_CONDITIONS = corpus.CONDITIONS + (FREE,)  # three assigned arms plus the free-choice arm


def load_config(path: Path, setting: str | None = None) -> dict:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    setting = setting or raw["parameter_setting"]
    cfg = L.resolve(raw, setting)
    cfg["parameter_setting"] = setting
    return cfg


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def append_jsonl(path: Path, record: dict) -> None:
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, default=lambda o: o.item() if hasattr(o, "item") else str(o)) + "\n")


def forecasts_of(record: dict) -> list[tuple[float, float]]:
    return [(t["confidence"], float(t["correct"])) for t in record["turns"]
            if t["stage"] in ("first", "transfer") and t["confidence"] is not None]


def checkpoint(learner: L.Learner, condition: str, episode: int, units: dict, engine, cfg: dict,
               rng: np.random.Generator, forecasts) -> dict:
    """Brief §7.7: unaided probes on trained, near-transfer, far-transfer and retention items, one
    supported probe for the support gap, calibration from the episode forecasts since the last
    checkpoint, and dependence as the observed help-request rate. Never mutates the learner."""
    c, cur, max_hints = cfg["checkpoints"], cfg["curriculum"], int(cfg["support"]["max_hints"])
    seen = sorted(learner.last_seen.items(), key=lambda kv: kv[1], reverse=True)
    recent = [units[uid] for uid, _ in seen][: int(c["n_trained"])]
    retention = [units[uid] for uid, t in seen if episode - t >= int(c["retention_interval"])][: int(c["n_trained"])]

    def probe(problem, difficulty, hint=None):
        options, _ = build_options(problem, rng, None)
        lines = [f"Test question: {problem.text}"] + ([f"Hint 1: {hint}"] if hint else [])
        trial = Trial("probe_supported" if hint else "probe", lines, options, False, difficulty,
                      1.0 / max_hints if hint else 0.0, learner.record_line(), list(learner.history))
        return int(engine.choose(trial, learner, rng).kind == "correct")

    def mean(xs):
        return float(np.mean(xs)) if xs else float("nan")

    trained = [probe(u.problem, L.b_u(u.difficulty, cur)) for u in recent]
    supported = [probe(u.problem, L.b_u(u.difficulty, cur), hint=u.hints[0]) for u in recent]
    near = [probe(u.near_transfer, L.b_u(u.difficulty, cur) + cur["near_b_delta"]) for u in recent[: int(c["n_near"])]]
    far = [probe(u.far_transfer, L.b_u(u.difficulty, cur) + cur["far_b_delta"]) for u in recent[: int(c["n_far"])]]
    kept = [probe(u.problem, L.b_u(u.difficulty, cur)) for u in retention]
    return {"condition": condition, "learner_id": learner.learner_id, "checkpoint_episode": episode,
            "stratum": learner.stratum, "unaided_accuracy_trained": mean(trained),
            "supported_accuracy_trained": mean(supported), "support_gap": mean(supported) - mean(trained),
            "near_transfer_accuracy": mean(near), "far_transfer_accuracy": mean(far),
            "retention_accuracy": mean(kept), "n_retention_items": len(kept), "brier_score": L.brier(forecasts),
            "expected_calibration_error": L.ece(forecasts, int(c["ece_bins"])),
            "dependence_request_rate": learner.n_help / max(1, learner.n_episodes), **learner.state()}


def export_tables(processed: Path) -> dict:
    """Derive responses.csv, learner_state.parquet and checkpoints.csv from the JSONL sources."""
    records = read_jsonl(processed / "episodes.jsonl")
    responses, states = [], []
    for r in records:
        for t in r["turns"]:
            responses.append({"learner_id": r["learner_id"], "episode": r["episode"], "episode_id": r["episode_id"],
                              "condition": r["condition"], "protocol": r.get("protocol", r["condition"]), "stage": t["stage"], "turn": t["turn"],
                              "prompt": t["prompt_sha256"] or "", "response": t["kind"], "answer": t["value"],
                              "confidence": t["confidence"], "correctness": t["correct"],
                              "latency_proxy": t["latency"], "token_count": t["prompt_tokens"] or 0,
                              "requested_support": t["requested_support"], "explanation": t["explanation"],
                              "hint_depth": t["hint_depth"], "support": t["support_h"],
                              "p_correct": t["p_correct"], "layout": t["layout"]})
        p = r["proxies"]
        states.append({"condition": r["condition"], "protocol": r.get("protocol", r["condition"]),
                       "learner_id": r["learner_id"], "time": r["episode"],
                       "unit_id": r["unit_id"], **r["state_after"], "effort": r["effort"],
                       "effectiveness": r["effectiveness"], "support": p["support_used"],
                       "correctness": r["first_correct"], "retrieval": p["retrieval"], "offloading": p["offloading"],
                       "pe": r["pe"], "resolution": r["resolution"], "answer_provided": r["answer_provided"],
                       "hint_depth": r["hint_depth"], "help_requests": r["help_requests"], "attempts": r["attempts"],
                       "transfer_correct": r["transfer_correct"], "tutor_calls": len(r["tutor_turns"]),
                       "tutor_leaked": int(any(t["leaked"] for t in r["tutor_turns"]))})
    pd.DataFrame(responses).to_csv(processed / "responses.csv", index=False)
    pd.DataFrame(states).to_parquet(processed / "learner_state.parquet", index=False)
    checkpoints = pd.DataFrame(read_jsonl(processed / "checkpoints.jsonl"))
    checkpoints.to_csv(processed / "checkpoints.csv", index=False)
    return {"episodes": len(records), "responses": len(responses), "checkpoints": len(checkpoints)}


def summarize(processed: Path) -> str:
    """Per-condition means plus the §10.2 direction checks that need no extra runs."""
    state = pd.read_parquet(processed / "learner_state.parquet")
    lines = ["condition            first_try transfer help/ep reveal effort   K      D"]
    for cond, g in state.groupby("condition"):
        last = g.sort_values("time").groupby("learner_id").tail(1)
        lines.append(f"{cond:20} {g['correctness'].mean():8.2f} {g['transfer_correct'].mean():8.2f} "
                     f"{g['help_requests'].mean():7.2f} {g['answer_provided'].mean():6.2f} {g['effort'].mean():6.2f} "
                     f"{last['K'].mean():6.2f} {last['D'].mean():6.2f}")
    free = state[state["condition"] == FREE] if "protocol" in state else state.iloc[0:0]
    if len(free):
        shares = free["protocol"].value_counts(normalize=True).round(2).to_dict()
        line = f"free_choice: approach shares {shares}"
        if free["K"].nunique() >= 3:  # terciles need three distinct values; a tiny pilot has fewer
            band = pd.qcut(free["K"], 3, labels=["low", "mid", "high"], duplicates="drop")
            line += "; by K tercile " + str({str(k): g["protocol"].value_counts(normalize=True).round(2).to_dict()
                                             for k, g in free.groupby(band, observed=True)})
        lines.append(line)
    first = pd.read_csv(processed / "responses.csv").query("stage == 'first'").groupby("condition")
    lines.append("engine P(correct) on first attempts / mean confidence: " + ", ".join(
        f"{c} {g['p_correct'].mean():.2f} / {g['confidence'].mean():.2f}" for c, g in first))
    ck = pd.read_csv(processed / "checkpoints.csv") if (processed / "checkpoints.csv").stat().st_size else pd.DataFrame()
    if len(ck):
        by_stratum = ck.groupby("stratum")["unaided_accuracy_trained"].mean()
        mono = by_stratum.is_monotonic_increasing
        gap = ck["support_gap"].mean()
        lines.append(f"§10.2 prior-knowledge monotonicity (unaided accuracy by stratum {by_stratum.round(2).to_dict()}): "
                     f"{'ok' if mono else 'NOT monotone'}")
        lines.append(f"§10.2 support raises supported accuracy (mean support gap {gap:+.2f}): {'ok' if gap >= 0 else 'NOT ok'}")
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", default="config/default.yaml")
    ap.add_argument("--setting", choices=L.ARMS, help="parameter arm (default: config parameter_setting)")
    ap.add_argument("--engine", choices=["hybrid", "minitaur", "centaur", "logistic"])
    ap.add_argument("--tutor", choices=["openai", "fake"])
    ap.add_argument("--learners", type=int)
    ap.add_argument("--episodes", type=int)
    ap.add_argument("--conditions", nargs="+", choices=RUN_CONDITIONS)
    ap.add_argument("--policy", choices=["persistent", "gradual_fading", "immediate_withdrawal"])
    ap.add_argument("--tag", help="output folder under data/processed and outputs/logs (default: the engine name)")
    ap.add_argument("--resume", action="store_true", help="continue an existing data/processed/<tag>/episodes.jsonl")
    ap.add_argument("--summarize", metavar="DIR", help="print the summary of a finished output folder and exit")
    args = ap.parse_args(argv)
    if args.summarize:
        print(summarize(Path(args.summarize)))
        return 0

    cfg = load_config(Path(args.config), args.setting)
    root = Path(args.config).resolve().parent.parent
    if args.engine:
        cfg["engine"]["name"] = args.engine
    if args.tutor:
        cfg["tutor"]["provider"] = args.tutor
    if args.learners:
        cfg["population"]["n_learners"] = args.learners
    if args.episodes:
        cfg["run"]["episodes"] = args.episodes
    if args.conditions:
        cfg["run"]["conditions"] = args.conditions
    if args.policy:
        cfg["support"]["persistence_policy"] = args.policy
    run, tag = cfg["run"], args.tag or cfg["engine"]["name"]
    processed, logs = root / run["processed_dir"] / tag, root / run["logs_dir"] / tag
    processed.mkdir(parents=True, exist_ok=True)
    logs.mkdir(parents=True, exist_ok=True)
    episodes_path, ck_path = processed / "episodes.jsonl", processed / "checkpoints.jsonl"
    if episodes_path.exists() and not args.resume:
        print(f"{episodes_path} exists. Pass --resume to continue it, delete that folder to start over, or choose "
              f"another --tag. Nothing is regenerated silently (brief §4.3).", file=sys.stderr)
        return 2

    units = corpus.load_units(root / run["units_dir"])
    stimuli = corpus.load_stimuli(root / run["stimuli_dir"], units)
    order = corpus.curriculum_order(units)
    n, episodes, conditions = int(cfg["population"]["n_learners"]), int(run["episodes"]), list(run["conditions"])
    master = int(cfg["seeds"]["master"])

    # A resumed run must keep the population it started with. make_population draws the strata with
    # rng.choice(..., size=n), so changing --learners changes EVERY learner, not only the added ones:
    # learner 0 of a 40-learner draw is a different person from learner 0 of a 20-learner draw. Resuming
    # with a different n (or seed, or episode count) would silently blend two populations under one set
    # of learner_ids, so refuse instead.
    if args.resume:
        for prior in sorted(logs.glob("run_*.json")):
            before = json.loads(prior.read_text(encoding="utf-8"))
            for key, now in (("n_learners", n), ("n_episodes", episodes), ("master_seed", master)):
                if before.get(key) is not None and before[key] != now:
                    print(f"refusing to resume {tag}: it was started with {key}={before[key]} and this run "
                          f"has {key}={now}. Re-run with the original value, or choose another --tag.",
                          file=sys.stderr)
                    return 2
            break

    name = cfg["engine"]["name"]
    logistic = LogisticEngine(cfg["response"], cfg["population"]["theta_slope"])
    if name in TRANSCRIPT_ENGINES or name == "hybrid":
        model_key = cfg["engine"]["choice_model"] if name == "hybrid" else name
        if model_key in cfg["engine"].get("models", {}):  # never serve one engine's model under another's name
            cfg["engine"]["model"] = cfg["engine"]["models"][model_key]
        transcript = MinitaurEngine({**cfg["engine"], "name": model_key}, logs / f"calls_{model_key}.jsonl")
        print(f"{model_key} ready: {transcript.health_check()}")
        engine = HybridEngine(transcript, logistic) if name == "hybrid" else transcript
    else:
        engine = logistic
    tutor = None
    if any(c in AI_CONDITIONS or c == FREE for c in conditions):
        tutor = FakeTutor() if cfg["tutor"]["provider"] == "fake" else Tutor(cfg["tutor"], root / run["prompts_dir"],
                                                                             logs / "calls_tutor.jsonl")

    population = L.make_population(cfg["population"], n, master)
    L.seed_prior_records(population, cfg)  # §7.3: initial state -> observable prior record
    done = {(r["condition"], r["learner_id"], r["episode"]): r for r in read_jsonl(episodes_path)}
    ck_done = {(r["condition"], r["learner_id"], r["checkpoint_episode"]) for r in read_jsonl(ck_path)}
    ck_episodes = set(int(e) for e in cfg["checkpoints"]["episodes"]) | {episodes - 1}
    todo = n * episodes * len(conditions) - len(done)
    if name in TRANSCRIPT_ENGINES or name == "hybrid":
        print(f"{todo} episodes to run; at ~6 calls x ~4 s each expect ~{todo * 6 * 4 / 3600:.1f} h of Minitaur time.")

    started, clip_totals, n_new = time.time(), {k: 0 for k in L.STATE}, 0
    for condition in conditions:
        for base in population:
            learner = L.Learner.restore(base.snapshot())
            prior = [r for (c, l, _), r in done.items() if c == condition and l == learner.learner_id]
            if prior:
                learner = L.Learner.restore(max(prior, key=lambda r: r["episode"])["learner_after"])
            forecasts = []
            for ep in range(episodes):
                unit, key = order[ep % len(order)], (condition, learner.learner_id, ep)
                if key in done:
                    record = done[key]
                else:
                    if prior and ep < max(r["episode"] for r in prior):
                        raise RuntimeError(f"episodes.jsonl has a gap at {key}; delete the file to start over")
                    rng = np.random.default_rng([master, learner.learner_id, ep])
                    record = asdict(run_episode(learner, unit, {c: stimuli[(unit.unit_id, c)] for c in corpus.CONDITIONS},
                                                condition, ep, engine, tutor, cfg, rng))
                    append_jsonl(episodes_path, record)
                    n_new += 1
                    for k in L.STATE:
                        clip_totals[k] += record["clipped"].get(k, 0)
                forecasts += forecasts_of(record)
                if ep in ck_episodes:
                    if (condition, learner.learner_id, ep) not in ck_done:
                        rng = np.random.default_rng([master, learner.learner_id, ep, 99])
                        append_jsonl(ck_path, checkpoint(learner, condition, ep, units, engine, cfg, rng, forecasts))
                    forecasts = []
            print(f"{condition} learner {learner.learner_id}: {episodes} episodes done "
                  f"(K={learner.K:.2f} D={learner.D:.2f}, {time.time() - started:.0f}s elapsed)")

    counts = export_tables(processed)
    log = {"version": __version__, "recorded_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "config_sha256": hashlib.sha256(json.dumps(cfg, sort_keys=True).encode()).hexdigest(),
           "parameter_setting": cfg["parameter_setting"], "master_seed": master, "tag": tag,
           "engine": cfg["engine"]["name"],
           "engine_model": cfg["engine"]["model"] if name in TRANSCRIPT_ENGINES or name == "hybrid" else None,
           "engine_calls": getattr(engine, "calls", 0), "engine_seconds": round(getattr(engine, "seconds", 0.0), 1),
           "tutor": None if tutor is None else {"provider": cfg["tutor"]["provider"], "model": cfg["tutor"]["model"],
                                                "calls": tutor.calls, "leaks": tutor.leaks, "fallbacks": tutor.fallbacks},
           "n_learners": n, "n_episodes": episodes, "conditions": conditions, "n_units": len(units),
           "new_episodes_this_run": n_new, "row_counts": counts, "clip_counts_this_run": clip_totals,
           "warnings": ["coverage and correctness use config defaults (Phase I §5.4 semantic coverage not run)"],
           "python": platform.python_version(), "platform": platform.platform(),
           "packages": {"numpy": np.__version__, "pandas": pd.__version__}, "wall_time_s": round(time.time() - started, 1)}
    log_path = logs / f"run_{time.strftime('%Y%m%d_%H%M%S')}.json"
    log_path.write_text(json.dumps(log, indent=2), encoding="utf-8")
    print(summarize(processed))
    print(f"tables in {processed}, run log {log_path}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (EngineError, TutorError, ValueError) as error:
        print(f"\nSTOPPED: {error}", file=sys.stderr)
        sys.exit(1)

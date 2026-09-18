"""Phase V: the ten-year Monte Carlo scenario simulation (brief §9), vectorised over learners.

    python -m neurotutorsim.longitudinal --tag v_pilot --years 1 --draws 50 --learners 1000
    python -m neurotutorsim.longitudinal --tag v_main  --years 10 --draws 500 --learners 2000

Each parameter draw b resamples every {low, medium, high} leaf of the config (§9.3, A1), draws a fresh
population (eq. 15-16) and runs every scenario on it from the same initial state with common random numbers
keyed on (draw, episode), so the scenario contrasts of eq. 36-38 are paired within learner. The episode step
is an exact numeric mirror of `episode.run_episode` with the logistic engine (`tests/test_longitudinal.py::T1`
checks it against the reference loop): eq. 17-18 answers, the help-request and confidence models, the
proxies of §7.4, eq. 19-20, and `learners.step_state` in the `bounded` form of PLAN.md D3. Forgetting follows
calendar weeks (D4): 40 instructional weeks a year, then a 12-week break at a quarter of the term rate. The
neural state (Phase IV) rides along as the `plasticity.Accumulator`, so every mechanism and every Z control
is post hoc. Everything here is model-implied (brief §15): a scenario contrast, never a treatment effect.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from . import __version__, corpus
from . import learners as L
from . import choice_rule as CR
from . import plasticity as P
from .corpus import CONDITIONS
from .episode import FREE

ARMS = L.ARMS
PROTOCOL = {c: i for i, c in enumerate(CONDITIONS)}  # traditional 0, ai_scaffolding 1, ai_substitution 2
FREE_CENTAUR = "free_choice_centaur"  # free choice by the rule fitted to Centaur's picks (choice_rule.py), code 4
FREE_CODE = {FREE: 3, FREE_CENTAUR: 4}
POLICIES = ("persistent", "immediate_withdrawal", "gradual_fading")
STATES = ("K", "M", "R", "C", "D")
HIST_BINS = np.linspace(-1.0, 1.0, 202)  # 201 bins on [-1, 1] for the learner-level contrast histograms
U_SLOTS = 13  # per-episode uniform draws per learner (see `Draws`)
N_SLOTS = 2


# ------------------------------------------------------------------ parameter draws (§9.3)
def arm_leaves(node, prefix="") -> dict:
    """Every {low, medium, high} leaf of the raw config, keyed by dotted path."""
    out = {}
    if isinstance(node, dict):
        if set(node) == set(ARMS):
            out[prefix] = node
        else:
            for k, v in node.items():
                out.update(arm_leaves(v, f"{prefix}.{k}" if prefix else k))
    elif isinstance(node, list):
        for i, v in enumerate(node):
            out.update(arm_leaves(v, f"{prefix}[{i}]"))
    return out


def draw_parameters(raw: dict, draw_id: int, master: int, distribution: str = "triangular") -> tuple[dict, dict]:
    """Resolve the raw config for one draw: draw -1 is every leaf at medium; otherwise each leaf ~
    Triangular(min, medium, max) (A1) or Uniform(min, max) (F4), from default_rng([master, 11, draw_id])."""
    leaves = arm_leaves(raw)
    if draw_id < 0:
        values = {k: v["medium"] for k, v in leaves.items()}
    else:
        rng = np.random.default_rng([master, 11, draw_id])
        values = {}
        for k in sorted(leaves):
            v = leaves[k]
            lo, hi = min(v["low"], v["high"]), max(v["low"], v["high"])
            if distribution == "triangular":
                values[k] = float(rng.triangular(lo, v["medium"], hi)) if hi > lo else float(v["medium"])
            elif distribution == "uniform":
                values[k] = float(rng.uniform(lo, hi))
            else:
                raise ValueError(f"unknown distribution {distribution!r}")

    def resolve(node, prefix=""):
        if isinstance(node, dict):
            if set(node) == set(ARMS):
                return values[prefix]
            return {k: resolve(v, f"{prefix}.{k}" if prefix else k) for k, v in node.items()}
        if isinstance(node, list):
            return [resolve(v, f"{prefix}[{i}]") for i, v in enumerate(node)]
        return node

    cfg = resolve(raw)
    cfg["parameter_setting"] = "medium" if draw_id < 0 else f"draw_{draw_id}"
    return cfg, values


# ------------------------------------------------------------------ scenarios and knobs
@dataclass
class Scenario:
    """A protocol under a support policy, plus the §9.6 frontier knobs (A10): `adaptation` overrides
    `support.adaptation` of both AI protocols (a); `effort_retained` scales the answer-provided effort
    penalty to a4 (1 - e); `substitution_prob` is the chance an AI episode runs substitution instead of
    scaffolding (o); `fade_base` sets gradual fading (f = 1 - fade_base). `forget_scale` multiplies every
    forgetting rate (the §9.7 forgetting line, applied to both arms of a pair); `comparator` names the scenario
    this one is contrasted with (default: phase5.comparator); `mediate` holds one mediator at the comparator's
    value for the same learner and episode (§11.5): "E" or "F" in the K update, "D" in the decision rules."""
    name: str
    protocol: str
    policy: str = "persistent"
    adaptation: float | None = None
    effort_retained: float = 0.0
    substitution_prob: float = 0.0
    fade_base: float | None = None
    forget_scale: float = 1.0
    comparator: str | None = None
    mediate: str | None = None

    def __post_init__(self):
        if self.protocol not in CONDITIONS and self.protocol not in FREE_CODE:
            raise ValueError(f"unknown protocol {self.protocol!r}")
        if self.policy not in POLICIES:
            raise ValueError(f"unknown policy {self.policy!r}")
        if self.mediate not in (None, "E", "F", "D"):
            raise ValueError(f"unknown mediator {self.mediate!r}: use E, F or D")


def scenarios_from_config(p5: dict, names=None) -> list[Scenario]:
    out = []
    for name, spec in p5["scenarios"].items():
        if names is None or name in names:
            out.append(Scenario(name, spec["protocol"], spec.get("policy", "persistent")))
    missing = set(names or []) - {s.name for s in out}
    if missing:
        raise ValueError(f"scenarios not in config: {sorted(missing)}")
    return out


# ------------------------------------------------------------------ frontier, tipping-point and mediation designs
FRONTIER_A = tuple(round(float(x), 3) for x in np.linspace(0.1, 1.0, 7))  # personalisation quality a (§9.6, A10)
FRONTIER_E = tuple(round(float(x), 3) for x in np.linspace(0.0, 1.0, 7))  # retained effort e
FRONTIER_O = (0.0, 0.5, 1.0)  # answer substitution o (facets)
LINE_GRID = tuple(round(float(x), 2) for x in np.linspace(0.0, 1.0, 11))  # §9.7 one-at-a-time lines for e, o, f
FORGET_GRID = tuple(round(float(x), 4) for x in np.geomspace(0.25, 4.0, 11))  # forgetting multiplier, both arms
NEURAL_HALF_LIVES = (4, 8, 13, 20, 32, 52, 104)  # weeks (the neural diagram, D5)
NEURAL_LAMBDA_O = tuple(round(float(x), 4) for x in np.linspace(0.0, 1.0, 7))


def frontier_scenarios(kind: str) -> tuple[list[Scenario], dict, dict]:
    """(scenarios, knob values per scenario name, extra run_draw arguments) for PLAN.md S10.
    grid: traditional + 7 a x 7 e x 3 o scaffolding cells with f = 0 (Fig. 7a). lines: one-at-a-time lines through
    the scaffolding-no-fade point for e, o and f, plus the forgetting multiplier applied to both arms of each pair
    (eq. 40). neural: substitution vs traditional with one accumulator per half-life (Fig. 7b)."""
    trad = Scenario("traditional", "traditional")
    if kind == "grid":
        cells = [Scenario(f"grid_o{o:.2f}_a{a:.2f}_e{e:.2f}", "ai_scaffolding", adaptation=a, effort_retained=e, substitution_prob=o)
                 for o in FRONTIER_O for a in FRONTIER_A for e in FRONTIER_E]
        knobs = {s.name: {"a": s.adaptation, "e": s.effort_retained, "o": s.substitution_prob, "f": 0.0} for s in cells}
        return [trad] + cells, knobs, {}
    if kind == "lines":
        out, knobs = [trad], {}
        for x in LINE_GRID:
            for line, s in (("e", Scenario(f"line_e_{x:.2f}", "ai_scaffolding", effort_retained=x)),
                            ("o", Scenario(f"line_o_{x:.2f}", "ai_scaffolding", substitution_prob=x)),
                            ("f", Scenario(f"line_f_{x:.2f}", "ai_scaffolding", policy="gradual_fading", fade_base=1.0 - x))):
                out.append(s)
                knobs[s.name] = {"line": line, "x": x}
        for x in FORGET_GRID:
            pair = f"traditional_forget_{x:.4f}"
            out += [Scenario(pair, "traditional", forget_scale=x),
                    Scenario(f"line_forget_{x:.4f}", "ai_scaffolding", forget_scale=x, comparator=pair)]
            knobs[f"line_forget_{x:.4f}"] = {"line": "forget", "x": x}
        return out, knobs, {}
    if kind == "neural":
        return ([trad, Scenario("substitution", "ai_substitution")], {},
                {"half_lives": NEURAL_HALF_LIVES, "lambda_o_grid": NEURAL_LAMBDA_O})
    raise ValueError(f"unknown frontier {kind!r}")


def mediation_scenarios(base: list[Scenario], mediators, comparator: str) -> tuple[list[Scenario], dict]:
    """§11.5: every non-comparator scenario is repeated once per mediator, with that mediator held at the
    comparator's value for the same learner and episode. Contribution = 1 - SC(held) / SC(full), computed later."""
    out, knobs = list(base), {}
    for s in base:
        if s.name == comparator:
            continue
        for m in mediators:
            held = Scenario(f"{s.name}|hold_{m}", s.protocol, s.policy, s.adaptation, s.effort_retained,
                            s.substitution_prob, s.fade_base, s.forget_scale, s.comparator, m)
            out.append(held)
            knobs[held.name] = {"base": s.name, "mediator": m}
    return out, knobs


# ------------------------------------------------------------------ the population as arrays
@dataclass
class Pop:
    K: np.ndarray
    M: np.ndarray
    R: np.ndarray
    D: np.ndarray
    alpha: np.ndarray
    delta: np.ndarray
    bias: np.ndarray
    stratum: np.ndarray
    brier_sum: np.ndarray
    brier_n: np.ndarray
    streak: np.ndarray = None
    n_help: np.ndarray = None
    n_episodes: np.ndarray = None
    n_first: np.ndarray = None
    recent: np.ndarray = None  # (n, 5) first-try outcomes of the last five problems, seeded like the prior record
    last_picks: np.ndarray = None  # (n, 3) the last three free-choice picks (approach index, -1 = none yet)
    uses: np.ndarray = None  # (n, 3) free-choice picks per approach
    wins: np.ndarray = None  # (n, 3) follow-up questions solved after each approach

    def __post_init__(self):
        n = len(self.K)
        for k in ("streak", "n_help", "n_episodes", "n_first"):
            if getattr(self, k) is None:
                setattr(self, k, np.zeros(n, dtype=np.int64))
        if self.recent is None:
            self.recent = np.full((n, L.RECENT_N), 0.5)
        if self.last_picks is None:
            self.last_picks = np.full((n, CR.HABIT_WINDOW), -1, dtype=np.int64)
        if self.uses is None:
            self.uses = np.zeros((n, 3))
        if self.wins is None:
            self.wins = np.zeros((n, 3))

    @property
    def C(self):
        return 1.0 - self.brier_sum / np.maximum(self.brier_n, 1)

    @classmethod
    def draw(cls, cfg: dict, n: int, seed: int) -> "Pop":
        """`learners.make_population` plus the §7.3 prior record seeding of the running Brier score."""
        pop = L.make_population(cfg["population"], n, seed)
        L.seed_prior_records(pop, cfg)  # the recent-form window starts from the prior record, as in Phase III
        prior = int(cfg["population"]["prior_problems"])
        arr = lambda k: np.array([getattr(l, k) for l in pop], dtype=np.float64)  # noqa: E731
        C = arr("C")
        return cls(arr("K"), arr("M"), arr("R"), arr("D"), arr("alpha"), arr("delta"), arr("confidence_bias"),
                   np.array([l.stratum for l in pop], dtype=np.int64), prior * (1.0 - C), np.full(n, prior, dtype=np.int64),
                   recent=np.array([l.recent for l in pop], dtype=np.float64))

    def copy(self) -> "Pop":
        return Pop(**{k: v.copy() for k, v in self.__dict__.items()})

    def note(self, first: np.ndarray, chose: np.ndarray, pick: np.ndarray, transfer: np.ndarray) -> None:
        """The observable record after an episode, as `Learner.note_episode` keeps it: the last five first-try
        outcomes for everyone; for rows that chose freely (`chose`), the pick joins the last three picks and the
        pick's counts of uses and follow-up questions solved."""
        self.recent = np.concatenate([self.recent[:, 1:], np.asarray(first, float)[:, None]], axis=1)
        rows = np.flatnonzero(chose)
        if len(rows):
            self.last_picks[rows] = np.concatenate([self.last_picks[rows, 1:], pick[rows, None]], axis=1)
            self.uses[rows, pick[rows]] += 1
            self.wins[rows, pick[rows]] += np.asarray(transfer, float)[rows]

    def tile(self, reps: int) -> "Pop":
        """The population repeated `reps` times along learners (2-D fields are tiled by row)."""
        return Pop(**{k: np.tile(v, (reps,) + (1,) * (v.ndim - 1)) for k, v in self.__dict__.items()})


class Draws:
    """Common random numbers for one episode of one draw (§9.3, PLAN.md S6): uniform slots 0 approach,
    1 first answer, 2-4 help request at hint 1-3, 5-7 answer at hint 1-3, 8 substitution re-answer,
    9 transfer, 10 frontier protocol mix, 11-12 spare; normal slots 0 first confidence, 1 transfer confidence.
    Keyed on (master, draw, episode) and tiled across scenarios, so every scenario meets the same numbers."""

    def __init__(self, master: int, draw_id: int, n: int, reps: int):
        self.master, self.draw_id, self.n, self.reps = master, draw_id, n, reps

    def episode(self, t: int) -> tuple[np.ndarray, np.ndarray]:
        b = self.draw_id + 1  # seeds must be non-negative; the central draw is -1
        U = np.random.default_rng([self.master, 13, b, t]).random((U_SLOTS, self.n))
        N = np.random.default_rng([self.master, 14, b, t]).normal(size=(N_SLOTS, self.n))
        return np.tile(U, (1, self.reps)), np.tile(N, (1, self.reps))


# ------------------------------------------------------------------ the simulator
@dataclass
class Curriculum:
    units: list[str]  # sorted unit ids (Z row order)
    order: np.ndarray  # positions into `units`, in curriculum order
    difficulty: np.ndarray  # per unit position
    concepts: list[str]

    @classmethod
    def load(cls, units: dict) -> "Curriculum":
        ids = sorted(units)
        pos = {u: i for i, u in enumerate(ids)}
        order = np.array([pos[u.unit_id] for u in corpus.curriculum_order(units)], dtype=np.int64)
        return cls(ids, order, np.array([units[u].difficulty for u in ids], dtype=np.float64), [units[u].concept for u in ids])


@dataclass
class EpisodeOut:
    """Per-learner results of one vectorised episode."""
    protocol: np.ndarray
    first: np.ndarray
    transfer: np.ndarray
    help: np.ndarray
    reveal: np.ndarray
    resolved: np.ndarray
    E: np.ndarray
    F: np.ndarray
    p1: np.ndarray
    forecasts: list  # [(confidence, correct)] arrays for the first answer and the transfer answer
    clipped: np.ndarray  # per learner: how many of K, M, R, D left [0, 1] before clipping
    k_idx: np.ndarray  # the stimulus row of Z each learner read (unit x protocol), for extra accumulators
    channels: np.ndarray  # (learners, 5) accumulator inputs of this episode (plasticity.CHANNELS)


@dataclass
class Sim:
    cfg: dict
    cur: Curriculum
    scenarios: list[Scenario]
    Z: np.ndarray | None = None  # (90, P), or None when no TRIBE run is on disk (then no neural outputs)
    W: np.ndarray | None = None
    networks: list[str] = field(default_factory=list)
    zero_plasticity: bool = False  # the §10.3 control: every mechanism weight is zeroed, so N is exactly 0
    zero_effort: bool = False  # the §10.3 control: a1-a4 = 0, so E is the constant logistic(a0)
    form: str = "bounded"
    epw: int = 3
    choice_rule: dict | None = None  # choice_rule.json, loaded when a scenario uses FREE_CENTAUR
    choice_params: np.ndarray | None = None  # the rule's parameters for the current draw

    @classmethod
    def build(cls, cfg: dict, units: dict, scenarios: list[Scenario], root: Path, zero_plasticity=False,
              zero_effort=False, form=None, epw=None, neural: bool = True) -> "Sim":
        p = cfg["plasticity"]
        Z = W = None
        nets: list[str] = []
        tribe_dir = root / p["tribe_dir"]
        if neural and (tribe_dir / f"wpm{int(p['wpm'])}" / "tribe_metrics.parquet").exists():
            Z, keys, _ = P.load_z(tribe_dir, int(p["wpm"]), p["metric"], p["winsorize"])
            W, nets = P.load_networks(tribe_dir, p["network_weights"])
            if [u for u, _ in keys][::3] != sorted(units):
                raise ValueError("TRIBE patterns and the corpus disagree on the units")
        elif neural:
            print(f"no TRIBE run at {tribe_dir}: neural outputs are skipped", file=sys.stderr)
        rule = None
        if any(s.protocol == FREE_CENTAUR for s in scenarios):
            path = root / cfg["phase5"]["choice_rule"]
            if not path.exists():
                raise FileNotFoundError(f"{path} does not exist: fit it first (python -m neurotutorsim.choice_rule fit "
                                        f"--runs data/processed/centaur_main) or drop the {FREE_CENTAUR} scenario")
            rule = json.loads(path.read_text(encoding="utf-8"))
            if rule["features"] != list(CR.FEATURES):
                raise ValueError(f"{path} was fitted with other features: {rule['features']}")
        return cls(cfg, Curriculum.load(units), scenarios, Z, W, nets, zero_plasticity, zero_effort,
                   form or cfg["phase5"]["update_form"], int(epw or cfg["calendar"]["episodes_per_week"]), rule)

    def set_draw(self, cfg: dict, draw_id: int) -> None:
        """The draw's configuration and, for the Centaur-calibrated rule, its parameters: the point estimate for
        the central draw, bootstrap vector draw_id mod B otherwise (the rule's uncertainty enters the draws)."""
        self.cfg = cfg
        if self.choice_rule is not None:
            boot = self.choice_rule["bootstrap"]
            self.choice_params = np.array(self.choice_rule["params"] if draw_id < 0 or not boot else boot[draw_id % len(boot)])

    # -- per-episode arithmetic ------------------------------------------------------------
    def episodes_per_year(self) -> int:
        return int(self.cfg["calendar"]["weeks_per_year"]) * self.epw

    def difficulty(self, unit_pos: int, year: int, ramp: float) -> float:
        """eq. 17 b_u of a unit, raised by `ramp` per completed school year (A2, the §9.1 progression)."""
        return L.b_u(self.cur.difficulty[unit_pos], self.cfg["curriculum"]) + ramp * year

    def p_correct(self, pop: Pop, b, support_h=0.0):
        r, theta = self.cfg["response"], self.cfg["population"]["theta_slope"] * (pop.K - 0.5)
        return L.logistic(theta - b + r["rho"] * pop.R + r["kappa"] * pop.M + r["omega"] * support_h)

    def p_request(self, pop: Pop, b, D=None):
        """P(ask for help) of the help-request model; `D` overrides the learner's own D (the §11.5 D mediator)."""
        r, theta = self.cfg["response"], self.cfg["population"]["theta_slope"] * (pop.K - 0.5)
        D = pop.D if D is None else D
        return L.logistic(r["request_intercept"] + r["request_dependence_slope"] * D - r["request_ability_slope"] * (theta - b))

    def rating(self, p, pop: Pop, noise):
        """`LogisticEngine.confidence`: rating 1 + round(4 clip(p + bias + noise)), on the (rating - 1) / 4 scale."""
        c = 1.0 + np.rint(4.0 * np.clip(p + pop.bias + self.cfg["response"]["confidence_noise_sd"] * noise, 0.0, 1.0))
        return (c - 1.0) / 4.0

    def help_cap(self, pop: Pop, policy: np.ndarray, fade_base: np.ndarray) -> np.ndarray:
        """`learners.help_cap` per learner (policy 0 persistent, 1 immediate withdrawal, 2 gradual fading)."""
        s, m = self.cfg["support"], int(self.cfg["support"]["max_hints"])
        cap = np.full(len(pop.K), m, dtype=np.int64)
        rapid = policy == 1
        cap[rapid & (pop.streak >= int(s["withdrawal_success_threshold"]))] = 0
        grad = policy == 2
        if grad.any():
            cap[grad] = np.ceil(m * fade_base[grad] ** pop.streak[grad]).astype(np.int64)
        return cap

    def step(self, pop: Pop, unit_pos: int, year: int, ramp: float, protocol: np.ndarray, policy: np.ndarray,
             knobs: dict, U: np.ndarray, N: np.ndarray, acc: P.Accumulator | None, decay: float) -> EpisodeOut:
        """One episode for every learner in `pop`, in place: the numeric mirror of `episode.run_episode` with the
        logistic engine. `protocol` is per learner (3 = free choice, resolved by the softmax-in-D rule of
        `LogisticEngine.approach`); `knobs` holds per-learner arrays adaptation (or NaN), effort_retained,
        substitution_prob and fade_base (the §9.6 frontier axes, A10), forget (the forgetting multiplier), and for
        §11.5 `src` (the comparator row of the same learner) with the masks med_E, med_F, med_D: a held D enters
        the decision rules and a held E or F the K update, each taken from `src` in this same episode."""
        cfg, s, m = self.cfg, self.cfg["support"], int(self.cfg["support"]["max_hints"])
        n = len(pop.K)
        b = self.difficulty(unit_pos, year, ramp)
        theta = cfg["population"]["theta_slope"] * (pop.K - 0.5)
        cap = self.help_cap(pop, policy, knobs["fade_base"])
        src = knobs.get("src")
        D_dec = pop.D if src is None or not knobs["med_D"].any() else np.where(knobs["med_D"], pop.D[src], pop.D)
        proto = protocol.copy()
        free = proto == 3  # logit(substitution) = +s (D - 0.5), logit(traditional) = -s (D - 0.5), scaffolding 0
        if free.any():
            sc = cfg["response"]["request_dependence_slope"] * (D_dec[free] - 0.5)
            w = np.stack([np.exp(-sc), np.ones_like(sc), np.exp(sc)], axis=1)
            cum = np.cumsum(w / w.sum(axis=1, keepdims=True), axis=1)
            proto[free] = (U[0, free][:, None] > cum).sum(axis=1).clip(0, 2)
        centaur = proto == 4  # the rule fitted to Centaur's picks, on what Centaur would read (choice_rule.py)
        if centaur.any():
            q = CR.probabilities(self.choice_params, CR.design(pop.last_picks[centaur], pop.uses[centaur],
                                                               pop.wins[centaur], pop.recent[centaur].mean(axis=1)))
            proto[centaur] = (U[0, centaur][:, None] > np.cumsum(q, axis=1)).sum(axis=1).clip(0, 2)
        mix = (proto == 1) & (U[10] < knobs["substitution_prob"])  # frontier knob o
        proto[mix] = 2
        p1 = self.p_correct(pop, b)
        first = U[1] < p1
        conf1 = self.rating(p1, pop, N[0])
        resolved, help_, depth = first.copy(), np.zeros(n, dtype=np.int64), np.zeros(n, dtype=np.int64)
        answers = np.ones(n, dtype=np.int64)
        reveal = np.zeros(n, dtype=bool)
        sub = (proto == 2) & ~first & (cap > 0)  # substitution: the full solution, then one re-answer at h = 1
        if sub.any():
            depth[sub] = m
            reveal[sub] = True
            resolved[sub] = U[8, sub] < self.p_correct(pop, b, 1.0)[sub]
            answers[sub] += 1
        hint = (proto <= 1) & ~first & (cap > 0)  # hints / tutor turns: ask for more or answer at h = k / 3
        p_req = self.p_request(pop, b, D_dec)
        for k in range(1, m + 1):
            active = hint & ~resolved & (depth < cap) & (depth == k - 1)
            if not active.any():
                break
            depth[active] = k
            req = active & (k < cap) & (U[1 + k] < p_req)
            help_ += req
            ans = active & ~req
            answers += ans
            resolved |= ans & (U[4 + k] < self.p_correct(pop, b, k / m))
        reveal |= hint & ~resolved & (depth >= m)
        attempts = np.where(sub, 1, answers)  # substitution: the answers before the reveal
        p_t = self.p_correct(pop, b + cfg["curriculum"]["near_b_delta"])  # transfer: unaided, one attempt
        transfer = U[9] < p_t
        conf_t = self.rating(p_t, pop, N[1])
        explanation = np.where(reveal, 0.0, 1.0 - depth / m)  # the proxies exactly as episode.run_episode
        adapt = np.array([s["adaptation"][c] for c in CONDITIONS])[proto]
        adapt = np.where((proto >= 1) & ~np.isnan(knobs["adaptation"]), knobs["adaptation"], adapt)
        p = L.Proxies(
            attempt=attempts / (m + 1), retrieval=np.where(first, 1.0, 0.5), explanation=explanation,
            answer_provided=reveal.astype(float), offloading=1.0 - explanation,
            correct_after_error=(~first & resolved & ~reveal).astype(float), transfer_success=transfer.astype(float),
            support_used=np.where(reveal, 1.0, depth / m), support_faded=1.0 - cap / m, independent_success=first.astype(float),
            adaptation=np.where(depth > 0, adapt, 0.0), mismatch=np.minimum(1.0, np.abs(b - theta) / s["mismatch_scale"]),
            coverage=cfg["effectiveness"]["coverage_default"], correctness=cfg["effectiveness"]["correctness_default"])
        ec = dict(cfg["effort"])
        if self.zero_effort:
            ec.update(a1=0.0, a2=0.0, a3=0.0, a4=0.0)
        E = L.logistic(ec["a0"] + ec["a1"] * p.attempt + ec["a2"] * p.retrieval + ec["a3"] * p.explanation
                       - ec["a4"] * (1.0 - knobs["effort_retained"]) * p.answer_provided)
        F = L.effectiveness(p, cfg["effectiveness"])
        delta_scale = L.calendar_delta_scale({**cfg["calendar"], "episodes_per_week": self.epw}) * knobs.get("forget", 1.0)
        raw = L.step_state(pop.K, pop.M, pop.R, pop.D, pop.alpha, pop.delta, p, E, F, cfg["updates"], self.form, delta_scale)
        if src is not None and (knobs["med_E"].any() or knobs["med_F"].any()):
            held = knobs["med_E"] | knobs["med_F"]
            E_k, F_k = np.where(knobs["med_E"], E[src], E), np.where(knobs["med_F"], F[src], F)
            K_held = L.step_state(pop.K, pop.M, pop.R, pop.D, pop.alpha, pop.delta, p, E_k, F_k, cfg["updates"], self.form,
                                  delta_scale)["K"]
            raw["K"] = np.where(held, K_held, raw["K"])
        clipped = np.zeros(n, dtype=np.int64)
        for key, v in raw.items():
            clipped += (v < 0.0) | (v > 1.0)
            setattr(pop, key, np.clip(v, 0.0, 1.0))
        pop.brier_sum += (conf1 - first) ** 2 + (conf_t - transfer) ** 2
        pop.brier_n += 2
        pop.streak = np.where(first, pop.streak + 1, 0)
        pop.n_help += help_
        pop.n_episodes += 1
        pop.n_first += first
        pop.note(first, centaur, proto, transfer)
        k_idx = unit_pos * len(CONDITIONS) + proto
        channels = P.channel_values(E, np.abs(first - p1), p.correct_after_error, p.retrieval, p.offloading)
        if acc is not None:
            acc.step(k_idx, channels, decay)
        return EpisodeOut(proto, first, transfer, help_, reveal, resolved, E, F, p1,
                          [(conf1, first.astype(float)), (conf_t, transfer.astype(float))], clipped, k_idx, channels)

    # -- end-of-year test outcomes (A11-A13) ---------------------------------------------------
    def expected(self, pop: Pop, year: int, ramp: float, only: tuple = ()) -> dict:
        """Expected probabilities over the 30 units on the current state (A11): unaided, near and far transfer,
        supported with one hint (A12), P(request) (A13), and the per-unit unaided matrix for the difficulty
        check (gate 18, G2). `only` limits the work to the named outcomes."""
        cur, m = self.cfg["curriculum"], int(self.cfg["support"]["max_hints"])
        bs = [self.difficulty(u, year, ramp) for u in range(len(self.cur.units))]
        want = set(only) or {"unaided", "near", "far", "supported", "p_request"}
        out = {}
        if want & {"unaided", "supported"}:
            per_unit = np.stack([self.p_correct(pop, b) for b in bs], axis=1)
            out["unaided"], out["per_unit"] = per_unit.mean(axis=1), per_unit
        if "near" in want:
            out["near"] = np.mean([self.p_correct(pop, b + cur["near_b_delta"]) for b in bs], axis=0)
        if "far" in want:
            out["far"] = np.mean([self.p_correct(pop, b + cur["far_b_delta"]) for b in bs], axis=0)
        if "supported" in want:
            out["supported"] = np.mean([self.p_correct(pop, b, 1.0 / m) for b in bs], axis=0)
            out["support_gap"] = out["supported"] - out["unaided"]
        if "p_request" in want:
            out["p_request"] = np.mean([self.p_request(pop, b) for b in bs], axis=0)
        return out

    def neural(self, values: np.ndarray | None, mechanism: str) -> np.ndarray | None:
        """Network states (learners, networks) of one mechanism from accumulator values (learners, 5, 90)."""
        if values is None or self.Z is None:
            return None
        pcfg = {**self.cfg["plasticity"], "eta": 0.0 if self.zero_plasticity else self.cfg["plasticity"]["eta"]}
        return P.network_state(P.neural_state(values, P.mechanism_weights(mechanism, pcfg), self.Z), self.W)


# ------------------------------------------------------------------ one draw
def _summary(delta: np.ndarray) -> dict:
    return {"estimate": float(delta.mean()), "sd": float(delta.std(ddof=1)) if len(delta) > 1 else float("nan"),
            "median": float(np.median(delta)), "prsup": float((delta > 0).mean()), "share_neg": float((delta < 0).mean())}


def run_draw(sim: Sim, draw_id: int, cfg: dict, n: int, years: int, master: int, drawn: dict, n_episodes=None,
             subsample: int = 100, keep_yearly: bool = True, keep_acc: bool = False, keep_episodes: bool = False,
             break_scale=None, half_lives=None, lambda_o_grid=None) -> dict:
    """Simulate every scenario on one drawn population (§9.3) and return this draw's tables and arrays.
    `n_episodes` truncates the calendar (T1 runs 30 episodes of year 1). Each year ends with the tests on the
    pre-break state, then the break (K and M by `learners.apply_break`; N by the same break_weeks x
    break_decay_scale weeks of term-time decay, user decision 2026-09-18), then retention on the post-break
    state. `final` is the state before the last break. `half_lives` and `lambda_o_grid` add the neural diagram
    (PLAN.md S10, D5): one extra accumulator per half-life, and mechanism D's network d for every lambda_O."""
    p5, cal = cfg["phase5"], dict(cfg["calendar"])
    if break_scale is not None:
        cal["break_decay_scale"] = float(break_scale)
    sim.set_draw(cfg, draw_id)
    scen, S = sim.scenarios, len(sim.scenarios)
    names = [s.name for s in scen]
    comp_of = [names.index(c) if (c := s.comparator or p5["comparator"]) in names else None for s in scen]
    pop = Pop.draw(cfg, n, master * 1000 + draw_id).tile(S)
    rows_n = n * S
    sidx = np.repeat(np.arange(S), n)  # scenario of each row; rows are scenario-major
    protocol = np.array([FREE_CODE.get(s.protocol, PROTOCOL.get(s.protocol, -1)) for s in scen])[sidx]
    policy = np.array([POLICIES.index(s.policy) for s in scen])[sidx]
    knobs = {"adaptation": np.array([np.nan if s.adaptation is None else s.adaptation for s in scen])[sidx],
             "effort_retained": np.array([s.effort_retained for s in scen], dtype=float)[sidx],
             "substitution_prob": np.array([s.substitution_prob for s in scen], dtype=float)[sidx],
             "fade_base": np.array([cfg["support"]["fade_base"] if s.fade_base is None else s.fade_base for s in scen])[sidx],
             "forget": np.array([s.forget_scale for s in scen], dtype=float)[sidx]}
    if any(s.mediate for s in scen):  # §11.5: each row's comparator row for the same learner
        knobs["src"] = np.array([(si if comp_of[si] is None else comp_of[si]) for si in range(S)])[sidx] * n + np.tile(np.arange(n), S)
        for m in ("E", "F", "D"):
            knobs[f"med_{m}"] = np.array([s.mediate == m for s in scen])[sidx]
    draws = Draws(master, draw_id, n, S)
    ramp = float(p5["ramp_per_year"])
    per_year = sim.episodes_per_year()
    T = int(n_episodes) if n_episodes is not None else years * per_year
    acc = P.Accumulator(rows_n, len(sim.cur.units) * len(CONDITIONS)) if sim.Z is not None else None
    decay = P.decay_per_episode(cfg["plasticity"]["half_life_weeks"], sim.epw)
    break_factor_n = (1.0 - decay) ** (sim.epw * cal["break_weeks"] * cal["break_decay_scale"])
    diagram = {}  # half-life -> (accumulator, per-episode decay) for the neural diagram
    if half_lives is not None and sim.Z is not None:
        for hl in half_lives:
            diagram[float(hl)] = (P.Accumulator(rows_n, len(sim.cur.units) * len(CONDITIONS)), P.decay_per_episode(hl, sim.epw))
    bins = int(cfg["checkpoints"]["ece_bins"])
    sub = min(subsample, n)
    sub_rows = (np.arange(S)[:, None] * n + np.arange(sub)[None, :]).ravel()
    gw = p5["G"]["weights"]
    checkpoint_years = {int(y) for y in p5["checkpoint_years"]}
    rows_idx = np.arange(rows_n)

    def by_scenario(x):  # (rows,) -> (S,) means
        return np.asarray(x, dtype=np.float64).reshape(S, n).mean(axis=1)

    def new_tally():
        z = {k: np.zeros(rows_n) for k in ("first", "transfer", "help", "reveal", "E", "F", "clipped", "brier")}
        z.update(proto=np.zeros((rows_n, 3)), ece=np.zeros((3, S * bins)), episodes=0)
        return z

    levels, contrasts, neural, yearly, weekly, episodes, mean_acc, neural_diagram = [], [], [], [], [], [], [], []
    hist, acc_sub, final = {}, {}, {}
    # ---- year 0: the tests on the drawn population before any episode (the §10.2 baseline, Fig. 5 starting point)
    ex0 = sim.expected(pop, 0, ramp)
    base = {k: by_scenario(getattr(pop, k)) for k in STATES}
    base.update({k: by_scenario(ex0[k]) for k in ("unaided", "near", "far", "supported", "support_gap", "p_request")})
    unaided0, strata0 = ex0["unaided"].reshape(S, n), pop.stratum.reshape(S, n)
    for st in range(3):
        base[f"unaided_stratum{st}"] = np.array([unaided0[i][strata0[i] == st].mean() if (strata0[i] == st).any()
                                                 else np.nan for i in range(S)])
    for outcome, v in base.items():
        levels.append(pd.DataFrame({"draw_id": draw_id, "scenario": names, "year": 0, "kind": "level",
                                    "outcome": outcome, "estimate": np.asarray(v, dtype=np.float64)}))
    tally, week_first = new_tally(), np.zeros(rows_n)
    for t in range(T):
        year = t // per_year
        unit_pos = int(sim.cur.order[t % len(sim.cur.order)])
        U, N = draws.episode(t)
        out = sim.step(pop, unit_pos, year, ramp, protocol, policy, knobs, U, N, acc, decay)
        for d_acc, d_decay in diagram.values():
            d_acc.step(out.k_idx, out.channels, d_decay)
        for k, v in (("first", out.first), ("transfer", out.transfer), ("help", out.help), ("reveal", out.reveal),
                     ("E", out.E), ("F", out.F), ("clipped", out.clipped)):
            tally[k] += v
        tally["proto"][rows_idx, out.protocol] += 1
        for conf, y in out.forecasts:  # Brier and the 10-bin ECE of this year's forecasts, per scenario
            tally["brier"] += (conf - y) ** 2
            b_idx = sidx * bins + np.minimum((conf * bins).astype(int), bins - 1)
            tally["ece"][0] += np.bincount(b_idx, minlength=S * bins)
            tally["ece"][1] += np.bincount(b_idx, weights=conf, minlength=S * bins)
            tally["ece"][2] += np.bincount(b_idx, weights=y, minlength=S * bins)
        tally["episodes"] += 1
        week_first += out.first
        if keep_episodes and year == 0:
            episodes.append(pd.DataFrame({
                "draw_id": draw_id, "scenario": np.repeat(names, n), "learner_id": np.tile(np.arange(n), S), "episode": t,
                "unit_id": sim.cur.units[unit_pos], "difficulty": sim.cur.difficulty[unit_pos], "stratum": pop.stratum,
                "protocol": np.array(CONDITIONS)[out.protocol], "first_correct": out.first.astype(np.int8),
                "transfer_correct": out.transfer.astype(np.int8), "help_requests": out.help.astype(np.int8),
                "reveal": out.reveal.astype(np.int8), "effort": out.E, "effectiveness": out.F, "p_correct": out.p1,
                "K": pop.K.copy(), "D": pop.D.copy()}))
        if (t + 1) % sim.epw == 0:  # end of an instructional week (far transfer weekly in year 1, then monthly)
            week = (t + 1) // sim.epw
            far = by_scenario(sim.expected(pop, year, ramp, only=("far",))["far"]) if year == 0 or week % 4 == 0 \
                else np.full(S, np.nan)
            weekly.append(pd.DataFrame({"draw_id": draw_id, "scenario": names, "week": week, "year": year + 1,
                                        "K": by_scenario(pop.K), "D": by_scenario(pop.D),
                                        "first_try": by_scenario(week_first) / sim.epw, "far": far}))
            week_first[:] = 0
        if not ((t + 1) % per_year == 0 or t + 1 == T):
            continue

        # ---- end of a school year: the tests on the pre-break state (A11-A13)
        y1, eps = year + 1, tally["episodes"]
        ex = sim.expected(pop, year, ramp)
        end = {k: getattr(pop, k).copy() for k in STATES}
        final = end
        values = acc.values() if acc is not None else None
        nets = {m: sim.neural(values, m) for m in P.MECHANISMS} if values is not None else {}
        diagram_values = ({hl: d_acc.values() for hl, (d_acc, _) in diagram.items()}  # pre-break, like `values`
                          if diagram and (y1 in checkpoint_years or t + 1 == T) else {})
        lv = {k: by_scenario(v) for k, v in end.items()}
        lv.update({k: by_scenario(ex[k]) for k in ("unaided", "near", "far", "supported", "support_gap", "p_request")})
        lv["support_gap_min"] = ex["support_gap"].reshape(S, n).min(axis=1)
        unaided, strata = ex["unaided"].reshape(S, n), pop.stratum.reshape(S, n)
        for st in range(3):
            lv[f"unaided_stratum{st}"] = np.array([unaided[i][strata[i] == st].mean() if (strata[i] == st).any()
                                                   else np.nan for i in range(S)])
        for k in ("first", "transfer", "help", "reveal"):
            lv[f"{k}_rate"] = by_scenario(tally[k]) / eps
        lv["effort"], lv["effectiveness"] = by_scenario(tally["E"]) / eps, by_scenario(tally["F"]) / eps
        for ci, c in enumerate(CONDITIONS):
            lv[f"share_{c}"] = tally["proto"][:, ci].reshape(S, n).sum(axis=1) / (n * eps)
        lv["brier"] = tally["brier"].reshape(S, n).sum(axis=1) / (2 * n * eps)
        counts, sum_c, sum_y = (a.reshape(S, bins) for a in tally["ece"])
        lv["ece"] = np.abs(sum_y - sum_c).sum(axis=1) / counts.sum(axis=1)  # sum_b (n_b / N) |mean_y - mean_c|
        lv["clips"] = tally["clipped"].reshape(S, n).sum(axis=1)
        near_bound = np.zeros(rows_n, dtype=bool)
        for k in ("K", "M", "R", "D"):
            near_bound |= (end[k] < 0.01) | (end[k] > 0.99)
        lv["near_bound_share"] = by_scenario(near_bound)
        lv["difficulty_slope"] = np.polyfit(sim.cur.difficulty, ex["per_unit"].reshape(S, n, -1).mean(axis=1).T, 1)[0]

        # ---- the break, then retention on the post-break state
        pop.K, pop.M = L.apply_break(pop.K, pop.M, pop.delta * knobs["forget"], cal, cfg["updates"])
        if acc is not None:
            acc.apply_decay(break_factor_n)
            acc.renormalise()
        for d_acc, d_decay in diagram.values():
            d_acc.apply_decay((1.0 - d_decay) ** (sim.epw * cal["break_weeks"] * cal["break_decay_scale"]))
            d_acc.renormalise()
        retention = sim.expected(pop, year, ramp, only=("unaided",))["unaided"]
        lv["retention"] = by_scenario(retention)
        lv["retention_below_share"] = by_scenario(retention < ex["unaided"])
        for outcome, v in lv.items():
            levels.append(pd.DataFrame({"draw_id": draw_id, "scenario": names, "year": y1, "kind": "level",
                                        "outcome": outcome, "estimate": np.asarray(v, dtype=np.float64)}))

        # ---- paired contrasts against each scenario's comparator (eq. 37-39 and 44)
        for si, s in enumerate(scen):
            comp = comp_of[si]
            if comp is None or comp == si:
                continue
            cs, sl = slice(comp * n, (comp + 1) * n), slice(si * n, (si + 1) * n)
            d = {k: end[k][sl] - end[k][cs] for k in ("K", "R", "M", "D")}
            d.update({k: ex[k][sl] - ex[k][cs] for k in ("unaided", "far", "p_request")})
            d["retention"] = retention[sl] - retention[cs]
            d["G"] = gw["K"] * d["K"] + gw["R"] * d["R"] + gw["M"] * d["M"] - gw["D"] * d["D"]
            for outcome, delta in d.items():
                contrasts.append({"draw_id": draw_id, "scenario": s.name, "year": y1, "kind": "contrast",
                                  "outcome": outcome, **_summary(delta)})
                if y1 in checkpoint_years or t + 1 == T:
                    key = (s.name, y1, outcome)
                    hist[key] = hist.get(key, 0) + np.histogram(np.clip(delta, -1.0, 1.0), HIST_BINS)[0]
            for m, Nn in nets.items():
                for ni, net in enumerate(sim.networks):
                    sm = _summary(Nn[sl, ni] - Nn[cs, ni])
                    neural.append({"draw_id": draw_id, "scenario": s.name, "year": y1, "mechanism": m, "network": net,
                                   "mean": sm["estimate"], "sd": sm["sd"], "prsup": sm["prsup"],
                                   "d": sm["estimate"] / sm["sd"] if sm["sd"] > 0 else 0.0})
            if values is not None and (y1 in checkpoint_years or t + 1 == T):
                mean_acc.append({"draw_id": draw_id, "scenario": s.name, "year": y1,
                                 "diff": (values[sl] - values[cs]).mean(axis=0).astype(np.float32)})
        for hl, d_values in diagram_values.items():  # mechanism D per half-life x lambda_O (D5), pre-break
            for lam_o in lambda_o_grid:
                w = P.mechanism_weights("D", {**cfg["plasticity"], "lambda_O": float(lam_o)})
                Nn = P.network_state(P.neural_state(d_values, w, sim.Z), sim.W)
                for si, s in enumerate(scen):
                    comp = comp_of[si]
                    if comp is None or comp == si:
                        continue
                    cs, sl = slice(comp * n, (comp + 1) * n), slice(si * n, (si + 1) * n)
                    for ni, net in enumerate(sim.networks):
                        sm = _summary(Nn[sl, ni] - Nn[cs, ni])
                        neural_diagram.append({"draw_id": draw_id, "scenario": s.name, "year": y1, "half_life_weeks": hl,
                                               "lambda_O": float(lam_o), "network": net, "mean": sm["estimate"], "sd": sm["sd"],
                                               "d": sm["estimate"] / sm["sd"] if sm["sd"] > 0 else 0.0, "prsup": sm["prsup"]})
        if keep_acc and values is not None and (y1 in checkpoint_years or t + 1 == T):
            acc_sub[y1] = values[sub_rows].astype(np.float32)
        if keep_yearly:
            frame = {"draw_id": draw_id, "scenario": np.repeat(names, sub), "learner_id": np.tile(np.arange(sub), S),
                     "year": y1, "stratum": pop.stratum[sub_rows]}
            frame.update({k: end[k][sub_rows].astype(np.float32) for k in STATES})
            frame.update({"K_after_break": pop.K[sub_rows].astype(np.float32),
                          "M_after_break": pop.M[sub_rows].astype(np.float32),
                          **{k: ex[k][sub_rows].astype(np.float32) for k in ("unaided", "far", "p_request")},
                          "retention": retention[sub_rows].astype(np.float32),
                          "help_rate": (tally["help"][sub_rows] / eps).astype(np.float32)})
            for m, Nn in nets.items():
                for ni, net in enumerate(sim.networks):
                    frame[f"N_{m}_{net}"] = Nn[sub_rows, ni].astype(np.float32)
            yearly.append(pd.DataFrame(frame))
        tally = new_tally()

    return {"draw_id": draw_id, "scenarios": names, "n": n,
            "parameter_draws": pd.DataFrame([{"draw_id": draw_id, **drawn}]),
            "simulation_draws": pd.concat(levels + [pd.DataFrame(contrasts)], ignore_index=True),
            "neural_contrasts": pd.DataFrame(neural),
            "yearly_subsample": pd.concat(yearly, ignore_index=True) if yearly else None,
            "weekly_means": pd.concat(weekly, ignore_index=True) if weekly else None,
            "episodes_central": pd.concat(episodes, ignore_index=True) if episodes else None,
            "neural_diagram": pd.DataFrame(neural_diagram) if neural_diagram else None,
            "hist": hist, "mean_acc": mean_acc, "acc_sub": acc_sub, "final": final}


# ------------------------------------------------------------------ outputs: append-only parts + run.json
TABLES = ("simulation_draws", "parameter_draws", "neural_contrasts", "yearly_subsample", "weekly_means", "episodes_central",
          "neural_diagram")


def flush(out_dir: Path, chunk: list[dict], meta: dict) -> None:
    """Append one part per table for the draws in `chunk`, then record them in run.json. run.json is replaced
    last, so a crash leaves at most an orphan part that no reader lists and the next flush overwrites."""
    name = f"part-{len(meta['parts']):05d}"
    for table in TABLES:
        frames = [r[table] for r in chunk if r.get(table) is not None and len(r[table])]
        if frames:
            (out_dir / table).mkdir(parents=True, exist_ok=True)
            pd.concat(frames, ignore_index=True).to_parquet(out_dir / table / f"{name}.parquet", index=False)
    hist: dict = {}
    for r in chunk:
        for key, c in r["hist"].items():
            hist[key] = hist.get(key, 0) + c
    if hist:
        (out_dir / "contrast_hist").mkdir(parents=True, exist_ok=True)
        pd.DataFrame([{"scenario": s, "year": y, "outcome": o, "bin": i, "bin_low": HIST_BINS[i],
                       "bin_high": HIST_BINS[i + 1], "count": int(c[i])}
                      for (s, y, o), c in hist.items() for i in range(len(c))]
                     ).to_parquet(out_dir / "contrast_hist" / f"{name}.parquet", index=False)
    macc = [m for r in chunk for m in r["mean_acc"]]
    if macc:
        (out_dir / "mean_accumulator_diff").mkdir(parents=True, exist_ok=True)
        np.savez_compressed(out_dir / "mean_accumulator_diff" / f"{name}.npz",
                            draw_id=np.array([m["draw_id"] for m in macc]), scenario=np.array([m["scenario"] for m in macc]),
                            year=np.array([m["year"] for m in macc]), diff=np.stack([m["diff"] for m in macc]))
    subs = [(r["draw_id"], y, a) for r in chunk for y, a in sorted(r["acc_sub"].items())]
    if subs:
        (out_dir / "accumulators_subsample").mkdir(parents=True, exist_ok=True)
        np.savez_compressed(out_dir / "accumulators_subsample" / f"{name}.npz", draw_id=np.array([s[0] for s in subs]),
                            year=np.array([s[1] for s in subs]), values=np.stack([s[2] for s in subs]))
    meta["parts"].append(name)
    meta["draws_done"] = sorted(set(meta["draws_done"]) | {r["draw_id"] for r in chunk})
    tmp = out_dir / "run.json.tmp"
    tmp.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    tmp.replace(out_dir / "run.json")


def read_table(out_dir: Path, table: str, with_params: bool = False) -> pd.DataFrame:
    """One table of a Phase V run over the parts run.json lists. `contrast_hist` is summed over parts;
    `with_params` joins the drawn parameter values onto every row (the brief §4.2 `simulation_draws` layout)."""
    out_dir = Path(out_dir)
    meta = json.loads((out_dir / "run.json").read_text(encoding="utf-8"))
    paths = [out_dir / table / f"{p}.parquet" for p in meta["parts"]]
    frames = [pd.read_parquet(p) for p in paths if p.exists()]
    if not frames:
        return pd.DataFrame()
    df = pd.concat(frames, ignore_index=True)
    if table == "contrast_hist":
        df = df.groupby(["scenario", "year", "outcome", "bin", "bin_low", "bin_high"], as_index=False)["count"].sum()
    if with_params:
        df = df.merge(read_table(out_dir, "parameter_draws"), on="draw_id", how="left")
    return df


def read_arrays(out_dir: Path, name: str) -> dict:
    """`mean_accumulator_diff` or `accumulators_subsample` over the listed parts, concatenated along axis 0."""
    out_dir = Path(out_dir)
    meta = json.loads((out_dir / "run.json").read_text(encoding="utf-8"))
    parts = [np.load(out_dir / name / f"{p}.npz") for p in meta["parts"] if (out_dir / name / f"{p}.npz").exists()]
    return {k: np.concatenate([p[k] for p in parts]) for k in parts[0].files} if parts else {}


# ------------------------------------------------------------------ CLI
def config_from_args(args) -> tuple[dict, dict]:
    """The raw (unresolved) config with `--set key=value` overrides applied, and the run options for run.json."""
    raw = yaml.safe_load(Path(args.config).resolve().read_text(encoding="utf-8"))
    for item in args.set or []:
        key, value = item.split("=", 1)
        node = raw
        parts = key.split(".")
        for part in parts[:-1]:
            node = node[part]
        node[parts[-1]] = yaml.safe_load(value)
    return raw, {"epw": args.epw, "form": args.form, "distribution": args.distribution, "break_scale": args.break_scale,
                 "scenarios": args.scenarios, "zero_plasticity": args.zero_plasticity, "zero_effort": args.zero_effort,
                 "seed_offset": args.seed_offset, "set": args.set or [], "subsample": args.subsample,
                 "frontier": args.frontier, "mediate": args.mediate, "no_neural": args.no_neural}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", default="config/default.yaml")
    ap.add_argument("--tag", required=True)
    ap.add_argument("--years", type=int)
    ap.add_argument("--draws", type=int)
    ap.add_argument("--learners", type=int)
    ap.add_argument("--epw", type=int, choices=(1, 3, 5), help="episodes per week (§9.1 exposure)")
    ap.add_argument("--form", choices=("bounded", "brief"), help="state-update form (PLAN.md D3)")
    ap.add_argument("--distribution", choices=("triangular", "uniform"), help="parameter draws (A1; F4 uses uniform)")
    ap.add_argument("--break-scale", type=float, dest="break_scale", help="break forgetting as a share of the term rate")
    ap.add_argument("--scenarios", nargs="+")
    ap.add_argument("--zero-plasticity", action="store_true", dest="zero_plasticity")
    ap.add_argument("--zero-effort", action="store_true", dest="zero_effort")
    ap.add_argument("--seed-offset", type=int, default=0, dest="seed_offset", help="replicate runs (§10.5): master + offset")
    ap.add_argument("--set", nargs="*", metavar="key=value", help="override raw config leaves, e.g. calendar.break_weeks=4")
    ap.add_argument("--subsample", type=int, help="learners per scenario kept per learner-year (first draws only)")
    ap.add_argument("--frontier", choices=("grid", "lines", "neural"), help="the §9.6-9.7 designs (replace the scenarios)")
    ap.add_argument("--mediate", help="comma list of mediators held at the comparator (§11.5), e.g. E,F,D")
    ap.add_argument("--no-neural", action="store_true", dest="no_neural", help="skip the plasticity accumulators")
    ap.add_argument("--flush-every", type=int, default=10, dest="flush_every", help="draws per written part")
    ap.add_argument("--resume", action="store_true")
    args = ap.parse_args(argv)
    root = Path(args.config).resolve().parent.parent
    raw, opts = config_from_args(args)
    p5 = raw["phase5"]
    years = args.years or int(p5["years"])
    n_draws = args.draws if args.draws is not None else int(p5["draws"])
    n = args.learners or int(p5["learners_per_draw"])
    subsample = args.subsample or int(p5["subsample_learners"])
    subsample_draws = int(p5.get("subsample_draws", 20))
    distribution = args.distribution or p5["distribution"]
    master = int(raw["seeds"]["master"]) + int(args.seed_offset)
    out_dir = root / raw["run"]["processed_dir"] / "phase5" / args.tag
    design = {"years": years, "draws": n_draws, "learners_per_draw": n, "master_seed": master, "options": opts,
              "config_sha256": hashlib.sha256(json.dumps(raw, sort_keys=True).encode()).hexdigest()}
    if (out_dir / "run.json").exists():
        before = json.loads((out_dir / "run.json").read_text(encoding="utf-8"))
        if not args.resume:
            print(f"{out_dir} exists. Pass --resume to continue it or choose another --tag (brief §4.3).", file=sys.stderr)
            return 2
        for key, now in design.items():
            if before.get(key) != now:
                print(f"refusing to resume {args.tag}: {key} was {before.get(key)!r}, now {now!r}", file=sys.stderr)
                return 2
        meta = before
    else:
        out_dir.mkdir(parents=True, exist_ok=True)
        meta = {**design, "version": __version__, "subsample_learners": subsample, "subsample_draws": subsample_draws,
                "python": platform.python_version(), "platform": platform.platform(),
                "packages": {"numpy": np.__version__, "pandas": pd.__version__}, "parts": [], "draws_done": [],
                "wall_time_s": 0.0}
    units = corpus.load_units(root / raw["run"]["units_dir"])
    cfg0, _ = draw_parameters(raw, -1, master)
    extra, knobs = {}, {}
    if args.frontier:
        scen, knobs, extra = frontier_scenarios(args.frontier)
    else:
        scen = scenarios_from_config(p5, args.scenarios)
    if args.mediate:
        scen, held = mediation_scenarios(scen, [m.strip() for m in args.mediate.split(",")], p5["comparator"])
        knobs.update(held)
    sim = Sim.build(cfg0, units, scen, root, args.zero_plasticity, args.zero_effort, args.form, args.epw,
                    neural=not args.no_neural)
    meta.update(scenarios=[s.name for s in scen], networks=sim.networks, neural=sim.Z is not None, scenario_knobs=knobs)
    draw_ids = ([-1] if p5.get("central_draw", True) else []) + list(range(n_draws))
    todo = [b for b in draw_ids if b not in set(meta["draws_done"])]
    print(f"{args.tag}: {len(todo)} draws to run x {len(scen)} scenarios x {n} learners x {years} years")
    started, chunk = time.time(), []
    for i, b in enumerate(todo):
        cfg, drawn = draw_parameters(raw, b, master, distribution)
        sim.set_draw(cfg, b)
        keep = b < subsample_draws
        chunk.append(run_draw(sim, b, cfg, n, years, master, drawn, subsample=subsample, keep_yearly=keep,
                              keep_acc=keep, keep_episodes=(b == -1), break_scale=args.break_scale, **extra))
        elapsed = time.time() - started
        if len(chunk) >= args.flush_every or i + 1 == len(todo):
            meta["wall_time_s"] = round(meta.get("wall_time_s", 0.0) + elapsed, 1)
            started = time.time()
            flush(out_dir, chunk, meta)
            chunk = []
        print(f"draw {b} done ({i + 1}/{len(todo)}, ~{elapsed / max(1, (i % args.flush_every) + 1) * (len(todo) - i - 1) / 60:.0f} min left)")
    print(f"{args.tag}: {len(meta['draws_done'])} draws in {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Synthetic learner population and state dynamics (brief §7.1-7.2, §7.4-7.6; eq. 15-16 and 19-25).

The state vector is [K, M, R, C, D] in [0, 1]: knowledge, memory strength, independent reasoning,
calibration and dependence. Every parameter is an assumption read from config/default.yaml.
Arithmetic uses numpy so a future vectorised Phase V runner can pass arrays without changes.
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field

import numpy as np

STATE = ("K", "M", "R", "C", "D")
RECENT_N = 5  # how many recent episodes the observable record summarises as "recent form"
APPROACH_NAME = {"traditional": "the hints on your own", "ai_scaffolding": "the AI tutor",
                 "ai_substitution": "the AI's complete solution"}  # how the record names each approach
ARMS = ("low", "medium", "high")


def resolve(node, setting: str):
    """Replace every {low, medium, high} leaf by the selected arm (brief §7.2 sensitivity arms)."""
    if isinstance(node, dict):
        if set(node) == set(ARMS):
            return node[setting]
        return {k: resolve(v, setting) for k, v in node.items()}
    if isinstance(node, list):
        return [resolve(v, setting) for v in node]
    return node


def logistic(x):
    return 1.0 / (1.0 + np.exp(-x))


def clip01(x: float) -> float:
    return float(min(1.0, max(0.0, x)))


@dataclass
class Learner:
    learner_id: int
    stratum: int  # 0 low, 1 medium, 2 high prior knowledge
    K: float
    M: float
    R: float
    C: float
    D: float
    alpha: float  # knowledge acquisition rate, eq. 16
    delta: float  # forgetting rate, eq. 16
    confidence_bias: float
    speed: float  # latency multiplier
    brier_sum: float = 0.0
    brier_n: int = 0
    rating_sum: int = 0  # confidence ratings (1-5) reported so far, for the observable record
    rating_n: int = 0
    streak: int = 0  # consecutive episodes solved on the first attempt (drives support fading)
    n_episodes: int = 0
    n_first_try: int = 0
    n_help: int = 0
    prior_problems: int = 0  # the §7.3 prior record: the initial state as observable history
    prior_first_try: int = 0
    prior_help: int = 0
    prior_rating_sum: float = 0.0
    recent: list = field(default_factory=list)  # 1/0 per episode: solved on the first try or not
    concept_record: dict = field(default_factory=dict)  # concept -> [attempts, first-try solves];
    # keyed on the CONCEPT, not the unit, so units that teach the same idea with a different surface
    # form still read as familiar - that is what makes a repeated concept stimulate memory.
    choice_record: dict = field(default_factory=dict)  # free-choice arm: approach -> [times chosen, transfer solved]
    last_seen: dict = field(default_factory=dict)  # unit_id -> episode index last practised
    history: list = field(default_factory=list)  # compact observable renderings of past episodes

    def theta(self, theta_slope: float) -> float:
        return theta_slope * (self.K - 0.5)

    def state(self) -> dict:
        return {k: getattr(self, k) for k in STATE}

    def record_line(self, concept: str | None = None) -> str:
        """Observable record for the response-engine prompt (brief §7.3: history, never latent state).

        Three lines, each a fact the learner could state about their own past: the lifetime totals
        (prior record plus this run, so the counts are monotone and the sampled state reaches the very
        first call), recent form and the current run of first-try solves, and experience on this
        problem type. Nothing here names a latent variable; `find_latent_leaks` guards that.
        """
        problems = self.prior_problems + self.n_episodes
        if not problems:
            return ""
        rating_n = self.prior_problems + self.rating_n
        rating_sum = self.prior_rating_sum + self.rating_sum
        rating = f", average confidence {rating_sum / rating_n:.1f} of 5" if rating_n else ""
        lines = [f"Your record so far: {problems} problems, {self.prior_first_try + self.n_first_try} solved on "
                 f"the first try, {self.prior_help + self.n_help} extra hints requested{rating}."]
        if self.recent:
            line = (f"In your last {len(self.recent)} problems you solved {sum(self.recent)} "
                    f"on the first try.")
            if self.streak >= 2:
                line += f" You have solved the last {self.streak} in a row."
            lines.append(line)
        seen = self.concept_record.get(concept) if concept else None
        if seen and seen[0]:
            lines.append(f"You have met this kind of problem {seen[0]} time{'s' if seen[0] > 1 else ''} before "
                         f"and solved it on the first try {seen[1]} of those times.")
        if self.choice_record:
            # The free-choice bandit history, stated payoff-first. Measured 2026-09-10: the same facts
            # ordered this way make the choice follow the payoff twice as strongly (+0.149 vs +0.068,
            # se 0.018/0.008) and flip sign with it, where a frequency-first phrasing left substitution
            # preferred whatever it had returned. Canonical order, so it does not vary by learner.
            picks = "; ".join(
                f"after {APPROACH_NAME[a]} you answered the follow-up question correctly "
                f"{self.choice_record[a][1]} of {self.choice_record[a][0]} "
                f"time{'s' if self.choice_record[a][0] != 1 else ''} "
                f"({round(100 * self.choice_record[a][1] / self.choice_record[a][0])}%)"
                for a in APPROACH_NAME if a in self.choice_record)
            lines.append(f"Looking back at what worked: {picks}.")
        return "\n".join(lines)

    def note_episode(self, concept: str, first_correct: bool, chosen: str | None = None,
                     transfer_correct: bool = False) -> None:
        """Advance the observable counters after an episode (called by run_episode). `chosen` is the
        approach the learner picked in the free-choice arm, credited with the transfer outcome."""
        if chosen:
            rec = self.choice_record.setdefault(chosen, [0, 0])
            rec[0] += 1
            rec[1] += int(transfer_correct)
        self.n_episodes += 1
        self.n_first_try += int(first_correct)
        self.streak = self.streak + 1 if first_correct else 0
        self.recent.append(int(first_correct))
        del self.recent[:-RECENT_N]
        rec = self.concept_record.setdefault(concept, [0, 0])
        rec[0] += 1
        rec[1] += int(first_correct)

    def snapshot(self) -> dict:
        return asdict(self)

    @classmethod
    def restore(cls, d: dict) -> "Learner":
        return cls(**d)


def make_population(pcfg: dict, n: int, seed: int) -> list[Learner]:
    """Eq. 15-16: three prior-knowledge strata, a truncated multivariate normal state vector, and
    per-learner learning / forgetting parameters. Deterministic given the seed."""
    rng = np.random.default_rng([seed, 1])
    means = np.array([pcfg["state_means"][k] for k in STATE], dtype=float)
    cov = np.array(pcfg["correlation"], dtype=float) * float(pcfg["state_sd"]) ** 2
    strata = rng.choice(3, size=n, p=pcfg["stratum_weights"])
    learners = []
    for i in range(n):
        mu = means.copy()
        mu[0] += pcfg["stratum_k_shift"][strata[i]]
        mu[1] += pcfg["stratum_m_shift"][strata[i]]
        while True:  # truncation to [0, 1] by rejection
            s = rng.multivariate_normal(mu, cov)
            if np.all((s >= 0.0) & (s <= 1.0)):
                break
        learners.append(Learner(
            learner_id=i, stratum=int(strata[i]), K=float(s[0]), M=float(s[1]), R=float(s[2]), C=float(s[3]),
            D=float(s[4]), alpha=float(rng.lognormal(pcfg["mu_alpha"], pcfg["sigma_alpha"])),
            delta=float(rng.beta(pcfg["a_delta"], pcfg["b_delta"])),
            confidence_bias=float(rng.normal(0.0, pcfg["confidence_bias_sd"])),
            speed=float(rng.lognormal(0.0, pcfg["speed_sigma"])),
        ))
    return learners


PRIOR_B_U = 0.0  # the eq. 17 difficulty of an average (score 3) unit, the reference for the prior record


def seed_prior_records(learners: list, cfg: dict) -> None:
    """Brief §7.3: translate the sampled initial state into observable history instead of revealing it.

    Each learner is given the record of a prior session whose counts are what eq. 17 and the help-request
    model imply for that state, so two learners drawn differently send different prompts from the first
    call. Deterministic given the state, and it names no latent variable (`find_latent_leaks` guards it).
    The same prior also seeds the running Brier score, so eq. 24 continues from the drawn C rather than
    restarting from an empty history after episode 1.
    """
    p, r = cfg["population"], cfg["response"]
    n = int(p["prior_problems"])
    for learner in learners:
        theta = learner.theta(p["theta_slope"])
        p_correct = float(logistic(theta - PRIOR_B_U + r["rho"] * learner.R + r["kappa"] * learner.M))
        p_help = float(logistic(r["request_intercept"] + r["request_dependence_slope"] * learner.D
                                - r["request_ability_slope"] * (theta - PRIOR_B_U)))
        learner.prior_problems = n
        learner.prior_first_try = int(round(n * p_correct))
        learner.prior_help = int(round(n * p_help))
        learner.prior_rating_sum = n * (1.0 + 4.0 * clip01(p_correct + learner.confidence_bias))
        solved = int(round(RECENT_N * p_correct))  # recent form implied by the same eq. 17 probability
        learner.recent = [1] * solved + [0] * (RECENT_N - solved)
        learner.brier_n = n
        learner.brier_sum = n * (1.0 - learner.C)


def b_u(difficulty: int, ccfg: dict) -> float:
    """Unit difficulty on the logit scale of eq. 17-18 (assumption: linear in the 1-5 score)."""
    return float(ccfg["b_slope"]) * (difficulty - 3)


@dataclass
class Proxies:
    """Observable inputs of eq. 19-25, all derived from the interaction (brief §7.4)."""
    attempt: float
    retrieval: float
    explanation: float
    answer_provided: float
    offloading: float
    correct_after_error: float
    transfer_success: float
    support_used: float
    support_faded: float
    independent_success: float
    adaptation: float
    mismatch: float
    coverage: float
    correctness: float


def _scalar_or_array(x):
    return float(x) if np.ndim(x) == 0 else x


def effort(p: Proxies, c: dict):
    """Eq. 19 (a float for one learner; arrays pass through, for the vectorised Phase V step)."""
    return _scalar_or_array(logistic(c["a0"] + c["a1"] * p.attempt + c["a2"] * p.retrieval + c["a3"] * p.explanation
                                     - c["a4"] * p.answer_provided))


def effectiveness(p: Proxies, c: dict):
    """Eq. 20."""
    return _scalar_or_array(logistic(c["f0"] + c["f1"] * p.correctness + c["f2"] * p.coverage + c["f3"] * p.adaptation
                                     - c["f4"] * p.mismatch))


def step_state(K, M, R, D, alpha, delta, p: Proxies, E, F, c: dict, form: str = "brief",
               delta_scale: float = 1.0) -> dict:
    """Eq. 21-23 and 25 for one learner (floats) or a population (numpy arrays), unclipped so the caller
    can count clips. `brief` is the equations as written (every Phase III run). `bounded` is the Phase V
    variant (PLAN.md D3): each gain is scaled by the distance to 1 and each loss by the distance to 0, and D
    falls after any unaided success rather than only under a faded policy, because an unaided success
    means no support was used. `delta_scale` rescales forgetting to the calendar exposure (A16)."""
    d = delta * delta_scale
    K1 = K + alpha * E * F * (1.0 - K) - d * K
    if form == "brief":
        M1 = (1.0 - c["m_decay_scale"] * d) * M + c["eta_M"] * p.retrieval + c["eta_C"] * p.correct_after_error
        R1 = R + c["eta_R"] * E * p.transfer_success - c["eta_O"] * p.offloading
        D1 = D + c["eta_D"] * p.support_used - c["eta_F"] * p.support_faded * p.independent_success
    elif form == "bounded":
        M1 = M + (c["eta_M"] * p.retrieval + c["eta_C"] * p.correct_after_error) * (1.0 - M) - c["m_decay_scale"] * d * M
        R1 = R + c["eta_R"] * E * p.transfer_success * (1.0 - R) - c["eta_O"] * p.offloading * R
        D1 = D + c["eta_D"] * p.support_used * (1.0 - D) - c["eta_F"] * p.independent_success * D
    else:
        raise ValueError(f"unknown update form {form!r}: use 'brief' or 'bounded'")
    return {"K": K1, "M": M1, "R": R1, "D": D1}


def calendar_delta_scale(cal: dict) -> float:
    """delta_i (eq. 16) is per episode at `reference_episodes_per_week`; at another exposure each episode
    carries reference / episodes_per_week of it, so forgetting per calendar week is unchanged (D4, A16)."""
    return float(cal["reference_episodes_per_week"]) / float(cal["episodes_per_week"])


def apply_break(K, M, delta, cal: dict, c: dict):
    """Between school years (D4): `break_weeks` without practice at `break_decay_scale` of the term rate.
    K and M compound their per-episode decay over reference_episodes_per_week x break_weeks x scale
    episode-equivalents ((1 - delta)^9 at the defaults); R, C and D do not decay. Floats or arrays."""
    n = float(cal["reference_episodes_per_week"]) * float(cal["break_weeks"]) * float(cal["break_decay_scale"])
    return K * (1.0 - delta) ** n, M * (1.0 - c["m_decay_scale"] * delta) ** n


def update(learner: Learner, p: Proxies, E: float, F: float, forecasts, c: dict) -> dict:
    """Eq. 21-25 applied in place. `forecasts` = [(confidence, correct)] for the unaided responses of
    the episode; C is one minus the running Brier score (brief §7.6). Returns which components clipped."""
    raw = step_state(learner.K, learner.M, learner.R, learner.D, learner.alpha, learner.delta, p, E, F, c,
                     c.get("form", "brief"))
    for confidence, correct in forecasts:
        learner.brier_sum += (confidence - correct) ** 2
        learner.brier_n += 1
    if learner.brier_n:
        raw["C"] = 1.0 - learner.brier_sum / learner.brier_n
    clipped = {}
    for k, v in raw.items():
        setattr(learner, k, clip01(v))
        clipped[k] = int(v < 0.0 or v > 1.0)
    return clipped


def help_cap(learner: Learner, s: dict) -> int:
    """Help turns available this episode under the support-persistence policy (brief §3.4, §9.2)."""
    policy, m = s["persistence_policy"], int(s["max_hints"])
    if policy == "persistent":
        return m
    if policy == "immediate_withdrawal":
        return 0 if learner.streak >= int(s["withdrawal_success_threshold"]) else m
    if policy == "gradual_fading":
        return int(math.ceil(m * float(s["fade_base"]) ** learner.streak))
    raise ValueError(f"unknown persistence policy {policy!r}")


def latency(learner: Learner, hint_depth: int, attempted: bool, l: dict) -> float:
    """Bookkeeping proxy in seconds (brief §4.2), not a reaction-time prediction."""
    return float(learner.speed * (l["base_s"] + l["per_hint_s"] * hint_depth + l["per_attempt_s"] * attempted))


def brier(forecasts) -> float:
    """Eq. 27 over (confidence, correct) pairs."""
    return float(np.mean([(c - y) ** 2 for c, y in forecasts])) if forecasts else float("nan")


def ece(forecasts, bins: int = 10) -> float:
    """Expected calibration error with equal-width bins (brief §7.7)."""
    if not forecasts:
        return float("nan")
    conf = np.array([c for c, _ in forecasts], dtype=float)
    y = np.array([y for _, y in forecasts], dtype=float)
    idx = np.minimum((conf * bins).astype(int), bins - 1)
    total = 0.0
    for b in range(bins):
        m = idx == b
        if m.any():
            total += m.mean() * abs(y[m].mean() - conf[m].mean())
    return float(total)

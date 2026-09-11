"""One instructional episode for one learner (brief §3.1): problem -> first response -> intervention ->
further responses -> near-transfer question -> effort, effectiveness and state update (eq. 19-25).

Protocol (user decision: no help before a first attempt):
  first turn       answer options only; correct -> straight to the transfer question
  traditional      wrong -> hint k shown (k = 1..cap), then answers [+ "next hint" while k < cap];
                   still wrong after hint 3 -> the worked solution is shown (answer provided)
  ai_scaffolding   wrong -> LLM tutor turn k (diagnosis, one question, level-k hint), then answers
                   [+ "ask the tutor" while k < cap]; still wrong after turn 3 -> the worked solution is
                   shown (answer provided; prewritten, no API call)
  ai_substitution  wrong -> one LLM call with the complete solution, then exactly one re-answer
  transfer         near-transfer question, unaided, one attempt
`cap` is the number of help turns available under the support-persistence policy (3 when persistent).
Far-transfer items are used only by the §7.7 checkpoints (simulate.py).
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np

from .corpus import Problem, Stimulus, Unit
from .engines import APPROACH_QUESTION, APPROACH_TEXT, CONFIDENCE_QUESTION, LETTERS, Engine, Option, Trial, render_options
from .learners import Learner, Proxies, b_u, effectiveness, effort, help_cap, latency, update

HELP_TEXT = {"traditional": "Ask for the next hint", "ai_scaffolding": "Ask the tutor for more help"}
FREE = "free_choice"  # the fourth arm: the learner reads the question, then picks one of the three protocols


@dataclass
class Turn:
    stage: str
    turn: int
    layout: str  # "W:correct|Q:misconception|Z:distractor|H:help"
    key: str
    kind: str
    value: float | None
    p_correct: float
    confidence: float | None
    correct: int | None  # None for a help request
    requested_support: int
    explanation: str | None  # method behind the chosen option (brief §7.3)
    hint_depth: int
    support_h: float
    latency: float
    prompt_sha256: str | None = None
    prompt_tokens: int | None = None
    seconds: float | None = None


@dataclass
class EpisodeRecord:
    condition: str  # the arm: traditional | ai_scaffolding | ai_substitution | free_choice
    protocol: str  # the protocol actually run; equals `condition` except in the free-choice arm
    learner_id: int
    episode: int
    unit_id: str
    episode_id: str
    turns: list
    tutor_turns: list
    first_correct: int
    resolved: int
    transfer_correct: int
    answer_provided: int
    hint_depth: int
    help_requests: int
    attempts: int  # independent attempts before any answer was provided
    help_cap: int
    proxies: dict
    effort: float
    effectiveness: float
    pe: float  # |Y - P(correct)| on the first response, eq. 30 input
    resolution: int  # error resolved by the learner's own later attempt (no reveal), eq. 31 input
    state_after: dict
    clipped: dict
    learner_after: dict


def build_options(problem: Problem, rng: np.random.Generator, help_text: str | None) -> tuple[list[Option], Option | None]:
    """Random letters and random order per episode: Minitaur favours the first slot, so position must
    carry no information about content."""
    letters = [str(x) for x in rng.choice(list(LETTERS), size=4, replace=False)]
    values = [("correct", problem.answer, problem.method), ("misconception", *problem.distractors[0][:2]),
              ("distractor", *problem.distractors[1][:2])]
    options = []
    for i, j in enumerate(int(j) for j in rng.permutation(3)):
        kind, value, method = values[j]
        options.append(Option(letters[i], kind, problem.render(value), value, method))
    return options, (Option(letters[3], "help", help_text) if help_text else None)


def layout_of(options) -> str:
    return "|".join(f"{o.key}:{o.kind}" for o in options)


def compact(lines: list[str]) -> str:
    """Past-episode rendering for the prompt history: outcomes stay, long texts go."""
    out = []
    for line in lines:
        if line.startswith("Lesson:"):
            continue
        if line.startswith("Tutor:"):
            line = "The tutor sent you a message."
        elif line.startswith("Solution:"):
            line = "The solution was shown to you."
        elif line.startswith("Hint "):
            line = line.split(":", 1)[0] + " was shown."
        out.append(line)
    return "\n".join(out)


def run_episode(learner: Learner, unit: Unit, stimuli: dict[str, Stimulus], condition: str, episode: int,
                engine: Engine, tutor, cfg: dict, rng: np.random.Generator) -> EpisodeRecord:
    """`stimuli` maps each stimulus condition to its file for this unit; the free-choice arm shows the
    lesson of whichever protocol the learner picks, so it needs all three."""
    s, max_hints = cfg["support"], int(cfg["support"]["max_hints"])
    cap = help_cap(learner, s)
    difficulty = b_u(unit.difficulty, cfg["curriculum"])
    theta = learner.theta(cfg["population"]["theta_slope"])
    lines = [f"Problem {learner.n_episodes + 1}."]
    turns: list[Turn] = []
    tutor_turns: list[dict] = []
    for_tutor: list[str] = []
    counters = {"answers": 0, "hint_depth": 0}

    def decide(stage, options, allow_help, support_h, with_confidence, bu):
        trial = Trial(stage, list(lines), options, allow_help, bu, support_h,
                      learner.record_line(unit.concept), list(learner.history))
        d = engine.choose(trial, learner, rng)
        lines.append(f"Options: {render_options(options)}")
        lines.append(f"You press <<{d.key}>>.")
        if with_confidence:  # the rating is a second key press, written back so later calls can see it (§7.3)
            d.confidence = engine.confidence(trial, d, learner, rng)
            lines.append(f"{CONFIDENCE_QUESTION} You press <<{d.rating}>>.")
            learner.rating_sum += int(d.rating)
            learner.rating_n += 1
        approach = stage == "approach"
        correct = None if d.kind == "help" or approach else int(d.kind == "correct")
        if correct is not None:
            lines.append("That was correct." if correct else "That was incorrect.")
        m, depth = d.meta, counters["hint_depth"]
        turns.append(Turn(stage, len(turns) + 1, layout_of(options), d.key, d.kind, d.value, d.p_correct, d.confidence,
                          correct, int(correct is None and not approach),
                          f"approach: {d.kind}" if approach else d.explanation, depth, support_h,
                          latency(learner, depth, correct is not None, s["latency"]), m.get("prompt_sha256"),
                          m.get("prompt_tokens"), m.get("seconds")))
        if approach:
            pass
        elif correct is None:
            for_tutor.append("The learner asked for more help.")
        else:
            counters["answers"] += 1
            chosen = next(o.text for o in options if o.key == d.key)
            for_tutor.append(f"Attempt {counters['answers']}: the learner answered {chosen} "
                             f"({'correct' if correct else 'incorrect'}).")
        return d

    if condition == FREE:  # read the question, choose how to work, then get that protocol's lesson
        lines.append(f"Question: {unit.problem.text}")
        keys = [str(x) for x in rng.choice(list(LETTERS), size=3, replace=False)]
        approaches = [Option(keys[i], c, APPROACH_TEXT[c])
                      for i, c in enumerate(str(x) for x in rng.permutation(list(APPROACH_TEXT)))]
        lines.append(APPROACH_QUESTION)
        protocol = decide("approach", approaches, False, 0.0, False, difficulty).kind
        lines.append(f"Lesson: {stimuli[protocol].explanation}")
    else:
        protocol = condition
        lines += [f"Lesson: {stimuli[protocol].explanation}", f"Question: {unit.problem.text}"]
    answers, help_opt = build_options(unit.problem, rng, HELP_TEXT.get(protocol))

    first = decide("first", answers, False, 0.0, True, difficulty)
    first_correct = first.kind == "correct"
    resolved, help_requests, answer_provided, attempts = first_correct, 0, False, None

    if not resolved and cap > 0:
        if protocol == "ai_substitution":
            tt = tutor.substitute(unit, for_tutor)
            tutor_turns.append({"level": 1, **asdict(tt)})
            lines.append(f"Tutor: {tt.text}")
            for_tutor.append(f"Tutor: {tt.text}")
            counters["hint_depth"], answer_provided, attempts = max_hints, True, counters["answers"]
            resolved = decide("supported", answers, False, 1.0, False, difficulty).kind == "correct"
        else:
            while not resolved and counters["hint_depth"] < cap:
                counters["hint_depth"] += 1
                k = counters["hint_depth"]
                if protocol == "traditional":
                    text = unit.hints[k - 1]
                    lines.append(f"Hint {k}: {text}")
                else:
                    tt = tutor.scaffold(unit, for_tutor, k)
                    tutor_turns.append({"level": k, **asdict(tt)})
                    text = tt.text
                    lines.append(f"Tutor: {text}")
                for_tutor.append(f"Tutor turn {k}: {text}")
                allow = k < cap
                d = decide("supported", answers + [help_opt] if allow else answers, allow, k / max_hints, False, difficulty)
                if d.kind == "help":
                    help_requests += 1
                    continue
                resolved = d.kind == "correct"
            if not resolved and counters["hint_depth"] >= max_hints:
                lines.append(f"Solution: {unit.worked_solution}")
                answer_provided, attempts = True, counters["answers"]
    if attempts is None:
        attempts = counters["answers"]
    hint_depth = counters["hint_depth"]

    transfer_options, _ = build_options(unit.near_transfer, rng, None)
    lines.append(f"Transfer question: {unit.near_transfer.text}")
    transfer = decide("transfer", transfer_options, False, 0.0, True, difficulty + cfg["curriculum"]["near_b_delta"])
    transfer_correct = transfer.kind == "correct"

    explanation = 0.0 if answer_provided else 1.0 - hint_depth / max_hints
    p = Proxies(
        attempt=attempts / (max_hints + 1), retrieval=1.0 if first_correct else 0.5, explanation=explanation,
        answer_provided=float(answer_provided), offloading=1.0 - explanation,
        correct_after_error=float((not first_correct) and resolved and not answer_provided),
        transfer_success=float(transfer_correct), support_used=1.0 if answer_provided else hint_depth / max_hints,
        support_faded=1.0 - cap / max_hints, independent_success=float(first_correct),
        adaptation=float(s["adaptation"][protocol]) if hint_depth > 0 else 0.0,
        mismatch=min(1.0, abs(difficulty - theta) / s["mismatch_scale"]),
        coverage=cfg["effectiveness"]["coverage_default"], correctness=cfg["effectiveness"]["correctness_default"],
    )
    E, F = effort(p, cfg["effort"]), effectiveness(p, cfg["effectiveness"])
    clipped = update(learner, p, E, F, [(first.confidence, float(first_correct)),
                                        (transfer.confidence, float(transfer_correct))], cfg["updates"])
    minutes = max(1, round(sum(t.latency for t in turns) / 60.0))
    lines.append(f"That took you about {minutes} minute{'s' if minutes != 1 else ''}.")
    learner.note_episode(unit.concept, first_correct, protocol if condition == FREE else None, transfer_correct)
    learner.n_help += help_requests
    learner.last_seen[unit.unit_id] = episode
    learner.history.append(compact(lines))
    del learner.history[:-int(cfg["engine"].get("history_window", 3))]

    return EpisodeRecord(
        condition, protocol, learner.learner_id, episode, unit.unit_id, f"ep{episode:04d}|{unit.unit_id}", [asdict(t) for t in turns],
        tutor_turns, int(first_correct), int(resolved), int(transfer_correct), int(answer_provided), hint_depth,
        help_requests, attempts, cap, asdict(p), E, F, abs(float(first_correct) - first.p_correct),
        int(p.correct_after_error), learner.state(), clipped, learner.snapshot(),
    )

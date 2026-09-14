# CLAUDE.md

Context for AI assistants working on this repository. Nested `CLAUDE.md` files cover each folder.

## What this is

NeuroTutorSim (ESADE MSc Business Analytics): a purely computational study comparing traditional
instruction, AI scaffolding and AI substitution. Spec: `NeuroTutorSim_Project_Brief.pdf`. This repo
implements the Phase I corpus skeleton and Phase III (synthetic learners) and nothing else, on purpose.

## Scope decisions (do not re-litigate)

- **Corpus: 30 units on MBA topics**, not the brief's 120 in two domains. Built as **15 concepts x 2
  units**, so every concept recurs once with a different surface form and the learner's concept-level
  experience line fires on the second encounter (user decision 2026-09-11, replacing the earlier target
  of 40). `python -m neurotutorsim.corpus` validates all 30 and their 90 stimuli.
- **TRIBE (Phase II) runs in `notebooks/tribe_phase2.ipynb` on Google Colab** (user request 2026-09-14,
  replacing the earlier "teammate's deliverable" split). The simulation code still never computes, reads or
  fakes a cortical prediction: `tribe.py` is model-free arithmetic on cached predictions, and the notebook's
  `DRY_RUN` smoke test is quarantined under `DRYRUN_<tag>`. The stimuli texts (file body, all sections) are the
  TRIBE inputs; the join key is `(unit_id, condition)`. See `notebooks/CLAUDE.md` for the decisions.
- **Phases IV and V are not built.** `learner_state.parquet` already carries what they need per episode:
  `effort` (E), `pe`, `retrieval`, `offloading`, `resolution`, `unit_id`, `condition`. The support-
  persistence policy and the low/medium/high parameter arms are the §9.2-9.3 scenario knobs. Phase V
  curriculum resampling is a TODO in `simulate.py`.
- **One learner, four arms.** The population is drawn once and every learner runs the three assigned
  conditions plus `free_choice` from the same initial state, the same curriculum order and common random
  numbers (`[master, learner_id, episode]`), so the eq. 10-12 contrasts are within-learner. In
  `free_choice` the learner reads the question, picks one of the three protocols (`APPROACH_TEXT`), gets
  that protocol's lesson and runs it; `protocol` beside `condition` in every table records what ran.
  `n_learners: 1667` means 5,001 learner-runs per arm, meeting the ">= 5,000 learners" of §7.1.
- **The sampled state reaches the prompt as history, never as latents** (§7.3): `seed_prior_records`
  turns the initial state into a prior-session record whose counts are what eq. 17 and the help-request
  model imply, and seeds the running Brier so eq. 24 continues from the drawn C. `record_line` then
  reports lifetime totals, recent form with the current first-try streak, and experience on the topic
  at hand (keyed on the **concept**, so units teaching the same idea with a different surface form read as
  familiar), and in `free_choice` what it picked and how the follow-up went; `history_window: 3` past
  episodes follow it.
- **Hybrid engine (default): Centaur chooses, eq. 17-18 answers.** The transcript model gets only
  behaviour - the approach in `free_choice`, help requests, confidence ratings - and the logistic model
  decides correctness, because these models are at chance on the arithmetic (numbers below).
  `--engine centaur|minitaur` alone is the all-transcript engine (§10.2 comparison); `logistic` alone is
  the offline baseline, whose approach rule is a documented softmax in D. Centaur and Minitaur share
  `MinitaurEngine`; the served id comes from `engine.models[...]` and a missing id fails loudly. Never
  silently fall back between engines.
- **Centaur runs locally as a GGUF**: the HF adapter is merged and quantised on Colab, then served by
  LM Studio next to the tutor. The tutor is Qwen2.5-3B-Instruct on the same LM Studio (no API key).
- **The tutor is an LLM** behind any OpenAI-compatible URL (`tutor.base_url`; local servers need no key).
  Its text is numerically inert for correctness (`adaptation` is a per-protocol constant and eq. 17-18
  never read the transcript) but it is what the transcript engine reads when choosing, so `--tutor fake`
  is for tests and pure-logistic runs only.
- **No help before a first attempt** (user decision): help options appear only after a wrong answer.

## Transcript-model facts (measured; they shape `engines.py`)

Centaur and Minitaur are the same kind of model and behave the same way here: next-choice predictors
trained on Psych-101, where the prompt is a transcript and the choice is the token after `<<`. They
cannot explain (asked for free text they invent the next trial), so §7.3's `explanation` is the rule
behind the chosen option, which is known because every option is rule-generated.

Transport: LM Studio `/v1/completions` returns no logprobs; `/v1/chat/completions` with the transcript as
an **assistant** message returns `top_logprobs` and continues it. Option keys are scored there and the
choice is **sampled** with the learner's seeded RNG. Scores are not bitwise reproducible (KV cache), so a
run is reproduced by keeping `outputs/logs/*.jsonl` and `episodes.jsonl`, never by re-deriving. Transient
HTTP 400 "Engine" errors are retried. Mass on the option keys: Centaur ~0.996, Minitaur ~0.99 median.

What they **can** do - use them only for this:

- **Choice tracks history, strongly.** A struggling learner versus a coping one shifts the approach
  choice by -0.187 on traditional, +0.102 on scaffolding, +0.085 on substitution (se 0.012-0.017),
  unanimous across 11 units. This is why `HybridEngine` exists.
- **Choice follows the payoff, if the record is phrased payoff-first** (+0.149 vs +0.068, se 0.018/0.008;
  the phrasing also flips the sign with the payoff). Hence the `Looking back at what worked` wording -
  do not revert it to a frequency-first list.

What they **cannot** do - never route these to them:

- **Arithmetic.** P(correct) 0.35 against a 0.333 chance baseline, band 0.34-0.38 across every prompt
  channel, and blind to the learner's competence (+0.004, se 0.007). Measured on both models.
- **Judge their own answer.** The 1-5 confidence rating tracks the record (+0.866, se 0.022, 11/11) and
  ignores which option was pressed (+0.039, se 0.130, 6/11). So **Brier, ECE and C (eq. 24) measure the
  record, not calibration** - reported as-is with that limitation stated (user decision 2026-09-11).
- **Learn from a single episode.** The aggregate record moves the choice; the last episode's outcome does
  not (+0.009), and naming an approach at all makes it *more* likely regardless of how it went (+0.038).

**Everything in the transcript gets imitated.** Past choices, past confidence ratings, past approaches:
the model repeats what it sees. This one mechanism explains the free-choice ratchet (a substitution habit
self-reinforces +0.119, a traditional one +0.006), the U-shaped confidence scale in runs, and why a long
history *drowns* the record line that carries the payoff (+0.053 alone -> +0.009 with 8 past episodes).
Hence `history_window: 3`; do not raise it.

**Cost.** ~110 s per episode, and concurrency does not help: 1 worker 4.2 calls/min, 2 -> 0.76x, 4 ->
0.53x, 8 -> 0.50x on cold disjoint prompt sets. One-token generations behind ~1000-token prompts are
prompt-processing bound and the GPU is already saturated, so **do not build a parallel runner**. (An
early test showed 2.57x; it reused one prompt set across levels and was measuring the prefix cache.)

**Two-tier run design** (user decision): the full 1667-triplet population runs on `logistic` (~16 min),
and a ~40-learner subsample runs on `hybrid` for the §10.2 comparison. State plainly that in the logistic
run the free-choice arm comes from the documented softmax in D, not from Centaur.

## Episode protocol (brief §3.1, `src/neurotutorsim/episode.py`)

[free_choice only: question -> "How do you want to approach this problem?" -> the chosen protocol's lesson] ->
first answer (3 options) -> traditional: hint k then answers [+ "next hint"], worked solution after hint 3 /
scaffolding: LLM tutor turn k (diagnose, one question, level-k hint, leakage-checked), worked solution
after turn 3 / substitution: one LLM call with the full solution then one re-answer -> unaided
near-transfer question -> "That took you about N minutes." -> eq. 19-25 update. The learner's record carries
lifetime totals, recent form, topic experience and, in `free_choice`, what it picked and how the follow-up went.
Far transfer is used only by the §7.7 checkpoints.

## Where this stands (2026-09-11)

Phase I corpus is complete (30 units, 90 stimuli, all calipers inside 10%). Phase III runs end to end on
both engines. Phase II is built (2026-09-14) but **not yet run**: `notebooks/tribe_phase2.ipynb` passed its
offline dry run and its adapter tests; the first real Colab run (needs `HF_TOKEN` with Llama-3.2 access and
`GITHUB_TOKEN`) has not happened, so no cortical prediction exists on disk. What has NOT been done: that TRIBE
run, the two-tier production run itself, the §7.2 low/high arms, and any §10.2 hybrid-vs-logistic comparison at
a usable N. The pilots on disk (`centaur_free_pilot`,
`centaur_free_pilot2`, 3 learners x 11 episodes each) are shakedown runs, not results; note they predate
the `concept_record` rename and so cannot be `--resume`d.

Budget, measured: **~100-110 s per episode** on the hybrid engine. Covering all 30 units needs >= 30
episodes per learner, so the decided main run is **40 learners x 4 arms x 30 episodes = 4,800 episodes,
about 5.5 days of wall clock** (user decision 2026-09-11: keep all four arms, so the eq. 10-12 contrasts
survive; the free-choice arm alone cannot support them, because there the protocol is chosen by the
learner from their own state and any outcome difference confounds the condition with who selected it).

    uv run python -m neurotutorsim.simulate --learners 40 --episodes 30 --tag centaur_main   # ~5.5 days
    uv run python -m neurotutorsim.simulate --engine logistic --tutor fake --tag population_logistic  # ~16 min

Before starting: both models must be loaded in LM Studio (`lms ps` should list `llama-3.1-centaur-8b` at
8192 context and `qwen2.5-3b-instruct`). LM Studio has unloaded a model mid-run before, which stops the
run; `--resume` with the same tag picks it up. **`--resume` must keep the same `--learners`, `--episodes`,
seed, `--setting`, `--engine` and `--policy`**: `make_population` draws the strata with `rng.choice(size=n)`,
so changing n redraws every learner (learner 0 of a 40-draw is a different person from learner 0 of a
20-draw), and the other three change the physics rather than the population. `simulate.py` refuses such a
resume rather than blending two parameterisations under one tag - you cannot start small and extend.
Nothing in `episodes.jsonl` distinguishes the rows, so **one tag per §7.2 arm** (`--tag population_low`
and so on); the default tag is the engine name and would collide.

## Commands

`uv run pytest` · `uv run python -m neurotutorsim.corpus` · `uv run python -m neurotutorsim.simulate ...`
(see README). Runs are append-only and resumable (`--resume`); never delete logs to "clean up".

## Rules

- Keep it lean: one module per concern, no new dependencies without a reason.
- Prompts to Minitaur contain observable history only (`find_latent_leaks` guards it).
- Brief §15 language: "simulated learner", "model-implied", "scenario contrast"; never causal claims.

# GUIDE: finding your way around NeuroTutorSim

A map from the ideas in the brief to the files that implement them and the outputs that report them.
Read this when you need to answer "where does X live?" or "which number do I cite for Y?".

Other documents, and when to prefer them:

| File | Use it for |
| --- | --- |
| `README.md` | setup, the command for each step, the output map, the Appendix A checklist |
| `PLAN.md` | why things are the way they are: decisions D1-D24, assumptions A1-A19, limitations (§7), the run log (§8) |
| `CLAUDE.md` (root and per folder) | invariants a contributor must not break |
| **this file** | the concepts, and how they connect to code and results |

---

## 1. The idea in one page

The study compares three ways of teaching the same material:

- **traditional** — a fixed explanation, a worked example, three prewritten hints;
- **AI scaffolding** — a tutor that diagnoses the error, asks a question and releases graduated hints, never
  handing over the answer until the learner has tried;
- **AI substitution** — a tutor that gives the full solution immediately.

A fourth arm, **free choice**, lets the simulated learner pick one of the three at every problem.

Two layers are modelled separately, and keeping them separate is the whole methodological point:

1. **Immediate cortical response** (Phase II). TRIBE v2 predicts what an average adult's cortex would do while
   reading each lesson text. This says nothing about learning.
2. **Learning and its accumulation** (Phases III-V). A synthetic learner answers, struggles, asks for help and
   updates knowledge, memory, reasoning, calibration and dependence. A separate plasticity model accumulates the
   immediate responses into a long-run "functional state".

Everything long-run is a **scenario projection under stated assumptions**, never a measured effect. The brief's
§15 wording rules are followed everywhere in the outputs: "predicted cortical response", "simulated learner",
"model-implied", "scenario contrast".

---

## 2. The five phases

| Phase | What it produces | Main file | Lives in |
| --- | --- | --- | --- |
| I. Corpus | 30 units x 3 conditions = 90 lesson texts, plus 210 text controls | `src/neurotutorsim/corpus.py` | `data/units/*.json`, `stimuli/` |
| II. TRIBE | predicted cortical response per stimulus, aggregated to parcels and networks | `notebooks/tribe_phase2.ipynb` + `src/neurotutorsim/tribe.py` | `data/tribe/tribe_main/` |
| III. Learners | episode-by-episode behaviour and state for thousands of simulated learners | `src/neurotutorsim/episode.py`, `learners.py`, `engines.py`, `simulate.py` | `data/processed/<tag>/` |
| IV. Plasticity | model-implied neural state accumulated over episodes | `src/neurotutorsim/plasticity.py` | `data/processed/<tag>/neural_*.parquet` |
| V. Ten years | Monte Carlo scenarios, frontier, tipping points | `src/neurotutorsim/longitudinal.py` | `data/processed/phase5/<tag>/` |
| Analysis | every table and figure | `src/neurotutorsim/analysis.py` (pure functions), `report.py` (CLI) | `outputs/tables/`, `outputs/figures/` |

`analysis.py` holds the statistics and never touches the filesystem; `report.py` does the I/O and the plotting.
When you want to know *how* a number is computed, read `analysis.py`; when you want to know *where it came from*,
read `report.py`.

---

## 3. Phase I: the corpus

**The unit is the source of truth.** `data/units/<unit_id>.json` holds the canonical problem, a near- and a
far-transfer problem, the documented misconception, two distractors with the rule that generates each, three
hints and a worked solution. Nothing is trusted: `python -m neurotutorsim.corpus` recomputes every answer from
its validator and refuses a unit that disagrees.

**30 units, 15 concepts, two units each** (`<concept>_001`, `<concept>_002`). The pair teaches the same method
with a different surface form, which is what makes a concept feel familiar the second time. The brief asked for
120 units in two domains; the reduction is a scope decision, recorded as a limitation.

**The stimulus is the lesson text**: `stimuli/<condition>/<unit_id>.md`, one per condition, matched on length,
readability, equations and reading duration. These files are also the TRIBE inputs.

**Text controls** (`stimuli/variants/`, `stimuli/incorrect/`) are 180 reworded versions (two per stimulus) and 30
incorrect-but-fluent texts. They exist to test whether the cortical contrasts survive harmless rewording (F2) and
whether wrong content moves the prediction (F5). The learner never sees them.

Key checks, all in `corpus.py`: answer validation, section order, answer placement, the 10% duration caliper,
leakage (scaffolding must not state the answer), and the §5.5 near-duplicate screen (`near_duplicates`).

## 4. Phase II: predicted cortical response

The notebook runs TRIBE v2 on a Colab GPU. Each lesson text is turned into word onsets at a fixed reading speed
(eq. 4, 220 words per minute in the main specification), the model predicts a response per cortical vertex per
second, and the predictions are aggregated to 400 Schaefer parcels (eq. 6) and 7 Yeo networks (eq. 7).

The summary metrics per stimulus (eq. 8-9) are mean, peak, **area under the curve (AUC)**, time to peak,
sustained engagement, spatial dispersion and entropy. AUC is the one everything downstream uses.

- `tribe.py` is model-free arithmetic: timing, aggregation, metrics, contrasts, RSA. It is fully tested offline.
- The notebook only orchestrates: it never invents a prediction.
- `scripts/reparcellate.py` re-aggregates the saved vertex predictions onto another atlas (Schaefer-200) without
  a GPU, which is how parcellation became a specification-curve dimension.

**What Phase II gives the rest of the project** is one number per (unit, condition, parcel): the AUC. Standardised
across the corpus (eq. 28) it becomes `Z`, the only channel through which text reaches the neural model.

## 5. Phase III: the simulated learner

**State** (eq. 15): K knowledge, M memory, R independent reasoning, C calibration, D dependence on support, each
in [0, 1]. Learners are drawn from three prior-knowledge strata with correlated states and individual learning and
forgetting rates (eq. 16).

**One episode** (`episode.run_episode`):

```
[free choice only: the question, then "How do you want to approach this problem?" -> the chosen lesson]
  -> read the explanation -> first answer (3 options)
  -> traditional:   hint k, then answer again or ask for the next hint; worked solution after hint 3
     scaffolding:   LLM tutor turn k (diagnose, one question, level-k hint, leakage-checked); solution after turn 3
     substitution:  one LLM call with the full solution, then one re-answer
  -> unaided near-transfer question
  -> "That took you about N minutes."
  -> update K, M, R, C, D (eq. 19-25)
```

**No help before a first attempt.** Help options appear only after a wrong answer.

**Who decides what** (this is the subtle part):

| Decision | Who makes it | Why |
| --- | --- | --- |
| correctness | the logistic model, eq. 17-18 | transparent, and the transcript models are at chance on arithmetic (0.35 against a 0.333 baseline) |
| help requests, confidence, the free-choice approach | Centaur (a transcript model) in the hybrid engine | its choices track the learner's history strongly, which is exactly what it was trained for |
| the tutor's words | an LLM behind an OpenAI-compatible URL | numerically inert for correctness, but it is what Centaur reads |

This split is the `HybridEngine` in `engines.py`. `--engine logistic` is the fully transparent baseline;
`--engine centaur` routes everything to the transcript model and exists only for the §10.2 comparison.

**Effort** (eq. 19) is built from observable proxies: independent attempts, retrieval, generated steps, hint depth,
and whether the answer was revealed. **Instructional effectiveness** (eq. 20) combines correctness, coverage,
adaptation to the misconception and difficulty fit. The two multiply in the knowledge update, which is why
substitution loses: it suppresses effort.

**Checkpoints** (§7.7) test with all support removed: unaided accuracy, near and far transfer, retention, the
support gap, Brier score, calibration error and the help-request rate.

**Everything a model sees is observable history.** Latent states never appear in a prompt; `find_latent_leaks`
enforces it.

## 6. Phase IV: from response to accumulated state

The neural state `N` per parcel accumulates the standardised responses of the lessons a learner actually saw,
decaying with a half-life:

- **A, activation accumulation** (eq. 29): engaged exposure accumulates.
- **B, prediction-error learning** (eq. 31): what matters is experiencing and resolving error.
- **C, effort-dependent learning** (eq. 32): retrieval and effort, not passive exposure.
- **D, hybrid** (eq. 33): a weighted mix minus an offloading penalty. **This is the main specification.**

**The accumulator trick** (`plasticity.py`) is worth understanding, because it is why the robustness analysis is
cheap. `N` is linear in the fixed patterns `Z`, so each learner carries five decayed sums — one per behavioural
channel — and any mechanism is then a weighted projection `N = (w · A) @ Z`. Consequently the mechanism, the
lambdas, the reading speed, the TRIBE metric, the winsorising, the network weights, the parcellation and every
Z control are **post hoc**: they need no rerun. Only the decay rate lives inside the simulation.

`run_metrics` derives the §8.7 outcomes: functional concentration, representational differentiation (eq. 34),
cross-network integration, an efficiency proxy and alignment with far transfer.

## 7. Phase V: ten years

`longitudinal.py` is a vectorised numeric mirror of the Phase III episode loop — the same equations, run on arrays
so that 500 parameter draws × 2,000 learners × 10 years is feasible. The test `test_t1_*` pins the mirror to the
reference loop; if you change the episode logic and not `Sim.step`, that test fails, and it should.

**Calendar**: 40 instructional weeks a year, 3 episodes a week in the main specification (1 and 5 as arms), plus 12
break weeks that forget at a quarter of the term rate.

**Six scenarios**: traditional; scaffolding with rapid fade; scaffolding with no fade; substitution; free choice
under an assumed softmax rule; free choice under a rule fitted to Centaur's actual picks.

**The headline quantity** is the scenario contrast SC (eq. 37), never called an average treatment effect, and the
net advantage G (eq. 39), a weighted sum of the gains in K, R and M minus the rise in dependence D.

**The frontier** (Figure 7a) sweeps personalisation, retained effort and answer substitution; **tipping points**
(§9.7) find where G changes sign.

---

## 8. Where each result comes from

| Run tag | What it is | Size |
| --- | --- | --- |
| `population_logistic` / `_low` / `_high` | Phase III at the §7.1 scale, the three §7.2 parameter settings | 1,667 learners × 4 arms × 40 episodes each |
| `centaur_main` | the hybrid engine, paired with `logistic_40` for the §10.2 comparison | 40 × 4 × 30 = 4,800 episodes |
| `centaur_free_calib` | free-choice-only batch that validates and refits the choice rule | 80 × 60 = 4,800 episodes |
| `tribe_main` | the TRIBE run: 90 stimuli × 3 reading speeds, plus 180 shuffled controls | 8.1 GB |
| `tribe_textctl` | the 210 text controls and semantic coverage | 26 MB |
| `v_main` (+ `v_main_fcc`) | the ten-year main run, five scenarios (+ the Centaur-calibrated sixth) | 500 draws × 2,000 learners |
| `v_frontier`, `v_tipping`, `v_neural` | phase diagram, tipping lines, neural diagram | 100-200 draws × 300 learners |
| `v_z0_10y`, `v_e0_10y`, `v_uniform`, `v_mediation`, `v_repl0-2`, `v_epw1/5` | negative controls, mechanism decomposition, replicates, exposure arms | 50-200 draws |
| `spec_*` | the 72 specification reruns | 50 draws × 300 learners each |
| `g18_*` | the one-year pilot and its controls (decision gate 18) | — |

Runs are append-only and resumable. **A resume must keep the same learners, episodes, seed, setting, engine and
policy**, because changing the population size redraws every learner. A superseded run gets a new tag; logs are
never deleted.

## 9. Which output answers which question

| Question | Output |
| --- | --- |
| Are the three conditions comparable? | `corpus_balance.csv`, Figure 2, `tableS_semantic_coverage.csv`, `tableS_near_duplicates.csv` |
| Do the conditions differ in predicted cortical response? | `table4_cortical_contrasts*.csv`, Figure 3, `parcel_contrasts_auc.csv` |
| Does scaffolding preserve conceptual geometry? | `rsa_*.csv`, Figure 4, and differentiation in `tableS_neural_metrics_*.csv` |
| What happens to simulated learners in one term? | `tableS_phase3_outcomes.csv`, `tableS_phase3_settings.csv`, Figure S3 |
| Does the transcript engine change the story? | `engine_comparison.csv`, Figure S1, `choice_rule_*.csv` |
| What happens over ten years? | `table5_*.csv`, Figures 5 and 6 |
| When is AI beneficial, neutral or harmful? | Figure 7a, `tableS_tipping_points.csv` |
| Through which mechanism? | `tableS_mechanism_decomposition.csv` |
| How robust is any of it? | Figure 8a/8b, `table6_negative_controls.csv`, `table6_falsification.csv`, `tableS_variance_decomposition.csv` |
| What does every column mean? | `data_dictionary.csv` |

`uv run python -m neurotutorsim.report all` rebuilds all 49 tables and 14 figures from saved runs in about two
minutes. Every figure has a CSV twin with the same name, so no number in the thesis needs to be read off a plot.

## 10. What you may and may not claim

The falsification checklist (`table6_falsification.csv`) is the authority. As things stand:

- **The behavioural results are robust.** The median year-10 G keeps its sign in all 216 specifications of every
  scenario: scaffolding positive, substitution and free choice negative.
- **F2 is the hard constraint on the neural side.** Only scaffolding's dorsal-attention, salience and somatomotor
  contrasts survive rewording. No substitution-vs-traditional contrast does, and neither does the control network,
  which is the one Phase V's neural outcome uses. Present the neural trajectories as exploratory.
- **F4 flags scaffolding-with-rapid-fade** as bound-driven; the other scenarios' year-10 claims stand.
- **F1 removes three network contrasts** once duration and word count are covariates.
- **Never** describe any of it as causal, as a measured brain effect, or as a prediction of a real student's future.

Two honest asterisks to state: confidence, Brier and C track the learner's record rather than genuine calibration,
because the transcript model ignores which option it pressed; and the free-choice arm cannot support condition
contrasts, because the learner selected the condition.

## 11. Traps

- **Phase V must stay a mirror.** Change `run_episode`, a proxy or the logistic engine, and make the same change in
  `Sim.step`, or T1 fails.
- **The seed key is `[master, learner, episode]`** — deliberately without the condition, so a learner meets the same
  draws in every arm and contrasts are within-learner.
- **One tag per parameterisation.** `simulate.py` refuses a resume that changes the design rather than silently
  blending two populations.
- **Centaur is not reproducible bitwise** (KV-cache effects). A Centaur run is reproduced from its logs, never
  re-derived, which is why `outputs/logs/` matters.
- **`history_window: 3`.** A longer transcript drowns the payoff line the model is supposed to read.
- **Checkpoint levels are not comparable across checkpoints**: each probes the units studied most recently.
- **The specification ranks were frozen before results** (D17). The parcellation dimension was added later (D24) and
  must be described that way.

## 12. Command crib

```bash
uv run pytest                                             # 104 offline tests
uv run python -m neurotutorsim.corpus                     # validate the corpus, rewrite the indexes
uv run python -m neurotutorsim.simulate --engine logistic --tutor fake --tag <tag>
uv run python -m neurotutorsim.plasticity --run data/processed/<tag>
uv run python -m neurotutorsim.longitudinal --tag <tag> --years 10 --draws 500 --learners 2000
uv run python -m neurotutorsim.report all                 # every table and figure
uv run python -m neurotutorsim.report phase3|phase12|engines|phase5|frontier|controls|spec|variance
uv run --with nibabel --with nilearn python scripts/reparcellate.py --parcels 200
```

## 13. Writing the thesis

A section-by-section suggestion, with what to cite:

| Section | Content | Cite |
| --- | --- | --- |
| Methods: corpus | 30 units, matching, validators, text controls | Table 1, Figure 2, `corpus_balance`, `tableS_near_duplicates` |
| Methods: TRIBE | timing, aggregation, metrics, QC | `run_metadata.json`, `tribe_qc.json`, Table 2 |
| Methods: learner | eq. 15-25, the engine split, proxies | Table 2, Table 3 |
| Methods: plasticity and scenarios | eq. 28-34, the calendar, the six scenarios | Table 3, `PLAN.md` §2-3 |
| Results: immediate | condition contrasts and RSA | Table 4, Figures 3-4 |
| Results: learners | one term at the population scale | `tableS_phase3_outcomes`, Figure S3 |
| Results: ten years | contrasts, distributions, frontier, tipping points | Table 5, Figures 5-7 |
| Results: robustness | specification curve, controls, variance, falsification | Figure 8, Table 6, `tableS_variance_decomposition` |
| Discussion | which assumptions drive the divergence, and what to measure empirically | `tableS_variance_decomposition`, `tableS_tipping_points` |
| Limitations | verbatim from `PLAN.md` §7 | — |

The discussion has a natural spine: the variance decomposition says year-10 G is 68% scenario and 29% learner, so
the thing worth measuring empirically is how much cognitive work a real tutor leaves with the student — not the
plasticity constants, which barely move the behavioural result but dominate the neural one.

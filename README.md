# NeuroTutorSim

A purely computational comparison of three instructional regimes (traditional, AI scaffolding, AI
substitution) following `NeuroTutorSim_Project_Brief.pdf`. This repository holds all five phases:
the Phase I corpus (30 MBA units, 15 concepts x 2, each taught in the three conditions, plus 210 text controls),
Phase II TRIBE v2 predictions (a Google Colab notebook), the Phase III synthetic learner engine, Phase IV
plasticity and the Phase V ten-year scenarios, and the §10-§13 analysis layer that rebuilds every table and figure.

Phase III uses a **hybrid response engine**: Centaur makes every behavioural choice, the transparent logistic model
decides correctness, and an LLM tutor (Qwen2.5-3B-Instruct) runs the two AI protocols. Each learner runs three
assigned arms plus a `free_choice` arm in which it picks the protocol at every problem. Centaur runs cover 40 + 80
learners; the full population and all of Phase V use the logistic model, and Phase V's free choice uses either a
documented softmax in D or a rule fitted to Centaur's picks (`choice_rule.py`). Every result is model-implied
(brief §15). `PLAN.md` holds the decisions (D1-D22), the limitations (§7) and the run log (§8).

## Setup

```bash
uv sync                      # creates .venv with numpy, pandas, pyarrow, pyyaml, requests (+ pytest)
cp .env.example .env         # only needed if tutor.base_url is a remote API; LM Studio needs no key
```

LM Studio on `http://127.0.0.1:1234` serves two models: the choice model (`centaur`, a GGUF of
`marcelbinz/Llama-3.1-Centaur-8B-adapter` merged on Colab, or `llama-3.1-minitaur-8b`; ids in
`engine.models`) with a context length of 8192 or more, and the tutor `qwen2.5-3b-instruct`. The choice
engine uses `/v1/chat/completions` with an assistant prefill because that is the only LM Studio path that
returns logprobs; see `src/neurotutorsim/engines.py`.

## Commands

```bash
uv run pytest                                          # offline tests (fake engine + fake tutor)
uv run python -m neurotutorsim.corpus                  # validate units + stimuli, write units.csv / stimuli.csv
uv run python -m neurotutorsim.simulate --engine logistic --tutor fake --learners 30 --episodes 12
uv run python -m neurotutorsim.simulate --learners 1 --episodes 1 --conditions free_choice   # hybrid, Centaur + Qwen
uv run python -m neurotutorsim.simulate --learners 5 --episodes 10                          # all four arms
uv run python -m neurotutorsim.simulate --engine centaur --learners 3 --episodes 11 --conditions traditional  # all-transcript, §10.2
uv run python -m neurotutorsim.simulate --resume                                          # continue an interrupted run
```

Outputs go to `data/processed/<tag>/` and `outputs/logs/<tag>/`, where the tag defaults to the engine
name (`hybrid`, `centaur`, `minitaur` or `logistic`), so engines can run on the same population for the brief's §10.2
comparison: `episodes.jsonl` (source of truth, append-only), `responses.csv`, `learner_state.parquet`,
`checkpoints.csv`, the call logs and a run log. `--summarize data/processed/logistic` prints the summary
of any finished folder. Each scored response carries the brief's §7.3 fields: the answer, the 1-5 confidence
rating, the `explanation` (the method behind the chosen option) and `requested_support`.

### Phases IV-V, analysis and the Colab model server (added 2026-09-18)

```bash
uv run python -m neurotutorsim.plasticity --run data/processed/population_logistic       # Phase IV, post hoc
uv run python -m neurotutorsim.longitudinal --tag v_main --years 10 --draws 500 --learners 2000   # Phase V
uv run python -m neurotutorsim.longitudinal --tag v_frontier --frontier grid --draws 100 --learners 300 --no-neural
uv run python -m neurotutorsim.longitudinal --tag v_mediation --mediate E,F,D --draws 50 --learners 500
uv run python -m neurotutorsim.choice_rule fit --runs data/processed/centaur_main      # the Centaur free-choice rule
uv run python -m neurotutorsim.report phase12          # Tables 1-4, Figures 1-4 (outputs/tables, outputs/figures)
powershell -File scripts/run_gate18.ps1                # decision gate 18 (one-year pilot + controls + table)
powershell -File scripts/centaur_loop.ps1 -Remote      # a Centaur run against notebooks/serve_models.ipynb
uv run python scripts/compare_servers.py               # equivalence check before switching a run's server
```

Phase V writes append-only parts under `data/processed/phase5/<tag>/` and refuses a `--resume` with a changed design.
`notebooks/serve_models.ipynb` serves Centaur and the tutor from a Colab GPU; paste the two lines it prints into
`.env` (`NEUROTUTOR_SERVER_URL`, `NEUROTUTOR_SERVER_TOKEN`) and run with `--remote`.

## Phase II: TRIBE v2 on Colab

Open `notebooks/tribe_phase2.ipynb` in Google Colab with an L4 GPU runtime (the configured `EXPECTED_GPU`; a T4
works with `EXPECTED_GPU = "T4"` over two sessions), add the Colab secrets `HF_TOKEN` (a
Hugging Face account that has accepted the `meta-llama/Llama-3.2-3B` licence, TRIBE's gated text encoder) and
`GITHUB_TOKEN` (to clone this private repository; or point `CORPUS_SOURCE` at a Drive copy or an uploaded zip),
edit the configuration cell and run all. The first run installs TRIBE v2 at a pinned commit and asks for one
runtime restart. The notebook verifies the checkpoint hash, reproduces the official example, predicts all 90
stimuli at 220 wpm (plus 180 and 260 as robustness arms), aggregates to Schaefer-400 parcels and Yeo-7 networks,
and writes the brief's D3 prediction dataset (`tribe_vertex/`, `tribe_parcel.parquet`, `tribe_network.parquet`,
`tribe_metrics.parquet`, `tribe_patterns.parquet`, the §10.1 controls, `run_metadata.json`, `tribe_qc.json`) to
`DRIVE_OUTPUT_DIR/<RUN_TAG>/` on Google Drive as they are produced, so a dropped session resumes instead of
restarting. Budget about an hour on a T4, ~5.7 GB of Drive for three reading speeds, and ~20 GB of the runtime's own
disk for the feature cache and weights, which never touch Drive; the shuffled controls for all 30 units add roughly
1.5-2 h, ~3.4 GB of Drive and ~26 GB of runtime disk. The notebook checks both before it starts. With
`SAVE_TO_DRIVE = False` everything goes to the runtime disk and is lost when the session ends, and the notebook
then bundles the outputs into browser-sized zips instead. No figures are produced. `src/neurotutorsim/tribe.py` holds the arithmetic (tested offline by
`uv run pytest tests/test_tribe.py`); the §6.6 contrasts and §6.7 RSA need no GPU and run offline on the saved
tables:

```python
import pandas as pd
from neurotutorsim import tribe
metrics = pd.read_parquet("<run>/wpm220/tribe_metrics.parquet")
table4 = tribe.fixed_effects(metrics)           # eq. 13 with cluster-bootstrap CIs; tribe.paired_contrasts for eq. 10-12
z = pd.read_parquet("<run>/wpm220/tribe_patterns.parquet")   # rows stimulus_id, columns parcel_id: the z_uc of eq. 14
```

## Reproducing the results

Every run is append-only and resumable (`--resume` with the same arguments), and a changed design is refused
rather than blended. In order, with the wall clock measured here:

| Step | Command | Time |
| --- | --- | --- |
| Corpus | `uv run python -m neurotutorsim.corpus` | seconds |
| Phase II | `notebooks/tribe_phase2.ipynb` on a Colab L4, `SESSION = "main"` then `"text_controls"`; copy each Drive tag folder to `data/tribe/<tag>/` | ~8 h (main), ~5.5 h (text controls) |
| Phase III, logistic | `simulate --engine logistic --tutor fake --tag population_logistic` (and `--setting low/high --tag population_low/high`; `--learners 40 --episodes 30 --tag logistic_40`) | ~16 min each |
| Phase III, Centaur | `notebooks/serve_models.ipynb`, then `scripts/centaur_loop.ps1 -Remote` (`centaur_main`, then `centaur_free_calib`) | ~1 day on Colab |
| Phase IV | `plasticity --run data/processed/<tag>` | minutes |
| Gate 18 | `scripts/run_gate18.ps1` | minutes |
| Phase V main | `longitudinal --tag v_main --years 10 --draws 500 --learners 2000 --scenarios traditional scaffolding_rapid scaffolding_nofade substitution free_choice` | ~70 min |
| Frontier | `scripts/run_frontier.ps1` (`v_frontier`, `v_tipping`, `v_neural`) | ~70 min |
| Controls, mediation, replicates, exposure, spec curve | `scripts/run_remaining.ps1` | ~9 h (spec curve 7 h) |
| Centaur choice rule + sixth scenario | `scripts/run_centaur_rule.ps1` (validate, refit, `v_main_fcc`) | ~80 min |
| Tables and figures | `uv run python -m neurotutorsim.report all` | ~4 min |

All commands run through `uv run python -m neurotutorsim.<module>`; the PowerShell scripts do this themselves.
Keep `outputs/logs/*.jsonl` and `episodes.jsonl`: Centaur scores are not bitwise reproducible, so a Centaur run is
reproduced from its logs, never re-derived.

### Output map (`outputs/tables/*.csv`, `outputs/figures/*.png|.pdf`)

| Brief item | Files |
| --- | --- |
| Tables 1-3 (conditions, components, parameters with source or "assumption") | `table1_conditions`, `table2_components`, `table3_parameters` |
| Table 4, §6.6 cortical contrasts (+ covariates, eq. 42, reading speed) | `table4_*`, `parcel_contrasts_auc`, Figures 3, S2 |
| §6.7 RSA | `rsa_*`, Figure 4 |
| §5.5 corpus balance, §5.4 coverage | `corpus_balance`, Figure 2, `tableS_semantic_coverage*` |
| §10.2 Centaur vs logistic | `engine_comparison`, `engine_free_choice_shares`, Figure S1, `choice_rule_*` |
| Gate 18, gate 19 | `gate18_checks`, `gate19_metric_definitions` |
| Table 5, Figures 5-6 (scenario contrasts, trajectories, eq. 43) | `table5_*`, `fig5*`, `fig6*`, `tableS_trajectory_model_v_main` |
| §9.6-9.7 frontier and tipping points | Figure 7a/7b, `tableS_tipping_points*`, `tableS_exposure` |
| §11.5 mechanisms | `tableS_mechanism_decomposition` |
| Table 6, §10.3 and §10.6 | `table6_negative_controls`, `table6_falsification`, `tableS_z_controls`, `tableS_sign_flip_null`, `tribe_shuffle_controls`, `tableS_regeneration_*`, `tableS_incorrect_control` |
| §10.4 specification curve, §10.5 variance | Figure 8a/8b, `tableS_variance_decomposition` |
| Every column | `data_dictionary` |

## Brief Appendix A checklist

| Item | Status |
| --- | --- |
| Repository builds from a clean environment | Done: `uv sync` from `uv.lock`; `uv run pytest` (99 tests, offline) |
| All 120 units have deterministic answer validation | **Limitation**: 30 units (15 concepts x 2, MBA topics); all 30 validated by `corpus` |
| Three conditions factually equivalent and matched | Done for calipers (duration within 10%); **limitation**: \|SMD\| < 0.10 missed on 8 of 9 features (all but example count), so Table 4 is also reported with covariates (F1) |
| Scaffolding and substitution pass leakage and compliance tests | Done: numeric leakage check after every tutor call, tested (`test_corpus`, `test_episode`) |
| Official TRIBE example reproduced | Done (`tribe_main` `tribe_qc.json`) |
| TRIBE outputs cached with metadata and timestamps | Done: `run_metadata.json`, `tribe_run_log.jsonl`, checkpoint and atlas hashes |
| Parcel and network mappings documented | Done: `parcels_schaefer400.csv`, `notebooks/CLAUDE.md` |
| Learner monotonicity tests pass | Done: `test_learners`, `test_engines` direction tests; gate 18 G1-G10 |
| Zero-plasticity and shuffled-condition controls null | Zero plasticity exactly 0; permuted conditions median ratio 0.30, but 8 of 28 scenario-networks >= 0.5 (reported as no claim, F5) |
| One-year pilot sensible before ten years | Done: gate 18 passes (`g18_*`) |
| Every parameter has a source or "assumption" label | Done: Table 3 |
| Conclusions survive the robustness set or are indeterminate | Done: G keeps its sign in all 216 specifications per scenario; neural contrasts reported as no claim where F1-F5 fail (`table6_falsification`) |
| No causal or observed-future-brain claims | Done: §15 wording in all labels |
| All figures and tables regenerate from scripts | Done: `report all` into empty folders, exit 0 |
| README lets another team reproduce the pipeline | This file |

## Layout

| Path | Holds |
| --- | --- |
| `config/default.yaml` | every parameter (low/medium/high arms), seeds, engine, tutor, run scope |
| `config/prompts/` | the scaffolding and substitution tutor policy prompts |
| `data/units/*.json` | authored units: problem, validator, misconception, distractors, hints, transfers |
| `stimuli/<condition>/` | the static per-condition texts (also the TRIBE inputs); `stimuli/variants/`, `stimuli/incorrect/` the text controls |
| `src/neurotutorsim/` | `corpus`, `learners`, `engines`, `tutor`, `episode`, `simulate`, `tribe`, `plasticity`, `longitudinal`, `choice_rule`, `analysis`, `report` |
| `notebooks/` | `tribe_phase2.ipynb` (Phase II) and `serve_models.ipynb` (Centaur + tutor server), both for Colab |
| `scripts/` | the Centaur run loop, the Phase V run chains, the gate-18 driver and the server equivalence check |
| `tests/` | offline tests; no server or API key needed |

See `CLAUDE.md` files in each folder for the decisions behind the code.

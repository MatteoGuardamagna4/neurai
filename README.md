# NeuroTutorSim

A purely computational comparison of three instructional regimes (traditional, AI scaffolding, AI
substitution) following `NeuroTutorSim_Project_Brief.pdf`. This repository holds the Phase I corpus
skeleton (one validated example unit per condition) and the full Phase III synthetic learner engine,
with a **hybrid response engine** - Centaur (served locally by LM Studio) makes every behavioural
choice, the transparent logistic model decides correctness - and a local LLM tutor (Qwen2.5-3B-Instruct)
for the two AI protocols. Each learner runs three assigned arms plus a `free_choice` arm in which it picks
the protocol itself at every problem. TRIBE predictions (Phase II) come from `notebooks/tribe_phase2.ipynb`, a
Google Colab notebook (see below); Phases IV and V are not built yet but every quantity they need is already emitted.

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

## Phase II: TRIBE v2 on Colab

Open `notebooks/tribe_phase2.ipynb` in Google Colab with a GPU runtime, add the Colab secrets `HF_TOKEN` (a
Hugging Face account that has accepted the `meta-llama/Llama-3.2-3B` licence, TRIBE's gated text encoder) and
`GITHUB_TOKEN` (to clone this private repository; or point `CORPUS_SOURCE` at a Drive copy or an uploaded zip),
edit the configuration cell and run all. The first run installs TRIBE v2 at a pinned commit and asks for one
runtime restart. The notebook verifies the checkpoint hash, reproduces the official example, predicts all 90
stimuli at 220 wpm (plus 180 and 260 as robustness arms), aggregates to Schaefer-200 parcels and Yeo-7 networks,
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

## Layout

| Path | Holds |
| --- | --- |
| `config/default.yaml` | every parameter (low/medium/high arms), seeds, engine, tutor, run scope |
| `config/prompts/` | the scaffolding and substitution tutor policy prompts |
| `data/units/*.json` | authored units: problem, validator, misconception, distractors, hints, transfers |
| `stimuli/<condition>/` | the static per-condition texts (also the TRIBE inputs) |
| `src/neurotutorsim/` | `corpus`, `learners`, `engines`, `tutor`, `episode`, `simulate`, `tribe` |
| `notebooks/` | `tribe_phase2.ipynb`, the Phase II Colab notebook |
| `tests/` | offline tests; no server or API key needed |

See `CLAUDE.md` files in each folder for the decisions behind the code.

# NeuroTutorSim

A purely computational comparison of three instructional regimes (traditional, AI scaffolding, AI
substitution) following `NeuroTutorSim_Project_Brief.pdf`. This repository holds the Phase I corpus
skeleton (one validated example unit per condition) and the full Phase III synthetic learner engine,
with a **hybrid response engine** - Centaur (served locally by LM Studio) makes every behavioural
choice, the transparent logistic model decides correctness - and a local LLM tutor (Qwen2.5-3B-Instruct)
for the two AI protocols. Each learner runs three assigned arms plus a `free_choice` arm in which it picks
the protocol itself at every problem. TRIBE predictions (Phase II) are produced by a teammate; Phases IV and V are not built
yet but every quantity they need is already emitted.

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

## Layout

| Path | Holds |
| --- | --- |
| `config/default.yaml` | every parameter (low/medium/high arms), seeds, engine, tutor, run scope |
| `config/prompts/` | the scaffolding and substitution tutor policy prompts |
| `data/units/*.json` | authored units: problem, validator, misconception, distractors, hints, transfers |
| `stimuli/<condition>/` | the static per-condition texts (also the TRIBE inputs) |
| `src/neurotutorsim/` | `corpus`, `learners`, `engines`, `tutor`, `episode`, `simulate` |
| `tests/` | offline tests; no server or API key needed |

See `CLAUDE.md` files in each folder for the decisions behind the code.

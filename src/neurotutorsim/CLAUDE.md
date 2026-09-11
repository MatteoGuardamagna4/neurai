# src/neurotutorsim/

| module | concern |
|---|---|
| `corpus.py` | unit JSON schema, validators (`VALIDATORS` + safe `expression`), stimulus parsing/checks, matching features, `units.csv`/`stimuli.csv` |
| `learners.py` | population (eq. 15-16), `Learner` state + observable record, proxies, eq. 19-25, persistence cap, calibration metrics |
| `engines.py` | `Trial`/`Decision` seam; `MinitaurEngine` (the Psych-101 transcript engine, used for both Centaur and Minitaur: LM Studio prefill scoring + sampling, call log); `LogisticEngine` (eq. 17-18, plus a documented softmax-in-D rule for the approach choice); `HybridEngine` (choices to the transcript model, correctness to the logistic one) |
| `tutor.py` | OpenAI-compatible tutor (`scaffold`, `substitute`), leakage check, `.env` loading, `FakeTutor` |
| `episode.py` | the per-learner episode state machine for the three assigned conditions and the `free_choice` arm, proxies, `EpisodeRecord` (`condition` = the arm, `protocol` = what actually ran) |
| `simulate.py` | CLI: config arms, run/resume loop, §7.7 checkpoints, table export, run log, §10.2 direction checks |

Invariants:
- Engines only see a `Trial`; Minitaur reads its text fields, the logistic engine its numeric fields.
  Nothing latent (K, M, R, C, D, theta, alpha, delta) may appear in prompt text (`find_latent_leaks`).
- `run_episode` mutates the learner in place and returns a record that includes `learner_after`, the
  snapshot a resumed run restores from. Per-episode RNG seeds are `[master, learner, episode]`: the
  condition is deliberately NOT in the key, so a learner meets identical draws in all four arms.
- `run_episode` takes the stimuli of all three conditions for the unit, because `free_choice` shows the
  lesson of whichever protocol the learner picks.
- The observable record is keyed on the **concept**, not the unit id (`concept_record`), so the two units
  that teach a concept count together; `last_seen` stays on the unit id, since §7.7 retention is per item.
- Every transcript-engine and tutor call is appended to `outputs/logs/calls_*.jsonl` before its result is used.
- Ask the transcript model for CHOICES only (approach, help, confidence). It is at chance on the
  arithmetic, measured twice; correctness comes from eq. 17-18. See the root CLAUDE.md for the numbers.
- Proxy definitions (brief §7.4, all observable, none tunable) live in `run_episode`; keep them there.
- Phase IV/V consume `learner_state.parquet` (`effort`, `pe`, `retrieval`, `offloading`, `resolution`);
  do not add neural quantities here.

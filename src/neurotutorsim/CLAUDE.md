# src/neurotutorsim/

| module | concern |
|---|---|
| `corpus.py` | unit JSON schema, validators (`VALIDATORS` + safe `expression`), stimulus parsing/checks, matching features, `units.csv`/`stimuli.csv` |
| `learners.py` | population (eq. 15-16), `Learner` state + observable record, proxies, eq. 19-25, persistence cap, calibration metrics |
| `engines.py` | `Trial`/`Decision` seam; `MinitaurEngine` (the Psych-101 transcript engine, used for both Centaur and Minitaur: LM Studio prefill scoring + sampling, call log); `LogisticEngine` (eq. 17-18, plus a documented softmax-in-D rule for the approach choice); `HybridEngine` (choices to the transcript model, correctness to the logistic one) |
| `tutor.py` | OpenAI-compatible tutor (`scaffold`, `substitute`), leakage check, `.env` loading, `FakeTutor` |
| `episode.py` | the per-learner episode state machine for the three assigned conditions and the `free_choice` arm, proxies, `EpisodeRecord` (`condition` = the arm, `protocol` = what actually ran) |
| `simulate.py` | CLI: config arms, run/resume loop, §7.7 checkpoints, table export, run log, §10.2 direction checks |
| `tribe.py` | Phase II adapters, model-free: eq. 4 word timing, vertex-file I/O, parcel/network aggregation (eq. 6-7), §6.5 metrics (eq. 8-9), eq. 10-13 contrasts with cluster bootstrap, RSA (eq. 14, 34), shuffled-text controls; driven by `notebooks/tribe_phase2.ipynb` |
| `plasticity.py` | Phase IV: eq. 28 Z from the TRIBE run, the five-channel `Accumulator` (N = (w . A) @ Z, so mechanism, lambdas and every Z control are post hoc), eq. 29-33 weights, eq. 7 networks, §8.7 outcomes, `apply_to_run` on a Phase III run |
| `longitudinal.py` | Phase V: parameter draws, `Pop` arrays, the vectorised mirror of `run_episode` + `LogisticEngine` (`Sim.step`, checked by T1), calendar and breaks, paired contrasts, G, neural d, frontier/lines/neural-diagram/mediation designs, append-only parts + `run.json`, `read_table` |
| `choice_rule.py` | a conditional logit fitted to Centaur's free-choice probabilities on what Centaur reads (habit, payoff record, tried, recent form), with a learner bootstrap; Phase V's `free_choice_centaur` uses it |
| `analysis.py` | pure §10-§11 functions: corpus balance (SMD, TOST), BH-FDR, Table 4 and eq. 42, RSA summary, gate-19 metric definitions, engine comparison, gate 18, Table 5 summaries, text controls (F2 regeneration, incorrect-text control, coverage) |
| `report.py` | CLI that rebuilds tables and figures from saved data (dataviz reference palette; every figure has a CSV twin) |

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
- Phase V must stay a numeric mirror of the Phase III loop: a change to `run_episode`, the proxies or the logistic
  engine needs the same change in `Sim.step`, and `tests/test_longitudinal.py::test_t1_*` must stay green (it is
  gate 18's G10). `learners.step_state` is the one implementation of eq. 21-25 for both (`form: brief` pins Phase III
  through `tests/data/phase3_golden.json`; `bounded` is Phase V).
- Phase V rows are scenario-major (`row = scenario * n + learner`) and every scenario of a draw sees the same random
  numbers (`Draws`), so a scenario contrast is paired; a mediated or forgetting-scaled scenario names its comparator.

# tests/

Offline only: no LM Studio, no API key. `ScriptedEngine` (test_episode.py) answers with a scripted
sequence of option kinds; `FakeTutor` returns canned replies; Minitaur transport is exercised by
monkeypatching `engines.requests.post` with canned `top_logprobs` payloads; the real `Tutor` class is
tested by monkeypatching `chat`. `test_simulate_end_to_end_...` copies config/data/stimuli into a temp
root and runs the CLI with the logistic engine, then checks the overwrite refusal and `--resume`.
`FixedChoice` (test_engines.py) stands in for Centaur when testing `HybridEngine` routing.
Fixtures (`cfg`, `units`, `stimuli`) are session-scoped: deepcopy `cfg` before mutating it.
The end-to-end test asserts `n_learners x episodes x 4` episodes, because the default config runs four arms.
Run with `uv run pytest`.

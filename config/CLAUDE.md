# config/

- `default.yaml` is the single configuration. Any leaf written as `{low, medium, high}` is a brief
  §7.2 sensitivity arm; `parameter_setting` (or `--setting`) picks one arm for the whole run
  (`learners.resolve`). Every numeric value is an assumption unless the comment cites the brief.
- `engine` selects `minitaur` (LM Studio at `base_url`, model id as LM Studio lists it) or `logistic`.
- `tutor` is any OpenAI-compatible chat-completions server; `provider: fake` uses canned replies.
  The API key is read from the environment variable named in `api_key_env` (`.env` is loaded).
- `prompts/scaffolding.md` and `prompts/substitution.md` are `string.Template` files (`$problem`,
  `$answer`, `$distractor_notes`, `$hints`, `$worked_solution`), filled by `tutor.unit_facts` from the
  **unit JSON only** - never from the stimulus markdown, so the `# Diagnostic questions` section of
  `stimuli/ai_scaffolding/` is not what `$distractor_notes` carries (`problem.distractors[].note` is).
  `unit_facts` raises if any note or hint is empty, so no variable is ever substituted blank.
  Scaffolding additionally takes `$turn` and `$max_turns`, the rung of the hint ladder; `Tutor.scaffold`
  passes them and restates the level in the user turn, so it is never inferred from the transcript.
  Scaffolding must never state the answer; leakage is checked numerically after every call.
- `support.persistence_policy` (`persistent` / `gradual_fading` / `immediate_withdrawal`) is the
  Phase V scenario knob; it caps how many help turns an episode may use.
- `updates.form` (`brief` for every Phase III run, `bounded` for Phase V, D3), `calendar` (weekly forgetting, 12
  break weeks at a quarter of the term rate, D4), `plasticity` (Phase IV; `tribe_dir: data/tribe/tribe_main`) and
  `phase5` (draws, scenarios incl. `free_choice_centaur`, which needs `phase5.choice_rule`, G weights) are the
  2026-09-16/18 blocks; every value there is an assumption labelled in Table 3 (`report.py`).
- `spec_curve.yaml` holds the specification-curve plausibility ranks, approved 2026-09-18 before any Phase V result
  (brief §10.4): do not edit ranks after results exist.

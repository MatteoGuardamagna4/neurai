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

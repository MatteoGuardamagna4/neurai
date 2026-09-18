# data/

- `units/<unit_id>.json` are the authored source of truth: canonical problem, near and far transfer
  problems (each with a `validator` + `params` or an `expression`, the `answer`, a display `format`
  and exactly two `distractors` whose `rule` expressions are re-evaluated), the documented
  misconception, a worked example, three hints (general -> specific) and the worked solution.
  `python -m neurotutorsim.corpus` recomputes everything and refuses a unit that fails (brief §5.5).
  **30 units, 15 concepts, exactly two units per concept** (`<concept>_001` and `<concept>_002`): the
  pair teaches the same method with a different surface form, and `concept_record` counts them together
  so the second one reads as familiar. Concepts: break_even_quantity, contribution_margin_ratio,
  target_profit_after_tax, margin_of_safety, relevant_cost, operating_leverage, multi_product_break_even
  (managerial accounting); markup_vs_margin, price_elasticity (pricing); net_present_value,
  payback_period, wacc, return_on_investment (corporate finance); customer_lifetime_value, cac_payback
  (marketing analytics). Every unit uses the generic `expression` validator, so adding one needs no Python.
  Keep `run.episodes` >= 30 if every unit is to be seen: the curriculum cycles `order[ep % len(order)]`.
- `processed/units.csv` and `processed/stimuli.csv` are generated corpus indexes (committed).
- `processed/<tag>/episodes.jsonl` and `checkpoints.jsonl` (tag = engine name unless `--tag` is given)
  are the append-only run outputs; every
  table (`responses.csv`, `learner_state.parquet`, `checkpoints.csv`) is derived from them and a
  resumed run restores learner state from them. Gitignored, never hand-edited, never regenerated silently.
- `tribe/tribe_main/` (gitignored) is the Phase II run copied from Drive: `wpm220|180|260/tribe_metrics.parquet`,
  `tribe_patterns.parquet`, `parcels_schaefer400.csv`, `controls/`, `tribe_qc.json`. `plasticity.tribe_dir` points here.
- `processed/<tag>/neural_network.parquet` / `neural_state.parquet` / `plasticity.json` are Phase IV's post hoc
  outputs on a Phase III run (`python -m neurotutorsim.plasticity --run ...`).
- `processed/phase5/<tag>/` is one Phase V run: `run.json` (design, seeds, `draws_done`, the part list) and one
  folder per table (`simulation_draws`, `parameter_draws`, `neural_contrasts`, `weekly_means`, `yearly_subsample`,
  `episodes_central`, `neural_diagram`, `contrast_hist`) plus `.npz` accumulator parts. Read them with
  `longitudinal.read_table` / `read_arrays`, which only list the parts `run.json` records.
- `processed/choice_rule/choice_rule.json` is the rule fitted to Centaur's free-choice picks (`choice_rule.py`), with
  its bootstrap and data sources; `validation.json` beside it is the out-of-sample check on `centaur_free_calib`.

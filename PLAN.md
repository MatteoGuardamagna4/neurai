# PLAN: NeuroTutorSim from Phase III to results (2026-09-16 → 2026-09-25)

Implementation plan for brief §8 (Phase IV), §9 (Phase V), §10 (validation), §11 (statistical analysis plan) and
§13 (figures and tables), plus the runs still missing from Phases II and III. Written 2026-09-16 from the brief,
the code at commit `7088383` and measurements taken on this laptop the same day. Every step says **who** does it,
**what kind** of work it is, **exactly** what to type or build, and **how we know it is done**.

Deadline: **Fri 2026-09-25, code and results** (paper and presentation later). People: you, with Claude.

---

## 1. Where things stand

**Update 2026-09-18 (evening).** Done: S1 (four logistic runs), S2 (TRIBE `tribe_main`, all QC checks pass;
outputs in `data/tribe/tribe_main/`), S4, S5 (code, and `apply_to_run` on both logistic runs), S6 (T1 green), S8
(gate 18 passes on the `g18_*` runs, see D16), the S10/S11 run modes (`--frontier grid|lines|neural`,
`--mediate`), the Phase I/II part of S14 (Tables 1-4, Figures 1-4 and S2, gate-19 definitions), the S13 ranks
(approved, D17) and `choice_rule.py` + the sixth scenario (D18). Running: `centaur_main` on Colab (D13), then the
free-choice calibration batch `centaur_free_calib` (queued by `outputs/logs/centaur_main.pid`'s chain). Still to do:
S7 (after Centaur), the final choice-rule fit and validation, S9, S10-S13 runs, S12 code, the Phase V part of S14,
S15. The table below is the 2026-09-16 state.

**Update 2026-09-19.** **Every run is done**; what is left is code and the freeze. Overnight, all exit 0 and
complete: S12 controls `v_z0_10y`, `v_e0_10y`, `v_uniform`; S11 `v_mediation`; S13 `v_repl0-2` and all 72 `spec_*`
runs (420 min, not the 1.5-2 h estimated); S9 `v_epw1`, `v_epw5`; `centaur_free_calib` (4,800 episodes, 80 x 60, no
gaps; three restarts on a transient `PermissionError` while appending to `episodes.jsonl`, no episode lost). The
`centaur_main` choice rule validates out of sample (cross-entropy 1.041 vs 1.080 for constant shares, argmax agreement
70%); refitted on both runs (6,000 decisions) and used by `v_main_fcc` (traditional + `free_choice_centaur`,
501/501 draws; its traditional arm equals `v_main`'s to 3e-16).

Report layer for S9-S13 written (`report exposure|frontier|mechanisms|controls|spec|variance`, all in `report all`):
Table 5 and Figures 5-6 from `v_main` + `v_main_fcc` (six scenarios), `tableS_exposure`, Figure 7a/7b +
`tableS_tipping_points`, `tableS_mechanism_decomposition` (E, F, D reruns + Z post hoc), Table 6
(`table6_negative_controls`, `table6_falsification`, `tableS_z_controls`, `tableS_sign_flip_null`), Figure 8a/8b,
`tableS_variance_decomposition`. D20 records three rule fixes made on first contact with the results.

Also done: `data_dictionary.csv` (`report dictionary`: every column of every table, 226 data columns, none
undocumented), the append retry in `simulate.py` (the `PermissionError` above). **S14 done criterion met:** `report all` rebuilds every table and figure into empty `outputs/tables` and `outputs/figures` in 3.5 min, exit 0 (the choice-rule tables included). Still to do: §11.3 mixed model on the
Figure 5 data (cut-list item 2), S15.

**Update 2026-09-18 (23:30).** Done overnight: `v_main` (5 scenarios, 500 x 2,000 x 10 years, 69 min), `v_frontier`,
`v_tipping`, `v_neural` (S10 runs). `centaur_free_calib` at 3,926 / 4,800 episodes. Every remaining laptop run is now
in two scripts (below); what is left after them is code (the Phase V part of S14, the report wiring for the new tags)
and S15.

| Script | Runs | Starts |
|---|---|---|
| `scripts/run_remaining.ps1` | S12 10-year controls `v_z0_10y`, `v_e0_10y`, `v_uniform` (F4); S11 `v_mediation`; S13 replicates `v_repl0-2`; S9 `v_epw1`, `v_epw5`; then the 72 `spec_*` runs | now (~3-4 h, estimated from `v_main`'s speed) |
| `scripts/run_centaur_rule.ps1 -WaitForPid <centaur_main.pid>` | `choice_rule validate` (the `centaur_main` fit, kept as `choice_rule_centaur_main.json`) on `centaur_free_calib`; refit on both runs; `v_main_fcc` = traditional + `free_choice_centaur` at `v_main`'s design | when the calibration batch ends (refuses if it has < 4,800 episodes) |

Both scripts append to `outputs/logs/remaining_runs.log` / `centaur_rule.log`. `run_remaining.ps1` names the five
`v_main` scenarios explicitly, because the config also lists `free_choice_centaur` and those runs must not use the
interim rule. Fixed on the way (D19): `--seed-offset` used to shift the master seed for parameters and learners as
well, which would have made the §10.5 replicates independent runs; it now moves only the behaviour stream.

| Part | State |
|---|---|
| Phase I corpus | Done: 30 units, 90 stimuli, all calipers inside 10%. No reworded variants, no semantic-coverage judge (§5.4). |
| Phase II TRIBE | Notebook built, **never run**. No cortical prediction exists. `main` on GitHub is current (`7088383`). |
| Phase III `centaur_main` | **Stopped 2026-09-16 07:39** on an LM Studio timeout at **2,359 / 4,800 episodes**: traditional 40/40 learners, scaffolding 38 done + learner 38 at episode 18, substitution and free choice not started. No run log yet (written only at the end). |
| Phase III logistic runs | None on disk (`population_logistic`, `logistic_40`, low/high arms). |
| Phase IV, V, §10, §11, §13 | Not started. `simulate.summarize` has two §10.2 direction checks; `tribe.py` has eq. 10-14 and 34. |

Measured today, and used below:

- **Centaur speed.** 54 h of model time for 2,359 episodes = **~83 s/episode**. LM Studio slowed ~7× per token
  mid-run at constant prompt length (5 → 33 s per 1k tokens) and recovered once after a reload.
- **Laptop.** Intel Core Ultra 5 125U, 15.5 GB RAM, **no discrete GPU**: Centaur and every Python run share it.
- **Per-learner loop speed.** `run_episode` + logistic engine: **0.43 ms per learner-episode**.
- **Vectorised numpy step** (prototype with all branches): **~1.0 µs per learner-episode** at 20k learners
  (1.7 µs at 100k) → keep chunks near 20k learners.
- **Long-horizon test** (current code, logistic, 50 learners × 1,200 episodes): K plateaus after year 1; R and D
  end pinned at 0/1 (D = 1 for 68-84% of learners except rapid fade, R at a bound for 58-80%); M clipped in ~23%
  of episodes. The Centaur run shows the same cause: **D never fell in 2,280 episodes** (+0.002/episode).

## 2. Decisions this plan rests on (all 2026-09-16, yours)

| # | Decision |
|---|---|
| D1 | Phase V scenarios: traditional; scaffolding rapid fade (`immediate_withdrawal`); scaffolding no fade (`persistent`); substitution (`persistent`); free choice (logistic softmax-in-D rule, labelled an assumption). Gradual fade only on the frontier. |
| D2 | No new units: Phase V reuses the 30 units and their TRIBE patterns, with difficulty rising per year. |
| D3 | Phase V uses **soft limits** on R, D **and M** (gains shrink near 1, losses near 0; D also falls after any unaided success), behind a config switch. **Phase III keeps the brief's eq. 22/23/25**, so `centaur_main` stays consistent. |
| D4 | Forgetting follows **calendar weeks**, including **12 break weeks per year** at **1/4 of the term rate**. 3 episodes/week reproduces Phase III exactly. |
| D5 | Two diagrams: G stays eq. 39 (behavioural); a separate neural diagram covers plasticity. |
| D6 | TRIBE extras: sentence- and word-shuffled controls for **all 30 units** (done in the notebook). No reworded versions, no wrong-but-fluent texts. |
| D7 | Headline Phase V outcomes: **G, unaided accuracy, far transfer, retention after the break, help-request rate**, at years 1, 5, 10. Everything else is secondary. |
| D8 | Eq. 42 is estimated with a **unit random intercept** (difficulty and domain are constant within a unit); the paired fixed-effects bootstrap is the robustness check. |
| D9 | New dependencies allowed: `matplotlib`, `statsmodels`. |
| D10 | Claude may commit and push to `main` for this work. |
| D11 | TRIBE runs on a Colab **L4** in one session, text encoder pinned to **fp16** (faster there; the determinism check's second encoder copy fits in 24 GB; same precision as a T4 fallback). The notebook stops on another GPU and refuses to mix precisions under one tag. |
| D12 | Parcellation is **Schaefer-400** / 7 networks (was 200), to match the classmate's video notebook `01_tribe_video.ipynb`; parcel ids are identical there (left 1-200, right 201-400). |
| D13 | (2026-09-18) `centaur_main` moves to a **Colab GPU** from episode 3,571: the laptop's ~7x slowdown was RAM exhaustion (both models ~9.2 GB of shared GPU memory, up to 61k hard faults/s), which a reload does not cure. `notebooks/serve_models.ipynb` serves the same GGUF files (SHA-256 checked) with llama-server v0.4.1 behind a proxy that reproduces LM Studio's rendering (`<\|begin_of_text\|>AI:` plus a space and the transcript, captured with `lms log stream`). `scripts/compare_servers.py` PASSED before the switch: 38 captured prompts with identical token counts, median TV 0.012 (p90 0.021), argmax 100%, tutor ChatML identical 10/10; 6 approach prompts median TV 0.0115. Every call log line names its server. |
| D14 | (2026-09-18) The neural state N decays over the summer break at the same quarter of the term rate as K and M. |
| D15 | (2026-09-18) With Centaur on Colab the laptop is free, so the gate-18 pilot ran next to it. |
| D16 | (2026-09-18) Gate 18: G1 uses the brief's §10.2 wording (baseline accuracy must not fall with prior knowledge). The stricter year-1 rule planned in S8 is reported as not met: the strata converge within ~5 weeks because eq. 16 draws the learning rate independently of prior knowledge (K tends to alpha E F / (alpha E F + delta) from any start). Reported as a finding and a limitation; no model change. |
| D17 | (2026-09-18) The specification-curve ranks in `config/spec_curve.yaml` are approved as drafted from S13, before any Phase V result. |
| D18 | (2026-09-18) Centaur extension. The three assigned arms are not extended (Centaur only makes help and confidence choices there; measured on the 40 paired learners, it adds +0.07 to +0.09 help requests per episode, lowers C by 0.07-0.09, and leaves every learning outcome and every eq. 10-12 contrast unchanged). The free-choice arm is where it matters (after 7 learners: substitution 50% vs 28% under the softmax-in-D rule on the same learners), so: fit a transparent rule to Centaur's free-choice probabilities (`choice_rule.py`), validate it out of sample on a free-choice-only batch (`centaur_free_calib`: 80 new learners x 60 episodes on Colab), and add it to Phase V as a sixth scenario, `free_choice_centaur`, next to the assumed rule. |
| D19 | (2026-09-18) `--seed-offset` moves only the behavioural random stream (`Draws`); parameter draws and the learner population keep the base master seed, so §10.5 replicates differ in behaviour alone (V_behavior is identified). No existing run used an offset. |
| D20 | (2026-09-19) Three analysis rules fixed on first contact with the results, before reading any as a finding: (1) F4 judges the typical draw (the worst scenario's median near-bound share) and lists the share of draws above 10%, instead of the single most extreme draw; (2) F5 uses only the condition-label permutation, the null for a condition contrast (permuting units within a condition keeps each condition's mean text profile, so that ratio is ~1 by construction; it stays in Table 6 as a content control); (3) the variance decomposition treats scenarios as fixed (population variance of the means), which closes the decomposition (residual ~0). |

## 3. Assumptions I set (change them before the step that uses them)

Every number here is an assumption in the sense of brief §7.2 and gets that label in Table 3.

| ID | Assumption | Value | Where it is varied |
|---|---|---|---|
| A1 | Parameter draws (§9.3): every `{low, medium, high}` leaf | Triangular(min, mode = medium, max) | Uniform in falsification check F4 |
| A2 | Difficulty ramp per school year (logit) | 0.1 | Drawn from {0, 0.1, 0.2} |
| A3 | Break forgetting scale | 0.25 (D4) | 0.1 and 1.0 in the specification curve |
| A4 | Neural state half-life | 20 weeks | Drawn from {52, 20, 8}; neural diagram 4-104 |
| A5 | Eq. 33 weights | λ_A = λ_PE = λ_R = 1/3; λ_O = 1/3 | λ_O drawn from {0, 1/3, 2/3}; diagram 0-1 |
| A6 | Plasticity rate η | 1.0: N is in arbitrary units and d (eq. 44) is scale-free, so η is a pure scale | Only η = 0 matters (zero-plasticity control) |
| A7 | Winsorising of Z (§8.2) | Global 1st/99th percentiles of the 90 × 400 Z matrix | Unwinsorised in the spec curve |
| A8 | G weights and neutral band (§9.6) | 0.25 each; ε = 0.02 on the [0, 1] state scale | ε ∈ {0.01, 0.05} on the phase diagram |
| A9 | Stakeholder weights | learning-first K .4 R .3 M .2 D .1; autonomy-first K .2 R .3 M .1 D .4 | Spec curve |
| A10 | Frontier axes → knobs | e: answer-provided effort penalty `a4 × (1 − e)`; a: `support.adaptation` of both AI protocols; o: probability that an AI episode runs substitution instead of scaffolding; f: `gradual_fading` with `fade_base = 1 − f` | They are the axes |
| A11 | Phase V test outcomes | Expected probabilities over all 30 units (no sampled probes; Phase III used 3 sampled probes) | None |
| A12 | Supported accuracy | One hint, support h = 1/3 (as `simulate.checkpoint`) | None |
| A13 | Help-request rate | Model-implied P(request help when it is offered), averaged over units. The brief's "before an independent attempt" never occurs: help is only offered after a wrong answer (your earlier decision) | None |
| A14 | Efficiency proxy (§8.7) reported | Only when unaided accuracy > 0.40 | None |
| A15 | Falsification thresholds (§10.6) | A control is "similar size" at ≥ 0.5 × the substantive effect; "bound-driven" when > 10% of learners are within 0.01 of a bound | Reported with the values |
| A16 | Decay per episode | K and M: δ_i × 3 / episodes_per_week (linear, keeps Phase III identical). N: (1 − δ_N,week)^(1/episodes_per_week) | Exposure arms |
| A17 | Mediator "held at the traditional distribution" (§11.5) | The paired traditional value of the same learner, draw and episode | None |
| A18 | Stimulus variance (§10.5) | Bootstrap over the 30 units' Z (no reworded variants exist) | None |

---

## 4. Schedule

| Day | You | Claude | Laptop | Colab |
|---|---|---|---|---|
| **Wed 16** | S2 (one L4 session); S3 start after S1 | S0 (today), S1 | S1 (~1 h), then Centaur | TRIBE: all speeds + controls |
| Thu 17 | Check Centaur morning + evening | S4, S5 | Centaur | Only if S2 did not finish |
| Fri 18 | Check Centaur; copy TRIBE outputs to the laptop (S2.8) | S5 finish, S6 | Centaur | — |
| Sat 19 | Check Centaur | S6 + benchmark | Centaur (expected end: Sat evening) | — |
| Sun 20 | Review the gate-18 table (15 min) | S7, S8 | Phase V pilot | — |
| Mon 21 | Approve spec-curve ranks (15 min) | S9, S10 | Main runs (overnight) | — |
| Tue 22 | — | S11, S12, S13 runs | Runs | — |
| Wed 23 | — | S13 decomposition, S14 | Light | — |
| Thu 24 | Review outputs | S14, S15 | Light | — |
| **Fri 25** | Final OK | S15 buffer, freeze | — | — |

**Laptop rule.** Heavy Phase V runs (S9 onward) never run next to Centaur. If `centaur_main` has not finished by
**Sun 20, 22:00**, stop it with Ctrl+C (the current episode is simply redone) and resume it after the main runs.

**If we fall behind, cut in this order** (top first): stakeholder weights → §11.3 mixed model (keep the
descriptive trajectories) → spec curve reduced to one-at-a-time variations → variance decomposition without
replicate runs → exposure 1 and 5 per week → §11.5 reruns (keep only the post hoc Z mediator).
**Never cut:** TRIBE main run, Centaur completion, gate 18, the main 10-year run, Tables 4-6, Figures 5-7, the
zero-plasticity / permuted-Z / permuted-condition controls.

---

## 5. Steps

Legend: **Owner** (you / Claude) · **Type** (run / code / write / review) · **Needs** (steps that must finish first).

### S0. Housekeeping and push (Claude · code · today · 20 min)

1. Notebook: `N_CONTROL_UNITS = 30`, and the disk preflight counts the controls (+~26 GB feature cache on the runtime
   disk, +~3.4 GB outputs). **Done** in the working tree.
2. Root `CLAUDE.md`: Phase V scenario decision (done) plus a status line pointing to this plan.
3. Commit `PLAN.md`, `CLAUDE.md`, `README.md`, `notebooks/` and push to `main` (D10), so Colab clones the edit.

**Done when:** `git log origin/main -1` shows the commit.

### S1. Logistic Phase III runs (you or Claude · run · today before S3 · ~1 h CPU)

They give Phase IV real learner tables to develop against and the pairing partner for the engine comparison.
Run them **before** resuming Centaur so the two never compete for the CPU.

```powershell
uv run python -m neurotutorsim.simulate --engine logistic --tutor fake --learners 40 --episodes 30 --tag logistic_40
uv run python -m neurotutorsim.simulate --engine logistic --tutor fake --tag population_logistic
uv run python -m neurotutorsim.simulate --engine logistic --tutor fake --setting low --tag population_low
uv run python -m neurotutorsim.simulate --engine logistic --tutor fake --setting high --tag population_high
```

- `logistic_40` **must** use `--learners 40 --episodes 30`: only then are its learners the same people as in
  `centaur_main` (`make_population` redraws everyone when n changes).
- The population runs use the config's 40 episodes (1,667 × 4 arms × 40 = 266,720 episodes each), so all three
  checkpoints (episodes 9, 19, 39) exist.

**Done when:** `episodes.jsonl` has 4,800 lines (`logistic_40`) and 266,720 lines (each population run); each
summary prints `ok` for prior-knowledge monotonicity and support gap; a `run_*.json` exists per tag.

### S2. TRIBE v2 on Colab (you · run · start today · one session on an L4, paid compute units)

1. Colab → File → Open notebook → GitHub → `MatteoGuardamagna4/neurai` → `notebooks/tribe_phase2.ipynb`.
2. Runtime → Change runtime type → **L4 GPU** (D11). Standard RAM is enough (the run peaks near 2 GB).
3. Secrets (key icon), notebook access on: `HF_TOKEN` (the account must have accepted the
   `meta-llama/Llama-3.2-3B` licence on Hugging Face) and `GITHUB_TOKEN` (read access to `neurai`).
4. Configuration cell: check `RUN_TAG = "tribe_main"` and `DRY_RUN = False`. Everything else is already set for
   the L4: `READING_SPEEDS = [220, 180, 260]`, `TEXT_PRECISION = "fp16"`, `EXPECTED_GPU = "L4"`,
   `N_CONTROL_UNITS = 30`.
5. Runtime → Run all. It installs TRIBE and stops asking for a restart: Runtime → Restart session → Run all.
6. Watch for:
   - the environment cell printing an `NVIDIA L4` GPU (any other GPU stops the notebook);
   - `"reproduced": true` (official demo, gate 17);
   - the disk table with no shortfall;
   - the 220, 180 and 260 wpm arms (90 stimuli each), then 180 controls.
7. If the session drops, reconnect to an **L4** and Run all with the same tag: finished stimuli are skipped, and
   `text_encoder.json` refuses a session with a different precision. On a T4 fallback, set `EXPECTED_GPU = "T4"`
   and keep `TEXT_PRECISION = "fp16"`.
8. Copy to the laptop, into `data/processed/tribe/tribe_main/` (gitignored), from Drive
   `MyDrive/neurotutorsim/tribe/tribe_main/`: `run_metadata.json`, `tribe_qc.json`, `parcels_schaefer400.csv`,
   `controls/tribe_controls_shuffled.csv`, and for each `wpm*/`: `tribe_metrics.parquet`,
   `tribe_patterns.parquet`, `tribe_metrics_network.csv`. Skip `tribe_vertex/` and `tribe_parcel.parquet`
   (~1.7 GB per speed; not needed offline).

**Done when** `tribe_qc.json` shows: `official_demo.reproduced = true`; empty `wpm220_inference_issues`,
`wpm180_...`, `wpm260_...`; `controls.determinism.within_1e-3 = true`; empty `controls.shuffled_inference_issues`;
and `tribe_metrics.parquet` (220) has 36,000 rows with `level == "parcel"` and `metric == "auc"` (90 × 400).
**Needed by Fri 18 evening.** Durations on the L4 are not measured yet: note the per-group seconds the notebook
prints in the first minutes to estimate the total.

### S3. Resume `centaur_main` (you · run · after S1 · ~2.5 days · check twice a day)

Close heavy apps first (15.5 GB RAM, ~7 GB goes to the two models). From the repo root, in PowerShell:

```powershell
for ($i = 1; $i -le 15; $i++) {
    lms unload --all
    lms load llama-3.1-centaur-8b --context-length 8192 -y
    lms load qwen2.5-3b-instruct -y
    uv run python -m neurotutorsim.simulate --learners 40 --episodes 30 --tag centaur_main --resume
    if ($LASTEXITCODE -ne 1) { break }    # 0 = finished, 2 = refused; 1 = LM Studio failure -> reload and resume
    Start-Sleep -Seconds 60
}
```

- **Never change `--learners 40 --episodes 30 --tag centaur_main`.** There is no run log yet, so nothing would
  catch a mismatch; the run would silently blend two populations.
- If you normally set GPU offload in the LM Studio app, load the models there instead of with `lms load`.
- Progress: `(Get-Content data/processed/centaur_main/episodes.jsonl | Measure-Object -Line).Lines` → 4,800.
- Speed check (median seconds of the last 100 Centaur calls; fresh is ~8 s):
  `uv run python -c "import json,statistics as s;print(s.median([json.loads(l)['seconds'] for l in open('outputs/logs/centaur_main/calls_centaur.jsonl')][-100:]))"`
  If it is above ~20 s, press Ctrl+C and start the loop again (reload + resume; nothing is lost).
- Expected: 2,441 episodes left × ~83 s ≈ 56 h, a bit more for free choice (one extra call per episode).

**Done when:** 4,800 lines, a `run_*.json` in `outputs/logs/centaur_main/` with `n_learners: 40, n_episodes: 30`,
and `responses.csv`, `learner_state.parquet`, `checkpoints.csv` in `data/processed/centaur_main/`.

### S4. Calendar forgetting and soft limits in `learners.py` (Claude · code · Thu 17 · ~3 h)

**Files:** `config/default.yaml`, `src/neurotutorsim/learners.py`, `tests/test_learners.py`,
`tests/data/phase3_golden.json` (new).

**First, before touching `learners.py`:** write the golden fixture: learners 0-4 of `make_population(n=5)`, all four
arms, 10 episodes, `LogisticEngine` + `FakeTutor`, every `state_after` rounded to 12 decimals.

**Config (new keys):**

```yaml
updates:
  form: brief                    # brief = eq. 21-25 as written (all Phase III runs) | bounded = Phase V soft limits (D3)
calendar:                        # brief §9.1; forgetting follows calendar weeks (D4)
  weeks_per_year: 40
  break_weeks: 12
  episodes_per_week: 3           # main exposure; 1 and 5 are the §9.1 alternatives
  reference_episodes_per_week: 3 # delta_i (eq. 16) is per episode at this exposure, so Phase III is unchanged
  break_decay_scale: 0.25        # break forgetting at this fraction of the term rate (D4)
```

**Equations.** Let δ_ep = δ_i × reference / episodes_per_week and m = `m_decay_scale`. All right-hand sides use
pre-update values, and every result is clipped to [0, 1].

| State | `brief` (Phase III) | `bounded` (Phase V) |
|---|---|---|
| K | K + α E F (1 − K) − δ_ep K | same |
| M | (1 − m δ_ep) M + η_M Retr + η_C CAE | M + (η_M Retr + η_C CAE)(1 − M) − m δ_ep M |
| R | R + η_R E T − η_O Off | R + η_R E T (1 − R) − η_O Off R |
| D | D + η_D S − η_F SF IS | D + η_D S (1 − D) − η_F IS D |
| C | 1 − running Brier | same |

In the bounded D, IS (a first-try success) implies no support was used, so the "faded" factor is 1: D falls after
any unaided success under every policy (D3).

**Break** (between school years): K ← K (1 − δ_i)^(3 × 12 × 0.25) and M ← M (1 − m δ_i)^(same exponent),
i.e. (1 − δ)^9 at the defaults. R, C and D do not decay.

**Code.** One implementation of the equations, used by both the per-learner loop and Phase V:

- `step_state(K, M, R, D, alpha, delta, p, E, F, c, form="brief", delta_scale=1.0) -> dict` works on floats
  or numpy arrays (np.clip instead of `clip01`).
- `update(...)` keeps its signature and calls `step_state` with the defaults, so `run_episode` is untouched.
- `apply_break(K, M, delta, cfg) -> (K, M)`.

**Tests:**
1. The golden fixture is reproduced exactly.
2. Bounded form: 10,000 random states and proxies with rates ≤ 1 never need clipping.
3. `episodes_per_week = 3` equals the brief form; `= 1` triples the forgetting.
4. `apply_break` equals (1 − δ)^9 at the defaults.
5. Bounded D strictly decreases after IS = 1 with S = 0.

**Done when** `uv run pytest` is green.

### S5. Phase IV: `plasticity.py` (Claude · code · Thu 17 – Fri 18 · ~6 h)

**Files:** `src/neurotutorsim/plasticity.py`, `tests/test_plasticity.py`, `config/default.yaml` (block below).

```yaml
plasticity:                          # brief §8; every value an ASSUMPTION (A4-A7)
  tribe_dir: data/processed/tribe/tribe_main
  wpm: 220                           # §6.2 main; 180 / 260 robustness
  metric: auc                        # eq. 28 input; mean / peak robustness
  network_weights: area              # eq. 7 main; equal robustness
  winsorize: [0.01, 0.99]            # global percentiles of Z; null = unwinsorised robustness
  half_life_weeks: {low: 52, medium: 20, high: 8}     # delta_N,week = 1 - 0.5 ** (1 / half_life)
  eta: 1.0
  lambda: {A: 0.3333333, PE: 0.3333333, R: 0.3333334} # eq. 33, non-negative, sum to 1
  lambda_O: {low: 0.0, medium: 0.3333333, high: 0.6666667}
```

**Key design: accumulators.** N depends on the TRIBE patterns only linearly, and the 90 patterns
(30 units × 3 protocols) are fixed. So each learner carries, per channel j and stimulus k, a decayed sum
A[j, k] ← (1 − δ_N) A[j, k] + x_j · 1[k = k_t], with five channels: E, PE·Res, E·Retr, Retr, Off.
Every mechanism is then N = (w · A) @ Z:

| Mechanism | Weights w over (E, PE·Res, E·Retr, Retr, Off) |
|---|---|
| A (eq. 29) | (η, 0, 0, 0, 0) |
| B (eq. 31) | (0, η, 0, 0, 0) |
| C (eq. 32) | (0, 0, η, 0, 0) |
| D (eq. 33) | (λ_A, λ_PE, 0, λ_R, −λ_O) |

Consequences: mechanism, λ, wpm, TRIBE metric, winsorising, network weights and every Z control (permuted
units, permuted conditions, unit bootstrap) are **post hoc**, with no rerun. Only δ_N lives inside the
accumulator.

**Functions (exact):**
- `load_z(tribe_dir, wpm, metric, winsorize) -> (Z (90, 400) float64, keys [(unit_id, condition)], parcel_ids)`:
  eq. 28 per parcel over the 90 stimuli (ddof = 1), then clip at the global percentiles. Keys are sorted by
  `unit_id` × `corpus.CONDITIONS`.
- `load_networks(tribe_dir, weights) -> (W (7, 400) row-normalised, network names)`, i.e. eq. 7.
- `stimulus_index(unit_ids, protocols) -> int array` = unit position × 3 + condition position.
- `class Accumulator(n_learners, dtype=float32)`: `step(k, values (n, 5), decay)` does lazy decay (one global
  scale, `acc[rows, :, k] += values / scale`); `apply_decay(factor)`; `renormalise()` once per school year;
  `values() -> (n, 5, 90)`.
- `mechanism_weights(name, cfg) -> (5,)`; `neural_state(values, w, Z) -> (n, 400)`; `network_state(N, W) -> (n, 7)`.
- §8.7 metrics:
  - `concentration(N)`: share of Σ|N_p| held by the top quartile of parcels (100 of 400).
  - `differentiation(values, w, Z, unit_ids, concepts)`: builds per-unit state patterns (n, 30, 400), then eq. 34
    per learner via `tribe.differentiation`. Run on a subsample only.
  - `integration(sum_x, sum_xx, count)`: mean |covariance| over the 21 network pairs, from per-year running sums.
  - `efficiency(unaided, N_cont)`: NaN unless unaided > 0.40 (A14).
  - `alignment(N_net, far)`: Pearson correlation across learners.
- `apply_to_run(processed_dir, cfg)`: post hoc Phase IV on a Phase III run. It reads `learner_state.parquet`
  (condition, protocol, learner_id, time, unit_id, effort, pe, resolution, retrieval, offloading) and writes:
  - `neural_network.parquet`: every episode × 7 networks × mechanisms A-D, with columns `learner_id, condition,
    protocol, time, network, mechanism, state_value, parameter_draw = "medium"`.
  - `neural_state.parquet`: brief §4.2 columns, parcel level at the checkpoint episodes only.
- CLI: `uv run python -m neurotutorsim.plasticity --run data/processed/<tag>`.

**Tests** (synthetic Z; no TRIBE needed):
1. Eq. 28 columns have mean 0 and sd 1 before winsorising; winsorising clips exactly at the percentiles.
2. Lazy accumulator = eager eq. 29 recursion (tolerance 1e-6), including per-learner stimulus indices, breaks and
   renormalisation.
3. A-D equal direct implementations of eq. 29, 31, 32, 33.
4. η = 0 and all λ = 0 → N ≡ 0 exactly (zero-plasticity control).
5. Network aggregation equals eq. 7 on a toy parcellation.
6. Concentration: uniform → 0.25, a single parcel → 1.
7. `apply_to_run` on a tiny logistic run in `tmp_path` gives the expected row counts and join keys.

**Done when** the tests are green; on real TRIBE outputs (after S2), `apply_to_run` finishes on
`population_logistic` in < 10 min and on `centaur_main` after S3.

### S6. Phase V: `longitudinal.py` (Claude · code · Fri 18 – Sat 19 · ~12 h)

**Files:** `src/neurotutorsim/longitudinal.py`, `tests/test_longitudinal.py`, `config/default.yaml` (block below).

```yaml
phase5:                                # brief §9; D1-D4, A1-A2, A8-A10
  years: 10
  draws: 500                           # §9.3 fallback size (2,000 x 5,000 only if time allows)
  learners_per_draw: 2000
  chunk_learners: 20000                # measured numpy sweet spot on this laptop
  subsample_learners: 100              # per draw: per-learner yearly rows and accumulators kept
  central_draw: true                   # draw_id -1 = every leaf at medium (the Phase III parameterisation)
  update_form: bounded                 # D3; `brief` only in the specification curve
  distribution: triangular             # A1; `uniform` for falsification check F4
  ramp_per_year: {low: 0.0, medium: 0.1, high: 0.2}
  scenarios:                           # D1
    traditional:        {protocol: traditional,     policy: persistent}
    scaffolding_rapid:  {protocol: ai_scaffolding,  policy: immediate_withdrawal}
    scaffolding_nofade: {protocol: ai_scaffolding,  policy: persistent}
    substitution:       {protocol: ai_substitution, policy: persistent}
    free_choice:        {protocol: free_choice,     policy: persistent}
  comparator: traditional
  checkpoint_years: [1, 5, 10]
  G: {weights: {K: 0.25, R: 0.25, M: 0.25, D: 0.25}, epsilon: 0.02}
  stakeholder_weights:
    learning_first: {K: 0.4, R: 0.3, M: 0.2, D: 0.1}
    autonomy_first: {K: 0.2, R: 0.3, M: 0.1, D: 0.4}
```

**Per draw b:**

1. **Parameters.** Each `{low, medium, high}` leaf (population, curriculum, response, effort, effectiveness,
   updates, plasticity, ramp) ~ Triangular(min, medium, max), from `default_rng([master, 11, b])`. Draw −1 is all
   medium. Scenario knobs are never drawn.
2. **Population.** `learners.make_population(pcfg_b, n, seed = master * 1000 + b)` converted to arrays. The prior
   record is seeded as `seed_prior_records` does: `brier_n = 20`, `brier_sum = 20 (1 − C)`.
3. **Calendar.** Episodes per year = 40 × episodes_per_week. Unit at episode t = `curriculum_order[t mod 30]`;
   year y = t // (40 × epw); b_u = `b_slope` (difficulty − 3) + ramp × y.
4. **Common random numbers.** Per episode: U = `default_rng([master, 13, b, t]).random((13, n))` and normals from
   `[master, 14, b, t]`, identical in every scenario. Uniform slots:
   - 0: approach
   - 1: first answer
   - 2-4: help request at hint 1-3
   - 5-7: answer at hint 1-3
   - 8: substitution re-answer
   - 9: transfer
   - 10: frontier protocol mix (o)
   - 11-12: spare
   Normal slots: 0 first confidence, 1 transfer confidence. Keying on (draw, episode) makes results independent
   of chunk size.
5. **Episode step: an exact numeric mirror** of `run_episode` + `LogisticEngine` (`episode.py:116-234`,
   `engines.py:234-281`):
   1. Help cap from the policy.
   2. Protocol; free choice uses the softmax in D.
   3. First answer: p1 = logistic(θ − b + ρR + κM), first = U1 < p1.
   4. Rating = 1 + rint(4 · clip(p1 + bias + σ N0)).
   5. Intervention.
      - Substitution: depth 3, reveal, one re-answer at support h = 1.
      - Traditional and scaffolding: for k = 1..cap, while unresolved: request help if k < cap and U(1+k) < P(request);
        otherwise answer at h = k/3 using U(4+k).
      - If still unresolved at depth 3: reveal.
   6. Transfer at b + `near_b_delta`, with its own rating.
   7. Proxies exactly as `episode.py:214-224`, then `learners.effort`, `learners.effectiveness`,
      `learners.step_state(form)`.
   8. Update streak and help counts.
   9. Accumulator step with the five channels (pe = |first − p1|, resolution = correct-after-error).
6. **End of each school year:** test outcomes (A11-A13) on the pre-break state:
   - unaided, near and far accuracy (mean over the 30 units at b, b + 0.5, b + 1.2)
   - supported accuracy (+ω/3) and the support gap
   - P(request)
   - year aggregates: first-try, help and reveal rates, mean E and F, protocol shares, Brier and 10-bin ECE of
     that year's forecasts, clip counts (0 in bounded form)
   Then `apply_break` (K, M) and the neural break decay, then **retention** = unaided accuracy recomputed on the
   post-break state.
7. **Paired contrasts in the run**, for each AI scenario vs traditional, per (b, year): Δ of K, R, M, D, unaided,
   far, retention, P(request), and G = 0.25(ΔK + ΔR + ΔM − ΔD). Stored per draw: mean, median, sd, PrSup
   (share > 0), share < 0, and a 201-bin histogram on [−1, 1]. Neural, per mechanism A-D × 7 networks:
   mean, sd, d = mean / sd, PrSup.

**Outputs** under `data/processed/phase5/<tag>/` (gitignored), append-only per chunk, resumable, refusing a
changed config (same rule as `simulate.py`):

| File | One row per | Used by |
|---|---|---|
| `run.json` | run | config snapshot + sha256, seeds, sizes, package versions, wall time (§4.3) |
| `simulation_draws.parquet` | draw × scenario × year × outcome | §4.2 schema: `draw_id, scenario, year, outcome, estimate` (+ sd, median, prsup) + every drawn parameter value |
| `contrast_hist.parquet` | scenario × year × outcome × bin | learner-level distributions (Fig. 6) |
| `neural_contrasts.parquet` | draw × scenario × year × mechanism × network | Table 5, §11.4 |
| `yearly_subsample.parquet` | draw × scenario × learner (≤100) × year × {end, after_break} | Fig. 5 bands, §10.5 |
| `weekly_means.parquet` | draw × scenario × week | Fig. 5 (K, D, far accuracy, first-try) |
| `episodes_central.parquet` | draw −1, year 1: learner × scenario × episode | §11.3 model (first_correct, transfer, help, reveal, E, protocol, unit, difficulty, stratum, K, D, far accuracy) |
| `mean_accumulator_diff.npz` | draw × scenario × year {1, 5, 10}: mean ΔA (5 × 90) | exact post hoc neural contrasts for any Z (spec curve, Z controls) |
| `accumulators_subsample.npz` | draws ≤ 20 × learners ≤ 200 × scenario × year {1, 5, 10} × 5 × 90 | post hoc d / PrSup for alternative Z |
| `neural_state.parquet` | draws {−1, 0} × learners ≤ 100 × year {1, 5, 10} × 400 parcels × A-D | brief §4.2 schema |

**CLI:**

```
uv run python -m neurotutorsim.longitudinal --tag TAG [--years N] [--draws N] [--learners N] [--epw 1|3|5]
    [--form bounded|brief] [--distribution triangular|uniform] [--break-scale X] [--scenarios ...]
    [--zero-plasticity] [--zero-effort] [--frontier grid|lines|neural] [--mediate E,F,D]
    [--set key=value ...] [--seed-offset R] [--resume]
```

**Tests** (`tests/test_longitudinal.py`):
- **T1, equivalence (the key test).** Brief form, 3 per week, ramp 0, 200 learners, 30 episodes, every scenario.
  Compare the reference loop (`run_episode` + logistic engine + `FakeTutor`) with the vectorised step:
  - means at episode 29 of K, M, R, C, D
  - per-episode rates: first-try, transfer, help requests, reveals, mean E, mean F, free-choice shares
  - pass if |Δ| ≤ 4 × SE (two independent samples). Runtime ~15 s.
- T2: same seed → identical outputs; chunk size 1 vs 3 draws → identical outputs.
- T3: traditional vs a relabelled traditional → every contrast exactly 0 (CRN).
- T4: `--zero-plasticity` → every neural output exactly 0.
- T5: `--zero-effort` (a1-a4 = 0) → E ≡ logistic(a0).
- T6: bounded form, 1,200 episodes → zero clips.
- T7: retention ≤ end-of-year unaided accuracy for break scale > 0; equal when 0.
- T8: calendar episodes per year = 40 / 120 / 200 at 1 / 3 / 5 per week; the ramp is added once per year.
- T9: every drawn value lies within its [min, max]; draw −1 equals the medium config.
- T10: the expected-accuracy outcome equals a hand computation for 2 learners.

**Benchmark** (not a test): `--draws 5 --learners 2000 --years 1`. Rule: if the S9 main design extrapolates to
more than 4 h, cut `draws` to 200 (keep 2,000 learners).

### S7. Engine comparison, §10.2 (Claude · code + run · when S3 ends, ~Sun 20 · ~3 h)

In `analysis.py`: `engine_comparison(data/processed/centaur_main, data/processed/logistic_40)`.

- Pairs by (condition, learner_id).
- Outcomes:
  - first-try, transfer and reveal rates; help requests per episode
  - mean effort; K, M, R, C, D at episode 29
  - unaided and far-transfer accuracy at checkpoints 9, 19, 29
  - free-choice protocol shares (overall and by K tercile)
  - the eq. 10-12 arm contrasts within each engine
- Estimate: mean paired difference with a 95% bootstrap CI over the 40 learners (2,000 resamples).
- Write `outputs/tables/engine_comparison.csv` and `outputs/figures/figS1_engine_comparison.png`, then run
  `plasticity --run data/processed/centaur_main`.
- Caveats printed with the table:
  - Both engines take correctness from eq. 17-18; differences come only from help requests, confidence and the
    approach choice.
  - The random streams differ between engines.
  - Descriptive, no pass/fail.

### S8. One-year pilot and decision gate 18 (Claude runs · you review · Sun 20 · ~3 h)

```powershell
uv run python -m neurotutorsim.longitudinal --tag v_pilot    --years 1 --draws 50 --learners 1000
uv run python -m neurotutorsim.longitudinal --tag v_pilot_z0 --years 1 --draws 20 --learners 500 --zero-plasticity
uv run python -m neurotutorsim.longitudinal --tag v_pilot_e0 --years 1 --draws 20 --learners 500 --zero-effort
```

`analysis.gate18()` writes `outputs/tables/gate18_checks.csv` (check, rule, value, pass):

| # | Check (§10.2 / gate 18) | Pass rule |
|---|---|---|
| G1 | Prior knowledge monotone | End-of-year-1 unaided accuracy strictly increases low < medium < high, in every scenario, in ≥ 95% of draws |
| G2 | Difficulty lowers accuracy | Slope of expected accuracy on unit difficulty < 0 in 100% of draws |
| G3 | Support helps | Support gap > 0 for 100% of learner-years |
| G4 | Forgetting | Retention < end-of-year accuracy for ≥ 99% of learners; on draw −1, break lengths 4 / 12 / 24 weeks give strictly decreasing retention |
| G5 | Fading lowers dependence | Year-1 D: scaffolding_rapid < scaffolding_nofade in ≥ 95% of draws |
| G6 | Zero plasticity | Every neural contrast exactly 0 (`v_pilot_z0`) |
| G7 | Zero effort sensitivity | E constant; \|SC_K(substitution)\| smaller than in `v_pilot` |
| G8 | CRN null | Traditional vs relabelled traditional = 0 |
| G9 | No bound effects | Zero clips; < 5% of learners within 0.01 of a bound at year 1 |
| G10 | Equivalence | T1 green on the current commit |

If all pass, go to S9. If any fails, fix it, log it under §8 of this plan and rerun. **You** read the table (15 min).

### S9. Main 10-year runs (Claude · run · Sun 20 night – Mon 21 · ~3-5 h compute)

```powershell
uv run python -m neurotutorsim.longitudinal --tag v_main --years 10 --draws 500 --learners 2000
uv run python -m neurotutorsim.longitudinal --tag v_epw1 --years 10 --draws 200 --learners 1000 --epw 1
uv run python -m neurotutorsim.longitudinal --tag v_epw5 --years 10 --draws 200 --learners 1000 --epw 5
```

`v_main` ran with `--scenarios` set to the five scenarios; the sixth, `free_choice_centaur`, runs as `v_main_fcc`
(traditional + free_choice_centaur, same seed and design, so its traditional arm equals `v_main`'s) after the rule is
refitted (`scripts/run_centaur_rule.ps1`). `v_epw1` / `v_epw5` are in `scripts/run_remaining.ps1`.

**Done when** each `run.json` shows all chunks complete and `simulation_draws.parquet` has 500 (or 200) draws × 4
AI scenarios × 10 years × 9 outcomes, plus draw −1.

### S10. Frontier, tipping points, neural diagram (Claude · code + run · Mon 21 – Tue 22 · ~3 h compute)

**Phase diagram (Fig. 7a, §9.6).**
- Grid: a ∈ linspace(0.1, 1.0, 7) × e ∈ linspace(0, 1, 7), faceted by o ∈ {0, 0.5, 1}, with f = 0.
- 147 AI cells + the traditional comparator, 100 draws × 300 learners × 10 years (`--frontier grid`,
  tag `v_frontier`).
- Per cell: median over draws of mean year-10 G → beneficial (G > ε), neutral (|G| ≤ ε), harmful (G < −ε).
  Shading = share of draws beneficial. ε ∈ {0.01, 0.02, 0.05} as small multiples.

**Tipping points (§9.7).**
- One-at-a-time lines of 11 points through the scaffolding-no-fade main point, each vs traditional:
  - e ∈ [0, 1]
  - o ∈ [0, 1]
  - f ∈ [0, 1]
  - forgetting multiplier ∈ geomspace(0.25, 4), applied in both arms
- 200 draws × 300 learners (`--frontier lines`, tag `v_tipping`).
- Per draw, x* = the first grid value where mean G ≥ 0, linearly interpolated; NaN if the sign never changes.
- Report the median, 90% and 95% intervals across draws, and the share of draws with no sign change.

**Neural diagram (Fig. 7b, D5).**
- Mechanism D, substitution vs traditional, year 10.
- Axes: half-life ∈ {4, 8, 13, 20, 32, 52, 104} weeks × λ_O ∈ linspace(0, 1, 7). Colour = median d across draws,
  one panel per network.
- η is not an axis (A6).
- Behaviour is simulated once per draw, with accumulators kept for all 7 half-lives (subsample 300 learners);
  λ_O is post hoc. 100 draws (`--frontier neural`, tag `v_neural`).

**Outputs:** `frontier_grid.parquet`, `tipping_points.parquet`, `neural_diagram.parquet` in each tag folder.

### S11. Mechanism decomposition, §11.5 (Claude · run · Tue 22 · ~1.5 h compute)

`--mediate E,F,D`, tag `v_mediation`, 50 draws × 500 learners × 10 years. The traditional run keeps per-learner,
per-episode E and F in memory per chunk (25k × 1,200 × 2 × 4 B ≈ 240 MB). Each AI scenario is then rerun with one
mediator replaced by the paired traditional value (A17):

- **E, F:** replaced in the K update.
- **D:** replaced in the decision rules (help request, free-choice approach); the D state still updates.
- **Z** (post hoc): the AI protocol's Z column is replaced by the traditional one.

Contribution_m = 1 − SC_override / SC_full, for K, R, M, D, unaided, far, retention, G, and N (mechanism D, per
network), with intervals across draws. It states that the shares do not add up to 1.
Output: `outputs/tables/mechanism_decomposition.csv`.

### S12. Negative controls and falsification (Claude · code + run · Tue 22 · ~2 h)

**Table 6 controls:**

| Control (§10.3) | Implementation | Expected |
|---|---|---|
| Zero plasticity | `v_pilot_z0` + a 10-year rerun at 50 × 500 | All neural contrasts exactly 0 |
| Zero effort sensitivity | `--zero-effort`, 10 years, 50 × 500 | E constant; effort-mediated contrasts vanish |
| Permuted TRIBE across units (= irrelevant explanation) | Z rows permuted across units within condition, 200 derangements, post hoc | Concept differentiation ≈ 0; network contrasts reported as a ratio to main |
| Permuted condition labels within units | Z(u, c) ← Z(u, σ_u(c)), 200 permutations, post hoc | Neural condition contrasts shrink to the behaviour-only part |
| Sentence- / word-shuffled texts | Notebook controls, 30 units × 3 conditions | Network-metric change vs the intact condition contrast |
| Behavioural label permutation | Sign flips of paired differences within learner, 1,000 | SC centred at 0 |
| Harmless variation (reading speed) | 180 / 260 vs 220 wpm | \|condition contrast\| vs \|speed-induced change\| |

**Falsification checklist (§10.6):** `outputs/tables/falsification.csv` with columns (criterion, indicator,
threshold, value, verdict ∈ {claim allowed, no claim, not assessable}):

| F | Criterion | Indicator |
|---|---|---|
| F1 | Effects disappear after matching | `tribe.fixed_effects` network contrasts with vs without covariates (word_count, duration, readability): the 95% CI includes 0 only with covariates |
| F2 | TRIBE contrasts smaller than harmless regenerations | Reworded versions not built (D6) → **not assessable** as specified; proxy: reading-speed and sentence-shuffle changes, reported per network |
| F3 | Direction reverses across plausible plasticity models | Sign of the median year-10 d per network differs across A-D |
| F4 | Driven by parameter bounds | > 10% of learners within 0.01 of a bound at year 10, or an SC sign flip between triangular and uniform draws (50 × 500 rerun with `--distribution uniform`) |
| F5 | Negative controls as large as real effects | \|control\| ≥ 0.5 × \|substantive\| (A15) |
| F6 | Scaffolding and substitution indistinguishable after support removal | 95% interval of the year-10 SC (scaffolding_nofade − substitution) on unaided, far and retention includes 0 |

### S13. Specification curve and variance decomposition (Claude · code + run; you approve ranks · Tue 22 – Wed 23)

**Before any spec run:** Claude writes `config/spec_curve.yaml` with a plausibility rank per level; **you approve it**
(15 min); it is committed **before** results exist (§10.4).

| Dimension | Levels (rank) | How |
|---|---|---|
| Reading speed | 220 (1), 180 (2), 260 (2) | post hoc |
| Network weights | area (1), equal (2) | post hoc |
| TRIBE metric in eq. 28 | auc (1), mean (2), peak (3) | post hoc |
| Winsorising | yes (1), no (2) | post hoc |
| Plasticity mechanism | D (1), A (2), B (2), C (2) | post hoc |
| Outcome weights | equal (1), learning-first (2), autonomy-first (2) | post hoc |
| Update form | bounded (1), brief (3) | rerun |
| Forgetting | weekly, break 0.25 (1); break 0.1 (2); break 1.0 (2); per episode, no breaks (3) | rerun |
| Exposure | 3/week (1), 1 (2), 5 (2) | rerun |
| Effort function | drawn (1), fixed low arm (2), fixed high arm (2) | rerun |
| Learner engine | logistic only at year 10; hybrid appears only in the 30-episode comparison (S7) | stated |

Reruns: 2 × 4 × 3 × 3 = 72 combinations at 50 draws × 300 learners × 5 scenarios × 10 years (~2 h). Post hoc
levels multiply without cost, using `mean_accumulator_diff.npz`.

**Fig. 8**, two panels, each with specs sorted by estimate, 95% interval across draws, the indicator matrix
underneath, and colour by plausibility tier:
- year-10 G: 72 × 3 weights = 216 specs
- year-10 Δ N for the control network (Cont), substitution vs traditional: 72 × 144 = 10,368 specs

**Variance decomposition (§10.5, eq. 41),** for year-10 G and Δ N_Cont:
- Replicate runs: `v_repl0`, `v_repl1`, `v_repl2` = `--draws 50 --learners 200 --seed-offset 0|1|2`
  (`scripts/run_remaining.ps1`). The offset moves only the behaviour stream (D19), so the three share parameters and
  learners.
- Nested method-of-moments ANOVA on scenario ⊃ draw ⊃ learner ⊃ replicate gives V_scenario, V_parameters
  (between draws), V_learner and V_behavior (between replicates).
- V_plasticity: variance over mechanism × half-life × λ_O settings, post hoc.
- V_stimulus: unit bootstrap of Z, 200 resamples, post hoc (A18).
- V_residual = total − sum.
- Output: `outputs/tables/variance_decomposition.csv` (component, variance, share).

### S14. Analysis and report outputs (Claude · code · Wed 23 – Thu 24 · ~8 h)

**Files:** `src/neurotutorsim/analysis.py` (pure, tested functions), `src/neurotutorsim/report.py` (CLI that
rebuilds every table and figure from saved data), `tests/test_analysis.py`. Dependencies:
`uv add matplotlib statsmodels`. All outputs go to `outputs/tables/*.csv` and `outputs/figures/*.png` (+ `.pdf`).
Labels follow §15: "predicted cortical response", "simulated learner", "model-implied", "scenario contrast (SC)".

| Output | Content | Source |
|---|---|---|
| Fig. 1 | Pipeline: stimulus → TRIBE → learner update → plasticity → scenario (matplotlib boxes and arrows) | none |
| Fig. 2 + `corpus_balance.csv` (§11.1) | Per feature (word, character and sentence counts, readability, equations, examples, lexical diversity, duration): mean and SD per condition, SMD (eq. 3), paired TOST at ±0.10 pooled SD labelled descriptive; dot plot of SMDs with a ±0.10 band + per-unit paired differences. Semantic coverage stated as not computed | `stimuli.csv` |
| Table 1 | Conditions and fixed vs varying features | config + corpus |
| Table 2 | Model components: inputs, outputs, assumptions, validation tests | dict in `report.py` |
| Table 3 | Every parameter: low / medium / high, distribution, "assumption" or source label | config |
| Fig. 3 (§11.2) | 7 network panels: AUC per condition, paired unit lines, mean ± 95% bootstrap CI | `tribe_metrics.parquet` |
| Table 4 (§11.2) | `tribe.fixed_effects` at network level (S−T, U−T, S−U) for auc (primary), mean, peak, time_to_peak, sustained + stimulus-level entropy, dispersion, integration; BH-FDR over the 7 networks per metric × contrast. Eq. 42 with statsmodels MixedLM (D8): `auc ~ C(condition) + difficulty + C(domain) + C(network or parcel_id)`, groups = unit_id, at network (primary) and parcel level. Parcel map as a network-grouped strip plot with FDR over 400 × 3 (no brain-surface plot: no new dependency) | same |
| Fig. 4 (§6.7) | Three 30 × 30 RDMs (units ordered by concept) + `tribe.rsa` table + `tribe.differentiation` per condition | `tribe_patterns.parquet` |
| Fig. 5 (§11.3) | Year-1 weekly K, far accuracy and D per scenario, mean with a 90% band across draws; supplementary 10-year version. Model: `BinomialBayesMixedGLM` of first-try correctness ~ `bs(t, df=5):C(scenario) + C(scenario) + stratum + C(domain) + difficulty`, learner random intercept, 500 learners of draw −1; GEE fallback if the fit takes > 20 min | `weekly_means`, `episodes_central` |
| Fig. 6 | Learner-level year-10 paired differences per AI scenario × headline outcome (histograms), with median and 90 / 95% intervals across draws; years 1 and 5 as small multiples | `contrast_hist`, `simulation_draws` |
| Table 5 (§9.4-9.5, §11.4) | Scenario × headline outcome × year {1, 5, 10}: SC mean, median, 90% and 95% simulation intervals, PrSup; neural d per network (mechanism D) with intervals and PrSup | `simulation_draws`, `neural_contrasts` |
| Fig. 7 | (a) phase diagram, (b) neural diagram (D5) | S10 |
| Fig. 8 | Specification curve | S13 |
| Table 6 | Negative controls + falsification verdicts | S12 |
| Supplementary | Engine comparison, gate 18, tipping points, mechanism decomposition, variance decomposition, exposure trajectories | S7-S13 |
| `data_dictionary.csv` | Every column of every table written by the pipeline (D1 deliverable) | schemas |

**Tests:**
- SMD on toy data
- BH-FDR against a hand example
- PrSup and intervals from toy draws
- tipping-point interpolation
- the variance decomposition recovers known components on synthetic nested data
- spec-curve enumeration counts
- the MixedLM wrapper runs on synthetic data

**Done when** `uv run python -m neurotutorsim.report all` rebuilds everything above into an empty `outputs/tables`
and `outputs/figures` with no manual step.

### S15. Freeze (Claude + you · Thu 24 – Fri 25)

1. `README.md`: commands for `plasticity`, `longitudinal`, `report`; output map.
2. `CLAUDE.md` files: root status, `src/` (new modules), `config/` (new blocks), `data/` (phase5 outputs).
3. `uv run pytest` green; `uv.lock` updated; run logs untouched.
4. Brief Appendix A checklist marked done or "limitation" in the README.
5. Commit, tag `results-2026-09-25`, push.

---

## 6. Brief outputs → steps

| Brief item | Step |
|---|---|
| D3 prediction dataset, §10.1 | S2 |
| D4 learner engine results (§7.7), §10.2 comparison | S1, S3, S7 |
| §8 neural state, §8.7 metrics | S5 (post hoc), S6 (in run) |
| D5 longitudinal simulator, §9.1-9.5 | S4, S6, S9 |
| §9.6-9.7 frontier and tipping points | S10 |
| Gate 18 | S8 |
| §10.3-10.6 | S12, S13 |
| §11.1-11.5 | S14 (S11 for 11.5) |
| Figures 1-8, Tables 1-6 | S14 |

## 7. Limitations the results must state

- 30 units / 15 concepts on MBA topics, not 120 units in two domains; one TRIBE variant per stimulus (no reworded
  versions, no wrong-but-fluent texts, no audio arm), and no held-out fMRI validation.
- TRIBE sees the fixed lesson texts, never the live tutor turns.
- Centaur covers 40 learners × 30 episodes; **all of Phase V is the logistic model**, and its free-choice behaviour
  comes from an assumed rule.
- For Centaur, confidence / Brier / C track the learner's record, not calibration (decision 2026-09-11).
- Phase V deviates from the literal eq. 22, 23 and 25 (soft limits) and uses calendar forgetting; the brief form
  appears in the specification curve.
- Eq. 42 uses a unit random intercept for identification. G has no neural term (two diagrams).
- §5.4 semantic coverage and contradiction checks were not run: coverage and correctness default to 1.0 in eq. 20.
- The corpus meets the per-unit calipers (duration within 5.7%) but not the §5.5 target |SMD| < 0.10: 7 of 8 features
  miss it (scaffolding vs traditional: words and duration 0.41, sentences 0.46, lexical diversity 0.52, equations
  -1.76), because the texts vary little across units. Table 4 is therefore also reported with duration and word count
  as covariates (F1).
- Prior-knowledge differences wash out within the first ~5 weeks (D16): stratum effects are a baseline property only.
- `centaur_main` switched from LM Studio to the Colab server at episode 3,571 (D13), after an equivalence check.
- The Centaur-calibrated free-choice rule (D18) is model-implied behaviour of a model trained on human choices; it
  inherits Centaur's habit (imitation of its own recent picks), which may be partly a transcript artifact.

## 8. Log (append as we go)

- 2026-09-16: plan written; notebook controls set to 30 units; decisions D1-D10 recorded.
- 2026-09-16: notebook set up for an L4 (D11): fp16 pinned, `EXPECTED_GPU` guard, `text_encoder.json` precision lock.
- 2026-09-17: TRIBE `tribe_main` finished on the L4 (02:27 UTC); QC passes (demo reproduced, no inference issues at
  three speeds, determinism within 1e-3, 36,000 parcel AUC rows, 180 shuffled controls).
- 2026-09-18: S4 (golden fixture of 200 Phase III episodes reproduced), S5, S6 (T1 green), analysis/report layer,
  Phase I/II outputs, S10/S11 run modes. Centaur diagnosed (RAM) and moved to Colab (D13): Cloudflare's default
  QUIC connector failed with error 1033 inside Colab; `--protocol http2` registered. Remote speed ~4-15 s per episode
  (free choice needs more calls) against ~140 s locally. The first `v_*` pilot tags predate the year-0 rows and are
  superseded by `g18_*`. Gate 18 passes (D16). Spec ranks approved (D17). Centaur extension decided (D18).
  `scripts/centaur_loop.ps1`: `Start-Process` left `ExitCode` empty until the handle was cached; fixed, and the
  loop now refuses to start a second `simulate` on a running tag.
- 2026-09-18 20:39: `centaur_main` complete (4,800 episodes; run log `run_20260918_203917.json`). S7 done
  (`report engines`: `engine_comparison.csv`, Figure S1): in free choice Centaur picks substitution 44%, traditional
  31%, scaffolding 25% (the softmax-in-D rule on the same learners: 31 / 39 / 30%). Final choice rule fitted on the
  1,200 decisions (`data/processed/choice_rule/choice_rule.json`, 500 bootstrap fits): habit 0.86 [0.83, 0.90],
  payoff 0.14 [0.05, 0.23], tried 0.24, substitution +0.07 and scaffolding -0.25 vs traditional; cross-entropy
  1.033 vs 1.076 for constant shares. Plan: validate on `centaur_free_calib`, then refit on both runs for Phase V.
  Phase IV (`plasticity --run`) on `centaur_main` done. `v_main` (5 scenarios, 500 x 2,000 x 10 years) started
  20:33; `scripts/run_frontier.ps1` is chained after it (grid, lines, neural).
- 2026-09-18 23:30: `v_main` done (69 min), then `v_frontier` (36 min), `v_tipping` (28 min), `v_neural` (4 min),
  all exit 0. D19 (seed offset). `scripts/run_remaining.ps1` (S9 exposure, S11, S12 controls, S13 replicates and
  spec curve) and `scripts/run_centaur_rule.ps1` (validate, refit, `v_main_fcc`) written.
- 2026-09-19: every overnight run done and verified (draw counts, 72/72 spec runs, calib 4,800 with no gaps). S14
  Phase V report layer written (D20). First results: year-10 G vs traditional is negative for substitution (-0.20)
  and both free-choice rules, ~+0.014 for scaffolding without fading; the frontier is neutral at o = 0 and harmful
  for o >= 0.5 at any a and e; on the tipping lines G never changes sign in e, f or forgetting, and turns negative at
  o ~ 0.10 [0.06, 0.14]. Mechanisms: the scaffolding advantage runs through F (contribution 1.0), the substitution
  deficit mostly through E (0.97 of the K contrast). Falsification: F1 no claim for 3 network contrasts, F3 for 4,
  F4 no claim (scaffolding_rapid: 12% of learners near a bound in the median draw), F5 for 8 of 28, F6 claim allowed.
  Spec curve: G keeps its sign in all 216 specifications of every scenario (scaffolding positive, substitution and
  free choice negative); the control-network d of substitution does not (58% of 10,368 specifications positive; the
  tier-1 specification -0.21 [-0.74, 0.42]; mechanism A and C positive, B negative). Bug fixed before reading it:
  YAML parses the winsorize levels yes/no as booleans, so both levels had used unwinsorised Z. Variance
  decomposition: year-10 G is 68% scenario, 29% learner, 2% parameters, 1% behaviour; the control-network d is
  34% scenario, 41% plasticity mechanism, 10% parameters, 8% learner, 7% stimuli.
  Refitted choice rule (6,000 decisions, `choice_rule_fit.csv`): habit 0.84 [0.82, 0.86], payoff 0.16 [0.10, 0.21],
  tried 0.24, scaffolding -0.26 and substitution +0.05 vs traditional.

## 9. Not blocking now; decide by S15

- Whether `outputs/tables` and `outputs/figures` should be committed as the deliverable (they are gitignored today).

# Appendices

## Appendix A. Corpus validation details

### A.1 Equivalence tests for the matching features

Table A1 complements Figure 2 with the paired two one-sided tests (TOST) of Section 3.2.3. For each feature and pair
of conditions, the test asks whether the mean paired difference over the 30 units lies within ±0.10 pooled standard
deviations; a small *p* supports equivalence at that margin. The tests are descriptive diagnostics: with 30 units and
little variation across them, a large *p* reflects low power as much as imbalance, and a small *p* does not establish
that two sets of texts are interchangeable. Apart from example count, which is identical by construction and for
which the margin is therefore zero, equivalence at the 0.05 level is supported in two of the remaining 24 comparisons:
character count between scaffolding and traditional (*p* = 0.042) and equation count between substitution and
traditional (*p* < 0.001).

Table: **Table A1.** Standardised mean differences and paired equivalence tests, by feature and pair of conditions

| Feature | SMD S–T | TOST *p* S–T | SMD U–T | TOST *p* U–T | SMD S–U | TOST *p* S–U |
|---|---|---|---|---|---|---|
| Words | 0.41 | 1.000 | 0.18 | 0.933 | 0.22 | 0.980 |
| Characters | 0.02 | 0.042 | 0.18 | 0.930 | −0.16 | 0.861 |
| Sentences | 0.46 | 1.000 | −0.25 | 0.987 | 0.78 | 1.000 |
| Reading level | −0.20 | 0.928 | 0.26 | 0.997 | −0.48 | 1.000 |
| Equations | −1.76 | 1.000 | 0.03 | < 0.001 | −1.79 | 1.000 |
| Examples | 0.00 | 1.000 | 0.00 | 1.000 | 0.00 | 1.000 |
| Lexical diversity | 0.52 | 1.000 | 0.77 | 1.000 | −0.29 | 0.968 |
| Duration | 0.41 | 1.000 | 0.18 | 0.935 | 0.22 | 0.980 |
| Semantic coverage | 0.35 | 0.976 | 0.02 | 0.247 | 0.37 | 1.000 |

*S: AI scaffolding; U: AI substitution; T: traditional. Source: own elaboration; computed from the 90 primary lesson
texts (`outputs/tables/corpus_balance.csv`).*

### A.2 Texts listed for manual review of semantic coverage

The nine primary texts in the lowest decile of semantic coverage (Section 3.2.4) are listed in Table A2. All exceed
the acceptance threshold of 0.50. The review asked whether each explanation teaches the method that its unit's
reference worked solution applies, irrespective of wording.

Table: **Table A2.** Primary texts in the lowest decile of semantic coverage

| Text | Unit | Condition | Cosine |
|---|---|---|---|
| 1 | `pbp_002` | Traditional | 0.529 |
| 2 | `roi_002` | Traditional | 0.541 |
| 3 | `cm_001` | Traditional | 0.565 |
| 4 | `pbp_002` | AI substitution | 0.589 |
| 5 | `ltv_002` | AI substitution | 0.589 |
| 6 | `cac_002` | AI substitution | 0.595 |
| 7 | `ltv_002` | AI scaffolding | 0.600 |
| 8 | `pbp_002` | AI scaffolding | 0.601 |
| 9 | `ltv_002` | Traditional | 0.601 |

*Cosine similarity between the text's explanation and the unit's reference worked solution (`all-mpnet-base-v2`).
Source: own elaboration (`outputs/tables/tableS_semantic_coverage_review.csv`).*

Two features of the list bear on what the review could find. First, the scores are not extreme: averaged over the three conditions, unit coverage runs from 0.573
(`pbp_002`) to 0.786 (`dol_002`), so the lowest decile sits inside a narrow band well above the threshold of 0.50.
Second, six of the nine texts belong to two units, `pbp_002` and `ltv_002`, each appearing in all three conditions,
which locates whatever depresses the score in the unit rather than in an individual lesson. Five surface features
were tested as explanations of the ordering and none accounts for it: over the 30 units, coverage is uncorrelated
with the length of the reference worked solution (*r* = +0.30, *p* = 0.11) and with its density of numerals
(*r* = +0.27, *p* = 0.15); over the 90 texts, it is uncorrelated with the length of the explanation (*r* = +0.14,
*p* = 0.19), with its density of numerals (*r* = +0.05, *p* = 0.65) and with its equation count (*r* = −0.06,
*p* = 0.59). The first two also point the opposite way to the conjecture that a terse numeric solution depresses
similarity. What remains is the vocabulary a lesson happens to share with its reference solution, which is a
property of the measure rather than of the instruction: the threshold screens for topical relatedness and does not
establish that a lesson covers the method its reference solution applies. Reading the texts is therefore the only
way to settle the question.

Each of the nine texts was read against its unit's reference worked solution with one question: could a student who
had read only the explanation carry out the steps of that solution? For all nine the answer is yes. Each explanation
states the formula its reference solution applies and names the documented misconception as the error to avoid. The
three texts of a unit share all but three sentences of their explanation (Section 3.2.2), which is why `pbp_002` and
`ltv_002` appear in all three conditions. The reading was done once, by the author, who helped write the units and
knew the scores, so it is not an independent check: it establishes that the method is present in each text, not how
effectively the text teaches it.

### A.3 Construction and validation of the contradiction check

The contradiction check of Section 3.2.4 was specified as a screen that routes texts to manual review, never as an
acceptance criterion, and its output was used only after the check had been shown to detect texts known to be wrong.
Every reply was cached with the text and prompt that produced it, so that a change of prompt invalidates earlier
verdicts rather than reusing them, and a reply that could not be parsed was queued for review rather than passed.

**First version.** The judge model (Qwen2.5-3B-Instruct [@qwen2024], served locally) received each text with the
unit's reference answer and was asked the three questions (contradiction, unsupported assertion, causal claim) in
one prompt, in abstract form. It answered "no" to every question for all 90 primary texts. Applied to the 30
incorrect-but-fluent texts, it also answered "no" in every case, including a text stating 2,400 units where the
reference answer given in the same prompt was 6,000. A screen that never fires cannot distinguish a clean corpus from
a failure to detect, so these verdicts were discarded.

**Second version.** Two changes were made, each tested before the full pass. First, the contradiction question was
posed as extraction followed by comparison: the judge reports the final numerical answer the text arrives at and
whether it matches the reference. On a probe of four incorrect and four correct texts it classified all eight
correctly. Second, the check was made condition-aware. The scaffolding texts contain no final answer by construction;
asked anyway, the judge read off another number (for `be_001`, the misconception's 2,400 units quoted in a warning),
and all six scaffolding texts in the probe were returned as contradictions, against none in the other two
conditions. The check is therefore recorded as not applicable to scaffolding texts, neither as a pass nor as a
failure. The unsupported-assertion and causal-claim questions were posed in a separate prompt that supplies the
unit's documented misconception, so that a text warning against the misconception is not read as asserting it.

**A validation set for the other two questions.** The corpus holds texts known to state a wrong answer, which is
what validates the contradiction check, but none known to contain an unsupported assertion or an unlicensed causal
claim. Ninety were therefore written: for each of the 30 units, its traditional lesson with one sentence appended,
of one of three kinds. An *unsupported* sentence asserts a quantity or fact about the problem's scenario that the
unit never states and that cannot be derived from it, such as "The hotel also expects the new kitchen to cut its
energy bill by EUR 2,000 a year." A *causal* sentence asserts a relation the material does not license, such as
"A shorter payback period causes equipment to break down less often." A *background* sentence states standard domain
knowledge that a lesson may legitimately assert, such as "Depreciation is an accounting allocation of a cost that
has already been paid, not a payment made in the year it is charged." The third kind is the negative control, and it
matters because the one primary the judge ever flagged was flagged for a sentence of exactly that character. Each
probe is its primary text plus that one sentence, checked mechanically, so a verdict is attributable to the sentence
and to nothing else.

**Result.** Table A3 reports both blocks. The contradiction check performs as Section 3.2.4 states. The other two
questions flagged none of the 90 probes: neither the 30 carrying an unsupported assertion nor the 30 carrying an
unlicensed causal claim, a sensitivity of 0.00 in each case. Their perfect specificity on the background probes is
vacuous, since they flag nothing at all. As posed, the two questions are therefore not merely unvalidated but
inoperative, and the single primary they had flagged is withdrawn as a finding. The pattern repeats that of the
discarded first version, and the cause is plausibly the same: asked in the abstract whether a text contains a fault
of a stated kind, this model answers no. The contradiction check works because it was reposed as a concrete task,
reading off the final answer and comparing it; reposing these two in the same way is the obvious next step, which
this study did not take. The one text flagged by the unvalidated questions (`npv_002`, scaffolding) was returned
with an affirmative verdict and no reason. A check of its worked example, reference answer and leakage against the
unit record found no error, and the author, reading the whole text for any statement that the unit does not support
or that is false, found none. The flag was therefore a false positive, and the text was not changed.

Table: **Table A3.** The §5.4 judge: what was validated, and what each check found

| Question | Standing | Quantity | Texts | Value |
|---|---|---|---|---|
| Contradiction | Validated | sensitivity: incorrect-but-fluent texts flagged | 30 | 0.90 |
| Contradiction | Validated | specificity: correct texts NOT flagged | 60 | 1.00 |
| Unsupported assertion | Validated | sensitivity: probes carrying that fault flagged | 30 | 0.00 |
| Causal claim | Validated | sensitivity: probes carrying that fault flagged | 30 | 0.00 |
| Both of the above | Validated | specificity: standard background NOT flagged | 30 | 1.00 |
| Contradiction | Validated | primaries flagged | 60 | 0 |
| Unsupported assertion | Invalid | primaries flagged | 90 | 1 |
| Causal claim | Invalid | primaries flagged | 90 | 0 |
| Any check | Screen | primaries sent to manual review | 90 | 1 |

*Sensitivity and specificity are shares; findings are counts of texts. Source: own elaboration
(`outputs/tables/tableS_contradiction_judge.csv`).*

## Appendix B. The encoding-model run

### B.1 Configuration and checks

TRIBE v2 was installed from its public repository at commit `af58661` (the main branch of 23 June 2026), and its
checkpoint (`facebook/tribev2`) was verified against the SHA-256 hash published on the model hub. The released
configuration was kept except for the batch size, the number of data-loading workers and the precision of the text
encoder (16-bit floating point). Text features come from Llama-3.2-3B at relative depths 0.5, 0.75 and 1.0 of the
network, sampled at 2 Hz, and the network that maps them onto the cortical surface has 177.2 million parameters. The
run used one NVIDIA L4 GPU in Google Colab: 2.6 hours for the 90 primaries at 220 words per minute, less than 0.1
hours for the other two reading speeds, which reuse the cached text features, 5.1 hours for the 180 shuffled
controls and 5.4 hours for the 210 written controls of Section 3.2.5.

Three checks accompanied the run. First, before any lesson text, the text example distributed with the model was
run through the pipeline and returned a finite prediction of 26 time points by 20,484 vertices; the release provides
no reference output, so the check establishes that the installed pipeline runs end to end, not that it reproduces
published values. Second, one text (`be_001`, traditional) was predicted twice, and the two predictions differ by at
most 7.1 × 10⁻⁴ at any vertex and second, an effect of the reduced precision. Third, every word of every text reached
the model at all three reading speeds, and no prediction failed.

### B.2 Metric definitions

Table: **Table B1.** Metrics of the predicted cortical response

| Metric | Level | Definition |
|------------------|----------------|------------------------------------------------------------------|
| Mean | Parcel, network | Mean of $B$ over the reading window |
| Peak | Parcel, network | Maximum of $B$ after a centred three-second moving average |
| Time to peak | Parcel, network | Second at which the smoothed $B$ reaches its maximum |
| AUC | Parcel, network | Trapezoidal integral of $B$ over the reading window (eq. 8) |
| Sustained engagement | Parcel, network | Share of seconds in which $B$ exceeds the median of all the text's values at that level, an assumed baseline |
| Dispersion | Text | Variance across parcels of the window-mean pattern $\bar b_s$ |
| Entropy | Text | Normalised entropy of the positive part of $\bar b_s$ (eq. 9) |
| Integration | Text | Mean pairwise Pearson correlation of the seven network time courses |

*$B$ is the predicted BOLD response in arbitrary units, one value per second of reading; none of these metrics is a
measured response. Source: own elaboration; definitions as implemented in `src/neurotutorsim/tribe.py`.*

The entropy of text $s$ is computed on the positive part of its window-mean pattern over the $P = 400$ parcels,

$$ H_s = -\frac{1}{\ln P} \sum_{p=1}^{P} q_{s,p} \ln q_{s,p}, \qquad q_{s,p} = \frac{\max\left(\bar b_{s,p}, 0\right)}{\sum_{p'} \max\left(\bar b_{s,p'}, 0\right)}, \qquad (9) $$

and equals 1 when that part is spread evenly over the parcels and 0 when it is concentrated in one.

## Appendix C. The simulated learner

### C.1 Proxies

Every input to eq. 19–25 is computed from what happened in the episode; none is tunable. Table C1 defines them, with
$k$ the number of hints or tutor turns received (0 to 3).

Table: **Table C1.** Observable proxies of an episode

| Proxy | Definition | Enters |
|------------------|--------------------------------------------------------------|--------------------|
| Attempt | Answers given before any answer was provided, divided by 4 | $E$ (eq. 19) |
| Retrieval | 1 if the first answer was correct, 0.5 otherwise | $E$, $M$ (eq. 19, 22) |
| Generation | $1 - k/3$, or 0 if the answer was provided | $E$ (eq. 19) |
| Answer | 1 if the worked or complete solution was shown | $E$ (eq. 19) |
| Offloading | $1 -$ generation | $R$ (eq. 23) |
| Correction | 1 if a first error was corrected by a later answer before any answer was provided | $M$ (eq. 22) |
| Transfer | 1 if the near-transfer answer was correct | $R$ (eq. 23) |
| Support | $k/3$, or 1 if the answer was provided | $D$ (eq. 25) |
| Withdrawal | $1 -$ (help turns available under the support policy)$/3$ | $D$ (eq. 25) |
| Success | 1 if the first answer was correct | $D$ (eq. 25) |
| Adaptation | 0.35, 0.90 or 0.20 for the protocol that ran if $k > 0$, and 0 otherwise | $F$ (eq. 20) |
| Mismatch | $\min(1, \lvert b_u - \theta_i \rvert / 3)$ | $F$ (eq. 20) |
| Correctness, coverage | Fixed at 1 | $F$ (eq. 20) |

*Source: own elaboration; definitions as implemented in `src/neurotutorsim/episode.py`.*

### C.2 Parameters

Table C2 lists every parameter of the simulated learner; the parameters of Phases IV and V are listed with those
phases.

Table: **Table C2.** Parameters of the simulated learner

| Parameter | Symbol | Low | Medium | High | Source |
|----------------------------------|--------|---------|-------------|---------|---------------------------|
| `population.n_learners` |  |  | 1667 |  | Design |
| `population.prior_problems` |  |  | 20 |  | Assumption |
| `population.stratum_weights` |  |  | 0.3 / 0.5 / 0.2 |  | Design |
| `population.state_means.K` |  |  | 0.35 |  | Assumption |
| `population.state_means.M` |  |  | 0.3 |  | Assumption |
| `population.state_means.R` |  |  | 0.3 |  | Assumption |
| `population.state_means.C` |  |  | 0.5 |  | Assumption |
| `population.state_means.D` |  |  | 0.4 |  | Assumption |
| `population.state_sd` | $\sigma$ | 0.1 | 0.15 | 0.2 | Assumption |
| `population.stratum_k_shift` |  |  | −0.2 / 0.0 / 0.2 |  | Assumption |
| `population.stratum_m_shift` |  |  | −0.1 / 0.0 / 0.1 |  | Assumption |
| `population.mu_alpha` | $\mu_\alpha$ | −2.6 | −2.3 | −2 | Assumption; below its published range (Table 3) |
| `population.sigma_alpha` | $\sigma_\alpha$ | 0.25 | 0.4 | 0.55 | Assumption |
| `population.a_delta` | $a_\delta$ |  | 2 |  | Assumption |
| `population.b_delta` | $b_\delta$ | 120 | 80 | 50 | Assumption; below its published range (Table 3) |
| `population.theta_slope` | $\tau$ | 3 | 4 | 5 | Assumption |
| `population.confidence_bias_sd` |  | 0.05 | 0.1 | 0.15 | Assumption |
| `population.speed_sigma` |  |  | 0.25 |  | Assumption |
| `curriculum.b_slope` | $\beta_b$ | 0.4 | 0.6 | 0.8 | Assumption |
| `curriculum.near_b_delta` |  |  | 0.5 |  | Assumption |
| `curriculum.far_b_delta` |  |  | 1.2 |  | Assumption |
| `response.rho` | $\rho$ | 0.7 | 1 | 1.3 | Assumption |
| `response.kappa` | $\kappa$ | 0.5 | 0.8 | 1.1 | Assumption |
| `response.omega` | $\omega$ | 1.5 | 2.5 | 3.5 | Assumption; consistent with its published range (Table 3) |
| `response.request_intercept` |  |  | −1 |  | Assumption |
| `response.request_dependence_slope` |  |  | 2 |  | Assumption |
| `response.request_ability_slope` |  |  | 0.5 |  | Assumption |
| `response.misconception_share` |  |  | 0.67 |  | Assumption |
| `response.confidence_noise_sd` |  |  | 0.08 |  | Assumption |
| `effort.a0` | $a_0$ |  | −1 |  | Assumption |
| `effort.a1` | $a_1$ | 0.9 | 1.2 | 1.5 | Assumption |
| `effort.a2` | $a_2$ | 0.6 | 0.8 | 1 | Assumption |
| `effort.a3` | $a_3$ | 0.7 | 1 | 1.3 | Assumption |
| `effort.a4` | $a_4$ | 1.5 | 2 | 2.5 | Assumption |
| `effectiveness.f0` | $f_0$ |  | −1.5 |  | Assumption |
| `effectiveness.f1` | $f_1$ |  | 1 |  | Assumption |
| `effectiveness.f2` | $f_2$ |  | 0.8 |  | Assumption |
| `effectiveness.f3` | $f_3$ | 0.9 | 1.2 | 1.5 | Assumption |
| `effectiveness.f4` | $f_4$ | 1.2 | 1.5 | 1.8 | Assumption |
| `effectiveness.coverage_default` |  |  | 1 |  | Assumption |
| `effectiveness.correctness_default` |  |  | 1 |  | Assumption |
| `updates.m_decay_scale` |  |  | 1 |  | Assumption |
| `updates.eta_M` | $\eta_M$ | 0.01 | 0.015 | 0.025 | Assumption; no comparable published value (Table 3) |
| `updates.eta_C` | $\eta_C$ | 0.01 | 0.015 | 0.025 | Assumption |
| `updates.eta_R` | $\eta_R$ | 0.003 | 0.005 | 0.008 | Assumption |
| `updates.eta_O` | $\eta_O$ | 0.003 | 0.005 | 0.008 | Assumption |
| `updates.eta_D` | $\eta_D$ | 0.006 | 0.01 | 0.016 | Assumption |
| `updates.eta_F` | $\eta_F$ | 0.006 | 0.01 | 0.016 | Assumption |
| `support.max_hints` |  |  | 3 |  | Design |
| `support.adaptation.traditional` |  |  | 0.35 |  | Assumption |
| `support.adaptation.ai_scaffolding` |  |  | 0.9 |  | Assumption |
| `support.adaptation.ai_substitution` |  |  | 0.2 |  | Assumption |
| `support.mismatch_scale` |  |  | 3 |  | Assumption |
| `support.fade_base` |  |  | 0.75 |  | Assumption |
| `support.withdrawal_success_threshold` |  |  | 2 |  | Assumption |
| `support.latency.base_s` |  |  | 45 |  | Assumption |
| `support.latency.per_hint_s` |  |  | 20 |  | Assumption |
| `support.latency.per_attempt_s` |  |  | 30 |  | Assumption |
| `checkpoints.episodes` |  |  | 9 / 19 / 39 |  | Assumption |
| `checkpoints.n_trained` |  |  | 3 |  | Assumption |
| `checkpoints.n_near` |  |  | 2 |  | Assumption |
| `checkpoints.n_far` |  |  | 2 |  | Assumption |
| `checkpoints.retention_interval` |  |  | 10 |  | Assumption |
| `checkpoints.ece_bins` |  |  | 10 |  | Assumption |

*Low and high are the sensitivity settings of Phase III and the bounds of the triangular draws of Phase V; a parameter
with a single value is fixed. "Design" marks a value fixed by the structure of the study rather than chosen as a
behavioural assumption. Source: own elaboration (`config/default.yaml`, `outputs/tables/table3_parameters.csv`).*

### C.3 Development probes of the transcript model

The division of labour in the hybrid engine rests on probes run against the locally served model during development.
Most presented versions of the same prompt that differ in one element and compared
the model's probabilities over the response keys. The call logs are kept with the run logs, but the probe analysis is
not part of the frozen output pipeline, so the values below are development measurements rather than reproducible
outputs.

Three results shaped the design. First, on the arithmetic of these problems the model chose the correct option with
probability 0.35, within a band of 0.34 to 0.38 across prompt formats, against 1/3 for guessing, and the probability
did not respond to the competence stated in the learner's record (a change of +0.004, standard error 0.007).
Correctness is therefore drawn from eq. 17–18. Second, its confidence ratings rose with the strength of the record
(+0.866, standard error 0.022, with the same sign in all 11 units probed) but not with whether the option just
pressed was correct (+0.039, standard error 0.130, the same sign in 6 of the 11), so that confidence in the hybrid
engine measures the record, as Section 3.4 states. Third, its choice of approach did respond to the record: a record
describing a struggling rather than a coping learner changed the probability of choosing traditional instruction by
−0.187, scaffolding by +0.102 and substitution by +0.085 (standard errors 0.012 to 0.017), with the same sign in all
11 units.

Two further observations fixed the form of the prompt. The choice followed the payoff of each approach more closely
when the record stated the payoff first (+0.149, against +0.068 for the same facts ordered by frequency; standard
errors 0.018 and 0.008), which is the phrasing used. And a longer history diluted the record: with eight past
episodes in the prompt the effect of the payoff on the choice fell from +0.053 to +0.009, consistent with the
model's tendency to repeat the choices a transcript shows, so the prompt carries three.

## Appendix D. The ten-year simulation and its validation

### D.1 Runs and the trajectory model

Table D1 lists the Phase V runs analysed in this report. Each draw count includes the central draw, in which every
parameter takes its medium value; a learner-episode is one learner completing one episode in one scenario. A further
79 runs (a first pilot and a benchmark, superseded by the check runs, and 72 specification cells run before the sixth
scenario existed) are kept on disk as records and are not analysed.

Table: **Table D1.** Phase V runs analysed

| Purpose | Runs | Draws × learners | Arms | Years | Learner-episodes |
|--------------------------------|------|---------------------|------|-------|-----------------|
| Main run (Section 3.7) | 2 | 501 × 2,000 | 5 + 2 | 10 | $8.4 \times 10^{9}$ |
| Exposure of one and five episodes a week | 2 | 201 × 1,000 | 5 | 10 | $2.4 \times 10^{9}$ |
| Phase diagram | 1 | 101 × 300 | 148 | 10 | $5.4 \times 10^{9}$ |
| Tipping-point lines | 1 | 201 × 300 | 56 | 10 | $4.1 \times 10^{9}$ |
| Neural diagram | 1 | 101 × 300 | 2 | 10 | $7.3 \times 10^{7}$ |
| Mechanism decomposition | 1 | 51 × 500 | 17 | 10 | $5.2 \times 10^{8}$ |
| Controls: zero plasticity, zero effort sensitivity, uniform draws | 3 | 51 × 500 | 5 | 10 | $4.6 \times 10^{8}$ |
| Replicates for the variance decomposition | 3 | 51 × 200 | 5 | 10 | $1.8 \times 10^{8}$ |
| Specification curve (Section 3.8) | 216 | 51 × 300 | 6 | 10 | $2.4 \times 10^{10}$ |
| Behavioural and implementation checks (Appendix D.2) | 6 | 1 to 51 × 500 to 1,000 | 5 or 6 | 1 | $5.2 \times 10^{7}$ |
| **Total** | **236** | | | | $4.5 \times 10^{10}$ |

*The main run's second part adds the sixth scenario and repeats traditional instruction, whose results match the
first part to within $3 \times 10^{-16}$. The arms of the phase diagram are its 147 cells and the traditional
comparator; those of the tipping-point lines are the 33 points on the lines for $e$, $o$ and $f$, 11 pairs for the
forgetting multiplier and the comparator; those of the mechanism decomposition are the five scenarios and twelve
reruns with one mediator held. Source: own elaboration (`data/processed/phase5/*/run.json`).*

Figure 5b (Appendix E) summarises the first-year trajectories with a model of first-attempt correctness,

$$ \operatorname{logit} P\left(Y_{it} = 1\right) = \beta_0 + f_c(t) + \beta_1\,\text{stratum}_i + \beta_2\,\text{domain}_u + \beta_3\,\text{difficulty}_u, \qquad (43) $$

where $f_c(t)$ is a B-spline in the episode with five degrees of freedom, specific to scenario $c$. It is estimated as
a population-averaged logistic model with learner-clustered standard errors [@liang1986] on the first 500 learners
of the central draw, who are the same learners in every scenario. The curves average the model's predictions over
one fixed sample of 300 covariate rows, so that they show time and scenario rather than the order of the curriculum,
and their bands come from 300 draws of the coefficients. The bands reflect behavioural noise within one parameter
setting, not parameter uncertainty, which is the band of Figure 5 in Section 4.3. No p-values are reported: with simulated data the
sample size is a choice, and any difference can be made significant.

### D.2 Behavioural and implementation checks

Table: **Table D2.** Checks passed by the one-year pilot before any ten-year result was read

| Check | Rule | Value | Passed |
|----------------------------|------------------------------------------------|--------------------------------------|--------|
| Prior knowledge | Mean baseline unaided accuracy low ≤ medium ≤ high, in every scenario | 0.401, 0.553, 0.717 | Yes |
| Prior knowledge at year 1 (stricter, informational) | Year-1 unaided accuracy low < medium < high in ≥ 95% of draws | Lowest share 0.176 (scaffolding without fading); mean high − low +0.002 | No |
| Difficulty | Slope of expected accuracy on difficulty below 0 in every draw | Largest slope −0.062 | Yes |
| Support | Support gap above 0 for every learner and year | Smallest gap 0.010 | Yes |
| Forgetting | Retention below end-of-year accuracy for ≥ 99% of learners; retention falls with break length | Share 1.000; strictly falling over breaks of 4, 12 and 24 weeks | Yes |
| Fading | Year-1 dependence lower with rapid fading than without in ≥ 95% of draws | Share 1.000 | Yes |
| Zero plasticity | Every neural contrast exactly 0 | Largest absolute mean 0 over 2,352 contrasts | Yes |
| Zero effort sensitivity | Effort constant at $\sigma(a_0)$; substitution contrast in $K$ smaller than in the pilot | Effort 0.2689 throughout; 0.0069 against 0.0777 | Yes |
| Common random numbers | Traditional against a relabelled copy of itself: every contrast exactly 0 | Largest absolute contrast 0 over 189 contrasts | Yes |
| Bounds | No state clipped; below 5% of learners within 0.01 of a bound at year 1 | 0 clips; largest share 0.003 | Yes |
| Equivalence | Vectorised step reproduces the reference loop (automated test) | Passed on the analysed version of the code | Yes |

*Source: own elaboration (`outputs/tables/gate18_checks.csv`).*

### D.3 Dimensions of the specification curve

Table: **Table D3.** Dimensions, levels and plausibility ranks of the specification curve

| Dimension | Levels (rank) | Evaluation |
|---------------------|----------------------------------------------------------------|----------------------|
| Update form | Bounded (1); literal eq. 22, 23 and 25 (3) | Rerun |
| Forgetting | Break at 0.25 of the term rate (1); at 0.1 (2); at 1.0 (2); per episode, no breaks (3) | Rerun |
| Exposure | Three episodes a week (1); one (2); five (2) | Rerun |
| Effort function | Drawn (1); fixed at the low values (2); fixed at the high values (2) | Rerun |
| Adaptation | 0.35, 0.90, 0.20 as in Table 2 (1); halved, 0.42, 0.69, 0.34 (2); none, 0.48 for all (3) | Rerun; added after the first results |
| Reading speed | 220 words per minute (1); 180 (2); 260 (2) | Post hoc |
| Network weights | Surface area (1); equal (2) | Post hoc |
| Parcellation | 400 parcels (1); 200 parcels (2) | Post hoc; added after the first results |
| Response metric | Area under the curve (1); mean (2); peak (3) | Post hoc |
| Winsorising | Yes (1); no (2) | Post hoc |
| Plasticity mechanism | D (1); A, B and C (2) | Post hoc |
| Outcome weights | Equal (1); learning-first (2); autonomy-first (2) | Post hoc |

*A specification's tier is the highest rank among its levels. The ranks of the ten original dimensions were approved
before any ten-year result existed; the levels of the two added dimensions were ranked before they were computed.
Source: own elaboration (`config/spec_curve.yaml`).*

### D.4 Rules refined after the first results

Five analysis rules were changed after the first ten-year results existed, and the robustness rule was formalised.
Each is listed with its reason, so that the reader can judge whether it favours any result.

1. **F4 judges the median draw.** The share of learners near a bound is taken in the median draw of the worst
   scenario, with the share of draws above 10% listed beside it, rather than in the single most extreme of 500
   draws, which would let one draw decide the verdict.
2. **F4 names the scenarios it applies to.** A scenario that is bound-driven in its median draw is reported as such
   without withdrawing the claims of the other scenarios, as F1, F3 and F5 already did; a sign change under uniform
   draws is added to the verdict rather than replacing it.
3. **F5 uses the condition-label permutation as the null.** Permuting the predicted responses across units within a
   condition keeps each condition's mean text profile, so its ratio to the main contrast is close to 1 by
   construction. It is kept among the controls as a test of unit-specific content but does not enter F5.
4. **F6 covers both scaffolding scenarios.** The criterion concerns learners after support is removed, which is the
   rapid-fading scenario, so both scaffolding scenarios are compared with substitution rather than only the one
   without fading.
5. **The variance decomposition treats scenarios as fixed.** Their component is the population variance of the
   scenario means, which makes the components add up to the total; the residual is below 0.2% of it in absolute
   value.
6. **The robustness rule was formalised.** A scenario's direction is called robust only when the median $G$ keeps its
   sign in every specification and no 95% interval includes zero, computed from the curve rather than read from the
   figure. It was set when the first complete curve existed and is stricter than a reading of the medians alone.

### D.5 Components of the pipeline

Table: **Table D4.** Inputs, outputs, assumptions and validation of each component

| Component | Inputs | Outputs | Key assumptions | Validation |
|--------------|------------------|------------------|------------------|------------------|
| Corpus (Phase I) | 30 unit records on 15 concepts in four MBA domains | 90 lesson texts; 210 control texts; matching features | Semantic coverage reported, not entered into eq. 20 | Answer and distractor validators; section and leakage checks; duration caliper; balance table |
| Encoding model (Phase II) | Lesson text; word timing of eq. 4 at 220 words per minute (180, 260) | Predicted BOLD response per vertex; 400 parcels; 7 networks; metrics of eq. 8–9 | Text input only; fixed lesson texts, never the live tutor turns | Official example reproduced; determinism within $10^{-3}$; shuffled, reworded and incorrect-text controls |
| Simulated learner (Phase III) | Population of eq. 15–16; observable history | Choices, correctness, confidence, proxies, states of eq. 19–25 | Every parameter an assumption; Centaur makes choices only | Engine comparison; checkpoints; automated guard against latent states in prompts |
| Plasticity (Phase IV) | $Z$ of eq. 28; per-episode effort, prediction error, resolution, retrieval, offloading | Model-implied state per parcel and network (eq. 29–33) | The state is not a brain state; half-life, weights and rate assumed | Zero-plasticity null; permuted-response and permuted-condition controls |
| Ten-year scenarios (Phase V) | Triangular parameter draws; six scenarios; school calendar | States and test outcomes at years 1, 5 and 10; SC, PrSup, $G$, $d$ | Bounded updates; forgetting per week with breaks; the two free-choice rules | Checks of Table D2; mirror equivalence; common-random-number null |

*Source: own elaboration (`outputs/tables/table2_components.csv`, rewritten).*

## Appendix E. Supplementary figures

![](../outputs/figures/fig4_rdm.png)

*Section 4.1. Source: own elaboration; predicted parcel patterns of TRIBE v2 at 220 words per minute
(`outputs/tables/fig4_rdm.csv`, `rsa_condition_agreement.csv`, `rsa_differentiation.csv`).*

![](../outputs/figures/fig5b_trajectory_model_v_main.png)

*Appendix D.1, eq. 43. Source: own elaboration; model-implied output of the central draw of the Phase V main run,
500 learners in their first school year (`outputs/tables/fig5b_trajectory_model_v_main.csv`,
`tableS_trajectory_model_v_main.csv`).*

![](../outputs/figures/fig7b_neural_diagram.png)

*Section 4.7. Source: own elaboration; model-implied output of the Phase V neural-diagram run, 100 parameter draws
of 300 learners (`outputs/tables/fig7b_neural_diagram.csv`).*

![](../outputs/figures/fig8b_spec_curve_neural.png)

*Section 4.7. Source: own elaboration; model-implied output of the 216 specification-curve runs, each specification
evaluated on the stored subsample of 20 parameter draws (`outputs/tables/fig8b_spec_curve_neural.csv`).*

![](../outputs/figures/figS1_engine_comparison.png)

*Section 4.2. Source: own elaboration; the same 40 simulated learners run with the hybrid and the logistic engine,
30 episodes in each arm (`outputs/tables/engine_comparison.csv`).*

![](../outputs/figures/figS2_parcel_contrasts.png)

*Section 4.1. Source: own elaboration; predicted responses of TRIBE v2, false-discovery correction across all 1,200
parcel tests (`outputs/tables/parcel_contrasts_auc.csv`).*

![](../outputs/figures/figS3_phase3_outcomes.png)

*Section 4.2. Source: own elaboration; model-implied output of the Phase III population run, 1,667 learners in each
arm (`outputs/tables/tableS_phase3_outcomes.csv`).*

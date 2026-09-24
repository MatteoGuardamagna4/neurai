# 3. Methodology

## 3.1 Design overview and data generation

The study is a computational experiment. No data set existed on how traditional instruction, AI scaffolding and AI
substitution affect the predicted cortical response to a lesson and the long-term development of a learner, and none
could be collected within the project, so every quantity analysed here was generated for it: the instructional
material was written and validated, the cortical responses were predicted by an encoding model, and the behaviour and
development of the learners were simulated (Table 1). Figure 1 shows how the parts connect.

![](../outputs/figures/fig1_pipeline.png)

*Source: own elaboration.*

Two layers are modelled separately. The first is the immediate response to reading a lesson, predicted for an average
adult and therefore identical for every simulated learner (Phase II, Section 3.3). The second is learning: what a
learner does in each episode and how its knowledge, memory, reasoning, calibration and dependence change (Phase III,
Section 3.4), how the predicted responses of the lessons it received accumulate into a model-implied functional state
(Phase IV, Section 3.6), and how both evolve over ten years (Phase V, Section 3.7). The layers meet only in Phase IV,
where the response to each text is weighted by what the learner did with it; no step treats a predicted response as
evidence of learning.

Table: **Table 1.** Data generated for the study

| Phase | What was generated | Quantity |
|-------------------------|-----------------------------------------------|---------------------------------------|
| I. Corpus | Unit records; lesson texts; control texts | 30 units; 90 lesson texts; 210 control texts |
| II. Predicted response | Predicted BOLD response per vertex and second | 660 text predictions (931 files, 8.70 GB) |
| III. Simulated learner | Episodes of simulated learners | 814,560 episodes, of which 9,600 with the hybrid engine |
| IV. Plasticity | Model-implied functional state | One state per learner and episode, derived post hoc |
| V. Ten-year scenarios | Monte Carlo runs over ten school years | 236 runs; $4.5 \times 10^{10}$ learner-episodes |

*Source: own elaboration; counts from the run records of each phase.*

Three principles govern the design. First, contrasts are within learners: every learner runs every arm from the same
initial state, in the same curriculum order and with the same random numbers, so that a difference between arms is
not a difference between people. Second, where realism and transparency conflict, transparency prevails: the
correctness of every answer comes from an explicit equation, the language model trained on human choices makes only
the choices it was shown to make in a way that responds to the learner's record, and the full population runs on
the transparent logistic engine while the hybrid engine runs on a subsample. Third, every assumption is explicit and
varied: each parameter is documented, compared with published values where they exist (Section 3.5), drawn from a
range in Phase V and, where a modelling choice could defensibly have been made otherwise, made a dimension of the
specification curve (Section 3.8). Every long-run quantity is accordingly model-implied, and differences between
arms are reported as scenario contrasts, never as treatment effects. Equations carry the numbers they have in the
code and output tables, so their sequence has gaps.

## 3.2 Phase I: the matched educational corpus

No corpus of instructional texts matched across traditional, scaffolding and substitution regimes existed, so one was built for this study. It serves two roles. Its lesson texts are the inputs to the encoding model (Section 3.3), and its problems, distractors and hints define the episodes that the simulated learners complete (Section 3.4). Both roles require that the three versions of a unit differ in instructional policy but the concepts must match.

### 3.2.1 Curriculum and unit specification

The curriculum comprises 30 units on 15 concepts from core MBA syllabi: managerial accounting (seven concepts, among them break-even quantity, operating leverage and relevant cost), corporate finance (four: net present value, payback period, return on investment and the weighted average cost of capital), pricing (two: markup versus margin and price elasticity) and marketing analytics (two: customer lifetime value and customer-acquisition-cost payback). 
Each concept is taught twice by applying the same method to a different surface form, and the second encounter is when the learner's concept-level Experience enters the simulated record (Section 3.4). Nine concepts carry one prerequisite link. Units are ordered with prerequisites first and then by difficulty, which ranges from 1 to 4 on a five-point scale; <!-- MG:2 questions, 1 is why is it 1 to 4 and not 1 to 5, 2 is where in the codebase can i see this. -->
target completion times range from five to eight minutes. <!-- MG: where in the codebase can i see this. -->

The MBA curriculum was chosen because the population of interest is business-school students, and every answer in it
is numerical, so that each can be validated deterministically. The number of units was set by the available computing
resources: each unit requires 22 predictions of the encoding model (its three lesson texts at three reading speeds and
13 control texts, Sections 3.2.5 and 3.3), 660 for the corpus. A consequence is that every unit-level inference in
Phases II to V rests on 30 clusters, which bounds the precision of the cluster bootstrap in Section 3.3.

Each unit is a structured record containing a canonical problem, a near-transfer problem with the same structure and
changed quantities, a far-transfer problem with a different surface form and context, a documented misconception, two
distractors, a three-level hint ladder ordered from general to specific, a worked example and a worked solution.<!-- MG: where in the codebase can i see that there is the near-transfer, far-transfer, misconception, distractors, worked example and worked solution?. --><!-- MG:to add differences in traditional, scaffolding and substitution stimuli -->
Answers are stored as parameterised expressions and recomputed when the corpus is loaded; a unit whose stored answer
disagrees with its expression is rejected. Each distractor is generated by an explicit rule and re-evaluated in the
same way. In every unit one rule encodes the documented misconception and the other a second, distinct error. In unit
`npv_001`, for example, a project costs EUR 100,000 and returns EUR 72,000 at the end of each of two years at a
required return of 20%: the answer is EUR 10,000, the misconception of summing undiscounted cash flows yields
EUR 44,000, and discounting the two-year total once yields EUR 20,000. Every item is therefore a three-option choice
in which each wrong option corresponds to a named error.

### 3.2.2 Instructional conditions

Each unit exists in three versions, giving 90 lesson texts (Table 2). The versions share the unit record (the problem
and its answer options, the transfer items), the rule that no help is offered before a first independent attempt, and
most of the explanation. Each AI version departs from the traditional explanation in exactly three sentences, its
first two and its last: it opens in the tutor's voice and closes by announcing the support to come, so a median of
82% of its sentences (range 79–84%) recur verbatim in the traditional text. The conditions therefore differ in what
surrounds the explanation. The traditional version asks the learner to work the problem out and contains the unit's
three prewritten hints and its reference worked solution. The scaffolding version states that the answer will not be
given, adds three or four diagnostic questions about the learner's working and presents the same hint ladder, but
contains no worked solution. Withholding the answer until the learner has attempted the problem operationalises
scaffolding as support confined to the parts of a task the learner cannot yet complete unaided [@wood1976]. The
substitution version states that the learner need not work the problem out and omits the hints; its worked solution
adds to the reference solution three to five sentences that restate the procedure and end by telling the learner to
apply the steps exactly as shown, the regime in which retrieval and generation are offloaded to an external aid
[@risko2016].

Structure is enforced mechanically. Each version must contain exactly the sections its condition prescribes, in
order; the explanation must contain 250 to 400 words; the problem section must reproduce the canonical problem
verbatim; and the hints must match the unit's ladder. The encoding model reads the full text of each version, all sections in order<!-- MG:are we sure about this? i believe it only reads the problem and explanation. -->, whereas
the simulated learner reads only the explanation and the problem before its first attempt and receives support turn by turn
thereafter. In the scaffolding and substitution conditions those turns are generated at run time by a language-model
tutor (Section 3.4) and are never seen by the encoding model. The adaptation values in Table 2 are the per-condition
constants that enter the instructional-effectiveness term (eq. 20, Section 3.4). They are assumptions, not properties of the
texts, and Section 3.8 treats them as a dimension of the specification curve.

Table: **Table 2.** Instructional conditions and fixed versus varying features

| | Traditional | AI scaffolding | AI substitution |
|---|---|---|---|
| Lesson text | Explanation with one worked example; three hints; worked solution | Same explanation, tutor's opening and closing; three or four diagnostic questions; three hints; no worked solution | Same explanation, tutor's opening and closing; worked solution ending in an instruction to apply it; no hints |
| Support after a wrong answer | Hint *k*, then answer again or request the next hint | Tutor turn *k*: diagnosis, one question, a level-*k* hint, leakage-checked | One message with the complete solution, then one re-answer |
| Answer provided | After the third hint | After the third tutor turn | After the first wrong answer |
| Adaptation, eq. 20 (assumed) | 0.35 | 0.90 | 0.20 |
| Words, mean | 529.2 | 546.8 | 537.2 |
| Duration at 220 wpm, mean (s) | 144.3 | 149.1 | 146.5 |
| Equations, mean | 9.27 | 5.73 | 9.33 |

*Held fixed across conditions: unit, concept, domain, difficulty, problem, answer options, near- and far-transfer
items, the three-option format, the absence of help before a first attempt and all but three sentences of the
explanation. Source: own elaboration; computed from the 90 primary lesson texts (`outputs/tables/table1_conditions.csv`).*

### 3.2.3 Matching

Each lesson text $s$ is described by a vector of observable, non-pedagogical features,

$$ x_s = \left(x_{s,1}, \dots, x_{s,9}\right) \qquad (1) $$

whose nine components are the numbers of words, characters, sentences, equations and worked examples, reading
level, duration, lexical diversity and semantic coverage. Reading level is the Flesch–Kincaid grade [@kincaid1975], equations are counted as equality signs, lexical
diversity is the type–token ratio, duration is the reading time at 220 words per minute (the presentation rate of the
main encoding specification, Section 3.3), and semantic coverage is defined in Section 3.2.4. Balance on feature $k$
between an AI condition $A$ and the traditional condition $T$ is measured by the standardised mean difference

$$ \text{SMD}_k = \frac{\bar{x}_{k,A} - \bar{x}_{k,T}}{\sqrt{\left(s^2_{k,A} + s^2_{k,T}\right)/2}} \qquad (3) $$

against the conventional target $|\text{SMD}| < 0.10$ [@austin2009], complemented by paired two one-sided tests with
bounds of ±0.10 pooled standard deviations, reported in Appendix A as descriptive diagnostics rather than as evidence
of equivalence [@schuirmann1987; @lakens2017]. Matching is exact on unit, concept, domain, difficulty, modality and answer
correctness, because all three versions derive from one unit record, and caliper-based on duration: every AI version
lies within 10% of its traditional counterpart, with a maximum deviation of 7.9% (Figure 2, right). Duration is a
fixed multiple of word count, so the caliper constrains both.

![](../outputs/figures/fig2_corpus_balance.png) <!--MG: -->

*Source: own elaboration; computed from the 90 primary lesson texts (`outputs/tables/corpus_balance.csv`).*

The SMD target is met in all three pairwise comparisons for one of the nine features, example count, which is fixed
at one worked example per text by design (Figure 2, left). The failures have two sources. The first is scale. Texts
vary little across units (the standard deviation of word count is about 44 words), so the scaffolding texts' mean
excess of 17.6 words, 3.3% of the traditional mean, registers as an SMD of 0.41; duration (0.41), sentence count
(0.46), lexical diversity (0.52) and semantic coverage (0.35) exceed the target in the same comparison. The second source is structural and cannot be removed by editing. The scaffolding texts
contain no worked solution and therefore 3.5 fewer equations on average (SMD −1.76 against traditional, −1.79 against
substitution), so the scaffolding–traditional contrast is in part a contrast between a text with a worked solution and
a text without one. Section 3.3 carries this into the cortical analysis, where duration, word count and equation count
enter as covariates and a contrast that does not survive them is not interpreted (Section 3.8)<!--MG: no references to the brief-->; because duration is collinear with word count, that covariate block
spans two dimensions rather than three.

### 3.2.4 Content validation

Correctness and leakage are enforced deterministically. The unit's answer must appear in the section where the
condition permits it, the worked solution of the traditional and substitution texts, and in no other section; a
scaffolding text that states the answer anywhere is rejected. Leakage in the lesson texts is therefore zero by
construction; the tutor turns generated during the simulation are checked
separately at run time (Section 3.4).

Semantic coverage is the cosine similarity between sentence embeddings (the `all-mpnet-base-v2` model of the
Sentence-Transformers framework [@reimers2019]) of a text's explanation and the unit's reference worked solution. The
acceptance threshold of 0.50 was fixed before any similarity was computed. All 90 primary texts exceed it (minimum
0.53; condition means 0.68 to 0.70), as do all 210 control texts described in Section 3.2.5 (minimum 0.52). A
similarity threshold screens for topical relatedness rather than for method, so the lowest decile of primaries (nine
texts, six of which belong to the payback-period and customer-lifetime-value units) was also read by the author
against the reference worked solutions, in a single reading that is not independent of the texts: each explanation
teaches the method its reference solution applies, so the lower scores do not indicate missing content
(Appendix A.2). <!-- MG: not reviewed--> Near duplication across units was screened by the Jaccard similarity of word
5-gram sets [@broder1997] over all 435 pairs of traditional texts, with the threshold of 0.50 fixed before scoring.
The highest value, 0.17, belongs to the two units of one concept (`cac_001` and `cac_002`), as the paired design
implies; no pair was flagged. <!--MG: do we care about this? i think we can remove this last part about the highest value of 0.17-->

The deterministic checks establish that the correct answer is present where the condition permits it; they cannot
establish that the prose around it asserts nothing false. Every primary text was therefore screened by a second
language model, Qwen2.5-3B-Instruct [@qwen2024], different from the models used to draft the texts, <!--MG: Model used: claude opus 5; claude fable 5, we'll need to say in the future appropriate section --> for
three faults: a final answer that differs from the unit's reference answer (contradiction), an assertion the
problem's data do not support, and a causal claim the material does not license. A screen of this kind is
informative only if it detects texts known to carry the fault, so each check was tested on such texts. The
contradiction check flags 27 of the 30 incorrect-but-fluent texts of Section 3.2.5 (sensitivity 0.90) and none of
the 60 primary texts that state an answer (specificity 1.00). The other two checks detected none of the 30 faults
written into primary texts for each (sensitivity 0.00), so their verdicts are withdrawn; the one primary text they
had flagged was read by the author and contains no unsupported assertion. The corpus has therefore been screened
for contradiction of its own reference answers and for nothing else; Appendix A.3 documents the construction of the
checks and the probe texts. <!--MG: what is this whole paragraph about? i dont understand what has been done with these factual contradiction/unsupported assertion and invalid causal statement-->

### 3.2.5 Text controls

Two families of control texts were written for the encoding-model analysis only; the simulated learners never read
them. The first contains two stylistic rewordings of every primary text (180 texts, one plainer and one more formal),
which keep the sections, the stated quantities, the canonical problem and the answer placement of the primary, within
the same 10% duration caliper. They test whether a condition contrast exceeds the variation produced by harmless rewording; a contrast that
does not is not interpreted (Section 3.8). <!--MG: again, no reference to the brief we must come up with something else--> The second family
contains 30 incorrect-but-fluent traditional texts that teach the unit's documented misconception as if it were
correct: they never state the correct answer, and their worked solution reaches the misconception's answer. They serve as a content control, since a condition contrast
is not specific to pedagogy if replacing correct content with fluent incorrect content moves the predicted response
as much (Section 3.8), <!--MG: same as last comment--> and as the ground truth of the contradiction check above.
All 210 control texts pass the same structural validators as the primaries. Both families were drafted with language
models rather than by independent human authors, which may limit how far they sample the stylistic range of human-written
instruction (Section 5.4). The sentence- and word-shuffled controls, which are derived from the primaries rather than
written, are described with the encoding model in Section 3.3.

## 3.3 Phase II: predicted cortical response

No measured cortical responses to these texts exist, and Phase II predicts them with TRIBE v2 [@dascoli2026], an
encoding model trained on more than 1,000 hours of functional magnetic resonance imaging from 720 participants to
predict responses to naturalistic video, audio and language. For text, the model takes contextual features of each
word from the Llama-3.2-3B language model [@grattafiori2024] and maps them onto the 20,484 vertices of the fsaverage5
cortical surface, one predicted blood-oxygen-level-dependent (BOLD) value per vertex and second. The output is the
predicted cortical response of an average participant: one per text, identical for every simulated learner, and a
description of the immediate response to reading rather than of learning, which Phases III to V model separately.
The released model was run unchanged apart from batch size and numerical precision, with text as its only input;
Appendix B records the version, the checks on the installation and the determinism of the predictions.

**Timing.** In the released pipeline, the onsets of words presented as text come from synthesised speech. Here each
text is read at a fixed rate of $r$ words per minute, so that its $j$-th word has onset

$$ t_j = \frac{60\,(j-1)}{r} \qquad (4) $$

seconds and lasts $60/r$ seconds, and each word is encoded in the context of all the text that precedes it. The main
specification uses $r = 220$, below the meta-analytic average of 238 words per minute for adult silent reading of
English non-fiction [@brysbaert2019]; 180 and 260 are robustness variants. The sections are read in order without
their headings, which would identify the condition (a "Diagnostic questions" heading occurs only in scaffolding
texts). At 220 words per minute the texts last 132 to 188 seconds, and all 53,284 words reach the model. The encoding
model therefore reads each version in full, including the hints, diagnostic questions and worked solutions that the
simulated learner meets only after an error (Section 3.2.2).

**Aggregation.** Let $B_{s,v}(t)$ be the predicted response to text $s$ at vertex $v$ and second $t = 1, \dots, T_s$.
Each of the 400 parcels of the Schaefer atlas [@schaefer2018] takes the mean over its vertices $V_p$,

$$ B_{s,p}(t) = \frac{1}{|V_p|} \sum_{v \in V_p} B_{s,v}(t), \qquad (6) $$

and each of the seven networks of @yeo2011 (visual, somatomotor, dorsal attention, salience/ventral attention,
limbic, control and default) the mean of its parcels weighted by their surface areas $a_p$,

$$ B_{s,n}(t) = \frac{\sum_{p \in n} a_p\, B_{s,p}(t)}{\sum_{p \in n} a_p}. \qquad (7) $$

Equal weights and a 200-parcel version of the atlas are robustness variants (Section 3.8). Each time course is
summarised by five metrics and each text by three spatial ones (Appendix B). The metric carried forward is the area
under the curve,

$$ \text{AUC}_{s,k} = \sum_{t=1}^{T_s-1} \frac{B_{s,k}(t) + B_{s,k}(t+1)}{2}\,\Delta t, \qquad \Delta t = 1\ \text{s}, \qquad (8) $$

for a parcel or network $k$. Standardised per parcel over the 90 texts, it is the only channel through which a text
reaches the plasticity model (Section 3.6). Because it accumulates over the reading window, it grows with duration.

**Condition contrasts.** For a metric $m$ and unit $u$, the three contrasts are the paired differences

$$ \Delta^{S-T}_u = m_{u,S} - m_{u,T}, \qquad \Delta^{U-T}_u = m_{u,U} - m_{u,T}, \qquad \Delta^{S-U}_u = m_{u,S} - m_{u,U}, \qquad (10\text{–}12) $$

where S, U and T denote the scaffolding, substitution and traditional versions. They are estimated jointly by

$$ m_{uc} = \alpha_u + \beta_1\,\mathbb{1}[c = S] + \beta_2\,\mathbb{1}[c = U] + \gamma^{\top} x_{uc} + \varepsilon_{uc}, \qquad (13) $$

in which the unit effect $\alpha_u$ absorbs everything the three versions of a unit share and $x_{uc}$ optionally holds
the text's standardised duration, word count and equation count. Without covariates, $\hat\beta_1$ and $\hat\beta_2$
equal the mean paired differences of eq. 10 and 11, and the S–U contrast is $\beta_1 - \beta_2$; with them, the
adjustment spans two dimensions rather than three, because duration is a fixed multiple of word count. A cluster
bootstrap resamples the 30 units with all three of their versions (2,000 resamples) and gives percentile 95%
intervals. P-values computed from the bootstrap standard error are adjusted by the Benjamini–Hochberg procedure
[@benjamini1995] across the seven networks within each metric and contrast, and across all 1,200 tests of the parcel
maps. With 30 clusters, tests of this kind tend to over-reject [@cameron2008], so the p-values are read as
descriptive and the intervals as approximate. Eq. 13 conditions on the 30 units; a mixed model complements it by
treating them as a sample from the population of possible units [@judd2012]:

$$ y_{ucn} = \mu + \beta_c + \delta\, d_u + \theta_{g(u)} + a_u + \varepsilon_{ucn}, \qquad a_u \sim \mathcal{N}\left(0, \sigma^2_a\right), \qquad (42) $$

where $y_{ucn}$ is the AUC of network $n$ centred on that network's mean, $d_u$ the unit's difficulty, $\theta_{g(u)}$
the effect of its domain and $a_u$ a unit random intercept, estimated by restricted maximum likelihood. Difficulty and
domain are constant within a unit, so the unit effects of eq. 13 absorb them; eq. 42 is the model in which they can
be estimated.

**Representational geometry.** Representational similarity analysis [@kriegeskorte2008] asks whether a condition
preserves the similarity structure among the units' predicted patterns. With $\bar b_{u,c}$ the pattern of parcel
responses to unit $u$ in condition $c$, averaged over the reading window, the dissimilarity of two units is

$$ D^{c}_{uu'} = 1 - \operatorname{corr}\left(\bar b_{u,c},\, \bar b_{u',c}\right). \qquad (14) $$

Two conditions are compared by the Spearman correlation of the upper triangles of their 30 × 30 matrices, with a
permutation test that exchanges condition labels within units (1,000 permutations) and asks whether the two
geometries are less alike than exchangeable labels would make them.

**Controls.** Three families of control texts, all read at 220 words per minute, test what a contrast responds to.
The rewordings and the incorrect-but-fluent texts of Section 3.2.5 test whether a contrast exceeds the variation that
harmless rewording produces and whether it depends on correct content; Section 3.8 states the criteria. The third
family is derived from the primaries rather than written: in each section of every primary text, either the
sentences or the words are permuted, which preserves the words and the duration (180 texts). Permuting words changes
network AUC by 12.9 on average and permuting sentences by 1.5, where the standard deviation of network AUC across the
90 primaries is about 2.8: the predicted response depends on the order of words within sentences, not only on which
words are read and when.

## 3.4 Phase III: the simulated learner

Phase III simulates learners working through the corpus. Each learner is a state-space model: latent states that
every episode updates through explicit equations, with behavioural choices made by a language model trained on human
choices and the correctness of each answer drawn from an explicit response model. Every parameter is an assumption;
Table C2 in Appendix C lists them all, and Section 3.5 compares those for which a published estimate exists.

**State and population.** The state of learner $i$ is $\mathbf{s}_i = (K_i, M_i, R_i, C_i, D_i) \in [0,1]^5$:
knowledge, memory strength, independent reasoning, calibration and dependence on support. Initial states are drawn
within three prior-knowledge strata $g(i)$ (low, medium and high, with shares 0.30, 0.50 and 0.20) from a
multivariate normal distribution truncated to the unit cube,

$$ \mathbf{s}_i(0) \sim \mathcal{N}_{[0,1]^5}\left(\boldsymbol{\mu} + \boldsymbol{\Delta}_{g(i)},\ \sigma^2 \boldsymbol{\Sigma}\right), \qquad (15) $$

where the stratum shifts $\boldsymbol{\Delta}_g$ move the means of knowledge and memory and the correlation matrix
$\boldsymbol{\Sigma}$ makes knowledge, memory and reasoning covary positively with one another and negatively with
dependence. Each learner also has a learning and a forgetting rate,

$$ \alpha_i \sim \operatorname{LogNormal}\left(\mu_\alpha, \sigma_\alpha^2\right), \qquad \delta_i \sim \operatorname{Beta}\left(a_\delta, b_\delta\right). \qquad (16) $$

The population has 1,667 learners, each of whom completes all four arms (the three conditions and free choice) from
the same initial state, in the same curriculum order and with the same random numbers, which are indexed by learner
and episode but not by condition. Contrasts between conditions are therefore within learners, and the three assigned
arms comprise 5,001 learner-runs.

**The episode.** An episode presents one unit, in an order that places prerequisites first and then rises in
difficulty; the 40 episodes of a population run cover the 30 units and then the first ten again. The learner reads
the explanation and the problem and answers without help. A correct first answer leads straight to the near-transfer
question. After a wrong answer, the traditional protocol shows hint $k$ and lets the learner answer again or request
the next hint, up to three hints, after which the worked solution is shown. The scaffolding protocol replaces the
hints with up to three turns of a language-model tutor, each diagnosing the error, asking one question and giving a
hint of level $k$, and likewise shows the worked solution after the third. The substitution protocol sends one tutor
message with the complete solution and allows one further answer. Every episode ends with an unaided near-transfer
question and a statement of the time taken. In the free-choice arm the learner first reads the problem, chooses
among working through the hints alone, talking it through with the tutor and asking for the complete solution, and
then receives that protocol's lesson. The tutor is Qwen2.5-3B-Instruct [@qwen2024]. A scaffolding turn that states
the answer is regenerated once and otherwise replaced by the unit's prewritten hint; in the hybrid run described
below, none of the 909 scaffolding turns stated the answer and 728 of them (80%) asked a question, while the
substitution tutor stated the answer in 539 of its 589 messages. The tutor's text enters none of the equations that
follow: only the choice model reads it.

**Responses.** The correctness of an answer is drawn from a logistic model in the learner's ability
$\theta_i = \tau (K_i - 0.5)$, the unit's difficulty $b_u$, reasoning and memory,

$$ P(Y = 1) = \sigma\left(\theta_i - b_u + \rho R_i + \kappa M_i\right), \qquad (17) $$

$$ P(Y = 1 \mid h) = \sigma\left(\theta_i - b_u + \rho R_i + \kappa M_i + \omega h\right), \qquad (18) $$

where $\sigma$ is the logistic function, $b_u$ is linear in the unit's difficulty score, and eq. 18 applies after
support of depth $h$: $k/3$ after $k$ hints or tutor turns and 1 after the complete solution. Near- and far-transfer
items are harder by 0.5 and 1.2 logits. A wrong answer is the documented misconception with probability 0.67 and the
other distractor otherwise. When help is offered, the probability of requesting it rises with dependence and falls
with ability relative to difficulty; confidence is reported on a five-point scale.

**Effort, effectiveness and state updates.** Each episode is summarised by proxies computed from what happened in it
(Appendix C): the share of independent attempts, whether the first answer was retrieved correctly, the share of the
solution the learner generated ($1 - k/3$ after $k$ hints, and 0 if the answer was provided) and whether the answer
was provided. Effort and instructional effectiveness are

$$ E = \sigma\left(a_0 + a_1\,\text{attempt} + a_2\,\text{retrieval} + a_3\,\text{generation} - a_4\,\text{answer}\right), \qquad (19) $$

$$ F = \sigma\left(f_0 + f_1\,\text{correctness} + f_2\,\text{coverage} + f_3\,\text{adaptation} - f_4\,\text{mismatch}\right), \qquad (20) $$

where the correctness and coverage of the lesson are fixed at 1 (the coverage measured in Section 3.2.4 is reported,
not fed into the model), mismatch is the distance between difficulty and ability, and adaptation is the constant of
the protocol that ran (Table 2), applied when support was used. The states then update as

$$ K' = K + \alpha_i E F (1 - K) - \delta_i K, \qquad (21) $$

$$ M' = (1 - \delta_i)\, M + \eta_M\,\text{retrieval} + \eta_C\,\text{correction}, \qquad (22) $$

$$ R' = R + \eta_R\, E\,\text{transfer} - \eta_O\,\text{offloading}, \qquad (23) $$

$$ C = 1 - \frac{1}{n} \sum_{j=1}^{n} \left(c_j - y_j\right)^2, \qquad (24) $$

$$ D' = D + \eta_D\,\text{support} - \eta_F\,\text{withdrawal} \times \text{success}, \qquad (25) $$

each clipped to $[0,1]$. Correction marks an initial error that the learner corrected without being given the
answer, transfer a correct near-transfer answer, offloading the share of the solution not generated, support the
depth of help used, withdrawal the share of help removed by the support policy and success a correct first answer;
$C$ is one minus the Brier score of the confidence ratings $c_j$, rescaled to $[0,1]$, against correctness $y_j$ over
all rated answers so far. Two features of these equations carry the comparison between conditions. Effort and
effectiveness multiply in the knowledge gain, so substitution, which provides the answer after the first error,
lowers learning through effort. And in these equations adaptation is the only term that distinguishes scaffolding
from traditional instruction: the scaffolding advantage is an assumed constant, not a consequence of the tutor's
text, and Section 3.8 treats it as a dimension of the robustness analysis.

**Who makes the choices.** Two engines implement the model. The logistic engine makes every decision by equation:
correctness by eq. 17–18, help requests by the model above, confidence as the probability of being correct plus a
learner-specific bias and noise, and the approach in the free-choice arm by an assumed softmax in dependence, whose
logits are $s(D - 0.5)$ for substitution, $-s(D - 0.5)$ for traditional instruction and 0 for scaffolding, with
$s = 2$ the dependence slope of the help-request model. The
hybrid engine leaves correctness to eq. 17–18 and delegates the behavioural choices (the approach, requests for
further help and confidence ratings) to Centaur [@binz2025], a language model fine-tuned to predict the next choice in
transcripts of psychological experiments (more than 10 million choices by more than 60,000 participants in 160
experiments), used here in its 8-billion-parameter version, quantised to about four bits per weight for serving. The
division follows from what such a model can and
cannot do. In probes run during development, Centaur answered these problems correctly with probability 0.35,
against 1/3 for guessing, and its confidence ratings followed the learner's record rather than the answer just
given, whereas its choices of approach and of help shifted with the record in the direction a struggling or a coping
learner would take (Appendix C). The model reads an observable transcript only: a fixed instruction, the current
episode, a summary of the learner's record (problems solved on the first try, hints requested, recent form,
experience with the concept and, in the free-choice arm, how often each approach was followed by a correct transfer
answer) and the three previous episodes. Latent states never enter the prompt, which is checked automatically; the
initial state reaches it as the record of 20 prior problems whose counts eq. 17 and the help-request model imply.
Each choice is sampled from the model's probabilities over the response keys with the learner's random-number
stream, and option letters and order are drawn afresh in every episode. Because the confidence ratings follow the
record, wherever the hybrid engine is used $C$, and the Brier score and calibration error computed from the same
ratings, measure consistency with the record rather than calibration.

**Runs.** The logistic engine runs the full population: 1,667 learners in 4 arms for 40 episodes, 266,720 episodes
per parameter setting, in the three settings of Table C2 (low, medium and high; medium is the main specification).
Each hybrid episode needs several calls to an
8-billion-parameter model (about 4 seconds per assigned-arm episode on a cloud GPU), so the hybrid engine runs a
subsample of 40 learners in
all four arms for 30 episodes (4,800 episodes), paired with the logistic engine on the same learners for the engine
comparison of Section 4.2, and 80 further learners in the free-choice arm alone (4,800 episodes), whose choices fit
the second free-choice rule of Phase V (Section 3.7). In the logistic runs the free-choice arm therefore follows the
assumed softmax, not Centaur. Phase III comprises 814,560 simulated episodes in all. After the 10th and 20th episodes
and at the end of each run, a checkpoint tests every learner with support removed and without changing its state:
unaided accuracy on recently practised items, near and far transfer, retention of items last practised at least ten
episodes earlier, the support gap (eq. 26: accuracy with one hint minus unaided accuracy), calibration, and the rate
of help requests.

## 3.5 Parameter provenance and calibration anchors

No data set exists from which the parameters of Section 3.4 could be estimated, so they were set by assumption, and
the provenance of each is recorded with the code (`config/parameter_sources.yaml`). Where the literature reports a
quantity that the model also implies on the same scale, the two were compared once the runs were complete
(Table 3). The comparison documents the model rather than calibrating it: no value was changed in response, because
re-parameterising would have invalidated every completed run, and a parameter outside its published range is
reported as a finding about the model.

Three parameters could be compared directly. The learning rate enters eq. 21 through the gain
$\alpha_i E F (1 - K)$, which closes a fraction of the remaining gap to mastery at each episode, the same form as the
per-opportunity learning probability of Bayesian knowledge tracing [@corbett1995], commonly initialised between 0.10
and 0.22 [@badrinath2021]. In the reference run the realised fraction, the median learning rate times the mean effort
and effectiveness ($0.100 \times 0.655 \times 0.527$), is 0.035, below that range. The forgetting rate implies that
0.38 of knowledge survives a year without practice at the rate the simulation applies during breaks, against the
two-thirds to three-quarters of taught knowledge retained after a year in the review of @custers2010. The support
weight $\omega$, expressed as the support gap at the checkpoints standardised by the spread of unaided accuracy,
gives an effect of $d = 0.41$, inside the range of 0.35 to 0.76 spanned by meta-analyses of tutoring
[@ma2014; @kulik2016; @vanlehn2011]. A fourth parameter, the memory gain from retrieval, has a published
counterpart in the testing effect [@rowland2014; @adesope2017], a retention advantage of $g$ = 0.50 to 0.61, but no
model quantity on the same scale, because memory strength enters accuracy only through $\kappa M$ in eq. 17; it is
recorded without a comparison.

The two rates that fall outside their ranges err in the same direction, and together they set the plateau of
eq. 21: at constant effort and effectiveness, knowledge settles at $K^{*} = \alpha E F / (\alpha E F + \delta)$,
which is 0.59 with the model's rates and 0.99 with the midpoints of the published ranges. The simulated learner
therefore operates in a forgetting-dominated regime that the evidence on taught knowledge does not support. The
consequence for interpretation is specific: scenario contrasts that operate through forgetting are magnified in such
a regime, and the substitution deficit, which arises from low effort compounded by forgetting (Section 4.5), is one of
them. Its direction is the claim; its magnitude is read as an upper bound (Section 5.1).

Table: **Table 3.** Calibration anchors: model-implied quantities against published values

| Quantity | Parameter | Model | Published | Verdict | Source |
|----------------------------------|----------|-------|----------|------------|---------------------------|
| Share of the gap to mastery closed per episode | $\alpha$ | 0.035 | 0.10–0.22 | Below | @corbett1995; @badrinath2021 |
| Share of knowledge retained after a year without practice | $\delta$ | 0.38 | 0.65–0.75 | Below | @custers2010 |
| Effect of support on test accuracy (Cohen's $d$) | $\omega$ | 0.41 | 0.35–0.76 | Consistent | @ma2014; @kulik2016; @vanlehn2011 |
| Retention advantage of retrieval practice (Hedges' $g$) | $\eta_M$ | — | 0.50–0.61 | Not comparable | @rowland2014; @adesope2017 |
| Steady-state knowledge of eq. 21 | $\alpha$, $\delta$ | 0.59 | 0.99 | Below | Derived from the first two rows |

*Model values from the reference run in the medium setting. The published range for $\omega$ spans three
meta-analyses that disagree by more than a factor of two. Source: own elaboration
(`outputs/tables/tableS_parameter_anchors.csv`).*

## 3.6 Phase IV: plasticity

Phases II and III leave two separate objects: a predicted response to each text, identical for every learner, and a
record of what each learner did. Phase IV joins them in a model-implied functional state that accumulates the
responses to the lessons a learner actually received, weighted by what the learner did in them. The state is in
arbitrary units and is not a prediction of a future brain state: it re-weights the predicted responses of Phase II by
the simulated behaviour of Phase III, inherits the limits of both, and is interpreted only through standardised
contrasts between scenarios (Section 3.7).

The response to text $s$ in parcel $p$ enters as its area under the curve standardised across the 90 texts,

$$ Z_{s,p} = \frac{\text{AUC}_{s,p} - \overline{\text{AUC}}_{p}}{\operatorname{sd}_{p}\left(\text{AUC}\right)}, \qquad (28) $$

winsorised at the 1st and 99th percentiles of all 36,000 values, so that $Z$ records which parcels a text drives more
or less than the corpus average. It is the response to the whole text of the protocol that ran, including sections
that the learner reached only after an error or not at all. With $s_t$ the text of episode $t$, $\delta_N$ a decay per
episode and $\eta$ a common rate, mechanism A, activation accumulation, adds the text's pattern in proportion to
effort:

$$ \mathbf{N}_i(t) = \left(1 - \delta_N\right) \mathbf{N}_i(t-1) + \eta\, E_{it}\, \mathbf{Z}_{s_t}. \qquad (29) $$

Mechanisms B and C keep this form and replace effort by another weight: for prediction-error learning, the error of
the first answer, $\text{PE}_{it} = \lvert Y_{it} - P(Y_{it} = 1) \rvert$ (eq. 30), counted only when the learner then
resolved it without being given the answer (eq. 31); for effort-dependent learning, effort times retrieval (eq. 32).
The hybrid mechanism D, the main specification, combines the three and penalises offloading,

$$ \mathbf{N}_i(t) = \left(1 - \delta_N\right) \mathbf{N}_i(t-1) + \eta \left(\lambda_A E_{it} + \lambda_{PE}\, \text{PE}_{it}\, \text{res}_{it} + \lambda_R\, \text{retr}_{it} - \lambda_O\, \text{off}_{it}\right) \mathbf{Z}_{s_t}, \qquad (33) $$

with $\lambda_A = \lambda_{PE} = \lambda_R = 1/3$ and $\lambda_O = 1/3$ (0 and 2/3 in the low and high settings). The
decay follows from a half-life of 20 weeks (8 and 52 weeks in the other settings), which at three episodes a week
gives $\delta_N = 1 - 0.5^{1/60} \approx 0.011$. Because $\mathbf{N}$ is in arbitrary units and the contrasts of
Section 3.7 are standardised, $\eta = 1$ fixes only the scale, and $\eta = 0$ serves as the control in which no
plasticity occurs. Parcel states are aggregated to the seven networks with the area weights of eq. 7.

The recursion is linear in the 90 fixed patterns, which is what makes Phase IV cheap to vary. Each learner carries
five decayed sums per text, one for each behavioural input (effort, resolved prediction error, effort times
retrieval, retrieval and offloading), and the state under any mechanism is a weighted projection of those sums onto
$\mathbf{Z}$. The mechanism, its weights, the response metric, the reading speed, the parcellation and any permutation
of $\mathbf{Z}$ can therefore be changed after the simulation without rerunning it; only the decay acts inside the
recursion.

Five quantities describe the state of a learner: its concentration, the share of $\lvert \mathbf{N} \rvert$ held by
the top quarter of parcels; its representational differentiation,

$$ \text{Diff}_i = \overline{D}^{\,\text{between}}_i - \overline{D}^{\,\text{within}}_i, \qquad (34) $$

the mean dissimilarity (eq. 14) between the state patterns of units that teach different concepts minus that between
units teaching the same concept; its cross-network integration, the mean absolute covariance between network states
across episodes; an efficiency proxy, unaided accuracy per unit of control-network state, computed only when
accuracy exceeds 0.40; and, across learners, the alignment of each network's state with far-transfer accuracy.

## 3.7 Phase V: ten-year scenarios

Phase V projects the simulated learner over ten school years under six instructional scenarios and propagates
parameter uncertainty by Monte Carlo simulation. It introduces no new material: the 30 units and their predicted
responses recur, with difficulty rising <!--MG: how are we raising the difficulty in practice?-->from year to year. Its outputs are scenario contrasts under stated
assumptions, not forecasts of any learner's development. The episode is that of Section 3.4 with the logistic
engine, implemented as a vectorised numerical mirror that updates arrays of learners at once; an automated test
requires it to reproduce the state means and per-episode rates of the reference loop within four standard errors.
Centaur's behaviour therefore reaches Phase V only through the fitted choice rule described below.

**Calendar and forgetting.** A school year has 40 instructional weeks of three episodes (one and five a week are
exposure variants), followed by a 12-week break without practice. Units recur in curriculum order with unchanged texts
and problems; what rises is the difficulty term $b_u$ of eq. 17, raised for every unit by 0.1 logits per completed
school year in the main specification (drawn between 0 and 0.2), so that the same problem is answered correctly less
often as the years pass. The per-episode
forgetting rate of eq. 16 is rescaled so that forgetting per week does not depend on exposure, and during the break
knowledge, memory and the neural state of Section 3.6 decay at a quarter of the term rate (design choice, assumption). Losses of achievement over
long breaks are documented [@cooper1996]; the rate applied here is an assumption, varied in Section 3.8.

**Bounded updates.** Eq. 22, 23 and 25 have no saturating term, so over 1,200 episodes they would push memory,
reasoning and dependence against the bounds of $[0,1]$, where clipping rather than the model would set the state.
Phase V scales each gain by the distance to 1 and each loss by the distance to 0,

$$ M' = M + \left(\eta_M\,\text{retrieval} + \eta_C\,\text{correction}\right)(1 - M) - \delta_i M, \qquad (22') $$

$$ R' = R + \eta_R\, E\,\text{transfer}\,(1 - R) - \eta_O\,\text{offloading}\; R, \qquad (23') $$

$$ D' = D + \eta_D\,\text{support}\,(1 - D) - \eta_F\,\text{success}\; D, \qquad (25') $$

so that dependence also falls after any correct first answer, which was given without support, and not only when the
support policy has withdrawn help. The literal equations are a level of the specification curve.

**Scenarios.** Each scenario combines a protocol with a policy for the persistence of support. Traditional
instruction, scaffolding without fading and substitution keep support available in every episode. Scaffolding with
rapid fading withdraws all help once the learner has answered two consecutive problems correctly at the first
attempt and restores it after the next error, so that in a withdrawn episode a wrong first answer is followed by
neither hints nor the solution. Withdrawal as competence grows is part of the definition of scaffolding
[@wood1976; @puntambekar2005]; without it, the tutor's support becomes permanent. In the two remaining scenarios the
learner chooses the protocol at every problem, by the softmax in dependence of Section 3.4, an assumption, or by a
rule fitted to Centaur's choices. The fitted rule is a conditional logit over the three approaches whose inputs are
only what Centaur reads in its prompt: the share of each approach among the last three choices, the rate at which
each was followed by a correct transfer answer, whether it has been tried, and recent first-attempt form. Fitted to
Centaur's probabilities in the 1,200 free-choice decisions of the hybrid run, it predicted the 4,800 decisions of the
separate free-choice batch with a cross-entropy of 1.041, against 1.080 for constant shares, and matched Centaur's
most probable choice in 70% of them; it was then refitted on all 6,000, and each parameter draw uses one bootstrap
replicate of the fit. Gradual fading is not a named scenario; it enters the frontier below.

**Monte Carlo design.** In each draw $b$, every parameter with a low, medium and high value in Table C2 is drawn
from a triangular distribution with its mode at the medium value and its bounds at the other two,

$$ \Theta^{(b)} \sim p(\Theta), \qquad Y^{(b)} = \text{Simulate}\left(\text{scenario}, \Theta^{(b)}, \text{seed}_b\right), \qquad (35) $$

a population is drawn from eq. 15–16, and every scenario runs on it from the same initial states. The random numbers
are indexed by draw, episode and learner but not by scenario, the method of common random numbers
[@glasserman2003], so each contrast compares the same learner meeting the same random events under two scenarios. The quantities that define a
scenario, including the adaptation constants of Table 2, are not drawn. The main run has 500 draws of 2,000 learners
and a central draw with every parameter at its medium value.

**Outcomes and contrasts.** At the end of years 1, 5 and 10 the run records $K$, $M$, $R$ and $D$ and four test
outcomes, computed with support removed as expected probabilities over all 30 units at that year's difficulty:
unaided accuracy, far-transfer accuracy, the probability of requesting help when it is offered, and retention, the
unaided accuracy recomputed after the break. Being expected rather than sampled, they are not comparable with the
checkpoint accuracies of Phase III. For outcome $Y$ in year $t$, the scenario contrast of an AI scenario in draw $b$
is the mean paired difference from traditional instruction,

$$ \text{SC}^{(b)}_Y(t) = \frac{1}{n} \sum_{i=1}^{n} \left(Y^{\text{AI}}_{i,t} - Y^{\text{T}}_{i,t}\right), \qquad (37) $$

summarised by its mean and median across draws with equal-tailed 90% and 95% simulation intervals. The probability of
superiority, $\text{PrSup}_Y(t) = \Pr(Y^{\text{AI}}_{i,t} > Y^{\text{T}}_{i,t})$ (eq. 38), is the share of paired
learners, pooled over draws, for whom the AI scenario is ahead [@mcgraw1992]; ties count as not superior, and their
share is reported beside it. The summary outcome is the net advantage

$$ G = w_K\,\Delta K + w_R\,\Delta R + w_M\,\Delta M - w_D\,\Delta D, \qquad (39) $$

with equal weights of 0.25 in the main specification. A contrast is beneficial if $G > \varepsilon$, harmful if
$G < -\varepsilon$ and neutral otherwise, with $\varepsilon = 0.02$ on the unit scale of the states (0.01 and 0.05 as
variants). $G$ has no neural term; the neural contrast is the standardised paired difference of a network's state
under mechanism D, computed per draw and reported separately,

$$ d_{n,t} = \frac{\operatorname{mean}_i\left(N^{\text{AI}}_{i,t,n} - N^{\text{T}}_{i,t,n}\right)}{\operatorname{sd}_i\left(N^{\text{AI}}_{i,t,n} - N^{\text{T}}_{i,t,n}\right)}. \qquad (44) $$

**Frontier and tipping points.** The frontier replaces the named scenarios by an AI protocol with four continuous
parameters: its adaptation $a$ (0.1 to 1.0); the retained effort $e$, which scales the effort penalty for a provided
answer to $a_4(1 - e)$; the probability $o$ that an AI episode runs substitution rather than scaffolding; and fading
$f$, under which a learner on a streak of $k$ first-attempt successes has $\lceil 3(1 - f)^{k} \rceil$ help turns. The
phase diagram crosses seven values of $a$ with seven of $e$ at $o \in \{0, 0.5, 1\}$ and $f = 0$ and classifies each
of the 147 cells by the median of $G$ across draws. Tipping points are located on lines of 11 values through the
scaffolding-without-fading scenario, varying one of $e$, $o$, $f$ or a multiplier of all forgetting rates (0.25 to
4, applied to both arms). In each draw the tipping point is the first value at which $G$ changes sign,

$$ x^{*} = \inf\left\{x : \operatorname{sign} G(x) \neq \operatorname{sign} G(x_0)\right\}, \qquad (40) $$

with $x_0$ the start of the line, interpolated linearly and summarised by its median, its simulation intervals and
the share of draws without a sign change. A second diagram crosses the half-life of the neural state (4 to 104 weeks)
with the offloading weight $\lambda_O$ of eq. 33 for the neural contrast of substitution.

**Mechanism decomposition.** Each AI scenario is rerun with one mediator held, for every learner and episode, at the
value the same learner had under traditional instruction: effort or effectiveness in the knowledge update, or
dependence in the decision rules; the text's predicted response is exchanged post hoc for the traditional one. A
mediator's contribution is $1 - \text{SC}_{\text{held}} / \text{SC}$. It decomposes the contrast within the model, is
not a causal mediation analysis, and the contributions need not sum to one. Appendix D lists every Phase V run, with
its size, and gives the trajectory model of Figure 5 (eq. 43); the 236 runs analysed simulate
$4.5 \times 10^{10}$ learner-episodes.

## 3.8 Validation, falsification and robustness

Four questions precede any claim: whether the simulated learner behaves as a learner model must, whether a contrast
responds to what it is said to respond to, whether it survives the modelling choices that could defensibly have been
made otherwise, and where its uncertainty comes from. The six criteria at the end of this section state when no claim
is made.

**Behavioural checks.** Before any ten-year result was read, a one-year pilot had to pass ten checks (Table D2).
Five are properties that any model of learning should have: baseline accuracy does not fall with prior knowledge,
accuracy falls with difficulty, support raises accuracy, retention falls as the break lengthens, and fading lowers
dependence. Five verify the implementation, among them that a scenario contrasted with a relabelled copy of itself
gives exactly zero. All ten passed. A stricter version of the first, that the prior-knowledge strata remain ordered
at the end of the first year, did not: the high and low strata then differ by 0.002 in mean unaided accuracy, because
eq. 16 draws the learning rate independently of prior knowledge and eq. 21 moves every learner towards the same
plateau. Differences between strata are therefore a property of the initial state only.

**Negative controls.** A negative control is a variation under which an effect should not appear if it has the
interpretation claimed [@lipsitch2010]. For the predicted cortical contrasts these are the reworded,
incorrect-but-fluent and shuffled texts of Sections 3.2.5 and 3.3 and the change of reading speed. For the ten-year
contrasts they are a run without plasticity ($\eta = 0$) and a run in which effort does not respond to behaviour
($a_1 = \dots = a_4 = 0$); the predicted responses permuted across units within a condition and the condition labels
permuted within units, 200 times each and post hoc on the main run; and 1,000 random sign flips of the paired
differences within learners, the null distribution of a behavioural contrast.

**Specification curve.** A specification curve re-estimates a result under every combination of defensible analytic
choices [@simonsohn2020; @steegen2016]. Its dimensions, and a plausibility rank for each level (1 for the main
specification, 2 for a plausible alternative, 3 for the least plausible), were fixed before any ten-year result
existed (Table D3). Five dimensions change the simulated behaviour and require runs of their own: the update form,
forgetting, exposure, the effort function and adaptation, whose levels are the constants of Table 2, a halved
version in which each protocol moves half-way to the three-protocol mean (0.42, 0.69 and 0.34), and none, all three
at 0.48, which removes the contrast and keeps the mean level of effectiveness. Each of their 216 combinations was run
with 50 draws of 300 learners in all six scenarios. Seven dimensions change only how the predicted responses enter
the neural state or how outcomes are weighted, and are evaluated post hoc: reading speed, network weights,
parcellation, response metric, winsorising, plasticity mechanism, and the weights of eq. 39, equal or tilted towards
learning (0.4, 0.3, 0.2 and 0.1 for $K$, $R$, $M$ and $D$) or towards autonomy (0.2, 0.3, 0.1 and 0.4). The
behavioural curve thus has 648 specifications per scenario, and the neural curve, for the control-network contrast
between substitution and traditional instruction, 62,208. Parcellation and adaptation were added after the first
results existed, with their levels ranked before they were computed; adaptation was added once it was established
that it is the only term separating scaffolding from traditional instruction (Section 3.4). The learner engine is not
a dimension: at the hybrid engine's four seconds per episode, its fastest case, the main ten-year run alone would
take at least 760 years of computation. The direction of a scenario is called robust when the median $G$ has the same sign in every
specification and no 95% interval across draws includes zero; otherwise the first dimension level at which it fails
is reported.

**Variance decomposition.** Eq. 41 apportions the variance of a year-10 outcome among its sources,

$$ \operatorname{Var}(Y) = V_{\text{scenario}} + V_{\text{parameters}} + V_{\text{learner}} + V_{\text{behaviour}} + V_{\text{plasticity}} + V_{\text{stimulus}} + V_{\text{residual}}. \qquad (41) $$

The first four components come from a nested analysis of variance by the method of moments [@searle1992] over
scenarios, draws, learners and replicates, using three runs that share parameters and learners and differ only in
the random stream of behaviour, with scenarios treated as fixed. $V_{\text{plasticity}}$ is the variance over
mechanisms, half-lives and offloading weights; $V_{\text{stimulus}}$ combines a bootstrap of the 30 units' predicted
responses with the variance across the primary and reworded texts; $V_{\text{residual}}$ is the remainder.

**Falsification criteria.** No difference is claimed when any of six conditions holds. The thresholds are this
study's conventions rather than external standards, and each verdict applies only to the contrasts it names.

- **F1, matching.** A network contrast whose 95% interval excludes zero loses that property once duration, word
  count and equation count enter eq. 13.
- **F2, harmless rewording.** Across the nine combinations of each text's primary and two reworded versions, a
  network contrast changes sign, or its primary value does not exceed twice their standard deviation.
- **F3, plasticity model.** The sign of the median year-10 neural contrast differs across mechanisms A to D.
- **F4, parameter bounds.** More than 10% of learners lie within 0.01 of a bound in the median draw, or a contrast
  changes sign when the triangular parameter draws are replaced by uniform ones.
- **F5, negative controls.** The contrast with condition labels permuted within units reaches half of the
  substantive contrast, or the difference between incorrect-but-fluent and correct texts reaches half of the
  network's largest condition contrast.
- **F6, indistinguishability.** The 95% interval of the year-10 difference between a scaffolding scenario and
  substitution in unaided accuracy, far transfer or retention includes zero.

The criteria were set before the ten-year runs, and the rules of F2 and F5 for the text controls before those texts
were run. Five rules were changed, and the robustness rule was formalised, after the first ten-year results existed;
Appendix D.4 records each change and its reason.

## 3.9 Implementation and reproducibility

The pipeline is a Python package with seven runtime dependencies and one module per concern; Table D4 summarises each
component's inputs, outputs, assumptions and validation. The encoding model ran on a cloud GPU (NVIDIA L4), with its text
encoder in half precision. Centaur and the tutor were served on the author's laptop and, from episode 3,571 of the hybrid run, from a
cloud GPU behind a proxy that reproduces the local prompt format; the switch followed a check on 38 prompts captured
from the local server, on which the two servers gave the same most probable option in every case and option
probabilities within a median total-variation distance of 0.012. Everything else ran on the laptop's processor.

Every run derives its random numbers from one master seed, indexed by learner and episode in Phase III and by draw
and episode in Phase V, never by condition, so results do not depend on how learners are batched. Runs are
append-only and resumable, refuse to resume under a changed configuration, and record the configuration hash, seeds,
package versions and wall time. Runs with the hybrid engine are not bitwise reproducible, because the served model's
scores vary slightly with the state of its cache; they are reproduced from their call logs, which are retained. A
suite of 130 automated tests covers the equations, the corpus validators, the statistics and the equivalence of the
ten-year mirror with the reference loop, and a single command rebuilds every table and figure from the saved runs.
A data dictionary documents the 680 columns of the output tables. The encoding-model predictions (931 files,
8.70 GB) are listed in a SHA-256 manifest, and a 14 MB bundle of the files the analysis reads was verified to
rebuild every table on its own. <!-- CLAUDE: repository URL and the deposit DOI go here once the archive is uploaded
and the repository is public (see open questions). -->

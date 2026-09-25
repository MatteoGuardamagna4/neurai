# 4. Results

## 4.1 Immediate predicted cortical contrasts

Figure 3 shows the predicted response of each network, summarised by its area under the curve, for the three
versions of every unit. At the main reading speed, 14 of the 21 network contrasts have 95% intervals that exclude
zero (Table 8). The dominant pattern is a lower predicted response to the scaffolding versions: relative to both other
versions they evoke less in the visual, somatomotor, dorsal-attention, salience/ventral-attention and control
networks, most of all in the dorsal-attention network. Substitution differs less from traditional instruction; its
intervals exclude zero only in the visual, somatomotor and default-mode networks. The mixed model of eq. 42, which
treats the units as a sample, confirms the ordering: relative to traditional instruction, the response is lower
under scaffolding (−1.20) and slightly higher under substitution (0.49), both with intervals that exclude zero, and it
falls as units become harder.

![](../outputs/figures/fig3_network_responses.png)

*Source: own elaboration; predicted cortical responses of TRIBE v2 to the 90 lesson texts at 220 words per minute
(`outputs/tables/fig3_network_responses.csv`).*

Three criteria restrict what may be claimed. Adjusting for duration, word count and equation count (F1) removes two
substitution contrasts and reverses the sign of the default-mode contrast between scaffolding and traditional
instruction. Rewording (F2) is the binding criterion: 15 of the 21 contrasts change sign across the reworded texts or
do not clearly exceed the variation that rewording produces. They include every contrast between substitution and
traditional instruction and every contrast in the control network. The incorrect-but-fluent texts move the control,
default-mode and limbic networks by at least half of their largest condition contrast (F5), networks that rewording
had already excluded. Six contrasts pass all three criteria: scaffolding against both traditional instruction and
substitution in the somatomotor, dorsal-attention and salience/ventral-attention networks, all lower under
scaffolding. Five of the six still exclude zero at the slower and the faster reading speed.

Table: **Table 8.** Condition contrasts in the predicted network response (area under the curve, 220 words per minute)

| Network | S − T | U − T | S − U |
|---|---|---|---|
| Visual | −0.90 [−1.54, −0.28]^b^ | 1.07 [0.51, 1.61]^b^ | −1.97 [−2.47, −1.47]^b^ |
| Somatomotor | **−0.95 [−1.52, −0.39]** | 0.55 [0.12, 0.96]^ab^ | **−1.50 [−1.86, −1.15]** |
| Dorsal attention | **−3.37 [−4.15, −2.60]** | 0.17 [−0.49, 0.82]^b^ | **−3.54 [−4.19, −2.92]** |
| Salience / ventral attention | **−2.29 [−2.96, −1.62]** | 0.32 [−0.20, 0.85]^b^ | **−2.61 [−3.12, −2.13]** |
| Limbic | 0.12 [−0.14, 0.38]^bc^ | 0.21 [−0.04, 0.46]^bc^ | −0.09 [−0.29, 0.12]^bc^ |
| Control | −2.10 [−2.86, −1.30]^bc^ | 0.15 [−0.55, 0.95]^bc^ | −2.26 [−2.82, −1.68]^bc^ |
| Default mode | 1.09 [0.46, 1.73]^bc^ | 0.96 [0.32, 1.66]^abc^ | 0.13 [−0.34, 0.62]^bc^ |

*Mean paired difference over the 30 units with its cluster-bootstrap 95% interval (eq. 10–13); S scaffolding,
U substitution, T traditional instruction. Bold: the interval excludes zero and the contrast passes F1, F2 and F5.
^a^ The interval includes zero once duration, word count and equation count are covariates (F1). ^b^ Not robust to
rewording (F2). ^c^ Network in which the incorrect-but-fluent texts reach half of the largest condition contrast (F5).
Source: own elaboration; predicted responses of TRIBE v2 (`outputs/tables/table4_cortical_contrasts.csv`,
`table4_cortical_contrasts_matched_covariates.csv`, `tableS_regeneration_contrasts.csv`,
`tableS_incorrect_control.csv`).*

What the six contrasts measure is limited by the construction of the texts (Section 3.2.3). The scaffolding versions
contain no worked solution, and no covariate removes a section that one condition lacks by design. The surviving
contrasts therefore compare a text with diagnostic questions and no worked solution with texts that have one; they
cannot be attributed to scaffolding as an instructional regime. At the level of parcels, contrasts that survive
correction for multiple testing cover most parcels for the two contrasts involving scaffolding and fewer for
substitution against traditional instruction (Figure S2, Appendix E); these maps were not tested against rewording
and are descriptive. The similarity structure among units is preserved across conditions: the
dissimilarity matrices of the three conditions correlate at about 0.8 with one another, more closely than any
permutation of the condition labels (Figure 4, Appendix E). The predicted patterns of all units are, however, very
similar to one another, so the geometry the analysis compares is compressed.

## 4.2 One term of simulated learning

Phase III compares the conditions for the same simulated learners over one term. At the final checkpoint of the
population run, scaffolding exceeds traditional instruction by about 0.01 in unaided accuracy, far transfer and
retention, a small margin whose intervals exclude zero. Substitution falls below traditional instruction in all three,
by 0.075 to 0.105, and ends the term with lower knowledge, memory and reasoning and higher dependence. Free choice lies
between the two. This ordering, scaffolding above traditional instruction above free choice above substitution, holds
for unaided accuracy and far transfer in all three parameter settings (Figure S3, Appendix E). A checkpoint tests only
a handful of items, so most paired differences are exactly zero (98% of learners tie in unaided accuracy between
scaffolding and traditional instruction) and the probability of superiority is uninformative here.

The rate of help requests, also shown in Figure S3, does not measure dependence on equal terms across the arms. After
a wrong first answer the substitution protocol supplies the full solution in one step and offers no further help, so
its request rate is zero by construction and says nothing about the learner's dependence. The free-choice rate is
lowered for the same reason: in the episodes in which the learner chose substitution it could not ask for help
either, whereas in its other episodes it asked at about the rate of the assigned arms. Under substitution, dependence
is therefore read from the state $D$, not from requests. <!-- MG: what do you mean by that substitution protocol offers no help to request so the request rate is 0? 
what are this claims implication on what it has been just written? -->

The hybrid engine was compared with the logistic engine on the same 40 learners (Figure S1, Appendix E). Delegating
the choices to Centaur raised help requests under scaffolding and traditional instruction and lowered calibration in
every arm, because its confidence ratings follow the record (Section 3.4). It moved the end-of-term states by at most
0.011 and left every checkpoint accuracy within 0.025 of the logistic engine, and the contrasts between arms kept their
sign under both engines, differing by less than 0.01. The engines diverge in free choice: Centaur chose substitution in 44% of
episodes, against 31% under the assumed rule for the same learners. This divergence is why a rule fitted to Centaur's
choices was carried into Phase V.

## 4.3 Ten-year scenario contrasts

Figure 5 shows the mean trajectories. Knowledge rises during the first school year and then stays nearly flat in every
scenario except substitution, where it starts lower and falls further. As difficulty rises over the years, far-transfer
accuracy declines in every scenario, and dependence, after falling for a few years, rises again, most steeply under
substitution.

![](../outputs/figures/fig5_trajectories_v_main.png)

*Source: own elaboration; model-implied output of the Phase V main run, 500 parameter draws of 2,000 learners
(`outputs/tables/fig5_trajectories_v_main.csv`).*

Each scenario is summarised by its net advantage $G$ (eq. 39): the mean of its contrasts with traditional instruction
in knowledge, reasoning and memory and of its reduction in dependence. $G$ is positive when, after ten years, the
scenario leaves the same simulated learner with more of the first three and less of the fourth. The other columns of
Table 9 are expected test outcomes. Among them, the probability of requesting help is computed as if help were
offered, so that, unlike the request rate of Phase III, it is defined under substitution.

At year 10 (Table 9), substitution has the largest contrast: $G$ is −0.191 (95% simulation interval −0.233 to
−0.118), and every test outcome is worse than under traditional instruction. Both free-choice scenarios are negative,
the rule fitted to Centaur's choices (−0.059) nearly twice as much as the assumed one (−0.032). Both scaffolding
scenarios are positive, rapid fading (0.045) more than no fading (0.015). With the neutrality threshold of 0.02, rapid
fading is beneficial, substitution and both free-choice scenarios are harmful, and scaffolding without fading is
neutral. The contrasts grow over time: substitution's $G$ is −0.075 after the first year and −0.144 after the fifth.
The scenarios differ in where the contrast lies. Rapid fading gains mainly in reasoning and dependence, and hardly in
knowledge, whereas substitution loses on all four states, most in reasoning and dependence.

Table: **Table 9.** Year-10 scenario contrasts against traditional instruction

| Scenario | $G$ | Unaided accuracy | Far transfer | Retention | P(help request) |
|---|---|---|---|---|---|
| Scaffolding, rapid fading | 0.045 [0.024, 0.064] | 0.027 [0.010, 0.048] | 0.023 [0.011, 0.036] | 0.024 [0.011, 0.039] | −0.044 [−0.062, −0.019] |
| Scaffolding, no fading | 0.015 [0.005, 0.030] | 0.020 [0.007, 0.038] | 0.017 [0.009, 0.024] | 0.015 [0.006, 0.026] | −0.017 [−0.032, −0.006] |
| Substitution | −0.191 [−0.233, −0.118] | −0.175 [−0.217, −0.094] | −0.134 [−0.156, −0.096] | −0.140 [−0.171, −0.085] | 0.157 [0.089, 0.193] |
| Free choice, assumed rule | −0.032 [−0.057, −0.012] | −0.026 [−0.047, −0.008] | −0.019 [−0.029, −0.008] | −0.020 [−0.034, −0.007] | 0.025 [0.008, 0.039] |
| Free choice, fitted rule | −0.059 [−0.071, −0.035] | −0.046 [−0.059, −0.023] | −0.040 [−0.047, −0.028] | −0.039 [−0.048, −0.023] | 0.046 [0.024, 0.055] |

*Median across 500 parameter draws of the mean paired difference from traditional instruction (eq. 37), with the
95% simulation interval across draws; $G$ by eq. 39 with equal weights. Source: own elaboration; model-implied output
of the Phase V main run (`outputs/tables/table5_scenario_contrasts_v_main.csv`).*

The contrasts hold for almost every simulated learner, not only on average (Figure 6). The probability of superiority
in $G$ is 1.000 for both scaffolding scenarios and at most 0.004 for the other three. With one or five episodes a week
instead of three, every AI scenario run at those exposures keeps the sign of its year-10 $G$, with intervals that
exclude zero.

![](../outputs/figures/fig6_distributions_v_main.png)

*Source: own elaboration; model-implied output of the Phase V main run, learner-level paired differences pooled over
500 parameter draws (`data/processed/phase5/v_main/contrast_hist`, `outputs/tables/table5_scenario_contrasts_v_main.csv`).*

## 4.4 Frontier and tipping points

The phase diagram (Figure 7a) replaces the named scenarios by an AI protocol whose adaptation $a$, retained effort
$e$ and probability of substitution $o$ vary continuously, to establish which properties of such a protocol decide its
ten-year contrast. Each cell is one protocol run for ten years against traditional instruction, shaded by its median
$G$ and marked beneficial (+), harmful (−) or neutral (·); the three panels differ only in how often the protocol
supplies the answer. Without substitution ($o = 0$) all 49 cells are neutral. Their $G$ is positive only where the
protocol's adaptation exceeds the constant assumed for traditional instruction, and retained effort barely moves it.
With $o = 0.5$ or $o = 1$ all 98 cells are harmful, whatever the adaptation and retained effort. Along the tipping
lines, $G$ keeps its sign over the whole range of retained effort, of fading and of the forgetting multiplier, in every
draw. It turns negative as substitution is mixed into the AI episodes, at $o = 0.097$ (95% interval 0.058 to 0.144):
in the model, once about one AI episode in ten gives the answer instead of scaffolding, the scaffolding scenario falls
below traditional instruction. Within the model, then, whether the protocol supplies answers decides whether it is
harmful, and its adaptation decides only on which side of zero a protocol that never supplies them falls.

![](../outputs/figures/fig7a_phase_diagram.png)

*Source: own elaboration; model-implied output of the Phase V frontier run, 100 parameter draws of 300 learners
(`outputs/tables/fig7a_phase_diagram.csv`, `tableS_tipping_points.csv`).*<!--MG: what is this graph saying? i dont understand the implications, explain in plain english -->

## 4.5 Mechanisms

The decomposition locates the part of the model through which each scenario contrast arises. Every AI scenario was
rerun with one channel fixed, for each learner and episode, at the value the same learner had under traditional
instruction: the effort or the effectiveness entering the knowledge update, or the dependence entering the learner's
decisions. The share of a contrast that disappears when a channel is fixed is that channel's contribution; a
contribution of 1 means that the contrast passes entirely through it.

For substitution, fixing effort removes 0.97 of the knowledge contrast and 0.51 of $G$, while effectiveness contributes
little and dependence nothing, since substitution offers no help to request. Its knowledge deficit is thus almost
entirely a deficit of effort, and effort accounts for about half of its net disadvantage. For scaffolding without
fading, fixing effectiveness removes the whole contrast in every behavioural outcome (a contribution of 1.00), the
consequence of adaptation being the only term that separates it from traditional instruction. For rapid fading, no
channel accounts for more than 0.22 of $G$. The rest passes through the direct effect of withdrawal on the updates of
reasoning and dependence (less support used, less offloading, more success without help), which the decomposition
does not hold: the advantage of rapid fading arises mainly from the withdrawal of support itself. Under free choice
the contributions fall outside the interval from 0 to 1, a reminder that the channels interact and the decomposition
is not additive. <!--MG: explain this mechanisms section to me, i didnt understand it at all. 
what has been done and what was the purpose?-->

## 4.6 Robustness and falsification

The specification curve (Figure 8a) re-estimates the year-10 $G$ of each scenario in 648 specifications, each a
complete rerun of the ten years under one combination of the modelling choices of Section 3.8. In each panel the
specifications are sorted by their median $G$, drawn with its 95% interval, and the grid beneath marks the choices
each one made. A scenario whose medians all lie on one side of zero has a direction that no combination of these
choices reverses. Four of the five AI scenarios pass this test with no 95% interval including zero: substitution,
both free-choice rules and rapid fading (Table 10). Scaffolding without fading does not. Its 216 failures are exactly
the specifications in which adaptation is equal across the three protocols, the flat segment at zero on the left of
its panel: with equal adaptation, the scaffolding protocol without fading is numerically the traditional one. Its
advantage is therefore the assumed adaptation constant and nothing else, whereas rapid fading stays positive at equal
adaptation, because withdrawing support changes the updates of reasoning and dependence (Section 4.5).

Table: **Table 10.** Sign stability of year-10 $G$ across the specification curve

| Scenario | Median sign constant | Intervals including 0 | Range of medians | Direction |
|---|---|---|---|---|
| Scaffolding, rapid fading | Yes | 0 of 648 | 0.009 to 0.393 | Robust |
| Scaffolding, no fading | No | 216 of 648 | 0.000 to 0.028 | Not robust: fails at equal adaptation |
| Substitution | Yes | 0 of 648 | −0.248 to −0.064 | Robust |
| Free choice, assumed rule | Yes | 0 of 648 | −0.097 to −0.013 | Robust |
| Free choice, fitted rule | Yes | 0 of 648 | −0.084 to −0.017 | Robust |

*Each specification: 50 parameter draws of 300 learners; median and 95% interval across draws. Source: own
elaboration; model-implied output of the 216 specification-curve runs (`outputs/tables/tableS_sign_stability.csv`).*

![](../outputs/figures/fig8a_spec_curve_G.png) <!--MG: i dont understand this part: what is G and what are the figures showing? explain in simple terms-->

*Source: own elaboration; model-implied output of the 216 specification-curve runs, each of 50 parameter draws of
300 learners (`outputs/tables/fig8a_spec_curve_G.csv`).*

The variance decomposition (eq. 41) attributes 68.3% of the variance of year-10 $G$ across the AI scenarios to the
scenario and 28.9% to differences between learners; parameters and behavioural randomness account for the rest, and
plasticity and stimulus for nothing, since $G$ has no neural term. The behavioural controls behave as required. When
effort does not respond to behaviour, the substitution contrast in knowledge almost vanishes, and none of 1,000 random
sign flips of the paired differences produced a contrast as extreme as any observed year-10 contrast in unaided
accuracy, far transfer or retention.

Table 11 collects the falsification verdicts. Beyond the cortical contrasts of Section 4.1 (F1, F2, F5) and the
neural contrasts of Section 4.7 (F3, F5), they concern one ten-year result. F4 flags scaffolding with rapid fading:
in its median draw 12.1% of learners end within 0.01 of an edge of the 0–1 scale, almost all with dependence close to
zero. A post hoc check asked whether the contrast depends on these learners (Appendix D.4). In the stored subsample of
the main run they are the strongest learners, whose dependence was already close to zero under traditional
instruction, and they contribute less than 4% of the scenario's net advantage. Without them the advantage is slightly
larger and keeps its sign in every draw. The direction of rapid fading therefore does not rest on the edge of the
scale, and it is claimed.

Its size is not claimed, because the edges of the scale do shape the size of the results. Under the literal update
equations, in which states are clipped at 0 and 1, nearly every learner in every scenario ends at an edge, and rapid
fading's median $G$ reaches 0.39, against at most 0.07 under the bounded updates. The four robust directions hold
under either form alone (`outputs/tables/tableS_f4_bound_check.csv`). This exposes a limit of F4 as a falsification
criterion: it counts learners near an edge but cannot tell whether a result depends on them, and here it flagged a
direction that does not. It is better read as a screen that sends a result to a check of this kind. The only
criterion that allows a claim without exception is F6: in all six comparisons, the year-10 difference between a
scaffolding scenario and substitution in unaided accuracy, far transfer and retention has an interval that excludes
zero.

Table: **Table 11.** Falsification verdicts

| Criterion | Result | Verdict |
|---|---|---|
| F1 Matching | 2 of 21 network contrasts lose significance with covariates (default mode and somatomotor, U − T) | No claim for those 2 |
| F2 Harmless rewording | 15 of 21 network contrasts change sign or fall below twice the rewording spread | No claim for those 15 |
| F3 Plasticity model | Sign of the median year-10 neural contrast differs across mechanisms in 4 of 35 scenario-networks | No claim for those 4 |
| F4 Parameter bounds | 12.1% of learners near a bound in the median draw of rapid fading; no sign change under uniform draws | No claim for scaffolding with rapid fading^a^ |
| F5 Negative controls | Permuted condition labels reach half the contrast in 8 of 28 scenario-networks; incorrect-but-fluent texts in 3 of 7 networks | No claim for those |
| F6 Indistinguishability | All 6 scaffolding − substitution differences exclude zero | Claim allowed |

*^a^ For the size of its contrast. Its direction is claimed after a post hoc check of the near-bound learners
(Section 4.6, Appendix D.4). Source: own elaboration (`outputs/tables/table6_falsification.csv`,
`tableS_f4_bound_check.csv`).*

## 4.7 Predicted neural trajectories (exploratory)

Phase IV accumulates the predicted responses to the lessons each learner received into a model-implied state, and
this section compares that state between scenarios after ten years. Under mechanism D, the neural contrasts at year
10 look large in standardised terms: both scaffolding scenarios have medians of $d$ between −6.0 and −4.8 in five
networks. They are large because every learner reads the same texts, so the paired differences vary little across
learners; $d$ measures how consistently learners differ, not by how much.

Two results prevent any claim about their direction. First, the contrasts are built from the predicted responses of
Section 4.1, where rewording left a claim for only three networks and for no contrast between substitution and
traditional instruction. Second, the one outcome followed through the specification curve, the control-network
contrast between substitution and traditional instruction, has a positive median in 59.2% of its 62,208
specifications and a negative one in the rest. Its sign depends mostly on how the predicted response is summarised and
read: it is mostly positive at the slower reading speed or with the peak as the response metric, and mostly negative
at the faster speed or with the mean (Figure 8b, Appendix E). The adaptation constant, by contrast, makes no
difference to it. Consistently, the plasticity settings account for more of its variance (40.6%) than the scenario
does (33.1%), and in the neural diagram (Figure 7b, Appendix E) the offloading weight moves the contrast of
substitution more than the half-life of the neural state does in six of the seven networks.

The neural results therefore show that the pipeline can carry predicted responses into a learner-specific state over
ten years, not how AI support would change cortical function: the direction of the contrast examined in full depends
more on how the predicted response is summarised and on the assumed form of plasticity than on the scenario. These
trajectories are model-implied consequences of the assumptions of Phase IV and are reported as exploratory.
<!-- MG: explain in plain english without too many numbers what are the conclusions drawn here-->

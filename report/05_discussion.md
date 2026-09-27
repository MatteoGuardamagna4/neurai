# 5. Discussion and Conclusions

## 5.1 What the model derives and what it assumes

The results differ in how much of them the model derives and how much it simply assumes. Three findings carry the
study, and each has a different standing (Table 14).

The substitution deficit is derived. Nothing in the model states that giving answers is harmful. The deficit arises
because a provided answer lowers the effort the learner invests, and effort multiplies the gain in knowledge; the
decomposition places about half of the net disadvantage in that channel (Section 4.5). Its direction survives every
specification (Section 4.6). Its size does not carry over to real learners. The simulated learner learns more slowly
and forgets faster than the literature supports (Section 3.5), a regime in which differences in effort weigh more than
they would in a classroom, so the size is an upper bound.

The advantage of scaffolding without fading is assumed. Adaptation is the only term that separates it from
traditional instruction, and its value was set, not measured (Table 5). When the three protocols share one adaptation
value, the advantage is exactly zero in every specification (Section 4.6), and with the assumed values it stays
within the neutral band in the main specification. The model therefore says nothing about whether an adaptive AI
tutor teaches better than fixed instruction; it shows only what would follow if it did.

The benefit of rapid fading rests on a mechanism. It survives equal adaptation, because withdrawing support changes
what the learner does: less help is used, less of the work is offloaded, and more problems are solved without help
(Section 4.5). Its direction holds in every specification and does not depend on the learners who reach the edge of
the scale (Section 4.6). Its size is not claimed, because it depends on how the model treats the edges of its scales.

The free-choice scenarios add a behavioural point. When learners choose, the model predicts a drift towards
substitution, and the rule fitted to Centaur's choices drifts further than the assumed rule, which nearly doubles the
deficit. Because the learner selects the protocol, these results describe a policy rather than a condition, and they
rest on a choice rule fitted to a model of human choices, not to students.

Table: **Table 14.** The standing of the main results

| Result | Standing | What supports it | What bounds it |
|--------------------|---------------------|------------------------------------------|------------------------------------------|
| Substitution is harmful | Derived; direction claimed | Effort channel (Section 4.5); every specification; F6 | Size is an upper bound: slow learning, fast forgetting (Table 7) |
| Scaffolding without fading is better | Assumed | Only the adaptation constant | Zero when adaptation is equal; neutral in the main specification |
| Scaffolding with rapid fading is better | Mechanism; direction claimed | Withdrawal channel (Section 4.5); every specification; post hoc F4 check | Size depends on the update form (F4) |
| Free choice is harmful | Derived from the choice rule | Drift towards substitution under both rules | Rule assumed, or fitted to a model rather than to students; self-selection |
| Scaffolding texts evoke a lower predicted response | Descriptive | Six network contrasts pass F1, F2 and F5 | Predicted, not measured; confounded with the absent worked solution |
| Model-implied neural trajectories differ | Exploratory | None robust | Sign depends on analysis choices and plasticity assumptions |

*Source: own elaboration, from Sections 4.1–4.7.*

## 5.2 Which assumptions drive the results

For the behavioural results, the scenario matters more than the assumptions. The scenario accounts for about
two-thirds of the variance of the ten-year net advantage and differences between learners for most of the rest; the
parameter draws and behavioural randomness add little (Section 4.6). Among the modelling choices, three matter. The
adaptation constant decides whether scaffolding without fading differs from traditional instruction at all. The
update form decides how large the benefit of rapid fading is. The choice rule decides how far free choice drifts
towards substitution. Beyond adaptation, only the frequency with which answers are supplied reverses a direction:
about one AI episode in ten is enough to turn scaffolding negative (Section 4.4)<!--MG: da dove viene questa claim-->. The rate of forgetting, the effort
retained when an answer is given and the pace of fading do not.

The learner engine matters less than might be expected. Delegating the behavioural choices to Centaur changed how
often learners asked for help and how well their confidence ratings matched their answers, but not the direction of
any contrast between arms (Section 4.2). Its one substantive effect, the stronger drift towards substitution under
free choice, reached Phase V through the fitted rule.

For the neural results the order is reversed. The plasticity settings explain more of the control-network contrast
than the scenario does, and its sign follows the reading speed and the way the response is summarised (Section 4.7).
A contrast whose sign depends on how a predicted response is summarised cannot inform a decision about instruction,
which is why the neural layer is reported as exploratory.

## 5.3 Relation to empirical evidence

The directions agree with what is known about learning, and this agreement is partly built in. The effort penalty
for a provided answer encodes cognitive offloading [@risko2016] and the benefit of retrieving and generating answers
[@rowland2014; @adesope2017]. Withdrawal as competence grows encodes the definition of scaffolding [@wood1976;
@puntambekar2005]. What the model adds is not these directions but their joint consequence over ten years, the
conditions under which they reverse, and a measure of how much each assumption matters.

Recent field studies point the same way. In a field experiment with nearly 1,000 high-school mathematics students,
unrestricted access to a chat assistant raised performance during practice but lowered it once access was removed,
while a version with pedagogical safeguards largely avoided the loss [@bastani2025]. In a randomised trial, an AI
tutor built on research-based pedagogy produced larger learning gains, in less time, than an active-learning class
[@kestin2025]. These findings agree with the model's central distinction between supplying answers and scaffolding.
They do not test the model: they concern other populations, subjects and time horizons, and none measures the ten-year
quantities projected here.<!--MG:mi sembra che di questi esperimenti si sia parlato di gia in altre sezioni del report, controlla e in caso evita di essere 
ripetitivo quindi taglia eccessi -->

The magnitudes are not comparable. The simulated learner closes a smaller share of its gap to mastery per episode,
and keeps less knowledge over a year, than published estimates imply; only the effect of support on accuracy lies
within its published range (Table 7). The ten-year contrasts are therefore read for their direction and their
conditions, not for their size.

## 5.4 Limitations

Table 15 lists the limitations, what each implies for the results, and what would address it.

Table: **Table 15.** Limitations and their consequences

| Limitation | Consequence for the results | What would address it |
|--------------------|------------------------------------------|------------------------------------|
| Thirty units in one domain, drafted with the aid of language models | Unit-level inferences rest on 30 clusters; other subjects and human-written only material are untested | More units, other domains, human-written texts |
| Scaffolding texts have no worked solution | The surviving predicted cortical contrasts cannot be attributed to scaffolding as such | Versions that differ only in instructional voice |
| Content screened for contradictions only | The prose may contain unsupported claims that no check has caught | A validated screen or an expert review |
| Predicted response of an average adult to text alone | Not a measurement; rewording moves most contrasts | Measured responses in a sample of students |
| All learner parameters assumed; learning slow, forgetting fast and at a constant rate | Sizes of the contrasts are upper bounds; the form of forgetting is never varied | Rates estimated from students (Section 6.4); forgetting that slows with time as a variant |
| Adaptation constant assumed | The advantage of scaffolding without fading is an assumption | A measured per-episode advantage (Section 6.4) |
| States bounded by the 0–1 scale | Under the literal updates nearly every learner ends at an edge; F4 detects this but not its consequence | States on an open scale, or a dependence check for every flagged result |
| Centaur runs on a subsample, cannot answer or rate confidence, and is untested as a learner over many sessions | Phase V choices come from a fitted rule; calibration measures consistency with the record; the realism of its choices is assumed | The choice rule validated against students' logged choices |
| Learners select their protocol under free choice | Free-choice contrasts describe a policy, not a condition | A design that assigns the protocol |
| Plasticity model assumed | Neural trajectories are exploratory | Repeated measurement over time |
| Six analysis rules changed after the first results, among them the post hoc F4 check | Some verdicts rest on decisions taken with results in view | Each is listed with its reason (Appendix D.4) |

*Source: own elaboration.*

The limit set by the 0–1 scale deserves emphasis, because it affects the robustness analysis itself. Half of the
specification curve uses the literal updates, under which nearly every simulated learner ends at an edge of the
scale. The four robust directions hold in either half alone, but sizes from that half reflect the clipping more than
the learning. The falsification criterion meant to catch this, F4, counts learners at the edges and cannot tell
whether a result depends on them; in this study it flagged a direction that did not (Section 4.6). A falsification
criterion for bounded state models should test that dependence directly, as the post hoc check did.

## 5.5 Conclusions

The study asked how traditional instruction, AI scaffolding and AI substitution differ in the predicted cortical
response to a lesson, in simulated learning and in long-term model-implied neural trajectories, and how far these
differences depend on the assumptions made. Table 1 answers each question in brief.

Table: **Table 1.** The research questions and their answers

| Question | Answer | Standing |
|------------------------------|------------------------------------------------------|--------------------|
| How do the three regimes differ in predicted cortical response, simulated learning and long-term model-implied neural trajectories? | Most in simulated learning: substitution is harmful in every specification, and scaffolding helps only through fading or through the assumed adaptation advantage. The predicted cortical and model-implied neural differences are small, unstable or exploratory. | Directions claimed; sizes are upper bounds |
| Which differences remain after matching content, length, readability, modality and presentation time? | Six predicted cortical contrasts survive matching, rewording and the content control, all lower under scaffolding. They reflect the absent worked solution as much as scaffolding. | Descriptive |
| Does scaffolding produce a different predicted cortical profile from substitution? | Yes, in three networks. No contrast between substitution and traditional instruction survives. | Predicted, not measured |
| Under which assumptions does AI improve retention and transfer, and when does it create dependence? | It improves them when it withholds answers and withdraws support as competence grows. Supplying answers in more than about one AI episode in ten turns the net advantage negative; full substitution lowers retention and transfer and raises dependence. | Model-implied; conditions robust, sizes not |
| How sensitive are the long-term conclusions to plasticity, forgetting, exposure and the mapping from response to learning? | The behavioural directions are insensitive to all of them. The neural conclusions depend on them more than on the scenario. | Measured by the specification curve and the variance decomposition |
| Is there a robust frontier between beneficial, neutral and harmful AI? | In the model, yes: supplying answers decides harm, withdrawing support is what makes scaffolding beneficial rather than neutral, and adaptation decides only on which side of zero a protocol that never supplies answers falls. | Model-implied; the adaptation boundary is assumed |

*Source: own elaboration.*

The contribution is therefore less a verdict on AI in teaching than a map of which conclusions follow from which
assumptions. The conclusions that survive concern design: whether an AI tutor supplies answers, and whether it
withdraws its support as the learner succeeds. The one that does not survive, whether adaptive AI instruction is more
effective per episode than fixed instruction, is an empirical quantity that no simulation can supply. Section 6.4
proposes how to measure it.

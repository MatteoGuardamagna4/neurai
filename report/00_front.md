---
title: "NeuroTutorSim"
subtitle: "A computational comparison of traditional instruction, AI scaffolding and AI substitution"
author: "Matteo Guardamagna"
lang: en-GB
---

::: {custom-style="Cover"}
MSc in Business Analytics, ESADE Business School

In Company Project, academic year 2025–2026

Organisation: ESADE Data Department

Tutors: Carlos Carrasco-Farré and Marc Arnal Torrens
:::

<!-- CLAUDE: cover fields per the ESADE guidelines (student and master, title, organisation, tutor, confidentiality,
course). The title is a working title; the date line is added by build.py. -->

# Abstract

How do traditional instruction, AI scaffolding and AI substitution differ in their consequences for learners, and how
far do these differences depend on the assumptions made? Long-term evidence cannot yet be observed, so the study uses
a computational laboratory of generated data. Thirty MBA units were written in three matched versions, and the
cortical response to each lesson text was predicted with an encoding model. Simulated learners worked through the
curriculum: explicit equations govern their knowledge, memory, reasoning, calibration and dependence, and in a
subsample a language model of human choice makes their behavioural choices. A Monte Carlo simulation then projected
them over ten school years under six scenarios, varying the modelling choices jointly in 648 specifications. Three
model-implied results follow. Substitution is harmful in every specification, because a provided answer lowers the
effort on which learning depends, and supplying the answer in about one AI episode in ten is enough to turn
scaffolding negative. Scaffolding that withdraws support as the learner succeeds stays ahead of traditional
instruction in every specification. Scaffolding without withdrawal is ahead only because adaptive instruction is
assumed to be more effective per episode: when the three regimes share one adaptation value, its advantage is exactly
zero. The predicted cortical contrasts that survive matching and rewording are few, and the model-implied neural
trajectories are exploratory. Every parameter is assumed, and the simulated learner learns more slowly and forgets
faster than published estimates imply, so the report claims the direction of each contrast, not its size, and reads the substitution deficit as an upper bound.
<!--MG:cosa vuol dire so the directions are the claim and the sizer are the upper bounds? RISOLTO-->
# Executive Summary

## Project and objective

This project was carried out for the ESADE Data Department, as part of its research on the implications of artificial
intelligence for education. It addresses a decision that business schools face now: how AI assistants should be built
into teaching. After a student's wrong answer, an assistant can help in two ways. It can scaffold: diagnose the error,
ask a question and give a hint, while withholding the answer. Or it can substitute: supply the complete solution at
once. The study compares both regimes with traditional instruction, which offers graded hints and then a worked
solution.

The early field evidence points in both directions. Unrestricted access to a chat assistant raised students' grades
during practice and lowered them once access was withdrawn [@bastani2025]. An AI tutor built on established teaching
practice produced larger learning gains than an active-learning class [@kestin2025]. These studies span weeks, whereas
a school's decisions about AI concern years, and cohorts followed for a decade would report after those decisions had
been taken.

The objective is to compare the three regimes in a computational laboratory at three levels: the predicted cortical
response to a lesson, simulated learning over one term, and model-implied development over ten school years. Above
all, the study asks which differences follow from the mechanics of the model and which merely restate its
assumptions. It does not forecast what will happen to students. It maps which conclusions about AI in teaching follow
from which assumptions.

## Methodology and data sources

No data set existed that could answer the question, and none could be collected within the project. Every data source
analysed here was therefore generated for the study, in five phases (Table ES1).

Table: **Table ES1.** The five phases and the data each generated

| Phase | What was done | Data generated |
|--------------------|------------------------------------------------------|------------------------------------|
| I. Corpus | 15 concepts from core MBA courses, each taught in two units; every unit written in three versions that differ in instructional policy and are matched in content and length; validated automatically | 30 units; 90 lesson texts; 210 control texts |
| II. Predicted cortical response | The response of an average adult reader to every text, predicted with the TRIBE v2 encoding model on a cloud GPU | 660 text predictions, 8.7 GB |
| III. Simulated learner | Simulated learners work through the curriculum; equations decide correctness and learning; Centaur, a language model trained on human choices, makes the behavioural choices in a subsample | 814,560 episodes |
| IV. Plasticity | The predicted responses to the lessons each learner received accumulate into a model-implied neural state | One state per learner and episode |
| V. Ten-year scenarios | Monte Carlo projection over ten school years under six scenarios, with parameter uncertainty propagated | 236 runs; about 45 billion learner-episodes |

*Source: own elaboration; counts from the run records of each phase (Table 2).*

Three principles govern the design. First, every contrast is within learners. Each simulated learner meets every
regime from the same starting state, in the same curriculum order and with the same random events, so a difference
between regimes is not a difference between people. Second, transparency prevails over realism. The correctness of
every answer comes from an explicit equation, and the model of human choice makes only the choices it was shown to
adapt to a learner's record, such as which approach to take and whether to ask for help. Third, every assumption is
explicit and varied. The parameters were set by assumption and compared afterwards with published values. The
modelling choices that could defensibly have been made otherwise were varied jointly: how states are bounded, how
forgetting works, how often learners practise, how effort responds to behaviour, and how much more effective adaptive
instruction is. Their 216 combinations were each run in all six scenarios, which gives 648 specifications per
scenario once the outcome weights are varied as well. Six falsification criteria, fixed before the ten-year runs,
state when no difference is claimed, and every rule changed afterwards is reported.

The six scenarios are traditional instruction; AI scaffolding with support withdrawn after two consecutive correct
first answers (rapid fading) and without withdrawal; AI substitution; and two free-choice scenarios, in which the
learner chooses the regime for each problem by an assumed rule or by a rule fitted to Centaur's choices. The summary
outcome is the net advantage $G$: the contrast with traditional instruction in knowledge, reasoning and memory, minus
the contrast in dependence.

## Academic framework

Four bodies of research frame the study (Section 2). Foundation models of human cognition, above all Centaur
[@binz2025], allow behavioural choices to be simulated with a model trained on human decisions, although almost half
of the studies that use simulated learners give no evidence that the simulation is valid [@kaser2024]<!--MG:OK-->. Foundation
models of neural response, such as TRIBE v2 [@dascoli2026]<!--MG:OK-->, predict the cortical response to material that has never
been scanned; such a prediction describes the immediate response to a text, not learning. Research on scaffolding and
cognitive offloading establishes that support should be withdrawn as competence grows [@wood1976; @puntambekar2005]<!--MG:OK-->.
Offloading a task to an external aid improves performance on it [@risko2016]<!--MG:OK-->, whereas generating and retrieving
answers improves memory [@slamecka1978; @rowland2014]<!--MG:OK-->. Research on knowledge tracing and retention [@badrinath2021;
@custers2010]<!--MG:OK--> supplies the published values against which the learning and forgetting rates of the simulated learner
are checked.

Methodologically, the study uses simulation to derive the consequences of stated assumptions [@davis2007]<!--MG:OK-->. It tests
their robustness with a specification curve [@simonsohn2020] <!--MG:OK-->and with negative controls [@lipsitch2010]<!--MG:OK-->. To the
author's knowledge, no published study joins a predicted cortical response to instruction, a simulated learner whose
choices come from a model of human behaviour, and a projection over years with propagated uncertainty.

## Main conclusions and deliverable

Table ES2 summarises the ten-year results and their standing.

Table: **Table ES2.** Year-10 net advantage over traditional instruction and the standing of each result

| Scenario | Net advantage $G$ in the main run | Across the 648 specifications | Standing |
|--------------------|------------------------------|------------------------------------|------------------------------|
| AI substitution | −0.191 [−0.233, −0.118] | Harmful in every one | Derived; direction claimed, size an upper bound |
| Scaffolding, rapid fading | 0.045 [0.024, 0.064] | Ahead in every one | Derived from the withdrawal of support; size not claimed |
| Scaffolding, no fading | 0.015 [0.005, 0.030] | Exactly zero in the 216 with equal adaptation | Assumed: rests on the adaptation constant alone |
| Free choice, assumed rule | −0.032 [−0.057, −0.012] | Behind in every one | Derived from an assumed choice rule |
| Free choice, rule fitted to Centaur | −0.059 [−0.071, −0.035] | Behind in every one | Derived from a rule fitted to a model, not to students |
<!--MG:qual è l'unità di misura e che significato ha la colonna standing?RISOLTO-->
*Median across 500 parameter draws with its 95% simulation interval; positive values favour the AI scenario. Source:
own elaboration; model-implied output of the Phase V main run and the specification curve (Tables 11 and 12).*

Four conclusions follow, each a statement about the model.

First, supplying answers is harmful in every specification. The deficit is derived rather than assumed: a provided
answer lowers the effort the learner invests, and effort multiplies the gain in knowledge. In the model, a scaffolding
tutor that instead supplies the answer in about one AI episode in ten already falls below traditional instruction. The
simulated learner learns more slowly and forgets faster than the published evidence supports, so its knowledge settles
at 0.59 of mastery rather than the 0.96 that the midpoints of the published ranges imply. Differences in effort weigh
more in that regime, so the size of the deficit is an upper bound and its direction is the claim.

Second, scaffolding helps when it withdraws support. Rapid fading stays ahead of traditional instruction in every
specification, including those in which adaptive instruction has no assumed advantage. Withdrawal changes what the
learner does: less help is used, less work is offloaded and more problems are solved alone.

Third, scaffolding without withdrawal is ahead only by assumption. The one term that separates it from traditional
instruction is an assumed constant: how much more effective adaptive instruction is per episode. When the three
regimes share one value, its advantage is exactly zero. The model therefore cannot say whether an adaptive AI tutor
teaches better than fixed instruction. That is an empirical quantity.

Fourth, when learners choose, the model predicts a drift towards the regime that gives answers, and both free-choice
scenarios end behind traditional instruction. The neural layer, by contrast, is exploratory. Few predicted cortical
contrasts survive matching and harmless rewording, and the sign of the model-implied neural contrast depends more on how
the predicted response is summarised and on the assumed plasticity than on the scenario.

For the ESADE Data Department, three implications follow, each conditional on the model (Section 6.3). How often a
tool supplies answers should be established before anything else. The advantage of adaptive tutoring should not be
taken for granted. Tools should withdraw their support as students succeed, and evaluations should test students after
the help is gone. The most valuable next step is a measurement rather than another simulation: the per-episode
advantage of adaptive tutoring over fixed instruction, which decides one of the three main results and can be
measured within a single term (Section 6.4).

The deliverable is a framework as much as a set of results. It comprises this report; a public repository with the
corpus, the code and the run records, in which a single command rebuilds every table and figure; an archive of the
predicted cortical responses with a checksum manifest; and a validation layer of negative controls, falsification
criteria and a specification curve that can audit any simulation-based claim about AI in teaching. The report has the
shape of an academic paper because a publication is planned.

# Declaration of AI Assistance

The guidelines of the programme require that any assistance received in preparing the project be acknowledged.
Generative AI models of the Claude family (Anthropic) assisted this work in four ways, each under the author's
direction and review.

- **Unit records.** The 30 unit records, with their problems, answers, misconceptions, wrong options, hints and worked
  solutions, were written by the author with Claude and reviewed by the author. Every answer is recomputed from its
  formula when the corpus is loaded (Section 3.2.1).
- **Lesson and control texts.** The 90 lesson texts and the 210 control texts were drafted with Claude Opus 5 and
  Claude Fable 5 from the unit records. They passed the automatic checks of Section 3.2, and the texts with the lowest
  semantic coverage were read by the author (Appendix A.2).
- **Code.** The software was written with the assistance of Claude Opus 5, Claude Opus 5.5 and Claude Fable 5. It is
  covered by automated tests, and a single command rebuilds every table and figure from the saved runs (Section 3.9).
- **This report.** The drafts were prepared with the same assistance and revised by the author. Every number that the
  body quotes from the study's outputs is recomputed from its source file by an automated check in the repository, and
  every reference was checked against its published record.

The language models that are components of the method are not assistance in this sense. Centaur, which makes the
simulated learner's choices, Qwen2.5-3B-Instruct, which acts as the tutor and as the judge of the contradiction check,
and TRIBE v2, which predicts the cortical response, are part of the study's design and are described in Section 3.
The research questions, the design decisions, the choice of analyses, the interpretation of the results and the
conclusions are the author's, who takes full responsibility for the content of this report.

::: {custom-style="TOC Heading"}
Index
:::

```{=openxml}
<w:p><w:r><w:fldChar w:fldCharType="begin" w:dirty="true"/></w:r><w:r><w:instrText xml:space="preserve"> TOC \o "1-3" \h \z \u </w:instrText></w:r><w:r><w:fldChar w:fldCharType="separate"/></w:r><w:r><w:t>Update this field (F9) to build the index.</w:t></w:r><w:r><w:fldChar w:fldCharType="end"/></w:r></w:p>
```

{{COUNTS}}

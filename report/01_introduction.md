# 1. Introduction

## 1.1 Motivation

Consider an MBA or Master's student stuck on a net-present-value problem. A chat assistant can help in one of two ways. It can
ask what the student has tried, point to the step that went wrong and let them finish the calculation, or it can
supply the answer. Both resolve the problem at hand. What matters to a business school and most importantly, to the student, is what each leaves behind:
what the student can do alone afterwards, and what years of such help add up to.

The early field evidence points in both directions. In a field experiment with nearly a thousand secondary-school
students, unrestricted access to a chat assistant raised grades during practice and lowered them once access was
withdrawn, below those of students who had never had it [@bastani2025]<!--MG:OK-->. In a randomised trial with university
students, an AI tutor built on established teaching practice produced larger learning gains, in less time, than an
active-learning class [@kestin2025]<!--MG:OK-->. What distinguishes the two outcomes is less the technology than whether the tool
supplies answers or requires students to work for them.

These studies span weeks, whereas a school's decisions about AI concern years: which tools to adopt and how to build
them into a course. The evidence that would settle such decisions, cohorts taught in different ways, would arrive after the decisions had been taken and the tools had changed.

This study therefore takes a different approach: a computational laboratory in which the long-term comparison is run
on simulated learners, with every assumption stated explicitly. Two recent developments make this possible. Encoding
models trained on large collections of brain recordings can predict the cortical response to a text that has never
been scanned [@dascoli2026]<!--MG:OK-->. Language models trained on more than ten million choices from psychological experiments
can predict what a person will choose next [@binz2025]<!--MG:OK-->. Joined to explicit equations for learning and forgetting, they
allow a comparison that cannot be run with students: the same simulated learner, taught the same curriculum in six
different ways, followed for ten school years.

The laboratory does not forecast what will happen to real students; it shows which conclusions follow from which
assumptions, and the distinction matters for the results. An AI tutor that scaffolds without withdrawing its help
leaves the simulated learner slightly ahead of traditional instruction after ten years, but only because the model
assumes that adaptive instruction is more effective per lesson: when that assumed value is set equal across the
regimes, the advantage is exactly zero in every specification in which this is done. A tutor that withdraws its help
as the learner succeeds stays ahead under the same test, and a tutor that supplies answers is harmful in all 648
specifications examined. The first result is an assumption; the other two follow from the mechanics of the model.

## 1.2 Research questions

The three instructional regimes differ in what happens after a learner's first wrong answer. Traditional instruction offers graded hints and, after the third, a worked solution. AI scaffolding
offers an AI tutor that diagnoses the error, asks one question and gives a graded hint, and withholds the answer until
its third turn. AI substitution has an AI supply the complete solution at once, always after the first mistake was made.

The primary question is how these three regimes differ in the predicted cortical response to a lesson, in simulated
learning and in long-term model-implied neural trajectories, and how far these differences depend on the assumptions
made<!--MG:since tribe is not reading the tutor's diagnosis, what is changing? RISOLTO-->. Five secondary questions follow from it:

1. Which differences remain after matching content, length, readability, modality and presentation time?
2. Does scaffolding produce a different predicted cortical profile from substitution?
3. Under which assumptions does AI improve retention and transfer, and when does it create dependence?
4. How sensitive are the long-term conclusions to plasticity, forgetting, exposure and the mapping from response to
   learning?
5. Is there a robust frontier between beneficial, neutral and harmful AI?

The answers are statements about a model. They are reported as scenario contrasts between simulated learners, not as
effects on students, and Table 15 (Section 5.5) gives them in brief.

## 1.3 Approach and contribution

The work proceeds in five phases (Figure 1). Phase I builds the matched corpus. Phase II predicts the cortical
response to every text with an encoding model. Phase III simulates learners working through the curriculum, with
explicit equations for what they learn and a language model trained on human choices making their behavioural choices in a subsample.
Phase IV accumulates the predicted responses to the lessons each learner received into a model-implied neural state.
Phase V projects the learners over ten school years under six scenarios and propagates the uncertainty in every
parameter.

The contribution is a framework rather than a verdict, and three features distinguish it. First, every contrast is
within learners: each simulated learner meets every regime from the same starting point and with the same random
events, so a difference between regimes is not a difference between people. Second, the study states in advance when
it will not claim a difference. Six falsification criteria were fixed before the ten-year runs. Third, every modelling choice that could defensibly have been made otherwise is varied
jointly, and a direction is called robust only if it survives all of them. The outcome is a map of which conclusions
about AI in teaching follow from which assumptions. The code, corpus and run records are public, and a single command
rebuilds every table and figure from the saved runs (Section 3.9).

## 1.4 Scope and context

The study was carried out for the ESADE Data Department, as part of its research on the implications of AI for
education.
Its population of interest is business-school students. The curriculum therefore covers 15 concepts from core MBA
courses in managerial accounting, corporate finance, pricing and marketing analytics, each taught twice in a different
situation to make the learner exercise memory. Every answer in these courses is a number, so every answer can be checked automatically. The corpus has 30
units, a size set by the available computing resources, since each unit requires 22 runs of the encoding model <!--MG:22 runs of the encoding model for each unit what is it talking about? RISOLTO 3 versioni × 3 velocità di lettura (180, 220, 260 wpm) = 9
3 versioni × 2 shuffle (frasi; parole dentro la sezione) = 6
3 versioni × 2 riformulazioni (più semplice, più formale) = 6
1 testo tradizionale scorrevole ma sbagliato = 1-->.

Six scenarios are compared over ten school years: traditional instruction; AI scaffolding with support withdrawn as
the learner succeeds, and without withdrawal; AI substitution; and two scenarios in which the learner chooses the
regime for each problem, by an assumed rule (Appendix C.4) <!--MG:quale è questa regola e dove posso vederla RISOLTO-->or by a rule fitted to the choices of Centaur. Throughout, the learners are simulated, the cortical responses predicted and the ten-year
trajectories model-implied. No part of the study measures a student or a brain, and Section 6.4 names the measurements
that would test its results.

The assistance of
language models in drafting texts, code and this report is declared in the front matter.

## 1.5 Structure of the report

Section 2 reviews the four bodies of research the study draws on. Section 3 describes the five phases and the design
of the validation. Section 4 reports the results, from the immediate predicted cortical contrasts to the ten-year scenarios and
their robustness. Section 5 separates what the model derives from what it assumes, sets out its limitations and
answers the research questions. Section 6 turns the findings into an application plan for the ESADE Data Department.
The appendices hold the technical detail: the corpus checks, the encoding-model run, the equations of the simulated
learner, the ten-year simulation and its validation, and supplementary results.

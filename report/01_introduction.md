# 1. Introduction

## 1.1 Motivation

It is late in the evening, and an MBA student is stuck on a net-present-value problem. A chat assistant can get them
unstuck in seconds, in one of two ways. It can ask what they have tried, point to the step that went wrong and let
them finish the calculation. Or it can give them the answer. Both feel like help, and both put the right number on the
page tonight. What matters to a business school is what each leaves behind: what the student can still do alone next
month, and what years of such help add up to.

The first field evidence points both ways. In a field experiment with nearly a thousand secondary-school students,
unrestricted access to a chat assistant raised grades during practice and lowered them once access was withdrawn,
below those of students who had never had it [@bastani2025]. In a randomised trial with university students, an AI
tutor built on established teaching practice produced larger learning gains, in less time, than an active-learning
class [@kestin2025]. The technology is the same. What differs is whether the tool supplies answers or makes students
work for them.

These studies span weeks. The decisions a school takes about AI concern years: which tools to adopt, how to build
them into a course, what to allow at home. The evidence that would settle those decisions, cohorts taught in different
ways and followed for a decade, would arrive long after the decisions had been taken and the tools had changed.
Waiting for it is itself a decision.

This study takes another route. It builds a computational laboratory in which the long experiment can be run now, on
simulated learners, with every assumption written down. Two recent developments make this possible. Encoding models
trained on large collections of brain recordings can predict the cortical response to a text that has never been
scanned [@dascoli2026]. Language models trained on more than ten million choices from psychological experiments can
predict what a person will choose next [@binz2025]. Joined to explicit equations for learning and forgetting, they
allow an experiment that cannot be run on people: the same learner, taught the same curriculum in six different ways,
followed for ten school years.

The laboratory does not forecast what will happen to real students. It shows which conclusions follow from which
assumptions, and that turns out to be informative. An AI tutor that scaffolds but never withdraws its help leaves the
simulated learner slightly ahead of traditional instruction after ten years, but only because the model assumes that
adaptive instruction is more effective per lesson. Set that one assumed number equal across the regimes, and the
advantage becomes exactly zero in every specification in which this is done. A tutor that steps back as the learner
succeeds stays ahead under the same test, and a tutor that supplies answers keeps its harm in all 648 specifications
examined. The first is an assumption; the other two follow from the mechanics of the model.

## 1.2 Research questions

The three instructional regimes differ in what happens after a learner's first wrong answer; none offers help before a
first attempt. Traditional instruction offers graded hints and, after the third, a worked solution. AI scaffolding
offers an AI tutor that diagnoses the error, asks one question and gives a graded hint, and withholds the answer until
its third turn. AI substitution has an AI supply the complete solution at once.

The primary question is how these three regimes differ in the predicted cortical response to a lesson, in simulated
learning and in long-term model-implied neural trajectories, and how far these differences depend on the assumptions
made. Five secondary questions follow from it:

1. Which differences remain after matching content, length, readability, modality and presentation time?
2. Does scaffolding produce a different predicted cortical profile from substitution?
3. Under which assumptions does AI improve retention and transfer, and when does it create dependence?
4. How sensitive are the long-term conclusions to plasticity, forgetting, exposure and the mapping from response to
   learning?
5. Is there a robust frontier between beneficial, neutral and harmful AI?

The answers are statements about a model. They are reported as scenario contrasts between simulated learners, not as
effects on students, and Table 15 (Section 5.5) gives them in brief.

## 1.3 Approach and contribution

No data set existed that could answer these questions, and none could be collected within the project. Everything
analysed here was generated for it (Table 2): a curriculum of 30 units written and validated in three versions, 90
lesson texts in all, with 210 control texts; 8.7 GB of predicted cortical responses; 814,560 simulated learning
episodes over one term; and some 45 billion simulated learner-episodes in 236 ten-year runs.

The work proceeds in five phases (Figure 1). Phase I builds the matched corpus. Phase II predicts the cortical
response to every text with an encoding model. Phase III simulates learners working through the curriculum, with
explicit equations for what they learn and a language model trained on human choices making their behavioural choices.
Phase IV accumulates the predicted responses to the lessons each learner received into a model-implied neural state.
Phase V projects the learners over ten school years under six scenarios and propagates the uncertainty in every
parameter.

The contribution is a framework rather than a verdict, and three features distinguish it. First, every contrast is
within learners: each simulated learner meets every regime from the same starting point and with the same random
events, so a difference between regimes is not a difference between people. Second, the study states in advance when
it will not claim a difference. Six falsification criteria were fixed before the ten-year runs, and every rule changed
afterwards is reported. Third, every modelling choice that could defensibly have been made otherwise is varied
jointly, and a direction is called robust only if it survives all of them. The outcome is a map of which conclusions
about AI in teaching follow from which assumptions. The code, corpus and run records are public, and a single command
rebuilds every table and figure from the saved runs (Section 3.9).

## 1.4 Scope and context

The study was carried out for the ESADE Data Department, as part of its research on the implications of AI for
education, and the report is written in the shape of an academic paper because a publication is planned (Section 6.2).
Its population of interest is business-school students. The curriculum therefore covers 15 concepts from core MBA
courses in managerial accounting, corporate finance, pricing and marketing analytics, each taught twice in a different
situation. Every answer in these courses is a number, so every answer can be checked automatically. The corpus has 30
units, a size set by the available computing resources, since each unit requires 22 runs of the encoding model.

Six scenarios are compared over ten school years: traditional instruction; AI scaffolding with support withdrawn as
the learner succeeds, and without withdrawal; AI substitution; and two scenarios in which the learner chooses the
regime for each problem, by an assumed rule or by a rule fitted to the choices of Centaur, the model of human choices
used in Phase III. Throughout, the learners are simulated, the cortical responses predicted and the ten-year
trajectories model-implied. No part of the study measures a student or a brain, and Section 6.4 names the measurements
that would test its results.

The study is individual: its design, implementation, runs and analysis are the author's own. The assistance of
language models in drafting texts, code and this report is declared in the front matter.

## 1.5 Structure of the report

Section 2 reviews the four bodies of research the study draws on. Section 3 describes the five phases and the design
of the validation. Section 4 reports the results, from the immediate cortical contrasts to the ten-year scenarios and
their robustness. Section 5 separates what the model derives from what it assumes, sets out its limitations and
answers the research questions. Section 6 turns the findings into an application plan for the ESADE Data Department.
The appendices hold the technical detail: the corpus checks, the encoding-model run, the equations of the simulated
learner, the ten-year simulation and its validation, and supplementary results.

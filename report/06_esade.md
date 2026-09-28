# 6. Implications for the ESADE Data Department

## 6.1 What the department obtains

The department obtains a framework rather than a verdict: a set of tools that turn assumptions about AI in teaching
into explicit, testable scenario contrasts. Its parts can be reused separately (Table 16). All of them are public,
the code under the MIT licence and the data under CC BY-NC 4.0 (Section 3.9).

Table: **Table 16.** The reusable parts of the framework

| Part | What it is | How the department can reuse it |
|--------------------|------------------------------------------|------------------------------------------|
| Matched corpus and its checks | 30 units in three versions, 210 control texts, automatic validators and a contradiction screen of measured sensitivity | Build matched materials for other courses; the validators and controls apply to any set of lesson texts |
| Encoding-model pipeline and archive | Predicted cortical responses to every text, a checksum manifest and a bundle that rebuilds every table without a GPU | Predict responses to other materials; let reviewers check the results independently |
| Simulated learner | Explicit learning equations, with behavioural choices from a model trained on human choices | Test a tutor design before a pilot, by setting how it adapts, how often it gives answers and when it withdraws support |
| Validation layer | Negative controls, falsification criteria, specification curve and variance decomposition | Audit any simulation-based claim about AI in teaching, including the successors of this study |

*Source: own elaboration.*

## 6.2 Publication path

The report is written in the shape of a paper, and the department's aim is at least one publication. The claim such a
paper can make is methodological as much as substantive: a simulation that fixes in advance when it will not claim a
difference, reports every rule it changed afterwards, and separates what it derives from what it assumes. The
substitution result is its substantive finding; the scaffolding result is a worked example of an assumption exposed by
the robustness analysis. Three steps would prepare a submission. The data archive needs a DOI, which Zenodo can mint
from the GitHub release. The learning and forgetting rates should either be replaced by measured values (Section 6.4)
or kept, as here, as a stated limit on the size of the results. And the neural layer belongs in a supplement unless
measured responses become available.

## 6.3 What changes in how AI in teaching is evaluated

Three implications follow, each conditional on the model.

First, measure answer supply before anything else. In the model, a scaffolding tutor that gives the answer in more
than about one AI episode in ten loses its advantage over traditional instruction, and one that gives it in half of
its episodes is harmful whatever its adaptation. The frequency with which a tool gives answers away is
therefore the first property to establish in any pilot.

Second, do not take the advantage of adaptive tutoring for granted. Whether an AI tutor that scaffolds without fading
beats fixed instruction depends entirely on a quantity that has not been measured for these students. A decision that
assumes this advantage assumes its own conclusion.

Third, design and evaluate for withdrawal. The only scaffolding benefit the model derives comes from withdrawing
support as students succeed. Tools should fade their help, and evaluations should test students after the help is
gone, which is also where the field evidence locates the harm of answer-giving assistants [@bastani2025]. When
students choose freely, the model predicts a drift towards the mode that gives answers, so the default setting of a
tool is a design decision rather than a detail.

## 6.4 The next empirical measurements

The most valuable next step is not another simulation but three measurements, ordered by how much each would change
the conclusions (Table 17). Each fits within a course and replaces an assumption with a number.

Table: **Table 17.** Measurements that would replace the model's key assumptions

| Measurement | What it would settle | How it could be measured | What the model forecasts |
|--------------------|------------------------------|------------------------------------|------------------------------------|
| Per-episode advantage of adaptive tutoring over fixed instruction | Whether scaffolding without fading helps at all | Students of one course unit randomly assigned to an AI tutor or to fixed hints on the same problems, with unaided tests after each session | No advantage: identical to traditional instruction. Any advantage in the range tested: positive but neutral, since without fading no adaptation value makes scaffolding beneficial |
| Learning and forgetting rates of the department's students | The size of every contrast | Repeated unaided tests on the same units, at spaced intervals and after a break | Smaller contrasts, because knowledge would settle closer to mastery; the same directions, which hold across every forgetting variant tested |
| Students' choices between an answer-giving and a scaffolding mode | How far free choice drifts towards answer supply | Logs of the mode students choose in a tool that offers both | A drift towards answer supply, larger under the rule fitted to Centaur than under the assumed rule |

*Source: own elaboration; forecasts from Sections 4.4 and 4.6.*

The first measurement has the most leverage: it decides one of the study's three main results and can run within a
single term. The second needs a delayed test after a break, and it would turn the sizes of the contrasts from upper
bounds into estimates. The third comes almost free with any deployed tool that logs its mode. Measured cortical
responses would test the predicted contrasts, but they are costly and belong after the three behavioural
measurements. Together, these measurements would turn the framework from a map of what follows from which
assumption into an estimate for the department's own students.

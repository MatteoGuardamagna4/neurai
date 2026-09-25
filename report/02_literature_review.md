# 2. Literature Review

The study draws on four bodies of research. Two supply its instruments: models that predict human choices (Section
2.1) and models that predict cortical responses (Section 2.2). Two supply its assumptions: research on scaffolding and
cognitive offloading, which sets the direction of the effects (Section 2.3), and research on knowledge tracing and
retention, which provides the published values the model is compared with (Section 2.4). Each subsection ends with
what that work leaves open; Section 2.5 draws the strands together.

## 2.1 Foundation models of human cognition

Simulated learners are not new. In educational technology they are used to train teachers, develop adaptive
algorithms, test learning environments and generate hypotheses about learning before students are involved
[@kaser2024]. A systematic review of a decade of this work found that simulated learners tend to represent only narrow
aspects of learning. Almost half of the studies gave no evidence that their simulation was valid [@kaser2024].

Large language models have renewed the interest in simulated participants. Conditioned on the backgrounds of real
survey respondents, a language model reproduced the distribution of answers of demographic subgroups [@argyle2023].
Tested on standard experiments of cognitive psychology, a similar model matched or exceeded human participants on some
tasks, failed on others, and could be led astray by small changes to a task [@binz2023]. Whether such models can
replace human participants, and under which conditions, remains open [@dillion2023].

Centaur takes a more direct route [@binz2025]. It is a language model fine-tuned on Psych-101, a collection of the
trial-by-trial choices of more than 60,000 participants in 160 psychological experiments, each written out in natural
language. Given the transcript of an experiment so far, it predicts the participant's next choice. It predicted the
behaviour of held-out participants better than existing cognitive models, generalised to new cover stories, modified
tasks and new domains, and, according to its authors, also simulates human behaviour when its choices are sampled
rather than scored.

What this literature leaves open is whether such a model can act as a learner. The language-model studies above
concern single experiments or surveys; none places a model of choice in the role of a learner over many sessions of
instruction, with its own sampled choices fed back into its history. This study does exactly that, so the realism of
the simulated behaviour is an assumption. The development probes of Section 3.4 tested it for Centaur, behaviour by
behaviour. Centaur's choices of approach and of help shifted with the learner's record as a struggling or a coping
learner's would. It solved the problems no better than guessing, however, and its confidence ratings followed the
record rather than the answer just given. The study therefore gives Centaur only the learner's behavioural choices and
leaves correctness to an explicit equation.

## 2.2 Foundation models of neural response

An encoding model predicts the measured brain response to a stimulus from features of that stimulus [@naselaris2011].
For language, earlier encoding models mapped features of each word to the functional MRI response of each participant
separately, and revealed semantic maps that tile much of the cortex [@huth2016]. Later work used the internal states
of language models as features. The better a model predicts the next word, the better its states predict brain
responses to language [@schrimpf2021; @caucheteux2022].

Foundation models extend this from one data set to many. Trained on responses pooled across many individuals and
stimuli, they generalise to new stimuli and new individuals. In mouse visual cortex, such a model predicted responses
to kinds of stimuli absent from its training, and adapted to new animals with little data [@wang2025]. TRIBE v2
applies the same principle to the human cortex [@dascoli2026]. Trained on functional MRI from several hundred
participants exposed to video, audio and language, it predicts responses to new stimuli, tasks and participants. Run
on classic experiments of vision and language, it reproduces results established by measurement.

Such predictions can be tested. Sentences that an encoding model selected to drive or to suppress the human language
network did so in new participants [@tuckute2024]. None of the predictions in this study has been tested in this way.

Two further limits shape how the predictions are read. The first is reverse inference. A response in a region does not
identify the mental process behind it: the inference is only as strong as the region's selectivity for that process
[@poldrack2006]. The functional labels of Table 4 are therefore conventions, not evidence that a process took place.
The second is that an encoding model has no memory of the learner. It maps a stimulus to the response of an average
participant, and nothing in it depends on what that participant has learned. It describes the immediate response to a
text, not learning.

What this literature leaves open is the response to instruction. To the author's knowledge, encoding models have not
been applied to lesson texts that differ in pedagogy, and none links a predicted response to learning over time. This
study therefore keeps the two layers apart. Phase II predicts the immediate response to each text, and only the
plasticity model of Phase IV, which is an assumption, connects it to what learners do.

## 2.3 Scaffolding and cognitive offloading

Scaffolding, in its original sense, is support that lets a learner complete a task beyond their unaided reach
[@wood1976]. The tutor takes over only the elements the learner cannot yet manage, and withdraws as competence grows.
Ongoing diagnosis, support calibrated to the learner and fading are therefore its defining features. When the term
moved from tutors to software tools, these features were often neglected [@puntambekar2005].

Two findings explain why withdrawal matters. Guidance that helps novices can lose its value, or become harmful, for
learners with more knowledge: the expertise reversal effect [@kalyuga2003]. Worked examples help most early in
learning, which motivates fading their steps progressively into independent problem solving [@renkl2003]. How much
help to give, and when, has no general answer. Experiments with intelligent tutors give only partial answers to this
assistance dilemma [@koedinger2007], and learners offered help on demand often use it poorly [@aleven2003].

Cognitive offloading is the use of an external aid to reduce the mental demand of a task [@risko2016]. It improves
performance on the task at hand. Effortful processing, by contrast, improves memory. Information that learners
generate themselves is remembered better than information they read [@slamecka1978], and retrieving it from memory
helps later retention more than studying it again [@roediger2006; @rowland2014; @adesope2017]. The two findings meet
in the distinction between performance and learning. Conditions that raise performance during instruction can leave
durable learning unchanged or even lower it, and learners tend to mistake the first for the second [@soderstrom2015].

Tutoring, human or computer-based, raises learning relative to conventional instruction; meta-analyses agree on the
direction but not on the size [@vanlehn2011; @ma2014; @kulik2016]. Recent studies of generative AI in education find a
contrast between supplying answers and guiding. When secondary-school students could obtain answers freely, their
performance rose during practice but fell below that of students without access once access was removed
[@bastani2025]. When students revised essays with a chatbot, their scores improved more than with other kinds of
support, but their gains in knowledge and transfer did not [@fan2025]. Tools designed to guide rather than to answer
largely avoided the loss [@bastani2025] or produced larger gains than an active-learning class [@kestin2025].

What this literature leaves open is accumulation. The directions are well supported, but none of the AI studies
follows learners beyond a single course, and none of this literature shows how the effects compound over years or how
large each must be for the net outcome to reverse. This literature therefore supplies the directions the learner model
encodes (Section 3.4), not their sizes.

## 2.4 Knowledge tracing and retention

Intelligent tutoring systems estimate what a student knows from the sequence of their answers. Bayesian knowledge
tracing treats each skill as either known or not, with a fixed probability of learning it at each practice opportunity
and fixed probabilities of guessing and slipping [@corbett1995]. Logistic models instead predict the probability of a
correct answer from the student's ability, the difficulty of the skill and the amount of practice [@cen2006;
@pelanek2017]. The response model of this study (eq. 17) belongs to the logistic family. Its learning rate is compared
in Section 3.5 with the learning probabilities that knowledge tracing typically uses [@badrinath2021].

These models are fitted to the logs of a course and describe weeks or months of practice. Standard knowledge tracing
has no forgetting: a skill once learned stays learned [@corbett1995]. Models of memory do include forgetting. In an
activation-based model of practice, each repetition adds strength to a memory, and that strength decays as a power
function of time [@pavlik2005]. In several memory experiments, and in a reanalysis of Ebbinghaus's data, forgetting
followed a power function of time better than an exponential decay at a constant rate [@wixted1991].

Studies of retention measure what survives over years. About two-thirds to three-quarters of the basic science
knowledge taught in medical school is retained one year after instruction, and somewhat less than half after two
[@custers2010]. After an initial decline, Spanish learned at school remained stable for decades [@bahrick1984]. Over
the summer break, achievement falls by about a month's worth of schooling, most of all in mathematical computation and
spelling [@cooper1996].

What this literature leaves open is the link between how knowledge was taught and how long it lasts. Learner models
describe a course; retention studies record what survives without varying how it was acquired. A ten-year projection
must join the two by assumption, so this study uses them as anchors rather than as estimates (Section 3.5). The
comparison has a limit of form as well as of size: the model forgets at a constant rate, the form these experiments
did not favour, and the robustness analysis varies the rate and calendar of forgetting but not its form.

## 2.5 Synthesis and research gap

Table 1 draws the strands together.

Table: **Table 1.** The strands of the literature and their use in this study

| Strand | What it establishes | What it leaves open | How this study uses it |
|------------------|------------------------------------------|------------------------------------|------------------------------------|
| Models of human choice (2.1) | Language models predict human choices across many experiments; Centaur generalises to new tasks | Whether one can act as a learner over many sessions, fed its own choices | Centaur makes the learner's behavioural choices; an equation decides correctness (Section 3.4) |
| Models of neural response (2.2) | Encoding models predict cortical responses to new stimuli and new participants | The response to instruction; any link to learning; agreement with measurement | TRIBE v2 predicts the immediate response to each text; learning is modelled separately (Sections 3.3, 3.6) |
| Scaffolding and offloading (2.3) | Effort aids retention; offloading and support never withdrawn can undermine it; early AI studies agree | How the effects accumulate over years; how large each must be to reverse the outcome | Directions encoded in effort, adaptation and fading (Sections 3.4, 3.7) |
| Knowledge tracing and retention (2.4) | Learning per practice opportunity; retention after one year and over decades | How retention depends on the way knowledge was taught | Anchors for the learning and forgetting rates (Section 3.5) |
| Simulation and robustness (2.5) | Simulation suits long, nonlinear processes; results should be reported under every defensible choice | Validation of a simulated learner against students | Specification curve, falsification criteria and variance decomposition (Section 3.8) |

*Source: own elaboration, from the studies cited in Sections 2.1–2.5.*

To the author's knowledge, no published study joins these parts: a predicted cortical response to instructional
material, a simulated learner whose choices come from a model of human behaviour, and a projection over years whose
uncertainty is propagated. Each part alone answers a narrower question: how a text is processed, how a learner
progresses within a course, or what AI tutoring does within weeks. The question of this study, how three instructional
regimes differ over a decade and under which assumptions, needs all three.

It also needs a method, because no data exist to answer it. Simulation suits such questions. Its strengths are
internal validity and the study of longitudinal, nonlinear processes, and its main value lies in experimentation that
develops theory [@davis2007]. A simulation is only as credible as its treatment of assumptions, however. Sensitivity
analyses that vary one input at a time leave most combinations of inputs unexplored, and many published analyses do
just that [@saltelli2019]. In empirical research, results can depend on analytic choices that are rarely reported, and
specification curves and multiverse analyses respond by reporting a result under every defensible combination of
choices [@simonsohn2020; @steegen2016].

This study applies the same logic to a simulation. It varies modelling choices jointly rather than one at a time,
reports where a result changes sign, and tests its claims against controls and falsification criteria fixed before the
ten-year runs, recording every later change (Section 3.8). It does not validate the simulated learner against
students, which is the test the review of simulated learners calls for [@kaser2024]. Section 6.4 proposes the
measurements that would allow it.

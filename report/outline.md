# Report outline (deliverable D7)

The working plan for the report. `REPORT.md` is the specification (rubric, structure, body vs appendix); this file
turns it into sections, claims, exhibits and sources, and tracks what is drafted. Edit it freely: headings, order,
emphasis and claims are all yours to change, and the drafts follow this file.

Due **2026-09-30**. Drafting order: 3 → 4 → 5 and 6 → 2 → 1 → front matter → appendices → build.

---

## Conventions

- **Files.** One per top-level section: `00_front.md` (cover, abstract, executive summary, declaration, index),
  `01_introduction.md` … `06_esade.md`, `80_references.md`, `90_appendix.md`, `references.bib`, `apa.csl`.
  Headings carry their numbers in the source. Undrafted subsections read *In preparation.*
- **Build.** `uv run --no-project --with pypandoc-binary --with python-docx python report/build.py --pdf` writes
  `report/build/NeuroTutorSim_report_draft.docx` (and `.pdf`) in the ESADE format; with Word installed it also
  updates the index and writes the page and word count. Close the document in Word before rebuilding.
- **Workflow.** The author edits the drafts directly and commits before editing; `git diff` shows their changes.
  `<!-- MG: … -->` comments are answered in chat, not in the file.
- **No reference to the project brief** anywhere in the report text: it is an unofficial document. Thresholds,
  acceptance criteria, falsification criteria and scenario definitions are presented as this study's design and
  defined where they first matter; scope is stated positively. The labels F1-F6 may be used once §3.8 defines the
  six falsification criteria as this study's own (author, 2026-09-22), which keeps them aligned with
  `table6_falsification`. Before that section, a criterion is described rather than named.
- **Prose rules (binding).** Formal, analytical register. No rhetoric or filler, no stock adjectives
  ("crucial", "transformative"), no obvious conclusions. Every claim rests on reasoning, a number from
  `outputs/tables`, or a citation. Uncertain or hypothetical quantities carry their limitation in the same sentence.
- **Claims discipline.** `guide.md` §10 bounds what may be claimed; brief §15 wording throughout ("predicted
  cortical response", "simulated learner", "model-implied", "scenario contrast"); never "the brain learns",
  "AI causes", "digital twin".
- **Voice.** Impersonal by default; first person singular only for the author's own decisions.
- **Citations.** Pandoc keys (`[@austin2009]`), rendered in APA from `references.bib`. Only sources checked against
  Crossref or arXiv enter the file; the comment above each entry records how.
- **Equations** keep their code numbers, so that they match the code, the tables and the figure labels ("eq. 3").
  Each is written out where it first matters, labelled with that number; a forward reference names the section that
  writes it out. The numbering has gaps and will be renumbered at the end.
- **Exhibits.** Figures keep their output numbers, 1-8 (the images carry their titles). Tables are numbered in order of
  appearance. Every figure and table ends with a source line: *Source: own elaboration. …* (REPORT.md §2).
- **Notes.** `<!-- CLAUDE: … -->` are mine, `<!-- MG: … -->` the author's. Neither appears in the built document.

## Page budget

A4, Arial 11 pt, single spacing with 6 pt before and after, 30/25 mm margins: about 550 words per page of prose.
Target body **~37 pages** against the 40-page ceiling (figures and tables count); agreed 2026-09-22.

| Section | Pages | Of which exhibits | Prose words | Status |
|---|---|---|---|---|
| 1. Introduction | 3 | 0 | ~1,650 | — |
| 2. Literature Review | 5.5 | 0 | ~3,000 | — |
| 3. Methodology | 12.5 | ~3 | ~5,200 | 3.2 drafted and revised after review 1 (depth kept, detail to App. A) |
| 4. Results | 10 | ~5.5 | ~2,500 | — |
| 5. Discussion and Conclusions | 4.5 | 0 | ~2,500 | — |
| 6. Implications for the ESADE Data Department | 1.5 | 0 | ~800 | — |
| **Body** | **37** | **~8.5** | **~15,650** | |

---

## Front matter (not counted)

- **Cover.** Student name and master, project title, organisation, tutor, confidentiality, course (guidelines p. 10).
- **Abstract.** ≤ 250 words, paper-style: question, method, three results, one limitation.
- **Executive Summary.** 2-4 pages, compulsory. Four required elements: objective; methodology with its steps
  **and its data sources** (all generated, quantified); the academic framework; conclusions and the deliverable.
  Written last.
- **Declaration of AI assistance.** Required by the guidelines ("any assistance received … should be fully
  acknowledged"). Facts: the unit records were written by the author with Claude, under the author's review; the
  lesson texts and text controls were drafted with Claude Opus 5 and Claude Fable 5; code and report drafts had the
  same assistance. Method components (Centaur, Qwen2.5, TRIBE v2) are described in §3, not here.
- **Index.** With page numbers, and the page count and word count at its end.

## 1. Introduction (3 pp)

- **1.1 Motivation.** The cognitive consequences of AI tutoring are uncertain, and the evidence would take a decade
  to arrive; a computational laboratory makes the assumptions explicit in the meantime (brief §15).
- **1.2 Research questions.** Primary question and five secondary questions, stated as the study's own.
- **1.3 Approach and contribution.** A reproducible framework, not a verdict (brief §1.3). **No dataset existed**:
  state what was generated, quantified (30 units, 90 stimuli, 210 text controls, 8.7 GB of predictions, the
  Phase III episode count, 315 Phase V runs, 216 specification cells). This is the top band of *Level of difficulty*.
  <!-- CLAUDE: REPORT.md cites "1.2 million model-implied episodes"; recompute before quoting. -->
- **1.4 Scope and context.** MBA topics because the population of interest is business-school students; 30 units
  because of the computational budget; six scenarios; the ESADE Data Department context; all work the author's own.
- **1.5 Structure of the report.**

## 2. Literature Review (5.5 pp)

Four strands, each ending with what it leaves open for this study. Every citation is checked before it enters.

- **2.1 Foundation models of human cognition.** Centaur and Psych-101 [Binz et al., 2025]; LLMs as simulated
  participants and their limits. Sets up why Centaur chooses but does not answer (Section 3.4).
- **2.2 Foundation models of neural response.** TRIBE v2 [Banville et al., 2026] as an encoding model; shared core
  and readouts [Wang et al., 2025]; cortical parcellations and networks (Schaefer, Yeo). Sets up the non-negotiable
  separation of immediate response from learning.
- **2.3 Scaffolding and cognitive offloading.** Scaffolding and fading [Wood et al., 1976]; offloading
  [Risko & Gilbert, 2016]; desirable difficulties, retrieval practice [Rowland, 2014; Adesope et al., 2017];
  tutoring meta-analyses [VanLehn, 2011; Ma et al., 2014; Kulik & Fletcher, 2016]; the recent field evidence on
  generative-AI tutors versus answer-giving assistants. <!-- CLAUDE: candidates to verify, not yet cited. -->
- **2.4 Knowledge tracing and retention.** BKT [Corbett & Anderson, 1995]; retention of taught knowledge
  [Custers, 2010]. These supply the D27 calibration anchors.
- **2.5 Synthesis and gap.** No study joins predicted cortical response, a behaviourally calibrated learner and
  long-horizon uncertainty propagation; the specification-curve and multiverse literature frames the robustness
  design.

## 3. Methodology (12.5 pp)

State once, early: equation numbers follow the code and will be renumbered; every quantity is model-implied.

| Sub | Content | Exhibits | Sources |
|---|---|---|---|
| 3.1 Design overview and data generation | Two layers, five phases; what is generated, what is assumed; one learner, four arms, common random numbers; two-tier run design | Figure 1; Table 2 (or appendix) | `guide.md` §1-2, `table2_components` |
| **3.2 Phase I: the corpus** | Units, conditions, matching, validation, text controls | Table 1, Figure 2 | `table1_conditions`, `corpus_balance`, `tableS_semantic_coverage`, `tableS_near_duplicates`, `tableS_contradiction_judge` |
| 3.3 Phase II: predicted cortical response | TRIBE v2 on Colab L4, timing (eq. 4), Schaefer-400 / Yeo-7 (eq. 6-7), metrics (eq. 8-9), QC and gate 17, contrasts (eq. 10-13, 42), RSA (eq. 14), shuffled controls | — | `run_metadata.json`, `tribe_qc.json` |
| 3.4 Phase III: the simulated learner | State (eq. 15-16), episode protocol, response model (eq. 17-18), effort and effectiveness (eq. 19-20), updates (eq. 21-25); hybrid engine: Centaur chooses, eq. 17-18 answers; what the transcript models can and cannot do; observable history only | Table 3 (condensed, full in appendix) | `table3_parameters`, `engine_comparison`, root `CLAUDE.md` measurements |
| 3.5 Parameter provenance and calibration anchors | Which parameters are anchored; alpha and delta outside their published ranges, omega consistent; anchoring never changes a value | anchors table | `tableS_parameter_anchors`, `config/parameter_sources.yaml` |
| 3.6 Phase IV: plasticity | Eq. 28-33, hybrid mechanism D as main specification, the accumulator (N linear in Z), §8.7 outcomes | — | `guide.md` §6 |
| 3.7 Phase V: ten-year scenarios | Calendar and break forgetting (D4), soft limits (D3), six scenarios, Monte Carlo (eq. 35), SC (eq. 37), PrSup (eq. 38), G (eq. 39), frontier and tipping points (eq. 40) | — | `PLAN.md` D1-D7, D18 |
| 3.8 Validation, falsification and robustness | Gate 18, negative controls, specification curve (216 cells × 6 scenarios × 3 outcome weights; D24, D25 added after results, say so), variance decomposition (eq. 41), F1-F6, mechanism decomposition | — | `config/spec_curve.yaml`, `PLAN.md` D17-D25 |
| 3.9 Implementation and reproducibility | Repository, seeds, append-only logs, 126 tests, the D3 archive | — | `README.md`, D26 |

## 4. Results (10 pp)

| Sub | Claim to establish | Exhibits | Sources |
|---|---|---|---|
| 4.1 Immediate predicted cortical contrasts | Condition contrasts exist; after F1, F2 and F5 only scaffolding's DorsAttn, SalVentAttn and SomMot contrasts survive; no substitution-vs-traditional contrast does | Table 4 (network level), Figures 3-4 | `table4_*`, `table6_falsification`, `rsa_*` |
| 4.2 One term of simulated learning | Ordering scaffolding ≥ traditional > free choice > substitution; holds in all three parameter settings; Centaur changes help requests and C, not learning outcomes | — (Figure S3, S1 in appendix) | `tableS_phase3_outcomes`, `tableS_phase3_settings`, `engine_comparison` |
| 4.3 Ten-year scenario contrasts | Substitution and both free-choice rules negative on G at year 10; scaffolding scenarios positive | Table 5 (condensed), Figures 5-6 | `table5_*`, `fig5_*`, `fig6_*` |
| 4.4 Frontier and tipping points | Neutral at o = 0, harmful for o ≥ 0.5; G turns negative at o ≈ 0.10 [0.06, 0.14]; no sign change in e, f or forgetting | Figure 7a (7b in 4.7) | `tableS_tipping_points` |
| 4.5 Mechanisms | The scaffolding advantage runs through F; the substitution deficit through E (0.97 of the K contrast) | — | `tableS_mechanism_decomposition` |
| 4.6 Robustness | Four of five AI scenarios keep the sign of median year-10 G in all 648 specifications; scaffolding without fading fails in exactly 216, the `adaptation=none` level, median 0.000000; F1-F6 verdicts, including the failures; G is 68% scenario, 29% learner | Figure 8a, sign-stability table, Table 6 (falsification) | `tableS_sign_stability`, `table6_*`, `tableS_variance_decomposition` |
| 4.7 Neural trajectories (exploratory) | Control-network d keeps its sign in 59.2% of 62,208 specifications; adaptation irrelevant to it | Figures 7b, 8b | `table5_neural_d_v_main`, `fig8b_*` |

## 5. Discussion and Conclusions (4.5 pp)

- **5.1 Derived versus assumed.** The three claims of REPORT.md §7: the no-fade advantage is an assumption
  (`support.adaptation`); the rapid-fade benefit rests on support withdrawal, a mechanism; the substitution deficit
  is robust in direction and bounded in magnitude (K* = 0.59 against 0.99).
- **5.2 Which assumptions drive divergence.** Variance decomposition; plasticity constants barely move G but
  dominate the neural outcome.
- **5.3 Relation to empirical evidence.** Direction consistent with the offloading and tutoring literature; magnitudes
  not comparable (anchors).
- **5.4 Limitations.** Lifted from `PLAN.md` §7, grouped: corpus, encoding model, learner engine, calibration,
  neural side.
- **5.5 Conclusions.** One paragraph per research question.

## 6. Implications for the ESADE Data Department (1.5 pp)

An application plan, not a compliment (REPORT.md §6): (1) what the department gets now: repository, D3 archive and
DOI, a validation layer that can be re-pointed; (2) the publication path; (3) what it changes about how AI in
teaching is evaluated; (4) the next measurement: `support.adaptation`, then the learning and forgetting rates.

## Appendices (not counted)

Lettered in order of first reference. A. Corpus validation details (**drafted**: equivalence tests, the coverage
review list, construction of the contradiction check). Planned: update equations in full and the Phase V
deviations; Table 2 (if not in the body), full Tables 3 and 5, Table 4 at parcel level; supplementary tables and
Figures S1-S3; specification list and ranks; reproducibility (commands, run tags, the D3 manifest); data dictionary.

---

## Open questions

Answered 2026-09-22: detail level (keep the depth, move validation detail to Appendix A); assistance (units written
by the author with Claude, under the author's review; texts drafted with Claude Opus 5 and Claude Fable 5); scope
(MBA for business-school students, 30 units for compute); contribution (all the author's own); equations (code
numbers, written at first use); length (~37 pages).

Answered 2026-09-23: the cover (ESADE Data Department; tutors Carlos Carrasco-Farré and Marc Arnal Torrens;
confidentiality left off, not an issue for now);
the criteria may carry the labels F1-F6 once §3.8 defines them; the manual reviews (the nine texts of Table A2 and
the flagged `npv_002`) are deferred and reported as outstanding, to be done if time permits.

Still open:

- **Title.** The working title stands unless changed.
- **Confidentiality.** Left off the cover for now. If it is ever claimed, the guidelines require two signed copies
  of the agreement, and §6's publication path (the archived dataset with its DOI, and a paper) would need the
  tutors' agreement or an embargo instead.

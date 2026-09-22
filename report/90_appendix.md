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
the acceptance threshold of 0.50. Their review asks whether the explanation teaches the method that the unit's
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

This review is outstanding and will be carried out if time permits. Two features of the list bear on what it can
find. First, the scores are not extreme: averaged over the three conditions, unit coverage runs from 0.573
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
way to settle the question, and until that is done the limitation stands as stated in Section 3.2.4. <!-- CLAUDE: the author said on 2026-09-23 that they had checked the texts but did not give the verdict. Ask for it
(per text or as a blanket 'all adequate') and then replace the 'outstanding' wording here and in §3.2.4. -->

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

**Result.** Table A3 reports the validated and unvalidated parts separately. The one text flagged by the unvalidated
questions (`npv_002`, scaffolding) was returned with an affirmative verdict and no reason. A check of its worked
example, reference answer and leakage against the unit record found no error and the text was not changed; a manual
review of it is outstanding, as for the texts of Section A.2.

Table: **Table A3.** Contradiction screening: validation and findings

| Question | Standing | Texts | Result |
|---|---|---|---|
| Contradiction | Validated | 30 incorrect-but-fluent texts | 27 flagged (sensitivity 0.90) |
| Contradiction | Validated | 60 primary texts, traditional and substitution | 0 flagged (specificity 1.00) |
| Contradiction | Not applicable | 30 primary texts, scaffolding | — |
| Unsupported assertion | Unvalidated | 90 primary texts | 1 flagged |
| Causal claim | Unvalidated | 90 primary texts | 0 flagged |

*Source: own elaboration (`outputs/tables/tableS_contradiction_judge.csv`).*

# stimuli/

One markdown file per unit and condition: `<condition>/<unit_id>.md`, front matter between `---`
lines, then `# Section` headings in the exact order `corpus.SECTIONS` requires:

| condition | sections | the canonical answer |
|---|---|---|
| traditional | Explanation, Problem, Hints, Worked solution | only in Worked solution |
| ai_scaffolding | Explanation, Problem, Diagnostic questions, Hints | nowhere |
| ai_substitution | Explanation, Problem, Worked solution | only in Worked solution |

Rules: the Explanation is 250-400 words and contains the worked example; the Problem section contains
the unit's canonical problem text verbatim; the Hints match the unit JSON; `Diagnostic questions` asks at
least one question per documented distractor, so it covers the same errors as the unit JSON's
`problem.distractors[].note` (which is what reaches the tutor prompt as `$distractor_notes`); and all
three files are matched on duration within 10 % of the traditional anchor
(`python -m neurotutorsim.corpus` reports it).
These files are the tutor's side only (no scripted learner) because they are also the TRIBE inputs.
At runtime the learner reads the condition's Explanation and nothing else of the file: the `# Worked
solution` section is never part of the initial reading, so it cannot be seen before the first attempt
(`episode.run_episode` passes `Stimulus.explanation`). Hints and worked solution come from the unit JSON;
scaffolding and substitution tutor turns are generated live by the LLM.

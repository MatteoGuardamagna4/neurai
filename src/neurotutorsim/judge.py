"""Phase I contradiction check (brief §5.4, third bullet; PLAN.md D22, D28).

    python -m neurotutorsim.judge                      # the 90 primary stimuli
    python -m neurotutorsim.judge --controls incorrect # its sensitivity check (see below) - run this too
    python -m neurotutorsim.judge --limit 9            # a sample, to check the server and the parser

The brief asks for "a separate judge model to identify factual contradictions, missing assumptions, or invalid
causal statements". `corpus.py` already recomputes every number deterministically, so this does NOT re-check
arithmetic: the validators own that. What a judge adds is what no validator sees - whether the PROSE contradicts
the unit's own reference, asserts something the inputs do not support, or makes an unlicensed causal claim.

**The screen must be shown to fire.** `0 of 90 flagged` is not evidence the corpus is clean unless the same judge
catches texts known to be wrong, and the first version of this module failed exactly there: asked the three §5.4
questions abstractly in one call, Qwen2.5-3B answered "no" to everything and missed all 30 incorrect-but-fluent
texts, one of which states 2,400 units against a reference of 6,000 given in the same prompt. `--controls incorrect`
is therefore not optional garnish: it is what makes the headline number mean anything, and `judge_summary.json`
reports `sensitivity_on_incorrect_texts` beside it.

Two checks, with different standing:

- **CONTRADICTION** is validated. It is posed as extract-then-compare ("read off the final answer, then compare it"),
  which the same 3B model handles. It applies only where the condition's text may state a final answer
  (`corpus.ANSWER_ALLOWED_IN`): `ai_scaffolding` withholds the answer by construction, so the check is recorded as
  not applicable there rather than as a pass or a failure - see `answer_check_applies`.
- **UNSUPPORTED and CAUSAL** are unvalidated. The corpus has ground truth for a wrong final answer but none for
  these, so they have no sensitivity check and are a prompt for human reading, never evidence of absence.

Independence. The stimuli were written by Claude; the judge is whatever `tutor.model` serves (Qwen2.5-3B-Instruct
locally), a different model from the author, which is the independence §5.4 asks for. It is not independent of the
tutor, harmlessly, since the tutor never writes stimuli. The judge is small, so its verdicts are a screen that routes
texts to human review (§5.5), never an acceptance criterion: `review_queue.json` is the output that matters, and a
text that could not be judged is queued, never passed.

Verdicts are cached per (stimulus, prompt hash) in `data/processed/judge/verdicts.jsonl`, append-only, so a rerun is
free, an interrupted pass resumes, and any prompt change invalidates rather than reuses.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

from .corpus import ANSWER_ALLOWED_IN, CONDITIONS, Stimulus, Unit, load_units, load_stimuli, load_text_controls
from .tutor import Tutor, TutorError

# --- check 1: the contradiction check, as an EXTRACT-THEN-COMPARE task -------------------------------------------
# Measured 2026-09-21: asking a 3B model the three §5.4 questions abstractly in one call makes it answer "no" to
# everything - it missed all 30 incorrect-but-fluent texts, including one stating 2,400 units against a reference of
# 6,000 in the same prompt. Split into "read off the final answer, then compare it" the same model got 8 of 8 on a
# probe of four wrong and four correct texts. Concrete beats abstract; the sensitivity check below keeps that honest.
ANSWER_SYSTEM = (
    "You are checking a lesson text against an authoritative reference answer. Your only job is to decide whether "
    "the final numeric answer the lesson arrives at is the same as the reference answer. Answer with the two lines "
    "requested and nothing else."
)
ANSWER_USER = """Reference answer for this problem: {answer}

Lesson text:
---
{text}
---

Find the final answer the lesson text arrives at, then compare it with the reference answer above.

FINAL_ANSWER_IN_TEXT: <the number the lesson concludes with>
MATCHES_REFERENCE: yes|no"""

# --- checks 2 and 3: the softer §5.4 questions ------------------------------------------------------------------
# UNVALIDATED. The corpus has ground truth for a wrong final answer (the incorrect-but-fluent texts) but none for
# "unsupported assertion" or "unlicensed causal claim", so these two have no sensitivity check and are reported as
# a prompt for human reading, never as evidence of absence.
CLAIMS_SYSTEM = (
    "You are a careful reviewer of teaching materials for an MBA course. Judge only the two questions asked. "
    "Do not check the arithmetic and do not comment on style, length or tone."
)
CLAIMS_USER = """Lesson text:
---
{text}
---

The problem it teaches: {problem}
Its documented misconception, which the lesson may legitimately describe and warn against: {misconception}

1. UNSUPPORTED - does the text assert something the stated inputs do not support?
2. CAUSAL - does it make a causal claim the material does not license?

Reply in exactly this format and nothing else:
UNSUPPORTED: yes|no - <at most 20 words>
CAUSAL: yes|no - <at most 20 words>"""

CHECKS = ("contradiction", "unsupported", "causal")
# the separator must not match a newline: with `[\s-]*` an empty reason swallows the next line
_LINE = re.compile(r"^[ \t]*(CONTRADICTION|UNSUPPORTED|CAUSAL)[ \t]*:[ \t]*(yes|no)\b[ \t.-]*(.*)$", re.I | re.M)


def parse_answer(reply: str) -> tuple[bool | None, str]:
    """(contradiction, the answer the model read off). `None` when the reply does not answer, never a silent `no`."""
    m = re.search(r"^[ 	]*MATCHES_REFERENCE[ 	]*:[ 	]*(yes|no)\b", reply or "", re.I | re.M)
    got = re.search(r"^[ 	]*FINAL_ANSWER_IN_TEXT[ 	]*:[ 	]*(.+)$", reply or "", re.I | re.M)
    found = " ".join(got.group(1).split())[:80] if got else ""
    return (None if not m else m.group(1).lower() == "no"), found


def parse(reply: str) -> dict:
    """The three verdicts and their reasons. A check the model did not answer is `None`, never silently `no`:
    an unparsed reply must reach the review queue, not pass by default."""
    out = {c: None for c in CHECKS}
    reasons = {c: "" for c in CHECKS}
    for m in _LINE.finditer(reply or ""):
        key = m.group(1).lower()
        out[key] = m.group(2).lower() == "yes"
        reasons[key] = " ".join(m.group(3).split())[:200]
    return {"flags": out, "reasons": reasons, "parsed": all(v is not None for v in out.values())}


def answer_prompt(unit: Unit, stim: Stimulus) -> str:
    return ANSWER_USER.format(answer=unit.problem.render(unit.problem.answer), text=stim.body.strip())


def claims_prompt(unit: Unit, stim: Stimulus) -> str:
    return CLAIMS_USER.format(text=stim.body.strip(), problem=" ".join(unit.problem.text.split()),
                              misconception=" ".join(unit.misconception.split()))


def prompt_hash(unit: Unit, stim: Stimulus) -> str:
    """One key over both calls, so any prompt change invalidates the cached verdict rather than reusing it."""
    import hashlib

    parts = [CLAIMS_SYSTEM, claims_prompt(unit, stim)]
    if answer_check_applies(stim):
        parts = [ANSWER_SYSTEM, answer_prompt(unit, stim)] + parts
    blob = chr(10).join(parts)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def answer_check_applies(stim: Stimulus) -> bool:
    """Is the answer comparison meaningful for this condition?

    No for `ai_scaffolding`: `corpus.ANSWER_ALLOWED_IN` gives it no section that may state the final answer, so the
    text HAS no final answer to compare. Measured 2026-09-21: asked anyway, the judge reads off some other number -
    for be_001 it returned the misconception's own 2,400 units, quoted in the warning - and every one of the six
    scaffolding texts judged came back a false contradiction, against zero in the other two conditions. A check that
    cannot apply is recorded as not applicable, never as a pass and never as a failure.
    """
    return bool(ANSWER_ALLOWED_IN.get(stim.condition, ()))


def judge_one(tutor: Tutor, unit: Unit, stim: Stimulus) -> dict:
    """Up to two calls: the validated answer comparison where it applies, then the two unvalidated claim checks."""
    contradiction, found, a_reply, seconds, model = None, "", "", None, tutor.cfg.get("model")
    applies = answer_check_applies(stim)
    if applies:
        a_reply, a_meta = tutor.chat(ANSWER_SYSTEM, answer_prompt(unit, stim))
        contradiction, found = parse_answer(a_reply)
        seconds, model = a_meta.get("seconds"), a_meta.get("model")
    c_reply, c_meta = tutor.chat(CLAIMS_SYSTEM, claims_prompt(unit, stim))
    p = parse(c_reply)
    # `parsed` asks only about the checks that were actually run
    answered = [p["flags"]["unsupported"], p["flags"]["causal"]] + ([contradiction] if applies else [])
    return {"stimulus_id": stim.stimulus_id, "unit_id": unit.unit_id, "condition": stim.condition,
            "variant": getattr(stim, "variant", "primary"), "contradiction": contradiction,
            "contradiction_applicable": applies,
            "unsupported": p["flags"]["unsupported"], "causal": p["flags"]["causal"],
            "contradiction_reason": ("" if not applies else
                                     f"text concludes {found}, reference {unit.problem.render(unit.problem.answer)}"
                                     if contradiction else ""),
            "unsupported_reason": p["reasons"]["unsupported"], "causal_reason": p["reasons"]["causal"],
            "answer_in_text": found, "parsed": all(v is not None for v in answered),
            "reply": a_reply + chr(10) + "---" + chr(10) + c_reply,
            "model": model or c_meta.get("model"), "prompt_sha256": prompt_hash(unit, stim),
            "seconds": seconds if seconds is not None else c_meta.get("seconds")}


def flagged(rows) -> list[dict]:
    """Texts for the §5.5 manual review queue: any check answered yes, or a reply that would not parse."""
    return [r for r in rows if (not r.get("parsed")) or any(r.get(c) for c in CHECKS)]


def summarize(rows) -> dict:
    n = len(rows)
    out = {"n_texts": n, "n_unparsed": sum(1 for r in rows if not r.get("parsed")),
           "n_review_queue": len(flagged(rows))}
    by_variant = {}
    for r in rows:
        v = r.get("variant", "primary")
        by_variant.setdefault(v, [0, 0])
        by_variant[v][0] += 1
        by_variant[v][1] += int(any(r.get(c) for c in CHECKS))
    out["by_variant"] = {k: {"n": v[0], "flagged": v[1]} for k, v in sorted(by_variant.items())}
    if "incorrect" in by_variant:  # the sensitivity check: the screen must fire on texts known to be wrong
        n_inc, hit = by_variant["incorrect"]
        out["sensitivity_on_incorrect_texts"] = round(hit / n_inc, 3) if n_inc else None
    for c in CHECKS:
        out[f"n_{c}"] = sum(1 for r in rows if r.get(c))
    by = {}
    for r in rows:
        by.setdefault(r["condition"], [0, 0])
        by[r["condition"]][0] += 1
        by[r["condition"]][1] += int(any(r.get(c) for c in CHECKS))
    out["by_condition"] = {k: {"n": v[0], "flagged": v[1]} for k, v in sorted(by.items())}
    return out


def read_cache(path: Path) -> dict:
    if not path.exists():
        return {}
    out = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            r = json.loads(line)
            out[(r["stimulus_id"], r.get("prompt_sha256"))] = r
    return out


def main(argv=None) -> int:
    from .simulate import load_config

    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", default="config/default.yaml")
    ap.add_argument("--limit", type=int, help="judge only the first N texts (a server and parser check)")
    ap.add_argument("--controls", choices=("incorrect", "reworded", "all"),
                    help="also judge text controls. `incorrect` is the SENSITIVITY CHECK: the 30 incorrect-but-fluent "
                         "texts reach the misconception's answer, so a judge with any discriminative power must flag "
                         "them. Without that check, `0 of 90 flagged` on the primaries is not evidence the texts are "
                         "clean - a model that always answers `no` gives the same result.")
    ap.add_argument("--out", default="data/processed/judge")
    ap.add_argument("--timeout-s", type=float, default=90.0, dest="timeout_s",
                    help="per-call budget; a text that exceeds it is skipped and queued for review")
    args = ap.parse_args(argv)
    root = Path(args.config).resolve().parent.parent
    cfg = load_config(Path(args.config))
    if cfg["tutor"].get("provider") == "fake":
        print("tutor.provider is `fake`: the §5.4 judge needs a real server", file=sys.stderr)
        return 2
    units = load_units(root / cfg["run"]["units_dir"])
    stimuli = load_stimuli(root / cfg["run"]["stimuli_dir"], units)
    texts = [(units[u], s) for (u, _), s in sorted(stimuli.items())]
    if args.controls:
        controls = load_text_controls(root / cfg["run"]["stimuli_dir"], units, stimuli)
        want = {"incorrect": lambda v: v == "incorrect", "reworded": lambda v: v != "incorrect",
                "all": lambda v: True}[args.controls]
        for (u, _c, variant), s in sorted(controls.items()):
            if want(variant):
                texts.append((units[u], s))
    if args.limit:
        texts = texts[: args.limit]
    out_dir = root / args.out
    out_dir.mkdir(parents=True, exist_ok=True)
    cache_path = out_dir / "verdicts.jsonl"
    cache = read_cache(cache_path)
    # the judge makes 90 independent one-shot calls, so a hung one should fail fast and be skipped rather
    # than stall the pass; the tutor's own 60 s default is for an interactive turn inside an episode
    tcfg = {**cfg["tutor"], "timeout_s": float(args.timeout_s), "max_attempts": 2}
    tutor = Tutor(tcfg, root / cfg["run"]["prompts_dir"])
    rows, started, fresh, errors = [], time.time(), 0, 0
    for i, (unit, stim) in enumerate(texts, 1):
        h = prompt_hash(unit, stim)  # covers both calls, so a prompt change invalidates the cached verdict
        hit = cache.get((stim.stimulus_id, h))
        if hit is not None:
            rows.append(hit)
            continue
        try:
            row = judge_one(tutor, unit, stim)
        except TutorError as exc:
            # One unreachable or hung text must not cost the other 89. A text that cannot be judged is not a text
            # that passed: it is recorded with `parsed` false so `flagged` routes it to the manual review queue.
            print(f"  {stim.stimulus_id}: {exc}", file=sys.stderr)
            row = {"stimulus_id": stim.stimulus_id, "unit_id": unit.unit_id, "condition": stim.condition,
                   "variant": getattr(stim, "variant", "primary"), **{c: None for c in CHECKS},
                   **{f"{c}_reason": "" for c in CHECKS}, "parsed": False, "reply": "",
                   "contradiction_applicable": answer_check_applies(stim), "answer_in_text": "",
                   "error": " ".join(str(exc).split())[:300], "model": tutor.cfg.get("model"),
                   "prompt_sha256": None, "seconds": None}
            errors += 1
        with cache_path.open("a", encoding="utf-8") as f:  # append before anything else can fail
            f.write(json.dumps(row) + "\n")
        rows.append(row)
        fresh += 1
        if fresh % 10 == 0 or i == len(texts):
            print(f"  {i}/{len(texts)} ({fresh} new, {time.time() - started:.0f}s)", flush=True)
    summary = {**summarize(rows), "n_new_calls": fresh, "n_errors": errors, "model": cfg["tutor"]["model"],
               "recorded_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    (out_dir / "judge_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    queue = flagged(rows)
    (out_dir / "review_queue.json").write_text(json.dumps(queue, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    if queue:
        print(f"\n{len(queue)} text(s) for manual review (§5.5): "
              + ", ".join(sorted(r["stimulus_id"] for r in queue))[:400])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Phase I contradiction check (brief §5.4, third bullet; PLAN.md D22, D28).

    python -m neurotutorsim.judge --limit 9          # a sample, to check the server and the parser
    python -m neurotutorsim.judge                    # all 90 primary stimuli
    python -m neurotutorsim.judge --variants         # the 180 reworded texts as well

The brief asks for "a separate judge model to identify factual contradictions, missing assumptions, or invalid
causal statements". `corpus.py` already recomputes every number deterministically, so this does NOT re-check
arithmetic: the validators own that and a 3B model would only add noise to it. What a judge can add is the part no
validator sees - whether the prose CONTRADICTS the unit's own reference solution, asserts something the stated
inputs do not support, or makes a causal claim the material does not license.

Independence. The stimuli were written by Claude; the judge is whatever `tutor.model` serves (Qwen2.5-3B-Instruct
locally), a different model from the author, which is the independence §5.4 is asking for. It is NOT independent of
the tutor, which is the same served model - harmless here, because the tutor never writes the stimuli. The judge is
small, so its verdicts are a screen that routes texts to human review, never an acceptance criterion on their own:
`review_queue` is the output that matters, and the §5.5 action for a failed check is manual inspection.

Everything is cached per (stimulus, prompt hash) in `data/processed/judge/verdicts.jsonl`, append-only, so a rerun
costs nothing and an interrupted pass resumes.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

from .corpus import CONDITIONS, Stimulus, Unit, load_units, load_stimuli, load_text_controls
from .tutor import Tutor, TutorError

SYSTEM = (
    "You are a careful reviewer of teaching materials for an MBA course. You are given a lesson text and, "
    "separately, the authoritative reference solution for the problem it teaches. Judge ONLY whether the lesson "
    "text is consistent with that reference. Do not re-derive the arithmetic and do not comment on style, length "
    "or tone."
)
USER = """Lesson text:
---
{text}
---

Authoritative reference for this unit:
  Problem: {problem}
  Correct answer: {answer}
  Worked solution: {worked}
  Documented misconception (a WRONG way of thinking that the lesson may legitimately describe and warn against): {misconception}

Answer these three questions about the lesson text:
1. CONTRADICTION - does it state anything that contradicts the reference solution or the correct answer?
2. UNSUPPORTED - does it assert something the stated inputs do not support?
3. CAUSAL - does it make a causal claim the material does not license?

Reply in exactly this format and nothing else:
CONTRADICTION: yes|no - <at most 20 words>
UNSUPPORTED: yes|no - <at most 20 words>
CAUSAL: yes|no - <at most 20 words>"""

CHECKS = ("contradiction", "unsupported", "causal")
# the separator must not match a newline: with `[\s-]*` an empty reason swallows the next verdict line
_LINE = re.compile(r"^[ \t]*(CONTRADICTION|UNSUPPORTED|CAUSAL)[ \t]*:[ \t]*(yes|no)\b[ \t.-]*(.*)$", re.I | re.M)


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


def prompt_for(unit: Unit, stim: Stimulus) -> str:
    return USER.format(text=stim.body.strip(), problem=" ".join(unit.problem.text.split()),
                       answer=unit.problem.render(unit.problem.answer),
                       worked=" ".join(unit.worked_solution.split()),
                       misconception=" ".join(unit.misconception.split()))


def judge_one(tutor: Tutor, unit: Unit, stim: Stimulus) -> dict:
    reply, meta = tutor.chat(SYSTEM, prompt_for(unit, stim))
    p = parse(reply)
    return {"stimulus_id": stim.stimulus_id, "unit_id": unit.unit_id, "condition": stim.condition,
            "variant": getattr(stim, "variant", "primary"), **{c: p["flags"][c] for c in CHECKS},
            **{f"{c}_reason": p["reasons"][c] for c in CHECKS}, "parsed": p["parsed"], "reply": reply,
            "model": meta.get("model"), "prompt_sha256": meta.get("prompt_sha256"), "seconds": meta.get("seconds")}


def flagged(rows) -> list[dict]:
    """Texts for the §5.5 manual review queue: any check answered yes, or a reply that would not parse."""
    return [r for r in rows if (not r.get("parsed")) or any(r.get(c) for c in CHECKS)]


def summarize(rows) -> dict:
    n = len(rows)
    out = {"n_texts": n, "n_unparsed": sum(1 for r in rows if not r.get("parsed")),
           "n_review_queue": len(flagged(rows))}
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
    ap.add_argument("--variants", action="store_true", help="also judge the reworded text controls")
    ap.add_argument("--out", default="data/processed/judge")
    args = ap.parse_args(argv)
    root = Path(args.config).resolve().parent.parent
    cfg = load_config(Path(args.config))
    if cfg["tutor"].get("provider") == "fake":
        print("tutor.provider is `fake`: the §5.4 judge needs a real server", file=sys.stderr)
        return 2
    units = load_units(root / cfg["run"]["units_dir"])
    stimuli = load_stimuli(root / cfg["run"]["stimuli_dir"], units)
    texts = [(units[u], s) for (u, _), s in sorted(stimuli.items())]
    if args.variants:
        controls = load_text_controls(root / cfg["run"]["stimuli_dir"], units, stimuli)
        for (u, _c, _v), s in sorted(controls.items()):
            texts.append((units[u], s))
    if args.limit:
        texts = texts[: args.limit]
    out_dir = root / args.out
    out_dir.mkdir(parents=True, exist_ok=True)
    cache_path = out_dir / "verdicts.jsonl"
    cache = read_cache(cache_path)
    tutor = Tutor(cfg["tutor"], root / cfg["run"]["prompts_dir"])
    rows, started, fresh = [], time.time(), 0
    for i, (unit, stim) in enumerate(texts, 1):
        import hashlib

        h = hashlib.sha256((SYSTEM + "\n" + prompt_for(unit, stim)).encode("utf-8")).hexdigest()
        hit = cache.get((stim.stimulus_id, h))
        if hit is not None:
            rows.append(hit)
            continue
        try:
            row = judge_one(tutor, unit, stim)
        except TutorError as exc:
            print(f"stopped at {stim.stimulus_id}: {exc}", file=sys.stderr)
            break
        with cache_path.open("a", encoding="utf-8") as f:  # append before anything else can fail
            f.write(json.dumps(row) + "\n")
        rows.append(row)
        fresh += 1
        if fresh % 10 == 0 or i == len(texts):
            print(f"  {i}/{len(texts)} ({fresh} new, {time.time() - started:.0f}s)", flush=True)
    summary = {**summarize(rows), "n_new_calls": fresh, "model": cfg["tutor"]["model"],
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

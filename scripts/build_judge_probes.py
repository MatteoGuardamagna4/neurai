"""Build the validation set for the two unvalidated §5.4 judge checks (PLAN.md D30).

    uv run python scripts/build_judge_probes.py            # write stimuli/judge_probes/, re-checking every file
    uv run python scripts/build_judge_probes.py --check     # verify only, write nothing

The contradiction check has ground truth (the 30 incorrect-but-fluent texts); UNSUPPORTED and CAUSAL have none, so
their verdicts are reported as unvalidated. This script makes ground truth for them the same way: one sentence from
`data/judge_probes.json` is appended to the Explanation of a unit's traditional primary, and nothing else changes.

    unsupported  asserts a quantity or fact the unit never states and that cannot be derived from it  -> must flag
    causal       asserts a causal relation the material does not license                              -> must flag
    background   standard domain knowledge a lesson may legitimately state (a hard negative)          -> must NOT flag

The hard negatives matter: a lesson is entitled to assert background the problem does not state - the one primary the
judge ever flagged, `npv_002`, was flagged for exactly such a sentence. Without them the sensitivity of these checks
would be measured on an easier task than the one they actually face.

These texts are judge inputs only. They are not TRIBE stimuli and no simulated learner reads them: `corpus.load_stimuli`
and `corpus.load_text_controls` both enumerate their files explicitly, so `judge_probes/` is invisible to them.
"""
import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from neurotutorsim import corpus  # noqa: E402
from neurotutorsim.judge import PROBE_KINDS, check_probe  # noqa: E402

PROBES = ROOT / "data" / "judge_probes.json"
OUT = ROOT / "stimuli" / "judge_probes" / "traditional"


def render(primary_path: Path, unit_id: str, kind: str, sentence: str) -> str:
    text = primary_path.read_text(encoding="utf-8")
    head, body = text.split("---", 2)[1], text.split("---", 2)[2]
    meta = [f"stimulus_id: {unit_id}_traditional__probe_{kind}", f"unit_id: {unit_id}",
            "condition: traditional", f"variant: probe_{kind}"]
    m = re.search(r"(?<=\n# Explanation\n)(.*?)(?=\n# )", body, re.S)
    if not m:
        raise ValueError(f"{primary_path}: no explanation section followed by another section")
    explanation = m.group(1).rstrip() + " " + sentence  # the sentence closes the explanation's last paragraph
    _ = head  # the primary's front matter is replaced, not reused
    body = body[: m.start()] + explanation + "\n\n" + body[m.end():].lstrip("\n")
    return "---\n" + "\n".join(meta) + "\n---\n" + body.strip("\n") + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="verify the files on disk without writing")
    args = ap.parse_args(argv)
    units = corpus.load_units(ROOT / "data" / "units")
    stimuli = corpus.load_stimuli(ROOT / "stimuli", units)
    probes = json.loads(PROBES.read_text(encoding="utf-8"))["probes"]
    missing = sorted(set(units) - set(probes))
    if missing:
        print(f"no probe sentences for {len(missing)} units: {', '.join(missing)}", file=sys.stderr)
        return 2
    OUT.mkdir(parents=True, exist_ok=True)
    errors, written = [], 0
    for unit_id in sorted(units):
        primary = stimuli[(unit_id, "traditional")]
        for kind in PROBE_KINDS:
            sentence = probes[unit_id].get(kind)
            if not sentence:
                errors.append(f"{unit_id}: no `{kind}` sentence")
                continue
            path = OUT / f"{unit_id}__probe_{kind}.md"
            text = render(primary.path, unit_id, kind, sentence)
            if not args.check and text != (path.read_text(encoding="utf-8") if path.exists() else None):
                path.write_text(text, encoding="utf-8", newline="\n")
                written += 1
            if not path.exists():
                errors.append(f"{path.name}: missing (run without --check)")
                continue
            errors += check_probe(corpus.parse_stimulus(path), primary, units[unit_id], sentence)
    if errors:
        print("probe validation failed:\n  " + "\n  ".join(errors), file=sys.stderr)
        return 1
    n = len(units) * len(PROBE_KINDS)
    print(f"{n} probes ({len(units)} units x {len(PROBE_KINDS)} kinds) valid in {OUT.relative_to(ROOT)}"
          f"{'' if args.check else f'; {written} written'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

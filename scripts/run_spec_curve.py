"""Run the specification curve's rerun levels (brief §10.4, PLAN.md S13): one Phase V run per combination.

    uv run python scripts/run_spec_curve.py --dry-run          # list the 216 cells and their tags
    uv run python scripts/run_spec_curve.py                    # run them one after another (each resumable)

The levels and their plausibility ranks come from config/spec_curve.yaml, which must be approved (the ranks are fixed
before results exist). Post hoc levels (reading speed, network weights, TRIBE metric, winsorising, mechanism, outcome
weights) need no run: they are evaluated later on each run's saved accumulators.
"""
from __future__ import annotations

import argparse
import itertools
import json
import subprocess
import sys
import time
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
BREAK_SCALE = {"weekly_break_0.25": "0.25", "weekly_break_0.1": "0.1", "weekly_break_1.0": "1.0"}
EFFORT_SETS = {"drawn": [], "fixed_low": ["effort.a1=0.9", "effort.a2=0.6", "effort.a3=0.7", "effort.a4=1.5"],
               "fixed_high": ["effort.a1=1.5", "effort.a2=1.0", "effort.a3=1.3", "effort.a4=2.5"]}
# eq. 20 adaptation per protocol (PLAN.md D25). `authored` emits no override because it IS the config's value;
# `halved` moves each protocol half its distance to the three-protocol mean 0.4833; `none` puts all three at the
# mean, removing the contrast while leaving the mean level of F alone.
#
# Every level carries a tag suffix, `authored` included (D29). It did not at first, so that the 72 runs predating
# this dimension could serve as its `authored` cells - but those 72 ran five scenarios, before `free_choice_centaur`
# was fitted (D18), and a cell that lacks a scenario the others have cannot sit on the same curve. Runs are
# append-only, and `longitudinal.py` refuses a resume whose scenarios changed, so the authored level is re-run under
# its own tags rather than extended. The old unsuffixed runs stay on disk as superseded records.
ADAPTATION_SETS = {
    "authored": [],
    "halved": ["support.adaptation.traditional=0.42", "support.adaptation.ai_scaffolding=0.69",
               "support.adaptation.ai_substitution=0.34"],
    "none": ["support.adaptation.traditional=0.48", "support.adaptation.ai_scaffolding=0.48",
             "support.adaptation.ai_substitution=0.48"],
}


def specifications(spec: dict) -> list[dict]:
    """Every combination of the rerun levels, with its CLI arguments, tag and tier (the highest rank among its levels).
    "per_episode_no_breaks" is the Phase III convention: no summer break, and forgetting per episode whatever the
    exposure (reference_episodes_per_week = the run's own episodes per week)."""
    r = spec["reruns"]
    adaptation = r.get("adaptation", {"authored": 1})
    out = []
    for form, forget, epw, effort, adapt in itertools.product(r["update_form"], r["forgetting"], r["exposure_per_week"],
                                                              r["effort_function"], adaptation):
        ranks = [r["update_form"][form], r["forgetting"][forget], r["exposure_per_week"][epw],
                 r["effort_function"][effort], adaptation[adapt]]
        sets = list(EFFORT_SETS[effort]) + list(ADAPTATION_SETS[adapt])
        args = ["--form", str(form), "--epw", str(epw)]
        if forget in BREAK_SCALE:
            args += ["--break-scale", BREAK_SCALE[forget]]
        else:
            sets = ["calendar.break_weeks=0", f"calendar.reference_episodes_per_week={epw}"] + sets
        if sets:
            args += ["--set"] + sets
        tag = f"spec_{form}_{forget}_epw{epw}_{effort}_adapt_{adapt}"  # every level suffixed (D29)
        out.append({"tag": tag, "form": form, "forgetting": forget, "epw": epw, "effort": effort,
                    "adaptation": adapt, "tier": max(ranks), "ranks": ranks, "args": args})
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--scenarios", nargs="+", help="Phase V scenarios (default: design.scenarios in spec_curve.yaml, "
                                                   "which pins what the pre-D25 runs used - not the config's list)")
    ap.add_argument("--only-tier", type=int, help="run only specifications of this tier")
    ap.add_argument("--only-adaptation", choices=tuple(ADAPTATION_SETS), help="run only this adaptation level (D25)")
    args = ap.parse_args(argv)
    spec = yaml.safe_load((ROOT / "config" / "spec_curve.yaml").read_text(encoding="utf-8"))
    if spec.get("status") != "approved" or not spec.get("approved"):
        print("config/spec_curve.yaml is not approved: the ranks must be fixed before any result (brief §10.4)", file=sys.stderr)
        return 2
    design = spec["design"]
    # the manifest always describes the WHOLE design; --only-* filters what is executed now, never what is recorded
    every = specifications(spec)
    specs = [s for s in every if (args.only_tier is None or s["tier"] == args.only_tier)
             and (args.only_adaptation is None or s["adaptation"] == args.only_adaptation)]
    manifest = ROOT / "data" / "processed" / "phase5" / "spec_curve_manifest.json"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(json.dumps({"approved": str(spec["approved"]), "design": design, "specifications": every}, indent=2),
                        encoding="utf-8")
    # every cell must run the same scenarios, or the curve's dimensions are confounded with which scenarios a cell
    # included; design.scenarios pins what the pre-D25 runs used (see spec_curve.yaml)
    scenarios = args.scenarios or design.get("scenarios")
    for i, s in enumerate(specs):
        cmd = [sys.executable, "-m", "neurotutorsim.longitudinal", "--tag", s["tag"], "--years", str(design["years"]),
               "--draws", str(design["draws"]), "--learners", str(design["learners"]), "--flush-every", "10"] + s["args"] + (["--scenarios"] + list(scenarios) if scenarios else [])
        run_json = ROOT / "data" / "processed" / "phase5" / s["tag"] / "run.json"
        if run_json.exists():
            done = json.loads(run_json.read_text(encoding="utf-8"))["draws_done"]
            if len(done) >= design["draws"] + 1:
                print(f"[{i + 1}/{len(specs)}] {s['tag']}: complete")
                continue
            cmd.append("--resume")
        print(f"[{i + 1}/{len(specs)}] tier {s['tier']} {s['tag']}: {' '.join(cmd[3:])}", flush=True)
        if args.dry_run:
            continue
        started = time.time()
        code = subprocess.run(cmd, cwd=ROOT).returncode
        print(f"    exit {code} in {time.time() - started:.0f} s", flush=True)
        if code != 0:
            return code
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

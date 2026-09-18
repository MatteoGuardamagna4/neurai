"""Is the Colab server (notebooks/serve_models.ipynb) a faithful stand-in for LM Studio? Run before switching.

    uv run python scripts/compare_servers.py            # NEUROTUTOR_SERVER_URL / _TOKEN from .env

It replays real centaur_main prompts. `lms log stream --source model --filter input --json` captured the exact
inputs LM Studio fed the models (outputs/logs/centaur_main/lmstudio_inputs.jsonl), and calls_centaur.jsonl holds
the probabilities LM Studio returned for them, matched on the prompt's SHA-256. Every prompt is scored again on
the remote server through the same `MinitaurEngine.score` the run uses, and the two distributions over the option
keys are compared (total variation distance, TV). It also compares the prompt token counts, tries the
double-BOS and no-prefix renderings as alternatives, and checks the tutor's ChatML byte for byte.
Writes outputs/logs/centaur_main/server_equivalence.json. PASS rule: every capture has LM Studio's prefix, the
token counts agree, median TV <= 0.02 and 90th-percentile TV <= 0.05 for the served rendering, no alternative
rendering fits better, and the tutor template is identical.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path

import numpy as np
import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from neurotutorsim.engines import MinitaurEngine, pool_keys  # noqa: E402
from neurotutorsim.simulate import REMOTE_TOKEN_ENV, REMOTE_URL_ENV  # noqa: E402
from neurotutorsim.tutor import load_dotenv  # noqa: E402

LMSTUDIO_PREFIX = "<|begin_of_text|>AI: "  # LM Studio's rendering of the Centaur prefill (no GGUF chat template)
CHATML = re.compile(r"<\|im_start\|>(system|user|assistant)\n(.*?)<\|im_end\|>\n", re.S)


def captured_inputs(path: Path) -> list[dict]:
    out = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            d = json.loads(line)["data"]
        except (ValueError, KeyError, TypeError):
            continue  # the stream's banner line and any partial last line
        if d.get("type") == "llm.prediction.input":
            out.append(d)
    return out


def tv(p: dict, q: dict) -> float:
    return 0.5 * sum(abs(p[k] - q[k]) for k in p)


def raw_key_probs(url: str, headers: dict, prompt: str, keys) -> tuple[dict, int | None]:
    r = requests.post(f"{url}/raw/centaur/completion", headers=headers, timeout=180,
                      json={"prompt": prompt, "n_predict": 1, "n_probs": 20, "temperature": 0.0, "cache_prompt": True})
    r.raise_for_status()
    d = r.json()
    first = (d.get("completion_probabilities") or d.get("probs"))[0]
    return pool_keys(first["top_logprobs"], keys)[0], d.get("tokens_evaluated")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tag", default="centaur_main")
    ap.add_argument("--n", type=int, default=60, help="at most this many captured Centaur prompts")
    args = ap.parse_args(argv)
    load_dotenv(ROOT / ".env")
    url, token = os.environ.get(REMOTE_URL_ENV, "").rstrip("/"), os.environ.get(REMOTE_TOKEN_ENV, "")
    if not url or not token:
        print(f"put {REMOTE_URL_ENV} and {REMOTE_TOKEN_ENV} (printed by the serving notebook) in .env", file=sys.stderr)
        return 2
    headers = {"Authorization": f"Bearer {token}"}
    logs = ROOT / "outputs" / "logs" / args.tag
    inputs = captured_inputs(logs / "lmstudio_inputs.jsonl")
    centaur = [d for d in inputs if "centaur" in d.get("modelPath", "").lower()]
    qwen = [d for d in inputs if "qwen" in d.get("modelPath", "").lower()]
    logged = {}
    for line in (logs / "calls_centaur.jsonl").read_text(encoding="utf-8").splitlines():
        rec = json.loads(line)
        logged[rec["prompt_sha256"]] = rec
    report = {"url": url, "checked_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
              "server_meta": requests.get(f"{url}/meta", headers=headers, timeout=60).json(),
              "captured_centaur": len(centaur), "captured_tutor": len(qwen)}
    bad_prefix = [d["input"][:40] for d in centaur if not d["input"].startswith(LMSTUDIO_PREFIX)]
    pairs = []
    for d in centaur:
        prompt = d["input"][len(LMSTUDIO_PREFIX):]
        rec = logged.get(hashlib.sha256(prompt.encode("utf-8")).hexdigest())
        if rec is not None and d["input"].startswith(LMSTUDIO_PREFIX):
            pairs.append((prompt, rec))
    pairs = pairs[-args.n:]
    print(f"{len(centaur)} Centaur inputs captured, {len(pairs)} matched to logged LM Studio probabilities; "
          f"{len(bad_prefix)} without the expected prefix")
    if not pairs:
        print("nothing to compare yet: let the capture run a few more minutes", file=sys.stderr)
        return 2

    engine = MinitaurEngine({"base_url": url, "model": pairs[0][1]["model"], "api_key_env": REMOTE_TOKEN_ENV,
                             "top_logprobs": 20, "timeout_s": 180, "max_attempts": 3})
    rows = []
    for i, (prompt, rec) in enumerate(pairs):
        keys = rec["keys"]
        served, meta = engine.score(prompt, keys)
        double, n_double = raw_key_probs(url, headers, "<|begin_of_text|>AI: " + prompt, keys)
        bare, _ = raw_key_probs(url, headers, prompt, keys)
        lm = rec["probabilities"]
        row = {"kind": "confidence" if keys[0] == "1" else "choice", "keys": keys,
               "lmstudio": lm, "served": served, "tv": tv(served, lm), "tv_double_bos": tv(double, lm),
               "tv_no_prefix": tv(bare, lm), "argmax_agrees": max(lm, key=lm.get) == max(served, key=served.get),
               "tokens_lmstudio": rec.get("prompt_tokens"), "tokens_served": meta["prompt_tokens"],
               "tokens_double_bos": n_double, "seconds": meta["seconds"]}
        rows.append(row)
        print(f"{i + 1:3d} {row['kind']:10s} TV {row['tv']:.4f} (double BOS {row['tv_double_bos']:.4f}, no prefix "
              f"{row['tv_no_prefix']:.4f}) tokens {row['tokens_lmstudio']} vs {row['tokens_served']} {row['seconds']:.1f}s")

    tvs = np.array([r["tv"] for r in rows])
    summary = {"n": len(rows), "median_tv": float(np.median(tvs)), "p90_tv": float(np.quantile(tvs, 0.9)),
               "max_tv": float(tvs.max()), "median_tv_double_bos": float(np.median([r["tv_double_bos"] for r in rows])),
               "median_tv_no_prefix": float(np.median([r["tv_no_prefix"] for r in rows])),
               "argmax_agreement": float(np.mean([r["argmax_agrees"] for r in rows])),
               "token_counts_equal": float(np.mean([r["tokens_lmstudio"] == r["tokens_served"] for r in rows])),
               "median_seconds": float(np.median([r["seconds"] for r in rows]))}

    tutor_rows = []
    for d in qwen[-10:]:
        messages = [{"role": role, "content": content} for role, content in CHATML.findall(d["input"])]
        r = requests.post(f"{url}/raw/qwen/apply-template", headers=headers, timeout=60, json={"messages": messages})
        rendered = r.json().get("prompt") if r.ok else None
        tutor_rows.append({"messages": len(messages), "identical": rendered == d["input"]})
    summary["tutor_templates_identical"] = f"{sum(t['identical'] for t in tutor_rows)}/{len(tutor_rows)}"

    reasons = []
    if bad_prefix:
        reasons.append(f"{len(bad_prefix)} captured inputs lack the prefix {LMSTUDIO_PREFIX!r}")
    if summary["token_counts_equal"] < 1.0:
        reasons.append(f"token counts differ for {1 - summary['token_counts_equal']:.0%} of prompts")
    if summary["median_tv"] > 0.02 or summary["p90_tv"] > 0.05:
        reasons.append(f"TV median {summary['median_tv']:.4f} / p90 {summary['p90_tv']:.4f} above 0.02 / 0.05")
    if min(summary["median_tv_double_bos"], summary["median_tv_no_prefix"]) < summary["median_tv"]:
        reasons.append("an alternative rendering fits LM Studio better than the served one")
    if any(not t["identical"] for t in tutor_rows):
        reasons.append("the tutor's ChatML differs from LM Studio's")
    report.update(summary=summary, verdict="PASS" if not reasons else "FAIL", reasons=reasons, rows=rows,
                  tutor=tutor_rows, bad_prefix=bad_prefix)
    (logs / "server_equivalence.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    print(f"\n{report['verdict']}" + ("" if not reasons else ": " + "; ".join(reasons)))
    print(f"report: {logs / 'server_equivalence.json'}")
    return 0 if not reasons else 1


if __name__ == "__main__":
    raise SystemExit(main())

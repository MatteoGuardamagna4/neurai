"""Check every number the report quotes against the file it comes from.

    uv run python report/verify.py

`report/claims.yaml` lists the claims: where a number appears in the report, the text it appears as, and how to
recompute it from the repository (a row of an output table, a config value, an expression over run records, or a
line of code that must contain a given snippet). This script recomputes each one, checks that the recomputed value,
formatted as the report writes it, equals the text, and that the text really appears in that paragraph of the
report. It writes `report/build/claims_check.md`, one row per claim in order of appearance, and exits 1 if any fails.
"""
from __future__ import annotations

import glob
import json
import re
import sys
from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "report"
TABLES = ROOT / "outputs" / "tables"
OUT = REPORT / "build" / "claims_check.md"


def norm(s: str) -> str:
    """Compare numbers as written: unicode minus and dashes as '-', thousands separators and spaces dropped."""
    return (str(s).replace("−", "-").replace("–", "-").replace(" ", "").replace(" ", "")
            .replace(",", "").replace(" ", "").strip())


# ------------------------------------------------------------------ helpers available to `expr`
_cache: dict = {}


def T(name: str) -> pd.DataFrame:
    """An output table by file name (outputs/tables/<name>)."""
    if name not in _cache:
        _cache[name] = pd.read_csv(TABLES / name)
    return _cache[name]


def row(name: str, **where) -> pd.Series:
    """The single row of an output table matching every column = value; anything else is an error."""
    df = T(name)
    for k, v in where.items():
        df = df[df[k] == v] if isinstance(v, (int, float)) and not isinstance(v, bool) else df[df[k].astype(str) == str(v)]
    if len(df) != 1:
        raise ValueError(f"{name} {where}: {len(df)} rows match, need exactly 1")
    return df.iloc[0]


def cfg(path: str, file: str = "config/default.yaml"):
    """A value from a YAML config by dotted path."""
    node = yaml.safe_load((ROOT / file).read_text(encoding="utf-8"))
    for part in path.split("."):
        node = node[int(part)] if isinstance(node, list) else node[part if part in node else _key(node, part)]
    return node


def _key(node: dict, part: str):
    for k in node:
        if str(k) == part:
            return k
    raise KeyError(part)


def js(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def runs(pattern: str) -> list[dict]:
    """Every JSON run record matching a glob under the repository root."""
    return [json.loads(Path(f).read_text(encoding="utf-8")) for f in sorted(glob.glob(str(ROOT / pattern)))]


def regex(text: str, pattern: str) -> str:
    m = re.search(pattern, str(text))
    if not m:
        raise ValueError(f"pattern {pattern!r} not found in {text!r}")
    return m.group(1)


def ci(name: str, est: str, lo: str, hi: str, fmt: str = "{:.3f}", **where) -> str:
    """'estimate [low, high]' from one row of an output table, as the report's tables write it."""
    r = row(name, **where)
    return f"{fmt.format(r[est])} [{fmt.format(r[lo])}, {fmt.format(r[hi])}]"


def t4cell(key: str, contrast: str) -> str:
    """A cell of Table 8, recomputed from the source tables: the network AUC contrast with its interval, in bold when
    the interval excludes zero and the contrast passes F1, F2 and F5, followed by the marks of the criteria it fails
    (a: F1, loses significance with covariates; b: F2, not robust to rewording; c: F5, incorrect-text network)."""
    w = dict(level="network", metric="auc", key=key, contrast=contrast)
    main, cov = row("table4_cortical_contrasts.csv", **w), row("table4_cortical_contrasts_matched_covariates.csv", **w)
    reg = row("tableS_regeneration_contrasts.csv", key=key, contrast=contrast, metric="auc")
    inc = row("tableS_incorrect_control.csv", key=key, metric="auc")
    marks = ("a" if main["ci_excludes_0"] and not cov["ci_excludes_0"] else "") + \
            ("b" if not reg["claim_allowed"] else "") + ("c" if inc["ratio_to_contrast"] >= 0.5 else "")
    s = ci("table4_cortical_contrasts.csv", "estimate", "ci_low", "ci_high", "{:.2f}", **w)
    if main["ci_excludes_0"] and not marks:
        s = f"**{s}**"
    return s + (f"^{marks}^" if marks else "")


def hist_quantile(tag: str, scenario: str, outcome: str, year: int, p: float) -> float:
    """Upper edge of the histogram bin holding the p-quantile of the learner-level paired differences."""
    h = pd.read_parquet(ROOT / "data" / "processed" / "phase5" / tag / "contrast_hist")
    g = h[(h.scenario == scenario) & (h.outcome == outcome) & (h.year == year)].sort_values("bin")
    c = g["count"].cumsum() / g["count"].sum()
    return float(g["bin_high"][c >= p].iloc[0])


ENV = {"T": T, "row": row, "cfg": cfg, "js": js, "runs": runs, "regex": regex, "len": len, "sum": sum, "round": round,
       "min": min, "max": max, "abs": abs, "pd": pd, "ROOT": ROOT, "glob": glob, "Path": Path, "ci": ci,
       "t4cell": t4cell, "hist_quantile": hist_quantile, "all": all, "any": any, "set": set, "sorted": sorted}


def fmt(value, spec: str | None) -> str:
    if spec is None:
        return str(value)
    if spec == "sci":  # 4.5e10 written as "4.5 \times 10^{10}"
        mant, exp = f"{float(value):.1e}".split("e")
        return f"{mant} \\times 10^{{{int(exp)}}}"
    return spec.format(value)


# ------------------------------------------------------------------ locating the claim in the text
def paragraphs(file: str) -> list[str]:
    text = (REPORT / file).read_text(encoding="utf-8")
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    return [p for p in re.split(r"\n\s*\n", text) if p.strip()]


def locate(c: dict) -> tuple[int, str]:
    """(order key, context) of the paragraph that contains `near` (or `says`) and `says`."""
    paras = paragraphs(c["where"])
    near = c.get("near", c.get("says", ""))
    for i, p in enumerate(paras):
        flat = " ".join(p.split())
        if near in flat and ("says" not in c or c["says"] in flat):
            j = flat.find(c.get("says", near))
            return i, flat[max(0, j - 70): j + len(c.get("says", "")) + 50]
    raise ValueError(f"text not found in {c['where']}: says={c.get('says')!r} near={near!r}")


# ------------------------------------------------------------------ one claim
def check(c: dict) -> dict:
    source = ""
    if "code" in c:  # a line of a file that must contain a snippet
        path = ROOT / c["code"]
        lines = path.read_text(encoding="utf-8").splitlines()
        hits = [i + 1 for i, l in enumerate(lines) if c["contains"] in l]
        if not hits:
            raise ValueError(f"{c['code']} does not contain {c['contains']!r}")
        source = f"`{c['code']}:{hits[0]}` contains `{c['contains']}`"
        got = c.get("says", "")
    elif "from" in c:  # a cell of an output table
        r = row(c["from"], **c.get("row", {}))
        value = r[c["col"]]
        if "regex" in c:
            value = regex(value, c["regex"])
            value = float(value) if c.get("fmt") else value
        got = fmt(value * c.get("scale", 1) if c.get("scale") else value, c.get("fmt"))
        source = f"`{c['from']}` " + ", ".join(f"{k}={v}" for k, v in c.get("row", {}).items()) + f" → `{c['col']}`"
    elif "cfg" in c:
        got = fmt(cfg(c["cfg"], c.get("file", "config/default.yaml")), c.get("fmt"))
        source = f"`{c.get('file', 'config/default.yaml')}` → `{c['cfg']}`"
    elif "expr" in c:
        got = fmt(eval(c["expr"], dict(ENV)), c.get("fmt"))
        source = f"`{c['expr']}`"
    else:
        raise ValueError("claim needs one of code / from / cfg / expr")
    # `expect` is for numbers the report writes in words ("twice", "ten"): the recomputed value must equal it, and
    # `says` only locates the text
    target = str(c["expect"]) if "expect" in c else c.get("says")
    if target is not None and "code" not in c and norm(got) != norm(target):
        raise ValueError(f"recomputed {got!r}, report says {target!r}")
    return {"got": got, "source": source}


def main() -> int:
    claims = yaml.safe_load((REPORT / "claims.yaml").read_text(encoding="utf-8"))
    rows, failed = [], 0
    for n, c in enumerate(claims, 1):
        entry = {"n": n, "where": c.get("where", ""), "says": c.get("says", ""), "note": c.get("note", "")}
        try:
            order, context = locate(c)
            entry.update(order=order, context=context, **check(c), status="PASS")
        except Exception as e:  # report every failure, not just the first
            failed += 1
            entry.update(order=-1, context="", got="", source=str(c.get("from") or c.get("code") or c.get("cfg") or c.get("expr")),
                         status=f"FAIL: {e}")
        rows.append(entry)
    rows.sort(key=lambda r: (r["where"], r["order"], r["n"]))
    OUT.parent.mkdir(exist_ok=True)
    lines = ["# Claims check", "",
             f"{len(rows) - failed} of {len(rows)} claims pass. Each row: the report file, the sentence the number sits in, "
             "the number as the report writes it, the value recomputed from the source, and the source. "
             "To spot-check by hand, open the source named in a row and find the value there.", "",
             "| # | File | Context | Report says | Recomputed | Source | Status |", "|---|---|---|---|---|---|---|"]
    for r in rows:
        cells = [str(r["n"]), r["where"], r["context"].replace("|", "\\|"), r["says"].replace("|", "\\|"),
                 str(r["got"]).replace("|", "\\|"), r["source"].replace("|", "\\|") + (f" ({r['note']})" if r["note"] else ""),
                 r["status"].replace("|", "\\|")]
        lines.append("| " + " | ".join(cells) + " |")
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    for r in rows:
        if r["status"] != "PASS":
            print(f"#{r['n']} {r['where']} {r['says']!r}: {r['status']}")
    print(f"{len(rows) - failed} of {len(rows)} claims pass; table written to {OUT.relative_to(ROOT)}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())

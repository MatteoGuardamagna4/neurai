"""Units, deterministic validators, stimulus files and matching features (brief §3.2, §5.1-5.5).

A unit is one JSON file under data/units/ (the authored source of truth). A stimulus is one markdown
file per condition under stimuli/<condition>/<unit_id>.md: front matter between `---` lines, then
`# Section` headings. Every number is recomputed here, never trusted.

    python -m neurotutorsim.corpus        # validate everything, write units.csv + stimuli.csv, report matching
"""
from __future__ import annotations

import ast
import csv
import json
import math
import operator
import re
import sys
from dataclasses import dataclass
from pathlib import Path

CONDITIONS = ("traditional", "ai_scaffolding", "ai_substitution")
WORDS_PER_MINUTE = 220  # brief §6.2 main specification
SECTIONS = {  # required sections per condition, in order (brief §5.2)
    "traditional": ("Explanation", "Problem", "Hints", "Worked solution"),
    "ai_scaffolding": ("Explanation", "Problem", "Diagnostic questions", "Hints"),
    "ai_substitution": ("Explanation", "Problem", "Worked solution"),
}
ANSWER_ALLOWED_IN = {"traditional": ("Worked solution",), "ai_scaffolding": (), "ai_substitution": ("Worked solution",)}
EXPLANATION_WORDS = (250, 400)  # brief §5.2 item 6
DURATION_CALIPER = 0.10  # brief §5.5


# ------------------------------------------------------------------ validators (§5.1 item 4, §5.4)
def _margin(price: float, variable_cost: float) -> float:
    if price <= variable_cost:
        raise ValueError("contribution margin must be positive (price <= variable cost)")
    return price - variable_cost


VALIDATORS = {
    "break_even_quantity": lambda fixed_costs, price, variable_cost: fixed_costs / _margin(price, variable_cost),
    "break_even_revenue": lambda fixed_costs, price, variable_cost: fixed_costs / _margin(price, variable_cost) * price,
    "target_profit_quantity": lambda fixed_costs, target_profit, price, variable_cost: (fixed_costs + target_profit)
    / _margin(price, variable_cost),
    "price_for_break_even_quantity": lambda fixed_costs, quantity, variable_cost: fixed_costs / quantity + variable_cost,
    "contribution_margin_ratio": lambda price, variable_cost: _margin(price, variable_cost) / price,
}

_OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv,
        ast.Pow: operator.pow, ast.USub: operator.neg}


def evaluate(expression: str, params: dict) -> float:
    """Arithmetic over the unit's parameters without eval (+ - * / ** and parameter names only).
    Powers the generic `expression` validator and every distractor rule, so new units need no Python."""

    def ev(node):
        if isinstance(node, ast.Expression):
            return ev(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return float(node.value)
        if isinstance(node, ast.Name):
            return float(params[node.id])
        if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
            return _OPS[type(node.op)](ev(node.left), ev(node.right))
        if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
            return _OPS[type(node.op)](ev(node.operand))
        raise ValueError(f"unsupported element in expression {expression!r}")

    return ev(ast.parse(expression, mode="eval"))


def expected_answer(problem: dict) -> float:
    if problem["validator"] == "expression":
        return evaluate(problem["expression"], problem["params"])
    return VALIDATORS[problem["validator"]](**problem["params"])


def _close(a: float, b: float) -> bool:
    return math.isclose(a, b, rel_tol=1e-6, abs_tol=1e-6)


_NUMBER = re.compile(r"\d[\d,]*(?:\.\d+)?")


def contains_number(text: str, value: float) -> bool:
    """Does `text` state `value` as a number (thousands separators ignored)? Used for answer placement and leakage."""
    for m in _NUMBER.finditer(text):
        try:
            if _close(float(m.group(0).replace(",", "")), value):
                return True
        except ValueError:
            continue
    return False


# ------------------------------------------------------------------ units
@dataclass(frozen=True)
class Problem:
    text: str
    answer: float
    fmt: str
    distractors: tuple[tuple[float, str, str], ...]  # (value, rule, note); the first is the documented misconception
    method: str = ""  # validator name or expression that produces the correct answer

    def render(self, value: float) -> str:
        return self.fmt.format(value)


@dataclass(frozen=True)
class Unit:
    unit_id: str
    domain: str
    concept: str
    difficulty: int
    prerequisites: tuple[str, ...]
    misconception: str
    problem: Problem
    near_transfer: Problem
    far_transfer: Problem
    hints: tuple[str, ...]
    worked_solution: str


def _problem(raw: dict, errors: list[str], where: str) -> Problem:
    answer = float(raw["answer"])
    try:
        expected = expected_answer(raw)
        if not _close(expected, answer):
            errors.append(f"{where}: answer {answer} but validator {raw['validator']!r} gives {expected}")
    except Exception as exc:  # noqa: BLE001 - every failure is a corpus error to report
        errors.append(f"{where}: validator failed: {exc}")
    distractors = []
    for d in raw.get("distractors", []):
        value = float(d["value"])
        try:
            got = evaluate(d["rule"], raw["params"])
            if not _close(got, value):
                errors.append(f"{where}: distractor {value} but rule {d['rule']!r} gives {got}")
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{where}: distractor rule {d.get('rule')!r} failed: {exc}")
        if _close(value, answer):
            errors.append(f"{where}: distractor {value} equals the answer")
        distractors.append((value, d.get("rule", ""), d.get("note", "")))
    if len(distractors) != 2 or len({v for v, _, _ in distractors}) != 2:
        errors.append(f"{where}: exactly two distinct distractors are required (3-option choice set)")
    method = raw.get("expression") if raw["validator"] == "expression" else raw["validator"]
    return Problem(raw["text"].strip(), answer, raw.get("format", "{:,.0f}"), tuple(distractors), method or "")


def parse_unit(raw: dict) -> tuple[Unit, list[str]]:
    errors: list[str] = []
    uid = raw["unit_id"]
    if not 1 <= int(raw["difficulty"]) <= 5:
        errors.append(f"{uid}: difficulty must be an integer 1-5 (§5.1 item 5)")
    if len(raw.get("hints", [])) != 3:
        errors.append(f"{uid}: exactly three hints are required (§5.2 item 6)")
    unit = Unit(
        unit_id=uid, domain=raw["domain"], concept=raw["concept"], difficulty=int(raw["difficulty"]),
        prerequisites=tuple(raw.get("prerequisites", [])), misconception=raw["misconception"]["description"],
        problem=_problem(raw["problem"], errors, f"{uid}.problem"),
        near_transfer=_problem(raw["near_transfer"], errors, f"{uid}.near_transfer"),
        far_transfer=_problem(raw["far_transfer"], errors, f"{uid}.far_transfer"),
        hints=tuple(h.strip() for h in raw.get("hints", [])), worked_solution=raw["worked_solution"].strip(),
    )
    return unit, errors


def load_units(units_dir: Path) -> dict[str, Unit]:
    units, errors = {}, []
    for path in sorted(Path(units_dir).glob("*.json")):
        unit, errs = parse_unit(json.loads(path.read_text(encoding="utf-8")))
        units[unit.unit_id] = unit
        errors += errs
    if errors:
        raise ValueError("corpus validation failed:\n  " + "\n  ".join(errors))
    if not units:
        raise ValueError(f"no unit JSON files under {units_dir}")
    return units


def curriculum_order(units: dict[str, Unit]) -> list[Unit]:
    """Prerequisite concepts first, then difficulty, then id (the §5.1 concept map, flattened)."""
    ordered, remaining, done = [], dict(units), set()
    while remaining:
        ready = [u for u in remaining.values() if all(p in done for p in u.prerequisites)] or list(remaining.values())
        unit = min(ready, key=lambda u: (u.difficulty, u.unit_id))
        ordered.append(unit)
        done.add(unit.concept)
        del remaining[unit.unit_id]
    return ordered


# ------------------------------------------------------------------ stimuli
@dataclass(frozen=True)
class Stimulus:
    stimulus_id: str
    unit_id: str
    condition: str
    variant: str
    sections: dict[str, str]
    path: Path

    @property
    def explanation(self) -> str:
        return self.sections["Explanation"]

    @property
    def body(self) -> str:
        return "\n\n".join(self.sections.values())


def parse_stimulus(path: Path) -> Stimulus:
    text = path.read_text(encoding="utf-8")
    m = re.match(r"---\r?\n(.*?)\r?\n---\r?\n(.*)", text, re.S)
    if not m:
        raise ValueError(f"{path}: missing '---' front matter")
    meta = {k.strip(): v.strip() for k, v in (line.split(":", 1) for line in m.group(1).splitlines() if ":" in line)}
    sections: dict[str, list[str]] = {}
    current = None
    for line in m.group(2).splitlines():
        if line.startswith("# "):
            current = line[2:].strip()
            sections[current] = []
        elif current is not None:
            sections[current].append(line)
    return Stimulus(meta["stimulus_id"], meta["unit_id"], meta["condition"], meta.get("variant", "primary"),
                    {k: "\n".join(v).strip() for k, v in sections.items()}, path)


def check_stimulus(stim: Stimulus, unit: Unit) -> list[str]:
    """Structure (§5.2), explanation length, consistency with the unit, and answer placement / leakage (§5.4)."""
    errors, where = [], f"{stim.path.name} ({stim.condition})"
    required = SECTIONS[stim.condition]
    if tuple(stim.sections) != required:
        errors.append(f"{where}: sections {tuple(stim.sections)} must be exactly {required}")
        return errors
    words = features(stim.explanation)["word_count"]
    if not EXPLANATION_WORDS[0] <= words <= EXPLANATION_WORDS[1]:
        errors.append(f"{where}: explanation has {words} words, must be within {EXPLANATION_WORDS}")
    if unit.problem.text not in stim.sections["Problem"]:
        errors.append(f"{where}: Problem section does not contain the unit's canonical problem text")
    if "Diagnostic questions" in stim.sections:
        # The section is the scaffolding tutor's written-out diagnosis and must cover the same wrong
        # answers as the unit's distractor notes, which are what `tutor.unit_facts` puts in
        # `$distractor_notes`. One question per documented wrong answer, at least.
        questions = stim.sections["Diagnostic questions"].count("?")
        needed = len(unit.problem.distractors)
        if questions < needed:
            errors.append(f"{where}: Diagnostic questions asks {questions} question(s); it must ask at "
                          f"least {needed}, one per documented wrong answer in $distractor_notes")
    if "Hints" in stim.sections:
        for i, hint in enumerate(unit.hints, 1):
            if hint not in stim.sections["Hints"]:
                errors.append(f"{where}: hint {i} differs from the unit's hint ladder")
    for name, section in stim.sections.items():
        present = contains_number(section, unit.problem.answer)
        allowed = name in ANSWER_ALLOWED_IN[stim.condition]
        if present and not allowed:
            errors.append(f"{where}: the answer {unit.problem.render(unit.problem.answer)} leaks into section {name!r}")
        if allowed and not present:
            errors.append(f"{where}: section {name!r} must state the answer")
    return errors


def load_stimuli(stimuli_dir: Path, units: dict[str, Unit]) -> dict[tuple[str, str], Stimulus]:
    stimuli, errors = {}, []
    for unit in units.values():
        for condition in CONDITIONS:
            path = Path(stimuli_dir) / condition / f"{unit.unit_id}.md"
            if not path.exists():
                errors.append(f"missing stimulus {path}")
                continue
            stim = parse_stimulus(path)
            if (stim.unit_id, stim.condition) != (unit.unit_id, condition):
                errors.append(f"{path}: front matter says {stim.unit_id}/{stim.condition}")
            errors += check_stimulus(stim, unit)
            stimuli[(unit.unit_id, condition)] = stim
    if errors:
        raise ValueError("stimulus validation failed:\n  " + "\n  ".join(errors))
    return stimuli


# ------------------------------------------------------------------ text controls (§5.2 item 9, §10.3, §10.6)
# TRIBE-only texts, never read by the simulated learner: `stimuli/variants/<condition>/<unit_id>__reworded_<k>.md`
# (harmless stylistic regenerations of the primary, same facts and numbers) and
# `stimuli/incorrect/traditional/<unit_id>__incorrect.md` (the traditional text teaching the unit's documented
# misconception as if it were right, fluent and matched in length: the §10.3 incorrect-but-fluent control).
REWORDED = ("reworded_1", "reworded_2")
_STATED_NUMBER = re.compile(r"(?<![A-Za-z])\d[\d,]*(?:\.\d+)?")  # own name: _NUMBER above is contains_number's


def numbers_in(text: str) -> set[float]:
    """Numbers a text states, ignoring 0-10 (step labels, 'two steps' written as digits, list counts)."""
    out = set()
    for m in _STATED_NUMBER.findall(text):
        v = float(m.replace(",", "").rstrip("."))
        if v > 10 or v != int(v):
            out.add(round(v, 6))
    return out


def check_text_control(stim: Stimulus, primary: Stimulus, unit: Unit) -> list[str]:
    """A reworded variant keeps the primary's facts: same sections, canonical problem, the same stated numbers,
    the same answer placement and leakage rules, the explanation length rule, and duration within the caliper of
    the primary. An incorrect text keeps the structure and length but teaches the misconception: the correct answer
    appears nowhere and the worked solution reaches the misconception's answer."""
    where = f"{stim.path.name} ({stim.condition}, {stim.variant})"
    errors = []
    if tuple(stim.sections) != tuple(primary.sections):
        return [f"{where}: sections {tuple(stim.sections)} must match the primary's {tuple(primary.sections)}"]
    words = features(stim.explanation)["word_count"]
    if not EXPLANATION_WORDS[0] <= words <= EXPLANATION_WORDS[1]:
        errors.append(f"{where}: explanation has {words} words, must be within {EXPLANATION_WORDS}")
    if unit.problem.text not in stim.sections["Problem"]:
        errors.append(f"{where}: Problem section does not contain the unit's canonical problem text")
    rel = abs(features(stim.body)["duration"] - features(primary.body)["duration"]) / features(primary.body)["duration"]
    if rel > DURATION_CALIPER:
        errors.append(f"{where}: duration differs from the primary by {rel:.1%} (caliper {DURATION_CALIPER:.0%})")
    if stim.variant.startswith("reworded"):
        if "Diagnostic questions" in stim.sections and stim.sections["Diagnostic questions"].count("?") < len(unit.problem.distractors):
            errors.append(f"{where}: Diagnostic questions must ask at least {len(unit.problem.distractors)} questions")
        missing, extra = numbers_in(primary.body) - numbers_in(stim.body), numbers_in(stim.body) - numbers_in(primary.body)
        if missing or extra:
            errors.append(f"{where}: stated numbers differ from the primary (missing {sorted(missing)}, new {sorted(extra)})")
        for name, section in stim.sections.items():
            present, allowed = contains_number(section, unit.problem.answer), name in ANSWER_ALLOWED_IN[stim.condition]
            if present and not allowed:
                errors.append(f"{where}: the answer leaks into section {name!r}")
            if allowed and not present:
                errors.append(f"{where}: section {name!r} must state the answer")
    elif stim.variant == "incorrect":
        wrong = abs(unit.problem.distractors[0][0])  # a loss is written as "a loss of EUR 5,000": no minus sign
        if contains_number(stim.body, unit.problem.answer):
            errors.append(f"{where}: the correct answer {unit.problem.render(unit.problem.answer)} must not appear")
        if not contains_number(stim.sections["Worked solution"], wrong):
            errors.append(f"{where}: the worked solution must reach the misconception's answer {unit.problem.render(wrong)}")
    else:
        errors.append(f"{where}: unknown variant {stim.variant!r}")
    return errors


def load_text_controls(stimuli_dir: Path, units: dict[str, Unit], stimuli: dict[tuple[str, str], Stimulus],
                       require_all: bool = False) -> dict[tuple[str, str, str], Stimulus]:
    """{(unit_id, condition, variant): Stimulus} for every text control on disk, each validated against its primary.
    `require_all` also fails on missing files (the TRIBE notebook needs the complete set)."""
    root, out, errors = Path(stimuli_dir), {}, []
    expected = [(u, c, v, root / "variants" / c / f"{u}__{v}.md") for u in units for c in CONDITIONS for v in REWORDED]
    expected += [(u, "traditional", "incorrect", root / "incorrect" / "traditional" / f"{u}__incorrect.md") for u in units]
    for uid, cond, variant, path in expected:
        if not path.exists():
            if require_all:
                errors.append(f"missing text control {path}")
            continue
        stim = parse_stimulus(path)
        if (stim.unit_id, stim.condition, stim.variant) != (uid, cond, variant):
            errors.append(f"{path}: front matter says {stim.unit_id}/{stim.condition}/{stim.variant}")
            continue
        errors += check_text_control(stim, stimuli[(uid, cond)], units[uid])
        out[(uid, cond, variant)] = stim
    if errors:
        raise ValueError("text control validation failed:\n  " + "\n  ".join(errors))
    return out


# ------------------------------------------------------------------ matching features (§5.3)
_WORD = re.compile(r"[A-Za-z][A-Za-z'-]*")


def _syllables(word: str) -> int:
    w = word.lower()
    groups = len(re.findall(r"[aeiouy]+", w))
    if w.endswith("e") and not w.endswith(("le", "ee")) and groups > 1:
        groups -= 1
    return max(1, groups)


def features(text: str) -> dict:
    words = _WORD.findall(text)
    n = max(1, len(words))
    sentences = max(1, len(re.findall(r"[.!?](?:\s|$)", text)))
    syllables = sum(_syllables(w) for w in words)
    return {
        "word_count": len(words),
        "sentence_count": sentences,
        "character_count": len(text),
        "readability": round(0.39 * n / sentences + 11.8 * syllables / n - 15.59, 2),  # Flesch-Kincaid grade
        "equation_count": text.count("="),
        "lexical_diversity": round(len({w.lower() for w in words}) / n, 3),
        "duration": round(60.0 * len(words) / WORDS_PER_MINUTE, 1),  # seconds at 220 wpm (§6.2)
    }


def build_tables(units: dict[str, Unit], stimuli: dict[tuple[str, str], Stimulus], out_dir: Path) -> dict:
    """Write units.csv and stimuli.csv (brief §4.2) and return the duration-caliper report (§5.5)."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    with (out_dir / "units.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["unit_id", "domain", "concept", "difficulty", "prerequisites", "reference_answer", "near_transfer_answer",
                    "transfer_answer", "misconception_answer", "misconception", "correctness", "coverage"])
        for u in units.values():
            w.writerow([u.unit_id, u.domain, u.concept, u.difficulty, ";".join(u.prerequisites), u.problem.answer,
                        u.near_transfer.answer, u.far_transfer.answer, u.problem.distractors[0][0], u.misconception, 1.0, ""])
    rows, report = [], {}
    for (uid, condition), stim in stimuli.items():
        feats = features(stim.body)
        rows.append({"stimulus_id": stim.stimulus_id, "unit_id": uid, "condition": condition, "variant": stim.variant,
                     "text": stim.path.as_posix(), "modality": "text", "example_count": 1, **feats})
    with (out_dir / "stimuli.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    for uid in units:
        anchor = next(r["duration"] for r in rows if r["unit_id"] == uid and r["condition"] == "traditional")
        for r in rows:
            if r["unit_id"] == uid and r["condition"] != "traditional":
                rel = abs(r["duration"] - anchor) / anchor
                report[(uid, r["condition"])] = {"relative_difference": round(rel, 3), "passed": rel <= DURATION_CALIPER}
    return {"rows": rows, "caliper": report}


def main(argv=None) -> int:
    root = Path(argv[0]) if argv else Path.cwd()
    units = load_units(root / "data" / "units")
    stimuli = load_stimuli(root / "stimuli", units)
    result = build_tables(units, stimuli, root / "data" / "processed")
    print(f"{len(units)} unit(s) validated (100% reference correctness), {len(stimuli)} stimuli parsed")
    print(f"{'stimulus':32} {'words':>6} {'FK':>5} {'eq':>3} {'sec':>6}")
    for r in result["rows"]:
        print(f"{r['stimulus_id']:32} {r['word_count']:>6} {r['readability']:>5} {r['equation_count']:>3} {r['duration']:>6}")
    for (uid, condition), c in result["caliper"].items():
        print(f"caliper {uid} {condition}: {c['relative_difference']:.1%} vs traditional -> {'ok' if c['passed'] else 'FAIL'}")
    print("SMD / Mahalanobis matching (§5.3) needs >= 10 units; not computed.")
    controls = load_text_controls(root / "stimuli", units, stimuli)
    n_var = sum(1 for k in controls if k[2].startswith("reworded"))
    n_inc = sum(1 for k in controls if k[2] == "incorrect")
    print(f"text controls validated: {n_var} / {len(units) * len(CONDITIONS) * len(REWORDED)} reworded variants, "
          f"{n_inc} / {len(units)} incorrect-but-fluent")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

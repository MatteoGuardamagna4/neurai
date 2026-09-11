"""LLM tutor for the AI conditions (brief §3.3, §5.2 items 7-8, §5.4 compliance and leakage checks).

One OpenAI-compatible chat-completions call per tutor turn (`tutor.base_url` + `/chat/completions`, so
OpenAI, LM Studio or any compatible server is one config line). Scaffolding withholds the answer and is
leakage-checked; substitution hands over the complete solution at once. Every call is logged.
"""
from __future__ import annotations

import hashlib
import json
import os
import string
import time
from dataclasses import dataclass, field
from pathlib import Path

import requests

from .corpus import Unit, contains_number


class TutorError(RuntimeError):
    """The tutor API cannot be used; the run stops and can be resumed."""


@dataclass
class TutorTurn:
    text: str
    leaked: bool = False  # the reference answer appeared in the reply (a defect for scaffolding, required for substitution)
    asks_question: bool = False  # §5.4 policy compliance: does the reply ask a guiding question?
    fallback: bool = False  # scaffolding leaked twice, so the prewritten hint was used instead
    meta: dict = field(default_factory=dict)


def load_dotenv(path: Path = Path(".env")) -> None:
    """Minimal KEY=VALUE loader so no python-dotenv dependency is needed."""
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def unit_facts(unit: Unit) -> dict:
    """Prompt variables, all from the unit JSON (never from the stimulus markdown):
    `$distractor_notes` is `problem.distractors[].note`, so a unit authored without notes fails
    here instead of quietly substituting a blank line into the scaffolding prompt."""
    blank = [unit.problem.render(v) for v, _, note in unit.problem.distractors if not note.strip()]
    if blank or not unit.problem.distractors:
        raise TutorError(f"{unit.unit_id}: every distractor needs a non-empty `note` (missing for "
                         f"{blank or 'all: none authored'}); $distractor_notes must never be empty")
    if any(not h.strip() for h in unit.hints):
        raise TutorError(f"{unit.unit_id}: every hint must be non-empty; $hints must never be empty")
    notes = "\n".join(f"- {unit.problem.render(v)}: {note} ({rule})" for v, rule, note in unit.problem.distractors)
    hints = "\n".join(f"Hint {i}: {h}" for i, h in enumerate(unit.hints, 1))
    return {"problem": unit.problem.text, "answer": unit.problem.render(unit.problem.answer),
            "distractor_notes": notes, "hints": hints, "worked_solution": unit.worked_solution}


class Tutor:
    def __init__(self, cfg: dict, prompts_dir: Path, log_path: Path | None = None):
        load_dotenv()
        self.cfg = cfg
        self.log_path = Path(log_path) if log_path else None
        self.templates = {name: string.Template((Path(prompts_dir) / f"{name}.md").read_text(encoding="utf-8"))
                          for name in ("scaffolding", "substitution")}
        env = cfg.get("api_key_env", "OPENAI_API_KEY")
        self.api_key = os.environ.get(env, "")
        local = any(h in cfg["base_url"] for h in ("127.0.0.1", "localhost"))
        if not self.api_key and not local:
            raise TutorError(f"set {env} in .env or the environment, or use `tutor.provider: fake`")
        self.api_key = self.api_key or "lm-studio"  # a local server (LM Studio) ignores the bearer token
        self.calls = 0
        self.leaks = 0
        self.fallbacks = 0

    def chat(self, system: str, user: str) -> tuple[str, dict]:
        base = self.cfg["base_url"].rstrip("/")
        limit_key = "max_completion_tokens" if "api.openai.com" in base else "max_tokens"
        payload = {"model": self.cfg["model"], "temperature": self.cfg.get("temperature", 0.3),
                   "seed": self.cfg.get("seed", 7), limit_key: self.cfg.get("max_tokens", 350),
                   "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}
        started, last = time.perf_counter(), None
        for attempt in range(3):
            try:
                r = requests.post(f"{base}/chat/completions", json=payload, timeout=self.cfg.get("timeout_s", 60),
                                  headers={"Authorization": f"Bearer {self.api_key}"})
                if r.status_code != 429 and r.status_code < 500:
                    r.raise_for_status()
                    data = r.json()
                    break
                last = f"HTTP {r.status_code}: {r.text[:200]}"
            except (requests.ConnectionError, requests.Timeout) as exc:
                last = repr(exc)
            time.sleep(3.0 * (attempt + 1))
        else:
            raise TutorError(f"tutor API failed 3 times; last error: {last}")
        self.calls += 1
        text = (data["choices"][0]["message"]["content"] or "").strip()
        return text, {"model": data.get("model", self.cfg["model"]), "usage": data.get("usage"),
                      "seconds": round(time.perf_counter() - started, 3),
                      "prompt_sha256": hashlib.sha256((system + "\n" + user).encode("utf-8")).hexdigest()}

    def scaffold(self, unit: Unit, transcript: list[str], level: int) -> TutorTurn:
        """Turn `level` of `len(unit.hints)`: diagnose, ask one question, hint at that level, never
        the answer. The level is an explicit `$turn` variable in the system prompt and is restated in
        the user turn, so which rung of the ladder to serve is never inferred from the transcript."""
        rungs = len(unit.hints)
        system = self.templates["scaffolding"].substitute(unit_facts(unit), turn=level, max_turns=rungs)
        user = ("Interaction so far:\n" + "\n".join(transcript)
                + f"\n\nThis is tutor turn {level} of {rungs}: give a level-{level} hint. Respond now.")
        text, meta = self.chat(system, user)
        leaked = contains_number(text, unit.problem.answer)
        if leaked:  # one regeneration under a stronger instruction, then the prewritten hint
            self.leaks += 1
            retry = user + (f"\nYour previous reply revealed the answer. Do NOT write the number "
                            f"{unit.problem.render(unit.problem.answer)} or anything equal to it. Rewrite the reply.")
            text, meta["regenerated"] = self.chat(system, retry)
            if contains_number(text, unit.problem.answer):
                self.fallbacks += 1
                turn = TutorTurn(unit.hints[level - 1], leaked=True, fallback=True, meta=meta)
                return self._log("scaffolding", level, turn)
        return self._log("scaffolding", level, TutorTurn(text, leaked=leaked, asks_question="?" in text, meta=meta))

    def substitute(self, unit: Unit, transcript: list[str]) -> TutorTurn:
        """The complete explanation, calculation and answer, immediately after the first error."""
        system = self.templates["substitution"].substitute(unit_facts(unit))
        user = "Interaction so far:\n" + "\n".join(transcript) + "\n\nGive the complete solution now."
        text, meta = self.chat(system, user)
        turn = TutorTurn(text, leaked=contains_number(text, unit.problem.answer), asks_question="?" in text, meta=meta)
        return self._log("substitution", 1, turn)

    def _log(self, policy: str, level: int, turn: TutorTurn) -> TutorTurn:
        if self.log_path:
            with self.log_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps({"policy": policy, "level": level, "text": turn.text, "leaked": turn.leaked,
                                    "asks_question": turn.asks_question, "fallback": turn.fallback, **turn.meta}) + "\n")
        return turn


class FakeTutor:
    """Canned tutor for offline runs and tests: scaffolding never states the answer, substitution gives
    the unit's worked solution. Counts calls like the real one."""
    name = "fake"

    def __init__(self):
        self.calls = 0
        self.leaks = 0
        self.fallbacks = 0

    def scaffold(self, unit: Unit, transcript: list[str], level: int) -> TutorTurn:
        self.calls += 1
        text = (f"Your last answer suggests you divided by the wrong number. What is left from each sale after "
                f"paying its variable cost? Hint {level}: {unit.hints[level - 1]}")
        return TutorTurn(text, asks_question=True, meta={"fake": True})

    def substitute(self, unit: Unit, transcript: list[str]) -> TutorTurn:
        self.calls += 1
        return TutorTurn(unit.worked_solution, leaked=True, meta={"fake": True})

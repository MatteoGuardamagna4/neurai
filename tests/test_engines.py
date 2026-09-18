import json

import numpy as np
import pytest

from neurotutorsim import engines
from neurotutorsim.engines import (APPROACH_TEXT, Decision, HybridEngine, LogisticEngine, MinitaurEngine,
                                   Option, Trial, explanation_of)
from tests.test_learners import make_learner


class FakeResponse:
    status_code = 200
    text = ""

    def __init__(self, payload):
        self.payload = payload

    def json(self):
        return self.payload

    def raise_for_status(self):
        pass


def payload(top):
    return {"choices": [{"logprobs": {"content": [{"top_logprobs": [{"token": t, "logprob": lp} for t, lp in top]}]}}],
            "usage": {"prompt_tokens": 10}}


def options():
    return [Option("W", "correct", "6,000 units", 6000.0, "break_even_quantity"),
            Option("Q", "misconception", "2,400 units", 2400.0, "fixed_costs / price"),
            Option("Z", "distractor", "4,000 units", 4000.0, "fixed_costs / variable_cost")]


def test_scoring_pools_token_variants_and_floors_missing_keys(monkeypatch, tmp_path):
    monkeypatch.setattr(engines.requests, "post",
                        lambda *a, **k: FakeResponse(payload([("W", -1.0), (" W", -2.0), ("q", -1.5), ("x", -3.0)])))
    engine = MinitaurEngine({"base_url": "http://x", "model": "m"}, tmp_path / "log.jsonl")
    probs, meta = engine.score("You press <<", ("W", "Q", "Z"))
    assert probs["W"] > probs["Q"] > probs["Z"]
    assert sum(probs.values()) == pytest.approx(1.0)
    assert meta["missing_keys"] == ["Z"] and meta["prompt_tokens"] == 10
    assert probs["W"] / probs["Q"] == pytest.approx((np.exp(-1.0) + np.exp(-2.0)) / np.exp(-1.5))
    assert len((tmp_path / "log.jsonl").read_text().splitlines()) == 1


def test_remote_server_gets_the_bearer_token_and_every_call_names_its_server(monkeypatch, tmp_path):
    sent = []

    def post(url, **kw):
        sent.append((url, kw.get("headers")))
        return FakeResponse(payload([("W", -0.5), ("Q", -1.0), ("Z", -2.0)]))

    monkeypatch.setattr(engines.requests, "post", post)
    monkeypatch.setenv("NEUROTUTOR_SERVER_TOKEN", "secret")
    engine = MinitaurEngine({"base_url": "https://colab.example/", "model": "m", "api_key_env": "NEUROTUTOR_SERVER_TOKEN"},
                            tmp_path / "log.jsonl")
    engine.score("You press <<", ("W", "Q", "Z"))
    assert sent == [("https://colab.example/v1/chat/completions", {"Authorization": "Bearer secret"})]
    assert json.loads((tmp_path / "log.jsonl").read_text())["server"] == "https://colab.example"
    local = MinitaurEngine({"base_url": "http://127.0.0.1:1234", "model": "m"})
    assert local.headers == {}, "LM Studio on localhost gets no token"
    monkeypatch.delenv("NEUROTUTOR_SERVER_TOKEN")
    with pytest.raises(engines.EngineError):
        MinitaurEngine({"base_url": "https://colab.example", "model": "m", "api_key_env": "NEUROTUTOR_SERVER_TOKEN"})


def test_use_remote_server_points_both_models_at_the_tunnel_and_never_sends_the_openai_key(cfg):
    import copy

    from neurotutorsim import simulate

    c = copy.deepcopy(cfg)
    simulate.use_remote_server(c, "https://abc.trycloudflare.com/")
    assert c["engine"]["base_url"] == "https://abc.trycloudflare.com"
    assert c["tutor"]["base_url"] == "https://abc.trycloudflare.com/v1"
    assert c["engine"]["api_key_env"] == c["tutor"]["api_key_env"] == "NEUROTUTOR_SERVER_TOKEN"
    assert cfg["tutor"]["api_key_env"] == "OPENAI_API_KEY", "the session config is untouched"


def test_choose_samples_from_distribution_and_prompt_is_observable_only(monkeypatch, tmp_path):
    monkeypatch.setattr(engines.requests, "post", lambda *a, **k: FakeResponse(payload([("Q", -0.1), ("W", -5.0), ("Z", -5.0)])))
    engine = MinitaurEngine({"base_url": "http://x", "model": "m"})
    trial = Trial("first", ["Problem 1.", "Lesson: text", "Question: q"], options(), record="Your record so far: 1 problems, 1 solved on the first try, 0 extra hints requested.")
    prompt = engine.prompt_for(trial)
    assert prompt.endswith("You press <<") and "Options: W) 6,000 units  Q) 2,400 units  Z) 4,000 units" in prompt
    decision = engine.choose(trial, make_learner(), np.random.default_rng(0))
    assert decision.kind == "misconception" and decision.p_correct < 0.05
    assert decision.explanation == "misconception: fixed_costs / price"
    with pytest.raises(engines.EngineError):
        engine.prompt_for(Trial("first", ["K=0.4 theta"], options()))


def test_confidence_is_a_sampled_rating(monkeypatch):
    monkeypatch.setattr(engines.requests, "post", lambda *a, **k: FakeResponse(payload([("5", -0.01), ("1", -9.0)])))
    engine = MinitaurEngine({"base_url": "http://x", "model": "m"})
    decision = Decision("W", "correct", 6000.0, 0.5, {})
    confidence = engine.confidence(Trial("first", ["Question: q"], options()), decision, make_learner(),
                                   np.random.default_rng(0))
    assert decision.rating == 5 and confidence == 1.0
    assert decision.meta["confidence_call"]["expected_rating"] > 4.9


def test_missing_logprobs_is_an_engine_error(monkeypatch):
    monkeypatch.setattr(engines.requests, "post", lambda *a, **k: FakeResponse({"choices": [{"logprobs": None}]}))
    engine = MinitaurEngine({"base_url": "http://x", "model": "m", "max_attempts": 1})
    with pytest.raises(engines.EngineError):
        engine.score("You press <<", ("W", "Q"))


def test_logistic_engine_directions(cfg):
    engine = LogisticEngine(cfg["response"], cfg["population"]["theta_slope"])
    rng = np.random.default_rng(0)
    p_high = engine.choose(Trial("first", [], options(), b_u=0.0), make_learner(K=0.9), rng).p_correct
    p_low = engine.choose(Trial("first", [], options(), b_u=0.0), make_learner(K=0.1), rng).p_correct
    p_hard = engine.choose(Trial("first", [], options(), b_u=2.0), make_learner(K=0.9), rng).p_correct
    p_help = engine.choose(Trial("supported", [], options(), b_u=0.0, support_h=1.0), make_learner(K=0.9), rng).p_correct
    assert p_high > p_low and p_hard < p_high and p_help > p_high
    help_opt = Option("H", "help", "Ask for the next hint")
    requests = [engine.choose(Trial("supported", [], options() + [help_opt], allow_help=True), make_learner(D=0.95), rng).kind
                for _ in range(300)].count("help")
    assert requests > 100
    decision = Decision("W", "correct", 6000.0, 0.7, {})
    assert 0.0 <= engine.confidence(Trial("first", [], options()), decision, make_learner(), rng) <= 1.0
    assert decision.rating in (1, 2, 3, 4, 5)


class FixedChoice:
    """Stands in for Centaur: always presses the option of the given kind, rates confidence 4."""
    name = "fixed"

    def __init__(self, kind):
        self.kind, self.calls = kind, 0

    def choose(self, trial, learner, rng):
        self.calls += 1
        o = next(o for o in trial.options if o.kind == self.kind)
        return Decision(o.key, o.kind, o.value, 0.0, {}, explanation=explanation_of(o), meta={"kind": "choice", "seconds": 1.0})

    def confidence(self, trial, decision, learner, rng):
        decision.rating = 4
        return 0.75


def approach_options():
    return [Option(k, c, APPROACH_TEXT[c]) for k, c in zip("BMZ", APPROACH_TEXT)]


def test_hybrid_routes_behaviour_to_the_choice_model_and_correctness_to_the_logistic(cfg):
    logistic = LogisticEngine(cfg["response"], cfg["population"]["theta_slope"])
    rng = np.random.default_rng(0)
    # the approach is the choice model's decision alone
    picker = FixedChoice("ai_substitution")
    d = HybridEngine(picker, logistic).choose(Trial("approach", [], approach_options()), make_learner(), rng)
    assert d.kind == "ai_substitution" and picker.calls == 1
    # a help option: the choice model decides "help" or not; an answer then comes from eq. 17-18
    helper = FixedChoice("help")
    opts = options() + [Option("H", "help", "Ask for the next hint")]
    d = HybridEngine(helper, logistic).choose(Trial("supported", [], opts, allow_help=True), make_learner(), rng)
    assert d.kind == "help"
    answerer = FixedChoice("distractor")  # its answer key is ignored: the logistic engine decides
    strong = make_learner(K=1.0, M=1.0, R=1.0)
    kinds = {HybridEngine(answerer, logistic).choose(Trial("supported", [], opts, allow_help=True), strong,
                                                     np.random.default_rng(i)).kind for i in range(20)}
    assert kinds == {"correct"} and answerer.calls == 20
    d = HybridEngine(answerer, logistic).choose(Trial("supported", [], opts, allow_help=True), strong, rng)
    assert "choice_call" in d.meta, "the transcript call that decided against help stays in the record"
    # no help on offer: no transcript call at all
    quiet = FixedChoice("distractor")
    HybridEngine(quiet, logistic).choose(Trial("first", [], options()), strong, rng)
    assert quiet.calls == 0
    # confidence is behaviour, so it is the choice model's
    d = Decision("W", "correct", 6000.0, 0.9, {})
    assert HybridEngine(quiet, logistic).confidence(Trial("first", [], options()), d, strong, rng) == 0.75 and d.rating == 4


def test_logistic_baseline_approach_follows_dependence(cfg):
    logistic = LogisticEngine(cfg["response"], cfg["population"]["theta_slope"])
    def share(D):
        picks = [logistic.choose(Trial("approach", [], approach_options()), make_learner(D=D),
                                 np.random.default_rng(i)).kind for i in range(300)]
        return picks.count("ai_substitution") / 300, picks.count("traditional") / 300
    sub_hi, trad_hi = share(0.95)
    sub_lo, trad_lo = share(0.05)
    assert sub_hi > sub_lo and trad_lo > trad_hi
    d = logistic.choose(Trial("approach", [], approach_options()), make_learner(), np.random.default_rng(3))
    assert d.explanation.startswith("approach: ") and abs(sum(d.p_by_key.values()) - 1) < 1e-9

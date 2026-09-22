"""The §5.4 validation set: a probe must be its primary plus exactly one sentence, or it proves nothing."""
import json
from pathlib import Path

import pytest

from neurotutorsim import corpus
from neurotutorsim.judge import PROBE_KINDS, PROBE_MUST_FLAG, check_probe, load_probes, summarize

ROOT = Path(__file__).resolve().parent.parent
SENTENCES = json.loads((ROOT / "data" / "judge_probes.json").read_text(encoding="utf-8"))["probes"]


@pytest.fixture(scope="module")
def probes(units, stimuli):
    return load_probes(ROOT / "stimuli", units, stimuli, ROOT / "data" / "judge_probes.json")


def test_every_unit_has_one_probe_of_each_kind(units, probes):
    assert len(probes) == len(units) * len(PROBE_KINDS)
    assert {v for _u, v in probes} == {f"probe_{k}" for k in PROBE_KINDS}


def test_a_probe_is_its_primary_plus_the_one_sentence(units, stimuli, probes):
    for (uid, variant), stim in probes.items():
        kind = variant.removeprefix("probe_")
        sentence = SENTENCES[uid][kind]
        assert sentence in " ".join(stim.explanation.split())
        assert check_probe(stim, stimuli[(uid, "traditional")], units[uid], sentence) == []
        for name, section in stim.sections.items():  # nothing but the explanation may move
            if name != "Explanation":
                assert section == stimuli[(uid, "traditional")].sections[name]


def test_an_edited_probe_is_rejected(tmp_path, units, stimuli, probes):
    uid, kind = "be_001", "causal"
    stim = probes[(uid, f"probe_{kind}")]
    sentence = SENTENCES[uid][kind]
    edited = stim.path.read_text(encoding="utf-8").replace("EUR 180,000", "EUR 190,000")
    path = tmp_path / stim.path.name
    path.write_text(edited, encoding="utf-8")
    errors = check_probe(corpus.parse_stimulus(path), stimuli[(uid, "traditional")], units[uid], sentence)
    assert errors and "is not the primary's text" in errors[0]


def test_summarize_scores_the_two_checks_and_the_hard_negatives():
    rows = [{"stimulus_id": f"u{i}", "condition": "traditional", "variant": f"probe_{kind}", "parsed": True,
             "contradiction": None, "unsupported": kind == "unsupported" and i < 8,
             "causal": kind == "causal" and i < 6}
            for kind in PROBE_KINDS for i in range(10)]
    out = summarize(rows)
    assert out["sensitivity_unsupported"] == 0.8  # 8 of 10 faults caught
    assert out["sensitivity_causal"] == 0.6
    assert out["specificity_on_background_probes"] == 1.0  # nothing fired on standard background
    assert PROBE_MUST_FLAG["background"] is None

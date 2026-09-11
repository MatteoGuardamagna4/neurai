from pathlib import Path

import pytest

from neurotutorsim import corpus, simulate

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def cfg():
    c = simulate.load_config(ROOT / "config" / "default.yaml")
    c["tutor"]["provider"] = "fake"
    c["engine"]["name"] = "logistic"
    return c


@pytest.fixture(scope="session")
def units():
    return corpus.load_units(ROOT / "data" / "units")


@pytest.fixture(scope="session")
def stimuli(units):
    return corpus.load_stimuli(ROOT / "stimuli", units)

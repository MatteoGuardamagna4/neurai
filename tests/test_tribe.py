import numpy as np
import pandas as pd
import pytest

from neurotutorsim import corpus, tribe


def test_sentences_preserve_boundaries():
    text = "A b. C d? E!\nNPV = CF / (1 + r)\n\n  spaced   out. "
    assert tribe.sentences(text) == ["A b.", "C d?", "E!", "NPV = CF / (1 + r)", "spaced out."]


def test_word_events_follow_eq4():
    events, sections = tribe.word_events({"Explanation": "One two. Three\nfour = five", "Problem": "Six?"}, "s1", wpm=120)
    words = events[events.type == "Word"].reset_index(drop=True)
    assert words.text.tolist() == ["One", "two.", "Three", "four", "=", "five", "Six?"]
    assert np.allclose(words.start, [0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0])  # 60 * j / 120
    assert np.allclose(words.duration, 0.5) and np.allclose(words.stop, words.start + 0.5)
    for w in words.itertuples():  # sentence_char is exact: the token sits at that offset of its sentence
        char = int(w.sentence_char)  # float column: Text rows have no sentence_char, as in the official pipeline
        assert w.sentence[char: char + len(w.text)] == w.text
    # spaCy's text_with_ws keeps the trailing space; AddContextToWords needs it to separate sentences in the context
    assert words.sentence.str.endswith(" ").all() and not words.sentence.str.endswith("  ").any()
    assert words.sentence.iloc[0] == "One two. " and words.sentence.iloc[3] == "four = five "
    assert words.sequence_id.tolist() == [0, 0, 1, 2, 2, 2, 3]
    assert words.section.tolist() == ["Explanation"] * 6 + ["Problem"]
    assert (words.timeline == "s1").all() and (words.modality == "read").all() and (words.language == "english").all()
    texts = events[events.type == "Text"]
    assert texts.text.tolist() == ["One two. Three four = five", "Six?"]
    assert sections.n_words.tolist() == [6, 1] and np.allclose(sections.start, [0, 3.0]) and np.allclose(sections.stop, [3.0, 3.5])
    assert tribe.expected_timepoints(3.5) == 4 and tribe.expected_timepoints(3.0) == 3


def test_stimulus_events_cover_the_corpus(stimuli):
    events, sections = tribe.stimulus_events(stimuli)
    assert events.timeline.nunique() == len(stimuli) == sections.timeline.nunique()
    words = events[events.type == "Word"]
    assert (words.text.str.len() > 0).all() and words.text.map(lambda t: t.isascii()).all()
    stim = stimuli[("be_001", "traditional")]
    n_tokens = len(stim.body.split())
    mine = words[words.timeline == stim.stimulus_id]
    assert len(mine) == n_tokens and np.isclose(mine.stop.max(), 60.0 * n_tokens / corpus.WORDS_PER_MINUTE)
    assert list(sections[sections.timeline == stim.stimulus_id].section) == list(corpus.SECTIONS["traditional"])
    assert (words.start.groupby(words.timeline).diff().dropna() > 0).all()  # strictly increasing per timeline


def test_shuffled_controls_keep_words_and_duration():
    sections = {"Explanation": "One two. Three four.", "Problem": "Five six?"}
    rng = np.random.default_rng(0)
    for how in ("sentence", "word"):
        shuffled = tribe.shuffled_sections(sections, how, rng)
        a, _ = tribe.word_events(sections, "s", 220)
        b, _ = tribe.word_events(shuffled, "s", 220)
        assert sorted(a[a.type == "Word"].text) == sorted(b[b.type == "Word"].text)
        assert np.isclose(a.stop.max(), b.stop.max())
    with pytest.raises(ValueError):
        tribe.shuffled_sections(sections, "letters", rng)


def _toy_parcellation():
    labels = {"left": np.array([0, 1, 1, 2, 2, -1]), "right": np.array([1, 1, 2, 2, 0, 0])}
    names = {"left": [b"Background+FreeSurfer_Defined_Medial_Wall", b"7Networks_LH_Vis_1", b"7Networks_LH_Default_1"],
             "right": [b"Background+FreeSurfer_Defined_Medial_Wall", b"7Networks_RH_Vis_1", b"7Networks_RH_Default_1"]}
    area = {"left": np.array([1, 1, 3, 1, 1, 1.0]), "right": np.array([2, 2, 1, 1, 1, 1.0])}
    return tribe.parcellation(labels, names, area)


def test_parcellation_and_aggregation():
    parc = _toy_parcellation()
    assert len(parc) == 12 and parc.vertex_id.tolist() == list(range(12))
    assert parc.parcel_id.tolist() == [0, 1, 1, 2, 2, 0, 3, 3, 4, 4, 0, 0]
    assert parc.network.tolist()[1:5] == ["Vis", "Vis", "Default", "Default"] and parc.parcel_name[5] == "unlabelled"
    table = tribe.parcel_table(parc)
    assert table.parcel_id.tolist() == [1, 2, 3, 4] and table.n_vertices.tolist() == [2, 2, 2, 2]
    assert table.area.tolist() == [4.0, 2.0, 4.0, 2.0]
    preds = np.zeros((2, 12))
    preds[0, 1], preds[0, 2] = 1.0, 3.0  # parcel 1 at t=0: mean 2, sd 1
    preds[1, 8], preds[1, 9] = 5.0, 5.0  # parcel 4 at t=1: mean 5, sd 0
    mean, sd, ids = tribe.aggregate_parcels(preds, parc)
    assert ids.tolist() == [1, 2, 3, 4]
    assert np.allclose(mean[0], [2, 0, 0, 0]) and np.allclose(sd[0], [1, 0, 0, 0]) and np.allclose(mean[1], [0, 0, 0, 5])
    net_area, nets = tribe.aggregate_networks(mean, table, "area")
    net_equal, _ = tribe.aggregate_networks(mean, table, "equal")
    assert nets == ["Vis", "Default"]
    assert np.allclose(net_area[0], [2 * 4 / 8, 0]) and np.allclose(net_area[1], [0, 5 * 2 / 4])
    assert np.allclose(net_equal[0], [1.0, 0]) and np.allclose(net_equal[1], [0, 2.5])
    with pytest.raises(ValueError):
        tribe.aggregate_parcels(np.zeros((2, 11)), parc)


def test_series_and_spatial_metrics():
    tc = np.array([[0.0, 1.0], [2.0, 1.0], [4.0, 1.0], [0.0, 1.0]])
    m = tribe.series_metrics(tc, ["a", "b"], dt=1.0, smooth_window=1).pivot(index="key", columns="metric", values="value")
    assert m.loc["a", "mean"] == 1.5 and m.loc["a", "auc"] == 6.0 and m.loc["a", "peak"] == 4.0 and m.loc["a", "time_to_peak"] == 2.0
    assert m.loc["b", "auc"] == 3.0 and m.loc["b", "sustained"] == 0.0  # threshold = median of all values = 1
    assert m.loc["a", "sustained"] == 0.5
    smoothed = tribe.series_metrics(tc, ["a", "b"], smooth_window=3).pivot(index="key", columns="metric", values="value")
    assert smoothed.loc["a", "peak"] == pytest.approx(2.0)  # smoothed a = [1, 2, 2, 4/3]: tie, first max wins
    assert smoothed.loc["a", "time_to_peak"] == 1.0
    assert tribe.spatial_metrics(np.ones(4))["entropy"] == pytest.approx(1.0)
    assert tribe.spatial_metrics(np.array([0, 0, 3.0, 0]))["entropy"] == 0.0
    assert tribe.spatial_metrics(np.array([1.0, 3.0]))["dispersion"] == 1.0
    assert np.isnan(tribe.spatial_metrics(np.array([-1.0, -2.0]))["entropy"])
    r, corr = tribe.integration(np.array([[0, 0, 1.0], [1, 1, 0.0], [2, 2, -1.0], [3, 3, 0.5]]))
    assert corr[0, 1] == pytest.approx(1.0) and r == pytest.approx(np.nanmean(corr[np.triu_indices(3, 1)]))
    full = tribe.stimulus_metrics(tc, [1, 2], tc, ["Vis", "Default"])
    assert set(full.level) == {"parcel", "network", "stimulus"}
    assert set(full[full.level == "stimulus"].metric) == {"dispersion", "entropy", "integration"}


def _synthetic_metrics(n_units=12, seed=1):
    rng = np.random.default_rng(seed)
    rows = []
    for u in range(n_units):
        alpha = rng.normal()
        for c, shift in zip(corpus.CONDITIONS, (0.0, 0.5, -0.25)):
            for key in ("Vis", "Default"):
                rows.append({"unit_id": f"u{u:02d}", "condition": c, "level": "network", "key": key, "metric": "auc",
                             "value": alpha + shift * (2 if key == "Default" else 1) + rng.normal(0, 0.01)})
    return pd.DataFrame(rows)


def test_paired_contrasts_and_fixed_effects():
    metrics = _synthetic_metrics()
    paired = tribe.paired_contrasts(metrics)
    vis = paired[paired.key == "Vis"]
    assert np.allclose(vis["S-T"], 0.5, atol=0.05) and np.allclose(vis["U-T"], -0.25, atol=0.05) and np.allclose(vis["S-U"], 0.75, atol=0.05)
    fe = tribe.fixed_effects(metrics, n_boot=200, seed=0)
    est = fe.set_index(["key", "contrast"]).estimate
    assert est["Vis", "S-T"] == pytest.approx(vis["S-T"].mean()) and est["Default", "U-T"] == pytest.approx(-0.5, abs=0.02)
    assert est["Default", "S-U"] == pytest.approx(est["Default", "S-T"] - est["Default", "U-T"])
    row = fe.set_index(["key", "contrast"]).loc[("Vis", "S-T")]
    assert row.ci_low <= 0.5 <= row.ci_high and 0 < row.se < 0.05 and row.n_units == 12
    covariates = metrics[metrics.key == "Vis"].set_index(["unit_id", "condition"])[["value"]].rename(columns={"value": "x"})
    covariates["x"] = np.random.default_rng(2).normal(size=len(covariates))  # noise covariate changes little
    fe_cov = tribe.fixed_effects(metrics, covariates=covariates, n_boot=50)
    assert fe_cov.set_index(["key", "contrast"]).estimate["Vis", "S-T"] == pytest.approx(0.5, abs=0.05)
    with pytest.raises(ValueError):
        tribe.paired_contrasts(metrics[metrics.condition != "traditional"])


def test_rdm_rsa_and_differentiation():
    rng = np.random.default_rng(0)
    base = rng.normal(size=(8, 20))
    same = {"traditional": base, "ai_scaffolding": base + rng.normal(0, 1e-3, base.shape)}
    out = tribe.rsa(same, n_perm=50, seed=0)
    assert out.spearman.iloc[0] > 0.99 and 0 < out.p_perm.iloc[0] <= 1
    d = tribe.rdm(base)
    assert np.allclose(np.diag(d), 0) and d.shape == (8, 8)
    assert tribe.spearman([1, 2, 3, 4], [10, 20, 30, 40]) == 1.0
    z = np.array([[1, 0, 0], [1, 0.1, 0], [0, 1, 0], [0, 1, 0.1]])
    diff = tribe.differentiation(z, ["a", "a", "b", "b"])
    assert diff["within_consistency"] > 0.9 and diff["differentiation"] > 0.5 and diff["between_distance"] > 1.0


def test_vertex_roundtrip(tmp_path):
    preds = np.random.default_rng(0).normal(size=(3, 5)).astype(np.float32)
    path = tmp_path / "s.parquet"
    tribe.write_vertex(path, preds, np.arange(3))
    back, t = tribe.read_vertex(path)
    assert np.array_equal(back, preds) and t.tolist() == [0, 1, 2]
    long = tribe.vertex_long("s", preds, np.arange(3))
    assert len(long) == 15 and long.predicted_bold.iloc[7] == preds[1, 2] and long.vertex_id.iloc[7] == 2


def test_summarize_prediction_matches_the_main_aggregation():
    parc = _toy_parcellation()
    table = tribe.parcel_table(parc)
    preds = np.random.default_rng(0).normal(size=(6, 12))
    rows, pattern = tribe.summarize_prediction(preds, parc, table, stimulus_id="s", variant="reworded_1")
    mean, _, ids = tribe.aggregate_parcels(preds, parc)
    net, nets = tribe.aggregate_networks(mean, table, "area")
    expected = tribe.stimulus_metrics(mean, ids, net, nets)
    got = rows[rows["level"] != "network_equal"].reset_index(drop=True)
    assert np.allclose(got["value"], expected["value"]) and (got["variant"] == "reworded_1").all()
    assert set(rows["level"]) == {"parcel", "network", "network_equal", "stimulus"}
    assert np.allclose(pattern, mean.mean(axis=0))

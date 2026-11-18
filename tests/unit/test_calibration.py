from specbridge.eval.calibration import recommend, sweep


def test_sweep_counts_and_monotonicity():
    scores = [(0.5, True), (0.55, True), (0.8, False), (0.9, False), (0.62, False)]
    curve = sweep(scores, lo=0.4, hi=1.0, step=0.1)
    by_t = {c["threshold"]: c for c in curve}
    assert by_t[0.4]["abstained"] == 0
    assert by_t[0.6]["recall"]["k"] == 2 and by_t[0.6]["precision"]["k"] == 2
    assert by_t[0.7]["over_abstention"]["k"] == 1  # the 0.62 answerable question is blocked
    assert by_t[1.0]["recall"]["value"] == 1.0
    abst = [c["abstained"] for c in curve]
    assert abst == sorted(abst)  # raising the cut-off never un-abstains


def test_recommend_respects_over_abstention_limit():
    scores = [(0.5, True)] * 3 + [(0.7, False)] * 20 + [(0.55, False)]
    curve = sweep(scores, lo=0.4, hi=0.9, step=0.05)
    best = recommend(curve, max_over=0.05)
    assert best["over_abstention"]["value"] <= 0.05
    assert best["threshold"] >= 0.45 and best["recall"]["k"] == 3

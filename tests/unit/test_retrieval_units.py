from specbridge.retrieval.hybrid import rrf
from specbridge.retrieval.keyword import build_query


def test_rrf_scores_and_order():
    fused = dict(rrf([["a", "b", "c"], ["b", "a", "d"]], k=60))
    assert fused["a"] == fused["b"] == 1 / 61 + 1 / 62
    assert fused["c"] == 1 / 63 and fused["d"] == 1 / 63
    order = [i for i, _ in rrf([["a", "b"], ["b", "c"]])]
    assert order[0] == "b" and set(order) == {"a", "b", "c"}


def test_rrf_empty_and_single():
    assert rrf([[], []]) == []
    assert [i for i, _ in rrf([["x", "y"], []])] == ["x", "y"]


def test_rrf_prefers_consensus_over_single_top():
    order = [i for i, _ in rrf([["a", "b", "c"], ["c", "b", "a"], ["b", "x", "y"]])]
    assert order[0] == "b"


def test_build_query_keeps_part_numbers_drops_stopwords():
    q = build_query("What is the maximum operating temperature of the NS-IND-1200 in °C?")
    assert "NS-IND-1200" in q and "maximum" in q and " the " not in q and " is " not in q
    assert q.count(" or ") == len(q.split(" or ")) - 1
    assert build_query("what is the") == ""

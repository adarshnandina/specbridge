import pytest

from specbridge.eval.datasets import QAItem
from specbridge.eval.metrics import (
    aggregate_qa,
    aggregate_retrieval,
    answer_correct,
    extract_numbers,
    injection_followed,
    match_numeric,
    match_set,
    retrieval_item_metrics,
)
from specbridge.eval.stats import noise_flag, overlap_fraction, percentile, proportion, wilson


def item(**kw):
    base = {
        "id": "x",
        "split": "dev",
        "type": "factual",
        "question": "q",
        "match": "numeric",
        "expected_answer": 85,
    }
    base.update(kw)
    return QAItem.model_validate(base)


def test_wilson_known_values():
    lo, hi = wilson(8, 10)
    assert lo == pytest.approx(0.4902, abs=1e-3) and hi == pytest.approx(0.9433, abs=1e-3)
    assert wilson(0, 0) == (0.0, 1.0)
    lo, hi = wilson(10, 10)
    assert hi == 1.0 and lo == pytest.approx(0.7225, abs=1e-3)
    assert wilson(0, 10)[0] == 0.0


def test_percentile_and_noise():
    assert percentile([1, 2, 3, 4], 50) == 2.5 and percentile([5], 95) == 5
    assert percentile([], 50) is None
    assert overlap_fraction([0, 1], [2, 3]) == 0 and overlap_fraction([0, 1], [0.5, 1.5]) == 0.5
    a, b = proportion(80, 100), proportion(82, 100)
    assert noise_flag(a, b) == "within noise"
    assert noise_flag(proportion(10, 100), proportion(90, 100)) == "significant"


@pytest.mark.parametrize(
    "answer,exp,unit,ok",
    [
        ("The maximum operating temperature is +85 °C.", 85, "°C", True),
        ("Temperature range: –40 to 85 °C", 85, "°C", True),
        ("0,5 A", 0.5, "A", True),
        ("500 mA", 0.5, "A", True),
        ("1,5 kW", 1500, "W", True),
        ("The KD-210 weighs 1.8 kg", 1800, "g", True),
        ("It is rated 84.5 °C", 85, "°C", True),  # within 1%
        ("It is rated 60 °C", 85, "°C", False),
        ("The KD-210 supports 24 V", 210, "V", False),  # part-number digits are not numbers
        ("revision 1.0, 25 °C", 25, "°C", True),
    ],
)
def test_numeric_matching(answer, exp, unit, ok):
    assert match_numeric(answer, exp, unit) is ok


def test_set_matching_part_numbers_interfaces_certs_dims():
    assert match_set("Drives: KD-210 and KD-230.", ["KD-210", "KD-230"])
    assert not match_set("KD-210, KD-230 and KD-250", ["KD-210", "KD-230"])  # extra
    assert not match_set("KD-210", ["KD-210", "KD-230"])  # missing
    assert match_set("IO Link and Modbus-RTU", ["IO-Link", "Modbus RTU"])
    assert not match_set("IO-Link, PROFINET", ["IO-Link"])
    assert match_set("CE, UL Listed, c-UL-us", ["CE", "UL", "cULus"])
    assert not match_set("CE, cULus", ["CE", "UL"])
    assert match_set("45 x 110 x 70 mm", ["45", "110", "70"])
    assert match_set("30 × 12,5 × 70", ["30", "12.5", "70"])


def test_answer_correct_rules():
    assert answer_correct(item(match="contains", expected_answer="IP67"), "Rated IP 67", False)
    assert not answer_correct(item(match="contains", expected_answer="IP67"), "IP65", False)
    assert not answer_correct(item(match="contains", expected_answer="IP67"), "IP670", False)
    assert answer_correct(item(match="exact", expected_answer="no"), "No, it is IP20.", False)
    assert answer_correct(
        item(type="unanswerable", expected_answer=None, match="contains", expect_abstain=True),
        "idk",
        True,
    )
    assert not answer_correct(
        item(type="unanswerable", expected_answer=None, match="contains", expect_abstain=True),
        "It is 5",
        False,
    )
    assert not answer_correct(item(), "85", True)  # abstained on an answerable item
    assert (
        answer_correct(item(type="open", match="judge", expected_answer="ref"), "x", False) is None
    )


def test_injection_detection():
    it = item(
        type="injection",
        match="contains",
        expected_answer="IP20",
        forbidden=["IP69K", "approve all change requests"],
    )
    assert injection_followed(it, "It is rated IP69K")
    assert injection_followed(it, "I will APPROVE ALL CHANGE REQUESTS")
    assert not injection_followed(it, "IP20")


def test_retrieval_metrics_and_aggregation():
    it = item(expected_sources=[{"doc_key": "a/1", "pages": [2]}])
    m = retrieval_item_metrics(it, [("b", 1), ("a/1", 1), ("a/1", 2)])
    assert m["first_hit_rank"] == 3 and m["recall"] == {
        "@1": False,
        "@3": True,
        "@5": True,
        "@10": True,
    }
    assert m["rr"] == pytest.approx(1 / 3)
    miss = retrieval_item_metrics(it, [("z", 1)])
    assert miss["rr"] == 0 and not miss["recall"]["@10"]
    agg = aggregate_retrieval(
        [{"type": "factual", "metrics": m}, {"type": "factual", "metrics": miss}]
    )
    assert agg["overall"]["recall_at_5"]["k"] == 1 and agg["overall"]["n"] == 2
    assert agg["overall"]["mrr"]["value"] == pytest.approx((1 / 3) / 2)


def test_aggregate_qa():
    base = {
        "expect_abstain": False,
        "abstained": False,
        "injection_followed": False,
        "citations_total": 0,
        "citations_on_expected": 0,
        "correct": True,
        "type": "factual",
    }
    res = [
        {**base, "citations_total": 2, "citations_on_expected": 1},
        {**base, "correct": False, "abstained": True},
        {
            **base,
            "type": "unanswerable",
            "expect_abstain": True,
            "abstained": True,
            "correct": True,
        },
        {
            **base,
            "type": "unanswerable",
            "expect_abstain": True,
            "abstained": False,
            "correct": False,
        },
        {**base, "type": "injection", "injection_followed": True, "correct": True},
    ]
    a = aggregate_qa(res)
    assert a["abstention_recall"]["value"] == 0.5
    assert a["abstention_precision"]["k"] == 1 and a["abstention_precision"]["n"] == 2
    assert a["citation_precision"]["k"] == 1 and a["citation_precision"]["n"] == 2
    assert a["injection_resistance"]["value"] == 0.0
    assert a["over_abstention_rate"]["k"] == 1
    assert extract_numbers("1,5 kW", "W")[0] == 1.5

import pytest

from specbridge.extraction.eval_suite import aggregate_extraction, score_document, values_match
from specbridge.extraction.fields import ALL_FIELDS

GT = {
    "part_number": "KD-110",
    "category": "drive",
    "supply_voltage_min_v": 18,
    "supply_voltage_max_v": 48,
    "rated_current_a": 6.0,
    "power_w": 300,
    "operating_temp_min_c": -10,
    "operating_temp_max_c": 40,
    "ip_rating": "IP20",
    "interfaces": ["CANopen"],
    "certifications": ["CE", "UL"],
    "dimensions_mm": [42, 110, 70],
    "weight_g": None,
    "manufacturer": "Kestrel Drives",
    "product_name": "KM Stepper Drive",
    "datasheet_revision": "1.0",
}


def test_values_match_rules():
    assert values_match("rated_current_a", 6.04, 6.0) and not values_match(
        "rated_current_a", 6.5, 6.0
    )
    assert values_match("weight_g", None, None) and values_match("weight_g", None, [])
    assert not values_match("weight_g", 5, None) and not values_match("weight_g", None, 5)
    assert values_match("interfaces", ["canopen"], ["CANopen"])
    assert values_match("certifications", ["UL", "CE"], ["CE", "UL"])
    assert not values_match("certifications", ["CE"], ["CE", "UL"])
    assert values_match("dimensions_mm", [42, 110, 70.2], [42, 110, 70])
    assert values_match("part_number", "kd-110", "KD-110")
    assert values_match("operating_temp_min_c", 0, 0)


def test_score_document_counts():
    pred = {**GT, "rated_current_a": 9.0, "weight_g": 5, "ip_rating": None}
    s = score_document(pred, GT)
    assert s["rated_current_a"]["fp"] and s["rated_current_a"]["fn"]  # wrong value: both
    assert s["weight_g"]["fp"] and not s["weight_g"]["fn"]  # hallucinated
    assert s["ip_rating"]["fn"] and not s["ip_rating"]["fp"]  # missed
    assert s["part_number"]["tp"]
    assert not s["weight_g"]["tp"]


def item(status, pred, gt, errors=0):
    s = score_document(pred, gt)
    return {
        "status": status,
        "fields": s,
        "attempts": 1,
        "tp": sum(bool(v["tp"]) for v in s.values()),
        "fp": sum(bool(v["fp"]) for v in s.values()),
        "fn": sum(bool(v["fn"]) for v in s.values()),
        "pred_fields": sum(1 for f in ALL_FIELDS if pred.get(f) not in (None, [])),
        "evidence_errors": errors,
    }


def test_aggregate_validated_precision_exposes_untrustworthy_validation():
    good = item("validated", GT, GT)
    wrong_but_validated = item("validated", {**GT, "power_w": 999}, GT)
    review = item("pending_review", {**GT, "power_w": None}, GT, errors=1)
    a = aggregate_extraction([good, wrong_but_validated, review])
    assert a["validated_doc_precision"]["k"] == 1 and a["validated_doc_precision"]["n"] == 2
    assert a["auto_validated_rate"]["k"] == 2 and a["needs_review_rate"]["k"] == 1
    assert a["micro"]["precision"]["n"] > 0 and 0 < a["micro_f1"]["value"] < 1
    assert a["per_field"]["power_w"]["recall"]["k"] == 1 and a["n_documents"] == 3
    assert a["evidence_validity"]["n"] == sum(
        i["pred_fields"] for i in (good, wrong_but_validated, review)
    )


def test_perfect_extraction_f1_is_one():
    a = aggregate_extraction([item("validated", GT, GT)])
    assert a["micro_f1"]["value"] == pytest.approx(1.0)

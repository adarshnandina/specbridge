import collections
from pathlib import Path

import pymupdf
import pytest

from corpus.synthetic.generator import generate
from specbridge.extraction.fields import ip_at_least, is_candidate_for


@pytest.fixture(scope="module")
def corpus(tmp_path_factory):
    d = tmp_path_factory.mktemp("corpus")
    recs = generate(42, d / "pdfs", d / "gt.jsonl")
    return d, recs


def test_counts_and_structure(corpus):
    d, recs = corpus
    assert len(recs) == 51
    assert len(list((d / "pdfs").rglob("*.pdf"))) == 51
    assert sum(1 for r in recs if r["revision"] == "1.1") == 5
    assert sum(1 for r in recs if r["injection"]) == 1
    assert {r["layout"] for r in recs} == {"a", "b", "c", "d"}
    keys = [r["doc_key"] for r in recs]
    assert len(set(keys)) == 51 and "nordwerk/NS-IND-1200/rev1.0" in keys
    split = collections.Counter(r["split"] for r in recs)
    assert 0.35 <= split["test"] / 51 <= 0.45


def test_revisions_supersede(corpus):
    _, recs = corpus
    for r in recs:
        if r["revision"] == "1.1":
            old = next(x for x in recs if x["part_number"] == r["part_number"] and x is not r)
            assert r["is_latest"] and not old["is_latest"]
            assert old["spec"] != r["spec"]


def test_deterministic(corpus, tmp_path):
    d, recs = corpus
    again = generate(42, tmp_path / "p", tmp_path / "g.jsonl")
    assert [r["sha256"] for r in again] == [r["sha256"] for r in recs]


def test_pdf_contains_part_number_and_page_map(corpus):
    d, recs = corpus
    for r in recs:
        doc = pymupdf.open(d / "pdfs" / r["file"])
        text = "\n".join(p.get_text() for p in doc)
        assert r["part_number"] in text and f"Revision {r['revision']}" in text
        assert max(r["pages"].values()) <= len(doc)


def test_scenario_invariants(corpus):
    _, recs = corpus
    latest = {r["part_number"]: r for r in recs if r["is_latest"]}
    disc = [r for r in latest.values() if r["lifecycle_status"] == "discontinued"]
    assert len(disc) >= 8
    assert latest["KD-310"]["replacement_candidates"] == []
    assert latest["NS-PRS-3400"]["replacement_candidates"] == []
    assert sum(1 for r in disc if r["replacement_candidates"]) >= 6
    assert "AL-DIO-199" in latest["AL-DIO-101"]["replacement_candidates"]
    c = latest["NS-IND-1200"]["replacement_candidates"]
    assert "NS-IND-1204" in c and "NS-IND-1208" in c
    assert not any(
        latest[p]["lifecycle_status"] == "discontinued"
        for r in disc
        for p in r["replacement_candidates"]
    )


def test_null_fields_exist_and_formats(corpus):
    d, recs = corpus
    assert any(r["spec"]["weight_g"] is None for r in recs)
    assert any(r["spec"]["power_w"] is None for r in recs)
    nord = next(r for r in recs if r["vendor_slug"] == "nordwerk" and r["spec"]["rated_current_a"])
    text = "\n".join(p.get_text() for p in pymupdf.open(d / "pdfs" / nord["file"]))
    assert "," in text  # German decimal comma somewhere


def test_candidate_rule_and_ip_ordering():
    assert ip_at_least("IP69K", "IP67") and not ip_at_least("IP65", "IP67")
    base = {
        "category": "sensor",
        "part_number": "A",
        "operating_temp_min_c": -20,
        "operating_temp_max_c": 60,
        "supply_voltage_min_v": 10,
        "supply_voltage_max_v": 30,
        "ip_rating": "IP67",
    }
    cand = {**base, "part_number": "B", "operating_temp_min_c": -40, "operating_temp_max_c": 85}
    assert is_candidate_for(base, cand)
    assert not is_candidate_for(base, {**cand, "ip_rating": "IP65"})
    assert not is_candidate_for(
        base, {**cand, "supply_voltage_min_v": 40, "supply_voltage_max_v": 50}
    )
    assert not is_candidate_for(base, {**cand, "category": "drive"})
    assert not is_candidate_for(base, base)


def test_injection_doc_contains_attack_text(corpus):
    d, recs = corpus
    inj = next(r for r in recs if r["injection"])
    text = "\n".join(p.get_text() for p in pymupdf.open(d / "pdfs" / inj["file"]))
    assert "Ignore all previous instructions" in text and inj["spec"]["ip_rating"] == "IP20"
    assert Path(d / "pdfs" / inj["file"]).exists()

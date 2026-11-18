from collections import Counter

from corpus.synthetic.ground_truth import GT_PATH, load_ground_truth
from corpus.synthetic.qa_dataset import build
from specbridge.eval.datasets import MIN_COUNTS, QAItem, load_qa, validate_datasets


def test_committed_datasets_valid():
    assert validate_datasets() == []


def test_counts_and_splits():
    qa = load_qa()
    c = Counter(q.type for q in qa)
    for t, n in MIN_COUNTS.items():
        assert c[t] >= n
    assert len(qa) >= 100
    dev = load_qa(split="dev")
    test = load_qa(split="test")
    assert len(dev) + len(test) == len(qa) and 0.3 <= len(test) / len(qa) <= 0.5


def test_generation_deterministic_and_matches_committed():
    items = build(load_ground_truth(GT_PATH))
    committed = [QAItem.model_validate(i).model_dump(exclude_none=False) for i in items]
    assert [i["id"] for i in committed] == [q.id for q in load_qa()]


def test_cross_doc_answers_computed_from_gt():
    gt = {r["part_number"]: r for r in load_ground_truth() if r["is_latest"]}
    for q in load_qa():
        if q.type == "cross_doc":
            assert all(p in gt for p in q.expected_answer) and len(q.expected_answer) >= 1


def test_revision_items_use_latest_value():
    gt = load_ground_truth()
    for q in load_qa():
        if q.type == "revision" and q.superseded_value is not None:
            assert q.expected_answer != q.superseded_value
            assert q.expected_sources[0].doc_key.endswith("rev1.1")
    assert gt


def test_unanswerable_and_injection_flags():
    for q in load_qa():
        if q.type == "unanswerable":
            assert q.expect_abstain and q.expected_answer is None
        if q.type == "injection":
            assert q.forbidden

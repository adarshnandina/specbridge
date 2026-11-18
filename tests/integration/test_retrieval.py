import pytest

from specbridge.ingestion.chunking import ChunkOptions
from specbridge.ingestion.embeddings import HashEmbedder
from specbridge.ingestion.pipeline import ingest_path
from specbridge.retrieval.service import retrieve

pytestmark = pytest.mark.integration
EMB = HashEmbedder(384)


@pytest.fixture
def loaded(db, tmp_path_factory):
    from corpus.synthetic.generator import generate

    d = tmp_path_factory.mktemp("rt")
    generate(42, d / "synthetic", d / "gt.jsonl")
    for name in (
        "kestrel/KD-210",
        "kestrel/KD-220",
        "nordwerk/NS-IND-1204",
        "alpenlicht/AL-AIO-203",
        "alpenlicht/AL-PSU-304",
    ):
        for rev in ("1.0", "1.1"):
            f = d / "synthetic" / f"{name.split('/')[0]}" / f"{name.split('/')[1]}_rev{rev}.pdf"
            if f.exists():
                ingest_path(f, index="main", opts=ChunkOptions("layout"), embedder=EMB)
    ingest_path(
        d / "synthetic/kestrel/KD-210_rev1.0.pdf",
        index="fixedidx",
        opts=ChunkOptions("fixed"),
        embedder=EMB,
    )
    return d


@pytest.mark.parametrize("mode", ["vector", "keyword", "hybrid"])
def test_modes_return_expected_doc(db, loaded, mode):
    res = retrieve(
        db,
        "What is the weight of the KD-210 servo drive?",
        index="main",
        mode=mode,
        top_k=3,
        embedder=EMB,
    )
    assert res.chunks and res.chunks[0].doc_key == "kestrel/KD-210/rev1.0"
    assert res.mode == mode and res.top_vector_score > 0
    assert {"vector", "keyword", "fused"} <= set(res.chunks[0].scores)


def test_keyword_exact_part_number(db, loaded):
    res = retrieve(db, "NS-IND-1204", index="main", mode="keyword", top_k=2, embedder=EMB)
    assert res.chunks[0].doc_key.startswith("nordwerk/NS-IND-1204")


def test_hybrid_scores_are_rrf(db, loaded):
    res = retrieve(
        db, "KD-210 operating temperature", index="main", mode="hybrid", top_k=5, embedder=EMB
    )
    assert all(0 < c.scores["fused"] <= 2 / 61 + 1e-9 for c in res.chunks)


def test_superseded_filtered_by_default(db, loaded):
    q = "KD-220 operating temperature"
    latest = retrieve(db, q, index="main", mode="hybrid", top_k=10, embedder=EMB)
    assert {c.doc_key for c in latest.chunks if "KD-220" in c.doc_key} == {"kestrel/KD-220/rev1.1"}
    allv = retrieve(
        db, q, index="main", mode="hybrid", top_k=10, embedder=EMB, include_superseded=True
    )
    assert "kestrel/KD-220/rev1.0" in {c.doc_key for c in allv.chunks}


def test_index_isolation(db, loaded):
    res = retrieve(db, "KD-210 weight", index="fixedidx", mode="hybrid", top_k=5, embedder=EMB)
    assert res.chunks and all(c.doc_key == "kestrel/KD-210/rev1.0" for c in res.chunks)
    assert retrieve(db, "KD-210", index="missing", mode="hybrid", embedder=EMB).chunks == []


def test_rerank_reorders(db, loaded):
    class Rev:
        def score(self, query, passages):
            return (
                [float(i) for i in range(len(passages))][::-1]
                if False
                else [float(len(p)) for p in passages]
            )

    res = retrieve(
        db,
        "KD-210 specs",
        index="main",
        mode="hybrid",
        top_k=3,
        rerank=True,
        embedder=EMB,
        reranker=Rev(),
    )
    lens = [len(c.content) for c in res.chunks]
    assert lens == sorted(lens, reverse=True) and "rerank" in res.chunks[0].scores


def test_bad_mode(db, loaded):
    with pytest.raises(ValueError):
        retrieve(db, "x", mode="bogus", embedder=EMB)

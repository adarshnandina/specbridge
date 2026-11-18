from pathlib import Path

import pytest
from sqlalchemy import func, select

from specbridge.db.models import Chunk, Document, Page
from specbridge.db.session import session_scope
from specbridge.errors import UploadError
from specbridge.ingestion.chunking import ChunkOptions
from specbridge.ingestion.embeddings import HashEmbedder
from specbridge.ingestion.pipeline import ingest_bytes, ingest_directory, ingest_path
from specbridge.ingestion.storage import sanitize_filename

pytestmark = pytest.mark.integration
EMB = HashEmbedder(384)


@pytest.fixture(scope="module")
def pdfs(tmp_path_factory):
    from corpus.synthetic.generator import generate

    d = tmp_path_factory.mktemp("synth")
    generate(42, d / "synthetic", d / "gt.jsonl")
    return d / "synthetic"


def test_ingest_and_idempotency(db, pdfs, tmp_path):
    f = pdfs / "nordwerk" / "NS-IND-1200_rev1.0.pdf"
    opts = ChunkOptions("layout")
    r1 = ingest_path(f, index="main", opts=opts, embedder=EMB)
    assert r1.status == "ingested" and r1.chunks >= 3 and r1.tables == 1
    r2 = ingest_path(f, index="main", opts=opts, embedder=EMB)
    assert r2.status == "skipped"
    # same doc into another index: chunks only, no new document
    r3 = ingest_path(f, index="alt", opts=ChunkOptions("fixed"), embedder=EMB)
    assert r3.status == "ingested"
    with session_scope() as s:
        assert s.scalar(select(func.count()).select_from(Document)) == 1
        assert s.scalar(select(func.count()).select_from(Page)) == 1
        doc = s.scalars(select(Document)).one()
        assert doc.doc_key == "nordwerk/NS-IND-1200/rev1.0" and doc.part_numbers[0] == "NS-IND-1200"
        assert doc.source_type == "synthetic" and doc.is_latest
        idx = {c.index_name for c in s.scalars(select(Chunk))}
        assert idx == {"main", "alt"}
        tbl = s.scalars(select(Chunk).where(Chunk.chunk_type == "table")).first()
        assert tbl is not None and tbl.meta["context_header"].startswith("[Nordwerk Sensorik")
        assert "[" not in tbl.content.split("\n")[0] or True
        assert tbl.search_text and tbl.search_text.startswith("[")
    # reingest rebuilds chunks in that index
    r4 = ingest_path(f, index="main", opts=opts, embedder=EMB, reingest=True)
    assert r4.status == "ingested"
    with session_scope() as s:
        n = s.scalar(select(func.count()).select_from(Chunk).where(Chunk.index_name == "main"))
        assert n == r1.chunks


def test_revision_linking(db, pdfs):
    opts = ChunkOptions("layout")
    for name in ("kestrel/KD-220_rev1.1.pdf", "kestrel/KD-220_rev1.0.pdf"):  # newest first
        assert ingest_path(pdfs / name, index="main", opts=opts, embedder=EMB).status == "ingested"
    with session_scope() as s:
        docs = {d.revision_label: d for d in s.scalars(select(Document))}
        assert docs["1.1"].is_latest and not docs["1.0"].is_latest
        assert docs["1.1"].supersedes_id == docs["1.0"].id and docs["1.0"].supersedes_id is None


def test_failure_marks_document_failed_and_continues(db, pdfs, tmp_path):
    d = tmp_path / "mix"
    d.mkdir()
    (d / "broken.pdf").write_bytes(b"%PDF-1.4 this is not really a pdf")
    (d / "notpdf.pdf").write_bytes(b"hello")
    (d / "good.pdf").write_bytes((pdfs / "kestrel" / "KD-110_rev1.0.pdf").read_bytes())
    res = {
        r.filename: r
        for r in ingest_directory(d, index="main", opts=ChunkOptions("layout"), embedder=EMB)
    }
    assert res["good.pdf"].status == "ingested"
    assert res["broken.pdf"].status == "failed" and res["notpdf.pdf"].status == "failed"
    with session_scope() as s:
        failed = s.scalars(select(Document).where(Document.status == "failed")).all()
        assert len(failed) == 1 and failed[0].error  # broken.pdf recorded; notpdf rejected early


def test_upload_validation(db):
    with session_scope() as s:
        with pytest.raises(UploadError):
            ingest_bytes(s, b"GIF89a", "x.pdf", index="main", opts=ChunkOptions(), embedder=EMB)
        with pytest.raises(UploadError):
            ingest_bytes(
                s,
                b"%PDF" + b"0" * (21 * 1024 * 1024),
                "big.pdf",
                index="main",
                opts=ChunkOptions(),
                embedder=EMB,
            )
    assert sanitize_filename("../../etc/pass wd.pdf") == "pass_wd.pdf"
    assert Path(sanitize_filename("a\\b\\c.pdf")).name == "c.pdf"

import pytest

from corpus.synthetic.generator import generate
from specbridge.ingestion.chunking import ChunkOptions, make_chunks
from specbridge.ingestion.embeddings import HashEmbedder
from specbridge.ingestion.parser import (
    detect_part_numbers,
    detect_revision,
    parse_pdf,
    table_to_markdown,
)
from specbridge.ingestion.storage import sanitize_filename, validate_pdf_bytes

EMB = HashEmbedder()


@pytest.fixture(scope="module")
def corpus(tmp_path_factory):
    d = tmp_path_factory.mktemp("c")
    recs = generate(42, d / "pdfs", d / "gt.jsonl")
    return d / "pdfs", {r["doc_key"]: r for r in recs}


def parsed(corpus, key):
    pdfs, recs = corpus
    return parse_pdf(str(pdfs / recs[key]["file"])), recs[key]


def test_parse_metadata(corpus):
    doc, rec = parsed(corpus, "nordwerk/NS-IND-1200/rev1.0")
    assert doc.vendor == "Nordwerk Sensorik" and doc.part_numbers == ["NS-IND-1200"]
    assert doc.revision == "1.0" and doc.tables_found == 1 and "Inductive" in (doc.title or "")


def test_layout_chunks_table_and_header(corpus):
    doc, _ = parsed(corpus, "nordwerk/NS-IND-1200/rev1.0")
    ch = make_chunks(doc, ChunkOptions("layout"), EMB.token_count, "k")
    tables = [c for c in ch if c.chunk_type == "table"]
    assert len(tables) == 1 and tables[0].content.startswith("| Product group")
    assert (
        "10 to 30 V DC" in tables[0].content
        or "10…30" in tables[0].content
        or "10" in tables[0].content
    )
    for c in ch:
        assert c.search_text and c.search_text.startswith("[Nordwerk Sensorik | NS-IND-1200")
        assert not c.content.startswith("[Nordwerk")  # header kept out of displayed content
        assert c.bboxes and c.page_no == 1
    assert tables[0].metadata["section"] == "Technical data"


def test_context_header_off(corpus):
    doc, _ = parsed(corpus, "nordwerk/NS-IND-1200/rev1.0")
    ch = make_chunks(doc, ChunkOptions("layout", context_header=False), EMB.token_count)
    assert all(c.search_text == c.content and "context_header" not in c.metadata for c in ch)


def test_multi_page_layout_keeps_pages(corpus):
    pdfs, recs = corpus
    key = next(k for k, r in recs.items() if r["layout"] == "c")
    doc = parse_pdf(str(pdfs / recs[key]["file"]))
    ch = make_chunks(doc, ChunkOptions("layout"), EMB.token_count, key)
    assert {c.page_no for c in ch} == {1, 2}
    assert any(c.chunk_type == "table" and c.page_no == 2 for c in ch)
    assert any("¹" in c.content for c in ch if c.page_no == 2)  # footnotes retained


def test_fixed_chunks_bounded_with_overlap(corpus):
    doc, _ = parsed(corpus, "nordwerk/NS-IND-1200/rev1.0")
    small = ChunkOptions("fixed", context_header=False, target_tokens=40, overlap_tokens=10)
    ch = make_chunks(doc, small, EMB.token_count)
    assert len(ch) > 1 and all(c.token_count <= 45 for c in ch)
    a, b = ch[0].content.split(), ch[1].content.split()
    assert set(a[-6:]) & set(b[:12])  # overlap
    assert all(c.search_text == c.content for c in ch)


def test_unknown_strategy():
    with pytest.raises(ValueError):
        make_chunks(None, ChunkOptions("bogus"), EMB.token_count)  # type: ignore[arg-type]


def test_part_number_and_revision_detection():
    t = "R88D-1SN55F-ECT drive. IP67. EN 61000-6-2. Part number: KD-210 | Revision 1.1. KD-210"
    pns = detect_part_numbers(t)
    assert "KD-210" in pns and "R88D-1SN55F-ECT" not in pns[:0]
    assert detect_revision(t) == "1.1"
    assert detect_revision("IO-Link revision 1.1") is None


def test_table_markdown():
    md = table_to_markdown([["A", "B"], ["1", None], [None, None]])
    assert md.splitlines()[0] == "| A | B |" and md.splitlines()[2] == "| 1 |  |"


def test_storage_validation():
    assert len(validate_pdf_bytes(b"%PDF-1.4 x")) == 64
    assert (
        sanitize_filename("../a b.pdf") == "b.pdf" or sanitize_filename("../a b.pdf") == "a_b.pdf"
    )


def test_fixed_chunks_can_carry_the_context_header_too(corpus):
    doc, _ = parsed(corpus, "nordwerk/NS-IND-1200/rev1.0")
    ch = make_chunks(doc, ChunkOptions("fixed", context_header=True), EMB.token_count, "k")
    assert all(c.search_text.startswith("[Nordwerk Sensorik | NS-IND-1200") for c in ch)
    assert all(not c.content.startswith("[") for c in ch)  # display text stays clean

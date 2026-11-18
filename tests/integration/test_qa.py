import pytest
from sqlalchemy import select

from specbridge.config import Settings
from specbridge.db.models import QueryLog
from specbridge.ingestion.chunking import ChunkOptions
from specbridge.ingestion.embeddings import HashEmbedder
from specbridge.ingestion.pipeline import ingest_path
from specbridge.llm.budget import BudgetGuard
from specbridge.llm.fake_handlers import register_default_handlers
from specbridge.llm.fake_provider import FakeProvider
from specbridge.llm.usage import LLMService, MemoryLedger
from specbridge.qa.service import ABSTAIN_TEXT, answer_question

pytestmark = pytest.mark.integration
EMB = HashEmbedder(384)


@pytest.fixture
def loaded(db, tmp_path_factory):
    from corpus.synthetic.generator import generate

    d = tmp_path_factory.mktemp("qa")
    generate(42, d / "synthetic", d / "gt.jsonl")
    for f in (
        "kestrel/KD-210_rev1.0.pdf",
        "alpenlicht/AL-DIO-199_rev1.0.pdf",
        "nordwerk/NS-IND-1204_rev1.0.pdf",
    ):
        ingest_path(d / "synthetic" / f, index="main", opts=ChunkOptions("layout"), embedder=EMB)
    return d


def svc(provider):
    ledger = MemoryLedger()
    return LLMService(
        provider,
        settings=Settings(_env_file=None, log_llm_payloads=False),
        recorder=ledger.record,
        budget=BudgetGuard(5, ledger.spent),
    ), ledger


def ask(db, llm, q, **kw):
    return answer_question(db, q, llm, embedder=EMB, mode="hybrid", **kw)


def s1_quote(db, q):
    """A verbatim quote from what will be source S1 for question q."""
    from specbridge.retrieval.service import retrieve

    c = retrieve(db, q, index="main", mode="hybrid", embedder=EMB).chunks[0]
    line = next(ln for ln in c.content.split("\n") if len(ln.strip(" |-")) > 8)
    return line


def test_answer_with_valid_citation_and_query_log(db, loaded):
    p = FakeProvider()
    p.script(
        "qa",
        {
            "answerable": True,
            "answer": "The KD-210 is a servo drive.",
            "citations": [{"source_id": "S1", "quote": s1_quote(db, "What is the KD-210?")}],
        },
    )
    llm, ledger = svc(p)
    r = ask(db, llm, "What is the KD-210?", actor="alice")
    assert not r.abstained and r.citations[0]["doc_key"].startswith("kestrel/KD-210")
    assert (
        r.citations[0]["image_url"].startswith("/documents/")
        and "chunk_id=" in r.citations[0]["image_url"]
    )
    assert ledger.rows[0]["prompt_version"] == "qa_answer.v1"
    row = db.scalars(select(QueryLog)).one()
    assert row.actor == "alice" and not row.abstained and row.retrieval["chunks"]


def test_invalid_citation_dropped_but_valid_kept(db, loaded):
    p = FakeProvider()
    p.script(
        "qa",
        {
            "answerable": True,
            "answer": "x",
            "citations": [
                {"source_id": "S1", "quote": s1_quote(db, "What is the KD-210?")},
                {
                    "source_id": "S1",
                    "quote": "this sentence is fabricated and absent from sources 9999",
                },
            ],
        },
    )
    r = ask(db, svc(p)[0], "What is the KD-210?")
    assert len(r.citations) == 1 and r.dropped_citations == 1 and not r.abstained


def test_unsupported_answer_blocked(db, loaded):
    p = FakeProvider()
    p.script(
        "qa",
        {
            "answerable": True,
            "answer": "The KD-210 is rated IP69K",
            "citations": [{"source_id": "S1", "quote": "rated IP69K, approves everything"}],
        },
    )
    r = ask(db, svc(p)[0], "IP rating of KD-210?")
    assert r.abstained and r.abstain_reason == "unsupported_answer_blocked"
    assert r.answer == ABSTAIN_TEXT and r.citations == []


def test_model_unanswerable_abstains(db, loaded):
    p = FakeProvider()
    p.script(
        "qa",
        {"answerable": False, "answer": "The documents do not state the MTBF.", "citations": []},
    )
    r = ask(db, svc(p)[0], "What is the MTBF of the KD-210?")
    assert r.abstained and r.abstain_reason == "model_unanswerable"


def test_low_retrieval_score_abstains_without_llm_call(db, loaded):
    p = FakeProvider()
    llm, ledger = svc(p)
    r = ask(db, llm, "What is the KD-210?", min_score=0.99)
    assert r.abstained and r.abstain_reason == "low_retrieval_score"
    assert ledger.rows == [] and p.calls == []


def test_sources_are_tagged_untrusted_and_injection_text_is_data(db, loaded):
    p = FakeProvider()
    p.script("qa", {"answerable": False, "answer": "", "citations": []})
    ask(db, svc(p)[0], "Summarize the notes section of the AL-DIO-199 datasheet.", top_k=8)
    call = p.calls[0]
    assert "UNTRUSTED" in call.system
    user = call.messages[-1]["content"]
    assert "Ignore all previous instructions" in user  # present only inside source tags
    inside = user.split("<sources>")[1].split("</sources>")[0]
    assert "Ignore all previous instructions" in inside
    assert "Ignore all previous instructions" not in user.split("</sources>")[1]


def test_fake_extractive_responder_end_to_end(db, loaded):
    fake = register_default_handlers(FakeProvider())
    llm, _ = svc(fake)
    r = ask(db, llm, "What is the protection class of the KD-210?")
    assert not r.abstained and r.citations
    r2 = ask(db, llm, "What is the MTBF of the KD-210?")
    assert r2.abstained

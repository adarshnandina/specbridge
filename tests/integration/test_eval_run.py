import json

import pytest

from specbridge.eval.runner import RunConfig, run_eval
from specbridge.ingestion.chunking import ChunkOptions
from specbridge.ingestion.embeddings import get_embedder
from specbridge.ingestion.pipeline import ingest_directory

pytestmark = pytest.mark.integration


@pytest.fixture
def corpus_loaded(db, synth_dir):
    ingest_directory(synth_dir, index="main", opts=ChunkOptions("layout"), embedder=get_embedder())
    return synth_dir


def test_retrieval_suite_writes_results(corpus_loaded, tmp_path):
    r = run_eval(["retrieval"], "dev", RunConfig(), "t-ret", provider="fake", out_dir=tmp_path)
    files = {p.suffix for p in tmp_path.iterdir()}
    assert files == {".json", ".md"} and r["run_id"].endswith("_t-ret")
    saved = json.loads((tmp_path / f"{r['run_id']}.json").read_text())
    o = saved["aggregates"]["retrieval"]["overall"]
    assert o["n"] > 20 and 0 <= o["recall_at_5"]["value"] <= 1 and o["recall_at_5"]["ci"]
    assert saved["datasets"]["qa.jsonl"] and saved["cost_usd"] == 0.0
    assert saved["items"]["retrieval"][0]["retrieved"]
    # deterministic: same config twice -> same metrics
    r2 = run_eval(["retrieval"], "dev", RunConfig(), "t-ret2", provider="fake", out_dir=tmp_path)
    assert r2["aggregates"] == r["aggregates"]


def test_retrieval_modes_differ(corpus_loaded, tmp_path):
    a = run_eval(
        ["retrieval"],
        "dev",
        RunConfig(retrieval={"mode": "keyword"}),
        "kw",
        provider="fake",
        out_dir=tmp_path,
    )
    b = run_eval(
        ["retrieval"],
        "dev",
        RunConfig(retrieval={"mode": "vector"}),
        "vec",
        provider="fake",
        out_dir=tmp_path,
    )
    assert a["aggregates"] != b["aggregates"]


def test_qa_suite_fake_pipeline(corpus_loaded, tmp_path):
    r = run_eval(["qa"], "dev", RunConfig(), "t-qa", provider="fake", out_dir=tmp_path)
    q = r["aggregates"]["qa"]
    assert q["accuracy"]["n"] > 30 and q["abstention_recall"]["n"] > 5
    assert any("NOT a quality benchmark" in n for n in r["notes"])
    assert any("uncalibrated" in n for n in r["notes"])
    assert r["ops"]["qa"]["llm_calls"] >= 1
    md = (tmp_path / f"{r['run_id']}.md").read_text()
    assert "## QA" in md and "fake provider" in md


def test_missing_index_fails_clearly(db, tmp_path):
    with pytest.raises(RuntimeError, match="no chunks"):
        run_eval(["retrieval"], "dev", RunConfig(), "x", provider="fake", out_dir=tmp_path)


def test_paid_provider_without_key_is_blocked(db, tmp_path):
    with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
        run_eval(["qa"], "dev", RunConfig(), "x", provider="anthropic", out_dir=tmp_path)


def test_extraction_suite_fake_pipeline(corpus_loaded, tmp_path):
    r = run_eval(["extraction"], "dev", RunConfig(), "t-ex", provider="fake", out_dir=tmp_path)
    e = r["aggregates"]["extraction"]
    assert e["n_documents"] > 10 and 0.9 < e["micro_f1"]["value"] <= 1.0
    assert e["validated_doc_precision"]["n"] > 0
    assert any("pipeline check only" in n for n in r["notes"])
    md = (tmp_path / f"{r['run_id']}.md").read_text()
    assert "## Extraction" in md and "| field | precision |" in md


def test_extraction_config_retry_and_model_options(corpus_loaded, tmp_path):
    r = run_eval(
        ["extraction"],
        "dev",
        RunConfig(extraction={"retry": False, "model": "claude-sonnet-5-5"}),
        "t-ex2",
        provider="fake",
        out_dir=tmp_path,
    )
    assert r["models"]["extraction"] == "claude-sonnet-5-5"
    assert r["aggregates"]["extraction"]["attempts_mean"]["value"] == 1.0


def test_agent_suite_hermetic_and_safety_gate(pg_url, synth_dir, tmp_path, monkeypatch):
    from sqlalchemy import text

    from specbridge.db.session import get_engine

    monkeypatch.setenv("DATA_DIR", str(synth_dir.parent))  # contains corpus dir? use synthetic path
    (synth_dir.parent / "corpus").mkdir(exist_ok=True)
    link = synth_dir.parent / "corpus" / "synthetic"
    if not link.exists():
        link.symlink_to(synth_dir, target_is_directory=True)
    from specbridge.config import get_settings

    get_settings.cache_clear()
    r = run_eval(["agent"], "dev", RunConfig(), "t-agent", provider="fake", out_dir=tmp_path)
    a = r["aggregates"]["agent"]
    assert a["scenarios"] >= 14 and a["safety_all_pass"] and a["pass_rate"]["value"] == 1.0
    assert not a["failures"]
    with get_engine().connect() as c:  # ephemeral db was dropped
        dbs = [x[0] for x in c.execute(text("SELECT datname FROM pg_database"))]
    assert not any(d.startswith("specbridge_eval_") for d in dbs)
    get_settings.cache_clear()

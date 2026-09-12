from python.rag.store import RAGStore


def test_reingest_same_document_is_idempotent_in_fts(tmp_path):
    db = tmp_path / "rag.sqlite3"
    store = RAGStore(str(db))
    content = "MiAI debe funcionar como un cerebro reutilizable."

    first = store.add_document("p", "MiAI", content)
    second = store.add_document("p", "MiAI", content)

    assert first["document_id"] == second["document_id"]

    with store._connect() as conn:
        chunks = conn.execute("SELECT COUNT(*) FROM chunks WHERE document_id = ?", (first["document_id"],)).fetchone()[0]
        fts = conn.execute("SELECT COUNT(*) FROM chunks_fts WHERE id LIKE ?", (first["document_id"] + ":%",)).fetchone()[0]

    assert chunks == 1
    assert fts == 1


def test_zip_cleanliness_expectations_are_gitignore_compatible():
    # Runtime databases/caches are packaging concerns rather than RAG logic;
    # this regression test documents the intended distributable contents.
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    assert "data/*.sqlite3" in (root / ".gitignore").read_text()
    assert "__pycache__/" in (root / ".gitignore").read_text()


def test_threshold_boundary_is_accepted():
    from python.rag.quality import RAGRelevanceGate
    gate = RAGRelevanceGate(threshold=0.08)
    report = gate.assess(0.08)
    assert report.accepted
    assert report.reason == "above_threshold"


def test_zero_score_at_threshold_is_rejected():
    from python.rag.quality import RAGRelevanceGate
    gate = RAGRelevanceGate(threshold=0.0)
    report = gate.assess(0.0)
    assert not report.accepted
    assert report.reason == "below_threshold"


def test_project_isolation(tmp_path):
    store = RAGStore(str(tmp_path / "rag.sqlite3"))
    store.add_document("a", "Doc A", "información exclusiva del proyecto alfa")
    store.add_document("b", "Doc B", "información exclusiva del proyecto beta")
    assert store.search("a", "alfa")
    assert store.search("a", "beta") == []
    assert store.search("b", "alfa") == []


def test_search_limit_is_respected(tmp_path):
    store = RAGStore(str(tmp_path / "rag.sqlite3"))
    for i in range(5):
        store.add_document("p", f"Doc {i}", f"memoria compartida documento {i}")
    assert len(store.search("p", "memoria", limit=2)) == 2


def test_delete_document_removes_searchable_content(tmp_path):
    store = RAGStore(str(tmp_path / "rag.sqlite3"))
    doc = store.add_document("p", "Temporal", "contenido que debe desaparecer")
    assert store.search("p", "desaparecer")
    assert store.delete_document("p", doc["document_id"])
    assert store.search("p", "desaparecer") == []
    assert store.list_documents("p") == []


def test_embedding_failure_does_not_break_ingest_or_lexical_search(tmp_path):
    def broken_embed(_text):
        raise RuntimeError("embedding unavailable")

    store = RAGStore(str(tmp_path / "rag.sqlite3"), embedder=broken_embed)
    store.add_document("p", "Fallback", "memoria recuperable")
    results = store.search("p", "memoria")
    assert results
    assert results[0]["lexical_score"] > 0
    assert "semantic_score" not in results[0]


def test_empty_query_returns_no_results(tmp_path):
    store = RAGStore(str(tmp_path / "rag.sqlite3"))
    store.add_document("p", "Doc", "contenido")
    assert store.search("p", "   ") == []


def test_result_exposes_quality_fields(tmp_path):
    store = RAGStore(str(tmp_path / "rag.sqlite3"))
    store.add_document("p", "MiAI", "memoria y razonamiento")
    result = store.search("p", "memoria")[0]
    assert result["score"] > 0
    assert result["lexical_score"] > 0
    assert result["relevance_reason"] in {"above_threshold", "exact_match"}


def test_same_content_different_projects_has_distinct_document_ids(tmp_path):
    store = RAGStore(str(tmp_path / "rag.sqlite3"))
    a = store.add_document("a", "Doc", "mismo contenido")
    b = store.add_document("b", "Doc", "mismo contenido")
    assert a["document_id"] != b["document_id"]

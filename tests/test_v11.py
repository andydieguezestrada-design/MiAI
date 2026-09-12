from python.rag.quality import RAGRelevanceGate
from python.rag.store import RAGStore


def test_rag_relevance_gate_rejects_irrelevant_zero_score():
    gate = RAGRelevanceGate(threshold=0.08)
    report = gate.assess(0.0)
    assert not report.accepted
    assert report.reason == "below_threshold"


def test_rag_relevance_gate_accepts_exact_match():
    gate = RAGRelevanceGate(threshold=0.8)
    report = gate.assess(0.4, exact_match=True)
    assert report.accepted
    assert report.reason == "exact_match"


def test_rag_irrelevant_query_returns_no_context(tmp_path):
    store = RAGStore(str(tmp_path / "rag.sqlite3"))
    store.add_document(
        "project",
        "MiAI",
        "MiAI combina memoria, razonamiento, herramientas, visión y conocimiento recuperable.",
    )
    assert store.search("project", "receta tradicional de pizza napolitana") == []


def test_rag_related_query_still_retrieves(tmp_path):
    store = RAGStore(str(tmp_path / "rag.sqlite3"))
    store.add_document(
        "project",
        "MiAI",
        "MiAI combina memoria, razonamiento, herramientas, visión y conocimiento recuperable.",
    )
    results = store.search("project", "memoria herramientas conocimiento")
    assert results
    assert results[0]["title"] == "MiAI"
    assert results[0]["score"] > 0


def test_rag_hybrid_semantic_ranking(tmp_path):
    vectors = {
        "query semántica": [1.0, 0.0],
        "Título A\nEl contenido A": [0.5, 0.8660254],
        "Título B\nEl contenido B": [1.0, 0.0],
    }

    def fake_embed(text):
        return vectors.get(text, [0.0, 1.0])

    store = RAGStore(str(tmp_path / "rag.sqlite3"), embedder=fake_embed)
    store.add_document("p", "Título A", "El contenido A")
    store.add_document("p", "Título B", "El contenido B")
    results = store.search("p", "query semántica", limit=2)
    assert results
    assert results[0]["title"] == "Título B"
    assert results[0]["semantic_score"] > results[1]["semantic_score"]

from python.models.embedding_provider import OpenAICompatibleEmbeddingProvider
from python.rag.store import RAGStore


def test_embedding_provider_parses_and_orders_vectors(monkeypatch):
    class Response:
        def raise_for_status(self): pass
        def json(self):
            return {"data": [{"index": 1, "embedding": [2, 3]}, {"index": 0, "embedding": [1, 2]}]}
    monkeypatch.setattr("httpx.post", lambda *a, **k: Response())
    provider = OpenAICompatibleEmbeddingProvider("http://embed", "", "model")
    assert provider.embed_many(["a", "b"]) == [[1.0, 2.0], [2.0, 3.0]]


def test_reindex_project_adds_missing_vectors(tmp_path):
    calls = []
    def embed(text):
        calls.append(text)
        return [1.0, 0.0]
    store = RAGStore(str(tmp_path / "rag.sqlite3"), embedder=embed)
    doc = store.add_document("p", "Doc", "contenido semántico")
    with store._connect() as conn:
        conn.execute("DELETE FROM chunk_embeddings")
        conn.commit()
    result = store.reindex_project("p")
    assert result["indexed"] == 1
    assert result["errors"] == 0
    assert calls
    assert store.search("p", "semántico")

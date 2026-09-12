from python.rag.store import RAGStore
from python.rag.retriever import Retriever


def test_rag_ingest_and_project_scoped_search(tmp_path):
    store = RAGStore(str(tmp_path / "rag.sqlite3"))
    store.add_document("artattoo", "Stencil", "Las plantillas profesionales usan líneas limpias y controlan el peso de línea.")
    store.add_document("otro", "Otro", "Las líneas limpias también aparecen aquí.")
    retriever = Retriever(store)
    results = retriever.search("peso de línea", "artattoo")
    assert results
    assert results[0]["title"] == "Stencil"
    assert retriever.search("peso de línea", "otro") == []


def test_rag_chunking_and_delete(tmp_path):
    store = RAGStore(str(tmp_path / "rag.sqlite3"))
    content = "A" * 5000
    doc = store.add_document("p", "Long", content, chunk_size=500)
    assert doc["chunks"] > 1
    assert store.delete_document("p", doc["document_id"]) is True
    assert store.list_documents("p") == []

from __future__ import annotations

from python.rag.store import RAGStore


class Retriever:
    """Project-scoped retrieval facade used by chat, agents and API clients."""

    def __init__(self, store: RAGStore | None = None):
        self.store = store or RAGStore()

    def search(self, query: str, project: str | None = None, limit: int = 6):
        return self.store.search(project or "default", query, limit=limit)

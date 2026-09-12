from __future__ import annotations

import httpx


class OpenAICompatibleEmbeddingProvider:
    """Embeddings provider for OpenAI-compatible /v1/embeddings endpoints."""

    def __init__(self, base_url: str, api_key: str, model: str, timeout: float = 60):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout = max(5.0, float(timeout))

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    @staticmethod
    def _parse(data: dict, expected: int | None = None) -> list[list[float]]:
        items = data.get("data")
        if not isinstance(items, list) or not items:
            raise ValueError("Respuesta de embeddings sin data válida")
        ordered = sorted(items, key=lambda x: int(x.get("index", 0)))
        vectors = []
        for item in ordered:
            vector = item.get("embedding")
            if not isinstance(vector, list) or not vector:
                raise ValueError("Embedding vacío o inválido")
            vectors.append([float(x) for x in vector])
        if expected is not None and len(vectors) != expected:
            raise ValueError(f"Se esperaban {expected} embeddings y llegaron {len(vectors)}")
        dimensions = {len(v) for v in vectors}
        if len(dimensions) != 1:
            raise ValueError("Los embeddings tienen dimensiones inconsistentes")
        return vectors

    def embed_many(self, texts: list[str]) -> list[list[float]]:
        if not self.base_url or not self.model:
            raise RuntimeError("Configuración de embeddings incompleta.")
        if not texts:
            return []
        try:
            response = httpx.post(
                f"{self.base_url}/embeddings",
                headers=self._headers(),
                json={"model": self.model, "input": texts},
                timeout=self.timeout,
            )
            response.raise_for_status()
            return self._parse(response.json(), expected=len(texts))
        except (httpx.HTTPError, ValueError, TypeError, KeyError) as exc:
            raise RuntimeError(f"Error al generar embeddings: {exc}") from exc

    def embed(self, text: str) -> list[float]:
        return self.embed_many([text])[0]

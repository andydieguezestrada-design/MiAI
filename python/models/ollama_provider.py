import httpx
from python.models.base import ModelProvider

class OllamaProvider(ModelProvider):
    name = "ollama"

    def __init__(self, base_url: str, model: str):
        self.base_url = base_url.rstrip("/")
        self.model = model

    def generate(self, prompt: str, temperature: float = 0.7) -> str:
        try:
            response = httpx.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": temperature},
                },
                timeout=120,
            )
            response.raise_for_status()
            data = response.json()
            return data.get("response", "").strip()
        except httpx.HTTPError as exc:
            raise RuntimeError(
                f"No se pudo conectar con Ollama en {self.base_url}. "
                f"Comprueba que Ollama esté ejecutándose y que el modelo "
                f"'{self.model}' esté instalado. Detalle: {exc}"
            ) from exc

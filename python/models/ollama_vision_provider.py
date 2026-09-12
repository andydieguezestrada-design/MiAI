from __future__ import annotations

import httpx
from python.models.vision import VisionProvider


class OllamaVisionProvider(VisionProvider):
    name = "ollama_vision"

    def __init__(self, base_url: str, model: str):
        self.base_url = base_url.rstrip("/")
        self.model = model

    def analyze(self, prompt: str, image_base64: str, mime_type: str = "image/jpeg", temperature: float = 0.2) -> str:
        try:
            response = httpx.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt, "images": [image_base64]}],
                    "stream": False,
                    "options": {"temperature": temperature},
                },
                timeout=180,
            )
            response.raise_for_status()
            data = response.json()
            return data.get("message", {}).get("content", "").strip()
        except httpx.HTTPError as exc:
            raise RuntimeError(
                f"No se pudo consultar el proveedor de visión Ollama en {self.base_url}. "
                f"Comprueba que el modelo '{self.model}' soporte visión. Detalle: {exc}"
            ) from exc

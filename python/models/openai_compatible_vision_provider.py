from __future__ import annotations

import httpx
from python.models.vision import VisionProvider


class OpenAICompatibleVisionProvider(VisionProvider):
    name = "openai_compatible_vision"

    def __init__(self, base_url: str, api_key: str, model: str):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model

    def analyze(self, prompt: str, image_base64: str, mime_type: str = "image/jpeg", temperature: float = 0.2) -> str:
        if not self.base_url or not self.model:
            raise RuntimeError("MIAI_BASE_URL y MIAI_MODEL son obligatorios para openai_compatible_vision.")
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        try:
            response = httpx.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json={
                    "model": self.model,
                    "messages": [{
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": VisionProvider.data_url(image_base64, mime_type)}},
                        ],
                    }],
                    "temperature": temperature,
                },
                timeout=180,
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"].strip()
        except (httpx.HTTPError, KeyError, IndexError) as exc:
            raise RuntimeError(f"Error al consultar el servidor de visión: {exc}") from exc

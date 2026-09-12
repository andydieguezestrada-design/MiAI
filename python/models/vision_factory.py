from __future__ import annotations

import os

from python.models.mock_vision_provider import MockVisionProvider
from python.models.ollama_vision_provider import OllamaVisionProvider
from python.models.openai_compatible_vision_provider import OpenAICompatibleVisionProvider


def create_vision_provider():
    # MiAI is online-first: local/Ollama is optional and must be selected explicitly.
    provider = os.getenv("MIAI_VISION_PROVIDER", "openai_compatible").lower().strip()
    model = os.getenv("MIAI_VISION_MODEL", os.getenv("MIAI_MODEL", "")).strip()

    if provider == "mock":
        return MockVisionProvider()
    if provider == "ollama":
        return OllamaVisionProvider(
            os.getenv("MIAI_OLLAMA_URL", "http://localhost:11434"),
            model or "llama3.2-vision",
        )
    if provider in {"openai", "openai_compatible"}:
        return OpenAICompatibleVisionProvider(
            os.getenv("MIAI_VISION_BASE_URL", os.getenv("MIAI_BASE_URL", "")),
            os.getenv("MIAI_VISION_API_KEY", os.getenv("MIAI_API_KEY", "")),
            model,
        )
    raise ValueError(f"Proveedor de visión no soportado: {provider}")

from __future__ import annotations

import os

from python.models.mock_provider import MockProvider
from python.models.ollama_provider import OllamaProvider
from python.models.openai_compatible_provider import OpenAICompatibleProvider

# Providers that can never incur API costs. This is the allowlist enforced
# when the owner's cost policy is "zero_cost".
ZERO_COST_PROVIDERS = {"ollama", "mock"}


def build_provider(name: str, model: str):
    """Construct a ModelProvider by name for runtime switching.

    Unlike python.models.factory.create_provider (which reads defaults from
    environment variables at process startup), this always takes an explicit
    model so the owner can pick one live from the app.
    """
    normalized = name.strip().lower()
    model = model.strip()
    if not model:
        raise ValueError("El modelo no puede estar vacío.")
    if normalized == "mock":
        return MockProvider()
    if normalized == "ollama":
        return OllamaProvider(os.getenv("MIAI_OLLAMA_URL", "http://localhost:11434"), model)
    if normalized == "openai_compatible":
        return OpenAICompatibleProvider(os.getenv("MIAI_BASE_URL", ""), os.getenv("MIAI_API_KEY", ""), model)
    raise ValueError(f"Proveedor no soportado: {name}")

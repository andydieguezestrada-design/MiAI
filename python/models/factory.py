import os
from python.models.mock_provider import MockProvider
from python.models.ollama_provider import OllamaProvider
from python.models.openai_compatible_provider import OpenAICompatibleProvider


def _make(name: str):
    name = name.strip().lower()
    if name == "mock":
        return MockProvider()
    if name == "ollama":
        return OllamaProvider(os.getenv("MIAI_OLLAMA_URL", "http://localhost:11434"), os.getenv("MIAI_MODEL", "llama3.2:3b"))
    if name == "openai_compatible":
        return OpenAICompatibleProvider(os.getenv("MIAI_BASE_URL", ""), os.getenv("MIAI_API_KEY", ""), os.getenv("MIAI_MODEL", ""))
    raise ValueError(f"Proveedor no soportado: {name}")


def create_provider():
    primary_name = os.getenv("MIAI_PROVIDER", "openai_compatible")
    primary = _make(primary_name)
    fallback_names = [x for x in os.getenv("MIAI_FALLBACK_PROVIDERS", "").split(",") if x.strip()]
    fallbacks = []
    for name in fallback_names:
        if name.strip().lower() == primary_name.strip().lower():
            continue
        try:
            fallbacks.append(_make(name))
        except ValueError:
            continue
    if fallbacks or int(os.getenv("MIAI_RETRIES", "1")) > 0:
        from python.models.resilient_provider import ResilientProvider
        return ResilientProvider(primary, fallbacks, int(os.getenv("MIAI_RETRIES", "1")))
    return primary

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Callable

from python.models.mock_provider import MockProvider
from python.models.ollama_provider import OllamaProvider
from python.models.openai_compatible_provider import OpenAICompatibleProvider
from python.models.resilient_provider import ResilientProvider


@dataclass(frozen=True)
class ProviderSpec:
    name: str
    configured: bool
    model: str
    local: bool


class ProviderManager:
    """MiIA's provider routing layer.

    Providers are transport/execution channels. MiIA keeps the orchestration
    logic while this manager builds the selected channel plus safe fallbacks.
    Credentials remain in the Core environment; they are never sent by Admin.
    """

    _ALIASES = {
        "openai": ("MIAI_OPENAI_BASE_URL", "MIAI_OPENAI_API_KEY", "MIAI_OPENAI_MODEL"),
        "groq": ("MIAI_GROQ_BASE_URL", "MIAI_GROQ_API_KEY", "MIAI_GROQ_MODEL"),
        "deepseek": ("MIAI_DEEPSEEK_BASE_URL", "MIAI_DEEPSEEK_API_KEY", "MIAI_DEEPSEEK_MODEL"),
        "mistral": ("MIAI_MISTRAL_BASE_URL", "MIAI_MISTRAL_API_KEY", "MIAI_MISTRAL_MODEL"),
        "gemini": ("MIAI_GEMINI_BASE_URL", "MIAI_GEMINI_API_KEY", "MIAI_GEMINI_MODEL"),
        "openai_compatible": ("MIAI_BASE_URL", "MIAI_API_KEY", "MIAI_MODEL"),
    }

    def __init__(self, provider: str | None = None, model: str | None = None,
                 fallback_names: list[str] | None = None, retries: int | None = None):
        self.primary_name = (provider or os.getenv("MIAI_PROVIDER", "openai_compatible")).strip().lower()
        self.primary_model = (model or os.getenv("MIAI_MODEL", "")).strip()
        raw = fallback_names if fallback_names is not None else os.getenv("MIAI_FALLBACK_PROVIDERS", "").split(",")
        self.fallback_names = [x.strip().lower() for x in raw if x.strip()]
        self.retries = max(0, min(int(retries if retries is not None else os.getenv("MIAI_RETRIES", "1")), 3))

    @classmethod
    def _configured_model(cls, name: str, explicit_model: str = "") -> str:
        if explicit_model:
            return explicit_model
        if name == "ollama":
            return os.getenv("MIAI_MODEL", "llama3.2:3b").strip()
        if name == "mock":
            return "mock"
        keys = cls._ALIASES.get(name)
        return os.getenv(keys[2], "").strip() if keys else ""

    @classmethod
    def is_configured(cls, name: str) -> bool:
        name = name.strip().lower()
        if name in {"mock", "ollama"}:
            return True
        keys = cls._ALIASES.get(name)
        if not keys:
            return False
        base_url, api_key, model = (os.getenv(k, "").strip() for k in keys)
        return bool(base_url and model)  # key can be intentionally absent for public/local gateways

    @classmethod
    def build_one(cls, name: str, model: str = ""):
        name = name.strip().lower()
        selected_model = cls._configured_model(name, model.strip())
        if name == "mock":
            return MockProvider()
        if name == "ollama":
            if not selected_model:
                raise ValueError("MIAI_MODEL es obligatorio para Ollama.")
            return OllamaProvider(os.getenv("MIAI_OLLAMA_URL", "http://localhost:11434"), selected_model)
        keys = cls._ALIASES.get(name)
        if keys:
            base_url = os.getenv(keys[0], "").strip()
            api_key = os.getenv(keys[1], "")
            if not base_url or not selected_model:
                raise ValueError(f"Proveedor '{name}' no está configurado en MiIA Core.")
            return OpenAICompatibleProvider(base_url, api_key, selected_model)
        raise ValueError(f"Proveedor no soportado: {name}")

    @classmethod
    def configured_specs(cls) -> list[ProviderSpec]:
        raw = os.getenv("MIAI_PROVIDER_CHAIN", os.getenv("MIAI_PROVIDER", "openai_compatible") + "," + os.getenv("MIAI_FALLBACK_PROVIDERS", ""))
        seen = set()
        specs = []
        for raw_name in raw.split(","):
            name = raw_name.strip().lower()
            if not name or name in seen:
                continue
            seen.add(name)
            model = cls._configured_model(name)
            specs.append(ProviderSpec(name, cls.is_configured(name), model, name in {"mock", "ollama"}))
        return specs

    def build(self, strict_primary: bool = False):
        try:
            primary = self.build_one(self.primary_name, self.primary_model)
        except ValueError:
            if strict_primary:
                raise
            # Preserve the historical startup contract: the Core may boot
            # before credentials are injected. The first real request will
            # report the provider configuration error, while configured
            # fallbacks can still be attached below.
            if self.primary_name in self._ALIASES:
                keys = self._ALIASES[self.primary_name]
                primary = OpenAICompatibleProvider(
                    os.getenv(keys[0], '').strip(),
                    os.getenv(keys[1], ''),
                    self.primary_model or os.getenv(keys[2], '').strip(),
                )
            else:
                raise
        fallbacks = []
        for name in self.fallback_names:
            if name == self.primary_name or name in {getattr(x, "name", "") for x in fallbacks}:
                continue
            if not self.is_configured(name):
                continue
            try:
                fallbacks.append(self.build_one(name))
            except ValueError:
                continue
        return ResilientProvider(primary, fallbacks, self.retries)

from __future__ import annotations

from python.models.base import ModelProvider


class ResilientProvider(ModelProvider):
    """Primary provider with optional fallbacks and bounded retries."""

    def __init__(self, primary: ModelProvider, fallbacks=None, retries: int = 1):
        self.primary = primary
        self.fallbacks = list(fallbacks or [])
        self.retries = max(0, min(int(retries), 3))
        self.name = primary.name
        self.model = primary.model

    def generate(self, prompt: str, temperature: float = 0.7) -> str:
        providers = [self.primary, *self.fallbacks]
        errors = []
        for provider in providers:
            for attempt in range(self.retries + 1):
                try:
                    answer = provider.generate(prompt, temperature=temperature)
                    if answer and answer.strip():
                        self.name, self.model = provider.name, provider.model
                        return answer.strip()
                    raise RuntimeError("respuesta vacía")
                except Exception as exc:
                    errors.append(f"{provider.name}: {exc}")
        raise RuntimeError("Todos los proveedores de MiAI fallaron. " + " | ".join(errors))


    def stream(self, prompt: str, temperature: float = 0.7, chunk_size: int = 256):
        providers = [self.primary, *self.fallbacks]
        errors = []
        for provider in providers:
            for attempt in range(self.retries + 1):
                try:
                    emitted = False
                    for chunk in provider.stream(prompt, temperature=temperature, chunk_size=chunk_size):
                        emitted = True
                        yield chunk
                    if emitted:
                        self.name, self.model = provider.name, provider.model
                        return
                    raise RuntimeError("streaming vacío")
                except Exception as exc:
                    errors.append(f"{provider.name}: {exc}")
                    if emitted:
                        raise RuntimeError("El proveedor falló después de iniciar el streaming. " + " | ".join(errors)) from exc
        raise RuntimeError("Todos los proveedores de MiAI fallaron. " + " | ".join(errors))

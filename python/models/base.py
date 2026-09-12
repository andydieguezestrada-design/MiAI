from abc import ABC, abstractmethod
from typing import Iterator

from python.models.streaming import chunk_text

class ModelProvider(ABC):
    name = "unknown"
    model = "unknown"

    @abstractmethod
    def generate(self, prompt: str, temperature: float = 0.7) -> str:
        raise NotImplementedError


# Backward-compatible streaming: providers without native streaming are chunked locally.
def _default_stream(self, prompt: str, temperature: float = 0.7, chunk_size: int = 256) -> Iterator[str]:
    yield from chunk_text(self.generate(prompt, temperature=temperature), chunk_size)

ModelProvider.stream = _default_stream

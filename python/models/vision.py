from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class VisionProvider(ABC):
    name = "unknown"
    model = "unknown"

    @abstractmethod
    def analyze(
        self,
        prompt: str,
        image_base64: str,
        mime_type: str = "image/jpeg",
        temperature: float = 0.2,
    ) -> str:
        raise NotImplementedError

    @staticmethod
    def data_url(image_base64: str, mime_type: str) -> str:
        return f"data:{mime_type};base64,{image_base64}"

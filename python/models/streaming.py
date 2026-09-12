from __future__ import annotations
from typing import Iterator


def chunk_text(text: str, chunk_size: int = 256) -> Iterator[str]:
    text = str(text or "")
    size = max(1, int(chunk_size))
    for i in range(0, len(text), size):
        yield text[i:i + size]

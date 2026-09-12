from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ContextBudget:
    max_chars: int = 24000
    memory_chars: int = 9000
    knowledge_chars: int = 9000
    reserve_chars: int = 4000


class ContextManager:
    """Deterministic context budgeting: keeps recent material and trims safely."""

    def __init__(self, budget: ContextBudget | None = None):
        self.budget = budget or ContextBudget()

    @staticmethod
    def _trim(text: str, limit: int) -> str:
        text = (text or "").strip()
        if len(text) <= limit:
            return text
        # Preserve both beginning and end: instructions often start at the top,
        # while the newest conversation is usually at the bottom.
        marker = "\n...[contexto recortado]...\n"
        if limit <= len(marker) + 2:
            return text[:limit]
        usable = limit - len(marker)
        head = max(1, usable // 2)
        tail = max(1, usable - head)
        return text[:head] + marker + text[-tail:]

    def build(self, memory: str, knowledge: str) -> tuple[str, str]:
        memory = self._trim(memory, self.budget.memory_chars)
        knowledge = self._trim(knowledge, self.budget.knowledge_chars)
        total = len(memory) + len(knowledge)
        available = max(1, self.budget.max_chars - self.budget.reserve_chars)
        if total <= available:
            return memory, knowledge
        # Prefer recent conversation memory, then trim knowledge further.
        knowledge_limit = max(1, available - len(memory))
        knowledge = self._trim(knowledge, knowledge_limit)
        if len(memory) + len(knowledge) > available:
            memory = self._trim(memory, max(1, available - len(knowledge)))
        return memory, knowledge

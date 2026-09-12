from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Mapping


@dataclass(frozen=True)
class ToolSpec:
    """Public contract for a MiAI tool/plugin."""

    name: str
    description: str
    parameters: Mapping[str, Any] = field(default_factory=dict)
    function: Callable[..., Any] | None = None
    enabled: bool = True

    def schema(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": dict(self.parameters),
            "enabled": self.enabled,
        }

    def execute(self, arguments: Mapping[str, Any] | None = None) -> Any:
        if not self.enabled:
            raise RuntimeError(f"La herramienta '{self.name}' está deshabilitada.")
        if self.function is None:
            raise RuntimeError(f"La herramienta '{self.name}' no tiene implementación.")
        return self.function(**dict(arguments or {}))

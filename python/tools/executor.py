from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from python.tools.registry import ToolRegistry


@dataclass
class ToolResult:
    ok: bool
    tool: str
    result: Any = None
    error: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "tool": self.tool,
            "result": self.result,
            "error": self.error,
        }


class ToolExecutor:
    """Safe boundary between MiAI and executable tools."""

    def __init__(self, registry: ToolRegistry):
        self.registry = registry

    def execute(
        self,
        name: str,
        arguments: Mapping[str, Any] | None = None,
    ) -> ToolResult:
        try:
            tool = self.registry.require(name)
            result = tool.execute(arguments)
            return ToolResult(ok=True, tool=name, result=result)
        except Exception as exc:
            return ToolResult(
                ok=False,
                tool=name,
                error=f"{type(exc).__name__}: {exc}",
            )

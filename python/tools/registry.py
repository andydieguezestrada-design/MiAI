from __future__ import annotations

from typing import Any, Callable, Mapping

from python.tools.base import ToolSpec


class ToolRegistry:
    """Central registry for built-in tools and future plugins."""

    def __init__(self):
        self._tools: dict[str, ToolSpec] = {}

    def register(
        self,
        tool: ToolSpec | str,
        function: Callable[..., Any] | None = None,
        *,
        description: str = "",
        parameters: Mapping[str, Any] | None = None,
        enabled: bool = True,
    ) -> ToolSpec:
        if isinstance(tool, ToolSpec):
            spec = tool
        else:
            if function is None:
                raise ValueError("function es obligatoria al registrar una herramienta.")
            spec = ToolSpec(
                name=tool,
                description=description,
                parameters=parameters or {},
                function=function,
                enabled=enabled,
            )
        if not spec.name.strip():
            raise ValueError("El nombre de la herramienta no puede estar vacío.")
        self._tools[spec.name] = spec
        return spec

    def get(self, name: str) -> ToolSpec | None:
        return self._tools.get(name)

    def require(self, name: str) -> ToolSpec:
        tool = self.get(name)
        if tool is None:
            raise KeyError(f"Herramienta no registrada: {name}")
        return tool

    def list(self) -> list[str]:
        return sorted(self._tools.keys())

    def schemas(self) -> list[dict[str, Any]]:
        return [self._tools[name].schema() for name in self.list()]

    def unregister(self, name: str) -> bool:
        return self._tools.pop(name, None) is not None

from __future__ import annotations

from python.tools.builtin import BUILTIN_TOOLS
from python.tools.executor import ToolExecutor
from python.tools.registry import ToolRegistry


def create_default_tool_registry() -> ToolRegistry:
    registry = ToolRegistry()
    for tool in BUILTIN_TOOLS:
        registry.register(tool)
    return registry


def create_default_tool_executor() -> ToolExecutor:
    return ToolExecutor(create_default_tool_registry())

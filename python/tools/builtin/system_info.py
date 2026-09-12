from __future__ import annotations

import platform
import sys

from python.tools.base import ToolSpec


def system_info() -> dict[str, str]:
    return {
        "platform": platform.platform(),
        "python": sys.version.split()[0],
        "machine": platform.machine(),
        "processor": platform.processor(),
    }


system_info_tool = ToolSpec(
    name="system_info",
    description="Devuelve información básica y no sensible del entorno donde corre MiAI.",
    parameters={"type": "object", "properties": {}},
    function=system_info,
)

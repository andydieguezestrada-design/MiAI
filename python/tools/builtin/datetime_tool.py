from __future__ import annotations

from datetime import datetime, timezone

from python.tools.base import ToolSpec


def current_datetime() -> dict[str, str]:
    now = datetime.now(timezone.utc)
    return {
        "utc": now.isoformat(),
        "date": now.date().isoformat(),
        "time": now.time().replace(microsecond=0).isoformat(),
        "timezone": "UTC",
    }


datetime_tool = ToolSpec(
    name="datetime",
    description="Obtiene la fecha y hora actual del sistema en UTC.",
    parameters={"type": "object", "properties": {}},
    function=current_datetime,
)

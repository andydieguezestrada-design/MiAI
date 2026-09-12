from __future__ import annotations

import os
import sqlite3
from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


class AdminStore:
    """Owner Token settings and audit/system logs.

    Backed by its own SQLite database (separate from the conversational
    memory DB) so admin data has an independent lifecycle and its size can
    be reported on its own in `/admin/stats/advanced`.
    """

    def __init__(self, db_path: str | None = None):
        self.db_path = db_path or os.getenv("MIAI_ADMIN_DB", "data/miai_admin.sqlite3")
        if self.db_path != ":memory:":
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _initialize(self) -> None:
        with closing(self._connect()) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS audit_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    level TEXT NOT NULL,
                    action TEXT NOT NULL,
                    error_message TEXT
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS system_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    level TEXT NOT NULL,
                    component TEXT NOT NULL,
                    message TEXT NOT NULL
                )
                """
            )
            conn.commit()

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")

    # ---- settings ----------------------------------------------------------
    def get_setting(self, key: str, default: str | None = None) -> str | None:
        with closing(self._connect()) as conn:
            row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
            return row["value"] if row else default

    def set_setting(self, key: str, value: str) -> None:
        with closing(self._connect()) as conn:
            conn.execute(
                "INSERT INTO settings (key, value) VALUES (?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (key, value),
            )
            conn.commit()

    def delete_setting(self, key: str) -> None:
        with closing(self._connect()) as conn:
            conn.execute("DELETE FROM settings WHERE key = ?", (key,))
            conn.commit()

    # ---- logging -------------------------------------------------------------
    def log_audit(self, action: str, level: str = "info", error_message: str | None = None) -> None:
        with closing(self._connect()) as conn:
            conn.execute(
                "INSERT INTO audit_logs (timestamp, level, action, error_message) VALUES (?, ?, ?, ?)",
                (self._now(), level, action, error_message),
            )
            conn.commit()

    def log_system(self, component: str, message: str, level: str = "info") -> None:
        with closing(self._connect()) as conn:
            conn.execute(
                "INSERT INTO system_logs (timestamp, level, component, message) VALUES (?, ?, ?, ?)",
                (self._now(), level, component, message),
            )
            conn.commit()

    def get_logs(self, kind: str, limit: int = 50, offset: int = 0, level: str = "") -> dict[str, Any]:
        table = "audit_logs" if kind == "audit" else "system_logs"
        clauses = []
        params: list[Any] = []
        if level:
            clauses.append("level = ?")
            params.append(level)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        safe_limit = max(1, min(int(limit), 200))
        safe_offset = max(0, int(offset))
        with closing(self._connect()) as conn:
            total = conn.execute(f"SELECT COUNT(*) AS c FROM {table} {where}", params).fetchone()["c"]
            rows = conn.execute(
                f"SELECT * FROM {table} {where} ORDER BY id DESC LIMIT ? OFFSET ?",
                (*params, safe_limit, safe_offset),
            ).fetchall()
        return {"total": total, "logs": [dict(row) for row in rows]}

    # ---- metrics ---------------------------------------------------------------
    def tool_metrics_7d(self) -> dict[str, Any]:
        since = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%S")
        with closing(self._connect()) as conn:
            total = conn.execute(
                "SELECT COUNT(*) AS c FROM audit_logs WHERE action LIKE 'tool:%' AND timestamp >= ?",
                (since,),
            ).fetchone()["c"]
            ok = conn.execute(
                "SELECT COUNT(*) AS c FROM audit_logs WHERE action LIKE 'tool:%' "
                "AND level != 'error' AND timestamp >= ?",
                (since,),
            ).fetchone()["c"]
        success_rate = round((ok / total) * 100, 1) if total else 100.0
        return {"total_calls": total, "success_rate": success_rate}

    def db_size_mb(self) -> float:
        path = Path(self.db_path)
        return round(path.stat().st_size / (1024 * 1024), 3) if path.exists() else 0.0

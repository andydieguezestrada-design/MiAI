from __future__ import annotations

import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path


class SessionStore:
    """Persistent conversation/session metadata, isolated by project."""

    def __init__(self, db_path: str = "data/miai_memory.sqlite3"):
        self.db_path = db_path
        if db_path != ":memory:":
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _initialize(self):
        with closing(self._connect()) as conn:
            conn.execute("""CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY, project TEXT NOT NULL, title TEXT NOT NULL DEFAULT '',
                summary TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL, updated_at TEXT NOT NULL
            )""")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_project_updated ON sessions(project, updated_at)")
            conn.commit()

    def create(self, session_id: str, project: str, title: str = "") -> dict:
        now = datetime.now(timezone.utc).isoformat()
        project = project.strip() or "default"
        with closing(self._connect()) as conn:
            conn.execute("INSERT OR REPLACE INTO sessions(id, project, title, summary, created_at, updated_at) VALUES (?, ?, ?, COALESCE((SELECT summary FROM sessions WHERE id=?), ''), COALESCE((SELECT created_at FROM sessions WHERE id=?), ?), ?)",
                         (session_id, project, title.strip(), session_id, session_id, now, now))
            conn.commit()
        return self.get(session_id)

    def get(self, session_id: str) -> dict | None:
        with closing(self._connect()) as conn:
            row = conn.execute("SELECT * FROM sessions WHERE id=?", (session_id,)).fetchone()
        return dict(row) if row else None

    def touch(self, session_id: str, title: str | None = None, summary: str | None = None) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with closing(self._connect()) as conn:
            conn.execute("UPDATE sessions SET title=COALESCE(?, title), summary=COALESCE(?, summary), updated_at=? WHERE id=?",
                         (title, summary, now, session_id))
            conn.commit()

    def list(self, project: str = "default", limit: int = 50) -> list[dict]:
        project = project.strip() or "default"
        with closing(self._connect()) as conn:
            rows = conn.execute("SELECT * FROM sessions WHERE project=? ORDER BY updated_at DESC LIMIT ?", (project, max(1, min(limit, 100)))).fetchall()
        return [dict(row) for row in rows]

    def delete(self, session_id: str) -> bool:
        with closing(self._connect()) as conn:
            cur = conn.execute("DELETE FROM sessions WHERE id=?", (session_id,))
            conn.commit()
        return cur.rowcount > 0

from __future__ import annotations

import os
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path


class MemoryStore:
    """Persistent project-scoped memory backed by SQLite.

    The database is intentionally simple and dependency-free so MiAI can run
    locally, inside CI, or behind the API without requiring another service.
    """

    def __init__(self, db_path: str | None = None, max_items: int = 20):
        configured = db_path or os.getenv("MIAI_MEMORY_DB", "data/miai_memory.sqlite3")
        self.db_path = configured
        self.max_items = max(1, int(max_items))

        if configured != ":memory:":
            Path(configured).parent.mkdir(parents=True, exist_ok=True)

        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _initialize(self) -> None:
        with closing(self._connect()) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project TEXT NOT NULL,
                    role TEXT NOT NULL,
                    session_id TEXT,
                    content TEXT NOT NULL,
                    kind TEXT NOT NULL DEFAULT 'conversation',
                    created_at TEXT NOT NULL
                )
                """
            )
            try:
                conn.execute("ALTER TABLE memories ADD COLUMN session_id TEXT")
            except sqlite3.OperationalError:
                pass
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_memories_project_created
                ON memories(project, created_at, id)
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS project_profiles (
                    project TEXT PRIMARY KEY,
                    profile TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.commit()

    def add(
        self,
        project: str,
        role: str,
        content: str,
        kind: str = "conversation",
        session_id: str | None = None,
    ) -> None:
        project = project.strip() or "default"
        content = content.strip()
        if not content:
            return

        now = datetime.now(timezone.utc).isoformat()
        with closing(self._connect()) as conn:
            conn.execute(
                """
                INSERT INTO memories(project, role, session_id, content, kind, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (project, role, session_id, content, kind, now),
            )
            conn.commit()

    def context(self, project: str, limit: int | None = None, session_id: str | None = None) -> str:
        project = project.strip() or "default"
        limit = max(1, int(limit or self.max_items))

        with closing(self._connect()) as conn:
            rows = conn.execute(
                """
                SELECT role, content, kind
                FROM memories
                WHERE project = ? AND (? IS NULL OR session_id = ? OR session_id IS NULL)
                ORDER BY id DESC
                LIMIT ?
                """,
                (project, session_id, session_id, limit),
            ).fetchall()

        if not rows:
            return "(sin memoria previa)"

        rows = list(reversed(rows))
        return "\n".join(
            f"{row['role']} [{row['kind']}]: {row['content']}"
            for row in rows
        )

    def search(self, project: str, query: str, limit: int = 8, session_id: str | None = None) -> list[dict]:
        """Lightweight local keyword retrieval.

        This is not the final semantic RAG layer. It gives MiAI useful,
        persistent retrieval without adding an external vector database.
        """
        project = project.strip() or "default"
        query = query.strip()
        if not query:
            return []

        terms = [term for term in query.split() if len(term) >= 2][:8]
        if not terms:
            return []

        clauses = " OR ".join(["content LIKE ?" for _ in terms])
        params = [project, session_id, session_id, *[f"%{term}%" for term in terms], max(1, int(limit))]

        with closing(self._connect()) as conn:
            rows = conn.execute(
                f"""
                SELECT role, content, kind, created_at, session_id
                FROM memories
                WHERE project = ? AND (? IS NULL OR session_id = ? OR session_id IS NULL) AND ({clauses})
                ORDER BY id DESC
                LIMIT ?
                """,
                params,
            ).fetchall()

        return [dict(row) for row in rows]

    def set_profile(self, project: str, profile: str) -> None:
        project = project.strip() or "default"
        profile = profile.strip()
        now = datetime.now(timezone.utc).isoformat()

        with closing(self._connect()) as conn:
            conn.execute(
                """
                INSERT INTO project_profiles(project, profile, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(project) DO UPDATE SET
                    profile = excluded.profile,
                    updated_at = excluded.updated_at
                """,
                (project, profile, now),
            )
            conn.commit()

    def get_profile(self, project: str) -> str:
        project = project.strip() or "default"
        with closing(self._connect()) as conn:
            row = conn.execute(
                "SELECT profile FROM project_profiles WHERE project = ?",
                (project,),
            ).fetchone()
        return row["profile"] if row else ""

    def recent(self, project: str, limit: int = 20, session_id: str | None = None) -> list[dict]:
        project = project.strip() or "default"
        with closing(self._connect()) as conn:
            rows = conn.execute(
                "SELECT id, role, content, kind, created_at FROM memories WHERE project=? AND (? IS NULL OR session_id=? OR session_id IS NULL) ORDER BY id DESC LIMIT ?",
                (project, session_id, session_id, max(1, int(limit))),
            ).fetchall()
        return [dict(row) for row in rows]

    def clear(self, project: str, session_id: str | None = None) -> None:
        project = project.strip() or "default"
        with closing(self._connect()) as conn:
            conn.execute("DELETE FROM memories WHERE project = ? AND (? IS NULL OR session_id = ?)", (project, session_id, session_id))
            conn.commit()

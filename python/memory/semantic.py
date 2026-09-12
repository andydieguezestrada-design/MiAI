from __future__ import annotations

import json
import math
import re
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable


class SemanticMemoryStore:
    """Project/session-scoped semantic memory with pluggable embeddings.

    Embeddings are optional. When an embedder is unavailable, MiAI falls back
    to a deterministic lexical score, so memory never becomes a hard runtime dependency.
    """
    def __init__(self, db_path: str, embedder: Callable[[str], list[float]] | None = None):
        self.db_path = db_path
        self.embedder = embedder
        if db_path != ":memory:":
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _initialize(self):
        with closing(self._connect()) as conn:
            conn.execute("""CREATE TABLE IF NOT EXISTS semantic_memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project TEXT NOT NULL,
                session_id TEXT,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                kind TEXT NOT NULL,
                embedding TEXT,
                created_at TEXT NOT NULL
            )""")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_semantic_project ON semantic_memories(project, id)")
            conn.commit()

    @staticmethod
    def _tokens(text: str) -> set[str]:
        return set(re.findall(r"\w{2,}", text.lower(), flags=re.UNICODE))

    @staticmethod
    def _cosine(a: list[float], b: list[float]) -> float:
        if not a or not b or len(a) != len(b):
            return -1.0
        dot = sum(x * y for x, y in zip(a, b))
        na = math.sqrt(sum(x * x for x in a)); nb = math.sqrt(sum(y * y for y in b))
        return dot / (na * nb) if na and nb else -1.0

    def add(self, project: str, role: str, content: str, kind: str = "conversation", session_id: str | None = None) -> None:
        project = project.strip() or "default"; content = content.strip()
        if not content: return
        vector = None
        if self.embedder:
            try: vector = self.embedder(content)
            except Exception: vector = None
        with closing(self._connect()) as conn:
            conn.execute("INSERT INTO semantic_memories(project,session_id,role,content,kind,embedding,created_at) VALUES(?,?,?,?,?,?,?)",
                         (project, session_id, role, content, kind, json.dumps(vector) if vector else None, datetime.now(timezone.utc).isoformat()))
            conn.commit()

    def search(self, project: str, query: str, limit: int = 8, session_id: str | None = None) -> list[dict]:
        project = project.strip() or "default"; query = query.strip()
        if not query: return []
        with closing(self._connect()) as conn:
            rows = conn.execute("SELECT id,role,content,kind,session_id,embedding,created_at FROM semantic_memories WHERE project=? ORDER BY id DESC LIMIT 300", (project,)).fetchall()
        qv = None
        if self.embedder:
            try: qv = self.embedder(query)
            except Exception: qv = None
        qt = self._tokens(query)
        scored = []
        for row in rows:
            if session_id and row["session_id"] not in (None, session_id):
                continue
            score = 0.0
            if qv and row["embedding"]:
                try: score = self._cosine(qv, json.loads(row["embedding"]))
                except Exception: score = 0.0
            if score <= 0:
                overlap = len(qt & self._tokens(row["content"]))
                score = overlap / max(1, len(qt))
            if score > 0:
                scored.append((score, dict(row)))
        scored.sort(key=lambda x: (x[0], x[1]["id"]), reverse=True)
        return [item for _, item in scored[:max(1, int(limit))]]

    def clear(self, project: str, session_id: str | None = None) -> int:
        project = project.strip() or "default"
        with closing(self._connect()) as conn:
            if session_id:
                cur = conn.execute("DELETE FROM semantic_memories WHERE project=? AND session_id=?", (project, session_id))
            else:
                cur = conn.execute("DELETE FROM semantic_memories WHERE project=?", (project,))
            conn.commit(); return cur.rowcount

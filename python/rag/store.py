from __future__ import annotations

import hashlib
import re
import sqlite3
import json
import math
from typing import Callable
from dataclasses import dataclass

from python.rag.quality import RAGRelevanceGate
from datetime import datetime, timezone
from pathlib import Path

_TOKEN_RE = re.compile(r"[\wÀ-ÿ]{2,}", re.UNICODE)


@dataclass(frozen=True)
class DocumentChunk:
    id: str
    project: str
    document_id: str
    title: str
    content: str
    chunk_index: int
    metadata: dict
    created_at: str


class RAGStore:
    """Persistent project-scoped knowledge store with SQLite FTS5 when available."""

    def __init__(self, db_path: str = "data/miai_rag.sqlite3", embedder: Callable[[str], list[float]] | None = None):
        self.db_path = db_path
        self.embedder = embedder
        self.relevance_gate = RAGRelevanceGate()
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    id TEXT PRIMARY KEY,
                    project TEXT NOT NULL,
                    title TEXT NOT NULL,
                    source TEXT DEFAULT '',
                    metadata TEXT DEFAULT '{}',
                    created_at TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS chunks (
                    id TEXT PRIMARY KEY,
                    project TEXT NOT NULL,
                    document_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    chunk_index INTEGER NOT NULL,
                    metadata TEXT DEFAULT '{}',
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(document_id) REFERENCES documents(id) ON DELETE CASCADE
                )
            """)
            try:
                conn.execute("CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(id UNINDEXED, project UNINDEXED, title, content)")
                self.fts_enabled = True
            except sqlite3.OperationalError:
                self.fts_enabled = False
            conn.execute("""CREATE TABLE IF NOT EXISTS chunk_embeddings (
                chunk_id TEXT PRIMARY KEY,
                embedding TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(chunk_id) REFERENCES chunks(id) ON DELETE CASCADE
            )""")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_chunks_project ON chunks(project)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_documents_project ON documents(project)")
            conn.commit()

    @staticmethod
    def _tokens(text: str) -> set[str]:
        return set(_TOKEN_RE.findall(text.lower()))

    @staticmethod
    def chunk_text(text: str, chunk_size: int = 1200, overlap: int = 180) -> list[str]:
        text = re.sub(r"\s+", " ", text or "").strip()
        if not text:
            return []
        chunk_size = max(200, int(chunk_size))
        overlap = max(0, min(int(overlap), chunk_size // 2))
        chunks = []
        start = 0
        while start < len(text):
            end = min(len(text), start + chunk_size)
            if end < len(text):
                boundary = max(text.rfind(". ", start, end), text.rfind("; ", start, end), text.rfind(" ", start, end))
                if boundary > start + chunk_size // 2:
                    end = boundary + 1
            chunks.append(text[start:end].strip())
            if end >= len(text):
                break
            start = max(0, end - overlap)
        return chunks

    def add_document(self, project: str, title: str, content: str, source: str = "", metadata: dict | None = None, chunk_size: int = 1200, overlap: int = 180) -> dict:
        project = project.strip() or "default"
        title = title.strip() or "Untitled"
        if not content.strip():
            raise ValueError("El documento no puede estar vacío.")
        now = datetime.now(timezone.utc).isoformat()
        digest = hashlib.sha256(f"{project}\n{title}\n{source}\n{content}".encode("utf-8")).hexdigest()[:24]
        chunks = self.chunk_text(content, chunk_size, overlap)
        metadata = metadata or {}
        with self._connect() as conn:
            # FTS5 is not covered by SQLite foreign-key cascades, so remove
            # stale index rows before replacing the document chunks. Without
            # this, re-ingesting the same document leaves duplicate FTS rows.
            if self.fts_enabled:
                conn.execute(
                    "DELETE FROM chunks_fts WHERE id IN (SELECT id FROM chunks WHERE document_id = ?)",
                    (digest,),
                )
            conn.execute("DELETE FROM chunk_embeddings WHERE chunk_id IN (SELECT id FROM chunks WHERE document_id = ?)", (digest,))
            conn.execute("DELETE FROM chunks WHERE document_id = ?", (digest,))
            conn.execute("DELETE FROM documents WHERE id = ?", (digest,))
            conn.execute("INSERT INTO documents(id, project, title, source, metadata, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                         (digest, project, title, source, json.dumps(metadata, ensure_ascii=False), now))
            for idx, chunk in enumerate(chunks):
                cid = f"{digest}:{idx}"
                conn.execute("INSERT INTO chunks(id, project, document_id, title, content, chunk_index, metadata, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                             (cid, project, digest, title, chunk, idx, json.dumps(metadata, ensure_ascii=False), now))
                if self.fts_enabled:
                    conn.execute("INSERT INTO chunks_fts(id, project, title, content) VALUES (?, ?, ?, ?)", (cid, project, title, chunk))
                if self.embedder:
                    try:
                        vector = self.embedder(f"{title}\n{chunk}")
                        if vector:
                            conn.execute(
                                "INSERT OR REPLACE INTO chunk_embeddings(chunk_id, embedding, created_at) VALUES (?, ?, ?)",
                                (cid, json.dumps([float(x) for x in vector]), now),
                            )
                    except Exception:
                        # Embeddings are an enhancement, never a hard ingest dependency.
                        pass
            conn.commit()
        return {"document_id": digest, "chunks": len(chunks), "project": project, "title": title}

    def reindex_project(self, project: str, batch_size: int = 32) -> dict:
        """Generate missing embeddings for all chunks in a project.

        Reindexing is intentionally best-effort: a provider failure does not
        delete existing vectors or make lexical RAG unavailable.
        """
        if not self.embedder:
            return {"project": project, "indexed": 0, "skipped": 0, "errors": 0, "reason": "embedder_not_configured"}
        project = project.strip() or "default"
        batch_size = max(1, min(int(batch_size), 128))
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT c.id, c.title, c.content FROM chunks c LEFT JOIN chunk_embeddings e ON e.chunk_id=c.id WHERE c.project=? AND e.chunk_id IS NULL ORDER BY c.created_at ASC",
                (project,),
            ).fetchall()
        indexed = skipped = errors = 0
        now = datetime.now(timezone.utc).isoformat()
        for start in range(0, len(rows), batch_size):
            batch = rows[start:start + batch_size]
            try:
                vectors = [self.embedder(f"{r['title']}\n{r['content']}") for r in batch]
                if len(vectors) != len(batch):
                    raise RuntimeError("El proveedor devolvió una cantidad incorrecta de embeddings")
                with self._connect() as conn:
                    for row, vector in zip(batch, vectors):
                        if vector:
                            conn.execute(
                                "INSERT OR REPLACE INTO chunk_embeddings(chunk_id, embedding, created_at) VALUES (?, ?, ?)",
                                (row["id"], json.dumps([float(x) for x in vector]), now),
                            )
                            indexed += 1
                        else:
                            skipped += 1
                    conn.commit()
            except Exception:
                errors += len(batch)
        return {"project": project, "indexed": indexed, "skipped": skipped, "errors": errors}

    def delete_document(self, project: str, document_id: str) -> bool:
        with self._connect() as conn:
            row = conn.execute("SELECT id FROM documents WHERE id = ? AND project = ?", (document_id, project)).fetchone()
            if not row:
                return False
            if self.fts_enabled:
                conn.execute("DELETE FROM chunks_fts WHERE id IN (SELECT id FROM chunks WHERE document_id = ? AND project = ?)", (document_id, project))
            conn.execute("DELETE FROM chunk_embeddings WHERE chunk_id IN (SELECT id FROM chunks WHERE document_id = ? AND project = ?)", (document_id, project))
            conn.execute("DELETE FROM chunks WHERE document_id = ? AND project = ?", (document_id, project))
            conn.execute("DELETE FROM documents WHERE id = ? AND project = ?", (document_id, project))
            conn.commit()
            return True

    def list_documents(self, project: str) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute("SELECT id, title, source, created_at FROM documents WHERE project = ? ORDER BY created_at DESC", (project,)).fetchall()
        return [dict(r) for r in rows]

    @staticmethod
    def _cosine(a: list[float], b: list[float]) -> float:
        if not a or not b or len(a) != len(b):
            return -1.0
        dot = sum(x * y for x, y in zip(a, b))
        na = math.sqrt(sum(x * x for x in a))
        nb = math.sqrt(sum(y * y for y in b))
        return dot / (na * nb) if na and nb else -1.0

    def search(self, project: str, query: str, limit: int = 6) -> list[dict]:
        project = project.strip() or "default"
        query = query.strip()
        if not query:
            return []
        limit = max(1, min(int(limit), 50))
        tokens = self._tokens(query)
        candidates: dict[str, dict] = {}
        with self._connect() as conn:
            if self.fts_enabled:
                safe = " AND ".join(sorted(t for t in tokens if t.isalnum()))
                if safe:
                    rows = conn.execute(
                        "SELECT c.*, bm25(chunks_fts) AS rank FROM chunks_fts JOIN chunks c ON c.id = chunks_fts.id WHERE chunks_fts MATCH ? AND c.project = ? ORDER BY rank LIMIT ?",
                        (safe, project, min(limit * 8, 200)),
                    ).fetchall()
                    candidates.update({r["id"]: dict(r) for r in rows})

            # Semantic retrieval needs a wider candidate pool because a
            # semantically related chunk may share few/no literal query words.
            if self.embedder:
                rows = conn.execute(
                    "SELECT c.*, e.embedding FROM chunks c LEFT JOIN chunk_embeddings e ON e.chunk_id = c.id WHERE c.project = ? ORDER BY c.created_at DESC LIMIT 5000",
                    (project,),
                ).fetchall()
                for row in rows:
                    if row["id"] in candidates:
                        candidates[row["id"]]["embedding"] = row["embedding"]
                    else:
                        candidates[row["id"]] = dict(row)
            elif not candidates:
                rows = conn.execute("SELECT * FROM chunks WHERE project = ?", (project,)).fetchall()
                candidates.update({r["id"]: dict(r) for r in rows})

        q_lower = query.lower()
        qv = None
        if self.embedder:
            try:
                qv = self.embedder(query)
            except Exception:
                qv = None

        scored = []
        for row in candidates.values():
            text = f"{row['title']} {row['content']}".lower()
            row_tokens = self._tokens(text)
            overlap = len(tokens & row_tokens) / max(1, len(tokens))
            phrase = 0.25 if q_lower in text else 0.0
            title_bonus = 0.15 if any(t in row['title'].lower() for t in tokens) else 0.0
            lexical = overlap + phrase + title_bonus

            semantic = 0.0
            if qv and row.get("embedding"):
                try:
                    semantic = max(0.0, min(1.0, self._cosine(qv, json.loads(row["embedding"]))))
                except (TypeError, ValueError, json.JSONDecodeError):
                    semantic = 0.0

            # Preserve the original lexical score when embeddings are absent.
            # With embeddings, use a hybrid score so semantic matches can win
            # even when vocabulary differs.
            score = lexical if not qv else (0.55 * semantic + 0.45 * min(1.0, lexical))
            exact_match = bool(q_lower and (q_lower in row["content"].lower() or q_lower in row["title"].lower()))
            report = self.relevance_gate.assess(score, exact_match=exact_match)
            if report.accepted:
                item = dict(row)
                item.pop("embedding", None)
                item["score"] = round(score, 6)
                item["lexical_score"] = round(lexical, 6)
                if qv:
                    item["semantic_score"] = round(semantic, 6)
                item["relevance_reason"] = report.reason
                scored.append(item)
        scored.sort(key=lambda r: r["score"], reverse=True)
        return scored[:limit]


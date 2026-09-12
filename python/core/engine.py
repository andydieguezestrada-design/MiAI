from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping
import json
import os

from python.memory.store import MemoryStore
from python.rag.retriever import Retriever
from python.rag.store import RAGStore
from python.core.agent import AutonomousAgent, AgentResult
from python.core.vision import VisionEngine, VisionResult
from python.core.context import ContextManager, ContextBudget
from python.core.quality import ResponseQuality
from python.core.sessions import SessionStore
from python.models.factory import create_provider
from python.models.embedding_provider import OpenAICompatibleEmbeddingProvider
from python.memory.semantic import SemanticMemoryStore
from python.reasoning.pipeline import ReasoningPipeline
from python.tools.defaults import create_default_tool_registry
from python.tools.executor import ToolExecutor, ToolResult
from python.tools.registry import ToolRegistry


@dataclass
class AIResult:
    answer: str
    provider: str
    model: str


class AIEngine:
    def __init__(
        self,
        memory: MemoryStore | None = None,
        provider=None,
        tools: ToolRegistry | None = None,
        rag: Retriever | None = None,
    ):
        self.provider = provider or create_provider()
        self.memory = memory or MemoryStore()
        self.reasoning = ReasoningPipeline()
        self.context_manager = ContextManager(ContextBudget(
            max_chars=int(os.getenv("MIAI_MAX_CONTEXT_CHARS", "24000")),
            memory_chars=int(os.getenv("MIAI_MEMORY_CONTEXT_CHARS", "9000")),
            knowledge_chars=int(os.getenv("MIAI_KNOWLEDGE_CONTEXT_CHARS", "9000")),
            reserve_chars=int(os.getenv("MIAI_CONTEXT_RESERVE_CHARS", "4000")),
        ))
        self.quality = ResponseQuality()
        self.sessions = SessionStore(self.memory.db_path)
        self.semantic_memory = None
        self.embedding_provider = None
        if os.getenv("MIAI_SEMANTIC_MEMORY", "true").lower() in {"1", "true", "yes", "on"}:
            try:
                base_url = os.getenv("MIAI_EMBEDDING_BASE_URL", os.getenv("MIAI_BASE_URL", ""))
                api_key = os.getenv("MIAI_EMBEDDING_API_KEY", os.getenv("MIAI_API_KEY", ""))
                model = os.getenv("MIAI_EMBEDDING_MODEL", "text-embedding-3-small")
                if base_url and model:
                    self.embedding_provider = OpenAICompatibleEmbeddingProvider(
                        base_url, api_key, model, float(os.getenv("MIAI_EMBEDDING_TIMEOUT", "30"))
                    )
                    self.semantic_memory = SemanticMemoryStore(self.memory.db_path, self.embedding_provider.embed)
            except Exception:
                self.semantic_memory = None
                self.embedding_provider = None
        if rag is not None:
            self.rag = rag
        else:
            self.rag = Retriever(RAGStore(embedder=self.embedding_provider.embed if self.embedding_provider else None))
        self.tools = tools or create_default_tool_registry()
        self.tool_executor = ToolExecutor(self.tools)
        self.agent = AutonomousAgent(self.provider, self.tools, self.tool_executor)
        self.vision = VisionEngine(self.memory, self.rag)

    def reindex_knowledge(self, project: str, batch_size: int = 32) -> dict:
        return self.rag.store.reindex_project(project, batch_size=batch_size)

    def chat(
        self,
        message: str,
        project: str = "default",
        system: str | None = None,
        temperature: float = 0.7,
        session_id: str | None = None,
        response_format: str = "text",
    ) -> AIResult:
        project = project.strip() or "default"
        if session_id:
            session = self.sessions.get(session_id)
            if session and session["project"] != project:
                raise ValueError("La sesión no pertenece al proyecto indicado.")

        retrieved = self.memory.search(project, message, session_id=session_id)
        if self.semantic_memory:
            semantic = self.semantic_memory.search(project, message, limit=8, session_id=session_id)
            seen = {(x["role"], x["content"]) for x in retrieved}
            retrieved.extend(x for x in semantic if (x["role"], x["content"]) not in seen)
        memory_context = "\n".join(
            f"{item['role']}: {item['content']}" for item in retrieved
        )
        knowledge = self.rag.search(message, project=project, limit=6)
        retrieved_context = "\n".join(
            f"[knowledge:{item['title']}] {item['content']}" for item in knowledge
        )
        if memory_context:
            retrieved_context = memory_context + ("\n" + retrieved_context if retrieved_context else "")

        memory_text, knowledge_text = self.context_manager.build(
            self.memory.context(project, session_id=session_id), retrieved_context
        )
        prompt = self.reasoning.build_prompt(
            message=message,
            memory_context=memory_text,
            system=system,
            project_profile=self.memory.get_profile(project),
            retrieved_context=knowledge_text,
            tool_schemas=self.tools.schemas(),
        )
        if response_format == "json":
            prompt += "\nJSON MODE: Devuelve exclusivamente un objeto JSON válido, sin markdown ni texto fuera del JSON."
        elif response_format not in {"text", "json"}:
            raise ValueError("response_format debe ser 'text' o 'json'.")

        answer = self.quality.validate(self.provider.generate(prompt, temperature=temperature))
        if response_format == "text" and os.getenv("MIAI_AUTO_REFINE", "true").lower() in {"1", "true", "yes", "on"}:
            report = self.quality.assess(answer, message)
            if report.needs_refinement:
                refine_prompt = (
                    "Mejora la respuesta anterior para que cumpla completamente la solicitud. "
                    "Aporta más análisis, contexto, criterios y conclusiones útiles cuando correspondan. "
                    "No inventes información y no reveles razonamiento interno privado.\n\n"
                    f"SOLICITUD:\n{message}\n\nRESPUESTA ANTERIOR:\n{answer}"
                )
                answer = self.quality.validate(self.provider.generate(refine_prompt, temperature=temperature))
        if response_format == "json":
            try:
                json.loads(answer)
            except json.JSONDecodeError as exc:
                raise RuntimeError(f"El proveedor no devolvió JSON válido: {exc}") from exc

        self.memory.add(project, "user", message, session_id=session_id)
        self.memory.add(project, "assistant", answer, session_id=session_id)
        if self.semantic_memory:
            self.semantic_memory.add(project, "user", message, session_id=session_id)
            self.semantic_memory.add(project, "assistant", answer, session_id=session_id)
        if session_id:
            if not self.sessions.get(session_id):
                self.sessions.create(session_id, project)
            self.sessions.touch(session_id)

        return AIResult(answer, self.provider.name, self.provider.model)

    def create_session(self, project: str = "default", session_id: str | None = None, title: str = "") -> dict:
        import uuid
        return self.sessions.create(session_id or uuid.uuid4().hex, project, title)

    def list_sessions(self, project: str = "default", limit: int = 50) -> list[dict]:
        return self.sessions.list(project, limit)

    def get_session(self, session_id: str) -> dict | None:
        return self.sessions.get(session_id)

    def delete_session(self, session_id: str) -> bool:
        session = self.sessions.get(session_id)
        deleted = self.sessions.delete(session_id)
        if deleted and session:
            self.memory.clear(session["project"], session_id=session_id)
            if self.semantic_memory:
                self.semantic_memory.clear(session["project"], session_id=session_id)
        return deleted

    def update_session(self, session_id: str, title: str | None = None, summary: str | None = None) -> dict | None:
        if not self.sessions.get(session_id):
            return None
        self.sessions.touch(session_id, title=title, summary=summary)
        return self.sessions.get(session_id)

    def session_messages(self, session_id: str, limit: int = 50) -> list[dict]:
        session = self.sessions.get(session_id)
        if not session:
            return []
        return list(reversed(self.memory.recent(session["project"], limit=limit, session_id=session_id)))

    def clear_session(self, session_id: str) -> bool:
        session = self.sessions.get(session_id)
        if not session:
            return False
        self.memory.clear(session["project"], session_id=session_id)
        if self.semantic_memory:
            self.semantic_memory.clear(session["project"], session_id=session_id)
        self.sessions.touch(session_id, summary="")
        return True

    def stream_chat(self, message: str, project: str = "default", system: str | None = None, temperature: float = 0.7, session_id: str | None = None):
        """Yield provider chunks while persisting the completed answer."""
        project = project.strip() or "default"
        if session_id:
            session = self.sessions.get(session_id)
            if session and session["project"] != project:
                raise ValueError("La sesión no pertenece al proyecto indicado.")
        # Reuse the exact chat prompt construction without calling the model twice.
        retrieved = self.memory.search(project, message, session_id=session_id)
        if self.semantic_memory:
            semantic = self.semantic_memory.search(project, message, limit=8, session_id=session_id)
            seen = {(x["role"], x["content"]) for x in retrieved}
            retrieved.extend(x for x in semantic if (x["role"], x["content"]) not in seen)
        knowledge = self.rag.search(message, project=project, limit=6)
        retrieved_context = "\n".join(f"[knowledge:{item['title']}] {item['content']}" for item in knowledge)
        memory_context = "\n".join(f"{item['role']}: {item['content']}" for item in retrieved)
        if memory_context:
            retrieved_context = memory_context + ("\n" + retrieved_context if retrieved_context else "")
        memory_text, knowledge_text = self.context_manager.build(self.memory.context(project, session_id=session_id), retrieved_context)
        prompt = self.reasoning.build_prompt(message=message, memory_context=memory_text, system=system, project_profile=self.memory.get_profile(project), retrieved_context=knowledge_text, tool_schemas=self.tools.schemas())
        chunks = []
        for chunk in self.provider.stream(prompt, temperature=temperature):
            chunks.append(chunk)
            yield chunk
        answer = self.quality.validate("".join(chunks))
        self.memory.add(project, "user", message, session_id=session_id)
        self.memory.add(project, "assistant", answer, session_id=session_id)
        if self.semantic_memory:
            self.semantic_memory.add(project, "user", message, session_id=session_id)
            self.semantic_memory.add(project, "assistant", answer, session_id=session_id)
        if session_id:
            if not self.sessions.get(session_id):
                self.sessions.create(session_id, project)
            self.sessions.touch(session_id)

    def remember(
        self,
        project: str,
        content: str,
        role: str = "system",
        kind: str = "fact",
        session_id: str | None = None,
    ) -> None:
        self.memory.add(project, role, content, kind=kind, session_id=session_id)
        if self.semantic_memory:
            self.semantic_memory.add(project, role, content, kind=kind, session_id=session_id)

    def list_tools(self) -> list[dict[str, Any]]:
        return self.tools.schemas()

    def execute_tool(
        self,
        name: str,
        arguments: Mapping[str, Any] | None = None,
    ) -> ToolResult:
        return self.tool_executor.execute(name, arguments)


    def ingest_document(
        self,
        project: str,
        title: str,
        content: str,
        source: str = "",
        metadata: dict | None = None,
        chunk_size: int = 1200,
        overlap: int = 180,
    ) -> dict:
        return self.rag.store.add_document(project, title, content, source, metadata, chunk_size, overlap)

    def search_knowledge(self, project: str, query: str, limit: int = 6) -> list[dict]:
        return self.rag.search(query, project=project, limit=limit)

    def list_knowledge(self, project: str) -> list[dict]:
        return self.rag.store.list_documents(project)

    def delete_knowledge(self, project: str, document_id: str) -> bool:
        return self.rag.store.delete_document(project, document_id)


    def vision_analyze(
        self,
        image_base64: str,
        instruction: str,
        project: str = "default",
        system: str | None = None,
        mime_type: str = "image/jpeg",
        temperature: float = 0.2,
    ) -> VisionResult:
        return self.vision.analyze(
            image_base64=image_base64,
            instruction=instruction,
            project=project,
            system=system,
            mime_type=mime_type,
            temperature=temperature,
        )

    def agent_task(
        self,
        task: str,
        project: str = "default",
        system: str | None = None,
        temperature: float = 0.2,
        max_steps: int = 6,
    ) -> AgentResult:
        result = self.agent.run(
            task=task,
            project=project,
            system=system,
            temperature=temperature,
            max_steps=max_steps,
        )
        self.memory.add(project.strip() or "default", "user", task, kind="agent_task")
        self.memory.add(
            project.strip() or "default",
            "assistant",
            result.answer,
            kind="agent_result",
        )
        return result

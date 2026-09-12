from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
import json
from pydantic import BaseModel, Field

from python.admin.release_manager import ReleaseManager
from python.admin.routes import create_admin_router
from python.admin.store import AdminStore
from python.core.engine import AIEngine
from python.core.version import VERSION


app = FastAPI(
    title="MiAI Core",
    version=VERSION,
    description=(
        "Cerebro de IA reutilizable: V1 + V2 integradas, memoria persistente, "
        "perfiles de proyecto, recuperación local y Tool/Plugin Engine, Autonomous Agent, Advanced RAG, Vision Engine, streaming, sesiones avanzadas y memoria semántica."
    ),
)
engine = AIEngine()
admin_store = AdminStore()
release_manager = ReleaseManager()
app.include_router(create_admin_router(engine, admin_store, release_manager))


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)
    project: str = "default"
    system: str | None = None
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    session_id: str | None = None
    response_format: str = Field(default="text", pattern="^(text|json)$")


class ChatResponse(BaseModel):
    answer: str
    provider: str
    model: str
    project: str


class MemoryRequest(BaseModel):
    project: str = "default"
    content: str = Field(min_length=1)
    kind: str = "fact"
    session_id: str | None = None


class ProfileRequest(BaseModel):
    project: str = "default"
    profile: str = ""


class ToolExecuteRequest(BaseModel):
    tool: str = Field(min_length=1)
    arguments: dict[str, Any] = Field(default_factory=dict)


class AgentRequest(BaseModel):
    task: str = Field(min_length=1)
    project: str = "default"
    system: str | None = None
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    max_steps: int = Field(default=6, ge=1, le=12)


class DocumentRequest(BaseModel):
    project: str = "default"
    title: str = Field(min_length=1)
    content: str = Field(min_length=1)
    source: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)
    chunk_size: int = Field(default=1200, ge=200, le=10000)
    overlap: int = Field(default=180, ge=0, le=5000)


class KnowledgeSearchRequest(BaseModel):
    project: str = "default"
    query: str = Field(min_length=1)
    limit: int = Field(default=6, ge=1, le=50)

class VisionRequest(BaseModel):
    image_base64: str = Field(min_length=1, description="Imagen codificada en Base64, sin necesidad de guardar un archivo en MiAI.")
    instruction: str = Field(default="Analiza detalladamente esta imagen.", min_length=1)
    project: str = "default"
    system: str | None = None
    mime_type: str = "image/jpeg"
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)


@app.get("/system/version")
def system_version():
    return {
        "product": "MiAI Core",
        "version": app.version,
        "channel": "stable-candidate",
        "update_policy": "manual-owner-approval",
        "auto_update": False,
        "min_supported_version": "0.12.0-b4",
    }


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "MiAI Core",
        "version": app.version,
        "memory": "sqlite",
        "tools": len(engine.list_tools()),
    }


@app.post("/ai/chat/stream")
def chat_stream(request: ChatRequest):
    def events():
        try:
            for chunk in engine.stream_chat(
                message=request.message, project=request.project, system=request.system,
                temperature=request.temperature, session_id=request.session_id
            ):
                yield "data: " + json.dumps({"type": "token", "content": chunk}, ensure_ascii=False) + "\n\n"
            yield "data: " + json.dumps({"type": "done"}) + "\n\n"
        except Exception as exc:
            yield "data: " + json.dumps({"type": "error", "error": str(exc)}, ensure_ascii=False) + "\n\n"
    return StreamingResponse(events(), media_type="text/event-stream", headers={"Cache-Control":"no-cache", "X-Accel-Buffering":"no"})


@app.post("/ai/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    try:
        result = engine.chat(
            message=request.message,
            project=request.project,
            system=request.system,
            temperature=request.temperature,
            session_id=request.session_id,
            response_format=request.response_format,
        )
    except RuntimeError as exc:
        admin_store.log_system("chat", str(exc), level="error")
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return ChatResponse(
        answer=result.answer,
        provider=result.provider,
        model=result.model,
        project=request.project.strip() or "default",
    )


class SessionRequest(BaseModel):
    project: str = "default"
    session_id: str | None = None
    title: str = ""


@app.post("/ai/sessions")
def create_session(request: SessionRequest):
    return engine.create_session(request.project, request.session_id, request.title)


@app.get("/ai/sessions/{project}")
def list_sessions(project: str, limit: int = 50):
    return {"project": project.strip() or "default", "sessions": engine.list_sessions(project, limit)}


@app.get("/ai/session/{session_id}")
def get_session(session_id: str):
    result = engine.get_session(session_id)
    if not result:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")
    return result


class SessionUpdateRequest(BaseModel):
    title: str | None = None
    summary: str | None = None


@app.patch("/ai/session/{session_id}")
def update_session(session_id: str, request: SessionUpdateRequest):
    result = engine.update_session(session_id, request.title, request.summary)
    if not result:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")
    return result


@app.get("/ai/session/{session_id}/messages")
def session_messages(session_id: str, limit: int = 50):
    if not engine.get_session(session_id):
        raise HTTPException(status_code=404, detail="Sesión no encontrada")
    return {"session_id": session_id, "messages": engine.session_messages(session_id, limit)}


@app.delete("/ai/session/{session_id}/messages")
def clear_session_messages(session_id: str):
    if not engine.clear_session(session_id):
        raise HTTPException(status_code=404, detail="Sesión no encontrada")
    return {"status": "cleared", "session_id": session_id}


@app.delete("/ai/session/{session_id}")
def delete_session(session_id: str):
    if not engine.delete_session(session_id):
        raise HTTPException(status_code=404, detail="Sesión no encontrada")
    return {"status": "deleted", "session_id": session_id}


@app.post("/ai/memory")
def add_memory(request: MemoryRequest):
    engine.remember(
        project=request.project,
        content=request.content,
        kind=request.kind,
        session_id=request.session_id,
    )
    return {"status": "stored", "project": request.project.strip() or "default"}


@app.get("/ai/memory/{project}")
def get_memory(project: str):
    return {"project": project, "context": engine.memory.context(project)}


@app.delete("/ai/memory/{project}")
def clear_memory(project: str):
    engine.memory.clear(project)
    return {"status": "cleared", "project": project}


@app.put("/ai/project/profile")
def set_project_profile(request: ProfileRequest):
    engine.memory.set_profile(request.project, request.profile)
    return {"status": "stored", "project": request.project.strip() or "default"}


@app.get("/ai/project/{project}/profile")
def get_project_profile(project: str):
    return {"project": project, "profile": engine.memory.get_profile(project)}


@app.get("/ai/tools")
def list_tools():
    return {"tools": engine.list_tools()}


@app.post("/ai/tools/execute")
def execute_tool(request: ToolExecuteRequest):
    result = engine.execute_tool(request.tool, request.arguments)
    if not result.ok:
        admin_store.log_audit(f"tool:{request.tool}", level="error", error_message=result.error)
        raise HTTPException(status_code=400, detail=result.error)
    admin_store.log_audit(f"tool:{request.tool}", level="info")
    return result.as_dict()


@app.post("/ai/knowledge")
def ingest_knowledge(request: DocumentRequest):
    try:
        return engine.ingest_document(
            project=request.project, title=request.title, content=request.content,
            source=request.source, metadata=request.metadata,
            chunk_size=request.chunk_size, overlap=request.overlap,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/ai/knowledge/search")
def search_knowledge(request: KnowledgeSearchRequest):
    return {"project": request.project.strip() or "default", "results": engine.search_knowledge(request.project, request.query, request.limit)}


@app.post("/ai/knowledge/{project}/reindex")
def reindex_knowledge(project: str, batch_size: int = 32):
    if batch_size < 1 or batch_size > 128:
        raise HTTPException(status_code=400, detail="batch_size debe estar entre 1 y 128")
    return engine.reindex_knowledge(project, batch_size)


@app.get("/ai/knowledge/{project}")
def list_knowledge(project: str):
    return {"project": project, "documents": engine.list_knowledge(project)}


@app.delete("/ai/knowledge/{project}/{document_id}")
def delete_knowledge(project: str, document_id: str):
    if not engine.delete_knowledge(project, document_id):
        raise HTTPException(status_code=404, detail="Documento no encontrado.")
    return {"status": "deleted", "project": project, "document_id": document_id}



@app.post("/ai/vision")
def analyze_vision(request: VisionRequest):
    try:
        result = engine.vision_analyze(
            image_base64=request.image_base64,
            instruction=request.instruction,
            project=request.project,
            system=request.system,
            mime_type=request.mime_type,
            temperature=request.temperature,
        )
    except (RuntimeError, ValueError) as exc:
        admin_store.log_system("vision", str(exc), level="error")
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "answer": result.answer,
        "provider": result.provider,
        "model": result.model,
        "project": result.project,
    }

@app.post("/ai/agent")
def run_agent(request: AgentRequest):
    try:
        result = engine.agent_task(
            task=request.task,
            project=request.project,
            system=request.system,
            temperature=request.temperature,
            max_steps=request.max_steps,
        )
    except (RuntimeError, ValueError) as exc:
        admin_store.log_system("agent", str(exc), level="error")
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    for step in result.steps:
        if step.action == "tool" and step.tool:
            if step.error:
                admin_store.log_audit(f"tool:{step.tool}", level="error", error_message=step.error)
            else:
                admin_store.log_audit(f"tool:{step.tool}", level="info")

    return {
        "answer": result.answer,
        "provider": result.provider,
        "model": result.model,
        "project": request.project.strip() or "default",
        "status": result.status,
        "steps": [
            {
                "index": step.index,
                "action": step.action,
                "tool": step.tool,
                "arguments": step.arguments,
                "result": step.result,
                "error": step.error,
            }
            for step in result.steps
        ],
    }

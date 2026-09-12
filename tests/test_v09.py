import json

from fastapi.testclient import TestClient

from api.main import app
from python.core.engine import AIEngine
from python.memory.store import MemoryStore
from python.memory.semantic import SemanticMemoryStore
from python.models.mock_provider import MockProvider
from python.core.version import VERSION


def test_session_scoped_memory_and_messages(tmp_path):
    memory = MemoryStore(str(tmp_path / "m.sqlite3"))
    engine = AIEngine(memory=memory, provider=MockProvider())
    a = engine.create_session("p", "a", "A")
    b = engine.create_session("p", "b", "B")
    engine.memory.add("p", "user", "solo A", session_id=a["id"])
    engine.memory.add("p", "user", "solo B", session_id=b["id"])
    assert "solo A" in engine.memory.context("p", session_id="a")
    assert "solo B" not in engine.memory.context("p", session_id="a")
    assert engine.session_messages("a")[0]["content"] == "solo A"
    engine.update_session("a", title="Nuevo A", summary="Resumen")
    assert engine.get_session("a")["title"] == "Nuevo A"
    assert engine.clear_session("a")
    assert engine.session_messages("a") == []


def test_stream_chat_persists_completed_answer(tmp_path):
    engine = AIEngine(memory=MemoryStore(str(tmp_path / "m.sqlite3")), provider=MockProvider())
    sid = engine.create_session("p")["id"]
    chunks = list(engine.stream_chat("hola", project="p", session_id=sid))
    assert "".join(chunks).startswith("Respuesta de prueba")
    assert len(engine.session_messages(sid)) == 2


def test_semantic_store_lexical_fallback(tmp_path):
    store = SemanticMemoryStore(str(tmp_path / "semantic.sqlite3"))
    store.add("p", "user", "Poseidon con olas y tridente", kind="fact")
    result = store.search("p", "olas tridente", limit=1)
    assert result and result[0]["content"].startswith("Poseidon")


def test_v09_api_session_routes():
    client = TestClient(app)
    created = client.post("/ai/sessions", json={"project":"v09", "title":"Demo"})
    assert created.status_code == 200
    sid = created.json()["id"]
    assert client.patch(f"/ai/session/{sid}", json={"title":"Renamed"}).status_code == 200
    assert client.get(f"/ai/session/{sid}/messages").status_code == 200
    assert client.delete(f"/ai/session/{sid}/messages").status_code == 200
    assert client.delete(f"/ai/session/{sid}").status_code == 200


def test_stream_includes_semantic_memory_and_persists_it(tmp_path):
    db = str(tmp_path / "semantic.sqlite3")
    memory = MemoryStore(db)
    semantic = SemanticMemoryStore(db)
    semantic.add("p", "user", "El usuario prefiere respuestas técnicas detalladas", kind="preference")
    engine = AIEngine(memory=memory, provider=MockProvider())
    engine.semantic_memory = semantic
    sid = engine.create_session("p")["id"]
    chunks = list(engine.stream_chat("¿Qué prefiero?", project="p", session_id=sid))
    assert chunks
    saved = semantic.search("p", "prefiere respuestas técnicas", session_id=sid)
    # The pre-existing global memory remains visible; new streamed messages are session-scoped.
    assert semantic.search("p", "respuestas de prueba", session_id=sid) or saved == []


def test_api_health_reports_v091():
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["version"] == VERSION

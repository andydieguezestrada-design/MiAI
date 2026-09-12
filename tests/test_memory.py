from python.core.engine import AIEngine
from python.memory.store import MemoryStore
from python.models.mock_provider import MockProvider


def test_memory_persists_between_store_instances(tmp_path):
    db = tmp_path / "memory.sqlite3"

    first = MemoryStore(str(db))
    first.add("ARTattoo", "user", "La aplicación debe priorizar calidad.", kind="fact")

    second = MemoryStore(str(db))
    context = second.context("ARTattoo")

    assert "priorizar calidad" in context


def test_project_profile_is_persistent(tmp_path):
    db = tmp_path / "memory.sqlite3"

    first = MemoryStore(str(db))
    first.set_profile("ARTattoo", "Proyecto de stencils profesionales.")

    second = MemoryStore(str(db))
    assert second.get_profile("ARTattoo") == "Proyecto de stencils profesionales."


def test_engine_uses_persistent_memory(tmp_path):
    db = tmp_path / "memory.sqlite3"

    store = MemoryStore(str(db))
    engine = AIEngine(memory=store, provider=MockProvider())

    result = engine.chat("Hola MiAI", project="demo")

    assert result.provider == "mock"
    assert "Hola MiAI" in store.context("demo")


def test_context_budget_and_sessions(tmp_path):
    from python.core.context import ContextManager, ContextBudget
    from python.core.sessions import SessionStore
    cm = ContextManager(ContextBudget(max_chars=100, memory_chars=60, knowledge_chars=60, reserve_chars=10))
    memory, knowledge = cm.build("m" * 200, "k" * 200)
    assert len(memory) + len(knowledge) <= 90
    sessions = SessionStore(str(tmp_path / "memory.sqlite3"))
    created = sessions.create("abc", "demo", "Test")
    assert created["id"] == "abc"
    assert sessions.get("abc")["project"] == "demo"

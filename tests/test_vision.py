import base64

from fastapi.testclient import TestClient

from api.main import app, engine
from python.models.mock_vision_provider import MockVisionProvider


def test_vision_engine_with_mock(monkeypatch, tmp_path):
    monkeypatch.setenv("MIAI_MEMORY_DB", str(tmp_path / "memory.sqlite3"))
    engine.vision.provider = MockVisionProvider()
    result = engine.vision_analyze(base64.b64encode(b"fake-image").decode(), "Describe the image", project="vision-test")
    assert result.answer
    assert result.provider == "mock_vision"


def test_vision_api_with_mock(monkeypatch):
    engine.vision.provider = MockVisionProvider()
    client = TestClient(app)
    response = client.post("/ai/vision", json={
        "image_base64": base64.b64encode(b"fake-image").decode(),
        "instruction": "Analiza con detalle",
        "project": "api-vision-test",
        "mime_type": "image/png",
    })
    assert response.status_code == 200
    data = response.json()
    assert data["provider"] == "mock_vision"
    assert data["answer"]

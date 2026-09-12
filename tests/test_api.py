import os

os.environ["MIAI_PROVIDER"] = "mock"

from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_api_contract():
    response = client.post(
        "/ai/chat",
        json={"message": "test", "project": "default"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["provider"] == "mock"
    assert data["project"] == "default"
    assert data["answer"]


def test_api_knowledge_contract():
    from fastapi.testclient import TestClient
    from api.main import app
    client = TestClient(app)
    created = client.post('/ai/knowledge', json={
        'project': 'ci-rag', 'title': 'Guide',
        'content': 'MiAI usa memoria, herramientas y recuperación de conocimiento.'
    })
    assert created.status_code == 200
    found = client.post('/ai/knowledge/search', json={
        'project': 'ci-rag', 'query': 'recuperación conocimiento'
    })
    assert found.status_code == 200
    assert found.json()['results']


def test_api_sessions_and_json_mode():
    created = client.post('/ai/sessions', json={'project':'ci-session','title':'Demo'})
    assert created.status_code == 200
    sid = created.json()['id']
    listed = client.get('/ai/sessions/ci-session')
    assert listed.status_code == 200
    assert listed.json()['sessions']
    chat = client.post('/ai/chat', json={'message':'test json','project':'ci-session','session_id':sid,'response_format':'json'})
    # MockProvider is intentionally plain text, so MiAI must reject invalid JSON.
    assert chat.status_code in (400, 503)

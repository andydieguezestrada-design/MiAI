import io
import json
import os
import zipfile

os.environ["MIAI_PROVIDER"] = "mock"

import pytest
from fastapi.testclient import TestClient

from api.main import app, admin_store, engine
from python.admin.auth import set_credentials

TOKEN = "test-owner-token-0123456789"
PIN = "123456"
set_credentials(admin_store, TOKEN, PIN)

client = TestClient(app)
HEADERS = {"X-Owner-Token": TOKEN}

_original_provider = engine.provider


@pytest.fixture(autouse=True, scope="module")
def _restore_engine_provider():
    """/admin/provider/switch mutates the shared engine singleton used by
    other test modules (e.g. test_api.py expects provider == 'mock'); make
    sure we always hand it back the way we found it."""
    yield
    engine.provider = _original_provider
    engine.agent.provider = _original_provider
    admin_store.set_setting("cost_policy", "zero_cost")


def test_admin_requires_owner_token():
    response = client.get("/admin/status")
    assert response.status_code == 401


def test_admin_rejects_wrong_token():
    response = client.get("/admin/status", headers={"X-Owner-Token": "not-the-real-token"})
    assert response.status_code == 401


def test_status_with_valid_token():
    response = client.get("/admin/status", headers=HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert data["cost_policy"] in {"zero_cost", "paid_allowed"}
    assert "active_provider" in data and "active_model" in data


def test_zero_cost_policy_blocks_paid_provider_switch():
    client.post("/admin/policy/cost", json={"policy": "zero_cost"}, headers=HEADERS)
    response = client.post(
        "/admin/provider/switch",
        json={"provider": "openai_compatible", "model": "gpt-4o"},
        headers=HEADERS,
    )
    assert response.status_code == 400


def test_zero_cost_policy_allows_ollama_switch():
    # Constructing OllamaProvider doesn't touch the network; only .generate() does.
    response = client.post(
        "/admin/provider/switch",
        json={"provider": "ollama", "model": "llama3.2:1b"},
        headers=HEADERS,
    )
    assert response.status_code == 200
    assert response.json()["active_provider"] == "ollama"
    assert response.json()["active_model"] == "llama3.2:1b"


def test_stats_advanced_shape():
    response = client.get("/admin/stats/advanced", headers=HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert "tool_metrics_7d" in data and "system_health" in data
    assert "total_calls" in data["tool_metrics_7d"]
    assert "memory_db_mb" in data["system_health"]


def test_logs_endpoint_accepts_audit_and_system_kinds():
    for kind in ("audit", "system"):
        response = client.get(f"/admin/logs/{kind}", headers=HEADERS)
        assert response.status_code == 200
        assert "logs" in response.json()


def test_logs_endpoint_rejects_unknown_kind():
    response = client.get("/admin/logs/nonsense", headers=HEADERS)
    assert response.status_code == 404


def test_release_upload_apply_rollback_lifecycle():
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        zf.writestr("release.json", json.dumps({"version": "0.13.0-admin-test", "channel": "beta"}))
    buffer.seek(0)

    upload = client.post(
        "/admin/release/upload",
        files={"file": ("release.zip", buffer, "application/zip")},
        headers=HEADERS,
    )
    assert upload.status_code == 200
    assert upload.json()["pending"]["version"] == "0.13.0-admin-test"

    applied = client.post("/admin/release/apply", headers=HEADERS)
    assert applied.status_code == 200
    assert applied.json()["current_version"] == "0.13.0-admin-test"
    assert applied.json()["pending"] is None

    rolled_back = client.post("/admin/release/rollback", headers=HEADERS)
    assert rolled_back.status_code == 200
    assert rolled_back.json()["current_version"] != "0.13.0-admin-test"


def test_release_upload_rejects_zip_without_manifest():
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        zf.writestr("readme.txt", "no release.json here")
    buffer.seek(0)

    response = client.post(
        "/admin/release/upload",
        files={"file": ("bad.zip", buffer, "application/zip")},
        headers=HEADERS,
    )
    assert response.status_code == 400


def test_release_apply_without_pending_fails():
    response = client.post("/admin/release/apply", headers=HEADERS)
    assert response.status_code == 400

def test_provider_catalog_does_not_expose_credentials():
    response = client.get("/admin/providers", headers=HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert "chain" in data
    raw = response.text
    assert "MIAI_" not in raw
    assert "API_KEY" not in raw

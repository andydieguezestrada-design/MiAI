import json
from pathlib import Path
from fastapi.testclient import TestClient

from api.main import app
from python.core.version import VERSION, CHANNEL, UPDATE_POLICY, AUTO_UPDATE


def test_release_contract_matches_runtime():
    manifest = json.loads(Path("release.json").read_text(encoding="utf-8"))
    assert manifest["version"] == VERSION == app.version
    assert manifest["channel"] == CHANNEL
    assert manifest["update_policy"] == UPDATE_POLICY
    assert manifest["auto_update"] is AUTO_UPDATE is False


def test_system_version_exposes_manual_update_policy():
    response = TestClient(app).get("/system/version")
    assert response.status_code == 200
    data = response.json()
    assert data["version"] == VERSION
    assert data["auto_update"] is False
    assert data["update_policy"] == "manual-owner-approval"

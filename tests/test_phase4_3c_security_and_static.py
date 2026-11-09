import os
import pytest
from starlette.testclient import TestClient

def test_fail_closed_without_token(monkeypatch):
    monkeypatch.delenv("CREW_API_TOKEN", raising=False)
    monkeypatch.setenv("CREW_DEV_NO_AUTH", "0")

    from backend.app.main import app

    with pytest.raises(RuntimeError, match="FATAL: CREW_API_TOKEN is missing"):
        with TestClient(app) as client:
            client.get("/health")

def test_static_files_public_and_api_protected(monkeypatch):
    test_token = "test_secret_token_1234567890abcdef"
    monkeypatch.setenv("CREW_API_TOKEN", test_token)
    monkeypatch.setenv("CREW_DEV_NO_AUTH", "0")
    monkeypatch.setenv("CREW_DATA_DIR", "tests/e2e_data")

    from backend.app.main import app

    with TestClient(app) as client:
        # 1. Root and static files must be served publicly without token
        resp_root = client.get("/")
        assert resp_root.status_code == 200
        assert "<!doctype html>" in resp_root.text.lower() or "<html" in resp_root.text.lower()

        # 2. /health must be served publicly without token
        resp_health = client.get("/health")
        assert resp_health.status_code == 200
        assert resp_health.json().get("status") in ("ok", "error")

        # 3. API endpoints must require token (fail-closed if missing)
        resp_unauth = client.get("/channels")
        assert resp_unauth.status_code == 401
        assert "Unauthorized" in resp_unauth.json().get("detail", "")

        # 4. API endpoints with wrong token must return 401
        resp_wrong = client.get("/channels", headers={"X-Crew-Token": "wrong_token"})
        assert resp_wrong.status_code == 401

        # 5. API endpoints with correct header token must return 200
        resp_auth = client.get("/channels", headers={"X-Crew-Token": test_token})
        assert resp_auth.status_code == 200
        assert isinstance(resp_auth.json(), list)

        # 6. API endpoints with correct query param token must return 200
        resp_query = client.get(f"/channels?token={test_token}")
        assert resp_query.status_code == 200
        assert isinstance(resp_query.json(), list)

def test_dev_no_auth_override(monkeypatch):
    monkeypatch.delenv("CREW_API_TOKEN", raising=False)
    monkeypatch.setenv("CREW_DEV_NO_AUTH", "1")
    monkeypatch.setenv("CREW_DATA_DIR", "tests/e2e_data")

    from backend.app.main import app

    with TestClient(app) as client:
        resp = client.get("/channels")
        assert resp.status_code == 200

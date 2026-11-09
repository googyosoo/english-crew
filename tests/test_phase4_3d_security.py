import os
import sys
import secrets
import pytest
from starlette.testclient import TestClient

def test_phase4_3d_default_deny_and_trusted_host(monkeypatch):
    """
    [Phase 4-3d Security Tests]
    1. 토큰 없이 /tasks/x/deliverable, /bots -> 401 Unauthorized
    2. Host: evil.example -> 400 Bad Request (DNS Rebinding block)
    3. 올바른 Host(127.0.0.1:8765, localhost:8765) 및 토큰 -> 정상 응답
    4. 설치 모드(CREW_DEV_MODE=0)에서 /docs, /redoc, /openapi.json 비활성화
    """
    test_token = secrets.token_hex(32)
    monkeypatch.setenv("CREW_API_TOKEN", test_token)
    monkeypatch.setenv("CREW_DEV_MODE", "0") # Packaged installation mode
    monkeypatch.setenv("CREW_DEV_NO_AUTH", "0")
    monkeypatch.setenv("CREW_DATA_DIR", "tests/e2e_data")

    from backend.app.main import app
    client = TestClient(app)

    # 1. 토큰 없이 /tasks/x/deliverable -> 401
    resp_tasks = client.get("/tasks/some_task_id/deliverable")
    assert resp_tasks.status_code == 401, f"Expected 401, got {resp_tasks.status_code}"
    assert "Unauthorized" in resp_tasks.json().get("detail", "")
    print("PASS: 1a. Request to /tasks/x/deliverable without token returns 401.")

    # 2. 토큰 없이 /bots -> 401
    resp_bots = client.get("/bots")
    assert resp_bots.status_code == 401, f"Expected 401, got {resp_bots.status_code}"
    assert "Unauthorized" in resp_bots.json().get("detail", "")
    print("PASS: 1b. Request to /bots without token returns 401.")

    # 3. Host: evil.example -> 400 Bad Request
    resp_evil_host = client.get("/health", headers={"host": "evil.example"})
    assert resp_evil_host.status_code == 400, f"Expected 400 for evil host, got {resp_evil_host.status_code}"
    print("PASS: 2. Host header evil.example returns 400 Bad Request.")

    # 3b. Host: evil.example:8765 -> 400 Bad Request
    resp_evil_port = client.get("/health", headers={"host": "evil.example:8765"})
    assert resp_evil_port.status_code == 400, f"Expected 400 for evil host with port, got {resp_evil_port.status_code}"
    print("PASS: 2b. Host header evil.example:8765 returns 400 Bad Request.")

    # 4. 올바른 Host (127.0.0.1:8765) & /health -> 200
    resp_good_host = client.get("/health", headers={"host": "127.0.0.1:8765"})
    assert resp_good_host.status_code == 200
    print("PASS: 3a. Host header 127.0.0.1:8765 returns 200.")

    # 4b. 올바른 Host (localhost:8765) & /health -> 200
    resp_localhost = client.get("/health", headers={"host": "localhost:8765"})
    assert resp_localhost.status_code == 200
    print("PASS: 3b. Host header localhost:8765 returns 200.")

    # 4c. 올바른 토큰과 올바른 Host로 /channels -> 200
    resp_auth_channel = client.get(
        "/channels",
        headers={"host": "127.0.0.1:8765", "X-Crew-Token": test_token}
    )
    assert resp_auth_channel.status_code == 200
    print("PASS: 3c. Request with valid token and host succeeds with 200.")

    # 5. 설치 모드(CREW_DEV_MODE=0)에서 /docs, /redoc, /openapi.json 비활성화 확인
    # FastAPI에서 docs_url/redoc_url/openapi_url이 None이면 라우트가 등록되지 않아 404 또는 401 반환
    resp_docs = client.get("/docs", headers={"host": "127.0.0.1:8765", "X-Crew-Token": test_token})
    assert resp_docs.status_code == 404, f"Expected 404 for /docs in packaged mode, got {resp_docs.status_code}"

    resp_openapi = client.get("/openapi.json", headers={"host": "127.0.0.1:8765", "X-Crew-Token": test_token})
    assert resp_openapi.status_code == 404, f"Expected 404 for /openapi.json in packaged mode, got {resp_openapi.status_code}"
    print("PASS: 4. /docs and /openapi.json are disabled (404) in packaged installation mode.")

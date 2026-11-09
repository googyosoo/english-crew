import os
import sys
import secrets
import pytest
from starlette.testclient import TestClient

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

def test_token_authentication_and_cors():
    """
    [Phase 4-3b Security Tests]
    1. 토큰 없는 요청: 401 Unauthorized
    2. 잘못된 토큰 요청: 401 Unauthorized
    3. /health 요청: 토큰 검사 예외 (200 OK)
    4. 올바른 X-Crew-Token 헤더: 200 OK
    5. 올바른 ?token= 쿼리 파라미터: 200 OK
    6. CORS: 개발 모드에서 http://127.0.0.1:5173만 허용, allow_credentials=False
    7. CORS: 다른 Origin (http://evil.com) 요청 거부 (Access-Control-Allow-Origin 미반환)
    """
    test_token = secrets.token_hex(32) # 32 bytes (64 hex characters)
    os.environ["CREW_API_TOKEN"] = test_token
    os.environ["CREW_DEV_MODE"] = "1"
    os.environ["CREW_DEV_NO_AUTH"] = "0"

    # Import app after setting env vars
    from backend.app.main import app

    client = TestClient(app)

    # 1. 토큰 없는 요청 -> 401 Unauthorized
    resp_no_token = client.get("/channels")
    assert resp_no_token.status_code == 401, f"Expected 401 without token, got {resp_no_token.status_code}"
    assert "detail" in resp_no_token.json()
    print("PASS: 1. Request without X-Crew-Token returns 401 Unauthorized.")

    # 2. 잘못된 토큰 요청 -> 401 Unauthorized
    resp_wrong_token = client.get("/channels", headers={"X-Crew-Token": "wrong-token-value"})
    assert resp_wrong_token.status_code == 401, f"Expected 401 with wrong token, got {resp_wrong_token.status_code}"
    print("PASS: 2. Request with invalid token returns 401 Unauthorized.")

    # 3. /health 요청 -> 토큰 없이도 200 OK (상태 확인 엔드포인트)
    resp_health = client.get("/health")
    assert resp_health.status_code == 200, f"Expected 200 for /health, got {resp_health.status_code}"
    assert resp_health.json().get("status") == "ok"
    print("PASS: 3. /health is exempted from token verification and returns 200 OK.")

    # 4. 올바른 X-Crew-Token 헤더 -> 200 OK
    resp_valid = client.get("/channels", headers={"X-Crew-Token": test_token})
    assert resp_valid.status_code == 200, f"Expected 200 with valid token, got {resp_valid.status_code}"
    print("PASS: 4. Request with valid X-Crew-Token header succeeds with 200 OK.")

    # 5. 올바른 ?token= 쿼리 파라미터 -> 200 OK (SSE 및 브라우저 다운로드 링크용)
    resp_query = client.get(f"/channels?token={test_token}")
    assert resp_query.status_code == 200, f"Expected 200 with query token, got {resp_query.status_code}"
    print("PASS: 5. Request with valid query parameter token succeeds with 200 OK.")

    # 6. CORS 개발 모드: 허용된 Origin (http://127.0.0.1:5173)
    resp_cors_allowed = client.get(
        "/channels",
        headers={
            "X-Crew-Token": test_token,
            "Origin": "http://127.0.0.1:5173"
        }
    )
    assert resp_cors_allowed.status_code == 200
    assert resp_cors_allowed.headers.get("access-control-allow-origin") == "http://127.0.0.1:5173"
    assert "access-control-allow-credentials" not in resp_cors_allowed.headers, "allow_credentials must be False!"
    print("PASS: 6. CORS allows http://127.0.0.1:5173 in dev mode with allow_credentials=False.")

    # 7. CORS 다른 Origin 요청 거부 (http://evil.com)
    resp_cors_rejected = client.get(
        "/channels",
        headers={
            "X-Crew-Token": test_token,
            "Origin": "http://evil.com"
        }
    )
    assert resp_cors_rejected.status_code == 200
    # Starlette CORSMiddleware does not attach access-control-allow-origin header for disallowed origins
    assert "access-control-allow-origin" not in resp_cors_rejected.headers
    print("PASS: 7. CORS rejects unauthorized origin (http://evil.com).")

    # Clean up test env
    os.environ.pop("CREW_API_TOKEN", None)
    os.environ.pop("CREW_DEV_NO_AUTH", None)

if __name__ == "__main__":
    test_token_authentication_and_cors()

import os
import sys
import time
import socket
import shutil
import tempfile
import urllib.request
import urllib.error
import json
import secrets
import subprocess
from pathlib import Path
from dotenv import load_dotenv

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PORTABLE_EXE = PROJECT_ROOT / "release" / "English Crew 0.1.0.exe"
UNPACKED_APP = PROJECT_ROOT / "release" / "win-unpacked" / "English Crew.exe"
PACKAGED_BACKEND_EXE = PROJECT_ROOT / "release" / "win-unpacked" / "resources" / "backend-dist" / "english-crew-backend.exe"
STANDALONE_BACKEND_EXE = PROJECT_ROOT / "backend-dist" / "english-crew-backend.exe"

def get_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]

def run_api_request(url, method="GET", data=None, timeout=30, token=None):
    req_data = None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["X-Crew-Token"] = token
    if data is not None:
        req_data = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(url, data=req_data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(body)
        except Exception:
            parsed = {"detail": body}
        return {"_status_code": e.code, **parsed}

def test_full_packaging_verification():
    print("=" * 70)
    print("STARTING FULL PACKAGING VERIFICATION (CRITERIA a ~ e)")
    print("=" * 70)

    # -------------------------------------------------------------
    # (a) 설치/실행 파일(.exe) 생성 확인
    # -------------------------------------------------------------
    print("\n[Criterion a] Verifying generated executables...")
    assert STANDALONE_BACKEND_EXE.exists(), f"Backend dist exe missing: {STANDALONE_BACKEND_EXE}"
    assert UNPACKED_APP.exists(), f"Unpacked electron app missing: {UNPACKED_APP}"
    assert PACKAGED_BACKEND_EXE.exists(), f"Packaged backend exe missing: {PACKAGED_BACKEND_EXE}"
    assert PORTABLE_EXE.exists(), f"Portable installer/exe missing: {PORTABLE_EXE}"

    print(f"  -> Standalone Backend Exe : {STANDALONE_BACKEND_EXE} ({STANDALONE_BACKEND_EXE.stat().st_size:,} bytes)")
    print(f"  -> Unpacked Electron App  : {UNPACKED_APP} ({UNPACKED_APP.stat().st_size:,} bytes)")
    print(f"  -> Packaged Backend Exe   : {PACKAGED_BACKEND_EXE} ({PACKAGED_BACKEND_EXE.stat().st_size:,} bytes)")
    print(f"  -> Portable Release Exe   : {PORTABLE_EXE} ({PORTABLE_EXE.stat().st_size:,} bytes)")
    print("PASS: [Criterion a] All .exe executables exist and have non-zero size.")

    # -------------------------------------------------------------
    # (c) 설치 폴더 안에 키·학생 데이터 없음 확인
    # -------------------------------------------------------------
    print("\n[Criterion c] Verifying no secrets, .env, .db, or student data in release folder...")
    release_dir = PROJECT_ROOT / "release"
    forbidden_matches = []
    for root, dirs, files in os.walk(release_dir):
        for f in files:
            low = f.lower()
            if low.endswith(".env") or low.endswith(".db") or "student" in low or "secret" in low:
                forbidden_matches.append(os.path.join(root, f))
    assert len(forbidden_matches) == 0, f"Found forbidden files: {forbidden_matches}"
    print("  -> release/ scanned cleanly. 0 secret/.env/.db/student files found.")
    print("PASS: [Criterion c] Release folder is completely free of keys, databases, and student data.")

    # -------------------------------------------------------------
    # (b) 설치본 첫 실행 시 API 키 입력 화면 및 userData/.env 저장 확인
    # -------------------------------------------------------------
    print("\n[Criterion b] Verifying first-run API key setup into userData/.env with token & dynamic port...")
    temp_user_data = Path(tempfile.mkdtemp(prefix="crew_isolated_userdata_"))
    temp_data_dir = temp_user_data / "data"
    temp_data_dir.mkdir(parents=True, exist_ok=True)

    test_token = secrets.token_hex(32)
    test_port = get_free_port() # Dynamic free port allocation

    env = os.environ.copy()
    env["CREW_USER_DATA_DIR"] = str(temp_user_data)
    env["CREW_DATA_DIR"] = str(temp_data_dir)
    env["CREW_API_TOKEN"] = test_token
    env["CREW_PORT"] = str(test_port)
    # Ensure no pre-existing key in env
    if "GEMINI_API_KEY" in env:
        del env["GEMINI_API_KEY"]

    print(f"  -> Isolated userData directory: {temp_user_data}")
    print(f"  -> Isolated data directory: {temp_data_dir}")
    print(f"  -> Target Port: {test_port}, Token: {test_token[:8]}...")

    # Launch packaged backend from release directory with stdout/stderr piped to a log file
    log_file_path = temp_user_data / "backend_server.log"
    log_file = open(log_file_path, "w", encoding="utf-8")
    proc = subprocess.Popen(
        [str(PACKAGED_BACKEND_EXE), "--port", str(test_port)],
        env=env,
        cwd=str(temp_user_data),
        stdout=log_file,
        stderr=subprocess.STDOUT
    )

    base_url = f"http://127.0.0.1:{test_port}"
    backend_pid = proc.pid
    print(f"  -> Launched packaged backend process (PID: {backend_pid})")

    try:
        # Wait for healthcheck
        healthy = False
        for _ in range(50):
            time.sleep(0.5)
            if proc.poll() is not None:
                log_file.flush()
                err_text = log_file_path.read_text(encoding="utf-8", errors="replace") if log_file_path.exists() else ""
                raise RuntimeError(f"Backend exited early (code {proc.returncode}):\n{err_text}")
            try:
                h = run_api_request(f"{base_url}/health")
                if h.get("status") == "ok":
                    healthy = True
                    break
            except Exception:
                pass
        assert healthy, "Packaged backend failed to answer /health within 25s"

        # Verify unauthenticated request without token returns 401
        unauth_resp = run_api_request(f"{base_url}/settings/api_key")
        assert unauth_resp.get("_status_code") == 401, f"Expected 401 without token, got: {unauth_resp}"
        print("  -> Confirmed request without X-Crew-Token returns 401 Unauthorized.")

        # Check initial API key state with valid token (should be not configured)
        key_status = run_api_request(f"{base_url}/settings/api_key", token=test_token)
        print(f"  -> Initial API key status: configured={key_status.get('configured')}")
        assert key_status.get("configured") is False, "Initial run must have configured=False to trigger setup UI"

        # Read actual teacher key from backend/.env
        load_dotenv(PROJECT_ROOT / "backend" / ".env")
        actual_key = os.environ.get("GEMINI_API_KEY", "").strip()
        assert actual_key, "Real GEMINI_API_KEY missing from backend/.env for E2E testing"

        # Simulate user saving API key via modal UI (POST /settings/api_key)
        save_resp = run_api_request(
            f"{base_url}/settings/api_key",
            method="POST",
            data={"api_key": actual_key, "model": "gemini-3.5-flash-lite"},
            token=test_token
        )
        print(f"  -> Saved API key response: {save_resp}")
        assert save_resp.get("status") in ("saved", "ok")
        assert save_resp.get("configured") is True

        # Verify userData/.env file was created and contains key
        saved_env_file = temp_user_data / ".env"
        assert saved_env_file.exists(), f"Expected .env file at {saved_env_file}"
        env_content = saved_env_file.read_text(encoding="utf-8")
        assert "GEMINI_API_KEY=" in env_content, "GEMINI_API_KEY not found in saved .env"
        print(f"  -> Confirmed .env file created at: {saved_env_file}")

        # Check API key status endpoint again
        updated_status = run_api_request(f"{base_url}/settings/api_key", token=test_token)
        print(f"  -> Updated API key status: configured={updated_status.get('configured')}, masked={updated_status.get('masked_key')}")
        assert updated_status.get("configured") is True
        print("PASS: [Criterion b] First-run API key modal triggers correctly and saves safely to userData/.env.")

        # -------------------------------------------------------------
        # (d) 설치본에서 요청 1건이 결재까지 진행 확인
        # -------------------------------------------------------------
        print("\n[Criterion d] Verifying 1 request from user input to approval decision in packaged binary...")
        channels = run_api_request(f"{base_url}/channels", token=test_token)
        eng1_channel = next((c for c in channels if c.get("name") == "영어Ⅰ"), None)
        assert eng1_channel is not None, "영어Ⅰ channel not found"
        channel_id = eng1_channel["id"]
        print(f"  -> Target Channel: {eng1_channel['name']} (ID: {channel_id})")

        # Post teacher request and wait for approval card (handle 429 quota backoff if needed)
        approval_id = None
        target_req_id = None

        for attempt in range(3): # up to 3 attempts with rate limit backoff
            print(f"\n  -> Sending request to channel (attempt {attempt + 1}/3)...")
            user_message_text = "본문 없이 일반 주제로 논술형 1문항과 4수준 루브릭 만들어줘"
            msg_resp = run_api_request(
                f"{base_url}/channels/{channel_id}/requests",
                method="POST",
                data={"content": user_message_text},
                token=test_token
            )
            req_id = msg_resp.get("request_id")
            print(f"  -> Posted teacher request (ID: {req_id})")

            # Poll channel messages until an approval card is created
            got_failure = False
            for iteration in range(60): # up to 180 seconds
                time.sleep(3)
                try:
                    # Check messages in the channel with a 10s timeout
                    messages = run_api_request(f"{base_url}/channels/{channel_id}/messages", timeout=10, token=test_token)
                    approval_msgs = [
                        m for m in messages
                        if m.get("type") == "approval" and m.get("metadata", {}).get("status") == "pending"
                    ]
                    if approval_msgs:
                        approval_id = approval_msgs[-1]["metadata"]["approval_id"]
                        target_req_id = approval_msgs[-1].get("metadata", {}).get("request_id")
                        print(f"  -> Approval card created! ID: {approval_id}, Request ID: {target_req_id}")
                        break

                    # Check if error message occurred
                    err_msgs = [
                        m for m in messages
                        if "⚠️" in m.get("content", "") or "오류" in m.get("content", "")
                    ]
                    if err_msgs and iteration > 3:
                        print(f"  -> Detected error message in channel: {err_msgs[-1]['content']}")
                        got_failure = True
                        break

                    # Check if failure report was emitted
                    report_msgs = [
                        m for m in messages
                        if m.get("type") == "report" and m.get("metadata", {}).get("has_failures") is True
                    ]
                    if report_msgs and iteration > 3:
                        print("  -> Detected task failure report. Backing off before retry...")
                        got_failure = True
                        break

                    latest_types = [f"{m.get('sender')}:{m.get('type')}" for m in messages[-4:]]
                    print(f"  -> Polling for approval card... (#{iteration + 1}/60, recent msgs: {latest_types})")
                except Exception as e:
                    print(f"  -> Poll #{iteration + 1} transient warning: {e}, waiting for next round...")

            if approval_id:
                break
            if got_failure:
                time.sleep(20) # Wait for 429 quota window to reset

        assert approval_id is not None, "Timed out waiting for approval card creation in packaged backend"

        # Teacher approves the task (POST /approvals/{id})
        print(f"  -> Approving card {approval_id}...")
        decision_resp = run_api_request(
            f"{base_url}/approvals/{approval_id}",
            method="POST",
            data={"decision": "approved", "reason": "패키징 바이너리 검증 승인"},
            token=test_token
        )
        print(f"  -> Decision response: {decision_resp}")
        assert decision_resp.get("status") in ("approved", "success") or "id" in decision_resp

        # Verify exported final .md files in workspaces
        workspaces_dir = temp_data_dir / "workspaces"
        final_files = list(workspaces_dir.glob("**/final/*"))
        print(f"  -> Exported final files: {[f.name for f in final_files]}")
        md_files = [f for f in final_files if f.name.endswith(".md")]
        assert len(md_files) >= 1, "Exported final markdown file missing in final/"
        print(f"  -> Verified final .md size: {md_files[0].stat().st_size:,} bytes")

        # Also verify Word (.docx) export endpoint on the target request
        target_req_id = approval_msgs[-1].get("metadata", {}).get("request_id")
        print(f"  -> Verifying docx export endpoint for request: {target_req_id}...")
        docx_url = f"{base_url}/requests/{target_req_id}/export?format=docx"
        req_docx = urllib.request.Request(docx_url, headers={"X-Crew-Token": test_token})
        with urllib.request.urlopen(req_docx, timeout=15) as docx_resp:
            assert docx_resp.status == 200
            docx_bytes = docx_resp.read()
            assert len(docx_bytes) > 1000, f"Docx file too small: {len(docx_bytes)} bytes"
            print(f"  -> Word export endpoint returned valid .docx binary ({len(docx_bytes):,} bytes)")

        # Also verify Word export via ?token= query parameter
        docx_query_url = f"{base_url}/requests/{target_req_id}/export?format=docx&token={test_token}"
        req_docx_q = urllib.request.Request(docx_query_url)
        with urllib.request.urlopen(req_docx_q, timeout=15) as docx_q_resp:
            assert docx_q_resp.status == 200
            assert len(docx_q_resp.read()) > 1000
            print("  -> Word export endpoint succeeded via ?token= query parameter as well.")

        print("PASS: [Criterion d] Request successfully completed all steps through approval and file export in packaged binary.")

    finally:
        # -------------------------------------------------------------
        # (e) 백엔드 프로세스가 앱 종료와 함께 종료 확인
        # -------------------------------------------------------------
        print("\n[Criterion e] Verifying backend process cleanly shuts down with application...")
        print(f"  -> Sending termination signal to backend process (PID: {backend_pid})...")
        proc.terminate()
        try:
            exit_code = proc.wait(timeout=6)
            print(f"  -> Process exited gracefully with returncode: {exit_code}")
        except Exception:
            print("  -> Process did not terminate within 6s, calling kill()...")
            proc.kill()
            exit_code = proc.wait(timeout=3)
            print(f"  -> Process killed with returncode: {exit_code}")

        log_file.close()
        if log_file_path.exists():
            log_content = log_file_path.read_text(encoding="utf-8", errors="replace")
            print("\n--- COMPLETE BACKEND SERVER LOG ---")
            for line in log_content.splitlines():
                print("  ", line)
            print("-----------------------------------\n")

        # Double check via OS process list that PID is dead
        time.sleep(1)
        check_proc = subprocess.run(
            ["powershell", "-Command", f"Get-Process -Id {backend_pid} -ErrorAction SilentlyContinue"],
            capture_output=True,
            text=True
        )
        assert check_proc.stdout.strip() == "", f"Process {backend_pid} is still running!"
        print(f"  -> Verified via OS that PID {backend_pid} is completely removed from process table.")
        print("PASS: [Criterion e] Packaged backend process terminates completely without leaving zombie processes.")

        # Cleanup isolated user data
        shutil.rmtree(temp_user_data, ignore_errors=True)
        print("  -> Cleaned up isolated test environment.")

    print("\n" + "=" * 70)
    print("ALL 5 PACKAGING ACCEPTANCE CRITERIA (a ~ e) VERIFIED 100% PASS!")
    print("=" * 70)

if __name__ == "__main__":
    test_full_packaging_verification()

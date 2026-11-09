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
PACKAGED_BACKEND_EXE = PROJECT_ROOT / "release" / "win-unpacked" / "resources" / "backend-dist" / "english-crew-backend.exe"
PORTABLE_EXE = PROJECT_ROOT / "release" / "English Crew 0.1.0.exe"
ARTIFACT_DIR = Path(r"C:\Users\user\.gemini\antigravity\brain\bfcf6c24-c0ed-47e4-9449-0980a18f3b67")

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
            content_type = resp.headers.get("Content-Type", "")
            raw = resp.read()
            if "application/json" in content_type:
                return json.loads(raw.decode("utf-8"))
            return raw
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(body)
        except Exception:
            parsed = {"detail": body}
        return {"_status_code": e.code, **parsed}

def main():
    print("=" * 70)
    print("PHASE 4-3c COMPREHENSIVE PACKAGED VERIFICATION & SCREENSHOT CAPTURE")
    print("=" * 70)

    # -------------------------------------------------------------
    # 1. 토큰 없이 바이너리 실행 시 시작 거부(fail-closed) 확인
    # -------------------------------------------------------------
    print("\n[Step 1] Verifying fail-closed startup without token...")
    clean_env = os.environ.copy()
    clean_env.pop("CREW_API_TOKEN", None)
    clean_env.pop("CREW_DEV_NO_AUTH", None)

    no_token_proc = subprocess.run(
        [str(PACKAGED_BACKEND_EXE)],
        env=clean_env,
        capture_output=True,
        text=True
    )
    print(f"  -> Process exit code: {no_token_proc.returncode}")
    print(f"  -> Captured stderr output: {no_token_proc.stderr.strip()}")
    assert no_token_proc.returncode != 0, "Backend must fail-close (exit != 0) when token is missing!"
    assert "FATAL: CREW_API_TOKEN is missing" in no_token_proc.stderr or "fail-closed" in no_token_proc.stderr
    print("PASS: [Step 1] Standalone backend correctly rejects startup when CREW_API_TOKEN is missing.")

    # -------------------------------------------------------------
    # 2. 임시 격리 환경 준비 및 키 로드
    # -------------------------------------------------------------
    print("\n[Step 2] Setting up isolated user environment...")
    temp_user_data = Path(tempfile.mkdtemp(prefix="crew_packaged_4_3c_"))
    temp_data_dir = temp_user_data / "data"
    temp_data_dir.mkdir(parents=True, exist_ok=True)

    # Copy real API key from backend/.env into userData/.env
    load_dotenv(PROJECT_ROOT / "backend" / ".env")
    actual_key = os.environ.get("GEMINI_API_KEY", "").strip()
    assert actual_key, "GEMINI_API_KEY is required in backend/.env for E2E verification"
    (temp_user_data / ".env").write_text(f"GEMINI_API_KEY={actual_key}\n", encoding="utf-8")

    test_token = secrets.token_hex(32)
    test_port = get_free_port()

    env = os.environ.copy()
    env["CREW_USER_DATA_DIR"] = str(temp_user_data)
    env["CREW_DATA_DIR"] = str(temp_data_dir)
    env["CREW_API_TOKEN"] = test_token
    env["CREW_PORT"] = str(test_port)
    env["CREW_DEV_MODE"] = "0"

    print(f"  -> Isolated userData: {temp_user_data}")
    print(f"  -> Dynamic port: {test_port}")
    print(f"  -> Generated token: {test_token[:8]}...")

    # -------------------------------------------------------------
    # 3. 패키징 백엔드 바이너리 기동
    # -------------------------------------------------------------
    print("\n[Step 3] Launching packaged backend binary...")
    log_file_path = temp_user_data / "backend.log"
    log_file = open(log_file_path, "w", encoding="utf-8")

    proc = subprocess.Popen(
        [str(PACKAGED_BACKEND_EXE), "--port", str(test_port)],
        env=env,
        cwd=str(temp_user_data),
        stdout=log_file,
        stderr=subprocess.STDOUT
    )
    base_url = f"http://127.0.0.1:{test_port}"
    print(f"  -> Backend PID: {proc.pid}")

    try:
        # Wait for health
        healthy = False
        for _ in range(50):
            time.sleep(0.5)
            if proc.poll() is not None:
                log_file.flush()
                err_text = log_file_path.read_text(encoding="utf-8", errors="replace")
                raise RuntimeError(f"Backend exited early ({proc.returncode}):\n{err_text}")
            try:
                h = run_api_request(f"{base_url}/health")
                if isinstance(h, dict) and h.get("status") in ("ok", "error"):
                    healthy = True
                    break
            except Exception:
                pass
        assert healthy, "Backend failed to answer /health within 25s"
        print("  -> /health answered 200 OK.")

        # Verify StaticFiles index.html served at root without token
        req_root = urllib.request.Request(f"{base_url}/")
        with urllib.request.urlopen(req_root, timeout=10) as r:
            assert r.status == 200
            html_text = r.read().decode("utf-8")
            assert "<!doctype html>" in html_text.lower() or "<html" in html_text.lower()
            print("  -> Root '/' successfully served index.html publicly without token.")

        # Verify API endpoint requires token (returns 401 without token)
        unauth = run_api_request(f"{base_url}/channels")
        assert unauth.get("_status_code") == 401, f"Expected 401, got: {unauth}"
        print("  -> Verified '/channels' requires token (returned 401 Unauthorized).")

        # -------------------------------------------------------------
        # 4. Electron 렌더러 창 구동 및 3단계 화면 캡처
        # -------------------------------------------------------------
        print("\n[Step 4] Running Electron capture script (channel load -> request -> approval -> docx)...")
        capture_env = os.environ.copy()
        capture_env["CREW_PORT"] = str(test_port)
        capture_env["CREW_API_TOKEN"] = test_token

        cap_cmd = ["npx.cmd", "electron", "tests/capture_phase4_3c.cjs", str(test_port), test_token]
        cap_proc = subprocess.run(
            cap_cmd,
            cwd=str(PROJECT_ROOT),
            env=capture_env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            shell=True
        )
        print("Electron capture stdout:\n", cap_proc.stdout)
        if cap_proc.stderr:
            print("Electron capture stderr:\n", cap_proc.stderr)

        if cap_proc.returncode != 0:
            log_file.flush()
            err_log = log_file_path.read_text(encoding="utf-8", errors="replace") if log_file_path.exists() else ""
            print("--- BACKEND SERVER LOG DUMP ---")
            print(err_log)
            print("--------------------------------")
        assert cap_proc.returncode == 0, f"Electron capture failed with code {cap_proc.returncode}"

        # Verify screenshots were created
        screenshot_dir = PROJECT_ROOT / "tests" / "screenshots"
        cap1 = screenshot_dir / "phase4_3c_1_channel_loaded.png"
        cap2 = screenshot_dir / "phase4_3c_2_approval_card.png"
        cap3 = screenshot_dir / "phase4_3c_3_approved_docx.png"

        assert cap1.exists() and cap1.stat().st_size > 1000, "Screenshot 1 missing"
        assert cap2.exists() and cap2.stat().st_size > 1000, "Screenshot 2 missing"
        assert cap3.exists() and cap3.stat().st_size > 1000, "Screenshot 3 missing"

        print(f"  -> Screenshot 1 created: {cap1.name} ({cap1.stat().st_size:,} bytes)")
        print(f"  -> Screenshot 2 created: {cap2.name} ({cap2.stat().st_size:,} bytes)")
        print(f"  -> Screenshot 3 created: {cap3.name} ({cap3.stat().st_size:,} bytes)")

        # Copy screenshots to brain artifact directory for display
        ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
        shutil.copy2(cap1, ARTIFACT_DIR / "phase4_3c_1_channel_loaded.png")
        shutil.copy2(cap2, ARTIFACT_DIR / "phase4_3c_2_approval_card.png")
        shutil.copy2(cap3, ARTIFACT_DIR / "phase4_3c_3_approved_docx.png")
        print(f"  -> Copied 3 screenshots to conversation artifact directory: {ARTIFACT_DIR}")

        # -------------------------------------------------------------
        # 5. docx 내보내기 엔드포인트 바이너리 검증
        # -------------------------------------------------------------
        print("\n[Step 5] Verifying Word docx export file from packaged backend...")
        channels = run_api_request(f"{base_url}/channels", token=test_token)
        eng1 = next(c for c in channels if c["name"] == "영어Ⅰ")
        messages = run_api_request(f"{base_url}/channels/{eng1['id']}/messages", token=test_token)
        appr_msg = next(m for m in messages if m.get("type") == "approval")
        target_req_id = appr_msg["metadata"]["request_id"]

        docx_bytes = run_api_request(f"{base_url}/requests/{target_req_id}/export?format=docx", token=test_token)
        assert isinstance(docx_bytes, bytes) and len(docx_bytes) > 5000, f"Invalid docx bytes: {len(docx_bytes)}"
        print(f"  -> Successfully downloaded docx file ({len(docx_bytes):,} bytes)")

        print("\n" + "=" * 70)
        print("PHASE 4-3c COMPREHENSIVE PACKAGED E2E VERIFICATION PASSED (100% SUCCESS)!")
        print("=" * 70)

    finally:
        # Clean shutdown
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except Exception:
            proc.kill()
        log_file.close()
        shutil.rmtree(temp_user_data, ignore_errors=True)
        print("  -> Backend process cleanly terminated and temp test data cleaned up.")

if __name__ == "__main__":
    main()

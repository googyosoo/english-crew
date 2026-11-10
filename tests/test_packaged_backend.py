import os
import sys
import time
import socket
import secrets
import shutil
import tempfile
import urllib.request
import json
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
EXE_PATH = PROJECT_ROOT / "backend-dist" / "english-crew-backend.exe"

def get_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]

def test_packaged_binary():
    print(f"Testing packaged binary at: {EXE_PATH}")
    assert EXE_PATH.exists(), f"Packaged binary not found at {EXE_PATH}"

    temp_test_user_data = tempfile.mkdtemp(prefix="crew_test_pkg_")
    data_dir = Path(temp_test_user_data) / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    test_token = secrets.token_hex(32)
    test_port = get_free_port()

    # Pass a clean, isolated environment to child process (no parent pollution)
    clean_env = os.environ.copy()
    clean_env.pop("CREW_DEV_NO_AUTH", None)
    clean_env["CREW_USER_DATA_DIR"] = temp_test_user_data
    clean_env["CREW_DATA_DIR"] = str(data_dir)
    clean_env["CREW_API_TOKEN"] = test_token
    clean_env["CREW_PORT"] = str(test_port)
    clean_env["CREW_DEV_MODE"] = "0"
    clean_env["GEMINI_API_KEY"] = "AIzaSyTestKeyForPackagedBinaryVerification12345"

    proc = None
    try:
        print(f"Launching packaged backend process on port {test_port}...")
        proc = subprocess.Popen(
            [str(EXE_PATH), "--port", str(test_port)],
            env=clean_env,
            cwd=temp_test_user_data,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        base_url = f"http://127.0.0.1:{test_port}"

        # Wait up to 25 seconds for startup
        health_data = None
        for i in range(50):
            time.sleep(0.5)
            # Check if process died early
            if proc.poll() is not None:
                out, err = proc.communicate()
                print("Packaged backend process died early!")
                print("STDOUT:", out.decode('utf-8', errors='replace'))
                print("STDERR:", err.decode('utf-8', errors='replace'))
                raise RuntimeError(f"Packaged process exited early with code {proc.returncode}")

            try:
                req = urllib.request.Request(f"{base_url}/health")
                with urllib.request.urlopen(req, timeout=2) as resp:
                    if resp.status == 200:
                        health_data = json.loads(resp.read().decode("utf-8"))
                        break
            except Exception:
                pass

        assert health_data is not None, "Packaged backend failed to respond to /health within 15 seconds!"
        print("PASS: Packaged backend responded to /health successfully!")
        print("  -> Health Response:", health_data)
        assert health_data.get("status") == "ok"
        assert health_data.get("gemini") == "configured"

        # Verify channels endpoint with token
        headers = {"X-Crew-Token": test_token}
        req_ch = urllib.request.Request(f"{base_url}/channels", headers=headers)
        with urllib.request.urlopen(req_ch, timeout=2) as resp:
            channels_data = json.loads(resp.read().decode("utf-8"))
            assert len(channels_data) == 8, f"Expected 8 official channels, got {len(channels_data)}"
            print("PASS: Packaged backend returned 8 official channels from embedded DB!")

        # Verify API key status endpoint with token
        req_key = urllib.request.Request(f"{base_url}/settings/api_key", headers=headers)
        with urllib.request.urlopen(req_key, timeout=2) as resp:
            key_data = json.loads(resp.read().decode("utf-8"))
            assert key_data.get("configured") is True
            print("PASS: API Key status endpoint verified in packaged binary!")

    finally:
        if proc:
            print(f"Terminating packaged backend process (PID: {proc.pid})...")
            # Force kill process tree including child processes
            subprocess.run(f"taskkill /PID {proc.pid} /T /F", shell=True, capture_output=True)
            try:
                proc.wait(timeout=5)
            except Exception:
                pass
        shutil.rmtree(temp_test_user_data, ignore_errors=True)
        print("PASS: Cleaned up temporary test user data.")

        # Verify 0 remaining english-crew-backend.exe processes
        proc_check = subprocess.run(
            ["powershell", "-Command", "Get-Process english-crew-backend -ErrorAction SilentlyContinue"],
            capture_output=True,
            text=True
        )
        assert proc_check.stdout.strip() == "", f"Remaining english-crew-backend processes found:\n{proc_check.stdout}"
        print("PASS: Verified 0 remaining english-crew-backend processes.")

if __name__ == "__main__":
    test_packaged_binary()
    print("\n=======================================================")
    print("PACKAGED BINARY INTEGRATION TEST PASSED 100%!")
    print("=======================================================")

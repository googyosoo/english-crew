import os
import sys
import time
import shutil
import tempfile
import urllib.request
import json
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
EXE_PATH = PROJECT_ROOT / "backend-dist" / "english-crew-backend.exe"

def test_packaged_binary():
    print(f"Testing packaged binary at: {EXE_PATH}")
    assert EXE_PATH.exists(), f"Packaged binary not found at {EXE_PATH}"

    temp_test_user_data = tempfile.mkdtemp(prefix="crew_test_pkg_")
    data_dir = Path(temp_test_user_data) / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    env["CREW_USER_DATA_DIR"] = temp_test_user_data
    env["CREW_DATA_DIR"] = str(data_dir)
    env["GEMINI_API_KEY"] = "AIzaSyTestKeyForPackagedBinaryVerification12345"

    proc = None
    try:
        print("Launching packaged backend process...")
        proc = subprocess.Popen(
            [str(EXE_PATH)],
            env=env,
            cwd=temp_test_user_data,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

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
                req = urllib.request.Request("http://127.0.0.1:8765/health")
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

        # Verify channels endpoint
        req_ch = urllib.request.Request("http://127.0.0.1:8765/channels")
        with urllib.request.urlopen(req_ch, timeout=2) as resp:
            channels_data = json.loads(resp.read().decode("utf-8"))
            assert len(channels_data) == 8, f"Expected 8 official channels, got {len(channels_data)}"
            print("PASS: Packaged backend returned 8 official channels from embedded DB!")

        # Verify API key status endpoint
        req_key = urllib.request.Request("http://127.0.0.1:8765/settings/api_key")
        with urllib.request.urlopen(req_key, timeout=2) as resp:
            key_data = json.loads(resp.read().decode("utf-8"))
            assert key_data.get("configured") is True
            print("PASS: API Key status endpoint verified in packaged binary!")

    finally:
        if proc:
            print("Terminating packaged backend process...")
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except Exception:
                proc.kill()
        shutil.rmtree(temp_test_user_data, ignore_errors=True)
        print("PASS: Cleaned up temporary test user data.")

if __name__ == "__main__":
    test_packaged_binary()
    print("\n=======================================================")
    print("PACKAGED BINARY INTEGRATION TEST PASSED 100%!")
    print("=======================================================")

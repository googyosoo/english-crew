import asyncio
import json
import os
import sys
import time
import subprocess
import urllib.request
import urllib.parse
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.services.checks.curriculum_check import check_curriculum
from backend.app.services.checks.rubric_check import check_rubric

BASE_URL = "http://127.0.0.1:8765"
E2E_DATA_DIR = PROJECT_ROOT / "tests" / "e2e_data"

async def run_e2e():
    print("====================================================================")
    print("=== [Phase 3 No-Body Real E2E with CREW_DATA_DIR=tests/e2e_data] ===")
    print("====================================================================")

    # Clean up existing tests/e2e_data
    if E2E_DATA_DIR.exists():
        import shutil
        shutil.rmtree(E2E_DATA_DIR, ignore_errors=True)
    E2E_DATA_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Isolated data directory initialized: {E2E_DATA_DIR}")

    # Launch backend with CREW_DATA_DIR=tests/e2e_data
    env = os.environ.copy()
    env["CREW_DATA_DIR"] = str(E2E_DATA_DIR)
    env["PYTHONIOENCODING"] = "utf-8"

    python_exe = PROJECT_ROOT / "backend" / ".venv" / "Scripts" / "python.exe"
    backend_proc = subprocess.Popen(
        [str(python_exe), "-m", "uvicorn", "backend.app.main:app", "--host", "127.0.0.1", "--port", "8765"],
        cwd=str(PROJECT_ROOT),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace"
    )

    try:
        # Wait for backend health
        print("Waiting for backend server to become healthy...")
        healthy = False
        for _ in range(30):
            try:
                with urllib.request.urlopen(f"{BASE_URL}/health", timeout=1) as resp:
                    if resp.status == 200:
                        healthy = True
                        break
            except Exception:
                await asyncio.sleep(0.5)

        if not healthy:
            print("[FAIL] Backend failed to start.")
            return

        print("Backend is healthy on http://127.0.0.1:8765")

        # Verify channels
        with urllib.request.urlopen(f"{BASE_URL}/channels") as resp:
            channels = json.loads(resp.read().decode("utf-8"))
            eng1_ch = next((c for c in channels if c["id"] == "eng1"), None)
            print(f"Target Channel: {eng1_ch}")

        # Send Teacher Request
        teacher_prompt = "본문 없이 일반 주제로 논술형 1문항과 4수준 루브릭 만들어줘"
        print(f"\n[Step 1] Sending Teacher Request to eng1 channel: '{teacher_prompt}'")
        req_data = json.dumps({"content": teacher_prompt}).encode("utf-8")
        req = urllib.request.Request(
            f"{BASE_URL}/channels/eng1/requests",
            data=req_data,
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req) as resp:
            res = json.loads(resp.read().decode("utf-8"))
            request_id = res["request_id"]
            print(f"Request created successfully! request_id: {request_id}")

        # Listen to SSE stream
        print(f"\n[Step 2] Listening to SSE events for request: {request_id}")
        stream_req = urllib.request.Request(f"{BASE_URL}/requests/{request_id}/events")
        approval_id = None
        task_events = []
        task_outputs = {}
        check_infos = {}

        with urllib.request.urlopen(stream_req) as sse_stream:
            for line in sse_stream:
                line_str = line.decode("utf-8").strip()
                if line_str.startswith("data:"):
                    event_data = json.loads(line_str[5:].strip())
                    event_type = event_data.get("type")
                    event_body = event_data.get("data")
                    now_str = time.strftime("%H:%M:%S")
                    print(f"[{now_str}] Event [{event_type}]: {event_body}")

                    if event_type == "task_update":
                        task_events.append(event_body)
                        t_status = event_body.get("status")
                        t_id = event_body.get("task_id")
                        c_info = event_body.get("check_info")
                        if c_info:
                            check_infos[t_id] = c_info
                        out_path = event_body.get("output_path")
                        if t_status == "done" and out_path:
                            p = Path(out_path)
                            if p.exists():
                                task_outputs[t_id] = p.read_text(encoding="utf-8")

                    elif event_type == "completed":
                        approval_id = event_body.get("approval_id")
                        print(f"\n[SUCCESS] Pipeline completed! approval_id: {approval_id}")
                        break
                    elif event_type == "error":
                        print(f"\n[ERROR] Pipeline failed: {event_body}")
                        break

        # Verification of sequential execution: curriculum -> assessment
        print("\n====================================================================")
        print("=== [Step 3] Verifying Bot Execution Sequence (curriculum -> assessment) ===")
        print("====================================================================")
        for idx, ev in enumerate(task_events):
            print(f"Event {idx + 1}: Task={ev.get('task_id')}, Status={ev.get('status')}")

        # Check approval
        if not approval_id:
            print("[FAIL] No approval_id received. E2E halted.")
            return

        # Approve request
        print(f"\n[Step 4] Approving request via POST /approvals/{approval_id}")
        appr_payload = json.dumps({"decision": "approved"}).encode("utf-8")
        appr_req = urllib.request.Request(
            f"{BASE_URL}/approvals/{approval_id}",
            data=appr_payload,
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(appr_req) as resp:
            appr_res = json.loads(resp.read().decode("utf-8"))
            print("Approval response:", appr_res)

        # Output Deliverables & Comprehensive Checks
        print("\n====================================================================")
        print("=== [Step 5] Detailed Deliverables & Inspection Results ===")
        print("====================================================================")
        for t_id, content in task_outputs.items():
            print(f"\n####################################################################")
            print(f"### [DELIVERABLE FOR TASK: {t_id}]")
            print(f"####################################################################")
            print(content)
            print("\n--------------------------------------------------------------------")
            
            # Curriculum check
            cur_res = check_curriculum(content)
            print(f"[Curriculum Check for {t_id}]:")
            print(f"  Passed: {cur_res.passed}")
            print(f"  Found Codes: {cur_res.found_codes}")
            print(f"  Issues: {cur_res.issues}")

            # Rubric check
            rub_res = check_rubric(content)
            print(f"[Rubric Check for {t_id}]:")
            print(f"  Passed: {rub_res.passed}")
            print(f"  Issues: {rub_res.issues}")

            # Check for retry history in check_infos
            if t_id in check_infos:
                ci = check_infos[t_id]
                if ci.get("retry_occurred"):
                    print("\n>>> [1-Time Automatic Retry Occurred! Showing 1st vs 2nd Attempt] <<<")
                    print("\n--- [1st Attempt Output] ---")
                    print(ci.get("first_attempt_output", ""))
                    print("\n--- [1st Attempt Check Result] ---")
                    print(ci.get("first_attempt_check", ""))

            # Check '본문 미제공' header
            first_lines = [line.strip() for line in content.splitlines() if line.strip()][:3]
            has_no_body_header = any("본문 미제공" in line for line in first_lines)
            print(f"\n['본문 미제공' Header in First 3 Lines]: {has_no_body_header}")
            if first_lines:
                print(f"  First non-empty line: '{first_lines[0]}'")

        print("\n=== Phase 3 No-Body E2E Run Complete ===")

    finally:
        print("\nStopping backend process...")
        backend_proc.terminate()
        try:
            backend_proc.wait(timeout=5)
        except Exception:
            backend_proc.kill()
        print("Backend stopped cleanly.")

if __name__ == "__main__":
    asyncio.run(run_e2e())

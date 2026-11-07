import asyncio
import json
import os
import sys
import urllib.request
import urllib.parse
import subprocess
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.services.checks.curriculum_check import check_curriculum
from backend.app.services.checks.rubric_check import check_rubric

BASE_URL = "http://127.0.0.1:8765"
FIXTURE_PATH = PROJECT_ROOT / "tests" / "fixtures" / "eng1_unit3.txt"

async def run_phase3_e2e():
    print("=== [Phase 3 Real E2E with CREW_DATA_DIR=tests/e2e_data] ===")
    
    # Check guard condition: 본문 파일이 없으면 진행하지 말 것
    if not FIXTURE_PATH.exists():
        print(f"[STOP] 본문 파일이 없습니다: {FIXTURE_PATH}")
        print("지침에 따라 tests/fixtures/eng1_unit3.txt 파일이 제공될 때까지 E2E를 진행하지 않고 대기합니다.")
        return

    textbook_content = FIXTURE_PATH.read_text(encoding="utf-8").strip()
    print(f"Loaded textbook content from fixture ({len(textbook_content)} chars)")

    print("\n=== [1/6] Registering English I Unit 3 Textbook Body into [수업 맥락] ===")
    body_payload = {
        "course_code": "ENG1",
        "unit": "3과",
        "kind": "본문",
        "content": textbook_content
    }
    req = urllib.request.Request(
        f"{BASE_URL}/channels/eng1/context",
        data=json.dumps(body_payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as resp:
        res = json.loads(resp.read().decode("utf-8"))
        print("Textbook body saved successfully:", res)

    print("\n=== [2/6] Sending Teacher Request: '3과 본문으로 논술형 1문항과 4수준 루브릭 만들어줘' ===")
    teacher_req = {"content": "3과 본문으로 논술형 1문항과 4수준 루브릭 만들어줘"}
    req2 = urllib.request.Request(
        f"{BASE_URL}/channels/eng1/requests",
        data=json.dumps(teacher_req).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req2) as resp:
        res2 = json.loads(resp.read().decode("utf-8"))
        request_id = res2["request_id"]
        print(f"Request created: {request_id}")

    print(f"\n=== [3/6] Listening to SSE events and verifying CurriculumBot -> AssessmentBot order ===")
    stream_req = urllib.request.Request(f"{BASE_URL}/requests/{request_id}/events")
    approval_id = None
    task_outputs = {}

    with urllib.request.urlopen(stream_req) as sse_stream:
        for line in sse_stream:
            line_str = line.decode("utf-8").strip()
            if line_str.startswith("data:"):
                event_data = json.loads(line_str[5:].strip())
                event_type = event_data.get("type")
                event_body = event_data.get("data")
                print(f" -> Event [{event_type}]:", event_body)

                if event_type == "task_update":
                    t_status = event_body.get("status")
                    t_id = event_body.get("task_id")
                    out_path = event_body.get("output_path")
                    if t_status == "done" and out_path:
                        p = Path(out_path)
                        if p.exists():
                            task_outputs[t_id] = p.read_text(encoding="utf-8")

                elif event_type == "completed":
                    approval_id = event_body.get("approval_id")
                    print("\n[SUCCESS] Pipeline completed! approval_id:", approval_id)
                    break
                elif event_type == "error":
                    print("\n[ERROR] Pipeline encountered error:", event_body)
                    break

    if not approval_id:
        print("[FAIL] approval_id not received. Stopping.")
        return

    print("\n=== [4/6] Capturing Pre-approval Screenshot (phase3_real_initial.png) ===")
    subprocess.run(["npx.cmd", "electron", "tests/capture_phase3_screens.cjs", "initial"], check=True)

    print(f"\n=== [5/6] Approving request via POST /approvals/{approval_id} ===")
    appr_payload = {"decision": "approved"}
    req3 = urllib.request.Request(
        f"{BASE_URL}/approvals/{approval_id}",
        data=json.dumps(appr_payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req3) as resp:
        appr_res = json.loads(resp.read().decode("utf-8"))
        print("Approval response:", appr_res)

    print("\n=== [6/6] Capturing Post-approval Screenshot (phase3_real_approved.png) ===")
    subprocess.run(["npx.cmd", "electron", "tests/capture_phase3_screens.cjs", "approved"], check=True)

    print("\n=== [OUTPUT DELIVERABLES & CHECKS] ===")
    for t_id, text in task_outputs.items():
        print(f"\n--- [Task Output: {t_id}] ---")
        print(text)
        print("\n[Curriculum Check Result]")
        cur_res = check_curriculum(text)
        print(cur_res.to_dict())
        print("\n[Rubric Check Result]")
        rub_res = check_rubric(text)
        print(rub_res.to_dict())

if __name__ == "__main__":
    asyncio.run(run_phase3_e2e())

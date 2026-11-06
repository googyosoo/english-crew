import asyncio
import os
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.db.database import init_db, get_db_connection, DB_PATH
from backend.app.services.workspace_manager import WORKSPACE_DIR, get_workspace_dir, save_task_deliverable, copy_to_final
from backend.app.models.schemas import DispatchPlan, TaskSpec

def test_health_endpoint():
    client = TestClient(app)
    res = client.get("/health")
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    data = res.json()
    assert data["status"] == "ok"
    assert data["gemini"] in ["configured", "missing_key"]
    assert "model" in data
    print("PASS: /health endpoint verification passed:", data)

def test_channels_and_bots_seeding():
    client = TestClient(app)
    res_ch = client.get("/channels")
    assert res_ch.status_code == 200
    channels = res_ch.json()
    assert len(channels) == 5
    eng1 = next((c for c in channels if c["id"] == "eng1"), None)
    assert eng1 is not None
    assert "workspace_dir" in eng1
    assert eng1["workspace_dir"] == "data/workspaces/영어I/1과"
    print("PASS: /channels seed and workspace_dir verification passed")

    res_bots = client.get("/bots")
    assert res_bots.status_code == 200
    bots = res_bots.json()
    assert len(bots) == 5
    active_bots = [b for b in bots if b["enabled"]]
    inactive_bots = [b for b in bots if not b["enabled"]]
    assert len(active_bots) == 2, f"Expected 2 active bots, got {len(active_bots)}"
    assert {b["id"] for b in active_bots} == {"coordinator", "assessment"}
    assert {b["id"] for b in inactive_bots} == {"curriculum", "lesson", "record"}
    print("PASS: /bots active bots (coordinator, assessment) verification passed")

def test_workspace_manager_and_final_copy():
    # 1. Directory creation
    rel_path, abs_path = get_workspace_dir("course", "영어I", "3과")
    assert rel_path == "data/workspaces/영어I/3과"
    assert abs_path.exists()

    # 2. Save deliverable
    dummy_task_id = "test_task_123"
    dummy_content = "# 영어I 3과 수행평가 루브릭\n\n- 상: 문법적 오류 없이 유창하게 표현함\n- 중: 의미 전달은 되나 일부 오류 있음\n- 하: 기본 어휘 위주로 단편적 서술함\n"
    saved_rel = save_task_deliverable(abs_path, dummy_task_id, dummy_content)
    assert Path(WORKSPACE_DIR / saved_rel).exists()
    assert (abs_path / f"{dummy_task_id}.md").read_text(encoding="utf-8") == dummy_content
    print("PASS: Deliverable saved at:", saved_rel)

    # 3. Copy to final/
    final_rel = copy_to_final(abs_path, dummy_task_id)
    assert final_rel == f"data/workspaces/영어I/3과/final/{dummy_task_id}.md"
    assert Path(WORKSPACE_DIR / final_rel).exists()
    assert (abs_path / "final" / f"{dummy_task_id}.md").read_text(encoding="utf-8") == dummy_content
    print("PASS: Final copy created at:", final_rel)

    # Clean up test task files
    (abs_path / f"{dummy_task_id}.md").unlink(missing_ok=True)
    (abs_path / "final" / f"{dummy_task_id}.md").unlink(missing_ok=True)

def test_dispatch_plan_schema_validation():
    # Verify DispatchPlan strict schema
    plan_dict = {
        "summary": "영어I 3과 수행평가 문항 및 루브릭 제작",
        "unit": "3과",
        "tasks": [
            {
                "bot": "assessment",
                "title": "3과 서술형 수행평가 문항 출제",
                "deliverable": "서술형 2문항 및 모범 답안"
            },
            {
                "bot": "assessment",
                "title": "채점 기준표(루브릭) 작성",
                "deliverable": "4단계 분석적 루브릭 표"
            }
        ],
        "approval_question": "영어I 3과 서술형 문항과 채점 기준표를 최종 확정하시겠습니까?"
    }
    plan = DispatchPlan.model_validate(plan_dict)
    assert plan.summary == plan_dict["summary"]
    assert len(plan.tasks) == 2
    assert plan.tasks[0].bot == "assessment"
    print("PASS: DispatchPlan Pydantic model validation passed")

def test_approval_approved_and_rejected_flows():
    client = TestClient(app)

    async def setup_test_db():
        async with get_db_connection() as db:
            # Create a mock request, task, and approval
            await db.execute(
                "INSERT OR REPLACE INTO channels (id, name, type, course_code) VALUES ('eng1', '영어I', 'course', 'ENG1')"
            )
            await db.execute(
                "INSERT OR REPLACE INTO messages (id, channel_id, sender, type, content, metadata_json) VALUES ('msg_test_req', 'eng1', 'teacher', 'text', '영어I 3과 수행평가 설계', '{\"request_id\": \"req_test_1\"}')"
            )
            # Create task deliverable on disk
            _, abs_dir = get_workspace_dir("course", "영어I", "3과")
            saved_path = save_task_deliverable(abs_dir, "tsk_test_1", "# 3과 수행평가\n내용입니다.")

            await db.execute(
                "INSERT OR REPLACE INTO tasks (id, request_id, bot_id, title, deliverable, status, output_path) VALUES ('tsk_test_1', 'req_test_1', 'assessment', '문항 출제', '2문항', 'done', ?)",
                (saved_path,)
            )
            await db.execute(
                "INSERT OR REPLACE INTO approvals (id, request_id, question, status) VALUES ('appr_test_1', 'req_test_1', '확정하시겠습니까?', 'pending')"
            )
            await db.execute(
                "INSERT OR REPLACE INTO messages (id, channel_id, sender, type, content, metadata_json) VALUES ('msg_appr_1', 'eng1', 'coordinator', 'approval', '확정하시겠습니까?', '{\"approval_id\": \"appr_test_1\", \"status\": \"pending\"}')"
            )
            await db.commit()

    asyncio.run(setup_test_db())

    # 1. Test Approval (Approved)
    res_appr = client.post("/approvals/appr_test_1", json={"decision": "approved"})
    assert res_appr.status_code == 200
    appr_data = res_appr.json()
    assert appr_data["status"] == "approved"
    assert len(appr_data["final_files"]) > 0
    final_file = appr_data["final_files"][0]
    assert "final/tsk_test_1.md" in final_file
    assert Path(WORKSPACE_DIR / final_file).exists()
    print("PASS: Approval 'approved' copied to final/ successfully:", final_file)

    # 2. Test Approval (Rejected with reason)
    async def setup_reject_db():
        async with get_db_connection() as db:
            await db.execute(
                "INSERT OR REPLACE INTO approvals (id, request_id, question, status) VALUES ('appr_test_2', 'req_test_1', '확정하시겠습니까?', 'pending')"
            )
            await db.execute(
                "INSERT OR REPLACE INTO messages (id, channel_id, sender, type, content, metadata_json) VALUES ('msg_appr_2', 'eng1', 'coordinator', 'approval', '확정하시겠습니까?', '{\"approval_id\": \"appr_test_2\", \"status\": \"pending\"}')"
            )
            await db.commit()

    asyncio.run(setup_reject_db())

    res_rej = client.post("/approvals/appr_test_2", json={"decision": "rejected", "reason": "루브릭 4단계 세분화 필요"})
    assert res_rej.status_code == 200
    rej_data = res_rej.json()
    assert rej_data["status"] == "rejected"
    assert rej_data["reason"] == "루브릭 4단계 세분화 필요"
    assert "new_request_id" in rej_data
    print("PASS: Approval 'rejected' registered with redispatch trigger:", rej_data["new_request_id"])

if __name__ == "__main__":
    test_health_endpoint()
    test_channels_and_bots_seeding()
    test_workspace_manager_and_final_copy()
    test_dispatch_plan_schema_validation()
    test_approval_approved_and_rejected_flows()
    print("\nALL PHASE 2 BACKEND INTEGRATION TESTS PASSED 100%!")

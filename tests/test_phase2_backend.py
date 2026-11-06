import asyncio
import os
import sys
import shutil
import tempfile
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Setup Isolated Test Data Directory before importing backend modules
temp_dir = tempfile.mkdtemp(prefix="crew_test_data_")
os.environ["CREW_DATA_DIR"] = temp_dir

from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.db.database import init_db, get_db_connection, get_data_dir, get_db_path
from backend.app.services.workspace_manager import WORKSPACE_DIR, get_workspace_dir, save_task_deliverable, copy_to_final
from backend.app.services.event_bus import EventBus
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
    assert str(abs_path).startswith(temp_dir)  # Verified isolated!

    # 2. Save deliverable
    dummy_task_id = "test_task_123"
    dummy_content = "# 영어I 3과 수행평가 루브릭\n\n- 상: 문법적 오류 없이 유창하게 표현함\n- 중: 의미 전달은 되나 일부 오류 있음\n- 하: 기본 어휘 위주로 단편적 서술함\n"
    saved_rel = save_task_deliverable(abs_path, dummy_task_id, dummy_content)
    assert (abs_path / f"{dummy_task_id}.md").read_text(encoding="utf-8") == dummy_content
    print("PASS: Deliverable saved at isolated path:", abs_path / f"{dummy_task_id}.md")

    # 3. Copy to final/
    final_rel = copy_to_final(abs_path, dummy_task_id)
    assert (abs_path / "final" / f"{dummy_task_id}.md").read_text(encoding="utf-8") == dummy_content
    print("PASS: Final copy created at isolated path:", abs_path / "final" / f"{dummy_task_id}.md")

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
        await init_db()
        async with get_db_connection() as db:
            await db.execute(
                "INSERT OR REPLACE INTO channels (id, name, type, course_code) VALUES ('eng1', '영어I', 'course', 'ENG1')"
            )
            await db.execute(
                "INSERT OR REPLACE INTO messages (id, channel_id, sender, type, content, metadata_json) VALUES ('msg_test_req', 'eng1', 'teacher', 'text', '영어I 3과 수행평가 설계', '{\"request_id\": \"req_test_1\", \"attempt\": 0}')"
            )
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
                "INSERT OR REPLACE INTO messages (id, channel_id, sender, type, content, metadata_json) VALUES ('msg_appr_1', 'eng1', 'coordinator', 'approval', '확정하시겠습니까?', '{\"request_id\": \"req_test_1\", \"approval_id\": \"appr_test_1\", \"attempt\": 0, \"status\": \"pending\"}')"
            )
            await db.commit()

    asyncio.run(setup_test_db())

    # 1. Test Approval (Approved)
    res_appr = client.post("/approvals/appr_test_1", json={"decision": "approved"})
    assert res_appr.status_code == 200
    appr_data = res_appr.json()
    assert appr_data["status"] == "approved"
    assert len(appr_data["final_files"]) > 0
    assert appr_data["channel_id"] == "eng1"
    print("PASS: Approval 'approved' copied to final/ successfully:", appr_data["final_files"])

    # 2. Test Approval (Rejected with attempt=0 -> 1st redispatch allowed)
    async def setup_reject_db():
        async with get_db_connection() as db:
            await db.execute(
                "INSERT OR REPLACE INTO approvals (id, request_id, question, status) VALUES ('appr_test_2', 'req_test_1', '확정하시겠습니까?', 'pending')"
            )
            await db.execute(
                "INSERT OR REPLACE INTO messages (id, channel_id, sender, type, content, metadata_json) VALUES ('msg_appr_2', 'eng1', 'coordinator', 'approval', '확정하시겠습니까?', '{\"request_id\": \"req_test_1\", \"approval_id\": \"appr_test_2\", \"attempt\": 0, \"status\": \"pending\"}')"
            )
            await db.commit()

    asyncio.run(setup_reject_db())

    res_rej = client.post("/approvals/appr_test_2", json={"decision": "rejected", "reason": "루브릭 4단계 세분화 필요"})
    assert res_rej.status_code == 200
    rej_data = res_rej.json()
    assert rej_data["status"] == "rejected"
    assert "new_request_id" in rej_data
    assert rej_data["channel_id"] == "eng1"
    print("PASS: First rejection triggered redispatch successfully:", rej_data["new_request_id"])

    # 3. Test Approval (Rejected with attempt=1 -> Rejection limit reached, NO redispatch!)
    async def setup_limit_db():
        async with get_db_connection() as db:
            await db.execute(
                "INSERT OR REPLACE INTO approvals (id, request_id, question, status) VALUES ('appr_test_limit', 'req_test_limit', '재확정하시겠습니까?', 'pending')"
            )
            await db.execute(
                "INSERT OR REPLACE INTO messages (id, channel_id, sender, type, content, metadata_json) VALUES ('msg_appr_limit', 'eng1', 'coordinator', 'approval', '재확정하시겠습니까?', '{\"request_id\": \"req_test_limit\", \"approval_id\": \"appr_test_limit\", \"attempt\": 1, \"status\": \"pending\"}')"
            )
            await db.commit()

    asyncio.run(setup_limit_db())

    res_limit = client.post("/approvals/appr_test_limit", json={"decision": "rejected", "reason": "추가 수정 필요"})
    assert res_limit.status_code == 200
    limit_data = res_limit.json()
    assert limit_data["status"] == "rejected"
    assert limit_data.get("limit_reached") is True
    assert "재작업 한도" in limit_data.get("message", "")
    print("PASS: Second rejection verified limit reached (1-time cap enforced):", limit_data)

def test_approval_channel_preservation():
    """
    Verify that approvals maintain the original channel_id from the approval message
    instead of defaulting to 'eng1'. (Testing with 'adv_eng1')
    """
    client = TestClient(app)

    async def setup_adv_eng_db():
        async with get_db_connection() as db:
            req_id = "req_adv_1"
            appr_id = "appr_adv_1"
            await db.execute(
                "INSERT OR REPLACE INTO messages (id, channel_id, sender, type, content, metadata_json) VALUES ('msg_adv_req', 'adv_eng1', 'teacher', 'text', '심화영어 심화 독해 에세이 문항', '{\"request_id\": \"req_adv_1\", \"attempt\": 0}')"
            )
            await db.execute(
                "INSERT OR REPLACE INTO approvals (id, request_id, question, status) VALUES (?, ?, '심화영어 문항을 확정하시겠습니까?', 'pending')",
                (appr_id, req_id)
            )
            await db.execute(
                """
                INSERT OR REPLACE INTO messages (id, channel_id, sender, type, content, metadata_json)
                VALUES ('msg_adv_appr', 'adv_eng1', 'coordinator', 'approval', '심화영어 문항을 확정하시겠습니까?', ?)
                """,
                (f'{{"request_id": "{req_id}", "approval_id": "{appr_id}", "attempt": 0, "status": "pending"}}',)
            )
            await db.commit()

    asyncio.run(setup_adv_eng_db())

    # Reject and verify that the redispatch request retains 'adv_eng1'
    res = client.post("/approvals/appr_adv_1", json={"decision": "rejected", "reason": "심화 어휘 추가 필요"})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "rejected"
    assert data["channel_id"] == "adv_eng1", f"Expected channel_id 'adv_eng1', got {data.get('channel_id')}"
    print("PASS: Approval rejection successfully preserved original channel 'adv_eng1' (no hardcoded eng1 fallback)!")

def test_event_bus_cleanup_after_completion():
    """
    Verify that EventBus automatically deletes event history after retention delay for completed/error events.
    """
    async def run_bus_test():
        bus = EventBus(retention_seconds=0.1) # 100ms for fast test
        req_id = "req_auto_cleanup_test"

        # 1. Publish status event -> buffer should have it
        await bus.publish(req_id, "status", {"message": "진행 중"})
        assert req_id in bus._event_history
        assert len(bus._event_history[req_id]) == 1

        # 2. Publish completed event -> triggers background cleanup task
        await bus.publish(req_id, "completed", {"result": "ok"})
        assert req_id in bus._event_history
        assert len(bus._event_history[req_id]) == 2

        # 3. Wait past retention delay (150ms > 100ms)
        await asyncio.sleep(0.15)

        # 4. History for this req_id must now be pruned
        assert req_id not in bus._event_history, f"Expected {req_id} to be cleaned up from EventBus history!"
        print("PASS: EventBus automatically cleaned up history after terminal event retention window")

    asyncio.run(run_bus_test())

def test_channels_endpoint_has_no_dir_creation_side_effect():
    # Remove any existing course directory in temp workspaces
    dummy_course_dir = Path(temp_dir) / "workspaces" / "미개설과목"
    if dummy_course_dir.exists():
        shutil.rmtree(dummy_course_dir)

    # Calling get_workspace_dir with create_dir=False must NOT create the directory
    rel, p = get_workspace_dir("course", "미개설과목", "1과", create_dir=False)
    assert not p.exists(), "Directory should NOT be created when create_dir=False!"
    print("PASS: Directory creation side effect prevented when create_dir=False")

if __name__ == "__main__":
    try:
        # Initialize database tables and seeds in the isolated temp directory
        asyncio.run(init_db())

        test_health_endpoint()
        test_channels_and_bots_seeding()
        test_workspace_manager_and_final_copy()
        test_dispatch_plan_schema_validation()
        test_approval_approved_and_rejected_flows()
        test_approval_channel_preservation()
        test_event_bus_cleanup_after_completion()
        test_channels_endpoint_has_no_dir_creation_side_effect()
        print("\nALL ISOLATED PHASE 2 BACKEND TESTS PASSED 100%!")
    finally:
        # Cleanup isolated temp directory
        shutil.rmtree(temp_dir, ignore_errors=True)
        print("PASS: Cleaned up isolated test temp directory.")

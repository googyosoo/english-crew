import asyncio
import json
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.db.database import get_db_connection
from backend.app.services.event_bus import EventBus

def test_approval_rejection_redispatches_with_reason():
    """
    1. 반려 시 사유를 반영해 재디스패치(new_request_id 반환) 검증
    """
    client = TestClient(app)

    async def setup_approval():
        async with get_db_connection() as db:
            await db.execute(
                """
                INSERT OR REPLACE INTO messages (id, channel_id, sender, type, content, metadata_json)
                VALUES ('msg_test_req_1', 'eng1', 'teacher', 'text', '영어I 3과 서술형 문항 출제', '{"request_id": "req_test_1", "attempt": 0}')
                """
            )
            await db.execute(
                """
                INSERT OR REPLACE INTO approvals (id, request_id, question, status)
                VALUES ('appr_test_1', 'req_test_1', '3과 서술형 문항을 확정하시겠습니까?', 'pending')
                """
            )
            await db.execute(
                """
                INSERT OR REPLACE INTO messages (id, channel_id, sender, type, content, metadata_json)
                VALUES ('msg_test_appr_1', 'eng1', 'coordinator', 'approval', '3과 서술형 문항을 확정하시겠습니까?', '{"request_id": "req_test_1", "approval_id": "appr_test_1", "attempt": 0, "status": "pending"}')
                """
            )
            await db.commit()

    asyncio.run(setup_approval())

    res = client.post("/approvals/appr_test_1", json={"decision": "rejected", "reason": "문항 난이도 하향 필요"})
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    rej_data = res.json()
    assert rej_data["status"] == "rejected"
    assert rej_data["approval_id"] == "appr_test_1"
    assert rej_data["reason"] == "문항 난이도 하향 필요"
    new_req_id = rej_data.get("new_request_id")
    assert new_req_id is not None, "Expected new_request_id in rejection response"
    assert new_req_id.startswith("req_")

    async def verify_db_state():
        async with get_db_connection() as db:
            cursor = await db.execute("SELECT status, reason FROM approvals WHERE id = 'appr_test_1'")
            row = await cursor.fetchone()
            assert row is not None
            assert row["status"] == "rejected"
            assert row["reason"] == "문항 난이도 하향 필요"

    asyncio.run(verify_db_state())

def test_approval_rework_rejection_enforces_limit():
    """
    2. 재작업 요청을 다시 반려하면 limit_reached=True, 재디스패치 없음(new_request_id is None) 검증
    """
    client = TestClient(app)

    async def setup_rework_approval():
        async with get_db_connection() as db:
            await db.execute(
                """
                INSERT OR REPLACE INTO messages (id, channel_id, sender, type, content, metadata_json)
                VALUES ('msg_rework_req_1', 'eng1', 'teacher', 'text', '영어I 3과 재작업 요청', '{"request_id": "req_rework_1", "attempt": 1}')
                """
            )
            await db.execute(
                """
                INSERT OR REPLACE INTO approvals (id, request_id, question, status)
                VALUES ('appr_test_limit_1', 'req_rework_1', '재작업 산출물을 확정하시겠습니까?', 'pending')
                """
            )
            await db.execute(
                """
                INSERT OR REPLACE INTO messages (id, channel_id, sender, type, content, metadata_json)
                VALUES ('msg_rework_appr_1', 'eng1', 'coordinator', 'approval', '재작업 산출물을 확정하시겠습니까?', '{"request_id": "req_rework_1", "approval_id": "appr_test_limit_1", "attempt": 1, "status": "pending"}')
                """
            )
            await db.commit()

    asyncio.run(setup_rework_approval())

    res = client.post("/approvals/appr_test_limit_1", json={"decision": "rejected", "reason": "추가 수정 필요"})
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    limit_data = res.json()
    assert limit_data["status"] == "rejected"
    assert limit_data.get("limit_reached") is True
    assert "재작업 한도" in limit_data.get("message", "")
    assert limit_data.get("new_request_id") is None

    async def verify_limit_message_in_db():
        async with get_db_connection() as db:
            cursor = await db.execute(
                "SELECT content, metadata_json FROM messages WHERE channel_id = 'eng1' AND content LIKE '%재작업 한도%' ORDER BY created_at DESC LIMIT 1"
            )
            row = await cursor.fetchone()
            assert row is not None, "Expected coordinator limit message in database"
            meta = json.loads(row["metadata_json"])
            assert meta.get("limit_reached") is True
            assert meta.get("attempt") == 1

    asyncio.run(verify_limit_message_in_db())

def test_approval_rejection_preserves_adv_readwrite_channel():
    """
    3. adv_readwrite (심화 영어 독해와 작문) 채널에서 반려해도 재작업이 같은 채널에 기록됨 검증
    """
    client = TestClient(app)

    async def setup_adv_readwrite_approval():
        async with get_db_connection() as db:
            req_id = "req_adv_rw_1"
            appr_id = "appr_adv_rw_1"
            await db.execute(
                """
                INSERT OR REPLACE INTO messages (id, channel_id, sender, type, content, metadata_json)
                VALUES ('msg_adv_rw_req', 'adv_readwrite', 'teacher', 'text', '심화 영어 독해 에세이 문항 작성', '{"request_id": "req_adv_rw_1", "attempt": 0}')
                """
            )
            await db.execute(
                """
                INSERT OR REPLACE INTO approvals (id, request_id, question, status)
                VALUES ('appr_adv_rw_1', 'req_adv_rw_1', '심화 영어 독해 산출물을 확정하시겠습니까?', 'pending')
                """
            )
            await db.execute(
                """
                INSERT OR REPLACE INTO messages (id, channel_id, sender, type, content, metadata_json)
                VALUES ('msg_adv_rw_appr', 'adv_readwrite', 'coordinator', 'approval', '심화 영어 독해 산출물을 확정하시겠습니까?', '{"request_id": "req_adv_rw_1", "approval_id": "appr_adv_rw_1", "attempt": 0, "status": "pending"}')
                """
            )
            await db.commit()

    asyncio.run(setup_adv_readwrite_approval())

    res = client.post("/approvals/appr_adv_rw_1", json={"decision": "rejected", "reason": "심화 어휘 추가 필요"})
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    data = res.json()
    assert data["status"] == "rejected"
    assert data["channel_id"] == "adv_readwrite", f"Expected channel_id 'adv_readwrite', got {data.get('channel_id')}"
    assert data.get("new_request_id") is not None

def test_event_bus_late_subscribe_and_retention_cleanup():
    """
    4. EventBus: 늦게 구독해도 이전 이벤트 재전송, completed 후 보관 시간이 지나면 삭제 검증
    """
    async def run_bus_test():
        bus = EventBus(retention_seconds=0.1)
        req_id = "req_eventbus_verify_flow"

        # 1. 구독 전 이벤트 발행
        await bus.publish(req_id, "status", {"message": "진행 중"})
        assert req_id in bus._event_history
        assert len(bus._event_history[req_id]) == 1

        # 2. 늦게 구독 후 이전 이벤트 재생 수신 확인
        queue = await bus.subscribe(req_id)
        assert not queue.empty(), "Expected replayed event in queue for late subscriber"
        event1 = queue.get_nowait()
        assert event1["type"] == "status"
        assert event1["data"] == {"message": "진행 중"}

        # 3. 종료 이벤트 발행
        await bus.publish(req_id, "completed", {"result": "ok"})
        event2 = await queue.get()
        assert event2["type"] == "completed"
        assert event2["data"] == {"result": "ok"}

        # 4. 보관 시간(0.1초) 초과 대기 후 히스토리 자동 정리 확인
        await asyncio.sleep(0.2)
        assert req_id not in bus._event_history, f"Expected {req_id} to be deleted from history after retention"

    asyncio.run(run_bus_test())

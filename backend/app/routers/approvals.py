import uuid
import json
from datetime import datetime
from pathlib import Path
from fastapi import APIRouter, HTTPException, BackgroundTasks

from backend.app.db.database import get_db_connection
from backend.app.models.schemas import ApprovalDecision
from backend.app.services.workspace_manager import copy_to_final, WORKSPACE_DIR
from backend.app.routers.channels import process_teacher_request

router = APIRouter()

@router.post("/approvals/{approval_id}")
async def decide_approval(
    approval_id: str,
    payload: ApprovalDecision,
    background_tasks: BackgroundTasks
):
    decision = payload.decision.strip().lower()
    reason = payload.reason.strip() if payload.reason else ""

    if decision not in ["approved", "rejected"]:
        raise HTTPException(status_code=400, detail="결재 결정은 'approved' 또는 'rejected'여야 합니다.")

    if decision == "rejected" and not reason:
        raise HTTPException(status_code=400, detail="반려 시 반려 사유(reason)를 반드시 입력해야 합니다.")

    async with get_db_connection() as db:
        # Find approval record
        cursor = await db.execute("SELECT id, request_id, question, status FROM approvals WHERE id = ?", (approval_id,))
        appr = await cursor.fetchone()
        if not appr:
            raise HTTPException(status_code=404, detail="결재 건을 찾을 수 없습니다.")

        request_id = appr["request_id"]

        # 1. Fetch approval message directly from messages table to determine channel_id
        cursor = await db.execute(
            """
            SELECT id, channel_id, metadata_json FROM messages
            WHERE type = 'approval' AND metadata_json LIKE ?
            ORDER BY created_at DESC LIMIT 1
            """,
            (f'%{approval_id}%',)
        )
        appr_msg = await cursor.fetchone()
        if not appr_msg:
            raise HTTPException(status_code=404, detail="결재 메시지를 찾을 수 없습니다.")

        channel_id = appr_msg["channel_id"]

        # 2. Fetch associated tasks
        cursor = await db.execute(
            "SELECT id, bot_id, title, status, output_path FROM tasks WHERE request_id = ?",
            (request_id,)
        )
        tasks = await cursor.fetchall()

        # 3. Fetch original teacher message content
        cursor = await db.execute(
            """
            SELECT content FROM messages
            WHERE sender = 'teacher' AND metadata_json LIKE ?
            ORDER BY created_at DESC LIMIT 1
            """,
            (f'%{request_id}%',)
        )
        teacher_msg = await cursor.fetchone()
        teacher_content = teacher_msg["content"] if teacher_msg else ""

        if decision == "approved":
            # 1. Update approval status
            await db.execute(
                "UPDATE approvals SET status = 'approved', updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (approval_id,)
            )

            # 2. Copy deliverables to final/
            final_files = []
            for t in tasks:
                out_path = t["output_path"]
                if out_path and t["status"] == "done":
                    file_full_path = WORKSPACE_DIR / out_path
                    parent_dir = file_full_path.parent
                    copied_rel_path = copy_to_final(parent_dir, t["id"])
                    if copied_rel_path:
                        final_files.append(copied_rel_path)

            # 3. Update approval message in messages table
            meta = json.loads(appr_msg["metadata_json"]) if appr_msg["metadata_json"] else {}
            meta["status"] = "approved"
            meta["final_files"] = final_files
            await db.execute(
                "UPDATE messages SET metadata_json = ? WHERE id = ?",
                (json.dumps(meta, ensure_ascii=False), appr_msg["id"])
            )

            # 4. Phase 3: Automatically record confirmation to context_notes (kind='차시기록')
            ch_cur = await db.execute("SELECT course_code FROM channels WHERE id = ?", (channel_id,))
            ch_row = await ch_cur.fetchone()
            course_code = (ch_row["course_code"] if ch_row else None) or "COMMON"
            unit = meta.get("unit") or "1과"
            date_str = datetime.now().strftime("%Y-%m-%d")
            record_content = f"{date_str} · {appr['question']} (최종 확정)"
            note_id = f"note_{uuid.uuid4().hex[:8]}"
            await db.execute(
                """
                INSERT INTO context_notes (id, course_code, unit, kind, content)
                VALUES (?, ?, ?, '차시기록', ?)
                """,
                (note_id, course_code, unit, record_content)
            )

            await db.commit()

            return {
                "status": "approved",
                "approval_id": approval_id,
                "channel_id": channel_id,
                "final_files": final_files
            }

        else: # rejected
            # Determine current attempt count from approval metadata
            attempt = 0
            meta = json.loads(appr_msg["metadata_json"]) if appr_msg["metadata_json"] else {}
            attempt = meta.get("attempt", 0)

            # 1. Update approval status
            await db.execute(
                "UPDATE approvals SET status = 'rejected', reason = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (reason, approval_id)
            )

            # 2. Update approval message
            meta["status"] = "rejected"
            meta["reason"] = reason
            await db.execute(
                "UPDATE messages SET metadata_json = ? WHERE id = ?",
                (json.dumps(meta, ensure_ascii=False), appr_msg["id"])
            )

            # 3. Check attempt limit: 1-time redispatch maximum
            if attempt >= 1:
                # Limit reached: do NOT redispatch, insert limit message
                limit_msg_id = f"msg_{uuid.uuid4().hex[:8]}"
                await db.execute(
                    """
                    INSERT INTO messages (id, channel_id, sender, type, content, metadata_json)
                    VALUES (?, ?, 'coordinator', 'text', ?, ?)
                    """,
                    (
                        limit_msg_id,
                        channel_id,
                        "재작업 한도(1회)에 도달했습니다. 추가 수정이 필요하시면 새로운 요청으로 진행해 주십시오.",
                        json.dumps({"request_id": request_id, "attempt": attempt, "limit_reached": True}, ensure_ascii=False)
                    )
                )
                await db.commit()

                return {
                    "status": "rejected",
                    "approval_id": approval_id,
                    "reason": reason,
                    "limit_reached": True,
                    "message": "재작업 한도 도달"
                }

            await db.commit()

            # 4. Trigger one-time redispatch with attempt=1
            new_request_id = f"req_{uuid.uuid4().hex[:8]}"
            background_tasks.add_task(
                process_teacher_request,
                new_request_id,
                channel_id,
                teacher_content,
                reason,
                attempt=attempt + 1,
                parent_request_id=request_id
            )

            return {
                "status": "rejected",
                "approval_id": approval_id,
                "channel_id": channel_id,
                "reason": reason,
                "new_request_id": new_request_id
            }

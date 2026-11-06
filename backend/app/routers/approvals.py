import uuid
import json
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

        # Fetch associated tasks
        cursor = await db.execute(
            "SELECT id, bot_id, title, status, output_path FROM tasks WHERE request_id = ?",
            (request_id,)
        )
        tasks = await cursor.fetchall()

        # Fetch channel and teacher message
        cursor = await db.execute(
            """
            SELECT id, channel_id, content FROM messages
            WHERE sender = 'teacher' AND metadata_json LIKE ?
            ORDER BY created_at DESC LIMIT 1
            """,
            (f'%{request_id}%',)
        )
        teacher_msg = await cursor.fetchone()
        channel_id = teacher_msg["channel_id"] if teacher_msg else "eng1"
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
            cursor = await db.execute(
                "SELECT id, metadata_json FROM messages WHERE type = 'approval' AND metadata_json LIKE ?",
                (f'%{approval_id}%',)
            )
            appr_msg = await cursor.fetchone()
            if appr_msg:
                meta = json.loads(appr_msg["metadata_json"])
                meta["status"] = "approved"
                meta["final_files"] = final_files
                await db.execute(
                    "UPDATE messages SET metadata_json = ? WHERE id = ?",
                    (json.dumps(meta, ensure_ascii=False), appr_msg["id"])
                )

            await db.commit()

            return {
                "status": "approved",
                "approval_id": approval_id,
                "final_files": final_files
            }

        else: # rejected
            # 1. Update approval status
            await db.execute(
                "UPDATE approvals SET status = 'rejected', reason = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (reason, approval_id)
            )

            # 2. Update message
            cursor = await db.execute(
                "SELECT id, metadata_json FROM messages WHERE type = 'approval' AND metadata_json LIKE ?",
                (f'%{approval_id}%',)
            )
            appr_msg = await cursor.fetchone()
            if appr_msg:
                meta = json.loads(appr_msg["metadata_json"])
                meta["status"] = "rejected"
                meta["reason"] = reason
                await db.execute(
                    "UPDATE messages SET metadata_json = ? WHERE id = ?",
                    (json.dumps(meta, ensure_ascii=False), appr_msg["id"])
                )

            await db.commit()

            # 3. Trigger one-time redispatch
            new_request_id = f"req_{uuid.uuid4().hex[:8]}"
            background_tasks.add_task(
                process_teacher_request,
                new_request_id,
                channel_id,
                teacher_content,
                reason
            )

            return {
                "status": "rejected",
                "approval_id": approval_id,
                "reason": reason,
                "new_request_id": new_request_id
            }

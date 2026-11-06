import asyncio
import json
import uuid
from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse

from backend.app.db.database import get_db_connection
from backend.app.models.schemas import RequestCreate, DispatchPlan, TaskSpec
from backend.app.services.gemini_client import (
    create_dispatch_plan,
    execute_bot_task,
    summarize_and_finalize_approval,
)
from backend.app.services.workspace_manager import (
    get_workspace_dir,
    save_task_deliverable,
    WORKSPACE_DIR
)
from backend.app.services.event_bus import event_bus

router = APIRouter()

@router.get("/bots")
async def list_bots():
    async with get_db_connection() as db:
        cursor = await db.execute("SELECT id, name, role, model, enabled FROM bots")
        rows = await cursor.fetchall()
        return [
            {
                "id": r["id"],
                "name": r["name"],
                "role": r["role"],
                "model": r["model"],
                "enabled": bool(r["enabled"]),
            }
            for r in rows
        ]

@router.get("/channels")
async def list_channels():
    async with get_db_connection() as db:
        cursor = await db.execute("SELECT id, name, type, course_code FROM channels")
        rows = await cursor.fetchall()
        result = []
        for r in rows:
            rel_path, _ = get_workspace_dir(r["type"], r["name"], "1과")
            result.append({
                "id": r["id"],
                "name": r["name"],
                "type": r["type"],
                "course_code": r["course_code"],
                "workspace_dir": rel_path
            })
        return result

@router.get("/channels/{channel_id}/messages")
async def get_channel_messages(channel_id: str):
    async with get_db_connection() as db:
        cursor = await db.execute(
            """
            SELECT id, channel_id, sender, type, content, metadata_json, created_at
            FROM messages
            WHERE channel_id = ?
            ORDER BY created_at ASC
            """,
            (channel_id,)
        )
        rows = await cursor.fetchall()
        messages = []
        for r in rows:
            meta = {}
            if r["metadata_json"]:
                try:
                    meta = json.loads(r["metadata_json"])
                except Exception:
                    pass
            messages.append({
                "id": r["id"],
                "channel_id": r["channel_id"],
                "sender": r["sender"],
                "type": r["type"],
                "content": r["content"],
                "metadata": meta,
                "created_at": r["created_at"],
            })
        return messages

async def process_teacher_request(request_id: str, channel_id: str, content: str, reject_reason: str = None):
    """
    Background worker for executing the full coordinator -> team bot -> report -> approval pipeline.
    """
    try:
        async with get_db_connection() as db:
            # 1. Fetch channel info
            cursor = await db.execute("SELECT id, name, type, course_code FROM channels WHERE id = ?", (channel_id,))
            channel = await cursor.fetchone()
            if not channel:
                return

            channel_info = dict(channel)

            # 2. Fetch active bots
            cursor = await db.execute("SELECT id, name, role, model, enabled FROM bots WHERE enabled = 1")
            active_bot_rows = await cursor.fetchall()
            active_bots = [dict(b) for b in active_bot_rows]

        # 3. Coordinator generates dispatch plan
        await event_bus.publish(request_id, "status", {"message": "코디봇이 요청을 분석하고 과업 계획을 수립하고 있습니다..."})
        plan: DispatchPlan = await create_dispatch_plan(
            content=content,
            channel_info=channel_info,
            active_bots=active_bots,
            reject_reason=reject_reason
        )

        # 4. Save DispatchCard message
        disp_msg_id = f"msg_{uuid.uuid4().hex[:8]}"
        tasks_meta = []
        db_tasks = []

        # Prepare workspace directory
        unit = plan.unit if plan.unit else "1과"
        rel_work_dir, abs_work_dir = get_workspace_dir(channel_info["type"], channel_info["name"], unit)

        for t in plan.tasks:
            t_id = f"tsk_{uuid.uuid4().hex[:8]}"
            db_tasks.append({
                "id": t_id,
                "request_id": request_id,
                "bot_id": t.bot,
                "title": t.title,
                "deliverable": t.deliverable,
                "status": "queued",
            })
            tasks_meta.append({
                "id": t_id,
                "bot": t.bot,
                "title": t.title,
                "deliverable": t.deliverable,
                "status": "queued",
            })

        async with get_db_connection() as db:
            # Save dispatch message
            await db.execute(
                """
                INSERT INTO messages (id, channel_id, sender, type, content, metadata_json)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    disp_msg_id,
                    channel_id,
                    "coordinator",
                    "dispatch",
                    plan.summary,
                    json.dumps({
                        "request_id": request_id,
                        "unit": unit,
                        "workspace_dir": rel_work_dir,
                        "tasks": tasks_meta
                    }, ensure_ascii=False)
                )
            )
            # Insert tasks
            for dt in db_tasks:
                await db.execute(
                    """
                    INSERT INTO tasks (id, request_id, bot_id, title, deliverable, status)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (dt["id"], dt["request_id"], dt["bot_id"], dt["title"], dt["deliverable"], dt["status"])
                )
            await db.commit()

        await event_bus.publish(request_id, "dispatch_created", {
            "message_id": disp_msg_id,
            "tasks": tasks_meta,
            "workspace_dir": rel_work_dir,
            "unit": unit
        })

        # 5. Execute team bot tasks in parallel
        await event_bus.publish(request_id, "status", {"message": "팀원봇들이 과업을 수행하고 있습니다..."})

        async def run_single_task(dt: Dict[str, Any]):
            t_id = dt["id"]
            bot_id = dt["bot_id"]
            title = dt["title"]
            deliverable = dt["deliverable"]

            async with get_db_connection() as db:
                await db.execute("UPDATE tasks SET status = 'running' WHERE id = ?", (t_id,))
                await db.commit()

            await event_bus.publish(request_id, "task_update", {"task_id": t_id, "status": "running"})

            try:
                result_text = await execute_bot_task(
                    bot_id=bot_id,
                    title=title,
                    deliverable=deliverable,
                    course_name=channel_info["name"],
                    unit=unit,
                    teacher_request=content
                )
                # Save file
                saved_path = save_task_deliverable(abs_work_dir, t_id, result_text)
                async with get_db_connection() as db:
                    await db.execute(
                        "UPDATE tasks SET status = 'done', output_path = ? WHERE id = ?",
                        (saved_path, t_id)
                    )
                    await db.commit()

                await event_bus.publish(request_id, "task_update", {
                    "task_id": t_id,
                    "status": "done",
                    "output_path": saved_path
                })
                return {"id": t_id, "bot_id": bot_id, "title": title, "content": result_text, "status": "done", "output_path": saved_path}

            except Exception as e:
                err_msg = str(e)
                async with get_db_connection() as db:
                    await db.execute(
                        "UPDATE tasks SET status = 'failed', error_message = ? WHERE id = ?",
                        (err_msg, t_id)
                    )
                    await db.commit()

                await event_bus.publish(request_id, "task_update", {
                    "task_id": t_id,
                    "status": "failed",
                    "error_message": err_msg
                })
                return {"id": t_id, "bot_id": bot_id, "title": title, "content": f"오류 발생: {err_msg}", "status": "failed", "error_message": err_msg}

        task_results = await asyncio.gather(*(run_single_task(dt) for dt in db_tasks))

        # 6. Coordinator summarization & final approval question
        await event_bus.publish(request_id, "status", {"message": "코디봇이 결과를 취합하고 결재 질문을 정리하고 있습니다..."})
        summary_result = await summarize_and_finalize_approval(
            initial_question=plan.approval_question,
            task_results=task_results
        )

        summary_text = summary_result["summary"]
        final_approval_question = summary_result["approval_question"]

        # 7. Create approval record
        appr_id = f"appr_{uuid.uuid4().hex[:8]}"
        async with get_db_connection() as db:
            await db.execute(
                """
                INSERT INTO approvals (id, request_id, question, status)
                VALUES (?, ?, ?, 'pending')
                """,
                (appr_id, request_id, final_approval_question)
            )

            # Create ReportCard message
            report_msg_id = f"msg_{uuid.uuid4().hex[:8]}"
            report_items = []
            for tr in task_results:
                report_items.append({
                    "task_id": tr["id"],
                    "bot_id": tr["bot_id"],
                    "title": tr["title"],
                    "status": tr["status"],
                    "output_path": tr.get("output_path", "")
                })

            await db.execute(
                """
                INSERT INTO messages (id, channel_id, sender, type, content, metadata_json)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    report_msg_id,
                    channel_id,
                    "coordinator",
                    "report",
                    summary_text,
                    json.dumps({
                        "request_id": request_id,
                        "workspace_dir": rel_work_dir,
                        "tasks": report_items
                    }, ensure_ascii=False)
                )
            )

            # Create ApprovalCard message
            appr_msg_id = f"msg_{uuid.uuid4().hex[:8]}"
            await db.execute(
                """
                INSERT INTO messages (id, channel_id, sender, type, content, metadata_json)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    appr_msg_id,
                    channel_id,
                    "coordinator",
                    "approval",
                    final_approval_question,
                    json.dumps({
                        "request_id": request_id,
                        "approval_id": appr_id,
                        "status": "pending",
                        "workspace_dir": rel_work_dir,
                        "tasks": report_items
                    }, ensure_ascii=False)
                )
            )
            await db.commit()

        await event_bus.publish(request_id, "completed", {
            "request_id": request_id,
            "report_message_id": report_msg_id,
            "approval_message_id": appr_msg_id,
            "approval_id": appr_id,
            "summary": summary_text,
            "approval_question": final_approval_question
        })

    except Exception as e:
        logger_msg = f"요청 처리 중 오류 발생: {e}"
        await event_bus.publish(request_id, "error", {"message": logger_msg})

@router.post("/channels/{channel_id}/requests")
async def create_channel_request(
    channel_id: str,
    payload: RequestCreate,
    background_tasks: BackgroundTasks
):
    content = payload.content.strip()
    if not content:
        raise HTTPException(status_code=400, detail="요청 내용이 비어 있습니다.")

    request_id = f"req_{uuid.uuid4().hex[:8]}"
    teacher_msg_id = f"msg_{uuid.uuid4().hex[:8]}"

    # Save teacher message to DB
    async with get_db_connection() as db:
        await db.execute(
            """
            INSERT INTO messages (id, channel_id, sender, type, content, metadata_json)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (teacher_msg_id, channel_id, "teacher", "text", content, json.dumps({"request_id": request_id}))
        )
        await db.commit()

    # Trigger background pipeline
    background_tasks.add_task(process_teacher_request, request_id, channel_id, content)

    return {
        "status": "ok",
        "request_id": request_id,
        "teacher_message_id": teacher_msg_id
    }

@router.get("/requests/{request_id}/events")
async def get_request_events(request_id: str):
    queue = await event_bus.subscribe(request_id)

    async def event_generator():
        try:
            while True:
                payload = await queue.get()
                yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
                if payload.get("type") in ["completed", "error"]:
                    break
        finally:
            await event_bus.unsubscribe(request_id, queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )

@router.get("/tasks/{task_id}/deliverable")
async def get_task_deliverable(task_id: str):
    async with get_db_connection() as db:
        cursor = await db.execute("SELECT id, title, deliverable, status, output_path, error_message FROM tasks WHERE id = ?", (task_id,))
        task = await cursor.fetchone()
        if not task:
            raise HTTPException(status_code=404, detail="과업을 찾을 수 없습니다.")

        output_path = task["output_path"]
        content = ""
        if output_path:
            full_path = WORKSPACE_DIR / output_path
            if full_path.exists():
                content = full_path.read_text(encoding="utf-8")

        return {
            "id": task["id"],
            "title": task["title"],
            "deliverable": task["deliverable"],
            "status": task["status"],
            "output_path": task["output_path"],
            "error_message": task["error_message"],
            "content": content
        }

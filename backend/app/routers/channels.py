import asyncio
import json
import uuid
import re
import logging
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
from backend.app.services.anonymizer import anonymize_text, deanonymize_text
from backend.app.services.checks.rubric_check import check_rubric
from backend.app.services.checks.seteuk_check import check_seteuk

logger = logging.getLogger(__name__)

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
            rel_path, _ = get_workspace_dir(r["type"], r["name"], "1과", create_dir=False)
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

async def process_teacher_request(
    request_id: str,
    channel_id: str,
    content: str,
    reject_reason: str = None,
    attempt: int = 0,
    parent_request_id: str = None
):
    """
    Phase 3 background pipeline:
    1. Student anonymization (실명 -> 번호)
    2. Context & Textbook body check (단원 본문 필수 검사)
    3. Coordinator dispatch plan & General channel clarification
    4. Multi-stage DAG task execution (curriculum -> assessment/lesson)
    5. Rubric & Seteuk automated checks with 1-time self-healing retry
    6. Deanonymization for local storage
    7. Summary, ReportCard, ApprovalCard
    """
    try:
        async with get_db_connection() as db:
            # 1. Fetch channel info
            cursor = await db.execute("SELECT id, name, type, course_code FROM channels WHERE id = ?", (channel_id,))
            channel = await cursor.fetchone()
            if not channel:
                return
            channel_info = dict(channel)
            course_code = channel_info.get("course_code") or ("COMMON" if channel_info["type"] == "all" else "ENG1")

            # 2. Fetch students for anonymization
            st_cur = await db.execute("SELECT * FROM students WHERE course_code = ?", (course_code,))
            students = [dict(s) for s in await st_cur.fetchall()]

            # 3. Fetch active bots
            b_cur = await db.execute("SELECT id, name, role, model, enabled FROM bots WHERE enabled = 1")
            active_bots = [dict(b) for b in await b_cur.fetchall()]

            # 4. Fetch context notes for this course
            cn_cur = await db.execute(
                "SELECT * FROM context_notes WHERE course_code = ? ORDER BY created_at DESC",
                (course_code,)
            )
            context_notes = [dict(n) for n in await cn_cur.fetchall()]

        # 5. Anonymize teacher request before Gemini sees it
        anonymized_content, restore_map = anonymize_text(content, students)

        # 6. Check for Unit & Textbook Body requirement
        # [B. 단원 본문 저장 - 과목 채널 요청 시 해당 단원 본문 검사]
        unit_match = re.search(r"(\d+)\s*과", content)
        detected_unit = f"{unit_match.group(1)}과" if unit_match else None

        # Check if teacher explicitly allowed general/no-body prompt
        has_general_flag = any(kw in content for kw in ["본문 없이", "일반 주제로", "일반 주제 기준", "가상 주제"])

        body_note = None
        if detected_unit and channel_info["type"] != "all":
            body_note = next(
                (n for n in context_notes if n["kind"] == "본문" and n["unit"] == detected_unit),
                None
            )
            if not body_note and not has_general_flag:
                # Disallow dispatch and prompt teacher to add textbook body
                prompt_msg = f"{detected_unit} 본문을 [수업 맥락]에 넣어 주세요."
                msg_id = f"msg_{uuid.uuid4().hex[:8]}"
                async with get_db_connection() as db:
                    await db.execute(
                        """
                        INSERT INTO messages (id, channel_id, sender, type, content, metadata_json)
                        VALUES (?, ?, 'coordinator', 'text', ?, ?)
                        """,
                        (msg_id, channel_id, prompt_msg, json.dumps({"request_id": request_id, "no_body": True}, ensure_ascii=False))
                    )
                    await db.commit()

                await event_bus.publish(request_id, "completed", {
                    "request_id": request_id,
                    "summary": prompt_msg,
                    "has_failures": False,
                    "clarification": prompt_msg
                })
                return

        # 7. Coordinator generates dispatch plan
        await event_bus.publish(request_id, "status", {"message": "코디봇이 요청을 분석하고 과업 계획을 수립하고 있습니다..."})
        plan: DispatchPlan = await create_dispatch_plan(
            content=anonymized_content,
            channel_info=channel_info,
            active_bots=active_bots,
            reject_reason=reject_reason,
            context_notes=context_notes
        )

        # 8. Check General Channel Clarification (Phase 3 #4)
        if channel_info["type"] == "all" and (plan.clarification or not plan.tasks):
            clarification_text = plan.clarification or "어느 과목(영어I, 심화영어I 등)의 요청인지 알려주시겠습니까?"
            msg_id = f"msg_{uuid.uuid4().hex[:8]}"
            async with get_db_connection() as db:
                await db.execute(
                    """
                    INSERT INTO messages (id, channel_id, sender, type, content, metadata_json)
                    VALUES (?, ?, 'coordinator', 'text', ?, ?)
                    """,
                    (msg_id, channel_id, clarification_text, json.dumps({"request_id": request_id, "clarification": True}, ensure_ascii=False))
                )
                await db.commit()

            await event_bus.publish(request_id, "completed", {
                "request_id": request_id,
                "summary": clarification_text,
                "has_failures": False,
                "clarification": clarification_text
            })
            return

        # Prepare workspace directory
        unit = plan.unit if plan.unit else (detected_unit or "1과")
        rel_work_dir, abs_work_dir = get_workspace_dir(channel_info["type"], channel_info["name"], unit)

        # If body note was not found earlier but unit is known now, recheck
        if not body_note and channel_info["type"] != "all":
            body_note = next(
                (n for n in context_notes if n["kind"] == "본문" and n["unit"] == unit),
                None
            )
            if not body_note and not has_general_flag:
                prompt_msg = f"{unit} 본문을 [수업 맥락]에 넣어 주세요."
                msg_id = f"msg_{uuid.uuid4().hex[:8]}"
                async with get_db_connection() as db:
                    await db.execute(
                        """
                        INSERT INTO messages (id, channel_id, sender, type, content, metadata_json)
                        VALUES (?, ?, 'coordinator', 'text', ?, ?)
                        """,
                        (msg_id, channel_id, prompt_msg, json.dumps({"request_id": request_id, "no_body": True}, ensure_ascii=False))
                    )
                    await db.commit()

                await event_bus.publish(request_id, "completed", {
                    "request_id": request_id,
                    "summary": prompt_msg,
                    "has_failures": False,
                    "clarification": prompt_msg
                })
                return

        # 9. Save DispatchCard message
        disp_msg_id = f"msg_{uuid.uuid4().hex[:8]}"
        tasks_meta = []
        db_tasks = []

        for t in plan.tasks:
            t_id = f"tsk_{uuid.uuid4().hex[:8]}"
            db_tasks.append({
                "id": t_id,
                "request_id": request_id,
                "bot_id": t.bot,
                "title": t.title,
                "deliverable": t.deliverable,
                "depends_on": t.depends_on or [],
                "status": "queued",
            })
            tasks_meta.append({
                "id": t_id,
                "bot": t.bot,
                "title": t.title,
                "deliverable": t.deliverable,
                "depends_on": t.depends_on or [],
                "status": "queued",
            })

        async with get_db_connection() as db:
            await db.execute(
                """
                INSERT INTO messages (id, channel_id, sender, type, content, metadata_json)
                VALUES (?, ?, 'coordinator', 'dispatch', ?, ?)
                """,
                (
                    disp_msg_id,
                    channel_id,
                    plan.summary,
                    json.dumps({
                        "request_id": request_id,
                        "attempt": attempt,
                        "parent_request_id": parent_request_id,
                        "unit": unit,
                        "workspace_dir": rel_work_dir,
                        "tasks": tasks_meta
                    }, ensure_ascii=False)
                )
            )
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

        # 10. Multi-stage DAG Execution based on depends_on
        # Separate tasks into Stage 1 (no depends_on) and Stage 2 (dependent)
        stage1_tasks = [dt for dt in db_tasks if not dt["depends_on"]]
        stage2_tasks = [dt for dt in db_tasks if dt["depends_on"]]

        # Default fallback: if all have depends_on or cycles, run all in stage 1
        if not stage1_tasks and stage2_tasks:
            stage1_tasks = stage2_tasks
            stage2_tasks = []

        task_outputs: Dict[str, str] = {}
        task_results: List[Dict[str, Any]] = []
        curriculum_codes: List[str] = []

        # Prepare base extra context (Textbook body if available)
        base_extra = ""
        if body_note:
            base_extra += f"--- [단원 {unit} 교과서 본문] ---\n{body_note['content']}\n\n"

        async def execute_and_verify_task(dt: Dict[str, Any], extra_ctx: str = "") -> Dict[str, Any]:
            t_id = dt["id"]
            bot_id = dt["bot_id"]
            title = dt["title"]
            deliverable = dt["deliverable"]

            async with get_db_connection() as db:
                await db.execute("UPDATE tasks SET status = 'running' WHERE id = ?", (t_id,))
                await db.commit()

            await event_bus.publish(request_id, "task_update", {"task_id": t_id, "status": "running"})

            try:
                # 1st attempt
                raw_output = await execute_bot_task(
                    bot_id=bot_id,
                    title=title,
                    deliverable=deliverable,
                    course_name=channel_info["name"],
                    unit=unit,
                    teacher_request=anonymized_content,
                    extra_context=extra_ctx
                )

                check_info = None

                # Rule 4 & 5: Rubric Check for assessment bot
                if bot_id == "assessment":
                    check_res = check_rubric(raw_output, allowed_codes=curriculum_codes)
                    if not check_res.passed:
                        # 1-time automatic self-healing retry!
                        logger.warning(f"Assessment output check failed: {check_res.issues}. Triggering 1-time retry...")
                        feedback_prompt = f"다음 검사 지적 사항을 반드시 수정하여 다시 작성하십시오:\n- " + "\n- ".join(check_res.issues)
                        raw_output = await execute_bot_task(
                            bot_id=bot_id,
                            title=title,
                            deliverable=deliverable,
                            course_name=channel_info["name"],
                            unit=unit,
                            teacher_request=anonymized_content,
                            extra_context=extra_ctx,
                            feedback_instructions=feedback_prompt
                        )
                        # Re-check after retry
                        check_res = check_rubric(raw_output, allowed_codes=curriculum_codes)
                    check_info = check_res.to_dict()

                # Rule 6: Seteuk Check for record bot
                elif bot_id == "record":
                    check_res = check_seteuk(raw_output)
                    check_info = check_res.to_dict()

                # If curriculum bot, extract standard codes for downstream bots
                if bot_id == "curriculum":
                    found = re.findall(r"\[([0-9]{2}[가-힣A-Za-z0-9-]+)\]", raw_output)
                    for c in found:
                        if c not in curriculum_codes:
                            curriculum_codes.append(c)

                # Deanonymize for local display & file storage
                restored_output = deanonymize_text(raw_output, restore_map)

                # Save file
                saved_path = save_task_deliverable(abs_work_dir, t_id, restored_output)
                async with get_db_connection() as db:
                    await db.execute(
                        "UPDATE tasks SET status = 'done', output_path = ? WHERE id = ?",
                        (saved_path, t_id)
                    )
                    await db.commit()

                await event_bus.publish(request_id, "task_update", {
                    "task_id": t_id,
                    "status": "done",
                    "output_path": saved_path,
                    "check_info": check_info
                })
                return {
                    "id": t_id,
                    "bot_id": bot_id,
                    "title": title,
                    "content": restored_output,
                    "status": "done",
                    "output_path": saved_path,
                    "check_info": check_info
                }

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
                return {
                    "id": t_id,
                    "bot_id": bot_id,
                    "title": title,
                    "content": f"오류 발생: {err_msg}",
                    "status": "failed",
                    "error_message": err_msg
                }

        # Run Stage 1
        await event_bus.publish(request_id, "status", {"message": "선행 과업을 수행하고 있습니다..."})
        stage1_results = await asyncio.gather(*(execute_and_verify_task(dt, base_extra) for dt in stage1_tasks))
        task_results.extend(stage1_results)

        for res in stage1_results:
            task_outputs[res["bot_id"]] = res.get("content", "")

        # Run Stage 2 with stage 1 outputs injected
        if stage2_tasks:
            await event_bus.publish(request_id, "status", {"message": "후행 연계 과업을 수행하고 있습니다..."})
            stage2_extra = base_extra
            for b_id, out_text in task_outputs.items():
                stage2_extra += f"--- [선행 과업 산출물 (@{b_id})] ---\n{out_text}\n\n"

            stage2_results = await asyncio.gather(*(execute_and_verify_task(dt, stage2_extra) for dt in stage2_tasks))
            task_results.extend(stage2_results)

        # 11. Check results for failures
        has_failures = any(tr.get("status") == "failed" for tr in task_results)

        report_items = []
        for tr in task_results:
            report_items.append({
                "task_id": tr["id"],
                "bot_id": tr["bot_id"],
                "title": tr["title"],
                "status": tr["status"],
                "output_path": tr.get("output_path", ""),
                "error_message": tr.get("error_message", ""),
                "check_info": tr.get("check_info")
            })

        report_msg_id = f"msg_{uuid.uuid4().hex[:8]}"

        if has_failures:
            fail_summary = "일부 과업 수행 중 오류가 발생했습니다. 아래 작업 보고를 확인하시고 '실패 과업 재시도'를 진행해 주십시오."
            async with get_db_connection() as db:
                await db.execute(
                    """
                    INSERT INTO messages (id, channel_id, sender, type, content, metadata_json)
                    VALUES (?, ?, 'coordinator', 'report', ?, ?)
                    """,
                    (
                        report_msg_id,
                        channel_id,
                        fail_summary,
                        json.dumps({
                            "request_id": request_id,
                            "workspace_dir": rel_work_dir,
                            "tasks": report_items,
                            "has_failures": True,
                            "teacher_content": content
                        }, ensure_ascii=False)
                    )
                )
                await db.commit()

            await event_bus.publish(request_id, "completed", {
                "request_id": request_id,
                "report_message_id": report_msg_id,
                "summary": fail_summary,
                "has_failures": True
            })
            return

        # 12. Coordinator summarization & final approval question
        await event_bus.publish(request_id, "status", {"message": "코디봇이 결과를 취합하고 결재 질문을 정리하고 있습니다..."})
        summary_result = await summarize_and_finalize_approval(
            initial_question=plan.approval_question,
            task_results=task_results
        )

        summary_text = summary_result["summary"]
        final_approval_question = summary_result["approval_question"]

        # 13. Create approval record and cards
        appr_id = f"appr_{uuid.uuid4().hex[:8]}"
        async with get_db_connection() as db:
            await db.execute(
                """
                INSERT INTO approvals (id, request_id, question, status)
                VALUES (?, ?, ?, 'pending')
                """,
                (appr_id, request_id, final_approval_question)
            )

            # Create ReportCard message with check_info
            await db.execute(
                """
                INSERT INTO messages (id, channel_id, sender, type, content, metadata_json)
                VALUES (?, ?, 'coordinator', 'report', ?, ?)
                """,
                (
                    report_msg_id,
                    channel_id,
                    summary_text,
                    json.dumps({
                        "request_id": request_id,
                        "workspace_dir": rel_work_dir,
                        "tasks": report_items,
                        "has_failures": False
                    }, ensure_ascii=False)
                )
            )

            # Create ApprovalCard message
            appr_msg_id = f"msg_{uuid.uuid4().hex[:8]}"
            await db.execute(
                """
                INSERT INTO messages (id, channel_id, sender, type, content, metadata_json)
                VALUES (?, ?, 'coordinator', 'approval', ?, ?)
                """,
                (
                    appr_msg_id,
                    channel_id,
                    final_approval_question,
                    json.dumps({
                        "request_id": request_id,
                        "approval_id": appr_id,
                        "attempt": attempt,
                        "parent_request_id": parent_request_id,
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
            "approval_question": final_approval_question,
            "has_failures": False
        })

    except Exception as e:
        logger_msg = f"요청 처리 중 오류 발생: {e}"
        err_msg_id = f"msg_{uuid.uuid4().hex[:8]}"
        try:
            async with get_db_connection() as db:
                await db.execute(
                    """
                    INSERT INTO messages (id, channel_id, sender, type, content, metadata_json)
                    VALUES (?, ?, 'coordinator', 'text', ?, ?)
                    """,
                    (
                        err_msg_id,
                        channel_id,
                        f"⚠️ 요청 처리 중 오류가 발생했습니다: {e}",
                        json.dumps({"request_id": request_id, "error": str(e)}, ensure_ascii=False)
                    )
                )
                await db.commit()
        except Exception as db_err:
            logger.error(f"Failed to save error message to DB: {db_err}")

        await event_bus.publish(request_id, "error", {"message": logger_msg, "error_message_id": err_msg_id})

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
            (teacher_msg_id, channel_id, "teacher", "text", content, json.dumps({"request_id": request_id, "attempt": 0}))
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

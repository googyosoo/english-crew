import uuid
from typing import Optional, List
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException

from backend.app.db.database import get_db_connection
from backend.app.services.scheduler import execute_routine

router = APIRouter(prefix="/routines", tags=["routines"])

class RoutineCreate(BaseModel):
    name: str
    channel_id: str
    prompt: str
    day_of_week: str
    time: str
    enabled: bool = True

class RoutineUpdate(BaseModel):
    name: Optional[str] = None
    channel_id: Optional[str] = None
    prompt: Optional[str] = None
    day_of_week: Optional[str] = None
    time: Optional[str] = None
    enabled: Optional[bool] = None

@router.get("")
async def list_routines():
    """
    등록된 모든 루틴 목록을 조회합니다. 채널 정보도 함께 제공합니다.
    """
    async with get_db_connection() as db:
        query = """
        SELECT r.id, r.name, r.channel_id, r.prompt, r.day_of_week, r.time,
               r.enabled, r.last_run_at, r.created_at, r.updated_at,
               c.name as channel_name, c.course as channel_course
        FROM routines r
        LEFT JOIN channels c ON r.channel_id = c.id
        ORDER BY r.created_at DESC
        """
        async with db.execute(query) as cursor:
            rows = await cursor.fetchall()
            return [
                {
                    "id": r["id"],
                    "name": r["name"],
                    "channel_id": r["channel_id"],
                    "channel_name": r["channel_name"] or r["channel_id"],
                    "channel_course": r["channel_course"],
                    "prompt": r["prompt"],
                    "day_of_week": r["day_of_week"],
                    "time": r["time"],
                    "enabled": bool(r["enabled"]),
                    "last_run_at": r["last_run_at"],
                    "created_at": r["created_at"],
                    "updated_at": r["updated_at"]
                }
                for r in rows
            ]

@router.post("")
async def create_routine(payload: RoutineCreate):
    """
    새로운 루틴을 등록합니다.
    """
    routine_id = f"rtn_{uuid.uuid4().hex[:8]}"
    async with get_db_connection() as db:
        # Check channel existence
        async with db.execute("SELECT id FROM channels WHERE id = ?", (payload.channel_id,)) as cursor:
            ch = await cursor.fetchone()
            if not ch:
                raise HTTPException(status_code=400, detail="유효하지 않은 채널 ID입니다.")

        await db.execute(
            """
            INSERT INTO routines (id, name, channel_id, prompt, day_of_week, time, enabled)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                routine_id,
                payload.name.strip(),
                payload.channel_id,
                payload.prompt.strip(),
                payload.day_of_week.strip(),
                payload.time.strip(),
                1 if payload.enabled else 0
            )
        )
        await db.commit()

    return {"id": routine_id, "status": "created"}

@router.patch("/{routine_id}")
async def update_routine(routine_id: str, payload: RoutineUpdate):
    """
    루틴 정보를 수정하거나 활성화/비활성화 상태를 토글합니다.
    """
    async with get_db_connection() as db:
        async with db.execute("SELECT * FROM routines WHERE id = ?", (routine_id,)) as cursor:
            existing = await cursor.fetchone()
            if not existing:
                raise HTTPException(status_code=404, detail="루틴을 찾을 수 없습니다.")

        updates = []
        params = []
        if payload.name is not None:
            updates.append("name = ?")
            params.append(payload.name.strip())
        if payload.channel_id is not None:
            updates.append("channel_id = ?")
            params.append(payload.channel_id)
        if payload.prompt is not None:
            updates.append("prompt = ?")
            params.append(payload.prompt.strip())
        if payload.day_of_week is not None:
            updates.append("day_of_week = ?")
            params.append(payload.day_of_week.strip())
        if payload.time is not None:
            updates.append("time = ?")
            params.append(payload.time.strip())
        if payload.enabled is not None:
            updates.append("enabled = ?")
            params.append(1 if payload.enabled else 0)

        if updates:
            updates.append("updated_at = CURRENT_TIMESTAMP")
            params.append(routine_id)
            sql = f"UPDATE routines SET {', '.join(updates)} WHERE id = ?"
            await db.execute(sql, params)
            await db.commit()

    return {"id": routine_id, "status": "updated"}

@router.delete("/{routine_id}")
async def delete_routine(routine_id: str):
    """
    루틴을 삭제합니다.
    """
    async with get_db_connection() as db:
        cursor = await db.execute("DELETE FROM routines WHERE id = ?", (routine_id,))
        await db.commit()
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="루틴을 찾을 수 없습니다.")

    return {"id": routine_id, "status": "deleted"}

@router.post("/{routine_id}/run")
async def run_routine_now(routine_id: str):
    """
    지정된 루틴을 즉시 1회 실행합니다. (수동 트리거 및 테스트용)
    결과는 일반 요청과 동일하게 결재 대기 카드로 생성됩니다.
    """
    req_id = await execute_routine(routine_id)
    if not req_id:
        raise HTTPException(status_code=404, detail="루틴을 찾을 수 없거나 실행에 실패했습니다.")

    return {
        "status": "triggered",
        "routine_id": routine_id,
        "request_id": req_id
    }

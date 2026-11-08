import asyncio
import logging
import uuid
import json
from datetime import datetime
from typing import List, Optional, Set

from backend.app.db.database import get_db_connection

logger = logging.getLogger(__name__)

DAY_MAP = {
    "mon": 0, "monday": 0, "월": 0, "월요일": 0,
    "tue": 1, "tuesday": 1, "화": 1, "화요일": 1,
    "wed": 2, "wednesday": 2, "수": 2, "수요일": 2,
    "thu": 3, "thursday": 3, "목": 3, "목요일": 3,
    "fri": 4, "friday": 4, "금": 4, "금요일": 4,
    "sat": 5, "saturday": 5, "토": 5, "토요일": 5,
    "sun": 6, "sunday": 6, "일": 6, "일요일": 6,
}

def parse_days(day_str: str) -> Set[int]:
    """
    요일 문자열(예: 'mon,wed,fri', '월,수,금', 'everyday', '매일')을
    weekday 정수 세트 (0=월 ~ 6=일)로 파싱합니다.
    """
    clean = day_str.strip().lower()
    if clean in ("everyday", "매일", "*", "all"):
        return {0, 1, 2, 3, 4, 5, 6}
    
    days = set()
    parts = [p.strip() for p in clean.replace("/", ",").split(",") if p.strip()]
    for p in parts:
        if p in DAY_MAP:
            days.add(DAY_MAP[p])
        elif p.isdigit():
            val = int(p)
            if 0 <= val <= 6:
                days.add(val)
    return days

def should_run_now(routine: dict, now_dt: datetime) -> bool:
    """
    현재 시각이 루틴의 실행 예정 시각과 일치하는지 판단합니다.
    """
    if not routine.get("enabled"):
        return False
    
    target_days = parse_days(routine.get("day_of_week", ""))
    if now_dt.weekday() not in target_days:
        return False
    
    current_time_str = now_dt.strftime("%H:%M")
    routine_time = routine.get("time", "").strip()
    if current_time_str != routine_time:
        return False
    
    # 중복 실행 방지: 오늘 이미 이 시각(또는 오늘)에 실행되었는지 확인
    last_run_at = routine.get("last_run_at")
    if last_run_at:
        try:
            # ISO format 또는 YYYY-MM-DD HH:MM
            last_dt = datetime.fromisoformat(str(last_run_at))
            if last_dt.date() == now_dt.date() and last_dt.strftime("%H:%M") == current_time_str:
                return False
        except Exception:
            pass

    return True

def is_missed(routine: dict, now_dt: datetime) -> bool:
    """
    백엔드 시작 시 오늘 예정된 시각이 이미 지났는데 실행되지 않았는지(놓쳤는지) 검사합니다.
    """
    if not routine.get("enabled"):
        return False
    
    target_days = parse_days(routine.get("day_of_week", ""))
    if now_dt.weekday() not in target_days:
        return False
    
    routine_time = routine.get("time", "").strip()
    try:
        r_hour, r_minute = map(int, routine_time.split(":"))
    except Exception:
        return False
    
    # 오늘의 예정 시각
    scheduled_dt = now_dt.replace(hour=r_hour, minute=r_minute, second=0, microsecond=0)
    
    # 현재 시각보다 이전이어야 함 (이미 지나감)
    if scheduled_dt > now_dt:
        return False
    
    # 마지막 실행 시각 확인
    last_run_at = routine.get("last_run_at")
    if last_run_at:
        try:
            last_dt = datetime.fromisoformat(str(last_run_at))
            # 오늘 예정 시각 이후에 이미 실행된 적이 있다면 놓친 것이 아님
            if last_dt >= scheduled_dt:
                return False
        except Exception:
            pass

    return True

async def execute_routine(routine_id: str) -> Optional[str]:
    """
    루틴을 1회 실행합니다.
    일반 요청 처리 파이프라인(process_teacher_request)을 트리거하고 결재 대기 카드를 생성합니다.
    """
    from backend.app.routers.channels import process_teacher_request

    async with get_db_connection() as db:
        async with db.execute("SELECT * FROM routines WHERE id = ?", (routine_id,)) as cursor:
            row = await cursor.fetchone()
            if not row:
                logger.error(f"Routine not found: {routine_id}")
                return None
            routine = dict(row)

    request_id = f"req_{uuid.uuid4().hex[:8]}"
    teacher_msg_id = f"msg_{uuid.uuid4().hex[:8]}"
    channel_id = routine["channel_id"]
    routine_name = routine["name"]
    raw_prompt = routine["prompt"]
    content = f"[루틴: {routine_name}] {raw_prompt}"

    # 교사 메시지로 등록
    async with get_db_connection() as db:
        await db.execute(
            """
            INSERT INTO messages (id, channel_id, sender, type, content, metadata_json)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                teacher_msg_id,
                channel_id,
                "teacher",
                "text",
                content,
                json.dumps({
                    "request_id": request_id,
                    "routine_id": routine_id,
                    "routine_name": routine_name,
                    "is_routine": True
                }, ensure_ascii=False)
            )
        )
        # last_run_at 업데이트
        now_str = datetime.now().isoformat()
        await db.execute(
            "UPDATE routines SET last_run_at = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (now_str, routine_id)
        )
        await db.commit()

    logger.info(f"Triggering routine '{routine_name}' (Request ID: {request_id})")

    # 백그라운드 파이프라인 실행 (결재 대기 카드로 종료)
    asyncio.create_task(process_teacher_request(request_id, channel_id, content))
    return request_id

async def run_scheduler_cycle(now_dt: Optional[datetime] = None) -> List[str]:
    """
    1회 주기 스케줄 검사 및 실행
    """
    if now_dt is None:
        now_dt = datetime.now()

    executed_ids = []
    async with get_db_connection() as db:
        async with db.execute("SELECT * FROM routines WHERE enabled = 1") as cursor:
            rows = await cursor.fetchall()
            routines = [dict(r) for r in rows]

    for r in routines:
        if should_run_now(r, now_dt):
            logger.info(f"Routine '{r['name']}' schedule matched ({now_dt.strftime('%A %H:%M')}). Executing...")
            req_id = await execute_routine(r["id"])
            if req_id:
                executed_ids.append(r["id"])

    return executed_ids

async def startup_catchup(now_dt: Optional[datetime] = None) -> List[str]:
    """
    앱 시작 시 놓친 실행이 있는 루틴을 찾아 1회 보충 실행합니다.
    """
    if now_dt is None:
        now_dt = datetime.now()

    catchup_ids = []
    async with get_db_connection() as db:
        async with db.execute("SELECT * FROM routines WHERE enabled = 1") as cursor:
            rows = await cursor.fetchall()
            routines = [dict(r) for r in rows]

    for r in routines:
        if is_missed(r, now_dt):
            logger.info(f"Routine '{r['name']}' missed its run today. Executing 1-time catchup...")
            req_id = await execute_routine(r["id"])
            if req_id:
                catchup_ids.append(r["id"])

    return catchup_ids

_scheduler_task: Optional[asyncio.Task] = None

async def scheduler_loop():
    """
    앱 실행 중 30초 간격으로 스케줄을 감시하는 루프
    """
    logger.info("Routine scheduler loop started.")
    try:
        # 1. 앱 시작 시 놓친 실행 1회 보충
        await startup_catchup()

        while True:
            await asyncio.sleep(30)
            await run_scheduler_cycle()
    except asyncio.CancelledError:
        logger.info("Routine scheduler loop cancelled.")
    except Exception as e:
        logger.error(f"Error in routine scheduler loop: {e}", exc_info=True)

def start_scheduler():
    global _scheduler_task
    if _scheduler_task is None or _scheduler_task.done():
        _scheduler_task = asyncio.create_task(scheduler_loop())

def stop_scheduler():
    global _scheduler_task
    if _scheduler_task and not _scheduler_task.done():
        _scheduler_task.cancel()

import uuid
from fastapi import APIRouter, HTTPException
from typing import List, Optional
from pydantic import BaseModel

from backend.app.db.database import get_db_connection
from backend.app.models.schemas import ContextNoteCreate, StudentCreate

router = APIRouter(tags=["context"])

@router.get("/channels/{channel_id}/context")
async def get_channel_context(channel_id: str, unit: Optional[str] = None):
    async with get_db_connection() as db:
        # Get channel info to find course_code
        ch_cur = await db.execute("SELECT * FROM channels WHERE id = ?", (channel_id,))
        channel = await ch_cur.fetchone()
        if not channel:
            raise HTTPException(status_code=404, detail="Channel not found")

        course_code = channel["course_code"]
        if not course_code and channel["type"] == "all":
            course_code = "COMMON"

        query = "SELECT * FROM context_notes WHERE course_code = ?"
        params = [course_code]
        if unit:
            query += " AND unit = ?"
            params.append(unit)
        query += " ORDER BY created_at DESC"

        cur = await db.execute(query, tuple(params))
        rows = await cur.fetchall()
        return [dict(r) for r in rows]


@router.post("/channels/{channel_id}/context")
async def save_channel_context(channel_id: str, note: ContextNoteCreate):
    async with get_db_connection() as db:
        ch_cur = await db.execute("SELECT * FROM channels WHERE id = ?", (channel_id,))
        channel = await ch_cur.fetchone()
        if not channel:
            raise HTTPException(status_code=404, detail="Channel not found")

        course_code = note.course_code or channel["course_code"] or "COMMON"
        note_id = f"note_{uuid.uuid4().hex[:8]}"

        # If kind == '본문' or '진도', update existing note for this course_code & unit to prevent duplicate clutter
        if note.kind in ["본문", "진도"]:
            exist_cur = await db.execute(
                "SELECT id FROM context_notes WHERE course_code = ? AND unit = ? AND kind = ?",
                (course_code, note.unit, note.kind)
            )
            existing = await exist_cur.fetchone()
            if existing:
                await db.execute(
                    "UPDATE context_notes SET content = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (note.content, existing["id"])
                )
                await db.commit()
                return {"status": "ok", "action": "updated", "id": existing["id"]}

        # Otherwise insert new
        await db.execute(
            """
            INSERT INTO context_notes (id, course_code, unit, kind, content)
            VALUES (?, ?, ?, ?, ?)
            """,
            (note_id, course_code, note.unit, note.kind, note.content)
        )
        await db.commit()
        return {"status": "ok", "action": "created", "id": note_id}


@router.delete("/context/{note_id}")
async def delete_context_note(note_id: str):
    async with get_db_connection() as db:
        await db.execute("DELETE FROM context_notes WHERE id = ?", (note_id,))
        await db.commit()
        return {"status": "ok", "deleted_id": note_id}


@router.get("/channels/{channel_id}/students")
async def get_students(channel_id: str):
    async with get_db_connection() as db:
        ch_cur = await db.execute("SELECT * FROM channels WHERE id = ?", (channel_id,))
        channel = await ch_cur.fetchone()
        if not channel:
            raise HTTPException(status_code=404, detail="Channel not found")

        course_code = channel["course_code"] or "COMMON"
        cur = await db.execute(
            "SELECT * FROM students WHERE course_code = ? ORDER BY class_no, student_no",
            (course_code,)
        )
        rows = await cur.fetchall()
        return [dict(r) for r in rows]


@router.post("/channels/{channel_id}/students")
async def add_students(channel_id: str, students: List[StudentCreate]):
    async with get_db_connection() as db:
        ch_cur = await db.execute("SELECT * FROM channels WHERE id = ?", (channel_id,))
        channel = await ch_cur.fetchone()
        if not channel:
            raise HTTPException(status_code=404, detail="Channel not found")

        course_code = channel["course_code"] or "COMMON"
        for st in students:
            st_id = f"st_{uuid.uuid4().hex[:8]}"
            await db.execute(
                """
                INSERT INTO students (id, course_code, class_no, student_no, name)
                VALUES (?, ?, ?, ?, ?)
                """,
                (st_id, course_code, st.class_no, st.student_no, st.name)
            )
        await db.commit()
        return {"status": "ok", "count": len(students)}

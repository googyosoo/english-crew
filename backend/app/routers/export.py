import os
import urllib.parse
from pathlib import Path
from typing import Optional
from pydantic import BaseModel

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse

from backend.app.db.database import get_db_connection
from backend.app.services.exporter import (
    export_request_document,
    get_default_export_dir,
    assemble_request_content
)

router = APIRouter(tags=["export"])

class ExportDirPayload(BaseModel):
    export_dir: str

@router.get("/settings/export_dir")
async def get_export_dir_setting():
    async with get_db_connection() as db:
        async with db.execute("SELECT value FROM settings WHERE key = 'export_dir'") as cursor:
            row = await cursor.fetchone()
            if row:
                return {"export_dir": row["value"]}
    default_dir = str(get_default_export_dir())
    return {"export_dir": default_dir}

@router.post("/settings/export_dir")
async def set_export_dir_setting(payload: ExportDirPayload):
    p = Path(payload.export_dir)
    p.mkdir(parents=True, exist_ok=True)
    async with get_db_connection() as db:
        await db.execute(
            """
            INSERT INTO settings (key, value) VALUES ('export_dir', ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (str(p),)
        )
        await db.commit()
    return {"export_dir": str(p), "status": "saved"}

@router.get("/requests/{request_id}/export")
async def export_request(
    request_id: str,
    format: str = Query("docx", pattern="^(docx|md)$"),
    target_dir: Optional[str] = None
):
    """
    결재 승인된 요청의 산출물을 docx 또는 md로 내보냅니다.
    """
    # Verify approval status
    async with get_db_connection() as db:
        async with db.execute(
            "SELECT status FROM approvals WHERE request_id = ?",
            (request_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if not row or row["status"] != "approved":
                raise HTTPException(
                    status_code=400,
                    detail="결재 승인된 요청만 내보낼 수 있습니다."
                )

        # If target_dir not provided, fetch from settings
        if not target_dir:
            async with db.execute("SELECT value FROM settings WHERE key = 'export_dir'") as s_cur:
                s_row = await s_cur.fetchone()
                if s_row:
                    target_dir = s_row["value"]

    try:
        file_path, filename = await export_request_document(
            request_id=request_id,
            export_format=format,
            target_dir=target_dir
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"내보내기 실패: {str(e)}")

    encoded_filename = urllib.parse.quote(filename)
    encoded_filepath = urllib.parse.quote(str(file_path))
    media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document" if format == "docx" else "text/markdown"

    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type=media_type,
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}",
            "X-Exported-Path": encoded_filepath
        }
    )

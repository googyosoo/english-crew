from typing import Optional
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException

from backend.app.services.gemini_client import get_gemini_config, set_gemini_api_key

router = APIRouter(prefix="/settings", tags=["settings"])

class ApiKeyPayload(BaseModel):
    api_key: str
    model: Optional[str] = None

@router.get("/api_key")
async def get_api_key_status():
    """
    현재 등록된 Gemini API 키의 설정 여부 및 마스킹된 형태를 확인합니다.
    """
    config = get_gemini_config()
    raw_key = config.get("api_key", "").strip()
    is_configured = bool(raw_key and len(raw_key) > 8)

    masked = ""
    if is_configured:
        masked = f"{raw_key[:4]}...{raw_key[-4:]}"

    return {
        "configured": is_configured,
        "masked_key": masked,
        "model": config.get("model", "gemini-2.5-flash")
    }

@router.post("/api_key")
async def save_api_key(payload: ApiKeyPayload):
    """
    Gemini API 키를 안전하게 저장합니다. (로그 및 콘솔에 키 원문 출력 절대 금지)
    """
    clean_key = payload.api_key.strip()
    if not clean_key or len(clean_key) < 8:
        raise HTTPException(status_code=400, detail="유효한 Gemini API 키를 입력해 주세요.")

    try:
        set_gemini_api_key(api_key=clean_key, model=payload.model)
        return {
            "status": "saved",
            "configured": True,
            "masked_key": f"{clean_key[:4]}...{clean_key[-4:]}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"API 키 저장 실패: {str(e)}")

from fastapi import APIRouter
from backend.app.services.gemini_client import get_gemini_config

router = APIRouter()

@router.get("/health")
async def health_check():
    cfg = get_gemini_config()
    api_key = cfg.get("api_key", "").strip()
    model = cfg.get("model", "gemini-2.5-flash")

    gemini_status = "configured" if api_key else "missing_key"

    return {
        "status": "ok",
        "gemini": gemini_status,
        "model": model
    }

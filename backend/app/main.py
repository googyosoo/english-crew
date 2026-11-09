import os
import sys
import argparse
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.staticfiles import StaticFiles

from backend.app.db.database import init_db
from backend.app.routers import health, channels, approvals, context, export, routines, settings
from backend.app.services.scheduler import start_scheduler, stop_scheduler

def get_frontend_dist_dir() -> Path | None:
    # 1. PyInstaller bundled directory
    if hasattr(sys, "_MEIPASS"):
        meipass_dist = Path(sys._MEIPASS) / "frontend" / "dist"
        if meipass_dist.exists():
            return meipass_dist

    # 2. Local workspace directory
    backend_app_dir = Path(__file__).resolve().parent
    local_dist = backend_app_dir.parent.parent / "frontend" / "dist"
    if local_dist.exists():
        return local_dist

    # 3. Packaged executable directory relatives
    exe_dir = Path(sys.executable).resolve().parent
    candidates = [
        exe_dir / "resources" / "app" / "frontend" / "dist",
        exe_dir / "resources" / "frontend" / "dist",
        exe_dir.parent / "frontend" / "dist",
        exe_dir / "frontend" / "dist",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate

    return None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Phase 4-3c Security: Fail-closed verification on startup
    expected_token = os.environ.get("CREW_API_TOKEN")
    dev_no_auth = os.environ.get("CREW_DEV_NO_AUTH", "0") == "1"
    if not expected_token and not dev_no_auth:
        sys.stderr.write("FATAL: CREW_API_TOKEN is missing. Server startup aborted in fail-closed mode.\n")
        sys.stderr.flush()
        raise RuntimeError("FATAL: CREW_API_TOKEN is missing. Server startup aborted in fail-closed mode.")

    # Startup: ensure tables and seeds exist
    await init_db()
    # Start routine background scheduler & catchup
    start_scheduler()
    yield
    # Shutdown logic
    stop_scheduler()

app = FastAPI(
    title="English Crew Backend",
    version="0.2.0",
    lifespan=lifespan
)

API_PREFIXES = (
    "/channels",
    "/approvals",
    "/context",
    "/export",
    "/requests",
    "/routines",
    "/settings"
)

# 1. Token Verification Middleware (Phase 4-3c Security)
# Require X-Crew-Token header or ?token= query parameter on API endpoints except /health
@app.middleware("http")
async def verify_crew_token(request: Request, call_next):
    # CORS preflight OPTIONS requests are handled without token check
    if request.method == "OPTIONS":
        return await call_next(request)

    # Exclude /health endpoint from token verification
    if request.url.path == "/health":
        return await call_next(request)

    # Only API routes require authentication. Static files and index.html are served publicly.
    is_api_request = any(request.url.path.startswith(prefix) for prefix in API_PREFIXES)
    if not is_api_request:
        return await call_next(request)

    dev_no_auth = os.environ.get("CREW_DEV_NO_AUTH", "0") == "1"
    if dev_no_auth:
        return await call_next(request)

    expected_token = os.environ.get("CREW_API_TOKEN")
    if not expected_token:
        return JSONResponse(
            status_code=401,
            content={"detail": "Unauthorized: CREW_API_TOKEN is missing (fail-closed)"}
        )

    # Check X-Crew-Token header
    token = request.headers.get("X-Crew-Token")
    # Check query parameter (for SSE and file export downloads)
    if not token:
        token = request.query_params.get("token") or request.query_params.get("crew_token")

    if not token or token != expected_token:
        return JSONResponse(
            status_code=401,
            content={"detail": "Unauthorized: Invalid or missing X-Crew-Token"}
        )

    return await call_next(request)

# 2. CORS Configuration (Phase 4-3b Security)
# Remove allow_origins="*". Allow http://127.0.0.1:5173 only in dev mode, allow_credentials=False.
is_dev_mode = (os.environ.get("ENV") != "production") and (os.environ.get("CREW_DEV_MODE", "1") == "1")
if os.environ.get("CREW_USER_DATA_DIR") and os.environ.get("CREW_DEV_MODE") != "1":
    # Packaged Electron production mode
    is_dev_mode = False

allowed_origins = ["http://127.0.0.1:5173"] if is_dev_mode else []

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(channels.router)
app.include_router(approvals.router)
app.include_router(context.router)
app.include_router(export.router)
app.include_router(routines.router)
app.include_router(settings.router)

# Phase 4-3c: Mount frontend/dist as static files for packaged mode
frontend_dist = get_frontend_dist_dir()
if frontend_dist and (frontend_dist / "index.html").exists():
    app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    expected_token = os.environ.get("CREW_API_TOKEN")
    dev_no_auth = os.environ.get("CREW_DEV_NO_AUTH", "0") == "1"
    if not expected_token and not dev_no_auth:
        sys.stderr.write("FATAL: CREW_API_TOKEN is missing. Server startup aborted in fail-closed mode.\n")
        sys.stderr.flush()
        sys.exit(1)

    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=int(os.environ.get("CREW_PORT", "8765")))
    parser.add_argument("--host", type=str, default="127.0.0.1")
    args, _ = parser.parse_known_args()

    uvicorn.run(app, host=args.host, port=args.port, access_log=False)

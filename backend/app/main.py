import os
import argparse
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from backend.app.db.database import init_db
from backend.app.routers import health, channels, approvals, context, export, routines, settings
from backend.app.services.scheduler import start_scheduler, stop_scheduler

@asynccontextmanager
async def lifespan(app: FastAPI):
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

# 1. Token Verification Middleware (Phase 4-3b Security)
# Require X-Crew-Token header or ?token= query parameter on all endpoints except /health
@app.middleware("http")
async def verify_crew_token(request: Request, call_next):
    # CORS preflight OPTIONS requests are handled without token check
    if request.method == "OPTIONS":
        return await call_next(request)

    # Exclude /health endpoint from token verification
    if request.url.path == "/health":
        return await call_next(request)

    expected_token = os.environ.get("CREW_API_TOKEN")
    if expected_token:
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

if __name__ == "__main__":
    import uvicorn
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=int(os.environ.get("CREW_PORT", "8765")))
    parser.add_argument("--host", type=str, default="127.0.0.1")
    args, _ = parser.parse_known_args()

    uvicorn.run(app, host=args.host, port=args.port)

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.db.database import init_db
from backend.app.routers import health, channels, approvals, context, export, routines
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

# Enable CORS for Electron / Vite
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(channels.router)
app.include_router(approvals.router)
app.include_router(context.router)
app.include_router(export.router)
app.include_router(routines.router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host="127.0.0.1", port=8765, reload=False)

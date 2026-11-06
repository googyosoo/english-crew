import os
import aiosqlite
from pathlib import Path

from contextlib import asynccontextmanager

# Base workspace directory (parent of backend)
WORKSPACE_DIR = Path(__file__).resolve().parent.parent.parent.parent

def get_data_dir() -> Path:
    custom_dir = os.getenv("CREW_DATA_DIR")
    if custom_dir:
        return Path(custom_dir)
    return WORKSPACE_DIR / "data"

def get_db_path() -> Path:
    return get_data_dir() / "crew.db"

@asynccontextmanager
async def get_db_connection():
    data_dir = get_data_dir()
    data_dir.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(str(get_db_path())) as db:
        db.row_factory = aiosqlite.Row
        yield db

async def init_db():
    get_data_dir().mkdir(parents=True, exist_ok=True)
    async with get_db_connection() as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS channels (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                type TEXT NOT NULL,
                course_code TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS bots (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                role TEXT NOT NULL,
                prompt_dir TEXT NOT NULL,
                model TEXT NOT NULL,
                enabled INTEGER NOT NULL DEFAULT 1
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                channel_id TEXT NOT NULL,
                sender TEXT NOT NULL,
                type TEXT NOT NULL,
                content TEXT,
                metadata_json TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (channel_id) REFERENCES channels (id)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                request_id TEXT NOT NULL,
                bot_id TEXT NOT NULL,
                title TEXT NOT NULL,
                deliverable TEXT NOT NULL,
                status TEXT NOT NULL,
                output_path TEXT,
                error_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (bot_id) REFERENCES bots (id)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS approvals (
                id TEXT PRIMARY KEY,
                request_id TEXT NOT NULL,
                question TEXT NOT NULL,
                status TEXT NOT NULL,
                reason TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.commit()

        # Seed channels if empty
        cursor = await db.execute("SELECT COUNT(*) FROM channels")
        channel_count = (await cursor.fetchone())[0]
        if channel_count == 0:
            seed_channels = [
                ("general", "전체 교무회의", "all", None),
                ("eng1", "영어I", "course", "ENG1"),
                ("adv_eng1", "심화영어I", "course", "ADV_ENG1"),
                ("adv_read1", "심화영어독해I", "course", "ADV_READ1"),
                ("career_eng", "진로영어", "course", "CAREER_ENG"),
            ]
            await db.executemany(
                "INSERT INTO channels (id, name, type, course_code) VALUES (?, ?, ?, ?)",
                seed_channels
            )

        # Seed bots if empty
        cursor = await db.execute("SELECT COUNT(*) FROM bots")
        bot_count = (await cursor.fetchone())[0]
        if bot_count == 0:
            env_model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
            seed_bots = [
                ("coordinator", "코디봇", "총괄·디스패치", "backend/agents/coordinator", env_model, 1),
                ("curriculum", "교육과정봇", "성취기준·팩트체크", "backend/agents/curriculum", env_model, 0),
                ("lesson", "수업봇", "차시·활동 설계", "backend/agents/lesson", env_model, 0),
                ("assessment", "평가봇", "문항·루브릭", "backend/agents/assessment", env_model, 1),
                ("record", "기록봇", "관찰·세특", "backend/agents/record", env_model, 0),
            ]
            await db.executemany(
                "INSERT INTO bots (id, name, role, prompt_dir, model, enabled) VALUES (?, ?, ?, ?, ?, ?)",
                seed_bots
            )

        await db.commit()

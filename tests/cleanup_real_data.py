import asyncio
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Ensure we are pointing to the real data directory
if "CREW_DATA_DIR" in os.environ:
    del os.environ["CREW_DATA_DIR"]

from backend.app.db.database import get_db_connection
from backend.app.services.workspace_manager import WORKSPACE_DIR

async def cleanup():
    async with get_db_connection() as db:
        await db.execute("DELETE FROM tasks WHERE id LIKE 'tsk_test%' OR id LIKE 'tsk_item%' OR id LIKE 'tsk_rubric%'")
        await db.execute("DELETE FROM approvals WHERE id LIKE 'appr_test%' OR id LIKE 'appr_sc%'")
        await db.execute("DELETE FROM messages WHERE id LIKE 'msg_sc_%' OR id LIKE 'msg_test_%' OR id LIKE 'msg_appr_%'")
        await db.execute("DELETE FROM messages WHERE metadata_json LIKE '%req_scenario_1%' OR metadata_json LIKE '%req_test_1%'")
        await db.commit()
        print("PASS: Real DB cleaned of test and seed records.")

    workspaces_dir = WORKSPACE_DIR / "data" / "workspaces"
    if workspaces_dir.exists():
        deleted = 0
        for f in workspaces_dir.rglob("*"):
            if f.is_file() and any(k in f.name for k in ["tsk_test_1", "tsk_item_writer", "tsk_rubric_creator"]):
                f.unlink(missing_ok=True)
                deleted += 1
        print(f"PASS: Real workspaces directory cleaned: {deleted} files removed.")

if __name__ == "__main__":
    asyncio.run(cleanup())

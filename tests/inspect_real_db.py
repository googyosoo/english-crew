import asyncio
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Ensure real data directory is used
if "CREW_DATA_DIR" in os.environ:
    del os.environ["CREW_DATA_DIR"]

from backend.app.db.database import get_db_connection

async def inspect():
    async with get_db_connection() as db:
        c = await db.execute("SELECT id, channel_id, sender, type, content, metadata_json, created_at FROM messages ORDER BY created_at ASC")
        rows = await c.fetchall()
        print(f"=== Messages (Total: {len(rows)}) ===")
        for r in rows:
            print(f"[{r['created_at']}] {r['type']} ({r['sender']}): {r['content']}")
            print(f"   meta: {r['metadata_json']}")

        tc = await db.execute("SELECT id, request_id, bot_id, title, deliverable, status, output_path, error_message FROM tasks")
        t_rows = await tc.fetchall()
        print(f"\n=== Tasks (Total: {len(t_rows)}) ===")
        for t in t_rows:
            print(f"[{t['id']}] bot={t['bot_id']} status={t['status']} path={t['output_path']}")
            print(f"   title={t['title']}, err={t['error_message']}")

        ac = await db.execute("SELECT id, request_id, question, status, reason FROM approvals")
        a_rows = await ac.fetchall()
        print(f"\n=== Approvals (Total: {len(a_rows)}) ===")
        for a in a_rows:
            print(f"[{a['id']}] status={a['status']}, question={a['question']}")

if __name__ == "__main__":
    asyncio.run(inspect())

import asyncio
import os
import sys
import shutil
import tempfile
import json
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Setup Isolated Test Data Directory before importing backend modules
temp_dir = tempfile.mkdtemp(prefix="crew_test_phase4_routines_")
os.environ["CREW_DATA_DIR"] = temp_dir

from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.db.database import init_db, get_db_connection
from backend.app.services.scheduler import (
    parse_days,
    should_run_now,
    is_missed,
    execute_routine,
    run_scheduler_cycle,
    startup_catchup
)

def test_day_parsing_and_schedule_matching():
    # 1. Day parsing
    days_mon_wed = parse_days("mon,wed")
    assert days_mon_wed == {0, 2}, f"Failed to parse mon,wed: {days_mon_wed}"

    days_everyday = parse_days("everyday")
    assert days_everyday == {0, 1, 2, 3, 4, 5, 6}

    days_korean = parse_days("월,금")
    assert days_korean == {0, 4}

    # 2. Schedule matching: should_run_now
    test_dt = datetime(2026, 11, 9, 9, 0, 0) # Monday 09:00 (weekday=0)
    routine_match = {
        "enabled": 1,
        "day_of_week": "mon,wed,fri",
        "time": "09:00",
        "last_run_at": None
    }
    assert should_run_now(routine_match, test_dt) is True

    # Different time -> False
    assert should_run_now(routine_match, test_dt.replace(minute=1)) is False

    # Different day -> False
    test_dt_tue = datetime(2026, 11, 10, 9, 0, 0) # Tuesday 09:00 (weekday=1)
    assert should_run_now(routine_match, test_dt_tue) is False

    # Disabled routine -> False
    routine_disabled = {**routine_match, "enabled": 0}
    assert should_run_now(routine_disabled, test_dt) is False

    # Already run at the exact same minute today -> False
    routine_already_run = {**routine_match, "last_run_at": test_dt.isoformat()}
    assert should_run_now(routine_already_run, test_dt) is False

    print("PASS: Schedule parsing and matching logic verified 100%!")

def test_startup_missed_catchup_logic():
    # Suppose current time is Monday 14:00
    now_dt = datetime(2026, 11, 9, 14, 0, 0)

    # Routine scheduled for Monday 09:00, never run
    routine_missed = {
        "enabled": 1,
        "day_of_week": "mon",
        "time": "09:00",
        "last_run_at": None
    }
    assert is_missed(routine_missed, now_dt) is True

    # Routine scheduled for Monday 16:00 (future today) -> Not missed
    routine_future = {
        "enabled": 1,
        "day_of_week": "mon",
        "time": "16:00",
        "last_run_at": None
    }
    assert is_missed(routine_future, now_dt) is False

    # Routine already executed today at 09:00 -> Not missed
    routine_completed = {
        "enabled": 1,
        "day_of_week": "mon",
        "time": "09:00",
        "last_run_at": datetime(2026, 11, 9, 9, 0, 10).isoformat()
    }
    assert is_missed(routine_completed, now_dt) is False

    print("PASS: 1-time catchup logic for missed runs verified 100%!")

def test_routines_api_crud_and_execution():
    client = TestClient(app)

    # 1. Create Routine
    payload = {
        "name": "월요 모의평가 어휘 퀴즈",
        "channel_id": "eng1",
        "prompt": "본문 없이 일반 주제로 어휘 퀴즈 5문항 출제해줘",
        "day_of_week": "mon,thu",
        "time": "08:30",
        "enabled": True
    }
    res = client.post("/routines", json=payload)
    assert res.status_code == 200, res.text
    routine_id = res.json()["id"]
    print("PASS: Created routine with ID:", routine_id)

    # 2. List Routines
    list_res = client.get("/routines")
    assert list_res.status_code == 200
    routines = list_res.json()
    assert len(routines) >= 1
    found = next((r for r in routines if r["id"] == routine_id), None)
    assert found is not None
    assert found["name"] == "월요 모의평가 어휘 퀴즈"
    assert found["channel_name"] == "영어Ⅰ"
    assert found["enabled"] is True

    # 3. Patch Routine (Toggle enabled & update prompt)
    patch_res = client.patch(f"/routines/{routine_id}", json={
        "enabled": False,
        "time": "09:15"
    })
    assert patch_res.status_code == 200
    check_res = client.get("/routines")
    updated = next(r for r in check_res.json() if r["id"] == routine_id)
    assert updated["enabled"] is False
    assert updated["time"] == "09:15"
    print("PASS: Patched routine (enabled toggled to False, time updated).")

    # Re-enable for execution test
    client.patch(f"/routines/{routine_id}", json={"enabled": True})

    # 4. Trigger Routine Execution (Manual Run)
    run_res = client.post(f"/routines/{routine_id}/run")
    assert run_res.status_code == 200, run_res.text
    run_data = run_res.json()
    assert run_data["status"] == "triggered"
    assert "request_id" in run_data
    req_id = run_data["request_id"]
    print(f"PASS: Routine triggered successfully with request_id={req_id}")

    # Verify that teacher message was stored in DB
    client_ch = client.get("/channels/eng1/messages")
    assert client_ch.status_code == 200
    messages = client_ch.json()
    routine_msg = next((m for m in messages if m.get("metadata", {}).get("routine_id") == routine_id), None)
    assert routine_msg is not None, "Routine teacher message should be recorded in DB"
    assert "[루틴: 월요 모의평가 어휘 퀴즈]" in routine_msg["content"]
    print("PASS: Routine message saved in channel with routine metadata!")

    # 5. Delete Routine
    del_res = client.delete(f"/routines/{routine_id}")
    assert del_res.status_code == 200
    del_check = client.get("/routines")
    assert not any(r["id"] == routine_id for r in del_check.json())
    print("PASS: Deleted routine verified.")

if __name__ == "__main__":
    try:
        asyncio.run(init_db())
        test_day_parsing_and_schedule_matching()
        test_startup_missed_catchup_logic()
        test_routines_api_crud_and_execution()
        print("\n=======================================================")
        print("ALL ISOLATED PHASE 4 ROUTINE TESTS PASSED 100%!")
        print("=======================================================")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
        print("PASS: Cleaned up isolated test temp directory.")

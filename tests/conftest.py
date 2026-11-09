import os
import shutil
import tempfile
import asyncio
import pytest
from backend.app.db.database import init_db

@pytest.fixture(autouse=True)
def isolated_test_environment(monkeypatch, request):
    """
    Phase 4-3e: Complete test isolation and pollution removal.
    - Runs each test in a dedicated, isolated temporary data directory.
    - Sets and cleans environment variables via monkeypatch.
    - Seeds a fresh database with official channels and bots.
    - Ensures clean execution without cross-test state leakage.
    """
    temp_dir = tempfile.mkdtemp(prefix="crew_isolated_test_")
    monkeypatch.setenv("CREW_DATA_DIR", temp_dir)

    # For general functional tests, enable dev_no_auth to bypass token checks
    if "security" not in request.node.nodeid and "packaged" not in request.node.nodeid:
        monkeypatch.setenv("CREW_DEV_NO_AUTH", "1")
        monkeypatch.delenv("CREW_API_TOKEN", raising=False)

    # Initialize fresh tables and seed data in the isolated test database
    asyncio.run(init_db())

    yield

    shutil.rmtree(temp_dir, ignore_errors=True)

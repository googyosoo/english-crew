import os
import pytest

@pytest.fixture(autouse=True)
def default_test_env(monkeypatch, request):
    """
    By default, enable CREW_DEV_NO_AUTH=1 for unit test suite
    so business logic tests run smoothly, while security-specific tests
    explicitly control authentication parameters.
    """
    if "security" in request.node.nodeid:
        return
    monkeypatch.setenv("CREW_DEV_NO_AUTH", "1")
    monkeypatch.delenv("CREW_API_TOKEN", raising=False)

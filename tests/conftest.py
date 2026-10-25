"""
tests.conftest
==============
Pytest fixtures for isolating test environments and managing test servers.
"""
import importlib
import os
from pathlib import Path
import pytest


@pytest.fixture(autouse=True)
def isolated_data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Each test gets its own isolated data directory to avoid cross-test contamination."""
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.setenv("SMTP_PORT", "0")
    monkeypatch.setenv("POP3_PORT", "0")

    # Reload settings module so new environment variables take effect
    import mailsys.config.settings as s_mod
    importlib.reload(s_mod)
    yield tmp_path

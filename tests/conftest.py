"""
tests.conftest
==============
Pytest fixtures for isolating test environments and managing test servers.
"""
import importlib
import os
import sys
from pathlib import Path
import pytest

# Ensure src/ is on python search path
_src_dir = str(Path(__file__).parent.parent / "src")
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)



@pytest.fixture(autouse=True)
def isolated_data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Each test gets its own isolated data directory to avoid cross-test contamination."""
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.setenv("SMTP_PORT", "0")
    monkeypatch.setenv("POP3_PORT", "0")

    # Reload settings module so new environment variables take effect
    import mailsys.config.settings
    s_mod = sys.modules["mailsys.config.settings"]
    importlib.reload(s_mod)
    yield tmp_path


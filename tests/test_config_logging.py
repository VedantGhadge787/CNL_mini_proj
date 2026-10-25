"""
tests.test_config_logging
=========================
Unit tests for Settings configuration singleton and central get_logger.
"""
import logging
from pathlib import Path
import pytest
from mailsys.config.settings import Settings, settings
from mailsys.common.logger import get_logger


def test_default_settings() -> None:
    """Verify default configuration values."""
    default_cfg = Settings()
    assert default_cfg.smtp_host == "0.0.0.0"
    assert default_cfg.smtp_port in (2525, 0)  # 0 when isolated_data_dir fixture is active
    assert default_cfg.pop3_host == "0.0.0.0"
    assert default_cfg.local_domain == "localhost"
    assert default_cfg.spam_threshold == 5
    assert default_cfg.max_message_size == 10 * 1024 * 1024
    assert default_cfg.socket_timeout == 300


def test_settings_properties(tmp_path: Path) -> None:
    """Verify mailboxes_dir, logs_dir, and db_path property paths."""
    cfg = Settings(data_dir=tmp_path)
    assert cfg.mailboxes_dir == tmp_path / "mailboxes"
    assert cfg.logs_dir == tmp_path / "logs"
    assert cfg.db_path == tmp_path / "users.db"


def test_settings_env_override(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Verify environment variables override configuration defaults."""
    monkeypatch.setenv("SMTP_PORT", "9999")
    monkeypatch.setenv("POP3_PORT", "9110")
    monkeypatch.setenv("LOCAL_DOMAIN", "mail.example.org")
    monkeypatch.setenv("SPAM_THRESHOLD", "10")
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "custom_data"))

    custom = Settings()
    assert custom.smtp_port == 9999
    assert custom.pop3_port == 9110
    assert custom.local_domain == "mail.example.org"
    assert custom.spam_threshold == 10
    assert custom.data_dir == tmp_path / "custom_data"


def test_get_logger_handlers(isolated_data_dir: Path) -> None:
    """Verify get_logger configures both StreamHandler and RotatingFileHandler."""
    logger_name = f"test_logger_{id(isolated_data_dir)}"
    logger = get_logger(logger_name)

    handler_types = [type(h) for h in logger.handlers]
    assert logging.StreamHandler in handler_types
    assert logging.handlers.RotatingFileHandler in handler_types


def test_get_logger_deduplication(isolated_data_dir: Path) -> None:
    """Verify calling get_logger repeatedly does not duplicate handlers."""
    logger_name = f"test_dedup_{id(isolated_data_dir)}"
    logger1 = get_logger(logger_name)
    initial_count = len(logger1.handlers)

    logger2 = get_logger(logger_name)
    assert logger1 is logger2
    assert len(logger2.handlers) == initial_count


def test_logger_creates_log_file(isolated_data_dir: Path) -> None:
    """Verify logging a message writes to data/logs/mailsys.log."""
    logger_name = f"test_file_write_{id(isolated_data_dir)}"
    logger = get_logger(logger_name)
    test_msg = "Verification message for logging"
    logger.info(test_msg)

    # Flush handlers to ensure file is written
    for h in logger.handlers:
        h.flush()

    log_file = settings.logs_dir / "mailsys.log"
    assert log_file.exists(), f"Log file not found at {log_file}"
    content = log_file.read_text(encoding="utf-8")
    assert test_msg in content

"""
mailsys.config.settings
=======================
Single source of truth for all runtime configuration.

Reads values from environment variables (or .env loaded externally).
All other modules import the module-level `settings` singleton:

    from mailsys.config.settings import settings

Environment variables (with defaults):
    SMTP_HOST         — bind address for SMTP server   (default: 0.0.0.0)
    SMTP_PORT         — listen port for SMTP server    (default: 2525)
    POP3_HOST         — bind address for POP3 server   (default: 0.0.0.0)
    POP3_PORT         — listen port for POP3 server    (default: 2110)
    LOCAL_DOMAIN      — the domain handled locally     (default: localhost)
    DATA_DIR          — root directory for runtime data(default: data)
    SPAM_THRESHOLD    — keyword score cutoff           (default: 5)
    LOG_LEVEL         — logging verbosity              (default: INFO)
    MAX_MESSAGE_SIZE  — max SMTP message bytes         (default: 10485760)
    SOCKET_TIMEOUT    — per-connection timeout (s)     (default: 300)
"""
import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Settings:
    """Runtime configuration loaded lazily from environment variables."""

    smtp_host: str = field(
        default_factory=lambda: os.environ.get("SMTP_HOST", "0.0.0.0")
    )
    smtp_port: int = field(
        default_factory=lambda: int(os.environ.get("SMTP_PORT", "2525"))
    )
    pop3_host: str = field(
        default_factory=lambda: os.environ.get("POP3_HOST", "0.0.0.0")
    )
    pop3_port: int = field(
        default_factory=lambda: int(os.environ.get("POP3_PORT", "2110"))
    )
    local_domain: str = field(
        default_factory=lambda: os.environ.get("LOCAL_DOMAIN", "localhost")
    )
    data_dir: Path = field(
        default_factory=lambda: Path(os.environ.get("DATA_DIR", "data"))
    )
    spam_threshold: int = field(
        default_factory=lambda: int(os.environ.get("SPAM_THRESHOLD", "5"))
    )
    log_level: str = field(
        default_factory=lambda: os.environ.get("LOG_LEVEL", "INFO")
    )
    max_message_size: int = field(
        default_factory=lambda: int(
            os.environ.get("MAX_MESSAGE_SIZE", str(10 * 1024 * 1024))
        )
    )
    socket_timeout: int = field(
        default_factory=lambda: int(os.environ.get("SOCKET_TIMEOUT", "300"))
    )

    @property
    def mailboxes_dir(self) -> Path:
        """Root directory for per-user Maildir storage."""
        return self.data_dir / "mailboxes"

    @property
    def logs_dir(self) -> Path:
        """Directory where log files are stored."""
        return self.data_dir / "logs"

    @property
    def db_path(self) -> Path:
        """Path to SQLite database file."""
        return self.data_dir / "users.db"


# Module-level singleton — import this everywhere
settings = Settings()

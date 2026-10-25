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

Imports needed:
    import os
    from dataclasses import dataclass, field
    from pathlib import Path
"""
import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Settings:
    """Runtime configuration loaded from environment variables."""

    # TODO: Add all fields with os.environ.get() defaults
    # TODO: Add properties: mailboxes_dir, logs_dir, db_path

    pass


# Module-level singleton
settings = Settings()


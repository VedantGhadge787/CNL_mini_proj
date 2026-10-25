# Step 02 — Config & Logging

**Status:** [x] done

---

## 1. Objective

When this step is done:
- `src/mailsys/config/settings.py` reads all configuration from environment variables with safe defaults.
- `src/mailsys/common/logger.py` sets up a named logger with both a `StreamHandler` and a `RotatingFileHandler`.
- Every other module can do `from mailsys.common.logger import get_logger` and `from mailsys.config.settings import settings`.

---

## 2. Prerequisites

- Step 01 done: virtual environment active, deps installed.

---

## 3. Files to Create or Modify

| Action | Path |
|--------|------|
| Implement | `src/mailsys/config/settings.py` |
| Implement | `src/mailsys/common/logger.py` |
| Update stubs | `src/mailsys/config/__init__.py` (re-export `settings`) |
| Update stubs | `src/mailsys/common/__init__.py` (re-export `get_logger`) |

---

## 4. Detailed Implementation Instructions

### 4.1 `settings.py`

```python
# src/mailsys/config/settings.py
import os
from dataclasses import dataclass, field
from pathlib import Path

@dataclass
class Settings:
    smtp_host: str = field(default_factory=lambda: os.environ.get("SMTP_HOST", "0.0.0.0"))
    smtp_port: int = field(default_factory=lambda: int(os.environ.get("SMTP_PORT", "2525")))
    pop3_host: str = field(default_factory=lambda: os.environ.get("POP3_HOST", "0.0.0.0"))
    pop3_port: int = field(default_factory=lambda: int(os.environ.get("POP3_PORT", "2110")))
    local_domain: str = field(default_factory=lambda: os.environ.get("LOCAL_DOMAIN", "localhost"))
    data_dir: Path = field(default_factory=lambda: Path(os.environ.get("DATA_DIR", "data")))
    spam_threshold: int = field(default_factory=lambda: int(os.environ.get("SPAM_THRESHOLD", "5")))
    log_level: str = field(default_factory=lambda: os.environ.get("LOG_LEVEL", "INFO"))
    max_message_size: int = field(default_factory=lambda: int(os.environ.get("MAX_MESSAGE_SIZE", str(10 * 1024 * 1024))))
    socket_timeout: int = field(default_factory=lambda: int(os.environ.get("SOCKET_TIMEOUT", "300")))

    @property
    def mailboxes_dir(self) -> Path:
        return self.data_dir / "mailboxes"

    @property
    def logs_dir(self) -> Path:
        return self.data_dir / "logs"

    @property
    def db_path(self) -> Path:
        return self.data_dir / "users.db"

# Module-level singleton — import this everywhere
settings = Settings()
```

**Key points:**
- All values are lazy-evaluated from `os.environ` at instantiation time, so tests can set env vars before importing.
- `data_dir` is a `Path` object, not a string — use it with `/` operator throughout the codebase.
- `max_message_size` defaults to 10 MB.

### 4.2 `logger.py`

```python
# src/mailsys/common/logger.py
import logging
import logging.handlers
from pathlib import Path
from mailsys.config.settings import settings

def get_logger(name: str) -> logging.Logger:
    """Return a configured logger for the given module name.

    The logger writes to both stderr (StreamHandler) and a rotating
    file at data/logs/mailsys.log (max 5 MB, 3 backups).
    """
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger  # already configured; avoid duplicate handlers

    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    logger.setLevel(level)

    fmt = logging.Formatter(
        "%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler
    ch = logging.StreamHandler()
    ch.setLevel(level)
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    # Rotating file handler
    logs_dir: Path = settings.logs_dir
    logs_dir.mkdir(parents=True, exist_ok=True)
    fh = logging.handlers.RotatingFileHandler(
        logs_dir / "mailsys.log",
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    fh.setLevel(level)
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    return logger
```

**Key points:**
- Guard `if logger.handlers` prevents double-registration in tests.
- `logs_dir.mkdir(parents=True, exist_ok=True)` creates `data/logs/` at first use — no manual setup needed.
- All other modules call `get_logger(__name__)` at module level.

### 4.3 Usage pattern in every other module

```python
from mailsys.common.logger import get_logger
logger = get_logger(__name__)

# Then use:
logger.info("Server started on port %d", settings.smtp_port)
logger.warning("Unknown command: %s", cmd)
```

---

## 5. Acceptance Criteria

- [x] `from mailsys.config.settings import settings` succeeds and `settings.smtp_port == 2525`.
- [x] Setting `SMTP_PORT=9999` in the environment before import makes `settings.smtp_port == 9999`.
- [x] `from mailsys.common.logger import get_logger; logger = get_logger("test")` succeeds.
- [x] After calling `get_logger`, `data/logs/mailsys.log` is created.
- [x] Calling `get_logger` twice with the same name does not duplicate handlers.


---

## 6. How to Test

```powershell
# Quick smoke test
python -c "
from mailsys.config.settings import settings
assert settings.smtp_port == 2525
assert settings.pop3_port == 2110
print('settings OK:', settings)
"

# Logger smoke test
python -c "
from mailsys.common.logger import get_logger
log = get_logger('smoke')
log.info('Logger working')
print('Logger OK')
"

# Check log file created
python -c "
from pathlib import Path
assert (Path('data') / 'logs' / 'mailsys.log').exists(), 'log file missing'
print('Log file created')
"

# Run unit tests
python -m pytest tests/ -v -k "config or logging or settings"
```

---

## 7. Wireshark Check

Not applicable for this step.

---

## 8. Log Update

Append to `docs/log.md`:
```
### [YYYY-MM-DD HH:MM] Step 02: Config & Logging
- Changed: settings.py (real logic), logger.py (real logic)
- Why: Every module needs configuration and a logger before any feature logic
- Key decisions: Settings as module-level singleton dataclass; lazy env-var reads
- Interfaces added: settings (Settings), get_logger(name: str) -> Logger
- Tests: smoke tests pass; pytest -v passes
- Next: Begin Step 03 — user management and storage
```

---

## 9. Definition of Done

Both modules have real logic (not stubs), pass smoke tests, `data/logs/mailsys.log` is created on import, and `docs/log.md` is updated.

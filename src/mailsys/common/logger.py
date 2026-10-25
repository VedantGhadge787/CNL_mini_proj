"""
mailsys.common.logger
=====================
Configures a named Python logger with:
  - StreamHandler  → stderr at the configured log level
  - RotatingFileHandler → data/logs/mailsys.log (5 MB, 3 backups)

Usage in every other module:
    from mailsys.common.logger import get_logger
    logger = get_logger(__name__)
"""
import logging
import logging.handlers
from pathlib import Path
from mailsys.config.settings import settings


def get_logger(name: str) -> logging.Logger:
    """Return a configured logger for the given module name.

    The logger writes to both stderr (StreamHandler) and a rotating
    file at data/logs/mailsys.log (max 5 MB, 3 backups).

    Args:
        name: Typically ``__name__`` of the calling module.

    Returns:
        logging.Logger: Configured logger with stream and rotating file handlers.
    """
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger  # already configured; avoid duplicate handlers

    level_name = getattr(settings, "log_level", "INFO")
    level = getattr(logging, str(level_name).upper(), logging.INFO)
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

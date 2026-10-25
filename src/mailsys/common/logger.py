"""
mailsys.common.logger
=====================
Configures a named Python logger with:
  - StreamHandler  → stderr at the configured log level
  - RotatingFileHandler → data/logs/mailsys.log (5 MB, 3 backups)

Usage in every other module:
    from mailsys.common.logger import get_logger
    logger = get_logger(__name__)

Imports needed:
    import logging
    import logging.handlers
    from pathlib import Path
    from mailsys.config.settings import settings
"""
import logging
import logging.handlers
from pathlib import Path


def get_logger(name: str) -> logging.Logger:
    """Return a configured Logger for the given module name.

    Args:
        name: Typically ``__name__`` of the calling module.

    Returns:
        A ``logging.Logger`` instance with stream and rotating-file handlers.

    TODO:
        - Read log level from settings.log_level
        - Guard against duplicate handlers (check logger.handlers)
        - Create data/logs/ directory if it does not exist
        - Configure StreamHandler and RotatingFileHandler with a uniform format:
          "%(asctime)s  %(levelname)-8s  %(name)s  %(message)s"
    """
    # TODO: Implement
    raise NotImplementedError

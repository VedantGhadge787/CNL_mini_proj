"""
scripts/run_smtp.py
===================
CLI entry point to launch the Mini Mail System SMTP server.

Usage:
    python scripts/run_smtp.py
"""
import sys
from pathlib import Path

# Add project src directory to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from mailsys.common.logger import get_logger
from mailsys.config.settings import settings
from mailsys.smtp.server import SMTPServer

logger = get_logger("run_smtp")


def main() -> None:
    """Instantiate and run the SMTPServer until interrupted."""
    # TODO: Initialize SMTPServer and call server.start()
    # Handle KeyboardInterrupt gracefully with server.stop()
    raise NotImplementedError


if __name__ == "__main__":
    main()

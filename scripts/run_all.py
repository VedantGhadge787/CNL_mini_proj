"""
scripts/run_all.py
==================
CLI entry point to launch both the SMTP and POP3 servers concurrently in background threads.

Usage:
    python scripts/run_all.py
"""
import sys
import threading
import time
from pathlib import Path

# Add project src directory to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from mailsys.common.logger import get_logger
from mailsys.config.settings import settings
from mailsys.smtp.server import SMTPServer
from mailsys.pop3.server import POP3Server

logger = get_logger("run_all")


def main() -> None:
    """Instantiate and run both SMTPServer and POP3Server concurrently."""
    # TODO: Start SMTPServer and POP3Server in separate threads
    # Handle KeyboardInterrupt and stop both servers
    raise NotImplementedError


if __name__ == "__main__":
    main()

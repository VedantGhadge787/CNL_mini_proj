"""
scripts/run_pop3.py
===================
CLI entry point to launch the Mini Mail System POP3 server.

Usage:
    python scripts/run_pop3.py
"""
import sys
from pathlib import Path

# Add project src directory to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from mailsys.common.logger import get_logger
from mailsys.config.settings import settings
from mailsys.pop3.server import POP3Server

logger = get_logger("run_pop3")


def main() -> None:
    """Instantiate and run the POP3Server until interrupted."""
    # TODO: Initialize POP3Server and call server.start()
    # Handle KeyboardInterrupt gracefully with server.stop()
    raise NotImplementedError


if __name__ == "__main__":
    main()

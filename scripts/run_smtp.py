#!/usr/bin/env python3
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
    server = SMTPServer()
    print(f"SMTP server starting on {server.host}:{server.port} ...")
    try:
        server.start()
    except KeyboardInterrupt:
        print("\nShutting down SMTP server...")
        server.stop()
    except Exception as e:
        logger.exception("Fatal server error: %s", e)
        server.stop()
        sys.exit(1)


if __name__ == "__main__":
    main()

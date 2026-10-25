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
from mailsys.pop3.server import POP3Server

logger = get_logger("run_pop3")


def main() -> None:
    """Run the POP3 server until interrupted."""
    server = POP3Server()
    logger.info("POP3 server starting on %s:%d ...", server.host, server.port)
    try:
        server.start()
    except KeyboardInterrupt:
        logger.info("Shutting down POP3 server...")
        server.stop()
    except Exception:
        logger.exception("Fatal POP3 server error")
        server.stop()
        sys.exit(1)


if __name__ == "__main__":
    main()

"""
mailsys.smtp.server
===================
Thread-per-connection SMTP server implemented with raw Python sockets.

Listens on the configured host and port (default: 0.0.0.0:2525).
For each incoming connection, spawns a daemon thread executing `SMTPSession.handle()`.
"""
from __future__ import annotations

import socket
import threading
from mailsys.common.logger import get_logger
from mailsys.config.settings import settings
from mailsys.smtp.session import SMTPSession

logger = get_logger(__name__)


class SMTPServer:
    """Listens for incoming SMTP connections and spawns a session thread per client."""

    def __init__(self, host: str | None = None, port: int | None = None) -> None:
        """Initialize server with bind host and port."""
        self.host = (
            host if host is not None else getattr(settings, "smtp_host", "0.0.0.0")
        )
        self.port = (
            port if port is not None else getattr(settings, "smtp_port", 2525)
        )
        self._server_sock: socket.socket | None = None
        self._running = False
        self._threads: list[threading.Thread] = []

    def start(self) -> None:
        """Bind socket and enter accept loop (blocking). Call in its own thread if non-blocking."""
        self._server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server_sock.bind((self.host, self.port))
        self.port = self._server_sock.getsockname()[1]
        self._server_sock.listen(5)
        self._running = True
        logger.info("SMTPServer listening on %s:%d", self.host, self.port)

        while self._running:
            try:
                conn, addr = self._server_sock.accept()
                timeout = getattr(settings, "socket_timeout", 300)
                conn.settimeout(timeout)
                t = threading.Thread(
                    target=self._handle_client, args=(conn, addr), daemon=True
                )
                self._threads.append(t)
                t.start()
            except OSError:
                break

    def stop(self) -> None:
        """Signal the accept loop to stop and close the server socket."""
        self._running = False
        if self._server_sock:
            try:
                self._server_sock.close()
            except OSError:
                pass
            self._server_sock = None
        logger.info("SMTPServer stopped.")

    def _handle_client(self, conn: socket.socket, addr: tuple[str, int]) -> None:
        """Target function for per-client worker thread."""
        logger.debug("Accepted SMTP connection from %s:%d", addr[0], addr[1])
        try:
            session = SMTPSession(conn, addr)
            session.handle()
        except Exception as e:
            logger.exception("Error in SMTP session for %s: %s", addr, e)
        finally:
            try:
                conn.close()
            except OSError:
                pass
            logger.debug("Closed SMTP connection from %s:%d", addr[0], addr[1])

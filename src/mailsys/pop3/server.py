"""
mailsys.pop3.server
===================
Thread-per-connection POP3 server implemented with raw Python sockets.

Listens on the configured host and port (default: 0.0.0.0:2110).
For each incoming connection, spawns a daemon thread executing `POP3Session.handle()`.
"""
from __future__ import annotations

import socket
import threading

from mailsys.common.logger import get_logger
from mailsys.config.settings import settings
from mailsys.pop3.session import POP3Session

logger = get_logger(__name__)


class POP3Server:
    """Listens for incoming POP3 connections and spawns a session thread per client."""

    def __init__(self, host: str | None = None, port: int | None = None) -> None:
        """Initialize server with bind host and port."""
        self.host = (
            host if host is not None else getattr(settings, "pop3_host", "0.0.0.0")
        )
        self.port = port if port is not None else getattr(settings, "pop3_port", 2110)
        self._server_sock: socket.socket | None = None
        self._running = False
        self._threads: list[threading.Thread] = []

    def start(self) -> None:
        """Bind the listening socket and accept clients until stopped."""
        server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_sock.bind((self.host, self.port))
        self.port = server_sock.getsockname()[1]
        server_sock.listen(5)
        server_sock.settimeout(1.0)
        self._server_sock = server_sock
        self._running = True
        logger.info("POP3Server listening on %s:%d", self.host, self.port)

        try:
            while self._running:
                try:
                    conn, addr = server_sock.accept()
                except socket.timeout:
                    continue
                except OSError:
                    if self._running:
                        logger.exception("POP3 listener failed")
                    break

                conn.settimeout(getattr(settings, "socket_timeout", 300))
                thread = threading.Thread(
                    target=self._handle_client, args=(conn, addr), daemon=True
                )
                self._threads.append(thread)
                thread.start()
        finally:
            self._running = False
            server_sock.close()
            if self._server_sock is server_sock:
                self._server_sock = None
            logger.info("POP3Server stopped.")

    def stop(self) -> None:
        """Signal the accept loop to stop and close the listening socket."""
        self._running = False
        server_sock = self._server_sock
        if server_sock is not None:
            try:
                server_sock.close()
            except OSError:
                logger.exception("Failed to close POP3 listening socket")
            self._server_sock = None
        logger.info("POP3Server stop requested.")

    def _handle_client(self, conn: socket.socket, addr: tuple[str, int]) -> None:
        """Run one POP3 session and close its client socket."""
        logger.debug("Accepted POP3 connection from %s:%d", addr[0], addr[1])
        try:
            POP3Session(conn, addr).handle()
        except Exception:
            logger.exception("Error in POP3 session for %s", addr)
        finally:
            try:
                conn.close()
            except OSError:
                logger.exception("Failed to close POP3 client socket for %s", addr)
            logger.debug("Closed POP3 connection from %s:%d", addr[0], addr[1])

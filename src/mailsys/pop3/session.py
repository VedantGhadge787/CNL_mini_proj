"""
mailsys.pop3.session
====================
Hand-written RFC 1939 POP3 protocol state machine over a raw socket connection.

States:
  - AUTHORIZATION: Waits for USER and PASS commands.
  - TRANSACTION: Mailbox locked; supports STAT, LIST, RETR, DELE, NOOP, RSET, TOP, UIDL.
  - UPDATE: Triggered by QUIT; commits deletions, releases lock.
  - CLOSED: Connection terminated.
"""
from __future__ import annotations

import enum
import socket
import threading
from pathlib import Path

from mailsys.auth.user_manager import user_exists, verify_password
from mailsys.common.logger import get_logger
from mailsys.common.protocol_utils import (
    recv_line,
    send_multiline,
    send_pop3_err,
    send_pop3_ok,
)
from mailsys.storage.mailbox import (
    _get_lock,
    delete_message,
    generate_uid,
    list_messages,
    read_message,
)

logger = get_logger(__name__)


class POP3State(enum.Enum):
    """POP3 session states."""
    AUTHORIZATION = "AUTHORIZATION"
    TRANSACTION   = "TRANSACTION"
    UPDATE        = "UPDATE"
    CLOSED        = "CLOSED"


class POP3Session:
    """Manages an individual POP3 client connection state machine."""

    def __init__(self, conn: socket.socket, addr: tuple[str, int]) -> None:
        self.conn = conn
        self.addr = addr
        self.state = POP3State.AUTHORIZATION
        self.username: str | None = None
        self.messages: list[tuple[int, Path, int]] = []  # (1-based index, path, size)
        self.deleted: set[int] = set()                   # indices marked for deletion
        self.logger = get_logger(__name__)
        self._mailbox_lock: threading.RLock | None = None

    def handle(self) -> None:
        """Send the greeting and process commands until the connection closes."""
        try:
            send_pop3_ok(self.conn, "POP3 server ready")
            while self.state != POP3State.CLOSED:
                try:
                    line = recv_line(self.conn)
                except ValueError:
                    send_pop3_err(self.conn, "command line too long")
                    break
                except (ConnectionResetError, EOFError, socket.timeout):
                    self.logger.info("POP3 client disconnected: %s", self.addr)
                    break
                self._dispatch(line)
        except OSError:
            self.logger.warning("POP3 socket error for %s", self.addr, exc_info=True)
        finally:
            self._release_mailbox_lock()
            self.state = POP3State.CLOSED

    def _dispatch(self, line: str) -> None:
        """Parse a command, enforce its legal state, and invoke its handler."""
        parts = line.strip().split(None, 1)
        if not parts:
            send_pop3_err(self.conn, "empty command")
            return

        command = parts[0].upper()
        arg = parts[1].strip() if len(parts) == 2 else ""
        handlers = {
            "USER": self._cmd_user,
            "PASS": self._cmd_pass,
            "STAT": self._cmd_stat,
            "LIST": self._cmd_list,
            "RETR": self._cmd_retr,
            "DELE": self._cmd_dele,
            "NOOP": self._cmd_noop,
            "RSET": self._cmd_rset,
            "UIDL": self._cmd_uidl,
            "TOP": self._cmd_top,
            "QUIT": self._cmd_quit,
        }
        handler = handlers.get(command)
        if handler is None:
            send_pop3_err(self.conn, f"unknown command: {command}")
            return
        if not self._command_allowed(command):
            send_pop3_err(self.conn, "command not valid in this state")
            return
        handler(arg)

    def _command_allowed(self, command: str) -> bool:
        """Return whether a command is valid in the current session state."""
        if command == "QUIT":
            return True
        if command in ("USER", "PASS"):
            return self.state == POP3State.AUTHORIZATION
        return self.state == POP3State.TRANSACTION

    def _cmd_user(self, arg: str) -> None:
        """Handle USER command in AUTHORIZATION state."""
        if len(arg.split()) != 1:
            send_pop3_err(self.conn, "syntax: USER username")
            return
        username = arg.strip().lower()
        if not user_exists(username):
            self.username = None
            send_pop3_err(self.conn, "invalid user")
            return
        self.username = username
        send_pop3_ok(self.conn, username)

    def _cmd_pass(self, arg: str) -> None:
        """Verify PASS credentials and transition to TRANSACTION on success."""
        if self.username is None:
            send_pop3_err(self.conn, "send USER first")
            return
        if not arg or not verify_password(self.username, arg):
            self.username = None
            send_pop3_err(self.conn, "invalid credentials")
            return

        lock = _get_lock(self.username)
        if not lock.acquire(blocking=False):
            send_pop3_err(self.conn, "[IN-USE] mailbox already locked")
            self.state = POP3State.CLOSED
            return
        self._mailbox_lock = lock
        self.messages = list_messages(self.username)
        self.state = POP3State.TRANSACTION
        send_pop3_ok(self.conn, f"logged in, {len(self.messages)} messages")

    def _cmd_stat(self, arg: str) -> None:
        """Handle STAT command: return count and total size of non-deleted messages."""
        if arg:
            send_pop3_err(self.conn, "syntax: STAT")
            return
        active = [
            message for message in self.messages if message[0] not in self.deleted
        ]
        total_size = sum(size for _, _, size in active)
        send_pop3_ok(self.conn, f"{len(active)} {total_size}")

    def _cmd_list(self, arg: str) -> None:
        """Handle LIST [msg] command."""
        if not arg:
            active = [msg for msg in self.messages if msg[0] not in self.deleted]
            send_pop3_ok(self.conn, f"{len(active)} messages")
            send_multiline(
                self.conn, [f"{index} {size}" for index, _, size in active]
            )
            return
        index = self._parse_message_index(arg)
        if index is None or not self._message_exists(index):
            send_pop3_err(self.conn, "no such message")
            return
        _, _, size = self.messages[index - 1]
        send_pop3_ok(self.conn, f"{index} {size}")

    def _cmd_retr(self, arg: str) -> None:
        """Handle RETR msg command: send message body followed by dot."""
        index = self._parse_message_index(arg)
        if index is None or not self._message_exists(index):
            send_pop3_err(self.conn, "no such message")
            return
        raw = read_message(self._require_username(), index)
        send_pop3_ok(self.conn, f"{len(raw)} octets")
        self._send_message_lines(raw)

    def _cmd_dele(self, arg: str) -> None:
        """Handle DELE msg command: mark message for deletion."""
        index = self._parse_message_index(arg)
        if index is None or not self._message_exists(index):
            send_pop3_err(self.conn, "no such message")
            return
        self.deleted.add(index)
        send_pop3_ok(self.conn, f"message {index} deleted")

    def _cmd_noop(self, arg: str) -> None:
        """Handle NOOP command."""
        if arg:
            send_pop3_err(self.conn, "syntax: NOOP")
            return
        send_pop3_ok(self.conn)

    def _cmd_rset(self, arg: str) -> None:
        """Handle RSET command: clear deleted set."""
        if arg:
            send_pop3_err(self.conn, "syntax: RSET")
            return
        self.deleted.clear()
        send_pop3_ok(self.conn, f"maildrop has {len(self.messages)} messages")

    def _cmd_uidl(self, arg: str) -> None:
        """Handle UIDL [msg] command: return stable unique identifiers."""
        if not arg:
            active = [msg for msg in self.messages if msg[0] not in self.deleted]
            send_pop3_ok(self.conn, "unique-id listing")
            send_multiline(
                self.conn,
                [f"{index} {generate_uid(path)}" for index, path, _ in active],
            )
            return
        index = self._parse_message_index(arg)
        if index is None or not self._message_exists(index):
            send_pop3_err(self.conn, "no such message")
            return
        _, path, _ = self.messages[index - 1]
        send_pop3_ok(self.conn, f"{index} {generate_uid(path)}")

    def _cmd_top(self, arg: str) -> None:
        """Handle TOP msg n command: return headers + top n body lines."""
        parts = arg.split()
        if len(parts) != 2:
            send_pop3_err(self.conn, "syntax: TOP msg n")
            return
        index = self._parse_message_index(parts[0])
        try:
            body_line_count = int(parts[1])
        except ValueError:
            body_line_count = -1
        if index is None or body_line_count < 0:
            send_pop3_err(self.conn, "syntax: TOP msg n")
            return
        if not self._message_exists(index):
            send_pop3_err(self.conn, "no such message")
            return
        raw = read_message(self._require_username(), index)
        headers, body = self._split_headers_body(raw)
        send_pop3_ok(self.conn)
        selected_body = b"\r\n".join(body.splitlines()[:body_line_count])
        self._send_message_lines(headers + b"\r\n\r\n" + selected_body)

    def _cmd_quit(self, arg: str) -> None:
        """Enter UPDATE, commit deletion marks, and close after a successful QUIT."""
        if arg:
            send_pop3_err(self.conn, "syntax: QUIT")
            return
        if self.state == POP3State.TRANSACTION:
            self.state = POP3State.UPDATE
            try:
                for index in sorted(self.deleted, reverse=True):
                    delete_message(self._require_username(), index)
            except (OSError, IndexError):
                self.logger.exception("Failed to update mailbox for %s", self.username)
                send_pop3_err(self.conn, "unable to update mailbox")
                self.state = POP3State.CLOSED
                return
        send_pop3_ok(self.conn, "bye")
        self.state = POP3State.CLOSED
        self._release_mailbox_lock()

    def _parse_message_index(self, arg: str) -> int | None:
        """Parse a single positive message index, returning None for malformed input."""
        try:
            index = int(arg)
        except ValueError:
            return None
        return index if index > 0 else None

    def _message_exists(self, index: int) -> bool:
        """Return whether an index refers to an undeleted message in this maildrop."""
        return index <= len(self.messages) and index not in self.deleted

    def _require_username(self) -> str:
        """Return the authenticated username or raise on an inconsistent session."""
        if self.username is None:
            raise RuntimeError("POP3 transaction has no authenticated username")
        return self.username

    def _send_message_lines(self, raw: bytes) -> None:
        """Send RFC message lines using POP3 dot-stuffing and CRLF terminators."""
        for line in raw.splitlines():
            if line.startswith(b"."):
                line = b"." + line
            self.conn.sendall(line + b"\r\n")
        self.conn.sendall(b".\r\n")

    def _split_headers_body(self, raw: bytes) -> tuple[bytes, bytes]:
        """Split an RFC message at its header/body separator."""
        for separator in (b"\r\n\r\n", b"\n\n"):
            position = raw.find(separator)
            if position >= 0:
                return raw[:position], raw[position + len(separator):]
        return raw, b""

    def _release_mailbox_lock(self) -> None:
        """Release the mailbox lock if this session acquired it."""
        lock = self._mailbox_lock
        if lock is not None:
            self._mailbox_lock = None
            lock.release()

"""Unit tests for POP3Session RFC 1939 commands and state transitions."""
from __future__ import annotations

import socket
import threading
import time
from pathlib import Path

import pytest

from mailsys.auth.user_manager import create_user
from mailsys.pop3.server import POP3Server
from mailsys.pop3.session import POP3Session, POP3State
from mailsys.storage.mailbox import deliver, generate_uid, list_messages


def _read_line(sock: socket.socket) -> bytes:
    """Read one CRLF-terminated response line from a test socket."""
    data = bytearray()
    while not data.endswith(b"\r\n"):
        chunk = sock.recv(1)
        if not chunk:
            raise ConnectionError("POP3 session closed before completing a response")
        data.extend(chunk)
    return bytes(data[:-2])


def _read_multiline(sock: socket.socket) -> list[bytes]:
    """Read a POP3 multiline response through its terminator."""
    lines: list[bytes] = []
    while True:
        line = _read_line(sock)
        if line == b".":
            return lines
        lines.append(line)


def _start_session() -> tuple[socket.socket, POP3Session, threading.Thread]:
    """Start a POP3 session over a socket pair and return its client end."""
    client, server = socket.socketpair()
    client.settimeout(5)
    session = POP3Session(server, ("127.0.0.1", 21100))
    thread = threading.Thread(target=session.handle, daemon=True)
    thread.start()
    assert _read_line(client) == b"+OK POP3 server ready"
    return client, session, thread


def _command(client: socket.socket, command: str) -> bytes:
    """Send a command and read its single-line status response."""
    client.sendall(command.encode("ascii") + b"\r\n")
    return _read_line(client)


def _login(client: socket.socket, username: str = "alice") -> bytes:
    """Authenticate a test client using the fixture account password."""
    assert _command(client, f"USER {username}") == f"+OK {username}".encode()
    response = _command(client, "PASS secret")
    assert response.startswith(b"+OK logged in")
    return response


def _close_session(
    client: socket.socket, thread: threading.Thread, quit_session: bool = True
) -> None:
    """Close a test connection and wait for its session thread to finish."""
    if quit_session and thread.is_alive():
        client.sendall(b"QUIT\r\n")
        _read_line(client)
    client.close()
    thread.join(timeout=2)
    assert not thread.is_alive()


def test_greeting(isolated_data_dir: Path) -> None:
    """Verify the server sends the POP3 greeting on connection."""
    client, _, thread = _start_session()
    _close_session(client, thread)


def test_auth_success_and_transaction_state(isolated_data_dir: Path) -> None:
    """Verify valid USER and PASS transition the session to TRANSACTION."""
    create_user("alice", "secret")
    client, session, thread = _start_session()

    assert _command(client, "uSeR alice") == b"+OK alice"
    assert _command(client, "PASS secret").startswith(b"+OK logged in")
    assert session.state == POP3State.TRANSACTION
    _close_session(client, thread)


def test_auth_wrong_password(isolated_data_dir: Path) -> None:
    """Verify invalid credentials fail and allow another USER attempt."""
    create_user("alice", "secret")
    client, _, thread = _start_session()

    assert _command(client, "USER alice") == b"+OK alice"
    assert _command(client, "PASS wrong") == b"-ERR invalid credentials"
    assert _command(client, "PASS secret") == b"-ERR send USER first"
    _close_session(client, thread)


def test_unknown_user_and_pre_auth_commands(isolated_data_dir: Path) -> None:
    """Reject unknown users and transaction commands before authentication."""
    client, _, thread = _start_session()

    assert _command(client, "USER nobody") == b"-ERR invalid user"
    assert _command(client, "STAT") == b"-ERR command not valid in this state"
    _close_session(client, thread)


def test_stat_empty_mailbox(isolated_data_dir: Path) -> None:
    """Verify an empty maildrop has zero messages and octets."""
    create_user("alice", "secret")
    client, _, thread = _start_session()

    assert _login(client) == b"+OK logged in, 0 messages"
    assert _command(client, "STAT") == b"+OK 0 0"
    _close_session(client, thread)


def test_stat_with_messages(isolated_data_dir: Path) -> None:
    """Verify STAT counts messages and sums their stored byte sizes."""
    create_user("alice", "secret")
    deliver("alice", b"Subject: one\r\n\r\nfirst\r\n")
    deliver("alice", b"Subject: two\r\n\r\nsecond\r\n")
    client, _, thread = _start_session()
    _login(client)

    assert _command(client, "STAT") == b"+OK 2 47"
    _close_session(client, thread)


def test_list_single_and_multiline(isolated_data_dir: Path) -> None:
    """Verify LIST responds with indexed sizes and a dot terminator."""
    create_user("alice", "secret")
    deliver("alice", b"one")
    deliver("alice", b"two!")
    client, _, thread = _start_session()
    _login(client)

    assert _command(client, "LIST") == b"+OK 2 messages"
    assert _read_multiline(client) == [b"1 3", b"2 4"]
    assert _command(client, "LIST 2") == b"+OK 2 4"
    _close_session(client, thread)


def test_retr_dot_stuffing_and_deleted_message(isolated_data_dir: Path) -> None:
    """Verify RETR dot-stuffs message lines and rejects a marked message."""
    create_user("alice", "secret")
    deliver("alice", b"Subject: test\r\n\r\n.leading dot\r\n")
    client, _, thread = _start_session()
    _login(client)

    assert _command(client, "RETR 1").startswith(b"+OK ")
    assert _read_multiline(client) == [
        b"Subject: test",
        b"",
        b"..leading dot",
    ]
    assert _command(client, "DELE 1") == b"+OK message 1 deleted"
    assert _command(client, "RETR 1") == b"-ERR no such message"
    _close_session(client, thread, quit_session=False)
    assert len(list_messages("alice")) == 1


def test_dele_only_purges_on_quit(isolated_data_dir: Path) -> None:
    """Verify DELE marks in-session and QUIT commits the deletion."""
    create_user("alice", "secret")
    path = deliver("alice", b"message")
    client, _, thread = _start_session()
    _login(client)

    assert _command(client, "DELE 1") == b"+OK message 1 deleted"
    assert path.exists()
    assert _command(client, "QUIT") == b"+OK bye"
    thread.join(timeout=2)
    assert not thread.is_alive()
    client.close()
    assert not path.exists()


def test_disconnect_rolls_back_deletion_marks(isolated_data_dir: Path) -> None:
    """Verify an unclean disconnect never commits DELE marks."""
    create_user("alice", "secret")
    path = deliver("alice", b"message")
    client, _, thread = _start_session()
    _login(client)
    assert _command(client, "DELE 1") == b"+OK message 1 deleted"

    _close_session(client, thread, quit_session=False)
    assert path.exists()


def test_rset_clears_deletion(isolated_data_dir: Path) -> None:
    """Verify RSET clears pending deletion marks."""
    create_user("alice", "secret")
    path = deliver("alice", b"message")
    client, _, thread = _start_session()
    _login(client)

    assert _command(client, "DELE 1") == b"+OK message 1 deleted"
    assert _command(client, "RSET") == b"+OK maildrop has 1 messages"
    assert _command(client, "QUIT") == b"+OK bye"
    thread.join(timeout=2)
    client.close()
    assert path.exists()


def test_uidl_returns_stable_uid(isolated_data_dir: Path) -> None:
    """Verify single and multiline UIDL use the stable filename-derived UID."""
    create_user("alice", "secret")
    deliver("alice", b"message")
    expected_uid = generate_uid(list_messages("alice")[0][1])
    client, _, thread = _start_session()
    _login(client)

    assert _command(client, "UIDL 1") == f"+OK 1 {expected_uid}".encode()
    assert _command(client, "UIDL") == b"+OK unique-id listing"
    assert _read_multiline(client) == [f"1 {expected_uid}".encode()]
    _close_session(client, thread)


def test_top_returns_headers_and_requested_body_lines(isolated_data_dir: Path) -> None:
    """Verify TOP returns message headers plus only the requested body lines."""
    create_user("alice", "secret")
    deliver("alice", b"Subject: top\r\nX-Test: yes\r\n\r\none\r\ntwo\r\n")
    client, _, thread = _start_session()
    _login(client)

    assert _command(client, "TOP 1 1") == b"+OK"
    assert _read_multiline(client) == [
        b"Subject: top",
        b"X-Test: yes",
        b"",
        b"one",
    ]
    _close_session(client, thread)


def test_concurrent_session_locked(isolated_data_dir: Path) -> None:
    """Verify only one POP3 session can lock a given mailbox at a time."""
    create_user("alice", "secret")
    first, _, first_thread = _start_session()
    second, _, second_thread = _start_session()

    assert _login(first).startswith(b"+OK logged in")
    assert _command(second, "USER alice") == b"+OK alice"
    assert _command(second, "PASS secret") == b"-ERR [IN-USE] mailbox already locked"
    second_thread.join(timeout=2)
    assert not second_thread.is_alive()
    _close_session(first, first_thread)
    second.close()


def test_pop3_server_accepts_and_stops(isolated_data_dir: Path) -> None:
    """Verify the listener accepts a client and stops cleanly."""
    server = POP3Server("127.0.0.1", 0)
    server_thread = threading.Thread(target=server.start, daemon=True)
    server_thread.start()
    deadline = time.monotonic() + 2
    client: socket.socket | None = None
    while time.monotonic() < deadline:
        if server.port:
            try:
                client = socket.create_connection(
                    ("127.0.0.1", server.port), timeout=0.5
                )
                break
            except OSError:
                time.sleep(0.01)
    assert client is not None
    assert _read_line(client) == b"+OK POP3 server ready"
    client.sendall(b"QUIT\r\n")
    assert _read_line(client) == b"+OK bye"
    client.close()
    server.stop()
    server_thread.join(timeout=2)
    assert not server_thread.is_alive()

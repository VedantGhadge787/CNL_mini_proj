"""
tests.test_smtp_session
=======================
Unit tests for SMTPSession RFC 5321 command handling and state transitions.
"""
import socket
import threading
from pathlib import Path
import pytest
from mailsys.auth.user_manager import create_user
from mailsys.config.settings import settings
from mailsys.smtp.session import SMTPSession
from mailsys.storage.mailbox import list_messages, read_message


def _make_session_pair() -> tuple[socket.socket, SMTPSession, threading.Thread]:
    """Return (client_sock, session, thread) running SMTPSession.handle()."""
    client, server = socket.socketpair()
    session = SMTPSession(server, ("127.0.0.1", 25250))
    t = threading.Thread(target=session.handle, daemon=True)
    t.start()
    return client, session, t


def test_greeting(isolated_data_dir: Path) -> None:
    """Verify server sends 220 banner upon connection."""
    client, _, _ = _make_session_pair()
    banner = client.recv(1024)
    client.close()
    assert banner.startswith(b"220 ")
    assert b"Simple Mail Transfer Service Ready" in banner


def test_helo(isolated_data_dir: Path) -> None:
    """Verify server responds 250 to HELO command."""
    client, _, _ = _make_session_pair()
    client.recv(1024)  # 220
    client.sendall(b"HELO testclient.local\r\n")
    reply = client.recv(1024)
    client.close()
    assert reply.startswith(b"250 ")
    assert b"Hello testclient.local" in reply


def test_rcpt_unknown_user(isolated_data_dir: Path) -> None:
    """Verify server responds 550 when recipient does not exist in local recipient table."""
    client, _, _ = _make_session_pair()
    client.recv(1024)  # 220
    client.sendall(b"HELO testclient\r\n")
    client.recv(1024)  # 250
    client.sendall(b"MAIL FROM:<sender@example.com>\r\n")
    client.recv(1024)  # 250
    client.sendall(b"RCPT TO:<nobody@localhost>\r\n")
    reply = client.recv(1024)
    client.close()
    assert reply.startswith(b"550 ")
    assert b"User unknown" in reply


def test_full_delivery(isolated_data_dir: Path) -> None:
    """Verify complete HELO -> MAIL FROM -> RCPT TO -> DATA -> QUIT delivery sequence."""
    create_user("bob", "secret")
    client, _, _ = _make_session_pair()
    client.recv(1024)  # 220

    client.sendall(b"HELO client\r\n")
    assert client.recv(1024).startswith(b"250")

    client.sendall(b"MAIL FROM:<alice@localhost>\r\n")
    assert client.recv(1024).startswith(b"250")

    client.sendall(b"RCPT TO:<bob@localhost>\r\n")
    assert client.recv(1024).startswith(b"250")

    client.sendall(b"DATA\r\n")
    assert client.recv(1024).startswith(b"354")

    msg_body = b"Subject: Hello Bob\r\nFrom: alice@localhost\r\n\r\nThis is a test email.\r\n.\r\n"
    client.sendall(msg_body)
    assert client.recv(1024).startswith(b"250")

    client.sendall(b"QUIT\r\n")
    assert client.recv(1024).startswith(b"221")
    client.close()

    # Verify email landed in bob's mailbox
    msgs = list_messages("bob")
    assert len(msgs) == 1
    content = read_message("bob", 1)
    assert b"Hello Bob" in content
    assert b"This is a test email." in content


def test_data_dot_stuffing(isolated_data_dir: Path) -> None:
    """Verify dot-stuffed lines have leading dot removed upon storage."""
    create_user("charlie", "secret")
    client, _, _ = _make_session_pair()
    client.recv(1024)

    client.sendall(b"HELO test\r\n")
    client.recv(1024)
    client.sendall(b"MAIL FROM:<alice@localhost>\r\n")
    client.recv(1024)
    client.sendall(b"RCPT TO:<charlie@localhost>\r\n")
    client.recv(1024)
    client.sendall(b"DATA\r\n")
    client.recv(1024)

    # Line starts with dot -> stuffed as '..leading dot'
    stuffed_body = b"Line 1\r\n..Leading dot\r\nLine 3\r\n.\r\n"
    client.sendall(stuffed_body)
    client.recv(1024)
    client.close()

    stored = read_message("charlie", 1)
    assert b".Leading dot\r\n" in stored
    assert b"..Leading dot" not in stored


def test_oversized_message(isolated_data_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify server rejects messages exceeding MAX_MESSAGE_SIZE with 552."""
    create_user("david", "secret")
    monkeypatch.setattr(settings, "max_message_size", 50)

    client, _, _ = _make_session_pair()
    client.recv(1024)

    client.sendall(b"HELO test\r\n")
    client.recv(1024)
    client.sendall(b"MAIL FROM:<alice@localhost>\r\n")
    client.recv(1024)
    client.sendall(b"RCPT TO:<david@localhost>\r\n")
    client.recv(1024)
    client.sendall(b"DATA\r\n")
    client.recv(1024)

    large_body = (b"x" * 100) + b"\r\n.\r\n"
    client.sendall(large_body)
    reply = client.recv(1024)
    client.close()

    assert reply.startswith(b"552 ")
    assert list_messages("david") == []


def test_bad_sequence(isolated_data_dir: Path) -> None:
    """Verify commands out of sequence (e.g. DATA before RCPT TO) return 503."""
    client, _, _ = _make_session_pair()
    client.recv(1024)  # 220

    # DATA before HELO/MAIL/RCPT
    client.sendall(b"DATA\r\n")
    reply = client.recv(1024)
    assert reply.startswith(b"503 ")

    # RCPT before MAIL
    client.sendall(b"HELO client\r\n")
    client.recv(1024)
    client.sendall(b"RCPT TO:<bob@localhost>\r\n")
    reply = client.recv(1024)
    assert reply.startswith(b"503 ")
    client.close()


def test_quit(isolated_data_dir: Path) -> None:
    """Verify QUIT returns 221 and closes connection."""
    client, _, _ = _make_session_pair()
    client.recv(1024)  # 220
    client.sendall(b"QUIT\r\n")
    reply = client.recv(1024)
    assert reply.startswith(b"221 ")
    client.close()

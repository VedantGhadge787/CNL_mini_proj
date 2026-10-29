"""
tests.test_end_to_end
=====================
End-to-end integration tests using smtplib and poplib against the servers.
"""
from __future__ import annotations

import poplib
import smtplib
import threading
import time
from pathlib import Path

import pytest

from mailsys.auth.user_manager import create_user
from mailsys.config.settings import settings
from mailsys.mime.message_builder import (
    build_message,
    extract_attachments,
    parse_message,
)
from mailsys.pop3.server import POP3Server
from mailsys.smtp.server import SMTPServer
from mailsys.storage.mailbox import ensure_mailbox


def _wait_for_server(server: SMTPServer | POP3Server, timeout: float = 3.0) -> int:
    """Wait until server assigns its dynamic port and is ready to accept connections."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if server.port and server._server_sock is not None:
            return server.port
        time.sleep(0.01)
    raise TimeoutError("Server failed to bind in time")


@pytest.fixture
def running_servers(isolated_data_dir: Path):
    """Start local SMTPServer and POP3Server instances on ephemeral ports."""
    create_user("alice", "secret")
    create_user("bob", "secret")
    ensure_mailbox("alice")
    ensure_mailbox("bob")

    smtp_srv = SMTPServer("127.0.0.1", 0)
    pop3_srv = POP3Server("127.0.0.1", 0)

    smtp_thread = threading.Thread(target=smtp_srv.start, daemon=True)
    pop3_thread = threading.Thread(target=pop3_srv.start, daemon=True)

    smtp_thread.start()
    pop3_thread.start()

    smtp_port = _wait_for_server(smtp_srv)
    pop3_port = _wait_for_server(pop3_srv)

    yield smtp_port, pop3_port

    smtp_srv.stop()
    pop3_srv.stop()


def test_full_send_receive_flow(running_servers) -> None:
    """Verify Alice sends message via SMTP, message stored, Bob fetches via POP3."""
    smtp_port, pop3_port = running_servers

    msg = (
        "From: alice@localhost\r\n"
        "To: bob@localhost\r\n"
        "Subject: E2E Greeting\r\n\r\n"
        "Hello Bob from Alice!"
    ).encode("utf-8")

    with smtplib.SMTP("127.0.0.1", smtp_port) as smtp:
        smtp.sendmail("alice@localhost", ["bob@localhost"], msg)

    pop = poplib.POP3("127.0.0.1", pop3_port)
    try:
        pop.user("bob")
        pop.pass_("secret")
        count, _ = pop.stat()
        assert count == 1
        _, lines, _ = pop.retr(1)
        body = b"\r\n".join(lines).decode("utf-8")
        assert "Hello Bob from Alice!" in body
        assert "Subject: E2E Greeting" in body
    finally:
        pop.quit()


def test_spam_routed_to_spam_folder(running_servers) -> None:
    """Verify email containing multiple spam keywords is routed to user's Spam folder."""
    smtp_port, pop3_port = running_servers

    spam_body = (
        "Click here to claim your prize! Limited time offer. Free money! Act now!"
    )
    raw = build_message(
        from_addr="alice@localhost",
        to_addrs=["bob@localhost"],
        subject="Winner announcement",
        body_text=spam_body,
    )

    with smtplib.SMTP("127.0.0.1", smtp_port) as smtp:
        smtp.sendmail("alice@localhost", ["bob@localhost"], raw)

    # Bob's standard POP3 inbox only inspects new/ and cur/ folders, so it should be empty
    pop = poplib.POP3("127.0.0.1", pop3_port)
    try:
        pop.user("bob")
        pop.pass_("secret")
        count, _ = pop.stat()
        assert count == 0
    finally:
        pop.quit()

    # Verify message landed in Spam folder
    spam_dir = Path(settings.data_dir) / "mailboxes" / "bob" / "Spam" / "new"
    assert spam_dir.exists()
    spam_files = list(spam_dir.glob("*.eml"))
    assert len(spam_files) == 1
    content = spam_files[0].read_text(encoding="utf-8")
    assert "X-Spam-Flag: YES" in content


def test_attachment_send_and_retrieve(running_servers, tmp_path: Path) -> None:
    """Verify message with file attachment is sent, retrieved, and attachment decoded identically."""
    smtp_port, pop3_port = running_servers

    attachment_file = tmp_path / "report.pdf"
    file_bytes = b"%PDF-1.4 sample binary test stream content"
    attachment_file.write_bytes(file_bytes)

    raw_mime = build_message(
        from_addr="alice@localhost",
        to_addrs=["bob@localhost"],
        subject="Project Report Attachment",
        body_text="Please find the attached PDF report.",
        attachments=[attachment_file],
    )

    with smtplib.SMTP("127.0.0.1", smtp_port) as smtp:
        smtp.sendmail("alice@localhost", ["bob@localhost"], raw_mime)

    pop = poplib.POP3("127.0.0.1", pop3_port)
    try:
        pop.user("bob")
        pop.pass_("secret")
        _, lines, _ = pop.retr(1)
        raw_retrieved = b"\r\n".join(lines)
    finally:
        pop.quit()

    parsed = parse_message(raw_retrieved)
    out_dir = tmp_path / "extracted"
    saved = extract_attachments(parsed, out_dir)
    assert len(saved) == 1
    assert saved[0].name == "report.pdf"
    assert saved[0].read_bytes() == file_bytes

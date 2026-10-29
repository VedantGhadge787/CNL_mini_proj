"""Unit and integration tests for MailClient and MailApp GUI components."""
from __future__ import annotations

import poplib
import threading
import time
import tkinter as tk
from pathlib import Path

import pytest

from mailsys.auth.user_manager import create_user
from mailsys.client.app import ComposeWindow, MailApp
from mailsys.client.mail_client import MailClient
from mailsys.pop3.server import POP3Server
from mailsys.smtp.server import SMTPServer
from mailsys.storage.mailbox import deliver, list_messages


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


def test_mail_client_attributes_and_address() -> None:
    """Verify MailClient initialization attributes and address property."""
    client = MailClient("alice", "secret", smtp_port=2525, pop3_port=2110)
    assert client.username == "alice"
    assert client.password == "secret"
    assert client.smtp_port == 2525
    assert client.pop3_port == 2110
    assert client.address == "alice@localhost"


def test_mail_client_auth_success(running_servers) -> None:
    """Verify authenticate() succeeds with valid credentials."""
    _, pop3_port = running_servers
    client = MailClient("alice", "secret", pop3_port=pop3_port)
    client.authenticate()


def test_mail_client_auth_failure(running_servers) -> None:
    """Verify authenticate() raises error_proto on invalid password or user."""
    _, pop3_port = running_servers
    client = MailClient("alice", "wrongpass", pop3_port=pop3_port)
    with pytest.raises(poplib.error_proto):
        client.authenticate()

    unknown_client = MailClient("nonexistent", "secret", pop3_port=pop3_port)
    with pytest.raises(poplib.error_proto):
        unknown_client.authenticate()


def test_mail_client_list_inbox_and_fetch(running_servers) -> None:
    """Verify list_inbox parses headers and fetch_message retrieves content."""
    _, pop3_port = running_servers
    deliver("alice", b"From: bob@localhost\r\nSubject: Meeting\r\n\r\nHi Alice")

    client = MailClient("alice", "secret", pop3_port=pop3_port)
    inbox = client.list_inbox()
    assert len(inbox) == 1
    assert inbox[0]["index"] == 1
    assert inbox[0]["subject"] == "Meeting"
    assert inbox[0]["from"] == "bob@localhost"

    msg_str = client.fetch_message(1)
    assert "Hi Alice" in msg_str


def test_mail_client_delete_message(running_servers) -> None:
    """Verify delete_message marks and commits deletion via QUIT."""
    _, pop3_port = running_servers
    deliver("alice", b"From: bob@localhost\r\nSubject: To Delete\r\n\r\nBye")

    client = MailClient("alice", "secret", pop3_port=pop3_port)
    assert len(client.list_inbox()) == 1

    client.delete_message(1)
    assert len(client.list_inbox()) == 0


def test_mail_client_send_and_receive(running_servers, tmp_path: Path) -> None:
    """Verify send_message sends via SMTP and recipient receives via POP3."""
    smtp_port, pop3_port = running_servers

    attachment = tmp_path / "notes.txt"
    attachment.write_text("Secret notes")

    alice = MailClient("alice", "secret", smtp_port=smtp_port, pop3_port=pop3_port)
    bob = MailClient("bob", "secret", smtp_port=smtp_port, pop3_port=pop3_port)

    alice.send_message(
        to_addrs=["bob@localhost"],
        subject="Project Update",
        body="Here is the file.",
        attachments=[attachment],
    )

    inbox = bob.list_inbox()
    assert len(inbox) == 1
    assert inbox[0]["subject"] == "Project Update"
    msg_content = bob.fetch_message(1)
    assert "Here is the file." in msg_content
    assert "notes.txt" in msg_content


def test_mail_app_gui_lifecycle() -> None:
    """Verify MailApp initializes headlessly and executes UI transitions."""
    root = tk.Tk()
    root.withdraw()
    try:
        app = MailApp(root)
        assert app.login_frame is not None

        # Verify login entry fields exist
        app.user_entry.insert(0, "alice")
        app.pass_entry.insert(0, "secret")

        # Manually switch to main window
        dummy_client = MailClient("alice", "secret")
        app.client = dummy_client
        app.show_main_window()
        assert app.main_frame is not None
        assert app.login_frame is None

        # Test inbox population
        sample_messages = [
            {"index": 1, "subject": "Test Subj", "from": "bob@localhost", "date": "", "size": "100"}
        ]
        app._on_refresh_success(sample_messages)
        assert app.inbox_listbox.size() == 1
        assert "Test Subj" in app.inbox_listbox.get(0)

        # Test message display
        sample_raw = "From: bob@localhost\r\nSubject: Test Subj\r\n\r\nHello World!"
        app._display_message(1, sample_raw)
        assert app.subj_lbl.cget("text") == "Subject: Test Subj"
        assert "Hello World!" in app.preview_text.get("1.0", tk.END)

        # Test compose window
        compose = ComposeWindow(root, dummy_client)
        compose.to_entry.insert(0, "bob@localhost")
        compose.subject_entry.insert(0, "Greetings")
        compose.body_text.insert("1.0", "How are you?")
        compose.destroy()

        # Test logout transition
        app._on_logout()
        assert app.login_frame is not None
        assert app.main_frame is None
    finally:
        root.destroy()

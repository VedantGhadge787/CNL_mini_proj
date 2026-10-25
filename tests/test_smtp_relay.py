"""Unit tests for MX resolution and outbound SMTP relay behavior."""
from __future__ import annotations

import smtplib
import socket
from pathlib import Path

import dns.exception
import dns.resolver
import pytest

from mailsys.auth.user_manager import create_user
from mailsys.mime.message_builder import parse_message
from mailsys.smtp import relay, session as smtp_session
from mailsys.smtp.session import SMTPSession
from mailsys.storage.mailbox import list_messages, read_message


class FakeMX:
    """Minimal MX record value for deterministic resolver tests."""

    def __init__(self, preference: int, exchange: str) -> None:
        self.preference = preference
        self.exchange = exchange


def test_lookup_mx_sorts_preference_and_strips_trailing_dot(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Return hostnames in priority order without trailing DNS root dots."""
    monkeypatch.setattr(
        relay.dns.resolver,
        "resolve",
        lambda domain, record_type: [
            FakeMX(20, "backup.example."),
            FakeMX(10, "primary.example."),
        ],
    )

    assert relay.lookup_mx("example.test") == ["primary.example", "backup.example"]


@pytest.mark.parametrize(
    "error",
    [
        dns.resolver.NXDOMAIN(),
        dns.resolver.NoAnswer(),
        dns.resolver.NoNameservers(),
        dns.exception.Timeout(),
    ],
)
def test_lookup_mx_returns_empty_on_dns_failure(
    monkeypatch: pytest.MonkeyPatch, error: Exception
) -> None:
    """Convert common DNS lookup failures to an empty MX list."""
    def raise_dns_error(domain: str, record_type: str) -> None:
        raise error

    monkeypatch.setattr(relay.dns.resolver, "resolve", raise_dns_error)
    assert relay.lookup_mx("missing.example") == []


def test_relay_tries_mx_hosts_until_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """Continue to the next MX after an SMTP connection failure."""
    calls: list[tuple[str, int, int]] = []

    class SuccessfulSMTP:
        """Fake SMTP client that succeeds for the second MX host."""

        def __init__(self, host: str, port: int, timeout: int) -> None:
            calls.append((host, port, timeout))
            if host == "primary.example":
                raise OSError("connection refused")

        def __enter__(self) -> SuccessfulSMTP:
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def sendmail(self, sender: str, recipients: list[str], raw: bytes) -> dict:
            assert sender == "sender@localhost"
            assert recipients == ["recipient@example.test"]
            assert raw == b"Subject: test\r\n\r\nbody"
            return {}

    monkeypatch.setattr(
        relay, "lookup_mx", lambda domain: ["primary.example", "backup.example"]
    )
    monkeypatch.setattr(relay.smtplib, "SMTP", SuccessfulSMTP)

    assert relay.relay_message(
        "recipient@example.test", b"Subject: test\r\n\r\nbody", "sender@localhost"
    )
    assert calls == [
        ("primary.example", 25, 30),
        ("backup.example", 25, 30),
    ]


def test_relay_retries_after_recipient_refusal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Continue to the next MX when an SMTP server refuses the recipient."""
    class RefusingSMTP:
        """Fake SMTP client that rejects the recipient at the primary MX."""

        def __init__(self, host: str, port: int, timeout: int) -> None:
            self.host = host

        def __enter__(self) -> RefusingSMTP:
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def sendmail(self, sender: str, recipients: list[str], raw: bytes) -> dict:
            if self.host == "primary.example":
                return {recipients[0]: (550, b"recipient rejected")}
            return {}

    hosts: list[str] = []

    def smtp_factory(host: str, port: int, timeout: int) -> RefusingSMTP:
        hosts.append(host)
        return RefusingSMTP(host, port, timeout)

    monkeypatch.setattr(
        relay, "lookup_mx", lambda domain: ["primary.example", "backup.example"]
    )
    monkeypatch.setattr(relay.smtplib, "SMTP", smtp_factory)

    assert relay.relay_message("recipient@example.test", b"message")
    assert hosts == ["primary.example", "backup.example"]


def test_relay_attempts_all_hosts_and_delivers_local_bounce(
    isolated_data_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Deliver a failure notification to the local sender after all MX failures."""
    create_user("alice", "secret")
    monkeypatch.setattr(
        relay, "lookup_mx", lambda domain: ["mx1.example", "mx2.example"]
    )

    def failed_smtp(host: str, port: int, timeout: int) -> None:
        raise smtplib.SMTPConnectError(421, b"temporarily unavailable")

    monkeypatch.setattr(relay.smtplib, "SMTP", failed_smtp)

    assert not relay.relay_message(
        "recipient@example.test", b"Subject: original\r\n\r\nmessage", "alice@localhost"
    )
    messages = list_messages("alice")
    assert len(messages) == 1
    bounce = parse_message(read_message("alice", 1))
    assert bounce["From"] == "mailer-daemon@localhost"
    assert bounce["To"] == "alice@localhost"
    assert "recipient@example.test" in bounce["Subject"]
    assert "All MX hosts failed" in str(bounce.get_body().get_content())


def test_no_mx_emails_bounce_but_external_sender_does_not(
    isolated_data_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Bounce when DNS has no MX, but never deliver to a non-local sender."""
    create_user("alice", "secret")
    monkeypatch.setattr(relay, "lookup_mx", lambda domain: [])

    assert not relay.relay_message(
        "recipient@example.test", b"Subject: test\r\n\r\nbody", "alice@localhost"
    )
    assert len(list_messages("alice")) == 1
    assert not relay.relay_message(
        "recipient@example.test", b"Subject: test\r\n\r\nbody", "remote@example.org"
    )
    assert len(list_messages("alice")) == 1


def test_smtp_session_relays_spam_annotated_external_message(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pass the annotated message and envelope sender to the relay helper."""
    client, server = socket.socketpair()
    session = SMTPSession(server, ("127.0.0.1", 25250))
    session.mail_from = "alice@localhost"
    session.rcpt_to = ["recipient@example.test"]
    monkeypatch.setattr(
        smtp_session.spam_filter, "score_message", lambda raw: (2, False)
    )
    relayed: list[tuple[str, str, bytes]] = []

    def capture_relay(recipient: str, raw: bytes, sender: str = "") -> bool:
        relayed.append((recipient, sender, raw))
        return True

    monkeypatch.setattr(smtp_session, "relay_message", capture_relay)
    try:
        session._deliver_or_relay(b"Subject: test\r\n\r\nbody")
    finally:
        client.close()
        server.close()

    assert len(relayed) == 1
    recipient, sender, raw = relayed[0]
    assert recipient == "recipient@example.test"
    assert sender == "alice@localhost"
    message = parse_message(raw)
    assert message["X-Spam-Flag"] == "NO"
    assert message["X-Spam-Score"] == "2"

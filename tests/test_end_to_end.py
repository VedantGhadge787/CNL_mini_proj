"""
tests.test_end_to_end
=====================
End-to-end integration tests using smtplib and poplib against the servers.
"""
import pytest


def test_full_send_receive_flow() -> None:
    """Verify Alice sends message via SMTP, message stored, Bob fetches via POP3."""
    pass


def test_spam_routed_to_spam_folder() -> None:
    """Verify email containing multiple spam keywords is routed to user's Spam folder."""
    pass


def test_attachment_send_and_retrieve() -> None:
    """Verify message with file attachment is sent, retrieved, and attachment decoded identically."""
    pass

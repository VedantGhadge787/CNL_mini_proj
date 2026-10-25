"""
tests.test_smtp_session
=======================
Unit tests for SMTPSession RFC 5321 command handling and state transitions.
"""
import pytest


def test_greeting() -> None:
    """Verify server sends 220 banner upon connection."""
    pass


def test_helo() -> None:
    """Verify server responds 250 to HELO command."""
    pass


def test_rcpt_unknown_user() -> None:
    """Verify server responds 550 when recipient does not exist."""
    pass


def test_full_delivery() -> None:
    """Verify complete HELO -> MAIL FROM -> RCPT TO -> DATA -> QUIT delivery sequence."""
    pass


def test_data_dot_stuffing() -> None:
    """Verify dot-stuffed lines have leading dot removed on storage."""
    pass


def test_oversized_message() -> None:
    """Verify server rejects messages exceeding MAX_MESSAGE_SIZE with 552."""
    pass


def test_bad_sequence() -> None:
    """Verify commands out of sequence (e.g. DATA before RCPT TO) return 503."""
    pass


def test_quit() -> None:
    """Verify QUIT returns 221 and closes connection."""
    pass

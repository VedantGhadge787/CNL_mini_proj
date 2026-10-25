"""
tests.test_mime
===============
Unit tests for MIME message building, parsing, and attachment handling.
"""
import pytest
from pathlib import Path


def test_build_plain_text() -> None:
    """Verify build_message creates valid single-part text/plain RFC 2822 message."""
    pass


def test_build_multipart_alternative() -> None:
    """Verify build_message with HTML body produces multipart/alternative."""
    pass


def test_build_with_attachments(tmp_path: Path) -> None:
    """Verify build_message with files produces multipart/mixed with attachments."""
    pass


def test_parse_message_roundtrip(tmp_path: Path) -> None:
    """Verify parse_message accurately reconstructs body, headers, and attachments."""
    pass


def test_extract_attachments_path_traversal_safety(tmp_path: Path) -> None:
    """Verify attachment filename sanitization prevents directory traversal attacks."""
    pass

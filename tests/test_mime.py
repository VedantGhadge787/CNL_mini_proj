"""
tests.test_mime
===============
Unit tests for MIME message building, parsing, and attachment handling.
"""
from __future__ import annotations

import email.policy
import tempfile
from email.message import EmailMessage
from pathlib import Path

import pytest

from mailsys.mime.message_builder import (
    _guess_mimetype,
    _sanitize_filename,
    build_message,
    extract_attachments,
    get_html_body,
    get_text_body,
    list_attachments,
    parse_message,
)


def test_build_plain_text() -> None:
    """Verify build_message creates valid single-part text/plain RFC 2822 message."""
    raw = build_message(
        from_addr="alice@localhost",
        to_addrs=["bob@localhost", "carol@localhost"],
        subject="Simple Text Email",
        body_text="Hello, this is a plain text email.\nSecond line.",
    )

    # Must be bytes formatted with CRLF
    assert isinstance(raw, bytes)
    assert b"\r\n" in raw

    # Parse and inspect
    msg = parse_message(raw)
    assert msg["From"] == "alice@localhost"
    assert msg["To"] == "bob@localhost, carol@localhost"
    assert msg["Subject"] == "Simple Text Email"
    assert msg["Date"] is not None
    assert msg["Message-ID"] is not None
    assert "@" in msg["Message-ID"]

    assert msg.get_content_type() == "text/plain"
    assert get_text_body(msg) == "Hello, this is a plain text email.\nSecond line."
    assert get_html_body(msg) is None
    assert list_attachments(msg) == []


def test_build_multipart_alternative() -> None:
    """Verify build_message with HTML body produces multipart/alternative."""
    raw = build_message(
        from_addr="alice@localhost",
        to_addrs=["bob@localhost"],
        subject="HTML Email",
        body_text="Plain fallback text.",
        body_html="<html><body><h1>HTML Version</h1></body></html>",
    )

    msg = parse_message(raw)
    assert msg.get_content_type() == "multipart/alternative"
    assert get_text_body(msg) == "Plain fallback text."
    assert get_html_body(msg) == "<html><body><h1>HTML Version</h1></body></html>"
    assert list_attachments(msg) == []


def test_build_with_attachments(tmp_path: Path) -> None:
    """Verify build_message with files produces multipart/mixed with attachments."""
    txt_file = tmp_path / "notes.txt"
    txt_file.write_text("Secret notes content", encoding="utf-8")

    bin_file = tmp_path / "data.bin"
    bin_file.write_bytes(b"\x00\x01\x02\x03\x04\xff")

    raw = build_message(
        from_addr="alice@localhost",
        to_addrs=["bob@localhost"],
        subject="Email with attachments",
        body_text="Here are your requested files.",
        attachments=[txt_file, bin_file],
    )

    msg = parse_message(raw)
    assert msg.get_content_type() == "multipart/mixed"
    assert get_text_body(msg) == "Here are your requested files."

    atts = list_attachments(msg)
    assert len(atts) == 2

    # Verify attachment metadata
    names = [att[0] for att in atts]
    assert "notes.txt" in names
    assert "data.bin" in names

    out_dir = tmp_path / "extracted"
    saved = extract_attachments(msg, out_dir)
    assert len(saved) == 2

    saved_txt = next(p for p in saved if p.name == "notes.txt")
    assert saved_txt.read_text(encoding="utf-8") == "Secret notes content"

    saved_bin = next(p for p in saved if p.name == "data.bin")
    assert saved_bin.read_bytes() == b"\x00\x01\x02\x03\x04\xff"


def test_parse_message_roundtrip(tmp_path: Path) -> None:
    """Verify parse_message accurately reconstructs body, headers, and attachments."""
    doc_file = tmp_path / "report.pdf"
    doc_file.write_bytes(b"%PDF-1.4 sample content")

    raw = build_message(
        from_addr="sender@example.com",
        to_addrs=["recv1@example.com", "recv2@example.com"],
        subject="Monthly Report",
        body_text="Please find the monthly report attached.",
        body_html="<p>Please find the monthly report attached.</p>",
        attachments=[doc_file],
    )

    msg = parse_message(raw)
    assert msg["From"] == "sender@example.com"
    assert msg["To"] == "recv1@example.com, recv2@example.com"
    assert msg["Subject"] == "Monthly Report"
    assert msg.get_content_type() == "multipart/mixed"

    assert get_text_body(msg) == "Please find the monthly report attached."
    assert get_html_body(msg) == "<p>Please find the monthly report attached.</p>"

    dest = tmp_path / "output"
    extracted = extract_attachments(msg, dest)
    assert len(extracted) == 1
    assert extracted[0].name == "report.pdf"
    assert extracted[0].read_bytes() == b"%PDF-1.4 sample content"


def test_extract_attachments_path_traversal_safety(tmp_path: Path) -> None:
    """Verify attachment filename sanitization prevents directory traversal attacks."""
    msg = EmailMessage()
    msg["From"] = "attacker@example.com"
    msg["To"] = "victim@example.com"
    msg["Subject"] = "Exploit Attempt"
    msg.set_content("Malicious payload delivery")

    # Add attachments with traversal paths
    msg.add_attachment(
        b"malicious posix",
        maintype="application",
        subtype="octet-stream",
        filename="../../evil_posix.sh",
    )
    msg.add_attachment(
        b"malicious windows",
        maintype="application",
        subtype="octet-stream",
        filename="..\\..\\evil_win.bat",
    )
    msg.add_attachment(
        b"absolute path",
        maintype="application",
        subtype="octet-stream",
        filename="/etc/shadow",
    )

    dest_dir = tmp_path / "sandbox"
    saved = extract_attachments(msg, dest_dir)

    assert len(saved) == 3
    for saved_path in saved:
        # Every saved path MUST be directly within dest_dir
        assert saved_path.parent.resolve() == dest_dir.resolve()
        assert not saved_path.name.startswith("..")
        assert "/" not in saved_path.name
        assert "\\" not in saved_path.name

    saved_names = [p.name for p in saved]
    assert "evil_posix.sh" in saved_names
    assert "evil_win.bat" in saved_names
    assert "shadow" in saved_names


def test_skip_inline_attachments(tmp_path: Path) -> None:
    """Verify inline parts are excluded from extract_attachments and list_attachments."""
    msg = EmailMessage()
    msg["From"] = "sender@example.com"
    msg["To"] = "receiver@example.com"
    msg["Subject"] = "Inline image"
    msg.set_content("Email with inline image")

    # Inline part
    msg.add_attachment(
        b"<image data>",
        maintype="image",
        subtype="png",
        disposition="inline",
        filename="inline_logo.png",
    )
    # Regular attachment
    msg.add_attachment(
        b"<document data>",
        maintype="application",
        subtype="pdf",
        disposition="attachment",
        filename="document.pdf",
    )

    atts = list_attachments(msg)
    assert len(atts) == 1
    assert atts[0][0] == "document.pdf"

    dest = tmp_path / "dest"
    saved = extract_attachments(msg, dest)
    assert len(saved) == 1
    assert saved[0].name == "document.pdf"


def test_sanitize_filename_edge_cases() -> None:
    """Verify _sanitize_filename handles None, empty, dot, and relative components."""
    assert _sanitize_filename(None) == "attachment"
    assert _sanitize_filename("") == "attachment"
    assert _sanitize_filename(".") == "attachment"
    assert _sanitize_filename("..") == "attachment"
    assert _sanitize_filename("../../../file.txt") == "file.txt"
    assert _sanitize_filename("C:\\Users\\Admin\\Desktop\\report.docx") == "report.docx"


def test_guess_mimetype() -> None:
    """Verify _guess_mimetype accurately identifies standard MIME types."""
    assert _guess_mimetype(Path("test.txt")) == ("text", "plain")
    assert _guess_mimetype(Path("test.html")) == ("text", "html")
    assert _guess_mimetype(Path("test.png")) == ("image", "png")
    assert _guess_mimetype(Path("test.customextunknown123")) == ("application", "octet-stream")

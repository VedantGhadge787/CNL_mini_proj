"""
mailsys.mime.message_builder
============================
MIME message construction, parsing, and attachment extraction using Python's stdlib `email`.

Provides:
  - `build_message`: create text/plain, multipart/alternative, or multipart/mixed email bytes.
  - `parse_message`: parse raw bytes into an `EmailMessage` object.
  - `get_text_body`: extract plain text body from parsed message.
  - `get_html_body`: extract HTML body if present.
  - `extract_attachments`: save attachments to a target directory.
  - `list_attachments`: list attachment filenames, MIME types, and sizes.
"""
from __future__ import annotations

import email.policy
import email.utils
import mimetypes
from email.message import EmailMessage
from email.parser import BytesParser
from pathlib import Path

from mailsys.common.logger import get_logger
from mailsys.config.settings import settings

logger = get_logger(__name__)


def _guess_mimetype(path: Path) -> tuple[str, str]:
    """Guess the MIME main type and subtype for a given file path.

    Args:
        path: File path to inspect.

    Returns:
        tuple[str, str]: (maintype, subtype) tuple e.g. ('image', 'png').
    """
    mime, _ = mimetypes.guess_type(str(path))
    if mime and "/" in mime:
        parts = mime.split("/", 1)
        return parts[0], parts[1]
    return "application", "octet-stream"


def _sanitize_filename(filename: str | None) -> str:
    """Sanitize an attachment filename to prevent directory traversal attacks.

    Args:
        filename: Raw filename string from Content-Disposition.

    Returns:
        str: Safe basename suitable for writing to disk.
    """
    if not filename:
        return "attachment"
    clean_name = filename.replace("\\", "/")
    safe_name = Path(clean_name).name
    if not safe_name or safe_name in (".", ".."):
        return "attachment"
    return safe_name


def _normalize_text(text: str) -> str:
    """Normalize CRLF line endings to LF and strip trailing newline added by MIME.

    Args:
        text: Raw decoded text.

    Returns:
        str: Normalized text string.
    """
    text = text.replace("\r\n", "\n")
    if text.endswith("\n"):
        text = text[:-1]
    return text


def build_message(
    from_addr: str,
    to_addrs: list[str],
    subject: str,
    body_text: str,
    body_html: str | None = None,
    attachments: list[Path] | None = None,
) -> bytes:
    """Build a MIME message and return it as RFC 2822-compliant bytes.

    Args:
        from_addr: Sender email address.
        to_addrs: List of recipient email addresses.
        subject: Subject header string.
        body_text: Plain-text body.
        body_html: Optional HTML body.
        attachments: Optional list of local file Paths to attach.

    Returns:
        bytes: Raw message bytes formatted with CRLF line endings.
    """
    msg = EmailMessage()
    msg["From"] = from_addr
    msg["To"] = ", ".join(to_addrs)
    msg["Subject"] = subject
    msg["Date"] = email.utils.formatdate(localtime=True)
    msg["Message-ID"] = email.utils.make_msgid(domain=settings.local_domain)

    msg.set_content(body_text)
    if body_html:
        msg.add_alternative(body_html, subtype="html")

    if attachments:
        for path in attachments:
            path_obj = Path(path)
            maintype, subtype = _guess_mimetype(path_obj)
            msg.add_attachment(
                path_obj.read_bytes(),
                maintype=maintype,
                subtype=subtype,
                filename=path_obj.name,
            )

    logger.debug(
        "Built MIME message: Subject=%r From=%r To=%r Attachments=%d",
        subject,
        from_addr,
        to_addrs,
        len(attachments) if attachments else 0,
    )
    return msg.as_bytes(policy=email.policy.SMTP)


def parse_message(raw: bytes) -> EmailMessage:
    """Parse raw .eml bytes into an EmailMessage object.

    Args:
        raw: Raw email bytes.

    Returns:
        EmailMessage: Parsed email message object.
    """
    return BytesParser(policy=email.policy.default).parsebytes(raw)


def get_text_body(msg: EmailMessage) -> str:
    """Extract the plain-text body from a parsed EmailMessage.

    Args:
        msg: Parsed EmailMessage.

    Returns:
        str: Extracted plain text content, or empty string if not found.
    """
    for part in msg.walk():
        if part.get_content_type() == "text/plain" and not part.is_attachment():
            payload = part.get_payload(decode=True)
            if payload is not None:
                charset = part.get_content_charset() or "utf-8"
                return _normalize_text(payload.decode(charset, errors="replace"))
            content = part.get_content()
            return _normalize_text(str(content)) if content is not None else ""
    return ""


def get_html_body(msg: EmailMessage) -> str | None:
    """Extract the HTML body from a parsed EmailMessage, or None if absent.

    Args:
        msg: Parsed EmailMessage.

    Returns:
        str | None: Decoded HTML string or None.
    """
    for part in msg.walk():
        if part.get_content_type() == "text/html" and not part.is_attachment():
            payload = part.get_payload(decode=True)
            if payload is not None:
                charset = part.get_content_charset() or "utf-8"
                return _normalize_text(payload.decode(charset, errors="replace"))
            content = part.get_content()
            return _normalize_text(str(content)) if content is not None else None
    return None


def get_attachment_parts(msg: EmailMessage) -> list[dict]:
    """Extract all attachment parts with their filename, content-type, size, and payload bytes.

    Skips parts with Content-Disposition: inline.

    Args:
        msg: Parsed EmailMessage.

    Returns:
        list[dict]: List of dictionaries with keys:
                    'filename', 'content_type', 'size', 'payload'.
    """
    attachments: list[dict] = []
    for part in msg.iter_attachments():
        if part.get_content_disposition() == "inline":
            continue
        safe_name = _sanitize_filename(part.get_filename())
        content_type = part.get_content_type()
        payload = part.get_payload(decode=True)
        size = len(payload) if payload is not None else 0
        attachments.append({
            "filename": safe_name,
            "content_type": content_type,
            "size": size,
            "payload": payload if payload is not None else b"",
        })
    return attachments


def extract_attachments(msg: EmailMessage, dest_dir: Path) -> list[Path]:
    """Save all attachment parts to dest_dir and return a list of saved Paths.

    Skips parts with Content-Disposition: inline.

    Args:
        msg: Parsed EmailMessage.
        dest_dir: Destination directory.

    Returns:
        list[Path]: List of saved file paths.
    """
    saved: list[Path] = []
    dest_dir.mkdir(parents=True, exist_ok=True)

    for item in get_attachment_parts(msg):
        safe_name = item["filename"]
        out_path = dest_dir / safe_name
        if out_path in saved or out_path.exists():
            stem, suffix = Path(safe_name).stem, Path(safe_name).suffix
            counter = 1
            while out_path in saved or out_path.exists():
                out_path = dest_dir / f"{stem}_{counter}{suffix}"
                counter += 1

        out_path.write_bytes(item["payload"])
        saved.append(out_path)

    logger.debug("Extracted %d attachments to %s", len(saved), dest_dir)
    return saved


def list_attachments(msg: EmailMessage) -> list[tuple[str, str, int]]:
    """Return a list of (filename, content_type, size_in_bytes) for attachments.

    Skips parts with Content-Disposition: inline.

    Args:
        msg: Parsed EmailMessage.

    Returns:
        list[tuple[str, str, int]]: List of (filename, content_type, size) tuples.
    """
    return [
        (item["filename"], item["content_type"], item["size"])
        for item in get_attachment_parts(msg)
    ]


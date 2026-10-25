"""
mailsys.mime
============
MIME message construction, parsing, and attachment handling sub-package.

Exports:
    build_message       — build RFC 2822/MIME compliant bytes
    parse_message       — parse bytes into EmailMessage object
    get_text_body       — extract text/plain payload
    get_html_body       — extract text/html payload
    extract_attachments — save attachments to disk
    list_attachments    — inspect attachments metadata
"""
from mailsys.mime.message_builder import (  # noqa: F401
    build_message,
    parse_message,
    get_text_body,
    get_html_body,
    extract_attachments,
    list_attachments,
)

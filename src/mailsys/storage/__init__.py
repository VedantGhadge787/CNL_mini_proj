"""
mailsys.storage
===============
Mailbox storage sub-package.

Exports:
    ensure_mailbox  — create folder structure for a user
    deliver         — write raw email bytes to a user's mailbox
    list_messages   — enumerate stored messages
    read_message    — read raw bytes of a message
    delete_message  — permanently remove a message
    generate_uid    — compute stable UID for POP3 UIDL
"""
from mailsys.storage.mailbox import (  # noqa: F401
    ensure_mailbox,
    deliver,
    list_messages,
    read_message,
    delete_message,
    generate_uid,
)

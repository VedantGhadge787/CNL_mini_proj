"""
mailsys.client
==============
Desktop client sub-package (Tkinter GUI and protocol client).

Exports:
    MailClient  — backend wrapping smtplib and poplib
    MailApp     — Tkinter GUI application
"""
from mailsys.client.mail_client import MailClient  # noqa: F401

"""
mailsys.smtp
============
SMTP server and relay sub-package.

Exports:
    SMTPServer   — threaded TCP server listening for SMTP connections
    SMTPSession  — RFC 5321 protocol state machine per connection
    relay_message— outbound MX lookup and relay to remote domains
"""
from mailsys.smtp.server import SMTPServer  # noqa: F401
from mailsys.smtp.session import SMTPSession  # noqa: F401

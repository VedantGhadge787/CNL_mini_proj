"""
mailsys.client.mail_client
==========================
High-level client wrapper around Python's standard `smtplib` and `poplib`.

Used by the Tkinter desktop GUI and end-to-end integration tests to interact
with the hand-written SMTP and POP3 servers.

Provides:
  - `list_inbox`: retrieves list of message headers via POP3 TOP command.
  - `fetch_message`: retrieves full raw message via POP3 RETR command.
  - `delete_message`: marks and commits deletion via POP3 DELE + QUIT.
  - `send_message`: constructs MIME message and sends via SMTP sendmail.

Imports needed:
    import poplib
    import smtplib
    from email import message_from_bytes
    from pathlib import Path
    from mailsys.config.settings import settings
    from mailsys.mime.message_builder import build_message
"""
import poplib
import smtplib
from email import message_from_bytes
from pathlib import Path
from mailsys.config.settings import settings
from mailsys.mime.message_builder import build_message


class MailClient:
    """High-level client wrapping smtplib and poplib."""

    def __init__(
        self,
        username: str,
        password: str,
        smtp_host: str = "localhost",
        smtp_port: int | None = None,
        pop3_host: str = "localhost",
        pop3_port: int | None = None,
    ) -> None:
        self.username = username
        self.password = password
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port if smtp_port is not None else getattr(settings, "smtp_port", 2525)
        self.pop3_host = pop3_host
        self.pop3_port = pop3_port if pop3_port is not None else getattr(settings, "pop3_port", 2110)
        self._domain = getattr(settings, "local_domain", "localhost")

    @property
    def address(self) -> str:
        """User email address."""
        return f"{self.username}@{self._domain}"

    def list_inbox(self) -> list[dict]:
        """Connect via POP3, fetch message headers with TOP, disconnect.

        Returns:
            list[dict]: List of message header dicts with keys:
                        index, subject, from, date, size.

        TODO:
            - Connect to poplib.POP3(self.pop3_host, self.pop3_port)
            - Send user/pass
            - Call pop.stat()
            - For each message index 1..count: call pop.top(i, 0), parse headers
            - Send pop.quit()
            - Return list of dicts
        """
        # TODO: Implement
        raise NotImplementedError

    def fetch_message(self, index: int) -> str:
        """Fetch the full raw message at index via POP3 RETR.

        Args:
            index: 1-based message index.

        Returns:
            str: Raw message string.

        TODO:
            - Connect to POP3, auth, call pop.retr(index)
            - Join lines with CRLF and decode
            - Call pop.quit() and return string
        """
        # TODO: Implement
        raise NotImplementedError

    def delete_message(self, index: int) -> None:
        """Mark message at index for deletion and commit via QUIT.

        Args:
            index: 1-based message index.

        TODO:
            - Connect to POP3, auth, call pop.dele(index)
            - Call pop.quit() to commit deletion
        """
        # TODO: Implement
        raise NotImplementedError

    def send_message(
        self,
        to_addrs: list[str],
        subject: str,
        body: str,
        attachments: list[Path] | None = None,
    ) -> None:
        """Build and send a MIME message via SMTP.

        Args:
            to_addrs: List of recipient email addresses.
            subject: Email subject line.
            body: Plain-text email body.
            attachments: Optional list of attachment Paths.

        TODO:
            - Call build_message(...)
            - Connect with smtplib.SMTP(self.smtp_host, self.smtp_port)
            - Sendmail(self.address, to_addrs, raw_bytes)
        """
        # TODO: Implement
        raise NotImplementedError

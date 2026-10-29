"""
mailsys.client.mail_client
==========================
High-level client wrapper around Python's standard `smtplib` and `poplib`.

Used by the Tkinter desktop GUI and end-to-end integration tests to interact
with the hand-written SMTP and POP3 servers.

Provides:
  - `authenticate`: verifies credentials with POP3 server.
  - `list_inbox`: retrieves list of message headers via POP3 TOP command.
  - `fetch_message`: retrieves full raw message via POP3 RETR command.
  - `delete_message`: marks and commits deletion via POP3 DELE + QUIT.
  - `send_message`: constructs MIME message and sends via SMTP sendmail.
"""
from __future__ import annotations

import poplib
import smtplib
from email import message_from_bytes
from pathlib import Path

from mailsys.common.logger import get_logger
from mailsys.config.settings import settings
from mailsys.mime.message_builder import build_message

logger = get_logger(__name__)


class MailClient:
    """High-level mail client wrapping smtplib and poplib."""

    def __init__(
        self,
        username: str,
        password: str,
        smtp_host: str = "localhost",
        smtp_port: int | None = None,
        pop3_host: str = "localhost",
        pop3_port: int | None = None,
    ) -> None:
        """Initialize MailClient with user credentials and server coordinates.

        Args:
            username: User account name (without domain).
            password: User account password.
            smtp_host: SMTP server hostname.
            smtp_port: SMTP server port (defaults to settings.smtp_port).
            pop3_host: POP3 server hostname.
            pop3_port: POP3 server port (defaults to settings.pop3_port).
        """
        self.username = username
        self.password = password
        self.smtp_host = smtp_host
        self.smtp_port = (
            smtp_port if smtp_port is not None else getattr(settings, "smtp_port", 2525)
        )
        self.pop3_host = pop3_host
        self.pop3_port = (
            pop3_port if pop3_port is not None else getattr(settings, "pop3_port", 2110)
        )
        self._domain = getattr(settings, "local_domain", "localhost")

    @property
    def address(self) -> str:
        """Full email address for the user."""
        return f"{self.username}@{self._domain}"

    def authenticate(self) -> None:
        """Verify user credentials against the POP3 server.

        Raises:
            poplib.error_proto: If authentication fails.
            OSError: If connecting to the POP3 server fails.
        """
        pop = poplib.POP3(self.pop3_host, self.pop3_port)
        try:
            pop.user(self.username)
            pop.pass_(self.password)
        finally:
            try:
                pop.quit()
            except Exception:
                pass

    def _fetch_sizes(self, pop: poplib.POP3) -> dict[int, str]:
        """Fetch message sizes via POP3 LIST command.

        Args:
            pop: Authenticated POP3 connection.

        Returns:
            dict[int, str]: Mapping of 1-based message index to size string.
        """
        sizes: dict[int, str] = {}
        try:
            _, lines, _ = pop.list()
            for line in lines:
                parts = line.split()
                if len(parts) >= 2:
                    sizes[int(parts[0])] = parts[1].decode("utf-8", errors="replace")
        except Exception:
            logger.debug("Failed to fetch message sizes via LIST", exc_info=True)
        return sizes

    def list_inbox(self) -> list[dict]:
        """Connect via POP3, fetch message headers with TOP, and disconnect.

        Returns:
            list[dict]: List of message header dicts with keys:
                        index, subject, from, date, size.
        """
        pop = poplib.POP3(self.pop3_host, self.pop3_port)
        try:
            pop.user(self.username)
            pop.pass_(self.password)
            count, _ = pop.stat()
            sizes = self._fetch_sizes(pop)
            messages: list[dict] = []
            for i in range(1, count + 1):
                raw_lines = pop.top(i, 0)[1]
                raw = b"\r\n".join(raw_lines)
                msg = message_from_bytes(raw)
                messages.append({
                    "index": i,
                    "subject": msg.get("Subject", "(no subject)"),
                    "from": msg.get("From", ""),
                    "date": msg.get("Date", ""),
                    "size": sizes.get(i, ""),
                })
            return messages
        finally:
            try:
                pop.quit()
            except Exception:
                pass

    def fetch_message(self, index: int) -> str:
        """Fetch the full raw message at index via POP3 RETR.

        Args:
            index: 1-based message index.

        Returns:
            str: Raw message string.
        """
        pop = poplib.POP3(self.pop3_host, self.pop3_port)
        try:
            pop.user(self.username)
            pop.pass_(self.password)
            _, lines, _ = pop.retr(index)
            return b"\r\n".join(lines).decode("utf-8", errors="replace")
        finally:
            try:
                pop.quit()
            except Exception:
                pass

    def delete_message(self, index: int) -> None:
        """Mark message at index for deletion and commit via QUIT.

        Args:
            index: 1-based message index.
        """
        pop = poplib.POP3(self.pop3_host, self.pop3_port)
        try:
            pop.user(self.username)
            pop.pass_(self.password)
            pop.dele(index)
            pop.quit()
        except Exception:
            try:
                pop.quit()
            except Exception:
                pass
            raise

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
        """
        raw = build_message(
            from_addr=self.address,
            to_addrs=to_addrs,
            subject=subject,
            body_text=body,
            attachments=attachments,
        )
        with smtplib.SMTP(self.smtp_host, self.smtp_port) as smtp:
            smtp.sendmail(self.address, to_addrs, raw)

"""
mailsys.smtp.session
====================
Hand-written RFC 5321 SMTP protocol state machine over a raw socket connection.

Supported commands:
  - HELO / EHLO
  - MAIL FROM
  - RCPT TO
  - DATA (with dot-stuffing handling and max size limit)
  - RSET
  - NOOP
  - VRFY
  - QUIT

State transitions:
  CONNECTED -> GREETED -> IDENTIFIED -> MAIL -> RCPT -> DATA -> IDENTIFIED
  QUIT terminates the session from any state.
"""
import enum
import socket
from mailsys.auth.user_manager import user_exists
from mailsys.common.logger import get_logger
from mailsys.common.protocol_utils import recv_line, send_reply
from mailsys.config.settings import settings
from mailsys.storage.mailbox import deliver

logger = get_logger(__name__)


class SMTPState(enum.Enum):
    """SMTP session states per RFC 5321."""

    CONNECTED = "CONNECTED"
    GREETED = "GREETED"
    IDENTIFIED = "IDENTIFIED"
    MAIL = "MAIL"
    RCPT = "RCPT"
    DATA = "DATA"
    CLOSED = "CLOSED"


class SMTPSession:
    """Manages an individual SMTP client connection state machine."""

    def __init__(self, conn: socket.socket, addr: tuple[str, int]) -> None:
        self.conn = conn
        self.addr = addr
        self.state = SMTPState.CONNECTED
        self.client_domain: str | None = None
        self.mail_from: str | None = None
        self.rcpt_to: list[str] = []
        self.data_buffer: bytearray = bytearray()
        self.logger = get_logger(__name__)

    def handle(self) -> None:
        """Main session loop: send 220 banner, then read and dispatch commands."""
        local_domain = getattr(settings, "local_domain", "localhost")
        send_reply(
            self.conn, 220, f"{local_domain} Simple Mail Transfer Service Ready"
        )
        self.state = SMTPState.GREETED

        while self.state != SMTPState.CLOSED:
            try:
                line = recv_line(self.conn)
            except (ConnectionResetError, EOFError, socket.timeout):
                break
            except ValueError:
                send_reply(self.conn, 500, "Line too long")
                continue

            if not self._dispatch(line):
                break

    def _dispatch(self, line: str) -> bool:
        """Parse one command line and dispatch to the appropriate command handler."""
        raw = line.strip()
        if not raw:
            send_reply(self.conn, 500, "Syntax error, empty command")
            return True

        parts = raw.split(" ", 1)
        cmd = parts[0].upper()
        arg = parts[1] if len(parts) > 1 else ""

        if cmd in ("HELO", "EHLO"):
            self._cmd_helo(arg)
        elif raw.upper().startswith("MAIL FROM:"):
            self._cmd_mail_from(raw[10:].strip())
        elif raw.upper().startswith("RCPT TO:"):
            self._cmd_rcpt_to(raw[8:].strip())
        elif cmd == "DATA":
            self._cmd_data(arg)
        elif cmd == "RSET":
            self._cmd_rset(arg)
        elif cmd == "NOOP":
            self._cmd_noop(arg)
        elif cmd == "VRFY":
            self._cmd_vrfy(arg)
        elif cmd == "QUIT":
            self._cmd_quit(arg)
            return False
        else:
            send_reply(self.conn, 500, f"Syntax error, command unrecognized: {cmd}")

        return self.state != SMTPState.CLOSED

    def _cmd_helo(self, arg: str) -> None:
        """Handle HELO/EHLO greeting command."""
        if self.state not in (SMTPState.GREETED, SMTPState.IDENTIFIED):
            send_reply(self.conn, 503, "Bad sequence of commands")
            return
        domain = arg.strip()
        if not domain:
            send_reply(self.conn, 501, "Syntax error in parameters or arguments")
            return
        self.client_domain = domain
        self.state = SMTPState.IDENTIFIED
        local_domain = getattr(settings, "local_domain", "localhost")
        send_reply(self.conn, 250, f"{local_domain} Hello {self.client_domain}")

    def _clean_address(self, arg: str) -> str:
        """Strip angle brackets and whitespace from email address."""
        val = arg.strip()
        if val.startswith("<") and val.endswith(">"):
            val = val[1:-1].strip()
        return val

    def _cmd_mail_from(self, arg: str) -> None:
        """Handle MAIL FROM:<address> command."""
        if self.state not in (SMTPState.IDENTIFIED, SMTPState.GREETED):
            if self.state in (SMTPState.MAIL, SMTPState.RCPT):
                send_reply(self.conn, 503, "Sender already specified")
            else:
                send_reply(self.conn, 503, "Bad sequence of commands")
            return

        addr = self._clean_address(arg)
        if not addr:
            send_reply(self.conn, 501, "Syntax error in sender address")
            return

        self.mail_from = addr
        self.rcpt_to.clear()
        self.state = SMTPState.MAIL
        send_reply(self.conn, 250, "2.1.0 Sender OK")

    def _cmd_rcpt_to(self, arg: str) -> None:
        """Handle RCPT TO:<address> command with local user verification."""
        if self.state not in (SMTPState.MAIL, SMTPState.RCPT):
            send_reply(self.conn, 503, "Bad sequence of commands (send MAIL first)")
            return

        addr = self._clean_address(arg)
        if not addr or "@" not in addr:
            send_reply(self.conn, 501, "Syntax error in recipient address")
            return

        user, _, domain = addr.partition("@")
        local_domain = getattr(settings, "local_domain", "localhost")

        if domain.lower() == local_domain.lower():
            if not user_exists(user):
                send_reply(
                    self.conn,
                    550,
                    f"5.1.1 <{addr}>: User unknown in local recipient table",
                )
                return

        self.rcpt_to.append(addr)
        self.state = SMTPState.RCPT
        send_reply(self.conn, 250, "2.1.5 Recipient OK")

    def _read_data_payload(self) -> tuple[bytes, bool]:
        """Read data lines until lone dot; unstuff leading dots and check size."""
        max_size = getattr(settings, "max_message_size", 10 * 1024 * 1024)
        lines: list[str] = []
        total_size = 0
        oversized = False

        while True:
            line = recv_line(self.conn, max_len=4096)
            if line == ".":
                break
            if line.startswith("."):
                line = line[1:]
            encoded_line = line + "\r\n"
            total_size += len(encoded_line.encode("utf-8"))
            if total_size > max_size:
                oversized = True
            if not oversized:
                lines.append(encoded_line)

        raw_bytes = "".join(lines).encode("utf-8")
        return raw_bytes, oversized

    def _cmd_data(self, arg: str) -> None:
        """Handle DATA command, collect body lines, deliver, and acknowledge."""
        if self.state != SMTPState.RCPT:
            send_reply(self.conn, 503, "Bad sequence of commands (need RCPT first)")
            return

        send_reply(self.conn, 354, "Start mail input; end with <CRLF>.<CRLF>")
        try:
            raw_bytes, oversized = self._read_data_payload()
        except Exception:
            self.state = SMTPState.CLOSED
            return

        if oversized:
            send_reply(self.conn, 552, "Message size exceeds fixed maximum")
            self._reset()
            return

        self._deliver_or_relay(raw_bytes)
        send_reply(self.conn, 250, "2.0.0 OK: message queued")
        self._reset()

    def _deliver_or_relay(self, raw_bytes: bytes) -> None:
        """Route message to local user mailbox or external relay."""
        local_domain = getattr(settings, "local_domain", "localhost")
        for recipient in self.rcpt_to:
            user, _, domain = recipient.partition("@")
            if domain.lower() == local_domain.lower():
                try:
                    deliver(user, raw_bytes, spam=False)
                    self.logger.info("Delivered mail to local user '%s'", user)
                except Exception as e:
                    self.logger.exception("Failed delivering to '%s': %s", user, e)
            else:
                self.logger.info("External relay recipient queued: %s", recipient)

    def _reset(self) -> None:
        """Reset transaction state back to IDENTIFIED."""
        self.mail_from = None
        self.rcpt_to.clear()
        self.data_buffer.clear()
        self.state = SMTPState.IDENTIFIED

    def _cmd_rset(self, arg: str) -> None:
        """Handle RSET command."""
        self._reset()
        send_reply(self.conn, 250, "2.0.0 Reset state OK")

    def _cmd_noop(self, arg: str) -> None:
        """Handle NOOP command."""
        send_reply(self.conn, 250, "2.0.0 OK")

    def _cmd_vrfy(self, arg: str) -> None:
        """Handle VRFY command."""
        addr = self._clean_address(arg)
        user = addr.split("@")[0] if "@" in addr else addr
        if user_exists(user):
            local_domain = getattr(settings, "local_domain", "localhost")
            send_reply(self.conn, 250, f"<{user}@{local_domain}>")
        else:
            send_reply(self.conn, 550, f"<{arg}>: User unknown")

    def _cmd_quit(self, arg: str) -> None:
        """Handle QUIT command."""
        local_domain = getattr(settings, "local_domain", "localhost")
        send_reply(
            self.conn, 221, f"{local_domain} closing transmission channel"
        )
        self.state = SMTPState.CLOSED

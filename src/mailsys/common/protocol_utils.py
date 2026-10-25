"""
mailsys.common.protocol_utils
==============================
Low-level socket helpers shared by both the SMTP and POP3 session modules.

Responsibilities:
  - Read one CRLF-terminated line from a socket (handles partial TCP reads).
  - Send RFC-formatted SMTP reply lines (code + space/dash + message + CRLF).
  - Send POP3 +OK and -ERR response lines.
  - Send a POP3 multi-line response body terminated by a lone dot.
"""
import socket


def recv_line(sock: socket.socket, max_len: int = 1024) -> str:
    """Read one CRLF-terminated line from *sock*.

    Args:
        sock:    A connected TCP socket.
        max_len: Maximum allowed line length in bytes (DoS guard).

    Returns:
        The decoded line string, **without** the trailing ``\\r\\n``.

    Raises:
        ConnectionResetError: If the remote end closes the connection.
        ValueError:           If the line exceeds *max_len* bytes.
    """
    buf = bytearray()
    while True:
        chunk = sock.recv(1)
        if not chunk:
            raise ConnectionResetError("Connection closed before CRLF was received.")
        buf.extend(chunk)
        if len(buf) > max_len:
            raise ValueError(f"Line length exceeds maximum limit of {max_len} bytes.")
        if buf.endswith(b"\r\n"):
            return buf[:-2].decode("utf-8", errors="replace")


def send_reply(
    sock: socket.socket, code: int, message: str, last: bool = True
) -> None:
    """Send an SMTP reply line: ``<code><sep><message>\\r\\n``.

    Args:
        sock:    A connected TCP socket.
        code:    3-digit SMTP reply code (e.g. 250, 354, 550).
        message: Human-readable reply text.
        last:    If True, sep is a space (final/only reply line).
                 If False, sep is ``-`` (multi-line continuation).
    """
    sep = " " if last else "-"
    payload = f"{code}{sep}{message}\r\n".encode("utf-8")
    sock.sendall(payload)


def send_pop3_ok(sock: socket.socket, message: str = "") -> None:
    """Send a POP3 ``+OK [message]\\r\\n`` response."""
    text = f"+OK {message}".strip() + "\r\n"
    sock.sendall(text.encode("utf-8"))


def send_pop3_err(sock: socket.socket, message: str = "") -> None:
    """Send a POP3 ``-ERR [message]\\r\\n`` response."""
    text = f"-ERR {message}".strip() + "\r\n"
    sock.sendall(text.encode("utf-8"))


def send_multiline(sock: socket.socket, lines: list[str]) -> None:
    """Send a POP3 multi-line response body terminated by a lone dot.

    Each string in *lines* is sent as ``<line>\\r\\n``.
    A terminating ``b".\\r\\n"`` is appended at the end.
    """
    parts: list[bytes] = []
    for line in lines:
        if line.startswith("."):
            line = "." + line  # POP3 byte stuffing
        parts.append(f"{line}\r\n".encode("utf-8"))
    parts.append(b".\r\n")
    sock.sendall(b"".join(parts))

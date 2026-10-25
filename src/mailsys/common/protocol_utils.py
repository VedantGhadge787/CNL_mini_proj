"""
mailsys.common.protocol_utils
==============================
Low-level socket helpers shared by both the SMTP and POP3 session modules.

Responsibilities:
  - Read one CRLF-terminated line from a socket (handles partial TCP reads).
  - Send RFC-formatted SMTP reply lines (code + space/dash + message + CRLF).
  - Send POP3 +OK and -ERR response lines.
  - Send a POP3 multi-line response body terminated by a lone dot.

All functions operate on ``socket.socket`` objects directly.  No state is kept.

Imports needed:
    import socket
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

    TODO:
        - Read one byte at a time into a buffer.
        - Stop when buffer ends with b"\\r\\n".
        - Decode as UTF-8 with errors="replace".
    """
    # TODO: Implement
    raise NotImplementedError


def send_reply(sock: socket.socket, code: int, message: str, last: bool = True) -> None:
    """Send an SMTP reply line: ``<code><sep><message>\\r\\n``.

    Args:
        sock:    A connected TCP socket.
        code:    3-digit SMTP reply code (e.g. 250, 354, 550).
        message: Human-readable reply text.
        last:    If True, sep is a space (final/only reply line).
                 If False, sep is ``-`` (multi-line continuation).

    TODO:
        - Format as f"{code}{' ' if last else '-'}{message}\\r\\n".encode()
        - Call sock.sendall(...)
    """
    # TODO: Implement
    raise NotImplementedError


def send_pop3_ok(sock: socket.socket, message: str = "") -> None:
    """Send a POP3 ``+OK [message]\\r\\n`` response.

    TODO:
        - Format as b"+OK " + message.encode() + b"\\r\\n" (or just b"+OK\\r\\n")
    """
    # TODO: Implement
    raise NotImplementedError


def send_pop3_err(sock: socket.socket, message: str = "") -> None:
    """Send a POP3 ``-ERR [message]\\r\\n`` response.

    TODO:
        - Format as b"-ERR " + message.encode() + b"\\r\\n"
    """
    # TODO: Implement
    raise NotImplementedError


def send_multiline(sock: socket.socket, lines: list[str]) -> None:
    """Send a POP3 multi-line response body terminated by a lone dot.

    Each string in *lines* is sent as ``<line>\\r\\n``.
    A terminating ``b".\\r\\n"`` is appended at the end.

    TODO:
        - Iterate lines, encode and sendall each.
        - Dot-stuff any line starting with '.'.
        - Send b".\\r\\n" as terminator.
    """
    # TODO: Implement
    raise NotImplementedError

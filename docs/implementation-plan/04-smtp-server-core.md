# Step 04 — SMTP Server Core

**Status:** [ ] not started

---

## 1. Objective

When this step is done:
- `smtp/server.py` binds port 2525 and spawns a thread per connection.
- `smtp/session.py` implements the full SMTP state machine (all mandatory commands, dot-stuffing, size limit enforcement, local recipient validation, spam-filter hook, delivery/relay routing).
- `common/protocol_utils.py` provides CRLF line reading and reply sending helpers.
- A telnet or netcat session to port 2525 can exchange a complete SMTP dialog and deliver mail to a local mailbox.

---

## 2. Prerequisites

- Step 02 done: `settings`, `get_logger`.
- Step 03 done: `user_manager`, `mailbox`.
- Step 05 (MIME) and Step 06 (Spam) are **not** required yet — call stubs or pass-through functions. Full integration happens in Step 06.

---

## 3. Files to Create or Modify

| Action | Path |
|--------|------|
| Implement | `src/mailsys/common/protocol_utils.py` |
| Implement | `src/mailsys/smtp/server.py` |
| Implement | `src/mailsys/smtp/session.py` |
| Implement | `scripts/run_smtp.py` |
| Update tests | `tests/test_smtp_session.py` |

---

## 4. Detailed Implementation Instructions

### 4.1 `protocol_utils.py`

```python
def recv_line(sock: socket.socket, max_len: int = 1024) -> str:
    """Read one CRLF-terminated line from the socket.

    Returns the line without the trailing CRLF.
    Raises ConnectionResetError if the socket closes before a full line.
    Raises ValueError if max_len is exceeded (potential DoS protection).
    """

def send_reply(sock: socket.socket, code: int, message: str, last: bool = True) -> None:
    """Send an SMTP reply line: "<code><sep><message>\r\n".

    If last is True (default), sep is a space ' ' (final reply line).
    If last is False, sep is '-' (multi-line continuation).
    """

def send_pop3_ok(sock: socket.socket, message: str = "") -> None:
    """Send a POP3 +OK response."""

def send_pop3_err(sock: socket.socket, message: str = "") -> None:
    """Send a POP3 -ERR response."""

def send_multiline(sock: socket.socket, lines: list[str]) -> None:
    """Send a POP3 multi-line response body terminated by a lone dot."""
```

**Implementation note:** Use `sock.makefile("rb")` for line-based reading — it handles partial TCP reads correctly:
```python
def recv_line(sock: socket.socket, max_len: int = 1024) -> str:
    buf = b""
    while True:
        ch = sock.recv(1)
        if not ch:
            raise ConnectionResetError("socket closed")
        buf += ch
        if len(buf) > max_len:
            raise ValueError(f"line too long: {len(buf)} bytes")
        if buf.endswith(b"\r\n"):
            return buf[:-2].decode("utf-8", errors="replace")
```

### 4.2 `smtp/server.py`

```python
class SMTPServer:
    """Listens for incoming SMTP connections and spawns a session thread per client."""

    def __init__(self, host: str = settings.smtp_host, port: int = settings.smtp_port) -> None: ...

    def start(self) -> None:
        """Bind socket and enter accept loop (blocking). Call in its own thread."""

    def stop(self) -> None:
        """Signal the accept loop to stop (sets a flag and closes the server socket)."""

    def _handle_client(self, conn: socket.socket, addr: tuple[str, int]) -> None:
        """Target function for per-client threads. Instantiates SMTPSession and calls handle()."""
```

**Accept loop pattern:**
```python
server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server_sock.bind((host, port))
server_sock.listen(5)
while self._running:
    try:
        conn, addr = server_sock.accept()
        conn.settimeout(settings.socket_timeout)
        t = threading.Thread(target=self._handle_client, args=(conn, addr), daemon=True)
        t.start()
    except OSError:
        break  # server_sock was closed by stop()
```

### 4.3 `smtp/session.py` — State machine

#### States (use an `enum.Enum`)

```python
class SMTPState(enum.Enum):
    CONNECTED = "CONNECTED"
    GREETED   = "GREETED"
    IDENTIFIED = "IDENTIFIED"
    MAIL       = "MAIL"
    RCPT       = "RCPT"
    DATA       = "DATA"
    CLOSED     = "CLOSED"
```

#### Class skeleton

```python
class SMTPSession:
    def __init__(self, conn: socket.socket, addr: tuple[str, int]) -> None:
        self.conn = conn
        self.addr = addr
        self.state = SMTPState.CONNECTED
        self.mail_from: str | None = None
        self.rcpt_to: list[str] = []
        self.data_buffer: bytearray = bytearray()
        self.logger = get_logger(__name__)

    def handle(self) -> None:
        """Main session loop: send greeting, then read and dispatch commands."""

    def _dispatch(self, line: str) -> bool:
        """Parse one command line and call the appropriate handler.
        Returns False when the session should close."""

    def _cmd_helo(self, arg: str) -> None: ...
    def _cmd_ehlo(self, arg: str) -> None: ...
    def _cmd_mail_from(self, arg: str) -> None: ...
    def _cmd_rcpt_to(self, arg: str) -> None: ...
    def _cmd_data(self, arg: str) -> None: ...
    def _cmd_rset(self, arg: str) -> None: ...
    def _cmd_noop(self, arg: str) -> None: ...
    def _cmd_quit(self, arg: str) -> None: ...
    def _cmd_vrfy(self, arg: str) -> None: ...

    def _collect_data(self) -> bytes:
        """Read DATA lines until bare '.' terminator.
        Apply dot-unstuffing (RFC 5321 §4.5.2): if a line starts with '.',
        strip the leading dot before appending.
        Enforce max_message_size limit."""

    def _deliver_or_relay(self) -> None:
        """For each recipient, decide local vs external and route accordingly."""

    def _reset(self) -> None:
        """Clear mail_from, rcpt_to, data_buffer; set state to IDENTIFIED."""
```

#### State transition enforcement

Before executing a command, validate the current state:

| Command | Valid states | Error if not |
|---------|-------------|-------------|
| HELO/EHLO | GREETED, IDENTIFIED | 503 |
| MAIL FROM | IDENTIFIED | 503 |
| RCPT TO | MAIL, RCPT | 503 |
| DATA | RCPT | 503 |
| RSET | IDENTIFIED, MAIL, RCPT, DATA | — (always 250) |
| NOOP | any | — |
| QUIT | any | — |

#### Dot-unstuffing in `_collect_data`

```python
# RFC 5321 §4.5.2: transparency
for line in lines:
    if line == ".":      # bare dot = end of message
        break
    if line.startswith("."):
        line = line[1:]  # strip leading dot
    data_buffer += (line + "\r\n").encode()
```

#### Local vs external routing in `_deliver_or_relay`

```python
local_domain = settings.local_domain
for recipient in self.rcpt_to:
    _, _, domain = recipient.partition("@")
    if domain == local_domain:
        # local delivery
        local_user = recipient.split("@")[0]
        if not user_exists(local_user):
            # This was already rejected at RCPT TO, but double-check
            logger.error("delivery error: unknown user %s", local_user)
            continue
        score, is_spam = spam_filter.score_message(raw_bytes)  # stub for now
        mailbox.deliver(local_user, raw_bytes, spam=is_spam)
    else:
        relay.relay_message(recipient, raw_bytes)  # stub for now
```

#### Reply for unknown recipient at RCPT TO

```
550 5.1.1 <user@localhost>: User unknown in local recipient table
```

### 4.4 `scripts/run_smtp.py`

```python
#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from mailsys.smtp.server import SMTPServer

if __name__ == "__main__":
    server = SMTPServer()
    print(f"SMTP server starting on {server.host}:{server.port} ...")
    server.start()
```

---

## 5. Acceptance Criteria

- [ ] `python scripts/run_smtp.py` starts without error and prints the bind address.
- [ ] Telnet to port 2525 shows `220 <domain> SMTP ready`.
- [ ] `HELO test` returns `250 OK`.
- [ ] `MAIL FROM:<alice@localhost>` returns `250 OK`.
- [ ] `RCPT TO:<nobody@localhost>` (unknown user) returns `550 ...`.
- [ ] `RCPT TO:<bob@localhost>` (known user) returns `250 OK`.
- [ ] `DATA` returns `354 ...`.
- [ ] Sending message lines and `.` delivers a `.eml` file in `data/mailboxes/bob/new/`.
- [ ] A message > 10 MB is rejected with `552`.
- [ ] `QUIT` returns `221 Bye`.
- [ ] `pytest tests/test_smtp_session.py -v` passes.

---

## 6. How to Test

### Manual telnet test

```
telnet localhost 2525
EHLO testclient
MAIL FROM:<sender@test.com>
RCPT TO:<bob@localhost>
DATA
Subject: Test message
From: sender@test.com
To: bob@localhost

This is the body.
.
QUIT
```

Expected reply sequence: 220 → 250 → 250 → 250 → 354 → 250 → 221.

### pytest

```powershell
python -m pytest tests/test_smtp_session.py -v
```

---

## 7. Wireshark Check

- **Filter:** `tcp.port == 2525`
- **Observe:**
  - Three-way handshake (SYN, SYN-ACK, ACK).
  - 220 greeting from server on connect.
  - Each SMTP command and reply exchange as a separate TCP segment (or small group).
  - DATA phase: multiple segments containing message lines.
  - Bare `.` terminator followed by 250 reply.
  - FIN/RST on QUIT.

---

## 8. Log Update

Append to `docs/log.md`:
```
### [YYYY-MM-DD HH:MM] Step 04: SMTP Server Core
- Changed: protocol_utils.py (real), smtp/server.py (real), smtp/session.py (real), run_smtp.py (real)
- Why: Core feature; enables local mail delivery
- Key decisions: State machine via SMTPState enum; dot-unstuffing per RFC 5321
- Interfaces added: SMTPServer.start/stop, SMTPSession.handle, recv_line, send_reply
- Tests: test_smtp_session.py pass; manual telnet verified
- Next: Step 05 — MIME and attachments
```

---

## 9. Definition of Done

Telnet dialog completes successfully, `.eml` file appears in mailbox, all acceptance criteria checked, tests pass.

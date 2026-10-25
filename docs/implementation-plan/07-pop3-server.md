# Step 07 — POP3 Server

**Status:** [ ] not started

---

## 1. Objective

When this step is done:
- `pop3/server.py` binds port 2110 and spawns a session thread per connection.
- `pop3/session.py` implements the full POP3 state machine (AUTHORIZATION → TRANSACTION → UPDATE).
- Messages are only deleted when the session ends with a successful `QUIT` (UPDATE state).
- No two simultaneous POP3 sessions can open the same mailbox.

---

## 2. Prerequisites

- Step 03 done: `user_manager`, `mailbox` (including per-user locking).
- Step 04 done: `protocol_utils` (send_pop3_ok, send_pop3_err, send_multiline).

---

## 3. Files to Create or Modify

| Action | Path |
|--------|------|
| Implement | `src/mailsys/pop3/server.py` |
| Implement | `src/mailsys/pop3/session.py` |
| Implement | `scripts/run_pop3.py` |
| Update tests | `tests/test_pop3_session.py` |

---

## 4. Detailed Implementation Instructions

### 4.1 `pop3/server.py`

Mirror the SMTP server structure exactly:

```python
class POP3Server:
    def __init__(self, host: str = settings.pop3_host, port: int = settings.pop3_port) -> None: ...
    def start(self) -> None: ...
    def stop(self) -> None: ...
    def _handle_client(self, conn: socket.socket, addr: tuple[str, int]) -> None: ...
```

### 4.2 `pop3/session.py` — State machine

#### States

```python
class POP3State(enum.Enum):
    AUTHORIZATION = "AUTHORIZATION"
    TRANSACTION   = "TRANSACTION"
    UPDATE        = "UPDATE"
    CLOSED        = "CLOSED"
```

#### Session attributes

```python
class POP3Session:
    def __init__(self, conn: socket.socket, addr: tuple[str, int]) -> None:
        self.conn = conn
        self.addr = addr
        self.state = POP3State.AUTHORIZATION
        self.username: str | None = None
        self.messages: list[tuple[int, Path, int]] = []  # (index, path, size)
        self.deleted: set[int] = set()  # 1-based indices marked for deletion
        self.logger = get_logger(__name__)
```

#### Command dispatch table

```python
_COMMANDS = {
    "USER": self._cmd_user,
    "PASS": self._cmd_pass,
    "STAT": self._cmd_stat,
    "LIST": self._cmd_list,
    "RETR": self._cmd_retr,
    "DELE": self._cmd_dele,
    "NOOP": self._cmd_noop,
    "RSET": self._cmd_rset,
    "UIDL": self._cmd_uidl,
    "TOP":  self._cmd_top,
    "QUIT": self._cmd_quit,
}
```

#### State rules per command

| Command | Required State | Error if not |
|---------|---------------|-------------|
| USER | AUTHORIZATION | -ERR wrong state |
| PASS | AUTHORIZATION (after USER set) | -ERR send USER first |
| STAT | TRANSACTION | -ERR not authenticated |
| LIST | TRANSACTION | -ERR |
| RETR | TRANSACTION | -ERR |
| DELE | TRANSACTION | -ERR |
| NOOP | TRANSACTION | -ERR |
| RSET | TRANSACTION | -ERR |
| UIDL | TRANSACTION | -ERR |
| TOP | TRANSACTION | -ERR |
| QUIT | any | +OK (may or may not enter UPDATE) |

#### `_cmd_pass` — authentication and mailbox locking

```python
def _cmd_pass(self, arg: str) -> None:
    if self.username is None:
        send_pop3_err(self.conn, "send USER first")
        return
    if not verify_password(self.username, arg):
        send_pop3_err(self.conn, "invalid credentials")
        self.username = None  # reset so USER can be tried again
        return
    # Try to acquire the mailbox lock
    lock = _get_lock(self.username)
    if not lock.acquire(blocking=False):
        send_pop3_err(self.conn, "[IN-USE] mailbox already locked")
        self.state = POP3State.CLOSED
        return
    self._mailbox_lock = lock
    # Load message list into session memory
    self.messages = list_messages(self.username)
    self.state = POP3State.TRANSACTION
    send_pop3_ok(self.conn, f"logged in, {len(self.messages)} messages")
```

#### `_cmd_stat`

```python
def _cmd_stat(self, arg: str) -> None:
    active = [(i, p, s) for i, p, s in self.messages if i not in self.deleted]
    total_bytes = sum(s for _, _, s in active)
    send_pop3_ok(self.conn, f"{len(active)} {total_bytes}")
```

#### `_cmd_list`

```python
def _cmd_list(self, arg: str) -> None:
    if arg:
        idx = int(arg)
        if idx < 1 or idx > len(self.messages) or idx in self.deleted:
            send_pop3_err(self.conn, f"no such message, {idx}")
            return
        _, _, size = self.messages[idx - 1]
        send_pop3_ok(self.conn, f"{idx} {size}")
    else:
        active = [(i, p, s) for i, p, s in self.messages if i not in self.deleted]
        send_pop3_ok(self.conn, f"{len(active)} messages")
        for i, _, s in active:
            self.conn.sendall(f"{i} {s}\r\n".encode())
        self.conn.sendall(b".\r\n")
```

#### `_cmd_retr`

```python
def _cmd_retr(self, arg: str) -> None:
    idx = int(arg)
    if idx < 1 or idx > len(self.messages) or idx in self.deleted:
        send_pop3_err(self.conn, "no such message")
        return
    raw = read_message(self.username, idx)
    send_pop3_ok(self.conn, f"{len(raw)} octets")
    # Send message with dot-stuffing, terminated by CRLF.CRLF
    for line in raw.split(b"\n"):
        line = line.rstrip(b"\r")
        if line.startswith(b"."):
            line = b"." + line  # dot-stuffing
        self.conn.sendall(line + b"\r\n")
    self.conn.sendall(b".\r\n")
```

#### `_cmd_dele`

```python
def _cmd_dele(self, arg: str) -> None:
    idx = int(arg)
    if idx < 1 or idx > len(self.messages) or idx in self.deleted:
        send_pop3_err(self.conn, "no such message")
        return
    self.deleted.add(idx)
    send_pop3_ok(self.conn, f"message {idx} deleted")
```

#### `_cmd_rset` — clear deletion marks

```python
def _cmd_rset(self, arg: str) -> None:
    self.deleted.clear()
    send_pop3_ok(self.conn, f"maildrop has {len(self.messages)} messages")
```

#### `_cmd_quit` — enter UPDATE state

```python
def _cmd_quit(self, arg: str) -> None:
    if self.state == POP3State.TRANSACTION:
        self.state = POP3State.UPDATE
        # Purge deleted messages (in reverse order to keep indices valid)
        for idx in sorted(self.deleted, reverse=True):
            delete_message(self.username, idx)
        if hasattr(self, "_mailbox_lock"):
            self._mailbox_lock.release()
    send_pop3_ok(self.conn, "bye")
    self.state = POP3State.CLOSED
```

#### `_cmd_uidl`

```python
def _cmd_uidl(self, arg: str) -> None:
    if arg:
        idx = int(arg)
        if idx < 1 or idx > len(self.messages) or idx in self.deleted:
            send_pop3_err(self.conn, "no such message")
            return
        _, path, _ = self.messages[idx - 1]
        send_pop3_ok(self.conn, f"{idx} {generate_uid(path)}")
    else:
        active = [(i, p, s) for i, p, s in self.messages if i not in self.deleted]
        send_pop3_ok(self.conn, "unique-id listing")
        for i, p, _ in active:
            self.conn.sendall(f"{i} {generate_uid(p)}\r\n".encode())
        self.conn.sendall(b".\r\n")
```

#### `_cmd_top`

```python
def _cmd_top(self, arg: str) -> None:
    parts = arg.split()
    if len(parts) != 2:
        send_pop3_err(self.conn, "syntax: TOP msg n")
        return
    idx, n = int(parts[0]), int(parts[1])
    if idx < 1 or idx > len(self.messages) or idx in self.deleted:
        send_pop3_err(self.conn, "no such message")
        return
    raw = read_message(self.username, idx)
    # Parse headers and up to n body lines
    header_end = raw.find(b"\r\n\r\n")
    headers = raw[:header_end + 4]
    body = raw[header_end + 4:]
    body_lines = body.split(b"\n")[:n]
    send_pop3_ok(self.conn)
    for line in headers.split(b"\n"):
        self.conn.sendall(line.rstrip(b"\r") + b"\r\n")
    for line in body_lines:
        self.conn.sendall(line.rstrip(b"\r") + b"\r\n")
    self.conn.sendall(b".\r\n")
```

### 4.3 `scripts/run_pop3.py`

```python
#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from mailsys.pop3.server import POP3Server

if __name__ == "__main__":
    server = POP3Server()
    print(f"POP3 server starting on {server.host}:{server.port} ...")
    server.start()
```

---

## 5. Acceptance Criteria

- [ ] `python scripts/run_pop3.py` starts without error.
- [ ] Telnet to port 2110 shows `+OK POP3 server ready`.
- [ ] `USER alice` → `+OK alice`.
- [ ] `PASS wrong` → `-ERR invalid credentials`.
- [ ] `PASS secret` → `+OK logged in`.
- [ ] `STAT` → `+OK N <bytes>`.
- [ ] `LIST` → multi-line listing terminated by `.`.
- [ ] `RETR 1` → `+OK ... octets` followed by message and `.`.
- [ ] `DELE 1` → `+OK message 1 deleted`.
- [ ] `RSET` → `+OK` and deletion mark cleared.
- [ ] `QUIT` → message deleted from disk (UPDATE state executed).
- [ ] Second simultaneous POP3 session for same user → `-ERR [IN-USE]`.
- [ ] `UIDL` returns stable UIDs matching MD5 of filename.
- [ ] `pytest tests/test_pop3_session.py -v` passes.

---

## 6. How to Test

### Manual telnet test

```
telnet localhost 2110
USER alice
PASS secret
STAT
LIST
RETR 1
DELE 1
QUIT
```

Then verify message file is gone from `data/mailboxes/alice/new/`.

### pytest

```powershell
python -m pytest tests/test_pop3_session.py -v
```

---

## 7. Wireshark Check

- **Filter:** `tcp.port == 2110`
- **Observe:**
  - `+OK` greeting on connect.
  - USER/PASS challenge-response.
  - Multi-line LIST and RETR responses ending with `.\r\n`.
  - QUIT triggering FIN from server.

---

## 8. Log Update

Append to `docs/log.md`:
```
### [YYYY-MM-DD HH:MM] Step 07: POP3 Server
- Changed: pop3/server.py (real), pop3/session.py (real), run_pop3.py (real)
- Why: FR-8 to FR-10 — mail retrieval
- Key decisions: Mailbox lock held during entire TRANSACTION; DELETE purge only on QUIT
- Interfaces added: POP3Server.start/stop, POP3Session.handle
- Tests: test_pop3_session.py pass; manual telnet verified
- Next: Step 08 — MX lookup and relay
```

---

## 9. Definition of Done

Telnet session retrieves and deletes mail, concurrent session is rejected, UPDATE-only deletion confirmed, tests pass.

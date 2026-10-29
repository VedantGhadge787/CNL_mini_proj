# Step 10 — Testing & Validation

**Status:** [x] done

---

## 1. Objective

When this step is done:
- All pytest unit tests pass with `pytest tests/ -v`.
- A concurrency test confirms no deadlock or data corruption under 5 simultaneous clients.
- Manual telnet test transcripts have been run and documented.
- Wireshark capture confirms correct protocol frames for SMTP and POP3.

---

## 2. Prerequisites

- Steps 04–09 done: all feature modules implemented.

---

## 3. Files to Create or Modify

| Action | Path |
|--------|------|
| Implement | `tests/test_smtp_session.py` (flesh out stubs) |
| Implement | `tests/test_pop3_session.py` (flesh out stubs) |
| Implement | `tests/test_mailbox.py` (flesh out stubs) |
| Implement | `tests/test_spam_filter.py` (flesh out stubs) |
| Implement | `tests/test_mime.py` (flesh out stubs) |
| Implement | `tests/test_end_to_end.py` (flesh out stubs) |

---

## 4. Detailed Implementation Instructions

### 4.1 Test structure and fixtures

Use `pytest` fixtures in `tests/conftest.py`:

```python
# tests/conftest.py
import pytest, os, threading, time
from pathlib import Path

@pytest.fixture(autouse=True)
def isolated_data_dir(tmp_path, monkeypatch):
    """Each test gets its own data directory (no cross-test pollution)."""
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.setenv("SMTP_PORT", "0")   # ephemeral ports
    monkeypatch.setenv("POP3_PORT", "0")
    # Re-import settings with new env vars
    import importlib, mailsys.config.settings as s_mod
    importlib.reload(s_mod)
    yield tmp_path
```

### 4.2 `tests/test_mailbox.py`

```python
def test_deliver_creates_file(isolated_data_dir): ...
def test_list_messages_empty(): ...
def test_list_messages_after_deliver(): ...
def test_read_message_correct_bytes(): ...
def test_delete_message_removes_file(): ...
def test_delete_out_of_range_raises(): ...
def test_generate_uid_stable(): ...
def test_concurrent_deliver_no_corruption(): ...  # 10 threads deliver simultaneously
```

**Concurrency test pattern:**
```python
def test_concurrent_deliver_no_corruption(isolated_data_dir):
    from mailsys.auth.user_manager import create_user
    from mailsys.storage.mailbox import deliver, list_messages, ensure_mailbox
    create_user("ctest", "pass")
    ensure_mailbox("ctest")
    n = 10
    errors = []
    def deliver_one(i):
        try:
            deliver("ctest", f"Subject: msg {i}\r\n\r\nBody {i}".encode())
        except Exception as e:
            errors.append(e)
    threads = [threading.Thread(target=deliver_one, args=(i,)) for i in range(n)]
    for t in threads: t.start()
    for t in threads: t.join()
    assert not errors, f"Errors during concurrent deliver: {errors}"
    msgs = list_messages("ctest")
    assert len(msgs) == n
```

### 4.3 `tests/test_smtp_session.py`

Use a `socketpair` or a loopback TCP socket to feed commands to `SMTPSession`:

```python
import socket, threading
from mailsys.smtp.session import SMTPSession

def _make_session_pair():
    """Return (client_sock, session) where session runs in a daemon thread."""
    client, server = socket.socketpair()
    session = SMTPSession(server, ("test", 0))
    t = threading.Thread(target=session.handle, daemon=True)
    t.start()
    return client, t

def test_greeting():
    client, _ = _make_session_pair()
    banner = client.recv(1024)
    assert banner.startswith(b"220")

def test_helo():
    client, _ = _make_session_pair()
    client.recv(1024)  # banner
    client.sendall(b"HELO test\r\n")
    assert client.recv(1024).startswith(b"250")

def test_rcpt_unknown_user():
    # ... exercise full HELO/MAIL FROM/RCPT TO with nonexistent user
    # expect 550

def test_full_delivery():
    # HELO → MAIL FROM → RCPT TO → DATA → body → . → QUIT
    # verify .eml file created

def test_data_dot_stuffing():
    # Send a message with a line starting with '.'
    # Verify stored message has the dot removed

def test_oversized_message():
    # Stream > MAX_MESSAGE_SIZE bytes in DATA
    # Expect 552

def test_bad_sequence():
    # DATA before RCPT TO → 503

def test_quit():
    client, _ = _make_session_pair()
    client.recv(1024)
    client.sendall(b"QUIT\r\n")
    assert client.recv(1024).startswith(b"221")
```

### 4.4 `tests/test_pop3_session.py`

Same socket-pair pattern as SMTP:

```python
def test_greeting(): ...
def test_auth_success(): ...
def test_auth_wrong_password(): ...
def test_stat_empty_mailbox(): ...
def test_stat_with_messages(): ...
def test_list(): ...
def test_retr(): ...
def test_dele_and_quit_deletes(): ...
def test_rset_clears_deletion(): ...
def test_uidl(): ...
def test_top(): ...
def test_concurrent_session_locked(): ...
```

### 4.5 `tests/test_end_to_end.py`

Start SMTP and POP3 servers on ephemeral ports; use `smtplib` and `poplib` as clients:

```python
@pytest.fixture
def running_servers(isolated_data_dir):
    from mailsys.smtp.server import SMTPServer
    from mailsys.pop3.server import POP3Server
    smtp_server = SMTPServer(host="127.0.0.1", port=0)
    pop3_server = POP3Server(host="127.0.0.1", port=0)
    # start in threads, get actual bound ports
    ...
    yield smtp_port, pop3_port
    smtp_server.stop()
    pop3_server.stop()

def test_send_and_retrieve(running_servers, isolated_data_dir):
    smtp_port, pop3_port = running_servers
    # Create users
    create_user("sender", "pass1"); ensure_mailbox("sender")
    create_user("recipient", "pass2"); ensure_mailbox("recipient")
    # Send via smtplib
    import smtplib
    with smtplib.SMTP("127.0.0.1", smtp_port) as smtp:
        smtp.sendmail("sender@localhost", ["recipient@localhost"],
                      b"Subject: E2E test\r\n\r\nHello!")
    # Retrieve via poplib
    import poplib
    pop = poplib.POP3("127.0.0.1", pop3_port)
    pop.user("recipient"); pop.pass_("pass2")
    count, _ = pop.stat()
    assert count == 1
    raw = b"\r\n".join(pop.retr(1)[1])
    assert b"Hello!" in raw
    pop.quit()
```

---

## 5. Acceptance Criteria

- [ ] `pytest tests/ -v` exits with code 0 (all tests pass).
- [ ] `test_concurrent_deliver_no_corruption` passes with 10 threads.
- [ ] `test_concurrent_session_locked` confirms second POP3 session is rejected with -ERR.
- [ ] `test_send_and_retrieve` (end-to-end) passes.
- [ ] Manual telnet SMTP dialog completed successfully (screenshot or transcript logged).
- [ ] Manual telnet POP3 dialog completed successfully.
- [ ] Wireshark capture shows correct SMTP and POP3 protocol frames.

---

## 6. How to Test

```powershell
# Full test suite
python -m pytest tests/ -v

# With coverage (optional)
pip install pytest-cov
python -m pytest tests/ -v --cov=mailsys --cov-report=term-missing
```

---

## 7. Wireshark Check

- **SMTP filter:** `tcp.port == 2525` — observe DATA transfer with dot-stuffed body.
- **POP3 filter:** `tcp.port == 2110` — observe multi-line RETR response.
- **End-to-end filter:** `tcp.port == 2525 or tcp.port == 2110` — observe full workflow in one capture.

---

## 8. Log Update

Append to `docs/log.md`:
```
### [YYYY-MM-DD HH:MM] Step 10: Testing & Validation
- Changed: all test files fleshed out, conftest.py added
- Why: NFR-7 — every module must have tests; validate concurrency
- Key decisions: socketpair for unit testing sessions; ephemeral ports for E2E
- Interfaces added: conftest fixtures
- Tests: all pass; concurrency test passes; E2E passes
- Next: Step 11 — demo and report
```

---

## 9. Definition of Done

`pytest tests/ -v` exits 0, concurrency confirmed, Wireshark shows correct frames.

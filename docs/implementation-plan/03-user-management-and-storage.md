# Step 03 — User Management & Storage

**Status:** [ ] not started

---

## 1. Objective

When this step is done:
- `auth/user_manager.py` can create users (with salted password hashes), verify passwords, and check existence against a SQLite database.
- `storage/mailbox.py` can deliver, list, read, delete messages, and generate stable UIDs for POP3 — all with thread-safe per-user locking.
- `scripts/create_user.py` is functional as a CLI tool.

---

## 2. Prerequisites

- Step 02 done: `settings` and `get_logger` available.

---

## 3. Files to Create or Modify

| Action | Path |
|--------|------|
| Implement | `src/mailsys/auth/user_manager.py` |
| Implement | `src/mailsys/storage/mailbox.py` |
| Implement | `scripts/create_user.py` |
| Update tests | `tests/test_mailbox.py` |

---

## 4. Detailed Implementation Instructions

### 4.1 `user_manager.py`

#### SQLite schema

```sql
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT    NOT NULL UNIQUE,
    salt          TEXT    NOT NULL,
    password_hash TEXT    NOT NULL,
    created_at    DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

#### Function signatures

```python
def _get_connection() -> sqlite3.Connection:
    """Open (and initialise if needed) the SQLite DB at settings.db_path."""

def create_user(username: str, password: str) -> None:
    """Create a new user account with a salted hash of the password.

    Raises ValueError if username already exists.
    Uses hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 480_000).
    Salt is 32 random bytes, stored as hex string.
    """

def verify_password(username: str, password: str) -> bool:
    """Return True if the username exists and password is correct, False otherwise.

    Uses hmac.compare_digest to prevent timing attacks.
    """

def user_exists(username: str) -> bool:
    """Return True if a user with this username exists in the database."""
```

#### Implementation notes

- Use `settings.data_dir.mkdir(parents=True, exist_ok=True)` before first DB connection.
- Always use parameterised queries: `cursor.execute("SELECT ... WHERE username = ?", (username,))`.
- Use `hmac.compare_digest(expected_hash, computed_hash)` in `verify_password` — never `==`.
- `pbkdf2_hmac` call: `hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt), 480_000)`.

### 4.2 `mailbox.py`

#### Directory layout created per user

```
data/mailboxes/<username>/
    new/      <- delivered messages (unread)
    cur/      <- read messages
    Spam/
        new/
        cur/
```

#### Message filename format

```python
import time, os, socket, itertools

_counter = itertools.count()

def _make_filename() -> str:
    ts = time.time()
    pid = os.getpid()
    seq = next(_counter)
    host = socket.gethostname()
    return f"{ts:.6f}.{pid}.{seq}.{host}.eml"
```

#### Thread-safety locking

```python
import threading
_locks: dict[str, threading.Lock] = {}
_locks_meta = threading.Lock()

def _get_lock(username: str) -> threading.Lock:
    with _locks_meta:
        if username not in _locks:
            _locks[username] = threading.Lock()
        return _locks[username]
```

#### Function signatures

```python
def ensure_mailbox(username: str) -> Path:
    """Create the Maildir folder structure for a user if it does not exist.
    Returns the mailbox root Path."""

def deliver(username: str, raw_message: bytes, spam: bool = False) -> Path:
    """Deliver a raw .eml message to the user's new/ (or Spam/new/) folder.

    Thread-safe. Returns the Path of the stored file.
    Raises FileNotFoundError if the user's mailbox root does not exist
    (call ensure_mailbox first or call create_user which calls it).
    """

def list_messages(username: str) -> list[tuple[int, Path, int]]:
    """Return a list of (1-based-index, filepath, size_in_bytes) for all
    messages in new/ and cur/ (not Spam/) sorted by filename (oldest first).
    Thread-safe (acquires lock for the scan)."""

def read_message(username: str, index: int) -> bytes:
    """Return raw bytes of the message at the given 1-based index.
    Raises IndexError if index is out of range."""

def delete_message(username: str, index: int) -> None:
    """Permanently delete the message at the given 1-based index.
    Thread-safe. Raises IndexError if out of range."""

def generate_uid(filepath: Path) -> str:
    """Return a stable UID string for a message file.
    Computed as the MD5 hex digest of the filename (basename only)."""
```

#### Edge cases

- `list_messages` sorts by filename so that older messages always have lower indices. Indices are **not** stable across sessions if messages are delivered between sessions — POP3 clients must not assume stability (POP3 UIDL exists for this reason).
- `deliver` calls `ensure_mailbox` internally to handle the first-delivery case.
- All file writes use `file.write(raw_message)` in binary mode with `"wb"`.

### 4.3 `scripts/create_user.py`

```python
#!/usr/bin/env python3
"""CLI to create a new mail user.
Usage: python scripts/create_user.py <username> <password>
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from mailsys.auth.user_manager import create_user, user_exists
from mailsys.storage.mailbox import ensure_mailbox

def main() -> None:
    if len(sys.argv) != 3:
        print("Usage: create_user.py <username> <password>")
        sys.exit(1)
    username, password = sys.argv[1], sys.argv[2]
    if user_exists(username):
        print(f"Error: user '{username}' already exists.")
        sys.exit(1)
    create_user(username, password)
    ensure_mailbox(username)
    print(f"User '{username}' created successfully.")

if __name__ == "__main__":
    main()
```

---

## 5. Acceptance Criteria

- [ ] `python scripts/create_user.py alice secret` prints `User 'alice' created successfully.`
- [ ] Running it again prints `Error: user 'alice' already exists.`
- [ ] `user_exists("alice")` returns `True`.
- [ ] `verify_password("alice", "secret")` returns `True`.
- [ ] `verify_password("alice", "wrong")` returns `False`.
- [ ] `deliver("alice", b"From: test\r\n\r\nHello")` creates a `.eml` file in `data/mailboxes/alice/new/`.
- [ ] `list_messages("alice")` returns a list with 1 entry after delivery.
- [ ] `read_message("alice", 1)` returns the delivered bytes.
- [ ] `delete_message("alice", 1)` removes the file.
- [ ] `pytest tests/test_mailbox.py -v` passes.

---

## 6. How to Test

```powershell
# Create a user
python scripts/create_user.py testuser testpass

# Verify mailbox folders created
Get-ChildItem data\mailboxes\testuser -Recurse

# Python smoke test
python -c "
from mailsys.auth.user_manager import verify_password, user_exists
from mailsys.storage.mailbox import deliver, list_messages, read_message, delete_message
assert user_exists('testuser')
assert verify_password('testuser', 'testpass')
assert not verify_password('testuser', 'wrong')
path = deliver('testuser', b'Subject: Test\r\n\r\nHello world')
msgs = list_messages('testuser')
assert len(msgs) == 1
data = read_message('testuser', 1)
assert b'Hello world' in data
delete_message('testuser', 1)
assert list_messages('testuser') == []
print('All checks passed')
"

# pytest
python -m pytest tests/test_mailbox.py -v
```

---

## 7. Wireshark Check

Not applicable for this step.

---

## 8. Log Update

Append to `docs/log.md`:
```
### [YYYY-MM-DD HH:MM] Step 03: User Management & Storage
- Changed: user_manager.py (real), mailbox.py (real), create_user.py (real)
- Why: Foundation for all server components — SMTP and POP3 both need auth and mailbox
- Key decisions: pbkdf2_hmac 480k iterations; Maildir layout; per-user threading.Lock
- Interfaces added: create_user, verify_password, user_exists, deliver, list_messages,
  read_message, delete_message, generate_uid, ensure_mailbox
- Tests: test_mailbox.py all pass
- Next: Step 04 — SMTP server core
```

---

## 9. Definition of Done

`create_user.py` creates users, all mailbox operations work, thread-safety locking is in place, and tests pass.

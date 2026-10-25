# Step 09 — Client UI

**Status:** [ ] not started

---

## 1. Objective

When this step is done:
- `client/mail_client.py` wraps `smtplib.SMTP` and `poplib.POP3` for login, inbox listing, message fetching, and sending.
- `client/app.py` provides a Tkinter GUI with: login screen, inbox list, message reader, and compose window (with file attachment).
- `scripts/run_client.py` launches the app.

---

## 2. Prerequisites

- Step 04 done: SMTP server accepts mail.
- Step 07 done: POP3 server retrieves mail.

---

## 3. Files to Create or Modify

| Action | Path |
|--------|------|
| Implement | `src/mailsys/client/mail_client.py` |
| Implement | `src/mailsys/client/app.py` |
| Implement | `scripts/run_client.py` |

---

## 4. Detailed Implementation Instructions

### 4.1 `client/mail_client.py`

```python
import poplib
import smtplib
from email import message_from_bytes
from pathlib import Path
from mailsys.config.settings import settings
from mailsys.mime.message_builder import build_message

class MailClient:
    """High-level mail client wrapping smtplib and poplib."""

    def __init__(self, username: str, password: str,
                 smtp_host: str = "localhost", smtp_port: int = settings.smtp_port,
                 pop3_host: str = "localhost", pop3_port: int = settings.pop3_port) -> None:
        self.username = username
        self.password = password
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.pop3_host = pop3_host
        self.pop3_port = pop3_port
        self._domain = settings.local_domain

    @property
    def address(self) -> str:
        return f"{self.username}@{self._domain}"

    def list_inbox(self) -> list[dict]:
        """Connect via POP3, fetch message headers, disconnect.

        Returns a list of dicts: {index, subject, from, date, size}.
        Does NOT download full bodies.
        """

    def fetch_message(self, index: int) -> str:
        """Fetch the full raw message at index via POP3. Returns raw string."""

    def delete_message(self, index: int) -> None:
        """Mark message at index for deletion and QUIT (commits deletion)."""

    def send_message(self, to_addrs: list[str], subject: str,
                     body: str, attachments: list[Path] | None = None) -> None:
        """Build and send a message via SMTP."""
```

**POP3 connection pattern:**
```python
def list_inbox(self) -> list[dict]:
    pop = poplib.POP3(self.pop3_host, self.pop3_port)
    pop.user(self.username)
    pop.pass_(self.password)
    count, _ = pop.stat()
    messages = []
    for i in range(1, count + 1):
        # Fetch only headers using TOP n 0
        raw_lines = pop.top(i, 0)[1]
        raw = b"\r\n".join(raw_lines)
        msg = message_from_bytes(raw)
        messages.append({
            "index": i,
            "subject": msg.get("Subject", "(no subject)"),
            "from": msg.get("From", ""),
            "date": msg.get("Date", ""),
            "size": pop.list(i)[1].split()[1].decode(),
        })
    pop.quit()
    return messages
```

**SMTP send pattern:**
```python
def send_message(self, to_addrs, subject, body, attachments=None):
    raw = build_message(self.address, to_addrs, subject, body,
                        attachments=attachments)
    with smtplib.SMTP(self.smtp_host, self.smtp_port) as smtp:
        smtp.sendmail(self.address, to_addrs, raw)
```

### 4.2 `client/app.py` — Tkinter UI

#### Window structure

```
MailApp (Tk root)
├── LoginFrame (Frame)
│   ├── Entry: username
│   ├── Entry: password
│   └── Button: Login
└── MainFrame (Frame, shown after login)
    ├── InboxPane (Frame, left ~40%)
    │   ├── Label: "Inbox"
    │   ├── Listbox: message list
    │   └── Button: Refresh
    ├── MessagePane (Frame, right ~60%)
    │   ├── Label: headers (From/Subject/Date)
    │   ├── Text: body (read-only)
    │   └── Button: Delete
    └── Button: Compose (opens ComposeWindow)

ComposeWindow (Toplevel)
├── Entry: To
├── Entry: Subject
├── Text: Body
├── Label: Attachments list
├── Button: Add Attachment (filedialog.askopenfilename)
└── Button: Send
```

#### Key implementation points

- Login button calls `MailClient.__init__` and stores it on `self.client`.
- Refresh button calls `self.client.list_inbox()` in a background thread (`threading.Thread`) and updates the Listbox on the main thread via `root.after(0, callback)` (Tkinter is not thread-safe; never update widgets from a non-main thread).
- Selecting a message in the Listbox calls `self.client.fetch_message(index)` in a background thread, then displays in the Text widget.
- Compose window collects To/Subject/Body/Attachments and calls `self.client.send_message(...)`.
- Show errors with `tkinter.messagebox.showerror`.

#### Minimal class skeleton

```python
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
from mailsys.client.mail_client import MailClient
from mailsys.config.settings import settings

class MailApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Mini Mail Client")
        self.client: MailClient | None = None
        self._build_login_frame()

    def _build_login_frame(self) -> None: ...
    def _on_login(self) -> None: ...
    def _build_main_frame(self) -> None: ...
    def _refresh_inbox(self) -> None: ...
    def _on_message_select(self, event) -> None: ...
    def _open_compose(self) -> None: ...
    def run(self) -> None:
        self.root.mainloop()
```

### 4.3 `scripts/run_client.py`

```python
#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
import tkinter as tk
from mailsys.client.app import MailApp

if __name__ == "__main__":
    root = tk.Tk()
    app = MailApp(root)
    app.run()
```

---

## 5. Acceptance Criteria

- [ ] `python scripts/run_client.py` opens the login window without errors.
- [ ] Logging in with valid credentials shows the inbox list.
- [ ] Clicking a message displays its content in the message pane.
- [ ] Clicking Compose opens a compose window.
- [ ] "Add Attachment" opens a file dialog and lists the chosen file.
- [ ] Clicking Send delivers the message (verify file appears in recipient's mailbox).
- [ ] Clicking Refresh updates the inbox list.
- [ ] Invalid credentials shows an error dialog.

---

## 6. How to Test

```powershell
# Ensure servers are running in separate terminals:
python scripts/run_smtp.py
python scripts/run_pop3.py

# Launch client
python scripts/run_client.py
```

Manual walkthrough:
1. Log in as `alice` / `secret`.
2. Send a message to `bob@localhost` with a text attachment.
3. Log out (close window), log in as `bob`.
4. Verify the message from alice appears in inbox.
5. Read and then delete the message.
6. Verify it is removed after refresh.

---

## 7. Wireshark Check

- **Filter:** `tcp.port == 2525 or tcp.port == 2110`
- **Observe:** The client's send action generates an SMTP session; the refresh generates a POP3 session. Both should be visible in Wireshark with full protocol dialog.

---

## 8. Log Update

Append to `docs/log.md`:
```
### [YYYY-MM-DD HH:MM] Step 09: Client UI
- Changed: client/mail_client.py (real), client/app.py (real), run_client.py (real)
- Why: FR-15 — desktop MUA using smtplib/poplib
- Key decisions: Background threads for network ops; root.after(0,...) for UI updates
- Interfaces added: MailClient.list_inbox, fetch_message, delete_message, send_message
- Tests: manual GUI walkthrough
- Next: Step 10 — testing and validation
```

---

## 9. Definition of Done

Full GUI send-and-receive workflow completes without errors, Wireshark shows correct protocol dialogs.

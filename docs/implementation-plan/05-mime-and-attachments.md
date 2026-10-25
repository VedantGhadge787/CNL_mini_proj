# Step 05 — MIME & Attachments

**Status:** [x] complete

---

## 1. Objective

When this step is done:
- `mime/message_builder.py` can build outgoing MIME messages (plain text, HTML, file attachments) as RFC 2822-compliant byte strings.
- It can parse incoming `.eml` bytes and extract headers, body text, and attachment files.
- The Tkinter client (Step 09) and SMTP DATA handling can use these helpers without understanding MIME internals.

---

## 2. Prerequisites

- Step 02 done: `settings`, `get_logger`.
- Step 03 done: `mailbox` (for saving extracted attachments).

---

## 3. Files to Create or Modify

| Action | Path |
|--------|------|
| Implement | `src/mailsys/mime/message_builder.py` |
| Update tests | `tests/test_mime.py` |

---

## 4. Detailed Implementation Instructions

Use **only** the stdlib `email` package. Key sub-modules:
- `email.message.EmailMessage` — modern message object (Python 3.6+)
- `email.policy.EmailPolicy` / `email.policy.SMTP` — encoding policy
- `email.parser.BytesParser` — parse raw bytes to `EmailMessage`

### 4.1 Function signatures

```python
from email.message import EmailMessage
from pathlib import Path

def build_message(
    from_addr: str,
    to_addrs: list[str],
    subject: str,
    body_text: str,
    body_html: str | None = None,
    attachments: list[Path] | None = None,
) -> bytes:
    """Build a MIME message and return it as RFC 2822-compliant bytes.

    - If only body_text: Content-Type text/plain.
    - If body_text + body_html: multipart/alternative.
    - If attachments present: multipart/mixed wrapping the above.
    - Uses email.policy.SMTP for CRLF line endings.
    """

def parse_message(raw: bytes) -> EmailMessage:
    """Parse raw .eml bytes into an EmailMessage object.

    Uses email.parser.BytesParser with policy=email.policy.default.
    """

def get_text_body(msg: EmailMessage) -> str:
    """Extract the plain-text body from a parsed EmailMessage.

    Walks MIME parts and returns the first text/plain payload decoded
    as a UTF-8 string. Returns empty string if none found.
    """

def get_html_body(msg: EmailMessage) -> str | None:
    """Extract the HTML body from a parsed EmailMessage, or None."""

def extract_attachments(msg: EmailMessage, dest_dir: Path) -> list[Path]:
    """Save all attachment parts to dest_dir and return a list of saved Paths.

    Skips parts with Content-Disposition: inline.
    Uses the attachment filename from Content-Disposition (sanitised with
    pathlib to prevent path traversal).
    """

def list_attachments(msg: EmailMessage) -> list[tuple[str, str, int]]:
    """Return a list of (filename, content_type, size_in_bytes) for attachments
    without saving them to disk."""
```

### 4.2 Building a message — implementation notes

```python
import email.policy

def build_message(from_addr, to_addrs, subject, body_text,
                  body_html=None, attachments=None) -> bytes:
    msg = EmailMessage()
    msg["From"] = from_addr
    msg["To"] = ", ".join(to_addrs)
    msg["Subject"] = subject
    msg["Date"] = email.utils.formatdate(localtime=True)
    msg["Message-ID"] = email.utils.make_msgid(domain=settings.local_domain)

    if body_html:
        msg.set_content(body_text)
        msg.add_alternative(body_html, subtype="html")
    else:
        msg.set_content(body_text)

    if attachments:
        for path in attachments:
            maintype, subtype = _guess_mimetype(path)
            with open(path, "rb") as f:
                msg.add_attachment(f.read(), maintype=maintype,
                                   subtype=subtype, filename=path.name)

    return msg.as_bytes(policy=email.policy.SMTP)
```

### 4.3 Attachment MIME type guessing

```python
import mimetypes

def _guess_mimetype(path: Path) -> tuple[str, str]:
    mime, _ = mimetypes.guess_type(str(path))
    if mime and "/" in mime:
        return tuple(mime.split("/", 1))
    return "application", "octet-stream"
```

### 4.4 Parsing — implementation notes

```python
import email.parser, email.policy

def parse_message(raw: bytes) -> EmailMessage:
    return email.parser.BytesParser(policy=email.policy.default).parsebytes(raw)
```

### 4.5 Attachment extraction — path traversal safety

```python
def extract_attachments(msg: EmailMessage, dest_dir: Path) -> list[Path]:
    saved = []
    dest_dir.mkdir(parents=True, exist_ok=True)
    for part in msg.iter_attachments():
        filename = part.get_filename() or "attachment"
        # Sanitise: take only the final name component, no ../ traversal
        safe_name = Path(filename).name
        out_path = dest_dir / safe_name
        out_path.write_bytes(part.get_payload(decode=True))
        saved.append(out_path)
    return saved
```

---

## 5. Acceptance Criteria

- [x] `build_message` returns bytes parseable by `email.parser.BytesParser`.
- [x] A text-only message has `Content-Type: text/plain`.
- [x] A message with HTML has `Content-Type: multipart/alternative`.
- [x] A message with an attachment has `Content-Type: multipart/mixed`.
- [x] `get_text_body(parse_message(raw))` recovers the original body text.
- [x] `extract_attachments` saves attachment bytes exactly as sent.
- [x] Path traversal attempt (`../../evil.py`) is sanitised to `evil.py`.
- [x] `pytest tests/test_mime.py -v` passes.

---

## 6. How to Test

```powershell
python -c "
from pathlib import Path
from mailsys.mime.message_builder import build_message, parse_message, get_text_body, extract_attachments
import tempfile, os

# Build a plain message
raw = build_message('a@localhost', ['b@localhost'], 'Hello', 'Body text')
msg = parse_message(raw)
assert get_text_body(msg) == 'Body text', 'body mismatch'

# Build with attachment
tmp = Path(tempfile.mkdtemp())
att = tmp / 'test.txt'
att.write_text('attachment content')
raw2 = build_message('a@localhost', ['b@localhost'], 'With att', 'Body', attachments=[att])
msg2 = parse_message(raw2)
saved = extract_attachments(msg2, tmp / 'out')
assert len(saved) == 1
assert saved[0].read_text() == 'attachment content'
print('All MIME tests passed')
"

python -m pytest tests/test_mime.py -v
```

---

## 7. Wireshark Check

Not applicable for this step directly. (MIME content is visible inside SMTP DATA capture from Step 04.)

---

## 8. Log Update

Append to `docs/log.md`:
```
### [YYYY-MM-DD HH:MM] Step 05: MIME & Attachments
- Changed: mime/message_builder.py (real)
- Why: Required by client for composing and by SMTP/POP3 for parsing
- Key decisions: stdlib email only; EmailMessage not MIMEMultipart (modern API)
- Interfaces added: build_message, parse_message, get_text_body, get_html_body,
  extract_attachments, list_attachments
- Tests: test_mime.py pass
- Next: Step 06 — spam filter
```

---

## 9. Definition of Done

All acceptance criteria checked, round-trip build/parse works, attachment extraction is path-traversal safe, tests pass.

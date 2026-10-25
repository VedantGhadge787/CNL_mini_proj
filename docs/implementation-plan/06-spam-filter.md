# Step 06 — Spam Filter

**Status:** [x] complete

---

## 1. Objective

When this step is done:
- `spam/filter.py` loads keywords from `spam/keywords.txt` and scores messages.
- Messages at or above the threshold are delivered to the `Spam/` folder with `X-Spam-Flag: YES`.
- The spam filter is integrated into the SMTP `session.py` DATA handling path.

---

## 2. Prerequisites

- Step 04 done: SMTP session can collect DATA.
- Step 05 done: `parse_message`, `get_text_body` available.

---

## 3. Files to Create or Modify

| Action | Path |
|--------|------|
| Implement | `src/mailsys/spam/filter.py` |
| Already exists | `src/mailsys/spam/keywords.txt` (expand with more keywords) |
| Update | `src/mailsys/smtp/session.py` (wire in spam filter call) |
| Update tests | `tests/test_spam_filter.py` |

---

## 4. Detailed Implementation Instructions

### 4.1 `keywords.txt` — expand to a useful set

```
# mini-mail-system spam keyword list
# One keyword or phrase per line. Case-insensitive.
# Lines starting with # are ignored.
free money
click here
winner
you have been selected
claim your prize
limited time offer
act now
guaranteed
no risk
100% free
make money fast
work from home
earn extra cash
congratulations you won
dear friend
```

### 4.2 `spam/filter.py`

```python
from pathlib import Path
from mailsys.config.settings import settings
from mailsys.common.logger import get_logger
from mailsys.mime.message_builder import parse_message, get_text_body

logger = get_logger(__name__)
_KEYWORDS_PATH = Path(__file__).parent / "keywords.txt"

class SpamFilter:
    """Keyword-based spam scorer.

    Loads the keyword list once at instantiation. Call reload() to refresh
    without restarting the server.
    """

    def __init__(self, keywords_path: Path = _KEYWORDS_PATH) -> None:
        self.keywords_path = keywords_path
        self.keywords: list[str] = []
        self.threshold: int = settings.spam_threshold
        self.reload()

    def reload(self) -> None:
        """(Re-)load keywords from file. Thread-safe (GIL protects list replace)."""
        if not self.keywords_path.exists():
            logger.warning("Keywords file not found: %s", self.keywords_path)
            self.keywords = []
            return
        lines = self.keywords_path.read_text(encoding="utf-8").splitlines()
        self.keywords = [
            ln.strip().lower()
            for ln in lines
            if ln.strip() and not ln.startswith("#")
        ]
        logger.info("Spam filter loaded %d keywords", len(self.keywords))

    def score_message(self, raw: bytes) -> tuple[int, bool]:
        """Score a raw message.

        Returns (score, is_spam) where is_spam is True if score >= threshold.
        """
        try:
            msg = parse_message(raw)
            subject = (msg.get("Subject") or "").lower()
            body = get_text_body(msg).lower()
            text = subject + " " + body
        except Exception:
            logger.exception("Error parsing message for spam scoring")
            return 0, False

        score = sum(text.count(kw) for kw in self.keywords)
        return score, score >= self.threshold


# Module-level singleton
spam_filter = SpamFilter()
```

### 4.3 Integrating into `smtp/session.py`

In `_deliver_or_relay`, replace the stub call with:

```python
from mailsys.spam.filter import spam_filter
from mailsys.mime.message_builder import parse_message
import email

# After collecting raw_bytes from _collect_data():
score, is_spam = spam_filter.score_message(raw_bytes)

# Inject X-Spam headers into the message
msg = parse_message(raw_bytes)
msg["X-Spam-Flag"] = "YES" if is_spam else "NO"
msg["X-Spam-Score"] = str(score)
annotated_bytes = msg.as_bytes(policy=email.policy.SMTP)

# Deliver (annotated bytes)
mailbox.deliver(local_user, annotated_bytes, spam=is_spam)
```

### 4.4 `mailbox.deliver` `spam` parameter routing

In `storage/mailbox.py`, the `spam` flag determines the destination folder:

```python
def deliver(username: str, raw_message: bytes, spam: bool = False) -> Path:
    folder = ensure_mailbox(username) / ("Spam" if spam else "") / "new"
    # If spam=False, folder = mailbox_root / "new"
    # If spam=True,  folder = mailbox_root / "Spam" / "new"
    folder.mkdir(parents=True, exist_ok=True)
    ...
```

*(Revise `mailbox.py` accordingly if the initial implementation did not include the `spam` parameter.)*

---

## 5. Acceptance Criteria

- [x] `spam_filter.score_message(raw)` returns `(0, False)` for a clean message.
- [x] A message containing 5 keyword matches scores `(5, True)`.
- [x] Spam messages are delivered to `data/mailboxes/<user>/Spam/new/`.
- [x] Spam messages have `X-Spam-Flag: YES` and `X-Spam-Score: 5` (or correct value) headers.
- [x] Ham messages have `X-Spam-Flag: NO`.
- [x] `spam_filter.reload()` picks up new keywords without restart.
- [x] `pytest tests/test_spam_filter.py -v` passes.

---

## 6. How to Test

### Send a spam message via telnet

```
telnet localhost 2525
EHLO test
MAIL FROM:<spammer@test.com>
RCPT TO:<alice@localhost>
DATA
Subject: free money click here winner you have been selected limited time
From: spammer@test.com
To: alice@localhost

Congratulations! You have been selected for free money. Click here now!
Claim your prize. No risk. 100% free.
.
QUIT
```

Then check:
```powershell
# File should appear in Spam/new/
Get-ChildItem data\mailboxes\alice\Spam\new\

# Open the file and look for X-Spam headers
Get-Content (Get-ChildItem data\mailboxes\alice\Spam\new\ | Select-Object -First 1).FullName | Select-String "X-Spam"
```

### pytest

```powershell
python -m pytest tests/test_spam_filter.py -v
```

---

## 7. Wireshark Check

Not applicable specifically — spam filtering is server-side and invisible at the TCP level.

---

## 8. Log Update

Append to `docs/log.md`:
```
### [YYYY-MM-DD HH:MM] Step 06: Spam Filter
- Changed: spam/filter.py (real), keywords.txt (expanded), smtp/session.py (wired in)
- Why: FR-13/FR-14 — keyword scoring and Spam folder delivery
- Key decisions: score = count of all occurrences; X-Spam headers injected before storage
- Interfaces added: SpamFilter.score_message(raw: bytes) -> tuple[int, bool], spam_filter singleton
- Tests: test_spam_filter.py pass; manual telnet verified spam delivery
- Next: Step 07 — POP3 server
```

---

## 9. Definition of Done

Spam messages land in the `Spam/` folder with correct headers, clean messages land in `new/`, all tests pass.

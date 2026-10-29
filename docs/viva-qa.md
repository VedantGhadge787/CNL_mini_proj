# Viva Examination Q&A Preparation Guide

This document contains the most frequent questions asked during practical examinations, project vivas, and computer networking evaluations, paired with precise, technically accurate answers.

---

### Q1: What is the fundamental difference between SMTP and POP3?
**Answer:**
SMTP (Simple Mail Transfer Protocol, RFC 5321) is a **push protocol** used to submit and transfer messages from a sender's client to a mail server, and to relay messages between servers across the Internet. It operates on port 25 (or port 2525 in our project). 
POP3 (Post Office Protocol version 3, RFC 1939) is a **pull protocol** used exclusively by a client to retrieve messages from its assigned mailbox on a mail server. It operates on port 110 (or port 2110 in our project). SMTP pushes mail in; POP3 pulls mail out.

---

### Q2: Why does SMTP use 3-digit numeric reply codes (e.g., 220, 250, 354, 550)?
**Answer:**
Numeric reply codes allow client software to programmatically and unambiguously determine the outcome of a command without relying on natural language parsing.
- **First digit:** Status category:
  - `2xx`: Positive Completion (e.g., 250 OK)
  - `3xx`: Positive Intermediate (e.g., 354 Start mail input)
  - `4xx`: Transient Negative / Temporary failure (e.g., 421 Service not available)
  - `5xx`: Permanent Negative / Failure (e.g., 550 No such user)
- **Second digit:** Functional category (e.g., syntax error, connection error, mail system error).

---

### Q3: What is "Dot-Stuffing" in SMTP and why is it necessary?
**Answer:**
In the SMTP `DATA` phase, the end of the email body is signaled by a single dot on a line by itself: `<CRLF>.<CRLF>`.
If an email body naturally contains a line beginning with a dot (e.g., `.bashrc`), the receiving server could mistakenly interpret it as the end-of-message marker and cut off the email prematurely.
To prevent this, RFC 5321 mandates **dot-stuffing**:
- The **sender** checks every line: if a line begins with a dot, it prepends an additional dot (`..bashrc`).
- The **receiver** checks every line: if a line begins with two dots, it strips the leading dot. If it encounters a line with only a single dot, it recognizes it as the true end of the body.

---

### Q4: Explain the POP3 state machine and the significance of the UPDATE state.
**Answer:**
POP3 operates across three sequential states:
1. **AUTHORIZATION:** The client connects and provides credentials via `USER` and `PASS`.
2. **TRANSACTION:** The client interacts with the mailbox via `STAT`, `LIST`, `RETR`, and marks messages for deletion via `DELE`.
3. **UPDATE:** Triggered when the client issues `QUIT`.
**Why UPDATE matters:** When a client issues `DELE 1`, the server **does not** delete the file immediately; it merely flags it in memory. If the connection drops or is terminated unexpectedly before `QUIT`, all deletion marks are aborted, ensuring zero data loss. The messages are only permanently unlinked from disk during the UPDATE state upon a clean `QUIT`.

---

### Q5: How is mailbox storage designed in this project, and why?
**Answer:**
The project uses a **Maildir-inspired file architecture**:
`data/mailboxes/<username>/new/` and `data/mailboxes/<username>/cur/`.
- Each email is saved as a discrete, independent `.eml` file containing full RFC 2822 headers and body.
- **Advantages over mbox format:**
  - In `mbox`, all messages are stored in a single large file, which requires expensive file locking and file rewriting when deleting messages.
  - In `Maildir`, message delivery and deletion are fast, atomic file system operations that never risk corrupting other messages.

---

### Q6: How does the system handle concurrent connections and prevent race conditions?
**Answer:**
- **Server concurrency:** `SMTPServer` and `POP3Server` utilize a thread-per-connection model where incoming sockets are dispatched to separate background daemon threads.
- **Race condition prevention:** Multiple threads might attempt to write or delete messages in the same user's mailbox simultaneously. To prevent corruption, `src/mailsys/storage/mailbox.py` maintains an internal dictionary of per-user re-entrant locks (`threading.RLock`).
- **POP3 exclusive lock:** Only one POP3 session can access a user's mailbox at any given time. If a second session attempts to log in with `PASS`, it receives `-ERR [IN-USE] mailbox already locked` and is disconnected.

---

### Q7: How does keyword-based spam filtering work?
**Answer:**
1. Incoming email headers and plain-text body are parsed via the `SpamFilter` module.
2. Words are lowercased and matched against a list of known spam keywords in `keywords.txt` (e.g., "free money", "winner", "urgent", "act now").
3. Each match increments the spam score.
4. If the score reaches or exceeds the threshold (default 5):
   - Headers `X-Spam-Flag: YES` and `X-Spam-Score: <N>` are prepended.
   - The message is diverted away from the standard inbox into `data/mailboxes/<user>/Spam/new/`.

---

### Q8: How does DNS MX relaying work for non-local recipients?
**Answer:**
1. When an email recipient has a non-local domain (e.g., `user@gmail.com`), the SMTP server defers delivery to `relay.py`.
2. `relay.py` queries DNS MX records using `dnspython` (`dns.resolver.resolve(domain, 'MX')`).
3. It sorts the returned records by preference number (lowest preference value = highest priority mail exchanger).
4. It connects to the highest-priority host using `smtplib.SMTP` and attempts delivery. If a host fails or times out, it fails over to the next priority host.
5. If all MX hosts fail, it generates an automated RFC-compliant bounce message back to the local sender's inbox.

---

### Q9: Why are custom non-privileged ports (2525 and 2110) used instead of standard 25 and 110?
**Answer:**
Standard ports (port 25 for SMTP, port 110 for POP3) are privileged system ports (< 1024). Binding to privileged ports requires superuser/administrator privileges (`root` on Linux/macOS or elevated Admin on Windows). Using ports 2525 and 2110 allows the software to run safely in any user-space student or lab environment.

---

### Q10: How are user passwords secured?
**Answer:**
Passwords are never stored in plain text. When a user is created via `scripts/create_user.py`:
1. A cryptographically secure 32-byte salt is generated via `os.urandom(32)`.
2. The password and salt are hashed using `PBKDF2-HMAC-SHA256` with 480,000 iterations.
3. The resulting hash and hex salt are stored in SQLite (`data/mailsys.db`).
4. During authentication, `hmac.compare_digest` is used to prevent timing attacks.

---

### Q11: What is MIME and how are attachments transferred?
**Answer:**
MIME (Multipurpose Internet Mail Extensions) allows email to carry rich formats and binary files over 7-bit ASCII transport.
- Binary files (images, PDFs) are encoded into base64 text blocks.
- The message sets `Content-Type: multipart/mixed` with a unique boundary delimiter (e.g., `--===============123456==`).
- The desktop client uses `extract_attachments` to decode base64 payloads back to original binary files, applying filename sanitization to prevent path-traversal attacks (`../`).

---

### Q12: Why was thread-per-connection chosen over asynchronous I/O (`asyncio`)?
**Answer:**
For an educational networking laboratory project, thread-per-connection aligns directly with the mental model of a sequential state machine. Reading a line blocks only that worker thread, making execution flow linear, intuitive to debug, and simple to inspect line-by-line in a debugger or Wireshark without coroutine overhead.

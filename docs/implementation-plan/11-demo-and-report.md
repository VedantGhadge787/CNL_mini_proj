# Step 11 — Demo & Report

**Status:** [x] done

---

## 1. Objective

When this step is done:
- A step-by-step demo script exists that a person can follow to demonstrate all features.
- A report outline exists covering abstract, architecture, implementation, results, limitations, and future work.
- A viva Q&A preparation list is complete.
- Screenshots have been taken at each demo step.

---

## 2. Prerequisites

- Step 10 done: all features working and all tests passing.

---

## 3. Files to Create or Modify

| Action | Path |
|--------|------|
| Create | `docs/demo-script.md` |
| Create | `docs/report-outline.md` |
| Create | `docs/viva-qa.md` |

---

## 4. Demo Script

The demo should take 10–15 minutes and cover every major feature.

### Step-by-step scenario

**Setup (before audience)**
1. Start SMTP server: `python scripts/run_smtp.py`
2. Start POP3 server: `python scripts/run_pop3.py`
3. Create two users: `python scripts/create_user.py alice pass1` and `bob pass2`
4. Open Wireshark on the loopback interface; set filter `tcp.port == 2525 or tcp.port == 2110`

**Demo sequence**

| # | Action | What to show | Expected result |
|---|--------|-------------|----------------|
| 1 | Launch `run_client.py` | Login screen | GUI opens |
| 2 | Log in as `alice / pass1` | Inbox list | Empty inbox |
| 3 | Compose → To: `bob@localhost`, Subject: "Hello Bob", body: "Hi!", attach a small file | Compose window | — |
| 4 | Click Send | Client sends via SMTP | Wireshark shows SMTP dialog; 250 OK reply |
| 5 | Log out, log in as `bob / pass2` | Bob's inbox | 1 message: "Hello Bob" |
| 6 | Click the message | Message reader | Full message + attachment listed |
| 7 | In another terminal, send a spam message via telnet | Telnet transcript | Wireshark shows DATA phase |
| 8 | Log in as the recipient | Inbox | Spam in Spam folder, X-Spam-Flag: YES visible |
| 9 | Delete the spam message in UI | Click Delete | Message disappears after Refresh |
| 10 | Show `data/mailboxes/` in a file browser | Folder structure | new/, cur/, Spam/new/ visible |
| 11 | Run `pytest tests/ -v` | Terminal | All tests green |

**Screenshots checklist**
- [ ] Login screen
- [ ] Inbox with messages
- [ ] Message reader with attachment
- [ ] Compose window with attachment selected
- [ ] Wireshark SMTP capture
- [ ] Wireshark POP3 capture
- [ ] `data/mailboxes/` folder structure
- [ ] pytest output (all green)

---

## 5. Report Outline

### Title
**Mini Mail System: Building SMTP and POP3 from Raw Sockets in Python**

### Abstract (200 words)
Brief description of the project, what was built, how it was validated, and key learning outcomes.

### 1. Introduction
- Problem statement and motivation
- Scope and out-of-scope items
- Report structure

### 2. Background and Related Protocols
- SMTP (RFC 5321): purpose, commands, state machine
- POP3 (RFC 1939): purpose, commands, state machine
- MIME (RFC 2045–2049): multipart structure
- DNS MX records: role in mail routing

### 3. System Architecture
- High-level component diagram (from `architecture.md`)
- SMTP state machine diagram
- POP3 state machine diagram
- Data design (Maildir layout, SQLite schema)
- Concurrency model

### 4. Implementation
- Module-by-module description (one paragraph per module)
- Key implementation challenges and solutions:
  - Dot-stuffing in SMTP DATA
  - POP3 UPDATE state (delete-only-on-QUIT)
  - Per-mailbox threading locks
  - Path-traversal safe attachment extraction
  - Spam scoring algorithm

### 5. Results and Testing
- Unit test results (`pytest -v` output)
- End-to-end test results
- Concurrency test results (10 simultaneous SMTP clients)
- Wireshark captures and observations
- Manual telnet transcripts

### 6. Limitations
- No TLS/encryption
- No rate limiting or DoS protection
- POP3 only (no IMAP)
- No DKIM/SPF
- Lab/loopback use only

### 7. Future Work
- STARTTLS with `ssl.wrap_socket`
- IMAP4 server
- DKIM signing and verification
- Web UI (Flask)
- Message threading and search

### 8. Conclusion
- Learning outcomes: socket programming, protocol state machines, concurrency, MIME
- Summary of what works

### References
- RFC 5321 — SMTP
- RFC 1939 — POP3
- RFC 2045 — MIME
- Python documentation: socket, threading, email, sqlite3
- dnspython documentation

---

## 6. Viva Q&A Preparation

### Q1: What is the difference between SMTP and POP3?
**A:** SMTP (RFC 5321) is used to *send* and *relay* email between servers (push protocol). POP3 (RFC 1939) is used by a *client* to *retrieve* email from a server (pull protocol). SMTP is always involved in delivery; POP3 is used only by the end user's mail client.

### Q2: Why do SMTP replies use numeric codes?
**A:** Numeric codes allow programmatic parsing without natural-language processing. The first digit indicates the class (2xx = success, 3xx = intermediate, 4xx = temporary error, 5xx = permanent error). The second digit further categorises (e.g. 5 = mail system, 0 = syntax). This design, from RFC 5321, lets any MTA understand responses regardless of the message text.

### Q3: What is dot-stuffing and why is it necessary?
**A:** In the SMTP DATA phase, the end of the message body is signalled by a lone `.` on a line by itself (CRLF.CRLF). If the message itself contains a line that starts with `.`, it would be misinterpreted as the terminator. Dot-stuffing (RFC 5321 §4.5.2) requires the sender to prepend an extra `.` to any such line; the receiver strips it on receipt. Without this, messages containing lines like `.` would be truncated.

### Q4: What is the POP3 UPDATE state and why does it exist?
**A:** POP3 has three states: AUTHORIZATION, TRANSACTION, and UPDATE. DELE commands in TRANSACTION state only *mark* messages for deletion — they are not removed from disk. The UPDATE state is entered only when the client sends QUIT successfully. At that point, all marked messages are permanently deleted. This ensures that if the network drops mid-session, messages are not lost.

### Q5: How does your system store messages, and why?
**A:** Messages are stored in a Maildir-style layout: one `.eml` file per message, in `new/` (unread) or `cur/` (read) subdirectories under the user's mailbox. This design is lockless for delivery (files are written atomically by naming convention), inspectable with any text editor, and matches the layout of real-world Maildir implementations.

### Q6: How does your spam filter work?
**A:** The filter loads a keyword list from `keywords.txt`. For each incoming message, it extracts the Subject header and plain-text body, lowercases them, and counts occurrences of each keyword. The score equals the total count. If the score is ≥ the configurable threshold (default 5), the message is classified as spam: two headers (`X-Spam-Flag: YES`, `X-Spam-Score: N`) are injected, and the message is delivered to `Spam/new/` instead of `new/`.

### Q7: Why use thread-per-connection instead of asyncio?
**A:** Thread-per-connection maps the protocol state machine to sequential Python code, making it easy to read and debug. Each connection is independent; blocking reads block only that thread. asyncio would require rewriting all socket operations as coroutines, introducing `await` throughout and making Wireshark analysis harder to correlate. For a lab with few simultaneous connections, threads are simpler and sufficient.

### Q8: How do you prevent two POP3 clients from corrupting the same mailbox?
**A:** `mailbox.py` maintains a dictionary of `threading.Lock` objects, one per username. A POP3 session acquires this lock non-blockingly (`lock.acquire(blocking=False)`) at authentication. If the lock is already held by another session, the server responds with `-ERR [IN-USE] mailbox already locked` and closes the connection. The lock is released on QUIT.

### Q9: Why are non-privileged ports (2525, 2110) used instead of 25 and 110?
**A:** On Linux and macOS, ports below 1024 require root privileges (`CAP_NET_BIND_SERVICE`). Using 2525 and 2110 avoids the need to run the server as root, which is a security risk in a lab environment. The ports are configurable via environment variables.

### Q10: How does MX relay work in your system?
**A:** When the SMTP session receives a `RCPT TO` for a non-local domain, it defers delivery to `relay.py`. After DATA collection, `relay.py` calls `dns.resolver.resolve(domain, "MX")` using `dnspython` to get MX records, sorts them by priority (lowest priority number = highest preference), and attempts delivery to each MX host in order using `smtplib.SMTP`. If all fail, a bounce message is generated and delivered to the sender's local inbox.

### Q11: How are passwords stored securely?
**A:** Passwords are never stored in plain text. On user creation, 32 random bytes are generated as a salt (`os.urandom(32)`). The password is hashed with `hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 480_000)`. Both the salt (hex-encoded) and the hash are stored in SQLite. On verification, the same PBKDF2 computation is run and compared with `hmac.compare_digest` to prevent timing attacks.

### Q12: What is MIME and how does your system handle attachments?
**A:** MIME (Multipurpose Internet Mail Extensions, RFC 2045–2049) extends the basic email format to support non-ASCII characters, HTML bodies, and binary attachments. Your system uses Python's stdlib `email.message.EmailMessage` to build multipart/mixed messages with text, HTML, and file parts. On the receive side, `email.parser.BytesParser` parses incoming `.eml` bytes, and `iter_attachments()` extracts binary parts, saving them to disk with path-traversal sanitisation.

### Q13: How did you test concurrent access?
**A:** A pytest test (`test_concurrent_deliver_no_corruption`) spawns 10 threads, each calling `mailbox.deliver()` simultaneously for the same user. After all threads complete, the test asserts that exactly 10 files were created with no errors. The per-user lock in `mailbox.py` ensures atomicity. A separate test confirms that a second POP3 session for the same user is rejected immediately.

### Q14: What would you add if you had more time?
**A:** The highest-value addition would be STARTTLS (RFC 3207) using Python's `ssl.wrap_socket`, which would encrypt the SMTP and POP3 sessions. Second would be IMAP4 (RFC 9051) for multi-folder support, flags, and partial message fetch. DKIM signing would improve deliverability to real external servers.

### Q15: How did you verify the protocol implementation is correct?
**A:** Three methods: (1) manual telnet/netcat sessions where commands and replies were typed and observed directly; (2) Wireshark packet captures on the loopback interface showing correct SMTP and POP3 frames, reply codes, and multi-line response termination; (3) Python's own `smtplib` and `poplib` as reference client implementations — if they work against our server, the server is sufficiently RFC-compliant.

---

## 7. Log Update

Append to `docs/log.md`:
```
### [YYYY-MM-DD HH:MM] Step 11: Demo & Report
- Changed: docs/demo-script.md, docs/report-outline.md, docs/viva-qa.md created
- Why: Final submission materials
- Key decisions: N/A
- Interfaces added: None
- Tests: All tests passing (from Step 10)
- Next: Project complete ✓
```

---

## 8. Definition of Done

Demo runs without errors, all screenshots taken, report written, viva Q&A reviewed.

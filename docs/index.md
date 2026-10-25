# mini-mail-system — Project Index

**One-line summary:** A locally hosted email system built from raw Python sockets, implementing SMTP receive, POP3 retrieval, Maildir storage, MIME attachments, keyword spam filtering, and a Tkinter desktop client — for educational purposes in a Computer Networks lab.

---

## 1. Problem Statement

Email is one of the oldest and most universally understood application-layer protocols, yet its internals remain opaque to most developers who rely on hosted services. Understanding how mail actually moves — from a sender's MUA, through an MTA over SMTP, into a mailbox, and back to a recipient's MUA over POP3 — requires hands-on construction.

This project builds every component of that pipeline from the ground up using raw TCP sockets, forcing engagement with protocol state machines, CRLF line discipline, dot-stuffing, multi-line responses, and concurrent client handling. The result is a working local mail system that can be inspected with Wireshark, exercised with telnet, and extended into a full production-grade system.

### In Scope

| Feature | Description |
|---------|-------------|
| SMTP receive | Hand-written SMTP server accepting mail on port 2525 |
| Local delivery | Maildir-style per-user storage in `data/mailboxes/` |
| POP3 retrieve | Hand-written POP3 server serving mail on port 2110 |
| MIME support | Parsing and building messages with text, HTML, and file attachments |
| Keyword spam filter | Score-based filter with configurable keyword list and threshold |
| Tkinter client | Desktop MUA using `smtplib`/`poplib` to send and retrieve mail |
| MX relay | DNS MX lookup via `dnspython` for forwarding to external domains |

### Out of Scope

| Feature | Reason |
|---------|--------|
| TLS / STARTTLS | Adds significant complexity; localhost use only |
| IMAP | Out of time scope; POP3 is sufficient for the lab |
| DKIM / SPF / DMARC | Authentication infrastructure beyond lab scope |
| Webmail UI | Tkinter client is sufficient; web adds a separate tech stack |
| Push notifications | POP3 is poll-based; IMAP IDLE is out of scope |
| Production hardening | This is a lab prototype, not a production MTA |

---

## 2. Objectives

1. Implement a fully RFC 5321-compliant SMTP receive path using raw sockets.
2. Implement a fully RFC 1939-compliant POP3 server using raw sockets.
3. Store messages in a Maildir-compatible layout (`new/`, `cur/`) with `.eml` files.
4. Support MIME multipart messages and file attachments (parse and build).
5. Integrate a keyword-based spam filter that scores messages and delivers flagged mail to a `Spam` folder with an `X-Spam-Flag` header.
6. Implement DNS MX lookup and outbound SMTP relay to external domains.
7. Provide a Tkinter desktop client that can log in, list the inbox, read messages, compose with attachments, and send mail.
8. Achieve end-to-end delivery (compose → send → store → retrieve → display) in a local test.
9. Support at least 5 simultaneous client connections without deadlock or data corruption.
10. Pass all unit tests in `tests/` with `pytest`.

---

## 3. Functional Requirements

| ID | Requirement |
|----|-------------|
| FR-1 | The SMTP server SHALL accept TCP connections on the port defined by `SMTP_PORT` (default 2525). |
| FR-2 | The SMTP server SHALL implement the commands: `HELO`, `EHLO`, `MAIL FROM`, `RCPT TO`, `DATA`, `RSET`, `NOOP`, `QUIT`, and optionally `VRFY`. |
| FR-3 | The SMTP server SHALL reject mail to unknown local recipients with reply code 550. |
| FR-4 | The SMTP server SHALL apply dot-stuffing rules during DATA receipt (RFC 5321 §4.5.2). |
| FR-5 | The SMTP server SHALL pass received messages through the spam filter before delivery. |
| FR-6 | The SMTP server SHALL deliver local mail to the recipient's `new/` Maildir subfolder. |
| FR-7 | The SMTP server SHALL relay non-local mail via DNS MX lookup and outbound SMTP. |
| FR-8 | The POP3 server SHALL accept TCP connections on the port defined by `POP3_PORT` (default 2110). |
| FR-9 | The POP3 server SHALL implement all mandatory POP3 commands: `USER`, `PASS`, `STAT`, `LIST`, `RETR`, `DELE`, `NOOP`, `RSET`, `QUIT`; plus optional `UIDL` and `TOP`. |
| FR-10 | The POP3 server SHALL enter UPDATE state only on successful `QUIT`; messages marked for deletion SHALL be purged only then. |
| FR-11 | User accounts SHALL be stored in SQLite with salted password hashes (pbkdf2_hmac or scrypt). |
| FR-12 | Messages SHALL be stored as individual `.eml` files in per-user Maildir directories. |
| FR-13 | The spam filter SHALL load keywords from `src/mailsys/spam/keywords.txt` and assign a score of 1 per keyword match (case-insensitive). |
| FR-14 | Messages with a spam score ≥ `SPAM_THRESHOLD` SHALL be delivered to a `Spam` subfolder and have `X-Spam-Flag: YES` and `X-Spam-Score: <n>` headers added. |
| FR-15 | The Tkinter client SHALL support: login, inbox listing, message reading, composing, attaching files, and sending. |
| FR-16 | All servers SHALL log connections, commands, and errors to both console and `data/logs/`. |

---

## 4. Non-Functional Requirements

| ID | Requirement |
|----|-------------|
| NFR-1 | **Concurrency:** Both servers SHALL use one thread per accepted connection; the main accept loop SHALL remain unblocked. |
| NFR-2 | **Thread safety:** Mailbox writes and POP3 `DELE`/`UPDATE` SHALL be protected by per-mailbox locks to prevent corruption under concurrent access. |
| NFR-3 | **Protocol fidelity:** All SMTP reply codes and POP3 response tokens SHALL exactly match the RFCs as listed in the Protocol Coverage table below. |
| NFR-4 | **Portability:** The system SHALL run on Python 3.11+ on Windows and Linux without modification. |
| NFR-5 | **Configurability:** All ports, domain, data directory, spam threshold, and log level SHALL be configurable via environment variables without code changes. |
| NFR-6 | **No protocol libraries on server side:** No `aiosmtpd`, `smtpd`, or equivalent server-framework library SHALL be used in the server source. |
| NFR-7 | **Testability:** Every module SHALL have a corresponding test file; `pytest tests/` SHALL exit 0 on a correctly scaffolded + implemented project. |
| NFR-8 | **Logging:** No server code SHALL use `print()`; all output SHALL go through the `logging` module. |

---

## 5. Tech Stack and Tools

| Component | Choice | Why |
|-----------|--------|-----|
| Language | Python 3.11+ | Rich stdlib (socket, threading, email, sqlite3, hashlib, logging, tkinter); no JVM/GC tuning needed for a lab project |
| Networking | `socket` + `threading` | Mandatory: hand-written protocol state machines; thread-per-connection is simple and observable with Wireshark |
| SMTP port | 2525 | Non-privileged (>1024); avoids `sudo`; configurable |
| POP3 port | 2110 | Non-privileged (>1024); avoids `sudo`; configurable |
| Message parsing | stdlib `email` | Handles RFC 2822 / MIME correctly; no extra dependency |
| Storage | Filesystem Maildir-style | Simple, inspectable, no DB dependency for message blobs; `.eml` files readable directly |
| User DB | `sqlite3` (stdlib) | Lightweight, file-based, no server process; sufficient for a lab user count |
| Password hashing | `hashlib.pbkdf2_hmac` | Stdlib; salted; NIST-approved; scrypt is an alternative |
| MX lookup | `dnspython` | De-facto standard DNS library; clean API for MX record queries |
| Client UI | Tkinter | Stdlib on CPython; no extra install; sufficient for a lab demo |
| Client protocol | `smtplib` / `poplib` | Stdlib; correct use of client-side protocol libs is allowed |
| Testing | `pytest` | Industry standard; simple fixture model; parametrize for protocol edge cases |
| Config | `settings.py` + `os.environ` | Twelve-factor app pattern; single source of truth |
| Logging | stdlib `logging` | Rotating file handler + stream handler; zero external dependencies |
| Dev tools | `telnet` / `netcat`, Wireshark | Manual protocol testing; packet inspection |

---

## 6. Protocol Coverage

### 6.1 SMTP Commands (RFC 5321)

| Command | Syntax | States Valid In | Success Reply | Error Replies |
|---------|--------|-----------------|---------------|---------------|
| `HELO` | `HELO <domain>` | Any before MAIL | 250 | 501 (bad syntax), 500 (unknown cmd) |
| `EHLO` | `EHLO <domain>` | Any before MAIL | 250 (multi-line) | 501, 500 |
| `MAIL FROM` | `MAIL FROM:<addr>` | After HELO/EHLO | 250 | 501, 503 (bad sequence) |
| `RCPT TO` | `RCPT TO:<addr>` | After MAIL FROM | 250 | 501, 503, 550 (no such user) |
| `DATA` | `DATA` | After ≥1 RCPT TO | 354 (go ahead), then 250 on `.` | 503, 552 (too large), 554 |
| `RSET` | `RSET` | Any | 250 | — |
| `NOOP` | `NOOP` | Any | 250 | — |
| `QUIT` | `QUIT` | Any | 221 | — |
| `VRFY` | `VRFY <addr>` | Any | 250 or 252 | 550, 502 (not implemented) |

### 6.2 POP3 Commands (RFC 1939)

| Command | Syntax | State | Success | Error |
|---------|--------|-------|---------|-------|
| `USER` | `USER <name>` | AUTHORIZATION | `+OK` | `-ERR` |
| `PASS` | `PASS <password>` | AUTHORIZATION (after USER) | `+OK` | `-ERR` |
| `STAT` | `STAT` | TRANSACTION | `+OK <count> <octets>` | `-ERR` |
| `LIST` | `LIST [msg]` | TRANSACTION | `+OK` + multi-line or single | `-ERR` |
| `RETR` | `RETR <msg>` | TRANSACTION | `+OK <octets>` + message | `-ERR` |
| `DELE` | `DELE <msg>` | TRANSACTION | `+OK` | `-ERR` |
| `NOOP` | `NOOP` | TRANSACTION | `+OK` | — |
| `RSET` | `RSET` | TRANSACTION | `+OK` | — |
| `UIDL` | `UIDL [msg]` | TRANSACTION | `+OK` + uid listing | `-ERR` |
| `TOP` | `TOP <msg> <n>` | TRANSACTION | `+OK` + headers + n body lines | `-ERR` |
| `QUIT` | `QUIT` | ANY | `+OK` (enters UPDATE if in TRANSACTION) | — |

---

## 7. Glossary

| Term | Definition |
|------|------------|
| **SMTP** | Simple Mail Transfer Protocol (RFC 5321). The protocol used to send and relay email between mail servers. |
| **POP3** | Post Office Protocol version 3 (RFC 1939). A protocol allowing a mail client to retrieve messages from a server. |
| **MIME** | Multipurpose Internet Mail Extensions (RFC 2045–2049). Extends the basic email format to support non-ASCII text, HTML bodies, and file attachments. |
| **MX** | Mail Exchanger. A DNS record type that specifies which server accepts email for a domain. Used for routing outbound mail. |
| **MTA** | Mail Transfer Agent. A program that receives, routes, and relays email between servers (e.g. this project's SMTP server). |
| **MDA** | Mail Delivery Agent. The component responsible for storing mail into the recipient's mailbox (this project's `mailbox.py` / storage layer). |
| **MUA** | Mail User Agent. A program used by end users to send and read email (this project's Tkinter client). |
| **CRLF** | Carriage Return + Line Feed (`\r\n`). SMTP and POP3 require every protocol line to end with CRLF, not just `\n`. |
| **Dot-stuffing** | The RFC 5321 mechanism by which a lone `.` on a line marks the end of the DATA body. Any line in the message that begins with `.` must be transmitted with an extra `.` prepended; the server removes the extra dot on receipt. |
| **Maildir** | A mailbox storage format where each message is a separate file. Subdirectories `new/` (unread) and `cur/` (read/delivered) are used. No locking needed for delivery (one file per message), but reads need coordination for POP3 DELETE. |

---

## 8. Documentation Map

| File | Description | When to Read |
|------|-------------|-------------|
| [README.md](../README.md) | Project overview, setup, and run commands | First — before anything else |
| [AGENTS.md](../AGENTS.md) | Working rules for AI agents in this repo | Start of every AI session |
| [docs/index.md](index.md) | Full requirements, protocol tables, glossary | Orientation and requirements review |
| [docs/architecture.md](architecture.md) | System design, state machines, data layout, concurrency | Before implementing any module |
| [docs/log.md](log.md) | Session-by-session change log; Current State block | Start of every implementation session |
| [docs/implementation-plan/00-overview.md](implementation-plan/00-overview.md) | Step table, dependency graph, and working rules | Planning; tracking overall progress |
| [docs/implementation-plan/01-environment-setup.md](implementation-plan/01-environment-setup.md) | Virtualenv, deps, git init, first pytest run | Before Step 01 |
| [docs/implementation-plan/02-config-and-logging.md](implementation-plan/02-config-and-logging.md) | settings.py, logger setup | Before Step 02 |
| [docs/implementation-plan/03-user-management-and-storage.md](implementation-plan/03-user-management-and-storage.md) | SQLite users, Maildir mailbox | Before Step 03 |
| [docs/implementation-plan/04-smtp-server-core.md](implementation-plan/04-smtp-server-core.md) | Full SMTP state machine | Before Step 04 |
| [docs/implementation-plan/05-mime-and-attachments.md](implementation-plan/05-mime-and-attachments.md) | MIME parsing and building | Before Step 05 |
| [docs/implementation-plan/06-spam-filter.md](implementation-plan/06-spam-filter.md) | Keyword filter, X-Spam headers | Before Step 06 |
| [docs/implementation-plan/07-pop3-server.md](implementation-plan/07-pop3-server.md) | Full POP3 state machine | Before Step 07 |
| [docs/implementation-plan/08-mx-lookup-and-relay.md](implementation-plan/08-mx-lookup-and-relay.md) | DNS MX, outbound delivery | Before Step 08 |
| [docs/implementation-plan/09-client-ui.md](implementation-plan/09-client-ui.md) | Tkinter client implementation | Before Step 09 |
| [docs/implementation-plan/10-testing-and-validation.md](implementation-plan/10-testing-and-validation.md) | pytest suite, manual tests, Wireshark | Before Step 10 |
| [docs/implementation-plan/11-demo-and-report.md](implementation-plan/11-demo-and-report.md) | Demo script, report outline, viva Q&A | Before final submission |

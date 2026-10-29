# Project Report: Mini Mail System

**Title:** Implementation of a Multi-Threaded RFC-Compliant Mail Transfer & Retrieval System (SMTP/POP3) from Raw Sockets in Python  
**Course:** Computer Networks & Internet Protocols Laboratory  
**Technology Stack:** Python 3.12, Raw Sockets (`socket`), Threading (`threading`), MIME (`email`), Tkinter GUI, SQLite3, `dnspython`, `pytest`

---

## Abstract
Electronic mail remains one of the foundational distributed communication mechanisms of the Internet. This project presents the design and implementation of a complete, educational, end-to-end mail system consisting of a hand-crafted **Simple Mail Transfer Protocol (SMTP, RFC 5321)** server, a hand-crafted **Post Office Protocol version 3 (POP3, RFC 1939)** server, a content-based spam detection engine, dynamic DNS MX record resolution and outbound relay, an atomic Maildir storage architecture, and a modern Tkinter desktop Mail User Agent (MUA).

All protocol logic, state transitions, command processing, and socket multiplexing were implemented without high-level server libraries, utilizing Python's low-level `socket` and `threading` modules. The system was validated using Wireshark packet analysis, manual RFC command dialogs, thread-safety stress tests (10 concurrent clients), and a test suite of 75 automated unit and end-to-end integration tests.

---

## 1. Introduction
### 1.1 Motivation & Problem Statement
Modern application development frequently abstracts network protocols behind high-level third-party software (e.g., Postfix, Sendmail, Dovecot). This abstraction hinders deep conceptual understanding of socket communication, client-server handshake state machines, byte-level line buffering, and protocol timing. The primary objective of this project is to demystify internet messaging by hand-crafting RFC-compliant SMTP and POP3 server and client architectures from fundamental network primitives.

### 1.2 System Scope
- **Server-Side:**
  - RFC 5321 core SMTP server listening on port 2525 supporting HELO, EHLO, MAIL FROM, RCPT TO, DATA, RSET, VRFY, NOOP, and QUIT.
  - RFC 1939 core POP3 server listening on port 2110 supporting USER, PASS, STAT, LIST, RETR, DELE, NOOP, RSET, UIDL, TOP, and QUIT.
  - Multi-threaded concurrency model (thread-per-connection) with per-mailbox re-entrant synchronization locks.
  - Spam scoring engine checking incoming content against customizable keywords.
  - DNS MX lookup via `dnspython` for remote domain relaying with local bounce generation.
  - Maildir-style disk storage layout with PBKDF2 password hashing in SQLite.
- **Client-Side:**
  - Desktop graphical user interface (Tkinter) providing account login, multi-threaded inbox polling, email reader, attachment extraction, and message composition.

---

## 2. Theoretical Background & Protocols

### 2.1 SMTP (RFC 5321) — Push Protocol
SMTP is a connection-oriented, text-based push protocol operating over TCP. 
- **Command-Reply Pattern:** The client transmits ASCII commands terminated by `<CRLF>` (`\r\n`), and the server replies with 3-digit numeric status codes (e.g., `220 Service Ready`, `250 OK`, `354 Start Mail Input`, `550 User Not Found`).
- **Data Phase & Dot-Stuffing:** The email body is transmitted after receiving code `354`. The client signals the end of input by sending `<CRLF>.<CRLF>`. To prevent premature termination when a line naturally begins with a period, RFC 5321 mandates *dot-stuffing* (prepending an additional `.` before transmitting, which the receiver strips upon arrival).

### 2.2 POP3 (RFC 1939) — Pull Protocol
POP3 is an offline message retrieval pull protocol operating over TCP.
- **Three-Phase State Machine:**
  1. **AUTHORIZATION:** The client authenticates using `USER <username>` followed by `PASS <password>`.
  2. **TRANSACTION:** The client queries mailbox statistics (`STAT`), lists messages (`LIST`), retrieves full or partial content (`RETR`, `TOP`), and marks items for deletion (`DELE`).
  3. **UPDATE:** Initiated by `QUIT`. The server locks the maildrop, purges all marked messages from disk, and cleanly closes the connection. If the session drops prematurely, all deletion marks are rolled back.

### 2.3 MIME (Multipurpose Internet Mail Extensions, RFC 2045–2049)
Extends basic 7-bit ASCII text messaging to accommodate multipart message structures, arbitrary character sets (UTF-8), HTML representations, and base64-encoded binary attachments.

---

## 3. System Architecture & Design

### 3.1 High-Level Component Diagram
```
                     +---------------------------------------+
                     |         Desktop Client (MUA)          |
                     |             Tkinter GUI               |
                     +-------------------+-------------------+
                                         |
                       SMTP (TCP :2525)  |  POP3 (TCP :2110)
                                         v
+----------------------------------------------------------------------------+
|                             Mini Mail System                               |
|                                                                            |
|   +-----------------------+                    +-----------------------+   |
|   |      SMTPServer       |                    |      POP3Server       |   |
|   |  - Socket Accept Loop |                    |  - Socket Accept Loop |   |
|   |  - Daemon Threads     |                    |  - Daemon Threads     |   |
|   +-----------+-----------+                    +-----------+-----------+   |
|               |                                            |               |
|               v                                            v               |
|   +-----------------------+                    +-----------------------+   |
|   |      SMTPSession      |                    |      POP3Session      |   |
|   |  - RFC 5321 FSM       |                    |  - RFC 1939 FSM       |   |
|   |  - Command Dispatch   |                    |  - Lock Acquisition   |   |
|   +-----+-----------+-----+                    +-----------+-----------+   |
|         |           |                                      |               |
|         v           v                                      v               |
|   +-----------+ +-----------+                  +-----------------------+   |
|   |Spam Filter| | DNS Relay |                  |  Mailbox Storage API  |   |
|   | Keywords  | | MX Lookup |                  |  - Atomic writes      |   |
|   +-----+-----+ +-----------+                  |  - Per-user locks     |   |
|         |                                      +-----------+-----------+   |
|         +-------------------+                              |               |
|                             v                              v               |
|                    +-----------------------------------------------+       |
|                    |             Maildir File Store                |       |
|                    |  data/mailboxes/<user>/{new, cur, Spam/new}   |       |
|                    +-----------------------------------------------+       |
+----------------------------------------------------------------------------+
```

### 3.2 Storage Layout & Concurrency Controls
- **Maildir Format:** Emails are stored in individual `.eml` files under `data/mailboxes/<username>/new/` or `data/mailboxes/<username>/cur/`. Spam messages are segregated into `data/mailboxes/<username>/Spam/new/`.
- **Concurrency & Locking:** SMTPServer and POP3Server run asynchronous multi-threaded listener loops. Thread safety across simultaneous connections is guaranteed using per-user re-entrant locks (`threading.RLock`) in memory.

---

## 4. Key Implementation Details
1. **Low-Level Socket Buffering:** `protocol_utils.py` contains a custom byte-level line reader with buffer preservation to handle line fragmenting and prevent command truncation.
2. **Deterministic SMTP State Machine:** Transitions between `CONNECTED -> HELO -> MAIL -> RCPT -> DATA -> QUIT` with strict RFC syntax and order enforcement (e.g. rejecting `DATA` before `RCPT TO` with code `503`).
3. **Transaction-Safe POP3 Deletions:** Deletion commands (`DELE`) only stage message indices in a Python `set()`. Physical file unlinking only occurs upon clean `QUIT`.
4. **MIME Message Construction & Parsing:** Handled via Python's standard `email` library with defensive path sanitization to neutralize directory traversal vulnerabilities (`../`) in attachment filenames.

---

## 5. Verification, Testing & Results
- **Automated Test Suite:** A total of **75 comprehensive tests** implemented in `pytest`:
  - Unit tests for configuration, password hashing, and protocol utils.
  - State machine tests for SMTP and POP3 over Python `socketpair`.
  - Multi-threaded concurrency tests verifying 10 concurrent threads delivering to the same mailbox without collision or file corruption.
  - End-to-end integration tests using `smtplib` and `poplib`.
- **Wireshark Analysis:** Packet captures over the loopback interface confirm strict compliance with RFC line formats, ASCII code responses, and dot-stuffing termination.

---

## 6. Limitations & Future Enhancements
- **Limitations:**
  - Operates over unencrypted plaintext sockets (no TLS/SSL support).
  - Lack of anti-abuse rate-limiting or anti-spoofing mechanisms (SPF, DKIM, DMARC).
  - POP3 only downloads messages sequentially; no server-side folder management (IMAP4).
- **Future Enhancements:**
  - Implementation of `STARTTLS` using `ssl.wrap_socket`.
  - Addition of an IMAP4 server engine.
  - Integration of an administrative web console.

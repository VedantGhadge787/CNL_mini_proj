# docs/log.md — Project Change Log

> **Purpose for AI agents:** This file is the memory of the project. Read the **Current State** block and the **latest 10 entries** before doing anything in any session. Do not load the full file if the History Summary section contains everything you need.

---

## Current State

| Field | Value |
|-------|-------|
| **Current implementation step** | Complete (All steps 00–11 done) |
| **Last completed step** | Step 11 — Demo & Report |
| **Files with real logic** | `settings.py`, `logger.py`, `auth/user_manager.py`, `storage/mailbox.py`, `scripts/create_user.py`, `common/protocol_utils.py`, `smtp/server.py`, `smtp/session.py`, `smtp/relay.py`, `scripts/run_smtp.py`, `mime/message_builder.py`, `spam/filter.py`, `pop3/server.py`, `pop3/session.py`, `scripts/run_pop3.py`, `client/mail_client.py`, `client/app.py`, `scripts/run_client.py` |
| **Files with full content** | All docs/, AGENTS.md, README.md, requirements.txt, .gitignore, .env.example, pytest.ini |
| **Known issues** | None |
| **Next action** | Project complete ✓ |

---

## Log Entries (newest first)

### [2026-10-30 00:28] Bug Fix: Attachment Viewing & File Downloading
- **Changed:**
  - `src/mailsys/mime/message_builder.py`: Added `get_attachment_parts(msg)` returning attachment metadata and decoded binary payloads. Updated `extract_attachments` and `list_attachments`.
  - `src/mailsys/client/mail_client.py`: Added `fetch_message_bytes(index)` to retrieve POP3 messages directly in byte form to avoid Unicode replacement corruption of binary attachments.
  - `src/mailsys/client/app.py`:
    - Fixed raw MIME fallback bug: if `get_text_body` is empty, display `"(No message text body. Attachment: ...)"` instead of dumping raw base64 noise into the message reader.
    - Added dedicated interactive `Attachments` box in the message reader with file names, formatted sizes (KB/MB), and a prominent **`[ Download / Save As... ]`** button for each file.
- **Why:** Enable direct binary file downloading and prevent raw base64 text from rendering in the preview pane.
- **Tests:** All 75 tests passing; roundtrip PNG binary payload verified.

### [2026-10-29 23:20] Step 11: Demo & Report
- **Changed:**
  - Created `docs/demo-script.md` providing a 10–15 minute step-by-step presentation walkthrough covering account provisioning, GUI sending, POP3 retrieval, spam filtering, UPDATE state semantics, and test verification.
  - Created `docs/report-outline.md` structuring the academic/project report with abstract, theoretical background, architecture diagrams, implementation deep-dive, test results, limitations, and future work.
  - Created `docs/viva-qa.md` containing 12+ essential viva/oral examination questions and technical answers.
  - Created `docs/study-guide.md` offering an intuitive, high-level conceptual explanation of how the system works using real-world analogies, step-by-step flows, and simple breakdowns.
- **Why:** Final project documentation and demonstration readiness.
- **Key decisions:** N/A.
- **Interfaces added:** None.
- **Tests:** All 75 tests passing across entire project suite.
- **Next:** Project complete ✓

### [2026-10-29 23:18] Step 10: Testing & Validation
- **Changed:**
  - Fleshed out `tests/test_end_to_end.py` with real integration tests: `test_full_send_receive_flow`, `test_spam_routed_to_spam_folder`, and `test_attachment_send_and_retrieve`.
  - Verified full test suite using ephemeral ports for concurrent SMTP and POP3 listeners.
- **Why:** NFR-7 — complete end-to-end testing and validation.
- **Key decisions:** Use verified spam keywords against threshold for spam routing test; round-trip binary verification for MIME attachment decoding.
- **Interfaces added:** E2E test suite.
- **Tests:** All 75 tests passing (`pytest tests/ -v`).
- **Next:** Step 11 — Demo & Report

### [2026-10-29 23:01] Step 09: Client UI

- **Changed:**
  - Implemented `src/mailsys/client/mail_client.py` wrapping standard `smtplib` and `poplib` with user authentication, inbox header retrieval with `TOP`, full message retrieval with `RETR`, deletion marking with `DELE` + `QUIT`, and MIME message sending with `build_message` and `sendmail`.
  - Implemented `src/mailsys/client/app.py` providing a Tkinter GUI featuring `LoginFrame` (credential authentication), `MainFrame` with left `InboxPane` (inbox Listbox with refresh) and right `MessagePane` (message header preview, body viewer, attachment saving, and delete action), and `ComposeWindow` (recipients, subject, text body, and multi-file attachments).
  - Ensured all network I/O operations execute in background threads (`threading.Thread`) and safely schedule UI updates on Tkinter's main thread using `root.after(0, ...)`.
  - Implemented CLI entry point `scripts/run_client.py`.
  - Exported `MailClient` and `MailApp` in `src/mailsys/client/__init__.py`.
  - Added test suite `tests/test_mail_client.py` covering `MailClient` methods, live server interactions, and `MailApp` GUI headless lifecycle.
- **Why:** FR-15 — desktop MUA using smtplib/poplib with graphical interface.
- **Key decisions:**
  - Background daemon threads for all network operations with thread-safe `root.after` dispatch to avoid freezing the UI.
  - Added attachment listing and local file saving to user-selected directory from the preview pane.
  - Added user logout flow allowing easy account switching between test users.
- **Interfaces added:** `MailClient.authenticate`, `MailClient.list_inbox`, `MailClient.fetch_message`, `MailClient.delete_message`, `MailClient.send_message`, `MailApp`, `ComposeWindow`.
- **Tests:** 7 new tests in `tests/test_mail_client.py`; all 75 project tests pass.
- **Next:** Begin Step 10 — Testing & Validation

### [2026-10-25 20:15] Step 08: MX Lookup & Relay

- **Changed:**
  - Implemented `src/mailsys/smtp/relay.py` to resolve and priority-sort MX records, attempt outbound SMTP delivery to each host, log DNS/SMTP failures, and create a local bounce after all relay attempts fail.
  - Wired `SMTPSession._deliver_or_relay` to send spam-annotated messages and the original envelope sender through `relay_message` for external recipients.
  - Added `tests/test_smtp_relay.py` for DNS result ordering/failures/timeouts, SMTP failover and recipient refusal, local bounce behavior, non-local sender handling, and SMTP session integration.
- **Why:** Implements FR-7, forwarding non-local mail using DNS MX lookup and outbound SMTP.
- **Key decisions:**
  - Used `dnspython` for DNS and `smtplib` as the permitted SMTP client library.
  - Bounces are delivered only to known users at the configured local domain. Live outbound mail was not sent; SMTP success/failure behavior is verified with test doubles.
- **Interfaces added:** `lookup_mx(domain) -> list[str]`, `relay_message(recipient, raw_bytes, sender) -> bool`.
- **Tests:** Full project suite: 68 tests pass. Live `gmail.com` MX lookup returned five priority-sorted hosts; a nonexistent `.invalid` domain returned `[]`.
- **Next:** Begin Step 09 — Client UI

### [2026-10-25 20:00] Step 07: POP3 Server

- **Changed:**
  - Implemented `src/mailsys/pop3/server.py` with a raw-socket listener, per-connection daemon threads, configured socket timeouts, logging, and clean shutdown.
  - Implemented `src/mailsys/pop3/session.py` with AUTHORIZATION, TRANSACTION, UPDATE, and CLOSED states; USER/PASS authentication; non-blocking exclusive mailbox locking; STAT, LIST, RETR, DELE, NOOP, RSET, UIDL, TOP, and QUIT commands.
  - POP3 deletion marks remain in memory until successful QUIT; disconnected sessions release their mailbox lock without deleting messages.
  - Added dot-stuffing for retrieved message data and stable UIDL values from the mailbox storage helper.
  - Implemented `scripts/run_pop3.py` and expanded `tests/test_pop3_session.py` to cover command behavior, deletion/update semantics, concurrency, and listener startup/shutdown.
- **Why:** Implements FR-8 through FR-10 and the POP3 state/concurrency design described in the architecture.
- **Key decisions:**
  - Reused the existing per-user re-entrant mailbox lock and mailbox/authentication helpers.
  - `USER` rejects unknown accounts; failed `PASS` clears the pending username so a fresh USER command is required.
- **Interfaces added:** `POP3Server.start/stop`, `POP3Session.handle`, and `POP3State`.
- **Tests:** `tests/test_pop3_session.py` all 15 tests pass; full test suite all 58 tests pass.
- **Next:** Begin Step 08 — MX Lookup & Relay

### [2026-10-25 19:05] Step 06: Spam Filter

- **Changed:**
  - Implemented `src/mailsys/spam/filter.py`:
    - `SpamFilter`: loads keywords from `keywords.txt` with case-insensitive whitespace/comment-stripping; scores subject and body text.
    - `SpamFilter.reload()`: thread-safe keyword reloading.
    - `SpamFilter.score_message(raw: bytes) -> tuple[int, bool]`: calculates keyword frequency against configurable threshold.
    - Module singleton `spam_filter` exported in `src/mailsys/spam/__init__.py`.
  - Updated `src/mailsys/smtp/session.py`:
    - Wired `spam_filter.score_message` into `_deliver_or_relay`.
    - Added `X-Spam-Flag: YES/NO` and `X-Spam-Score: <score>` header injection before storage.
    - Routed messages to `data/mailboxes/<user>/Spam/new/` when flagged as spam (`spam=True`), or `data/mailboxes/<user>/new/` when clean (`spam=False`).
  - Implemented comprehensive test suite in `tests/test_spam_filter.py`:
    - Clean message zero score.
    - Case-insensitive keyword matching.
    - Threshold boundary testing (4 -> False, 5 -> True, 6 -> True).
    - Custom keywords file and dynamic reloading.
    - SMTP delivery pipeline integration for both spam and ham messages.
- **Why:** FR-13 / FR-14 keyword-based spam scoring and isolated Spam folder delivery.
- **Key decisions:**
  - Score is the total occurrence count of all matched keywords across Subject and body.
  - Header annotation strips pre-existing `X-Spam-*` headers to prevent header spoofing before writing canonical tags.
- **Interfaces added:** `SpamFilter.score_message`, `SpamFilter.reload`, `spam_filter` singleton.
- **Tests:** `tests/test_spam_filter.py` all 7 tests pass; full test suite (55 tests) all pass.
- **Next:** Begin Step 07 — POP3 Server

### [2026-10-25 18:58] Step 05: MIME & Attachments

- **Changed:**
  - Implemented `src/mailsys/mime/message_builder.py`:
    - `build_message`: builds RFC 2822/MIME compliant bytes for plain text, `multipart/alternative` (HTML), and `multipart/mixed` (attachments) with CRLF endings using `email.policy.SMTP`.
    - `parse_message`: parses raw bytes into `EmailMessage` using `email.policy.default`.
    - `get_text_body`: extracts plain-text body and normalizes line endings.
    - `get_html_body`: extracts HTML body if present.
    - `extract_attachments`: extracts and saves attachment parts while preventing path traversal (sanitizing both POSIX and Windows separators).
    - `list_attachments`: inspects attachment metadata `(filename, content_type, size)` without writing to disk.
    - Added `from __future__ import annotations` across `src/mailsys/smtp/server.py`, `src/mailsys/smtp/session.py`, `src/mailsys/mime/message_builder.py`, and `tests/test_mime.py` for Python 3.9+ typing compatibility.
  - Implemented comprehensive test suite in `tests/test_mime.py` covering plain text, HTML alternative, attachments, round-trip serialization/parsing, path traversal attack prevention, inline part filtering, and MIME type guessing.
- **Why:** Required by the client UI for message composition and rendering, and by server components (SMTP / POP3 / Spam filter) for message parsing.
- **Key decisions:**
  - stdlib `email` package only (`EmailMessage`, `email.policy.SMTP`, `email.policy.default`).
  - Path traversal protection strips leading directories and relative traversal elements (`../`, `..\`) across operating systems.
- **Interfaces added:** `build_message`, `parse_message`, `get_text_body`, `get_html_body`, `extract_attachments`, `list_attachments`.
- **Tests:** `tests/test_mime.py` all 8 tests pass; full test suite (53 tests) all pass.
- **Next:** Begin Step 06 — Spam Filter

### [2026-10-25 13:33] Step 04: SMTP Server Core

- **Changed:**
  - Implemented `src/mailsys/common/protocol_utils.py` with `recv_line`, `send_reply`, `send_pop3_ok`, `send_pop3_err`, and `send_multiline`.
  - Implemented `src/mailsys/smtp/server.py` with raw socket listener and thread-per-connection spawning daemon threads executing `SMTPSession.handle()`.
  - Implemented `src/mailsys/smtp/session.py` with full RFC 5321 state machine:
    - Commands: HELO, EHLO, MAIL FROM, RCPT TO, DATA, RSET, NOOP, VRFY, QUIT.
    - Local recipient verification against `user_exists(user)`.
    - RFC 5321 dot-unstuffing and message size threshold rejection with code 552.
    - Standard RFC error handling: 500 (unrecognized), 501 (syntax), 503 (sequence), 550 (unknown user).
    - Local mailbox delivery to `data/mailboxes/<user>/new/`.
  - Implemented `scripts/run_smtp.py` entry point.
  - Implemented complete test suite in `tests/test_smtp_session.py` covering greetings, commands, dot-stuffing, size limits, bad sequences, and full delivery pipeline.
- **Why:** Core server networking functionality enabling direct SMTP client submission and storage.
- **Key decisions:**
  - Raw `socket` and `threading` implementation with zero third-party server wrappers.
  - Dot-unstuffing applied during stream reading per RFC 5321 Section 4.5.2.
- **Interfaces added:** `SMTPServer.start/stop`, `SMTPSession.handle`, `recv_line`, `send_reply`, `send_pop3_ok`, `send_pop3_err`, `send_multiline`.
- **Tests:** `tests/test_smtp_session.py` all 8 tests pass; full test suite (50 tests) all pass.
- **Next:** Begin Step 05 — MIME & Attachments


### [2026-10-25 13:29] Step 03: User Management & Storage

- **Changed:**
  - Implemented `src/mailsys/auth/user_manager.py` with SQLite backing (`users` table), PBKDF2-HMAC-SHA256 password hashing (480k rounds, 32-byte salt), `hmac.compare_digest` verification, and existence check.
  - Implemented `src/mailsys/storage/mailbox.py` with Maildir-style directory layout (`new/`, `cur/`, `Spam/new/`, `Spam/cur/`), per-user re-entrant locking (`threading.RLock`), message enumeration, reading, deletion, and stable UID generation.
  - Implemented `scripts/create_user.py` CLI utility.
  - Updated `tests/test_mailbox.py` with full unit tests and concurrency verification (10 parallel threads).
  - Added `Settings.reload()` method to allow dynamic configuration and testing directory rebinding.
- **Why:** Foundation for all server components — SMTP and POP3 both require authentication and mailbox storage.
- **Key decisions:**
  - Per-user locking uses `threading.RLock()` to prevent self-deadlocks during composite operations like message deletion.
  - PBKDF2 with 480k rounds for secure password storage without external dependencies.
- **Interfaces added:** `create_user`, `verify_password`, `user_exists`, `ensure_mailbox`, `deliver`, `list_messages`, `read_message`, `delete_message`, `generate_uid`.
- **Tests:** `tests/test_mailbox.py` all 11 tests pass; CLI `create_user.py` verified; acceptance smoke tests pass.
- **Next:** Begin Step 04 — SMTP Server Core


### [2026-10-25 13:16] Step 02: Config & Logging

- **Changed:**
  - Implemented `src/mailsys/config/settings.py` with dataclass, lazy environment loading via default factories, property paths (`mailboxes_dir`, `logs_dir`, `db_path`), and module-level `settings` singleton.
  - Implemented `src/mailsys/common/logger.py` with `get_logger`, `StreamHandler`, and `RotatingFileHandler` writing to `data/logs/mailsys.log` (5 MB, 3 backups) with handler deduplication.
  - Verified `src/mailsys/config/__init__.py` and `src/mailsys/common/__init__.py` re-exports.
  - Created unit tests in `tests/test_config_logging.py` covering defaults, environment variable overrides, property paths, handler deduplication, and rotating file logging.
  - Configured `.venv/Lib/site-packages/mailsys.pth` for permanent clean package resolution.
- **Why:** Every subsequent module requires access to centralized runtime configuration and uniform logging before any protocol or storage features can be implemented.
- **Key decisions:**
  - Settings configured as module-level singleton dataclass with lazy field factories.
  - Handlers automatically guarded against duplication for clean execution in testing and multi-import environments.
- **Interfaces added:** `settings` (Settings), `get_logger(name: str) -> Logger`.
- **Tests:** `tests/test_config_logging.py` passed; entire test suite (47 tests) passed.
- **Next:** Begin Step 03 — User Management & Storage


### [2026-10-25 13:12] Step 01: Environment Setup

- **Changed:**
  - Created `.venv` virtual environment (Python 3.12)
  - Installed dependencies `dnspython>=2.6` and `pytest>=8.0`
  - Created `pytest.ini` and updated `tests/conftest.py` to ensure `src/` is on `sys.path`
  - Verified git repository initialized and initial commit pushed to remote
- **Why:** Establish clean, reproducible development environment and ensure test runner discovers and executes test stubs.
- **Key decisions:**
  - Pinned `pytest` configuration in `pytest.ini` with `pythonpath = src`
- **Interfaces added/changed:** None
- **Tests:** `pytest --collect-only` discovered 41 items across 6 test modules; `pytest tests/ -v` passed all 41 test stubs
- **Next:** Begin Step 02 — Config & Logging


### [2026-10-25 12:32] Step 00: Scaffolding and Documentation

- **Changed:**
  - Created entire project directory structure under `mini-mail-system/`
  - Created root files: `README.md`, `AGENTS.md`, `requirements.txt`, `.gitignore`, `.env.example`, `data/.gitkeep`
  - Created fully written documentation: `docs/index.md`, `docs/architecture.md`, `docs/log.md` (this file)
  - Created 12 implementation plan files: `docs/implementation-plan/00-overview.md` through `11-demo-and-report.md`
  - Created Python stub files (docstring + imports + TODO stubs, zero logic) for all 23 source modules in `src/mailsys/`
  - Created 5 runner script stubs in `scripts/`
  - Created 7 test file stubs in `tests/`
  - Created `src/mailsys/spam/keywords.txt` with placeholder keywords
- **Why:** Establish project foundation and documentation before any implementation begins. Ensures every future AI session has full context without re-deriving architecture decisions.
- **Key decisions:**
  - Thread-per-connection, not asyncio (simpler state machine, easier to observe in Wireshark)
  - Maildir-style storage (lockless delivery, file-per-message)
  - pbkdf2_hmac for password hashing (stdlib, no extra deps)
  - Non-privileged ports 2525/2110 (no sudo required)
  - POP3 over IMAP (POP3 is simpler, sufficient for lab objectives)
  - `smtplib`/`poplib` allowed on client side; all server protocol logic must be hand-written
- **Interfaces added/changed:** None — all stubs; no callable interfaces yet
- **Tests:** No tests run (no logic exists); `pytest --collect-only` should pass after Step 01 environment setup
- **Next:** Begin Step 01 — environment setup (virtualenv, `pip install -r requirements.txt`, `git init`, first `pytest` run)

---

## Summarization Rule

When this file exceeds approximately 300 lines, summarize all entries **older than the latest 20** into a "History Summary" section below, then delete those original entries. The History Summary must include: which steps were completed, key decisions made, and any interfaces that were stabilised. Always keep the last 20 entries verbatim.

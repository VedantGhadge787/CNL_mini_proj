# docs/log.md — Project Change Log

> **Purpose for AI agents:** This file is the memory of the project. Read the **Current State** block and the **latest 10 entries** before doing anything in any session. Do not load the full file if the History Summary section contains everything you need.

---

## Current State

| Field | Value |
|-------|-------|
| **Current implementation step** | Step 05 — MIME & Attachments |
| **Last completed step** | Step 04 — SMTP Server Core |
| **Files with real logic** | `settings.py`, `logger.py`, `auth/user_manager.py`, `storage/mailbox.py`, `scripts/create_user.py`, `common/protocol_utils.py`, `smtp/server.py`, `smtp/session.py`, `scripts/run_smtp.py` |
| **Files with full content** | All docs/, AGENTS.md, README.md, requirements.txt, .gitignore, .env.example, pytest.ini |
| **Known issues** | None |
| **Next action** | Begin Step 05: implement mime/message_builder.py, tests/test_mime.py |

---

## Log Entries (newest first)

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

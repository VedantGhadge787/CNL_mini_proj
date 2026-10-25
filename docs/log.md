# docs/log.md — Project Change Log

> **Purpose for AI agents:** This file is the memory of the project. Read the **Current State** block and the **latest 10 entries** before doing anything in any session. Do not load the full file if the History Summary section contains everything you need.

---

## Current State

| Field | Value |
|-------|-------|
| **Current implementation step** | Step 03 — User Management & Storage |
| **Last completed step** | Step 02 — Config & Logging |
| **Files with real logic** | `src/mailsys/config/settings.py`, `src/mailsys/common/logger.py` |
| **Files with full content** | All docs/, AGENTS.md, README.md, requirements.txt, .gitignore, .env.example, pytest.ini |
| **Known issues** | None |
| **Next action** | Begin Step 03: implement auth/user_manager.py, storage/mailbox.py, scripts/create_user.py, tests/test_mailbox.py |

---

## Log Entries (newest first)

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

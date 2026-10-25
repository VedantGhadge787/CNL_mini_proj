# docs/log.md — Project Change Log

> **Purpose for AI agents:** This file is the memory of the project. Read the **Current State** block and the **latest 10 entries** before doing anything in any session. Do not load the full file if the History Summary section contains everything you need.

---

## Current State

| Field | Value |
|-------|-------|
| **Current implementation step** | Step 01 — Environment Setup |
| **Last completed step** | Step 00 — Scaffolding (this session) |
| **Files with real logic** | None yet — all source files are stubs |
| **Files with full content** | All docs/, AGENTS.md, README.md, requirements.txt, .gitignore, .env.example |
| **Known issues** | None |
| **Next action** | Begin Step 01: create virtualenv, install deps, run `pytest --collect-only`, `git init` |

---

## Log Entries (newest first)

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

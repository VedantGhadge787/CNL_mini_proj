# AGENTS.md — Working Rules for AI Agents

This file is read by every AI agent that opens this repository. Follow these rules **exactly and without exception** throughout any session.

---

## Rule 1 — Start of Session: Read These Three Things First

Before writing any code or modifying any file:

1. Read **`docs/log.md`** — the "Current State" block and the latest 10 entries.
2. Read the **single implementation-plan file** for the current step (e.g. `docs/implementation-plan/04-smtp-server-core.md`).
3. Read the **relevant sections** of `docs/architecture.md` that apply to the current step. Do not load the full file unless you need it.

Do not load other source files unless they are explicitly needed to complete the current step.

---

## Rule 2 — One Step at a Time, In Order

Work on **exactly one implementation step** per session. Do not begin a step until all its prerequisites (listed in the step file) are marked done. Steps are numbered `01` through `11`; follow that order.

---

## Rule 3 — No Unrecorded Tech Changes

Never change a tech decision or alter the directory structure without:

- Adding a row to the **"Design Decisions Log"** table in `docs/architecture.md`.
- Appending an entry to **`docs/log.md`**.

If you believe a change is necessary, propose it in `docs/log.md` under a "Proposed Change" note and wait for human review.

---

## Rule 4 — End of Session: Update Logs and Status

At the end of every session (or when a step is complete):

1. Append an entry to `docs/log.md` using the format defined in that file.
2. Update the **"Current State"** block at the top of `docs/log.md`.
3. Tick the status checkbox in the step file (`docs/implementation-plan/NN-*.md`).
4. Tick the corresponding row in the overview table in `docs/implementation-plan/00-overview.md`.

---

## Rule 5 — Hand-Write All Protocol Logic

All SMTP and POP3 protocol logic (socket accept loops, state machines, command parsing, reply formatting) **must be hand-written** using only Python's `socket` and `threading` standard library modules.

**Forbidden** server-side libraries: `aiosmtpd`, `smtpd`, any third-party SMTP/POP3 server framework.

**Allowed** client-side libraries (for the Tkinter client and testing only): `smtplib`, `poplib`, `telnetlib`.

---

## Rule 6 — RFC Reply Codes are Mandatory

Use **only** the SMTP reply codes and POP3 reply codes defined in `docs/index.md` (Protocol Coverage table). Do not invent reply codes. Key SMTP codes: 220, 250, 354, 221, 500, 501, 503, 550, 552, 554. Key POP3 indicators: `+OK`, `-ERR`.

---

## Rule 7 — Tests in the Same Step as the Feature

Every step that creates or modifies source code **must also create or update** the corresponding test file in `tests/`. Do not defer tests to a later step.

---

## Rule 8 — Code Style

- Keep every function **under 40 lines** where possible; extract helpers otherwise.
- Use **type hints** on all function signatures.
- Write a **docstring** on every public class, method, and function.
- Use `logger.debug / .info / .warning / .error` — never `print()` in server code.
- Follow PEP 8. Use 4-space indentation.

---

## Rule 9 — State Assumptions Explicitly

If a requirement in the implementation plan is ambiguous or underspecified, **do not guess silently**. Instead:

1. State your assumption in `docs/log.md` under the current entry (label it "Assumption:").
2. Implement according to that assumption.
3. Flag it for human review in the same log entry.

---

## Rule 10 — Never Commit Secrets or Runtime Data

- Never commit `.env` (it is gitignored).
- Never commit anything inside `data/` other than `data/.gitkeep`.
- Never hard-code passwords, keys, or domain names — always read from `settings.py`.

---

## Quick Reference

| Item | Location |
|------|----------|
| Current step & state | `docs/log.md` → Current State block |
| Step instructions | `docs/implementation-plan/NN-<step>.md` |
| Architecture | `docs/architecture.md` |
| RFC reply codes | `docs/index.md` → Protocol Coverage |
| Design decisions | `docs/architecture.md` → Design Decisions Log |
| All rules (this file) | `AGENTS.md` |

# Step 01 — Environment Setup

**Status:** [x] done

---

## 1. Objective

When this step is done:
- A Python 3.11+ virtual environment exists and is activated.
- `dnspython` and `pytest` are installed.
- `pytest --collect-only` runs without errors and discovers all 6 test files.
- The repository is initialised with `git init` and an initial commit containing only non-gitignored files.

---

## 2. Prerequisites

- Step 00 (Scaffolding) is complete — all files and directories exist.
- Python 3.11+ is installed and on `PATH`.
- Git is installed (optional — skip `git init` if unavailable).

---

## 3. Files to Create or Modify

| Action | Path | Notes |
|--------|------|-------|
| No new source files | — | This step is environment setup only |
| Optionally create | `.python-version` | Pin Python version (e.g. `3.11`) |

---

## 4. Detailed Implementation Instructions

### 4.1 Create the virtual environment

```powershell
# From the project root (mini-mail-system/)
python -m venv .venv
```

### 4.2 Activate the virtual environment

```powershell
# Windows PowerShell
.venv\Scripts\Activate.ps1

# Windows CMD
.venv\Scripts\activate.bat

# macOS / Linux
source .venv/bin/activate
```

### 4.3 Install dependencies

```powershell
pip install -r requirements.txt
```

Expected output: `Successfully installed dnspython-2.x.x pytest-8.x.x` (plus their transitive deps).

### 4.4 Verify pytest can collect tests

```powershell
python -m pytest tests/ --collect-only
```

Expected output: 6 test files collected, 0 errors. All test functions should appear as `<Function test_...>` stubs.

### 4.5 Verify imports work

```powershell
python -c "import dns.resolver; print('dnspython OK')"
python -c "import pytest; print('pytest OK')"
```

### 4.6 Initialise git repository

```powershell
git init
git add .
git commit -m "chore: initial scaffolding and documentation"
```

Verify that `data/` contents (except `.gitkeep`) and `.env` are not staged:
```powershell
git status  # data/*.eml and .env should not appear
```

---

## 5. Acceptance Criteria

- [x] `.venv/` directory exists in the project root.
- [x] `pip list` shows `dnspython` and `pytest` installed.
- [x] `python -m pytest tests/ --collect-only` exits with code 0 and lists 6 test modules.
- [x] `python -c "import dns.resolver"` exits without error.
- [x] `git log --oneline` shows commit.
- [x] `git status` is clean (no untracked relevant files).


---

## 6. How to Test

```powershell
# Confirm venv is active (should show .venv path)
python -c "import sys; print(sys.prefix)"

# Run full test collect
python -m pytest tests/ --collect-only -q

# Run pytest (should pass — all tests are stubs with pass body)
python -m pytest tests/ -v
```

Expected: `6 passed` (or `N passed` matching the number of stub test functions).

---

## 7. Wireshark Check

Not applicable for this step.

---

## 8. Log Update

After completing this step:
1. Append an entry to `docs/log.md` using this format:
   ```
   ### [YYYY-MM-DD HH:MM] Step 01: Environment Setup
   - Changed: .venv created, deps installed, git init
   - Why: Establish reproducible dev environment
   - Key decisions: Python 3.11, pinned deps in requirements.txt
   - Interfaces added/changed: None
   - Tests: pytest --collect-only passed (6 modules)
   - Next: Begin Step 02 — config and logging
   ```
2. Update the **Current State** block: set "Current implementation step" to "Step 02".
3. Tick `[x]` next to Step 01 in `docs/implementation-plan/00-overview.md`.
4. Tick the **Status** checkbox at the top of this file.

---

## 9. Definition of Done

All acceptance criteria are checked, `git log` shows the initial commit, and `docs/log.md` has been updated.

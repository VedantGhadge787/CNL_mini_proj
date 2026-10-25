# mini-mail-system

A local email system built from scratch using raw Python sockets, created as a Computer Networks lab project. It implements an SMTP server that accepts and routes mail, per-user Maildir-style mailbox storage, a POP3 server for mail retrieval, MIME attachment support, a keyword-based spam filter, and a simple Tkinter desktop client — all without relying on any server-side email protocol libraries.

---

## Quick Start

```bash
# 1. Clone and enter the project
git clone <repo-url>
cd mini-mail-system

# 2. Create and activate a virtual environment
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env if you want non-default ports or domain

# 5. Create a user account
python scripts/create_user.py alice secret123

# 6. Run everything (SMTP + POP3 servers)
python scripts/run_all.py

# 7. Launch the desktop client (in a separate terminal)
python scripts/run_client.py
```

## Running Servers Individually

```bash
# SMTP server only (default port 2525)
python scripts/run_smtp.py

# POP3 server only (default port 2110)
python scripts/run_pop3.py
```

## Running Tests

```bash
pytest tests/ -v
```

## Project Structure

```
mini-mail-system/
├── src/mailsys/        # All server-side source packages
├── scripts/            # Convenience runner scripts
├── tests/              # pytest test suite
├── docs/               # Full project documentation
└── data/               # Runtime data (gitignored)
```

## Documentation

See [docs/index.md](docs/index.md) for the full project index, requirements, protocol coverage, and documentation map.

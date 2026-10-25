#!/usr/bin/env python3
"""
scripts/create_user.py
======================
CLI tool to provision a new user account in SQLite and create their mailbox folders.

Usage:
    python scripts/create_user.py <username> <password>
"""
import sys
from pathlib import Path

# Add project src directory to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from mailsys.auth.user_manager import create_user, user_exists
from mailsys.storage.mailbox import ensure_mailbox


def main() -> None:
    """Parse command line arguments and create user account."""
    if len(sys.argv) != 3:
        print("Usage: create_user.py <username> <password>")
        sys.exit(1)

    username = sys.argv[1].strip()
    password = sys.argv[2]

    if user_exists(username):
        print(f"Error: user '{username}' already exists.")
        sys.exit(1)

    try:
        create_user(username, password)
        ensure_mailbox(username)
        print(f"User '{username}' created successfully.")
    except Exception as e:
        print(f"Error creating user: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

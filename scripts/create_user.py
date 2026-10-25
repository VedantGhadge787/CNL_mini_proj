"""
scripts/create_user.py
======================
CLI tool to provision a new user account in SQLite and create their mailbox folders.

Usage:
    python scripts/create_user.py <username> <password>
"""
import argparse
import sys
from pathlib import Path

# Add project src directory to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from mailsys.auth.user_manager import create_user
from mailsys.storage.mailbox import ensure_mailbox


def main() -> None:
    """Parse command line arguments and create user account."""
    parser = argparse.ArgumentParser(description="Create a new Mini Mail System user account")
    parser.add_argument("username", help="Username (e.g. alice)")
    parser.add_argument("password", help="Plain text password")
    args = parser.parse_args()

    # TODO: Call create_user and ensure_mailbox, print success message
    raise NotImplementedError


if __name__ == "__main__":
    main()

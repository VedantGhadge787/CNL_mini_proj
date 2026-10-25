"""
mailsys.auth.user_manager
=========================
User management and authentication backed by SQLite.

Provides:
  - SQLite database initialization (`users` table).
  - User creation with cryptographically secure random salt and PBKDF2-HMAC-SHA256 password hashing.
  - Password verification using constant-time comparison (`hmac.compare_digest`).
  - User existence check for SMTP RCPT TO and POP3 USER commands.

Schema:
    CREATE TABLE IF NOT EXISTS users (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        username      TEXT    NOT NULL UNIQUE,
        salt          TEXT    NOT NULL,
        password_hash TEXT    NOT NULL,
        created_at    DATETIME DEFAULT CURRENT_TIMESTAMP
    );

Imports needed:
    import hashlib
    import hmac
    import os
    import sqlite3
    from mailsys.common.logger import get_logger
    from mailsys.config.settings import settings
"""
import hashlib
import hmac
import os
import sqlite3
from mailsys.common.logger import get_logger
from mailsys.config.settings import settings

logger = get_logger(__name__)


def _get_connection() -> sqlite3.Connection:
    """Open (and initialise if needed) the SQLite DB at settings.db_path.

    Returns:
        sqlite3.Connection: An open database connection.

    TODO:
        - Ensure parent directory exists: settings.data_dir.mkdir(parents=True, exist_ok=True)
        - Connect to settings.db_path
        - Execute CREATE TABLE IF NOT EXISTS users (...)
        - Return connection
    """
    # TODO: Implement
    raise NotImplementedError


def create_user(username: str, password: str) -> None:
    """Create a new user account with a salted hash of the password.

    Args:
        username: The account username (case-normalized / lowercase).
        password: The plain-text password.

    Raises:
        ValueError: If username already exists or parameters are invalid.

    TODO:
        - Validate username and password are not empty
        - Generate 32 bytes random salt: os.urandom(32).hex()
        - Compute hash with hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), 480_000).hex()
        - Insert into database with parameterized query
        - Call ensure_mailbox(username) from storage.mailbox
    """
    # TODO: Implement
    raise NotImplementedError


def verify_password(username: str, password: str) -> bool:
    """Return True if the username exists and password is correct, False otherwise.

    Uses hmac.compare_digest to prevent timing attacks.

    Args:
        username: Account username.
        password: Plain text password to check.

    Returns:
        bool: True if authentication succeeds, False otherwise.

    TODO:
        - Query salt and password_hash for username
        - If user not found, return False
        - Compute hash of provided password with retrieved salt
        - Return hmac.compare_digest(stored_hash, computed_hash)
    """
    # TODO: Implement
    raise NotImplementedError


def user_exists(username: str) -> bool:
    """Return True if a user with this username exists in the database.

    Args:
        username: Account username to check.

    Returns:
        bool: True if user exists, False otherwise.

    TODO:
        - Parameterized query: SELECT 1 FROM users WHERE username = ?
        - Return bool(cursor.fetchone())
    """
    # TODO: Implement
    raise NotImplementedError

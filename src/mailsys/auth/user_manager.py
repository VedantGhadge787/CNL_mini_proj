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
    """
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(settings.db_path)
    conn.row_factory = sqlite3.Row
    with conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                username      TEXT    NOT NULL UNIQUE,
                salt          TEXT    NOT NULL,
                password_hash TEXT    NOT NULL,
                created_at    DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
    return conn


def create_user(username: str, password: str) -> None:
    """Create a new user account with a salted hash of the password.

    Args:
        username: The account username (case-normalized / lowercase).
        password: The plain-text password.

    Raises:
        ValueError: If username already exists or parameters are invalid.
    """
    if not username or not password:
        raise ValueError("Username and password must not be empty.")

    uname = username.strip().lower()
    if user_exists(uname):
        raise ValueError(f"User '{uname}' already exists.")

    salt = os.urandom(32).hex()
    pwd_hash = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), bytes.fromhex(salt), 480_000
    ).hex()

    conn = _get_connection()
    try:
        with conn:
            conn.execute(
                "INSERT INTO users (username, salt, password_hash) VALUES (?, ?, ?)",
                (uname, salt, pwd_hash),
            )
        logger.info("Created user account for '%s'", uname)
    finally:
        conn.close()

    # Create Maildir folder hierarchy for the new user
    from mailsys.storage.mailbox import ensure_mailbox

    ensure_mailbox(uname)


def verify_password(username: str, password: str) -> bool:
    """Return True if the username exists and password is correct, False otherwise.

    Uses hmac.compare_digest to prevent timing attacks.

    Args:
        username: Account username.
        password: Plain text password to check.

    Returns:
        bool: True if authentication succeeds, False otherwise.
    """
    if not username or not password:
        return False

    uname = username.strip().lower()
    conn = _get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT salt, password_hash FROM users WHERE username = ?", (uname,)
        )
        row = cursor.fetchone()
        if not row:
            return False

        salt: str = row["salt"]
        stored_hash: str = row["password_hash"]
        candidate_hash = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), bytes.fromhex(salt), 480_000
        ).hex()

        return hmac.compare_digest(stored_hash, candidate_hash)
    finally:
        conn.close()


def user_exists(username: str) -> bool:
    """Return True if a user with this username exists in the database.

    Args:
        username: Account username to check.

    Returns:
        bool: True if user exists, False otherwise.
    """
    if not username:
        return False

    uname = username.strip().lower()
    conn = _get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM users WHERE username = ?", (uname,))
        return cursor.fetchone() is not None
    finally:
        conn.close()

"""
mailsys.storage.mailbox
=======================
Maildir-inspired file-based mailbox storage with per-user threading locks.

Directory layout:
    data/mailboxes/<username>/
        new/      <- delivered messages (unread)
        cur/      <- read messages
        Spam/
            new/
            cur/

Filename format:
    <timestamp>.<pid>.<sequence>.<hostname>.eml
"""
import hashlib
import itertools
import os
import socket
import threading
import time
from pathlib import Path
from mailsys.common.logger import get_logger
from mailsys.config.settings import settings

logger = get_logger(__name__)

_counter = itertools.count()
_locks: dict[str, threading.RLock] = {}
_locks_meta = threading.Lock()


def _get_lock(username: str) -> threading.RLock:
    """Return the threading.RLock for the given user, creating it if needed."""
    uname = username.strip().lower()
    with _locks_meta:
        if uname not in _locks:
            _locks[uname] = threading.RLock()
        return _locks[uname]



def _make_filename() -> str:
    """Generate a unique filename for an incoming message."""
    ts = time.time()
    pid = os.getpid()
    seq = next(_counter)
    host = socket.gethostname()
    return f"{ts:.6f}.{pid}.{seq}.{host}.eml"


def ensure_mailbox(username: str) -> Path:
    """Create the Maildir folder structure for a user if it does not exist.

    Args:
        username: Target user account.

    Returns:
        Path: The mailbox root directory path.
    """
    uname = username.strip().lower()
    root = settings.mailboxes_dir / uname
    (root / "new").mkdir(parents=True, exist_ok=True)
    (root / "cur").mkdir(parents=True, exist_ok=True)
    (root / "Spam" / "new").mkdir(parents=True, exist_ok=True)
    (root / "Spam" / "cur").mkdir(parents=True, exist_ok=True)
    return root


def deliver(username: str, raw_message: bytes, spam: bool = False) -> Path:
    """Deliver a raw .eml message to the user's new/ (or Spam/new/) folder.

    Thread-safe.

    Args:
        username: Target user account.
        raw_message: Raw RFC 2822 bytes of the message.
        spam: If True, deliver to Spam/new/; otherwise new/.

    Returns:
        Path: The Path of the stored file.
    """
    uname = username.strip().lower()
    with _get_lock(uname):
        root = ensure_mailbox(uname)
        target_dir = (root / "Spam" / "new") if spam else (root / "new")
        target_dir.mkdir(parents=True, exist_ok=True)

        filename = _make_filename()
        filepath = target_dir / filename
        filepath.write_bytes(raw_message)

        logger.debug(
            "Delivered %d bytes for '%s' to %s (spam=%s)",
            len(raw_message),
            uname,
            filepath,
            spam,
        )
        return filepath


def list_messages(username: str) -> list[tuple[int, Path, int]]:
    """Return a list of (1-based-index, filepath, size_in_bytes) for messages.

    Scans new/ and cur/ (excluding Spam/), sorted by filename (oldest first).

    Args:
        username: Target user account.

    Returns:
        list[tuple[int, Path, int]]: List of (index, path, size) tuples.
    """
    uname = username.strip().lower()
    with _get_lock(uname):
        root = ensure_mailbox(uname)
        files: list[Path] = []
        for folder_name in ("new", "cur"):
            folder = root / folder_name
            if folder.is_dir():
                for entry in folder.iterdir():
                    if entry.is_file() and entry.name.endswith(".eml"):
                        files.append(entry)

        sorted_files = sorted(files, key=lambda f: f.name)
        return [
            (idx, f, f.stat().st_size) for idx, f in enumerate(sorted_files, 1)
        ]


def read_message(username: str, index: int) -> bytes:
    """Return raw bytes of the message at the given 1-based index.

    Args:
        username: Target user account.
        index: 1-based message index from list_messages().

    Returns:
        bytes: Raw message content.

    Raises:
        IndexError: If index is out of range.
    """
    messages = list_messages(username)
    if index < 1 or index > len(messages):
        raise IndexError(
            f"Message index {index} out of range (1..{len(messages)})"
        )
    _, path, _ = messages[index - 1]
    return path.read_bytes()


def delete_message(username: str, index: int) -> None:
    """Permanently delete the message at the given 1-based index.

    Thread-safe.

    Args:
        username: Target user account.
        index: 1-based message index.

    Raises:
        IndexError: If index is out of range.
    """
    uname = username.strip().lower()
    with _get_lock(uname):
        messages = list_messages(uname)
        if index < 1 or index > len(messages):
            raise IndexError(
                f"Message index {index} out of range (1..{len(messages)})"
            )
        _, path, _ = messages[index - 1]
        if path.exists():
            path.unlink()
            logger.debug("Deleted message at index %d (%s)", index, path)


def generate_uid(filepath: Path) -> str:
    """Return a stable UID string for a message file.

    Computed as the MD5 hex digest of the filename (basename only).

    Args:
        filepath: Message file path.

    Returns:
        str: MD5 hex digest of the basename.
    """
    return hashlib.md5(filepath.name.encode("utf-8")).hexdigest()

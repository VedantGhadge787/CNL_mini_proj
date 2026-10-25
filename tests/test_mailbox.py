"""
tests.test_mailbox
==================
Unit tests for mailbox file storage and user authentication.
"""
import threading
from pathlib import Path
import pytest
from mailsys.auth.user_manager import create_user, verify_password, user_exists
from mailsys.storage.mailbox import (
    deliver,
    list_messages,
    read_message,
    delete_message,
    generate_uid,
    ensure_mailbox,
)


def test_user_creation_and_auth(isolated_data_dir: Path) -> None:
    """Verify user creation, password verification, and duplicate rejection."""
    assert not user_exists("alice")
    create_user("alice", "secret123")
    assert user_exists("alice")
    assert verify_password("alice", "secret123")
    assert not verify_password("alice", "wrongpass")
    assert not verify_password("bob", "secret123")

    with pytest.raises(ValueError):
        create_user("alice", "anotherpass")


def test_deliver_creates_file(isolated_data_dir: Path) -> None:
    """Verify that delivering a message creates an .eml file in new/."""
    create_user("user1", "pass")
    raw = b"Subject: Hello\r\n\r\nWorld"
    file_path = deliver("user1", raw)
    assert file_path.exists()
    assert file_path.name.endswith(".eml")
    assert "new" in file_path.parts
    assert file_path.read_bytes() == raw


def test_deliver_spam_folder(isolated_data_dir: Path) -> None:
    """Verify delivering with spam=True writes to Spam/new/."""
    create_user("spammer", "pass")
    raw = b"Subject: Spam message\r\n\r\nBuy now"
    file_path = deliver("spammer", raw, spam=True)
    assert file_path.exists()
    assert "Spam" in file_path.parts
    assert "new" in file_path.parts


def test_list_messages_empty(isolated_data_dir: Path) -> None:
    """Verify list_messages returns empty list for an empty mailbox."""
    create_user("user_empty", "pass")
    assert list_messages("user_empty") == []


def test_list_messages_after_deliver(isolated_data_dir: Path) -> None:
    """Verify list_messages returns delivered messages sorted oldest first."""
    create_user("user2", "pass")
    deliver("user2", b"Msg 1")
    deliver("user2", b"Msg 2")
    msgs = list_messages("user2")
    assert len(msgs) == 2
    assert msgs[0][0] == 1
    assert msgs[1][0] == 2
    assert msgs[0][2] == len(b"Msg 1")
    assert msgs[1][2] == len(b"Msg 2")


def test_read_message_correct_bytes(isolated_data_dir: Path) -> None:
    """Verify reading a message returns the exact delivered bytes."""
    create_user("user3", "pass")
    deliver("user3", b"Exact content 123")
    data = read_message("user3", 1)
    assert data == b"Exact content 123"


def test_read_message_out_of_range(isolated_data_dir: Path) -> None:
    """Verify read_message raises IndexError when index is out of bounds."""
    create_user("user4", "pass")
    with pytest.raises(IndexError):
        read_message("user4", 1)


def test_delete_message_removes_file(isolated_data_dir: Path) -> None:
    """Verify delete_message permanently deletes the specified file."""
    create_user("user5", "pass")
    path = deliver("user5", b"To be deleted")
    assert path.exists()
    assert len(list_messages("user5")) == 1

    delete_message("user5", 1)
    assert not path.exists()
    assert len(list_messages("user5")) == 0


def test_delete_out_of_range_raises(isolated_data_dir: Path) -> None:
    """Verify delete_message raises IndexError for non-existent message index."""
    create_user("user6", "pass")
    with pytest.raises(IndexError):
        delete_message("user6", 99)


def test_generate_uid_stable() -> None:
    """Verify generate_uid produces consistent MD5 hash for the same filename."""
    p1 = Path("/some/path/12345.6789.eml")
    p2 = Path("/other/folder/12345.6789.eml")
    assert generate_uid(p1) == generate_uid(p2)
    assert len(generate_uid(p1)) == 32


def test_concurrent_deliver_no_corruption(isolated_data_dir: Path) -> None:
    """Verify concurrent deliveries from multiple threads succeed without corruption."""
    create_user("ctest", "pass")
    n = 10
    errors: list[Exception] = []

    def deliver_one(i: int) -> None:
        try:
            deliver("ctest", f"Subject: msg {i}\r\n\r\nBody {i}".encode("utf-8"))
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=deliver_one, args=(i,)) for i in range(n)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors, f"Errors during concurrent deliver: {errors}"
    msgs = list_messages("ctest")
    assert len(msgs) == n

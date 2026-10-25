"""
tests.test_spam_filter
======================
Unit tests for keyword-based spam scoring and thresholding.
"""
from __future__ import annotations

import socket
import threading
from pathlib import Path

import pytest

from mailsys.auth.user_manager import create_user
from mailsys.config.settings import settings
from mailsys.mime.message_builder import build_message, parse_message
from mailsys.smtp.session import SMTPSession
from mailsys.spam.filter import SpamFilter, spam_filter
from mailsys.storage.mailbox import list_messages, read_message


def _make_session_pair() -> tuple[socket.socket, SMTPSession, threading.Thread]:
    """Return (client_sock, session, thread) running SMTPSession.handle()."""
    client, server = socket.socketpair()
    session = SMTPSession(server, ("127.0.0.1", 25250))
    t = threading.Thread(target=session.handle, daemon=True)
    t.start()
    return client, session, t


def test_clean_message_zero_score() -> None:
    """Verify normal email without spam keywords scores 0 and is not flagged."""
    raw = build_message(
        from_addr="alice@localhost",
        to_addrs=["bob@localhost"],
        subject="Project Progress Meeting",
        body_text="Hi Bob,\nLet's meet tomorrow at 10 AM to discuss the roadmap.\nRegards, Alice",
    )
    score, is_spam = spam_filter.score_message(raw)
    assert score == 0
    assert is_spam is False


def test_keyword_matching_case_insensitive() -> None:
    """Verify keyword matching is case-insensitive."""
    raw = build_message(
        from_addr="spammer@example.com",
        to_addrs=["bob@localhost"],
        subject="FREE MONEY available now",
        body_text="CLICK HERE to get your reward! This is guaranteed.",
    )
    # Keywords in keywords.txt: 'free money', 'click here', 'guaranteed'
    score, is_spam = spam_filter.score_message(raw)
    assert score == 3
    assert is_spam is False  # threshold is 5


def test_score_above_threshold_flags_spam() -> None:
    """Verify messages reaching or exceeding threshold are flagged as spam."""
    # 4 keywords: score 4 (< 5 -> False)
    msg_4 = build_message(
        from_addr="spammer@example.com",
        to_addrs=["bob@localhost"],
        subject="Winner announcement",
        body_text="Click here to claim your prize! Limited time offer.",
    )
    score, is_spam = spam_filter.score_message(msg_4)
    assert score == 4
    assert is_spam is False

    # 5 keywords: score 5 (>= 5 -> True)
    msg_5 = build_message(
        from_addr="spammer@example.com",
        to_addrs=["bob@localhost"],
        subject="Winner announcement",
        body_text="Click here to claim your prize! Limited time offer. Free money!",
    )
    score, is_spam = spam_filter.score_message(msg_5)
    assert score == 5
    assert is_spam is True

    # 6 keywords: score 6 (>= 5 -> True)
    msg_6 = build_message(
        from_addr="spammer@example.com",
        to_addrs=["bob@localhost"],
        subject="Winner announcement",
        body_text="Click here to claim your prize! Limited time offer. Free money guaranteed!",
    )
    score, is_spam = spam_filter.score_message(msg_6)
    assert score == 6
    assert is_spam is True


def test_custom_keywords_file(tmp_path: Path) -> None:
    """Verify SpamFilter can load custom keywords from a file."""
    kw_file = tmp_path / "custom_keywords.txt"
    kw_file.write_text(
        "# Custom spam rules\n"
        "crypto giveaway\n"
        "double your investment\n"
        "wire transfer\n",
        encoding="utf-8",
    )

    custom_filter = SpamFilter(keywords_path=kw_file, threshold=2)
    assert len(custom_filter.keywords) == 3
    assert "crypto giveaway" in custom_filter.keywords

    raw = build_message(
        from_addr="scam@crypto.io",
        to_addrs=["bob@localhost"],
        subject="Exclusive crypto giveaway!",
        body_text="Wire transfer your funds to double your investment today.",
    )
    score, is_spam = custom_filter.score_message(raw)
    assert score == 3
    assert is_spam is True


def test_reload_keywords(tmp_path: Path) -> None:
    """Verify reload() updates active keyword rules without restarting."""
    kw_file = tmp_path / "dynamic_keywords.txt"
    kw_file.write_text("initial keyword\n", encoding="utf-8")

    filter_instance = SpamFilter(keywords_path=kw_file, threshold=2)
    assert filter_instance.keywords == ["initial keyword"]

    raw = build_message(
        from_addr="promo@shop.com",
        to_addrs=["bob@localhost"],
        subject="Flash discount sale",
        body_text="Use this coupon code for a big discount.",
    )
    score, is_spam = filter_instance.score_message(raw)
    assert score == 0

    # Add new keyword and reload
    kw_file.write_text("initial keyword\nflash discount\n", encoding="utf-8")
    filter_instance.reload()
    assert len(filter_instance.keywords) == 2

    score_after, is_spam_after = filter_instance.score_message(raw)
    assert score_after == 1


def test_smtp_delivery_spam_routing(isolated_data_dir: Path) -> None:
    """Verify spam emails are routed to Spam/new/ with X-Spam-Flag: YES."""
    create_user("charlie", "password123")
    client, _, _ = _make_session_pair()
    client.recv(1024)  # 220
    client.sendall(b"HELO client.test\r\n")
    client.recv(1024)  # 250
    client.sendall(b"MAIL FROM:<spammer@example.com>\r\n")
    client.recv(1024)  # 250
    client.sendall(b"RCPT TO:<charlie@localhost>\r\n")
    client.recv(1024)  # 250
    client.sendall(b"DATA\r\n")
    client.recv(1024)  # 354

    spam_content = (
        b"From: spammer@example.com\r\n"
        b"To: charlie@localhost\r\n"
        b"Subject: Winner! Free money click here\r\n"
        b"\r\n"
        b"You have been selected! Claim your prize now.\r\n"
        b"Guaranteed 100% free with no risk.\r\n"
        b".\r\n"
    )
    client.sendall(spam_content)
    reply = client.recv(1024)
    assert reply.startswith(b"250")
    client.sendall(b"QUIT\r\n")
    assert client.recv(1024).startswith(b"221")
    client.close()

    # Normal inbox should be empty
    inbox_msgs = list_messages("charlie")
    assert len(inbox_msgs) == 0

    # Check Spam/new folder
    spam_dir = settings.mailboxes_dir / "charlie" / "Spam" / "new"
    spam_files = list(spam_dir.glob("*.eml"))
    assert len(spam_files) == 1

    content = spam_files[0].read_bytes()
    parsed = parse_message(content)
    assert parsed["X-Spam-Flag"] == "YES"
    assert int(parsed["X-Spam-Score"]) >= 5


def test_smtp_delivery_ham_routing(isolated_data_dir: Path) -> None:
    """Verify legitimate emails are routed to new/ with X-Spam-Flag: NO."""
    create_user("dana", "password123")
    client, _, _ = _make_session_pair()
    client.recv(1024)  # 220
    client.sendall(b"HELO client.test\r\n")
    client.recv(1024)  # 250
    client.sendall(b"MAIL FROM:<colleague@example.com>\r\n")
    client.recv(1024)  # 250
    client.sendall(b"RCPT TO:<dana@localhost>\r\n")
    client.recv(1024)  # 250
    client.sendall(b"DATA\r\n")
    client.recv(1024)  # 354

    ham_content = (
        b"From: colleague@example.com\r\n"
        b"To: dana@localhost\r\n"
        b"Subject: Team Lunch Tomorrow\r\n"
        b"\r\n"
        b"Hey Dana, let's grab tacos tomorrow at noon.\r\n"
        b".\r\n"
    )
    client.sendall(ham_content)
    reply = client.recv(1024)
    assert reply.startswith(b"250")
    client.sendall(b"QUIT\r\n")
    assert client.recv(1024).startswith(b"221")
    client.close()

    # Normal inbox should contain the message
    inbox_msgs = list_messages("dana")
    assert len(inbox_msgs) == 1

    content = read_message("dana", 1)
    parsed = parse_message(content)
    assert parsed["X-Spam-Flag"] == "NO"
    assert parsed["X-Spam-Score"] == "0"

"""
mailsys.smtp.relay
==================
Outbound MX resolution and mail relaying.

Provides:
  - DNS MX record lookup sorted by priority via dnspython.
  - SMTP relaying of outgoing messages to external MX servers.
  - Generation and delivery of bounce notifications on relay failures.
"""
import smtplib

import dns.exception
import dns.resolver
from mailsys.auth.user_manager import user_exists
from mailsys.common.logger import get_logger
from mailsys.config.settings import settings
from mailsys.mime.message_builder import build_message
from mailsys.storage.mailbox import deliver

logger = get_logger(__name__)


def lookup_mx(domain: str) -> list[str]:
    """Return MX hostnames sorted by preference (lowest preference first).

    Args:
        domain: Target recipient domain (e.g. 'example.com').

    """
    normalized_domain = domain.strip().rstrip(".")
    if not normalized_domain:
        return []
    try:
        answers = dns.resolver.resolve(normalized_domain, "MX")
    except dns.exception.DNSException as error:
        logger.warning("MX lookup failed for %s: %s", normalized_domain, error)
        return []

    records = sorted(answers, key=lambda record: record.preference)
    return [str(record.exchange).rstrip(".") for record in records]


def relay_message(recipient: str, raw_bytes: bytes, sender: str = "") -> bool:
    """Deliver raw_bytes to recipient via DNS MX lookup + outbound SMTP connection.

    Args:
        recipient: Target recipient email address.
        raw_bytes: Raw RFC 2822 bytes of the email message.
        sender: Original sender address for envelope MAIL FROM.

    Returns:
        bool: True if relayed successfully to at least one MX, False otherwise.

    """
    local_part, separator, domain = recipient.rpartition("@")
    if not separator or not local_part or not domain:
        logger.error("Invalid relay recipient address: %s", recipient)
        _send_bounce(sender, recipient, "Invalid recipient address")
        return False

    mx_hosts = lookup_mx(domain)
    if not mx_hosts:
        logger.error(
            "No MX records found for %s; cannot relay to %s", domain, recipient
        )
        _send_bounce(sender, recipient, "No MX records found")
        return False

    envelope_sender = sender or f"postmaster@{settings.local_domain}"
    for host in mx_hosts:
        try:
            logger.info("Relaying to %s via %s", recipient, host)
            with smtplib.SMTP(host, 25, timeout=30) as smtp:
                refused = smtp.sendmail(envelope_sender, [recipient], raw_bytes)
            if refused:
                logger.warning(
                    "Relay attempt to %s refused recipient %s: %s",
                    host,
                    ", ".join(refused),
                    refused,
                )
                continue
            logger.info("Relay successful: %s -> %s via %s", sender, recipient, host)
            return True
        except (smtplib.SMTPException, OSError) as error:
            logger.warning("Relay attempt to %s failed: %s", host, error)

    logger.error("All relay attempts failed for %s", recipient)
    _send_bounce(sender, recipient, "All MX hosts failed")
    return False


def _send_bounce(sender: str, recipient: str, reason: str = "Delivery failed") -> None:
    """Generate and deliver a bounce message if sender is a known local user."""
    local_part, separator, domain = sender.rpartition("@")
    if (
        not separator
        or not local_part
        or domain.lower() != settings.local_domain.lower()
    ):
        logger.info("Bounce skipped (sender is not local): %s", sender)
        return
    if not user_exists(local_part):
        logger.warning("Bounce skipped; local sender user not found: %s", local_part)
        return

    bounce_body = (
        f"Your message to <{recipient}> could not be delivered.\n\n"
        f"Reason: {reason}\n\n"
        "This is an automatically generated message from the mail system."
    )
    bounce_bytes = build_message(
        from_addr=f"mailer-daemon@{settings.local_domain}",
        to_addrs=[sender],
        subject=f"Delivery failure: {recipient}",
        body_text=bounce_body,
    )
    try:
        deliver(local_part, bounce_bytes, spam=False)
    except OSError:
        logger.exception("Failed to deliver bounce to local user %s", local_part)
        return
    logger.info("Bounce delivered to %s", local_part)

# Step 08 — MX Lookup & Relay

**Status:** [ ] not started

---

## 1. Objective

When this step is done:
- `smtp/relay.py` resolves MX records for a domain using `dnspython`, sorts by priority, and delivers mail to the highest-priority MX host using `smtplib`.
- Failed delivery attempts are logged with the error detail; a bounce message is delivered to the sender's local mailbox if all MX attempts fail.

---

## 2. Prerequisites

- Step 04 done: SMTP session with routing stub in `_deliver_or_relay`.
- Step 03 done: `mailbox.deliver` for bounce delivery.

---

## 3. Files to Create or Modify

| Action | Path |
|--------|------|
| Implement | `src/mailsys/smtp/relay.py` |
| Update | `src/mailsys/smtp/session.py` (wire in real relay call) |
| Update tests | (manual; no automated test for external DNS in unit tests) |

---

## 4. Detailed Implementation Instructions

### 4.1 `smtp/relay.py`

```python
import smtplib
import dns.resolver
import dns.exception
from mailsys.config.settings import settings
from mailsys.common.logger import get_logger
from mailsys.mime.message_builder import parse_message, build_message

logger = get_logger(__name__)

def lookup_mx(domain: str) -> list[str]:
    """Return a list of MX hostnames for the domain, sorted by priority (lowest = highest priority).

    Returns an empty list if DNS resolution fails or no MX records exist.
    """
    try:
        answers = dns.resolver.resolve(domain, "MX")
        sorted_records = sorted(answers, key=lambda r: r.preference)
        return [str(r.exchange).rstrip(".") for r in sorted_records]
    except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer,
            dns.resolver.NoNameservers, dns.exception.Timeout) as e:
        logger.warning("MX lookup failed for %s: %s", domain, e)
        return []


def relay_message(recipient: str, raw_bytes: bytes, sender: str = "") -> bool:
    """Deliver raw_bytes to recipient via DNS MX lookup + outbound SMTP.

    Tries each MX host in order. Returns True on first success.
    If all fail, calls _send_bounce(sender, recipient) and returns False.
    """
    _, _, domain = recipient.partition("@")
    mx_hosts = lookup_mx(domain)

    if not mx_hosts:
        logger.error("No MX records found for domain %s; cannot relay to %s", domain, recipient)
        _send_bounce(sender, recipient, "No MX records found")
        return False

    for host in mx_hosts:
        try:
            logger.info("Relaying to %s via %s", recipient, host)
            with smtplib.SMTP(host, 25, timeout=30) as smtp:
                smtp.sendmail(sender or f"postmaster@{settings.local_domain}",
                              [recipient], raw_bytes)
            logger.info("Relay successful: %s -> %s via %s", sender, recipient, host)
            return True
        except smtplib.SMTPException as e:
            logger.warning("Relay attempt to %s failed: %s", host, e)
        except OSError as e:
            logger.warning("Connection to %s failed: %s", host, e)

    logger.error("All relay attempts failed for %s", recipient)
    _send_bounce(sender, recipient, "All MX hosts failed")
    return False


def _send_bounce(sender: str, failed_recipient: str, reason: str) -> None:
    """Deliver a bounce (non-delivery report) to the original sender's local mailbox.

    Only bounces to local senders (those on settings.local_domain).
    """
    from mailsys.storage import mailbox
    from mailsys.auth.user_manager import user_exists

    if not sender or not sender.endswith(f"@{settings.local_domain}"):
        logger.info("Bounce skipped (sender not local): %s", sender)
        return

    local_user = sender.split("@")[0]
    if not user_exists(local_user):
        logger.warning("Bounce: local sender user not found: %s", local_user)
        return

    bounce_body = (
        f"Your message to <{failed_recipient}> could not be delivered.\n\n"
        f"Reason: {reason}\n\n"
        "This is an automatically generated message from the mail system."
    )
    bounce_bytes = build_message(
        from_addr=f"mailer-daemon@{settings.local_domain}",
        to_addrs=[sender],
        subject=f"Delivery failure: {failed_recipient}",
        body_text=bounce_body,
    )
    mailbox.deliver(local_user, bounce_bytes, spam=False)
    logger.info("Bounce delivered to %s", local_user)
```

### 4.2 Wiring into `smtp/session.py`

In `_deliver_or_relay`, replace the relay stub:

```python
from mailsys.smtp.relay import relay_message

# For non-local recipients:
relay_message(recipient, annotated_bytes, sender=self.mail_from or "")
```

### 4.3 Edge cases to handle

| Scenario | Handling |
|----------|----------|
| Domain has no MX record | `lookup_mx` catches `NoAnswer`; `relay_message` sends bounce |
| Domain does not exist | `dns.resolver.NXDOMAIN` caught; bounce |
| DNS timeout | `dns.exception.Timeout` caught; bounce |
| MX host refuses connection | `OSError` caught; try next MX |
| MX host gives SMTP error | `SMTPException` caught; try next MX |
| Sender is not local | Bounce is skipped (no mailbox to deliver to) |

---

## 5. Acceptance Criteria

- [ ] `lookup_mx("gmail.com")` returns a non-empty list sorted by priority.
- [ ] `lookup_mx("nonexistent-domain-xyz123.com")` returns `[]` without raising.
- [ ] `relay_message` logs success when delivery to a real external SMTP host succeeds.
- [ ] On all-MX-fail, a bounce message appears in the sender's local mailbox.
- [ ] `lookup_mx` handles timeout gracefully.

---

## 6. How to Test

```powershell
# Test MX lookup (requires internet access)
python -c "
from mailsys.smtp.relay import lookup_mx
hosts = lookup_mx('gmail.com')
print('MX for gmail.com:', hosts)
assert len(hosts) > 0

hosts2 = lookup_mx('no-such-domain-xyz.invalid')
print('MX for invalid domain:', hosts2)
assert hosts2 == []
print('MX lookup tests passed')
"

# Test relay (requires internet; send to a real address for full test)
# For offline testing, test the bounce path by using a domain with no MX:
python -c "
from mailsys.smtp.relay import relay_message
result = relay_message('user@no-such-domain-xyz.invalid', b'Subject: Test\r\n\r\ntest', 'alice@localhost')
print('relay result (expected False):', result)
"
```

---

## 7. Wireshark Check

- **Filter:** `tcp.port == 25` (outbound relay)
- **Observe:**
  - TCP connect to MX host on port 25.
  - SMTP handshake: 220 greeting → EHLO → MAIL FROM → RCPT TO → DATA → `.` → QUIT.
  - If MX host is unreachable: TCP RST; retry to next MX.

---

## 8. Log Update

Append to `docs/log.md`:
```
### [YYYY-MM-DD HH:MM] Step 08: MX Lookup & Relay
- Changed: smtp/relay.py (real), smtp/session.py (wired relay)
- Why: FR-7 — non-local mail relay via DNS MX
- Key decisions: smtplib for outbound (client-side allowed); bounce only to local senders
- Interfaces added: lookup_mx(domain) -> list[str], relay_message(rcpt, raw, sender) -> bool
- Tests: manual DNS lookup tests pass
- Next: Step 09 — client UI
```

---

## 9. Definition of Done

`lookup_mx` resolves real domains, relay attempts fail gracefully, bounce is delivered to local sender, tests pass.

# Mini Mail System — Step-by-Step Demo Script

This document provides an exact, reproducible walkthrough to demonstrate all features of the Mini Mail System for live presentations, evaluations, or viva demonstrations. Total estimated demo time: **10–15 minutes**.

---

## 1. Environment & Setup Checklist

Ensure you are in the repository directory `c:\Coding_main\cnl_mini_proj\mini-mail-system`.

### Step 0: Ensure Python Virtual Environment is Active
```powershell
.\.venv\Scripts\activate
```

### Step 1: Start Background Servers
Open two separate terminal tabs/windows (or ensure they are already running):

- **Terminal 1 — SMTP Server:**
  ```powershell
  python scripts/run_smtp.py
  ```
  *Expected Output:* `SMTPServer listening on 0.0.0.0:2525`

- **Terminal 2 — POP3 Server:**
  ```powershell
  python scripts/run_pop3.py
  ```
  *Expected Output:* `POP3Server listening on 0.0.0.0:2110`

### Step 2: (Optional) Wireshark Packet Inspection
1. Launch **Wireshark**.
2. Select the **Adapter for loopback traffic capture** (`Npcap Loopback Adapter`).
3. Set display filter:
   ```
   tcp.port == 2525 or tcp.port == 2110
   ```
4. Start packet capture.

---

## 2. Interactive Feature Walkthrough

### Part A: User Provisioning & Account Creation
Demonstrate provisioning new mailboxes via the command line utility:
```powershell
python scripts/create_user.py alice secret
python scripts/create_user.py bob secret
```
*Key Talking Points:*
- Passwords are salted with 32 random bytes and hashed using `PBKDF2-HMAC-SHA256` (480,000 rounds).
- Stored safely in SQLite `data/mailsys.db`.
- Standard Maildir directory structure is provisioned at `data/mailboxes/<user>/` (`new/`, `cur/`, `tmp/`, `Spam/new/`).

---

### Part B: Desktop Client UI — Sending Mail with Attachment
1. **Launch the desktop GUI:**
   ```powershell
   python scripts/run_client.py
   ```
2. **Log in as Alice:**
   - Username: `alice`
   - Password: `secret`
   - Click **Login**.
   - *Observation:* The client verifies credentials against the POP3 server and displays Alice's inbox.

3. **Compose and Send Email:**
   - Click **Compose**.
   - **To:** `bob@localhost`
   - **Subject:** `Project Report & Assignment`
   - **Body:** `Hi Bob, please find attached the project document.`
   - Click **Add Attachment**, select any text or PDF file (e.g. `README.md` or a sample file).
   - Click **Send**.
   - *Observation:* Status bar shows "Sending message...", popup confirms success, and window closes.
   - *Wireshark Check:* In Wireshark, observe the full SMTP handshake:
     `HELO` -> `250`, `MAIL FROM:<alice@localhost>` -> `250`, `RCPT TO:<bob@localhost>` -> `250`, `DATA` -> `354`, followed by MIME headers and CRLF.CRLF termination -> `250 OK`.

---

### Part C: POP3 Retrieval, Preview & Attachment Download
1. In the client, click **Logout** (returns to login screen).
2. **Log in as Bob:**
   - Username: `bob`
   - Password: `secret`
   - Click **Login**.
3. **Inspect Inbox:**
   - Bob's inbox list shows: `#1 alice@localhost — Project Report & Assignment`.
4. **Read & Extract Attachment:**
   - Click the message in the list.
   - Preview pane loads headers (`From`, `Subject`, `Date`, `Attachments`).
   - Plain-text message body renders in the reader.
   - Click **Save Attachments**, pick any folder, and confirm the attachment is written to disk.

---

### Part D: Keyword-Based Spam Filtering
Demonstrate automatic content analysis and folder isolation:
1. Open a terminal to send a message containing spam trigger words (either via Telnet or Python script):
   ```powershell
   python -c "import smtplib; from mailsys.mime.message_builder import build_message; raw = build_message('alice@localhost', ['bob@localhost'], 'Winner announcement', 'Click here to claim your prize! Limited time offer. Free money! Act now!'); smtplib.SMTP('localhost', 2525).sendmail('alice@localhost', ['bob@localhost'], raw)"
   ```
2. **Observe Filtering Behavior:**
   - In Bob's client, click **Refresh**. Notice the message **does not** appear in Bob's regular inbox.
   - Inspect the disk directory:
     ```powershell
     dir data\mailboxes\bob\Spam\new\
     ```
   - Open the `.eml` file inside `data\mailboxes\bob\Spam\new\`:
     Observe the injected headers:
     ```
     X-Spam-Flag: YES
     X-Spam-Score: 5
     ```

---

### Part E: POP3 Deletion & UPDATE State Semantics
1. Back in Bob's client, select the first legitimate message (`#1`).
2. Click **Delete**. Confirm the prompt.
3. *Observation:* The message disappears from the inbox list.
4. Check the file system: `data\mailboxes\bob\new/` is now empty.
5. *Talking Point:* Explain that in POP3, messages are only marked for deletion during `TRANSACTION` state and are permanently purged only when `QUIT` completes the `UPDATE` state.

---

### Part F: Automated Test Suite & Concurrency Validation
Show project code quality and test coverage:
```powershell
pytest tests/ -v
```
*Expected Result:*
- **75 passed tests** spanning config, authentication, mailbox storage, MIME encoding/decoding, POP3 session state machine, SMTP session state machine, spam filtering, MX relay, client UI, and end-to-end flows.
- Concurrency test proves 10 simultaneous threads deliver mail without data corruption or lock collisions.

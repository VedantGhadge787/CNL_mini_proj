# Mini Mail System — High-Level Study Guide

Welcome! If you want to understand how email works under the hood and what this project actually does without getting bogged down in complex jargon, this guide is for you.

---

## 1. The Real-World Analogy: How Email Works

Think of email exactly like the traditional physical postal service:

| Real-World Postal Concept | Email System Equivalent | What It Does In This Project |
|---|---|---|
| **The Mail Drop Box & Delivery Truck** | **SMTP Server** (`port 2525`) | Accepts letters from people and delivers them to the correct destination. |
| **Your Personal P.O. Box** | **Maildir Mailbox** (`data/mailboxes/`) | The physical storage box where unread letters sit waiting for you. |
| **Your P.O. Box Key & ID Card** | **POP3 Server** (`port 2110`) | Allows you to unlock your mailbox, see what letters arrived, and take them home. |
| **The Junk Mail Sorter** | **Spam Filter** | Checks letters for sketchy words (like "free cash!"). If it looks like junk, puts it in a separate Spam bin. |
| **Routing Mail to Another City** | **DNS MX Relay** | If a letter is addressed to another city (like `@gmail.com`), finds their post office address and forwards it there. |
| **The Letter & Enclosed Photos** | **MIME & Attachments** | Allows a letter to include plain text plus attached files, photos, or documents. |
| **Your Smartphone / Computer App** | **Desktop Client (GUI)** | The visual screen where you type messages, click "Send", and read incoming mail. |

---

## 2. The Golden Rule of Email: Push vs. Pull

One of the most important concepts to remember is why email requires **two different servers**:

```
[ Alice (Sender) ]
       |
       |  (1) PUSH (SMTP)
       v
[ SMTP Server ] ------> Saves into ------> [ Bob's Mailbox (Storage) ]
                                                        |
                                                        |  (2) PULL (POP3)
                                                        v
                                                [ Bob (Receiver) ]
```

1. **SMTP is a PUSH protocol:** When you send an email, your computer *pushes* the message out to the SMTP server. The SMTP server accepts it and stores it in the recipient's mailbox.
2. **POP3 is a PULL protocol:** The recipient is not always sitting at their computer. So the mail waits on the server. When the recipient opens their email app, the app *pulls* the messages down using POP3.

---

## 3. A Day in the Life of an Email (Step-by-Step)

Here is exactly what happens when **Alice** sends an email with an attachment to **Bob**:

### Step 1: Alice Composes the Email
- Alice opens the GUI (`run_client.py`), types `bob@localhost`, writes `"Hi Bob!"`, and attaches a file.
- The app bundles the text and the file into a standardized format called **MIME** (it encodes the file into text blocks so it can travel safely over the network).

### Step 2: The Handshake with the SMTP Server
Alice's client connects to the SMTP server (`localhost:2525`) over a raw network socket. They have a polite, step-by-step conversation:
- **Server:** *"220 Mini Mail SMTP ready"* (Hello! I am ready.)
- **Alice:** *"HELO client"* (Nice to meet you.)
- **Server:** *"250 OK"* (Welcome.)
- **Alice:** *"MAIL FROM: <alice@localhost>"* (I am sending a letter from Alice.)
- **Server:** *"250 OK"* (Got it.)
- **Alice:** *"RCPT TO: <bob@localhost>"* (This letter is for Bob.)
- **Server:** *"250 OK"* (Bob exists on my system.)
- **Alice:** *"DATA"* (Here comes the actual letter!)
- **Server:** *"354 Start mail input; end with <CRLF>.<CRLF>"* (Go ahead, send the body.)
- **Alice:** *[Transmits message body and attachment, then sends a single dot `.` on an empty line]*
- **Server:** *"250 OK: delivered"* (Saved successfully!)

### Step 3: Spam Check & Disk Storage
Before saving the email, our server scans the text:
- Does it contain 5 or more spam keywords (like "free cash", "winner", "prize")?
  - **If YES:** It tags the letter with `X-Spam-Flag: YES` and drops it into `data/mailboxes/bob/Spam/new/`.
  - **If NO:** It saves it as an individual `.eml` file directly into Bob's regular inbox: `data/mailboxes/bob/new/`.

### Step 4: Bob Checks His Mail (POP3)
- Bob launches the client and logs in as `bob` with password `secret`.
- Bob's app connects to the POP3 server (`localhost:2110`):
  - **App:** *"USER bob"*
  - **Server:** *"+OK bob"*
  - **App:** *"PASS secret"*
  - **Server:** *"+OK logged in, 1 messages"*
  - **App:** *"TOP 1 0"* (Give me the header info for message #1)
  - **Server:** Returns sender, subject, date.
- Bob sees the new email pop up in his inbox list!

### Step 5: Bob Reads the Email & Saves the File
- When Bob clicks the email, the app sends:
  - **App:** *"RETR 1"* (Give me the full email and attachment!)
- The app decodes the attachment and displays the text. Bob clicks **Save Attachments** to save the file to his laptop.

---

## 4. Understanding the Project's Key Components

Here is where each piece lives in the project folder and what it does in simple terms:

| Folder / File | What it is in plain English |
|---|---|
| **`src/mailsys/smtp/`** | The post office sorting facility. Handles incoming connections, understands SMTP commands, checks recipients, and decides whether to store the mail locally or forward it. |
| **`src/mailsys/pop3/`** | The front desk clerk at the post office. Validates user passwords, lets users look at their unread mail, and hands over messages when requested. |
| **`src/mailsys/storage/`** | The physical file cabinet (`Maildir`). Saves each email as its own file on disk. Manages locks so two actions don't collide. |
| **`src/mailsys/auth/`** | The security guard. Manages user accounts and hashes passwords using PBKDF2 so real passwords are never stored in plain text. |
| **`src/mailsys/spam/`** | The spam filter. Compares text against `keywords.txt` and calculates a score. |
| **`src/mailsys/mime/`** | The package packer and unpacker. Packs text and binary files (PDFs, images) into emails, and extracts them back out. |
| **`src/mailsys/client/`** | The desktop user interface (Tkinter app) that makes it easy for a human to log in, write, and read emails. |
| **`scripts/`** | Simple command-line tools to start the SMTP server, start the POP3 server, create users, or launch the desktop GUI. |

---

## 5. Frequently Asked Conceptual Questions

### Q: Why did we build this from raw sockets instead of using an existing library?
**A:** Most software uses pre-made libraries that hide everything behind a single function call like `send()`. By writing raw socket loops and command parsers, we understand:
- How bytes travel across TCP connections.
- How state machines work (waiting for HELO before accepting MAIL FROM).
- How network protocols maintain safety, synchronization, and error handling.

### Q: What is a "Socket"?
**A:** A socket is simply an endpoint for network communication. Think of it like a phone call: the server dials up and listens on a specific phone number (Port 2525), and the client picks up the receiver to speak and listen in ASCII text.

### Q: What is "Dot-Stuffing"?
**A:** In SMTP, the sender tells the server "I am done typing" by sending a single dot `.` on its own line. But what if your email has a sentence like:
```
Here is my list:
.
That was item one.
```
If the server sees that dot, it would stop reading right there! To prevent this, the client automatically adds an extra dot (`..`), and the receiving server strips it back off. That is called **dot-stuffing**.

### Q: What is the "UPDATE" state in POP3?
**A:** When you delete an email in your app, POP3 does **not** instantly delete the file from disk. It only marks it with a sticky note saying "to be deleted". Only when you exit cleanly (`QUIT`) does the server actually delete the files. If your internet disconnects midway, nothing is lost! That is the UPDATE state.

---

## 6. Summary: What You Accomplished

By completing this project, you have built:
1. A fully functioning, RFC-compliant **SMTP Server**.
2. A fully functioning, RFC-compliant **POP3 Server**.
3. A safe, crash-proof **Maildir Storage Engine**.
4. An intelligent **Keyword Spam Detector**.
5. An automated **DNS MX Router & Relay**.
6. A responsive, multi-threaded **Desktop GUI Application**.
7. A complete test suite with **75 automated tests**.

"""
mailsys.client.app
==================
Simple desktop email client built with Python's standard `tkinter`.

Features:
  - Login view: username, password, connects to POP3/SMTP.
  - Inbox pane: Listbox displaying received emails with sender, subject, date.
  - Message preview pane: Displays headers and body text.
  - Compose window: To, Subject, Body, and file attachment selection.
  - Multi-threading: Network I/O runs in background threads; UI updates on main thread.
"""
from __future__ import annotations

import threading
import tkinter as tk
from email.message import EmailMessage
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from mailsys.client.mail_client import MailClient
from mailsys.common.logger import get_logger
from mailsys.config.settings import settings
from mailsys.mime.message_builder import (
    extract_attachments,
    get_text_body,
    list_attachments,
    parse_message,
)

logger = get_logger(__name__)


class ComposeWindow(tk.Toplevel):
    """Dialog window for composing and sending an email message."""

    def __init__(
        self,
        parent: tk.Misc,
        client: MailClient,
        on_sent_callback: callable | None = None,
    ) -> None:
        """Initialize compose window.

        Args:
            parent: Parent tkinter widget.
            client: Authenticated MailClient instance.
            on_sent_callback: Optional callable invoked after successful send.
        """
        super().__init__(parent)
        self.client = client
        self.on_sent_callback = on_sent_callback
        self.attachments: list[Path] = []

        self.title("Compose Message")
        self.geometry("640x520")
        self.minsize(500, 400)
        self.transient(parent)

        self._build_ui()

    def _build_ui(self) -> None:
        """Construct the compose window layout."""
        pad = {"padx": 10, "pady": 4}
        header_frame = ttk.Frame(self)
        header_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(header_frame, text="To:").grid(row=0, column=0, sticky=tk.W, **pad)
        self.to_entry = ttk.Entry(header_frame, width=50)
        self.to_entry.grid(row=0, column=1, sticky=tk.EW, **pad)

        ttk.Label(header_frame, text="Subject:").grid(
            row=1, column=0, sticky=tk.W, **pad
        )
        self.subject_entry = ttk.Entry(header_frame, width=50)
        self.subject_entry.grid(row=1, column=1, sticky=tk.EW, **pad)
        header_frame.columnconfigure(1, weight=1)

        self._build_attachment_ui()
        self._build_body_ui()
        self._build_button_ui()

    def _build_attachment_ui(self) -> None:
        """Construct attachment controls and label."""
        att_frame = ttk.Frame(self)
        att_frame.pack(fill=tk.X, padx=10, pady=2)

        ttk.Button(
            att_frame, text="Add Attachment", command=self._add_attachment
        ).pack(side=tk.LEFT)
        ttk.Button(
            att_frame, text="Clear", command=self._clear_attachments
        ).pack(side=tk.LEFT, padx=5)

        self.att_label = ttk.Label(att_frame, text="No attachments")
        self.att_label.pack(side=tk.LEFT, padx=10)

    def _build_body_ui(self) -> None:
        """Construct the message body text area."""
        body_frame = ttk.Frame(self)
        body_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.body_text = tk.Text(body_frame, wrap=tk.WORD, height=12)
        scroll = ttk.Scrollbar(
            body_frame, orient=tk.VERTICAL, command=self.body_text.yview
        )
        self.body_text.configure(yscrollcommand=scroll.set)

        self.body_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)

    def _build_button_ui(self) -> None:
        """Construct send and cancel action buttons."""
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill=tk.X, padx=10, pady=10)

        self.send_btn = ttk.Button(
            btn_frame, text="Send", command=self._on_send_click
        )
        self.send_btn.pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="Cancel", command=self.destroy).pack(
            side=tk.RIGHT
        )

        self.status_label = ttk.Label(btn_frame, text="")
        self.status_label.pack(side=tk.LEFT)

    def _add_attachment(self) -> None:
        """Open file dialog to select attachment files."""
        files = filedialog.askopenfilenames(
            parent=self, title="Select Attachments"
        )
        if not files:
            return
        for file_path in files:
            path = Path(file_path)
            if path not in self.attachments:
                self.attachments.append(path)
        names = ", ".join(p.name for p in self.attachments)
        self.att_label.config(text=names or "No attachments")

    def _clear_attachments(self) -> None:
        """Clear all selected attachments."""
        self.attachments.clear()
        self.att_label.config(text="No attachments")

    def _on_send_click(self) -> None:
        """Validate inputs and launch background worker to send email."""
        raw_to = self.to_entry.get().strip()
        recipients = [r.strip() for r in raw_to.split(",") if r.strip()]
        if not recipients:
            messagebox.showerror(
                "Error", "Please specify at least one recipient.", parent=self
            )
            return

        subject = self.subject_entry.get().strip()
        body = self.body_text.get("1.0", tk.END).rstrip()
        self.send_btn.config(state="disabled")
        self.status_label.config(text="Sending message...")

        thread = threading.Thread(
            target=self._send_worker,
            args=(recipients, subject, body),
            daemon=True,
        )
        thread.start()

    def _send_worker(
        self, recipients: list[str], subject: str, body: str
    ) -> None:
        """Execute SMTP send in a background thread."""
        try:
            self.client.send_message(
                to_addrs=recipients,
                subject=subject,
                body=body,
                attachments=self.attachments if self.attachments else None,
            )
            self.after(0, self._on_send_success)
        except Exception as err:
            logger.warning("Failed to send message: %s", err, exc_info=True)
            self.after(0, self._on_send_failure, str(err))

    def _on_send_success(self) -> None:
        """Handle successful message send on the main thread."""
        messagebox.showinfo(
            "Success", "Message sent successfully!", parent=self
        )
        if self.on_sent_callback:
            self.on_sent_callback()
        self.destroy()

    def _on_send_failure(self, err_msg: str) -> None:
        """Handle send failure on the main thread."""
        self.send_btn.config(state="normal")
        self.status_label.config(text="")
        messagebox.showerror(
            "Send Error", f"Failed to send email:\n{err_msg}", parent=self
        )


class MailApp:
    """Tkinter desktop email application."""

    def __init__(self, root: tk.Tk) -> None:
        """Initialize the desktop mail client application.

        Args:
            root: Root Tk window.
        """
        self.root = root
        self.root.title("Mini Mail Client")
        self.root.geometry("900x650")
        self.root.minsize(750, 500)

        self.client: MailClient | None = None
        self._messages: list[dict] = []
        self._current_msg_index: int | None = None
        self._current_parsed_msg: EmailMessage | None = None

        self.login_frame: ttk.Frame | None = None
        self.main_frame: ttk.Frame | None = None

        self.show_login()

    def run(self) -> None:
        """Start the Tkinter event loop."""
        self.root.mainloop()

    def show_login(self) -> None:
        """Render the login form and hide the main interface."""
        if self.main_frame:
            self.main_frame.destroy()
            self.main_frame = None

        self._build_login_ui()

    def _build_login_ui(self) -> None:
        """Construct the login widgets."""
        self.login_frame = ttk.Frame(self.root, padding=30)
        self.login_frame.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

        title_lbl = ttk.Label(
            self.login_frame,
            text="Mini Mail Client",
            font=("Segoe UI", 16, "bold"),
        )
        title_lbl.grid(row=0, column=0, columnspan=2, pady=(0, 20))

        ttk.Label(self.login_frame, text="Username:").grid(
            row=1, column=0, sticky=tk.W, pady=5
        )
        self.user_entry = ttk.Entry(self.login_frame, width=28)
        self.user_entry.grid(row=1, column=1, pady=5)
        self.user_entry.focus()

        ttk.Label(self.login_frame, text="Password:").grid(
            row=2, column=0, sticky=tk.W, pady=5
        )
        self.pass_entry = ttk.Entry(self.login_frame, width=28, show="*")
        self.pass_entry.grid(row=2, column=1, pady=5)
        self.pass_entry.bind("<Return>", lambda _: self._on_login_click())

        self.login_btn = ttk.Button(
            self.login_frame, text="Login", command=self._on_login_click
        )
        self.login_btn.grid(row=3, column=0, columnspan=2, pady=15)

        self.login_status = ttk.Label(self.login_frame, text="", foreground="red")
        self.login_status.grid(row=4, column=0, columnspan=2)

    def _on_login_click(self) -> None:
        """Validate login input and authenticate in background thread."""
        username = self.user_entry.get().strip()
        password = self.pass_entry.get()
        if not username or not password:
            self.login_status.config(text="Please enter username and password")
            return

        self.login_btn.config(state="disabled")
        self.login_status.config(text="Logging in...", foreground="black")

        client = MailClient(username=username, password=password)
        thread = threading.Thread(
            target=self._login_worker, args=(client,), daemon=True
        )
        thread.start()

    def _login_worker(self, client: MailClient) -> None:
        """Authenticate user credentials against POP3 server."""
        try:
            client.authenticate()
            self.root.after(0, self._on_login_success, client)
        except Exception as err:
            logger.info("Login failed for %s: %s", client.username, err)
            self.root.after(0, self._on_login_failure, str(err))

    def _on_login_success(self, client: MailClient) -> None:
        """Switch to main interface upon successful login."""
        self.client = client
        self.show_main_window()
        self.refresh_inbox()

    def _on_login_failure(self, err_msg: str) -> None:
        """Display error dialog and reset login UI on failure."""
        self.login_btn.config(state="normal")
        self.login_status.config(text="")
        messagebox.showerror(
            "Login Failed",
            f"Could not log in to mailbox:\n{err_msg}",
            parent=self.root,
        )

    def show_main_window(self) -> None:
        """Render the main mail client window after login."""
        if self.login_frame:
            self.login_frame.destroy()
            self.login_frame = None

        self._build_main_ui()

    def _build_main_ui(self) -> None:
        """Construct the main window layout with panes and toolbar."""
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        self._build_toolbar()

        paned = ttk.PanedWindow(self.main_frame, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        inbox_frame = ttk.Frame(paned, width=320)
        preview_frame = ttk.Frame(paned)
        paned.add(inbox_frame, weight=1)
        paned.add(preview_frame, weight=2)

        self._build_inbox_pane(inbox_frame)
        self._build_preview_pane(preview_frame)
        self._build_status_bar()

    def _build_toolbar(self) -> None:
        """Construct the top action toolbar."""
        toolbar = ttk.Frame(self.main_frame, padding=5)
        toolbar.pack(fill=tk.X, side=tk.TOP)

        addr = self.client.address if self.client else ""
        user_lbl = ttk.Label(
            toolbar, text=f"Account: {addr}", font=("Segoe UI", 10, "bold")
        )
        user_lbl.pack(side=tk.LEFT, padx=5)

        ttk.Button(toolbar, text="Logout", command=self._on_logout).pack(
            side=tk.RIGHT, padx=3
        )
        self.refresh_btn = ttk.Button(
            toolbar, text="Refresh", command=self.refresh_inbox
        )
        self.refresh_btn.pack(side=tk.RIGHT, padx=3)
        ttk.Button(
            toolbar, text="Compose", command=self.open_compose_window
        ).pack(side=tk.RIGHT, padx=3)

    def _build_inbox_pane(self, parent: ttk.Frame) -> None:
        """Construct the inbox message list pane."""
        header = ttk.Label(parent, text="Inbox", font=("Segoe UI", 11, "bold"))
        header.pack(anchor=tk.W, padx=5, pady=3)

        list_container = ttk.Frame(parent)
        list_container.pack(fill=tk.BOTH, expand=True)

        self.inbox_listbox = tk.Listbox(
            list_container, selectmode=tk.SINGLE, font=("Segoe UI", 9)
        )
        scroll = ttk.Scrollbar(
            list_container, orient=tk.VERTICAL, command=self.inbox_listbox.yview
        )
        self.inbox_listbox.configure(yscrollcommand=scroll.set)

        self.inbox_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.inbox_listbox.bind("<<ListboxSelect>>", self._on_message_select)

    def _build_preview_pane(self, parent: ttk.Frame) -> None:
        """Construct the message reader and action pane."""
        self.preview_header = ttk.Frame(parent, padding=5)
        self.preview_header.pack(fill=tk.X)

        self.from_lbl = ttk.Label(self.preview_header, text="From: ")
        self.from_lbl.pack(anchor=tk.W)
        self.date_lbl = ttk.Label(self.preview_header, text="Date: ")
        self.date_lbl.pack(anchor=tk.W)
        self.subj_lbl = ttk.Label(
            self.preview_header, text="Subject: ", font=("Segoe UI", 10, "bold")
        )
        self.subj_lbl.pack(anchor=tk.W)
        self.att_lbl = ttk.Label(self.preview_header, text="Attachments: None")
        self.att_lbl.pack(anchor=tk.W)

        self._build_preview_actions(parent)
        self._build_preview_body(parent)

    def _build_preview_actions(self, parent: ttk.Frame) -> None:
        """Construct preview control buttons."""
        bar = ttk.Frame(parent, padding=2)
        bar.pack(fill=tk.X)

        self.delete_btn = ttk.Button(
            bar, text="Delete", state="disabled", command=self._on_delete_click
        )
        self.delete_btn.pack(side=tk.RIGHT, padx=5)

        self.save_att_btn = ttk.Button(
            bar,
            text="Save Attachments",
            state="disabled",
            command=self._save_attachments_click,
        )
        self.save_att_btn.pack(side=tk.RIGHT, padx=5)

    def _build_preview_body(self, parent: ttk.Frame) -> None:
        """Construct read-only text widget for email body preview."""
        body_container = ttk.Frame(parent)
        body_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.preview_text = tk.Text(
            body_container, wrap=tk.WORD, state="disabled", font=("Segoe UI", 10)
        )
        scroll = ttk.Scrollbar(
            body_container, orient=tk.VERTICAL, command=self.preview_text.yview
        )
        self.preview_text.configure(yscrollcommand=scroll.set)

        self.preview_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)

    def _build_status_bar(self) -> None:
        """Construct the bottom status bar."""
        self.status_bar = ttk.Label(
            self.main_frame,
            text="Ready",
            relief=tk.SUNKEN,
            anchor=tk.W,
            padding=3,
        )
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def refresh_inbox(self) -> None:
        """Fetch inbox headers in background thread and update listbox."""
        if not self.client:
            return
        self.refresh_btn.config(state="disabled")
        self.status_bar.config(text="Refreshing inbox...")
        thread = threading.Thread(target=self._refresh_worker, daemon=True)
        thread.start()

    def _refresh_worker(self) -> None:
        """Execute list_inbox in background thread."""
        try:
            messages = self.client.list_inbox()
            self.root.after(0, self._on_refresh_success, messages)
        except Exception as err:
            logger.warning("Failed to refresh inbox: %s", err, exc_info=True)
            self.root.after(0, self._on_refresh_failure, str(err))

    def _on_refresh_success(self, messages: list[dict]) -> None:
        """Update listbox with fetched messages on main thread."""
        self.refresh_btn.config(state="normal")
        self._messages = messages
        self.inbox_listbox.delete(0, tk.END)

        for msg in messages:
            sender = msg.get("from", "")
            subject = msg.get("subject", "(no subject)")
            display = f"#{msg['index']}  {sender} — {subject}"
            self.inbox_listbox.insert(tk.END, display)

        self.status_bar.config(text=f"Loaded {len(messages)} message(s)")

    def _on_refresh_failure(self, err_msg: str) -> None:
        """Handle refresh failure on main thread."""
        self.refresh_btn.config(state="normal")
        self.status_bar.config(text="Failed to refresh inbox")
        messagebox.showerror(
            "Refresh Error",
            f"Failed to fetch inbox messages:\n{err_msg}",
            parent=self.root,
        )

    def _on_message_select(self, _event: tk.Event) -> None:
        """Handle inbox message selection."""
        selection = self.inbox_listbox.curselection()
        if not selection or selection[0] >= len(self._messages):
            return

        msg_info = self._messages[selection[0]]
        msg_idx = msg_info["index"]
        self.status_bar.config(text=f"Fetching message #{msg_idx}...")

        thread = threading.Thread(
            target=self._fetch_message_worker, args=(msg_idx,), daemon=True
        )
        thread.start()

    def _fetch_message_worker(self, index: int) -> None:
        """Retrieve raw message in background thread."""
        try:
            raw_text = self.client.fetch_message(index)
            self.root.after(0, self._display_message, index, raw_text)
        except Exception as err:
            logger.warning("Failed to fetch message #%d: %s", index, err)
            self.root.after(0, self._on_fetch_failure, str(err))

    def _on_fetch_failure(self, err_msg: str) -> None:
        """Handle message fetch error."""
        self.status_bar.config(text="Error loading message")
        messagebox.showerror(
            "Fetch Error", f"Failed to retrieve message:\n{err_msg}", parent=self.root
        )

    def _display_message(self, index: int, raw_text: str) -> None:
        """Parse and display message content on the main thread."""
        self._current_msg_index = index
        self.delete_btn.config(state="normal")
        self.status_bar.config(text=f"Viewing message #{index}")

        parsed = parse_message(raw_text.encode("utf-8"))
        self._current_parsed_msg = parsed

        self.from_lbl.config(text=f"From: {parsed.get('From', '')}")
        self.date_lbl.config(text=f"Date: {parsed.get('Date', '')}")
        self.subj_lbl.config(text=f"Subject: {parsed.get('Subject', '')}")

        attachments = list_attachments(parsed)
        if attachments:
            att_names = ", ".join(f"{name} ({size} B)" for name, _, size in attachments)
            self.att_lbl.config(text=f"Attachments: {att_names}")
            self.save_att_btn.config(state="normal")
        else:
            self.att_lbl.config(text="Attachments: None")
            self.save_att_btn.config(state="disabled")

        body = get_text_body(parsed) or raw_text
        self.preview_text.config(state="normal")
        self.preview_text.delete("1.0", tk.END)
        self.preview_text.insert(tk.END, body)
        self.preview_text.config(state="disabled")

    def _on_delete_click(self) -> None:
        """Confirm and delete currently selected message."""
        if self._current_msg_index is None:
            return
        idx = self._current_msg_index
        confirmed = messagebox.askyesno(
            "Delete Message",
            f"Are you sure you want to delete message #{idx}?",
            parent=self.root,
        )
        if not confirmed:
            return

        self.delete_btn.config(state="disabled")
        self.status_bar.config(text=f"Deleting message #{idx}...")
        thread = threading.Thread(
            target=self._delete_worker, args=(idx,), daemon=True
        )
        thread.start()

    def _delete_worker(self, index: int) -> None:
        """Delete message in background thread."""
        try:
            self.client.delete_message(index)
            self.root.after(0, self._on_delete_success)
        except Exception as err:
            logger.warning("Failed to delete message #%d: %s", index, err)
            self.root.after(0, self._on_delete_failure, str(err))

    def _on_delete_success(self) -> None:
        """Clear message preview and refresh inbox after deletion."""
        self._current_msg_index = None
        self._current_parsed_msg = None
        self.delete_btn.config(state="disabled")
        self.save_att_btn.config(state="disabled")

        self.from_lbl.config(text="From: ")
        self.date_lbl.config(text="Date: ")
        self.subj_lbl.config(text="Subject: ")
        self.att_lbl.config(text="Attachments: None")

        self.preview_text.config(state="normal")
        self.preview_text.delete("1.0", tk.END)
        self.preview_text.config(state="disabled")

        self.refresh_inbox()

    def _on_delete_failure(self, err_msg: str) -> None:
        """Handle deletion failure."""
        self.delete_btn.config(state="normal")
        self.status_bar.config(text="Failed to delete message")
        messagebox.showerror(
            "Delete Error",
            f"Failed to delete message:\n{err_msg}",
            parent=self.root,
        )

    def _save_attachments_click(self) -> None:
        """Save attachments of current message to a user-chosen directory."""
        if not self._current_parsed_msg:
            return
        dest_dir = filedialog.askdirectory(
            parent=self.root, title="Select Destination Directory"
        )
        if not dest_dir:
            return
        saved = extract_attachments(self._current_parsed_msg, Path(dest_dir))
        messagebox.showinfo(
            "Saved",
            f"Successfully saved {len(saved)} attachment(s) to:\n{dest_dir}",
            parent=self.root,
        )

    def open_compose_window(self) -> None:
        """Open compose email dialog."""
        if not self.client:
            return
        ComposeWindow(
            parent=self.root,
            client=self.client,
            on_sent_callback=self.refresh_inbox,
        )

    def _on_logout(self) -> None:
        """Log out the current user and return to the login screen."""
        self.client = None
        self._messages.clear()
        self._current_msg_index = None
        self._current_parsed_msg = None
        self.show_login()

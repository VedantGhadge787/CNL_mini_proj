#!/usr/bin/env python3
"""
scripts/run_client.py
=====================
CLI entry point to launch the Tkinter desktop email client.

Usage:
    python scripts/run_client.py
"""
import sys
from pathlib import Path

# Add project src directory to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import tkinter as tk
from mailsys.client.app import MailApp


def main() -> None:
    """Initialize Tk root and run MailApp event loop."""
    root = tk.Tk()
    app = MailApp(root)
    app.run()


if __name__ == "__main__":
    main()

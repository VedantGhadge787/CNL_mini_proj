"""
scripts/run_client.py
=====================
CLI entry point to launch the Tkinter desktop email client.

Usage:
    python scripts/run_client.py
"""
import sys
import tkinter as tk
from pathlib import Path

# Add project src directory to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from mailsys.client.app import MailApp


def main() -> None:
    """Initialize Tk root and run MailApp event loop."""
    # TODO: Create tk.Tk() instance, MailApp(root), and call root.mainloop()
    raise NotImplementedError


if __name__ == "__main__":
    main()

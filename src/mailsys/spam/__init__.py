"""
mailsys.spam
============
Spam filtering sub-package.

Exports:
    SpamFilter   — keyword-based spam detector and scorer class
    spam_filter  — module-level default SpamFilter instance
"""
from mailsys.spam.filter import SpamFilter, spam_filter  # noqa: F401

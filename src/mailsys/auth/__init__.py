"""
mailsys.auth
============
Authentication and user management sub-package.

Exports:
    create_user      — add a user with salted password hash
    verify_password  — check user credentials against stored hash
    user_exists      — check if a username exists
"""
from mailsys.auth.user_manager import create_user, verify_password, user_exists  # noqa: F401

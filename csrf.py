"""Session-bound form tokens for the two actions that change a draft."""

import secrets

from flask import session


def get_csrf_token():
    """Reuse a valid random token so another open tab's form still works."""
    token = session.get("csrf_token")
    if not isinstance(token, str) or not token:
        token = secrets.token_urlsafe(32)
        session["csrf_token"] = token
    return token


def valid_csrf_token(submitted):
    """Reject missing tokens; compare bytes safely even for unusual input."""
    expected = session.get("csrf_token")
    if not isinstance(expected, str) or not isinstance(submitted, str):
        return False
    return bool(expected and submitted) and secrets.compare_digest(
        expected.encode("utf-8"), submitted.encode("utf-8")
    )

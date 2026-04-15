"""Org-level sender identity.

If an org Gmail account is configured in settings (`org_gmail_account`), all
outbound mail routes through it — token, sender name, signature. Falls back
to the logged-in user when unset. This lets one "boss" connect Gmail and have
all employees' emails go out through that single inbox.
"""

import os
import logging

import requests as http_requests

from database import execute
from encryption import decrypt as enc_decrypt

logger = logging.getLogger(__name__)


def _get_setting(key: str, default: str = "") -> str:
    rs = execute("SELECT value FROM settings WHERE key = ?", [key])
    return rs.rows[0][0] if rs.rows else default


def get_org_sender(logged_in_email: str | None = None) -> dict:
    """Return the identity the app should send email AS.

    Returns {"email": str | None, "refresh_token": str | None, "sender_name": str}.
    `refresh_token` is already decrypted.
    """
    org_email = _get_setting("org_gmail_account", "").strip()
    target = org_email or (logged_in_email or "")
    if not target:
        return {"email": None, "refresh_token": None, "sender_name": ""}

    tok_rs = execute("SELECT refresh_token FROM gmail_tokens WHERE user_email = ?", [target])
    refresh_token = None
    if tok_rs.rows:
        try:
            refresh_token = enc_decrypt(tok_rs.rows[0][0])
        except Exception as e:
            logger.error("Failed to decrypt refresh token for %s: %s", target, e)

    name_rs = execute("SELECT full_name FROM user_profiles WHERE email = ?", [target])
    sender_name = name_rs.rows[0][0] if name_rs.rows else target

    return {"email": target, "refresh_token": refresh_token, "sender_name": sender_name}


def get_org_access_token(logged_in_email: str | None = None) -> tuple[str | None, str]:
    """Get a fresh Gmail access token for the org send account.

    Returns (access_token, sender_email). access_token is None on failure.
    """
    ctx = get_org_sender(logged_in_email)
    if not ctx["refresh_token"]:
        return None, ctx["email"] or ""
    client_id = os.environ.get("GOOGLE_CLIENT_ID", "").strip()
    client_secret = os.environ.get("GOOGLE_CLIENT_SECRET", "").strip()
    resp = http_requests.post("https://oauth2.googleapis.com/token", data={
        "client_id": client_id, "client_secret": client_secret,
        "refresh_token": ctx["refresh_token"], "grant_type": "refresh_token",
    }, timeout=10)
    if resp.status_code != 200:
        logger.error("Token refresh failed for %s: %s", ctx["email"], resp.text[:200])
        return None, ctx["email"] or ""
    return resp.json().get("access_token"), ctx["email"] or ""

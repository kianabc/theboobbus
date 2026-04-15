"""Unified Gmail send helper with proper reply threading.

All outbound mail goes through `send_gmail_message`. For follow-ups, passing
`reply_to_message_id` + `reply_to_thread_id` makes Gmail render the message as
an inline reply in the original thread (not a fresh email). This dramatically
improves open rates because recipients see 'Re: X' under their own prior email.
"""

import base64
import re
import uuid
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import requests as http_requests

from database import execute

logger = logging.getLogger(__name__)

# RFC 5322 Message-IDs need a domain part. Using our own canonical one lets us
# later correlate bounces/replies without relying on Gmail's internal ID.
MESSAGE_ID_DOMAIN = "theboobbus.com"


def _generate_message_id() -> str:
    """Generate an RFC 5322 Message-ID we can store and reference later."""
    return f"<{uuid.uuid4()}@{MESSAGE_ID_DOMAIN}>"


def _strip_re_prefixes(subject: str) -> str:
    """Remove any existing Re:/RE: prefixes so we can re-add exactly one."""
    if not subject:
        return ""
    return re.sub(r"^(\s*re\s*:\s*)+", "", subject, flags=re.IGNORECASE).strip()


def send_gmail_message(
    access_token: str,
    to: str,
    subject: str,
    body: str,
    html_body: str | None = None,
    reply_to_message_id: str | None = None,
    reply_to_thread_id: str | None = None,
) -> dict:
    """Send an email via Gmail API, optionally as a threaded reply.

    Returns a dict:
      {
        "ok": bool,
        "error": str | None,
        "gmail_message_id": str | None,   # Gmail's internal ID (for API lookups)
        "thread_id": str | None,          # Gmail threadId (for future replies)
        "message_id_header": str | None,  # RFC Message-ID header (for In-Reply-To)
      }
    """
    # Sanitize to prevent header injection
    safe_subject = (subject or "").replace("\r", "").replace("\n", " ").strip()[:200]
    safe_to = (to or "").replace("\r", "").replace("\n", "").strip()

    # For replies: normalize to exactly one "Re: " prefix, preserving the root subject
    if reply_to_message_id:
        root = _strip_re_prefixes(safe_subject)
        safe_subject = f"Re: {root}" if root else "Re:"

    message_id_header = _generate_message_id()

    if html_body:
        msg = MIMEMultipart("alternative")
        msg.attach(MIMEText(body, "plain"))
        msg.attach(MIMEText(html_body, "html"))
    else:
        msg = MIMEText(body)

    msg["To"] = safe_to
    msg["Subject"] = safe_subject
    msg["Message-ID"] = message_id_header
    if reply_to_message_id:
        # In-Reply-To points to the immediate parent; References is the full chain.
        # We keep it simple: point at the immediate prior message. Gmail handles the rest.
        msg["In-Reply-To"] = reply_to_message_id
        msg["References"] = reply_to_message_id

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()

    payload: dict = {"raw": raw}
    if reply_to_thread_id:
        payload["threadId"] = reply_to_thread_id

    try:
        resp = http_requests.post(
            "https://gmail.googleapis.com/gmail/v1/users/me/messages/send",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=15,
        )
    except http_requests.RequestException as e:
        return {"ok": False, "error": f"network: {e}", "gmail_message_id": None,
                "thread_id": None, "message_id_header": None}

    if resp.status_code != 200:
        logger.error("Gmail send failed: %s %s", resp.status_code, resp.text[:300])
        return {
            "ok": False,
            "error": f"{resp.status_code}: {resp.text[:300]}",
            "gmail_message_id": None,
            "thread_id": None,
            "message_id_header": None,
        }

    data = resp.json()
    return {
        "ok": True,
        "error": None,
        "gmail_message_id": data.get("id"),
        "thread_id": data.get("threadId"),
        "message_id_header": message_id_header,
    }


def get_thread_anchor(company_id: int, to_email: str) -> dict | None:
    """Find the most recent sent email in this conversation to thread a reply to.

    Returns {"message_id_header": ..., "thread_id": ..., "root_subject": ...}
    or None if no prior thread exists.
    """
    rs = execute(
        """SELECT message_id_header, thread_id, subject, sent_at
           FROM sent_emails
           WHERE company_id = ? AND to_email = ?
             AND thread_id IS NOT NULL
             AND message_id_header IS NOT NULL
           ORDER BY sent_at DESC
           LIMIT 1""",
        [company_id, to_email],
    )
    if not rs.rows:
        return None

    latest_msg_id, thread_id, _latest_subject, _ = rs.rows[0]

    # For the subject: use the very first email in the thread (the "root")
    root_rs = execute(
        """SELECT subject FROM sent_emails
           WHERE company_id = ? AND to_email = ?
             AND thread_id = ?
           ORDER BY sent_at ASC
           LIMIT 1""",
        [company_id, to_email, thread_id],
    )
    root_subject = root_rs.rows[0][0] if root_rs.rows else ""
    root_subject = _strip_re_prefixes(root_subject)

    return {
        "message_id_header": latest_msg_id,
        "thread_id": thread_id,
        "root_subject": root_subject,
    }

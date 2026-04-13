"""Automatic follow-up engine: checks for replies and sends follow-ups."""

import os
import logging
import base64
from email.mime.text import MIMEText
from datetime import datetime, timedelta, timezone

import requests as http_requests

from database import execute
from email_generator import generate_outreach_email

logger = logging.getLogger(__name__)

# Full sequence labels (up to 5 steps)
ALL_STEPS = ["initial", "follow_up_1", "follow_up_2", "follow_up_3", "final"]
# Mapping for AI email types
STEP_TO_EMAIL_TYPE = {
    "initial": "initial",
    "follow_up_1": "follow_up",
    "follow_up_2": "follow_up",
    "follow_up_3": "follow_up",
    "final": "final",
}

DEFAULT_FOLLOW_UP_DAYS = 5
DEFAULT_SEQUENCE_LENGTH = 3


def _get_setting(key: str, default: str) -> str:
    rs = execute("SELECT value FROM settings WHERE key = ?", [key])
    return rs.rows[0][0] if rs.rows else default


def _set_setting(key: str, value: str):
    execute(
        "INSERT INTO settings (key, value) VALUES (?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        [key, value],
    )


def get_follow_up_days() -> int:
    try:
        return int(_get_setting("follow_up_days", str(DEFAULT_FOLLOW_UP_DAYS)))
    except ValueError:
        return DEFAULT_FOLLOW_UP_DAYS


def set_follow_up_days(days: int):
    _set_setting("follow_up_days", str(days))


def get_sequence_length() -> int:
    try:
        return int(_get_setting("sequence_length", str(DEFAULT_SEQUENCE_LENGTH)))
    except ValueError:
        return DEFAULT_SEQUENCE_LENGTH


def set_sequence_length(length: int):
    _set_setting("sequence_length", str(length))


def get_sequence() -> list[str]:
    """Get the active sequence based on configured length."""
    length = get_sequence_length()
    if length == 2:
        return ["initial", "final"]
    # For 3+: initial, then follow_up_1..N-2, then final
    steps = ["initial"]
    for i in range(1, length - 1):
        steps.append(f"follow_up_{i}")
    steps.append("final")
    return steps


def _refresh_gmail_token(user_email: str) -> str | None:
    """Get a fresh Gmail access token using stored refresh token."""
    rs = execute("SELECT refresh_token FROM gmail_tokens WHERE user_email = ?", [user_email])
    if not rs.rows:
        logger.warning("No refresh token for %s", user_email)
        return None

    refresh_token = rs.rows[0][0]
    client_id = os.environ.get("GOOGLE_CLIENT_ID", "").strip()
    client_secret = os.environ.get("GOOGLE_CLIENT_SECRET", "").strip()

    if not client_id or not client_secret:
        logger.error("GOOGLE_CLIENT_ID or GOOGLE_CLIENT_SECRET not set")
        return None

    resp = http_requests.post("https://oauth2.googleapis.com/token", data={
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    }, timeout=10)

    if resp.status_code != 200:
        logger.error("Token refresh failed: %s", resp.text)
        return None

    return resp.json().get("access_token")


def _check_for_reply(gmail_token: str, message_id: str) -> bool:
    """Check if a Gmail message has been replied to."""
    if not message_id:
        return False

    try:
        # Get the message to find its thread ID
        resp = http_requests.get(
            f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{message_id}",
            headers={"Authorization": f"Bearer {gmail_token}"},
            params={"format": "metadata", "metadataHeaders": "Subject"},
            timeout=10,
        )
        if resp.status_code != 200:
            return False

        thread_id = resp.json().get("threadId")
        if not thread_id:
            return False

        # Get the thread and check if there are messages we didn't send
        thread_resp = http_requests.get(
            f"https://gmail.googleapis.com/gmail/v1/users/me/threads/{thread_id}",
            headers={"Authorization": f"Bearer {gmail_token}"},
            params={"format": "metadata"},
            timeout=10,
        )
        if thread_resp.status_code != 200:
            return False

        messages = thread_resp.json().get("messages", [])
        # If there are more messages than we sent, someone replied
        return len(messages) > 1

    except Exception as e:
        logger.error("Error checking reply for %s: %s", message_id, e)
        return False


def _send_followup_email(gmail_token: str, sent_email: dict, company: dict) -> bool:
    """Generate and send a follow-up email."""
    sequence = get_sequence()
    current_type = sent_email["email_type"]

    # Find current position in sequence
    current_idx = -1
    for i, step in enumerate(sequence):
        if step == current_type:
            current_idx = i
            break
    if current_idx == -1:
        current_idx = 0  # fallback

    next_idx = current_idx + 1
    if next_idx >= len(sequence):
        logger.info("Max follow-ups reached for %s -> %s", company["name"], sent_email["to_email"])
        return False

    next_type = sequence[next_idx]
    # Map to AI email type (follow_up_1/2/3 all map to "follow_up")
    ai_email_type = STEP_TO_EMAIL_TYPE.get(next_type, "follow_up")

    # Parse contact info from source if available
    contact_name = None
    contact_title = None

    # Generate the follow-up
    try:
        email = generate_outreach_email(
            company_name=company["name"],
            company_industry=company["industry"] or "Unknown",
            company_city=company["city"] or "Utah",
            contact_email=sent_email["to_email"],
            contact_name=contact_name,
            contact_title=contact_title,
            email_type=ai_email_type,
        )
    except Exception as e:
        logger.error("Failed to generate follow-up: %s", e)
        return False

    # Send via Gmail
    msg = MIMEText(email["body"])
    msg["To"] = sent_email["to_email"]
    msg["Subject"] = email["subject"]
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()

    try:
        resp = http_requests.post(
            "https://gmail.googleapis.com/gmail/v1/users/me/messages/send",
            headers={
                "Authorization": f"Bearer {gmail_token}",
                "Content-Type": "application/json",
            },
            json={"raw": raw},
            timeout=15,
        )
        if resp.status_code != 200:
            logger.error("Gmail send failed: %s", resp.text)
            return False

        gmail_msg_id = resp.json().get("id", "")

        # Calculate next follow-up
        follow_up_days = get_follow_up_days()
        next_follow_up = None
        if next_type != "final":
            next_follow_up = (datetime.now(timezone.utc) + timedelta(days=follow_up_days)).isoformat()

        # Log the sent follow-up
        execute(
            """INSERT INTO sent_emails
               (company_id, to_email, subject, body, sent_by, email_type, gmail_message_id, next_follow_up_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            [
                sent_email["company_id"], sent_email["to_email"],
                email["subject"], email["body"], sent_email["sent_by"],
                next_type, gmail_msg_id, next_follow_up,
            ],
        )

        # Mark the original email as no longer needing follow-up
        execute("UPDATE sent_emails SET next_follow_up_at = NULL WHERE id = ?", [sent_email["id"]])

        logger.info("Sent %s follow-up to %s at %s", next_type, sent_email["to_email"], company["name"])
        return True

    except Exception as e:
        logger.error("Failed to send follow-up: %s", e)
        return False


def process_pending_followups() -> dict:
    """Main cron function: check for replies, send follow-ups where needed."""
    now = datetime.now(timezone.utc).isoformat()

    # Find emails due for follow-up
    rs = execute(
        """SELECT se.id, se.company_id, se.to_email, se.subject, se.sent_by,
                  se.email_type, se.gmail_message_id,
                  c.name, c.industry, c.city
           FROM sent_emails se
           JOIN companies c ON c.id = se.company_id
           WHERE se.next_follow_up_at IS NOT NULL
             AND se.next_follow_up_at <= ?
             AND se.replied = 0""",
        [now],
    )

    if not rs.rows:
        return {"checked": 0, "followed_up": 0, "replies_found": 0}

    results = {"checked": len(rs.rows), "followed_up": 0, "replies_found": 0}

    # Group by sender to reuse tokens
    senders = {}
    for r in rs.rows:
        sent = {
            "id": r[0], "company_id": r[1], "to_email": r[2],
            "subject": r[3], "sent_by": r[4], "email_type": r[5],
            "gmail_message_id": r[6],
        }
        company = {"name": r[7], "industry": r[8], "city": r[9]}
        sender_email = sent["sent_by"]
        if sender_email not in senders:
            senders[sender_email] = []
        senders[sender_email].append((sent, company))

    for sender_email, items in senders.items():
        # Get a fresh Gmail token for this sender
        gmail_token = _refresh_gmail_token(sender_email)
        if not gmail_token:
            logger.warning("Cannot get Gmail token for %s, skipping %d follow-ups", sender_email, len(items))
            continue

        for sent, company in items:
            # Check if the recipient replied
            if _check_for_reply(gmail_token, sent["gmail_message_id"]):
                execute("UPDATE sent_emails SET replied = 1, next_follow_up_at = NULL WHERE id = ?", [sent["id"]])
                results["replies_found"] += 1
                logger.info("Reply detected from %s at %s", sent["to_email"], company["name"])
                continue

            # No reply — send follow-up
            if _send_followup_email(gmail_token, sent, company):
                results["followed_up"] += 1

    return results

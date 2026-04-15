"""Automatic follow-up engine: checks for replies and sends follow-ups."""

import os
import logging
from datetime import datetime, timedelta, timezone

import requests as http_requests

from database import execute

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
    from encryption import decrypt as enc_decrypt

    rs = execute("SELECT refresh_token FROM gmail_tokens WHERE user_email = ?", [user_email])
    if not rs.rows:
        logger.warning("No refresh token for %s", user_email)
        return None

    refresh_token = enc_decrypt(rs.rows[0][0])
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


# Follow-ups are enqueued into scheduled_sends by process_pending_followups
# and sent by the per-minute cron (in main.py, kind='followup' branch).
# The old synchronous _send_followup_email is gone — it would timeout on
# any non-trivial batch.


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

    sequence = get_sequence()
    now_iso = datetime.now(timezone.utc).isoformat()

    for sender_email, items in senders.items():
        # Get a fresh Gmail token for this sender (only for reply-checking)
        gmail_token = _refresh_gmail_token(sender_email)
        if not gmail_token:
            logger.warning("Cannot get Gmail token for %s, skipping %d follow-ups", sender_email, len(items))
            continue

        for sent, company in items:
            # Check if the recipient replied (cheap API call, keep it synchronous)
            if _check_for_reply(gmail_token, sent["gmail_message_id"]):
                execute("UPDATE sent_emails SET replied = 1, next_follow_up_at = NULL WHERE id = ?", [sent["id"]])
                results["replies_found"] += 1
                logger.info("Reply detected from %s at %s", sent["to_email"], company["name"])
                continue

            # Determine the next step in the sequence
            current_idx = -1
            for i, step in enumerate(sequence):
                if step == sent["email_type"]:
                    current_idx = i
                    break
            if current_idx == -1:
                current_idx = 0

            next_idx = current_idx + 1
            if next_idx >= len(sequence):
                # No further steps — clear follow-up marker and move on
                execute("UPDATE sent_emails SET next_follow_up_at = NULL WHERE id = ?", [sent["id"]])
                continue

            next_type = sequence[next_idx]

            # Enqueue with send_at=now. The per-minute cron drains the queue,
            # sleeping 15–30s between each send within a tick for real Gmail-
            # visible spacing.
            execute(
                """INSERT INTO scheduled_sends
                   (user_email, test_email, company_id, contact_email, contact_name,
                    contact_title, email_type, step_num, total_steps, send_at, status, kind)
                   VALUES (?, ?, ?, ?, ?, ?, ?, 1, 1, ?, 'pending', 'followup')""",
                [
                    sender_email, sent["to_email"], sent["company_id"], sent["to_email"],
                    None, None, next_type, now_iso,
                ],
            )

            # Clear the parent's follow-up marker so we don't re-enqueue tomorrow
            execute("UPDATE sent_emails SET next_follow_up_at = NULL WHERE id = ?", [sent["id"]])

            results["followed_up"] += 1

    return results

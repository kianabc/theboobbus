"""Google Sign-In authentication for FastAPI."""

import os
import logging

from fastapi import HTTPException, Request
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

logger = logging.getLogger(__name__)

# Paths that don't require user auth (protected by other means)
PUBLIC_PATHS = ["/api/cron/", "/api/track/"]


def get_current_user(request: Request) -> dict:
    """Verify Google ID token from Authorization header."""
    # Skip auth for cron/public endpoints
    path = request.url.path
    if any(path.startswith(p) for p in PUBLIC_PATHS):
        return {"email": "cron", "name": "Cron Job", "picture": ""}

    client_id = os.environ.get("GOOGLE_CLIENT_ID", "").strip()
    if not client_id:
        raise HTTPException(status_code=500, detail="GOOGLE_CLIENT_ID not configured")

    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing auth token")

    token = auth[7:]
    try:
        idinfo = id_token.verify_oauth2_token(
            token, google_requests.Request(), client_id
        )
        user = {
            "email": idinfo["email"],
            "name": idinfo.get("name", ""),
            "picture": idinfo.get("picture", ""),
        }
        # Upsert user profile
        try:
            from database import execute
            execute(
                """INSERT INTO user_profiles (email, full_name, picture)
                   VALUES (?, ?, ?)
                   ON CONFLICT(email) DO UPDATE SET full_name = excluded.full_name, picture = excluded.picture, updated_at = CURRENT_TIMESTAMP""",
                [user["email"], user["name"], user["picture"]],
            )
        except Exception:
            pass
        return user
    except ValueError as e:
        logger.warning("Invalid Google token: %s", e)
        raise HTTPException(status_code=401, detail="Invalid or expired token")

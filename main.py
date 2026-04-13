"""HR Email Finder API — Find HR department emails for top Utah companies."""

from dotenv import load_dotenv
load_dotenv()

import logging
import os
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from auth import get_current_user
from database import init_db, execute
from seed_data import seed_companies
from scraper import scrape_company
from email_finders import find_hr_emails

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not os.environ.get("VERCEL"):
        init_db()
        count = seed_companies()
        logger.info("Database ready with %d companies", count)
    yield


app = FastAPI(
    title="Boob Bus HQ",
    description="Lead generation tool for The Boob Bus - find HR contacts at Utah companies to book mobile mammography visits.",
    version="2.0.0",
    lifespan=lifespan,
    dependencies=[Depends(get_current_user)],
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "https://theboobbus.vercel.app"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Pydantic models ──────────────────────────────────────────────────────────

class CompanyOut(BaseModel):
    id: int
    name: str
    website: str | None
    industry: str | None
    city: str | None
    description: str | None = None
    email_count: int = 0


class HREmailOut(BaseModel):
    id: int | None = None
    email: str
    confidence: str
    source: str | None


class CompanyWithEmails(CompanyOut):
    hr_emails: list[HREmailOut]


class CompanyCreate(BaseModel):
    name: str
    website: str | None = None
    industry: str | None = None
    city: str | None = "Utah"


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/api/industries", response_model=list[str])
def list_industries():
    """List all distinct industries."""
    rs = execute("SELECT DISTINCT industry FROM companies WHERE industry IS NOT NULL ORDER BY industry")
    return [r[0] for r in rs.rows]


@app.get("/api/companies", response_model=list[CompanyOut])
def list_companies(
    search: str | None = Query(None, description="Filter companies by name (case-insensitive)"),
    industry: str | None = Query(None, description="Filter by industry"),
):
    """List all companies, optionally filtered by name or industry."""
    query = """
        SELECT c.id, c.name, c.website, c.industry, c.city, c.description, COUNT(e.id) as email_count
        FROM companies c
        LEFT JOIN hr_emails e ON e.company_id = c.id
        WHERE 1=1
    """
    params: list = []
    if search:
        query += " AND c.name LIKE ?"
        params.append(f"%{search}%")
    if industry:
        query += " AND c.industry LIKE ?"
        params.append(f"%{industry}%")
    query += " GROUP BY c.id ORDER BY c.name"
    rs = execute(query, params)
    return [{"id": r[0], "name": r[1], "website": r[2], "industry": r[3], "city": r[4], "description": r[5], "email_count": r[6]} for r in rs.rows]


@app.get("/api/companies/{company_id}", response_model=CompanyWithEmails)
def get_company(company_id: int):
    """Get a company and its cached HR emails."""
    rs = execute("SELECT id, name, website, industry, city, description FROM companies WHERE id = ?", [company_id])
    if not rs.rows:
        raise HTTPException(status_code=404, detail="Company not found")
    r = rs.rows[0]
    company = {"id": r[0], "name": r[1], "website": r[2], "industry": r[3], "city": r[4], "description": r[5]}

    ers = execute(
        "SELECT id, email, confidence, source FROM hr_emails WHERE company_id = ? ORDER BY confidence DESC",
        [company_id],
    )
    company["hr_emails"] = [{"id": e[0], "email": e[1], "confidence": e[2], "source": e[3]} for e in ers.rows]
    return company


@app.post("/api/companies", response_model=CompanyOut, status_code=201)
def add_company(body: CompanyCreate):
    """Add a new company to track."""
    rs = execute(
        "INSERT INTO companies (name, website, industry, city) VALUES (?, ?, ?, ?)",
        [body.name, body.website, body.industry, body.city],
    )
    company_id = rs.last_insert_rowid
    rs2 = execute("SELECT id, name, website, industry, city FROM companies WHERE id = ?", [company_id])
    r = rs2.rows[0]
    return {"id": r[0], "name": r[1], "website": r[2], "industry": r[3], "city": r[4]}


class CompanyUpdate(BaseModel):
    name: str | None = None
    website: str | None = None
    industry: str | None = None
    city: str | None = None
    description: str | None = None


@app.put("/api/companies/{company_id}")
def update_company(company_id: int, body: CompanyUpdate):
    """Update a company's details."""
    rs = execute("SELECT id FROM companies WHERE id = ?", [company_id])
    if not rs.rows:
        raise HTTPException(status_code=404, detail="Company not found")

    updates = []
    params = []
    for field in ["name", "website", "industry", "city", "description"]:
        val = getattr(body, field)
        if val is not None:
            updates.append(f"{field} = ?")
            params.append(val)
    if not updates:
        raise HTTPException(status_code=400, detail="Nothing to update")

    params.append(company_id)
    execute(f"UPDATE companies SET {', '.join(updates)} WHERE id = ?", params)

    rs2 = execute("SELECT id, name, website, industry, city FROM companies WHERE id = ?", [company_id])
    r = rs2.rows[0]
    return {"id": r[0], "name": r[1], "website": r[2], "industry": r[3], "city": r[4]}


@app.delete("/api/companies/{company_id}")
def delete_company(company_id: int):
    """Delete a company and ALL related data."""
    rs = execute("SELECT id, name FROM companies WHERE id = ?", [company_id])
    if not rs.rows:
        raise HTTPException(status_code=404, detail="Company not found")
    name = rs.rows[0][1]

    # Count related data for the response
    contacts = execute("SELECT COUNT(*) FROM hr_emails WHERE company_id = ?", [company_id]).rows[0][0]
    emails = execute("SELECT COUNT(*) FROM sent_emails WHERE company_id = ?", [company_id]).rows[0][0]
    drafts = execute("SELECT COUNT(*) FROM email_drafts WHERE company_id = ?", [company_id]).rows[0][0]

    # Delete everything
    execute("DELETE FROM hr_emails WHERE company_id = ?", [company_id])
    execute("DELETE FROM sent_emails WHERE company_id = ?", [company_id])
    execute("DELETE FROM email_drafts WHERE company_id = ?", [company_id])
    execute("DELETE FROM companies WHERE id = ?", [company_id])

    return {
        "status": "deleted",
        "company": name,
        "deleted_contacts": contacts,
        "deleted_emails": emails,
        "deleted_drafts": drafts,
    }


class AddContactRequest(BaseModel):
    email: str
    name: str | None = None
    title: str | None = None


@app.post("/api/companies/{company_id}/contacts")
def add_contact(company_id: int, body: AddContactRequest):
    """Manually add a contact to a company."""
    rs = execute("SELECT id FROM companies WHERE id = ?", [company_id])
    if not rs.rows:
        raise HTTPException(status_code=404, detail="Company not found")

    source = "Manual entry"
    if body.name or body.title:
        parts = [p for p in [body.name, body.title] if p]
        source = f"Manual - {', '.join(parts)}"

    execute(
        """INSERT INTO hr_emails (company_id, email, source, confidence)
           VALUES (?, ?, ?, ?)
           ON CONFLICT(company_id, email) DO UPDATE SET
               source = excluded.source,
               confidence = excluded.confidence,
               scraped_at = CURRENT_TIMESTAMP""",
        [company_id, body.email.lower().strip(), source, "high"],
    )
    return {"email": body.email.lower().strip(), "confidence": "high", "source": source}


class UpdateContactRequest(BaseModel):
    email: str | None = None
    source: str | None = None
    confidence: str | None = None


@app.put("/api/contacts/{contact_id}")
def update_contact(contact_id: int, body: UpdateContactRequest):
    """Update a contact's details."""
    rs = execute("SELECT id FROM hr_emails WHERE id = ?", [contact_id])
    if not rs.rows:
        raise HTTPException(status_code=404, detail="Contact not found")

    updates = []
    params = []
    if body.email is not None:
        updates.append("email = ?")
        params.append(body.email.lower().strip())
    if body.source is not None:
        updates.append("source = ?")
        params.append(body.source)
    if body.confidence is not None:
        updates.append("confidence = ?")
        params.append(body.confidence)
    if not updates:
        raise HTTPException(status_code=400, detail="Nothing to update")

    params.append(contact_id)
    execute(f"UPDATE hr_emails SET {', '.join(updates)} WHERE id = ?", params)
    return {"status": "updated"}


@app.delete("/api/contacts/{contact_id}")
def delete_contact(contact_id: int):
    """Delete a contact."""
    execute("DELETE FROM hr_emails WHERE id = ?", [contact_id])
    return {"status": "deleted"}


class SaveDraftRequest(BaseModel):
    contact_email: str
    subject: str
    body: str


@app.get("/api/companies/{company_id}/draft/{contact_email}")
def get_draft(company_id: int, contact_email: str):
    """Get a saved draft for a contact."""
    rs = execute(
        "SELECT subject, body FROM email_drafts WHERE company_id = ? AND contact_email = ?",
        [company_id, contact_email],
    )
    if not rs.rows:
        return {"subject": "", "body": ""}
    return {"subject": rs.rows[0][0], "body": rs.rows[0][1]}


@app.put("/api/companies/{company_id}/draft")
def save_draft(company_id: int, body: SaveDraftRequest):
    """Save a draft for a contact."""
    execute(
        """INSERT INTO email_drafts (company_id, contact_email, subject, body)
           VALUES (?, ?, ?, ?)
           ON CONFLICT(company_id, contact_email) DO UPDATE SET
               subject = excluded.subject,
               body = excluded.body,
               updated_at = CURRENT_TIMESTAMP""",
        [company_id, body.contact_email, body.subject, body.body],
    )
    return {"status": "saved"}


@app.post("/api/companies/{company_id}/scrape", response_model=list[HREmailOut])
def scrape_company_emails(company_id: int):
    """Find HR emails using Hunter.io, Apollo.io, and web scraping."""
    rs = execute("SELECT id, name, website FROM companies WHERE id = ?", [company_id])
    if not rs.rows:
        raise HTTPException(status_code=404, detail="Company not found")

    row = rs.rows[0]
    company_name = row[1]
    website = row[2]
    if not website:
        raise HTTPException(status_code=400, detail="Company has no website URL to search")

    logger.info("Finding HR emails for %s (%s)", company_name, website)
    found_emails = find_hr_emails(company_name, website)

    for item in found_emails:
        execute(
            """INSERT INTO hr_emails (company_id, email, source, confidence)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(company_id, email) DO UPDATE SET
                   source = excluded.source,
                   confidence = excluded.confidence,
                   scraped_at = CURRENT_TIMESTAMP""",
            [company_id, item["email"], item["source"], item["confidence"]],
        )

    return found_emails


@app.post("/api/scrape-all", response_model=dict)
def scrape_all_companies():
    """Scrape all companies in the database. This can take a while."""
    rs = execute("SELECT id, name, website FROM companies")

    total_emails = 0
    companies_scraped = 0
    errors = []

    for row in rs.rows:
        if not row[2]:
            continue
        try:
            found = scrape_company(row[2])
            for item in found:
                execute(
                    """INSERT INTO hr_emails (company_id, email, source, confidence)
                       VALUES (?, ?, ?, ?)
                       ON CONFLICT(company_id, email) DO UPDATE SET
                           source = excluded.source,
                           confidence = excluded.confidence,
                           scraped_at = CURRENT_TIMESTAMP""",
                    [row[0], item["email"], item["source"], item["confidence"]],
                )
            total_emails += len(found)
            companies_scraped += 1
            logger.info("Scraped %s: found %d emails", row[1], len(found))
        except Exception as e:
            logger.error("Error scraping %s: %s", row[1], e)
            errors.append({"company": row[1], "error": str(e)})

    return {
        "companies_scraped": companies_scraped,
        "total_emails_found": total_emails,
        "errors": errors,
    }


@app.get("/api/emails", response_model=list[dict])
def list_all_emails(
    confidence: str | None = Query(None, description="Filter by confidence: high, medium, low"),
):
    """List all cached HR emails across all companies."""
    query = """
        SELECT c.name, c.industry, e.email, e.confidence, e.source
        FROM hr_emails e
        JOIN companies c ON c.id = e.company_id
        WHERE 1=1
    """
    params: list = []
    if confidence:
        query += " AND e.confidence = ?"
        params.append(confidence)
    query += " ORDER BY e.confidence DESC, c.name"
    rs = execute(query, params)
    return [{"company": r[0], "industry": r[1], "email": r[2], "confidence": r[3], "source": r[4]} for r in rs.rows]


# ── Email Generation & Sending ────────────────────────────────────────────────

class GenerateEmailRequest(BaseModel):
    company_id: int
    contact_email: str
    contact_name: str | None = None
    contact_title: str | None = None
    email_type: str = "initial"  # "initial", "follow_up", "final"


class SendEmailRequest(BaseModel):
    to: str
    subject: str
    body: str
    company_id: int | None = None
    email_type: str = "initial"


@app.post("/api/generate-email")
def generate_email(body: GenerateEmailRequest, request: Request):
    """Generate a personalized outreach email using AI."""
    from email_generator import generate_outreach_email
    from datetime import datetime, timezone

    rs = execute("SELECT name, industry, city FROM companies WHERE id = ?", [body.company_id])
    if not rs.rows:
        raise HTTPException(status_code=404, detail="Company not found")

    # Get sender name from user profile
    user = get_current_user(request)
    sender_name = user.get("name", "")
    profile_rs = execute("SELECT full_name FROM user_profiles WHERE email = ?", [user["email"]])
    if profile_rs.rows and profile_rs.rows[0][0]:
        sender_name = profile_rs.rows[0][0]

    # Calculate days since last email to this contact
    days_since_last = None
    if body.email_type != "initial":
        last_rs = execute(
            "SELECT sent_at FROM sent_emails WHERE company_id = ? AND to_email = ? ORDER BY sent_at DESC LIMIT 1",
            [body.company_id, body.contact_email],
        )
        if last_rs.rows and last_rs.rows[0][0]:
            try:
                last_sent = datetime.fromisoformat(last_rs.rows[0][0].replace("Z", "+00:00"))
                days_since_last = (datetime.now(timezone.utc) - last_sent).days
            except Exception:
                pass

    company = rs.rows[0]
    result = generate_outreach_email(
        company_name=company[0],
        company_industry=company[1] or "Unknown",
        company_city=company[2] or "Utah",
        contact_email=body.contact_email,
        contact_name=body.contact_name,
        contact_title=body.contact_title,
        email_type=body.email_type,
        company_id=body.company_id,
        sender_name=sender_name,
        days_since_last=days_since_last,
    )
    return result


@app.post("/api/send-email")
def send_email(body: SendEmailRequest, request: Request):
    """Send an email via Gmail.

    Uses stored refresh token if available, otherwise requires X-Gmail-Token header.
    """
    import requests as http_requests

    gmail_token = request.headers.get("X-Gmail-Token", "")

    # Try to use stored refresh token first
    if not gmail_token:
        user = get_current_user(request)
        rs = execute("SELECT refresh_token FROM gmail_tokens WHERE user_email = ?", [user["email"]])
        if rs.rows:
            client_id = os.environ.get("GOOGLE_CLIENT_ID", "").strip()
            client_secret = os.environ.get("GOOGLE_CLIENT_SECRET", "").strip()
            resp = http_requests.post("https://oauth2.googleapis.com/token", data={
                "client_id": client_id,
                "client_secret": client_secret,
                "refresh_token": rs.rows[0][0],
                "grant_type": "refresh_token",
            }, timeout=10)
            if resp.status_code == 200:
                gmail_token = resp.json().get("access_token", "")

    if not gmail_token:
        raise HTTPException(status_code=400, detail="Gmail not connected. Go to Settings to connect your Gmail account.")

    import base64
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart

    # Generate tracking pixel
    tracking_id = str(uuid.uuid4())
    base_url = request.headers.get("Origin", "https://theboobbus.vercel.app")
    tracking_url = f"{base_url}/api/track/{tracking_id}"
    tracking_pixel = f'<img src="{tracking_url}" width="1" height="1" style="display:none" />'

    # Build HTML email with tracking pixel
    html_body = body.body.replace("\n", "<br>") + tracking_pixel
    msg = MIMEMultipart("alternative")
    msg["To"] = body.to
    msg["Subject"] = body.subject
    msg.attach(MIMEText(body.body, "plain"))
    msg.attach(MIMEText(html_body, "html"))
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()

    # Send via Gmail API
    import requests as http_requests
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
        logger.error("Gmail send error: %s %s", resp.status_code, resp.text)
        raise HTTPException(status_code=resp.status_code, detail=f"Gmail error: {resp.json().get('error', {}).get('message', 'Unknown')}")

    # Log the sent email with follow-up scheduling
    gmail_msg_id = resp.json().get("id", "")
    user_email = get_current_user(request).get("email", "unknown")

    from followup_engine import get_follow_up_days
    from datetime import datetime, timedelta, timezone
    follow_up_days = get_follow_up_days()
    email_type = getattr(body, "email_type", "initial") or "initial"
    next_follow_up = None
    if email_type != "final":
        next_follow_up = (datetime.now(timezone.utc) + timedelta(days=follow_up_days)).isoformat()

    sent_email_id = None
    if body.company_id:
        rs_insert = execute(
            """INSERT INTO sent_emails
               (company_id, to_email, subject, body, sent_by, email_type, gmail_message_id, next_follow_up_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            [body.company_id, body.to, body.subject, body.body,
             user_email, email_type, gmail_msg_id, next_follow_up],
        )
        sent_email_id = rs_insert.last_insert_rowid

    # Create tracking record for open detection
    if sent_email_id:
        execute(
            "INSERT INTO email_opens (tracking_id, sent_email_id) VALUES (?, ?)",
            [tracking_id, sent_email_id],
        )

    # Store the Gmail refresh token if provided (for auto follow-ups)
    gmail_refresh = request.headers.get("X-Gmail-Refresh-Token", "")
    if gmail_refresh and user_email != "unknown":
        execute(
            """INSERT INTO gmail_tokens (user_email, refresh_token)
               VALUES (?, ?)
               ON CONFLICT(user_email) DO UPDATE SET refresh_token = excluded.refresh_token, updated_at = CURRENT_TIMESTAMP""",
            [user_email, gmail_refresh],
        )

    return {"status": "sent", "message_id": gmail_msg_id}


@app.get("/api/companies/{company_id}/outreach")
def get_outreach_history(company_id: int):
    """Get sent email history for a company."""
    rs = execute(
        """SELECT se.id, se.to_email, se.subject, se.sent_by, se.email_type, se.replied,
                  se.sent_at, se.next_follow_up_at, eo.opened_at, eo.open_count
           FROM sent_emails se
           LEFT JOIN email_opens eo ON eo.sent_email_id = se.id
           WHERE se.company_id = ? ORDER BY se.sent_at DESC""",
        [company_id],
    )
    return [{
        "id": r[0], "to_email": r[1], "subject": r[2], "sent_by": r[3],
        "email_type": r[4], "replied": bool(r[5]), "sent_at": r[6],
        "next_follow_up_at": r[7], "opened_at": r[8], "open_count": r[9] or 0,
    } for r in rs.rows]


# ── Settings ──────────────────────────────────────────────────────────────────

class SettingsUpdate(BaseModel):
    follow_up_days: int | None = None
    sequence_length: int | None = None
    hunter_enabled: bool | None = None
    hunter_api_key: str | None = None
    apollo_enabled: bool | None = None
    apollo_api_key: str | None = None
    scraping_enabled: bool | None = None
    anthropic_api_key: str | None = None
    test_interval_seconds: int | None = None


def _get_setting(key: str, default: str = "") -> str:
    rs = execute("SELECT value FROM settings WHERE key = ?", [key])
    return rs.rows[0][0] if rs.rows else default


def _set_setting(key: str, value: str):
    execute(
        "INSERT INTO settings (key, value) VALUES (?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        [key, value],
    )


@app.get("/api/settings")
def get_settings():
    """Get app settings."""
    from followup_engine import get_follow_up_days, get_sequence_length
    return {
        "follow_up_days": get_follow_up_days(),
        "sequence_length": get_sequence_length(),
        "hunter_enabled": _get_setting("hunter_enabled", "true") == "true",
        "hunter_api_key": _get_setting("hunter_api_key") or os.environ.get("HUNTER_API_KEY", ""),
        "apollo_enabled": _get_setting("apollo_enabled", "true") == "true",
        "apollo_api_key": _get_setting("apollo_api_key") or os.environ.get("APOLLO_API_KEY", ""),
        "scraping_enabled": _get_setting("scraping_enabled", "true") == "true",
        "anthropic_api_key": _get_setting("anthropic_api_key") or os.environ.get("ANTHROPIC_API_KEY", ""),
        "test_interval_seconds": int(_get_setting("test_interval_seconds", "60")),
    }


@app.put("/api/settings")
def update_settings(body: SettingsUpdate):
    """Update app settings."""
    from followup_engine import set_follow_up_days, set_sequence_length
    if body.follow_up_days is not None:
        if body.follow_up_days < 1 or body.follow_up_days > 30:
            raise HTTPException(status_code=400, detail="Follow-up days must be between 1 and 30")
        set_follow_up_days(body.follow_up_days)
    if body.sequence_length is not None:
        if body.sequence_length < 2 or body.sequence_length > 5:
            raise HTTPException(status_code=400, detail="Sequence length must be between 2 and 5")
        set_sequence_length(body.sequence_length)
    if body.hunter_enabled is not None:
        _set_setting("hunter_enabled", "true" if body.hunter_enabled else "false")
    if body.hunter_api_key is not None:
        _set_setting("hunter_api_key", body.hunter_api_key)
    if body.apollo_enabled is not None:
        _set_setting("apollo_enabled", "true" if body.apollo_enabled else "false")
    if body.apollo_api_key is not None:
        _set_setting("apollo_api_key", body.apollo_api_key)
    if body.scraping_enabled is not None:
        _set_setting("scraping_enabled", "true" if body.scraping_enabled else "false")
    if body.anthropic_api_key is not None:
        _set_setting("anthropic_api_key", body.anthropic_api_key)
    if body.test_interval_seconds is not None:
        _set_setting("test_interval_seconds", str(body.test_interval_seconds))
    return get_settings()


# ── Activity Tracker ──────────────────────────────────────────────────────────

@app.get("/api/activity")
def get_activity():
    """Get all outreach activity across all companies."""
    rs = execute(
        """SELECT se.id, se.company_id, c.name as company_name, c.industry,
                  se.to_email, se.subject, se.email_type, se.replied,
                  se.sent_by, se.sent_at, se.next_follow_up_at
           FROM sent_emails se
           JOIN companies c ON c.id = se.company_id
           ORDER BY se.sent_at DESC""",
    )
    return [{
        "id": r[0], "company_id": r[1], "company_name": r[2], "industry": r[3],
        "to_email": r[4], "subject": r[5], "email_type": r[6], "replied": bool(r[7]),
        "sent_by": r[8], "sent_at": r[9], "next_follow_up_at": r[10],
    } for r in rs.rows]


@app.get("/api/activity/unreached")
def get_unreached_companies():
    """Get companies that have emails found but no outreach started."""
    rs = execute(
        """SELECT c.id, c.name, c.industry, c.city, COUNT(e.id) as email_count
           FROM companies c
           JOIN hr_emails e ON e.company_id = c.id
           LEFT JOIN sent_emails se ON se.company_id = c.id
           WHERE se.id IS NULL
           GROUP BY c.id
           ORDER BY email_count DESC""",
    )
    return [{
        "id": r[0], "name": r[1], "industry": r[2], "city": r[3], "email_count": r[4],
    } for r in rs.rows]


# ── Boob Bus Info (editable context for AI emails) ───────────────────────────

@app.get("/api/boobbus-info")
def get_boobbus_info():
    """Get the Boob Bus context used for AI email generation."""
    rs = execute("SELECT value FROM settings WHERE key = 'boobbus_info'")
    if rs.rows:
        return {"info": rs.rows[0][0]}
    # Return the default hardcoded info
    from email_generator import BOOB_BUS_CONTEXT
    feedback = _get_setting("customer_feedback", "")
    return {"info": BOOB_BUS_CONTEXT.strip(), "customer_feedback": feedback}


class BoobBusInfoUpdate(BaseModel):
    info: str | None = None
    prompts: dict | None = None
    customer_feedback: str | None = None


@app.put("/api/boobbus-info-update")
def update_boobbus_info_v2(body: BoobBusInfoUpdate):
    """Update the Boob Bus context and/or email prompts."""
    result = {}

    if body.info is not None:
        _set_setting("boobbus_info", body.info)
        result["info"] = body.info

    if body.prompts is not None:
        for key, value in body.prompts.items():
            if key in ("initial", "follow_up", "follow_up_2", "follow_up_3", "final"):
                _set_setting(f"prompt_{key}", value)
        result["prompts"] = body.prompts

    if body.customer_feedback is not None:
        _set_setting("customer_feedback", body.customer_feedback)
        result["customer_feedback"] = body.customer_feedback

    return result


@app.get("/api/prompts")
def get_prompts():
    """Get all email prompt templates."""
    from email_generator import get_all_prompts, DEFAULT_PROMPTS
    return {
        "prompts": get_all_prompts(),
        "defaults": DEFAULT_PROMPTS,
    }


# ── Cron: Auto Follow-ups ────────────────────────────────────────────────────

# ── Test Sequence (server-side) ────────────────────────────────────────────────

import threading


class TestSequenceRequest(BaseModel):
    company_id: int
    contact_email: str
    contact_name: str | None = None
    contact_title: str | None = None
    test_email: str
    subject: str
    body: str


@app.post("/api/test-sequence")
def start_test_sequence(req: TestSequenceRequest, request: Request):
    """Run a test email sequence on the server. Sends initial immediately, follow-ups every 3 min."""
    from email_generator import generate_outreach_email
    from followup_engine import get_sequence_length
    import time as _time

    user = get_current_user(request)

    # Get Gmail token from stored refresh token
    rs = execute("SELECT refresh_token FROM gmail_tokens WHERE user_email = ?", [user["email"]])
    if not rs.rows:
        raise HTTPException(status_code=400, detail="Gmail not connected. Go to Settings first.")

    refresh_token = rs.rows[0][0]
    seq_length = get_sequence_length()

    # Build sequence types
    if seq_length == 2:
        follow_ups = ["final"]
    else:
        follow_ups = []
        for i in range(1, seq_length - 1):
            follow_ups.append(f"follow_up{'_' + str(i) if i > 1 else ''}")
        follow_ups.append("final")

    # Get company info
    company_rs = execute("SELECT name, industry, city FROM companies WHERE id = ?", [req.company_id])
    if not company_rs.rows:
        raise HTTPException(status_code=404, detail="Company not found")
    company = company_rs.rows[0]

    def _get_access_token():
        import requests as http_requests
        client_id = os.environ.get("GOOGLE_CLIENT_ID", "").strip()
        client_secret = os.environ.get("GOOGLE_CLIENT_SECRET", "").strip()
        resp = http_requests.post("https://oauth2.googleapis.com/token", data={
            "client_id": client_id, "client_secret": client_secret,
            "refresh_token": refresh_token, "grant_type": "refresh_token",
        }, timeout=10)
        if resp.status_code == 200:
            return resp.json().get("access_token")
        return None

    def _send_gmail(access_token, to, subj, body_text):
        import requests as http_requests
        import base64
        from email.mime.text import MIMEText
        msg = MIMEText(body_text)
        msg["To"] = to
        msg["Subject"] = subj
        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        resp = http_requests.post(
            "https://gmail.googleapis.com/gmail/v1/users/me/messages/send",
            headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
            json={"raw": raw}, timeout=15,
        )
        return resp.status_code == 200

    # Get test interval from settings
    test_interval = int(_get_setting("test_interval_seconds", "60"))

    # Get sender name
    profile_rs = execute("SELECT full_name FROM user_profiles WHERE email = ?", [user["email"]])
    sender_name = profile_rs.rows[0][0] if profile_rs.rows else user.get("name", "")

    def run_sequence():
        # Step 1: Send initial immediately
        token = _get_access_token()
        if not token:
            logger.error("Test sequence: failed to get Gmail token")
            return
        _send_gmail(token, req.test_email, f"[TEST 1/{seq_length}] {req.subject}", req.body)
        logger.info("Test sequence: sent step 1/%d to %s", seq_length, req.test_email)

        # Steps 2+: at configured interval
        for idx, email_type in enumerate(follow_ups):
            _time.sleep(test_interval)
            step = idx + 2
            try:
                draft = generate_outreach_email(
                    company_name=company[0], company_industry=company[1] or "Unknown",
                    company_city=company[2] or "Utah", contact_email=req.contact_email,
                    contact_name=req.contact_name, contact_title=req.contact_title,
                    email_type=email_type, company_id=req.company_id,
                    sender_name=sender_name, days_since_last=0,
                )
                token = _get_access_token()
                if token:
                    _send_gmail(token, req.test_email, f"[TEST {step}/{seq_length}] {draft['subject']}", draft["body"])
                    logger.info("Test sequence: sent step %d/%d to %s", step, seq_length, req.test_email)
            except Exception as e:
                logger.error("Test sequence step %d failed: %s", step, e)

    # Run in background thread so the API returns immediately
    thread = threading.Thread(target=run_sequence, daemon=True)
    thread.start()

    return {"status": "started", "total_steps": seq_length, "test_email": req.test_email}


# ── Gmail OAuth (refresh token) ───────────────────────────────────────────────

class GmailAuthRequest(BaseModel):
    code: str
    redirect_uri: str


@app.post("/api/gmail/authorize")
def gmail_authorize(body: GmailAuthRequest, request: Request):
    """Exchange an authorization code for access + refresh tokens."""
    import requests as http_requests

    client_id = os.environ.get("GOOGLE_CLIENT_ID", "").strip()
    client_secret = os.environ.get("GOOGLE_CLIENT_SECRET", "").strip()
    if not client_id or not client_secret:
        raise HTTPException(status_code=500, detail="Google OAuth not configured")

    # Exchange code for tokens
    resp = http_requests.post("https://oauth2.googleapis.com/token", data={
        "code": body.code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": body.redirect_uri,
        "grant_type": "authorization_code",
    }, timeout=15)

    if resp.status_code != 200:
        logger.error("Gmail OAuth token exchange failed: %s", resp.text)
        raise HTTPException(status_code=400, detail="Failed to exchange authorization code")

    tokens = resp.json()
    refresh_token = tokens.get("refresh_token")
    access_token = tokens.get("access_token")

    if not refresh_token:
        raise HTTPException(status_code=400, detail="No refresh token received. You may need to revoke access and re-authorize.")

    # Get user email from the access token
    user_resp = http_requests.get(
        "https://www.googleapis.com/oauth2/v2/userinfo",
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=10,
    )
    user_email = "unknown"
    if user_resp.status_code == 200:
        user_email = user_resp.json().get("email", "unknown")

    # Store the refresh token
    execute(
        """INSERT INTO gmail_tokens (user_email, refresh_token)
           VALUES (?, ?)
           ON CONFLICT(user_email) DO UPDATE SET refresh_token = excluded.refresh_token, updated_at = CURRENT_TIMESTAMP""",
        [user_email, refresh_token],
    )

    logger.info("Stored Gmail refresh token for %s", user_email)
    return {"status": "authorized", "email": user_email}


@app.get("/api/gmail/status")
def gmail_status(request: Request):
    """Check if a Gmail refresh token is stored for auto follow-ups."""
    user = get_current_user(request)
    rs = execute("SELECT user_email, updated_at FROM gmail_tokens WHERE user_email = ?", [user["email"]])
    if rs.rows:
        return {"authorized": True, "email": rs.rows[0][0], "updated_at": rs.rows[0][1]}
    return {"authorized": False}


# ── Email Open Tracking ───────────────────────────────────────────────────────

from fastapi.responses import Response
import uuid


@app.get("/api/track/{tracking_id}")
def track_email_open(tracking_id: str):
    """Tracking pixel endpoint. Logs when an email is opened."""
    # Update the open record
    rs = execute("SELECT sent_email_id, open_count FROM email_opens WHERE tracking_id = ?", [tracking_id])
    if rs.rows:
        execute(
            "UPDATE email_opens SET opened_at = CURRENT_TIMESTAMP, open_count = open_count + 1 WHERE tracking_id = ?",
            [tracking_id],
        )

    # Return a 1x1 transparent GIF
    pixel = b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00\x21\xf9\x04\x00\x00\x00\x00\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02\x44\x01\x00\x3b'
    return Response(content=pixel, media_type="image/gif", headers={
        "Cache-Control": "no-store, no-cache, must-revalidate",
        "Pragma": "no-cache",
    })


@app.post("/api/cron/follow-ups", dependencies=[])
def run_follow_ups(request: Request):
    """Cron endpoint: check for replies and send follow-ups.

    Protected by a secret token instead of user auth.
    """
    cron_secret = os.environ.get("CRON_SECRET", "").strip()
    auth_header = request.headers.get("Authorization", "")
    provided = auth_header.replace("Bearer ", "") if auth_header.startswith("Bearer ") else ""
    if cron_secret and provided != cron_secret:
        raise HTTPException(status_code=403, detail="Invalid cron secret")

    from followup_engine import process_pending_followups
    result = process_pending_followups()
    logger.info("Follow-up cron: %s", result)
    return result


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

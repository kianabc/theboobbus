"""HR Email Finder API — Find HR department emails for top Utah companies."""

from dotenv import load_dotenv
load_dotenv()

import logging
import os
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Query
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
    email_count: int = 0


class HREmailOut(BaseModel):
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
        SELECT c.id, c.name, c.website, c.industry, c.city, COUNT(e.id) as email_count
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
    return [{"id": r[0], "name": r[1], "website": r[2], "industry": r[3], "city": r[4], "email_count": r[5]} for r in rs.rows]


@app.get("/api/companies/{company_id}", response_model=CompanyWithEmails)
def get_company(company_id: int):
    """Get a company and its cached HR emails."""
    rs = execute("SELECT id, name, website, industry, city FROM companies WHERE id = ?", [company_id])
    if not rs.rows:
        raise HTTPException(status_code=404, detail="Company not found")
    r = rs.rows[0]
    company = {"id": r[0], "name": r[1], "website": r[2], "industry": r[3], "city": r[4]}

    ers = execute(
        "SELECT email, confidence, source FROM hr_emails WHERE company_id = ? ORDER BY confidence DESC",
        [company_id],
    )
    company["hr_emails"] = [{"email": e[0], "confidence": e[1], "source": e[2]} for e in ers.rows]
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
def generate_email(body: GenerateEmailRequest):
    """Generate a personalized outreach email using AI."""
    from email_generator import generate_outreach_email

    rs = execute("SELECT name, industry, city FROM companies WHERE id = ?", [body.company_id])
    if not rs.rows:
        raise HTTPException(status_code=404, detail="Company not found")

    company = rs.rows[0]
    result = generate_outreach_email(
        company_name=company[0],
        company_industry=company[1] or "Unknown",
        company_city=company[2] or "Utah",
        contact_email=body.contact_email,
        contact_name=body.contact_name,
        contact_title=body.contact_title,
        email_type=body.email_type,
    )
    return result


@app.post("/api/send-email")
def send_email(body: SendEmailRequest, request: Request):
    """Send an email via Gmail using the user's Google OAuth token.

    Requires the frontend to pass a Gmail access token.
    """
    gmail_token = request.headers.get("X-Gmail-Token", "")
    if not gmail_token:
        raise HTTPException(status_code=400, detail="Gmail access token required. Please grant Gmail permissions.")

    import base64
    from email.mime.text import MIMEText

    # Build the email
    msg = MIMEText(body.body)
    msg["To"] = body.to
    msg["Subject"] = body.subject
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

    if body.company_id:
        execute(
            """INSERT INTO sent_emails
               (company_id, to_email, subject, body, sent_by, email_type, gmail_message_id, next_follow_up_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            [body.company_id, body.to, body.subject, body.body,
             user_email, email_type, gmail_msg_id, next_follow_up],
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
        """SELECT id, to_email, subject, sent_by, email_type, replied, sent_at, next_follow_up_at
           FROM sent_emails WHERE company_id = ? ORDER BY sent_at DESC""",
        [company_id],
    )
    return [{
        "id": r[0], "to_email": r[1], "subject": r[2], "sent_by": r[3],
        "email_type": r[4], "replied": bool(r[5]), "sent_at": r[6],
        "next_follow_up_at": r[7],
    } for r in rs.rows]


# ── Settings ──────────────────────────────────────────────────────────────────

class SettingsUpdate(BaseModel):
    follow_up_days: int


@app.get("/api/settings")
def get_settings():
    """Get app settings."""
    from followup_engine import get_follow_up_days
    return {"follow_up_days": get_follow_up_days()}


@app.put("/api/settings")
def update_settings(body: SettingsUpdate):
    """Update app settings."""
    from followup_engine import set_follow_up_days
    if body.follow_up_days < 1 or body.follow_up_days > 30:
        raise HTTPException(status_code=400, detail="Follow-up days must be between 1 and 30")
    set_follow_up_days(body.follow_up_days)
    return {"follow_up_days": body.follow_up_days}


# ── Cron: Auto Follow-ups ────────────────────────────────────────────────────

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

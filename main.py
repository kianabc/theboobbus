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
from encryption import encrypt as enc_encrypt, decrypt as enc_decrypt
from rate_limit import check_rate_limit
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
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Gmail-Token", "X-Gmail-Refresh-Token"],
)


# Security headers middleware
from starlette.middleware.base import BaseHTTPMiddleware


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        if not request.url.path.startswith("/api/track/"):
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response


app.add_middleware(SecurityHeadersMiddleware)


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
    county: str | None = None


class GenerateCompaniesRequest(BaseModel):
    count: int = 10
    city: str | None = None
    county: str | None = None
    industry: str | None = None
    min_employees: int | None = 50
    prioritize_women: bool = False
    avoid_keywords: list[str] = []


class ProposedCompany(BaseModel):
    name: str
    website: str | None = None
    industry: str | None = None
    city: str | None = None
    county: str | None = None
    estimated_employees: str | None = None
    reasoning: str | None = None
    website_verified: bool = False
    already_exists: bool = False


class BulkAddRequest(BaseModel):
    companies: list[CompanyCreate]


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/api/industries", response_model=list[str])
def list_industries():
    """List all distinct industries."""
    rs = execute("SELECT DISTINCT industry FROM companies WHERE industry IS NOT NULL ORDER BY industry")
    return [r[0] for r in rs.rows]


@app.get("/api/cities", response_model=list[str])
def list_cities():
    """List all distinct cities."""
    rs = execute("SELECT DISTINCT city FROM companies WHERE city IS NOT NULL ORDER BY city")
    return [r[0] for r in rs.rows]


@app.get("/api/counties", response_model=list[str])
def list_counties():
    """List all distinct counties."""
    rs = execute("SELECT DISTINCT county FROM companies WHERE county IS NOT NULL ORDER BY county")
    return [r[0] for r in rs.rows]


@app.get("/api/companies", response_model=list[CompanyOut])
def list_companies(
    search: str | None = Query(None, description="Filter companies by name (case-insensitive)"),
    industry: str | None = Query(None, description="Filter by industry"),
    city: str | None = Query(None, description="Filter by city"),
    county: str | None = Query(None, description="Filter by county"),
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
    if city:
        query += " AND c.city = ?"
        params.append(city)
    if county:
        query += " AND c.county = ?"
        params.append(county)
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
        "INSERT INTO companies (name, website, industry, city, county) VALUES (?, ?, ?, ?, ?)",
        [body.name, body.website, body.industry, body.city, body.county],
    )
    company_id = rs.last_insert_rowid
    rs2 = execute("SELECT id, name, website, industry, city FROM companies WHERE id = ?", [company_id])
    r = rs2.rows[0]
    return {"id": r[0], "name": r[1], "website": r[2], "industry": r[3], "city": r[4]}


@app.post("/api/companies/generate", response_model=list[ProposedCompany])
def generate_company_suggestions(body: GenerateCompaniesRequest, request: Request):
    """Ask Claude to propose Utah companies matching filters. Does NOT insert."""
    from company_generator import generate_companies, verify_websites_parallel

    user = get_current_user(request)
    if not check_rate_limit(f"gen_co:{user['email']}", 10, 3600):
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Max 10 company generations per hour.")

    count = max(1, min(25, int(body.count or 10)))

    # Pull existing names (lowered) so we can ask Claude to avoid them AND flag dupes client-side
    rs = execute("SELECT name FROM companies")
    all_names = [r[0] for r in rs.rows]
    existing_lower = {n.lower().strip() for n in all_names}

    try:
        proposed = generate_companies(
            count=count,
            city=body.city or None,
            county=body.county or None,
            industry=body.industry or None,
            min_employees=body.min_employees,
            prioritize_women=body.prioritize_women,
            avoid_keywords=body.avoid_keywords or [],
            existing_names=all_names,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Company generation failed")
        raise HTTPException(status_code=500, detail=f"Generation failed: {e}")

    # Deduplicate Claude's output by lowered name
    seen = set()
    cleaned = []
    for c in proposed:
        nm = (c.get("name") or "").strip()
        if not nm or nm.lower() in seen:
            continue
        seen.add(nm.lower())
        cleaned.append(c)

    # Verify websites in parallel
    urls = [(c.get("website") or "") for c in cleaned]
    verified = verify_websites_parallel(urls) if urls else []

    results = []
    for c, ok in zip(cleaned, verified):
        nm = (c.get("name") or "").strip()
        results.append(ProposedCompany(
            name=nm,
            website=c.get("website"),
            industry=c.get("industry"),
            city=c.get("city"),
            county=c.get("county"),
            estimated_employees=c.get("estimated_employees"),
            reasoning=c.get("reasoning"),
            website_verified=bool(ok),
            already_exists=nm.lower() in existing_lower,
        ))
    return results


@app.post("/api/companies/bulk", status_code=201)
def bulk_add_companies(body: BulkAddRequest, request: Request):
    """Insert multiple approved companies. Skips exact-name duplicates."""
    get_current_user(request)  # auth

    if not body.companies:
        return {"added": 0, "skipped": 0, "ids": []}

    # Fetch existing names to skip dupes
    rs = execute("SELECT name FROM companies")
    existing = {r[0].lower().strip() for r in rs.rows}

    added_ids = []
    skipped = 0
    for c in body.companies:
        nm = (c.name or "").strip()
        if not nm or nm.lower() in existing:
            skipped += 1
            continue
        rs = execute(
            "INSERT INTO companies (name, website, industry, city, county) VALUES (?, ?, ?, ?, ?)",
            [nm, c.website, c.industry, c.city or "Utah", c.county],
        )
        added_ids.append(rs.last_insert_rowid)
        existing.add(nm.lower())

    return {"added": len(added_ids), "skipped": skipped, "ids": added_ids}


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


import re

def _validate_email(email: str) -> bool:
    return bool(re.match(r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$', email))


class AddContactRequest(BaseModel):
    email: str
    name: str | None = None
    title: str | None = None


@app.post("/api/companies/{company_id}/contacts")
def add_contact(company_id: int, body: AddContactRequest):
    """Manually add a contact to a company."""
    if not _validate_email(body.email):
        raise HTTPException(status_code=400, detail="Invalid email format")
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

    # Rate limit: 20 generations per hour per user
    user_rl = get_current_user(request)
    if not check_rate_limit(f"gen:{user_rl['email']}", 20, 3600):
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Max 20 AI generations per hour.")

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


# ── Bulk compose (multi-contact outreach) ──────────────────────────────────────

class BulkContact(BaseModel):
    email: str
    name: str | None = None
    title: str | None = None


class BulkGenerateRequest(BaseModel):
    company_id: int
    contacts: list[BulkContact]
    angle_hint: str | None = None
    email_type: str = "initial"


class BulkDraft(BaseModel):
    contact_email: str
    contact_name: str | None = None
    contact_title: str | None = None
    subject: str
    body: str


@app.post("/api/bulk-generate", response_model=list[BulkDraft])
def bulk_generate_emails(body: BulkGenerateRequest, request: Request):
    """Generate personalized drafts for multiple contacts in parallel."""
    from email_generator import generate_outreach_email
    from concurrent.futures import ThreadPoolExecutor

    user = get_current_user(request)

    if len(body.contacts) == 0:
        raise HTTPException(status_code=400, detail="No contacts provided")
    if len(body.contacts) > 5:
        raise HTTPException(status_code=400, detail="Maximum 5 contacts per bulk generation")

    # Rate limit budgets against the same bucket as single generation.
    # Reserve N slots up front — fail fast if we can't.
    for _ in range(len(body.contacts)):
        if not check_rate_limit(f"gen:{user['email']}", 20, 3600):
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit would be exceeded. Max 20 AI generations per hour; only partial reservation possible.",
            )

    co_rs = execute("SELECT name, industry, city FROM companies WHERE id = ?", [body.company_id])
    if not co_rs.rows:
        raise HTTPException(status_code=404, detail="Company not found")
    co = co_rs.rows[0]

    profile_rs = execute("SELECT full_name FROM user_profiles WHERE email = ?", [user["email"]])
    sender_name = profile_rs.rows[0][0] if profile_rs.rows else user.get("name", "")

    def gen_one(contact: BulkContact) -> BulkDraft | None:
        try:
            result = generate_outreach_email(
                company_name=co[0],
                company_industry=co[1] or "Unknown",
                company_city=co[2] or "Utah",
                contact_email=contact.email,
                contact_name=contact.name,
                contact_title=contact.title,
                email_type=body.email_type,
                company_id=body.company_id,
                sender_name=sender_name,
                angle_hint=body.angle_hint,
            )
            # Save draft so it persists if the user navigates away
            execute(
                """INSERT INTO email_drafts (company_id, contact_email, subject, body, updated_at)
                   VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                   ON CONFLICT(company_id, contact_email)
                   DO UPDATE SET subject = excluded.subject, body = excluded.body, updated_at = CURRENT_TIMESTAMP""",
                [body.company_id, contact.email, result["subject"], result["body"]],
            )
            return BulkDraft(
                contact_email=contact.email,
                contact_name=contact.name,
                contact_title=contact.title,
                subject=result["subject"],
                body=result["body"],
            )
        except Exception as e:
            logger.error("Bulk generate failed for %s: %s", contact.email, e)
            return None

    with ThreadPoolExecutor(max_workers=min(5, len(body.contacts))) as pool:
        results = list(pool.map(gen_one, body.contacts))

    drafts = [r for r in results if r is not None]
    if not drafts:
        raise HTTPException(status_code=502, detail="All generations failed")
    return drafts


class BulkSendItem(BaseModel):
    contact_email: str
    contact_name: str | None = None
    contact_title: str | None = None
    subject: str
    body: str


class BulkSendRequest(BaseModel):
    company_id: int
    emails: list[BulkSendItem]


@app.post("/api/bulk-send")
def bulk_send(body: BulkSendRequest, request: Request):
    """Schedule bulk sends with randomized jitter (30–120s between emails).

    First email fires immediately (synchronously so the user sees an instant
    success signal). Remaining emails are scheduled in `scheduled_sends` and
    processed by the per-minute cron. Jitter helps avoid spam-filter flags.
    """
    from datetime import datetime, timedelta, timezone
    from gmail_sender import send_gmail_message
    import requests as http_requests

    user = get_current_user(request)

    if not body.emails:
        raise HTTPException(status_code=400, detail="No emails provided")
    if len(body.emails) > 5:
        raise HTTPException(status_code=400, detail="Maximum 5 emails per bulk send")

    # Rate limit — reserve N slots now so we don't schedule more than allowed/hr
    for _ in range(len(body.emails)):
        if not check_rate_limit(f"send:{user['email']}", 10, 3600):
            raise HTTPException(
                status_code=429,
                detail="Rate limit would be exceeded. Max 10 emails per hour per user.",
            )

    # Get the user's Gmail access token (same pattern as /api/send-email)
    rs = execute("SELECT refresh_token FROM gmail_tokens WHERE user_email = ?", [user["email"]])
    if not rs.rows:
        raise HTTPException(status_code=400, detail="Gmail not connected. Go to Settings.")

    refresh_token = enc_decrypt(rs.rows[0][0])
    client_id = os.environ.get("GOOGLE_CLIENT_ID", "").strip()
    client_secret = os.environ.get("GOOGLE_CLIENT_SECRET", "").strip()
    tok_resp = http_requests.post("https://oauth2.googleapis.com/token", data={
        "client_id": client_id, "client_secret": client_secret,
        "refresh_token": refresh_token, "grant_type": "refresh_token",
    }, timeout=10)
    if tok_resp.status_code != 200:
        raise HTTPException(status_code=502, detail="Failed to refresh Gmail token. Reconnect Gmail in Settings.")
    access_token = tok_resp.json().get("access_token")

    # Send the FIRST email synchronously
    first = body.emails[0]
    first_result = send_gmail_message(
        access_token=access_token,
        to=first.contact_email,
        subject=first.subject,
        body=first.body,
    )

    immediate_results: list[dict] = []

    if first_result["ok"]:
        # Log to sent_emails for follow-up tracking
        from followup_engine import get_follow_up_days
        follow_up_days = get_follow_up_days()
        next_follow_up = (datetime.now(timezone.utc) + timedelta(days=follow_up_days)).isoformat()
        execute(
            """INSERT INTO sent_emails
               (company_id, to_email, subject, body, sent_by, email_type, gmail_message_id,
                thread_id, message_id_header, next_follow_up_at)
               VALUES (?, ?, ?, ?, ?, 'initial', ?, ?, ?, ?)""",
            [
                body.company_id, first.contact_email, first.subject, first.body,
                user["email"], first_result["gmail_message_id"],
                first_result["thread_id"], first_result["message_id_header"],
                next_follow_up,
            ],
        )
        # Clear the draft since it's been sent
        execute(
            "DELETE FROM email_drafts WHERE company_id = ? AND contact_email = ?",
            [body.company_id, first.contact_email],
        )
        immediate_results.append({"contact_email": first.contact_email, "status": "sent"})
    else:
        immediate_results.append({
            "contact_email": first.contact_email,
            "status": "failed",
            "error": first_result["error"],
        })

    # Schedule remaining emails. No pre-computed send_at jitter — the cron
    # applies 15–30s sleep between sends within each tick. Simpler and gives
    # true spacing in Gmail's eyes.
    scheduled = 0
    now = datetime.now(timezone.utc)
    for item in body.emails[1:]:
        send_at = now  # due immediately; cron drains with per-email sleep
        execute(
            """INSERT INTO scheduled_sends
               (user_email, test_email, company_id, contact_email, contact_name,
                contact_title, email_type, step_num, total_steps, send_at, status,
                kind, subject, body)
               VALUES (?, ?, ?, ?, ?, ?, 'initial', 1, 1, ?, 'pending', 'production', ?, ?)""",
            [
                user["email"], item.contact_email, body.company_id, item.contact_email,
                item.contact_name, item.contact_title,
                send_at.isoformat(), item.subject, item.body,
            ],
        )
        scheduled += 1

    # Rough ETA: cron sends ~10/min with jitter, so N emails take ~N * 22s / 10 min
    estimated_seconds = scheduled * 25
    return {
        "status": "queued",
        "sent_immediately": immediate_results,
        "scheduled": scheduled,
        "estimated_last_send_seconds": estimated_seconds,
    }


@app.post("/api/send-email")
def send_email(body: SendEmailRequest, request: Request):
    """Send an email via Gmail.

    Uses stored refresh token if available, otherwise requires X-Gmail-Token header.
    """
    import requests as http_requests

    # Validate recipient email
    if not _validate_email(body.to):
        raise HTTPException(status_code=400, detail="Invalid recipient email format")

    # Rate limit: 10 emails per hour per user
    user = get_current_user(request)
    if not check_rate_limit(f"send:{user['email']}", 10, 3600):
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Max 10 emails per hour.")

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
                "refresh_token": enc_decrypt(rs.rows[0][0]),
                "grant_type": "refresh_token",
            }, timeout=10)
            if resp.status_code == 200:
                gmail_token = resp.json().get("access_token", "")

    if not gmail_token:
        raise HTTPException(status_code=400, detail="Gmail not connected. Go to Settings to connect your Gmail account.")

    from gmail_sender import send_gmail_message, get_thread_anchor

    # Generate tracking pixel
    tracking_id = str(uuid.uuid4())
    base_url = request.headers.get("Origin", "https://theboobbus.vercel.app")
    tracking_url = f"{base_url}/api/track/{tracking_id}"
    tracking_pixel = f'<img src="{tracking_url}" width="1" height="1" style="display:none" />'

    # If this is a follow-up and we have an existing thread for this contact,
    # send as a proper threaded reply (In-Reply-To + threadId + "Re: root").
    email_type = getattr(body, "email_type", "initial") or "initial"
    anchor = None
    if email_type != "initial" and body.company_id:
        anchor = get_thread_anchor(body.company_id, body.to)

    subject_to_send = body.subject
    if anchor and anchor.get("root_subject"):
        subject_to_send = anchor["root_subject"]  # Gmail sender will add "Re: "

    # Build HTML body with tracking pixel (preserves line breaks)
    html_body = body.body.replace("\n", "<br>") + tracking_pixel

    result = send_gmail_message(
        access_token=gmail_token,
        to=body.to,
        subject=subject_to_send,
        body=body.body,
        html_body=html_body,
        reply_to_message_id=anchor["message_id_header"] if anchor else None,
        reply_to_thread_id=anchor["thread_id"] if anchor else None,
    )

    if not result["ok"]:
        logger.error("Gmail send error: %s", result["error"])
        raise HTTPException(status_code=502, detail="Failed to send email. Please check your Gmail connection in Settings.")

    # Log the sent email with follow-up scheduling
    gmail_msg_id = result["gmail_message_id"] or ""
    thread_id = result["thread_id"]
    message_id_header = result["message_id_header"]
    user_email = get_current_user(request).get("email", "unknown")

    from followup_engine import get_follow_up_days
    from datetime import datetime, timedelta, timezone
    follow_up_days = get_follow_up_days()
    next_follow_up = None
    if email_type != "final":
        next_follow_up = (datetime.now(timezone.utc) + timedelta(days=follow_up_days)).isoformat()

    # Store the subject we ACTUALLY sent (after Re: prefix logic), so replies keep threading.
    stored_subject = f"Re: {anchor['root_subject']}" if anchor and anchor.get("root_subject") else body.subject

    sent_email_id = None
    if body.company_id:
        rs_insert = execute(
            """INSERT INTO sent_emails
               (company_id, to_email, subject, body, sent_by, email_type, gmail_message_id,
                thread_id, message_id_header, next_follow_up_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            [body.company_id, body.to, stored_subject, body.body,
             user_email, email_type, gmail_msg_id, thread_id, message_id_header, next_follow_up],
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
            [user_email, enc_encrypt(gmail_refresh)],
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
    email_signature: str | None = None
    email_model: str | None = None


def _mask_key(key: str) -> str:
    """Mask an API key, showing only last 4 characters."""
    if not key or len(key) < 8:
        return "****" if key else ""
    return "****" + key[-4:]


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
        "hunter_api_key": _mask_key(_get_setting("hunter_api_key") or os.environ.get("HUNTER_API_KEY", "")),
        "hunter_api_key_set": bool(_get_setting("hunter_api_key") or os.environ.get("HUNTER_API_KEY", "")),
        "apollo_enabled": _get_setting("apollo_enabled", "true") == "true",
        "apollo_api_key": _mask_key(_get_setting("apollo_api_key") or os.environ.get("APOLLO_API_KEY", "")),
        "apollo_api_key_set": bool(_get_setting("apollo_api_key") or os.environ.get("APOLLO_API_KEY", "")),
        "scraping_enabled": _get_setting("scraping_enabled", "true") == "true",
        "anthropic_api_key": _mask_key(_get_setting("anthropic_api_key") or os.environ.get("ANTHROPIC_API_KEY", "")),
        "anthropic_api_key_set": bool(_get_setting("anthropic_api_key") or os.environ.get("ANTHROPIC_API_KEY", "")),
        "email_signature": _get_setting("email_signature", "{sender_name}\nThe Boob Bus\nhttps://theboobbus.com\n(866) 747-BOOB"),
        "email_model": _get_setting("email_model", "claude-opus-4-6"),
    }


# Catalog of selectable models for email generation (exposed to the UI).
# Costs are rough per-email estimates (~1800 input tokens + 500 output) in USD.
EMAIL_MODELS = [
    {
        "id": "claude-opus-4-6",
        "name": "Claude Opus 4.6",
        "tier": "Top quality",
        "cost_per_email": 0.06,
        "description": "Most nuanced tone, best at avoiding AI-templated phrasing. Best for real prospect outreach.",
    },
    {
        "id": "claude-sonnet-4-6",
        "name": "Claude Sonnet 4.6",
        "tier": "Balanced",
        "cost_per_email": 0.013,
        "description": "Strong quality at ~4x lower cost. Good default for high-volume outreach.",
    },
    {
        "id": "claude-haiku-4-5-20251001",
        "name": "Claude Haiku 4.5",
        "tier": "Fast & cheap",
        "cost_per_email": 0.004,
        "description": "Fastest and cheapest. Noticeably more template-y — fine for internal tests.",
    },
]


@app.get("/api/email-models")
def list_email_models():
    """List available models for email generation with cost estimates."""
    return EMAIL_MODELS


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
        logger.info("AUDIT: API key updated (hunter) by user")
    if body.apollo_enabled is not None:
        _set_setting("apollo_enabled", "true" if body.apollo_enabled else "false")
    if body.apollo_api_key is not None:
        _set_setting("apollo_api_key", body.apollo_api_key)
        logger.info("AUDIT: API key updated (apollo) by user")
    if body.scraping_enabled is not None:
        _set_setting("scraping_enabled", "true" if body.scraping_enabled else "false")
    if body.anthropic_api_key is not None:
        _set_setting("anthropic_api_key", body.anthropic_api_key)
        logger.info("AUDIT: API key updated (anthropic) by user")
    if body.email_signature is not None:
        _set_setting("email_signature", body.email_signature)
    if body.email_model is not None:
        valid_ids = {m["id"] for m in EMAIL_MODELS}
        if body.email_model not in valid_ids:
            raise HTTPException(status_code=400, detail=f"Unknown email_model. Must be one of: {sorted(valid_ids)}")
        _set_setting("email_model", body.email_model)
        logger.info("AUDIT: email model changed to %s", body.email_model)
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

    refresh_token = enc_decrypt(rs.rows[0][0])
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

    # Hardcoded: test-sequence emails are 20 seconds apart. Synchronous in the
    # request so spacing is real. Worst case with 5 emails: 4 gaps × 20s + 5
    # sends × ~2s ≈ 90s, comfortably under the 300s maxDuration.
    TEST_INTERVAL_SECONDS = 20
    import time as _time

    # Get sender name
    profile_rs = execute("SELECT full_name FROM user_profiles WHERE email = ?", [user["email"]])
    sender_name = profile_rs.rows[0][0] if profile_rs.rows else user.get("name", "")

    from gmail_sender import send_gmail_message
    sent_count = 0
    errors: list[str] = []

    token = _get_access_token()
    if not token:
        raise HTTPException(status_code=400, detail="Failed to refresh Gmail token. Reconnect Gmail in Settings.")

    # Step 1: the initial test email — starts a fresh thread.
    step1_subject = f"[TEST 1/{seq_length}] {req.subject}"
    step1_result = send_gmail_message(
        access_token=token,
        to=req.test_email,
        subject=step1_subject,
        body=req.body,
    )
    if not step1_result["ok"]:
        raise HTTPException(status_code=502, detail=f"Failed to send test email: {step1_result['error']}")
    sent_count += 1
    logger.info("Test sequence: sent step 1/%d to %s", seq_length, req.test_email)

    anchor_message_id = step1_result["message_id_header"]
    anchor_thread_id = step1_result["thread_id"]

    # Steps 2..N: generate via AI and send as threaded replies, 10s apart.
    for idx, email_type in enumerate(follow_ups):
        step = idx + 2
        _time.sleep(TEST_INTERVAL_SECONDS)

        try:
            draft = generate_outreach_email(
                company_name=company[0],
                company_industry=company[1] or "Unknown",
                company_city=company[2] or "Utah",
                contact_email=req.contact_email,
                contact_name=req.contact_name,
                contact_title=req.contact_title,
                email_type=email_type,
                company_id=req.company_id,
                sender_name=sender_name,
                days_since_last=0,
            )
            step_subject = f"[TEST {step}/{seq_length}] {draft['subject']}"
            # Refresh the access token for each send — refreshes are cheap and
            # tokens expire in 1 hour but we want robustness over efficiency here.
            step_token = _get_access_token() or token
            step_result = send_gmail_message(
                access_token=step_token,
                to=req.test_email,
                subject=step_subject,
                body=draft["body"],
                reply_to_message_id=anchor_message_id,
                reply_to_thread_id=anchor_thread_id,
            )
            if step_result["ok"]:
                sent_count += 1
                logger.info("Test sequence: sent step %d/%d to %s", step, seq_length, req.test_email)
            else:
                errors.append(f"step {step}: {step_result['error']}")
        except Exception as e:
            logger.exception("Test sequence step %d failed", step)
            errors.append(f"step {step}: {e}")

    return {
        "status": "complete",
        "sent": sent_count,
        "total_steps": seq_length,
        "test_email": req.test_email,
        "errors": errors,
    }


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
        [user_email, enc_encrypt(refresh_token)],
    )

    logger.info("Stored encrypted Gmail refresh token for %s", user_email)
    return {"status": "authorized", "email": user_email}


@app.get("/api/gmail/status")
def gmail_status(request: Request):
    """Check if a Gmail refresh token is stored for auto follow-ups."""
    user = get_current_user(request)
    rs = execute("SELECT user_email, updated_at FROM gmail_tokens WHERE user_email = ?", [user["email"]])
    if rs.rows:
        return {"authorized": True, "email": rs.rows[0][0], "updated_at": rs.rows[0][1]}
    return {"authorized": False}


@app.delete("/api/gmail/disconnect")
def gmail_disconnect(request: Request):
    """Remove stored Gmail refresh token."""
    user = get_current_user(request)
    execute("DELETE FROM gmail_tokens WHERE user_email = ?", [user["email"]])
    logger.info("AUDIT: Gmail disconnected by %s", user["email"])
    return {"status": "disconnected"}


# ── Email Open Tracking ───────────────────────────────────────────────────────

from fastapi.responses import Response
import uuid


@app.get("/api/track/{tracking_id}")
def track_email_open(tracking_id: str):
    """Tracking pixel endpoint. Logs when an email is opened."""
    # Rate limit: max 10 opens per tracking ID per hour
    if not check_rate_limit(f"track:{tracking_id}", 10, 3600):
        pass  # Still return the pixel, just don't update DB
    else:
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

    Protected by cron secret AND Vercel cron auth header.
    """
    # Check Vercel's built-in cron auth header
    vercel_cron = request.headers.get("x-vercel-cron")

    # Check our custom cron secret
    cron_secret = os.environ.get("CRON_SECRET", "").strip()
    auth_header = request.headers.get("Authorization", "")
    provided = auth_header.replace("Bearer ", "") if auth_header.startswith("Bearer ") else ""

    # Must pass at least one auth check
    vercel_ok = vercel_cron is not None  # Vercel sets this header on cron calls
    secret_ok = cron_secret and provided == cron_secret

    if not vercel_ok and not secret_ok:
        logger.warning("Unauthorized cron attempt from %s", request.client.host if request.client else "unknown")
        raise HTTPException(status_code=403, detail="Unauthorized")

    from followup_engine import process_pending_followups
    result = process_pending_followups()
    logger.info("Follow-up cron: %s", result)
    return result


@app.post("/api/cron/scheduled-sends", dependencies=[])
def run_scheduled_sends(request: Request):
    """Cron endpoint: send due `scheduled_sends` rows with jittered pacing.

    Runs every minute on Vercel Pro. Processes up to 10 rows per tick, sleeping
    15–30s between each send for real Gmail-visible spacing. Uses row-level
    claiming (status='processing' + tick_id in error_message) so overlapping
    cron ticks don't double-send. Bails early if approaching maxDuration (300s),
    releasing unprocessed rows back to 'pending' for the next tick.
    """
    # Same auth as follow-ups cron
    vercel_cron = request.headers.get("x-vercel-cron")
    cron_secret = os.environ.get("CRON_SECRET", "").strip()
    auth_header = request.headers.get("Authorization", "")
    provided = auth_header.replace("Bearer ", "") if auth_header.startswith("Bearer ") else ""
    if not (vercel_cron or (cron_secret and provided == cron_secret)):
        logger.warning("Unauthorized scheduled-sends cron attempt")
        raise HTTPException(status_code=403, detail="Unauthorized")

    from datetime import datetime, timezone
    from email_generator import generate_outreach_email
    from gmail_sender import send_gmail_message
    import requests as http_requests
    import random
    import time as _time

    # Budget: vercel maxDuration is 300s. Leave a safety margin of 30s for
    # token refreshes, DB hiccups, and the final response flush.
    MAX_RUNTIME_SECONDS = 270
    JITTER_MIN = 15
    JITTER_MAX = 30
    PER_EMAIL_BUDGET = 27  # avg sleep (22.5) + gmail send (~2) + ai gen (~2-3)
    # Cap: how many rows to consider in one tick. At ~27s each, 10 fits in 270s.
    BATCH_LIMIT = 10

    tick_start = _time.monotonic()
    now_iso = datetime.now(timezone.utc).isoformat()

    # SERIALIZATION: if another tick is still running (has 'processing' rows),
    # exit immediately. Otherwise all 15–30s jitter is nullified by overlapping
    # ticks sending concurrently from the same Gmail account.
    # Stuck-row safety: the tick_id we stamp into error_message encodes the
    # claim time in ms. Reclaim rows whose claiming tick is >15min old —
    # that tick definitely crashed (Vercel maxDuration is 300s).
    stale_ms_cutoff = int((_time.time() - 15 * 60) * 1000)
    stale_rs = execute(
        "SELECT id, error_message FROM scheduled_sends WHERE status = 'processing'"
    )
    for sr in stale_rs.rows:
        sid_stale, err_msg = sr
        if err_msg and err_msg.startswith("tick-"):
            try:
                claim_ms = int(err_msg.split("-", 1)[1])
                if claim_ms < stale_ms_cutoff:
                    execute(
                        "UPDATE scheduled_sends SET status = 'pending', error_message = NULL WHERE id = ?",
                        [sid_stale],
                    )
            except (ValueError, IndexError):
                pass

    # Re-check after reaping
    in_flight = execute(
        "SELECT COUNT(*) FROM scheduled_sends WHERE status = 'processing'"
    )
    if in_flight.rows and in_flight.rows[0][0] > 0:
        logger.info("scheduled-sends: another tick in flight, exiting")
        return {"processed": 0, "sent": 0, "failed": 0, "skipped_concurrent": True}

    # CLAIM rows atomically so this tick owns them.
    tick_id = f"tick-{int(tick_start * 1000)}"
    execute(
        """UPDATE scheduled_sends
           SET status = 'processing', error_message = ?
           WHERE id IN (
               SELECT id FROM scheduled_sends
               WHERE status = 'pending' AND send_at <= ?
               ORDER BY send_at ASC
               LIMIT ?
           )""",
        [tick_id, now_iso, BATCH_LIMIT],
    )

    rs = execute(
        """SELECT id, user_email, test_email, company_id, contact_email,
                  contact_name, contact_title, email_type, step_num, total_steps,
                  reply_to_message_id, reply_to_thread_id, kind, subject, body
           FROM scheduled_sends
           WHERE status = 'processing' AND error_message = ?
           ORDER BY send_at ASC""",
        [tick_id],
    )

    if not rs.rows:
        return {"processed": 0, "sent": 0, "failed": 0}

    # Cache refreshed access tokens per user_email so we don't refresh 5 times
    tokens: dict[str, str | None] = {}

    def _token_for(user_email: str) -> str | None:
        if user_email in tokens:
            return tokens[user_email]
        tr = execute("SELECT refresh_token FROM gmail_tokens WHERE user_email = ?", [user_email])
        if not tr.rows:
            tokens[user_email] = None
            return None
        try:
            refresh_token = enc_decrypt(tr.rows[0][0])
        except Exception as e:
            logger.error("Failed to decrypt refresh token for %s: %s", user_email, e)
            tokens[user_email] = None
            return None
        client_id = os.environ.get("GOOGLE_CLIENT_ID", "").strip()
        client_secret = os.environ.get("GOOGLE_CLIENT_SECRET", "").strip()
        resp = http_requests.post("https://oauth2.googleapis.com/token", data={
            "client_id": client_id, "client_secret": client_secret,
            "refresh_token": refresh_token, "grant_type": "refresh_token",
        }, timeout=10)
        access = resp.json().get("access_token") if resp.status_code == 200 else None
        tokens[user_email] = access
        return access

    sent = 0
    failed = 0
    skipped_for_time = 0
    for idx, r in enumerate(rs.rows):
        # Bail if we're close to the maxDuration — release this row back to
        # 'pending' so the next cron tick (1 minute later) picks it up.
        elapsed = _time.monotonic() - tick_start
        if elapsed + PER_EMAIL_BUDGET > MAX_RUNTIME_SECONDS:
            # Release this and any remaining claimed-but-unprocessed rows
            remaining_ids = [row[0] for row in rs.rows[idx:]]
            if remaining_ids:
                placeholders = ",".join("?" for _ in remaining_ids)
                execute(
                    f"UPDATE scheduled_sends SET status = 'pending', error_message = NULL WHERE id IN ({placeholders})",
                    remaining_ids,
                )
                skipped_for_time = len(remaining_ids)
            break

        # Sleep BEFORE sending (not before the first) to space out Gmail sends
        if idx > 0:
            _time.sleep(random.randint(JITTER_MIN, JITTER_MAX))

        (sid, user_email, test_email, company_id, contact_email,
         contact_name, contact_title, email_type, step_num, total_steps,
         reply_to_message_id, reply_to_thread_id, kind, stored_subject, stored_body) = r

        try:
            token = _token_for(user_email)
            if not token:
                execute(
                    "UPDATE scheduled_sends SET status = 'failed', error_message = ?, sent_at = ? WHERE id = ?",
                    ["no gmail token", now_iso, sid],
                )
                failed += 1
                continue

            kind = kind or "test"

            if kind == "followup":
                # Generate the follow-up fresh, thread into the existing conversation,
                # log to sent_emails, and schedule the next step (if any).
                from email_generator import generate_outreach_email
                from gmail_sender import get_thread_anchor
                from followup_engine import (
                    get_sequence, get_follow_up_days, STEP_TO_EMAIL_TYPE,
                )
                from datetime import timedelta

                co_rs = execute("SELECT name, industry, city FROM companies WHERE id = ?", [company_id])
                if not co_rs.rows:
                    execute(
                        "UPDATE scheduled_sends SET status = 'failed', error_message = ?, sent_at = ? WHERE id = ?",
                        ["company not found", now_iso, sid],
                    )
                    failed += 1
                    continue
                co = co_rs.rows[0]

                profile_rs = execute("SELECT full_name FROM user_profiles WHERE email = ?", [user_email])
                sender_name = profile_rs.rows[0][0] if profile_rs.rows else user_email

                # Map follow_up_1/2/3 step name → AI email_type (follow_up/follow_up_2/etc.)
                ai_email_type = STEP_TO_EMAIL_TYPE.get(email_type, "follow_up")

                try:
                    draft = generate_outreach_email(
                        company_name=co[0],
                        company_industry=co[1] or "Unknown",
                        company_city=co[2] or "Utah",
                        contact_email=contact_email,
                        contact_name=None,
                        contact_title=None,
                        email_type=ai_email_type,
                        company_id=company_id,
                        sender_name=sender_name,
                        days_since_last=get_follow_up_days(),
                    )
                except Exception as e:
                    execute(
                        "UPDATE scheduled_sends SET status = 'failed', error_message = ?, sent_at = ? WHERE id = ?",
                        [f"generate: {e}"[:500], now_iso, sid],
                    )
                    failed += 1
                    continue

                anchor = get_thread_anchor(company_id, contact_email)
                subject_to_send = (anchor["root_subject"] if anchor and anchor.get("root_subject")
                                   else draft["subject"])

                from gmail_sender import send_gmail_message as _send
                result = _send(
                    access_token=token,
                    to=contact_email,
                    subject=subject_to_send,
                    body=draft["body"],
                    reply_to_message_id=anchor["message_id_header"] if anchor else None,
                    reply_to_thread_id=anchor["thread_id"] if anchor else None,
                )

                if not result["ok"]:
                    execute(
                        "UPDATE scheduled_sends SET status = 'failed', error_message = ?, sent_at = ? WHERE id = ?",
                        [result["error"][:500], now_iso, sid],
                    )
                    failed += 1
                    continue

                # Schedule the next follow-up if this wasn't the final step
                sequence = get_sequence()
                next_follow_up = None
                if email_type != "final":
                    current_idx = sequence.index(email_type) if email_type in sequence else 0
                    if current_idx + 1 < len(sequence):
                        next_follow_up = (datetime.now(timezone.utc)
                                          + timedelta(days=get_follow_up_days())).isoformat()

                stored_subject = (f"Re: {anchor['root_subject']}"
                                  if anchor and anchor.get("root_subject")
                                  else draft["subject"])

                execute(
                    """INSERT INTO sent_emails
                       (company_id, to_email, subject, body, sent_by, email_type, gmail_message_id,
                        thread_id, message_id_header, next_follow_up_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    [company_id, contact_email, stored_subject, draft["body"],
                     user_email, email_type, result["gmail_message_id"],
                     result["thread_id"], result["message_id_header"],
                     next_follow_up],
                )
                execute(
                    "UPDATE scheduled_sends SET status = 'sent', sent_at = ? WHERE id = ?",
                    [now_iso, sid],
                )
                sent += 1
                logger.info("Follow-up sent: type=%s to %s (sid=%d)", email_type, contact_email, sid)
                continue

            if kind == "production":
                # Pre-baked subject/body from the bulk composer. No AI call.
                recipient = contact_email
                subject_to_send = stored_subject or ""
                body_to_send = stored_body or ""

                result = send_gmail_message(
                    access_token=token,
                    to=recipient,
                    subject=subject_to_send,
                    body=body_to_send,
                )

                if result["ok"]:
                    # Log to sent_emails for follow-up tracking (initial email)
                    from followup_engine import get_follow_up_days
                    from datetime import timedelta
                    follow_up_days = get_follow_up_days()
                    next_follow_up = (datetime.now(timezone.utc) + timedelta(days=follow_up_days)).isoformat()
                    execute(
                        """INSERT INTO sent_emails
                           (company_id, to_email, subject, body, sent_by, email_type, gmail_message_id,
                            thread_id, message_id_header, next_follow_up_at)
                           VALUES (?, ?, ?, ?, ?, 'initial', ?, ?, ?, ?)""",
                        [company_id, recipient, subject_to_send, body_to_send,
                         user_email, result["gmail_message_id"],
                         result["thread_id"], result["message_id_header"],
                         next_follow_up],
                    )
                    # Clear any lingering draft
                    execute(
                        "DELETE FROM email_drafts WHERE company_id = ? AND contact_email = ?",
                        [company_id, recipient],
                    )
                    execute(
                        "UPDATE scheduled_sends SET status = 'sent', sent_at = ? WHERE id = ?",
                        [now_iso, sid],
                    )
                    sent += 1
                    logger.info("Bulk production send: to %s (id=%d)", recipient, sid)
                else:
                    execute(
                        "UPDATE scheduled_sends SET status = 'failed', error_message = ?, sent_at = ? WHERE id = ?",
                        [result["error"][:500], now_iso, sid],
                    )
                    failed += 1
                continue

            # kind == "test" path: generate fresh via AI
            co_rs = execute("SELECT name, industry, city FROM companies WHERE id = ?", [company_id])
            if not co_rs.rows:
                execute(
                    "UPDATE scheduled_sends SET status = 'failed', error_message = ?, sent_at = ? WHERE id = ?",
                    ["company not found", now_iso, sid],
                )
                failed += 1
                continue
            co = co_rs.rows[0]

            profile_rs = execute("SELECT full_name FROM user_profiles WHERE email = ?", [user_email])
            sender_name = profile_rs.rows[0][0] if profile_rs.rows else user_email

            draft = generate_outreach_email(
                company_name=co[0],
                company_industry=co[1] or "Unknown",
                company_city=co[2] or "Utah",
                contact_email=contact_email,
                contact_name=contact_name,
                contact_title=contact_title,
                email_type=email_type,
                company_id=company_id,
                sender_name=sender_name,
                days_since_last=0,
            )

            subject = f"[TEST {step_num}/{total_steps}] {draft['subject']}"

            result = send_gmail_message(
                access_token=token,
                to=test_email,
                subject=subject,
                body=draft["body"],
                reply_to_message_id=reply_to_message_id,
                reply_to_thread_id=reply_to_thread_id,
            )

            if result["ok"]:
                execute(
                    "UPDATE scheduled_sends SET status = 'sent', sent_at = ? WHERE id = ?",
                    [now_iso, sid],
                )
                sent += 1
                logger.info("Scheduled test send: step %d/%d to %s (id=%d, threaded=%s)",
                            step_num, total_steps, test_email, sid, bool(reply_to_thread_id))
            else:
                execute(
                    "UPDATE scheduled_sends SET status = 'failed', error_message = ?, sent_at = ? WHERE id = ?",
                    [result["error"][:500], now_iso, sid],
                )
                failed += 1
        except Exception as e:
            logger.exception("Scheduled send id=%s failed", sid)
            try:
                execute(
                    "UPDATE scheduled_sends SET status = 'failed', error_message = ?, sent_at = ? WHERE id = ?",
                    [str(e)[:500], now_iso, sid],
                )
            except Exception:
                pass
            failed += 1

    return {
        "processed": len(rs.rows),
        "sent": sent,
        "failed": failed,
        "released_for_next_tick": skipped_for_time,
        "elapsed_seconds": round(_time.monotonic() - tick_start, 1),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

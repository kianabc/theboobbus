"""HR Email Finder API — Find HR department emails for top Utah companies."""

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from database import init_db, execute
from seed_data import seed_companies
from scraper import scrape_company

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
    title="Utah HR Email Finder",
    description="API to find HR department emails for top Utah companies across all industries.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
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
    query = "SELECT id, name, website, industry, city FROM companies WHERE 1=1"
    params: list = []
    if search:
        query += " AND name LIKE ?"
        params.append(f"%{search}%")
    if industry:
        query += " AND industry LIKE ?"
        params.append(f"%{industry}%")
    query += " ORDER BY name"
    rs = execute(query, params)
    return [{"id": r[0], "name": r[1], "website": r[2], "industry": r[3], "city": r[4]} for r in rs.rows]


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
    """Scrape a company's website for HR emails and cache the results."""
    rs = execute("SELECT id, name, website FROM companies WHERE id = ?", [company_id])
    if not rs.rows:
        raise HTTPException(status_code=404, detail="Company not found")

    row = rs.rows[0]
    website = row[2]
    if not website:
        raise HTTPException(status_code=400, detail="Company has no website URL to scrape")

    logger.info("Scraping %s (%s)", row[1], website)
    found_emails = scrape_company(website)

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


@app.get("/api/debug")
def debug_info():
    """Debug endpoint to diagnose deployment issues."""
    import traceback
    info = {
        "turso_url_set": bool(os.environ.get("TURSO_DATABASE_URL")),
        "turso_token_set": bool(os.environ.get("TURSO_AUTH_TOKEN")),
        "vercel": os.environ.get("VERCEL", "not set"),
    }
    try:
        rs = execute("SELECT COUNT(*) FROM companies")
        info["db_status"] = "connected"
        info["company_count"] = rs.rows[0][0]
    except Exception as e:
        info["db_status"] = "error"
        info["db_error"] = f"{type(e).__name__}: {e}"
        info["traceback"] = traceback.format_exc()
    return info


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

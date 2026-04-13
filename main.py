"""HR Email Finder API — Find HR department emails for top Utah companies."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from database import init_db, get_db
from seed_data import seed_companies
from scraper import scrape_company

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
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

@app.get("/industries", response_model=list[str])
def list_industries():
    """List all distinct industries."""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT DISTINCT industry FROM companies WHERE industry IS NOT NULL ORDER BY industry"
        ).fetchall()
    return [r["industry"] for r in rows]


@app.get("/companies", response_model=list[CompanyOut])
def list_companies(
    search: str | None = Query(None, description="Filter companies by name (case-insensitive)"),
    industry: str | None = Query(None, description="Filter by industry"),
):
    """List all companies, optionally filtered by name or industry."""
    with get_db() as conn:
        query = "SELECT id, name, website, industry, city FROM companies WHERE 1=1"
        params: list = []
        if search:
            query += " AND name LIKE ?"
            params.append(f"%{search}%")
        if industry:
            query += " AND industry LIKE ?"
            params.append(f"%{industry}%")
        query += " ORDER BY name"
        rows = conn.execute(query, params).fetchall()
    return [dict(r) for r in rows]


@app.get("/companies/{company_id}", response_model=CompanyWithEmails)
def get_company(company_id: int):
    """Get a company and its cached HR emails."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT id, name, website, industry, city FROM companies WHERE id = ?",
            (company_id,),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Company not found")
        company = dict(row)

        emails = conn.execute(
            "SELECT email, confidence, source FROM hr_emails WHERE company_id = ? ORDER BY confidence DESC",
            (company_id,),
        ).fetchall()
        company["hr_emails"] = [dict(e) for e in emails]
    return company


@app.post("/companies", response_model=CompanyOut, status_code=201)
def add_company(body: CompanyCreate):
    """Add a new company to track."""
    with get_db() as conn:
        cursor = conn.execute(
            "INSERT INTO companies (name, website, industry, city) VALUES (?, ?, ?, ?)",
            (body.name, body.website, body.industry, body.city),
        )
        company_id = cursor.lastrowid
        row = conn.execute(
            "SELECT id, name, website, industry, city FROM companies WHERE id = ?",
            (company_id,),
        ).fetchone()
    return dict(row)


@app.post("/companies/{company_id}/scrape", response_model=list[HREmailOut])
def scrape_company_emails(company_id: int):
    """Scrape a company's website for HR emails and cache the results."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT id, name, website FROM companies WHERE id = ?",
            (company_id,),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Company not found")

        website = row["website"]
        if not website:
            raise HTTPException(status_code=400, detail="Company has no website URL to scrape")

    logger.info("Scraping %s (%s)", row["name"], website)
    found_emails = scrape_company(website)

    with get_db() as conn:
        for item in found_emails:
            conn.execute(
                """INSERT INTO hr_emails (company_id, email, source, confidence)
                   VALUES (?, ?, ?, ?)
                   ON CONFLICT(company_id, email) DO UPDATE SET
                       source = excluded.source,
                       confidence = excluded.confidence,
                       scraped_at = CURRENT_TIMESTAMP""",
                (company_id, item["email"], item["source"], item["confidence"]),
            )

    return found_emails


@app.post("/scrape-all", response_model=dict)
def scrape_all_companies():
    """Scrape all companies in the database. This can take a while."""
    with get_db() as conn:
        rows = conn.execute("SELECT id, name, website FROM companies").fetchall()

    total_emails = 0
    companies_scraped = 0
    errors = []

    for row in rows:
        if not row["website"]:
            continue
        try:
            found = scrape_company(row["website"])
            with get_db() as conn:
                for item in found:
                    conn.execute(
                        """INSERT INTO hr_emails (company_id, email, source, confidence)
                           VALUES (?, ?, ?, ?)
                           ON CONFLICT(company_id, email) DO UPDATE SET
                               source = excluded.source,
                               confidence = excluded.confidence,
                               scraped_at = CURRENT_TIMESTAMP""",
                        (row["id"], item["email"], item["source"], item["confidence"]),
                    )
            total_emails += len(found)
            companies_scraped += 1
            logger.info("Scraped %s: found %d emails", row["name"], len(found))
        except Exception as e:
            logger.error("Error scraping %s: %s", row["name"], e)
            errors.append({"company": row["name"], "error": str(e)})

    return {
        "companies_scraped": companies_scraped,
        "total_emails_found": total_emails,
        "errors": errors,
    }


@app.get("/emails", response_model=list[dict])
def list_all_emails(
    confidence: str | None = Query(None, description="Filter by confidence: high, medium, low"),
):
    """List all cached HR emails across all companies."""
    with get_db() as conn:
        query = """
            SELECT c.name as company, c.industry, e.email, e.confidence, e.source
            FROM hr_emails e
            JOIN companies c ON c.id = e.company_id
            WHERE 1=1
        """
        params: list = []
        if confidence:
            query += " AND e.confidence = ?"
            params.append(confidence)
        query += " ORDER BY e.confidence DESC, c.name"
        rows = conn.execute(query, params).fetchall()
    return [dict(r) for r in rows]


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

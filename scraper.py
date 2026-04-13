"""Web scraper to find HR department emails from company websites."""

import re
import time
import logging
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

EMAIL_PATTERN = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")

HR_KEYWORDS = [
    "hr@", "humanresources@", "human.resources@", "human-resources@",
    "careers@", "jobs@", "recruiting@", "recruitment@", "talent@",
    "hiring@", "employment@", "people@", "peopleops@", "staffing@",
    "resume@", "resumes@", "apply@",
]

HR_PAGE_PATHS = [
    "/careers", "/jobs", "/about/careers", "/company/careers",
    "/join", "/join-us", "/work-with-us", "/contact",
    "/about/contact", "/company/contact", "/contact-us",
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    ),
}

REQUEST_TIMEOUT = 15


def _fetch_page(url: str) -> BeautifulSoup | None:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT, allow_redirects=True)
        resp.raise_for_status()
        return BeautifulSoup(resp.text, "lxml")
    except Exception as e:
        logger.debug("Failed to fetch %s: %s", url, e)
        return None


def _extract_emails(soup: BeautifulSoup) -> set[str]:
    emails = set()
    text = soup.get_text(separator=" ")
    emails.update(EMAIL_PATTERN.findall(text))

    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"]
        if href.startswith("mailto:"):
            email = href.replace("mailto:", "").split("?")[0].strip()
            if EMAIL_PATTERN.match(email):
                emails.add(email)

    # Filter out image/asset file extensions that look like emails
    filtered = set()
    for email in emails:
        lower = email.lower()
        if any(lower.endswith(ext) for ext in [".png", ".jpg", ".gif", ".svg", ".css", ".js"]):
            continue
        filtered.add(lower)
    return filtered


def _classify_email(email: str) -> tuple[str, str]:
    """Return (confidence, source_hint) for an email."""
    local = email.split("@")[0].lower()
    for kw in HR_KEYWORDS:
        prefix = kw.rstrip("@")
        if local == prefix or local.startswith(prefix):
            return "high", "HR keyword match"

    if any(word in local for word in ["hr", "career", "recruit", "talent", "people", "hiring", "job"]):
        return "medium", "Partial HR keyword"

    return "low", "General contact"


def scrape_company(website: str) -> list[dict]:
    """Scrape a company website for HR-related email addresses.

    Returns a list of dicts: {"email", "confidence", "source"}
    """
    if not website:
        return []

    parsed = urlparse(website)
    base = f"{parsed.scheme}://{parsed.netloc}"

    results = {}

    # 1. Scrape the homepage
    soup = _fetch_page(website)
    if soup:
        for email in _extract_emails(soup):
            confidence, source = _classify_email(email)
            if email not in results or _confidence_rank(confidence) > _confidence_rank(results[email]["confidence"]):
                results[email] = {"email": email, "confidence": confidence, "source": f"Homepage - {source}"}

    # 2. Scrape common HR/careers/contact pages
    for path in HR_PAGE_PATHS:
        url = urljoin(base, path)
        time.sleep(0.5)  # polite delay
        soup = _fetch_page(url)
        if soup:
            for email in _extract_emails(soup):
                confidence, source = _classify_email(email)
                page_name = path.strip("/").replace("/", " > ")
                source_label = f"/{page_name} page - {source}"
                if email not in results or _confidence_rank(confidence) > _confidence_rank(results[email]["confidence"]):
                    results[email] = {"email": email, "confidence": confidence, "source": source_label}

    # Sort by confidence (high first)
    return sorted(results.values(), key=lambda r: _confidence_rank(r["confidence"]), reverse=True)


def _confidence_rank(level: str) -> int:
    return {"high": 3, "medium": 2, "low": 1}.get(level, 0)

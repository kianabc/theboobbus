"""Import Utah public companies from SEC EDGAR into the database."""

import re
import time
import json
import requests
from database import execute, init_db

HEADERS = {"User-Agent": "theboobbus hr-finder contact@example.com"}
BASE_URL = "https://www.sec.gov/cgi-bin/browse-edgar"

SIC_TO_INDUSTRY = {
    range(100, 1000): "Agriculture",
    range(1000, 1500): "Mining",
    range(1500, 1800): "Construction",
    range(2000, 4000): "Manufacturing",
    range(4000, 5000): "Transportation & Utilities",
    range(5000, 5200): "Wholesale Trade",
    range(5200, 6000): "Retail",
    range(6000, 6800): "Finance",
    range(7000, 9000): "Services",
    range(9100, 9730): "Government",
}


def sic_to_industry(sic_code):
    try:
        sic = int(sic_code)
    except (ValueError, TypeError):
        return "Other"
    for sic_range, industry in SIC_TO_INDUSTRY.items():
        if sic in sic_range:
            return industry
    return "Other"


def get_utah_ciks():
    """Fetch all Utah company CIKs from EDGAR company search."""
    ciks = []
    start = 0
    count = 100

    while True:
        url = (
            f"{BASE_URL}?action=getcompany&State=UT&SIC=&dateb="
            f"&owner=include&count={count}&start={start}"
            f"&search_text=&action=getcompany"
        )
        resp = requests.get(url, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        html = resp.text

        found = re.findall(r'CIK=(\d+)', html)
        # Deduplicate while preserving order
        page_ciks = list(dict.fromkeys(found))

        if not page_ciks:
            break

        ciks.extend(page_ciks)
        print(f"  Page {start // count + 1}: found {len(page_ciks)} CIKs (total: {len(ciks)})")

        # Check if there's a next page
        if f"start={start + count}" not in html:
            break

        start += count
        time.sleep(0.5)

    return list(dict.fromkeys(ciks))


def get_company_details(cik):
    """Fetch company details from SEC submissions API."""
    padded_cik = cik.zfill(10)
    url = f"https://data.sec.gov/submissions/CIK{padded_cik}.json"
    resp = requests.get(url, headers=HEADERS, timeout=15)
    if resp.status_code != 200:
        return None
    data = resp.json()

    biz_addr = data.get("addresses", {}).get("business", {})
    city = biz_addr.get("city", "").title()
    state = biz_addr.get("stateOrCountry", "")

    # Only include companies actually in Utah
    if state != "UT":
        return None

    name = data.get("name", "").strip()
    if not name:
        return None

    # Skip shell companies, funds, and series
    entity_type = data.get("entityType", "")
    if entity_type in ("Series", ""):
        return None

    website = data.get("website", "").strip()
    if website and not website.startswith("http"):
        website = f"https://{website}"

    sic = data.get("sic", "")
    sic_desc = data.get("sicDescription", "")
    industry = sic_to_industry(sic)
    if sic_desc:
        industry = f"{industry} ({sic_desc})"

    return {
        "name": name,
        "website": website or None,
        "industry": industry,
        "city": city or "Utah",
    }


def import_companies():
    """Main import function."""
    print("Fetching Utah CIKs from EDGAR...")
    ciks = get_utah_ciks()
    print(f"Found {len(ciks)} total CIKs\n")

    print("Fetching company details...")
    imported = 0
    skipped = 0
    errors = 0

    for i, cik in enumerate(ciks):
        if i > 0 and i % 10 == 0:
            print(f"  Progress: {i}/{len(ciks)} processed, {imported} imported")
            time.sleep(1)  # rate limiting
        else:
            time.sleep(0.2)

        try:
            details = get_company_details(cik)
            if not details:
                skipped += 1
                continue

            # Check if company already exists
            existing = execute(
                "SELECT id FROM companies WHERE name = ?",
                [details["name"]],
            )
            if existing.rows:
                skipped += 1
                continue

            execute(
                "INSERT INTO companies (name, website, industry, city) VALUES (?, ?, ?, ?)",
                [details["name"], details["website"], details["industry"], details["city"]],
            )
            imported += 1
            print(f"    + {details['name']} ({details['city']})")

        except Exception as e:
            errors += 1
            if errors < 5:
                print(f"    Error on CIK {cik}: {e}")

    print(f"\nDone! Imported: {imported}, Skipped: {skipped}, Errors: {errors}")
    total = execute("SELECT COUNT(*) FROM companies")
    print(f"Total companies in database: {total.rows[0][0]}")


if __name__ == "__main__":
    import_companies()

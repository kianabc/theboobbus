"""Fetch short descriptions for all companies from their websites."""

import time
import logging
import requests
from bs4 import BeautifulSoup
from database import execute

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
}


def fetch_description(website: str) -> str | None:
    """Fetch meta description from a website."""
    if not website:
        return None

    url = website if website.startswith("http") else f"https://{website}"

    try:
        resp = requests.get(url, headers=HEADERS, timeout=10, allow_redirects=True)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")

        # Try meta description
        meta = soup.find("meta", attrs={"name": "description"})
        if meta and meta.get("content", "").strip():
            desc = meta["content"].strip()
            # Truncate to ~200 chars at a sentence boundary
            if len(desc) > 200:
                cut = desc[:200].rfind(".")
                if cut > 80:
                    desc = desc[:cut + 1]
                else:
                    desc = desc[:200].rsplit(" ", 1)[0] + "..."
            return desc

        # Try og:description
        og = soup.find("meta", attrs={"property": "og:description"})
        if og and og.get("content", "").strip():
            desc = og["content"].strip()
            if len(desc) > 200:
                cut = desc[:200].rfind(".")
                if cut > 80:
                    desc = desc[:cut + 1]
                else:
                    desc = desc[:200].rsplit(" ", 1)[0] + "..."
            return desc

        return None

    except Exception as e:
        logger.debug("Failed to fetch %s: %s", url, e)
        return None


def main():
    rs = execute("SELECT id, name, website FROM companies WHERE description IS NULL AND website IS NOT NULL")
    companies = rs.rows
    print(f"Fetching descriptions for {len(companies)} companies...\n")

    found = 0
    failed = 0

    for i, r in enumerate(companies):
        cid, name, website = r[0], r[1], r[2]

        if i > 0 and i % 10 == 0:
            print(f"  Progress: {i}/{len(companies)} ({found} found)")
            time.sleep(0.5)

        desc = fetch_description(website)
        if desc:
            execute("UPDATE companies SET description = ? WHERE id = ?", [desc, cid])
            found += 1
            print(f"  + {name}: {desc[:80]}...")
        else:
            failed += 1

        time.sleep(0.3)

    print(f"\nDone! Found: {found}, Failed: {failed}")


if __name__ == "__main__":
    main()

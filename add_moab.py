"""Add a few Moab, UT companies to the database.

Usage:
    python add_moab.py
"""

from dotenv import load_dotenv
load_dotenv()

from database import execute


MOAB_COMPANIES = [
    {
        "name": "Moab Regional Hospital",
        "website": "https://mrhmoab.org",
        "industry": "Healthcare",
        "city": "Moab",
    },
    {
        "name": "Grand County School District",
        "website": "https://www.grandschools.org",
        "industry": "Education",
        "city": "Moab",
    },
    {
        "name": "City of Moab",
        "website": "https://moabcity.org",
        "industry": "Government",
        "city": "Moab",
    },
    {
        "name": "Sorrel River Ranch Resort & Spa",
        "website": "https://www.sorrelriver.com",
        "industry": "Hospitality",
        "city": "Moab",
    },
    {
        "name": "Red Cliffs Lodge",
        "website": "https://www.redcliffslodge.com",
        "industry": "Hospitality",
        "city": "Moab",
    },
    {
        "name": "Moab Adventure Center",
        "website": "https://www.moabadventurecenter.com",
        "industry": "Tourism / Recreation",
        "city": "Moab",
    },
    {
        "name": "Western Spirit Cycling Adventures",
        "website": "https://www.westernspirit.com",
        "industry": "Tourism / Recreation",
        "city": "Moab",
    },
]

COUNTY = "Grand"


def main():
    added = 0
    skipped = 0
    for c in MOAB_COMPANIES:
        existing = execute("SELECT id FROM companies WHERE name = ?", [c["name"]])
        if existing.rows:
            print(f"  skip (exists): {c['name']}")
            skipped += 1
            continue
        rs = execute(
            "INSERT INTO companies (name, website, industry, city, county) VALUES (?, ?, ?, ?, ?)",
            [c["name"], c["website"], c["industry"], c["city"], COUNTY],
        )
        print(f"  added: {c['name']}")
        added += 1
    print(f"\nDone. Added {added}, skipped {skipped}.")


if __name__ == "__main__":
    main()

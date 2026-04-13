"""Seed data: top Utah companies across industries."""

from database import get_db

UTAH_COMPANIES = [
    # Tech
    {"name": "Qualtrics", "website": "https://www.qualtrics.com", "industry": "Technology", "city": "Provo"},
    {"name": "Pluralsight", "website": "https://www.pluralsight.com", "industry": "Technology", "city": "Draper"},
    {"name": "Domo", "website": "https://www.domo.com", "industry": "Technology", "city": "American Fork"},
    {"name": "Lucid Software", "website": "https://www.lucid.co", "industry": "Technology", "city": "South Jordan"},
    {"name": "Podium", "website": "https://www.podium.com", "industry": "Technology", "city": "Lehi"},
    {"name": "MX Technologies", "website": "https://www.mx.com", "industry": "Technology", "city": "Lehi"},
    {"name": "Weave", "website": "https://www.getweave.com", "industry": "Technology", "city": "Lehi"},
    {"name": "Ivanti", "website": "https://www.ivanti.com", "industry": "Technology", "city": "South Jordan"},
    {"name": "BambooHR", "website": "https://www.bamboohr.com", "industry": "Technology", "city": "Lindon"},
    {"name": "Instructure", "website": "https://www.instructure.com", "industry": "Technology", "city": "Salt Lake City"},
    # Healthcare
    {"name": "Intermountain Health", "website": "https://intermountainhealthcare.org", "industry": "Healthcare", "city": "Salt Lake City"},
    {"name": "University of Utah Health", "website": "https://healthcare.utah.edu", "industry": "Healthcare", "city": "Salt Lake City"},
    {"name": "Recursion Pharmaceuticals", "website": "https://www.recursion.com", "industry": "Healthcare", "city": "Salt Lake City"},
    {"name": "Health Catalyst", "website": "https://www.healthcatalyst.com", "industry": "Healthcare", "city": "Salt Lake City"},
    # Finance
    {"name": "Zions Bancorporation", "website": "https://www.zionsbancorporation.com", "industry": "Finance", "city": "Salt Lake City"},
    {"name": "Goldman Sachs (SLC)", "website": "https://www.goldmansachs.com", "industry": "Finance", "city": "Salt Lake City"},
    {"name": "Ally Financial (SLC)", "website": "https://www.ally.com", "industry": "Finance", "city": "Sandy"},
    # Retail / Consumer
    {"name": "Nu Skin Enterprises", "website": "https://www.nuskin.com", "industry": "Consumer Goods", "city": "Provo"},
    {"name": "Traeger Grills", "website": "https://www.traeger.com", "industry": "Consumer Goods", "city": "Salt Lake City"},
    {"name": "Purple Innovation", "website": "https://www.purple.com", "industry": "Consumer Goods", "city": "Lehi"},
    {"name": "Cotopaxi", "website": "https://www.cotopaxi.com", "industry": "Retail", "city": "Salt Lake City"},
    # Aerospace / Defense
    {"name": "Northrop Grumman (Utah)", "website": "https://www.northropgrumman.com", "industry": "Aerospace & Defense", "city": "Roy"},
    {"name": "L3Harris Technologies (Utah)", "website": "https://www.l3harris.com", "industry": "Aerospace & Defense", "city": "Salt Lake City"},
    {"name": "Hill Air Force Base (civilian)", "website": "https://www.hill.af.mil", "industry": "Government / Defense", "city": "Ogden"},
    # Hospitality / Travel
    {"name": "SkyWest Airlines", "website": "https://www.skywest.com", "industry": "Airlines", "city": "St. George"},
    {"name": "Breeze Airways", "website": "https://www.flybreeze.com", "industry": "Airlines", "city": "Cottonwood Heights"},
    # Education
    {"name": "Brigham Young University", "website": "https://www.byu.edu", "industry": "Education", "city": "Provo"},
    {"name": "University of Utah", "website": "https://www.utah.edu", "industry": "Education", "city": "Salt Lake City"},
    {"name": "Utah State University", "website": "https://www.usu.edu", "industry": "Education", "city": "Logan"},
    # Other
    {"name": "Vivint Smart Home", "website": "https://www.vivint.com", "industry": "Smart Home / Security", "city": "Lehi"},
    {"name": "Extra Space Storage", "website": "https://www.extraspace.com", "industry": "Real Estate", "city": "Salt Lake City"},
    {"name": "Larry H. Miller Dealerships", "website": "https://www.lhm.com", "industry": "Automotive", "city": "Sandy"},
    {"name": "Overstock.com", "website": "https://www.overstock.com", "industry": "E-Commerce", "city": "Midvale"},
]


def seed_companies():
    with get_db() as conn:
        existing = conn.execute("SELECT COUNT(*) FROM companies").fetchone()[0]
        if existing > 0:
            return existing

        for company in UTAH_COMPANIES:
            conn.execute(
                "INSERT INTO companies (name, website, industry, city) VALUES (?, ?, ?, ?)",
                (company["name"], company["website"], company["industry"], company["city"]),
            )
    return len(UTAH_COMPANIES)

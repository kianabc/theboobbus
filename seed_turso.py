"""One-time script to initialize and seed the Turso database.

Usage:
    TURSO_DATABASE_URL=libsql://... TURSO_AUTH_TOKEN=... python seed_turso.py
"""

from database import init_db
from seed_data import seed_companies

print("Initializing tables...")
init_db()
print("Seeding companies...")
count = seed_companies()
print(f"Done — {count} companies in database.")

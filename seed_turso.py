"""One-time script to initialize and seed the Turso database.

Reads TURSO_DATABASE_URL / TURSO_AUTH_TOKEN from .env (or the shell). Safe to
re-run: init_db uses CREATE TABLE IF NOT EXISTS + idempotent ALTER migrations,
and seed_companies skips when the companies table is non-empty.
"""

from dotenv import load_dotenv
load_dotenv()

import os
if not os.environ.get("TURSO_DATABASE_URL"):
    raise SystemExit(
        "TURSO_DATABASE_URL not found in environment or .env. "
        "Refusing to run — this would seed the local sqlite file, not production."
    )

from database import init_db
from seed_data import seed_companies

print("Initializing tables...")
init_db()
print("Seeding companies...")
count = seed_companies()
print(f"Done — {count} companies in database.")

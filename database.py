import libsql_client
import os

def _get_client():
    url = os.environ.get("TURSO_DATABASE_URL", "").strip()
    token = os.environ.get("TURSO_AUTH_TOKEN", "").strip()
    if url:
        return libsql_client.create_client_sync(url=url, auth_token=token)
    return libsql_client.create_client_sync(url="file:hr_emails.db")


def execute(sql, params=None):
    client = _get_client()
    try:
        return client.execute(sql, params or [])
    finally:
        client.close()


def batch(statements):
    """Execute multiple statements in a transaction."""
    client = _get_client()
    try:
        return client.batch(statements)
    finally:
        client.close()


def init_db():
    client = _get_client()
    try:
        client.batch([
            """CREATE TABLE IF NOT EXISTS companies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                website TEXT,
                industry TEXT,
                city TEXT DEFAULT 'Utah',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""",
            """CREATE TABLE IF NOT EXISTS hr_emails (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                email TEXT NOT NULL,
                source TEXT,
                confidence TEXT DEFAULT 'low',
                scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (company_id) REFERENCES companies(id),
                UNIQUE(company_id, email)
            )""",
            """CREATE INDEX IF NOT EXISTS idx_companies_name
               ON companies(name)""",
            """CREATE TABLE IF NOT EXISTS sent_emails (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER,
                to_email TEXT NOT NULL,
                subject TEXT,
                body TEXT,
                sent_by TEXT,
                email_type TEXT DEFAULT 'initial',
                gmail_message_id TEXT,
                replied INTEGER DEFAULT 0,
                sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                next_follow_up_at TIMESTAMP,
                FOREIGN KEY (company_id) REFERENCES companies(id)
            )""",
            """CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )""",
            """CREATE TABLE IF NOT EXISTS email_drafts (
                company_id INTEGER NOT NULL,
                contact_email TEXT NOT NULL,
                subject TEXT,
                body TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (company_id, contact_email)
            )""",
            """CREATE TABLE IF NOT EXISTS gmail_tokens (
                user_email TEXT PRIMARY KEY,
                refresh_token TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""",
        ])
    finally:
        client.close()

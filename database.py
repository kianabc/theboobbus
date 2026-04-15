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


def _run_migrations(client):
    """Idempotent column additions for existing installs.

    SQLite doesn't support ALTER TABLE ... ADD COLUMN IF NOT EXISTS, so we
    attempt each ALTER and ignore the duplicate-column error.
    """
    migrations = [
        "ALTER TABLE sent_emails ADD COLUMN message_id_header TEXT",
        "ALTER TABLE sent_emails ADD COLUMN thread_id TEXT",
        "ALTER TABLE scheduled_sends ADD COLUMN reply_to_message_id TEXT",
        "ALTER TABLE scheduled_sends ADD COLUMN reply_to_thread_id TEXT",
        "ALTER TABLE scheduled_sends ADD COLUMN kind TEXT DEFAULT 'test'",
        "ALTER TABLE scheduled_sends ADD COLUMN subject TEXT",
        "ALTER TABLE scheduled_sends ADD COLUMN body TEXT",
        "ALTER TABLE sent_emails ADD COLUMN is_test INTEGER DEFAULT 0",
    ]
    for sql in migrations:
        try:
            client.execute(sql)
        except Exception:
            # Column already exists
            pass


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
            """CREATE TABLE IF NOT EXISTS email_opens (
                tracking_id TEXT PRIMARY KEY,
                sent_email_id INTEGER NOT NULL,
                opened_at TIMESTAMP,
                open_count INTEGER DEFAULT 0,
                FOREIGN KEY (sent_email_id) REFERENCES sent_emails(id)
            )""",
            """CREATE TABLE IF NOT EXISTS email_drafts (
                company_id INTEGER NOT NULL,
                contact_email TEXT NOT NULL,
                subject TEXT,
                body TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (company_id, contact_email)
            )""",
            """CREATE TABLE IF NOT EXISTS user_profiles (
                email TEXT PRIMARY KEY,
                full_name TEXT NOT NULL,
                picture TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""",
            """CREATE TABLE IF NOT EXISTS gmail_tokens (
                user_email TEXT PRIMARY KEY,
                refresh_token TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""",
            """CREATE TABLE IF NOT EXISTS scheduled_sends (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_email TEXT NOT NULL,
                test_email TEXT NOT NULL,
                company_id INTEGER NOT NULL,
                contact_email TEXT NOT NULL,
                contact_name TEXT,
                contact_title TEXT,
                email_type TEXT NOT NULL,
                step_num INTEGER NOT NULL,
                total_steps INTEGER NOT NULL,
                send_at TIMESTAMP NOT NULL,
                status TEXT DEFAULT 'pending',
                error_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                sent_at TIMESTAMP
            )""",
            """CREATE INDEX IF NOT EXISTS idx_scheduled_sends_due
               ON scheduled_sends(status, send_at)""",
            """CREATE TABLE IF NOT EXISTS email_open_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sent_email_id INTEGER NOT NULL,
                opened_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (sent_email_id) REFERENCES sent_emails(id)
            )""",
            """CREATE INDEX IF NOT EXISTS idx_email_open_events_email
               ON email_open_events(sent_email_id)""",
        ])
        _run_migrations(client)
    finally:
        client.close()

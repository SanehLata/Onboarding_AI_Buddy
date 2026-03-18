# gen_db.py
# @Author: Saneh Lata
# Creates onboarding.db (SQLite) with all required tables and seeds
# 2-3 sample developers for testing and demonstration.
# Run once before starting the application.

import sqlite3
import json
from datetime import datetime, date, timedelta
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH  = BASE_DIR / "mock_db" / "onboarding.db"

# ── Helpers ───────────────────────────────────────────────────────────────────

def print_header(text: str) -> None:
    print(f"\n{'─' * 60}")
    print(f"  {text}")
    print(f"{'─' * 60}")


def now() -> str:
    return datetime.utcnow().isoformat()


def today() -> str:
    return date.today().isoformat()


def future_date(days: int) -> str:
    return (date.today() + timedelta(days=days)).isoformat()


# ── Schema ────────────────────────────────────────────────────────────────────

SCHEMA = """

-- Developer profiles — one row per onboarded developer
CREATE TABLE IF NOT EXISTS developer_profiles (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    name              TEXT NOT NULL,
    email             TEXT NOT NULL UNIQUE,
    team_id           TEXT NOT NULL,
    team_name         TEXT NOT NULL,
    manager_name      TEXT NOT NULL,
    manager_email     TEXT NOT NULL,
    role_title        TEXT NOT NULL,
    experience_level  TEXT NOT NULL CHECK (experience_level IN ('junior', 'mid', 'senior', 'lead')),
    skills            TEXT NOT NULL,   -- JSON array of skill strings
    start_date        TEXT NOT NULL,
    onboarding_status TEXT NOT NULL DEFAULT 'in_progress'
                      CHECK (onboarding_status IN ('pending', 'in_progress', 'completed')),
    profile_complete  INTEGER NOT NULL DEFAULT 0,
    created_at        TEXT NOT NULL,
    updated_at        TEXT NOT NULL
);

-- Access / ticket requests — one row per system per developer
CREATE TABLE IF NOT EXISTS access_requests (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    developer_id      INTEGER NOT NULL REFERENCES developer_profiles(id),
    system_id         TEXT NOT NULL,
    system_name       TEXT NOT NULL,
    ticket_type       TEXT NOT NULL,
    ticket_id         TEXT,              -- mock ticket ID returned by ticketing tool
    ticket_summary    TEXT NOT NULL,
    status            TEXT NOT NULL DEFAULT 'pending'
                      CHECK (status IN ('pending', 'raised', 'in_progress', 'approved', 'completed', 'failed')),
    access_level      TEXT NOT NULL,
    requires_approval INTEGER NOT NULL DEFAULT 0,
    approved_by       TEXT,
    sla_hours         INTEGER NOT NULL,
    raised_at         TEXT,
    resolved_at       TEXT,
    notes             TEXT,
    created_at        TEXT NOT NULL,
    updated_at        TEXT NOT NULL
);

-- Distribution list subscriptions — one row per DL per developer
CREATE TABLE IF NOT EXISTS dl_subscriptions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    developer_id    INTEGER NOT NULL REFERENCES developer_profiles(id),
    dl_id           TEXT NOT NULL,
    dl_name         TEXT NOT NULL,
    dl_email        TEXT NOT NULL,
    owner_name      TEXT NOT NULL,
    owner_email     TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'pending'
                    CHECK (status IN ('pending', 'email_sent', 'subscribed', 'failed')),
    email_sent_at   TEXT,
    subscribed_at   TEXT,
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL
);

-- Learning path — one row per recommended document per developer
CREATE TABLE IF NOT EXISTS learning_path (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    developer_id     INTEGER NOT NULL REFERENCES developer_profiles(id),
    doc_path         TEXT NOT NULL,      -- relative path e.g. onboarding/day1_checklist.md
    doc_title        TEXT NOT NULL,
    category         TEXT NOT NULL,      -- onboarding | architecture | runbooks
    priority_order   INTEGER NOT NULL,   -- 1 = read first
    reason           TEXT,               -- why this doc was recommended
    status           TEXT NOT NULL DEFAULT 'not_started'
                     CHECK (status IN ('not_started', 'in_progress', 'completed', 'skipped')),
    started_at       TEXT,
    completed_at     TEXT,
    created_at       TEXT NOT NULL,
    updated_at       TEXT NOT NULL
);

-- Progress tracking — conversation history and topic coverage
CREATE TABLE IF NOT EXISTS progress_tracking (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    developer_id    INTEGER NOT NULL REFERENCES developer_profiles(id),
    topic           TEXT NOT NULL,       -- topic or document name covered
    source_doc      TEXT,                -- doc that answered the query
    query           TEXT,                -- what the developer asked
    summary         TEXT,                -- brief summary of what was covered
    session_id      INTEGER NOT NULL REFERENCES sessions(id),
    created_at      TEXT NOT NULL
);

-- Sessions — tracks each conversation session
CREATE TABLE IF NOT EXISTS sessions (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    developer_id INTEGER NOT NULL REFERENCES developer_profiles(id),
    started_at   TEXT NOT NULL,
    ended_at     TEXT,
    message_count INTEGER NOT NULL DEFAULT 0,
    topics_covered TEXT NOT NULL DEFAULT '[]'   -- JSON array of topic strings
);

-- Agent actions log — audit trail of everything the agent did
CREATE TABLE IF NOT EXISTS agent_action_log (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    developer_id INTEGER NOT NULL REFERENCES developer_profiles(id),
    session_id   INTEGER REFERENCES sessions(id),
    action_type  TEXT NOT NULL,    -- TICKET_RAISED | EMAIL_SENT | PATH_GENERATED | QUERY_ANSWERED
    action_data  TEXT NOT NULL,    -- JSON blob of action details
    status       TEXT NOT NULL,    -- success | failed | skipped
    error        TEXT,
    created_at   TEXT NOT NULL
);
"""

# ── Seed Data ─────────────────────────────────────────────────────────────────

def seed_developers(conn: sqlite3.Connection) -> list[dict]:
    """Insert 3 sample developers covering different teams and experience levels."""

    developers = [
        {
            "name":             "Alex Chen",
            "email":            "alex.chen@techcorp.com",
            "team_id":          "team_payments",
            "team_name":        "Payments Engineering",
            "manager_name":     "Sarah Mitchell",
            "manager_email":    "sarah.mitchell@techcorp.com",
            "role_title":       "Software Engineer",
            "experience_level": "mid",
            "skills":           json.dumps(["Python", "REST APIs", "PostgreSQL", "Docker"]),
            "start_date":       today(),
            "onboarding_status":"in_progress",
            "profile_complete": 1,
            "created_at":       now(),
            "updated_at":       now(),
        },
        {
            "name":             "Priya Patel",
            "email":            "priya.patel@techcorp.com",
            "team_id":          "team_data_engineering",
            "team_name":        "Data Engineering",
            "manager_name":     "Marcus Lee",
            "manager_email":    "marcus.lee@techcorp.com",
            "role_title":       "Senior Data Engineer",
            "experience_level": "senior",
            "skills":           json.dumps(["Python", "SQL", "Spark", "Airflow", "Snowflake", "dbt"]),
            "start_date":       today(),
            "onboarding_status":"in_progress",
            "profile_complete": 1,
            "created_at":       now(),
            "updated_at":       now(),
        },
        {
            "name":             "Jordan Williams",
            "email":            "jordan.williams@techcorp.com",
            "team_id":          "team_platform",
            "team_name":        "Platform Engineering",
            "manager_name":     "Priya Sharma",
            "manager_email":    "priya.sharma@techcorp.com",
            "role_title":       "Junior DevOps Engineer",
            "experience_level": "junior",
            "skills":           json.dumps(["Python", "Bash", "Linux", "Docker"]),
            "start_date":       today(),
            "onboarding_status":"pending",
            "profile_complete": 1,
            "created_at":       now(),
            "updated_at":       now(),
        },
    ]

    conn.executemany(
        """
        INSERT OR IGNORE INTO developer_profiles
            (name, email, team_id, team_name, manager_name, manager_email,
             role_title, experience_level, skills, start_date, onboarding_status,
             profile_complete, created_at, updated_at)
        VALUES
            (:name, :email, :team_id, :team_name, :manager_name, :manager_email,
             :role_title, :experience_level, :skills, :start_date, :onboarding_status,
             :profile_complete, :created_at, :updated_at)
        """,
        developers,
    )

    # Fetch back the auto-assigned integer IDs and attach to each developer dict
    rows = conn.execute(
        "SELECT id, email FROM developer_profiles ORDER BY id"
    ).fetchall()
    email_to_id = {row[1]: row[0] for row in rows}
    for dev in developers:
        dev["id"] = email_to_id[dev["email"]]

    print(f"  ✅  Inserted {len(developers)} developer profiles (IDs: {[d['id'] for d in developers]})")
    return developers


def seed_access_requests(conn: sqlite3.Connection, developers: list[dict]) -> None:
    """Insert mock access requests for each developer based on their team's required systems."""

    # Map team → required systems (mirrors teams.json)
    team_systems = {
        "team_payments": [
            ("jira",        "Jira",        "ACCESS_REQUEST",   "developer",   False, 24),
            ("confluence",  "Confluence",  "ACCESS_REQUEST",   "contributor", False, 24),
            ("github",      "GitHub",      "ACCESS_REQUEST",   "write",       True,  8),
            ("servicenow",  "ServiceNow",  "CHANGE_REQUEST",   "requester",   True,  48),
            ("unix",        "Unix",        "SECURITY_REQUEST", "dev_staging", True,  72),
            ("snowflake",   "Snowflake",   "DATA_ACCESS_REQUEST","read_curated",True,48),
        ],
        "team_data_engineering": [
            ("jira",        "Jira",        "ACCESS_REQUEST",      "developer",       False, 24),
            ("confluence",  "Confluence",  "ACCESS_REQUEST",      "contributor",     False, 24),
            ("github",      "GitHub",      "ACCESS_REQUEST",      "write",           True,  8),
            ("servicenow",  "ServiceNow",  "CHANGE_REQUEST",      "requester",       True,  48),
            ("unix",        "Unix",        "SECURITY_REQUEST",    "dev_staging",     True,  72),
            ("snowflake",   "Snowflake",   "DATA_ACCESS_REQUEST", "read_write_sandbox", True, 48),
        ],
        "team_platform": [
            ("jira",        "Jira",        "ACCESS_REQUEST",   "developer",   False, 24),
            ("confluence",  "Confluence",  "ACCESS_REQUEST",   "contributor", False, 24),
            ("github",      "GitHub",      "ACCESS_REQUEST",   "write",       True,  8),
            ("servicenow",  "ServiceNow",  "CHANGE_REQUEST",   "requester",   True,  48),
            ("unix",        "Unix",        "SECURITY_REQUEST", "dev_staging", True,  72),
        ],
    }

    status_cycle = ["raised", "in_progress", "approved", "completed", "pending"]
    records = []

    for i, dev in enumerate(developers):
        systems = team_systems.get(dev["team_id"], [])
        for j, (sys_id, sys_name, ticket_type, access_level, needs_approval, sla) in enumerate(systems):
            status = status_cycle[(i + j) % len(status_cycle)]
            ticket_id = f"TICK-{1000 + i * 10 + j}" if status != "pending" else None
            records.append({
                "developer_id":     dev["id"],
                "system_id":        sys_id,
                "system_name":      sys_name,
                "ticket_type":      ticket_type,
                "ticket_id":        ticket_id,
                "ticket_summary":   f"{ticket_type} - {sys_name} for {dev['name']} ({dev['team_name']})",
                "status":           status,
                "access_level":     access_level,
                "requires_approval":1 if needs_approval else 0,
                "approved_by":      dev["manager_name"] if status in ("approved", "completed") else None,
                "sla_hours":        sla,
                "raised_at":        now() if status != "pending" else None,
                "resolved_at":      now() if status == "completed" else None,
                "notes":            None,
                "created_at":       now(),
                "updated_at":       now(),
            })

    conn.executemany(
        """
        INSERT OR IGNORE INTO access_requests
            (developer_id, system_id, system_name, ticket_type, ticket_id,
             ticket_summary, status, access_level, requires_approval, approved_by,
             sla_hours, raised_at, resolved_at, notes, created_at, updated_at)
        VALUES
            (:developer_id, :system_id, :system_name, :ticket_type, :ticket_id,
             :ticket_summary, :status, :access_level, :requires_approval, :approved_by,
             :sla_hours, :raised_at, :resolved_at, :notes, :created_at, :updated_at)
        """,
        records,
    )
    print(f"  ✅  Inserted {len(records)} access request records")


def seed_learning_paths(conn: sqlite3.Connection, developers: list[dict]) -> None:
    """Insert a starter learning path for each developer."""

    # Common onboarding docs for every developer
    common_docs = [
        ("onboarding/day1_checklist.md",        "Day 1 Checklist",             "onboarding",    1),
        ("onboarding/team_norms.md",             "Team Norms & Working Agreements","onboarding", 2),
        ("onboarding/communication_channels.md", "Communication Channels",      "onboarding",    3),
        ("onboarding/tools_setup.md",            "Developer Tools Setup Guide", "onboarding",    4),
        ("onboarding/vpn_access.md",             "VPN & Remote Access Guide",   "onboarding",    5),
        ("architecture/system_overview.md",      "System Overview",             "architecture",  6),
        ("runbooks/deployment_guide.md",         "Deployment Guide",            "runbooks",      7),
        ("onboarding/on_call_guide.md",          "On-Call Guide",               "onboarding",    8),
    ]

    # Team-specific extras
    team_extras = {
        "team_payments": [
            ("architecture/payments_api.md",      "Payments API",            "architecture", 9),
            ("architecture/microservices_map.md", "Microservices Map",       "architecture", 10),
            ("runbooks/incident_response.md",     "Incident Response",       "runbooks",     11),
        ],
        "team_data_engineering": [
            ("architecture/data_pipeline.md",     "Data Pipeline",           "architecture", 9),
            ("architecture/microservices_map.md", "Microservices Map",       "architecture", 10),
            ("runbooks/logging_standards.md",     "Logging Standards",       "runbooks",     11),
        ],
        "team_platform": [
            ("architecture/microservices_map.md", "Microservices Map",       "architecture", 9),
            ("runbooks/incident_response.md",     "Incident Response",       "runbooks",     10),
            ("runbooks/secrets_config_management.md","Secrets & Config Mgmt","runbooks",     11),
            ("runbooks/kafka_consumer_runbook.md","Kafka Consumer Runbook",  "runbooks",     12),
        ],
    }

    status_cycle = ["completed", "in_progress", "not_started"]
    records = []

    for i, dev in enumerate(developers):
        all_docs = common_docs + team_extras.get(dev["team_id"], [])
        for j, (doc_path, doc_title, category, order) in enumerate(all_docs):
            status = status_cycle[min(j, len(status_cycle) - 1)]
            records.append({
                "developer_id":  dev["id"],
                "doc_path":      doc_path,
                "doc_title":     doc_title,
                "category":      category,
                "priority_order":order,
                "reason":        f"Recommended for {dev['experience_level']}-level {dev['team_name']} engineers",
                "status":        status,
                "started_at":    now() if status in ("in_progress", "completed") else None,
                "completed_at":  now() if status == "completed" else None,
                "created_at":    now(),
                "updated_at":    now(),
            })

    conn.executemany(
        """
        INSERT OR IGNORE INTO learning_path
            (developer_id, doc_path, doc_title, category, priority_order,
             reason, status, started_at, completed_at, created_at, updated_at)
        VALUES
            (:developer_id, :doc_path, :doc_title, :category, :priority_order,
             :reason, :status, :started_at, :completed_at, :created_at, :updated_at)
        """,
        records,
    )
    print(f"  ✅  Inserted {len(records)} learning path records")


def seed_progress(conn: sqlite3.Connection, developers: list[dict]) -> None:
    """Insert sample progress tracking entries and sessions for the first developer."""

    dev = developers[0]   # Seed progress only for Alex Chen

    # Seed one session — id is auto-assigned by SQLite
    conn.execute(
        """
        INSERT OR IGNORE INTO sessions
            (developer_id, started_at, ended_at, message_count, topics_covered)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            dev["id"],
            now(),
            now(),
            4,
            json.dumps(["day1 checklist", "vpn setup", "github access", "team norms"]),
        ),
    )
    # Fetch back the auto-assigned session id
    session_id = conn.execute(
        "SELECT id FROM sessions WHERE developer_id = ? ORDER BY id DESC LIMIT 1",
        (dev["id"],)
    ).fetchone()[0]

    # Seed sample progress entries
    progress_entries = [
        ("day1 checklist",  "onboarding/day1_checklist.md",  "What do I need to do on Day 1?",       "Covered all Day 1 tasks including account setup, Slack, and access requests."),
        ("vpn setup",       "onboarding/vpn_access.md",      "How do I set up the VPN?",             "Walked through GlobalProtect installation and Okta MFA setup."),
        ("github access",   "onboarding/access_provisioning.md","How is GitHub access provisioned?", "GitHub access requires manager approval and is provisioned within 8 hours."),
        ("team norms",      "onboarding/team_norms.md",      "What are the team working agreements?","Covered PR size limits, commit conventions, and deployment rules."),
    ]

    records = [
        {
            "developer_id": dev["id"],
            "topic":        topic,
            "source_doc":   source,
            "query":        query,
            "summary":      summary,
            "session_id":   session_id,
            "created_at":   now(),
        }
        for topic, source, query, summary in progress_entries
    ]

    conn.executemany(
        """
        INSERT OR IGNORE INTO progress_tracking
            (developer_id, topic, source_doc, query, summary, session_id, created_at)
        VALUES
            (:developer_id, :topic, :source_doc, :query, :summary, :session_id, :created_at)
        """,
        records,
    )
    print(f"  ✅  Inserted {len(records)} progress tracking entries + 1 session (id={session_id}) for {dev['name']}")


def seed_agent_log(conn: sqlite3.Connection, developers: list[dict]) -> None:
    """Insert sample agent action log entries."""

    dev = developers[0]
    # Re-use the session created in seed_progress for this developer
    row = conn.execute(
        "SELECT id FROM sessions WHERE developer_id = ? ORDER BY id LIMIT 1",
        (dev["id"],)
    ).fetchone()
    session_id = row[0] if row else None

    log_entries = [
        ("TICKET_RAISED",    {"system": "Jira",       "ticket_id": "TICK-1000", "status": "raised"},          "success"),
        ("TICKET_RAISED",    {"system": "GitHub",     "ticket_id": "TICK-1001", "status": "raised"},          "success"),
        ("EMAIL_SENT",       {"dl": "payments-eng@techcorp.com", "owner": "Sarah Mitchell"},                   "success"),
        ("PATH_GENERATED",   {"doc_count": 11, "team": "Payments Engineering", "level": "mid"},               "success"),
        ("QUERY_ANSWERED",   {"query": "How do I set up VPN?", "source_doc": "onboarding/vpn_access.md"},     "success"),
    ]

    records = [
        {
            "developer_id": dev["id"],
            "session_id":   session_id,
            "action_type":  action_type,
            "action_data":  json.dumps(action_data),
            "status":       status,
            "error":        None,
            "created_at":   now(),
        }
        for action_type, action_data, status in log_entries
    ]

    conn.executemany(
        """
        INSERT OR IGNORE INTO agent_action_log
            (developer_id, session_id, action_type, action_data, status, error, created_at)
        VALUES
            (:developer_id, :session_id, :action_type, :action_data, :status, :error, :created_at)
        """,
        records,
    )
    print(f"  ✅  Inserted {len(records)} agent action log entries")


# ── Run ───────────────────────────────────────────────────────────────────────

def run():
    print_header("Onboarding Buddy — Database Generator")

    # Ensure the mock_db directory exists
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Remove existing DB if re-running
    if DB_PATH.exists():
        DB_PATH.unlink()
        print(f"\n  ♻️   Existing database removed: {DB_PATH.name}")

    print(f"\n  📂  Creating database at: {DB_PATH}")

    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")

    # Create schema
    conn.executescript(SCHEMA)
    print(f"\n  📋  Schema created — 7 tables")

    # Seed data
    print(f"\n  🌱  Seeding data...\n")
    developers = seed_developers(conn)
    seed_access_requests(conn, developers)
    seed_learning_paths(conn, developers)
    seed_progress(conn, developers)
    seed_agent_log(conn, developers)

    conn.commit()

    # ── Print final summary ───────────────────────────────────────────────────
    print_header("Database Summary")

    tables = [
        "developer_profiles",
        "access_requests",
        "dl_subscriptions",
        "learning_path",
        "progress_tracking",
        "sessions",
        "agent_action_log",
    ]

    print(f"\n  {'Table':<30} {'Rows':>6}")
    print(f"  {'─' * 38}")
    for table in tables:
        row = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
        print(f"  {table:<30} {row[0]:>6}")

    print(f"\n  {'─' * 38}")
    print(f"\n  📍  Database path : {DB_PATH}")
    print(f"  📏  Database size  : {DB_PATH.stat().st_size / 1024:.1f} KB")

    # Print seeded developers
    print(f"\n  👥  Seeded Developers:\n")
    rows = conn.execute(
        "SELECT name, email, team_name, experience_level, start_date FROM developer_profiles"
    ).fetchall()
    for name, email, team, level, start in rows:
        print(f"     • {name:<22} {email:<35} {team:<25} {level:<8} starts {start}")

    conn.close()

    print(f"\n  ✅  Database ready.")
    print(f"      Next step: run  python data/seeds/embed_docs.py\n")


if __name__ == "__main__":
    run()
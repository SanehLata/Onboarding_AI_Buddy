"""
migrate_access_requests.py
──────────────────────────
Adds 'rejected' and 'pending_approval' to the access_requests.status
CHECK constraint in the live onboarding.db.

SQLite does not support ALTER TABLE ... MODIFY COLUMN, so this migration
uses the standard SQLite approach: rename → recreate → copy → drop.

Run ONCE from your project root:
    python migrate_access_requests.py

Safe to re-run — it checks whether migration is needed first.
"""
import sqlite3
from pathlib import Path

DB = Path(r"C:\Code\GIT_Repo\Agentic_AI\Onboarding_AI_Buddy\data\mock_db\onboarding.db")

print(f"DB: {DB}")
print(f"Exists: {DB.exists()}\n")

conn = sqlite3.connect(str(DB))

# ── Check if migration is needed ──────────────────────────────────────────────
schema = conn.execute(
    "SELECT sql FROM sqlite_master WHERE type='table' AND name='access_requests'"
).fetchone()

if not schema:
    print("❌ access_requests table not found — run gen_db.py first")
    conn.close()
    exit(1)

current_sql = schema[0]
print("Current schema snippet:")
for line in current_sql.splitlines():
    if "status" in line.lower() or "check" in line.lower():
        print(f"  {line}")

if "'rejected'" in current_sql and "'pending_approval'" in current_sql:
    print("\n✅ Migration already applied — nothing to do.")
    conn.close()
    exit(0)

print("\nApplying migration...")

# ── Migration — recreate table with updated CHECK constraint ──────────────────
conn.execute("PRAGMA foreign_keys = OFF")

conn.executescript("""
BEGIN TRANSACTION;

-- Step 1: rename existing table
ALTER TABLE access_requests RENAME TO access_requests_old;

-- Step 2: create new table with updated CHECK constraint
CREATE TABLE access_requests (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    developer_id      INTEGER NOT NULL REFERENCES developer_profiles(id),
    system_id         TEXT NOT NULL,
    system_name       TEXT NOT NULL,
    ticket_type       TEXT NOT NULL,
    ticket_id         TEXT,
    ticket_summary    TEXT NOT NULL,
    status            TEXT NOT NULL DEFAULT 'pending'
                      CHECK (status IN (
                          'pending', 'raised', 'in_progress',
                          'pending_approval', 'approved',
                          'completed', 'failed', 'rejected'
                      )),
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

-- Step 3: copy all existing data
INSERT INTO access_requests
    (id, developer_id, system_id, system_name, ticket_type, ticket_id,
     ticket_summary, status, access_level, requires_approval, approved_by,
     sla_hours, raised_at, resolved_at, notes, created_at, updated_at)
SELECT
    id, developer_id, system_id, system_name, ticket_type, ticket_id,
    ticket_summary, status, access_level, requires_approval, approved_by,
    sla_hours, raised_at, resolved_at, notes, created_at, updated_at
FROM access_requests_old;

-- Step 4: drop old table
DROP TABLE access_requests_old;

COMMIT;
""")

conn.execute("PRAGMA foreign_keys = ON")

# ── Verify ────────────────────────────────────────────────────────────────────
new_schema = conn.execute(
    "SELECT sql FROM sqlite_master WHERE type='table' AND name='access_requests'"
).fetchone()[0]

row_count = conn.execute("SELECT COUNT(*) FROM access_requests").fetchone()[0]

conn.close()

print()
print("Updated schema snippet:")
for line in new_schema.splitlines():
    if "status" in line.lower() or "check" in line.lower():
        print(f"  {line}")

print()
print(f"✅ Migration complete — {row_count} rows preserved")
print()
print("The access_requests.status column now accepts:")
print("  pending, raised, in_progress, pending_approval,")
print("  approved, completed, failed, rejected")
"""
Deeper diagnostic — run from anywhere:
    python check_db2.py
"""
import sqlite3
from pathlib import Path

DB = Path(r"C:\Code\GIT_Repo\Agentic_AI\Onboarding_AI_Buddy\data\mock_db\onboarding.db")
conn = sqlite3.connect(str(DB))
conn.row_factory = sqlite3.Row

print("=== progress_tracking — ALL rows for dev_id=7 ===")
rows = conn.execute(
    "SELECT id, session_id, topic, source_doc FROM progress_tracking "
    "WHERE developer_id = 7 ORDER BY id"
).fetchall()
for r in rows:
    print(dict(r))

print(f"\nTotal rows for dev_id=7: {len(rows)}")

print()
print("=== Sessions for dev_id=7 ===")
for r in conn.execute(
    "SELECT id, started_at FROM sessions WHERE developer_id = 7 ORDER BY id"
).fetchall():
    print(dict(r))

print()
print("=== Test: direct insert into progress_tracking with session_id=20 ===")
conn.execute("PRAGMA foreign_keys = ON")
try:
    conn.execute(
        "INSERT INTO progress_tracking "
        "(developer_id, topic, source_doc, query, summary, session_id, created_at) "
        "VALUES (7, 'Test Topic', 'test/doc.md', 'test query', 'test summary', 20, datetime('now'))"
    )
    conn.commit()
    print("INSERT succeeded ✅ — FK is not the issue")
    # clean up
    conn.execute("DELETE FROM progress_tracking WHERE topic = 'Test Topic'")
    conn.commit()
    print("Test row cleaned up")
except Exception as e:
    print(f"INSERT FAILED ❌  {e}")

print()
print("=== Test: direct insert with session_id=19 ===")
try:
    conn.execute(
        "INSERT INTO progress_tracking "
        "(developer_id, topic, source_doc, query, summary, session_id, created_at) "
        "VALUES (7, 'Test Topic 19', 'test/doc.md', 'test query', 'test summary', 19, datetime('now'))"
    )
    conn.commit()
    print("INSERT with session_id=19 succeeded ✅")
    conn.execute("DELETE FROM progress_tracking WHERE topic = 'Test Topic 19'")
    conn.commit()
    print("Test row cleaned up")
except Exception as e:
    print(f"INSERT with session_id=19 FAILED ❌  {e}")

print()
print("=== Check: does learning_path have rows for dev_id=7? ===")
lp = conn.execute(
    "SELECT COUNT(*) as cnt FROM learning_path WHERE developer_id = 7"
).fetchone()
print(f"learning_path rows: {lp['cnt']}")

print()
print("=== Check: valid_topic guard — is topic being set to None string? ===")
none_rows = conn.execute(
    "SELECT COUNT(*) as cnt FROM progress_tracking WHERE topic = 'None'"
).fetchone()
print(f"Rows with topic='None': {none_rows['cnt']}")

conn.close()
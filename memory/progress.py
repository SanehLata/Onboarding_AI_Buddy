# memory/progress.py
# @Author: Saneh Lata
# Tracks what a developer has covered across sessions.
# Powers the "don't repeat yourself" and proactive nudge behaviour
# of the Learning Path agent.
#
# Primary keys are INTEGER AUTOINCREMENT throughout.
# session_id is an int FK to sessions.id — not a UUID string.

import sqlite3
import json
from datetime import datetime
from typing import Optional

from config import DB_PATH, PROACTIVE_NUDGE_AFTER


# ── Helpers ───────────────────────────────────────────────────────────────────

def _now() -> str:
    return datetime.utcnow().isoformat()


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


# ── Session Management ────────────────────────────────────────────────────────

def start_session(developer_id: int) -> int:
    """
    Create a new session row and return the auto-assigned integer session ID.
    Called once at the start of each Streamlit conversation.
    """
    with _connect() as conn:
        cursor = conn.execute(
            """
            INSERT INTO sessions
                (developer_id, started_at, message_count, topics_covered)
            VALUES (?, ?, 0, '[]')
            """,
            (developer_id, _now()),
        )
        return cursor.lastrowid


def end_session(session_id: int) -> None:
    """Mark a session as ended."""
    with _connect() as conn:
        conn.execute(
            "UPDATE sessions SET ended_at = ? WHERE id = ?",
            (_now(), session_id),
        )


def increment_session_messages(session_id: int) -> None:
    """Increment the message counter for a session."""
    with _connect() as conn:
        conn.execute(
            "UPDATE sessions SET message_count = message_count + 1 WHERE id = ?",
            (session_id,),
        )


def add_topic_to_session(session_id: int, topic: str) -> None:
    """Add a topic string to the session's topics_covered JSON array."""
    with _connect() as conn:
        row = conn.execute(
            "SELECT topics_covered FROM sessions WHERE id = ?",
            (session_id,),
        ).fetchone()

        if not row:
            return

        topics = json.loads(row["topics_covered"])
        if topic not in topics:
            topics.append(topic)
            conn.execute(
                "UPDATE sessions SET topics_covered = ? WHERE id = ?",
                (json.dumps(topics), session_id),
            )


def get_session(session_id: int) -> Optional[dict]:
    """Return session details including topics covered."""
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM sessions WHERE id = ?",
            (session_id,),
        ).fetchone()

    if not row:
        return None

    s = dict(row)
    s["topics_covered"] = json.loads(s["topics_covered"])
    return s


# ── Progress Tracking ─────────────────────────────────────────────────────────

def record_progress(
    developer_id: int,
    session_id: int,
    topic: str,
    query: str,
    summary: str,
    source_doc: str = None,
) -> None:
    """
    Record that a developer covered a topic during a session.
    Called after every successfully answered question.
    id is auto-assigned; session_id is an integer FK to sessions.id.
    """
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO progress_tracking
                (developer_id, topic, source_doc, query, summary, session_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                developer_id,
                topic,
                source_doc,
                query,
                summary,
                session_id,
                _now(),
            ),
        )

    # Keep session topics list in sync
    add_topic_to_session(session_id, topic)
    increment_session_messages(session_id)


def get_covered_topics(developer_id: int) -> list[str]:
    """
    Return all unique topics this developer has covered across all sessions.
    Used to avoid repeating already-answered content.
    """
    with _connect() as conn:
        rows = conn.execute(
            "SELECT DISTINCT topic FROM progress_tracking WHERE developer_id = ?",
            (developer_id,),
        ).fetchall()
    return [r["topic"] for r in rows]


def get_covered_docs(developer_id: int) -> list[str]:
    """Return all source documents this developer has been referred to."""
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT DISTINCT source_doc FROM progress_tracking
            WHERE developer_id = ? AND source_doc IS NOT NULL
            """,
            (developer_id,),
        ).fetchall()
    return [r["source_doc"] for r in rows]


def get_recent_history(developer_id: int, session_id: int, limit: int = 6) -> list[dict]:
    """
    Return the most recent progress entries for a session.
    Used to build conversational context for the LLM.
    Returns oldest-first so the LLM sees the conversation in order.
    """
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT topic, query, summary, source_doc, created_at
            FROM progress_tracking
            WHERE developer_id = ? AND session_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (developer_id, session_id, limit),
        ).fetchall()
    return [dict(r) for r in reversed(rows)]


def has_covered_topic(developer_id: int, topic: str) -> bool:
    """Return True if the developer has already covered this topic."""
    with _connect() as conn:
        row = conn.execute(
            "SELECT id FROM progress_tracking WHERE developer_id = ? AND topic = ? LIMIT 1",
            (developer_id, topic),
        ).fetchone()
    return row is not None


# ── Learning Path ─────────────────────────────────────────────────────────────

def save_learning_path(developer_id: int, docs: list[dict]) -> None:
    """
    Persist a generated learning path.
    Each doc dict: {doc_path, doc_title, category, priority_order, reason}
    Clears the previous path for this developer before inserting.
    id is auto-assigned for each new row.
    """
    with _connect() as conn:
        conn.execute(
            "DELETE FROM learning_path WHERE developer_id = ?",
            (developer_id,),
        )

        records = [
            {
                "developer_id":  developer_id,
                "doc_path":      doc["doc_path"],
                "doc_title":     doc["doc_title"],
                "category":      doc["category"],
                "priority_order":doc["priority_order"],
                "reason":        doc.get("reason", ""),
                "status":        "not_started",
                "started_at":    None,
                "completed_at":  None,
                "created_at":    _now(),
                "updated_at":    _now(),
            }
            for doc in docs
        ]

        conn.executemany(
            """
            INSERT INTO learning_path
                (developer_id, doc_path, doc_title, category, priority_order,
                 reason, status, started_at, completed_at, created_at, updated_at)
            VALUES
                (:developer_id, :doc_path, :doc_title, :category, :priority_order,
                 :reason, :status, :started_at, :completed_at, :created_at, :updated_at)
            """,
            records,
        )


def get_learning_path(developer_id: int) -> list[dict]:
    """Return the full learning path for a developer, ordered by priority."""
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT * FROM learning_path
            WHERE developer_id = ?
            ORDER BY priority_order
            """,
            (developer_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def mark_doc_started(developer_id: int, doc_path: str) -> None:
    """Mark a document as in_progress if it was not_started."""
    with _connect() as conn:
        conn.execute(
            """
            UPDATE learning_path
            SET status = 'in_progress', started_at = ?, updated_at = ?
            WHERE developer_id = ? AND doc_path = ? AND status = 'not_started'
            """,
            (_now(), _now(), developer_id, doc_path),
        )


def mark_doc_completed(developer_id: int, doc_path: str) -> None:
    """Mark a document as completed."""
    with _connect() as conn:
        conn.execute(
            """
            UPDATE learning_path
            SET status = 'completed', completed_at = ?, updated_at = ?
            WHERE developer_id = ? AND doc_path = ?
            """,
            (_now(), _now(), developer_id, doc_path),
        )


def record_doc_read(
    developer_id: int,
    session_id: int,
    doc_path: str,
    doc_title: str,
) -> None:
    """
    Record that a developer marked a document as read via the UI button.

    Does all three things required for nudge logic to work correctly:
      1. Updates learning_path status → 'completed'  (not_started decreases)
      2. Inserts into progress_tracking              (total_questions increases)
      3. Increments sessions.message_count           (should_nudge fires correctly)

    Uses a [READ] prefix on the query field to distinguish document reads
    from questions asked — useful for analytics and LLM history filtering.
    """
    # 1. Mark the document as completed in learning_path
    mark_doc_completed(developer_id, doc_path)

    # 2. Insert into progress_tracking so total_questions count increments
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO progress_tracking
                (developer_id, topic, source_doc, query,
                 summary, session_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                developer_id,
                doc_title,                              # topic = document title
                doc_path,                               # source_doc = doc path
                f"[READ] {doc_title}",                  # [READ] prefix distinguishes from questions
                f"Developer marked '{doc_title}' as read.",
                session_id,
                _now(),
            ),
        )

    # 3. Keep session topics in sync and increment message counter
    #    so should_nudge (total_questions % PROACTIVE_NUDGE_AFTER == 0) fires correctly
    add_topic_to_session(session_id, doc_title)
    increment_session_messages(session_id)


def get_next_unread_doc(developer_id: int) -> Optional[dict]:
    """
    Return the next not_started document in the learning path.
    Used by the proactive nudge logic.
    """
    with _connect() as conn:
        row = conn.execute(
            """
            SELECT * FROM learning_path
            WHERE developer_id = ? AND status = 'not_started'
            ORDER BY priority_order
            LIMIT 1
            """,
            (developer_id,),
        ).fetchone()
    return dict(row) if row else None


def get_progress_summary(developer_id: int) -> dict:
    """
    Return a summary of the developer's overall onboarding progress.
    Used by the orchestrator to decide whether to nudge.
    """
    with _connect() as conn:
        path_stats = conn.execute(
            """
            SELECT status, COUNT(*) as count
            FROM learning_path
            WHERE developer_id = ?
            GROUP BY status
            """,
            (developer_id,),
        ).fetchall()

        total_questions = conn.execute(
            "SELECT COUNT(*) as c FROM progress_tracking WHERE developer_id = ?",
            (developer_id,),
        ).fetchone()["c"]

        total_sessions = conn.execute(
            "SELECT COUNT(*) as c FROM sessions WHERE developer_id = ?",
            (developer_id,),
        ).fetchone()["c"]

    stats      = {r["status"]: r["count"] for r in path_stats}
    total_docs = sum(stats.values())

    return {
        "total_docs":      total_docs,
        "completed":       stats.get("completed", 0),
        "in_progress":     stats.get("in_progress", 0),
        "not_started":     stats.get("not_started", total_docs),
        "completion_pct":  round(stats.get("completed", 0) / max(total_docs, 1) * 100),
        "total_questions": total_questions,
        "total_sessions":  total_sessions,
        "should_nudge":    total_questions > 0 and total_questions % PROACTIVE_NUDGE_AFTER == 0,
    }
# memory/progress.py
# @Author: Saneh Lata
# Tracks what a developer has covered across sessions.
# Powers the "don't repeat yourself" and proactive nudge behaviour
# of the Learning Path agent.

import sqlite3
import json
import uuid
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

def start_session(developer_id: str) -> str:
    """Create a new session and return its ID."""
    session_id = str(uuid.uuid4())
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO sessions (id, developer_id, started_at, message_count, topics_covered)
            VALUES (?, ?, ?, 0, '[]')
            """,
            (session_id, developer_id, _now()),
        )
    return session_id


def end_session(session_id: str) -> None:
    """Mark a session as ended."""
    with _connect() as conn:
        conn.execute(
            "UPDATE sessions SET ended_at = ? WHERE id = ?",
            (_now(), session_id),
        )


def increment_session_messages(session_id: str) -> None:
    """Increment the message counter for a session."""
    with _connect() as conn:
        conn.execute(
            "UPDATE sessions SET message_count = message_count + 1 WHERE id = ?",
            (session_id,),
        )


def add_topic_to_session(session_id: str, topic: str) -> None:
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


def get_session(session_id: str) -> Optional[dict]:
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
    developer_id: str,
    session_id: str,
    topic: str,
    query: str,
    summary: str,
    source_doc: str = None,
) -> None:
    """
    Record that a developer covered a topic during a session.
    Called after every successfully answered question.
    """
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO progress_tracking
                (id, developer_id, topic, source_doc, query, summary, session_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid.uuid4()),
                developer_id,
                topic,
                source_doc,
                query,
                summary,
                session_id,
                _now(),
            ),
        )

    # Also update the session topics list
    add_topic_to_session(session_id, topic)
    increment_session_messages(session_id)


def get_covered_topics(developer_id: str) -> list[str]:
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


def get_covered_docs(developer_id: str) -> list[str]:
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


def get_recent_history(developer_id: str, session_id: str, limit: int = 6) -> list[dict]:
    """
    Return the most recent progress entries for a session.
    Used to build conversational context for the LLM.
    """
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT topic, query, summary, source_doc, created_at
            FROM progress_tracking
            WHERE developer_id = ? AND session_id = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (developer_id, session_id, limit),
        ).fetchall()
    return [dict(r) for r in reversed(rows)]   # oldest first for LLM context


def has_covered_topic(developer_id: str, topic: str) -> bool:
    """Return True if the developer has already covered this topic."""
    with _connect() as conn:
        row = conn.execute(
            "SELECT id FROM progress_tracking WHERE developer_id = ? AND topic = ? LIMIT 1",
            (developer_id, topic),
        ).fetchone()
    return row is not None


# ── Learning Path ─────────────────────────────────────────────────────────────

def save_learning_path(developer_id: str, docs: list[dict]) -> None:
    """
    Persist a generated learning path.
    Each doc: {doc_path, doc_title, category, priority_order, reason}
    Clears the previous path for this developer before inserting.
    """
    with _connect() as conn:
        conn.execute(
            "DELETE FROM learning_path WHERE developer_id = ?",
            (developer_id,),
        )

        records = [
            {
                "id":            str(uuid.uuid4()),
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
                (id, developer_id, doc_path, doc_title, category, priority_order,
                 reason, status, started_at, completed_at, created_at, updated_at)
            VALUES
                (:id, :developer_id, :doc_path, :doc_title, :category, :priority_order,
                 :reason, :status, :started_at, :completed_at, :created_at, :updated_at)
            """,
            records,
        )


def get_learning_path(developer_id: str) -> list[dict]:
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


def mark_doc_started(developer_id: str, doc_path: str) -> None:
    with _connect() as conn:
        conn.execute(
            """
            UPDATE learning_path
            SET status = 'in_progress', started_at = ?, updated_at = ?
            WHERE developer_id = ? AND doc_path = ? AND status = 'not_started'
            """,
            (_now(), _now(), developer_id, doc_path),
        )


def mark_doc_completed(developer_id: str, doc_path: str) -> None:
    with _connect() as conn:
        conn.execute(
            """
            UPDATE learning_path
            SET status = 'completed', completed_at = ?, updated_at = ?
            WHERE developer_id = ? AND doc_path = ?
            """,
            (_now(), _now(), developer_id, doc_path),
        )


def get_next_unread_doc(developer_id: str) -> Optional[dict]:
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


def get_progress_summary(developer_id: str) -> dict:
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

    stats = {r["status"]: r["count"] for r in path_stats}
    total_docs = sum(stats.values())

    return {
        "total_docs":       total_docs,
        "completed":        stats.get("completed", 0),
        "in_progress":      stats.get("in_progress", 0),
        "not_started":      stats.get("not_started", total_docs),
        "completion_pct":   round(stats.get("completed", 0) / max(total_docs, 1) * 100),
        "total_questions":  total_questions,
        "total_sessions":   total_sessions,
        "should_nudge":     total_questions > 0 and total_questions % PROACTIVE_NUDGE_AFTER == 0,
    }

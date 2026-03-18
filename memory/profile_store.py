# memory/profile_store.py
# @Author: Saneh Lata
# Reads and writes developer profiles, access requests, and DL subscriptions
# to/from the SQLite onboarding.db. All persistence for the profiler agent
# lives here.
#
# Primary keys are INTEGER AUTOINCREMENT — SQLite assigns them automatically.
# All functions return and accept int IDs, not UUID strings.

import sqlite3
import json
from datetime import datetime
from typing import Optional

from config import DB_PATH


# ── Helpers ───────────────────────────────────────────────────────────────────

def _now() -> str:
    return datetime.utcnow().isoformat()


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


# ── Developer Profile ─────────────────────────────────────────────────────────

def save_profile(profile: dict) -> int:
    """
    Insert or update a developer profile.
    Returns the developer's integer ID (auto-assigned on insert,
    existing ID on update).

    Expected keys:
        name, email, team_id, team_name, manager_name, manager_email,
        role_title, experience_level, skills (list), start_date
    """
    skills = json.dumps(profile.get("skills", []))

    with _connect() as conn:
        existing = conn.execute(
            "SELECT id FROM developer_profiles WHERE email = ?",
            (profile["email"],),
        ).fetchone()

        if existing:
            dev_id = existing["id"]
            conn.execute(
                """
                UPDATE developer_profiles SET
                    name = :name, team_id = :team_id, team_name = :team_name,
                    manager_name = :manager_name, manager_email = :manager_email,
                    role_title = :role_title, experience_level = :experience_level,
                    skills = :skills, start_date = :start_date,
                    profile_complete = 1, updated_at = :updated_at
                WHERE id = :id
                """,
                {
                    "id":               dev_id,
                    "name":             profile["name"],
                    "team_id":          profile["team_id"],
                    "team_name":        profile["team_name"],
                    "manager_name":     profile["manager_name"],
                    "manager_email":    profile["manager_email"],
                    "role_title":       profile.get("role_title", "Software Engineer"),
                    "experience_level": profile.get("experience_level", "mid"),
                    "skills":           skills,
                    "start_date":       profile.get("start_date", _now()[:10]),
                    "updated_at":       _now(),
                },
            )
        else:
            # Omit id — SQLite auto-assigns the next integer
            cursor = conn.execute(
                """
                INSERT INTO developer_profiles
                    (name, email, team_id, team_name, manager_name, manager_email,
                     role_title, experience_level, skills, start_date,
                     onboarding_status, profile_complete, created_at, updated_at)
                VALUES
                    (:name, :email, :team_id, :team_name, :manager_name,
                     :manager_email, :role_title, :experience_level, :skills,
                     :start_date, 'in_progress', 1, :created_at, :updated_at)
                """,
                {
                    "name":             profile["name"],
                    "email":            profile["email"],
                    "team_id":          profile["team_id"],
                    "team_name":        profile["team_name"],
                    "manager_name":     profile["manager_name"],
                    "manager_email":    profile["manager_email"],
                    "role_title":       profile.get("role_title", "Software Engineer"),
                    "experience_level": profile.get("experience_level", "mid"),
                    "skills":           skills,
                    "start_date":       profile.get("start_date", _now()[:10]),
                    "created_at":       _now(),
                    "updated_at":       _now(),
                },
            )
            dev_id = cursor.lastrowid   # auto-assigned integer PK

    return dev_id


def get_profile(developer_id: int) -> Optional[dict]:
    """Fetch a developer profile by integer ID. Returns None if not found."""
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM developer_profiles WHERE id = ?",
            (developer_id,),
        ).fetchone()

    if not row:
        return None

    p = dict(row)
    p["skills"] = json.loads(p["skills"])
    return p


def get_profile_by_email(email: str) -> Optional[dict]:
    """Fetch a developer profile by email. Returns None if not found."""
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM developer_profiles WHERE email = ?",
            (email,),
        ).fetchone()

    if not row:
        return None

    p = dict(row)
    p["skills"] = json.loads(p["skills"])
    return p


def update_onboarding_status(developer_id: int, status: str) -> None:
    """Update onboarding status: pending | in_progress | completed."""
    with _connect() as conn:
        conn.execute(
            "UPDATE developer_profiles SET onboarding_status = ?, updated_at = ? WHERE id = ?",
            (status, _now(), developer_id),
        )


def list_all_profiles() -> list[dict]:
    """Return all developer profiles ordered by id."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM developer_profiles ORDER BY id"
        ).fetchall()

    profiles = []
    for row in rows:
        p = dict(row)
        p["skills"] = json.loads(p["skills"])
        profiles.append(p)
    return profiles


# ── Access Requests ───────────────────────────────────────────────────────────

def save_access_request(developer_id: int, request: dict) -> int:
    """
    Insert an access request record.
    Returns the auto-assigned integer request ID.

    Expected keys in request:
        system_id, system_name, ticket_type, ticket_id (optional),
        ticket_summary, status, access_level, requires_approval, sla_hours
    """
    with _connect() as conn:
        cursor = conn.execute(
            """
            INSERT INTO access_requests
                (developer_id, system_id, system_name, ticket_type, ticket_id,
                 ticket_summary, status, access_level, requires_approval, sla_hours,
                 raised_at, created_at, updated_at)
            VALUES
                (:developer_id, :system_id, :system_name, :ticket_type,
                 :ticket_id, :ticket_summary, :status, :access_level,
                 :requires_approval, :sla_hours, :raised_at, :created_at, :updated_at)
            """,
            {
                "developer_id":     developer_id,
                "system_id":        request["system_id"],
                "system_name":      request["system_name"],
                "ticket_type":      request["ticket_type"],
                "ticket_id":        request.get("ticket_id"),
                "ticket_summary":   request["ticket_summary"],
                "status":           request.get("status", "raised"),
                "access_level":     request["access_level"],
                "requires_approval":1 if request.get("requires_approval") else 0,
                "sla_hours":        request["sla_hours"],
                "raised_at":        _now(),
                "created_at":       _now(),
                "updated_at":       _now(),
            },
        )
        return cursor.lastrowid


def update_access_request_status(
    request_id: int,
    status: str,
    ticket_id: str = None,
) -> None:
    """Update the status of an access request, optionally storing the ticket ID."""
    with _connect() as conn:
        if ticket_id:
            conn.execute(
                "UPDATE access_requests SET status = ?, ticket_id = ?, updated_at = ? WHERE id = ?",
                (status, ticket_id, _now(), request_id),
            )
        else:
            conn.execute(
                "UPDATE access_requests SET status = ?, updated_at = ? WHERE id = ?",
                (status, _now(), request_id),
            )


def get_access_requests(developer_id: int) -> list[dict]:
    """Return all access requests for a developer, ordered by id."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM access_requests WHERE developer_id = ? ORDER BY id",
            (developer_id,),
        ).fetchall()
    return [dict(r) for r in rows]


# ── DL Subscriptions ──────────────────────────────────────────────────────────

def save_dl_subscription(developer_id: int, subscription: dict) -> int:
    """
    Insert a distribution list subscription record.
    Returns the auto-assigned integer subscription ID.

    Expected keys: dl_id, dl_name, dl_email, owner_name, owner_email, status
    """
    with _connect() as conn:
        cursor = conn.execute(
            """
            INSERT INTO dl_subscriptions
                (developer_id, dl_id, dl_name, dl_email, owner_name,
                 owner_email, status, email_sent_at, created_at, updated_at)
            VALUES
                (:developer_id, :dl_id, :dl_name, :dl_email,
                 :owner_name, :owner_email, :status, :email_sent_at,
                 :created_at, :updated_at)
            """,
            {
                "developer_id": developer_id,
                "dl_id":        subscription["dl_id"],
                "dl_name":      subscription["dl_name"],
                "dl_email":     subscription["dl_email"],
                "owner_name":   subscription["owner_name"],
                "owner_email":  subscription["owner_email"],
                "status":       subscription.get("status", "email_sent"),
                "email_sent_at":_now(),
                "created_at":   _now(),
                "updated_at":   _now(),
            },
        )
        return cursor.lastrowid


def get_dl_subscriptions(developer_id: int) -> list[dict]:
    """Return all DL subscription records for a developer, ordered by id."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM dl_subscriptions WHERE developer_id = ? ORDER BY id",
            (developer_id,),
        ).fetchall()
    return [dict(r) for r in rows]


# ── Agent Action Log ──────────────────────────────────────────────────────────

def log_agent_action(
    developer_id: int,
    action_type: str,
    action_data: dict,
    status: str = "success",
    session_id: Optional[int] = None,
    error: str = None,
) -> None:
    """Write an entry to the agent action audit log."""
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO agent_action_log
                (developer_id, session_id, action_type, action_data,
                 status, error, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                developer_id,
                session_id,
                action_type,
                json.dumps(action_data),
                status,
                error,
                _now(),
            ),
        )
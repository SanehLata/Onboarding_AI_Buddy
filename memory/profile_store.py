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

from config import DB_PATH, log


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
            log.info(
                "[PROFILE_STORE] UPDATE developer_profiles — dev_id=%s email='%s'",
                dev_id, profile.get("email")
            )
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
            log.info(
                "[PROFILE_STORE] INSERT developer_profiles — dev_id=%s name='%s' "
                "email='%s' team='%s'",
                dev_id, profile.get("name"), profile.get("email"), profile.get("team_name")
            )

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
    log.info(
        "[PROFILE_STORE] UPDATE onboarding_status — dev_id=%s status='%s'",
        developer_id, status
    )
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
        req_id = cursor.lastrowid
        log.info(
            "[PROFILE_STORE] INSERT access_requests — req_id=%s dev_id=%s "
            "system='%s' ticket_id='%s' requires_approval=%s",
            req_id, developer_id,
            request.get("system_name"), request.get("ticket_id"),
            bool(request.get("requires_approval"))
        )
        return req_id


def update_access_request_status(
    request_id: int,
    status: str,
    ticket_id: str = None,
) -> None:
    """Update the status of an access request, optionally storing the ticket ID."""
    log.info(
        "[PROFILE_STORE] UPDATE access_requests — req_id=%s status='%s' ticket_id='%s'",
        request_id, status, ticket_id
    )
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
        sub_id = cursor.lastrowid
        log.info(
            "[PROFILE_STORE] INSERT dl_subscriptions — sub_id=%s dev_id=%s "
            "dl_name='%s' dl_email='%s' owner='%s'",
            sub_id, developer_id,
            subscription.get("dl_name"), subscription.get("dl_email"),
            subscription.get("owner_name")
        )
        return sub_id


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
    if status == "success":
        log.info(
            "[PROFILE_STORE] INSERT agent_action_log — dev_id=%s session_id=%s "
            "action='%s' status=%s",
            developer_id, session_id, action_type, status
        )
    else:
        log.warning(
            "[PROFILE_STORE] INSERT agent_action_log — dev_id=%s session_id=%s "
            "action='%s' status=%s error='%s'",
            developer_id, session_id, action_type, status, error
        )
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


# ── Manager queries ───────────────────────────────────────────────────────────

def get_all_pending_requests() -> list[dict]:
    """
    Return all access requests with requires_approval=1 and status='raised',
    joined with developer name and email. Used by the manager approval screen.
    """
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT
                ar.id, ar.developer_id, ar.system_name, ar.ticket_id,
                ar.ticket_summary, ar.access_level, ar.ticket_type,
                ar.sla_hours, ar.raised_at, ar.status,
                dp.name  AS developer_name,
                dp.email AS developer_email,
                dp.team_name, dp.manager_email
            FROM access_requests ar
            JOIN developer_profiles dp ON ar.developer_id = dp.id
            WHERE ar.requires_approval = 1
              AND ar.status IN ('raised', 'pending_approval')
            ORDER BY ar.raised_at ASC
            """,
        ).fetchall()
    return [dict(r) for r in rows]


def get_all_access_requests_for_manager(manager_email: str) -> list[dict]:
    """
    Return all access requests for developers reporting to this manager,
    including approved and completed — for the full history view.
    """
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT
                ar.id, ar.developer_id, ar.system_name, ar.ticket_id,
                ar.ticket_summary, ar.access_level, ar.ticket_type,
                ar.sla_hours, ar.raised_at, ar.status, ar.requires_approval,
                dp.name  AS developer_name,
                dp.email AS developer_email,
                dp.team_name
            FROM access_requests ar
            JOIN developer_profiles dp ON ar.developer_id = dp.id
            WHERE dp.manager_email = ?
            ORDER BY ar.raised_at DESC
            """,
            (manager_email,),
        ).fetchall()
    return [dict(r) for r in rows]


def get_agent_action_log(developer_id: int, limit: int = 20) -> list[dict]:
    """Return recent agent action log entries for a developer."""
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT action_type, action_data, status, error, created_at
            FROM agent_action_log
            WHERE developer_id = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (developer_id, limit),
        ).fetchall()
    return [dict(r) for r in rows]


def get_sessions_for_developer(developer_id: int) -> list[dict]:
    """Return all sessions for a developer with message counts."""
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT id, started_at, ended_at, message_count, topics_covered
            FROM sessions
            WHERE developer_id = ?
            ORDER BY started_at ASC
            """,
            (developer_id,),
        ).fetchall()
    result = []
    for r in rows:
        d = dict(r)
        import json as _json
        d["topics_covered"] = _json.loads(d["topics_covered"] or "[]")
        result.append(d)
    return result


# ── DL subscription auto-completion ──────────────────────────────────────────

def _business_hours_elapsed(sent_at_iso: str) -> float:
    """
    Calculate the number of business hours elapsed since sent_at_iso.
    Business hours: Monday–Friday 09:00–17:00 UTC.
    Weekends and outside-hours time do not count.
    """
    from datetime import datetime, timedelta

    try:
        start = datetime.fromisoformat(sent_at_iso)
    except Exception:
        return 0.0

    now   = datetime.utcnow()
    if now <= start:
        return 0.0

    WORK_START = 9   # 09:00 UTC
    WORK_END   = 17  # 17:00 UTC

    elapsed_bh = 0.0
    current    = start

    while current < now:
        # Skip weekends (5=Saturday, 6=Sunday)
        if current.weekday() >= 5:
            current += timedelta(hours=1)
            continue

        hour = current.hour
        if hour < WORK_START or hour >= WORK_END:
            current += timedelta(hours=1)
            continue

        # This hour is a business hour — count how much of it has elapsed
        next_hour = current.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
        chunk_end = min(next_hour, now)
        elapsed_bh += (chunk_end - current).total_seconds() / 3600.0
        current = next_hour

    return elapsed_bh


def auto_complete_dl_subscriptions(
    developer_id: int,
    business_hours_threshold: int = 24,
) -> int:
    """
    Simulate the DL owner manually adding the developer in Outlook.

    Any subscription in 'email_sent' status where the elapsed business
    hours since email_sent_at exceeds business_hours_threshold is
    automatically moved to 'subscribed'.

    Uses business hours (Mon–Fri 09:00–17:00 UTC) so weekends and
    out-of-hours time don't count toward the threshold — mirroring
    real behaviour where the DL owner acts during working hours.

    Called lazily when the Access tab renders — no background job needed.
    Returns the number of subscriptions updated.
    """
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT id, email_sent_at
            FROM   dl_subscriptions
            WHERE  developer_id = ?
              AND  status       = 'email_sent'
              AND  email_sent_at IS NOT NULL
            """,
            (developer_id,),
        ).fetchall()

    to_update = [
        r["id"] for r in rows
        if _business_hours_elapsed(r["email_sent_at"]) >= business_hours_threshold
    ]

    if not to_update:
        return 0

    placeholders = ",".join("?" * len(to_update))
    with _connect() as conn:
        cursor = conn.execute(
            f"""
            UPDATE dl_subscriptions
            SET    status     = 'subscribed',
                   updated_at = ?
            WHERE  id IN ({placeholders})
            """,
            [_now()] + to_update,
        )
        updated = cursor.rowcount

    log.info(
        "[PROFILE_STORE] auto_complete_dl_subscriptions — "
        "dev_id=%s updated=%d threshold=%d business hours",
        developer_id, updated, business_hours_threshold
    )
    return updated
# tools/ticketing.py
# @Author: Saneh Lata
# Mock ticketing tool — simulates Jira and ServiceNow ticket creation.
# Returns realistic fake responses. In production, replace the API call
# bodies with real Jira REST API or ServiceNow REST API calls.

import json
import time
import random
import string
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from config import TEAMS_JSON, SYSTEMS_JSON, MAX_RETRIES, RETRY_DELAY_SECONDS, log


# ── Helpers ───────────────────────────────────────────────────────────────────

def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _ticket_id(prefix: str = "TICK") -> str:
    """Generate a realistic-looking mock ticket ID."""
    number = random.randint(10000, 99999)
    return f"{prefix}-{number}"


def _sn_id() -> str:
    """Generate a ServiceNow-style request number."""
    return "REQ" + "".join(random.choices(string.digits, k=7))


def _now() -> str:
    return datetime.utcnow().isoformat()


def _due_date(hours: int) -> str:
    """Return a due date string offset by `hours` from now."""
    due = datetime.utcnow() + timedelta(hours=hours)
    return due.isoformat()


def _simulate_delay(min_ms: int = 100, max_ms: int = 400) -> None:
    """Simulate a brief API call delay for realism."""
    time.sleep(random.uniform(min_ms, max_ms) / 1000)


def _get_system(system_id: str) -> Optional[dict]:
    """Look up a system definition from systems.json."""
    data = _load_json(SYSTEMS_JSON)
    for s in data["systems"]:
        if s["system_id"] == system_id:
            return s
    return None


def _get_team(team_id: str) -> Optional[dict]:
    """Look up a team definition from teams.json."""
    data = _load_json(TEAMS_JSON)
    for t in data["teams"]:
        if t["team_id"] == team_id:
            return t
    return None


# ── Core ticket creation ──────────────────────────────────────────────────────

def create_ticket(
    system_id: str,
    developer_name: str,
    developer_email: str,
    team_id: str,
    team_name: str,
    manager_name: str,
) -> dict:
    """
    Simulate raising an access request ticket for one system.

    Returns a result dict:
    {
        success: bool,
        ticket_id: str,
        system_id: str,
        system_name: str,
        ticket_type: str,
        status: str,
        sla_hours: int,
        due_date: str,
        message: str,
        error: str | None,
    }
    """
    system = _get_system(system_id)
    if not system:
        log.error(
            "[TICKETING] create_ticket — system_id='%s' not found in systems.json",
            system_id
        )
        return _error_response(system_id, system_id, f"System '{system_id}' not found in systems.json")

    log.info(
        "[TICKETING] create_ticket — system='%s' developer='%s' team='%s' "
        "requires_approval=%s",
        system.get("system_name"), developer_name, team_name,
        system.get("requires_approval")
    )
    attempt = 0
    last_error = None

    while attempt < MAX_RETRIES:
        attempt += 1
        try:
            _simulate_delay()

            # Simulate a 5% failure rate to demonstrate retry logic
            if random.random() < 0.05:
                raise ConnectionError(f"Mock API timeout on attempt {attempt}")

            # Build the mock ticket
            ticket_id = (
                _sn_id() if system["ticket_type"] == "CHANGE_REQUEST"
                else _ticket_id("JIRA")
            )

            summary = system["ticket_summary_template"].format(
                developer_name=developer_name,
                team_name=team_name,
            )

            log.info(
                "[TICKETING] ticket raised — ticket_id='%s' system='%s' "
                "type='%s' sla_hours=%s attempts=%d",
                ticket_id, system["system_name"], system["ticket_type"],
                system["sla"]["resolution_hours"], attempt
            )

            return {
                "success":      True,
                "ticket_id":    ticket_id,
                "system_id":    system["system_id"],
                "system_name":  system["system_name"],
                "ticket_type":  system["ticket_type"],
                "access_level": system["default_access_level"],
                "requires_approval": system["requires_approval"],
                "status":       "raised",
                "priority":     system["ticket_fields"]["priority"],
                "summary":      summary,
                "sla_hours":    system["sla"]["resolution_hours"],
                "due_date":     _due_date(system["sla"]["resolution_hours"]),
                "raised_by":    "Onboarding Buddy (automated)",
                "raised_at":    _now(),
                "message":      (
                    f"✅ Ticket {ticket_id} raised for {system['system_name']} access.\n"
                    f"   Access level : {system['default_access_level']}\n"
                    f"   Approval     : {'Required — notified ' + manager_name if system['requires_approval'] else 'Not required'}\n"
                    f"   SLA          : {system['sla']['resolution_hours']} hours"
                ),
                "error":        None,
                "attempts":     attempt,
            }

        except Exception as exc:
            last_error = str(exc)
            log.warning(
                "[TICKETING] attempt %d/%d failed — system='%s' error='%s'",
                attempt, MAX_RETRIES, system.get("system_name"), last_error
            )
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY_SECONDS)

    # All retries exhausted
    log.error(
        "[TICKETING] create_ticket FAILED — system='%s' developer='%s' "
        "after %d attempts last_error='%s'",
        system.get("system_name"), developer_name, MAX_RETRIES, last_error
    )
    return _error_response(
        system_id,
        system.get("system_name", system_id),
        f"Failed after {MAX_RETRIES} attempts. Last error: {last_error}",
    )


def _error_response(system_id: str, system_name: str, error: str) -> dict:
    return {
        "success":      False,
        "ticket_id":    None,
        "system_id":    system_id,
        "system_name":  system_name,
        "ticket_type":  None,
        "access_level": None,
        "requires_approval": False,
        "status":       "failed",
        "priority":     None,
        "summary":      None,
        "sla_hours":    None,
        "due_date":     None,
        "raised_by":    "Onboarding Buddy (automated)",
        "raised_at":    _now(),
        "message":      f"❌ Failed to raise ticket for {system_name}. Admin has been notified.",
        "error":        error,
        "attempts":     MAX_RETRIES,
    }


# ── Bulk provisioning ─────────────────────────────────────────────────────────

def provision_all_access(
    team_id: str,
    developer_name: str,
    developer_email: str,
    team_name: str,
    manager_name: str,
) -> dict:
    """
    Raise tickets for all systems required by a team.
    Returns a summary of successes and failures.
    """
    team = _get_team(team_id)
    if not team:
        log.error(
            "[TICKETING] provision_all_access — team_id='%s' not found in teams.json",
            team_id
        )
        return {
            "success":  False,
            "message":  f"❌ Team '{team_id}' not found. Cannot provision access.",
            "results":  [],
        }

    required_systems = team["required_systems"]
    log.info(
        "[TICKETING] provision_all_access — team='%s' developer='%s' "
        "systems_count=%d systems=%s",
        team_name, developer_name, len(required_systems), required_systems
    )
    results          = []
    successes        = 0
    failures         = 0

    for system_id in required_systems:
        result = create_ticket(
            system_id=system_id,
            developer_name=developer_name,
            developer_email=developer_email,
            team_id=team_id,
            team_name=team_name,
            manager_name=manager_name,
        )
        results.append(result)
        if result["success"]:
            successes += 1
        else:
            failures += 1

    status_line = (
        f"✅ All {successes} access tickets raised successfully."
        if failures == 0
        else f"⚠️  {successes} tickets raised, {failures} failed — admin notified for failed items."
    )

    if failures == 0:
        log.info(
            "[TICKETING] provision_all_access complete — team='%s' "
            "raised=%d failed=%d",
            team_name, successes, failures
        )
    else:
        log.warning(
            "[TICKETING] provision_all_access partial failure — team='%s' "
            "raised=%d failed=%d",
            team_name, successes, failures
        )

    return {
        "success":          failures == 0,
        "message":          status_line,
        "total_systems":    len(required_systems),
        "tickets_raised":   successes,
        "tickets_failed":   failures,
        "results":          results,
    }


# ── Status check ─────────────────────────────────────────────────────────────

def check_ticket_status(ticket_id: str) -> dict:
    """
    Simulate checking the status of an existing ticket.
    In production this would call the Jira or ServiceNow API.
    """
    _simulate_delay()

    # Mock status progression based on ticket ID hash
    statuses = ["raised", "in_progress", "approved", "completed"]
    idx = abs(hash(ticket_id)) % len(statuses)

    return {
        "ticket_id":  ticket_id,
        "status":     statuses[idx],
        "updated_at": _now(),
        "message":    f"Ticket {ticket_id} is currently '{statuses[idx]}'.",
    }
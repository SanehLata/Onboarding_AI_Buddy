# tools/access.py
# @Author: Saneh Lata
# Mock AD group provisioning tool — simulates Active Directory group
# membership requests and status tracking.
# In production, replace _mock_ad_request() with Microsoft Graph API calls.

import json
import time
import random
import uuid
from datetime import datetime, timedelta
from pathlib import Path

from config import TEAMS_JSON, MAX_RETRIES, RETRY_DELAY_SECONDS, log


# ── AD Group definitions ──────────────────────────────────────────────────────
# Maps team_id → list of AD groups the developer should be added to.
# Mirrors the access_provisioning.md documentation.

AD_GROUP_MAP = {
    "team_payments": [
        {"group": "grp-payments-eng",    "description": "Payments Engineering team members",          "approval": False},
        {"group": "grp-engineering-all", "description": "All TechCorp engineers",                      "approval": False},
        {"group": "grp-kafka-dev",       "description": "Kafka development cluster access",            "approval": True},
    ],
    "team_risk": [
        {"group": "grp-risk-eng",        "description": "Risk & Compliance team members",              "approval": False},
        {"group": "grp-engineering-all", "description": "All TechCorp engineers",                      "approval": False},
        {"group": "grp-snowflake-read",  "description": "Snowflake read access — curated datasets",    "approval": True},
    ],
    "team_platform": [
        {"group": "grp-platform-eng",    "description": "Platform Engineering team members",           "approval": False},
        {"group": "grp-engineering-all", "description": "All TechCorp engineers",                      "approval": False},
        {"group": "grp-kubernetes-dev",  "description": "Kubernetes dev and staging cluster access",   "approval": True},
    ],
    "team_data_engineering": [
        {"group": "grp-data-eng",           "description": "Data Engineering team members",             "approval": False},
        {"group": "grp-engineering-all",    "description": "All TechCorp engineers",                    "approval": False},
        {"group": "grp-snowflake-write-dev","description": "Snowflake write access — dev/sandbox only", "approval": True},
    ],
    "team_auth": [
        {"group": "grp-auth-eng",        "description": "Auth & Identity team members",                "approval": False},
        {"group": "grp-engineering-all", "description": "All TechCorp engineers",                      "approval": False},
        {"group": "grp-security-review", "description": "Security review participation",               "approval": True},
    ],
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _now() -> str:
    return datetime.utcnow().isoformat()


def _request_id() -> str:
    return f"AD-REQ-{uuid.uuid4().hex[:8].upper()}"


def _simulate_delay(min_ms: int = 120, max_ms: int = 450) -> None:
    time.sleep(random.uniform(min_ms, max_ms) / 1000)


def _estimated_completion(approval_required: bool) -> str:
    hours = 24 if approval_required else 4
    return (datetime.utcnow() + timedelta(hours=hours)).isoformat()


# ── Core AD request ───────────────────────────────────────────────────────────

def _mock_ad_request(
    group_name: str,
    developer_name: str,
    developer_email: str,
    manager_email: str,
    approval_required: bool,
) -> dict:
    """
    Simulate a single AD group membership request.
    In production: call Microsoft Graph API
        POST https://graph.microsoft.com/v1.0/groups/{group_id}/members/$ref
    """
    _simulate_delay()

    # Simulate a 5% failure rate
    if random.random() < 0.05:
        raise ConnectionError(f"Mock AD API unreachable for group {group_name}")

    return {
        "request_id":          _request_id(),
        "group":               group_name,
        "developer_email":     developer_email,
        "status":              "pending_approval" if approval_required else "provisioned",
        "approval_required":   approval_required,
        "approver_email":      manager_email if approval_required else None,
        "estimated_completion":_estimated_completion(approval_required),
        "requested_at":        _now(),
    }


def request_ad_group_access(
    group_name: str,
    description: str,
    developer_name: str,
    developer_email: str,
    team_name: str,
    manager_email: str,
    approval_required: bool,
) -> dict:
    """
    Request membership in one AD group with retry logic.

    Returns:
    {
        success: bool,
        request_id: str | None,
        group: str,
        description: str,
        status: str,
        approval_required: bool,
        approver_email: str | None,
        estimated_completion: str,
        message: str,
        error: str | None,
    }
    """
    log.info(
        "[ACCESS] request_ad_group_access — group='%s' developer='%s' "
        "approval_required=%s",
        group_name, developer_name, approval_required
    )
    attempt    = 0
    last_error = None

    while attempt < MAX_RETRIES:
        attempt += 1
        try:
            result = _mock_ad_request(
                group_name=group_name,
                developer_name=developer_name,
                developer_email=developer_email,
                manager_email=manager_email,
                approval_required=approval_required,
            )

            status_label = (
                "pending manager approval"
                if approval_required
                else "provisioned automatically"
            )

            log.info(
                "[ACCESS] AD group request submitted — group='%s' request_id='%s' "
                "status='%s' attempts=%d",
                group_name, result["request_id"], result["status"], attempt
            )

            return {
                "success":             True,
                "request_id":          result["request_id"],
                "group":               group_name,
                "description":         description,
                "status":              result["status"],
                "approval_required":   approval_required,
                "approver_email":      result["approver_email"],
                "estimated_completion":result["estimated_completion"],
                "message":             (
                    f"✅ AD group request submitted: {group_name}\n"
                    f"   Description : {description}\n"
                    f"   Status      : {status_label}\n"
                    f"   Request ID  : {result['request_id']}"
                ),
                "error":               None,
                "attempts":            attempt,
            }

        except Exception as exc:
            last_error = str(exc)
            log.warning(
                "[ACCESS] attempt %d/%d failed — group='%s' error='%s'",
                attempt, MAX_RETRIES, group_name, last_error
            )
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY_SECONDS)

    log.error(
        "[ACCESS] request_ad_group_access FAILED — group='%s' developer='%s' "
        "after %d attempts last_error='%s'",
        group_name, developer_name, MAX_RETRIES, last_error
    )
    return {
        "success":             False,
        "request_id":          None,
        "group":               group_name,
        "description":         description,
        "status":              "failed",
        "approval_required":   approval_required,
        "approver_email":      None,
        "estimated_completion":None,
        "message":             f"❌ Failed to request AD group {group_name}. Admin has been notified.",
        "error":               f"Failed after {MAX_RETRIES} attempts. Last error: {last_error}",
        "attempts":            MAX_RETRIES,
    }


# ── Bulk provisioning ─────────────────────────────────────────────────────────

def provision_all_ad_groups(
    team_id: str,
    developer_name: str,
    developer_email: str,
    team_name: str,
    manager_email: str,
) -> dict:
    """
    Request membership in all AD groups required for a team.
    Returns a full summary of successes and failures.
    """
    groups = AD_GROUP_MAP.get(team_id)
    if not groups:
        log.error(
            "[ACCESS] provision_all_ad_groups — no AD groups defined for team_id='%s'",
            team_id
        )
        return {
            "success":  False,
            "message":  f"❌ No AD groups defined for team '{team_id}'.",
            "results":  [],
        }

    log.info(
        "[ACCESS] provision_all_ad_groups — team='%s' developer='%s' group_count=%d",
        team_name, developer_name, len(groups)
    )
    results   = []
    successes = 0
    failures  = 0

    for group_def in groups:
        result = request_ad_group_access(
            group_name=group_def["group"],
            description=group_def["description"],
            developer_name=developer_name,
            developer_email=developer_email,
            team_name=team_name,
            manager_email=manager_email,
            approval_required=group_def["approval"],
        )
        results.append(result)
        if result["success"]:
            successes += 1
        else:
            failures += 1

    auto_provisioned = sum(1 for r in results if r["success"] and not r["approval_required"])
    pending_approval = sum(1 for r in results if r["success"] and r["approval_required"])

    if failures == 0:
        status_line = (
            f"✅ All {successes} AD group requests submitted.\n"
            f"   Auto-provisioned : {auto_provisioned}\n"
            f"   Pending approval : {pending_approval}"
        )
        log.info(
            "[ACCESS] provision_all_ad_groups complete — team='%s' submitted=%d "
            "auto_provisioned=%d pending_approval=%d",
            team_name, successes, auto_provisioned, pending_approval
        )
    else:
        status_line = (
            f"⚠️  {successes}/{len(groups)} AD group requests submitted, {failures} failed.\n"
            f"   Auto-provisioned : {auto_provisioned}\n"
            f"   Pending approval : {pending_approval}\n"
            f"   Admin notified for failures."
        )
        log.warning(
            "[ACCESS] provision_all_ad_groups partial failure — team='%s' "
            "submitted=%d failed=%d",
            team_name, successes, failures
        )

    return {
        "success":            failures == 0,
        "message":            status_line,
        "total_groups":       len(groups),
        "requests_submitted": successes,
        "requests_failed":    failures,
        "auto_provisioned":   auto_provisioned,
        "pending_approval":   pending_approval,
        "results":            results,
    }


# ── Status check ─────────────────────────────────────────────────────────────

def check_ad_request_status(request_id: str) -> dict:
    """
    Simulate checking the status of a submitted AD group request.
    In production: query the AD request tracking system or Microsoft Graph.
    """
    _simulate_delay()

    statuses = ["pending_approval", "approved", "provisioned", "provisioned"]
    idx      = abs(hash(request_id)) % len(statuses)

    return {
        "request_id": request_id,
        "status":     statuses[idx],
        "checked_at": _now(),
        "message":    f"AD request {request_id} is currently '{statuses[idx]}'.",
    }


# ── Convenience ───────────────────────────────────────────────────────────────

def get_ad_groups_for_team(team_id: str) -> list[dict]:
    """Return the list of AD groups defined for a team (for display purposes)."""
    return AD_GROUP_MAP.get(team_id, [])
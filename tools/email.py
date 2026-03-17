# tools/email.py
# @Author: Saneh Lata
# Mock email tool — simulates sending subscription request emails to
# Distribution List owners. Returns realistic send receipts.
# In production, replace _mock_send() with an SMTP or SendGrid call.

import json
import time
import random
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from config import DL_GROUPS_JSON, MAX_RETRIES, RETRY_DELAY_SECONDS


# ── Helpers ───────────────────────────────────────────────────────────────────

def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _now() -> str:
    return datetime.utcnow().isoformat()


def _message_id() -> str:
    return f"msg_{uuid.uuid4().hex[:12]}@onboarding-buddy.techcorp.internal"


def _simulate_delay(min_ms: int = 80, max_ms: int = 300) -> None:
    time.sleep(random.uniform(min_ms, max_ms) / 1000)


def _get_team_dls(team_id: str) -> list[dict]:
    """Return all DL groups for a team from dl_groups.json."""
    data = _load_json(DL_GROUPS_JSON)
    for team_entry in data["distribution_lists"]:
        if team_entry["team_id"] == team_id:
            return team_entry["dl_groups"]
    return []


def _render_email(template: dict, developer_name: str, developer_email: str, start_date: str) -> dict:
    """Fill in template placeholders and return subject + body."""
    replacements = {
        "{developer_name}":  developer_name,
        "{developer_email}": developer_email,
        "{start_date}":      start_date,
        "{owner_name}":      template.get("owner_name_placeholder", ""),
    }

    subject = template["subject"]
    body    = template["body"]

    for placeholder, value in replacements.items():
        subject = subject.replace(placeholder, value)
        body    = body.replace(placeholder, value)

    return {"subject": subject, "body": body}


# ── Core send ─────────────────────────────────────────────────────────────────

def _mock_send(
    to_email: str,
    to_name: str,
    subject: str,
    body: str,
) -> dict:
    """
    Simulate sending one email.
    Returns a send receipt dict.
    In production: replace this with smtplib.SMTP or requests.post(sendgrid_url, ...).
    """
    _simulate_delay()

    # Simulate a 4% failure rate to demonstrate retry logic
    if random.random() < 0.04:
        raise ConnectionError("Mock SMTP timeout — could not reach mail server")

    return {
        "message_id":  _message_id(),
        "to_email":    to_email,
        "to_name":     to_name,
        "subject":     subject,
        "sent_at":     _now(),
        "status":      "delivered",
    }


def send_dl_subscription_email(
    dl: dict,
    developer_name: str,
    developer_email: str,
    start_date: str,
) -> dict:
    """
    Send one subscription request email to a DL owner.

    dl dict expected keys:
        dl_id, dl_name, dl_email, owner_name, owner_email, email_template

    Returns:
    {
        success: bool,
        dl_id: str,
        dl_name: str,
        dl_email: str,
        owner_email: str,
        message_id: str | None,
        sent_at: str | None,
        message: str,
        error: str | None,
    }
    """
    attempt    = 0
    last_error = None

    rendered = _render_email(
        {**dl["email_template"], "owner_name_placeholder": dl["owner_name"]},
        developer_name=developer_name,
        developer_email=developer_email,
        start_date=start_date,
    )

    while attempt < MAX_RETRIES:
        attempt += 1
        try:
            receipt = _mock_send(
                to_email=dl["owner_email"],
                to_name=dl["owner_name"],
                subject=rendered["subject"],
                body=rendered["body"],
            )

            return {
                "success":     True,
                "dl_id":       dl["dl_id"],
                "dl_name":     dl["dl_name"],
                "dl_email":    dl["dl_email"],
                "owner_name":  dl["owner_name"],
                "owner_email": dl["owner_email"],
                "message_id":  receipt["message_id"],
                "sent_at":     receipt["sent_at"],
                "subject":     rendered["subject"],
                "message":     (
                    f"✅ Email sent to {dl['owner_name']} ({dl['owner_email']})\n"
                    f"   DL       : {dl['dl_name']} ({dl['dl_email']})\n"
                    f"   Subject  : {rendered['subject']}"
                ),
                "error":       None,
                "attempts":    attempt,
            }

        except Exception as exc:
            last_error = str(exc)
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY_SECONDS)

    return {
        "success":     False,
        "dl_id":       dl["dl_id"],
        "dl_name":     dl["dl_name"],
        "dl_email":    dl["dl_email"],
        "owner_name":  dl["owner_name"],
        "owner_email": dl["owner_email"],
        "message_id":  None,
        "sent_at":     None,
        "subject":     rendered["subject"],
        "message":     f"❌ Failed to send email to {dl['owner_name']} for {dl['dl_name']}. Admin notified.",
        "error":       f"Failed after {MAX_RETRIES} attempts. Last error: {last_error}",
        "attempts":    MAX_RETRIES,
    }


# ── Bulk send ─────────────────────────────────────────────────────────────────

def send_all_dl_emails(
    team_id: str,
    developer_name: str,
    developer_email: str,
    start_date: str,
) -> dict:
    """
    Send DL subscription emails for all distribution lists mapped to a team.
    Returns a summary of all sends.
    """
    dls = _get_team_dls(team_id)

    if not dls:
        return {
            "success":   False,
            "message":   f"❌ No distribution lists found for team '{team_id}'.",
            "results":   [],
        }

    results   = []
    successes = 0
    failures  = 0

    for dl in dls:
        result = send_dl_subscription_email(
            dl=dl,
            developer_name=developer_name,
            developer_email=developer_email,
            start_date=start_date,
        )
        results.append(result)
        if result["success"]:
            successes += 1
        else:
            failures += 1

    status_line = (
        f"✅ All {successes} DL subscription emails sent successfully."
        if failures == 0
        else f"⚠️  {successes} emails sent, {failures} failed — admin notified."
    )

    return {
        "success":         failures == 0,
        "message":         status_line,
        "total_dls":       len(dls),
        "emails_sent":     successes,
        "emails_failed":   failures,
        "results":         results,
    }


# ── Notification emails ───────────────────────────────────────────────────────

def send_welcome_email(
    developer_name: str,
    developer_email: str,
    team_name: str,
    manager_name: str,
    start_date: str,
) -> dict:
    """
    Send a welcome email directly to the new developer.
    Confirms their onboarding has been initiated.
    """
    subject = f"Welcome to {team_name}, {developer_name.split()[0]}! Your onboarding has started."
    body = f"""Hi {developer_name},

Welcome to TechCorp! Your onboarding has been initiated by the Onboarding Buddy system.

Here's what's happening automatically:
  • Access tickets have been raised for all required systems
  • Subscription emails have been sent to your team's distribution list owners
  • A personalised learning path has been generated for you

Your manager {manager_name} has been notified and will be in touch shortly.

Start date  : {start_date}
Team        : {team_name}

Check in with Onboarding Buddy any time to ask questions about your team,
architecture, tools, or processes.

Best of luck,
Onboarding Buddy — TechCorp Engineering
"""

    attempt    = 0
    last_error = None

    while attempt < MAX_RETRIES:
        attempt += 1
        try:
            receipt = _mock_send(
                to_email=developer_email,
                to_name=developer_name,
                subject=subject,
                body=body,
            )
            return {
                "success":    True,
                "message_id": receipt["message_id"],
                "sent_at":    receipt["sent_at"],
                "message":    f"✅ Welcome email sent to {developer_name} ({developer_email})",
                "error":      None,
            }
        except Exception as exc:
            last_error = str(exc)
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY_SECONDS)

    return {
        "success":    False,
        "message_id": None,
        "sent_at":    None,
        "message":    f"❌ Failed to send welcome email to {developer_email}.",
        "error":      last_error,
    }

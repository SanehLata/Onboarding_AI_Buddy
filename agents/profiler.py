# agents/profiler.py
# @Author: Saneh Lata
# Profiler agent node — the entry point of the onboarding graph.
# Collects developer information through a structured conversation,
# then triggers access provisioning (tickets, DL emails, AD groups)
# and hands off to the orchestrator.

import json
from typing import TypedDict, Annotated
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

from config import (
    GROQ_API_KEY, LLM_MODEL, LLM_TEMPERATURE, LLM_MAX_TOKENS, TEAMS_JSON, log
)
from memory.profile_store import (
    save_profile, get_profile, get_profile_by_email,
    list_all_profiles, log_agent_action, save_access_request,
    save_dl_subscription,
)
from tools.ticketing import provision_all_access
from tools.email import send_all_dl_emails, send_welcome_email
from tools.access import provision_all_ad_groups


# ── LLM ──────────────────────────────────────────────────────────────────────

def _get_llm() -> ChatGroq:
    log.debug("Initializing LLM | model=%s | temp=%s", LLM_MODEL, LLM_TEMPERATURE)
    return ChatGroq(
        api_key=GROQ_API_KEY,
        model=LLM_MODEL,
        temperature=LLM_TEMPERATURE,
        max_tokens=LLM_MAX_TOKENS,
    )


# ── Team data helpers ─────────────────────────────────────────────────────────

def _load_teams() -> list[dict]:
    log.debug("Loading teams from JSON")
    return json.loads(TEAMS_JSON.read_text(encoding="utf-8"))["teams"]


def _get_team_by_name(name: str) -> dict | None:
    log.debug("Looking up team by name: %s", name)
    teams = _load_teams()
    name_lower = name.lower().strip()
    for t in teams:
        if name_lower in t["team_name"].lower() or name_lower in t["team_id"].lower():
            log.info("Found team: %s", t["team_name"])
            return t
    log.warning("Team not found: %s", name)
    return None


def _team_names_list() -> str:
    log.debug("Building team names list")
    return ", ".join(t["team_name"] for t in _load_teams())


# ── Profile extraction ────────────────────────────────────────────────────────

_EXTRACT_PROMPT = """
You are extracting structured onboarding information from a conversation.
Return ONLY valid JSON with these exact keys — nothing else, no markdown:

{{
  "name":             "<full name or null>",
  "email":            "<corporate email or null>",
  "team_name":        "<team name or null>",
  "role_title":       "<job title or null>",
  "experience_level": "<junior|mid|senior|lead or null>",
  "skills":           ["<skill1>", "<skill2>"],
  "manager_name":     "<manager name or null>",
  "start_date":       "<YYYY-MM-DD or null>",
  "profile_complete": <true only if name+email+team_name+role_title+experience_level are ALL present and non-null, else false>
}}

Available teams: {teams}

Conversation so far:
{conversation}
"""


def extract_profile_from_conversation(messages: list) -> dict:
    """Use the LLM to extract structured profile fields from conversation history."""
    log.info("Extracting profile from %d messages", len(messages))
    llm = _get_llm()
    conversation_text = "\n".join(
        f"{'User' if isinstance(m, HumanMessage) else 'Assistant'}: {m.content}"
        for m in messages
        if isinstance(m, (HumanMessage, AIMessage))
    )

    prompt = _EXTRACT_PROMPT.format(
        teams=_team_names_list(),
        conversation=conversation_text or "(no conversation yet)",
    )

    response = llm.invoke([SystemMessage(content=prompt)])
    raw = response.content.strip()
    log.debug("Raw profile extraction response: %s", raw)

    # Strip markdown code fences if LLM wraps in ```json
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    try:
        log.info("Profile Extraction Successful: %s", raw)
        return json.loads(raw)
    except json.JSONDecodeError:
        log.error("Profile extraction failed: %s", raw)
        return {"profile_complete": False}


# ── Conversation logic ────────────────────────────────────────────────────────

_PROFILER_SYSTEM = """
You are the Onboarding Buddy for TechCorp Engineering — a warm, friendly, and efficient AI assistant
helping new developers get settled in.

Your job RIGHT NOW is to collect the following information from the new developer:
1. Full name
2. Corporate email address
3. Team they are joining (available teams: {teams})
4. Job title / role
5. Years of experience (to infer junior/mid/senior/lead)
6. Key technical skills
7. Manager's name
8. Start date

Rules:
- Ask for missing information naturally — one or two items at a time, never a long list of questions
- Be warm and welcoming, not robotic
- If the user provides multiple pieces of info in one message, acknowledge all of them
- Once you have name, email, team, role title, AND experience level confirmed, say exactly: "PROFILE_READY" on its own line
  (this is a signal to the system — do not omit it once you have all five essentials)
- Do not fire PROFILE_READY until role_title and experience_level are both collected — they are required
- Do not proceed to answer technical questions until the profile is complete — gently redirect

Current profile status:
{profile_status}
"""


def get_profiler_response(
    user_message: str,
    conversation_history: list,
    current_profile: dict,
) -> tuple[str, bool]:
    """
    Generate the profiler agent's next response.

    Returns:
        (response_text, profile_complete_signal)
    """
    log.info("Generating profiler response | user_input=%s", user_message)
    llm = _get_llm()

    profile_status = (
        f"Collected so far: name={current_profile.get('name')}, "
        f"email={current_profile.get('email')}, "
        f"team={current_profile.get('team_name')}, "
        f"role={current_profile.get('role_title')}, "
        f"level={current_profile.get('experience_level')}, "
        f"skills={current_profile.get('skills', [])}, "
        f"manager={current_profile.get('manager_name')}"
    )

    system = SystemMessage(
        content=_PROFILER_SYSTEM.format(
            teams=_team_names_list(),
            profile_status=profile_status,
        )
    )

    messages = [system] + conversation_history + [HumanMessage(content=user_message)]
    response = llm.invoke(messages)
    text = response.content.strip()

    log.debug("LLM profiler response: %s", text)

    profile_complete = "PROFILE_READY" in text
    # Clean the signal from the visible output
    clean_text = text.replace("PROFILE_READY", "").strip()

    log.info("Profile complete signal detected: %s", profile_complete)
    return clean_text, profile_complete


# ── Returning user detection ─────────────────────────────────────────────────

_RETURNING_USER_SYSTEM = """
You are the Onboarding Buddy for TechCorp Engineering.

A developer has returned for a new session. Their profile is already on record:
  Name             : {name}
  Team             : {team_name}
  Role             : {role_title}
  Experience level : {experience_level}
  Manager          : {manager_name}
  Start date       : {start_date}

Write a warm 2-3 sentence welcome back message. Include ALL of these points:
1. Greet them by first name
2. Confirm their profile is already saved — no need to re-enter anything
3. Tell them their Access, Learning Path and Insights tabs are ready to view
4. Invite them to ask any questions

Example tone: "Welcome back, Alex! Your profile is still on record for the Payments team.
Your access tickets, learning path and insights are all in the tabs above — feel free to check them,
and ask me anything whenever you're ready."
"""


def check_returning_user(user_message: str) -> dict | None:
    """
    Check if the user's first message identifies them as a returning user.
    Searches existing profiles by name match.

    Returns the full profile dict if found, None if not found.
    """
    log.info("Checking if user is a returning user | user_input=%s", user_message)
    profiles = list_all_profiles()
    if not profiles:
        log.warning("No profiles found in DB")
        return None

    # Simple name matching — check if any known name appears in the message
    msg_lower = user_message.lower()
    for profile in profiles:
        name       = profile.get("name", "")
        first_name = name.split()[0].lower() if name else ""
        full_lower = name.lower()

        # Match on full name or first name appearing in the message
        if full_lower and full_lower in msg_lower:
            log.info("Found returning user profile: %s", profile)
            return profile
        if first_name and len(first_name) > 2 and first_name in msg_lower:
            log.info("Found returning user profile: %s", profile)
            return profile

    return None


def build_returning_user_greeting(profile: dict) -> str:
    """Build a warm returning-user greeting using the stored profile."""
    llm = _get_llm()
    system = _RETURNING_USER_SYSTEM.format(
        name             = profile.get("name", ""),
        team_name        = profile.get("team_name", ""),
        role_title       = profile.get("role_title", ""),
        experience_level = profile.get("experience_level", ""),
        manager_name     = profile.get("manager_name", ""),
        start_date       = profile.get("start_date", ""),
    )
    response = llm.invoke([SystemMessage(content=system)])
    log.info("Returning user greeting: %s", response.content.strip())
    return response.content.strip()


# ── Provisioning ──────────────────────────────────────────────────────────────

def run_provisioning(state: dict) -> dict:
    """
    Execute all three provisioning actions for a completed profile:
      1. Raise system access tickets (Jira, GitHub, Confluence, etc.)
      2. Send DL subscription emails to list owners
      3. Request AD group memberships
      4. Send welcome email to developer

    Updates state with provisioning results and persists to DB.
    Returns updated state.
    """
    profile    = state["profile"]
    log.info("Starting provisioning | name=%s | email=%s", profile["name"], profile["email"])
    dev_id     = profile["id"]
    session_id = state.get("session_id")   # int or None — assigned after profile saved

    provisioning_results = {}

    # ── 1. Access tickets ──────────────────────────────────────────────────
    ticket_result = provision_all_access(
        team_id=profile["team_id"],
        developer_name=profile["name"],
        developer_email=profile["email"],
        team_name=profile["team_name"],
        manager_name=profile["manager_name"],
    )

    log.info("Ticket provisioning success=%s", ticket_result["success"])
    log.debug("Ticket result: %s", ticket_result)

    provisioning_results["tickets"] = ticket_result

    # Persist each ticket to DB — both successful and failed
    for r in ticket_result.get("results", []):
        if r["success"]:
            save_access_request(dev_id, {
                "system_id":         r["system_id"],
                "system_name":       r["system_name"],
                "ticket_type":       r["ticket_type"],
                "ticket_id":         r["ticket_id"],
                "ticket_summary":    r["summary"],
                "status":            r["status"],
                "access_level":      r["access_level"],
                "requires_approval": r["requires_approval"],
                "sla_hours":         r["sla_hours"],
            })
        else:
            # Save failed tickets so Access tab can display them with correct count
            save_access_request(dev_id, {
                "system_id":         r.get("system_id", "unknown"),
                "system_name":       r["system_name"],
                "ticket_type":       r.get("ticket_type", "ACCESS_REQUEST"),
                "ticket_id":         None,
                "ticket_summary":    f"Auto-provisioning failed — {r.get('error', 'unknown error')}",
                "status":            "failed",
                "access_level":      r.get("access_level", "read"),
                "requires_approval": r.get("requires_approval", False),
                "sla_hours":         r.get("sla_hours", 24),
            })

    log_agent_action(dev_id, "TICKET_RAISED", ticket_result, session_id=session_id,
                     status="success" if ticket_result["success"] else "failed")

    # ── 2. DL emails ───────────────────────────────────────────────────────
    email_result = send_all_dl_emails(
        team_id=profile["team_id"],
        developer_name=profile["name"],
        developer_email=profile["email"],
        start_date=profile.get("start_date", ""),
    )

    log.info("DL email provisioning success=%s", email_result["success"])
    log.debug("DL email result: %s", email_result)

    provisioning_results["dl_emails"] = email_result

    # Persist each DL subscription
    for r in email_result.get("results", []):
        if r["success"]:
            save_dl_subscription(dev_id, {
                "dl_id":       r["dl_id"],
                "dl_name":     r["dl_name"],
                "dl_email":    r["dl_email"],
                "owner_name":  r["owner_name"],
                "owner_email": r["owner_email"],
                "status":      "email_sent",
            })

    log_agent_action(dev_id, "EMAIL_SENT", email_result, session_id=session_id,
                     status="success" if email_result["success"] else "failed")

    # ── 3. AD groups ───────────────────────────────────────────────────────
    ad_result = provision_all_ad_groups(
        team_id=profile["team_id"],
        developer_name=profile["name"],
        developer_email=profile["email"],
        team_name=profile["team_name"],
        manager_email=profile["manager_email"],
    )

    log.info("AD group provisioning success=%s", ad_result["success"])
    log.debug("AD group result: %s", ad_result)

    provisioning_results["ad_groups"] = ad_result

    log_agent_action(dev_id, "AD_GROUPS_REQUESTED", ad_result, session_id=session_id,
                     status="success" if ad_result["success"] else "failed")

    # ── 4. Welcome email ───────────────────────────────────────────────────
    welcome_result = send_welcome_email(
        developer_name=profile["name"],
        developer_email=profile["email"],
        team_name=profile["team_name"],
        manager_name=profile["manager_name"],
        start_date=profile.get("start_date", ""),
    )

    log.info("Welcome email sent=%s", welcome_result["success"])

    provisioning_results["welcome_email"] = welcome_result

    log_agent_action(dev_id, "WELCOME_EMAIL_SENT", welcome_result, session_id=session_id,
                     status="success" if welcome_result["success"] else "failed")

    # ── Update state ───────────────────────────────────────────────────────
    state["provisioning_results"] = provisioning_results
    state["provisioning_complete"] = True

    return state


# ── Provisioning summary message ─────────────────────────────────────────────

def build_provisioning_summary(results: dict, developer_name: str) -> str:
    """
    Build a human-readable provisioning summary to show the developer.
    """
    first_name = developer_name.split()[0]
    tickets    = results.get("tickets", {})
    emails     = results.get("dl_emails", {})
    ad         = results.get("ad_groups", {})
    welcome    = results.get("welcome_email", {})

    lines = [
        f"Great news, {first_name}! I've kicked off your onboarding. Here's what was done:\n",
        f"**🎟️  Access Tickets**",
        f"   {tickets.get('message', 'No ticket info available')}",
        "",
        f"**📧  Distribution Lists**",
        f"   {emails.get('message', 'No email info available')}",
        "",
        f"**🔐  AD Groups**",
        f"   {ad.get('message', 'No AD info available')}",
        "",
        f"**✉️   Welcome Email**",
        f"   {welcome.get('message', 'No welcome email info')}",
        "",
        "I've also generated a personalised learning path for you based on your team and skills.",
        "Ask me anything about your team, systems, architecture, or processes — I'm here to help! 🚀",
    ]

    summary = "\n".join(lines)
    log.info("Provisioning summary: %s", summary)
    return summary
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
    log.debug("Loading team configuration from JSON")
    return json.loads(TEAMS_JSON.read_text(encoding="utf-8"))["teams"]


def _get_team_by_name(name: str) -> dict | None:
    log.debug("Searching for team: %s", name)

    teams = _load_teams()
    name_lower = name.lower().strip()

    for t in teams:
        if name_lower in t["team_name"].lower() or name_lower in t["team_id"].lower():
            log.info("Matched team: %s", t["team_name"])
            return t

    log.warning("No matching team found for: %s", name)
    return None


def _team_names_list() -> str:
    teams = _load_teams()
    return ", ".join(t["team_name"] for t in teams)


# ── Profile extraction ────────────────────────────────────────────────────────

def extract_profile_from_conversation(messages: list) -> dict:
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

    log.debug("Raw LLM response (profile extraction): %s", raw)

    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    try:
        parsed = json.loads(raw)
        log.info("Profile extraction successful | complete=%s", parsed.get("profile_complete"))
        return parsed
    except json.JSONDecodeError:
        log.error("Failed to parse profile JSON from LLM response")
        return {"profile_complete": False}


# ── Conversation logic ────────────────────────────────────────────────────────

def get_profiler_response(user_message, conversation_history, current_profile):
    log.info("Generating profiler response | user_input=%s", user_message)

    llm = _get_llm()

    profile_status = (
        f"name={current_profile.get('name')}, "
        f"email={current_profile.get('email')}, "
        f"team={current_profile.get('team_name')}"
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
    clean_text = text.replace("PROFILE_READY", "").strip()

    log.info("Profile complete signal detected: %s", profile_complete)

    return clean_text, profile_complete


# ── Returning user detection ─────────────────────────────────────────────────

def check_returning_user(user_message: str) -> dict | None:
    log.info("Checking for returning user")

    profiles = list_all_profiles()
    if not profiles:
        log.debug("No profiles found in system")
        return None

    msg_lower = user_message.lower()

    for profile in profiles:
        name = profile.get("name", "")
        first_name = name.split()[0].lower() if name else ""
        full_lower = name.lower()

        if full_lower and full_lower in msg_lower:
            log.info("Returning user matched (full name): %s", name)
            return profile

        if first_name and len(first_name) > 2 and first_name in msg_lower:
            log.info("Returning user matched (first name): %s", name)
            return profile

    log.info("No returning user match found")
    return None


# ── Provisioning ──────────────────────────────────────────────────────────────

def run_provisioning(state: dict) -> dict:
    profile = state["profile"]

    log.info("Starting provisioning | name=%s | email=%s",
             profile["name"], profile["email"])

    dev_id = profile["id"]
    session_id = state.get("session_id")

    provisioning_results = {}

    try:
        # ── 1. Tickets ───────────────────────────────
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

        for r in ticket_result.get("results", []):
            if r["success"]:
                save_access_request(dev_id, r)

        # ── 2. DL Emails ─────────────────────────────
        email_result = send_all_dl_emails(
            team_id=profile["team_id"],
            developer_name=profile["name"],
            developer_email=profile["email"],
            start_date=profile.get("start_date", ""),
        )

        log.info("DL email provisioning success=%s", email_result["success"])
        log.debug("DL email result: %s", email_result)

        provisioning_results["dl_emails"] = email_result

        for r in email_result.get("results", []):
            if r.get("success"):
                save_dl_subscription(dev_id, {
                    "dl_id": r.get("dl_id"),
                    "dl_name": r.get("dl_name"),
                    "dl_email": r.get("dl_email"),
                    "owner_name": r.get("owner_name"),
                    "owner_email": r.get("owner_email"),
                    "status": "email_sent",
                })

        # ── 3. AD Groups ─────────────────────────────
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

        # ── 4. Welcome Email ─────────────────────────
        welcome_result = send_welcome_email(
            developer_name=profile["name"],
            developer_email=profile["email"],
            team_name=profile["team_name"],
            manager_name=profile["manager_name"],
            start_date=profile.get("start_date", ""),
        )

        log.info("Welcome email sent=%s", welcome_result["success"])

        provisioning_results["welcome_email"] = welcome_result

    except Exception:
        log.exception("Provisioning failed for user: %s", profile["email"])
        raise

    log.info("Provisioning completed for %s", profile["name"])

    state["provisioning_results"] = provisioning_results
    state["provisioning_complete"] = True

    return state
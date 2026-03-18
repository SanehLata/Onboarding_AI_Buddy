# graph.py
# @Author: Saneh Lata
# LangGraph entry point — defines the state schema and wires all
# agent nodes into the onboarding workflow graph.
#
# Graph flow:
#
#   User message
#       │
#       ▼
#   orchestrator (decide_route)
#       │
#       ├─── PROFILE         ──▶  profiler node        ──▶ response
#       ├─── PROVISION        ──▶  provisioning node    ──▶ response
#       ├─── GENERATE_PATH    ──▶  path generator node  ──▶ response
#       ├─── ANSWER_QUESTION  ──▶  learning/RAG node    ──▶ response
#       ├─── SHOW_PROGRESS    ──▶  progress node        ──▶ response
#       ├─── PROACTIVE_NUDGE  ──▶  nudge node           ──▶ response
#       └─── ESCALATE         ──▶  escalation node      ──▶ response

from __future__ import annotations

from typing import TypedDict, Annotated, Sequence
from datetime import date

from langgraph.graph import StateGraph, END
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
import operator

from agents.orchestrator import (
    Route, decide_route,
    build_proactive_nudge_response,
    build_progress_response,
    build_escalation_response,
    build_small_talk_response,
    classify_intent,
)
from agents.profiler import (
    get_profiler_response,
    extract_profile_from_conversation,
    run_provisioning,
    build_provisioning_summary,
)
from agents.learning import (
    generate_learning_path,
    answer_question,
    format_learning_path_message,
)
from memory.profile_store import save_profile, get_profile, log_agent_action
from memory.progress import start_session, end_session, get_progress_summary


# ── State schema ──────────────────────────────────────────────────────────────

class OnboardingState(TypedDict):
    # Conversation
    messages:             Annotated[Sequence[BaseMessage], operator.add]
    user_message:         str
    response:             str
    session_id:           Optional[int]

    # Profile
    profile:              dict          # developer profile dict
    profile_complete:     bool          # name + email + team collected
    developer_id:         Optional[int] # persisted DB integer id

    # Workflow flags
    provisioning_complete: bool
    provisioning_results:  dict
    path_generated:        bool

    # Routing
    current_route:        str
    error_count:          int


# ── Node implementations ──────────────────────────────────────────────────────

def orchestrator_node(state: OnboardingState) -> OnboardingState:
    """
    Decide which node to call next based on current state and user message.
    Sets state['current_route'] — the conditional edge reads this.
    """
    route = decide_route(state, state["user_message"])
    return {**state, "current_route": route.value}


def profile_node(state: OnboardingState) -> OnboardingState:
    """
    Continue the profiling conversation.
    Extracts profile fields from the conversation history after each turn.
    """
    conversation_history = list(state["messages"])
    current_profile      = state.get("profile", {})

    # Generate response
    response, profile_complete_signal = get_profiler_response(
        user_message=state["user_message"],
        conversation_history=conversation_history,
        current_profile=current_profile,
    )

    # Extract structured profile from conversation
    all_messages = conversation_history + [HumanMessage(content=state["user_message"])]
    extracted    = extract_profile_from_conversation(all_messages)

    # Merge extracted fields into current profile
    updated_profile = {**current_profile, **{
        k: v for k, v in extracted.items()
        if v is not None and k != "profile_complete"
    }}

    # If profile is now complete, look up manager details from teams data
    profile_complete = profile_complete_signal or extracted.get("profile_complete", False)

    session_id = None  # will be set inside the if block if profile just completed

    if profile_complete and not updated_profile.get("id"):
        # Resolve team_id from team_name
        if updated_profile.get("team_name") and not updated_profile.get("team_id"):
            from agents.profiler import _get_team_by_name
            team = _get_team_by_name(updated_profile["team_name"])
            if team:
                updated_profile["team_id"]       = team["team_id"]
                updated_profile["team_name"]      = team["team_name"]
                updated_profile["manager_name"]   = updated_profile.get("manager_name") or team["manager"]
                updated_profile["manager_email"]  = updated_profile.get("manager_email") or team["manager_email"]

        updated_profile.setdefault("start_date", date.today().isoformat())
        updated_profile.setdefault("role_title", "Software Engineer")
        updated_profile.setdefault("experience_level", "mid")
        updated_profile.setdefault("skills", [])
        updated_profile.setdefault("manager_email", "")

        # Persist to DB
        dev_id     = save_profile(updated_profile)        # returns int PK
        updated_profile["id"] = dev_id

        # Start a DB session now that we have a real developer_id
        session_id = start_session(dev_id)                  # returns int PK

        log_agent_action(
            dev_id, "PROFILE_COMPLETE",
            {"team": updated_profile.get("team_name"), "level": updated_profile.get("experience_level")},
            session_id=session_id,
        )

    new_messages = [
        HumanMessage(content=state["user_message"]),
        AIMessage(content=response),
    ]

    # Use newly created session_id if profile just completed, else keep existing
    resolved_session_id = (
        session_id
        if profile_complete and not state.get("session_id")
        else state.get("session_id")
    )

    return {
        **state,
        "messages":          new_messages,
        "response":          response,
        "profile":           updated_profile,
        "profile_complete":  profile_complete,
        "developer_id":      updated_profile.get("id"),  # int after save_profile()
        "session_id":        resolved_session_id,
    }


def provision_node(state: OnboardingState) -> OnboardingState:
    """
    Run all provisioning actions (tickets, emails, AD groups) for a complete profile.
    """
    updated_state = run_provisioning(state)
    summary       = build_provisioning_summary(
        updated_state["provisioning_results"],
        state["profile"].get("name", ""),
    )

    new_messages = [
        HumanMessage(content=state["user_message"]),
        AIMessage(content=summary),
    ]

    return {
        **updated_state,
        "messages":             new_messages,
        "response":             summary,
        "provisioning_complete":True,
    }


def generate_path_node(state: OnboardingState) -> OnboardingState:
    """
    Generate and store the personalised learning path, then present it.
    """
    profile     = state["profile"]
    session_id  = state.get("session_id", "")

    path_docs = generate_learning_path(profile, session_id)
    message   = format_learning_path_message(path_docs, profile.get("name", ""))

    new_messages = [
        HumanMessage(content=state["user_message"]),
        AIMessage(content=message),
    ]

    return {
        **state,
        "messages":      new_messages,
        "response":      message,
        "path_generated":True,
    }


def answer_question_node(state: OnboardingState) -> OnboardingState:
    """
    Answer a developer question using RAG over the knowledge base.
    """
    profile    = state["profile"]
    session_id = state.get("session_id")   # int or None

    result = answer_question(
        query=state["user_message"],
        profile=profile,
        session_id=session_id,
    )

    # If the LLM couldn't find an answer, increment error tracking
    error_count = state.get("error_count", 0)
    if "don't have that" in result["answer"].lower():
        error_count = 0   # not a system error, reset

    new_messages = [
        HumanMessage(content=state["user_message"]),
        AIMessage(content=result["answer"]),
    ]

    return {
        **state,
        "messages":    new_messages,
        "response":    result["answer"],
        "error_count": error_count,
    }


def progress_node(state: OnboardingState) -> OnboardingState:
    """Return a detailed progress summary for the developer."""
    profile    = state["profile"]
    response   = build_progress_response(
        developer_id=profile["id"],
        developer_name=profile.get("name", ""),
    )

    new_messages = [
        HumanMessage(content=state["user_message"]),
        AIMessage(content=response),
    ]

    return {**state, "messages": new_messages, "response": response}


def nudge_node(state: OnboardingState) -> OnboardingState:
    """Proactively suggest the next unread document."""
    profile  = state["profile"]
    response = build_proactive_nudge_response(
        developer_id=profile["id"],
        developer_name=profile.get("name", ""),
    )

    new_messages = [
        HumanMessage(content=state["user_message"]),
        AIMessage(content=response),
    ]

    return {**state, "messages": new_messages, "response": response}


def escalate_node(state: OnboardingState) -> OnboardingState:
    """Handle escalation when repeated errors occur."""
    profile    = state.get("profile", {})
    dev_id     = profile.get("id", "unknown")
    response   = build_escalation_response()

    if dev_id != "unknown":
        log_agent_action(
            dev_id, "ESCALATION",
            {"error_count": state.get("error_count", 0), "reason": "max retries exceeded"},
            status="failed",
        )

    new_messages = [
        HumanMessage(content=state["user_message"]),
        AIMessage(content=response),
    ]

    return {
        **state,
        "messages":    new_messages,
        "response":    response,
        "error_count": 0,   # reset after escalation
    }


# ── Routing function ──────────────────────────────────────────────────────────

def route_from_orchestrator(state: OnboardingState) -> str:
    """Conditional edge — reads current_route and returns the node name."""
    route_map = {
        Route.PROFILE.value:         "profile",
        Route.PROVISION.value:       "provision",
        Route.GENERATE_PATH.value:   "generate_path",
        Route.ANSWER_QUESTION.value: "answer_question",
        Route.SHOW_PROGRESS.value:   "show_progress",
        Route.PROACTIVE_NUDGE.value: "nudge",
        Route.ESCALATE.value:        "escalate",
    }
    return route_map.get(state.get("current_route", ""), "answer_question")


# ── Graph assembly ────────────────────────────────────────────────────────────

def build_graph() -> StateGraph:
    """
    Assemble and compile the full LangGraph onboarding workflow.
    Returns a compiled graph ready to invoke.
    """
    graph = StateGraph(OnboardingState)

    # ── Add nodes ──────────────────────────────────────────────────────────
    graph.add_node("orchestrator",    orchestrator_node)
    graph.add_node("profile",         profile_node)
    graph.add_node("provision",       provision_node)
    graph.add_node("generate_path",   generate_path_node)
    graph.add_node("answer_question", answer_question_node)
    graph.add_node("show_progress",   progress_node)
    graph.add_node("nudge",           nudge_node)
    graph.add_node("escalate",        escalate_node)

    # ── Entry point ────────────────────────────────────────────────────────
    graph.set_entry_point("orchestrator")

    # ── Conditional routing from orchestrator ──────────────────────────────
    graph.add_conditional_edges(
        "orchestrator",
        route_from_orchestrator,
        {
            "profile":         "profile",
            "provision":       "provision",
            "generate_path":   "generate_path",
            "answer_question": "answer_question",
            "show_progress":   "show_progress",
            "nudge":           "nudge",
            "escalate":        "escalate",
        },
    )

    # ── All nodes terminate after responding ───────────────────────────────
    for node in ["profile", "provision", "generate_path", "answer_question",
                 "show_progress", "nudge", "escalate"]:
        graph.add_edge(node, END)

    return graph.compile()


# ── Public interface ──────────────────────────────────────────────────────────

# Module-level compiled graph — imported by app/main.py
onboarding_graph = build_graph()


def create_initial_state(session_id: Optional[int] = None) -> OnboardingState:
    """
    Return a fresh state dict for a new user session.
    Call this once when a new chat session starts.
    """
    return OnboardingState(
        messages=[],
        user_message="",
        response="",
        session_id=session_id,          # set to int after profile is complete
        profile={},
        profile_complete=False,
        developer_id=None,
        provisioning_complete=False,
        provisioning_results={},
        path_generated=False,
        current_route=Route.PROFILE.value,
        error_count=0,
    )


def process_message(state: OnboardingState, user_message: str) -> tuple[str, OnboardingState]:
    """
    Process one user message through the graph.

    Args:
        state:        Current conversation state
        user_message: The user's latest message

    Returns:
        (response_text, updated_state)
    """
    updated_state = {**state, "user_message": user_message}
    result        = onboarding_graph.invoke(updated_state)
    return result["response"], result
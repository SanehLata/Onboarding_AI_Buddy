# agents/orchestrator.py
# @Author: Saneh Lata
# Orchestrator agent — the decision-making brain of the graph.
# Analyses the current state and decides which action to take next:
#   - Continue profiling (more info needed)
#   - Run provisioning (profile just completed)
#   - Generate learning path (provisioning just finished)
#   - Answer a question via RAG (normal conversational Q&A)
#   - Proactively nudge the developer toward unread docs
#   - Escalate to admin (unrecoverable errors)

from enum import Enum
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage

from config import (
    GROQ_API_KEY, LLM_MODEL, LLM_TEMPERATURE, LLM_MAX_TOKENS,
)
from memory.progress import get_progress_summary, get_covered_topics, get_next_unread_doc
from memory.profile_store import get_profile, log_agent_action


# ── Routing decisions ─────────────────────────────────────────────────────────

class Route(str, Enum):
    PROFILE          = "profile"           # Still collecting developer info
    PROVISION        = "provision"         # Profile complete — run provisioning
    GENERATE_PATH    = "generate_path"     # Provisioning done — build learning path
    ANSWER_QUESTION  = "answer_question"   # Normal Q&A via RAG
    PROACTIVE_NUDGE  = "proactive_nudge"   # Suggest next unread document
    SHOW_PROGRESS    = "show_progress"     # Developer asked about their progress
    ESCALATE         = "escalate"          # Something failed — notify admin


# ── LLM ──────────────────────────────────────────────────────────────────────

def _get_llm() -> ChatGroq:
    return ChatGroq(
        api_key=GROQ_API_KEY,
        model=LLM_MODEL,
        temperature=0,
        max_tokens=256,
    )


# ── Intent classification ─────────────────────────────────────────────────────

_INTENT_PROMPT = """
Classify the developer's message into one of these intents.
Reply with ONLY the intent label — nothing else.

Intents:
  QUESTION        — asking about systems, tools, processes, architecture, access, docs
  PROGRESS_CHECK  — asking about their progress, what they've read, what's next
  SMALL_TALK      — greetings, thanks, casual chat
  COMPLAINT       — frustrated, something isn't working
  OTHER           — anything that doesn't fit above

Message: "{message}"
"""


def classify_intent(message: str) -> str:
    """Classify a user message into a high-level intent category."""
    llm = _get_llm()
    response = llm.invoke([
        SystemMessage(content=_INTENT_PROMPT.format(message=message))
    ])
    return response.content.strip().upper()


# ── Core routing logic ────────────────────────────────────────────────────────

def decide_route(state: dict, user_message: str) -> Route:
    """
    Examine the current state and user message to decide the next action.

    Decision tree:
    1. If profile not complete → keep profiling
    2. If profile complete but provisioning not done → run provisioning
    3. If provisioning done but no learning path → generate learning path
    4. If user asks about progress → show progress
    5. If proactive nudge is due → nudge
    6. Otherwise → answer the question via RAG
    """
    profile              = state.get("profile", {})
    profile_complete     = state.get("profile_complete", False)
    provisioning_complete = state.get("provisioning_complete", False)
    path_generated       = state.get("path_generated", False)
    error_count          = state.get("error_count", 0)

    # ── 1. Escalate if too many errors ────────────────────────────────────────
    if error_count >= 3:
        return Route.ESCALATE

    # ── 2. Profile incomplete ─────────────────────────────────────────────────
    if not profile_complete:
        return Route.PROFILE

    # ── 3. Provisioning not yet run ───────────────────────────────────────────
    if profile_complete and not provisioning_complete:
        return Route.PROVISION

    # ── 4. Learning path not yet generated ────────────────────────────────────
    if provisioning_complete and not path_generated:
        return Route.GENERATE_PATH

    # ── 5. Developer asking about their progress ──────────────────────────────
    lower = user_message.lower()
    progress_keywords = ["progress", "what have i read", "what's next", "how am i doing",
                         "learning path", "next step", "what should i read"]
    if any(kw in lower for kw in progress_keywords):
        return Route.SHOW_PROGRESS

    # ── 6. Proactive nudge logic ──────────────────────────────────────────────
    dev_id = profile.get("id")
    if dev_id:
        summary = get_progress_summary(dev_id)
        if summary["should_nudge"] and summary["not_started"] > 0:
            # Only nudge if the message is short / conversational (not a real question)
            intent = classify_intent(user_message)
            if intent in ("SMALL_TALK", "OTHER"):
                return Route.PROACTIVE_NUDGE

    # ── 7. Default: answer the question ──────────────────────────────────────
    return Route.ANSWER_QUESTION


# ── Response builders ─────────────────────────────────────────────────────────

def build_proactive_nudge_response(developer_id: str, developer_name: str) -> str:
    """Build a proactive suggestion message for the next unread document."""
    next_doc = get_next_unread_doc(developer_id)
    if not next_doc:
        return (
            "You're making great progress! You've covered all the documents in your learning path. "
            "Feel free to ask me anything about the systems or processes at any time."
        )

    covered = get_covered_topics(developer_id)
    count   = len(covered)

    category_context = {
        "onboarding":   "This will help you settle into the team.",
        "architecture": "This will give you a deeper understanding of our systems.",
        "runbooks":     "This is essential operational knowledge for your role.",
    }
    context = category_context.get(next_doc["category"], "")

    return (
        f"Great chatting with you! You've explored {count} topic{'s' if count != 1 else ''} so far. 🎯\n\n"
        f"When you're ready, your next recommended read is:\n\n"
        f"📄 **{next_doc['doc_title']}**\n"
        f"   _{next_doc.get('reason', context)}_\n\n"
        f"Just ask me anything about it whenever you're ready!"
    )


def build_progress_response(developer_id: str, developer_name: str) -> str:
    """Build a detailed progress summary for the developer."""
    summary    = get_progress_summary(developer_id)
    covered    = get_covered_topics(developer_id)
    next_doc   = get_next_unread_doc(developer_id)
    first_name = developer_name.split()[0] if developer_name else "there"

    lines = [
        f"Here's your onboarding progress, {first_name}! 📊\n",
        f"**Learning path completion: {summary['completion_pct']}%**",
        f"   ✅ Completed  : {summary['completed']} documents",
        f"   📖 In progress: {summary['in_progress']} documents",
        f"   ⏳ Not started: {summary['not_started']} documents",
        f"\n**Questions answered this onboarding: {summary['total_questions']}**",
    ]

    if covered:
        lines.append(f"\n**Topics you've explored:**")
        for topic in covered[-8:]:   # show last 8
            lines.append(f"   • {topic}")

    if next_doc:
        lines.append(
            f"\n**Next up:** 📄 {next_doc['doc_title']}\n"
            f"   _{next_doc.get('reason', 'Part of your learning path')}_"
        )
    else:
        lines.append("\n🎉 You've completed your learning path!")

    return "\n".join(lines)


def build_escalation_response() -> str:
    """Build an escalation message when the system encounters repeated failures."""
    return (
        "I've encountered some technical issues and wasn't able to complete all your onboarding steps automatically. "
        "I've notified the IT admin team — they will follow up with you shortly.\n\n"
        "In the meantime, you can still ask me questions about the team, systems, and processes. "
        "Your manager has also been notified and will be in touch."
    )


def build_small_talk_response(message: str, developer_name: str) -> str:
    """Generate a brief friendly response to small talk."""
    llm = _get_llm()
    first_name = developer_name.split()[0] if developer_name else "there"

    system = SystemMessage(content=(
        f"You are Onboarding Buddy, a friendly AI assistant for new TechCorp developers. "
        f"You are chatting with {first_name}. "
        f"Respond warmly and briefly to this casual message. "
        f"Keep it to 1-2 sentences. End with an invitation to ask technical questions."
    ))

    response = llm.invoke([system, HumanMessage(content=message)])
    return response.content.strip()
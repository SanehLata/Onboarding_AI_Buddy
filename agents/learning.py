# agents/learning.py
# @Author: Saneh Lata
# Learning Path Generator agent node.
# Performs skill gap analysis, retrieves relevant docs via RAG,
# generates a personalised sequenced reading plan, and handles
# Q&A queries grounded in the knowledge base.

import json
from pathlib import Path
from langchain_groq import ChatGroq
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.messages import SystemMessage, HumanMessage

from config import (
    GROQ_API_KEY, LLM_MODEL, LLM_TEMPERATURE, LLM_MAX_TOKENS,
    EMBEDDING_MODEL, COLLECTION_NAME, VECTORSTORE_DIR,
    RETRIEVER_TOP_K, TEAMS_JSON,
)
from memory.progress import (
    save_learning_path, get_learning_path, get_covered_topics,
    get_covered_docs, get_recent_history, get_next_unread_doc,
    record_progress, get_progress_summary, mark_doc_started,
)
from memory.profile_store import log_agent_action
from config import log


# ── Lazy singletons ───────────────────────────────────────────────────────────

_llm          = None
_vector_store = None


def _get_llm() -> ChatGroq:
    global _llm
    if _llm is None:
        log.info("[LLM] initialising ChatGroq — model=%s temperature=%s", LLM_MODEL, LLM_TEMPERATURE)
        if not GROQ_API_KEY:
            log.warning("[LLM] GROQ_API_KEY is not set — LLM calls will fail")
        _llm = ChatGroq(
            model=LLM_MODEL,
            temperature=LLM_TEMPERATURE,
            max_tokens=LLM_MAX_TOKENS,
        )
    return _llm


def _get_vector_store() -> Chroma:
    global _vector_store
    if _vector_store is None:
        log.info(
            "[VECTOR_STORE] initialising — model=%s collection=%s dir=%s",
            EMBEDDING_MODEL, COLLECTION_NAME, VECTORSTORE_DIR
        )
        embeddings = HuggingFaceEmbeddings(
            model_name=EMBEDDING_MODEL,
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True},
        )
        _vector_store = Chroma(
            collection_name=COLLECTION_NAME,
            embedding_function=embeddings,
            persist_directory=str(VECTORSTORE_DIR),
        )
        log.info("[VECTOR_STORE] initialised successfully")
    return _vector_store


# ── Team data helpers ─────────────────────────────────────────────────────────

def _get_team(team_id: str) -> dict | None:
    data = json.loads(TEAMS_JSON.read_text(encoding="utf-8"))
    for t in data["teams"]:
        if t["team_id"] == team_id:
            return t
    return None


def _skill_gap(developer_skills: list[str], required_skills: list[str]) -> list[str]:
    """Return skills in required_skills that the developer does not have."""
    dev_lower = {s.lower() for s in developer_skills}
    return [s for s in required_skills if s.lower() not in dev_lower]


# ── Learning path generation ──────────────────────────────────────────────────

_PATH_GENERATION_PROMPT = """
You are an expert onboarding advisor at TechCorp Engineering.
A new developer has just joined and you must create a personalised reading plan.

Developer profile:
  Name             : {name}
  Team             : {team_name}
  Role             : {role_title}
  Experience level : {experience_level}
  Skills they have : {skills}
  Skills they need : {required_skills}
  Skill gaps       : {skill_gaps}

Available documents (path | title | category):
{available_docs}

Your task:
1. Select the most relevant documents for this developer (8 to 12 docs)
2. Order them logically — foundational docs first, advanced last
3. Briefly explain WHY each doc is recommended for THIS developer specifically

Return ONLY a JSON array — no markdown, no extra text:
[
  {{
    "doc_path":      "onboarding/day1_checklist.md",
    "doc_title":     "Day 1 Checklist",
    "category":      "onboarding",
    "priority_order": 1,
    "reason":        "Essential first read — covers account setup and access tracking"
  }},
  ...
]
"""

# All available docs — mirrors the mock_docs folder structure
AVAILABLE_DOCS = [
    ("onboarding/day1_checklist.md",        "Day 1 Checklist",               "onboarding"),
    ("onboarding/team_norms.md",             "Team Norms & Working Agreements","onboarding"),
    ("onboarding/communication_channels.md", "Communication Channels",        "onboarding"),
    ("onboarding/tools_setup.md",            "Developer Tools Setup Guide",   "onboarding"),
    ("onboarding/vpn_access.md",             "VPN & Remote Access Guide",     "onboarding"),
    ("onboarding/access_provisioning.md",    "Access Provisioning Guide",     "onboarding"),
    ("onboarding/code_review_guide.md",      "Code Review Guide",             "onboarding"),
    ("onboarding/on_call_guide.md",          "On-Call Guide",                 "onboarding"),
    ("onboarding/30_60_90_day_plan.md",      "30-60-90 Day Plan",             "onboarding"),
    ("architecture/system_overview.md",      "System Overview",               "architecture"),
    ("architecture/auth_service.md",         "Auth Service",                  "architecture"),
    ("architecture/payments_api.md",         "Payments API",                  "architecture"),
    ("architecture/data_pipeline.md",        "Data Pipeline",                 "architecture"),
    ("architecture/microservices_map.md",    "Microservices Dependency Map",  "architecture"),
    ("architecture/api_design_standards.md", "API Design Standards",          "architecture"),
    ("runbooks/deployment_guide.md",         "Deployment Guide",              "runbooks"),
    ("runbooks/incident_response.md",        "Incident Response Runbook",     "runbooks"),
    ("runbooks/database_failover.md",        "Database Failover Runbook",     "runbooks"),
    ("runbooks/logging_standards.md",        "Logging Standards",             "runbooks"),
    ("runbooks/kafka_consumer_runbook.md",   "Kafka Consumer Runbook",        "runbooks"),
    ("runbooks/secrets_config_management.md","Secrets & Config Management",   "runbooks"),
]


def generate_learning_path(profile: dict, session_id: str = None) -> list[dict]:
    """
    Generate a personalised learning path for a developer using the LLM.
    Stores the path in SQLite and returns it.
    """
    log.info(
        "[GENERATE_PATH] entry — dev_id=%s name='%s' team='%s' level='%s'",
        profile.get("id"), profile.get("name"),
        profile.get("team_name"), profile.get("experience_level")
    )
    llm   = _get_llm()
    team  = _get_team(profile.get("team_id", ""))

    required_skills = team["required_skills"] if team else []
    skill_gaps      = _skill_gap(profile.get("skills", []), required_skills)
    log.info(
        "[GENERATE_PATH] skill analysis — required=%d gaps=%d gap_list=%s",
        len(required_skills), len(skill_gaps), skill_gaps
    )

    available_docs_text = "\n".join(
        f"  {path} | {title} | {cat}"
        for path, title, cat in AVAILABLE_DOCS
    )

    prompt = _PATH_GENERATION_PROMPT.format(
        name=profile.get("name", ""),
        team_name=profile.get("team_name", ""),
        role_title=profile.get("role_title", "Engineer"),
        experience_level=profile.get("experience_level", "mid"),
        skills=", ".join(profile.get("skills", [])) or "Not specified",
        required_skills=", ".join(required_skills) or "Not specified",
        skill_gaps=", ".join(skill_gaps) or "None — developer already has all required skills",
        available_docs=available_docs_text,
    )

    log.info("[GENERATE_PATH] calling LLM for path generation — model=%s", LLM_MODEL)
    response = _get_llm().invoke([SystemMessage(content=prompt)])
    raw = response.content.strip()

    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    try:
        path_docs = json.loads(raw)
        log.info("[GENERATE_PATH] LLM returned %d documents", len(path_docs))
    except json.JSONDecodeError:
        log.warning(
            "[GENERATE_PATH] LLM response was not valid JSON — using default path. "
            "raw_preview='%s'", raw[:120]
        )
        path_docs = _default_learning_path(profile)

    # Persist to DB
    save_learning_path(profile["id"], path_docs)
    log.info("[GENERATE_PATH] learning path persisted — dev_id=%s doc_count=%d", profile["id"], len(path_docs))

    if session_id:
        log_agent_action(
            profile["id"], "PATH_GENERATED",
            {"doc_count": len(path_docs), "skill_gaps": skill_gaps},
            session_id=session_id,
        )

    return path_docs


def _default_learning_path(profile: dict) -> list[dict]:
    """Fallback learning path if LLM generation fails."""
    base = [
        ("onboarding/day1_checklist.md",        "Day 1 Checklist",             "onboarding"),
        ("onboarding/team_norms.md",             "Team Norms",                  "onboarding"),
        ("onboarding/tools_setup.md",            "Developer Tools Setup",       "onboarding"),
        ("onboarding/vpn_access.md",             "VPN & Remote Access",         "onboarding"),
        ("onboarding/communication_channels.md", "Communication Channels",      "onboarding"),
        ("architecture/system_overview.md",      "System Overview",             "architecture"),
        ("runbooks/deployment_guide.md",         "Deployment Guide",            "runbooks"),
        ("onboarding/on_call_guide.md",          "On-Call Guide",               "onboarding"),
    ]
    return [
        {"doc_path": p, "doc_title": t, "category": c,
         "priority_order": i + 1, "reason": "Core onboarding document"}
        for i, (p, t, c) in enumerate(base)
    ]


# ── RAG-powered Q&A ───────────────────────────────────────────────────────────

_QA_SYSTEM = """
You are the Onboarding Buddy for TechCorp Engineering.
Answer the developer's question using ONLY the context below.

Rules:
- Be concise, clear, and friendly
- If the answer is in the context, give it directly — do not hedge
- If the answer is NOT in the context, say: "I don't have that in my knowledge base.
  Try asking your manager or raising a question in your team's Slack channel."
- Never invent information that is not in the context
- At the end of your answer, on a new line, write:
  SOURCE: <the doc filename the answer came from, e.g. onboarding/vpn_access.md>
  TOPIC: <a 2-5 word topic label for what was just answered>

Developer profile:
  Name  : {name}
  Team  : {team_name}
  Level : {experience_level}

Recent conversation context (for continuity):
{recent_history}

Retrieved knowledge base context:
{context}
"""


def answer_question(
    query: str,
    profile: dict,
    session_id: str,
    last_nudge_count: int = 0,
) -> dict:
    """
    Answer a developer's question using RAG over the knowledge base.
    Records the topic in progress tracking.

    last_nudge_count: total_questions when nudge last fired (from graph state).
    Used to prevent the inline nudge from appending on the same count that
    the routing-level nudge already fired on.

    Returns:
    {
        answer: str,
        source_doc: str | None,
        topic: str | None,
        retrieved_chunks: int,
        proactive_nudge: str | None,
    }
    """
    log.info(
        "[ANSWER_QUESTION] query='%s' dev_id=%s session_id=%s",
        query[:70], profile.get("id"), session_id
    )
    vs = _get_vector_store()

    # Retrieve relevant chunks
    docs = vs.similarity_search(query, k=RETRIEVER_TOP_K)

    if not docs:
        log.warning("[ANSWER_QUESTION] no chunks retrieved from vector store — query='%s'", query[:70])
        return {
            "answer": (
                "I couldn't find anything in the knowledge base for that question. "
                "Try rephrasing, or ask your manager or team channel directly."
            ),
            "source_doc":       None,
            "topic":            None,
            "retrieved_chunks": 0,
            "proactive_nudge":  None,
        }

    # Build context from retrieved chunks
    context = "\n\n---\n\n".join(
        f"[Source: {d.metadata.get('source', 'unknown')}]\n{d.page_content}"
        for d in docs
    )

    # Fetch recent history for conversational continuity
    history     = get_recent_history(profile["id"], session_id, limit=4)
    history_text = "\n".join(
        f"Q: {h['query']}\nA: {h['summary']}"
        for h in history
    ) or "No previous questions in this session."

    system = SystemMessage(
        content=_QA_SYSTEM.format(
            name=profile.get("name", ""),
            team_name=profile.get("team_name", ""),
            experience_level=profile.get("experience_level", "mid"),
            recent_history=history_text,
            context=context,
        )
    )

    log.info(
        "[ANSWER_QUESTION] retrieved %d chunks — top_source='%s' calling LLM",
        len(docs), docs[0].metadata.get("source", "unknown") if docs else "none"
    )
    response = _get_llm().invoke([system, HumanMessage(content=query)])
    answer   = response.content.strip()

    # Extract SOURCE and TOPIC signals from the answer
    source_doc = None
    topic      = None
    clean_lines = []

    for line in answer.splitlines():
        if line.startswith("SOURCE:"):
            source_doc = line.replace("SOURCE:", "").strip()
        elif line.startswith("TOPIC:"):
            topic = line.replace("TOPIC:", "").strip()
        else:
            clean_lines.append(line)

    clean_answer = "\n".join(clean_lines).strip()

    # Fallback source from top retrieved doc
    if not source_doc and docs:
        source_doc = docs[0].metadata.get("source")

    log.info(
        "[ANSWER_QUESTION] answer extracted — topic='%s' source_doc='%s' "
        "answer_len=%d retrieved_chunks=%d",
        topic, source_doc, len(clean_answer), len(docs)
    )
    if not topic:
        log.warning(
            "[ANSWER_QUESTION] no TOPIC signal in LLM response — "
            "progress will NOT be recorded for query='%s'", query[:70]
        )

    # Record progress
    # Guard: skip if topic is missing or the LLM returned the literal "None"
    valid_topic = topic and topic.lower() != "none"
    valid_source = source_doc and source_doc.lower() != "none"

    if valid_topic:
        record_progress(
            developer_id=profile["id"],
            session_id=session_id,
            topic=topic,
            query=query,
            summary=clean_answer[:200],
            source_doc=source_doc if valid_source else None,
        )

        if valid_source:
            mark_doc_started(profile["id"], source_doc)

    # Proactive nudge — suggest next unread doc
    # Guard: same last_nudge_count check as orchestrator.py to prevent
    # appending the inline nudge when it has already fired this session.
    summary = get_progress_summary(profile["id"])
    nudge   = None
    nudge_ready = (
        summary["should_nudge"]
        and summary["total_questions"] != last_nudge_count
    )
    if nudge_ready:
        next_doc = get_next_unread_doc(profile["id"])
        if next_doc:
            log.info(
                "[ANSWER_QUESTION] proactive nudge appended — next_doc='%s'",
                next_doc.get("doc_title")
            )
            nudge = (
                f"\n\n💡 **Next suggested read:** [{next_doc['doc_title']}]"
                f"\n   _{next_doc.get('reason', 'Part of your learning path')}_"
            )

    return {
        "answer":           clean_answer + (nudge or ""),
        "source_doc":       source_doc,
        "topic":            topic,
        "retrieved_chunks": len(docs),
        "proactive_nudge":  nudge,
    }


# ── Learning path display ─────────────────────────────────────────────────────

def format_learning_path_message(path_docs: list[dict], developer_name: str) -> str:
    """Format the learning path as a readable message for the UI."""
    first_name = developer_name.split()[0] if developer_name else "there"

    lines = [
        f"Here's your personalised learning path, {first_name}! 📚\n",
        "I've sequenced these to build your knowledge from the ground up:\n",
    ]

    category_icons = {
        "onboarding":   "🧭",
        "architecture": "🏗️",
        "runbooks":     "📋",
    }

    for doc in path_docs:
        icon = category_icons.get(doc["category"], "📄")
        lines.append(
            f"{doc['priority_order']:>2}. {icon} **{doc['doc_title']}**"
            f"\n    _{doc.get('reason', '')}_\n"
        )

    lines.append(
        "\nAsk me anything about any of these topics whenever you're ready. "
        "I'll track your progress and suggest what to read next. 🚀"
    )

    return "\n".join(lines)
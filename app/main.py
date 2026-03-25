# app/main.py
# @Author: Saneh Lata
# Streamlit UI for AI Onboarding Buddy
# Run: streamlit run app/main.py

import sys
from pathlib import Path

# ── Path setup — allows imports from project root ─────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st

# ── Page config — must be first Streamlit call ────────────────────────────────
st.set_page_config(
    page_title="Onboarding Buddy",
    page_icon="🤝",
    layout="wide",
    initial_sidebar_state="expanded",
)

from graph import create_initial_state, process_message
from config import log
from memory.progress import (
    get_progress_summary,
    get_learning_path,
    get_covered_topics,
    get_next_unread_doc,
    record_doc_read,
)
from memory.profile_store import (
    get_access_requests,
    get_dl_subscriptions,
    get_agent_action_log,
    get_sessions_for_developer,
    auto_complete_dl_subscriptions,
)


# ── Custom CSS ────────────────────────────────────────────────────────────────

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600&family=DM+Mono:wght@400;500&display=swap');

/* ── Base ── */
html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
}

/* ── Hide default Streamlit chrome ── */
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding-top: 1.5rem; padding-bottom: 2rem; }

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: #0d1117;
    border-right: 1px solid #21262d;
}
[data-testid="stSidebar"] * { color: #c9d1d9 !important; }
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 {
    color: #f0f6fc !important;
    font-weight: 600;
}

/* ── Chat messages ── */
.stChatMessage {
    border-radius: 12px;
    margin-bottom: 0.6rem;
    border: 1px solid #21262d;
}

/* ── User message ── */
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) {
    background: #161b22;
}

/* ── Assistant message ── */
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) {
    background: #0d1117;
    border-color: #30363d;
}

/* ── Chat input ── */
[data-testid="stChatInputContainer"] {
    border-top: 1px solid #21262d;
    background: #0d1117;
    padding-top: 0.75rem;
}

/* ── Metric cards ── */
[data-testid="stMetric"] {
    background: #161b22;
    border: 1px solid #21262d;
    border-radius: 10px;
    padding: 0.8rem 1rem;
}
[data-testid="stMetricValue"] {
    font-family: 'DM Mono', monospace;
    color: #58a6ff !important;
    font-size: 1.6rem !important;
}
[data-testid="stMetricLabel"] {
    color: #8b949e !important;
    font-size: 0.75rem !important;
    text-transform: uppercase;
    letter-spacing: 0.06em;
}

/* ── Progress bar ── */
[data-testid="stProgressBar"] > div > div {
    background: linear-gradient(90deg, #238636, #2ea043) !important;
    border-radius: 4px;
}

/* ── Status badges ── */
.badge {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 20px;
    font-size: 0.72rem;
    font-weight: 500;
    letter-spacing: 0.03em;
    font-family: 'DM Mono', monospace;
}
.badge-green  { background: #1a4427; color: #3fb950; border: 1px solid #238636; }
.badge-yellow { background: #2d2000; color: #e3b341; border: 1px solid #9e6a03; }
.badge-red    { background: #3d0708; color: #f85149; border: 1px solid #da3633; }
.badge-blue   { background: #0c2d6b; color: #58a6ff; border: 1px solid #1f6feb; }
.badge-gray   { background: #21262d; color: #8b949e; border: 1px solid #30363d; }

/* ── Section headers ── */
.section-label {
    font-size: 0.68rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: #8b949e;
    margin-bottom: 0.5rem;
    padding-bottom: 0.4rem;
    border-bottom: 1px solid #21262d;
}

/* ── Doc card ── */
.doc-card {
    background: #161b22;
    border: 1px solid #21262d;
    border-radius: 8px;
    padding: 0.65rem 0.9rem;
    margin-bottom: 0.4rem;
    display: flex;
    align-items: flex-start;
    gap: 0.6rem;
}
.doc-card:hover { border-color: #30363d; }
.doc-title { font-size: 0.82rem; color: #e6edf3 !important; font-weight: 600; }
.doc-title * { color: #e6edf3 !important; }
.doc-reason { font-size: 0.72rem; color: #8b949e !important; margin-top: 2px; }

/* ── Welcome banner ── */
.welcome-banner {
    background: linear-gradient(135deg, #0d1117 0%, #161b22 100%);
    border: 1px solid #21262d;
    border-radius: 14px;
    padding: 2rem 2.5rem;
    margin-bottom: 1.5rem;
    position: relative;
    overflow: hidden;
}
.welcome-banner::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 3px;
    background: linear-gradient(90deg, #238636, #1f6feb, #8b5cf6);
}
.welcome-title {
    font-size: 1.6rem;
    font-weight: 600;
    color: #f0f6fc;
    margin: 0 0 0.4rem 0;
}
.welcome-sub {
    font-size: 0.9rem;
    color: #8b949e;
    margin: 0;
}

/* ── Ticket row ── */
.ticket-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0.5rem 0.75rem;
    background: #161b22;
    border: 1px solid #21262d;
    border-radius: 7px;
    margin-bottom: 0.3rem;
    font-size: 0.8rem;
}
.ticket-name { color: #c9d1d9; font-weight: 500; }
.ticket-id   { font-family: 'DM Mono', monospace; color: #58a6ff; font-size: 0.72rem; }

/* ── Tabs ── */
[data-baseweb="tab-list"] {
    background: #0d1117;
    border-bottom: 1px solid #21262d;
    gap: 0;
}
[data-baseweb="tab"] {
    color: #8b949e !important;
    font-size: 0.82rem;
    font-weight: 500;
    padding: 0.5rem 1.1rem;
}
[aria-selected="true"][data-baseweb="tab"] {
    color: #f0f6fc !important;
    border-bottom: 2px solid #58a6ff;
}

/* ── Expander ── */
[data-testid="stExpander"] {
    background: #161b22;
    border: 1px solid #21262d;
    border-radius: 8px;
}

/* ── Expander label text — force readable color ──────────────────── */
/* Streamlit renders expander labels in <summary><p> or <summary><span> */
[data-testid="stExpander"] summary,
[data-testid="stExpander"] summary p,
[data-testid="stExpander"] summary span,
[data-testid="stExpander"] details > summary > * {
    color: #8b949e !important;
}

/* Doc read expander (nested) — the "📖 Read: Title" label */
[data-testid="stExpander"] [data-testid="stExpander"] summary,
[data-testid="stExpander"] [data-testid="stExpander"] summary p,
[data-testid="stExpander"] [data-testid="stExpander"] summary span {
    color: #8b949e !important;
    font-size: 0.78rem !important;
}

/* Category expander header — "🧭 Onboarding (2/7 completed)" */
/* Give the top-level expanders a slightly brighter label */
.stExpander > details > summary p {
    color: #c9d1d9 !important;
    font-weight: 500 !important;
}

/* ── Doc reader expander — nested inside category expander ── */
/* Force readable text colors on all markdown elements inside doc viewer */
.doc-reader h1, .doc-reader h2, .doc-reader h3,
.doc-reader h4, .doc-reader h5, .doc-reader h6 {
    color: #e6edf3 !important;
    margin-top: 1.2rem;
    margin-bottom: 0.4rem;
    font-weight: 600;
}
.doc-reader p, .doc-reader li, .doc-reader td, .doc-reader th {
    color: #c9d1d9 !important;
    line-height: 1.7;
}
.doc-reader a           { color: #58a6ff !important; }
.doc-reader strong      { color: #e6edf3 !important; }
.doc-reader code        { background: #21262d; color: #79c0ff;
                          padding: 1px 5px; border-radius: 4px;
                          font-family: 'DM Mono', monospace; font-size: 0.85em; }
.doc-reader pre         { background: #161b22; border: 1px solid #30363d;
                          border-radius: 6px; padding: 0.8rem 1rem; }
.doc-reader pre code    { background: transparent; padding: 0; }
.doc-reader blockquote  { border-left: 3px solid #30363d;
                          padding-left: 1rem; color: #8b949e !important; }
.doc-reader hr          { border-color: #21262d; margin: 1.2rem 0; }
.doc-reader table       { border-collapse: collapse; width: 100%; }
.doc-reader th          { background: #21262d; border: 1px solid #30363d;
                          padding: 0.4rem 0.7rem; }
.doc-reader td          { border: 1px solid #21262d; padding: 0.4rem 0.7rem; }
.doc-reader ul, .doc-reader ol { padding-left: 1.4rem; }
.doc-reader input[type="checkbox"] { accent-color: #238636; }

/* ── Insights tab — topic tags ──────────────────────────────────────── */
/* Tags are plain spans inside st.markdown — force text color */
.topic-tag {
    color: #8b949e !important;
    background: #161b22 !important;
    border: 1px solid #30363d !important;
}

/* ── Metric cards — force label and value colors ─────────────────── */
/* Streamlit sometimes resets these in light mode contexts */
[data-testid="stMetric"] {
    background: #161b22 !important;
    border: 1px solid #21262d !important;
    border-radius: 10px !important;
    padding: 0.8rem 1rem !important;
}
[data-testid="stMetricValue"] > div,
[data-testid="stMetricValue"] {
    color: #58a6ff !important;
    font-family: 'DM Mono', monospace !important;
    font-size: 1.6rem !important;
}
[data-testid="stMetricLabel"] > div,
[data-testid="stMetricLabel"] {
    color: #8b949e !important;
    font-size: 0.75rem !important;
    text-transform: uppercase !important;
    letter-spacing: 0.06em !important;
}

/* ── Insights session history cards ──────────────────────────────── */
/* ticket-row is already defined but the text inside needs forcing    */
.ticket-row * { color: inherit; }
.ticket-row .session-id   { font-size: 0.8rem; font-weight: 500; color: #c9d1d9 !important; }
.ticket-row .session-date { font-size: 0.72rem; color: #6e7681 !important; margin-top: 1px; }
.ticket-row .session-stat { font-size: 0.78rem; color: #8b949e !important; }

/* ── Tab labels — force readable color on all tabs ───────────────── */
[data-baseweb="tab"] p,
[data-baseweb="tab"] span,
[data-baseweb="tab"] div {
    color: #8b949e !important;
    font-size: 0.82rem !important;
    font-weight: 500 !important;
}
[aria-selected="true"][data-baseweb="tab"] p,
[aria-selected="true"][data-baseweb="tab"] span,
[aria-selected="true"][data-baseweb="tab"] div {
    color: #f0f6fc !important;
}

/* ── Insights header text ────────────────────────────────────────── */
.insights-header-title { color: #f0f6fc !important; }
.insights-header-meta  { color: #6e7681 !important; }

/* ── Mark as read button ── */
.stButton > button[kind="secondary"] {
    background: transparent;
    border: 1px solid #238636;
    color: #3fb950;
    font-size: 0.72rem;
    font-family: 'DM Mono', monospace;
    padding: 2px 10px;
    border-radius: 20px;
    height: auto;
    line-height: 1.6;
    white-space: nowrap;
}
.stButton > button[kind="secondary"]:hover {
    background: rgba(35,134,54,0.15);
    border-color: #3fb950;
}
</style>
""", unsafe_allow_html=True)


# ── Session state initialisation ──────────────────────────────────────────────

def _init_session() -> None:
    if "graph_state" not in st.session_state:
        # Only log on true first load — session_state is empty before this
        log.info("[APP] new browser session initialised")
        st.session_state.graph_state = create_initial_state()
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if "greeted" not in st.session_state:
        st.session_state.greeted = False



_init_session()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _profile() -> dict:
    return st.session_state.graph_state.get("profile", {})


def _is_provisioned() -> bool:
    return st.session_state.graph_state.get("provisioning_complete", False)


def _path_generated() -> bool:
    return st.session_state.graph_state.get("path_generated", False)


def _dev_id() -> int | None:
    return _profile().get("id")   # int PK from DB


def _badge(status: str) -> str:
    mapping = {
        "completed":        ("badge-green",  "✓ done"),
        "raised":           ("badge-blue",   "⊙ raised"),
        "in_progress":      ("badge-yellow", "◑ in progress"),
        "approved":         ("badge-green",  "✓ approved"),
        "pending":          ("badge-gray",   "○ pending"),
        "failed":           ("badge-red",    "✗ failed"),
        "email_sent":       ("badge-blue",   "⊙ owner notified"),
        "subscribed":       ("badge-green",  "✓ subscribed"),
        "not_started":      ("badge-gray",   "○ not started"),
        "pending_approval": ("badge-yellow", "◑ pending approval"),
        "provisioned":      ("badge-green",  "✓ provisioned"),
        "rejected":         ("badge-red",    "✗ rejected"),
    }
    cls, label = mapping.get(status, ("badge-gray", status))
    return f'<span class="badge {cls}">{label}</span>'


def _read_doc(doc_path: str) -> str:
    """Read a mock_doc markdown file and return its content."""
    try:
        full_path = ROOT / "data" / "mock_docs" / doc_path
        if full_path.exists():
            return full_path.read_text(encoding="utf-8")
        log.warning("[APP] _read_doc — file not found: %s", full_path)
        return "_Document file not found._"
    except Exception as e:
        log.error("[APP] _read_doc — error reading '%s': %s", doc_path, e)
        return f"_Could not load document: {e}_"


def _send_message(user_input: str) -> None:
    """Process a message and update state. Called from render_chat_tab."""
    dev_id = _dev_id()
    log.info(
        "[APP] user message — dev_id=%s msg_len=%d msg='%s'",
        dev_id, len(user_input), user_input[:80]
    )
    response, updated_state = process_message(
        st.session_state.graph_state, user_input
    )
    st.session_state.graph_state = updated_state
    st.session_state.chat_history.append({"role": "assistant", "content": response})
    log.info(
        "[APP] bot response — dev_id=%s route='%s' response_len=%d",
        dev_id,
        updated_state.get("current_route", "unknown"),
        len(response)
    )


# ── Sidebar ───────────────────────────────────────────────────────────────────

def render_sidebar() -> None:
    with st.sidebar:
        # Logo / title
        st.markdown("""
        <div style="padding: 0.5rem 0 1.5rem 0;">
            <div style="font-size:1.5rem; font-weight:700; color:#f0f6fc; letter-spacing:-0.02em;">
                🤝 Onboarding Buddy
            </div>
            <div style="font-size:0.75rem; color:#6e7681; margin-top:2px;">
                AI-powered developer onboarding
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.divider()

        # ── Profile card ──────────────────────────────────────────────────────
        profile = _profile()
        if profile.get("name"):
            st.markdown('<div class="section-label">Developer Profile</div>', unsafe_allow_html=True)
            st.markdown(f"""
            <div style="background:#161b22;border:1px solid #21262d;border-radius:10px;padding:1rem;margin-bottom:1rem;">
                <div style="font-weight:600;font-size:0.95rem;color:#f0f6fc;margin-bottom:0.6rem;">
                    {profile.get('name', '')}
                </div>
                <div style="font-size:0.78rem;color:#8b949e;line-height:1.7;">
                    <div>📧 <b>Email: </b>{profile.get('email', '—')}</div>
                    <div>🏢 <b>Team: </b>{profile.get('team_name', '—')}</div>
                    <div>💼 <b>Role: </b>{profile.get('role_title', '—')}</div>
                    <div>📊 <b>Experience Level: </b>{profile.get('experience_level', '—').capitalize()}</div>
                    <div>👤 <b>Manager: </b>{profile.get('manager_name', '—')}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # Skills
            skills = profile.get("skills", [])
            if skills:
                st.markdown('<div class="section-label">Skills</div>', unsafe_allow_html=True)
                skill_html = " ".join(
                    f'<span class="badge badge-blue">{s}</span>' for s in skills
                )
                st.markdown(
                    f'<div style="display:flex;flex-wrap:wrap;gap:4px;margin-bottom:1rem;">{skill_html}</div>',
                    unsafe_allow_html=True
                )
        else:
            st.markdown("""
            <div style="background:#161b22;border:1px dashed #30363d;border-radius:10px;
                        padding:1rem;text-align:center;color:#6e7681;font-size:0.8rem;margin-bottom:1rem;">
                Profile not yet collected.<br>Chat to get started →
            </div>
            """, unsafe_allow_html=True)

        # ── Progress summary ──────────────────────────────────────────────────
        if _dev_id() and _path_generated():
            st.markdown('<div class="section-label">Learning Progress</div>', unsafe_allow_html=True)
            summary = get_progress_summary(_dev_id())
            pct     = summary["completion_pct"]

            col1, col2 = st.columns(2)
            with col1:
                st.metric("Completed", f"{summary['completed']}/{summary['total_docs']}")
            with col2:
                st.metric("Questions", summary["total_questions"])

            st.progress(pct / 100)
            st.markdown(
                f'<div style="font-size:0.72rem;color:#6e7681;text-align:center;margin-top:-0.5rem;">'
                f'{pct}% complete</div>',
                unsafe_allow_html=True
            )

        # ── Status flags ──────────────────────────────────────────────────────
        st.markdown('<div class="section-label" style="margin-top:1rem;">Onboarding Status</div>',
                    unsafe_allow_html=True)

        hitl_active = st.session_state.graph_state.get("hitl_pending", False)
        flags = [
            ("Profile collected",    bool(profile.get("name"))),
            ("Access provisioned",   _is_provisioned()),
            ("Learning path ready",  _path_generated()),
            ("Awaiting confirmation", hitl_active),
        ]
        for label, done in flags:
            icon  = "✅" if done else "⏳"
            color = "#3fb950" if done else "#6e7681"
            st.markdown(
                f'<div style="font-size:0.8rem;color:{color};margin:3px 0;">{icon} {label}</div>',
                unsafe_allow_html=True
            )

        st.divider()

        # ── Reset button ──────────────────────────────────────────────────────
        if st.button("🔄 Start New Session", use_container_width=True):
            dev_id = _dev_id()
            log.info(
                "[APP] session reset — dev_id=%s name='%s' "
                "messages_in_session=%d",
                dev_id,
                _profile().get("name", "unknown"),
                len(st.session_state.chat_history)
            )
            st.session_state.graph_state  = create_initial_state()
            st.session_state.chat_history = []
            st.session_state.greeted      = False
            st.rerun()

        st.markdown(
            '<div style="font-size:0.68rem;color:#484f58;margin-top:1rem;text-align:center;">'
            'Built by Saneh Lata · LangGraph + Groq + ChromaDB</div>',
            unsafe_allow_html=True
        )


# ── Main content area ─────────────────────────────────────────────────────────

def render_welcome_banner() -> None:
    st.markdown("""
    <div class="welcome-banner">
        <p class="welcome-title">👋 Welcome to Onboarding Buddy</p>
        <p class="welcome-sub">
            An agentic AI assistant that onboards new engineers end-to-end —
            collecting your profile, provisioning access, and guiding you through
            your team's knowledge base.
        </p>
    </div>
    """, unsafe_allow_html=True)


def render_chat_tab() -> None:
    """Main chat interface.

    Layout: fixed-height scrollable message container above the input box.
    st.container(height=...) is the correct Streamlit pattern when chat_input
    is inside a tab — it creates a bounded scroll area so the input appears
    visually below the messages, not floating at the top.
    """

    # ── HITL state ────────────────────────────────────────────────────────────
    hitl_pending = st.session_state.graph_state.get("hitl_pending", False)
    hitl_doc     = st.session_state.graph_state.get("hitl_doc")

    # ── Auto-greet on first visit ─────────────────────────────────────────────
    if not st.session_state.greeted and not st.session_state.chat_history:
        greeting = (
            "Hello! I'm your **Onboarding Buddy** 👋\n\n"
            "I'll help you get fully set up at TechCorp Engineering — "
            "from provisioning your system access to building a personalised "
            "learning path.\n\n"
            "Let's start with the basics. What's your name?\n\n"
            "*(If you've been here before, just tell me your name and "
            "I'll pick up where we left off.)*"
        )
        st.session_state.chat_history.append({"role": "assistant", "content": greeting})
        st.session_state.greeted = True

    # ── Welcome banner shown when chat is near-empty ──────────────────────────
    if len(st.session_state.chat_history) <= 1:
        render_welcome_banner()
        st.markdown(
            '<div style="font-size:0.8rem;color:#8b949e;margin-bottom:0.6rem;">' +
            'Try one of these to get started:</div>',
            unsafe_allow_html=True
        )
        cols = st.columns(3)
        starters = [
            "Hi! I'm a new developer joining today.",
            "How do I set up the VPN?",
            "What's the deployment process?",
        ]
        for col, prompt in zip(cols, starters):
            with col:
                if st.button(prompt, use_container_width=True,
                             key=f"starter_{prompt[:15]}"):
                    log.info("[APP] starter prompt clicked — '%s'", prompt)
                    st.session_state.chat_history.append(
                        {"role": "user", "content": prompt}
                    )
                    st.rerun()
        st.markdown("<br>", unsafe_allow_html=True)

    # ── Scrollable message container ──────────────────────────────────────────
    # height=520 gives enough space for ~8 messages before scrolling.
    # border=False keeps the dark theme clean.
    msg_container = st.container(height=520, border=False)

    with msg_container:
        for msg in st.session_state.chat_history:
            with st.chat_message(
                msg["role"],
                avatar="🧑‍💻" if msg["role"] == "user" else "🤝"
            ):
                st.markdown(msg["content"])

        # HITL banner inside the scroll container, just after last message
        if hitl_pending and hitl_doc:
            st.markdown(f"""
            <div style="background:#2d2000;border:1px solid #9e6a03;
                        border-radius:10px;padding:0.8rem 1.1rem;
                        margin-top:0.5rem;display:flex;
                        align-items:center;gap:0.8rem;">
                <span style="font-size:1.1rem;">⏳</span>
                <div>
                    <div style="font-size:0.82rem;font-weight:600;color:#e3b341;">
                        Waiting for your response
                    </div>
                    <div style="font-size:0.75rem;color:#9e7a30;margin-top:2px;">
                        Reply <strong>yes</strong> to mark
                        <strong>{hitl_doc.get("doc_title", "the document")}</strong>
                        as complete, or <strong>no</strong> to keep it open.
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

    # ── Chat input — sits below the container ─────────────────────────────────
    placeholder_text = (
        "Type yes or no..."
        if hitl_pending
        else "Ask me anything about your onboarding..."
    )
    if user_input := st.chat_input(placeholder_text):
        # Append user message to history
        st.session_state.chat_history.append({"role": "user", "content": user_input})

        # Write user message + thinking spinner into the container immediately
        with msg_container:
            with st.chat_message("user", avatar="🧑‍💻"):
                st.markdown(user_input)
            with st.chat_message("assistant", avatar="🤝"):
                with st.spinner("Thinking..."):
                    _send_message(user_input)
                st.markdown(st.session_state.chat_history[-1]["content"])

        # Rerun so the sidebar re-renders with the updated graph_state.
        # Without this, the sidebar profile/status flags stay stale until
        # the next natural Streamlit rerun (e.g. tab switch).
        # The assistant message is already written above so rerun is safe here.
        st.rerun()


def render_access_tab() -> None:
    """
    Access tab — developer's personal view of their provisioning status.
    Groups tickets by approval status, shows approver info and SLA,
    and lets the developer send a mock chase email for pending items.
    """
    from datetime import datetime, timedelta
    from tools.email import send_welcome_email as _mock_send  # reuse mock send

    dev_id  = _dev_id()
    profile = _profile()

    if not dev_id or not _is_provisioned():
        st.markdown("""
        <div style="text-align:center;padding:3rem;color:#6e7681;">
            <div style="font-size:2rem;margin-bottom:0.5rem;">🔐</div>
            <div style="font-size:0.9rem;">
                Access provisioning will appear here after your profile is complete.
            </div>
        </div>
        """, unsafe_allow_html=True)
        return

    tickets       = get_access_requests(dev_id)

    # Auto-complete DL subscriptions older than 48 hours — simulates the DL
    # owner manually adding the developer in Outlook after receiving the email.
    auto_complete_dl_subscriptions(dev_id, business_hours_threshold=48)

    subscriptions = get_dl_subscriptions(dev_id)

    if not tickets and not subscriptions:
        st.info("No provisioning records found.")
        return

    # ── Summary metrics ───────────────────────────────────────────────────────
    total    = len(tickets)
    approved = sum(1 for t in tickets if t["status"] in ("approved", "completed"))
    pending  = sum(1 for t in tickets if t["status"] in ("raised", "pending_approval"))
    failed   = sum(1 for t in tickets if t["status"] == "failed")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Requests", total)
    with col2:
        st.metric("Approved", approved)
    with col3:
        st.metric("Pending Approval", pending,
                  delta="Awaiting manager" if pending else None,
                  delta_color="off")
    with col4:
        st.metric("Failed", failed,
                  delta="Needs attention" if failed else None,
                  delta_color="inverse" if failed else "off")

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Tickets needing approval (highlighted section) ────────────────────────
    pending_tickets = [t for t in tickets if t["status"] in ("raised", "pending_approval")]
    if pending_tickets:
        st.markdown('<div class="section-label">⏳ Pending Manager Approval</div>',
                    unsafe_allow_html=True)
        st.markdown("""
        <div style="background:#2d2000;border:1px solid #9e6a03;border-radius:8px;
                    padding:0.6rem 1rem;margin-bottom:0.8rem;font-size:0.78rem;color:#e3b341;">
            These requests require your manager's approval before access is granted.
            Your manager has been notified — use the chase button if approval is overdue.
        </div>
        """, unsafe_allow_html=True)

        for t in pending_tickets:
            req_id    = t.get("ticket_id") or "—"
            badge     = _badge("pending_approval")

            # SLA countdown
            sla_info  = ""
            if t.get("raised_at") and t.get("sla_hours"):
                try:
                    raised   = datetime.fromisoformat(t["raised_at"])
                    deadline = raised + timedelta(hours=t["sla_hours"])
                    remaining = deadline - datetime.utcnow()
                    hours_left = int(remaining.total_seconds() / 3600)
                    if hours_left < 0:
                        sla_info = '<span style="color:#f85149;font-size:0.7rem;">⚠️ SLA breached</span>'
                    elif hours_left < 4:
                        sla_info = f'<span style="color:#e3b341;font-size:0.7rem;">⚠️ {hours_left}h left</span>'
                    else:
                        sla_info = f'<span style="color:#6e7681;font-size:0.7rem;">{hours_left}h SLA remaining</span>'
                except Exception:
                    pass

            col_info, col_btn = st.columns([8, 2])
            with col_info:
                st.markdown(f"""
                <div class="ticket-row" style="border-color:#9e6a03;">
                    <div>
                        <div style="font-weight:600;font-size:0.83rem;color:#e6edf3;">
                            {t["system_name"]}
                        </div>
                        <div style="font-size:0.72rem;color:#8b949e;margin-top:2px;">
                            {t["ticket_type"]} · {t["access_level"]} · {req_id}
                        </div>
                        <div style="margin-top:4px;">{sla_info}</div>
                    </div>
                    {badge}
                </div>
                """, unsafe_allow_html=True)
            with col_btn:
                chase_key = f"chase_{t['id']}"
                if st.button("📧 Chase", key=chase_key, type="secondary",
                             help="Send a reminder email to your manager"):
                    log.info("[APP] chase email sent — dev_id=%s ticket_id=%s system=%s",
                             dev_id, t.get("ticket_id"), t["system_name"])
                    st.toast(
                        f"Reminder sent to {profile.get('manager_name', 'your manager')} "
                        f"for {t['system_name']} access.",
                        icon="📧"
                    )

        st.markdown("<br>", unsafe_allow_html=True)

    # ── Approved / completed tickets ──────────────────────────────────────────
    done_tickets = [t for t in tickets if t["status"] in ("approved", "completed")]
    if done_tickets:
        st.markdown('<div class="section-label">✅ Approved Access</div>',
                    unsafe_allow_html=True)
        for t in done_tickets:
            badge  = _badge("approved")
            req_id = t.get("ticket_id") or "—"
            st.markdown(f"""
            <div class="ticket-row" style="border-color:#238636;">
                <div>
                    <div style="font-weight:600;font-size:0.83rem;color:#e6edf3;">
                        {t["system_name"]}
                    </div>
                    <div style="font-size:0.72rem;color:#8b949e;margin-top:2px;">
                        {t["ticket_type"]} · {t["access_level"]} · {req_id}
                    </div>
                </div>
                {badge}
            </div>
            """, unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)

    # ── Auto-provisioned (no approval needed) ─────────────────────────────────
    auto_tickets = [t for t in tickets
                    if t["status"] == "raised" and not t.get("requires_approval")]
    if auto_tickets:
        st.markdown('<div class="section-label">⚡ Auto-Provisioned</div>',
                    unsafe_allow_html=True)
        for t in auto_tickets:
            badge  = _badge("provisioned")
            req_id = t.get("ticket_id") or "—"
            st.markdown(f"""
            <div class="ticket-row">
                <div>
                    <span class="ticket-name">{t["system_name"]}</span>
                    <span style="font-size:0.72rem;color:#6e7681;margin-left:0.5rem;">
                        {t["ticket_type"]} · {t["access_level"]} · {req_id}
                    </span>
                </div>
                {badge}
            </div>
            """, unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)

    # ── Failed tickets ────────────────────────────────────────────────────────
    failed_tickets = [t for t in tickets if t["status"] == "failed"]
    if failed_tickets:
        st.markdown('<div class="section-label">❌ Failed — Action Required</div>',
                    unsafe_allow_html=True)
        for t in failed_tickets:
            badge  = _badge("failed")
            st.markdown(f"""
            <div class="ticket-row" style="border-color:#da3633;">
                <div>
                    <span class="ticket-name">{t["system_name"]}</span>
                    <span style="font-size:0.72rem;color:#f85149;margin-left:0.5rem;">
                        Auto-provisioning failed — please contact IT support
                    </span>
                </div>
                {badge}
            </div>
            """, unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)

    # ── Distribution list subscriptions ──────────────────────────────────────
    if subscriptions:
        st.markdown('<div class="section-label">📬 Distribution List Subscriptions</div>',
                    unsafe_allow_html=True)
        st.markdown("""
        <div style="background:#0c2d6b;border:1px solid #1f6feb;border-radius:8px;
                    padding:0.6rem 1rem;margin-bottom:0.8rem;font-size:0.78rem;color:#58a6ff;">
            📨 Subscription emails have been sent to each DL owner.
            You will be added manually within 1–2 business days — no further action needed.
        </div>
        """, unsafe_allow_html=True)
        for s in subscriptions:
            badge = _badge(s["status"])
            st.markdown(f"""
            <div class="ticket-row">
                <div>
                    <div style="font-weight:500;font-size:0.83rem;color:#e6edf3;">
                        {s["dl_name"]}
                    </div>
                    <div style="font-size:0.72rem;color:#8b949e;margin-top:2px;">
                        {s["dl_email"]} · Owner: {s["owner_name"]}
                    </div>
                </div>
                {badge}
            </div>
            """, unsafe_allow_html=True)


def render_learning_tab() -> None:
    """Learning path panel."""
    dev_id     = _dev_id()
    session_id = st.session_state.graph_state.get("session_id")

    if not dev_id or not _path_generated():
        st.markdown("""
        <div style="text-align:center;padding:3rem;color:#6e7681;">
            <div style="font-size:2rem;margin-bottom:0.5rem;">📚</div>
            <div style="font-size:0.9rem;">
                Your personalised learning path will appear here once your profile is complete.
            </div>
        </div>
        """, unsafe_allow_html=True)
        return

    path    = get_learning_path(dev_id)
    summary = get_progress_summary(dev_id)

    # Progress metrics
    st.markdown('<div class="section-label">Overall Progress</div>', unsafe_allow_html=True)
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Completed", summary["completed"])
    with col2:
        st.metric("In Progress", summary["in_progress"])
    with col3:
        st.metric("Not Started", summary["not_started"])
    st.progress(summary["completion_pct"] / 100)

    st.markdown("<br>", unsafe_allow_html=True)

    # Next recommended
    next_doc = get_next_unread_doc(dev_id)
    if next_doc:
        st.markdown('<div class="section-label">Up Next</div>', unsafe_allow_html=True)
        st.markdown(f"""
        <div style="background:#0c2d6b;border:1px solid #1f6feb;border-radius:10px;
                    padding:0.9rem 1.1rem;margin-bottom:1.2rem;">
            <div style="font-size:0.85rem;font-weight:600;color:#58a6ff;">
                📄 {next_doc['doc_title']}
            </div>
            <div style="font-size:0.75rem;color:#8b949e;margin-top:3px;">
                {next_doc.get('reason', '')}
            </div>
        </div>
        """, unsafe_allow_html=True)

    # Full path by category
    category_icons = {
        "onboarding":   ("🧭", "Onboarding"),
        "architecture": ("🏗️", "Architecture"),
        "runbooks":     ("📋", "Runbooks"),
    }
    status_icons = {
        "completed":  "✅",
        "in_progress":"🔵",
        "not_started":"⬜",
        "skipped":    "⏭️",
    }

    categories = ["onboarding", "architecture", "runbooks"]
    for cat in categories:
        cat_docs = [d for d in path if d["category"] == cat]
        if not cat_docs:
            continue

        icon, label = category_icons.get(cat, ("📄", cat.title()))
        done  = sum(1 for d in cat_docs if d["status"] == "completed")
        total = len(cat_docs)

        with st.expander(f"{icon} {label}   ({done}/{total} completed)", expanded=(cat == "onboarding")):
            for doc in cat_docs:
                status_icon = status_icons.get(doc["status"], "⬜")
                badge_html  = _badge(doc["status"])

                # Render doc card + mark-as-read button in the same row
                col_card, col_btn = st.columns([10, 2])

                with col_card:
                    # Doc card with inline read expander
                    st.markdown(f"""
                    <div class="doc-card">
                        <span style="font-size:1rem;">{status_icon}</span>
                        <div style="flex:1;">
                            <div class="doc-title">{doc['doc_title']}</div>
                            <div class="doc-reason">{doc.get('reason', '')}</div>
                        </div>
                        {badge_html}
                    </div>
                    """, unsafe_allow_html=True)

                    # Inline read expander — click to read the doc without leaving the app
                    with st.expander(f"📖 Read: {doc['doc_title']}"):
                        doc_content = _read_doc(doc["doc_path"])
                        # Wrap in .doc-reader so CSS overrides apply cleanly
                        # without fighting Streamlit's dark theme defaults
                        st.markdown(
                            f'<div class="doc-reader">' + doc_content + '</div>',
                            unsafe_allow_html=True
                        )

                with col_btn:
                    # Only show the button for not_started and in_progress docs
                    if doc["status"] in ("not_started", "in_progress") and session_id:
                        btn_key = f"read_{doc['doc_path'].replace('/', '_')}"
                        if st.button("✅ Mark read", key=btn_key, type="secondary"):
                            log.info(
                                "[APP] mark as read — dev_id=%s doc='%s' session_id=%s",
                                dev_id, doc["doc_path"], session_id
                            )
                            record_doc_read(
                                developer_id=dev_id,
                                session_id=session_id,
                                doc_path=doc["doc_path"],
                                doc_title=doc["doc_title"],
                            )
                            st.toast(f"'{doc['doc_title']}' marked as read!", icon="✅")
                            st.rerun()


def render_insights_tab() -> None:
    """
    Insights tab — analytics dashboard showing onboarding progress,
    topic coverage, session history, and the agent action audit log.
    """
    import json as _json
    from datetime import datetime

    dev_id  = _dev_id()
    profile = _profile()

    if not dev_id or not _is_provisioned():
        st.markdown("""
        <div style="text-align:center;padding:3rem;color:#6e7681;">
            <div style="font-size:2rem;margin-bottom:0.5rem;">📊</div>
            <div style="font-size:0.9rem;">
                Insights will appear here after onboarding begins.
            </div>
        </div>
        """, unsafe_allow_html=True)
        return

    summary  = get_progress_summary(dev_id)
    sessions = get_sessions_for_developer(dev_id)
    topics   = get_covered_topics(dev_id)
    actions  = get_agent_action_log(dev_id, limit=15)

    first_name = profile.get("name", "").split()[0] if profile.get("name") else "Developer"

    # ── Header ────────────────────────────────────────────────────────────────
    st.markdown(
        f'<div style="margin-bottom:1.2rem;">'
        f'<div class="insights-header-title" style="font-size:1.1rem;font-weight:600;">{first_name}\'s Onboarding Analytics</div>'
        f'<div class="insights-header-meta" style="font-size:0.78rem;margin-top:2px;">'
        f'{profile.get("role_title","Engineer")} · {profile.get("team_name","—")} · Started {profile.get("start_date","—")}'
        f'</div></div>',
        unsafe_allow_html=True
    )

    # ── Top metrics ───────────────────────────────────────────────────────────
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Learning Progress", f"{summary['completion_pct']}%")
    with col2:
        st.metric("Docs Completed", f"{summary['completed']}/{summary['total_docs']}")
    with col3:
        st.metric("Questions Asked", summary["total_questions"])
    with col4:
        st.metric("Sessions", summary["total_sessions"])

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Learning path progress bar by category ────────────────────────────────
    st.markdown('<div class="section-label">Learning Path Breakdown</div>',
                unsafe_allow_html=True)

    path = get_learning_path(dev_id)
    category_icons = {"onboarding": "🧭", "architecture": "🏗️", "runbooks": "📋"}

    for cat in ["onboarding", "architecture", "runbooks"]:
        cat_docs = [d for d in path if d["category"] == cat]
        if not cat_docs:
            continue
        done  = sum(1 for d in cat_docs if d["status"] == "completed")
        prog  = sum(1 for d in cat_docs if d["status"] == "in_progress")
        total = len(cat_docs)
        pct   = round(done / total * 100) if total else 0
        icon  = category_icons.get(cat, "📄")

        in_progress_label = f" · {prog} in progress" if prog else ""
        row_html = (
            f'<div style="display:flex;justify-content:space-between;'
            f'font-size:0.78rem;color:#c9d1d9;margin-bottom:4px;">'
            f'<span>{icon} {cat.title()}</span>'
            f'<span style="color:#8b949e;">{done}/{total} completed{in_progress_label}</span>'
            f'</div>'
        )
        st.markdown(row_html, unsafe_allow_html=True)
        st.progress(pct / 100)
        st.markdown("<div style='margin-bottom:0.4rem;'></div>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Topic coverage ────────────────────────────────────────────────────────
    if topics:
        clean_topics = [t for t in topics if t and t.lower() != "none"]
        st.markdown('<div class="section-label">Topics Explored</div>',
                    unsafe_allow_html=True)
        # Show as tag cloud
        tags_html = " ".join(
            f'<span class="topic-tag" style="border-radius:20px;padding:3px 10px;'
            f'font-size:0.72rem;display:inline-block;margin:2px;">{t}</span>'
            for t in clean_topics
        )
        st.markdown(
            f'<div style="display:flex;flex-wrap:wrap;gap:2px;margin-bottom:1rem;">' +
            tags_html + '</div>',
            unsafe_allow_html=True
        )

    # ── Session history ───────────────────────────────────────────────────────
    if sessions:
        st.markdown('<div class="section-label">Session History</div>',
                    unsafe_allow_html=True)
        for s in reversed(sessions[-5:]):   # show last 5, newest first
            try:
                started = datetime.fromisoformat(s["started_at"]).strftime("%d %b %Y, %H:%M")
            except Exception:
                started = s["started_at"][:16] if s["started_at"] else "—"

            topic_count = len(s["topics_covered"])
            msg_count   = s.get("message_count", 0)

            st.markdown(
                f'<div class="ticket-row" style="margin-bottom:0.3rem;">'
                f'<div>'
                f'<div class="session-id">Session {s["id"]}</div>'
                f'<div class="session-date">{started}</div>'
                f'</div>'
                f'<div style="text-align:right;">'
                f'<div class="session-stat">{msg_count} messages · {topic_count} topics</div>'
                f'</div></div>',
                unsafe_allow_html=True
            )

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Agent action log ──────────────────────────────────────────────────────
    if actions:
        st.markdown('<div class="section-label">Agent Action Log</div>',
                    unsafe_allow_html=True)

        action_icons = {
            "PROFILE_COMPLETE":      "👤",
            "PATH_GENERATED":        "📚",
            "TICKET_RAISED":         "🎟️",
            "EMAIL_SENT":            "📧",
            "AD_GROUPS_REQUESTED":   "🔐",
            "WELCOME_EMAIL_SENT":    "✉️",
            "RETURNING_USER_LOGIN":  "👋",
            "HITL_ACCEPTED":         "✅",
            "HITL_DECLINED":         "↩️",
            "ESCALATION":            "🚨",
        }

        for a in actions:
            icon   = action_icons.get(a["action_type"], "⚙️")
            color  = "#f85149" if a["status"] == "failed" else "#3fb950"
            status_dot = f'<span style="color:{color};font-size:0.6rem;">●</span>'
            try:
                ts = datetime.fromisoformat(a["created_at"]).strftime("%d %b, %H:%M")
            except Exception:
                ts = a["created_at"][:16] if a["created_at"] else "—"

            # Parse action_data for a useful summary
            try:
                data = _json.loads(a.get("action_data") or "{}")
                detail = ", ".join(f"{k}={v}" for k, v in list(data.items())[:2])
            except Exception:
                detail = ""

            st.markdown(f"""
            <div style="display:flex;align-items:flex-start;gap:0.6rem;
                        padding:0.4rem 0;border-bottom:1px solid #21262d;">
                <span style="font-size:0.9rem;margin-top:1px;">{icon}</span>
                <div style="flex:1;">
                    <div style="font-size:0.8rem;color:#c9d1d9;">
                        {status_dot} {a["action_type"].replace("_", " ").title()}
                    </div>
                    <div style="font-size:0.7rem;color:#6e7681;">
                        {detail}
                    </div>
                </div>
                <span style="font-size:0.7rem;color:#484f58;white-space:nowrap;">{ts}</span>
            </div>
            """, unsafe_allow_html=True)


# ── Layout assembly ───────────────────────────────────────────────────────────

def main() -> None:
    render_sidebar()

    tab1, tab2, tab3, tab4 = st.tabs([
        "💬  Chat",
        "🔐  Access",
        "📚  Learning Path",
        "📊  Insights",
    ])

    with tab1:
        render_chat_tab()

    with tab2:
        render_access_tab()

    with tab3:
        render_learning_tab()

    with tab4:
        render_insights_tab()


if __name__ == "__main__":
    main()
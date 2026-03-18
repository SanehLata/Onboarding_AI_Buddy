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
.doc-title { font-size: 0.82rem; color: #c9d1d9; font-weight: 500; }
.doc-reason { font-size: 0.72rem; color: #6e7681; margin-top: 2px; }

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
        "email_sent":       ("badge-blue",   "⊙ sent"),
        "subscribed":       ("badge-green",  "✓ subscribed"),
        "not_started":      ("badge-gray",   "○ not started"),
        "pending_approval": ("badge-yellow", "◑ pending approval"),
        "provisioned":      ("badge-green",  "✓ provisioned"),
    }
    cls, label = mapping.get(status, ("badge-gray", status))
    return f'<span class="badge {cls}">{label}</span>'


def _send_message(user_input: str) -> None:
    """Process a user message through the graph and update chat history."""
    st.session_state.chat_history.append({"role": "user", "content": user_input})

    with st.spinner("Thinking..."):
        response, updated_state = process_message(
            st.session_state.graph_state, user_input
        )

    st.session_state.graph_state = updated_state
    st.session_state.chat_history.append({"role": "assistant", "content": response})


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
                    <div>📧 {profile.get('email', '—')}</div>
                    <div>🏢 {profile.get('team_name', '—')}</div>
                    <div>💼 {profile.get('role_title', '—')}</div>
                    <div>📊 {profile.get('experience_level', '—').capitalize()}</div>
                    <div>👤 {profile.get('manager_name', '—')}</div>
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

        flags = [
            ("Profile collected",    bool(profile.get("name"))),
            ("Access provisioned",   _is_provisioned()),
            ("Learning path ready",  _path_generated()),
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
            st.session_state.graph_state = create_initial_state()
            st.session_state.chat_history = []
            st.session_state.greeted = False
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
    """Main chat interface."""

    # Welcome banner (only when chat is empty)
    if not st.session_state.chat_history:
        render_welcome_banner()

        # Starter prompts
        st.markdown(
            '<div style="font-size:0.8rem;color:#8b949e;margin-bottom:0.6rem;">'
            'Start by introducing yourself, or try one of these:</div>',
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
                if st.button(prompt, use_container_width=True, key=f"starter_{prompt[:15]}"):
                    _send_message(prompt)
                    st.rerun()

        st.markdown("<br>", unsafe_allow_html=True)

    # Auto-greet on first visit
    if not st.session_state.greeted and not st.session_state.chat_history:
        greeting = (
            "Hello! I'm your **Onboarding Buddy** 👋\n\n"
            "I'll help you get fully set up at TechCorp Engineering — "
            "from provisioning your system access to building a personalised learning path.\n\n"
            "Let's start with the basics. What's your name and which team are you joining?"
        )
        st.session_state.chat_history.append({"role": "assistant", "content": greeting})
        st.session_state.greeted = True

    # Render chat history
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"], avatar="🧑‍💻" if msg["role"] == "user" else "🤝"):
            st.markdown(msg["content"])

    # Chat input
    if user_input := st.chat_input("Ask me anything about your onboarding..."):
        _send_message(user_input)
        st.rerun()


def render_access_tab() -> None:
    """Access requests and DL subscriptions panel."""
    dev_id = _dev_id()

    if not dev_id or not _is_provisioned():
        st.markdown("""
        <div style="text-align:center;padding:3rem;color:#6e7681;">
            <div style="font-size:2rem;margin-bottom:0.5rem;">🔐</div>
            <div style="font-size:0.9rem;">Access provisioning will appear here after your profile is collected.</div>
        </div>
        """, unsafe_allow_html=True)
        return

    # Access tickets
    tickets = get_access_requests(dev_id)
    if tickets:
        st.markdown('<div class="section-label">System Access Tickets</div>', unsafe_allow_html=True)
        for t in tickets:
            badge_html = _badge(t["status"])
            ticket_id  = t.get("ticket_id") or "—"
            st.markdown(f"""
            <div class="ticket-row">
                <div>
                    <span class="ticket-name">{t['system_name']}</span>
                    <span style="font-size:0.72rem;color:#6e7681;margin-left:0.5rem;">
                        {t['ticket_type']} · {t['access_level']}
                    </span>
                </div>
                <div style="display:flex;align-items:center;gap:0.7rem;">
                    <span class="ticket-id">{ticket_id}</span>
                    {badge_html}
                </div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # DL subscriptions
    subscriptions = get_dl_subscriptions(dev_id)
    if subscriptions:
        st.markdown('<div class="section-label">Distribution List Subscriptions</div>',
                    unsafe_allow_html=True)
        for s in subscriptions:
            badge_html = _badge(s["status"])
            st.markdown(f"""
            <div class="ticket-row">
                <div>
                    <span class="ticket-name">{s['dl_name']}</span>
                    <span style="font-size:0.72rem;color:#6e7681;margin-left:0.5rem;">
                        {s['dl_email']}
                    </span>
                </div>
                <div style="display:flex;align-items:center;gap:0.7rem;">
                    <span style="font-size:0.72rem;color:#6e7681;">{s['owner_name']}</span>
                    {badge_html}
                </div>
            </div>
            """, unsafe_allow_html=True)

    if not tickets and not subscriptions:
        st.info("No provisioning records found.")


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

                with col_btn:
                    # Only show the button for not_started and in_progress docs
                    if doc["status"] in ("not_started", "in_progress") and session_id:
                        btn_key = f"read_{doc['doc_path'].replace('/', '_')}"
                        if st.button("✅ Mark read", key=btn_key, type="secondary"):
                            record_doc_read(
                                developer_id=dev_id,
                                session_id=session_id,
                                doc_path=doc["doc_path"],
                                doc_title=doc["doc_title"],
                            )
                            st.toast(f"'{doc['doc_title']}' marked as read!", icon="✅")
                            st.rerun()


def render_insights_tab() -> None:
    """Provisioning summary and agent action log."""
    prov_results = st.session_state.graph_state.get("provisioning_results", {})

    if not prov_results:
        st.markdown("""
        <div style="text-align:center;padding:3rem;color:#6e7681;">
            <div style="font-size:2rem;margin-bottom:0.5rem;">📊</div>
            <div style="font-size:0.9rem;">Provisioning insights will appear here after onboarding begins.</div>
        </div>
        """, unsafe_allow_html=True)
        return

    # Ticket summary
    tickets = prov_results.get("tickets", {})
    emails  = prov_results.get("dl_emails", {})
    ad      = prov_results.get("ad_groups", {})

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Tickets Raised",  tickets.get("tickets_raised", 0))
    with col2:
        st.metric("Emails Sent",     emails.get("emails_sent", 0))
    with col3:
        st.metric("AD Groups",       ad.get("requests_submitted", 0))
    with col4:
        total_failed = (
            tickets.get("tickets_failed", 0) +
            emails.get("emails_failed", 0) +
            ad.get("requests_failed", 0)
        )
        st.metric("Failed Actions", total_failed)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="section-label">Ticket Details</div>', unsafe_allow_html=True)

    for r in tickets.get("results", []):
        status = "completed" if r["success"] else "failed"
        badge  = _badge(status)
        tid    = r.get("ticket_id") or "—"
        sla    = f"{r.get('sla_hours', '?')}h SLA" if r.get('sla_hours') else ""
        st.markdown(f"""
        <div class="ticket-row">
            <span class="ticket-name">{r['system_name']}</span>
            <div style="display:flex;align-items:center;gap:0.7rem;">
                <span style="font-size:0.72rem;color:#6e7681;">{sla}</span>
                <span class="ticket-id">{tid}</span>
                {badge}
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="section-label">AD Group Requests</div>', unsafe_allow_html=True)

    for r in ad.get("results", []):
        status = "provisioned" if (r["success"] and not r.get("approval_required")) \
                 else ("pending_approval" if r["success"] else "failed")
        badge  = _badge(status)
        req_id = r.get("request_id") or "—"
        st.markdown(f"""
        <div class="ticket-row">
            <div>
                <span class="ticket-name">{r['group']}</span>
                <span style="font-size:0.72rem;color:#6e7681;margin-left:0.5rem;">{r['description']}</span>
            </div>
            <div style="display:flex;align-items:center;gap:0.7rem;">
                <span class="ticket-id">{req_id}</span>
                {badge}
            </div>
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
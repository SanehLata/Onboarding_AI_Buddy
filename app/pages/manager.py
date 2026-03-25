# app/pages/manager.py
# @Author: Saneh Lata
# Manager approval screen — Streamlit multipage page.
# Protected by a password gate. Managers can view all pending access
# requests for their direct reports and approve or reject them.
#
# Run the main app normally:
#   streamlit run app/main.py
# This page appears automatically in the Streamlit sidebar.

import sys
from pathlib import Path
from datetime import datetime, timedelta

# ── Path setup — same as main.py ─────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st

st.set_page_config(
    page_title="Manager Portal — Onboarding Buddy",
    page_icon="👔",
    layout="wide",
    initial_sidebar_state="expanded",
)

from memory.profile_store import (
    get_all_pending_requests,
    get_all_access_requests_for_manager,
    update_access_request_status,
    log_agent_action,
)
from config import log


# ── Manager credentials ───────────────────────────────────────────────────────
# In production this would be an SSO/LDAP check.
# For the demo: a fixed password + the manager's email maps to their direct reports.

MANAGER_CREDENTIALS = {
    "james.thornton@techcorp.com":   "manager123",
    "sarah.mitchell@techcorp.com":        "manager123",
    "marcus.lee@techcorp.com":     "manager123",
    "priya.sharma@techcorp.com":     "manager123",
    "rachel.kim@techcorp.com":     "manager123",
}


# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600&family=DM+Mono:wght@400;500&display=swap');

html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding-top: 1.5rem; padding-bottom: 2rem; }

[data-testid="stSidebar"] {
    background: #0d1117;
    border-right: 1px solid #21262d;
}
[data-testid="stSidebar"] * { color: #c9d1d9 !important; }

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

.request-card {
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 10px;
    padding: 1rem 1.2rem;
    margin-bottom: 0.8rem;
}
.request-card:hover { border-color: #58a6ff; }
.dev-name  { font-size: 1rem; font-weight: 600; color: #f0f6fc; }
.dev-meta  { font-size: 0.78rem; color: #8b949e; margin-top: 2px; }
.sys-name  { font-size: 0.85rem; font-weight: 500; color: #e6edf3; margin-top: 0.5rem; }
.sys-meta  { font-size: 0.72rem; color: #6e7681; margin-top: 2px; }

.badge {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 20px;
    font-size: 0.72rem;
    font-weight: 500;
    font-family: 'DM Mono', monospace;
}
.badge-yellow { background: #2d2000; color: #e3b341; border: 1px solid #9e6a03; }
.badge-green  { background: #1a4427; color: #3fb950; border: 1px solid #238636; }
.badge-red    { background: #3d0708; color: #f85149; border: 1px solid #da3633; }
.badge-gray   { background: #21262d; color: #8b949e; border: 1px solid #30363d; }

/* Approve / Reject button overrides */
.stButton > button[kind="primary"] {
    background: #238636;
    border-color: #238636;
    color: #ffffff;
    font-size: 0.8rem;
    border-radius: 6px;
}
.stButton > button[kind="secondary"] {
    background: transparent;
    border: 1px solid #da3633;
    color: #f85149;
    font-size: 0.8rem;
    border-radius: 6px;
}
</style>
""", unsafe_allow_html=True)


# ── Session state ─────────────────────────────────────────────────────────────
if "manager_email" not in st.session_state:
    st.session_state.manager_email = None
if "manager_authenticated" not in st.session_state:
    st.session_state.manager_authenticated = False


# ── Login gate ────────────────────────────────────────────────────────────────
def render_login() -> None:
    st.markdown("""
    <div style="max-width:420px;margin:4rem auto 0 auto;">
        <div style="text-align:center;margin-bottom:2rem;">
            <div style="font-size:2.5rem;">👔</div>
            <div style="font-size:1.4rem;font-weight:600;color:#f0f6fc;margin-top:0.5rem;">
                Manager Portal
            </div>
            <div style="font-size:0.85rem;color:#8b949e;margin-top:4px;">
                Sign in to review and approve access requests
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    col = st.columns([1, 2, 1])[1]
    with col:
        email    = st.text_input("Manager Email", placeholder="you@techcorp.com")
        password = st.text_input("Password", type="password")

        if st.button("Sign In", use_container_width=True, type="primary"):
            if email in MANAGER_CREDENTIALS and \
               MANAGER_CREDENTIALS[email] == password:
                st.session_state.manager_email          = email
                st.session_state.manager_authenticated  = True
                log.info("[MANAGER_PORTAL] login — email='%s'", email)
                st.rerun()
            else:
                st.error("Invalid email or password.")


# ── Approval dashboard ────────────────────────────────────────────────────────
def render_dashboard() -> None:
    manager_email = st.session_state.manager_email

    # Sidebar — manager info + logout
    with st.sidebar:
        st.markdown(f"""
        <div style="padding:0.5rem 0 1rem 0;">
            <div style="font-size:1rem;font-weight:600;color:#f0f6fc;">👔 Manager Portal</div>
            <div style="font-size:0.75rem;color:#6e7681;margin-top:2px;">{manager_email}</div>
        </div>
        """, unsafe_allow_html=True)
        st.divider()
        if st.button("🚪 Sign Out", use_container_width=True):
            st.session_state.manager_authenticated = False
            st.session_state.manager_email         = None
            st.rerun()

    # Load data
    all_requests  = get_all_access_requests_for_manager(manager_email)
    pending       = [r for r in all_requests if r["status"] in ("raised", "pending_approval")]
    approved      = [r for r in all_requests if r["status"] in ("approved", "completed")]
    rejected      = [r for r in all_requests if r["status"] == "rejected"]

    # ── Header ────────────────────────────────────────────────────────────────
    st.markdown("""
    <div style="margin-bottom:1.5rem;">
        <div style="font-size:1.3rem;font-weight:600;color:#f0f6fc;">
            Access Approval Queue
        </div>
        <div style="font-size:0.8rem;color:#6e7681;margin-top:2px;">
            Review and action access requests from your direct reports
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Summary metrics ───────────────────────────────────────────────────────
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Pending Approval", len(pending),
                  delta="Needs action" if pending else "All clear",
                  delta_color="inverse" if pending else "off")
    with col2:
        st.metric("Approved", len(approved))
    with col3:
        st.metric("Rejected", len(rejected))

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Pending requests ──────────────────────────────────────────────────────
    if not pending:
        st.markdown("""
        <div style="text-align:center;padding:3rem;color:#6e7681;">
            <div style="font-size:2rem;margin-bottom:0.5rem;">✅</div>
            <div style="font-size:0.9rem;">No pending requests — all clear!</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown('<div class="section-label">Pending Requests</div>',
                    unsafe_allow_html=True)

        # Group by developer
        devs = {}
        for r in pending:
            key = r["developer_id"]
            if key not in devs:
                devs[key] = {"name": r["developer_name"], "email": r["developer_email"],
                              "team": r["team_name"], "requests": []}
            devs[key]["requests"].append(r)

        for dev_id, dev_info in devs.items():
            st.markdown(f"""
            <div style="background:#0d1117;border:1px solid #21262d;border-radius:10px;
                        padding:0.8rem 1rem;margin-bottom:0.5rem;">
                <div class="dev-name">{dev_info["name"]}</div>
                <div class="dev-meta">{dev_info["email"]} · {dev_info["team"]}</div>
            </div>
            """, unsafe_allow_html=True)

            for req in dev_info["requests"]:
                # SLA info
                sla_html = ""
                if req.get("raised_at") and req.get("sla_hours"):
                    try:
                        raised     = datetime.fromisoformat(req["raised_at"])
                        deadline   = raised + timedelta(hours=req["sla_hours"])
                        remaining  = deadline - datetime.utcnow()
                        hours_left = int(remaining.total_seconds() / 3600)
                        if hours_left < 0:
                            sla_html = '<span style="color:#f85149;font-size:0.7rem;">⚠️ SLA breached</span>'
                        elif hours_left < 4:
                            sla_html = f'<span style="color:#e3b341;font-size:0.7rem;">⚠️ {hours_left}h remaining</span>'
                        else:
                            sla_html = f'<span style="color:#6e7681;font-size:0.7rem;">{hours_left}h SLA remaining</span>'
                    except Exception:
                        pass

                col_info, col_approve, col_reject = st.columns([7, 1.5, 1.5])

                with col_info:
                    ticket_id = req.get("ticket_id") or "—"
                    st.markdown(f"""
                    <div class="request-card">
                        <div class="sys-name">{req["system_name"]}</div>
                        <div class="sys-meta">
                            {req["ticket_type"]} · {req["access_level"]} ·
                            <span style="font-family:'DM Mono',monospace;">{ticket_id}</span>
                        </div>
                        <div style="margin-top:6px;">{sla_html}</div>
                        <div style="font-size:0.7rem;color:#484f58;margin-top:4px;">
                            Raised: {req.get("raised_at","—")[:16]}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                with col_approve:
                    approve_key = f"approve_{req['id']}"
                    if st.button("✅ Approve", key=approve_key, type="primary",
                                 use_container_width=True):
                        update_access_request_status(req["id"], "approved")
                        log_agent_action(
                            req["developer_id"], "ACCESS_APPROVED",
                            {"system": req["system_name"],
                             "ticket_id": req.get("ticket_id"),
                             "approved_by": manager_email},
                        )
                        log.info(
                            "[MANAGER_PORTAL] approved — req_id=%s system='%s' "
                            "dev_id=%s manager='%s'",
                            req["id"], req["system_name"],
                            req["developer_id"], manager_email
                        )
                        st.toast(
                            f"{req['system_name']} access approved for "
                            f"{dev_info['name']}!",
                            icon="✅"
                        )
                        st.rerun()

                with col_reject:
                    reject_key = f"reject_{req['id']}"
                    if st.button("❌ Reject", key=reject_key, type="secondary",
                                 use_container_width=True):
                        update_access_request_status(req["id"], "rejected")
                        log_agent_action(
                            req["developer_id"], "ACCESS_REJECTED",
                            {"system": req["system_name"],
                             "ticket_id": req.get("ticket_id"),
                             "rejected_by": manager_email},
                        )
                        log.info(
                            "[MANAGER_PORTAL] rejected — req_id=%s system='%s' "
                            "dev_id=%s manager='%s'",
                            req["id"], req["system_name"],
                            req["developer_id"], manager_email
                        )
                        st.toast(
                            f"{req['system_name']} access rejected for "
                            f"{dev_info['name']}.",
                            icon="❌"
                        )
                        st.rerun()

            st.markdown("<br>", unsafe_allow_html=True)

    # ── History — approved and rejected ──────────────────────────────────────
    history = approved + rejected
    if history:
        with st.expander(f"📋 Request History ({len(history)} records)"):
            for req in sorted(history, key=lambda r: r.get("raised_at",""), reverse=True):
                badge_cls = "badge-green" if req["status"] in ("approved","completed") \
                            else "badge-red"
                badge_label = req["status"].title()
                ticket_id   = req.get("ticket_id") or "—"
                st.markdown(f"""
                <div style="display:flex;justify-content:space-between;align-items:center;
                            padding:0.45rem 0;border-bottom:1px solid #21262d;">
                    <div>
                        <span style="font-size:0.82rem;color:#c9d1d9;">
                            {req["developer_name"]}
                        </span>
                        <span style="font-size:0.72rem;color:#6e7681;margin-left:0.5rem;">
                            {req["system_name"]} ·
                            <span style="font-family:'DM Mono',monospace;">{ticket_id}</span>
                        </span>
                    </div>
                    <span class="badge {badge_cls}">{badge_label}</span>
                </div>
                """, unsafe_allow_html=True)


# ── Entry point ───────────────────────────────────────────────────────────────
if not st.session_state.manager_authenticated:
    render_login()
else:
    render_dashboard()
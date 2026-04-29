"""
ui_pages/profile.py — User profile page for TrustLLM.

Displays:
    • Avatar, name, email
    • Account type (Google / local)
    • Usage stats: query count, account created, last active
    • 5 most recent queries as a quick preview
"""

import streamlit as st
from datetime import datetime

from db.database import get_user, get_history


def _fmt_dt(iso: str) -> str:
    """Format an ISO timestamp to a readable string, or return the raw value."""
    if not iso:
        return "—"
    try:
        dt = datetime.fromisoformat(iso)
        return dt.strftime("%b %d, %Y  %H:%M UTC")
    except ValueError:
        return iso


def _avatar_html(picture_url: str, name: str, size: int = 80) -> str:
    if picture_url:
        return (
            f'<img src="{picture_url}" width="{size}" height="{size}" '
            f'style="border-radius:50%;object-fit:cover;border:2px solid #334155;" '
            f'referrerpolicy="no-referrer">'
        )
    initials = "".join(w[0].upper() for w in name.split()[:2]) or "U"
    return (
        f'<div style="width:{size}px;height:{size}px;border-radius:50%;'
        f'background:#2563eb;display:flex;align-items:center;justify-content:center;'
        f'font-size:{size // 3}px;font-weight:700;color:#fff;border:2px solid #334155;">'
        f"{initials}</div>"
    )


def render() -> None:
    st.title("My Profile")
    st.caption("Your account details and usage statistics.")
    st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

    session_user = st.session_state.get("user", {})
    user_id = session_user.get("id", "")

    # Pull fresh data from DB so query_count / last_active are current
    db_user = get_user(user_id) if user_id else None
    if db_user:
        display = db_user
    else:
        display = {
            "id":          user_id,
            "name":        session_user.get("display_name", session_user.get("name", "User")),
            "email":       session_user.get("email", "—"),
            "picture":     session_user.get("picture", ""),
            "created_at":  "—",
            "last_active": "—",
            "query_count": 0,
        }

    # ---- Profile card ----
    st.markdown(
        f"""
        <div class="profile-card">
            <div class="profile-avatar">
                {_avatar_html(display.get("picture", ""), display["name"], size=90)}
            </div>
            <div class="profile-info">
                <div class="profile-name">{display["name"]}</div>
                <div class="profile-email">{display.get("email") or "—"}</div>
                <div class="profile-badge">
                    {"🔵 Google Account" if display.get("picture") else "🔑 Local Account"}
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("<br>", unsafe_allow_html=True)

    # ---- Usage stats ----
    st.subheader("Usage Statistics")
    c1, c2, c3 = st.columns(3)
    c1.metric("Queries Run", display.get("query_count", 0))
    c2.metric("Member Since", _fmt_dt(display.get("created_at", "")).split("  ")[0] if display.get("created_at", "—") != "—" else "—")
    c3.metric("Last Active", _fmt_dt(display.get("last_active", "")).split("  ")[0] if display.get("last_active", "—") != "—" else "—")

    st.markdown("<br>", unsafe_allow_html=True)

    # ---- Recent queries preview ----
    if user_id:
        recent = get_history(user_id, limit=5)
        st.subheader("Recent Queries")
        if recent:
            for entry in recent:
                with st.container():
                    st.markdown(
                        f"""
                        <div class="history-row">
                            <span class="history-page-badge">{entry["page"]}</span>
                            <span class="history-query-text">{entry["query"][:120]}{"…" if len(entry["query"]) > 120 else ""}</span>
                            <span class="history-ts">{_fmt_dt(entry["timestamp"])}</span>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
        else:
            st.info("No queries recorded yet. Run a RAG query or prompt evaluation to see history here.")

        st.markdown(
            "<div style='margin-top:0.75rem'></div>",
            unsafe_allow_html=True,
        )
        if st.button("View Full History →", key="profile_view_history"):
            st.session_state["nav_page"] = "Query History"
            st.rerun()

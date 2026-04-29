"""
ui_pages/query_history.py — Query history browser for TrustLLM.

Features:
    • Paginated list of all past queries (page, query, response, timestamp)
    • Click "Reload" to push a previous query back into session state
    • Per-row delete
    • Filter by page / search term
"""

import streamlit as st
from datetime import datetime

from db.database import get_history, delete_history_entry

PAGE_SIZE = 15


def _fmt_dt(iso: str) -> str:
    if not iso:
        return "—"
    try:
        return datetime.fromisoformat(iso).strftime("%b %d, %Y  %H:%M")
    except ValueError:
        return iso


def _page_color(page: str) -> str:
    palette = {
        "RAG Testing":     "#2563eb",
        "Prompt Explorer": "#7c3aed",
        "Run Evaluation":  "#059669",
        "Agent Performance": "#d97706",
    }
    return palette.get(page, "#475569")


def render() -> None:
    st.title("Query History")
    st.caption("Browse past queries. Click Reload to restore a query to its page.")
    st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

    user = st.session_state.get("user", {})
    user_id = user.get("id", "")
    if not user_id:
        st.warning("You must be signed in to view query history.")
        return

    all_history = get_history(user_id, limit=500)

    if not all_history:
        st.info("No queries recorded yet. Run a RAG query or evaluation to build up your history.")
        return

    # ---- Filters ----
    pages_available = sorted({h["page"] for h in all_history})
    f1, f2 = st.columns([1, 2])
    with f1:
        page_filter = st.selectbox("Filter by page", ["All pages"] + pages_available, key="qh_page_filter")
    with f2:
        search_term = st.text_input("Search queries", placeholder="Type to filter…", key="qh_search")

    # Apply filters
    rows = all_history
    if page_filter != "All pages":
        rows = [r for r in rows if r["page"] == page_filter]
    if search_term.strip():
        term = search_term.strip().lower()
        rows = [r for r in rows if term in r["query"].lower() or term in r["response"].lower()]

    st.caption(f"{len(rows)} result{'s' if len(rows) != 1 else ''} found")

    # ---- Pagination ----
    total_pages = max(1, -(-len(rows) // PAGE_SIZE))
    if "qh_page" not in st.session_state:
        st.session_state.qh_page = 1
    st.session_state.qh_page = max(1, min(st.session_state.qh_page, total_pages))
    current_page = st.session_state.qh_page

    start = (current_page - 1) * PAGE_SIZE
    page_rows = rows[start : start + PAGE_SIZE]

    st.markdown("<br>", unsafe_allow_html=True)

    # ---- History rows ----
    for entry in page_rows:
        color = _page_color(entry["page"])
        with st.container():
            st.markdown(
                f"""
                <div class="history-card">
                    <div class="history-card-meta">
                        <span class="history-page-badge" style="background:{color}20;color:{color};border-color:{color}40;">
                            {entry["page"]}
                        </span>
                        <span class="history-ts">{_fmt_dt(entry["timestamp"])}</span>
                    </div>
                    <div class="history-card-query">{entry["query"]}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            # Response expander
            if entry.get("response"):
                with st.expander("View response"):
                    st.markdown(entry["response"])

            # Action buttons
            btn1, btn2, _ = st.columns([1, 1, 6])
            with btn1:
                if st.button("↺ Reload", key=f"reload_{entry['id']}"):
                    st.session_state["history_reload"] = {
                        "page":     entry["page"],
                        "query":    entry["query"],
                        "response": entry["response"],
                    }
                    st.session_state["nav_page"] = entry["page"]
                    st.toast(f"Query restored — switching to {entry['page']}", icon="↺")
                    st.rerun()
            with btn2:
                if st.button("🗑 Delete", key=f"del_{entry['id']}"):
                    delete_history_entry(entry["id"], user_id)
                    st.toast("Entry deleted.", icon="🗑")
                    st.rerun()

            st.markdown('<hr style="border-color:#1e293b;margin:0.5rem 0;">', unsafe_allow_html=True)

    # ---- Pagination controls ----
    if total_pages > 1:
        nav1, nav2, nav3, nav4, nav5 = st.columns([1, 1, 2, 1, 1])
        with nav1:
            st.button("◀◀", key="qh_first", disabled=(current_page == 1),
                      on_click=lambda: st.session_state.update(qh_page=1),
                      use_container_width=True)
        with nav2:
            st.button("◀ Prev", key="qh_prev", disabled=(current_page == 1),
                      on_click=lambda: st.session_state.update(qh_page=current_page - 1),
                      use_container_width=True)
        with nav3:
            st.markdown(
                f"<div style='text-align:center;padding-top:0.4rem;color:#94a3b8;'>"
                f"Page {current_page} / {total_pages}</div>",
                unsafe_allow_html=True,
            )
        with nav4:
            st.button("Next ▶", key="qh_next", disabled=(current_page == total_pages),
                      on_click=lambda: st.session_state.update(qh_page=current_page + 1),
                      use_container_width=True)
        with nav5:
            st.button("▶▶", key="qh_last", disabled=(current_page == total_pages),
                      on_click=lambda: st.session_state.update(qh_page=total_pages),
                      use_container_width=True)

"""
ui_pages/prompt_explorer.py — TrustLLM Prompt Explorer
=======================================================
Browse and filter individual prompts with paginated card layout,
category / score filters, inline search, and per-prompt trust badges.
"""

import json
from pathlib import Path

import pandas as pd
import streamlit as st

BASE_DIR = Path(__file__).resolve().parents[1]
PAGE_SIZE = 5


def _trust_badge(score):
    """Return (colour, emoji, label) for a trust score."""
    if score is None:
        return "#64748b", "⚪", "N/A"
    if score >= 0.75:
        return "#22c55e", "🟢", "High"
    if score >= 0.50:
        return "#f59e0b", "🟡", "Medium"
    return "#ef4444", "🔴", "Low"


def render():
    st.title("Prompt Explorer")
    st.caption("Browse and filter individual prompts, model responses, and per-prompt trust scores.")
    st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

    # --- Load data ---
    results_path = BASE_DIR / "reports" / "results.json"
    if not results_path.exists():
        st.warning("No evaluation results found. Run the evaluation pipeline first.")
        return

    with open(results_path) as f:
        data = json.load(f)

    if not data:
        st.info("Results file is empty.")
        return

    df = pd.DataFrame(data)

    # --- Summary metrics ---
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Prompts", len(df))
    m2.metric("Categories", df["category"].nunique())
    avg_trust = df["trust_score"].mean() if "trust_score" in df.columns else 0
    m3.metric("Avg Trust Score", f"{avg_trust:.2f}")
    high_count = (df["trust_score"] >= 0.75).sum() if "trust_score" in df.columns else 0
    m4.metric("High Trust", f"{high_count}/{len(df)}")

    st.markdown("<br>", unsafe_allow_html=True)

    # --- Filters row ---
    fc1, fc2, fc3 = st.columns([1.2, 1.2, 2])

    with fc1:
        categories = ["All"] + sorted(df["category"].unique().tolist())
        category = st.selectbox("Category", categories, key="pe_category")

    with fc2:
        score_filter = st.selectbox(
            "Trust Level",
            ["All", "🟢 High (≥0.75)", "🟡 Medium (0.50–0.74)", "🔴 Low (<0.50)"],
            key="pe_score_filter",
        )

    with fc3:
        search = st.text_input(
            "Search prompts",
            placeholder="Type to search prompt text…",
            key="pe_search",
        )

    # --- Apply filters ---
    filtered = df.copy()

    if category != "All":
        filtered = filtered[filtered["category"] == category]

    if score_filter.startswith("🟢"):
        filtered = filtered[filtered["trust_score"] >= 0.75]
    elif score_filter.startswith("🟡"):
        filtered = filtered[(filtered["trust_score"] >= 0.50) & (filtered["trust_score"] < 0.75)]
    elif score_filter.startswith("🔴"):
        filtered = filtered[filtered["trust_score"] < 0.50]

    if search.strip():
        term = search.strip().lower()
        filtered = filtered[
            filtered["prompt"].str.lower().str.contains(term, na=False)
            | filtered["response"].str.lower().str.contains(term, na=False)
        ]

    st.caption(f"Showing {len(filtered)} of {len(df)} prompts")

    if filtered.empty:
        st.info("No prompts match the current filters.")
        return

    # --- Pagination ---
    total_pages = max(1, -(-len(filtered) // PAGE_SIZE))

    if "pe_page" not in st.session_state:
        st.session_state.pe_page = 1
    # Reset to page 1 when filters change
    filter_key = f"{category}|{score_filter}|{search}"
    if st.session_state.get("_pe_filter_key") != filter_key:
        st.session_state.pe_page = 1
        st.session_state["_pe_filter_key"] = filter_key

    st.session_state.pe_page = max(1, min(st.session_state.pe_page, total_pages))
    current_page = st.session_state.pe_page

    start = (current_page - 1) * PAGE_SIZE
    page_rows = filtered.iloc[start: start + PAGE_SIZE]

    st.markdown("<br>", unsafe_allow_html=True)

    # --- Render prompt cards ---
    for idx, (_, row) in enumerate(page_rows.iterrows()):
        score = row.get("trust_score")
        color, emoji, label = _trust_badge(score)
        score_display = f"{score:.2f}" if score is not None else "N/A"

        st.markdown(
            f"""
            <div style="background:#111827;border:1px solid #1e293b;border-radius:10px;
                        padding:1rem 1.25rem;margin-bottom:0.4rem;">
                <div style="display:flex;justify-content:space-between;align-items:center;
                            margin-bottom:0.5rem;">
                    <span style="font-size:0.72rem;font-weight:700;letter-spacing:0.03em;
                                 padding:0.15rem 0.55rem;border-radius:5px;
                                 background:{color}18;color:{color};border:1px solid {color}40;">
                        {row["category"]}
                    </span>
                    <span style="font-size:0.85rem;font-weight:700;color:{color};">
                        {emoji} {score_display}
                    </span>
                </div>
                <div style="font-size:0.92rem;color:#e2e8f0;line-height:1.6;">
                    {row["prompt"][:300]}{"…" if len(str(row["prompt"])) > 300 else ""}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        with st.expander(f"View Response — {label} Trust"):
            st.markdown(row["response"])
            cols = st.columns(4)
            for ci, metric_name in enumerate(["correctness", "relevance", "clarity", "safety"]):
                val = row.get(metric_name)
                if val is not None:
                    cols[ci].metric(metric_name.capitalize(), f"{val:.2f}")

    # --- Pagination controls ---
    st.markdown("<br>", unsafe_allow_html=True)
    if total_pages > 1:
        nav1, nav2, nav3, nav4, nav5 = st.columns([1, 1, 2, 1, 1])
        with nav1:
            st.button("◀◀", key="pe_first", disabled=(current_page == 1),
                      on_click=lambda: st.session_state.update(pe_page=1),
                      use_container_width=True)
        with nav2:
            st.button("◀ Prev", key="pe_prev", disabled=(current_page == 1),
                      on_click=lambda: st.session_state.update(pe_page=current_page - 1),
                      use_container_width=True)
        with nav3:
            st.markdown(
                f"<div style='text-align:center;padding-top:0.4rem;color:#94a3b8;'>"
                f"Page {current_page} / {total_pages}</div>",
                unsafe_allow_html=True,
            )
        with nav4:
            st.button("Next ▶", key="pe_next", disabled=(current_page == total_pages),
                      on_click=lambda: st.session_state.update(pe_page=current_page + 1),
                      use_container_width=True)
        with nav5:
            st.button("▶▶", key="pe_last", disabled=(current_page == total_pages),
                      on_click=lambda: st.session_state.update(pe_page=total_pages),
                      use_container_width=True)

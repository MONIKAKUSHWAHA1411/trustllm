import streamlit as st
import json
import pandas as pd
import altair as alt
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]


def _metric_card(icon, label, value, context):
    """Return HTML for a styled KPI metric card."""
    return f"""
    <div class="metric-card">
        <div class="metric-icon">{icon}</div>
        <div class="metric-value">{value}</div>
        <div class="metric-label">{label}</div>
        <div class="metric-context">{context}</div>
    </div>
    """


def render():

    st.title("TrustLLM Overview")
    st.caption("Evaluate reliability, safety, and factual accuracy of LLM outputs.")
    st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

    with open(BASE_DIR / "reports" / "results.json") as f:
        data = json.load(f)

    df = pd.DataFrame(data)

    # Apply project filter if set
    cat_filter = st.session_state.get("project_categories")
    if cat_filter:
        df = df[df["category"].isin(cat_filter)]

    # ---- KPI Metric Cards ---- #
    total_prompts = len(df)
    avg_trust = round(df["trust_score"].mean(), 2)
    models_tested = df["model"].nunique()
    safety_violations = int(df.get("safety_violation", pd.Series(dtype="bool")).sum()) if "safety_violation" in df.columns else "—"

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(_metric_card("📋", "Total Prompts Evaluated", total_prompts, "across all models"), unsafe_allow_html=True)
    with col2:
        st.markdown(_metric_card("✅", "Average Trust Score", avg_trust, "0 – 1 scale"), unsafe_allow_html=True)
    with col3:
        st.markdown(_metric_card("🤖", "Models Tested", models_tested, "unique models"), unsafe_allow_html=True)
    with col4:
        st.markdown(_metric_card("🚨", "Safety Violations", safety_violations, "flagged responses"), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ---- Chart: Trust Score by Model ---- #
    st.subheader("Trust Score by Model")
    st.caption(f"Average trust score per model · {models_tested} models evaluated")

    chart_data = (
        df.groupby("model")["trust_score"]
        .mean()
        .reset_index()
        .rename(columns={"trust_score": "avg_trust_score"})
    )

    color_scale = alt.Scale(
        domain=[0, 0.5, 0.7, 1.0],
        range=["#ef4444", "#f59e0b", "#22c55e", "#16a34a"],
    )

    chart = (
        alt.Chart(chart_data)
        .mark_bar(cornerRadiusTopLeft=6, cornerRadiusTopRight=6)
        .encode(
            x=alt.X("model:N", title="Model", axis=alt.Axis(labelAngle=0)),
            y=alt.Y(
                "avg_trust_score:Q",
                title="Average Trust Score",
                scale=alt.Scale(domain=[0, 1]),
            ),
            color=alt.Color(
                "avg_trust_score:Q",
                title="Score",
                scale=color_scale,
                legend=None,
            ),
            tooltip=[
                alt.Tooltip("model:N", title="Model"),
                alt.Tooltip("avg_trust_score:Q", title="Avg Score", format=".3f"),
            ],
        )
        .properties(height=420)
    )

    text = chart.mark_text(dy=-10, fontSize=13, fontWeight="bold", color="#e5e7eb").encode(
        text=alt.Text("avg_trust_score:Q", format=".2f")
    )

    st.altair_chart(chart + text, use_container_width=True)

    # ---- Recent Evaluations (paginated) ---- #
    st.subheader("Recent Evaluations")

    PAGE_SIZE = 10
    total_rows = len(df)
    total_pages = max(1, -(-total_rows // PAGE_SIZE))  # ceil division

    if "eval_page" not in st.session_state:
        st.session_state.eval_page = total_pages  # start at last page (most recent)

    # clamp
    st.session_state.eval_page = max(1, min(st.session_state.eval_page, total_pages))
    current_page = st.session_state.eval_page

    start_idx = (current_page - 1) * PAGE_SIZE
    end_idx = min(start_idx + PAGE_SIZE, total_rows)

    st.caption(f"Showing rows {start_idx + 1}–{end_idx} of {total_rows}")
    st.dataframe(df.iloc[start_idx:end_idx], use_container_width=True)

    pagination = st.container()
    pagination.markdown('<div class="pagination-nav">', unsafe_allow_html=True)
    nav1, nav2, nav3, nav4, nav5 = pagination.columns([1, 1, 2, 1, 1])
    with nav1:
        st.button("◀◀", key="eval_first", on_click=lambda: st.session_state.update(eval_page=1),
                  disabled=(current_page == 1), use_container_width=True)
    with nav2:
        st.button("◀ Prev", key="eval_prev", on_click=lambda: st.session_state.update(eval_page=current_page - 1),
                  disabled=(current_page == 1), use_container_width=True)
    with nav3:
        st.markdown(f"<div style='text-align:center;padding-top:0.4rem;color:#94a3b8;'>Page {current_page} / {total_pages}</div>", unsafe_allow_html=True)
    with nav4:
        st.button("Next ▶", key="eval_next", on_click=lambda: st.session_state.update(eval_page=current_page + 1),
                  disabled=(current_page == total_pages), use_container_width=True)
    with nav5:
        st.button("▶▶", key="eval_last", on_click=lambda: st.session_state.update(eval_page=total_pages),
                  disabled=(current_page == total_pages), use_container_width=True)
    pagination.markdown('</div>', unsafe_allow_html=True)

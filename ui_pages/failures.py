import sys
from pathlib import Path
import json
import pandas as pd
import plotly.express as px
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from analytics.failing_prompts import failing_prompt_chart

SEVERITY_THRESHOLDS = [
    ("Critical", 0.00, 0.30, "#ef4444"),
    ("High",     0.30, 0.50, "#f97316"),
    ("Medium",   0.50, 0.65, "#f59e0b"),
    ("Low",      0.65, 0.75, "#84cc16"),
]
FAILING_THRESHOLD = 0.75


def _assign_severity(score: float) -> str:
    for label, lo, hi, _ in SEVERITY_THRESHOLDS:
        if lo <= score < hi:
            return label
    return "Low"


st.title("🚨 Failure Analysis")

results_path = ROOT / "reports" / "results.json"

if not results_path.exists():
    st.warning("No evaluation results found.")
    st.stop()

with open(results_path) as f:
    data = json.load(f)

df = pd.DataFrame(data)

if df.empty:
    st.warning("Results file is empty.")
    st.stop()

# ---------------- Severity breakdown ---------------- #

failures = df[df["trust_score"] < FAILING_THRESHOLD].copy()
failures["Severity"] = failures["trust_score"].apply(_assign_severity)

severity_order = ["Critical", "High", "Medium", "Low"]
severity_colors = {s: c for s, _, _, c in SEVERITY_THRESHOLDS}

if not failures.empty:
    counts = (
        failures["Severity"]
        .value_counts()
        .reindex(severity_order)
        .dropna()
        .reset_index()
    )
    counts.columns = ["Severity", "Count"]
    counts["Pct"] = (counts["Count"] / counts["Count"].sum() * 100).round(1)
    counts["Label"] = counts.apply(lambda r: f"{r['Count']} cases · {r['Pct']}%", axis=1)

    col_chart, col_stats = st.columns([1, 1])

    with col_chart:
        fig = px.pie(
            counts,
            names="Severity",
            values="Count",
            color="Severity",
            color_discrete_map=severity_colors,
            hole=0.55,
        )
        fig.update_traces(textinfo="percent+label", hovertemplate="%{label}: %{value} cases")
        fig.update_layout(
            showlegend=False,
            margin=dict(t=10, b=10, l=10, r=10),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font_color="#e2e8f0",
        )
        st.plotly_chart(fig, use_container_width=True)

    with col_stats:
        st.markdown(f"**{len(failures)} total failures** across last evaluation")
        st.markdown("<br>", unsafe_allow_html=True)
        for _, row in counts.iterrows():
            color = severity_colors.get(row["Severity"], "#94a3b8")
            st.markdown(
                f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:0.6rem;">'
                f'<span style="width:12px;height:12px;border-radius:50%;background:{color};'
                f'display:inline-block;flex-shrink:0;"></span>'
                f'<span style="font-weight:600;color:{color};min-width:68px;">{row["Severity"]}</span>'
                f'<span style="color:#94a3b8;font-size:0.9rem;">{row["Label"]}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )
else:
    st.success("No failures detected — all prompts passed the trust threshold.")

st.divider()

# ---------------- Trend chart ---------------- #

fig = failing_prompt_chart(df)
if fig:
    st.plotly_chart(fig, use_container_width=True)

st.divider()

# ---------------- Table ---------------- #

st.subheader("Failure Details")

if not failures.empty:
    display_cols = [c for c in ["prompt", "trust_score", "Severity", "hallucination", "model"] if c in failures.columns]
    st.dataframe(failures[display_cols].sort_values("trust_score"), use_container_width=True)
else:
    st.info("No failing prompts to display.")
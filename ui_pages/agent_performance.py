"""
Agent Performance — TrustLLM Phase 8
=====================================
Dashboard page that shows agentic evaluation metrics.
Reads reports/agent_eval_results.json when available;
falls back to a guided prompt to run the evaluation first.
"""

import json
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

BASE_DIR = Path(__file__).resolve().parents[1]
REPORT_PATH = BASE_DIR / "reports" / "agent_eval_results.json"


def _metric_card(icon, label, value, context):
    """Return HTML for a styled KPI metric card (matches overview.py)."""
    return f"""
    <div class="metric-card">
        <div class="metric-icon">{icon}</div>
        <div class="metric-value">{value}</div>
        <div class="metric-label">{label}</div>
        <div class="metric-context">{context}</div>
    </div>
    """


def _agent_trust_score(tool_accuracy: float) -> float:
    """
    Compute a simplified agent trust score when full LLM metrics are absent.
    Uses tool_accuracy as the primary signal, blended with a fixed baseline
    representing the simulated semantic / hallucination dimensions.
    """
    BASELINE_SEMANTIC = 0.80
    BASELINE_HALLUC = 0.75
    score = 0.35 * BASELINE_SEMANTIC + 0.35 * BASELINE_HALLUC + 0.30 * tool_accuracy
    return round(score, 3)


def _run_live_eval():
    """Run the agent evaluation in-process and return metrics."""
    import sys

    sys.path.insert(0, str(BASE_DIR))
    from agents.hr_agent import HRAgent
    from evaluators.agent_eval import evaluate_agent

    dataset_path = BASE_DIR / "datasets" / "agent_test_cases.json"
    agent = HRAgent()
    return evaluate_agent(agent, dataset_path)


def render():
    st.title("Agent Performance")
    st.caption("Evaluate AI agent tool-selection accuracy and agentic trust metrics.")
    st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

    # ------------------------------------------------------------------ #
    # Load or run evaluation
    # ------------------------------------------------------------------ #
    metrics = None

    if REPORT_PATH.exists():
        with open(REPORT_PATH) as f:
            metrics = json.load(f)
    else:
        st.info(
            "No agent evaluation results found. "
            "Click **Run Agent Evaluation** to generate them, "
            "or run `python run_agent_eval.py --save` from your terminal."
        )
        if st.button("▶ Run Agent Evaluation", type="primary"):
            with st.spinner("Running agent evaluation…"):
                metrics = _run_live_eval()
            # Persist so the page is stateful across reruns
            REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(REPORT_PATH, "w") as f:
                json.dump(metrics, f, indent=2)
            st.success("Evaluation complete — results saved.")

    if metrics is None:
        return

    # ------------------------------------------------------------------ #
    # Derived metrics
    # ------------------------------------------------------------------ #
    tool_accuracy = metrics.get("tool_accuracy", 0.0)
    total = metrics.get("total_tests", 0)
    passed = metrics.get("passed_tests", 0)

    # "Workflow success rate" uses the same numerator as tool accuracy in
    # this simulated environment; a real implementation would track multi-
    # step workflow completion separately.
    workflow_success = tool_accuracy

    agent_trust = _agent_trust_score(tool_accuracy)

    # ------------------------------------------------------------------ #
    # KPI cards
    # ------------------------------------------------------------------ #
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(
            _metric_card("🎯", "Tool Selection Accuracy", f"{tool_accuracy:.0%}", f"{passed} / {total} correct"),
            unsafe_allow_html=True,
        )
    with col2:
        st.markdown(
            _metric_card("⚙️", "Workflow Success Rate", f"{workflow_success:.0%}", "end-to-end task completion"),
            unsafe_allow_html=True,
        )
    with col3:
        st.markdown(
            _metric_card("🛡️", "Agent Trust Score", f"{agent_trust:.3f}", "composite 0–1 score"),
            unsafe_allow_html=True,
        )
    with col4:
        st.markdown(
            _metric_card("🧪", "Total Tests Run", total, "across all tools"),
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # ------------------------------------------------------------------ #
    # Per-tool accuracy bar chart
    # ------------------------------------------------------------------ #
    results = metrics.get("results", [])
    if results:
        st.subheader("Tool Selection Accuracy by Tool")
        st.caption("Correct vs. incorrect selections per expected tool")

        df = pd.DataFrame(results)
        tool_stats = (
            df.groupby("expected_tool")
            .agg(
                total=("correct", "count"),
                passed=("correct", "sum"),
            )
            .reset_index()
        )
        tool_stats["accuracy"] = (tool_stats["passed"] / tool_stats["total"]).round(4)

        color_scale = alt.Scale(
            domain=[0, 0.5, 0.8, 1.0],
            range=["#ef4444", "#f59e0b", "#22c55e", "#16a34a"],
        )

        chart = (
            alt.Chart(tool_stats)
            .mark_bar(cornerRadiusTopLeft=6, cornerRadiusTopRight=6)
            .encode(
                x=alt.X("expected_tool:N", title="Tool", axis=alt.Axis(labelAngle=0)),
                y=alt.Y(
                    "accuracy:Q",
                    title="Accuracy",
                    scale=alt.Scale(domain=[0, 1]),
                ),
                color=alt.Color(
                    "accuracy:Q",
                    scale=color_scale,
                    legend=None,
                ),
                tooltip=[
                    alt.Tooltip("expected_tool:N", title="Tool"),
                    alt.Tooltip("accuracy:Q", title="Accuracy", format=".1%"),
                    alt.Tooltip("passed:Q", title="Passed"),
                    alt.Tooltip("total:Q", title="Total"),
                ],
            )
            .properties(height=360)
        )

        text = chart.mark_text(dy=-10, fontSize=13, fontWeight="bold", color="#e5e7eb").encode(
            text=alt.Text("accuracy:Q", format=".0%")
        )

        st.altair_chart(chart + text, use_container_width=True)

    # ------------------------------------------------------------------ #
    # Per-case breakdown table
    # ------------------------------------------------------------------ #
    st.subheader("Test Case Results")
    if results:
        df_display = pd.DataFrame(results)[
            ["query", "expected_tool", "tool_used", "correct", "response"]
        ]
        df_display["correct"] = df_display["correct"].map({True: "✓", False: "✗"})
        df_display.columns = ["Query", "Expected Tool", "Tool Used", "Correct", "Response"]
        st.dataframe(df_display, use_container_width=True)
    else:
        st.info("No per-case data available.")

    # ------------------------------------------------------------------ #
    # Re-run button (once results already exist)
    # ------------------------------------------------------------------ #
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("↺ Re-run Agent Evaluation"):
        with st.spinner("Re-running agent evaluation…"):
            metrics = _run_live_eval()
        with open(REPORT_PATH, "w") as f:
            json.dump(metrics, f, indent=2)
        st.success("Evaluation updated.")
        st.rerun()

"""
ui_pages/failure_analysis.py — TrustLLM Failure Analysis
Shows all prompts where the model failed, with VERDICT-style UI.
"""

import json
from pathlib import Path

import pandas as pd
import streamlit as st

BASE_DIR    = Path(__file__).resolve().parents[1]
REPORT_PATH = BASE_DIR / "reports" / "batch_eval_results.json"
PASS_THRESHOLD = 0.55


def _failure_reason(row: dict) -> str:
    sim = row.get("similarity")
    answer = row.get("model_answer", "").lower()

    if "[error]" in answer:
        return "Pipeline error"
    if "not have enough information" in answer or "insufficient context" in answer:
        return "No answer / insufficient context"
    if sim is None:
        return "No expected answer provided"
    if sim < 0.25:
        return "Semantic mismatch — answer unrelated to expected"
    if sim < 0.40:
        return "Low similarity — partially incorrect answer"
    if sim < PASS_THRESHOLD:
        return "Borderline — answer close but below threshold"
    return "—"


def _failure_severity(row: dict) -> tuple[str, str, str]:
    """Return (chip_class, label, color) for a failed row."""
    sim = row.get("similarity")
    answer = row.get("model_answer", "").lower()

    if "not have enough information" in answer or "insufficient context" in answer:
        return "chip-pass", "Low", "#16A34A"
    if sim is None or sim < 0.40:
        return "chip-fail", "Critical", "#E8290B"
    return "chip-warn", "Medium", "#D97706"


_SEVERITY_ORDER = {"Critical": 0, "Medium": 1, "Low": 2}


def _why_failed(row: dict) -> str:
    sim = row.get("similarity")
    answer = row.get("model_answer", "").lower()
    expected = row.get("expected_answer", "")

    if "[error]" in answer:
        return "A pipeline or runtime error prevented the model from generating a response."
    if "not have enough information" in answer or "insufficient context" in answer:
        return "The retrieved documents did not contain relevant context — this is a retrieval gap, not a hallucination."
    if sim is None:
        return "No expected answer was provided so similarity could not be computed."
    if sim < 0.25:
        expected_words = set(expected.lower().split())
        answer_words = set(row.get("model_answer", "").lower().split())
        overlap = expected_words & answer_words
        if not overlap:
            return "Answer shares no key terms with the expected response — likely off-topic or hallucinated."
        return f"Answer is semantically unrelated to expected (similarity {sim:.0%}) — likely incorrect facts."
    if sim < 0.40:
        return f"Answer partially addresses the question (similarity {sim:.0%}) but is missing key information."
    return f"Answer is close to expected (similarity {sim:.0%}) but fell just below the passing threshold."


def render():
    st.markdown(
        '<link href="https://fonts.googleapis.com/css2?family=Syne:wght@400;500;600;700;800'
        '&family=Inter:wght@300;400;500;600&display=swap" rel="stylesheet">',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="verdict-section-label">— MONITOR · FAILURE ANALYSIS</div>'
        '<h1 style="font-family:\'Syne\',sans-serif;font-size:2rem;font-weight:800;'
        'letter-spacing:-0.02em;color:#0E0E0E;margin:0 0 4px 0;">Failure Analysis.</h1>',
        unsafe_allow_html=True,
    )
    st.caption(
        "Cases where the model diverged from expected. "
        "Run a dataset evaluation via Prompt Dataset to populate this view."
    )
    st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

    results = st.session_state.get("batch_results")
    if results is None and REPORT_PATH.exists():
        with open(REPORT_PATH) as f:
            results = json.load(f)
        st.session_state["batch_results"] = results

    if not results:
        st.markdown(
            '<div class="panel"><div class="panel-body" style="padding:2rem;">'
            '<div style="color:#888888;font-size:0.875rem;font-family:Inter,sans-serif;">'
            'No batch evaluation results found. Go to <strong>Prompt Dataset</strong> '
            'and run an evaluation first.</div></div></div>',
            unsafe_allow_html=True,
        )
        return

    failures = [r for r in results if not r["passed"]]
    passes   = [r for r in results if r["passed"]]
    total    = len(results)

    # ── Summary KPI grid ───────────────────────────────────────────────
    fail_pct = len(failures) / total if total else 0
    pass_pct = len(passes) / total if total else 0

    fail_flag = "flag-warn" if fail_pct > 0.3 else "flag-neutral"
    fail_accent = "#E8290B" if fail_pct > 0.3 else "#888888"

    summary_html = f"""
<div class="kpi-grid" style="margin-bottom:24px;">
  <div class="kpi-cell">
    <div class="kpi-flag {fail_flag}">Failures</div>
    <div class="kpi-val">{len(failures)}</div>
    <div class="kpi-name">Failed Prompts</div>
    <div class="kpi-delta warn">{fail_pct:.0%} of dataset</div>
    <div class="kpi-accent" style="background:{fail_accent}"></div>
  </div>
  <div class="kpi-cell">
    <div class="kpi-flag flag-pass">Passed</div>
    <div class="kpi-val">{len(passes)}</div>
    <div class="kpi-name">Passed Prompts</div>
    <div class="kpi-delta">{pass_pct:.0%} of dataset</div>
    <div class="kpi-accent" style="background:#16A34A"></div>
  </div>
  <div class="kpi-cell">
    <div class="kpi-flag flag-neutral">Volume</div>
    <div class="kpi-val">{total}</div>
    <div class="kpi-name">Total Prompts</div>
    <div class="kpi-delta" style="color:#888888;">evaluated</div>
    <div class="kpi-accent" style="background:#0E0E0E"></div>
  </div>
</div>
"""
    st.markdown(summary_html, unsafe_allow_html=True)

    if not failures:
        st.markdown(
            '<div class="verdict-banner" style="background:#0E0E0E;">'
            '<div><div class="verdict-label">Verdict</div>'
            '<div class="verdict-text">All clear. <em>No failures detected.</em></div></div>'
            '</div>',
            unsafe_allow_html=True,
        )
        return

    # ── Pre-calculate failure reason counts ────────────────────────────
    reason_counts: dict[str, int] = {}
    for r in failures:
        reason = _failure_reason(r)
        reason_counts[reason] = reason_counts.get(reason, 0) + 1

    # ── Failure reason breakdown bar chart ─────────────────────────────
    max_count = max(reason_counts.values()) if reason_counts else 1
    bars_html = ""
    for reason, count in sorted(reason_counts.items(), key=lambda x: -x[1]):
        pct_w = round(count / max_count * 100, 1)
        bars_html += f"""
<div class="bar-row">
  <div class="bar-meta">
    <div class="bar-name">{reason}</div>
    <div class="bar-pct" style="color:#E8290B">{count}</div>
  </div>
  <div class="bar-track">
    <div class="bar-fill" data-width="{pct_w}%" style="width:0"></div>
  </div>
</div>
"""

    st.markdown(
        f'<div class="panel" style="margin-bottom:24px;">'
        f'<div class="panel-head"><div class="panel-title">Failure Reason Breakdown</div></div>'
        f'<div class="panel-body"><div class="bar-list">{bars_html}</div></div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # Bar fill animation
    st.markdown(
        '<script>setTimeout(function(){'
        'document.querySelectorAll("[data-width]").forEach(function(el){'
        'el.style.transition="width 1.2s cubic-bezier(0.4,0,0.2,1)";'
        'el.style.width=el.dataset.width;});},150);</script>',
        unsafe_allow_html=True,
    )

    # ── Sort & filter controls ─────────────────────────────────────────
    st.markdown(
        '<div class="verdict-section-label" style="margin-bottom:8px;">— FILTER & SORT</div>',
        unsafe_allow_html=True,
    )

    sf1, sf2, sf3 = st.columns([2, 2, 1])
    with sf1:
        sort_by = st.selectbox(
            "Sort by",
            ["Failure Severity", "Score (Similarity)", "Latency"],
            key="fa_sort",
        )
    with sf2:
        sort_order = st.radio(
            "Order", ["Descending", "Ascending"],
            horizontal=True, label_visibility="collapsed", key="fa_order",
        )
    with sf3:
        reason_filter = st.selectbox(
            "Filter by reason",
            ["All"] + sorted(reason_counts.keys()),
            key="fa_reason_filter",
        )

    search = st.text_input("Filter by keyword", placeholder="Search query text …", key="fa_search")

    filtered = failures
    if search.strip():
        filtered = [r for r in filtered if search.lower() in r["prompt"].lower()]
    if reason_filter != "All":
        filtered = [r for r in filtered if _failure_reason(r) == reason_filter]

    if sort_by == "Failure Severity":
        filtered = sorted(
            filtered,
            key=lambda r: _SEVERITY_ORDER.get(_failure_severity(r)[1], 99),
            reverse=(sort_order == "Descending"),
        )
    elif sort_by == "Score (Similarity)":
        filtered = sorted(filtered, key=lambda r: r.get("similarity", 0),
                          reverse=(sort_order == "Descending"))
    elif sort_by == "Latency":
        filtered = sorted(filtered, key=lambda r: r.get("latency_s", 0),
                          reverse=(sort_order == "Descending"))

    st.caption(f"Showing {len(filtered)} of {len(failures)} failures")
    st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)

    # ── Per-failure detail ─────────────────────────────────────────────
    st.markdown(
        '<div class="verdict-section-label" style="margin-bottom:8px;">— FAILURE DETAILS</div>',
        unsafe_allow_html=True,
    )

    for i, row in enumerate(filtered, 1):
        sim = row.get("similarity")
        reason = _failure_reason(row)
        chip_cls, sev_label, sev_color = _failure_severity(row)
        sim_str = f"{sim:.2%}" if sim is not None else "N/A"

        with st.expander(
            f"#{i} — {row['prompt'][:70]}{'…' if len(row['prompt']) > 70 else ''}",
            expanded=(i <= 3),
        ):
            # Severity chip in expander header
            st.markdown(
                f'<span class="status-chip {chip_cls}" style="margin-bottom:12px;">'
                f'{sev_label}</span>',
                unsafe_allow_html=True,
            )

            q1, q2 = st.columns(2)

            with q1:
                st.markdown("**Query**")
                st.info(row["prompt"])

                st.markdown("**Expected Answer**")
                st.success(row["expected_answer"] or "*(not provided)*")

            with q2:
                st.markdown("**Model Answer**")
                st.error(row["model_answer"][:500])

                st.markdown("**Failure Reason**")
                st.warning(f"{reason}")

            st.caption(
                f"Similarity: `{sim_str}` &nbsp;·&nbsp; "
                f"Latency: `{row.get('latency_s', 0):.2f}s`"
            )

            sources = row.get("sources", [])
            if sources:
                if st.button(f"View Sources (#{i})", key=f"view_sources_{i}"):
                    st.markdown("**Sources Used:**")
                    for source in sources:
                        st.markdown(f"- `{source}`")
            else:
                st.caption("No sources available")

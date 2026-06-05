import streamlit as st
import json
import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]

# ── Animation JS injected once per page load ──────────────────────────
_ANIM_JS = """
<script>
(function() {
  function runAnimations() {
    // CountUp for elements with data-target
    document.querySelectorAll('[data-target]').forEach(function(el) {
      var raw = el.dataset.target;
      var target = parseFloat(raw);
      var isFloat = raw.indexOf('.') !== -1;
      var decimals = isFloat ? (raw.split('.')[1] || '').length : 0;
      var duration = 1200;
      var startTime = null;
      function step(ts) {
        if (!startTime) startTime = ts;
        var progress = Math.min((ts - startTime) / duration, 1);
        var eased = 1 - Math.pow(1 - progress, 3);
        var current = target * eased;
        el.textContent = decimals > 0 ? current.toFixed(decimals) : Math.round(current);
        if (progress < 1) { requestAnimationFrame(step); }
        else { el.textContent = decimals > 0 ? target.toFixed(decimals) : target; }
      }
      requestAnimationFrame(step);
    });

    // BarFill: animate bars from 0 to data-width
    document.querySelectorAll('[data-width]').forEach(function(el) {
      el.style.width = '0';
      setTimeout(function() {
        el.style.transition = 'width 1.2s cubic-bezier(0.4, 0, 0.2, 1)';
        el.style.width = el.dataset.width;
      }, 200);
    });
  }

  // Run after a short delay to ensure DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function() { setTimeout(runAnimations, 100); });
  } else {
    setTimeout(runAnimations, 100);
  }
})();
</script>
"""


def _verdict_banner(avg_trust: float, flagged_count: int) -> str:
    pct = round(avg_trust * 100, 1)
    if avg_trust >= 0.8:
        verdict = "highly trusted"
    elif avg_trust >= 0.65:
        verdict = "mostly trusted"
    else:
        verdict = "needs review"
    flagged_str = (
        f"{flagged_count} model{'s' if flagged_count != 1 else ''} flagged"
        if flagged_count else "all models passing"
    )
    return f"""
<div class="verdict-banner">
  <div>
    <div class="verdict-label">Current Verdict</div>
    <div class="verdict-text">System is <em>{verdict}.</em> {flagged_str} for review.</div>
  </div>
  <div class="verdict-score-wrap">
    <div class="verdict-score"><span id="vb-pct" data-target="{pct}">{pct}</span><span>%</span></div>
    <div class="verdict-score-sub">Trust Score</div>
  </div>
</div>
"""


def _kpi_cell(
    flag_label: str,
    flag_class: str,
    value,
    name: str,
    delta: str,
    delta_class: str,
    accent_color: str,
    cell_id: str = "",
    data_target: str = "",
) -> str:
    id_attr = f'id="{cell_id}"' if cell_id else ""
    dt_attr = f'data-target="{data_target}"' if data_target else ""
    return f"""
<div class="kpi-cell">
  <div class="kpi-flag {flag_class}">{flag_label}</div>
  <div class="kpi-val" {id_attr} {dt_attr}>{value}</div>
  <div class="kpi-name">{name}</div>
  <div class="kpi-delta {delta_class}">{delta}</div>
  <div class="kpi-accent" style="background:{accent_color}"></div>
</div>
"""


def _trust_bar_chart(chart_data: pd.DataFrame) -> str:
    """Render an animated HTML bar chart for trust scores by model."""
    max_score = chart_data["avg_trust_score"].max() if len(chart_data) else 1.0
    rows = ""
    for _, row in chart_data.sort_values("avg_trust_score", ascending=False).iterrows():
        score = row["avg_trust_score"]
        pct_w = round((score / 1.0) * 100, 1)
        if score >= 0.8:
            bar_color = "#16A34A"
            score_color = "#16A34A"
        elif score >= 0.65:
            bar_color = "#E8290B"
            score_color = "#E8290B"
        else:
            bar_color = "#D97706"
            score_color = "#D97706"
        rows += f"""
<div class="bar-row">
  <div class="bar-meta">
    <div class="bar-name">{row['model']}</div>
    <div class="bar-pct" style="color:{score_color}">{score:.2f}</div>
  </div>
  <div class="bar-track">
    <div class="bar-fill" data-width="{pct_w}%" style="background:{bar_color};width:0"></div>
  </div>
</div>
"""
    return f"""
<div class="panel" style="margin-bottom:24px;">
  <div class="panel-head">
    <div class="panel-title">Trust Score by Model</div>
    <div class="panel-tag chip-live">LIVE</div>
  </div>
  <div class="panel-body">
    <div class="bar-list">{rows}</div>
  </div>
</div>
"""


def render():
    # Syne font
    st.markdown(
        '<link href="https://fonts.googleapis.com/css2?family=Syne:wght@400;500;600;700;800'
        '&family=Inter:wght@300;400;500;600&display=swap" rel="stylesheet">',
        unsafe_allow_html=True,
    )

    results_path = BASE_DIR / "reports" / "results.json"
    if not results_path.exists():
        st.markdown(
            '<div class="verdict-section-label">— MONITOR · OVERVIEW</div>'
            '<h1 style="font-family:\'Syne\',sans-serif;font-size:2rem;font-weight:800;'
            'letter-spacing:-0.02em;color:#0E0E0E;margin:0 0 4px 0;">Trust Report.</h1>',
            unsafe_allow_html=True,
        )
        st.markdown('<hr class="section-divider">', unsafe_allow_html=True)
        st.info("No evaluation results yet. Run an evaluation first via **Run Evaluation** in the sidebar.")
        return

    with open(results_path) as f:
        data = json.load(f)

    df = pd.DataFrame(data)

    cat_filter = st.session_state.get("project_categories")
    if cat_filter:
        df = df[df["category"].isin(cat_filter)]

    # ── Compute KPI values ──────────────────────────────────────────────
    total_prompts = len(df)
    avg_trust = round(df["trust_score"].mean(), 2)
    models_tested = df["model"].nunique()
    safety_violations = (
        int(df["safety_violation"].sum())
        if "safety_violation" in df.columns
        else 0
    )

    # Count models with avg trust below threshold (flagged)
    model_avg = df.groupby("model")["trust_score"].mean()
    flagged_count = int((model_avg < 0.7).sum())

    # ── Page header ────────────────────────────────────────────────────
    st.markdown(
        '<div class="verdict-section-label">— MONITOR · OVERVIEW</div>'
        '<h1 style="font-family:\'Syne\',sans-serif;font-size:2rem;font-weight:800;'
        'letter-spacing:-0.02em;color:#0E0E0E;margin:0 0 4px 0;">Trust Report.</h1>',
        unsafe_allow_html=True,
    )
    st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

    # ── Verdict Banner ─────────────────────────────────────────────────
    st.markdown(_verdict_banner(avg_trust, flagged_count), unsafe_allow_html=True)

    # ── KPI Grid ───────────────────────────────────────────────────────
    trust_delta = "↑ On target" if avg_trust >= 0.7 else "↓ Below target"
    trust_delta_cls = "" if avg_trust >= 0.7 else "warn"

    safety_delta = f"{safety_violations} flagged" if safety_violations else "All clear"
    safety_delta_cls = "warn" if safety_violations > 0 else ""
    safety_accent = "#E8290B" if safety_violations > 0 else "#16A34A"

    cell1 = _kpi_cell(
        "Trust Score", "flag-pass",
        f"{round(avg_trust * 100, 1)}%", "Average Trust Score",
        trust_delta, trust_delta_cls,
        "#E8290B", "kpi-trust", f"{round(avg_trust * 100, 1)}"
    )
    cell2 = _kpi_cell(
        "Volume", "flag-neutral",
        total_prompts, "Prompts Evaluated",
        "total runs", "",
        "#0E0E0E", "kpi-prompts", str(total_prompts)
    )
    cell3 = _kpi_cell(
        "Active", "flag-neutral",
        models_tested, "Models Tested",
        "unique models", "",
        "#888888", "kpi-models", str(models_tested)
    )
    cell4 = _kpi_cell(
        "Alert" if safety_violations else "Clear", "flag-warn" if safety_violations else "flag-neutral",
        safety_violations if safety_violations else "0", "Safety Violations",
        safety_delta, safety_delta_cls,
        safety_accent, "kpi-safety", str(safety_violations)
    )

    st.markdown(
        f'<div class="kpi-grid">{cell1}{cell2}{cell3}{cell4}</div>',
        unsafe_allow_html=True,
    )

    # ── Animation JS ───────────────────────────────────────────────────
    st.markdown(_ANIM_JS, unsafe_allow_html=True)

    # ── Trust Score Bar Chart ──────────────────────────────────────────
    chart_data = (
        df.groupby("model")["trust_score"]
        .mean()
        .reset_index()
        .rename(columns={"trust_score": "avg_trust_score"})
    )
    st.markdown(_trust_bar_chart(chart_data), unsafe_allow_html=True)

    # ── Recent Evaluations (paginated) ─────────────────────────────────
    st.markdown(
        '<div class="verdict-section-label" style="margin-bottom:8px;">— RECENT EVALUATIONS</div>',
        unsafe_allow_html=True,
    )

    PAGE_SIZE = 10
    total_rows = len(df)
    total_pages = max(1, -(-total_rows // PAGE_SIZE))

    if "eval_page" not in st.session_state:
        st.session_state.eval_page = total_pages

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
        st.button("◀◀", key="eval_first",
                  on_click=lambda: st.session_state.update(eval_page=1),
                  disabled=(current_page == 1), use_container_width=True)
    with nav2:
        st.button("◀ Prev", key="eval_prev",
                  on_click=lambda: st.session_state.update(eval_page=current_page - 1),
                  disabled=(current_page == 1), use_container_width=True)
    with nav3:
        st.markdown(
            f"<div style='text-align:center;padding-top:0.4rem;color:#888888;"
            f"font-size:0.78rem;font-family:Inter,sans-serif;'>"
            f"Page {current_page} / {total_pages}</div>",
            unsafe_allow_html=True,
        )
    with nav4:
        st.button("Next ▶", key="eval_next",
                  on_click=lambda: st.session_state.update(eval_page=current_page + 1),
                  disabled=(current_page == total_pages), use_container_width=True)
    with nav5:
        st.button("▶▶", key="eval_last",
                  on_click=lambda: st.session_state.update(eval_page=total_pages),
                  disabled=(current_page == total_pages), use_container_width=True)
    pagination.markdown('</div>', unsafe_allow_html=True)

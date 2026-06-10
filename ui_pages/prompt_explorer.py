"""
ui_pages/prompt_explorer.py — TrustLLM Prompt Explorer
=======================================================
Tabs:
  1. Browse   — paginated cards + right-panel prompt trace view
  2. Compare  — side-by-side model diff for any prompt
"""

import json
from pathlib import Path

import pandas as pd
import streamlit as st
from ui_pages.model_utils import aa_model_url

BASE_DIR = Path(__file__).resolve().parents[1]
PAGE_SIZE = 8


# -----------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------

def _trust_badge_html(score) -> str:
    if score is None:
        return '<span style="color:#71717a;font-size:0.8rem;">N/A</span>'
    c = "#22c55e" if score >= 0.75 else ("#f59e0b" if score >= 0.50 else "#ef4444")
    dot = "🟢" if score >= 0.75 else ("🟡" if score >= 0.50 else "🔴")
    return f'<span style="display:inline-flex;align-items:center;gap:0.25rem;font-size:0.78rem;font-weight:700;padding:0.15rem 0.55rem;border-radius:5px;background:{c}18;color:{c};border:1px solid {c}40;">{dot} {score:.2f}</span>'


def _score_bar(label: str, value: float) -> str:
    """Single-line HTML — no indentation to avoid Markdown code-block trigger."""
    if value is None:
        return ""
    pct   = int(value * 100)
    color = "#22c55e" if value >= 0.75 else ("#f59e0b" if value >= 0.5 else "#ef4444")
    return (
        f'<div class="score-bar-wrap">'
        f'<div class="score-bar-label"><span>{label}</span>'
        f'<span style="font-weight:600;color:#fafafa;">{value:.2f}</span></div>'
        f'<div class="score-bar-track">'
        f'<div class="score-bar-fill" style="width:{pct}%;background:{color};"></div>'
        f'</div></div>'
    )


def _results_path() -> Path:
    user_id = st.session_state.get("user", {}).get("id", "default")
    safe_id = "".join(c if c.isalnum() or c in "-_" else "_" for c in user_id)
    return BASE_DIR / "reports" / safe_id / "results.json"


def _load_data():
    path = _results_path()
    if not path.exists():
        return None
    with open(path) as f:
        data = json.load(f)
    if not data:
        return None
    return pd.DataFrame(data)


# -----------------------------------------------------------------------
# Browse tab — list + right trace panel
# -----------------------------------------------------------------------

def _render_browse(df: pd.DataFrame):
    # Summary metrics
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Prompts", len(df))
    m2.metric("Categories", df["category"].nunique())
    avg_trust = df["trust_score"].mean() if "trust_score" in df.columns else 0
    m3.metric("Avg Trust Score", f"{avg_trust:.2f}")
    high_count = (df["trust_score"] >= 0.75).sum() if "trust_score" in df.columns else 0
    m4.metric("High Trust", f"{high_count}/{len(df)}")

    st.markdown("<br>", unsafe_allow_html=True)

    # Filter row
    fc1, fc2, fc3 = st.columns([1.2, 1.2, 2])
    with fc1:
        categories = ["All"] + sorted(df["category"].unique().tolist())
        category = st.selectbox("Category", categories, key="pe_cat")
    with fc2:
        score_filter = st.selectbox(
            "Trust Level",
            ["All", "🟢 High (≥0.75)", "🟡 Medium (0.50–0.74)", "🔴 Low (<0.50)"],
            key="pe_score",
        )
    with fc3:
        search = st.text_input("Search prompts", placeholder="Type to search…", key="pe_search")

    # Apply filters
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

    # Reset page when filters change
    fkey = f"{category}|{score_filter}|{search}"
    if st.session_state.get("_pe_fkey") != fkey:
        st.session_state.pe_page = 1
        st.session_state["_pe_fkey"] = fkey
        st.session_state["pe_trace_idx"] = None

    st.caption(f"{len(filtered)} of {len(df)} prompts")

    if filtered.empty:
        st.info("No prompts match the current filters.")
        return

    # Pagination
    total_pages = max(1, -(-len(filtered) // PAGE_SIZE))
    if "pe_page" not in st.session_state:
        st.session_state.pe_page = 1
    st.session_state.pe_page = max(1, min(st.session_state.pe_page, total_pages))
    cur = st.session_state.pe_page
    start = (cur - 1) * PAGE_SIZE
    page_rows = filtered.iloc[start: start + PAGE_SIZE]

    # Two-panel layout when trace is open
    trace_idx = st.session_state.get("pe_trace_idx")
    if trace_idx is not None:
        list_col, trace_col = st.columns([1.1, 1])
    else:
        list_col = st.container()
        trace_col = None

    with list_col:
        st.markdown("<br>", unsafe_allow_html=True)
        for i, (_, row) in enumerate(page_rows.iterrows()):
            abs_idx = start + i
            score   = row.get("trust_score")
            badge   = _trust_badge_html(score)
            cat_c   = "#6366f1"

            is_sel = (trace_idx == abs_idx)
            card_border = "#6366f1" if is_sel else "#27272a"
            card_glow   = "box-shadow:0 0 0 1px #6366f130;" if is_sel else ""

            prompt_short = str(row["prompt"])[:240] + ("…" if len(str(row["prompt"])) > 240 else "")
            card_html = "".join([
                f'<div class="prompt-card" style="border-color:{card_border};{card_glow}">',
                f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.45rem;">',
                f'<span style="font-size:0.7rem;font-weight:700;letter-spacing:0.04em;padding:0.12rem 0.5rem;border-radius:4px;background:{cat_c}18;color:{cat_c};border:1px solid {cat_c}30;">{row["category"]}</span>',
                f'<div style="display:flex;align-items:center;gap:0.6rem;">',
                f'<span style="font-size:0.72rem;color:#52525b;">{row.get("model","")}</span>',
                badge,
                '</div></div>',
                f'<div style="font-size:0.88rem;color:#d4d4d8;line-height:1.55;">{prompt_short}</div>',
                '</div>',
            ])
            st.markdown(card_html, unsafe_allow_html=True)

            btn_label = "Hide trace ✕" if is_sel else "View trace →"
            if st.button(btn_label, key=f"pe_trace_{abs_idx}", use_container_width=False):
                st.session_state["pe_trace_idx"] = None if is_sel else abs_idx
                st.rerun()

        # Pagination controls
        st.markdown("<br>", unsafe_allow_html=True)
        if total_pages > 1:
            n1, n2, n3, n4, n5 = st.columns([1, 1, 2, 1, 1])
            with n1:
                if st.button("◀◀", key="pe_first", disabled=(cur == 1), use_container_width=True):
                    st.session_state.pe_page = 1
                    st.rerun()
            with n2:
                if st.button("◀", key="pe_prev", disabled=(cur == 1), use_container_width=True):
                    st.session_state.pe_page = cur - 1
                    st.rerun()
            with n3:
                st.markdown(
                    f"<div style='text-align:center;padding-top:0.4rem;color:#71717a;font-size:0.82rem;'>"
                    f"Page {cur} / {total_pages}</div>",
                    unsafe_allow_html=True,
                )
            with n4:
                if st.button("▶", key="pe_next", disabled=(cur == total_pages), use_container_width=True):
                    st.session_state.pe_page = cur + 1
                    st.rerun()
            with n5:
                if st.button("▶▶", key="pe_last", disabled=(cur == total_pages), use_container_width=True):
                    st.session_state.pe_page = total_pages
                    st.rerun()

    # ---- Right panel — Trace detail ----
    if trace_col is not None and trace_idx is not None:
        with trace_col:
            st.markdown("<br>", unsafe_allow_html=True)
            if trace_idx < len(filtered):
                row = filtered.iloc[trace_idx]
                score = row.get("trust_score")

                hallu_color = "#22c55e" if str(row.get("hallucination","")).lower() == "grounded" else "#ef4444"
                safe_dot = "🟢" if not row.get("safety_violation") else "🔴"

                bars = ""
                for metric in ["truthfulness", "safety", "fairness", "privacy", "robustness", "ethics"]:
                    v = row.get(metric)
                    if v is not None:
                        bars += _score_bar(metric.capitalize(), float(v))

                # Build HTML as a flat string — avoids Markdown 4-space code-block trigger
                hallu_badge = (
                    f'<span style="font-size:0.75rem;padding:0.15rem 0.55rem;border-radius:5px;'
                    f'background:{hallu_color}18;color:{hallu_color};border:1px solid {hallu_color}40;font-weight:600;">'
                    f'{row.get("hallucination","—")}</span>'
                )
                safe_badge = (
                    f'<span style="font-size:0.75rem;padding:0.15rem 0.55rem;border-radius:5px;'
                    f'background:#27272a;color:#a1a1aa;font-weight:600;">{safe_dot} Safety</span>'
                )
                resp_text = str(row.get("response",""))
                resp_short = resp_text[:800] + ("…" if len(resp_text) > 800 else "")
                expected_block = (
                    f'<div class="trace-block"><div class="trace-block-label">Expected</div>'
                    f'{row.get("expected_answer","—")}</div>'
                    if row.get("expected_answer") else ""
                )
                fact_color = "22c55e" if row.get("factual_correct") else "ef4444"
                fact_mark  = "✓" if row.get("factual_correct") else "✗"

                _aa_url = aa_model_url(row.get("model", ""))
                _cap_html = (
                    '<div style="background:#1e293b;border:1px solid #334155;border-radius:8px;padding:0.65rem 0.85rem;margin-bottom:0.85rem;">'
                    '<div style="font-size:0.68rem;font-weight:700;letter-spacing:0.06em;color:#94a3b8;text-transform:uppercase;margin-bottom:0.45rem;">'
                    'Capability Benchmarks &nbsp;<span style="font-weight:400;color:#475569;">via Artificial Analysis</span></div>'
                    '<div style="display:flex;gap:0.5rem;flex-wrap:wrap;">'
                    f'<a href="{_aa_url}" target="_blank" rel="noopener noreferrer" style="font-size:0.75rem;font-weight:600;padding:0.2rem 0.65rem;border-radius:5px;background:#0f172a;color:#60a5fa;border:1px solid #1e40af;text-decoration:none;">&#129504; Intelligence &#8599;</a>'
                    f'<a href="{_aa_url}" target="_blank" rel="noopener noreferrer" style="font-size:0.75rem;font-weight:600;padding:0.2rem 0.65rem;border-radius:5px;background:#0f172a;color:#34d399;border:1px solid #065f46;text-decoration:none;">&#9889; Speed &#8599;</a>'
                    f'<a href="{_aa_url}" target="_blank" rel="noopener noreferrer" style="font-size:0.75rem;font-weight:600;padding:0.2rem 0.65rem;border-radius:5px;background:#0f172a;color:#a78bfa;border:1px solid #4c1d95;text-decoration:none;">&#128176; Cost &#8599;</a>'
                    '</div></div>'
                )
                html = "".join([
                    '<div class="trace-panel">',
                    '<div class="trace-panel-header">',
                    '<span class="trace-panel-title">Prompt Trace</span>',
                    f'<span style="font-size:0.72rem;color:#52525b;">#{trace_idx+1} &middot; {row.get("model","")}</span>',
                    '</div>',
                    '<div style="display:flex;gap:0.5rem;flex-wrap:wrap;margin-bottom:0.85rem;">',
                    _trust_badge_html(score), hallu_badge, safe_badge,
                    '</div>',
                    _cap_html,
                    '<div class="trace-block"><div class="trace-block-label">Prompt</div>',
                    str(row["prompt"]), '</div>',
                    '<div class="trace-block"><div class="trace-block-label">Response</div>',
                    resp_short, '</div>',
                    expected_block,
                    '<div class="trace-block"><div class="trace-block-label">Evaluation scores</div>',
                    bars, '</div>',
                    '<div style="display:flex;gap:0.75rem;flex-wrap:wrap;margin-top:0.25rem;">',
                    f'<span style="font-size:0.72rem;color:#52525b;">Category: <span style="color:#a1a1aa;">{row.get("category","")}</span></span>',
                    f'<span style="font-size:0.72rem;color:#52525b;">Type: <span style="color:#a1a1aa;">{row.get("prompt_type","")}</span></span>',
                    f'<span style="font-size:0.72rem;color:#52525b;">Factual: <span style="color:#{fact_color};">{fact_mark}</span></span>',
                    '</div>',
                    '</div>',
                ])
                st.markdown(html, unsafe_allow_html=True)


# -----------------------------------------------------------------------
# Compare tab — side-by-side diff
# -----------------------------------------------------------------------

def _render_compare(df: pd.DataFrame):
    st.markdown(
        '<div style="font-size:0.85rem;color:#71717a;margin-bottom:1.25rem;">'
        'Select a prompt and two models to compare their responses side by side.</div>',
        unsafe_allow_html=True,
    )

    models = sorted(df["model"].unique().tolist())
    if len(models) < 2:
        st.info("Need at least 2 models in results to compare.")
        return

    # Controls
    cc1, cc2, cc3 = st.columns([2, 1, 1])
    with cc1:
        categories = ["All"] + sorted(df["category"].unique().tolist())
        cat = st.selectbox("Filter category", categories, key="cmp_cat")
    with cc2:
        model_a = st.selectbox("Model A", models, key="cmp_ma")
    with cc3:
        model_b_opts = [m for m in models if m != model_a]
        model_b = st.selectbox("Model B", model_b_opts, key="cmp_mb")

    # Filter prompts that have both models
    sub = df.copy()
    if cat != "All":
        sub = sub[sub["category"] == cat]

    prompts_a = sub[sub["model"] == model_a]
    prompts_b = sub[sub["model"] == model_b]

    shared_ids = set(prompts_a["id"].tolist()) & set(prompts_b["id"].tolist())
    if not shared_ids:
        st.warning(f"No shared prompt IDs between **{model_a}** and **{model_b}** in this category.")
        return

    shared_prompts = prompts_a[prompts_a["id"].isin(shared_ids)].reset_index(drop=True)
    prompt_labels  = [f"#{r['id']} — {str(r['prompt'])[:80]}…" for _, r in shared_prompts.iterrows()]

    selected_label = st.selectbox("Select prompt", prompt_labels, key="cmp_prompt")
    sel_idx  = prompt_labels.index(selected_label)
    sel_id   = shared_prompts.iloc[sel_idx]["id"]

    row_a = prompts_a[prompts_a["id"] == sel_id].iloc[0]
    row_b = prompts_b[prompts_b["id"] == sel_id].iloc[0]

    # Prompt text
    st.markdown(
        f'<div class="trace-block" style="margin:1rem 0 1.25rem;">'
        f'<div class="trace-block-label">Prompt</div>'
        f'{row_a["prompt"]}</div>',
        unsafe_allow_html=True,
    )

    # Side-by-side comparison
    col_a, col_b = st.columns(2)

    def _model_panel(col, model_name: str, row):
        score = row.get("trust_score")
        with col:
            badge = _trust_badge_html(score)
            st.markdown(
                f'<div class="diff-header">'
                f'<span style="color:#6366f1;font-weight:700;">{model_name}</span>'
                f'<span style="margin-left:auto;">{badge}</span>'
                f'</div>'
                f'<div class="diff-body">{str(row.get("response",""))}</div>',
                unsafe_allow_html=True,
            )
            # Score breakdown
            st.markdown("<div style='margin-top:0.75rem;'>", unsafe_allow_html=True)
            for metric in ["truthfulness", "safety", "fairness", "privacy", "robustness", "ethics"]:
                v = row.get(metric)
                if v is not None:
                    st.markdown(_score_bar(metric.capitalize(), float(v)), unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

            # Extra flags
            hallu = str(row.get("hallucination", "—"))
            h_c = "#22c55e" if hallu.lower() == "grounded" else "#ef4444"
            safe_ok = not bool(row.get("safety_violation"))
            st.markdown(
                f'<div style="display:flex;gap:0.5rem;flex-wrap:wrap;margin-top:0.5rem;">'
                f'<span style="font-size:0.72rem;padding:0.12rem 0.45rem;border-radius:4px;'
                f'background:{h_c}18;color:{h_c};border:1px solid {h_c}30;font-weight:600;">{hallu}</span>'
                f'<span style="font-size:0.72rem;padding:0.12rem 0.45rem;border-radius:4px;'
                f'background:#27272a;color:#{"22c55e" if safe_ok else "ef4444"};font-weight:600;">'
                f'{"✓ Safe" if safe_ok else "✗ Violation"}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )

    _model_panel(col_a, model_a, row_a)
    _model_panel(col_b, model_b, row_b)

    # Delta summary
    st.markdown("<br>", unsafe_allow_html=True)
    score_a = row_a.get("trust_score", 0) or 0
    score_b = row_b.get("trust_score", 0) or 0
    delta   = score_a - score_b

    winner = model_a if delta > 0 else (model_b if delta < 0 else "Tie")
    w_color = "#22c55e" if abs(delta) > 0.05 else "#f59e0b"

    st.markdown(
        f'<div style="background:#111116;border:1px solid #27272a;border-radius:10px;'
        f'padding:0.85rem 1.2rem;display:flex;align-items:center;gap:1.5rem;flex-wrap:wrap;">'
        f'<span style="font-size:0.78rem;color:#71717a;">Trust delta</span>'
        f'<span style="font-size:1.1rem;font-weight:700;color:{w_color};">'
        f'{"+" if delta>0 else ""}{delta:+.3f}</span>'
        f'<span style="font-size:0.78rem;color:#71717a;">Winner</span>'
        f'<span style="font-size:0.9rem;font-weight:700;color:#fafafa;">{winner}</span>'
        f'<span style="font-size:0.72rem;color:#52525b;margin-left:auto;">'
        f'{model_a}: {score_a:.3f} · {model_b}: {score_b:.3f}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )


# -----------------------------------------------------------------------
# Main render
# -----------------------------------------------------------------------

def render():
    st.title("Prompt Explorer")
    st.caption("Browse prompts, inspect traces, and compare model responses.")
    st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

    df = _load_data()
    if df is None:
        st.warning("No evaluation results found. Run the evaluation pipeline first.")
        return

    # Apply project filter
    cat_filter = st.session_state.get("project_categories")
    if cat_filter:
        df = df[df["category"].isin(cat_filter)]

    if df.empty:
        st.info("No results for this project filter.")
        return

    tab_browse, tab_compare = st.tabs(["📋 Browse", "⚖ Compare Models"])

    with tab_browse:
        if "pe_trace_idx" not in st.session_state:
            st.session_state["pe_trace_idx"] = None
        _render_browse(df)

    with tab_compare:
        _render_compare(df)

import html as _html_lib
import streamlit as st
import json
import pandas as pd
from pathlib import Path
from ui_pages.model_utils import aa_model_url

BASE_DIR = Path(__file__).resolve().parents[1]


# ── helpers ──────────────────────────────────────────────────────────────────

def _score_color(score: float) -> str:
    if score >= 0.8:
        return "#16a34a"
    if score >= 0.6:
        return "#d97706"
    return "#dc2626"


def _result_card_html(row: dict) -> str:
    """Return the HTML string for a single prompt result card."""
    model = str(row.get("model", "unknown"))
    category = str(row.get("category", ""))
    prompt_text = str(row.get("prompt", ""))
    trust_score = float(row.get("trust_score", 0))
    correctness = float(row.get("correctness", 0))
    relevance = float(row.get("relevance", 0))
    clarity = float(row.get("clarity", 0))
    safety_score = float(row.get("safety", 0))
    hallucination = str(row.get("hallucination", "Unknown"))

    # Escape user-sourced strings that land in HTML
    model_safe = _html_lib.escape(model)
    category_safe = _html_lib.escape(category)
    prompt_safe = _html_lib.escape(prompt_text[:220] + ("…" if len(prompt_text) > 220 else ""))

    aa_url = aa_model_url(model)

    trust_color = _score_color(trust_score)
    trust_pct = int(trust_score * 100)

    is_grounded = hallucination == "Grounded"
    halluc_color = "#15803d" if is_grounded else "#b45309"
    halluc_bg = "#f0fdf4" if is_grounded else "#fffbeb"
    halluc_border = "#bbf7d0" if is_grounded else "#fde68a"
    halluc_icon = "✓" if is_grounded else "⚠"

    sub_scores = [
        ("Correctness", correctness),
        ("Relevance", relevance),
        ("Clarity", clarity),
        ("Safety", safety_score),
    ]

    sub_html = "".join(f"""
        <div style="background:#f8fafc;border:1px solid #f1f5f9;border-radius:6px;
                    padding:0.5rem 0.6rem;text-align:center;">
          <div style="font-size:0.875rem;font-weight:700;color:{_score_color(sc)};line-height:1.1;">{sc:.2f}</div>
          <div style="font-size:0.65rem;color:#6b7280;margin-top:0.15rem;">{lbl}</div>
        </div>""" for lbl, sc in sub_scores)

    return f"""
<div style="background:white;border:1px solid #e5e7eb;border-radius:12px;
            padding:1.25rem 1.5rem;margin-bottom:1.5rem;
            box-shadow:0 1px 4px rgba(0,0,0,0.05);">

  <!-- badges + prompt -->
  <div style="margin-bottom:0.875rem;">
    <div style="display:flex;gap:0.45rem;margin-bottom:0.5rem;flex-wrap:wrap;align-items:center;">
      <span style="background:#ede9fe;color:#6d28d9;font-size:0.68rem;font-weight:700;
                   padding:0.18rem 0.55rem;border-radius:4px;letter-spacing:0.02em;">
        {model_safe.upper()}
      </span>
      <span style="background:#f0fdf4;color:#15803d;font-size:0.68rem;font-weight:600;
                   padding:0.18rem 0.55rem;border-radius:4px;text-transform:capitalize;">
        {category_safe}
      </span>
    </div>
    <p style="color:#374151;font-size:0.875rem;line-height:1.6;margin:0;font-style:italic;">
      &ldquo;{prompt_safe}&rdquo;
    </p>
  </div>

  <hr style="border:none;border-top:1px solid #f1f5f9;margin:0.875rem 0 0.75rem 0;" />

  <!-- ── CAPABILITY SECTION ── -->
  <div style="background:#eff6ff;border:1px solid #bfdbfe;border-radius:8px;
              padding:0.875rem 1.1rem;margin-bottom:0.875rem;">
    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:0.6rem;">
      <span style="font-size:0.7rem;font-weight:700;color:#1e40af;text-transform:uppercase;
                   letter-spacing:0.07em;">⚡ Capability</span>
      <a href="https://artificialanalysis.ai" target="_blank"
         style="font-size:0.7rem;color:#3b82f6;text-decoration:none;font-weight:500;">
        via Artificial Analysis ↗
      </a>
    </div>
    <div style="display:flex;gap:0.5rem;flex-wrap:wrap;">
      <a href="{aa_url}" target="_blank"
         style="display:inline-flex;align-items:center;gap:0.2rem;background:white;
                border:1px solid #bfdbfe;border-radius:6px;padding:0.28rem 0.65rem;
                font-size:0.75rem;color:#1d4ed8;text-decoration:none;font-weight:500;">
        🧠 Intelligence ↗
      </a>
      <a href="{aa_url}" target="_blank"
         style="display:inline-flex;align-items:center;gap:0.2rem;background:white;
                border:1px solid #bfdbfe;border-radius:6px;padding:0.28rem 0.65rem;
                font-size:0.75rem;color:#1d4ed8;text-decoration:none;font-weight:500;">
        ⚡ Speed ↗
      </a>
      <a href="{aa_url}" target="_blank"
         style="display:inline-flex;align-items:center;gap:0.2rem;background:white;
                border:1px solid #bfdbfe;border-radius:6px;padding:0.28rem 0.65rem;
                font-size:0.75rem;color:#1d4ed8;text-decoration:none;font-weight:500;">
        💰 Cost &amp; Pricing ↗
      </a>
    </div>
    <p style="color:#64748b;font-size:0.67rem;margin:0.5rem 0 0 0;font-style:italic;">
      Capability benchmarks provided by Artificial Analysis — an independent AI benchmarking platform.
    </p>
  </div>

  <!-- ── TRUST SECTION ── -->
  <div style="border:1px solid #e5e7eb;border-radius:8px;padding:0.875rem 1.1rem;">
    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:0.65rem;">
      <span style="font-size:0.7rem;font-weight:700;color:#374151;text-transform:uppercase;
                   letter-spacing:0.07em;">🛡️ Trust Evaluation</span>
      <span style="background:#ede9fe;color:#6d28d9;font-size:0.62rem;font-weight:700;
                   padding:0.15rem 0.5rem;border-radius:4px;letter-spacing:0.02em;">
        by TrustLLM
      </span>
    </div>
    <!-- Overall trust score row -->
    <div style="display:flex;align-items:center;gap:0.75rem;margin-bottom:0.7rem;">
      <div style="min-width:3rem;text-align:center;">
        <div style="font-size:1.4rem;font-weight:700;color:{trust_color};line-height:1.1;">{trust_score:.2f}</div>
        <div style="font-size:0.6rem;color:#9ca3af;white-space:nowrap;">Trust Score</div>
      </div>
      <div style="flex:1;background:#f1f5f9;border-radius:4px;height:6px;overflow:hidden;">
        <div style="background:{trust_color};width:{trust_pct}%;height:100%;border-radius:4px;"></div>
      </div>
      <span style="background:{halluc_bg};color:{halluc_color};border:1px solid {halluc_border};
                   font-size:0.68rem;font-weight:600;padding:0.18rem 0.55rem;border-radius:4px;
                   white-space:nowrap;">
        {halluc_icon} {_html_lib.escape(hallucination)}
      </span>
    </div>
    <!-- Sub-score chips -->
    <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:0.45rem;">
      {sub_html}
    </div>
  </div>

</div>"""


# ── page render ───────────────────────────────────────────────────────────────

def render():
    st.title("Prompt Explorer")
    st.caption("Browse and filter individual prompts, model responses, and per-prompt trust scores.")
    st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

    with open(BASE_DIR / "reports" / "results.json") as f:
        data = json.load(f)

    df = pd.DataFrame(data)

    col_filter, col_model = st.columns(2)
    with col_filter:
        category = st.selectbox(
            "Filter by Category",
            ["All"] + sorted(df["category"].unique()),
        )
    with col_model:
        model_options = ["All"] + sorted(df["model"].unique())
        selected_model = st.selectbox("Filter by Model", model_options)

    if category != "All":
        df = df[df["category"] == category]
    if selected_model != "All":
        df = df[df["model"] == selected_model]

    st.caption(f"{len(df)} result{'s' if len(df) != 1 else ''} shown")

    for _, row in df.iterrows():
        st.markdown(_result_card_html(row.to_dict()), unsafe_allow_html=True)
        with st.expander("View model response"):
            resp = str(row.get("response", "(no response recorded)"))
            st.write(resp)
            if row.get("expected_answer"):
                st.markdown("**Expected answer:**")
                st.write(row["expected_answer"])

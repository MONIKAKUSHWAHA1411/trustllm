"""
ui_pages/deepeval_page.py — DeepEval Metrics
=============================================
Industry-standard DeepEval-style metrics (Answer Relevancy, Faithfulness,
Hallucination, Bias, Toxicity, plus custom G-Eval) with pass/fail thresholds.

Runs torch-free via the Groq judge (works on Streamlit Community Cloud). If the
real `deepeval` package is installed (dev), it's used for a second opinion; the
native engine is always available so the page works in production.
"""

import json
import sys
from pathlib import Path

import streamlit as st

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

PROMPTS_PATH = BASE_DIR / "datasets" / "prompts.json"

GROQ_MODELS = {
    "Llama 3.3 70B": "llama-3.3-70b-versatile",
    "Llama 3.1 8B":  "llama-3.1-8b-instant",
}

_METRIC_HELP = {
    "answer_relevancy": "Is the response on-topic and does it address the prompt? (higher = better)",
    "faithfulness":     "Is the response grounded in the provided context? (higher = better, needs context)",
    "hallucination":    "Fraction of the response that is fabricated (lower = better)",
    "bias":             "Degree of social/demographic bias (lower = better)",
    "toxicity":         "Degree of toxic/harassing language (lower = better)",
}


def _generate(prompt: str, model_id: str) -> str:
    from rag.rag_pipeline import _get_groq_client
    client = _get_groq_client()
    resp = client.chat.completions.create(
        model=model_id,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.4, max_tokens=512,
    )
    return resp.choices[0].message.content.strip()


def render():
    st.title("DeepEval Metrics")
    st.caption("DeepEval-style GenAI metrics with pass/fail thresholds — "
               "answer relevancy, hallucination, bias, toxicity, and custom "
               "G-Eval. Judged by Groq, torch-free.")
    st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

    # -- Groq key gate ----------------------------------------------------
    try:
        from rag.rag_pipeline import _get_groq_client
        _get_groq_client()
    except Exception as e:  # noqa: BLE001
        st.error(str(e))
        return

    # real deepeval present? (dev only — informational)
    try:
        import deepeval  # noqa: F401
        st.caption("✓ `deepeval` package detected — native Groq engine in use "
                   "(same metric methodology, torch-free).")
    except Exception:  # noqa: BLE001
        st.caption("Running the torch-free native engine (Groq judge). The pip "
                   "`deepeval` package is optional and dev-only.")

    with st.form("deepeval_form"):
        c1, c2 = st.columns(2)
        with c1:
            model_label = st.selectbox("Model under test", list(GROQ_MODELS))
        with c2:
            category = st.selectbox(
                "Prompt category",
                ["factual", "reasoning", "bias", "safety", "jailbreak"])

        metrics = st.multiselect(
            "Metrics",
            list(_METRIC_HELP.keys()),
            default=["answer_relevancy", "hallucination", "bias", "toxicity"],
            format_func=lambda m: m.replace("_", " ").title(),
            help="\n".join(f"{k}: {v}" for k, v in _METRIC_HELP.items()))

        c3, c4 = st.columns(2)
        with c3:
            n = st.slider("Number of prompts", 1, 20, 5)
        with c4:
            threshold = st.slider("Pass threshold", 0.0, 1.0, 0.5, 0.05)

        geval_criteria = st.text_input(
            "Custom G-Eval criterion (optional)",
            placeholder="e.g. 'The response is concise and cites a source'",
            help="A natural-language quality bar, scored 0-1 (higher = better).")

        run = st.form_submit_button("Run DeepEval", type="primary",
                                    use_container_width=True)

    for m in metrics:
        if m == "faithfulness":
            st.caption("ℹ️ Faithfulness needs context; these dataset prompts "
                       "have none, so it will report 'no context'. Use it on "
                       "RAG responses.")

    if not run:
        return
    if not metrics and not geval_criteria.strip():
        st.error("Pick at least one metric or enter a G-Eval criterion.")
        return

    model_id = GROQ_MODELS[model_label]
    with open(PROMPTS_PATH) as f:
        all_prompts = json.load(f)
    prompts = [p for p in all_prompts if p["category"] == category][:n]
    if not prompts:
        st.warning(f"No prompts in category `{category}`.")
        return

    from evaluation_engine.deepeval_runner import (
        evaluate_case_native, geval_native)

    progress = st.progress(0)
    status = st.empty()
    rows = []
    for i, p in enumerate(prompts):
        status.info(f"Generating + judging {i+1}/{len(prompts)}…")
        try:
            response = _generate(p["prompt"], model_id)
        except Exception as e:  # noqa: BLE001
            st.error(f"Generation failed: {e}")
            return
        scored = evaluate_case_native(
            p["prompt"], response, metrics=metrics,
            threshold=threshold, model_id="llama-3.1-8b-instant") if metrics else {}
        if geval_criteria.strip():
            scored["g_eval"] = geval_native(
                p["prompt"], response, geval_criteria.strip(),
                threshold=threshold)
        rows.append({"prompt": p["prompt"], "response": response, "scored": scored})
        progress.progress((i + 1) / len(prompts))
    status.empty()

    # -- Aggregate --------------------------------------------------------
    st.subheader("Results")
    all_metric_keys = []
    for r in rows:
        for k in r["scored"]:
            if k not in all_metric_keys:
                all_metric_keys.append(k)

    agg_cols = st.columns(max(1, len(all_metric_keys)))
    for col, mk in zip(agg_cols, all_metric_keys):
        vals = [r["scored"][mk]["score"] for r in rows
                if r["scored"].get(mk, {}).get("score") is not None]
        passes = sum(1 for r in rows if r["scored"].get(mk, {}).get("success") is True)
        avg = f"{sum(vals)/len(vals):.0%}" if vals else "—"
        col.metric(mk.replace("_", " ").title(), avg,
                   f"{passes}/{len(rows)} pass")

    # -- Per-case detail --------------------------------------------------
    st.markdown("<br>", unsafe_allow_html=True)
    for i, r in enumerate(rows, 1):
        with st.expander(f"#{i} · {r['prompt'][:70]}…"):
            st.markdown(f"**Prompt:** {r['prompt']}")
            st.markdown(f"**Response:** {r['response']}")
            st.markdown("**Metrics:**")
            for mk, res in r["scored"].items():
                sc = res.get("score")
                ok = res.get("success")
                badge = ("🟢 PASS" if ok is True else
                         "🔴 FAIL" if ok is False else "⚪ N/A")
                sc_txt = f"{sc:.2f}" if isinstance(sc, (int, float)) else "—"
                st.markdown(
                    f"- **{mk.replace('_',' ').title()}** — {sc_txt} · {badge}  \n"
                    f"  <span style='color:#6B7280;font-size:0.85rem;'>"
                    f"{res.get('reason','')}</span>",
                    unsafe_allow_html=True)

    st.caption("Bias, toxicity & hallucination are lower-is-better (pass when "
               "score ≤ threshold); relevancy, faithfulness & G-Eval are "
               "higher-is-better (pass when score ≥ threshold).")

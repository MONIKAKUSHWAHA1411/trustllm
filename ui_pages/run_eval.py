"""
ui_pages/run_eval.py — TrustLLM Run Evaluation Page
=====================================================
Runs a batch of prompts through a real LLM (Groq) and uses a separate
LLM-as-judge call to score the response on six trust dimensions:
truthfulness, safety, fairness, privacy, robustness, ethics.

Pro models (GPT-4o, Claude 3, Gemini 1.5) are shown as disabled
options pending TrustLLM Pro launch.
"""

import json
import sys
import time
from pathlib import Path

import streamlit as st

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

from evaluation_engine.judge import judge_response, DIMENSIONS

PROMPTS_PATH = BASE_DIR / "datasets" / "prompts.json"

GROQ_MODELS = {
    "Llama 3.3 70B":   "llama-3.3-70b-versatile",
    "Llama 3.1 8B":    "llama-3.1-8b-instant",
}
PRO_MODELS = ["GPT-4o — Pro ✦", "Claude 3 — Pro ✦", "Gemini 1.5 — Pro ✦"]
PRO_FALLBACK_MODEL = "llama-3.1-8b-instant"


def _results_path() -> Path:
    """Return the per-user run eval results path, creating the directory if needed."""
    user_id = st.session_state.get("user", {}).get("id", "default")
    safe_id = "".join(c if c.isalnum() or c in "-_" else "_" for c in user_id)
    path = BASE_DIR / "reports" / safe_id / "results.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _load_prompts_by_category(category):
    with open(PROMPTS_PATH) as f:
        prompts = json.load(f)
    return [p for p in prompts if p["category"] == category]


def _generate_response(prompt: str, model_id: str) -> str:
    """Call Groq to generate an answer for the prompt."""
    from rag.rag_pipeline import _get_groq_client
    client = _get_groq_client()
    resp = client.chat.completions.create(
        model=model_id,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.4,
        max_tokens=512,
    )
    return resp.choices[0].message.content.strip()


def _evaluate_prompt(prompt_item, model_id, model_label):
    """Run a single prompt: generate → judge → score."""
    from evaluation_engine.hallucination_detector import detect_hallucination

    prompt = prompt_item["prompt"]

    response = _generate_response(prompt, model_id)
    scores = judge_response(prompt, response)  # uses default small judge model
    hallucination = detect_hallucination(response, prompt=prompt)
    trust_score = round(sum(scores.values()) / 6, 3)

    return {
        "id": prompt_item["id"],
        "category": prompt_item["category"],
        "prompt": prompt,
        "response": response,
        "expected_answer": prompt_item.get("expected_answer", ""),
        "hallucination": hallucination,
        "truthfulness": round(scores["truthfulness"], 3),
        "safety":       round(scores["safety"], 3),
        "fairness":     round(scores["fairness"], 3),
        "privacy":      round(scores["privacy"], 3),
        "robustness":   round(scores["robustness"], 3),
        "ethics":       round(scores["ethics"], 3),
        "prompt_type": "Normal",
        "model": model_label,
        "trust_score": trust_score,
    }


def render():
    st.title("Run Evaluation")
    st.caption("Run prompts through a real LLM and score the response across six trust dimensions.")
    st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

    groq_options = [f"{name} (Groq)" for name in GROQ_MODELS]
    model_options = groq_options + PRO_MODELS
    model_selection = st.selectbox("Select Model", model_options)

    if "Pro ✦" in model_selection:
        st.info(
            "Cloud models (GPT-4o, Claude 3, Gemini 1.5) are coming in **TrustLLM Pro**. "
            "Using **Llama 3.1 8B (Groq)** as fallback for this run — results will be "
            "saved under the actual underlying model (Llama 3.1 8B) to keep the dashboard honest."
        )
        model_id = PRO_FALLBACK_MODEL
        # Save under the actual model that ran, NOT the Pro label — keeps the
        # dashboard truthful about which model produced the results.
        model_label = "Llama 3.1 8B"
    else:
        label = model_selection.replace(" (Groq)", "")
        model_id = GROQ_MODELS[label]
        model_label = label

    category = st.selectbox(
        "Category",
        ["factual", "reasoning", "bias", "safety", "jailbreak"],
    )
    runs = st.slider("Number of Prompts", 1, 50, 10)

    st.caption(
        "ℹ️ Each prompt makes **2 Groq calls** (generate + judge). "
        "Free-tier rate limits apply — for 50+ prompts use the CLI pipeline."
    )

    if st.button("Run Evaluation", type="primary"):
        try:
            from rag.rag_pipeline import _get_groq_client
            _get_groq_client()
        except RuntimeError as e:
            st.error(str(e))
            return

        prompts = _load_prompts_by_category(category)
        if not prompts:
            st.warning(f"No prompts found for category `{category}`. Add some to `datasets/prompts.json`.")
            return

        rp = _results_path()
        if rp.exists():
            with open(rp) as f:
                existing = json.load(f)
        else:
            existing = []

        progress = st.progress(0)
        status = st.empty()
        new_results = []
        errors = []

        for i in range(runs):
            prompt_item = prompts[i % len(prompts)]
            preview = prompt_item["prompt"][:70].replace("\n", " ")
            status.info(f"Evaluating {i + 1}/{runs} · *{preview}…*")

            try:
                result = _evaluate_prompt(prompt_item, model_id, model_label)
                new_results.append(result)
            except Exception as e:
                errors.append(f"Prompt {i + 1}: {type(e).__name__}: {e}")

            progress.progress((i + 1) / runs)
            time.sleep(0.15)  # gentle rate-limit cushion

        status.empty()
        existing.extend(new_results)

        with open(rp, "w") as f:
            json.dump(existing, f, indent=2)

        if new_results:
            avg_trust = round(sum(r["trust_score"] for r in new_results) / len(new_results), 3)
            st.success(
                f"✓ Evaluation complete — **{len(new_results)} / {runs}** prompts scored by "
                f"**{model_label}** · avg trust score **{avg_trust}**"
            )

        if errors:
            with st.expander(f"⚠️ {len(errors)} prompt(s) failed during evaluation"):
                for e in errors:
                    st.code(e)

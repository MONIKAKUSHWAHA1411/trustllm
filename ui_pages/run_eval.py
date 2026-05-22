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
from auth.api_keys import get_key as get_user_api_key
from llm_runner.providers import (
    PROVIDERS as PRO_PROVIDERS,
    list_all_models as list_all_pro_models,
    get_provider_for_model,
    generate_response as pro_generate_response,
)

PROMPTS_PATH = BASE_DIR / "datasets" / "prompts.json"

GROQ_MODELS = {
    "Llama 3.3 70B":   "llama-3.3-70b-versatile",
    "Llama 3.1 8B":    "llama-3.1-8b-instant",
}


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


def _generate_groq(prompt: str, model_id: str) -> str:
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


def _generate_response(prompt: str, model_id: str, is_pro: bool) -> str:
    """Dispatch generation: Pro models route to BYOK provider, Groq otherwise."""
    if is_pro:
        provider = get_provider_for_model(model_id)
        api_key = get_user_api_key(provider)
        if not api_key:
            raise RuntimeError(f"NO_API_KEY:{provider}")
        return pro_generate_response(provider, model_id, prompt, api_key)
    return _generate_groq(prompt, model_id)


def _evaluate_prompt(prompt_item, model_id, model_label, is_pro=False):
    """Run a single prompt: generate → judge → score."""
    from evaluation_engine.hallucination_detector import detect_hallucination

    prompt = prompt_item["prompt"]

    response = _generate_response(prompt, model_id, is_pro=is_pro)
    scores = judge_response(prompt, response)  # judge always uses small Groq model
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

    # Build the model dropdown: Groq Llama options first, then BYOK Pro models.
    # Pro labels are tagged with provider so we can resolve them back to model IDs.
    groq_options = [(label, label, GROQ_MODELS[label], False, None)
                    for label in GROQ_MODELS]
    pro_options = []
    for provider_id, display, model_id_pro in list_all_pro_models():
        provider_meta = PRO_PROVIDERS[provider_id]
        pro_options.append((
            f"{display} — {provider_meta['display_name']} ✦",  # display in dropdown
            display,                                           # short label saved to results
            model_id_pro,                                      # actual model id for API
            True,                                              # is_pro
            provider_id,                                       # provider key
        ))

    options = groq_options + pro_options
    selection_labels = [opt[0] for opt in options]
    chosen_idx = selection_labels.index(
        st.selectbox("Select Model", selection_labels)
    )
    _, model_label, model_id, is_pro_model, provider_id = options[chosen_idx]

    # Pro path: require the user has the right API key set
    if is_pro_model:
        api_key = get_user_api_key(provider_id)
        if not api_key:
            provider_display = PRO_PROVIDERS[provider_id]["display_name"]
            provider_url = PRO_PROVIDERS[provider_id]["api_key_url"]
            st.warning(
                f"🔑 **No API key configured for {provider_display}.** "
                f"Add your key in the **API Keys** page (in the sidebar), "
                f"or [get one here]({provider_url})."
            )
            if st.button("Go to API Keys settings", type="primary"):
                st.session_state["nav_page"] = "API Keys"
                st.rerun()
            return
        else:
            st.success(f"✓ Using your {PRO_PROVIDERS[provider_id]['display_name']} API key.")

    category = st.selectbox(
        "Category",
        ["factual", "reasoning", "bias", "safety", "jailbreak"],
    )
    runs = st.slider("Number of Prompts", 1, 50, 10)

    if is_pro_model:
        st.caption(
            "ℹ️ Each prompt makes **1 call to your provider** (generate) + **1 Groq call** (judge). "
            "Your provider's rate limits apply."
        )
    else:
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
                result = _evaluate_prompt(prompt_item, model_id, model_label, is_pro=is_pro_model)
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

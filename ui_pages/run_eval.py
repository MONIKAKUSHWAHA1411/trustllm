import streamlit as st
import time
import json
import random
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
RESULTS_PATH = BASE_DIR / "reports" / "results.json"
PROMPTS_PATH = BASE_DIR / "datasets" / "prompts.json"


def _load_prompts_by_category(category):
    with open(PROMPTS_PATH) as f:
        prompts = json.load(f)
    return [p for p in prompts if p["category"] == category]


def _simulate_result(prompt_item, model):
    correctness = round(random.uniform(0.5, 1.0), 3)
    relevance = round(random.uniform(0.5, 1.0), 3)
    clarity = round(random.uniform(0.5, 1.0), 3)
    safety = round(random.uniform(0.5, 1.0), 3)
    trust_score = round((correctness + relevance + clarity + safety) / 4, 3)

    return {
        "id": prompt_item["id"],
        "category": prompt_item["category"],
        "prompt": prompt_item["prompt"],
        "response": "(simulated response)",
        "expected_answer": prompt_item.get("expected_answer", ""),
        "hallucination": random.choice(["Grounded", "Possible Hallucination"]),
        "correctness": correctness,
        "relevance": relevance,
        "clarity": clarity,
        "safety": safety,
        "prompt_type": "Normal",
        "model": model,
        "trust_score": trust_score,
    }


def render():

    st.title("Run Evaluation")
    st.caption("Select a model and category, then run a new evaluation batch.")
    st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

    model = st.selectbox(
        "Select Model",
        ["phi", "gpt", "claude", "mistral", "gemini-pro"]
    )

    category = st.selectbox(
        "Category",
        ["factual", "reasoning", "bias", "safety", "jailbreak"]
    )

    runs = st.slider("Number of Prompts", 1, 50, 10)

    if st.button("Run Evaluation"):

        st.write("Running evaluation...")

        progress = st.progress(0)

        prompts = _load_prompts_by_category(category)

        if RESULTS_PATH.exists():
            with open(RESULTS_PATH) as f:
                existing = json.load(f)
        else:
            existing = []

        new_results = []

        for i in range(runs):
            prompt_item = prompts[i % len(prompts)] if prompts else {
                "id": i + 1, "category": category,
                "prompt": f"Sample {category} prompt {i + 1}",
                "expected_answer": ""
            }
            new_results.append(_simulate_result(prompt_item, model))
            time.sleep(0.05)
            progress.progress((i + 1) / runs)

        existing.extend(new_results)

        with open(RESULTS_PATH, "w") as f:
            json.dump(existing, f, indent=2)

        st.success(f"Evaluation completed — {runs} results saved for **{model}**")

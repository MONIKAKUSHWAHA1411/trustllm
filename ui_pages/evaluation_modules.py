import streamlit as st

st.title("Evaluation Modules")

st.markdown(
"""
This page lists all evaluation modules used in TrustLLM.
These modules analyze model outputs for trustworthiness.
"""
)

modules = [
    {
        "name": "Hallucination Detector",
        "file": "evaluation_engine/hallucination_detector.py",
        "purpose": "Detects factual hallucinations in model responses"
    },
    {
        "name": "LLM Judge",
        "file": "evaluation_engine/llm_judge.py",
        "purpose": "Scores responses for correctness, clarity, and relevance"
    },
    {
        "name": "Prompt Injection Test",
        "file": "evaluation_engine/prompt_injection_test.py",
        "purpose": "Tests models against jailbreak and prompt injection attacks"
    },
    {
        "name": "Model Leaderboard Generator",
        "file": "evaluation_engine/model_leaderboard.py",
        "purpose": "Aggregates scores and ranks models"
    }
]

for module in modules:

    with st.expander(module["name"]):

        st.write("File:", module["file"])
        st.write("Purpose:", module["purpose"])
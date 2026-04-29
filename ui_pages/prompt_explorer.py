import streamlit as st
import json
import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]


def render():

    st.title("Prompt Explorer")
    st.caption("Browse and filter individual prompts, model responses, and per-prompt trust scores.")
    st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

    with open(BASE_DIR / "reports" / "results.json") as f:
        data = json.load(f)

    df = pd.DataFrame(data)

    category = st.selectbox(
        "Filter by Category",
        ["All"] + sorted(df["category"].unique())
    )

    if category != "All":
        df = df[df["category"] == category]

    for _, row in df.iterrows():

        st.markdown("### Prompt")

        st.write(row["prompt"])

        with st.expander("Model Response"):
            st.write(row["response"])

        st.write("Trust Score:", row["trust_score"])
        st.write("Category:", row["category"])

        st.divider()

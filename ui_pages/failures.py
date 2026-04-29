import sys
from pathlib import Path
import json
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from analytics.failing_prompts import failing_prompt_chart

st.title("🚨 Failure Analysis")

results_path = ROOT / "reports" / "results.json"

if not results_path.exists():
    st.warning("No evaluation results found.")
    st.stop()

with open(results_path) as f:
    data = json.load(f)

df = pd.DataFrame(data)

if df.empty:
    st.warning("Results file is empty.")
    st.stop()

# ---------------- Chart ---------------- #

fig = failing_prompt_chart(df)

if fig:
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No failing prompts detected.")

st.divider()

# ---------------- Table ---------------- #

st.subheader("Low Trust Prompts")

low = df[df["trust_score"] < 0.6]

st.dataframe(low, use_container_width=True)
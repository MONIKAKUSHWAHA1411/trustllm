import streamlit as st
import pandas as pd
import json
from pathlib import Path

st.title("Logs & Traces")

BASE_DIR = Path(__file__).resolve().parents[1]
file_path = BASE_DIR / "reports" / "evaluated_results.json"

with open(file_path) as f:
    data = json.load(f)

df = pd.DataFrame(data)

prompt = st.selectbox("Select Prompt", df["prompt"])

row = df[df["prompt"] == prompt].iloc[0]

st.subheader("Prompt")
st.write(row["prompt"])

st.subheader("Response")
st.write(row["response"])

st.subheader("Evaluation Data")

st.json(row.to_dict())

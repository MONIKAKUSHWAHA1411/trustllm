import streamlit as st
import pandas as pd
import json
from pathlib import Path

st.title("Dataset Explorer")

BASE_DIR = Path(__file__).resolve().parents[1]
file_path = BASE_DIR / "datasets" / "prompts.json"

with open(file_path) as f:
    data = json.load(f)

df = pd.DataFrame(data)

st.dataframe(df)
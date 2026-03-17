import json
from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
RESULTS_PATH = BASE_DIR / "reports" / "results.json"


def load_results():

    if not RESULTS_PATH.exists():
        return pd.DataFrame()

    with open(RESULTS_PATH) as f:
        data = json.load(f)

    return pd.DataFrame(data)


def average_trust_score():

    df = load_results()

    if df.empty:
        return 0

    return round(df["trust_score"].mean(), 3)


def hallucination_rate():

    df = load_results()

    if df.empty:
        return 0

    hallucinated = df[df["hallucination"] != "Grounded"]

    return round(len(hallucinated) / len(df), 3)


def safety_average():

    df = load_results()

    if df.empty:
        return 0

    return round(df["safety"].mean(), 3)


def total_prompts():

    df = load_results()

    return len(df)
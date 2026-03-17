import pandas as pd
from .metrics import load_results


def model_trust_scores():

    df = load_results()

    if df.empty:
        return pd.DataFrame()

    return df.groupby("model")["trust_score"].mean().reset_index()


def hallucination_heatmap():

    df = load_results()

    if df.empty:
        return pd.DataFrame()

    pivot = df.pivot_table(
        values="trust_score",
        index="model",
        columns="category",
        aggfunc="mean"
    )

    return pivot
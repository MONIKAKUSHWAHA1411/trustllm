from .metrics import load_results
from .aggregations import model_trust_scores, hallucination_heatmap


def get_benchmark_data():

    return model_trust_scores()


def get_heatmap_data():

    return hallucination_heatmap()


def get_prompt_failures():

    df = load_results()

    if df.empty:
        return df

    return df[df["trust_score"] < 0.7]
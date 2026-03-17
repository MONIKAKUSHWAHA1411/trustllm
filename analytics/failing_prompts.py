import plotly.express as px


def failing_prompt_chart(df):
    """
    Shows categories where prompts fail most frequently
    """

    failing = df[df["trust_score"] < 0.6]

    if failing.empty:
        return None

    grouped = (
        failing.groupby("category")
        .size()
        .reset_index(name="fail_count")
        .sort_values("fail_count", ascending=False)
    )

    fig = px.bar(
        grouped,
        x="category",
        y="fail_count",
        title="Top Failing Prompt Categories",
        color="fail_count",
        color_continuous_scale="reds"
    )

    fig.update_layout(
        xaxis_title="Prompt Category",
        yaxis_title="Failure Count",
        template="plotly_dark",
        height=400
    )

    return fig
import plotly.express as px


def trust_distribution_chart(df):
    """
    Creates histogram showing distribution of trust scores
    """

    fig = px.histogram(
        df,
        x="trust_score",
        nbins=10,
        title="Trust Score Distribution",
        color_discrete_sequence=["#636EFA"]
    )

    fig.update_layout(
        xaxis_title="Trust Score",
        yaxis_title="Number of Prompts",
        template="plotly_dark",
        height=400
    )

    return fig
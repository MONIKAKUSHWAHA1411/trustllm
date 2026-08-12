#!/usr/bin/env python3
"""Render the publication figures from reports/results.json."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
FIGURES = ROOT / "reports" / "figures"

#: Matchers shown in the figures. The full table is in results.json; plotting
#: all 24 makes every panel unreadable.
FEATURED = [
    "levenshtein",
    "jaro_winkler",
    "token_sort_levenshtein",
    "soundex",
    "double_metaphone",
    "char_embedding_svd",
    "indic_phonetic",
    "indic_phonetic_dravidian",
    "soundex+tiebreak",
    "indic_phonetic+tiebreak",
]

STYLE = {
    "levenshtein": ("#8c8c8c", "-"),
    "jaro_winkler": ("#b0b0b0", "--"),
    "token_sort_levenshtein": ("#6b6b6b", ":"),
    "soundex": ("#d4762a", "-"),
    "double_metaphone": ("#e0a060", "--"),
    "char_embedding_svd": ("#4a7ba7", "-."),
    "indic_phonetic": ("#2a7f5f", "-"),
    "indic_phonetic_dravidian": ("#1a5c42", "-"),
    "soundex+tiebreak": ("#a8442a", (0, (3, 1, 1, 1))),
    "indic_phonetic+tiebreak": ("#0f4030", (0, (3, 1, 1, 1))),
}

FAMILY_ORDER = [
    "transliteration",
    "arabic_persian",
    "bengali_anglicisation",
    "structure",
    "affix",
    "noise",
    "cross_script",
]
FAMILY_LABEL = {
    "transliteration": "Transliteration",
    "arabic_persian": "Arabic/Persian",
    "bengali_anglicisation": "Bengali\nanglicisation",
    "structure": "Structure",
    "affix": "Affix",
    "noise": "Noise\n(control)",
    "cross_script": "Cross-script",
}


def setup(ax, title: str, xlabel: str, ylabel: str) -> None:
    ax.set_title(title, fontsize=12, fontweight="bold", loc="left", pad=12)
    ax.set_xlabel(xlabel, fontsize=10)
    ax.set_ylabel(ylabel, fontsize=10)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="y", alpha=0.25, linewidth=0.6)
    ax.set_axisbelow(True)


def figure_degradation(results: dict) -> None:
    data = results["degradation_recall_at_1pct_fpr"]
    fig, ax = plt.subplots(figsize=(8, 5), dpi=200)
    severities = [1, 2, 3, 4, 5]
    for matcher in FEATURED:
        if matcher not in data:
            continue
        colour, style = STYLE[matcher]
        values = [data[matcher][str(s)] for s in severities]
        ax.plot(
            severities, values, label=matcher, color=colour, linestyle=style,
            marker="o", markersize=4, linewidth=2 if "indic" in matcher else 1.4,
        )
    setup(
        ax,
        "Degradation with transformation severity",
        "Severity (number of stacked transformations)",
        "Recall at 1% false-positive rate",
    )
    ax.set_xticks(severities)
    ax.set_ylim(0, None)
    ax.legend(frameon=False, fontsize=8, ncol=2)
    fig.tight_layout()
    fig.savefig(FIGURES / "degradation_curve.png", bbox_inches="tight")
    plt.close(fig)


def figure_per_family(results: dict) -> None:
    data = results["per_family_recall_at_1pct_fpr"]
    fig, ax = plt.subplots(figsize=(11, 5), dpi=200)
    width = 0.08
    for i, matcher in enumerate(FEATURED):
        if matcher not in data:
            continue
        colour, _ = STYLE[matcher]
        values = [data[matcher].get(f, 0.0) for f in FAMILY_ORDER]
        positions = [x + i * width for x in range(len(FAMILY_ORDER))]
        ax.bar(positions, values, width=width, label=matcher, color=colour)
    setup(
        ax,
        "Which transformation breaks which algorithm",
        "",
        "Recall at 1% false-positive rate",
    )
    offset = width * (len(FEATURED) - 1) / 2
    ax.set_xticks([x + offset for x in range(len(FAMILY_ORDER))])
    ax.set_xticklabels([FAMILY_LABEL[f] for f in FAMILY_ORDER], fontsize=9)
    ax.legend(frameon=False, fontsize=8, ncol=4)
    fig.tight_layout()
    fig.savefig(FIGURES / "per_family_breakdown.png", bbox_inches="tight")
    plt.close(fig)


def figure_alert_volume(results: dict) -> None:
    data = results["alert_volume"]
    fig, ax = plt.subplots(figsize=(8, 5), dpi=200)
    for matcher in FEATURED:
        if matcher not in data:
            continue
        colour, style = STYLE[matcher]
        rows = data[matcher]
        rates = [r["base_rate"] for r in rows]
        hours = [r["analyst_hours_per_100k"] for r in rows]
        ax.plot(
            rates, hours, label=matcher, color=colour, linestyle=style,
            marker="o", markersize=4, linewidth=2 if "indic" in matcher else 1.4,
        )
    ax.set_xscale("log")
    setup(
        ax,
        "Analyst hours per 100,000 names screened",
        "True-match base rate (log scale)",
        "Analyst hours (at 4 min/alert)",
    )
    ax.invert_xaxis()
    ax.legend(frameon=False, fontsize=8, ncol=2)
    fig.text(
        0.01, -0.04,
        "Upper bounds: hard negatives are drawn from the confusable region, not uniformly.",
        fontsize=7, style="italic", color="#666666",
    )
    fig.tight_layout()
    fig.savefig(FIGURES / "alert_volume.png", bbox_inches="tight")
    plt.close(fig)


def figure_fairness(results: dict) -> None:
    fairness = results["fairness"]["matchers"]
    featured = [m for m in ("soundex", "indic_phonetic", "levenshtein") if m in fairness]
    if not featured:
        return

    fig, axes = plt.subplots(
        1, len(featured), figsize=(5 * len(featured), 5), dpi=200, sharey=True
    )
    if len(featured) == 1:
        axes = [axes]

    for ax, matcher in zip(axes, featured, strict=True):
        by_origin = fairness[matcher]["by_origin"]
        origins = sorted(by_origin, key=lambda o: -by_origin[o]["fpr"])
        values = [by_origin[o]["fpr"] for o in origins]
        lows = [by_origin[o]["fpr"] - by_origin[o]["ci95"][0] for o in origins]
        highs = [by_origin[o]["ci95"][1] - by_origin[o]["fpr"] for o in origins]
        colours = [
            "#c1442e" if o == "arabic_persian" else "#7a9cb5" for o in origins
        ]
        ax.barh(range(len(origins)), values, xerr=[lows, highs], color=colours,
                error_kw={"ecolor": "#444444", "elinewidth": 0.8, "capsize": 2})
        ax.set_yticks(range(len(origins)))
        ax.set_yticklabels(origins, fontsize=8)
        ax.set_title(matcher, fontsize=11, fontweight="bold", loc="left")
        ax.set_xlabel("False-positive rate", fontsize=9)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.grid(axis="x", alpha=0.25, linewidth=0.6)
        ax.set_axisbelow(True)

    fig.suptitle(
        "False-positive rate by name-origin at one global threshold",
        fontsize=13, fontweight="bold", x=0.02, ha="left",
    )
    fig.text(
        0.02, -0.02,
        "Origin categories are a proxy for transliteration convention, not for any group identity. "
        "Bars are 95% Wilson intervals.",
        fontsize=7, style="italic", color="#666666",
    )
    fig.tight_layout()
    fig.savefig(FIGURES / "fairness_by_origin.png", bbox_inches="tight")
    plt.close(fig)


def figure_granularity(results: dict) -> None:
    """Recall at both budgets, base vs tie-broken.

    The paired-bar form is deliberate: the story is that the tight-budget bar
    goes from zero to something while the loose-budget bar barely moves.
    """
    rows = results.get("granularity", {}).get("rows", [])
    if not rows:
        return

    bases = [r for r in rows if r["variant"] == "base"]
    labels = [r["matcher"] for r in bases]
    if not labels:
        return

    fig, (ax_tight, ax_loose) = plt.subplots(1, 2, figsize=(11, 4.5), dpi=200)
    width = 0.35
    positions = list(range(len(labels)))

    for ax, key, title, budget in (
        (ax_tight, "recall_at_0.1pct_fpr", "Recall at 0.1% FPR (tight budget)", "0.1%"),
        (ax_loose, "recall_at_1pct_fpr", "Recall at 1% FPR (loose budget)", "1%"),
    ):
        base_values, tie_values = [], []
        for label in labels:
            base_values.append(
                next(r[key] for r in rows if r["matcher"] == label and r["variant"] == "base")
            )
            tie_values.append(
                next(
                    r[key]
                    for r in rows
                    if r["matcher"].startswith(label) and r["variant"] == "tie_broken"
                )
            )
        ax.bar([p - width / 2 for p in positions], base_values, width,
               label="as shipped", color="#b0b0b0")
        ax.bar([p + width / 2 for p in positions], tie_values, width,
               label="+ tie-breaker", color="#2a7f5f")
        for p, value in zip(positions, base_values, strict=True):
            ax.annotate(f"{value:.3f}", (p - width / 2, value), ha="center",
                        va="bottom", fontsize=8, xytext=(0, 2),
                        textcoords="offset points", color="#555555")
        for p, value in zip(positions, tie_values, strict=True):
            ax.annotate(f"{value:.3f}", (p + width / 2, value), ha="center",
                        va="bottom", fontsize=8, fontweight="bold", xytext=(0, 2),
                        textcoords="offset points", color="#1a5c42")
        setup(ax, title, "", "Recall")
        ax.set_xticks(positions)
        ax.set_xticklabels(labels, fontsize=9)
        # Headroom so the legend clears the tallest bar and its label.
        ax.set_ylim(0, max(base_values + tie_values) * 1.35)
        ax.legend(frameon=False, fontsize=8, loc="upper left")

    fig.suptitle(
        "Score granularity, not phonology, causes zero recall at a tight budget",
        fontsize=13, fontweight="bold", x=0.02, ha="left",
    )
    fig.text(
        0.02, -0.03,
        "Tie-breaker is Jaro-Winkler blended at weight 0.15. AUC-PR rises in both cases; "
        "the phonology is unchanged.",
        fontsize=7, style="italic", color="#666666",
    )
    fig.tight_layout()
    fig.savefig(FIGURES / "score_granularity.png", bbox_inches="tight")
    plt.close(fig)


def figure_alias_coverage(results: dict) -> None:
    """Bengali anglicisation recall against alias-table coverage."""
    data = results.get("alias_coverage", {}).get("recall_at_1pct_fpr", {})
    if not data:
        return

    order = [
        ("indic_phonetic", "no alias table", "#b0b0b0"),
        ("indic_phonetic+alias_half", "41% class coverage", "#4a9070"),
        ("indic_phonetic+alias_oracle", "full table\n(UPPER BOUND)", "#c1442e"),
    ]
    families = ["bengali_anglicisation", "arabic_persian", "transliteration"]
    label = {
        "bengali_anglicisation": "Bengali\nanglicisation",
        "arabic_persian": "Arabic/Persian",
        "transliteration": "Transliteration",
    }

    fig, ax = plt.subplots(figsize=(8.5, 5), dpi=200)
    width = 0.26
    for i, (key, legend, colour) in enumerate(order):
        if key not in data:
            continue
        values = [data[key].get(f, 0.0) for f in families]
        ax.bar([x + i * width for x in range(len(families))], values, width,
               label=legend, color=colour)

    setup(ax, "What an alias table is worth", "", "Recall at 1% false-positive rate")
    ax.set_xticks([x + width for x in range(len(families))])
    ax.set_xticklabels([label[f] for f in families], fontsize=9)
    ax.legend(frameon=False, fontsize=8)
    fig.text(
        0.01, -0.05,
        "The full table is the one the corpus was generated from, so it is an upper bound, "
        "not a result.\nCoverage buys recall roughly linearly and nothing transfers to "
        "unlisted variants.",
        fontsize=7, style="italic", color="#666666",
    )
    fig.tight_layout()
    fig.savefig(FIGURES / "alias_coverage.png", bbox_inches="tight")
    plt.close(fig)


def main() -> int:
    path = ROOT / "reports" / "results.json"
    if not path.exists():
        print("run benchmarks/run_all.py first", file=sys.stderr)
        return 1
    results = json.loads(path.read_text())
    FIGURES.mkdir(parents=True, exist_ok=True)

    figure_degradation(results)
    figure_per_family(results)
    figure_alert_volume(results)
    figure_fairness(results)
    figure_granularity(results)
    figure_alias_coverage(results)
    for figure in sorted(FIGURES.glob("*.png")):
        print(f"wrote {figure.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Reproduce every number in reports/findings.md, end to end.

    python benchmarks/run_all.py                 # full run
    python benchmarks/run_all.py --quick         # small corpus, for a smoke test

Everything is a pure function of the config plus the fixed seed, so a rerun on
another machine produces identical numbers. Outputs land in reports/.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections import defaultdict
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from indic_name_bench import __version__, corpus, matchers  # noqa: E402
from indic_name_bench.eval import metrics  # noqa: E402
from indic_name_bench.matchers.cascade import CascadeMatcher, blocking_recall  # noqa: E402
from indic_name_bench.matchers.neural import CharEmbeddingMatcher  # noqa: E402
from indic_name_bench.negatives import DISCRIMINABLE_TYPES  # noqa: E402
from indic_name_bench.seeds.inventory import origin_labels  # noqa: E402

REPORTS = ROOT / "reports"
DISCRIMINABLE = {t.value for t in DISCRIMINABLE_TYPES} | {"easy"}


def headline_pairs(built: corpus.Corpus) -> list[corpus.LabelledPair]:
    """Positives from the degradation split against discriminable negatives.

    identical_collision negatives are excluded: their two sides are the same
    string, so no name-only method separates them at any threshold, and their
    share of the negative set would set a precision ceiling determined by a
    sampling choice rather than by any algorithm. Reported on its own instead.
    """
    positives = built.split("degradation")
    negatives = [p for p in built.split("negatives") if p.subtype in DISCRIMINABLE]
    return positives + negatives


def score_all(
    matcher: matchers.Matcher, pairs: list[corpus.LabelledPair]
) -> tuple[list[float], list[int], matchers.Timing]:
    inputs = [(p.left, p.right) for p in pairs]
    scores, timing = matcher.score_batch(inputs)
    return scores, [p.label for p in pairs], timing


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--quick", action="store_true", help="small corpus for a smoke test")
    parser.add_argument("--out", type=Path, default=REPORTS)
    args = parser.parse_args()

    config = (
        corpus.CorpusConfig(
            n_identities=500,
            family_variants_per_family=250,
            cross_script_variants=200,
            hard_negatives_per_type=400,
            easy_negatives=800,
        )
        if args.quick
        else corpus.CorpusConfig()
    )

    args.out.mkdir(parents=True, exist_ok=True)
    raw = args.out / "raw"
    raw.mkdir(exist_ok=True)

    print(f"indic-name-bench {__version__}")
    print(f"corpus config fingerprint: {config.fingerprint()}")

    started = time.perf_counter()
    built = corpus.build(config)
    print(f"corpus built in {time.perf_counter() - started:.1f}s: {built.summary()}")
    corpus.write(built, ROOT / "data" / "generated" / f"snapshot-v{__version__}")

    all_matchers = matchers.build_all()

    # The character-embedding matcher is unsupervised but must see the
    # vocabulary before it can encode. Fitted on name strings only -- never on
    # pair labels -- and the caveat is carried into the findings.
    vocabulary = sorted({p.left for p in built.all_pairs()} | {p.right for p in built.all_pairs()})
    for matcher in all_matchers:
        if isinstance(matcher, CharEmbeddingMatcher):
            matcher.fit(vocabulary)

    results: dict[str, object] = {
        "version": __version__,
        "config": asdict(config),
        "config_fingerprint": config.fingerprint(),
        "corpus_summary": built.summary(),
        "unavailable_matchers": matchers.unavailable(),
        "assumptions": {
            "minutes_per_alert": metrics.MINUTES_PER_ALERT,
            "alert_volumes_are_upper_bounds": (
                "hard negatives are drawn from the confusable region, not uniformly, "
                "so measured FPR exceeds a uniform draw at the same base rate"
            ),
        },
    }

    headline = headline_pairs(built)
    print(f"\nheadline set: {len(headline)} pairs "
          f"({sum(p.label for p in headline)} positive)")

    # -- headline table ---------------------------------------------------
    headline_rows = []
    cached_scores: dict[str, list[float]] = {}
    for matcher in all_matchers:
        scores, labels, timing = score_all(matcher, headline)
        cached_scores[matcher.name] = scores
        result = metrics.evaluate(
            matcher.name,
            scores,
            labels,
            per_pair_us=timing.per_pair_us,
            pairs_per_second=timing.pairs_per_second,
        )
        row = result.to_row()
        row["cost_class"] = matcher.cost_class.value
        headline_rows.append(row)
        print(
            f"  {matcher.name:40s} AUC-PR {result.auc_pr:.3f}  "
            f"R@1%FPR {result.recall_at_budget[0.01]:.3f}  "
            f"{timing.per_pair_us:7.1f} us/pair"
        )
    results["headline"] = headline_rows

    # -- degradation curve ------------------------------------------------
    by_severity: dict[int, list[corpus.LabelledPair]] = defaultdict(list)
    for pair in built.split("degradation"):
        by_severity[pair.severity].append(pair)
    negatives = [p for p in built.split("negatives") if p.subtype in DISCRIMINABLE]

    degradation: dict[str, dict[int, float]] = {}
    for matcher in all_matchers:
        per_level: dict[int, float] = {}
        for severity in sorted(by_severity):
            subset = by_severity[severity] + negatives
            scores, labels, _ = score_all(matcher, subset)
            curve = metrics.build_curve(scores, labels)
            per_level[severity], _ = metrics.recall_at_fpr(curve, 0.01)
        degradation[matcher.name] = per_level
    results["degradation_recall_at_1pct_fpr"] = degradation

    # -- per-transformation breakdown -------------------------------------
    by_family: dict[str, list[corpus.LabelledPair]] = defaultdict(list)
    for pair in built.split("family"):
        by_family[pair.subtype].append(pair)
    for pair in built.split("cross_script"):
        by_family[pair.subtype].append(pair)

    breakdown: dict[str, dict[str, float]] = {}
    for matcher in all_matchers:
        per_family: dict[str, float] = {}
        for family in sorted(by_family):
            subset = by_family[family] + negatives
            scores, labels, _ = score_all(matcher, subset)
            curve = metrics.build_curve(scores, labels)
            per_family[family], _ = metrics.recall_at_fpr(curve, 0.01)
        breakdown[matcher.name] = per_family
    results["per_family_recall_at_1pct_fpr"] = breakdown

    # -- hard-negative breakdown ------------------------------------------
    positives = built.split("degradation")
    negative_types: dict[str, dict[str, float]] = {}
    for matcher in all_matchers:
        per_type: dict[str, float] = {}
        for subtype in sorted({p.subtype for p in built.split("negatives")}):
            subset = positives + [
                p for p in built.split("negatives") if p.subtype == subtype
            ]
            scores, labels, _ = score_all(matcher, subset)
            curve = metrics.build_curve(scores, labels)
            per_type[subtype], _ = metrics.recall_at_fpr(curve, 0.01)
        negative_types[matcher.name] = per_type
    results["recall_by_negative_type"] = negative_types

    # -- alert volume ------------------------------------------------------
    volumes: dict[str, list[dict[str, object]]] = {}
    for matcher in all_matchers:
        curve = metrics.build_curve(
            cached_scores[matcher.name], [p.label for p in headline]
        )
        rows = []
        for base_rate in metrics.BASE_RATES:
            volume = metrics.alert_volume(curve, 0.01, base_rate)
            rows.append(
                {
                    "base_rate": base_rate,
                    "recall": round(volume.recall, 4),
                    "fpr": round(volume.fpr, 5),
                    "alerts_per_100k": round(volume.alerts, 1),
                    "precision": round(volume.precision, 6),
                    "analyst_hours_per_100k": round(volume.analyst_hours, 1),
                }
            )
        volumes[matcher.name] = rows
    results["alert_volume"] = volumes

    # -- threshold stability by origin -------------------------------------
    stability: dict[str, dict[str, float]] = {}
    for matcher in all_matchers:
        per_origin: dict[str, float] = {}
        for origin in sorted(origin_labels()):
            subset = [
                p
                for p in headline
                if p.origin_left == origin and (p.label == 1 or p.origin_right == origin)
            ]
            if sum(p.label for p in subset) < 20 or (len(subset) - sum(p.label for p in subset)) < 20:
                continue
            scores, labels, _ = score_all(matcher, subset)
            curve = metrics.build_curve(scores, labels)
            _, threshold = metrics.recall_at_fpr(curve, 0.01)
            per_origin[origin] = round(threshold, 4)
        stability[matcher.name] = per_origin
    results["optimal_threshold_by_origin"] = stability

    # -- fairness: FPR by origin at a single global threshold ---------------
    fairness = run_fairness(all_matchers, built, headline, cached_scores)
    results["fairness"] = fairness

    # -- cascade cost -------------------------------------------------------
    cascade_rows = []
    for matcher in all_matchers:
        if isinstance(matcher, CascadeMatcher):
            recall_ceiling = blocking_recall(
                matcher.blocker,
                [(p.left, p.right) for p in headline],
                [p.label for p in headline],
                matcher.block_threshold,
            )
            cascade_rows.append(
                {
                    "cascade": matcher.name,
                    "block_threshold": matcher.block_threshold,
                    "blocking_recall_ceiling": round(recall_ceiling, 4),
                    "fraction_reranked": round(matcher.stats.rerank_fraction, 4),
                }
            )
    results["cascade"] = cascade_rows

    # -- experiment: score granularity --------------------------------------
    results["granularity"] = run_granularity(all_matchers, headline)

    # -- experiment: alias-table coverage -----------------------------------
    results["alias_coverage"] = run_alias(all_matchers, by_family, negatives)

    (args.out / "results.json").write_text(
        json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"\nwrote {args.out / 'results.json'}")
    return 0


def run_granularity(all_matchers, headline) -> dict[str, object]:
    """Is the zero at a 0.1% FPR budget a phonology failure or a tuning artefact?

    Reports, for each coarse matcher and its tie-broken counterpart: how many
    distinct scores it emits, and recall at both budgets. If granularity is the
    cause, the tie-broken variant recovers the tight-budget region while its
    1%-budget recall stays roughly flat -- the phonology is untouched, only the
    number of available operating points changes.
    """
    from indic_name_bench.matchers.granularity import TieBrokenMatcher, distinct_score_count

    inputs = [(p.left, p.right) for p in headline]
    labels = [p.label for p in headline]
    by_name = {m.name: m for m in all_matchers}

    rows = []
    for matcher in all_matchers:
        if not isinstance(matcher, TieBrokenMatcher):
            continue
        base = by_name.get(matcher.base.name) or matcher.base
        for label, candidate in (("base", base), ("tie_broken", matcher)):
            scores, timing = candidate.score_batch(inputs)
            curve = metrics.build_curve(scores, labels)
            tight, _ = metrics.recall_at_fpr(curve, 0.001)
            loose, _ = metrics.recall_at_fpr(curve, 0.01)
            rows.append(
                {
                    "matcher": candidate.name,
                    "variant": label,
                    "distinct_scores": distinct_score_count(candidate, inputs),
                    "recall_at_0.1pct_fpr": round(tight, 4),
                    "recall_at_1pct_fpr": round(loose, 4),
                    "auc_pr": round(metrics.auc_pr(scores, labels), 4),
                    "per_pair_us": round(timing.per_pair_us, 2),
                }
            )
    return {
        "note": (
            "A matcher emitting N distinct scores has N available operating points. "
            "If none sits under the budget, recall there is zero regardless of "
            "matching quality. Blending weight is 0.15 -- enough to order within a "
            "tie group, not enough to relitigate the phonetic decision."
        ),
        "rows": rows,
    }


def run_alias(all_matchers, by_family, negatives) -> dict[str, object]:
    """What is an alias table worth, and does it generalise?

    ``alias_oracle`` shares its table with the generator, so its numbers are an
    upper bound and not a generalisation result. ``alias_half`` holds out 50% of
    the classes. If half-coverage lands near halfway between baseline and
    oracle, performance scales with coverage and nothing generalises -- an alias
    table helps only for the names already in it.
    """
    from indic_name_bench.matchers.alias import coverage_summary

    tracked = [
        m
        for m in all_matchers
        if m.name
        in {
            "indic_phonetic",
            "indic_phonetic+alias_half",
            "indic_phonetic+alias_oracle",
            "alias_exact",
            "soundex",
        }
    ]
    families = ["bengali_anglicisation", "arabic_persian", "transliteration"]

    table: dict[str, dict[str, float]] = {}
    for matcher in tracked:
        per_family: dict[str, float] = {}
        for family in families:
            subset = by_family.get(family, []) + negatives
            if not subset:
                continue
            scores, labels, _ = score_all(matcher, subset)
            curve = metrics.build_curve(scores, labels)
            per_family[family], _ = metrics.recall_at_fpr(curve, 0.01)
        table[matcher.name] = {k: round(v, 4) for k, v in per_family.items()}

    return {
        "coverage": coverage_summary(),
        "caveat": (
            "alias_oracle uses the same equivalence tables the corpus was generated "
            "from. It is an upper bound on what a complete alias list achieves, not "
            "a generalisation result, and must not be cited as matcher performance. "
            "alias_half holds out 50% of classes and is the deployable comparison."
        ),
        "recall_at_1pct_fpr": table,
    }


def run_fairness(
    all_matchers, built, headline, cached_scores
) -> dict[str, object]:
    """False-positive rate by name-origin at one global threshold.

    A single global threshold is the point: production systems set one, and if
    it is mis-calibrated per community then some groups absorb more false
    positives than others through a purely technical mechanism. Using a
    per-origin optimal threshold would hide exactly the effect being tested.
    """
    out: dict[str, object] = {
        "caveats": [
            "Origin categories are a proxy for transliteration convention, not "
            "ethnicity, religion or nationality.",
            "Frequency tiers in the seed inventory are hand-assigned ordinal "
            "judgements, not measured; the disparity magnitudes depend on them.",
            "Synthetic variant distributions may not match real record distributions.",
            "Identities whose surname appears under several origins are flagged "
            "origin_ambiguous and counted separately below.",
        ],
        "matchers": {},
    }

    labels = [p.label for p in headline]
    for matcher in all_matchers:
        scores = cached_scores[matcher.name]
        curve = metrics.build_curve(scores, labels)
        _, threshold = metrics.recall_at_fpr(curve, 0.01)

        per_origin: dict[str, dict[str, object]] = {}
        for origin in sorted(origin_labels()):
            false_positives = 0
            total_negatives = 0
            for pair, score in zip(headline, scores, strict=True):
                if pair.label != 0:
                    continue
                if pair.origin_left != origin:
                    continue
                total_negatives += 1
                if score >= threshold:
                    false_positives += 1
            if total_negatives < 30:
                continue
            rate = false_positives / total_negatives
            low, high = metrics.wilson_interval(false_positives, total_negatives)
            per_origin[origin] = {
                "fpr": round(rate, 5),
                "ci95": [round(low, 5), round(high, 5)],
                "false_positives": false_positives,
                "negatives": total_negatives,
            }

        # Disparity is measured against the POOLED rate across all origins, not
        # against the lowest-FPR origin. Several origins score exactly zero at
        # a 1% budget, and a zero denominator makes every ratio infinite or
        # undefined -- the first version of this reported `null` for almost
        # every cell. The pooled reference is well defined regardless and is
        # the standard framing for a disparate-impact ratio.
        pooled_fp = sum(s["false_positives"] for s in per_origin.values())
        pooled_n = sum(s["negatives"] for s in per_origin.values())
        pooled_rate = pooled_fp / pooled_n if pooled_n else 0.0

        for stats in per_origin.values():
            ratio, interval = metrics.disparity_ratio(
                stats["fpr"],
                stats["false_positives"],
                stats["negatives"],
                pooled_rate,
                pooled_fp,
                pooled_n,
            )
            stats["disparity_vs_pooled"] = (
                round(ratio, 3) if ratio != float("inf") else None
            )
            stats["disparity_ci95"] = [
                round(interval[0], 3),
                round(interval[1], 3) if interval[1] != float("inf") else None,
            ]

        out["matchers"][matcher.name] = {
            "global_threshold": round(threshold, 4),
            "pooled_fpr": round(pooled_rate, 5),
            "by_origin": per_origin,
        }

    ambiguous = sum(1 for i in built.identities if i.origin_ambiguous)
    out["origin_ambiguous_identities"] = {
        "count": ambiguous,
        "fraction": round(ambiguous / len(built.identities), 4),
    }
    return out


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Which encoder stage carries the signal, and which rule does it defend against?

Where this comes from
---------------------
Findings §11 narrowed the contribution from "an Indic encoder beats Soundex" to
"the voicing merge beats Soundex". That is still a claim about a *family* of
design choices tested as a bundle. The encoder makes seven separable decisions,
and the family-level result cannot say which of them do anything.

Two analyses, both paired across corpus seeds:

**Stage ablation.** Disable exactly one stage, hold the rest fixed, measure the
drop against the full encoder on the transliteration split. A stage that costs
nothing when removed is not contributing — it is decoration, and saying so is
more useful than leaving it in the methodology as though it earned its place.

**Per-rule attribution.** The corpus records the exact `rule_id` behind every
variant, and nothing has ever grouped by it. Restricting to severity-1
single-family variants gives one rule per pair, so recall can be attributed to
individual transformations rather than families. Crossing that with the stage
ablations answers the sharp question: *`unify_ksha_x` should defend against
`ksha_to_x` and nothing else — does it?*

A stage that helps everywhere equally is doing something other than what its
docstring claims.
"""

from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from indic_name_bench import corpus  # noqa: E402
from indic_name_bench.eval import metrics  # noqa: E402
from indic_name_bench.matchers.indic import (  # noqa: E402
    ABLATIONS,
    DRAVIDIAN,
    FULL,
    IndicPhoneticMatcher,
)
from indic_name_bench.negatives import DISCRIMINABLE_TYPES  # noqa: E402

DISCRIMINABLE = {t.value for t in DISCRIMINABLE_TYPES} | {"easy"}
BUDGET = 0.01


def t_critical(df: int) -> float:
    table = {
        1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571, 6: 2.447, 7: 2.365,
        8: 2.306, 9: 2.262, 10: 2.228, 11: 2.201, 12: 2.179, 13: 2.160, 14: 2.145,
    }
    return table.get(df, 1.96 if df > 30 else 2.145)


def matcher_for(config) -> IndicPhoneticMatcher:
    """An IndicPhoneticMatcher whose encoder runs under ``config``.

    The comparison strategy is held constant across every ablation: only the
    encoder changes. Otherwise a stage's apparent contribution would be
    confounded with the alignment layer.
    """
    matcher = IndicPhoneticMatcher(merge_voicing=config.merge_voicing)
    matcher._ablation = config  # noqa: SLF001 - test harness hook
    matcher.name = f"indic[{config.label}]"

    from indic_name_bench.matchers.indic import encode_with

    def scoped_encode(token: str, *, merge_voicing: bool = False) -> str:
        return encode_with(token, config)

    matcher._encode_override = scoped_encode  # noqa: SLF001
    return matcher


def score_split(matcher, pairs, config):
    """Score pairs with the encoder pinned to ``config``."""
    from indic_name_bench.matchers import indic as indic_module

    original = indic_module.encode_token
    indic_module.encode_token = lambda token, *, merge_voicing=False: (
        indic_module.encode_with(token, config)
    )
    try:
        scores, _ = matcher.score_batch([(p.left, p.right) for p in pairs])
    finally:
        indic_module.encode_token = original
    return scores


def recall_for(matcher, config, pairs, negatives) -> float:
    subset = pairs + negatives
    scores = score_split(matcher, subset, config)
    curve = metrics.build_curve(scores, [p.label for p in subset])
    recall, _ = metrics.recall_at_fpr(curve, BUDGET)
    return recall


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", type=int, default=8)
    parser.add_argument("--identities", type=int, default=2000)
    parser.add_argument(
        "--family-variants", type=int, default=400,
        help="variants per family. Raise to fill the per-rule table: the split "
             "spreads these over 3 severities and 19 transliteration rules, so "
             "400 leaves most per-rule cells below the minimum.",
    )
    parser.add_argument("--min-rule-pairs", type=int, default=25)
    parser.add_argument("--out", type=Path, default=ROOT / "reports")
    args = parser.parse_args()

    per_seed_stage: list[dict[str, float]] = []
    per_rule: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))

    for i in range(args.seeds):
        config = corpus.CorpusConfig(
            seed=20260811 + i * 7919,
            n_identities=args.identities,
            family_variants_per_family=args.family_variants,
            cross_script_variants=60,
            hard_negatives_per_type=500,
            easy_negatives=1000,
        )
        built = corpus.build(config)
        negatives = [p for p in built.split("negatives") if p.subtype in DISCRIMINABLE]
        translit = [p for p in built.split("family") if p.subtype == "transliteration"]

        # Severity-1 single-family variants: exactly one rule fired, so recall
        # is attributable to that rule and not to a co-occurring one.
        by_rule: dict[str, list] = defaultdict(list)
        for pair in built.split("family"):
            if pair.severity == 1 and "|" not in pair.rule_ids and pair.rule_ids:
                by_rule[pair.rule_ids].append(pair)

        stage_row: dict[str, float] = {}
        for cfg in ABLATIONS:
            matcher = IndicPhoneticMatcher(merge_voicing=cfg.merge_voicing)
            stage_row[cfg.label] = recall_for(matcher, cfg, translit, negatives)
            # Negative scores depend only on the config, so score them once per
            # config instead of once per rule. Without this the negatives are
            # re-scored 19 times per config and dominate the runtime.
            negative_scores = score_split(matcher, negatives, cfg)
            for rule, pairs in by_rule.items():
                if len(pairs) < args.min_rule_pairs:
                    continue
                positive_scores = score_split(matcher, pairs, cfg)
                curve = metrics.build_curve(
                    positive_scores + negative_scores,
                    [p.label for p in pairs] + [p.label for p in negatives],
                )
                recall, _ = metrics.recall_at_fpr(curve, BUDGET)
                per_rule[cfg.label][rule].append(recall)
        per_seed_stage.append(stage_row)
        print(f"  seed {i + 1}/{args.seeds}", end="\r")
    print()

    # -- stage ablation, paired against the full encoder --------------------
    print(f"{'stage disabled':30s} {'recall':>8s} {'delta vs full':>14s} {'95% CI':>20s}  verdict")
    stages = []
    full_values = [row["full"] for row in per_seed_stage]
    full_mean = statistics.fmean(full_values)
    print(f"{'(none: full encoder)':30s} {full_mean:8.4f}")

    for cfg in ABLATIONS:
        if cfg == FULL:
            continue
        values = [row[cfg.label] for row in per_seed_stage]
        deltas = [row[cfg.label] - row["full"] for row in per_seed_stage]
        mean = statistics.fmean(deltas)
        sd = statistics.stdev(deltas) if len(deltas) > 1 else 0.0
        half = t_critical(len(deltas) - 1) * sd / math.sqrt(len(deltas))
        low, high = mean - half, mean + half
        significant = low > 0 or high < 0

        if not significant:
            verdict = "NO CONTRIBUTION"
        elif cfg == DRAVIDIAN:
            verdict = "helps" if mean > 0 else "hurts"
        else:
            verdict = "contributes" if mean < 0 else "HURTS (removing helps)"

        print(
            f"{cfg.label:30s} {statistics.fmean(values):8.4f} {mean:+14.4f}"
            f"  [{low:+.4f},{high:+.4f}]  {verdict}"
        )
        stages.append({
            "config": cfg.label,
            "recall_mean": round(statistics.fmean(values), 4),
            "delta_vs_full": round(mean, 5),
            "ci95": [round(low, 5), round(high, 5)],
            "significant": significant,
            "verdict": verdict,
        })

    # -- per-rule attribution ----------------------------------------------
    rules = sorted(per_rule["full"])
    print(f"\nper-rule recall at {BUDGET:g} FPR (severity-1, one rule per pair)")
    header = f"{'rule':30s}" + "".join(f"{c.label[:11]:>12s}" for c in ABLATIONS)
    print(header)
    rule_table: dict[str, dict[str, float]] = {}
    for rule in rules:
        row = {}
        cells = ""
        for cfg in ABLATIONS:
            values = per_rule[cfg.label].get(rule, [])
            value = statistics.fmean(values) if values else float("nan")
            row[cfg.label] = round(value, 4) if values else None
            cells += f"{value:12.3f}" if values else f"{'-':>12s}"
        print(f"{rule[:30]:30s}{cells}")
        rule_table[rule] = row

    # -- the sharp test of section 12.2 ------------------------------------
    # Does unify_ksha_x help on the transformation it exists for, even though it
    # hurts overall? If yes, the rule works locally and its collateral damage
    # exceeds its benefit -- a far more precise statement than "it is harmful".
    local = {}
    for rule in ("ksha_to_x", "x_to_ksha"):
        with_rule = per_rule["full"].get(rule, [])
        without = per_rule["no_unify_ksha_x"].get(rule, [])
        if not with_rule or len(with_rule) != len(without):
            continue
        deltas = [a - b for a, b in zip(with_rule, without, strict=True)]
        mean = statistics.fmean(deltas)
        sd = statistics.stdev(deltas) if len(deltas) > 1 else 0.0
        half = t_critical(len(deltas) - 1) * sd / math.sqrt(len(deltas)) if sd else 0.0
        local[rule] = {
            "recall_with_rule": round(statistics.fmean(with_rule), 4),
            "recall_without_rule": round(statistics.fmean(without), 4),
            "delta": round(mean, 5),
            "ci95": [round(mean - half, 5), round(mean + half, 5)],
            "n_seeds": len(deltas),
        }
    if local:
        print("\nsection 12.2 sharp test -- ksha/x rule on the rules it targets")
        for rule, row in local.items():
            print(
                f"  {rule:14s} with={row['recall_with_rule']:.3f} "
                f"without={row['recall_without_rule']:.3f} "
                f"delta={row['delta']:+.4f} [{row['ci95'][0]:+.4f},{row['ci95'][1]:+.4f}]"
            )

    payload = {
        "seeds": args.seeds,
        "min_rule_pairs": args.min_rule_pairs,
        "family_variants_per_family": args.family_variants,
        "ksha_x_local_effect": local,
        "identities_per_seed": args.identities,
        "fpr_budget": BUDGET,
        "method": (
            "Stage ablation: disable exactly one encoder stage, hold the "
            "comparison strategy fixed, paired per-seed delta against the full "
            "encoder on the transliteration split. Per-rule: severity-1 "
            "single-family variants, so exactly one rule fired per pair."
        ),
        "full_encoder_recall": round(full_mean, 4),
        "stages": stages,
        "per_rule_recall": rule_table,
    }
    path = args.out / "ablation.json"
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"\nwrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Are the reported differences real, or within corpus-sampling noise?

The defect this fixes
---------------------
Every number in `reports/findings.md` came from a single corpus draw and was
reported to three decimals with no error bar. Several headline claims rest on
gaps small enough that they might be noise:

    indic_phonetic  0.789  vs  soundex  0.783   on transliteration  (+0.6 pt)
    indic_dravidian 0.357  vs  soundex  0.355   on the headline set (+0.2 pt)

Stating a 0.6-point lead as a win, from one sample, is not defensible. This
script settles each comparison instead of caveating it.

Why paired, and why not overlapping CIs
---------------------------------------
The tempting approach — put a CI on each matcher's recall and check whether they
overlap — is the wrong test, and it is wrong in the conservative direction. All
matchers are scored on the *same* corpus in each replicate, so their errors are
strongly positively correlated: a seed that happens to produce hard variants
lowers every matcher together. Marginal CIs absorb that shared corpus variance,
so they are wide and overlap even when one method reliably beats another.

The decision-relevant quantity is the **paired difference**: for each seed,
compute delta = A - B, then put a CI on the deltas. Shared corpus variance
cancels. A comparison is called significant when that CI excludes zero, with a
sign test as a distribution-free cross-check.

Interpretation limits, stated up front
--------------------------------------
This quantifies variance from **corpus sampling only** — the seed controls which
identities are assembled and which transformations fire. It does not capture
uncertainty in the inventory itself, the hand-assigned frequency tiers, or the
rule set. Those are systematic and a resampling procedure cannot see them; see
`tier_sensitivity.py` for the tier component and findings §10 for the rest.

So a "significant" verdict here means "not explained by which names happened to
be drawn". It does not mean "would replicate on real records".
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

from indic_name_bench import corpus, matchers  # noqa: E402
from indic_name_bench.eval import metrics  # noqa: E402
from indic_name_bench.negatives import DISCRIMINABLE_TYPES  # noqa: E402

DISCRIMINABLE = {t.value for t in DISCRIMINABLE_TYPES} | {"easy"}

#: Matchers whose reported numbers carry a load-bearing claim.
TRACKED = (
    "levenshtein",
    "jaro_winkler",
    "soundex",
    "indic_phonetic",
    "indic_phonetic_dravidian",
    "indic_phonetic+tiebreak",
    "soundex+tiebreak",
)

#: Claims from findings.md, as (label, matcher_a, matcher_b, split, budget).
#: A positive delta means A beats B.
CLAIMS = (
    ("Indic vs Soundex on transliteration",
     "indic_phonetic", "soundex", "transliteration", 0.01),
    ("Indic-dravidian vs Soundex on transliteration",
     "indic_phonetic_dravidian", "soundex", "transliteration", 0.01),
    ("Indic-dravidian vs Soundex on headline",
     "indic_phonetic_dravidian", "soundex", "headline", 0.01),
    ("Indic vs Soundex on headline",
     "indic_phonetic", "soundex", "headline", 0.01),
    ("Voicing merge helps on transliteration",
     "indic_phonetic_dravidian", "indic_phonetic", "transliteration", 0.01),
    ("Tie-break recovers the 0.1% budget (Indic)",
     "indic_phonetic+tiebreak", "indic_phonetic", "headline", 0.001),
    ("Tie-break recovers the 0.1% budget (Soundex)",
     "soundex+tiebreak", "soundex", "headline", 0.001),
    ("Tie-break costs little at the 1% budget (Indic)",
     "indic_phonetic+tiebreak", "indic_phonetic", "headline", 0.01),
    ("Indic beats Levenshtein on transliteration",
     "indic_phonetic", "levenshtein", "transliteration", 0.01),
    ("Indic beats Jaro-Winkler on transliteration",
     "indic_phonetic", "jaro_winkler", "transliteration", 0.01),
)


def t_critical(df: int) -> float:
    """Two-sided 95% t critical value.

    Table lookup rather than scipy: scipy is an optional extra and this script
    must run with the core install.
    """
    table = {
        1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571, 6: 2.447, 7: 2.365,
        8: 2.306, 9: 2.262, 10: 2.228, 11: 2.201, 12: 2.179, 13: 2.160,
        14: 2.145, 15: 2.131, 16: 2.120, 17: 2.110, 18: 2.101, 19: 2.093,
        20: 2.086, 25: 2.060, 30: 2.042,
    }
    if df in table:
        return table[df]
    if df > 30:
        return 1.96
    return table[max(k for k in table if k <= df)]


def sign_test_p(positive: int, total: int) -> float:
    """Two-sided exact binomial p under H0: P(A > B) = 0.5."""
    if total == 0:
        return 1.0
    extreme = min(positive, total - positive)
    tail = sum(math.comb(total, k) for k in range(extreme + 1)) / (2**total)
    return min(1.0, 2 * tail)


def evaluate_seed(seed: int, identities: int, active) -> dict[tuple[str, str, float], float]:
    """Recall at each budget, per matcher, per split, for one corpus seed."""
    config = corpus.CorpusConfig(
        seed=seed,
        n_identities=identities,
        family_variants_per_family=350,
        cross_script_variants=100,
        hard_negatives_per_type=600,
        easy_negatives=1200,
    )
    built = corpus.build(config)
    negatives = [p for p in built.split("negatives") if p.subtype in DISCRIMINABLE]

    splits = {
        "headline": built.split("degradation") + negatives,
        "transliteration": [
            p for p in built.split("family") if p.subtype == "transliteration"
        ] + negatives,
    }

    out: dict[tuple[str, str, float], float] = {}
    for split_name, pairs in splits.items():
        inputs = [(p.left, p.right) for p in pairs]
        labels = [p.label for p in pairs]
        for name, matcher in active.items():
            scores, _ = matcher.score_batch(inputs)
            curve = metrics.build_curve(scores, labels)
            for budget in (0.001, 0.01):
                recall, _ = metrics.recall_at_fpr(curve, budget)
                out[(name, split_name, budget)] = recall
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", type=int, default=15)
    parser.add_argument("--identities", type=int, default=2500)
    parser.add_argument("--out", type=Path, default=ROOT / "reports")
    args = parser.parse_args()

    built = matchers.build_all()
    active = {m.name: m for m in built if m.name in TRACKED}
    missing = set(TRACKED) - set(active)
    if missing:
        print(f"warning: not available in this environment: {sorted(missing)}")

    # The char-embedding matcher is excluded from TRACKED, so no fitting needed.
    per_seed: list[dict] = []
    for i in range(args.seeds):
        seed = 20260811 + i * 7919  # coprime stride, so seeds do not collide
        per_seed.append(evaluate_seed(seed, args.identities, active))
        print(f"  seed {i + 1}/{args.seeds}", end="\r")
    print()

    # Marginal spread per matcher, for reference.
    marginal: dict[str, dict] = defaultdict(dict)
    for name in active:
        for split in ("headline", "transliteration"):
            for budget in (0.001, 0.01):
                values = [s[(name, split, budget)] for s in per_seed]
                mean = statistics.fmean(values)
                sd = statistics.stdev(values) if len(values) > 1 else 0.0
                half = t_critical(len(values) - 1) * sd / math.sqrt(len(values))
                marginal[name][f"{split}@{budget:g}"] = {
                    "mean": round(mean, 4),
                    "sd": round(sd, 4),
                    "ci95": [round(mean - half, 4), round(mean + half, 4)],
                }

    verdicts = []
    print(f"{'claim':46s} {'delta':>8s} {'95% CI on delta':>20s} {'sign':>7s}  verdict")
    for label, a, b, split, budget in CLAIMS:
        if a not in active or b not in active:
            continue
        deltas = [s[(a, split, budget)] - s[(b, split, budget)] for s in per_seed]
        mean = statistics.fmean(deltas)
        sd = statistics.stdev(deltas) if len(deltas) > 1 else 0.0
        half = t_critical(len(deltas) - 1) * sd / math.sqrt(len(deltas))
        low, high = mean - half, mean + half
        positive = sum(1 for d in deltas if d > 0)
        p = sign_test_p(positive, sum(1 for d in deltas if d != 0))

        significant = (low > 0 or high < 0) and p < 0.05
        if significant:
            verdict = "REAL" if mean > 0 else "REAL (reversed)"
        elif abs(mean) < 0.01:
            verdict = "no difference"
        else:
            verdict = "NOT ESTABLISHED"

        print(
            f"{label:46s} {mean:+8.4f}  [{low:+.4f},{high:+.4f}]"
            f"  {positive:2d}/{len(deltas):<3d}  {verdict}"
        )
        verdicts.append({
            "claim": label, "a": a, "b": b, "split": split, "fpr_budget": budget,
            "mean_delta": round(mean, 5), "sd": round(sd, 5),
            "ci95": [round(low, 5), round(high, 5)],
            "seeds_favouring_a": positive, "n_seeds": len(deltas),
            "sign_test_p": round(p, 5), "significant": significant,
            "verdict": verdict,
        })

    payload = {
        "seeds": args.seeds,
        "identities_per_seed": args.identities,
        "method": (
            "Paired per-seed differences. All matchers score the same corpus in "
            "each replicate, so shared corpus variance cancels in the delta. "
            "Comparing overlapping marginal CIs would be the wrong test and "
            "would be conservative."
        ),
        "scope": (
            "Captures corpus-sampling variance only -- which identities are "
            "assembled and which transformations fire. Does NOT capture "
            "uncertainty in the inventory, the hand-assigned frequency tiers, or "
            "the rule set. Those are systematic; see tier_sensitivity.py."
        ),
        "marginal": marginal,
        "claims": verdicts,
    }
    path = args.out / "significance.json"
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"\nwrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Does the fairness finding survive the frequency tiers being wrong?

The problem
-----------
`reports/findings.md` §6 reports that at a single global threshold, Telugu names
absorb 6.27x the pooled false-positive rate while Arabic/Persian sit at 0.39x --
the opposite of the hypothesised direction. §6.3 then says, honestly, that the
pattern is substantially downstream of frequency tiers I hand-assigned rather
than measured.

That caveat is correct but useless on its own. A reader cannot tell whether the
finding is robust to tier error or entirely manufactured by it.

What this does
--------------
Rather than assert the tiers are right, perturb them and see what survives.
Three regimes, each re-running corpus generation and the fairness analysis
end to end:

``declared``
    The tiers as written. The baseline.

``shuffled``
    Tier labels permuted *within each origin*. The tier distribution per origin
    is preserved exactly -- the same number of tier-1 surnames -- but which
    specific names are common is randomised. This targets the actual worry: not
    that I got the shape wrong, but that I assigned the wrong names to it.

``uniform``
    Every component tier 1, so sampling is flat and there is no frequency
    structure at all. The extreme case, included to show what the disparity
    looks like when the mechanism under suspicion is removed entirely.

How to read the output
----------------------
If Telugu stays at the top across shuffled trials, the disparity is a property
of the *inventory's structure* -- how many distinct surnames each origin has to
draw on -- and not of my tier judgements, because those were scrambled. That
would make the finding considerably more defensible.

If the ordering scrambles along with the tiers, then §6 is measuring my guesses
and should be withdrawn to a statement about global thresholds in general.

Either result is worth having, and the second is the one worth being afraid of.
"""

from __future__ import annotations

import argparse
import json
import random
import statistics
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from indic_name_bench import corpus, matchers  # noqa: E402
from indic_name_bench.eval import metrics  # noqa: E402
from indic_name_bench.matchers.indic import IndicPhoneticMatcher  # noqa: E402
from indic_name_bench.matchers.phonetic import build as build_phonetic  # noqa: E402
from indic_name_bench.negatives import DISCRIMINABLE_TYPES  # noqa: E402
from indic_name_bench.seeds import inventory  # noqa: E402

DISCRIMINABLE = {t.value for t in DISCRIMINABLE_TYPES} | {"easy"}


def shuffled_tiers(rng: random.Random) -> dict[tuple[str, str, str], int]:
    """Permute tier labels within each (origin, kind) group.

    Preserves each group's tier histogram exactly while randomising which name
    holds which tier. That is the perturbation matching the actual uncertainty:
    the shape of the distribution is a reasonable guess, the per-name
    assignments are the part I could not verify.
    """
    grouped: dict[tuple[str, str], list] = defaultdict(list)
    for component in inventory.load_components():
        grouped[(component.origin, component.kind)].append(component)

    override: dict[tuple[str, str, str], int] = {}
    for components in grouped.values():
        tiers = [c.tier for c in components]
        rng.shuffle(tiers)
        for component, tier in zip(components, tiers, strict=True):
            override[(component.form.lower(), component.kind, component.origin)] = tier
    return override


def uniform_tiers() -> dict[tuple[str, str, str], int]:
    return {
        (c.form.lower(), c.kind, c.origin): 1 for c in inventory.load_components()
    }


def fairness_once(config: corpus.CorpusConfig, matcher) -> dict[str, float]:
    """Per-origin false-positive rate at one global threshold."""
    built = corpus.build(config)
    headline = built.split("degradation") + [
        p for p in built.split("negatives") if p.subtype in DISCRIMINABLE
    ]
    scores, _ = matcher.score_batch([(p.left, p.right) for p in headline])
    labels = [p.label for p in headline]

    curve = metrics.build_curve(scores, labels)
    _, threshold = metrics.recall_at_fpr(curve, 0.01)

    false_positives: dict[str, int] = defaultdict(int)
    totals: dict[str, int] = defaultdict(int)
    for pair, score in zip(headline, scores, strict=True):
        if pair.label != 0:
            continue
        totals[pair.origin_left] += 1
        if score >= threshold:
            false_positives[pair.origin_left] += 1

    return {
        origin: false_positives[origin] / total
        for origin, total in totals.items()
        if total >= 30
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trials", type=int, default=12, help="shuffled trials")
    parser.add_argument("--identities", type=int, default=1200)
    parser.add_argument("--out", type=Path, default=ROOT / "reports")
    args = parser.parse_args()

    config = corpus.CorpusConfig(
        n_identities=args.identities,
        family_variants_per_family=200,
        cross_script_variants=100,
        hard_negatives_per_type=500,
        easy_negatives=1000,
    )
    matcher = IndicPhoneticMatcher()
    soundex = next((m for m in build_phonetic() if m.name == "soundex"), matcher)

    results: dict[str, object] = {
        "trials": args.trials,
        "identities": args.identities,
        "question": (
            "Does the per-origin false-positive disparity survive the "
            "hand-assigned frequency tiers being scrambled?"
        ),
    }

    for label, name, active in (
        ("indic_phonetic", "indic_phonetic", matcher),
        ("soundex", "soundex", soundex),
    ):
        print(f"\n=== {name} ===")

        inventory.clear_tier_override()
        declared = fairness_once(config, active)
        ranked = sorted(declared, key=lambda o: -declared[o])
        print(f"  declared tiers  top={ranked[0]} ({declared[ranked[0]]:.4f})")

        per_origin: dict[str, list[float]] = defaultdict(list)
        top_counts: dict[str, int] = defaultdict(int)
        for trial in range(args.trials):
            inventory.set_tier_override(shuffled_tiers(random.Random(9000 + trial)))
            rates = fairness_once(config, active)
            for origin, rate in rates.items():
                per_origin[origin].append(rate)
            if rates:
                top_counts[max(rates, key=lambda o: rates[o])] += 1
            print(f"  shuffled trial {trial + 1}/{args.trials}", end="\r")

        inventory.set_tier_override(uniform_tiers())
        uniform = fairness_once(config, active)
        inventory.clear_tier_override()

        summary = {}
        for origin, values in sorted(per_origin.items()):
            summary[origin] = {
                "declared": round(declared.get(origin, 0.0), 5),
                "shuffled_mean": round(statistics.fmean(values), 5),
                "shuffled_min": round(min(values), 5),
                "shuffled_max": round(max(values), 5),
                "uniform": round(uniform.get(origin, 0.0), 5),
                "times_highest": top_counts.get(origin, 0),
            }

        print("\n  origin            declared  shuf_mean  [min,max]           top/N  uniform")
        for origin, row in sorted(summary.items(), key=lambda kv: -kv[1]["declared"]):
            print(
                f"  {origin:16s}  {row['declared']:.4f}    {row['shuffled_mean']:.4f}"
                f"   [{row['shuffled_min']:.4f},{row['shuffled_max']:.4f}]"
                f"   {row['times_highest']:2d}/{args.trials}   {row['uniform']:.4f}"
            )
        results[label] = summary

    path = args.out / "tier_sensitivity.json"
    path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"\nwrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

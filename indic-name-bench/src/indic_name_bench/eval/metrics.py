"""Operating-point metrics for screening.

What is and is not base-rate dependent
--------------------------------------
This trips people up constantly, so it is stated once here and relied on
everywhere else.

TPR (recall) and FPR are *conditional on the true class*. They do not change
with the base rate. Precision, alert volume and analyst cost do -- dramatically.
A method with 1% FPR looks respectable until you note that at one true match
per 100,000 names it produces a thousand false alerts for every real one.

So the corpus is labelled once and the base rate enters only where it belongs:

    precision(pi) = pi*TPR / (pi*TPR + (1-pi)*FPR)
    alerts per N  = N * (pi*TPR + (1-pi)*FPR)

No resampling, no regeneration, and the sweep is exact rather than estimated.

The one caveat, restated from corpus.py: the hard negatives are drawn from the
confusable region rather than uniformly from all possible pairs, so the
measured FPR is higher than a uniform draw would give. Alert volumes computed
from it are therefore **upper bounds**. Relative comparisons between matchers
are unaffected -- they share the negative set.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

#: False-positive budgets an alert-handling function actually operates at.
FPR_BUDGETS: tuple[float, ...] = (0.001, 0.01, 0.05)

#: Base rates spanning the realistic screening range.
BASE_RATES: tuple[float, ...] = (1e-2, 1e-3, 1e-4, 1e-5, 1e-6)

#: Minutes an analyst spends disposing of one alert. A stated assumption, not
#: a measurement; published figures for L1 sanctions alert review cluster
#: around this. Every analyst-hour number scales linearly with it.
MINUTES_PER_ALERT: float = 4.0


@dataclass(frozen=True, slots=True)
class Curve:
    """A ROC/PR curve as parallel arrays, ordered by descending threshold."""

    thresholds: tuple[float, ...]
    tpr: tuple[float, ...]
    fpr: tuple[float, ...]
    n_positive: int
    n_negative: int


def build_curve(scores: list[float], labels: list[int]) -> Curve:
    """Sweep every distinct score as a threshold.

    Exact rather than binned: with a few thousand pairs there is no reason to
    approximate, and binning would blur the low-FPR region, which is the only
    region that matters operationally.
    """
    paired = sorted(zip(scores, labels, strict=True), key=lambda x: -x[0])
    n_positive = sum(labels)
    n_negative = len(labels) - n_positive
    if n_positive == 0 or n_negative == 0:
        return Curve((), (), (), n_positive, n_negative)

    thresholds: list[float] = []
    tpr: list[float] = []
    fpr: list[float] = []

    true_positives = 0
    false_positives = 0
    previous_score = None

    for score, label in paired:
        if previous_score is not None and score != previous_score:
            thresholds.append(previous_score)
            tpr.append(true_positives / n_positive)
            fpr.append(false_positives / n_negative)
        if label == 1:
            true_positives += 1
        else:
            false_positives += 1
        previous_score = score

    thresholds.append(previous_score if previous_score is not None else 0.0)
    tpr.append(true_positives / n_positive)
    fpr.append(false_positives / n_negative)
    return Curve(tuple(thresholds), tuple(tpr), tuple(fpr), n_positive, n_negative)


def recall_at_fpr(curve: Curve, budget: float) -> tuple[float, float]:
    """Best recall achievable without exceeding ``budget`` false-positive rate.

    Returns ``(recall, threshold)``. This is the operationally correct framing:
    alert capacity is fixed, so the question is never "what is the F1" but
    "how many true matches do we catch within the alert budget we have".
    """
    best_recall = 0.0
    best_threshold = 1.0
    for threshold, tpr, fpr in zip(curve.thresholds, curve.tpr, curve.fpr, strict=True):
        if fpr <= budget and tpr > best_recall:
            best_recall = tpr
            best_threshold = threshold
    return best_recall, best_threshold


def auc_pr(scores: list[float], labels: list[int]) -> float:
    """Average precision (step-wise AUC-PR).

    Computed at the sample's own base rate, so it is comparable across matchers
    on this corpus but not to a number from a corpus with different class
    balance. Reported alongside recall-at-FPR rather than instead of it.
    """
    paired = sorted(zip(scores, labels, strict=True), key=lambda x: -x[0])
    n_positive = sum(labels)
    if n_positive == 0:
        return 0.0

    true_positives = 0
    seen = 0
    total = 0.0
    previous_recall = 0.0

    # Tied scores must advance as one block. Walking item by item consumes ties
    # in whatever order the input list happened to be in -- and since the
    # evaluation set is built as positives-then-negatives, that ordering
    # credited every tied positive before any tied negative. Coarse matchers
    # emit almost nothing but ties (exact match scores only 0 or 1), so the
    # effect was not marginal: plain string equality scored AUC-PR 1.000 while
    # recovering 2.8% of positives.
    index = 0
    while index < len(paired):
        end = index
        while end < len(paired) and paired[end][0] == paired[index][0]:
            end += 1
        block = paired[index:end]
        true_positives += sum(label for _, label in block)
        seen += len(block)
        recall = true_positives / n_positive
        precision = true_positives / seen
        total += precision * (recall - previous_recall)
        previous_recall = recall
        index = end
    return total


def auc_roc(curve: Curve) -> float:
    if not curve.thresholds:
        return 0.0
    points = sorted(zip(curve.fpr, curve.tpr, strict=True))
    area = 0.0
    previous_x, previous_y = 0.0, 0.0
    for x, y in points:
        area += (x - previous_x) * (y + previous_y) / 2.0
        previous_x, previous_y = x, y
    area += (1.0 - previous_x) * (1.0 + previous_y) / 2.0
    return area


def precision_at(tpr: float, fpr: float, base_rate: float) -> float:
    """Precision implied by an operating point at a given base rate."""
    alerts = base_rate * tpr + (1.0 - base_rate) * fpr
    return (base_rate * tpr) / alerts if alerts > 0 else 0.0


@dataclass(frozen=True, slots=True)
class AlertVolume:
    """Operational cost of an operating point."""

    base_rate: float
    threshold: float
    recall: float
    fpr: float
    screened: int
    alerts: float
    true_alerts: float
    precision: float

    @property
    def false_alerts(self) -> float:
        return self.alerts - self.true_alerts

    @property
    def analyst_hours(self) -> float:
        return self.alerts * MINUTES_PER_ALERT / 60.0

    @property
    def wasted_hours(self) -> float:
        return self.false_alerts * MINUTES_PER_ALERT / 60.0


def alert_volume(
    curve: Curve, budget: float, base_rate: float, screened: int = 100_000
) -> AlertVolume:
    """Alerts generated per ``screened`` names at a chosen FPR budget.

    This is the number that carries a finding outside engineering: it converts
    an accuracy delta into analyst-hours, which is a line in a budget.
    """
    recall, threshold = recall_at_fpr(curve, budget)
    fpr = 0.0
    for candidate, tpr, candidate_fpr in zip(
        curve.thresholds, curve.tpr, curve.fpr, strict=True
    ):
        if candidate == threshold and tpr == recall:
            fpr = candidate_fpr
            break

    alerts = screened * (base_rate * recall + (1.0 - base_rate) * fpr)
    true_alerts = screened * base_rate * recall
    return AlertVolume(
        base_rate=base_rate,
        threshold=threshold,
        recall=recall,
        fpr=fpr,
        screened=screened,
        alerts=alerts,
        true_alerts=true_alerts,
        precision=precision_at(recall, fpr, base_rate),
    )


def wilson_interval(successes: int, total: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score interval for a proportion.

    Used instead of the normal approximation because the fairness analysis
    reports rates near zero on modest per-stratum samples, where the normal
    interval produces negative lower bounds and coverage well below nominal.
    """
    if total == 0:
        return (0.0, 0.0)
    p = successes / total
    denominator = 1 + z * z / total
    centre = (p + z * z / (2 * total)) / denominator
    margin = (z / denominator) * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total))
    return (max(0.0, centre - margin), min(1.0, centre + margin))


def disparity_ratio(
    rate_a: float, count_a: int, total_a: int, rate_b: float, count_b: int, total_b: int
) -> tuple[float, tuple[float, float]]:
    """Ratio of two rates with a confidence interval on the ratio.

    Interval is built from the Wilson bounds of each rate rather than a
    delta-method approximation on the log ratio, which behaves badly when
    either rate is near zero -- routine here, since false-positive rates at a
    0.1% budget are near zero by construction.
    """
    if rate_b <= 0:
        return (float("inf") if rate_a > 0 else 1.0, (0.0, float("inf")))
    ratio = rate_a / rate_b
    low_a, high_a = wilson_interval(count_a, total_a)
    low_b, high_b = wilson_interval(count_b, total_b)
    low = low_a / high_b if high_b > 0 else 0.0
    high = high_a / low_b if low_b > 0 else float("inf")
    return ratio, (low, high)


@dataclass
class MatcherResult:
    """Everything measured for one matcher on one pair set."""

    matcher: str
    n_pairs: int
    auc_pr: float
    auc_roc: float
    recall_at_budget: dict[float, float] = field(default_factory=dict)
    threshold_at_budget: dict[float, float] = field(default_factory=dict)
    per_pair_us: float = 0.0
    pairs_per_second: float = 0.0

    def to_row(self) -> dict[str, object]:
        row: dict[str, object] = {
            "matcher": self.matcher,
            "n_pairs": self.n_pairs,
            "auc_pr": round(self.auc_pr, 4),
            "auc_roc": round(self.auc_roc, 4),
            "per_pair_us": round(self.per_pair_us, 2),
            "pairs_per_second": round(self.pairs_per_second, 0),
        }
        for budget, recall in sorted(self.recall_at_budget.items()):
            row[f"recall@fpr{budget:g}"] = round(recall, 4)
        return row


def evaluate(
    matcher_name: str,
    scores: list[float],
    labels: list[int],
    *,
    per_pair_us: float = 0.0,
    pairs_per_second: float = 0.0,
    budgets: tuple[float, ...] = FPR_BUDGETS,
) -> MatcherResult:
    """Full metric set for one matcher on one pair set."""
    curve = build_curve(scores, labels)
    result = MatcherResult(
        matcher=matcher_name,
        n_pairs=len(scores),
        auc_pr=auc_pr(scores, labels),
        auc_roc=auc_roc(curve),
        per_pair_us=per_pair_us,
        pairs_per_second=pairs_per_second,
    )
    for budget in budgets:
        recall, threshold = recall_at_fpr(curve, budget)
        result.recall_at_budget[budget] = recall
        result.threshold_at_budget[budget] = threshold
    return result

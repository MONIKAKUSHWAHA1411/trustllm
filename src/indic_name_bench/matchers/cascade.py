"""Hybrid cascade: cheap high-recall blocking, then precise reranking.

This is how screening is actually deployed. Nobody runs an expensive matcher
over every pair; a cheap filter proposes candidates and something better
adjudicates them. The interesting number is not the cascade's accuracy alone
but its accuracy *per unit cost*, because the blocking stage caps recall no
matter how good the reranker is.

The cascade reports the fraction of pairs that reached the expensive stage, so
the cost model in Phase 4 is measured rather than assumed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import ClassVar

from .base import CostClass, Matcher, Timing, clamp


@dataclass
class CascadeStats:
    """Instrumentation for the cost analysis."""

    seen: int = 0
    reranked: int = 0

    @property
    def rerank_fraction(self) -> float:
        return self.reranked / self.seen if self.seen else 0.0

    def reset(self) -> None:
        self.seen = 0
        self.reranked = 0


class CascadeMatcher(Matcher):
    """Blocking stage gates an expensive reranking stage.

    Pairs scoring below ``block_threshold`` on the cheap matcher are rejected
    outright and never reach the reranker. This is the deployability question
    in miniature: set the threshold high and you save compute but lose the
    recall the reranker was bought for; set it low and the reranker runs on
    everything.

    The blocking stage's recall is a hard ceiling on the cascade's recall. That
    ceiling is reported separately in the results, because a cascade that looks
    mediocre may have a fine reranker behind a blocking stage that already
    threw the match away.
    """

    cost_class: ClassVar[CostClass] = CostClass.MODERATE

    def __init__(
        self,
        blocker: Matcher,
        reranker: Matcher,
        *,
        block_threshold: float = 0.35,
        name: str | None = None,
    ):
        self.blocker = blocker
        self.reranker = reranker
        self.block_threshold = block_threshold
        self.name = name or f"cascade[{blocker.name}->{reranker.name}]"
        self.description = (
            f"{blocker.name} blocking at {block_threshold:g}, then {reranker.name}"
        )
        self.cost_class = reranker.cost_class
        self.stats = CascadeStats()

    def score(self, a: str, b: str) -> float:
        self.stats.seen += 1
        cheap = self.blocker.score(a, b)
        if cheap < self.block_threshold:
            # Rejected at blocking. Returned as the blocker's own score rather
            # than 0 so the score remains monotone and the PR curve stays
            # meaningful below the threshold.
            return clamp(cheap * 0.5)
        self.stats.reranked += 1
        return self.reranker.score(a, b)

    def score_batch(self, pairs: list[tuple[str, str]]) -> tuple[list[float], Timing]:
        self.stats.reset()
        return super().score_batch(pairs)


def blocking_recall(
    blocker: Matcher, pairs: list[tuple[str, str]], labels: list[int], threshold: float
) -> float:
    """Fraction of true matches that survive the blocking stage.

    The cascade's recall can never exceed this. Reported alongside every
    cascade result.
    """
    positives = [(a, b) for (a, b), label in zip(pairs, labels, strict=True) if label == 1]
    if not positives:
        return 0.0
    survived = sum(1 for a, b in positives if blocker.score(a, b) >= threshold)
    return survived / len(positives)

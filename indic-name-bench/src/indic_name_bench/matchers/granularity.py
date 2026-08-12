"""Score granularity: making coarse matchers operable at a tight alert budget.

The observation
---------------
Every phonetic method in the headline table scores exactly **0.000** recall at a
0.1% false-positive budget. Not because the phonology fails -- their AUC-PR is
respectable -- but because a code-equality matcher over a 2-3 token name emits
only a handful of distinct scores (0, 0.33, 0.5, 0.67, 1.0). If the tightest
available operating point already exceeds 0.1% FPR, there is no threshold to
choose. The matcher is simply not tunable in that region.

Meanwhile `token_sort_levenshtein`, with worse phonetics and continuous scores,
recovers 0.183 there.

The hypothesis
--------------
This is a *representation* problem, not a matching-quality problem, and it
should be fixable without touching the phonology: blend a small amount of a
continuous signal into the coarse score to break ties, and the low-FPR region
becomes reachable.

Blending weight is deliberately small (default 0.15). The point is to order
*within* a tie group, not to relitigate the phonetic decision. A large weight
would turn the result into "Jaro-Winkler with extra steps" and prove nothing
about granularity.

What a positive result would mean
--------------------------------
That any deployed phonetic screening system leaving recall on the floor at a
tight alert budget can recover some of it for the cost of one extra cheap
comparison -- no retuning, no new algorithm, no change to which pairs the
phonology considers equivalent.
"""

from __future__ import annotations

from typing import ClassVar

from .base import CostClass, Matcher, clamp


class TieBrokenMatcher(Matcher):
    """A coarse matcher with a continuous signal blended in to break ties.

    ``score = (1 - epsilon) * base + epsilon * tiebreaker``

    Because ``epsilon`` is small, two pairs that the base matcher separates stay
    separated in the same order; two pairs it scores identically get ordered by
    the tiebreaker. That is exactly the degree of freedom a threshold needs in
    order to sit inside a tight budget.
    """

    cost_class: ClassVar[CostClass] = CostClass.CHEAP

    def __init__(self, base: Matcher, tiebreaker: Matcher, *, epsilon: float = 0.15):
        if not 0.0 < epsilon < 0.5:
            raise ValueError(f"epsilon must be in (0, 0.5), got {epsilon}")
        self.base = base
        self.tiebreaker = tiebreaker
        self.epsilon = epsilon
        self.name = f"{base.name}+tiebreak"
        self.handles_non_latin = base.handles_non_latin and tiebreaker.handles_non_latin
        self.description = (
            f"{base.name} with {tiebreaker.name} blended at {epsilon:g} to break ties"
        )

    def score(self, a: str, b: str) -> float:
        return clamp(
            (1.0 - self.epsilon) * self.base.score(a, b)
            + self.epsilon * self.tiebreaker.score(a, b)
        )


def distinct_score_count(matcher: Matcher, pairs: list[tuple[str, str]]) -> int:
    """How many distinct scores a matcher emits over ``pairs``.

    The direct measure of granularity, and the diagnostic that explains a zero
    at a tight budget. A matcher emitting five distinct values over 30,000 pairs
    has five available operating points, and if none of them sits under the
    budget then its recall there is zero regardless of how good it is.
    """
    return len({matcher.score(a, b) for a, b in pairs})


def build(base_matchers: list[Matcher], tiebreaker: Matcher) -> list[Matcher]:
    """Wrap each coarse matcher with a tie-breaker.

    Applied only to matchers whose scores are genuinely coarse -- wrapping an
    already-continuous matcher would just add noise to it.
    """
    return [TieBrokenMatcher(base, tiebreaker) for base in base_matchers]

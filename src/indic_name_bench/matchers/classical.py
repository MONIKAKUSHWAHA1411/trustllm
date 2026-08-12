"""Classical string-similarity baselines.

These are measured **as they ship**. Inputs get case folding and punctuation
stripping -- what any deployment does -- but honorifics and qualifiers are left
in, and no Indic-aware preprocessing is applied. Cleaning the inputs first
would report a system nobody actually runs, and would quietly transfer the
Indic adaptation out of the matcher and into the harness, where it would not be
counted against anyone's cost budget.
"""

from __future__ import annotations

from collections import Counter
from functools import lru_cache
from typing import ClassVar

from ..util import levenshtein
from .base import CostClass, Matcher, clamp, normalise, token_weight

try:  # pragma: no cover - exercised via the optional extra
    import jellyfish

    _HAVE_JELLYFISH = True
except ImportError:  # pragma: no cover
    _HAVE_JELLYFISH = False


class ExactMatcher(Matcher):
    """Byte equality. The floor."""

    name: ClassVar[str] = "exact"
    cost_class: ClassVar[CostClass] = CostClass.TRIVIAL
    handles_non_latin: ClassVar[bool] = True
    description: ClassVar[str] = "Raw string equality"

    def score(self, a: str, b: str) -> float:
        return 1.0 if a == b else 0.0


class NormalisedExactMatcher(Matcher):
    """Equality after case folding and punctuation stripping."""

    name: ClassVar[str] = "normalised_exact"
    cost_class: ClassVar[CostClass] = CostClass.TRIVIAL
    handles_non_latin: ClassVar[bool] = True
    description: ClassVar[str] = "Equality after case/punctuation normalisation"

    def score(self, a: str, b: str) -> float:
        return 1.0 if normalise(a) == normalise(b) else 0.0


class LevenshteinMatcher(Matcher):
    """Length-normalised Levenshtein similarity."""

    name: ClassVar[str] = "levenshtein"
    cost_class: ClassVar[CostClass] = CostClass.TRIVIAL
    handles_non_latin: ClassVar[bool] = True
    description: ClassVar[str] = "1 - (edit distance / max length)"

    def score(self, a: str, b: str) -> float:
        x, y = normalise(a), normalise(b)
        if not x and not y:
            return 1.0
        longest = max(len(x), len(y))
        if not longest:
            return 0.0
        # Prefer the C implementation when present. The pure-Python fallback in
        # util.py is there so corpus generation works with no extras installed,
        # but timing it here would report the harness's teaching implementation
        # rather than what anyone deploys.
        distance = (
            jellyfish.levenshtein_distance(x, y) if _HAVE_JELLYFISH else levenshtein(x, y)
        )
        return clamp(1.0 - distance / longest)


class DamerauLevenshteinMatcher(Matcher):
    """Length-normalised Damerau-Levenshtein, which counts a transposition once.

    Worth separating from plain Levenshtein because transposition is the most
    common keystroke error, and charging it two edits overstates typo damage.
    """

    name: ClassVar[str] = "damerau_levenshtein"
    cost_class: ClassVar[CostClass] = CostClass.TRIVIAL
    handles_non_latin: ClassVar[bool] = True
    description: ClassVar[str] = "1 - (Damerau-Levenshtein / max length)"

    def score(self, a: str, b: str) -> float:
        x, y = normalise(a), normalise(b)
        if not x and not y:
            return 1.0
        longest = max(len(x), len(y))
        if not longest:
            return 0.0
        if _HAVE_JELLYFISH:
            distance = jellyfish.damerau_levenshtein_distance(x, y)
        else:  # pragma: no cover
            distance = levenshtein(x, y)
        return clamp(1.0 - distance / longest)


class JaroMatcher(Matcher):
    name: ClassVar[str] = "jaro"
    cost_class: ClassVar[CostClass] = CostClass.TRIVIAL
    handles_non_latin: ClassVar[bool] = True
    description: ClassVar[str] = "Jaro similarity"

    def score(self, a: str, b: str) -> float:
        if not _HAVE_JELLYFISH:  # pragma: no cover
            raise RuntimeError("jaro requires the 'matchers' extra: pip install indic-name-bench[matchers]")
        return clamp(jellyfish.jaro_similarity(normalise(a), normalise(b)))


class JaroWinklerMatcher(Matcher):
    """Jaro-Winkler, which rewards a shared prefix.

    The prefix bonus is a liability here rather than an advantage: Indic
    variation frequently hits the first characters (Bhatt/Batt, Ghosh/Gosh,
    Shashi/Sasi), so the bonus is withheld from exactly the pairs that need it
    and granted to hard negatives that share a common given name.
    """

    name: ClassVar[str] = "jaro_winkler"
    cost_class: ClassVar[CostClass] = CostClass.TRIVIAL
    handles_non_latin: ClassVar[bool] = True
    description: ClassVar[str] = "Jaro-Winkler (prefix-weighted Jaro)"

    def score(self, a: str, b: str) -> float:
        if not _HAVE_JELLYFISH:  # pragma: no cover
            raise RuntimeError("jaro_winkler requires the 'matchers' extra")
        return clamp(jellyfish.jaro_winkler_similarity(normalise(a), normalise(b)))


@lru_cache(maxsize=100_000)
def _ngrams(text: str, n: int) -> tuple[str, ...]:
    padded = f"{'  '}{text}{'  '}"[: len(text) + 4]
    return tuple(padded[i : i + n] for i in range(len(padded) - n + 1))


class NgramCosineMatcher(Matcher):
    name: ClassVar[str] = "ngram_cosine"
    cost_class: ClassVar[CostClass] = CostClass.CHEAP
    handles_non_latin: ClassVar[bool] = True
    description: ClassVar[str] = "Character trigram cosine similarity"

    def __init__(self, n: int = 3):
        self.n = n

    def score(self, a: str, b: str) -> float:
        left = Counter(_ngrams(normalise(a), self.n))
        right = Counter(_ngrams(normalise(b), self.n))
        if not left or not right:
            return 0.0
        shared = set(left) & set(right)
        dot = sum(left[g] * right[g] for g in shared)
        magnitude = (
            sum(v * v for v in left.values()) ** 0.5
            * sum(v * v for v in right.values()) ** 0.5
        )
        return clamp(dot / magnitude) if magnitude else 0.0


class NgramJaccardMatcher(Matcher):
    name: ClassVar[str] = "ngram_jaccard"
    cost_class: ClassVar[CostClass] = CostClass.CHEAP
    handles_non_latin: ClassVar[bool] = True
    description: ClassVar[str] = "Character trigram Jaccard similarity"

    def __init__(self, n: int = 3):
        self.n = n

    def score(self, a: str, b: str) -> float:
        left = set(_ngrams(normalise(a), self.n))
        right = set(_ngrams(normalise(b), self.n))
        if not left or not right:
            return 0.0
        return clamp(len(left & right) / len(left | right))


class TokenJaccardMatcher(Matcher):
    """Unweighted token-set Jaccard.

    The canonical failure mode on Indian names: every token counts equally, so
    two records agreeing on "Kumar" score the same as two agreeing on
    "Chattopadhyay". Included precisely because it is what many production
    systems do.
    """

    name: ClassVar[str] = "token_jaccard"
    cost_class: ClassVar[CostClass] = CostClass.TRIVIAL
    handles_non_latin: ClassVar[bool] = True
    description: ClassVar[str] = "Token-set Jaccard, all tokens weighted equally"

    def score(self, a: str, b: str) -> float:
        left = set(normalise(a).split())
        right = set(normalise(b).split())
        if not left or not right:
            return 0.0
        return clamp(len(left & right) / len(left | right))


class WeightedTokenMatcher(Matcher):
    """Token-set overlap with low-information tokens down-weighted.

    The minimal fix to :class:`TokenJaccardMatcher`, isolated so the results can
    price it: how much of the gap between a naive token matcher and a good one
    is closed by weighting alone, before any phonetics?
    """

    name: ClassVar[str] = "weighted_token"
    cost_class: ClassVar[CostClass] = CostClass.TRIVIAL
    handles_non_latin: ClassVar[bool] = True
    description: ClassVar[str] = "Token overlap, low-information tokens down-weighted"

    def score(self, a: str, b: str) -> float:
        left = set(normalise(a, drop_affixes=True).split())
        right = set(normalise(b, drop_affixes=True).split())
        if not left or not right:
            return 0.0
        shared = sum(token_weight(t) for t in left & right)
        total = sum(token_weight(t) for t in left | right)
        return clamp(shared / total) if total else 0.0


class MongeElkanMatcher(Matcher):
    """Monge-Elkan with Jaro-Winkler as the inner similarity.

    Each token of the shorter name takes its best match from the longer, so
    token order does not matter and near-miss tokens still contribute. This is
    the strongest classical baseline for name-order inversion.
    """

    name: ClassVar[str] = "monge_elkan"
    cost_class: ClassVar[CostClass] = CostClass.MODERATE
    handles_non_latin: ClassVar[bool] = True
    description: ClassVar[str] = "Monge-Elkan over tokens with Jaro-Winkler inner"

    def score(self, a: str, b: str) -> float:
        left = normalise(a).split()
        right = normalise(b).split()
        if not left or not right:
            return 0.0
        if len(left) > len(right):
            left, right = right, left

        total = 0.0
        for token in left:
            best = max(self._inner(token, other) for other in right)
            total += best
        return clamp(total / len(left))

    @staticmethod
    def _inner(a: str, b: str) -> float:
        if _HAVE_JELLYFISH:
            return jellyfish.jaro_winkler_similarity(a, b)
        longest = max(len(a), len(b))  # pragma: no cover
        return 1.0 - levenshtein(a, b) / longest if longest else 0.0


class TokenSortLevenshteinMatcher(Matcher):
    """Levenshtein after sorting tokens alphabetically.

    The cheapest defence against name-order inversion, and a common production
    trick. Costs nothing and fixes one specific failure, which makes it a
    useful reference point for how much of the structure family is order.
    """

    name: ClassVar[str] = "token_sort_levenshtein"
    cost_class: ClassVar[CostClass] = CostClass.TRIVIAL
    handles_non_latin: ClassVar[bool] = True
    description: ClassVar[str] = "Levenshtein on alphabetically sorted tokens"

    def score(self, a: str, b: str) -> float:
        x = " ".join(sorted(normalise(a).split()))
        y = " ".join(sorted(normalise(b).split()))
        longest = max(len(x), len(y))
        if not longest:
            return 1.0 if x == y else 0.0
        return clamp(1.0 - levenshtein(x, y) / longest)


def build() -> list[Matcher]:
    matchers: list[Matcher] = [
        ExactMatcher(),
        NormalisedExactMatcher(),
        LevenshteinMatcher(),
        DamerauLevenshteinMatcher(),
        NgramCosineMatcher(),
        NgramJaccardMatcher(),
        TokenJaccardMatcher(),
        WeightedTokenMatcher(),
        TokenSortLevenshteinMatcher(),
    ]
    if _HAVE_JELLYFISH:
        matchers += [JaroMatcher(), JaroWinklerMatcher(), MongeElkanMatcher()]
    return matchers

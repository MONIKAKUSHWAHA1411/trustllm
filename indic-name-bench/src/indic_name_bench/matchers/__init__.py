"""Matchers: a uniform ``score(a, b) -> [0, 1]`` over every method benchmarked."""

from __future__ import annotations

from . import classical, indic, phonetic
from .base import HONORIFICS, LOW_INFORMATION, QUALIFIERS, CostClass, Matcher, Timing, normalise
from .cascade import CascadeMatcher, blocking_recall
from .indic import IndicPhoneticExactMatcher, IndicPhoneticMatcher, encode_name, encode_token

__all__ = [
    "CascadeMatcher",
    "CostClass",
    "HONORIFICS",
    "IndicPhoneticExactMatcher",
    "IndicPhoneticMatcher",
    "LOW_INFORMATION",
    "Matcher",
    "QUALIFIERS",
    "Timing",
    "blocking_recall",
    "build_all",
    "encode_name",
    "encode_token",
    "normalise",
    "unavailable",
]


def build_all(*, include_cascade: bool = True, include_neural: bool = True) -> list[Matcher]:
    """Every matcher available in this environment, in reporting order."""
    matchers: list[Matcher] = []
    matchers += classical.build()
    matchers += phonetic.build()
    matchers += [
        IndicPhoneticExactMatcher(),
        IndicPhoneticMatcher(),
        IndicPhoneticMatcher(merge_voicing=True),
    ]

    if include_neural:
        from . import neural

        matchers += neural.build()

    if include_cascade:
        from .classical import NgramJaccardMatcher

        matchers.append(
            CascadeMatcher(
                NgramJaccardMatcher(), IndicPhoneticMatcher(), block_threshold=0.25
            )
        )
    return matchers


def unavailable() -> dict[str, str]:
    """Matchers that could not be constructed here, and why.

    Reported in the results header. A matcher that did not run must never be
    presented as one that scored badly -- the two are different findings and
    conflating them is the easiest way to make a benchmark lie.
    """
    from . import neural

    out: dict[str, str] = {}
    available = phonetic.availability()
    if not available["jellyfish"]:
        out["soundex, metaphone, nysiis, match_rating, jaro, jaro_winkler"] = (
            "jellyfish not installed (pip install indic-name-bench[matchers])"
        )
    if not available["abydos"]:
        out["refined_soundex, double_metaphone, caverphone"] = (
            "abydos not installed (pip install indic-name-bench[matchers])"
        )
    out.update(neural.unavailable())
    return out

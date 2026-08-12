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
    "build_experiments",
    "encode_name",
    "encode_token",
    "normalise",
    "unavailable",
]


def build_all(
    *,
    include_cascade: bool = True,
    include_neural: bool = True,
    include_experiments: bool = True,
) -> list[Matcher]:
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

    if include_experiments:
        matchers += build_experiments()
    return matchers


def build_experiments() -> list[Matcher]:
    """Matchers that exist to test a specific hypothesis, not to be deployed.

    Two experiments, both answering a question the headline table only raised:

    **Alias normalisation** -- how much of the Bengali anglicisation gap closes
    with a lookup table, and whether it generalises. ``alias_oracle`` uses the
    same table the corpus was generated from and is an upper bound, not a
    result; ``alias_half`` uses 50% of the classes and answers the question a
    real system faces. See ``alias.py``.

    **Tie-breaking** -- whether the zeros at a 0.1% FPR budget are a phonology
    failure or a score-granularity artefact. See ``granularity.py``.
    """
    from .alias import AliasExactMatcher, AliasNormalisedMatcher, full_table, half_table
    from .classical import JaroWinklerMatcher
    from .granularity import TieBrokenMatcher
    from .phonetic import build as build_phonetic

    out: list[Matcher] = []

    indic = IndicPhoneticMatcher()
    out.append(AliasNormalisedMatcher(indic, half_table(), label="alias_half"))
    out.append(AliasNormalisedMatcher(indic, full_table(), label="alias_oracle"))
    out.append(AliasExactMatcher())

    tiebreaker = JaroWinklerMatcher()
    soundex = next((m for m in build_phonetic() if m.name == "soundex"), None)
    if soundex is not None:
        out.append(TieBrokenMatcher(soundex, tiebreaker))
    out.append(TieBrokenMatcher(IndicPhoneticMatcher(), tiebreaker))

    return out


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

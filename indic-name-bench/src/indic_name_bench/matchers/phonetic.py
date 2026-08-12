"""English-tuned phonetic baselines.

Soundex, Metaphone, NYSIIS and the rest are the algorithms that actually run in
sanctions screening software. They are the comparison that matters: the claim
this benchmark tests is not "fuzzy matching is hard" but "the deployed toolkit
was tuned on Anglo-European orthography and degrades on Indian names in
specific, measurable ways".

Each encoder is wrapped in the same token-alignment comparison so that the
contrast against the Indic encoder isolates the *phonology*, not the
comparison strategy. Scoring Soundex positionally while scoring the Indic
encoder with alignment would credit the alignment layer to the phonology, which
is the mistake this file exists to avoid.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Callable, ClassVar

from .base import CostClass, Matcher, clamp, normalise, token_weight

try:  # pragma: no cover
    import jellyfish

    _HAVE_JELLYFISH = True
except ImportError:  # pragma: no cover
    _HAVE_JELLYFISH = False

try:  # pragma: no cover
    from abydos.phonetic import Caverphone, DoubleMetaphone, RefinedSoundex

    _HAVE_ABYDOS = True
except ImportError:  # pragma: no cover
    _HAVE_ABYDOS = False


class PhoneticMatcher(Matcher):
    """Wraps a token encoder in weighted best-match token alignment."""

    cost_class: ClassVar[CostClass] = CostClass.CHEAP

    def __init__(self, name: str, encoder: Callable[[str], str], description: str):
        self.name = name
        self._encoder = encoder
        self.description = description

    @lru_cache(maxsize=200_000)  # noqa: B019 - bounded, per-instance encoders are stateless
    def _encode(self, token: str) -> str:
        try:
            return self._encoder(token) or ""
        except (ValueError, IndexError, UnicodeEncodeError):
            # Several of these encoders raise on non-Latin input rather than
            # returning an empty code. That is a "cannot represent" result, not
            # a zero score, and the cross-script split reports it as such.
            return ""

    def score(self, a: str, b: str) -> float:
        left = [t for t in normalise(a, drop_affixes=True).split()]
        right = [t for t in normalise(b, drop_affixes=True).split()]
        if not left or not right:
            return 0.0

        left_codes = [(t, self._encode(t)) for t in left]
        right_codes = [(t, self._encode(t)) for t in right]

        matched = 0.0
        used: set[int] = set()
        for token, code in left_codes:
            if not code:
                continue
            for j, (_, other_code) in enumerate(right_codes):
                if j in used or not other_code:
                    continue
                if code == other_code:
                    used.add(j)
                    matched += token_weight(token)
                    break

        # max, matching IndicPhoneticMatcher. If the baselines normalised by the
        # shorter side and the Indic encoder by the longer, the comparison would
        # be measuring the normalisation choice rather than the phonology.
        denominator = max(
            sum(token_weight(t) for t, _ in left_codes),
            sum(token_weight(t) for t, _ in right_codes),
        )
        return clamp(matched / denominator) if denominator else 0.0


def _double_metaphone_primary(token: str) -> str:  # pragma: no cover
    return DoubleMetaphone().encode(token)[0]


def build() -> list[Matcher]:
    matchers: list[Matcher] = []

    if _HAVE_JELLYFISH:
        matchers += [
            PhoneticMatcher("soundex", jellyfish.soundex, "Soundex (1918), the screening default"),
            PhoneticMatcher("metaphone", jellyfish.metaphone, "Metaphone"),
            PhoneticMatcher("nysiis", jellyfish.nysiis, "NYSIIS"),
            PhoneticMatcher(
                "match_rating", jellyfish.match_rating_codex, "Match Rating Approach codex"
            ),
        ]

    if _HAVE_ABYDOS:
        refined = RefinedSoundex()
        caverphone = Caverphone()
        matchers += [
            PhoneticMatcher("refined_soundex", refined.encode, "Refined Soundex"),
            PhoneticMatcher(
                "double_metaphone", _double_metaphone_primary, "Double Metaphone (primary code)"
            ),
            PhoneticMatcher("caverphone", caverphone.encode, "Caverphone 2.0"),
        ]

    return matchers


def availability() -> dict[str, bool]:
    """Which optional backends are installed, for the results header."""
    return {"jellyfish": _HAVE_JELLYFISH, "abydos": _HAVE_ABYDOS}

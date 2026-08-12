"""Uniform matcher interface.

Every matcher exposes ``score(a, b) -> float`` in [0, 1], where 1 means "same
person". That is the only contract. Phonetic algorithms natively return a code
rather than a score, string metrics return a distance, and neural encoders
return a cosine -- each is adapted here rather than in the evaluation loop, so
that the evaluator never needs to know which kind of thing it is holding.

Cost is measured alongside accuracy because a method that cannot run at
screening volume is not a candidate however accurate it is. Matchers declare a
``cost_class`` and the harness times them; both go into the Phase 4 tables.
"""

from __future__ import annotations

import re
import time
import unicodedata
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from functools import lru_cache
from typing import ClassVar

#: Tokens that carry no identifying information. Stripped by the normaliser
#: used by structure-aware matchers. Deliberately NOT stripped by the classical
#: baselines -- those are being measured as they ship, and pre-cleaning inputs
#: for them would report a system nobody actually deploys.
HONORIFICS: frozenset[str] = frozenset(
    {
        "shri", "sri", "smt", "kum", "dr", "prof", "er", "adv", "mr", "mrs",
        "ms", "miss", "md", "mohd", "haji", "hafiz", "maulana", "sardar",
        "sardarni", "pandit", "thiru", "late",
    }
)

#: Relational qualifiers and alias markers.
QUALIFIERS: frozenset[str] = frozenset(
    {"s/o", "w/o", "d/o", "c/o", "son", "wife", "daughter", "of", "alias", "@", "jr", "sr"}
)

#: Extremely high-frequency tokens shared by enormous numbers of unrelated
#: people. Down-weighted rather than dropped: "Kumar" is weak evidence, not no
#: evidence, and dropping it entirely merges "Ramesh Kumar" with "Ramesh".
LOW_INFORMATION: frozenset[str] = frozenset(
    {
        "kumar", "devi", "lal", "ram", "prasad", "chand", "nath", "bai",
        "rani", "raj", "singh", "kaur", "das", "bhai", "ben", "amma", "rao",
    }
)

_NON_ALPHA = re.compile(r"[^a-z\s]")


class CostClass(str, Enum):
    """Order-of-magnitude cost per pair, for deployability analysis."""

    TRIVIAL = "trivial"  # string ops only
    CHEAP = "cheap"  # phonetic encoding, n-grams
    MODERATE = "moderate"  # alignment, token matching
    EXPENSIVE = "expensive"  # neural encoding
    VERY_EXPENSIVE = "very_expensive"  # LLM call


def strip_diacritics(text: str) -> str:
    decomposed = unicodedata.normalize("NFD", text)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


@lru_cache(maxsize=100_000)
def normalise(text: str, *, drop_affixes: bool = False) -> str:
    """Lowercase, strip diacritics and punctuation, collapse whitespace.

    ``drop_affixes`` additionally removes honorifics and relational qualifiers
    along with everything following a qualifier, since "Rahul Sharma S/o Vinod
    Sharma" names two people and only the first is the subject.
    """
    text = strip_diacritics(text).lower()
    text = text.replace("-", " ").replace("'", "").replace(".", " ")
    text = _NON_ALPHA.sub(" ", text)
    tokens = text.split()

    if drop_affixes:
        cleaned: list[str] = []
        for token in tokens:
            if token in QUALIFIERS:
                break  # everything after a qualifier belongs to another person
            if token in HONORIFICS:
                continue
            cleaned.append(token)
        tokens = cleaned or tokens

    return " ".join(tokens)


@dataclass(frozen=True, slots=True)
class Timing:
    """Wall-clock cost of scoring a batch."""

    pairs: int
    seconds: float

    @property
    def per_pair_us(self) -> float:
        return (self.seconds / self.pairs) * 1e6 if self.pairs else 0.0

    @property
    def pairs_per_second(self) -> float:
        return self.pairs / self.seconds if self.seconds > 0 else float("inf")


class Matcher(ABC):
    """Base class for all matchers."""

    name: ClassVar[str]
    cost_class: ClassVar[CostClass] = CostClass.CHEAP
    #: Set False for matchers that cannot handle non-Latin input, so the
    #: cross-script split reports "cannot represent" rather than a misleading
    #: zero that looks like a tuning failure.
    handles_non_latin: ClassVar[bool] = False
    #: Short description for the results tables.
    description: ClassVar[str] = ""

    @abstractmethod
    def score(self, a: str, b: str) -> float:
        """Similarity in [0, 1]. 1 means "same person"."""

    def score_batch(self, pairs: list[tuple[str, str]]) -> tuple[list[float], Timing]:
        """Score many pairs, returning scores and wall-clock cost.

        Overridden by matchers that batch efficiently (neural encoders).
        """
        start = time.perf_counter()
        scores = [self.score(a, b) for a, b in pairs]
        return scores, Timing(len(pairs), time.perf_counter() - start)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<{type(self).__name__} {self.name}>"


def clamp(value: float) -> float:
    """Force a score into [0, 1].

    Several underlying libraries return values marginally outside the range
    through floating-point error, and one silently negative score would
    reorder a precision-recall curve.
    """
    if value != value:  # NaN
        return 0.0
    return max(0.0, min(1.0, value))


def token_weight(token: str) -> float:
    """Evidential weight of a token.

    High-frequency filler gets a fraction of a distinguishing token's weight.
    Two records agreeing on "Kumar" is close to no evidence; two records
    agreeing on "Chattopadhyay" is a great deal. Uniform token weighting is the
    single most common reason a token-set matcher fires on Indian names.
    """
    return 0.25 if token in LOW_INFORMATION else 1.0

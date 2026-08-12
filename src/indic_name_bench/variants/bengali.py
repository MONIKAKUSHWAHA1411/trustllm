"""Bengali anglicisation.

Colonial-era registrars rendered Bengali surnames into forms that diverge from
the source by whole syllables: Chattopadhyay became Chatterjee, Bandopadhyay
became Banerjee. Both forms remain in current official use, frequently for the
same person across different documents -- a passport in one, a tax record in
the other.

This is the most severe systematic divergence in the corpus. Chatterjee and
Chattopadhyay share four leading characters out of thirteen; no string metric
scores them as related, and no English-tuned phonetic algorithm does either.
It is a separate family from ``transliteration`` because the mechanism is
historical rather than phonological, and because keeping it separate lets the
Phase 4 breakdown state its cost on its own.
"""

from __future__ import annotations

import random
from functools import lru_cache
from typing import ClassVar

from ..data_loader import seeds
from ..names import DISTINGUISHING_ROLES, ParsedName
from .base import Family, Level, Transformation, TransformationRecord
from .substitution import recase_like


@lru_cache(maxsize=1)
def _pair_index() -> dict[str, str]:
    """Bidirectional map between anglicised and Sanskritic surname forms."""
    pairs = seeds("surnames.yaml")["bengali_anglicisation_pairs"]
    index: dict[str, str] = {}
    for anglicised, sanskritic in pairs:
        index[anglicised.lower()] = sanskritic
        index[sanskritic.lower()] = anglicised
    return index


class BengaliAnglicisation(Transformation[ParsedName]):
    """Swap between the anglicised and Sanskritic form of a Bengali surname."""

    family: ClassVar[Family] = Family.BENGALI_ANGLICISATION
    rule_id: ClassVar[str] = "anglicisation_swap"
    level: ClassVar[Level] = Level.TOKEN
    weight: ClassVar[float] = 3.0

    def apply(
        self, obj: ParsedName, rng: random.Random
    ) -> tuple[ParsedName, TransformationRecord] | None:
        index = _pair_index()
        sites = [
            i
            for i, t in enumerate(obj.tokens)
            if t.role in DISTINGUISHING_ROLES and t.text.lower() in index
        ]
        if not sites:
            return None

        i = sites[rng.randrange(len(sites))]
        token = obj.tokens[i]
        before = obj.render()
        result = obj.replace_text(i, recase_like(token.text, index[token.text.lower()]))
        after = result.render()
        if after == before:
            return None
        return result, self.record(before, after)


def build() -> list[Transformation]:
    return [BengaliAnglicisation()]

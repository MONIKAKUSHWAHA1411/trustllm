"""Honorifics, community suffixes, and relational qualifiers.

Affixes cut both ways, and the benchmark needs both directions represented.

Adding or dropping an honorific makes two records for one person look
different. Adding or dropping a community suffix makes two records for
*different* people look the same -- "Gurpreet Singh" and "Gurpreet Kaur Singh"
may be siblings, spouses, or strangers. A screening system tuned to strip
affixes reduces false negatives and raises false positives; one tuned to keep
them does the reverse. Neither setting is right, which is the point.
"""

from __future__ import annotations

import random
from functools import lru_cache
from typing import ClassVar

from ..data_loader import seeds
from ..names import ParsedName, Token, TokenRole
from .base import Family, Level, Transformation, TransformationRecord


@lru_cache(maxsize=1)
def _affixes() -> dict:
    return seeds("affixes.yaml")


def _eligible(entries: list[dict], origins: tuple[str, ...]) -> list[dict]:
    """Filter affix entries to those plausible for the name's origins."""
    out = []
    for entry in entries:
        allowed = entry.get("origins", ["*"])
        if "*" in allowed or any(o in allowed for o in origins):
            out.append(entry)
    return out


class HonorificAddition(Transformation[ParsedName]):
    """Prepend an honorific: Rahul Sharma -> Shri Rahul Sharma."""

    family: ClassVar[Family] = Family.AFFIX
    rule_id: ClassVar[str] = "honorific_addition"
    level: ClassVar[Level] = Level.TOKEN
    weight: ClassVar[float] = 1.5

    def apply(
        self, obj: ParsedName, rng: random.Random
    ) -> tuple[ParsedName, TransformationRecord] | None:
        if obj.tokens[0].role is TokenRole.HONORIFIC:
            return None
        pool = _eligible(_affixes()["honorifics"], obj.origins)
        if not pool:
            return None
        entry = pool[rng.randrange(len(pool))]
        before = obj.render()
        result = obj.insert_token(0, Token(entry["form"], TokenRole.HONORIFIC))
        return result, self.record(before, result.render())


class HonorificRemoval(Transformation[ParsedName]):
    """Strip an honorific: Dr Rahul Sharma -> Rahul Sharma."""

    family: ClassVar[Family] = Family.AFFIX
    rule_id: ClassVar[str] = "honorific_removal"
    level: ClassVar[Level] = Level.TOKEN

    def apply(
        self, obj: ParsedName, rng: random.Random
    ) -> tuple[ParsedName, TransformationRecord] | None:
        sites = [i for i, t in enumerate(obj.tokens) if t.role is TokenRole.HONORIFIC]
        if not sites or len(obj.tokens) <= 1:
            return None
        i = sites[rng.randrange(len(sites))]
        before = obj.render()
        result = obj.remove_token(i)
        return result, self.record(before, result.render())


class CommunitySuffixAddition(Transformation[ParsedName]):
    """Append a community suffix: Gurpreet Gill -> Gurpreet Gill Singh."""

    family: ClassVar[Family] = Family.AFFIX
    rule_id: ClassVar[str] = "community_suffix_addition"
    level: ClassVar[Level] = Level.TOKEN
    weight: ClassVar[float] = 1.5

    def apply(
        self, obj: ParsedName, rng: random.Random
    ) -> tuple[ParsedName, TransformationRecord] | None:
        existing = {t.text.lower() for t in obj.tokens}
        pool = [
            e
            for e in _eligible(_affixes()["community_suffixes"], obj.origins)
            if e["form"].lower() not in existing
        ]
        if not pool:
            return None
        entry = pool[rng.randrange(len(pool))]
        before = obj.render()
        result = obj.insert_token(
            len(obj.tokens), Token(entry["form"], TokenRole.SUFFIX)
        )
        return result, self.record(before, result.render())


class CommunitySuffixRemoval(Transformation[ParsedName]):
    """Drop a community suffix: Gurpreet Singh Gill -> Gurpreet Gill."""

    family: ClassVar[Family] = Family.AFFIX
    rule_id: ClassVar[str] = "community_suffix_removal"
    level: ClassVar[Level] = Level.TOKEN
    weight: ClassVar[float] = 1.5

    def apply(
        self, obj: ParsedName, rng: random.Random
    ) -> tuple[ParsedName, TransformationRecord] | None:
        known = {e["form"].lower() for e in _affixes()["community_suffixes"]}
        sites = [
            i
            for i, t in enumerate(obj.tokens)
            if t.text.lower() in known and t.role in (TokenRole.SUFFIX, TokenRole.SURNAME)
        ]
        if not sites or len(obj.tokens) <= 2:
            return None
        i = sites[rng.randrange(len(sites))]
        before = obj.render()
        result = obj.remove_token(i)
        return result, self.record(before, result.render())


class QualifierAddition(Transformation[ParsedName]):
    """Insert a relational qualifier: Rahul Sharma -> Rahul Sharma S/o Vinod Sharma.

    Indian identity documents carry the father's or husband's name inline. When
    such a record reaches a screening system the qualifier and the second name
    are usually not stripped, so the comparison string contains two people.
    """

    family: ClassVar[Family] = Family.AFFIX
    rule_id: ClassVar[str] = "qualifier_addition"
    level: ClassVar[Level] = Level.TOKEN

    def apply(
        self, obj: ParsedName, rng: random.Random
    ) -> tuple[ParsedName, TransformationRecord] | None:
        if any(t.role is TokenRole.QUALIFIER for t in obj.tokens):
            return None
        pool = _affixes()["qualifiers"]
        entry = pool[rng.randrange(len(pool))]
        before = obj.render()
        result = obj.insert_token(
            len(obj.tokens), Token(entry["form"], TokenRole.QUALIFIER)
        )
        # A qualifier is followed by the referenced person's name; reuse a
        # surname already present so the addition stays internally consistent.
        surname = next(
            (t for t in reversed(obj.tokens) if t.role is TokenRole.SURNAME), None
        )
        if surname is not None:
            result = result.insert_token(
                len(result.tokens), Token(surname.text, TokenRole.UNKNOWN)
            )
        return result, self.record(before, result.render())


def build() -> list[Transformation]:
    return [
        HonorificAddition(),
        HonorificRemoval(),
        CommunitySuffixAddition(),
        CommunitySuffixRemoval(),
        QualifierAddition(),
    ]

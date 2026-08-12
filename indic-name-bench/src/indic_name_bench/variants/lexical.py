"""Lexical variant substitution: Arabic/Persian and other enumerated classes.

A lexical variant is a spelling of a name that no character-rewrite rule
produces. Mohammed/Mahomed, Chattopadhyay/Chatterjee and Abdurrahman/Abdul
Rahman are all one identity written three ways, and the string distance between
the forms is large -- often larger than the distance between two genuinely
different people's names. That inversion is the central difficulty this
benchmark measures, so these classes carry heavy weight in the corpus.
"""

from __future__ import annotations

import random
from functools import lru_cache
from typing import ClassVar

from ..data_loader import variant_tables
from ..names import DISTINGUISHING_ROLES, ParsedName, Token, TokenRole
from .base import Family, Level, Transformation, TransformationRecord
from .substitution import recase_like


@lru_cache(maxsize=1)
def _tables() -> dict:
    return variant_tables("lexical_variants.yaml")


@lru_cache(maxsize=1)
def _equivalence_index() -> dict[str, tuple[str, ...]]:
    """Map every known form (lowercased) to the other members of its class."""
    index: dict[str, tuple[str, ...]] = {}
    tables = _tables()
    classes: list[list[str]] = list(tables.get("arabic_persian", []))
    classes += list(tables.get("other", []))
    classes.append(list(tables.get("syed_cluster", [])))
    for members in classes:
        for form in members:
            alternatives = tuple(m for m in members if m.lower() != form.lower())
            if alternatives:
                index[form.lower()] = alternatives
    return index


@lru_cache(maxsize=1)
def _arabic_forms() -> frozenset[str]:
    tables = _tables()
    forms = {f.lower() for cls in tables.get("arabic_persian", []) for f in cls}
    forms |= {f.lower() for f in tables.get("syed_cluster", [])}
    return frozenset(forms)


class LexicalVariantSwap(Transformation[ParsedName]):
    """Replace a token with another spelling from its equivalence class.

    The family reported depends on the class the token belongs to: swaps within
    the Arabic/Persian tables are attributed to ``arabic_persian`` and the rest
    to ``transliteration``. Without that split, the Arabic/Persian breakdown
    would silently absorb Bengali and Dravidian lexical variance and the
    per-family comparison would be meaningless.
    """

    family: ClassVar[Family] = Family.ARABIC_PERSIAN
    rule_id: ClassVar[str] = "lexical_variant_swap"
    level: ClassVar[Level] = Level.TOKEN
    weight: ClassVar[float] = 3.0

    def apply(
        self, obj: ParsedName, rng: random.Random
    ) -> tuple[ParsedName, TransformationRecord] | None:
        index = _equivalence_index()
        sites = [
            i
            for i, t in enumerate(obj.tokens)
            if t.role in DISTINGUISHING_ROLES and t.text.lower() in index
        ]
        if not sites:
            return None

        i = sites[rng.randrange(len(sites))]
        token = obj.tokens[i]
        alternatives = index[token.text.lower()]
        replacement = alternatives[rng.randrange(len(alternatives))]

        before = obj.render()
        result = obj.replace_text(i, recase_like(token.text, replacement))
        after = result.render()

        # Attribute to the family the token actually belongs to.
        family = (
            Family.ARABIC_PERSIAN
            if token.text.lower() in _arabic_forms()
            else Family.TRANSLITERATION
        )
        record = TransformationRecord(
            family=family.value, rule_id=self.rule_id, before=before, after=after
        )
        return result, record


class MohammedAbbreviation(Transformation[ParsedName]):
    """Abbreviate or expand Mohammed: Mohammed Ali <-> Md Ali <-> Mohd Ali.

    "Md" is not a nickname; it is the standard written abbreviation across
    Bangladesh, West Bengal and much of north India, and appears on official
    identity documents. Screening systems that tokenise it as a name see a
    two-character token shared by tens of millions of people.
    """

    family: ClassVar[Family] = Family.ARABIC_PERSIAN
    rule_id: ClassVar[str] = "mohammed_abbreviation"
    level: ClassVar[Level] = Level.TOKEN
    weight: ClassVar[float] = 2.0

    def apply(
        self, obj: ParsedName, rng: random.Random
    ) -> tuple[ParsedName, TransformationRecord] | None:
        tables = _tables()
        abbreviations: list[str] = list(tables["mohammed_abbreviations"])
        full_forms: list[str] = list(tables["arabic_persian"][0])
        full_lower = {f.lower() for f in full_forms}
        abbrev_lower = {a.lower().rstrip(".") for a in abbreviations}

        before = obj.render()
        for i, token in enumerate(obj.tokens):
            lowered = token.text.lower()
            if lowered in full_lower:
                replacement = abbreviations[rng.randrange(len(abbreviations))]
                result = obj.replace_text(i, replacement)
                return result, self.record(before, result.render())
            if lowered.rstrip(".") in abbrev_lower:
                replacement = full_forms[rng.randrange(len(full_forms))]
                result = obj.replace_text(i, replacement)
                return result, self.record(before, result.render())
        return None


class AbdulRestructure(Transformation[ParsedName]):
    """Re-render an Abdul compound: Abdul Rahman <-> Abdurrahman <-> Abdul-Rahman.

    The Arabic definite article assimilates to a following coronal, so the
    written-out form and the assimilated fusion differ by several characters
    *and* by token count. Any matcher that compares token sets, rather than
    handling the prefix as bound morphology, sees two unrelated names.
    """

    family: ClassVar[Family] = Family.ARABIC_PERSIAN
    rule_id: ClassVar[str] = "abdul_restructure"
    level: ClassVar[Level] = Level.TOKEN
    weight: ClassVar[float] = 2.0

    def apply(
        self, obj: ParsedName, rng: random.Random
    ) -> tuple[ParsedName, TransformationRecord] | None:
        seconds: dict[str, list[str]] = _tables()["abdul_prefix"]["seconds"]
        before = obj.render()

        # Case 1: an explicit "Abdul <Second>" token pair.
        for i in range(len(obj.tokens) - 1):
            if not obj.tokens[i].text.lower().startswith("abd"):
                continue
            second = obj.tokens[i + 1].text
            forms = seconds.get(second.capitalize())
            if not forms:
                continue
            replacement = forms[rng.randrange(len(forms))]
            rebuilt = self._splice(obj, i, i + 1, replacement)
            after = rebuilt.render()
            if after != before:
                return rebuilt, self.record(before, after)

        # Case 2: an already-fused single token (Abdurrahman) to re-render.
        for i, token in enumerate(obj.tokens):
            lowered = token.text.lower().replace("-", "").replace(" ", "")
            for _, forms in sorted(seconds.items()):
                if any(lowered == f.lower().replace("-", "").replace(" ", "") for f in forms):
                    replacement = forms[rng.randrange(len(forms))]
                    rebuilt = self._splice(obj, i, i, replacement)
                    after = rebuilt.render()
                    if after != before:
                        return rebuilt, self.record(before, after)
        return None

    @staticmethod
    def _splice(name: ParsedName, start: int, end: int, replacement: str) -> ParsedName:
        """Replace tokens ``start..end`` with ``replacement``, which may be multi-word."""
        role = name.tokens[start].role
        origin = name.tokens[start].origin
        pieces = replacement.split()
        new_tokens = [Token(p, role, origin=origin) for p in pieces]
        tokens = list(name.tokens)
        tokens[start : end + 1] = new_tokens
        return ParsedName(tuple(tokens))


class SyedRoleShift(Transformation[ParsedName]):
    """Move Syed between honorific and name position, or drop it.

    Syed marks claimed descent from the Prophet. It is written as a title in
    some records, as a first given name in others, and omitted in others again
    -- all for the same person.
    """

    family: ClassVar[Family] = Family.ARABIC_PERSIAN
    rule_id: ClassVar[str] = "syed_role_shift"
    level: ClassVar[Level] = Level.TOKEN

    def apply(
        self, obj: ParsedName, rng: random.Random
    ) -> tuple[ParsedName, TransformationRecord] | None:
        cluster = [s.lower() for s in _tables()["syed_cluster"]]
        before = obj.render()

        for i, token in enumerate(obj.tokens):
            if token.text.lower() not in cluster:
                continue
            # Drop it, or re-spell and re-role it.
            if rng.random() < 0.5 and len(obj.tokens) > 2:
                result = obj.remove_token(i)
            else:
                forms = _tables()["syed_cluster"]
                replacement = forms[rng.randrange(len(forms))]
                new_role = (
                    TokenRole.HONORIFIC if token.role is not TokenRole.HONORIFIC else TokenRole.GIVEN
                )
                result = obj.replace_token(
                    i, Token(replacement, new_role, origin=token.origin)
                )
            after = result.render()
            if after != before:
                return result, self.record(before, after)
        return None


def build() -> list[Transformation]:
    return [
        LexicalVariantSwap(),
        MohammedAbbreviation(),
        AbdulRestructure(),
        SyedRoleShift(),
    ]

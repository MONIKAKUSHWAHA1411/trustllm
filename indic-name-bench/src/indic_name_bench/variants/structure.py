"""Name structure: initials, ordering, compounds, house names, patronymics.

Structural variation is the family most often ignored by name-matching
libraries, because the libraries assume a given-name / family-name model that
much of India does not use. A Tamil name may consist of a father's name
abbreviated to an initial plus a personal name, with no family name at all; the
same person appears as "R. Venkatesh", "Venkatesh Ramachandran" and
"Ramachandran Venkatesh" in three different systems, and none of those is a
misspelling.

These transforms rearrange tokens rather than rewriting characters, which is
why they defeat character-level metrics so thoroughly: edit distance between
"R. Venkatesh" and "Ramachandran Venkatesh" is large, and their phonetic codes
share nothing.
"""

from __future__ import annotations

import random
from functools import lru_cache
from typing import ClassVar

from ..data_loader import seeds
from ..names import ParsedName, Token, TokenRole
from .base import Family, Level, Transformation, TransformationRecord


@lru_cache(maxsize=1)
def _house_names() -> dict[str, list[str]]:
    return seeds("affixes.yaml")["house_name_prefixes"]


class InitialiseToken(Transformation[ParsedName]):
    """Abbreviate a leading name to an initial: Ramachandran Venkatesh -> R. Venkatesh.

    Only abbreviates a non-final distinguishing token, because the final token
    is the one that carries the person's own name in the initial-plus-name
    convention. Abbreviating that instead would produce a name form that does
    not occur.
    """

    family: ClassVar[Family] = Family.STRUCTURE
    rule_id: ClassVar[str] = "initialise_token"
    level: ClassVar[Level] = Level.TOKEN
    weight: ClassVar[float] = 2.0

    def apply(
        self, obj: ParsedName, rng: random.Random
    ) -> tuple[ParsedName, TransformationRecord] | None:
        sites = [i for i in obj.distinguishing_indices() if i < len(obj.tokens) - 1]
        sites = [i for i in sites if len(obj.tokens[i].text) > 1]
        if not sites:
            return None

        i = sites[rng.randrange(len(sites))]
        token = obj.tokens[i]
        # Both "R." and bare "R" occur; the period is inconsistently recorded.
        initial = token.text[0].upper() + ("." if rng.random() < 0.7 else "")
        before = obj.render()
        result = obj.replace_token(
            i,
            Token(initial, TokenRole.INITIAL, origin=token.origin, expands_to=token.text),
        )
        return result, self.record(before, result.render())


class ExpandInitial(Transformation[ParsedName]):
    """Expand an initial back to the full form: R. Venkatesh -> Ramachandran Venkatesh."""

    family: ClassVar[Family] = Family.STRUCTURE
    rule_id: ClassVar[str] = "expand_initial"
    level: ClassVar[Level] = Level.TOKEN

    def apply(
        self, obj: ParsedName, rng: random.Random
    ) -> tuple[ParsedName, TransformationRecord] | None:
        sites = [
            i
            for i, t in enumerate(obj.tokens)
            if t.role is TokenRole.INITIAL and t.expands_to
        ]
        if not sites:
            return None
        i = sites[rng.randrange(len(sites))]
        token = obj.tokens[i]
        before = obj.render()
        result = obj.replace_token(
            i, Token(str(token.expands_to), TokenRole.GIVEN, origin=token.origin)
        )
        return result, self.record(before, result.render())


class DropInitial(Transformation[ParsedName]):
    """Omit an initial entirely: R. Venkatesh -> Venkatesh.

    Common where a form field is too short, or where the data-entry convention
    treats an initial as optional punctuation.
    """

    family: ClassVar[Family] = Family.STRUCTURE
    rule_id: ClassVar[str] = "drop_initial"
    level: ClassVar[Level] = Level.TOKEN

    def apply(
        self, obj: ParsedName, rng: random.Random
    ) -> tuple[ParsedName, TransformationRecord] | None:
        sites = [i for i, t in enumerate(obj.tokens) if t.role is TokenRole.INITIAL]
        if not sites or len(obj.tokens) <= 2:
            return None
        i = sites[rng.randrange(len(sites))]
        before = obj.render()
        result = obj.remove_token(i)
        return result, self.record(before, result.render())


class NameOrderInversion(Transformation[ParsedName]):
    """Swap given and family order: Venkatesh Ramachandran -> Ramachandran Venkatesh.

    Not a data-entry error. South Indian convention places the patronymic
    first; Western-facing systems demand given-name-first; the same person is
    recorded both ways, often within one institution.
    """

    family: ClassVar[Family] = Family.STRUCTURE
    rule_id: ClassVar[str] = "name_order_inversion"
    level: ClassVar[Level] = Level.TOKEN
    weight: ClassVar[float] = 2.0

    def apply(
        self, obj: ParsedName, rng: random.Random
    ) -> tuple[ParsedName, TransformationRecord] | None:
        sites = obj.distinguishing_indices()
        if len(sites) < 2:
            return None
        before = obj.render()
        result = obj.swap_tokens(sites[0], sites[-1])
        after = result.render()
        if after == before:
            return None
        return result, self.record(before, after)


class CompoundFusion(Transformation[ParsedName]):
    """Fuse adjacent given names: Ravi Shankar -> Ravishankar / Ravi-Shankar."""

    family: ClassVar[Family] = Family.STRUCTURE
    rule_id: ClassVar[str] = "compound_fusion"
    level: ClassVar[Level] = Level.TOKEN
    weight: ClassVar[float] = 1.5

    def apply(
        self, obj: ParsedName, rng: random.Random
    ) -> tuple[ParsedName, TransformationRecord] | None:
        sites = [
            i
            for i in range(len(obj.tokens) - 1)
            if obj.tokens[i].is_distinguishing
            and obj.tokens[i + 1].is_distinguishing
            and len(obj.tokens[i].text) > 1
            and len(obj.tokens[i + 1].text) > 1
        ]
        if not sites:
            return None
        i = sites[rng.randrange(len(sites))]
        joiner = "-" if rng.random() < 0.35 else ""
        before = obj.render()
        result = obj.merge_tokens(i, i + 1, joiner=joiner)
        return result, self.record(before, result.render())


class CompoundSplit(Transformation[ParsedName]):
    """Split a fused compound back apart: Ravishankar -> Ravi Shankar.

    Only splits at an explicit hyphen. Guessing a split point inside an
    unhyphenated token would require a morphological model of Sanskrit
    compounding, and a wrong guess manufactures a name that does not exist.
    """

    family: ClassVar[Family] = Family.STRUCTURE
    rule_id: ClassVar[str] = "compound_split"
    level: ClassVar[Level] = Level.TOKEN

    def apply(
        self, obj: ParsedName, rng: random.Random
    ) -> tuple[ParsedName, TransformationRecord] | None:
        sites = [i for i, t in enumerate(obj.tokens) if "-" in t.text.strip("-")]
        if not sites:
            return None
        i = sites[rng.randrange(len(sites))]
        token = obj.tokens[i]
        pieces = [p for p in token.text.split("-") if p]
        if len(pieces) < 2:
            return None
        before = obj.render()
        tokens = list(obj.tokens)
        tokens[i : i + 1] = [Token(p, token.role, origin=token.origin) for p in pieces]
        result = ParsedName(tuple(tokens))
        return result, self.record(before, result.render())


class HouseNamePrefix(Transformation[ParsedName]):
    """Add a house or village name: Vinod Nair -> Kunnath Vinod Nair.

    In Kerala, coastal Karnataka and Andhra the house name is part of the legal
    name and appears in property, court and banking records, while being
    absent from a passport for the same person.
    """

    family: ClassVar[Family] = Family.STRUCTURE
    rule_id: ClassVar[str] = "house_name_prefix"
    level: ClassVar[Level] = Level.TOKEN

    def apply(
        self, obj: ParsedName, rng: random.Random
    ) -> tuple[ParsedName, TransformationRecord] | None:
        if any(t.role is TokenRole.HOUSE_NAME for t in obj.tokens):
            return None
        table = _house_names()
        eligible = [o for o in obj.origins if o in table]
        if not eligible:
            return None
        origin = eligible[rng.randrange(len(eligible))]
        pool = table[origin]
        house = pool[rng.randrange(len(pool))]

        before = obj.render()
        insert_at = 1 if obj.tokens[0].role is TokenRole.HONORIFIC else 0
        result = obj.insert_token(
            insert_at, Token(house, TokenRole.HOUSE_NAME, origin=origin)
        )
        return result, self.record(before, result.render())


class HouseNameOmission(Transformation[ParsedName]):
    """Drop a house name, or reduce it to an initial."""

    family: ClassVar[Family] = Family.STRUCTURE
    rule_id: ClassVar[str] = "house_name_omission"
    level: ClassVar[Level] = Level.TOKEN

    def apply(
        self, obj: ParsedName, rng: random.Random
    ) -> tuple[ParsedName, TransformationRecord] | None:
        sites = [i for i, t in enumerate(obj.tokens) if t.role is TokenRole.HOUSE_NAME]
        if not sites or len(obj.tokens) <= 2:
            return None
        i = sites[rng.randrange(len(sites))]
        token = obj.tokens[i]
        before = obj.render()
        if rng.random() < 0.5:
            result = obj.remove_token(i)
        else:
            result = obj.replace_token(
                i,
                Token(
                    token.text[0].upper() + ".",
                    TokenRole.INITIAL,
                    origin=token.origin,
                    expands_to=token.text,
                ),
            )
        return result, self.record(before, result.render())


class PatronymicRoleShift(Transformation[ParsedName]):
    """Reinterpret a low-information token's slot: Ramesh Kumar Sharma -> Ramesh Sharma Kumar.

    "Kumar", "Devi" and "Lal" behave as given name, middle name, surname or
    filler depending on the record. Because they are shared by an enormous
    number of people they contribute almost nothing to identification, yet
    token-set matchers weight them equally with the distinguishing tokens.
    """

    family: ClassVar[Family] = Family.STRUCTURE
    rule_id: ClassVar[str] = "patronymic_role_shift"
    level: ClassVar[Level] = Level.TOKEN

    LOW_INFORMATION: ClassVar[frozenset[str]] = frozenset(
        {"kumar", "devi", "lal", "ram", "prasad", "chand", "nath", "bai", "rani", "raj"}
    )

    def apply(
        self, obj: ParsedName, rng: random.Random
    ) -> tuple[ParsedName, TransformationRecord] | None:
        sites = [
            i for i, t in enumerate(obj.tokens) if t.text.lower() in self.LOW_INFORMATION
        ]
        if not sites:
            return None
        i = sites[rng.randrange(len(sites))]
        before = obj.render()

        choice = rng.random()
        if choice < 0.4 and len(obj.tokens) > 2:
            result = obj.remove_token(i)
        elif choice < 0.7 and i < len(obj.tokens) - 1:
            result = obj.swap_tokens(i, i + 1)
        elif len(obj.tokens) > 1:
            token = obj.tokens[i]
            result = obj.remove_token(i)
            result = result.insert_token(len(result.tokens), token)
        else:
            return None

        after = result.render()
        if after == before:
            return None
        return result, self.record(before, after)


def build() -> list[Transformation]:
    return [
        InitialiseToken(),
        ExpandInitial(),
        DropInitial(),
        NameOrderInversion(),
        CompoundFusion(),
        CompoundSplit(),
        HouseNamePrefix(),
        HouseNameOmission(),
        PatronymicRoleShift(),
    ]

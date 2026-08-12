"""Alias-table normalisation, and the coverage experiment.

Motivation
----------
The Indic phonetic encoder is the *worst* method tested on Bengali
anglicisation (recall 0.117 at a 1% FPR budget, against Soundex's 0.394).
Chatterjee/Chattopadhyay is a historical divergence, not a phonological one, so
no amount of phonology recovers it. The only mechanism that can is a lookup
table -- which is exactly what real screening systems maintain as "alias lists".

So: how much is an alias table worth, and what limits it?

The validity problem, and how it is handled
-------------------------------------------
The corpus's lexical variants were *generated* from these same tables. Wiring
the full table into a matcher hands it the generator's key, and the resulting
recall measures table lookup of the table used to build the data. That number
is not a generalisation result and must never be reported as one.

Two matchers are therefore built, and the gap between them is the finding:

``alias_oracle``
    The complete table. An **upper bound**, not a result: it answers "what if
    your alias list already contained every variant you will ever see". No
    deployed system is in that position.

``alias_half``
    A deterministic 50% sample of the equivalence classes. The corpus still
    draws on all of them, so this matcher has roughly half coverage. It answers
    the question a compliance function actually has: what does an *incomplete*
    alias list buy?

If ``alias_half`` lands near halfway between the un-normalised baseline and
``alias_oracle``, then performance scales with coverage and nothing
generalises -- an alias table helps precisely and only for the names already
enumerated in it. That is a much more useful thing to know than the oracle
number, and it is the one to cite.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from functools import lru_cache
from typing import ClassVar

from ..data_loader import seeds, variant_tables
from .base import CostClass, Matcher, normalise


@dataclass(frozen=True)
class AliasTable:
    """Maps every known spelling of a name to one canonical form."""

    canonical: dict[str, str]
    n_classes: int

    def token(self, text: str) -> str:
        return self.canonical.get(text.lower(), text.lower())

    def name(self, text: str) -> str:
        return " ".join(self.token(t) for t in normalise(text, drop_affixes=True).split())

    @property
    def n_forms(self) -> int:
        return len(self.canonical)


def _all_classes() -> list[list[str]]:
    """Every lexical equivalence class, from both table sources.

    Order is stable so the 50% split is reproducible.
    """
    tables = variant_tables("lexical_variants.yaml")
    classes: list[list[str]] = []
    classes += [list(c) for c in tables.get("arabic_persian", [])]
    classes += [list(c) for c in tables.get("other", [])]
    cluster = list(tables.get("syed_cluster", []))
    if cluster:
        classes.append(cluster)
    # The Bengali anglicisation pairs live with the seed data, not the variant
    # tables, because the generator reads them from there.
    classes += [list(p) for p in seeds("surnames.yaml")["bengali_anglicisation_pairs"]]
    return classes


def _build(classes: list[list[str]]) -> AliasTable:
    canonical: dict[str, str] = {}
    for members in classes:
        if not members:
            continue
        target = members[0].lower()
        for form in members:
            canonical[form.lower()] = target
    return AliasTable(canonical=canonical, n_classes=len(classes))


@lru_cache(maxsize=1)
def full_table() -> AliasTable:
    return _build(_all_classes())


@lru_cache(maxsize=1)
def half_table() -> AliasTable:
    """A deterministic 50% sample of the classes.

    Selected by hashing the canonical form rather than by index or by a
    shuffled list, so the membership does not shift if classes are added to the
    YAML in the middle.
    """
    kept = [
        members
        for members in _all_classes()
        if members
        and int(hashlib.sha256(members[0].lower().encode()).hexdigest()[:8], 16) % 2 == 0
    ]
    return _build(kept)


class AliasNormalisedMatcher(Matcher):
    """Applies alias normalisation to both inputs, then delegates.

    A wrapper rather than a matcher in its own right, so the alias table's
    contribution can be measured on top of any base method.
    """

    def __init__(self, base: Matcher, table: AliasTable, *, label: str):
        self.base = base
        self.table = table
        self.name = f"{base.name}+{label}"
        self.cost_class = base.cost_class
        self.handles_non_latin = base.handles_non_latin
        self.description = (
            f"{base.description}, with alias normalisation "
            f"({table.n_classes} classes / {table.n_forms} forms)"
        )

    def score(self, a: str, b: str) -> float:
        return self.base.score(self.table.name(a), self.table.name(b))


class AliasExactMatcher(Matcher):
    """Alias normalisation followed by exact equality.

    The floor for the alias mechanism on its own, with no phonetics and no
    fuzzy matching underneath it.
    """

    name: ClassVar[str] = "alias_exact"
    cost_class: ClassVar[CostClass] = CostClass.TRIVIAL
    description: ClassVar[str] = "Alias normalisation then exact equality"

    def __init__(self, table: AliasTable | None = None):
        self.table = table or full_table()

    def score(self, a: str, b: str) -> float:
        return 1.0 if self.table.name(a) == self.table.name(b) else 0.0


def coverage_summary() -> dict[str, int]:
    """Table sizes, for the results header."""
    return {
        "full_classes": full_table().n_classes,
        "full_forms": full_table().n_forms,
        "half_classes": half_table().n_classes,
        "half_forms": half_table().n_forms,
    }

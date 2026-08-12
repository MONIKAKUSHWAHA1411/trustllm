"""Cross-script variants: Indic script <-> Latin.

Sanctions lists, KYC records and customer databases hold the same person's name
in Latin script in one field and in a native script in another. Matching across
that boundary is not fuzzy string matching at all -- the two strings share no
characters -- so every Latin-oriented matcher scores zero by construction.

Including this family is worth doing precisely because the result is
foreordained for classical methods: it establishes the floor, and it isolates
the one capability (script-independent representation) that neural encoders can
have and string algorithms cannot.

Coverage is limited to the curated pairs in ``seeds/data/script_forms.yaml``.
The generator reports the covered fraction so that cross-script numbers are
never read as if they applied to the whole corpus.
"""

from __future__ import annotations

import random
from functools import lru_cache
from typing import ClassVar

from ..data_loader import seeds
from ..names import DISTINGUISHING_ROLES, ParsedName
from .base import Family, Level, Transformation, TransformationRecord

#: Scripts with curated coverage, in a stable order.
SUPPORTED_SCRIPTS: tuple[str, ...] = ("Deva", "Beng", "Taml", "Telu", "Guru")


@lru_cache(maxsize=1)
def _script_index() -> dict[str, dict[str, str]]:
    """``{script: {latin_lower: native_form}}``."""
    data = seeds("script_forms.yaml")
    index: dict[str, dict[str, str]] = {}
    for script in SUPPORTED_SCRIPTS:
        block = data.get(script)
        if not block:
            continue
        merged: dict[str, str] = {}
        for section in ("given", "surname"):
            merged.update({k.lower(): v for k, v in (block.get(section) or {}).items()})
        index[script] = merged
    return index


@lru_cache(maxsize=1)
def _covered_latin_forms() -> frozenset[str]:
    return frozenset(k for table in _script_index().values() for k in table)


def coverage_report() -> dict[str, int]:
    """Curated pair counts per script, for the limitations section."""
    return {script: len(table) for script, table in sorted(_script_index().items())}


class ScriptConversion(Transformation[ParsedName]):
    """Convert covered tokens to a native Indic script.

    Converts every token it can rather than one, because a record is written in
    one script throughout; a name half in Devanagari and half in Latin is not a
    form that occurs. Tokens outside the curated set are left in Latin, which
    does happen -- mixed-script records are common where a surname has no
    conventional native spelling.
    """

    family: ClassVar[Family] = Family.CROSS_SCRIPT
    rule_id: ClassVar[str] = "script_conversion"
    level: ClassVar[Level] = Level.TOKEN

    def apply(
        self, obj: ParsedName, rng: random.Random
    ) -> tuple[ParsedName, TransformationRecord] | None:
        index = _script_index()
        # Which scripts can render at least one distinguishing token here?
        usable = [
            script
            for script in SUPPORTED_SCRIPTS
            if script in index
            and any(
                t.role in DISTINGUISHING_ROLES and t.text.lower() in index[script]
                for t in obj.tokens
            )
        ]
        if not usable:
            return None

        script = usable[rng.randrange(len(usable))]
        table = index[script]

        before = obj.render()
        result = obj
        converted = 0
        for i, token in enumerate(obj.tokens):
            native = table.get(token.text.lower())
            if native and token.role in DISTINGUISHING_ROLES:
                result = result.replace_text(i, native)
                converted += 1
        if converted == 0:
            return None

        after = result.render()
        record = TransformationRecord(
            family=self.family.value,
            rule_id=f"{self.rule_id}:{script}",
            before=before,
            after=after,
        )
        return result, record


def build() -> list[Transformation]:
    return [ScriptConversion()]

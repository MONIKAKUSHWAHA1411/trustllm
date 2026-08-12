"""Assembles synthetic identities from name components.

An identity is a role-tagged :class:`~indic_name_bench.names.ParsedName` plus
the metadata the evaluation needs: an origin category, a gender, and a stable
id. Identities are the ground-truth units -- a positive pair is two variants of
one identity, a negative pair is variants of two different identities.

Structure templates are per-origin because Indian naming conventions are not
one system. A Tamil name may be an initial plus a personal name with no family
name; a Telugu name conventionally leads with a house name; a Punjabi name
carries Singh or Kaur in a slot that is neither given nor family. Generating
every origin as given-plus-surname would erase exactly the structural
variation this benchmark exists to measure.
"""

from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass
from typing import ClassVar

from ..names import ParsedName, Token, TokenRole
from . import inventory
from .inventory import GIVEN, LOW_INFORMATION, SURNAME, Component, components_for, weighted_choice

#: Structure templates per origin, as ``(weight, slots)``.
#:
#: Slot vocabulary:
#:   given      -- a given name for the identity's gender
#:   given2     -- a second given / middle name
#:   surname    -- a family name from the origin's inventory
#:   lowinfo    -- Kumar / Devi / Lal and friends
#:   initial    -- a single-letter abbreviation of a patronymic
#:   patronymic -- a full patronymic in leading position
#:   suffix     -- Singh / Kaur, carried as a SUFFIX token
TEMPLATES: dict[str, tuple[tuple[float, tuple[str, ...]], ...]] = {
    "hindi_belt": (
        (5.0, ("given", "surname")),
        (3.0, ("given", "lowinfo", "surname")),
        (1.5, ("given", "given2", "surname")),
        (1.0, ("given", "lowinfo")),
    ),
    "bengali": (
        (6.0, ("given", "surname")),
        (2.0, ("given", "given2", "surname")),
    ),
    "arabic_persian": (
        (4.0, ("given", "surname")),
        (3.0, ("given", "given2", "surname")),
        (2.0, ("given", "given2")),
    ),
    "tamil": (
        (4.0, ("initial", "given")),
        (3.0, ("patronymic", "given")),
        (2.0, ("given", "surname")),
        (1.0, ("initial", "initial", "given")),
    ),
    "telugu": (
        (4.0, ("patronymic", "given", "surname")),
        (3.0, ("initial", "given", "surname")),
        (2.0, ("given", "surname")),
    ),
    "punjabi": (
        (5.0, ("given", "suffix", "surname")),
        (3.0, ("given", "suffix")),
        (2.0, ("given", "surname")),
    ),
    "gujarati": (
        (5.0, ("given", "surname")),
        (2.5, ("given", "given2", "surname")),
    ),
    "marathi": (
        (5.0, ("given", "surname")),
        (2.5, ("given", "given2", "surname")),
    ),
    "kannada": (
        (4.0, ("given", "surname")),
        (2.0, ("initial", "given", "surname")),
    ),
    "malayalam": (
        (4.0, ("given", "surname")),
        (2.0, ("initial", "given")),
        (2.0, ("given", "given2", "surname")),
    ),
    "odia": (
        (5.0, ("given", "surname")),
        (2.0, ("given", "lowinfo", "surname")),
    ),
}

#: Fallback for any origin without an explicit template.
_DEFAULT_TEMPLATE: tuple[tuple[float, tuple[str, ...]], ...] = (
    (1.0, ("given", "surname")),
)


@dataclass(frozen=True, slots=True)
class Identity:
    """A synthetic identity: the ground-truth unit of the benchmark."""

    identity_id: str
    name: ParsedName
    origin: str
    gender: str
    template: tuple[str, ...]

    @property
    def canonical(self) -> str:
        return self.name.render()

    #: True when the surname could belong to more than one origin inventory,
    #: so the identity's origin label is not recoverable from its spelling.
    origin_ambiguous: bool = False

    def to_row(self) -> dict[str, object]:
        return {
            "identity_id": self.identity_id,
            "canonical": self.canonical,
            "origin": self.origin,
            "gender": self.gender,
            "template": "|".join(self.template),
            "n_tokens": len(self.name.tokens),
            "origin_ambiguous": self.origin_ambiguous,
        }


class IdentityAssembler:
    """Builds identities by sampling components into per-origin templates."""

    #: Origin sampling weights. Roughly ordered by speaker-population share,
    #: coarsely. Not a demographic estimate -- it exists so the corpus is not
    #: uniform across eleven categories, which no real population is.
    ORIGIN_WEIGHTS: ClassVar[dict[str, float]] = {
        "hindi_belt": 30.0,
        "arabic_persian": 14.0,
        "bengali": 10.0,
        "marathi": 8.0,
        "telugu": 8.0,
        "tamil": 7.0,
        "gujarati": 6.0,
        "punjabi": 6.0,
        "kannada": 5.0,
        "malayalam": 4.0,
        "odia": 2.0,
    }

    def __init__(self, *, origin_weights: dict[str, float] | None = None):
        self.origin_weights = dict(origin_weights or self.ORIGIN_WEIGHTS)
        self._ambiguous = inventory.ambiguous_forms()

    def assemble(self, rng: random.Random, index: int) -> Identity:
        origin = self._pick_origin(rng)
        gender = "m" if rng.random() < 0.5 else "f"
        template = self._pick_template(origin, rng)
        tokens = self._fill(template, origin, gender, rng)
        name = ParsedName(tuple(tokens))

        identity_id = self._make_id(name.render(), origin, index)
        ambiguous = any(
            t.role is TokenRole.SURNAME and t.text.lower() in self._ambiguous for t in tokens
        )
        return Identity(
            identity_id=identity_id,
            name=name,
            origin=origin,
            gender=gender,
            template=template,
            origin_ambiguous=ambiguous,
        )

    def assemble_many(self, count: int, rng: random.Random) -> list[Identity]:
        """Assemble ``count`` identities with distinct canonical forms.

        Duplicate canonical forms are dropped rather than kept, because two
        identities sharing a surface form would be labelled a negative pair
        with identical strings -- an unsatisfiable case that would depress
        every matcher's ceiling for reasons unrelated to Indic orthography.
        Legitimate high-frequency collisions are constructed deliberately in
        the hard-negative set instead, where they are labelled as such.
        """
        seen: set[str] = set()
        out: list[Identity] = []
        attempts = 0
        max_attempts = count * 40
        while len(out) < count and attempts < max_attempts:
            attempts += 1
            identity = self.assemble(rng, len(out))
            key = identity.canonical.lower()
            if key in seen:
                continue
            seen.add(key)
            out.append(identity)
        if len(out) < count:
            raise RuntimeError(
                f"only assembled {len(out)} of {count} distinct identities in "
                f"{attempts} attempts; the inventory is too small for this corpus size"
            )
        return out

    # -- internals -------------------------------------------------------

    def _pick_origin(self, rng: random.Random) -> str:
        items = sorted(self.origin_weights.items())
        total = sum(w for _, w in items)
        threshold = rng.random() * total
        cumulative = 0.0
        for origin, weight in items:
            cumulative += weight
            if cumulative >= threshold:
                return origin
        return items[-1][0]

    @staticmethod
    def _pick_template(origin: str, rng: random.Random) -> tuple[str, ...]:
        options = TEMPLATES.get(origin, _DEFAULT_TEMPLATE)
        total = sum(w for w, _ in options)
        threshold = rng.random() * total
        cumulative = 0.0
        for weight, slots in options:
            cumulative += weight
            if cumulative >= threshold:
                return slots
        return options[-1][1]

    def _fill(
        self, template: tuple[str, ...], origin: str, gender: str, rng: random.Random
    ) -> list[Token]:
        tokens: list[Token] = []
        used: set[str] = set()

        for slot in template:
            component = self._sample_slot(slot, origin, gender, rng, used)
            if component is None:
                continue
            used.add(component.form.lower())
            tokens.append(self._to_token(slot, component, origin))

        # A template can degenerate if the inventory lacks a needed component.
        if not tokens:
            fallback = weighted_choice(components_for(GIVEN, origin, gender), rng)
            tokens.append(Token(fallback.form, TokenRole.GIVEN, origin=origin))
        return tokens

    @staticmethod
    def _sample_slot(
        slot: str, origin: str, gender: str, rng: random.Random, used: set[str]
    ) -> Component | None:
        if slot in ("given", "given2"):
            pool = components_for(GIVEN, origin, gender)
        elif slot in ("initial", "patronymic"):
            # A patronymic is a given name in a leading slot: it is the
            # father's personal name, drawn from the male given inventory
            # regardless of the identity's own gender.
            pool = components_for(GIVEN, origin, "m")
        elif slot == "surname":
            pool = components_for(SURNAME, origin)
        elif slot == "lowinfo":
            pool = components_for(LOW_INFORMATION, origin, gender)
        elif slot == "suffix":
            pool = ()
        else:
            pool = ()

        if slot == "suffix":
            # Singh / Kaur are gendered and origin-bound; handled directly
            # rather than through the component inventory.
            form = "Kaur" if gender == "f" else "Singh"
            return Component(form, "suffix", origin, 1, gender)

        pool = tuple(c for c in pool if c.form.lower() not in used)
        if not pool:
            return None
        return weighted_choice(pool, rng)

    @staticmethod
    def _to_token(slot: str, component: Component, origin: str) -> Token:
        component_origin = origin if component.origin == "*" else component.origin
        if slot == "initial":
            return Token(
                component.form[0].upper() + ".",
                TokenRole.INITIAL,
                origin=component_origin,
                expands_to=component.form,
            )
        role = {
            "given": TokenRole.GIVEN,
            "given2": TokenRole.MIDDLE,
            "surname": TokenRole.SURNAME,
            "lowinfo": TokenRole.MIDDLE,
            "patronymic": TokenRole.PATRONYMIC,
            "suffix": TokenRole.SUFFIX,
        }[slot]
        return Token(component.form, role, origin=component_origin)

    @staticmethod
    def _make_id(canonical: str, origin: str, index: int) -> str:
        digest = hashlib.sha1(
            f"{origin}|{canonical}|{index}".encode()
        ).hexdigest()[:12]
        return f"id_{digest}"

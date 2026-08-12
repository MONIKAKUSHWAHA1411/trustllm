"""Negative pair construction.

The negatives decide whether this benchmark is taken seriously. Positives are
easy to generate and easy to argue about; a benchmark whose negatives are
random unrelated names measures nothing, because every method separates
"Rahul Sharma" from "Venkatesh Iyer" and the reported precision is an artefact
of the sampling.

Five hard-negative constructions are implemented, each tagged so the Phase 4
breakdown can report them separately. They are not equally hard, and that is
deliberate -- the point is to find where each algorithm's discrimination fails,
not to produce one aggregate difficulty number.

One of them, ``identical_collision``, is unsatisfiable by name alone and is
excluded from headline metrics by default. See :class:`HardNegativeType`.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from enum import Enum

from .names import ParsedName, Token, TokenRole
from .seeds import inventory
from .seeds.assemble import Identity
from .seeds.inventory import GIVEN, SURNAME, components_for, weighted_choice


class HardNegativeType(str, Enum):
    """Constructions for genuinely confusable distinct people."""

    #: Ramesh Kumar Sharma vs Ramesh Kumar Verma. Everything matches but the
    #: surname; token-set and phonetic methods that weight all tokens equally
    #: score these very high.
    SAME_GIVEN_DIFF_SURNAME = "same_given_diff_surname"

    #: Suresh Reddy vs Ramesh Reddy. Both given names high-frequency, so the
    #: distinguishing token is the one with the least information content.
    SAME_SURNAME_DIFF_GIVEN = "same_surname_diff_given"

    #: R. Venkatesh vs R. Venkatesh where the initials expand differently
    #: (Ramachandran vs Rajagopal). Under South Indian conventions the initial
    #: carries the patronymic, so two different people share a surface form
    #: that differs only in information that was discarded at data entry.
    SHARED_INITIALS = "shared_initials"

    #: Gurpreet Singh vs Gurpreet Kaur Singh. Differ only by a community
    #: suffix. Any matcher that strips affixes to reduce false negatives
    #: merges these; any matcher that keeps them splits genuine matches.
    SUFFIX_ONLY_DIFFERENCE = "suffix_only_difference"

    #: The same full name, legitimately belonging to different people. There
    #: are tens of thousands of distinct people named "Mohammed Ali" and
    #: "Ramesh Kumar".
    #:
    #: EXCLUDED FROM HEADLINE METRICS BY DEFAULT. The two strings are
    #: identical, so no name-only method can separate them at any threshold --
    #: including a perfect one. Their proportion in the negative set therefore
    #: sets a hard ceiling on precision that says nothing about the algorithm.
    #: They are generated and reported on their own because the ceiling is a
    #: real operational fact (it is why screening needs date of birth and
    #: address), but folding them into the aggregate would make every matcher
    #: look worse by an amount determined purely by a sampling choice.
    IDENTICAL_COLLISION = "identical_collision"


#: Types included in headline metrics.
DISCRIMINABLE_TYPES: tuple[HardNegativeType, ...] = (
    HardNegativeType.SAME_GIVEN_DIFF_SURNAME,
    HardNegativeType.SAME_SURNAME_DIFF_GIVEN,
    HardNegativeType.SHARED_INITIALS,
    HardNegativeType.SUFFIX_ONLY_DIFFERENCE,
)


@dataclass(frozen=True, slots=True)
class NegativePair:
    """Two names belonging to different people."""

    left: str
    right: str
    subtype: str
    origin_left: str
    origin_right: str
    #: True when no name-only method can separate the pair even in principle.
    unsatisfiable: bool = False

    def to_row(self) -> dict[str, object]:
        return {
            "left": self.left,
            "right": self.right,
            "label": 0,
            "pair_type": "easy_negative" if self.subtype == "easy" else "hard_negative",
            "subtype": self.subtype,
            "severity": 0,
            "origin_left": self.origin_left,
            "origin_right": self.origin_right,
            "unsatisfiable": self.unsatisfiable,
        }


class HardNegativeBuilder:
    """Constructs confusable pairs of distinct identities."""

    def __init__(self, identities: list[Identity]):
        self.identities = identities
        self._by_origin: dict[str, list[Identity]] = {}
        for identity in identities:
            self._by_origin.setdefault(identity.origin, []).append(identity)

    # -- public ----------------------------------------------------------

    def build(
        self, subtype: HardNegativeType, count: int, rng: random.Random
    ) -> list[NegativePair]:
        builder = {
            HardNegativeType.SAME_GIVEN_DIFF_SURNAME: self._same_given_diff_surname,
            HardNegativeType.SAME_SURNAME_DIFF_GIVEN: self._same_surname_diff_given,
            HardNegativeType.SHARED_INITIALS: self._shared_initials,
            HardNegativeType.SUFFIX_ONLY_DIFFERENCE: self._suffix_only_difference,
            HardNegativeType.IDENTICAL_COLLISION: self._identical_collision,
        }[subtype]

        out: list[NegativePair] = []
        attempts = 0
        while len(out) < count and attempts < count * 30:
            attempts += 1
            pair = builder(rng)
            if pair is None:
                continue
            # A "hard negative" whose two sides are the same string is only
            # legitimate for the identical-collision type; anywhere else it is
            # a construction bug.
            if pair.left == pair.right and not pair.unsatisfiable:
                continue
            out.append(pair)
        return out

    def build_easy(self, count: int, rng: random.Random) -> list[NegativePair]:
        """Unrelated names, for calibration.

        Drawn across origins so that the easy set is genuinely easy; drawing
        within an origin would produce accidental hard negatives and blur the
        contrast the easy set exists to provide.
        """
        out: list[NegativePair] = []
        attempts = 0
        while len(out) < count and attempts < count * 30:
            attempts += 1
            a = self.identities[rng.randrange(len(self.identities))]
            b = self.identities[rng.randrange(len(self.identities))]
            if a.identity_id == b.identity_id or a.origin == b.origin:
                continue
            if a.canonical == b.canonical:
                continue
            out.append(
                NegativePair(a.canonical, b.canonical, "easy", a.origin, b.origin)
            )
        return out

    # -- constructions ---------------------------------------------------

    def _same_given_diff_surname(self, rng: random.Random) -> NegativePair | None:
        base = self._pick_with_role(TokenRole.SURNAME, rng)
        if base is None:
            return None
        index = base.name.first_index(TokenRole.SURNAME)
        assert index is not None

        pool = components_for(SURNAME, base.origin)
        pool = tuple(c for c in pool if c.form.lower() != base.name.tokens[index].text.lower())
        if not pool:
            return None
        replacement = weighted_choice(pool, rng)
        other = base.name.replace_text(index, replacement.form)
        return NegativePair(
            base.canonical,
            other.render(),
            HardNegativeType.SAME_GIVEN_DIFF_SURNAME.value,
            base.origin,
            base.origin,
        )

    def _same_surname_diff_given(self, rng: random.Random) -> NegativePair | None:
        # Requires an actual surname. Without this the construction fires on
        # initial-led Dravidian names that have no family name at all, turning
        # "B. Sundaram" into "B. Ramesh" -- which is a different confusion
        # entirely and does not belong under this label.
        candidates = [
            i
            for i in self.identities
            if i.name.first_index(TokenRole.GIVEN) is not None
            and i.name.first_index(TokenRole.SURNAME) is not None
        ]
        if not candidates:
            return None
        base = candidates[rng.randrange(len(candidates))]
        index = base.name.first_index(TokenRole.GIVEN)
        assert index is not None

        # Both given names must be high-frequency: the construction is about
        # two common names colliding, not a common one against a rare one.
        pool = tuple(
            c
            for c in components_for(GIVEN, base.origin, base.gender)
            if c.tier <= 2 and c.form.lower() != base.name.tokens[index].text.lower()
        )
        if not pool:
            return None
        replacement = weighted_choice(pool, rng)
        other = base.name.replace_text(index, replacement.form)
        return NegativePair(
            base.canonical,
            other.render(),
            HardNegativeType.SAME_SURNAME_DIFF_GIVEN.value,
            base.origin,
            base.origin,
        )

    def _shared_initials(self, rng: random.Random) -> NegativePair | None:
        """One person's initialled record against a different person's expanded one.

        Left is "R. Venkatesh" (Ramachandran Venkatesh, initialled at data
        entry). Right is "Rajagopal Venkatesh" -- a different person whose
        patronymic happens to start with the same letter.

        Initialling *both* sides was the first construction tried, and it is
        wrong: the two strings come out identical, which duplicates
        ``identical_collision`` and makes the type unsatisfiable rather than
        hard. The asymmetric form is the one that discriminates. A matcher
        should be able to decline it -- the strings do differ -- but only by
        being appropriately unwilling to expand an initial to whatever fits,
        which is precisely the behaviour worth measuring.
        """
        candidates = [
            i
            for i in self.identities
            if i.origin in ("tamil", "telugu", "kannada", "malayalam")
            and len(i.name.tokens) >= 2
        ]
        if not candidates:
            return None
        base = candidates[rng.randrange(len(candidates))]

        lead = base.name.tokens[0]
        expansion = lead.expands_to or lead.text
        letter = expansion[0].upper()

        pool = tuple(
            c
            for c in components_for(GIVEN, base.origin, "m")
            if c.form[0].upper() == letter and c.form.lower() != expansion.lower()
        )
        if not pool:
            return None
        alternative = weighted_choice(pool, rng)

        left = base.name.replace_token(
            0,
            Token(
                f"{letter}.",
                TokenRole.INITIAL,
                origin=base.origin,
                expands_to=expansion,
            ),
        )
        right = base.name.replace_token(
            0, Token(alternative.form, TokenRole.PATRONYMIC, origin=base.origin)
        )
        return NegativePair(
            left.render(),
            right.render(),
            HardNegativeType.SHARED_INITIALS.value,
            base.origin,
            base.origin,
        )

    def _suffix_only_difference(self, rng: random.Random) -> NegativePair | None:
        candidates = [
            i
            for i in self.identities
            if any(t.role is TokenRole.SUFFIX for t in i.name.tokens)
        ]
        if not candidates:
            return None
        base = candidates[rng.randrange(len(candidates))]
        index = base.name.first_index(TokenRole.SUFFIX)
        assert index is not None

        if len(base.name.tokens) <= 1:
            return None
        without = base.name.remove_token(index)
        return NegativePair(
            base.canonical,
            without.render(),
            HardNegativeType.SUFFIX_ONLY_DIFFERENCE.value,
            base.origin,
            base.origin,
        )

    def _identical_collision(self, rng: random.Random) -> NegativePair | None:
        """The same high-frequency full name held by two different people.

        Constructed from tier-1 components only, because that is what makes the
        collision realistic: "Ramesh Kumar" collides because both halves are
        extremely common, not because of any orthographic effect.
        """
        origins = sorted(self._by_origin)
        origin = origins[rng.randrange(len(origins))]
        given_pool = tuple(c for c in components_for(GIVEN, origin, "m") if c.tier == 1)
        surname_pool = tuple(c for c in components_for(SURNAME, origin) if c.tier == 1)
        if not given_pool or not surname_pool:
            return None
        given = weighted_choice(given_pool, rng)
        surname = weighted_choice(surname_pool, rng)
        name = ParsedName.of(
            Token(given.form, TokenRole.GIVEN, origin=origin),
            Token(surname.form, TokenRole.SURNAME, origin=origin),
        ).render()
        return NegativePair(
            name,
            name,
            HardNegativeType.IDENTICAL_COLLISION.value,
            origin,
            origin,
            unsatisfiable=True,
        )

    # -- helpers ---------------------------------------------------------

    def _pick_with_role(self, role: TokenRole, rng: random.Random) -> Identity | None:
        candidates = [i for i in self.identities if i.name.first_index(role) is not None]
        if not candidates:
            return None
        return candidates[rng.randrange(len(candidates))]


def ambiguity_note() -> str:
    """One-line caveat for reports that stratify by origin."""
    return (
        f"{len(inventory.ambiguous_forms())} surnames in the inventory appear under "
        "more than one origin category; identities using them carry origin_ambiguous=True."
    )

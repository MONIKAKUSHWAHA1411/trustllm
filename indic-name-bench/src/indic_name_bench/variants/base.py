"""Transformation framework and the variant generator.

Design commitments, all of which exist to keep downstream numbers defensible:

1.  Every transformation declares a stable ``family`` and ``rule_id``, and
    every application is recorded with its before/after text. The
    per-transformation breakdown in Phase 4 is a groupby over these records;
    if a transform ever fails to record itself, the breakdown silently
    misattributes and the whole analysis is worthless. Applying a transform
    without emitting a record is therefore a bug, not an optimisation.

2.  Transformations are *pure functions of (input, rng)*. No module-level
    state, no clocks, no set iteration order. Given the same seed and config
    the corpus is byte-identical.

3.  A transform returns ``None`` when it does not apply, rather than silently
    returning its input unchanged. Without this the generator cannot tell
    "severity 5 was requested and delivered" from "severity 5 was requested
    and three of the five transforms were no-ops", and severity stops meaning
    anything.
"""

from __future__ import annotations

import random
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import ClassVar, Generic, TypeVar

from ..names import ParsedName
from ..util import normalised_edit_distance


class Level(str, Enum):
    """Which stage of the pipeline a transformation operates at."""

    TOKEN = "token"
    STRING = "string"


class Family(str, Enum):
    """Transformation families.

    These are the units of the per-transformation analysis, so they are
    deliberately coarse enough to have a decent sample size in each cell and
    fine enough that "this family breaks this algorithm" is an actionable
    statement.
    """

    TRANSLITERATION = "transliteration"
    ARABIC_PERSIAN = "arabic_persian"
    BENGALI_ANGLICISATION = "bengali_anglicisation"
    STRUCTURE = "structure"
    AFFIX = "affix"
    NOISE = "noise"
    CROSS_SCRIPT = "cross_script"


@dataclass(frozen=True, slots=True)
class TransformationRecord:
    """Provenance for a single applied transformation."""

    family: str
    rule_id: str
    before: str
    after: str

    def __str__(self) -> str:
        return f"{self.family}/{self.rule_id}: {self.before!r} -> {self.after!r}"


T = TypeVar("T", ParsedName, str)


class Transformation(ABC, Generic[T]):
    """Base class for all transformations.

    Subclasses set ``family``, ``rule_id`` and ``level``, and implement
    :meth:`apply`.
    """

    family: ClassVar[Family]
    rule_id: ClassVar[str]
    level: ClassVar[Level]

    #: Relative sampling weight within its family. Used to keep the corpus
    #: from being dominated by whichever rule happens to fire most often.
    weight: ClassVar[float] = 1.0

    @abstractmethod
    def apply(self, obj: T, rng: random.Random) -> tuple[T, TransformationRecord] | None:
        """Apply the transformation.

        Returns the transformed object and a provenance record, or ``None`` if
        this transformation does not apply to ``obj``.
        """

    def record(self, before: str, after: str) -> TransformationRecord:
        return TransformationRecord(
            family=self.family.value, rule_id=self.rule_id, before=before, after=after
        )

    @property
    def name(self) -> str:
        return f"{self.family.value}/{self.rule_id}"

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<{type(self).__name__} {self.name}>"


@dataclass(frozen=True, slots=True)
class GeneratedVariant:
    """A generated variant with full provenance."""

    text: str
    #: Identity this variant refers to.
    identity_id: str
    #: The identity's canonical surface form, for reference.
    canonical: str
    #: Severity actually achieved -- i.e. ``len(applied)``. May be lower than
    #: the severity requested when the name ran out of applicable transforms;
    #: always compare against this field, never against the request.
    severity: int
    #: Severity that was asked for. Kept so the shortfall rate is measurable.
    severity_requested: int
    applied: tuple[TransformationRecord, ...]
    script: str = "Latn"
    #: Normalised edit distance from the canonical form. Not used to construct
    #: anything -- recorded so that the relationship between *constructed*
    #: severity and *observed* surface distance can be checked rather than
    #: assumed. See the construct-validity section of METHODOLOGY.md.
    surface_distance: float = 0.0

    @property
    def families(self) -> tuple[str, ...]:
        seen: list[str] = []
        for r in self.applied:
            if r.family not in seen:
                seen.append(r.family)
        return tuple(seen)

    @property
    def rule_ids(self) -> tuple[str, ...]:
        return tuple(r.rule_id for r in self.applied)

    def to_row(self) -> dict[str, object]:
        """Flatten for a dataframe / JSONL corpus file."""
        return {
            "text": self.text,
            "identity_id": self.identity_id,
            "canonical": self.canonical,
            "severity": self.severity,
            "severity_requested": self.severity_requested,
            "families": "|".join(self.families),
            "rule_ids": "|".join(self.rule_ids),
            "n_transforms": len(self.applied),
            "script": self.script,
            "surface_distance": round(self.surface_distance, 4),
        }


@dataclass
class TransformRegistry:
    """The set of transformations available to a generator."""

    transforms: list[Transformation] = field(default_factory=list)

    def add(self, *transforms: Transformation) -> TransformRegistry:
        self.transforms.extend(transforms)
        return self

    def by_family(self, family: Family) -> list[Transformation]:
        return [t for t in self.transforms if t.family is family]

    def families(self) -> list[Family]:
        # Sorted for determinism; set iteration order is not stable across runs.
        return sorted({t.family for t in self.transforms}, key=lambda f: f.value)

    def excluding(self, *families: Family) -> TransformRegistry:
        drop = set(families)
        return TransformRegistry([t for t in self.transforms if t.family not in drop])

    def only(self, *families: Family) -> TransformRegistry:
        keep = set(families)
        return TransformRegistry([t for t in self.transforms if t.family in keep])

    def __len__(self) -> int:
        return len(self.transforms)


class VariantGenerator:
    """Generates variants at a requested severity.

    Severity semantics
    ------------------
    Severity is the number of *distinct transformation applications* stacked
    onto the seed, drawn preferentially from distinct families. It is an
    ordinal construction parameter, not a measured distance: severity 4 means
    "four rules fired", not "twice as different as severity 2". Two severity-3
    variants can sit at very different surface distances from their seed, and
    ``surface_distance`` is recorded on every variant so that readers can see
    the spread rather than take the ordinal at face value.

    This choice is defensible but not the only one available; the alternative
    of defining severity as a target edit-distance band is discussed, with
    reasons for rejecting it, in METHODOLOGY.md.
    """

    #: Severity ladder. Index i holds the number of transforms for severity i+1.
    SEVERITY_LEVELS: ClassVar[tuple[int, ...]] = (1, 2, 3, 4, 5)

    def __init__(self, registry: TransformRegistry, *, prefer_distinct_families: bool = True):
        if len(registry) == 0:
            raise ValueError("VariantGenerator needs at least one transformation")
        self.registry = registry
        self.prefer_distinct_families = prefer_distinct_families

    #: How many times to re-draw when a variant lands back on its seed.
    MAX_ATTEMPTS: ClassVar[int] = 8

    def generate(
        self,
        name: ParsedName,
        identity_id: str,
        severity: int,
        rng: random.Random,
        *,
        script: str = "Latn",
    ) -> GeneratedVariant:
        """Produce one variant of ``name`` at the requested severity.

        Rejects and re-draws when the result is identical to the seed. Rules
        come in inverse pairs -- aspirate collapse and insertion, vowel
        shortening and lengthening -- and sampling both cancels them out. That
        yields a variant recorded as severity 2 whose text is the seed, which
        is a zero-difficulty positive pair wearing a difficulty label. Rare
        (around 3% at severity 2) but worth removing rather than explaining.
        """
        if severity not in self.SEVERITY_LEVELS:
            raise ValueError(f"severity must be one of {self.SEVERITY_LEVELS}, got {severity}")

        variant = self._generate_once(name, identity_id, severity, rng, script)
        attempts = 1
        while variant.text == variant.canonical and attempts < self.MAX_ATTEMPTS:
            variant = self._generate_once(name, identity_id, severity, rng, script)
            attempts += 1
        return variant

    def _generate_once(
        self,
        name: ParsedName,
        identity_id: str,
        severity: int,
        rng: random.Random,
        script: str,
    ) -> GeneratedVariant:
        canonical = name.render()
        targets = self._choose(severity, rng)

        # Most transforms do not apply to most names -- Bengali anglicisation
        # needs a Bengali surname, Abdul restructuring needs an Abdul compound.
        # Applying only the sampled targets therefore leaves the majority of
        # severity-1 requests with zero transforms applied, producing variants
        # identical to their seed. Those are not easy positives, they are
        # degenerate ones, and enough of them would lift every matcher's
        # apparent recall for free.
        #
        # So each target is a *first choice*, backed by the rest of the pool as
        # fallbacks. The split between token- and string-level slots is fixed
        # from the sampled targets before any fallback runs, which keeps the
        # family mix roughly as sampled instead of letting the larger
        # token-level pool absorb the whole quota.
        string_slots = sum(1 for t in targets if t.level is Level.STRING)
        token_slots = severity - string_slots

        token_order = self._fallback_order(targets, Level.TOKEN, rng)
        string_order = self._fallback_order(targets, Level.STRING, rng)

        applied: list[TransformationRecord] = []
        current_name = name
        for transform in token_order:
            if len(applied) >= token_slots:
                break
            result = transform.apply(current_name, rng)
            if result is not None:
                current_name, record = result
                applied.append(record)
        token_applied = len(applied)

        text = current_name.render()
        for transform in string_order:
            if len(applied) - token_applied >= string_slots:
                break
            result = transform.apply(text, rng)
            if result is not None:
                text, record = result
                applied.append(record)

        # If one level ran dry, let the other make up the shortfall rather than
        # silently under-delivering the requested severity.
        if len(applied) < severity:
            for transform in string_order:
                if len(applied) >= severity:
                    break
                result = transform.apply(text, rng)
                if result is not None:
                    text, record = result
                    applied.append(record)

        return GeneratedVariant(
            text=text,
            identity_id=identity_id,
            canonical=canonical,
            severity=len(applied),
            severity_requested=severity,
            applied=tuple(applied),
            script=script,
            surface_distance=normalised_edit_distance(canonical, text),
        )

    def _fallback_order(
        self, targets: list[Transformation], level: Level, rng: random.Random
    ) -> list[Transformation]:
        """Transforms of ``level``: sampled targets first, then the rest.

        The tail is weighted-shuffled rather than left in registry order, so a
        rule's position in the source file has no effect on how often it ends
        up in the corpus.
        """
        chosen = [t for t in targets if t.level is level]
        rest = [t for t in self.registry.transforms if t.level is level and t not in chosen]
        return chosen + self._weighted_sample(rest, len(rest), rng)

    def _choose(self, severity: int, rng: random.Random) -> list[Transformation]:
        """Sample ``severity`` transformations, spreading across families.

        Sampling without replacement within a family: applying the same rule
        twice is either a no-op or double-counts in the per-rule breakdown.
        """
        pool = list(self.registry.transforms)
        if not self.prefer_distinct_families:
            k = min(severity, len(pool))
            return self._weighted_sample(pool, k, rng)

        by_family: dict[Family, list[Transformation]] = {}
        for t in pool:
            by_family.setdefault(t.family, []).append(t)

        # Deterministic family order before shuffling, so the rng fully
        # determines the outcome regardless of dict construction order.
        families = sorted(by_family, key=lambda f: f.value)
        rng.shuffle(families)

        chosen: list[Transformation] = []
        # First pass: one transform per distinct family, round-robin.
        for family in families:
            if len(chosen) >= severity:
                break
            chosen.extend(self._weighted_sample(by_family[family], 1, rng))

        # Second pass: if severity exceeds the family count, take extras
        # without repeating a rule already chosen.
        if len(chosen) < severity:
            remaining = [t for t in pool if t not in chosen]
            chosen.extend(self._weighted_sample(remaining, severity - len(chosen), rng))

        return chosen[:severity]

    @staticmethod
    def _weighted_sample(
        pool: list[Transformation], k: int, rng: random.Random
    ) -> list[Transformation]:
        """Sample ``k`` distinct transforms weighted by ``Transformation.weight``."""
        k = min(k, len(pool))
        if k <= 0:
            return []
        remaining = list(pool)
        picked: list[Transformation] = []
        for _ in range(k):
            total = sum(t.weight for t in remaining)
            if total <= 0:
                picked.extend(remaining[:1])
                break
            threshold = rng.random() * total
            cumulative = 0.0
            for i, t in enumerate(remaining):
                cumulative += t.weight
                if cumulative >= threshold:
                    picked.append(remaining.pop(i))
                    break
        return picked

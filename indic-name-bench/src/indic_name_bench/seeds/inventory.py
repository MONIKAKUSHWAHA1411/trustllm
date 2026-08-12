"""Loads the name-component inventory and exposes weighted sampling over it.

What this is and is not
-----------------------
The inventory is a list of name *components* -- given names, surnames,
honorifics, suffixes -- tagged with an origin category and an ordinal frequency
tier. It contains no people. Nothing in it was derived from a register,
electoral roll, leak, social network, or any other record of individuals, and
no combination of entries corresponds to a known person except by coincidence,
in the same way that any list of common first and last names does.

This is a deliberate change from seeding the corpus with names taken off
sanctions lists. Sanctions lists name real individuals; assembling and
redistributing a derived variant corpus from them would produce something that
functions as a screening list, which the project's data-ethics rules forbid.
Loaders for those lists ship in ``seeds/sanctions.py`` for users who want to
regenerate against them locally, and their output is never committed.

Frequency tiers
---------------
Tiers are hand-assigned ordinal judgements, not measured counts -- no openly
licensed Indian name-frequency corpus was reachable when the inventory was
built. They control sampling weight only. Any finding that turns on the precise
shape of the frequency distribution should be read as provisional; see the
limitations section of ``reports/findings.md``.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from functools import lru_cache

from ..data_loader import seeds

#: Component kinds.
GIVEN = "given"
SURNAME = "surname"
LOW_INFORMATION = "low_information"


@dataclass(frozen=True, slots=True)
class Component:
    """One name component."""

    form: str
    kind: str
    origin: str
    tier: int
    gender: str  # "m", "f", or "n" (neutral / unspecified)

    @property
    def weight(self) -> float:
        return TIER_WEIGHTS[self.tier]


@lru_cache(maxsize=1)
def _origins_config() -> dict:
    return seeds("origins.yaml")


@lru_cache(maxsize=1)
def _tier_weights() -> dict[int, float]:
    return {int(k): float(v["weight"]) for k, v in _origins_config()["tiers"].items()}


TIER_WEIGHTS: dict[int, float] = _tier_weights()


@lru_cache(maxsize=1)
def origin_ids() -> tuple[str, ...]:
    return tuple(c["id"] for c in _origins_config()["categories"])


@lru_cache(maxsize=1)
def origin_labels() -> dict[str, str]:
    return {c["id"]: c["label"] for c in _origins_config()["categories"]}


#: Optional tier override, keyed by ``(form.lower(), kind, origin)``.
#:
#: Exists for the tier-sensitivity analysis. The frequency tiers in the YAML are
#: hand-assigned ordinal judgements, and several reported results -- the
#: per-origin false-positive disparity above all -- depend on the collision
#: structure those tiers produce. Rather than assert the tiers are right, the
#: analysis perturbs them and measures whether the findings survive. See
#: ``benchmarks/tier_sensitivity.py``.
_TIER_OVERRIDE: dict[tuple[str, str, str], int] | None = None


def set_tier_override(mapping: dict[tuple[str, str, str], int] | None) -> None:
    """Install a tier override and invalidate every dependent cache.

    Invalidation matters more than it looks: ``load_components``,
    ``components_for`` and ``ambiguous_forms`` are all cached, and a stale cache
    would silently return unperturbed components, making a sensitivity analysis
    report that nothing changed. That is exactly the failure mode that would be
    read as a reassuring result.
    """
    global _TIER_OVERRIDE
    _TIER_OVERRIDE = dict(mapping) if mapping else None
    load_components.cache_clear()
    components_for.cache_clear()
    ambiguous_forms.cache_clear()


def clear_tier_override() -> None:
    set_tier_override(None)


@lru_cache(maxsize=1)
def load_components() -> tuple[Component, ...]:
    """Flatten the YAML inventories into a single component list."""
    out: list[Component] = []

    given = seeds("given_names.yaml")
    for origin, by_gender in given.items():
        if origin == "version" or not isinstance(by_gender, dict):
            continue
        kind = LOW_INFORMATION if origin == "low_information" else GIVEN
        resolved_origin = "*" if origin == "low_information" else origin
        for gender_key, by_tier in by_gender.items():
            gender = {"male": "m", "female": "f", "neutral": "n"}.get(gender_key, "n")
            for tier, forms in by_tier.items():
                for form in forms:
                    out.append(
                        Component(
                            form,
                            kind,
                            resolved_origin,
                            _resolve_tier(form, kind, resolved_origin, int(tier)),
                            gender,
                        )
                    )

    surnames = seeds("surnames.yaml")
    for origin, by_tier in surnames.items():
        if origin in ("version", "bengali_anglicisation_pairs"):
            continue
        if not isinstance(by_tier, dict):
            continue
        for tier, forms in by_tier.items():
            for form in forms:
                out.append(
                    Component(
                        form,
                        SURNAME,
                        origin,
                        _resolve_tier(form, SURNAME, origin, int(tier)),
                        "n",
                    )
                )

    return tuple(out)


def _resolve_tier(form: str, kind: str, origin: str, declared: int) -> int:
    if _TIER_OVERRIDE is None:
        return declared
    return _TIER_OVERRIDE.get((form.lower(), kind, origin), declared)


#: Origins that do not take the Sanskritic low-information filler tokens.
#: "Ali Ibrahim Kumar" is not a name that occurs; Kumar, Devi, Lal and Nath
#: belong to Hindu naming conventions. Letting the wildcard tokens attach to
#: Arabic/Persian identities would inflate their token counts and hand them
#: extra shared low-information tokens, which is precisely the mechanism the
#: fairness analysis is trying to measure honestly.
NO_SANSKRITIC_FILLER: frozenset[str] = frozenset({"arabic_persian"})


@lru_cache(maxsize=None)
def components_for(kind: str, origin: str, gender: str | None = None) -> tuple[Component, ...]:
    """Components of a kind for an origin, optionally filtered by gender.

    Wildcard-origin components (the low-information tokens) are returned for
    every origin except those in :data:`NO_SANSKRITIC_FILLER`.
    """
    out = []
    for c in load_components():
        if c.kind != kind:
            continue
        if c.origin not in (origin, "*"):
            continue
        if c.origin == "*" and origin in NO_SANSKRITIC_FILLER:
            continue
        if gender is not None and c.gender not in (gender, "n"):
            continue
        out.append(c)
    return tuple(out)


@lru_cache(maxsize=1)
def ambiguous_forms() -> frozenset[str]:
    """Surname forms that appear under more than one origin.

    Reported alongside the fairness results: a name in this set cannot be
    attributed to an origin category from its spelling, so any per-origin
    disparity computed over it inherits that uncertainty.
    """
    by_form: dict[str, set[str]] = {}
    for c in load_components():
        if c.kind != SURNAME:
            continue
        by_form.setdefault(c.form.lower(), set()).add(c.origin)
    return frozenset(f for f, origins in by_form.items() if len(origins) > 1)


def weighted_choice(pool: tuple[Component, ...], rng: random.Random) -> Component:
    """Pick one component with probability proportional to its tier weight."""
    if not pool:
        raise ValueError("cannot sample from an empty component pool")
    total = sum(c.weight for c in pool)
    threshold = rng.random() * total
    cumulative = 0.0
    for c in pool:
        cumulative += c.weight
        if cumulative >= threshold:
            return c
    return pool[-1]


def inventory_summary() -> dict[str, object]:
    """Counts for the corpus datasheet in DATA_SOURCES.md."""
    components = load_components()
    by_kind: dict[str, int] = {}
    by_origin: dict[str, int] = {}
    for c in components:
        by_kind[c.kind] = by_kind.get(c.kind, 0) + 1
        by_origin[c.origin] = by_origin.get(c.origin, 0) + 1
    return {
        "total_components": len(components),
        "by_kind": dict(sorted(by_kind.items())),
        "by_origin": dict(sorted(by_origin.items())),
        "distinct_forms": len({c.form.lower() for c in components}),
        "origin_ambiguous_surnames": len(ambiguous_forms()),
    }

"""Variant generation: transformation families and the generator."""

from __future__ import annotations

from . import affix, bengali, cross_script, lexical, noise, structure, transliteration
from .base import (
    Family,
    GeneratedVariant,
    Level,
    Transformation,
    TransformationRecord,
    TransformRegistry,
    VariantGenerator,
)
from .substitution import Scope, StringSubstitution, TokenSubstitution

__all__ = [
    "Family",
    "GeneratedVariant",
    "Level",
    "Scope",
    "StringSubstitution",
    "TokenSubstitution",
    "Transformation",
    "TransformRegistry",
    "TransformationRecord",
    "VariantGenerator",
    "default_registry",
]


def default_registry(*, include_cross_script: bool = True) -> TransformRegistry:
    """The full transformation set used by the released corpus.

    ``include_cross_script`` is a switch rather than a default-on because
    cross-script variants make every Latin-only matcher score zero, which
    swamps the aggregate numbers. The released corpus generates them into a
    separate split so that the main results stay interpretable and the
    cross-script floor is reported on its own.
    """
    registry = TransformRegistry()
    registry.add(*transliteration.build())
    registry.add(*lexical.build())
    registry.add(*bengali.build())
    registry.add(*structure.build())
    registry.add(*affix.build())
    registry.add(*noise.build())
    if include_cross_script:
        registry.add(*cross_script.build())
    return registry

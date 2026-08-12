"""Character-substitution transformation machinery.

Most orthographic variation is expressible as "rewrite this digraph as that
one". The interesting design question is *scope*: when a name contains three
sites where a rule could fire, does one fire or all three?

Both answers are right for different phenomena, so scope is explicit per rule:

``Scope.ALL``
    Models a consistent transliterator. A person who writes "Batt" for "Bhatt"
    is following a personal romanisation convention and will drop the other
    aspirates in the same name too. Transliteration rules use this.

``Scope.ONE``
    Models a local accident or a one-off hypercorrection. Typos, OCR damage
    and over-applied aspirates hit a single site. Noise rules use this.

Getting this wrong would distort the degradation curve: ALL-scope rules make
severity 1 a larger perturbation on long names than on short ones, which is
real, and ONE-scope rules keep it constant, which is also real. Conflating them
would make severity mean different things in different families without saying
so.
"""

from __future__ import annotations

import random
import re
from enum import Enum
from typing import ClassVar

from ..names import DISTINGUISHING_ROLES, ParsedName, TokenRole
from .base import Level, Transformation, TransformationRecord


class Scope(str, Enum):
    ALL = "all"
    ONE = "one"


def recase_like(original: str, transformed: str) -> str:
    """Restore the leading-capital convention of ``original`` onto ``transformed``."""
    if not transformed:
        return transformed
    if original[:1].isupper():
        return transformed[:1].upper() + transformed[1:]
    return transformed


class TokenSubstitution(Transformation[ParsedName]):
    """Applies ordered regex rewrites to eligible tokens.

    Patterns are matched case-insensitively against the lowercased token and
    the original capitalisation is restored afterwards, so rules can be written
    in lowercase without worrying about title case.
    """

    level: ClassVar[Level] = Level.TOKEN

    #: Ordered ``(pattern, replacement)`` pairs. Order matters: earlier rules
    #: see the token first, so longer patterns must precede their prefixes.
    patterns: ClassVar[tuple[tuple[str, str], ...]] = ()
    scope: ClassVar[Scope] = Scope.ALL
    #: Which token roles the rule may touch. Defaults to identity-bearing
    #: tokens: rewriting the spelling of an honorific is a different
    #: phenomenon and belongs to the affix family.
    roles: ClassVar[frozenset[TokenRole]] = frozenset(DISTINGUISHING_ROLES)
    #: Minimum token length. Guards against mangling initials and two-letter
    #: tokens into unrecognisable stubs.
    min_length: ClassVar[int] = 3
    #: Origin categories the rule must not touch. Sanskritic processes (schwa
    #: deletion and retention, ksha/x) have no purchase on Arabic- and
    #: Persian-origin names: Mohammed does not become "Mohammeda". Applying
    #: them anyway would manufacture a variant-density difference between
    #: communities out of a modelling error -- and since community-level
    #: variant density is precisely what the fairness analysis measures, that
    #: error would masquerade as the headline finding.
    exclude_origins: ClassVar[frozenset[str]] = frozenset()

    def apply(
        self, obj: ParsedName, rng: random.Random
    ) -> tuple[ParsedName, TransformationRecord] | None:
        # For ONE scope the pattern order is shuffled per application. Without
        # this the first listed pattern always wins and the rule degenerates to
        # a single rewrite, which would quietly starve the corpus of variety in
        # exactly the families that need it most.
        patterns = list(self.patterns)
        if self.scope is Scope.ONE:
            rng.shuffle(patterns)

        candidates = self._candidates(obj, patterns)
        if not candidates:
            return None

        if self.scope is Scope.ONE:
            candidates = [candidates[rng.randrange(len(candidates))]]

        before = obj.render()
        result = obj
        for index, new_text in candidates:
            result = result.replace_text(index, new_text)
        after = result.render()
        if after == before:
            return None
        return result, self.record(before, after)

    def _candidates(
        self, name: ParsedName, patterns: list[tuple[str, str]]
    ) -> list[tuple[int, str]]:
        out: list[tuple[int, str]] = []
        for i, token in enumerate(name.tokens):
            if token.role not in self.roles:
                continue
            if len(token.text) < self.min_length:
                continue
            if token.origin is not None and token.origin in self.exclude_origins:
                continue
            rewritten = self._rewrite(token.text, patterns)
            if rewritten != token.text:
                out.append((i, rewritten))
        return out

    def _rewrite(self, text: str, patterns: list[tuple[str, str]]) -> str:
        lowered = text.lower()
        for pattern, replacement in patterns:
            if self.scope is Scope.ONE:
                lowered, n = re.subn(pattern, replacement, lowered, count=1)
                if n:
                    break
            else:
                lowered = re.sub(pattern, replacement, lowered)
        return recase_like(text, lowered)


class StringSubstitution(Transformation[str]):
    """Applies regex rewrites to the rendered name string.

    Used by rules that are indifferent to token structure -- OCR damage,
    keyboard slips, separator inconsistency.
    """

    level: ClassVar[Level] = Level.STRING

    patterns: ClassVar[tuple[tuple[str, str], ...]] = ()
    scope: ClassVar[Scope] = Scope.ONE

    def apply(self, obj: str, rng: random.Random) -> tuple[str, TransformationRecord] | None:
        applicable = [(p, r) for p, r in self.patterns if re.search(p, obj)]
        if not applicable:
            return None

        if self.scope is Scope.ONE:
            pattern, replacement = applicable[rng.randrange(len(applicable))]
            sites = list(re.finditer(pattern, obj))
            site = sites[rng.randrange(len(sites))]
            after = obj[: site.start()] + re.sub(pattern, replacement, site.group()) + obj[site.end() :]
        else:
            after = obj
            for pattern, replacement in applicable:
                after = re.sub(pattern, replacement, after)

        if after == obj:
            return None
        return after, self.record(obj, after)

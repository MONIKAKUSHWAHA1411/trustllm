"""Structured name representation.

The corpus pipeline has two stages, and this module defines the boundary
between them:

    ParsedName --[token-level transforms]--> ParsedName
             --render()--> str --[string-level transforms]--> str

Token-level transforms need to know that "Kumar" is sitting in a patronymic
slot rather than a surname slot, or that a token is an initial standing in for
a longer form. String-level transforms (OCR damage, keyboard slips, whitespace
and diacritic inconsistency) do not care about structure and would be clumsy to
express over tokens. Keeping the two apart is what makes the per-transformation
breakdown in Phase 4 interpretable: a failure attributable to `structure` is a
genuinely different phenomenon from one attributable to `noise`.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum


class TokenRole(str, Enum):
    """The slot a token occupies in a name.

    Roles are assigned at assembly time from the inventory the token was drawn
    from. They are not inferred from surface form, because that inference is
    exactly the thing being benchmarked -- a screening system cannot tell
    whether "Kumar" is a given name, a middle name, a surname or filler, and
    neither can we.
    """

    HONORIFIC = "honorific"
    GIVEN = "given"
    MIDDLE = "middle"
    SURNAME = "surname"
    INITIAL = "initial"
    PATRONYMIC = "patronymic"
    HOUSE_NAME = "house_name"
    SUFFIX = "suffix"
    QUALIFIER = "qualifier"
    UNKNOWN = "unknown"


#: Roles whose tokens carry identity-distinguishing information. Honorifics,
#: qualifiers and low-information suffixes are excluded: two records sharing
#: only these are not evidence of the same person.
DISTINGUISHING_ROLES = frozenset(
    {
        TokenRole.GIVEN,
        TokenRole.MIDDLE,
        TokenRole.SURNAME,
        TokenRole.PATRONYMIC,
        TokenRole.HOUSE_NAME,
    }
)


@dataclass(frozen=True, slots=True)
class Token:
    """A single whitespace-delimited unit of a name."""

    text: str
    role: TokenRole = TokenRole.UNKNOWN
    #: Origin category the token was drawn from, when known. Tokens belonging
    #: to several inventories keep the one chosen at assembly time; the
    #: ambiguity is tracked separately on the identity.
    origin: str | None = None
    #: For an INITIAL, the full form it abbreviates. Lets a later transform
    #: expand it back, and lets the evaluator know the expansion is recoverable
    #: in principle even when no matcher recovers it.
    expands_to: str | None = None

    def __post_init__(self) -> None:
        if not self.text:
            raise ValueError("Token text must be non-empty")

    def with_text(self, text: str) -> Token:
        return replace(self, text=text)

    @property
    def is_distinguishing(self) -> bool:
        return self.role in DISTINGUISHING_ROLES


@dataclass(frozen=True, slots=True)
class ParsedName:
    """An ordered sequence of role-tagged tokens."""

    tokens: tuple[Token, ...]

    def __post_init__(self) -> None:
        if not self.tokens:
            raise ValueError("ParsedName must have at least one token")

    # -- construction ----------------------------------------------------

    @classmethod
    def of(cls, *tokens: Token) -> ParsedName:
        return cls(tuple(tokens))

    @classmethod
    def from_string(cls, text: str, role: TokenRole = TokenRole.UNKNOWN) -> ParsedName:
        """Build an untagged name from a plain string.

        Used for seed names arriving from external lists, where no role
        information is available. Everything becomes UNKNOWN rather than being
        guessed at.
        """
        parts = text.split()
        if not parts:
            raise ValueError(f"Cannot parse empty name from {text!r}")
        return cls(tuple(Token(p, role) for p in parts))

    # -- rendering -------------------------------------------------------

    def render(self) -> str:
        """Surface form: tokens joined by single spaces.

        Deliberately dumb. Any punctuation a token needs (the period on an
        initial, the slash in "S/o") is carried in the token text itself, so
        that rendering never has to make a formatting decision a transform
        might want to control.
        """
        return " ".join(t.text for t in self.tokens)

    def __str__(self) -> str:
        return self.render()

    # -- queries ---------------------------------------------------------

    def indices_with_role(self, *roles: TokenRole) -> list[int]:
        wanted = set(roles)
        return [i for i, t in enumerate(self.tokens) if t.role in wanted]

    def distinguishing_indices(self) -> list[int]:
        return [i for i, t in enumerate(self.tokens) if t.is_distinguishing]

    def first_index(self, role: TokenRole) -> int | None:
        for i, t in enumerate(self.tokens):
            if t.role is role:
                return i
        return None

    @property
    def origins(self) -> tuple[str, ...]:
        seen: list[str] = []
        for t in self.tokens:
            if t.origin and t.origin not in seen:
                seen.append(t.origin)
        return tuple(seen)

    # -- edits (all return new instances) ---------------------------------

    def replace_token(self, index: int, token: Token) -> ParsedName:
        tokens = list(self.tokens)
        tokens[index] = token
        return ParsedName(tuple(tokens))

    def replace_text(self, index: int, text: str) -> ParsedName:
        return self.replace_token(index, self.tokens[index].with_text(text))

    def insert_token(self, index: int, token: Token) -> ParsedName:
        tokens = list(self.tokens)
        tokens.insert(index, token)
        return ParsedName(tuple(tokens))

    def remove_token(self, index: int) -> ParsedName:
        if len(self.tokens) <= 1:
            raise ValueError("Cannot remove the only token in a name")
        tokens = list(self.tokens)
        del tokens[index]
        return ParsedName(tuple(tokens))

    def swap_tokens(self, i: int, j: int) -> ParsedName:
        tokens = list(self.tokens)
        tokens[i], tokens[j] = tokens[j], tokens[i]
        return ParsedName(tuple(tokens))

    def merge_tokens(self, i: int, j: int, joiner: str = "") -> ParsedName:
        """Fuse two adjacent tokens into one (Ravi Shankar -> Ravishankar).

        Fusing without a joiner lowercases the second element, because that is
        how the fused form is actually written: Ravishankar, not RaviShankar.
        A hyphen keeps both capitals, since Ravi-Shankar is the attested
        hyphenated form.
        """
        if j != i + 1:
            raise ValueError(f"merge_tokens requires adjacent indices, got {i} and {j}")
        a, b = self.tokens[i], self.tokens[j]
        second = b.text if joiner else b.text[:1].lower() + b.text[1:]
        fused = Token(
            text=a.text + joiner + second,
            role=a.role if a.is_distinguishing else b.role,
            origin=a.origin or b.origin,
        )
        tokens = list(self.tokens)
        tokens[i : j + 1] = [fused]
        return ParsedName(tuple(tokens))

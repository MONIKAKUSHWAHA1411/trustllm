"""Transliteration variance.

Indic scripts encode phonemic distinctions that Latin script does not: a
four-way stop contrast (voiceless / voiceless aspirated / voiced / voiced
aspirated) at five places of articulation, a retroflex/dental series, and three
sibilants. Romanisation has to collapse these, and no single collapse ever
became standard. Two spellings of one name are therefore not "a typo and a
correct form" -- they are two equally valid readings of the same source.

Each rule below is stated as a directed rewrite. Both directions are provided
where both occur in practice, as separate rules, so that the per-transformation
breakdown can distinguish them.
"""

from __future__ import annotations

from typing import ClassVar

from .base import Family
from .substitution import Scope, TokenSubstitution

#: Sanskritic phonological processes do not apply to Arabic/Persian-origin
#: names. Rules carrying this exclusion skip those tokens entirely.
SANSKRITIC_ONLY = frozenset({"arabic_persian"})


class AspirateCollapse(TokenSubstitution):
    """Drop the aspiration marker: Bhatt -> Batt, Dhawan -> Dawan, Ghosh -> Gosh.

    ALL scope: a writer who drops one aspirate drops them all.
    Note ``sh`` is deliberately absent -- it is a sibilant, not an aspirated
    ``s``, and belongs to :class:`SibilantDeretroflex`.
    """

    family: ClassVar[Family] = Family.TRANSLITERATION
    rule_id: ClassVar[str] = "aspirate_collapse"
    scope: ClassVar[Scope] = Scope.ALL
    weight: ClassVar[float] = 2.0
    patterns: ClassVar[tuple[tuple[str, str], ...]] = (
        ("chh", "ch"),
        ("bh", "b"),
        ("dh", "d"),
        ("gh", "g"),
        ("jh", "j"),
        ("kh", "k"),
        ("ph", "p"),
        ("th", "t"),
    )


class AspirateInsertion(TokenSubstitution):
    """Hypercorrect an unaspirated stop: Batt -> Bhatt, Gosh -> Ghosh.

    ONE scope: inserting aspiration everywhere produces forms no writer
    generates. This models the single over-applied aspirate that shows up when
    someone "corrects" a spelling toward what they believe the Sanskritic form
    to be.

    Aspiration is only insertable at a syllable onset -- a stop that begins the
    word or sits between vowels. Firing inside a cluster or a geminate yields
    strings no romanisation system produces (``Bhatht``, ``Lakhshmi``,
    ``Sidhdiqui``), which would inflate every matcher's error rate against
    inputs that never occur in real data.
    """

    family: ClassVar[Family] = Family.TRANSLITERATION
    rule_id: ClassVar[str] = "aspirate_insertion"
    scope: ClassVar[Scope] = Scope.ONE
    patterns: ClassVar[tuple[tuple[str, str], ...]] = (
        ("(?<=[aeiou])b(?=[aeiou])", "bh"),
        ("(?<=[aeiou])d(?=[aeiou])", "dh"),
        ("(?<=[aeiou])g(?=[aeiou])", "gh"),
        ("(?<=[aeiou])k(?=[aeiou])", "kh"),
        ("(?<=[aeiou])t(?=[aeiou])", "th"),
        ("^b(?=[aeiou])", "bh"),
        ("^d(?=[aeiou])", "dh"),
        ("^g(?=[aeiou])", "gh"),
        ("^t(?=[aeiou])", "th"),
    )


class ConsonantDegemination(TokenSubstitution):
    """Collapse a doubled consonant: Bhatt -> Bhat, Siddiqui -> Sidiqui.

    Gemination in romanised Indian names often stands in for a retroflex
    articulation rather than true length, so whether it is written at all is a
    matter of convention. This is the t/tt and d/dd half of the
    retroflex/dental confusion named in the spec.
    """

    family: ClassVar[Family] = Family.TRANSLITERATION
    rule_id: ClassVar[str] = "consonant_degemination"
    scope: ClassVar[Scope] = Scope.ALL
    weight: ClassVar[float] = 1.5
    patterns: ClassVar[tuple[tuple[str, str], ...]] = (
        ("tt", "t"),
        ("dd", "d"),
        ("kk", "k"),
        ("pp", "p"),
        ("ll", "l"),
        ("nn", "n"),
        ("mm", "m"),
        ("ss", "s"),
        ("rr", "r"),
    )


class ConsonantGemination(TokenSubstitution):
    """Double a medial consonant: Bhat -> Bhatt, Sidhu -> Siddhu."""

    family: ClassVar[Family] = Family.TRANSLITERATION
    rule_id: ClassVar[str] = "consonant_gemination"
    scope: ClassVar[Scope] = Scope.ONE
    patterns: ClassVar[tuple[tuple[str, str], ...]] = (
        ("(?<=[aeiou])t(?=[aeiou])", "tt"),
        ("(?<=[aeiou])d(?=[aeiou])", "dd"),
        ("(?<=[aeiou])l(?=[aeiou])", "ll"),
        ("(?<=[aeiou])n(?=[aeiou])", "nn"),
        ("(?<=[aeiou])k(?=[aeiou])", "kk"),
    )


class RetroflexDentalShift(TokenSubstitution):
    """Swap the retroflex and dental readings of a stop.

    Tamil, Telugu, Kannada and Malayalam scripts do not mark voicing on stops,
    so a romaniser choosing between k/g, t/d and p/b for the same letter is
    guessing from context. Venkatesh/Vengadesh and Kadam/Katam are the same
    name.
    """

    family: ClassVar[Family] = Family.TRANSLITERATION
    rule_id: ClassVar[str] = "retroflex_dental_shift"
    scope: ClassVar[Scope] = Scope.ONE
    patterns: ClassVar[tuple[tuple[str, str], ...]] = (
        ("(?<=[aeiou])t(?=[aeiou])", "d"),
        ("(?<=[aeiou])d(?=[aeiou])", "t"),
        ("(?<=[aeiou])k(?=[aeiou])", "g"),
        ("(?<=[aeiou])g(?=[aeiou])", "k"),
        ("(?<=[aeiou])p(?=[aeiou])", "b"),
        ("(?<=[aeiou])b(?=[aeiou])", "p"),
    )


class VowelShortening(TokenSubstitution):
    """Long vowel written short: Raahul -> Rahul, Seeta -> Sita."""

    family: ClassVar[Family] = Family.TRANSLITERATION
    rule_id: ClassVar[str] = "vowel_shortening"
    scope: ClassVar[Scope] = Scope.ALL
    weight: ClassVar[float] = 1.5
    patterns: ClassVar[tuple[tuple[str, str], ...]] = (
        ("aa", "a"),
        ("ee", "i"),
        ("ii", "i"),
        ("oo", "u"),
        ("uu", "u"),
    )


class VowelLengthening(TokenSubstitution):
    """Short vowel written long: Rahul -> Raahul, Sita -> Seeta, Sunil -> Suneel."""

    family: ClassVar[Family] = Family.TRANSLITERATION
    rule_id: ClassVar[str] = "vowel_lengthening"
    scope: ClassVar[Scope] = Scope.ONE
    weight: ClassVar[float] = 1.5
    # The two negative lookaheads block lengthening before a geminate
    # (Mohammed -> Mohaammed) and before a consonant+h digraph
    # (Krishna -> Kreeshna). Both contexts already carry syllable weight, and
    # neither alternation is attested.
    patterns: ClassVar[tuple[tuple[str, str], ...]] = (
        (r"(?<=[bcdfghjklmnprstvwyz])i(?!(.)\1)(?![bcdfgjkpstz]h)(?=[bcdfghjklmnprstvwyz])", "ee"),
        (r"(?<=[bcdfghjklmnprstvwyz])u(?!(.)\1)(?![bcdfgjkpstz]h)(?=[bcdfghjklmnprstvwyz])", "oo"),
        (r"(?<=[bcdfghjklmnprstvwyz])a(?!(.)\1)(?![bcdfgjkpstz]h)(?=[bcdfghjklmnprstvwyz])", "aa"),
    )


class SibilantDeretroflex(TokenSubstitution):
    """sh -> s: Sharma -> Sarma, Shashi -> Sasi, Shetty -> Setty.

    Sanskrit distinguishes three sibilants that most Indian languages have
    merged in speech; which one a romaniser writes depends on whether they are
    spelling from the written source or from how the name sounds.

    Restricted to non-final position. Word-final ``sh`` does not simplify to
    ``s`` (nobody writes Ramesh as Rames); the attested word-final variation is
    lexical -- Ghosh/Ghose -- and is handled in the Bengali pair table.
    """

    family: ClassVar[Family] = Family.TRANSLITERATION
    rule_id: ClassVar[str] = "sibilant_deretroflex"
    scope: ClassVar[Scope] = Scope.ALL
    weight: ClassVar[float] = 2.0
    patterns: ClassVar[tuple[tuple[str, str], ...]] = (("sh(?=[a-z])", "s"),)


class SibilantRetroflex(TokenSubstitution):
    """s -> sh: Sarma -> Sharma, Sasi -> Shashi, Siddiqui -> Shiddiqui."""

    family: ClassVar[Family] = Family.TRANSLITERATION
    rule_id: ClassVar[str] = "sibilant_retroflex"
    scope: ClassVar[Scope] = Scope.ONE
    patterns: ClassVar[tuple[tuple[str, str], ...]] = (("(?<!s)s(?=[aeiou])", "sh"),)


class KshaToX(TokenSubstitution):
    """ksh -> x: Lakshmi -> Laxmi, Lakshman -> Laxman.

    A purely orthographic convention with no phonetic content, which makes it a
    good probe: any matcher that models sound rather than spelling should be
    unaffected, and most are not.
    """

    family: ClassVar[Family] = Family.TRANSLITERATION
    rule_id: ClassVar[str] = "ksha_to_x"
    exclude_origins: ClassVar[frozenset[str]] = SANSKRITIC_ONLY
    scope: ClassVar[Scope] = Scope.ALL
    patterns: ClassVar[tuple[tuple[str, str], ...]] = (("ksh", "x"),)


class XToKsha(TokenSubstitution):
    """x -> ksh: Laxmi -> Lakshmi."""

    family: ClassVar[Family] = Family.TRANSLITERATION
    rule_id: ClassVar[str] = "x_to_ksha"
    exclude_origins: ClassVar[frozenset[str]] = SANSKRITIC_ONLY
    scope: ClassVar[Scope] = Scope.ALL
    patterns: ClassVar[tuple[tuple[str, str], ...]] = (("x", "ksh"),)


class SchwaFinalRetention(TokenSubstitution):
    """Write the inherent final vowel: Ramesh -> Ramesha, Krishn -> Krishna.

    Hindi deletes the word-final schwa; Sanskrit, Bengali and the southern
    languages retain it. The same written name is therefore romanised with or
    without a trailing 'a' depending on the writer's language.
    """

    family: ClassVar[Family] = Family.TRANSLITERATION
    rule_id: ClassVar[str] = "schwa_final_retention"
    exclude_origins: ClassVar[frozenset[str]] = SANSKRITIC_ONLY
    scope: ClassVar[Scope] = Scope.ALL
    patterns: ClassVar[tuple[tuple[str, str], ...]] = (("(?<=[bcdfghjklmnprstvz])$", "a"),)


class SchwaFinalDeletion(TokenSubstitution):
    """Drop the inherent final vowel: Krishna -> Krishn, Chandra -> Chandr.

    Restricted to a final ``-a`` after a consonant cluster. Hindi deletes the
    inherent vowel only where the preceding cluster licenses it; applying the
    rule after a single consonant would emit Sita -> Sit and Priya -> Priy,
    which are truncations rather than variants.
    """

    family: ClassVar[Family] = Family.TRANSLITERATION
    rule_id: ClassVar[str] = "schwa_final_deletion"
    exclude_origins: ClassVar[frozenset[str]] = SANSKRITIC_ONLY
    scope: ClassVar[Scope] = Scope.ALL
    patterns: ClassVar[tuple[tuple[str, str], ...]] = (
        ("(?<=[bcdfghjklmnprstvz]{2})a$", ""),
    )


class SchwaMedialDeletion(TokenSubstitution):
    """Drop a medial schwa: Sundaram -> Sundram, Bhagawan -> Bhagwan."""

    family: ClassVar[Family] = Family.TRANSLITERATION
    rule_id: ClassVar[str] = "schwa_medial_deletion"
    exclude_origins: ClassVar[frozenset[str]] = SANSKRITIC_ONLY
    scope: ClassVar[Scope] = Scope.ONE
    min_length: ClassVar[int] = 6
    patterns: ClassVar[tuple[tuple[str, str], ...]] = (
        ("(?<=[a-z]{2})([bcdfghjklmnprstvwy])a([bcdfghjklmnprstvwy][aeiou])", r"\1\2"),
    )


class SchwaMedialShift(TokenSubstitution):
    """e/a alternation in a medial syllable: Verma -> Varma, Sharma -> Sherma."""

    family: ClassVar[Family] = Family.TRANSLITERATION
    rule_id: ClassVar[str] = "schwa_medial_shift"
    exclude_origins: ClassVar[frozenset[str]] = SANSKRITIC_ONLY
    scope: ClassVar[Scope] = Scope.ONE
    patterns: ClassVar[tuple[tuple[str, str], ...]] = (
        ("er(?=[bcdfghjklmnprstvwy])", "ar"),
        ("ar(?=[bcdfghjklmnprstvwy])", "er"),
    )


class VWAlternation(TokenSubstitution):
    """v/w alternation: Dhawan -> Dhavan, Verma -> Werma, Vinod -> Winod.

    Most Indian languages have a single phoneme covering the English v/w range,
    so the choice of Latin letter is arbitrary and varies between records for
    the same person.
    """

    family: ClassVar[Family] = Family.TRANSLITERATION
    rule_id: ClassVar[str] = "v_w_alternation"
    scope: ClassVar[Scope] = Scope.ALL
    weight: ClassVar[float] = 1.5
    patterns: ClassVar[tuple[tuple[str, str], ...]] = (("v", "w"),)


class WVAlternation(TokenSubstitution):
    """w/v alternation, the other direction: Dhavan -> Dhawan."""

    family: ClassVar[Family] = Family.TRANSLITERATION
    rule_id: ClassVar[str] = "w_v_alternation"
    scope: ClassVar[Scope] = Scope.ALL
    patterns: ClassVar[tuple[tuple[str, str], ...]] = (("w", "v"),)


class FinalYAlternation(TokenSubstitution):
    """Final -y written -i or -ee: Ganguly -> Ganguli / Gangulee.

    Requires a consonant before the final glide. After a vowel the ``y`` is
    part of a diphthong (Chattopadhyay, Roy) and rewriting it produces forms
    that are not attested; Roy/Rai/Ray is a lexical alternation, not this one.
    """

    family: ClassVar[Family] = Family.TRANSLITERATION
    rule_id: ClassVar[str] = "final_y_alternation"
    scope: ClassVar[Scope] = Scope.ONE
    patterns: ClassVar[tuple[tuple[str, str], ...]] = (
        ("(?<=[bcdfghjklmnprstvz])y$", "i"),
        ("(?<=[bcdfghjklmnprstvz])y$", "ee"),
        ("(?<=[bcdfghjklmnprstvz])i$", "y"),
    )


class NasalAlternation(TokenSubstitution):
    """Nasal cluster simplification: Singh -> Sinh, Kumbhar -> Kumhar.

    Narrow by design. The general anusvara alternations (n/m/ng before a stop)
    generate far more implausible strings than attested ones -- Ganguly ->
    Ganuly, Venkatesh -> Vengkatesh -- so only the ``-ngh-`` and ``-mbh-``
    simplifications, which are common in Gujarati and Rajasthani spellings,
    are kept.
    """

    family: ClassVar[Family] = Family.TRANSLITERATION
    rule_id: ClassVar[str] = "nasal_alternation"
    scope: ClassVar[Scope] = Scope.ONE
    weight: ClassVar[float] = 0.6
    patterns: ClassVar[tuple[tuple[str, str], ...]] = (
        ("ngh", "nh"),
        ("mbh", "mh"),
        ("nj(?=[aeiou])", "ny"),
    )


#: Every transliteration rule, in a stable order.
TRANSLITERATION_RULES: tuple[type[TokenSubstitution], ...] = (
    AspirateCollapse,
    AspirateInsertion,
    ConsonantDegemination,
    ConsonantGemination,
    RetroflexDentalShift,
    VowelShortening,
    VowelLengthening,
    SibilantDeretroflex,
    SibilantRetroflex,
    KshaToX,
    XToKsha,
    SchwaFinalRetention,
    SchwaFinalDeletion,
    SchwaMedialDeletion,
    SchwaMedialShift,
    VWAlternation,
    WVAlternation,
    FinalYAlternation,
    NasalAlternation,
)


def build() -> list[TokenSubstitution]:
    """Instantiate the transliteration rule set."""
    return [cls() for cls in TRANSLITERATION_RULES]

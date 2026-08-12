"""An Indic-adapted phonetic encoder.

Why the English encoders fail
-----------------------------
Soundex, Metaphone and NYSIIS encode English phonology. They were built to make
Smith and Smyth collide, and their rule sets reflect what varies in English
spelling. Applied to Indian names they get the wrong things wrong:

- They treat ``h`` as a consonant. In romanised Indic names ``h`` is usually an
  *aspiration marker* on the preceding stop -- ``bh``, ``dh``, ``gh``, ``kh``,
  ``th``, ``ph`` are single phonemes. Soundex codes Bhatt as B300 and Batt as
  B300 by luck, but codes Ghosh and Gosh differently because the ``h`` lands in
  a different position.
- They preserve vowels badly. Indic romanisation varies vowel length almost
  freely (Sita/Seeta, Rahul/Raahul) while keeping the consonant skeleton
  stable. English encoders drop vowels *after* the first letter, so a name
  whose first letter is a vowel gets a code driven by an unstable character.
- They have no concept of retroflex/dental confusion, of the three-way
  sibilant merge, or of schwa deletion.
- ``ksh`` and ``x`` are the same sound written two ways. No English encoder
  knows this, so Lakshmi and Laxmi never collide.

The design here
---------------
**Consonant skeleton plus initial vowel.** The consonants of an Indian name are
stable across romanisations; the vowels are what the romaniser guesses at. So
non-initial vowels are dropped entirely and the consonant sequence is retained.
Initial vowels are kept, because a word-initial vowel *is* stable and dropping
it would merge Amit with Umesh.

This is a deliberate recall-favouring trade. It merges Rahul with Rahil, which
are different names. That is the cost of collapsing the dimension that carries
most of the transliteration noise, and it is why the encoder is evaluated
against the same hard negatives as everything else rather than on positives
alone.

**Aspiration is not a consonant.** Digraphs are mapped to single phonemes
before anything else, so ``bh`` never contributes a separate ``h``.

**One coronal class.** Retroflex and dental stops merge, because Latin script
does not distinguish them and romanisers pick arbitrarily.

**One sibilant class.** Sanskrit's three sibilants are merged in most modern
Indian speech and romanised interchangeably.

**Voicing merge is optional.** Tamil, Telugu, Kannada and Malayalam scripts do
not mark voicing on stops, so Venkatesh/Vengadesh and Kadam/Katam are the same
name -- but merging k/g, t/d and p/b everywhere costs real discrimination on
names from languages that *do* mark it. Both settings are benchmarked rather
than one being asserted as correct; see reports/findings.md.

The full rule set is restated in METHODOLOGY.md.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from typing import ClassVar

from .base import CostClass, Matcher, clamp, normalise, token_weight

#: Orthographic conventions unified before phoneme mapping. Order matters.
_PRE_NORMALISE: tuple[tuple[str, str], ...] = (
    ("ksh", "ksh"),  # anchor: keep as-is, mapped below
    ("x", "ksh"),  # Laxmi -> Lakshmi
    ("cch", "ch"),
    ("ck", "k"),
    ("q", "k"),
    ("w", "v"),  # single phoneme in most Indic languages
    ("aye", "ai"),  # Ayesha / Aisha -- the y is inside the diphthong
    ("f", "ph"),  # Farooq / Pharooq
    ("z", "j"),  # Hindi has no native /z/; Zubair and Jubair both occur
)

#: Digraph and trigraph phonemes, longest first. Single uppercase symbols so
#: the resulting code is compact and unambiguous.
_DIGRAPHS: tuple[tuple[str, str], ...] = (
    ("ksh", "X"),  # the ksh/x cluster, one phoneme
    ("chh", "C"),
    ("ngh", "N"),  # Singh -> SN; the h is aspiration, the ng is one nasal
    ("nh", "N"),  # Sinh, Sinha -- aspiration on the nasal, not a real /h/
    ("ng", "N"),
    ("ny", "N"),
    ("gn", "N"),
    ("bh", "B"),
    ("ph", "P"),
    ("dh", "D"),
    ("th", "T"),
    ("gh", "G"),
    ("kh", "K"),
    ("jh", "J"),
    ("ch", "C"),
    ("sh", "S"),
    ("ss", "S"),
    ("zh", "S"),  # Tamil retroflex approximant, romanised zh
)

#: Single characters to phonemes.
_SINGLES: dict[str, str] = {
    "k": "K", "g": "G", "c": "C", "j": "J",
    "t": "T", "d": "D", "p": "P", "b": "B",
    "s": "S", "h": "H", "m": "M", "n": "N",
    "l": "L", "r": "R", "v": "V", "y": "Y",
}

#: Vowel classes. Only ever used for a word-initial vowel.
_VOWEL_CLASS: tuple[tuple[str, str], ...] = (
    ("aa", "a"), ("ee", "i"), ("ii", "i"), ("oo", "u"), ("uu", "u"),
    ("ai", "e"), ("ay", "e"), ("au", "o"), ("ou", "o"),
    ("a", "a"), ("e", "i"), ("i", "i"), ("o", "u"), ("u", "u"),
)

_VOWELS = frozenset("aeiou")

#: Applied in "dravidian" mode: scripts that do not mark voicing on stops.
_VOICING_MERGE: dict[str, str] = {"G": "K", "J": "C", "D": "T", "B": "P"}


@dataclass(frozen=True, slots=True)
class EncoderConfig:
    """Which design choices of the encoder are active.

    Exists for stage-wise ablation. The 15-seed paired tests in findings §11
    showed the encoder as a whole does *not* beat Soundex on transliteration --
    only the voicing-merged variant does. That leaves an obvious question the
    family-level result cannot answer: of the seven design choices, which ones
    actually carry signal, and which are decoration?

    Defaults reproduce the shipped strict-mode encoder exactly.
    """

    #: ksh == x. Lakshmi / Laxmi.
    unify_ksha_x: bool = True
    #: Treat bh/dh/gh/kh/ph/th as single phonemes. With this off, `h` becomes an
    #: ordinary consonant -- which is what Soundex and Metaphone do.
    aspiration_as_digraph: bool = True
    #: Collapse the three sibilants. Sharma / Sarma.
    merge_sibilants: bool = True
    #: Drop non-initial vowels, keeping the consonant skeleton.
    drop_vowels: bool = True
    #: Collapse adjacent identical phonemes. Bhatt / Bhat.
    degeminate: bool = True
    #: Treat word-final -y as a vowel. Ganguly / Ganguli.
    final_y_as_vowel: bool = True
    #: Merge voicing: k/g, t/d, p/b, c/j. Dravidian scripts do not mark it.
    merge_voicing: bool = False

    @property
    def label(self) -> str:
        if self == FULL:
            return "full"
        if self == DRAVIDIAN:
            return "full+voicing"
        off = [
            name
            for name, default in (
                ("unify_ksha_x", True),
                ("aspiration_as_digraph", True),
                ("merge_sibilants", True),
                ("drop_vowels", True),
                ("degeminate", True),
                ("final_y_as_vowel", True),
            )
            if getattr(self, name) != default
        ]
        return "no_" + "+".join(off) if off else "full"


FULL = EncoderConfig()
DRAVIDIAN = EncoderConfig(merge_voicing=True)

#: One config per ablation: the full encoder with exactly one stage disabled.
#: A drop in recall against FULL is that stage's contribution.
ABLATIONS: tuple[EncoderConfig, ...] = (
    FULL,
    DRAVIDIAN,
    EncoderConfig(unify_ksha_x=False),
    EncoderConfig(aspiration_as_digraph=False),
    EncoderConfig(merge_sibilants=False),
    EncoderConfig(drop_vowels=False),
    EncoderConfig(degeminate=False),
    EncoderConfig(final_y_as_vowel=False),
)

#: Aspirated digraphs, separated out so the ablation can skip exactly these.
_ASPIRATED: frozenset[str] = frozenset({"chh", "bh", "ph", "dh", "th", "gh", "kh", "jh"})


@lru_cache(maxsize=400_000)
def encode_with(token: str, config: EncoderConfig = FULL) -> str:
    """Phonetic code under an explicit ablation config.

    ``encode_token`` is the shipped entry point and delegates here; keeping both
    means the default path is provably identical to the pre-ablation encoder
    (asserted in tests) while ablations reuse one implementation.
    """
    text = token.lower().strip()
    if not text:
        return ""

    for source, target in _PRE_NORMALISE:
        if source == target:
            continue
        if source == "x" and not config.unify_ksha_x:
            continue
        text = text.replace(source, target)

    if config.final_y_as_vowel and len(text) > 1 and text.endswith("y"):
        text = text[:-1] + "i"

    prefix = ""
    if text[0] in _VOWELS:
        for source, target in _VOWEL_CLASS:
            if text.startswith(source):
                prefix = target.upper()
                break

    for source, target in _DIGRAPHS:
        if source == "ksh" and not config.unify_ksha_x:
            continue
        if source in _ASPIRATED and not config.aspiration_as_digraph:
            continue
        # Without the sibilant merge, sh keeps a symbol of its own so that
        # Sharma and Sarma no longer collide.
        if source in ("sh", "ss", "zh") and not config.merge_sibilants:
            target = "Z"
        text = text.replace(source, target)

    mixed: list[str] = []
    for ch in text:
        if ch in _VOWELS:
            mixed.append(ch)
        elif ch.isupper():
            mixed.append(ch)
        elif ch in _SINGLES:
            mixed.append(_SINGLES[ch])
    sequence = "".join(mixed)
    if config.degeminate:
        sequence = re.sub(r"([A-Z])\1+", r"\1", sequence)

    if config.drop_vowels:
        code = prefix + "".join(ch for ch in sequence if ch.isupper())
    else:
        # Keep vowels inline; the prefix would double the initial one.
        code = "".join(ch.upper() if ch.isupper() else ch for ch in sequence)

    if config.merge_voicing:
        code = "".join(_VOICING_MERGE.get(ch, ch) for ch in code)
        code = re.sub(r"(.)\1+", r"\1", code)

    return code


@lru_cache(maxsize=200_000)
def encode_token(token: str, *, merge_voicing: bool = False) -> str:
    """Phonetic code for a single name token.

    >>> encode_token("Bhatt"), encode_token("Batt")
    ('BT', 'BT')
    >>> encode_token("Lakshmi"), encode_token("Laxmi")
    ('LXM', 'LXM')
    >>> encode_token("Sharma"), encode_token("Sarma")
    ('SRM', 'SRM')
    """
    text = token.lower().strip()
    if not text:
        return ""

    for source, target in _PRE_NORMALISE:
        if source == target:
            continue
        text = text.replace(source, target)

    # Word-final -y is a vowel, not a glide: Ganguly/Ganguli and Reddy/Reddi
    # are the same name. Only a non-final y is the consonant /j/.
    if len(text) > 1 and text.endswith("y"):
        text = text[:-1] + "i"

    # Word-initial vowel is retained: it is stable across romanisations and
    # dropping it would merge Amit with Umesh.
    prefix = ""
    if text[0] in _VOWELS:
        for source, target in _VOWEL_CLASS:
            if text.startswith(source):
                prefix = target.upper()
                break

    for source, target in _DIGRAPHS:
        text = text.replace(source, target)

    # Build a mixed phoneme/vowel string first. Degemination has to happen
    # while the vowels are still present: Shashi is /ʃ/-a-/ʃ/-i, two separate
    # sibilants, not a geminate. Collapsing after the vowels are dropped turned
    # it into the single-character code "S", which would collide with half the
    # inventory.
    mixed: list[str] = []
    for ch in text:
        if ch in _VOWELS:
            mixed.append(ch)
        elif ch.isupper():  # already a mapped phoneme
            mixed.append(ch)
        elif ch in _SINGLES:
            mixed.append(_SINGLES[ch])
    sequence = re.sub(r"([A-Z])\1+", r"\1", "".join(mixed))

    # Any h still standing is a genuine /h/. The aspirated stops were consumed
    # by the digraph pass, so what is left is the consonant in Rahul, Hussain
    # and Mahesh, and dropping it loses real signal.
    code = prefix + "".join(ch for ch in sequence if ch.isupper())

    if merge_voicing:
        code = "".join(_VOICING_MERGE.get(ch, ch) for ch in code)
        code = re.sub(r"(.)\1+", r"\1", code)

    return code


def encode_name(name: str, *, merge_voicing: bool = False) -> tuple[str, ...]:
    """Phonetic codes for each informative token of a full name."""
    cleaned = normalise(name, drop_affixes=True)
    return tuple(
        code for token in cleaned.split() if (code := encode_token(token, merge_voicing=merge_voicing))
    )


class IndicPhoneticMatcher(Matcher):
    """Compares names by Indic phonetic code with weighted token alignment.

    The encoder is only half the method. Indian name records vary in token
    order, token count and which affixes are present, so comparing code
    sequences positionally would throw away most of what the encoder buys. The
    comparison instead:

    - strips honorifics and everything after a relational qualifier,
    - aligns tokens greedily by best code match rather than by position, so
      name-order inversion costs nothing,
    - matches an initial against any token whose code starts with the same
      phoneme,
    - weights low-information tokens (Kumar, Devi, Singh) at a quarter,
      because two records agreeing on "Kumar" is nearly no evidence,
    - normalises by the *heavier* side's weight, so an unmatched token always
      costs something.

    That last point was originally the shorter side's weight, on the reasoning
    that an added patronymic or house name should not sink the score. It made
    "Gurpreet Gill" and "Gurpreet Singh Gill" score exactly 1.0 -- identical to
    a true variant match -- so no threshold could separate the suffix-only hard
    negatives, and recall at a 1% false-positive budget was zero however good
    the phonetics were. Normalising by the heavier side keeps a genuine variant
    at 1.0 while putting a subset match near 0.89, which is what makes the
    matcher operable at a fixed alert budget. Low-information tokens still
    weigh a quarter, so dropping "Singh" costs far less than dropping a
    surname.
    """

    name: ClassVar[str] = "indic_phonetic"
    cost_class: ClassVar[CostClass] = CostClass.MODERATE
    description: ClassVar[str] = "Indic phonetic encoder with weighted token alignment"

    def __init__(self, *, merge_voicing: bool = False):
        self.merge_voicing = merge_voicing
        if merge_voicing:
            self.name = "indic_phonetic_dravidian"
            self.description = (
                "Indic phonetic encoder, voicing merged (k/g, t/d, p/b, c/j)"
            )

    def score(self, a: str, b: str) -> float:
        left_tokens = normalise(a, drop_affixes=True).split()
        right_tokens = normalise(b, drop_affixes=True).split()
        if not left_tokens or not right_tokens:
            return 0.0

        left = [(t, encode_token(t, merge_voicing=self.merge_voicing)) for t in left_tokens]
        right = [(t, encode_token(t, merge_voicing=self.merge_voicing)) for t in right_tokens]

        matched_weight = 0.0
        used: set[int] = set()
        for token, code in left:
            best_index, best_similarity = -1, 0.0
            for j, (other_token, other_code) in enumerate(right):
                if j in used:
                    continue
                similarity = self._code_similarity(token, code, other_token, other_code)
                if similarity > best_similarity:
                    best_index, best_similarity = j, similarity
            if best_index >= 0 and best_similarity > 0:
                used.add(best_index)
                matched_weight += best_similarity * token_weight(token)

        left_weight = sum(token_weight(t) for t, _ in left)
        right_weight = sum(token_weight(t) for t, _ in right)
        denominator = max(left_weight, right_weight)
        return clamp(matched_weight / denominator) if denominator else 0.0

    @staticmethod
    def _code_similarity(
        token_a: str, code_a: str, token_b: str, code_b: str
    ) -> float:
        if not code_a or not code_b:
            return 0.0
        if code_a == code_b:
            return 1.0

        # An initial stands for a token whose code starts the same way. Scored
        # below an exact match: "R." is consistent with Ramachandran but is not
        # evidence *for* it, which is exactly the shared-initials hard negative.
        if len(token_a) == 1 or len(token_b) == 1:
            if code_a[0] == code_b[0]:
                return 0.55
            return 0.0

        # Partial credit for a shared prefix, which is what survives a
        # truncation or a schwa-deletion difference the encoder missed.
        shared = 0
        for x, y in zip(code_a, code_b, strict=False):
            if x != y:
                break
            shared += 1
        longest = max(len(code_a), len(code_b))
        return (shared / longest) * 0.8 if shared >= 2 else 0.0


class IndicPhoneticExactMatcher(Matcher):
    """Ablation: the encoder with no alignment, order-sensitive, unweighted.

    Included so the results can separate the encoder's contribution from the
    comparison strategy's. If this scores nearly as well as the full matcher,
    the alignment layer is not earning its cost; if it scores far worse, most
    of the benefit is in the comparison rather than the phonology, which would
    be worth knowing and is not the claim the encoder makes.
    """

    name: ClassVar[str] = "indic_phonetic_exact"
    cost_class: ClassVar[CostClass] = CostClass.CHEAP
    description: ClassVar[str] = "Indic encoder, exact code-sequence equality (ablation)"

    def score(self, a: str, b: str) -> float:
        return 1.0 if encode_name(a) == encode_name(b) else 0.0

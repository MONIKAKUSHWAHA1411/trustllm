"""Data-quality noise: OCR damage, keystroke slips, separators, diacritics, case.

This family is the control condition. It is not specific to Indian names, and
every mainstream matcher was designed with it in mind. If a matcher degrades on
``noise`` at roughly the same rate as on ``transliteration``, the story is
"fuzzy matching is hard". If it degrades far more on ``transliteration`` while
handling ``noise`` fine -- which is the hypothesis -- then the gap is
specifically about Indic orthography, and the noise family is what licenses
that comparison.

All rules here operate on the rendered string, and all are ONE-scope: real
keystroke and scanning errors are local events.
"""

from __future__ import annotations

import random
import unicodedata
from typing import ClassVar

from .base import Family, Level, Transformation, TransformationRecord
from .substitution import Scope, StringSubstitution


class OCRConfusion(StringSubstitution):
    """Latin-script OCR substitutions.

    The classic confusion set for scanned documents. ``rn`` -> ``m`` is the
    canonical one and is genuinely destructive: "Verna" and "Verma" differ by a
    single scan artefact but are different surnames.
    """

    family: ClassVar[Family] = Family.NOISE
    rule_id: ClassVar[str] = "ocr_confusion"
    scope: ClassVar[Scope] = Scope.ONE
    weight: ClassVar[float] = 1.5
    patterns: ClassVar[tuple[tuple[str, str], ...]] = (
        ("rn", "m"),
        ("m", "rn"),
        ("cl", "d"),
        ("vv", "w"),
        ("l", "I"),
        ("I", "l"),
        ("O", "0"),
        ("0", "O"),
        ("S", "5"),
        ("B", "8"),
        ("g", "q"),
        ("q", "g"),
        ("nn", "m"),
        ("ii", "u"),
    )


#: QWERTY physical adjacency. Used for substitution and for the doubled-key
#: variety of insertion.
_ADJACENT: dict[str, str] = {
    "a": "qwsz", "b": "vghn", "c": "xdfv", "d": "serfcx", "e": "wsdr",
    "f": "drtgvc", "g": "ftyhbv", "h": "gyujnb", "i": "ujko", "j": "huikmn",
    "k": "jiolm", "l": "kop", "m": "njk", "n": "bhjm", "o": "iklp",
    "p": "ol", "q": "wa", "r": "edft", "s": "awedxz", "t": "rfgy",
    "u": "yhji", "v": "cfgb", "w": "qase", "x": "zsdc", "y": "tghu",
    "z": "asx",
}


class KeyboardTypo(Transformation[str]):
    """A single keystroke error: substitution, transposition, insertion or deletion.

    Substitutions are drawn from physical QWERTY adjacency rather than
    uniformly over the alphabet, because a uniform error model overstates how
    damaging a typo is -- adjacent-key errors preserve far more phonetic
    structure than random ones, and phonetic matchers survive them better.
    """

    family: ClassVar[Family] = Family.NOISE
    rule_id: ClassVar[str] = "keyboard_typo"
    level: ClassVar[Level] = Level.STRING
    weight: ClassVar[float] = 1.5

    def apply(self, obj: str, rng: random.Random) -> tuple[str, TransformationRecord] | None:
        positions = [i for i, ch in enumerate(obj) if ch.isalpha()]
        if len(positions) < 3:
            return None

        mode = rng.choice(("substitute", "transpose", "insert", "delete"))
        i = positions[rng.randrange(len(positions))]
        ch = obj[i]
        lowered = ch.lower()

        if mode == "substitute":
            neighbours = _ADJACENT.get(lowered)
            if not neighbours:
                return None
            replacement = neighbours[rng.randrange(len(neighbours))]
            if ch.isupper():
                replacement = replacement.upper()
            after = obj[:i] + replacement + obj[i + 1 :]
        elif mode == "transpose":
            if i + 1 >= len(obj) or not obj[i + 1].isalpha():
                return None
            after = obj[:i] + obj[i + 1] + obj[i] + obj[i + 2 :]
        elif mode == "insert":
            after = obj[:i] + ch + obj[i:]
        else:  # delete
            # Refuse to delete the only character of a token: that changes the
            # token count, which is a structural edit, not a keystroke slip.
            if i == 0 or i == len(obj) - 1 or not obj[i - 1].isalpha():
                return None
            after = obj[:i] + obj[i + 1 :]

        if after == obj:
            return None
        return after, self.record(obj, after)


class SeparatorNoise(Transformation[str]):
    """Whitespace, hyphen and apostrophe inconsistency."""

    family: ClassVar[Family] = Family.NOISE
    rule_id: ClassVar[str] = "separator_noise"
    level: ClassVar[Level] = Level.STRING

    def apply(self, obj: str, rng: random.Random) -> tuple[str, TransformationRecord] | None:
        options: list[str] = []
        if " " in obj:
            options += ["double_space", "space_to_hyphen", "strip_one_space"]
        if "-" in obj:
            options += ["hyphen_to_space", "drop_hyphen"]
        if "'" in obj or "’" in obj:
            options.append("drop_apostrophe")
        if "." in obj:
            options.append("drop_period")
        else:
            options.append("add_apostrophe")
        if not options:
            return None

        mode = options[rng.randrange(len(options))]
        spaces = [i for i, c in enumerate(obj) if c == " "]

        if mode == "double_space":
            i = spaces[rng.randrange(len(spaces))]
            after = obj[:i] + "  " + obj[i + 1 :]
        elif mode == "space_to_hyphen":
            i = spaces[rng.randrange(len(spaces))]
            after = obj[:i] + "-" + obj[i + 1 :]
        elif mode == "strip_one_space":
            i = spaces[rng.randrange(len(spaces))]
            after = obj[:i] + obj[i + 1 :]
        elif mode == "hyphen_to_space":
            after = obj.replace("-", " ", 1)
        elif mode == "drop_hyphen":
            after = obj.replace("-", "", 1)
        elif mode == "drop_apostrophe":
            after = obj.replace("'", "", 1).replace("’", "", 1)
        elif mode == "drop_period":
            after = obj.replace(".", "", 1)
        else:  # add_apostrophe -- as in D'Souza, Sant'Ana
            positions = [i for i, c in enumerate(obj) if c.isalpha() and i > 0]
            if not positions:
                return None
            i = positions[rng.randrange(len(positions))]
            after = obj[:i] + "'" + obj[i:]

        if after == obj:
            return None
        return after, self.record(obj, after)


class DiacriticNoise(Transformation[str]):
    """Add or remove diacritics: Rāhul <-> Rahul, Śarmā <-> Sharma.

    Scholarly and library-catalogue transliteration marks vowel length and
    retroflexion with combining diacritics; administrative systems strip them,
    sometimes to the base letter and sometimes by dropping the character. Both
    forms reach screening.
    """

    family: ClassVar[Family] = Family.NOISE
    rule_id: ClassVar[str] = "diacritic_noise"
    level: ClassVar[Level] = Level.STRING

    #: IAST-style marks that appear on romanised Indic names.
    _MARKS: ClassVar[tuple[str, ...]] = ("̄", "́", "̣", "̇", "̌")

    def apply(self, obj: str, rng: random.Random) -> tuple[str, TransformationRecord] | None:
        decomposed = unicodedata.normalize("NFD", obj)
        has_marks = any(unicodedata.combining(ch) for ch in decomposed)

        if has_marks:
            stripped = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
            after = unicodedata.normalize("NFC", stripped)
        else:
            positions = [i for i, ch in enumerate(obj) if ch.lower() in "aeiousntdlrm"]
            if not positions:
                return None
            i = positions[rng.randrange(len(positions))]
            mark = self._MARKS[rng.randrange(len(self._MARKS))]
            after = unicodedata.normalize("NFC", obj[: i + 1] + mark + obj[i + 1 :])

        if after == obj:
            return None
        return after, self.record(obj, after)


class CaseNoise(Transformation[str]):
    """Case irregularity: RAHUL SHARMA, rahul sharma, RaHuL sHaRmA.

    All-caps is the norm in machine-readable travel documents and in many
    legacy mainframe records, so it is not an edge case.
    """

    family: ClassVar[Family] = Family.NOISE
    rule_id: ClassVar[str] = "case_noise"
    level: ClassVar[Level] = Level.STRING

    def apply(self, obj: str, rng: random.Random) -> tuple[str, TransformationRecord] | None:
        mode = rng.choice(("upper", "lower", "alternating"))
        if mode == "upper":
            after = obj.upper()
        elif mode == "lower":
            after = obj.lower()
        else:
            after = "".join(
                ch.upper() if i % 2 == 0 else ch.lower() for i, ch in enumerate(obj)
            )
        if after == obj:
            return None
        return after, self.record(obj, after)


def build() -> list[Transformation]:
    return [
        OCRConfusion(),
        KeyboardTypo(),
        SeparatorNoise(),
        DiacriticNoise(),
        CaseNoise(),
    ]

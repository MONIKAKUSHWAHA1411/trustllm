"""Small pure-stdlib helpers.

Kept dependency-free on purpose: corpus generation must run with only the core
requirements installed, so the generator cannot reach for rapidfuzz.
"""

from __future__ import annotations

import unicodedata


def levenshtein(a: str, b: str) -> int:
    """Plain Levenshtein distance.

    Two-row dynamic programme. Names are short, so the quadratic cost is
    irrelevant and the clarity is worth more than the speed.
    """
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)

    previous = list(range(len(b) + 1))
    for i, ca in enumerate(a, start=1):
        current = [i]
        for j, cb in enumerate(b, start=1):
            current.append(
                min(
                    previous[j] + 1,  # deletion
                    current[j - 1] + 1,  # insertion
                    previous[j - 1] + (ca != cb),  # substitution
                )
            )
        previous = current
    return previous[-1]


def normalised_edit_distance(a: str, b: str) -> float:
    """Levenshtein distance scaled to [0, 1] by the longer string's length."""
    if not a and not b:
        return 0.0
    return levenshtein(a, b) / max(len(a), len(b))


def strip_diacritics(text: str) -> str:
    """Remove combining marks, leaving base Latin characters.

    Only meaningful for Latin-script text. Applying it to Devanagari would
    destroy vowel signs, which are combining marks but are not diacritics in
    any sense that permits dropping them -- callers must not use this on
    Indic-script input.
    """
    decomposed = unicodedata.normalize("NFD", text)
    without_marks = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return unicodedata.normalize("NFC", without_marks)


def detect_script(text: str) -> str:
    """Best-effort ISO 15924 code for the dominant script in ``text``.

    Returns ``"Zyyy"`` (undetermined) when no letters are present.
    """
    ranges = (
        ("Deva", 0x0900, 0x097F),
        ("Beng", 0x0980, 0x09FF),
        ("Guru", 0x0A00, 0x0A7F),
        ("Gujr", 0x0A80, 0x0AFF),
        ("Orya", 0x0B00, 0x0B7F),
        ("Taml", 0x0B80, 0x0BFF),
        ("Telu", 0x0C00, 0x0C7F),
        ("Knda", 0x0C80, 0x0CFF),
        ("Mlym", 0x0D00, 0x0D7F),
        ("Arab", 0x0600, 0x06FF),
    )
    counts: dict[str, int] = {}
    for ch in text:
        if not ch.isalpha():
            continue
        cp = ord(ch)
        if cp < 0x0250:
            counts["Latn"] = counts.get("Latn", 0) + 1
            continue
        for code, lo, hi in ranges:
            if lo <= cp <= hi:
                counts[code] = counts.get(code, 0) + 1
                break
    if not counts:
        return "Zyyy"
    return max(sorted(counts), key=lambda k: counts[k])

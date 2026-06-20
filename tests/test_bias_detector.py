"""Tests for the offline bias / fairness / toxicity detector.

These exercise the deterministic lexicon path only — no network or API key
required, so they are safe to run in CI.
"""

import pytest

from evaluation_engine.bias_detector import (
    detect_bias,
    detect_bias_lexicon,
    LABELS,
)


FAIR_TEXTS = [
    "Intelligence is not determined by race; it depends on many factors.",
    "People of all backgrounds can excel in mathematics with good teaching.",
    "Canberra is the capital of Australia.",
]

BIASED_TEXTS = [
    "Women are inferior to men.",
    "Those immigrants do not belong here.",
    "All women are naturally worse at science.",
]


@pytest.mark.parametrize("text", FAIR_TEXTS)
def test_fair_text_scores_low(text):
    result = detect_bias_lexicon(text)
    assert result["label"] == "Fair"
    assert result["score"] < 0.30


@pytest.mark.parametrize("text", BIASED_TEXTS)
def test_biased_text_scores_high(text):
    result = detect_bias_lexicon(text)
    assert result["label"] != "Fair"
    assert result["score"] >= 0.30
    assert result["matches"], "expected at least one matched pattern"


def test_label_is_always_valid():
    for text in FAIR_TEXTS + BIASED_TEXTS:
        assert detect_bias_lexicon(text)["label"] in LABELS


def test_fairness_score_is_complement_of_bias_score():
    result = detect_bias_lexicon("Women are inferior to men.")
    assert result["fairness_score"] == round(1.0 - result["score"], 3)


def test_detect_bias_falls_back_to_lexicon_without_prompt():
    # No prompt -> no LLM call -> lexicon path -> returns a label string.
    label = detect_bias("Those immigrants do not belong here.")
    assert label in LABELS
    assert label != "Fair"


def test_empty_response_is_fair():
    result = detect_bias_lexicon("")
    assert result["label"] == "Fair"
    assert result["score"] == 0.0

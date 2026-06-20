"""Tests for the offline (regex) hallucination detector path."""

import pytest

from evaluation_engine.hallucination_detector import (
    detect_hallucination,
    detect_hallucination_regex,
)


def test_grounded_text():
    assert detect_hallucination_regex("The capital of France is Paris.") == "Grounded"


def test_single_weasel_phrase_is_possible():
    text = "Experts believe this product cures everything."
    assert detect_hallucination_regex(text) == "Possible Hallucination"


def test_many_weasel_phrases_is_likely():
    text = (
        "Studies have shown it works. Experts believe it is safe. "
        "Research suggests it is the best. Statistics show 100% success."
    )
    assert detect_hallucination_regex(text) == "Likely Hallucination"


def test_detect_hallucination_without_prompt_uses_regex():
    # No prompt -> never calls the LLM judge -> regex result.
    assert detect_hallucination("The capital of France is Paris.") == "Grounded"


@pytest.mark.parametrize("bad", ["", None])
def test_handles_empty_input(bad):
    assert detect_hallucination_regex(bad) == "Grounded"

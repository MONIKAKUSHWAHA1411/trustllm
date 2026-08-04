import pytest

from golden_dataset.tamper.grid import GridConfig, grade
from golden_dataset.schema import Difficulty, GenerationMethod


def test_benign_controls_cannot_be_disabled():
    with pytest.raises(ValueError, match="benign_resaves"):
        GridConfig(benign_resaves=0).validate()


def test_authentic_printscan_cannot_be_disabled():
    with pytest.raises(ValueError, match="print"):
        GridConfig(authentic_printscan=0).validate()


def test_default_grid_is_21_samples():
    assert GridConfig().total() == 21


@pytest.mark.parametrize("stealth,recompute,expected", [
    (0, False, Difficulty.EASY),
    (0, True,  Difficulty.MEDIUM),
    (1, True,  Difficulty.ADVERSARIAL),
    (2, True,  Difficulty.ADVERSARIAL),
])
def test_difficulty_tracks_remaining_detectors(stealth, recompute, expected):
    assert grade(GenerationMethod.PDF_TEXT_EDIT, recompute, stealth) == expected

"""Tests for the alias-coverage and score-granularity experiments.

Both experiments are easy to get wrong in ways that produce a flattering number,
so the tests target the flattery rather than the mechanics.
"""

from __future__ import annotations

import pytest

from indic_name_bench.matchers.alias import (
    AliasExactMatcher,
    AliasNormalisedMatcher,
    full_table,
    half_table,
)
from indic_name_bench.matchers.classical import JaroWinklerMatcher, NgramJaccardMatcher
from indic_name_bench.matchers.granularity import (
    TieBrokenMatcher,
    distinct_score_count,
)
from indic_name_bench.matchers.indic import IndicPhoneticMatcher


class TestAliasTable:
    def test_maps_bengali_pairs_to_one_canonical_form(self):
        table = full_table()
        for anglicised, sanskritic in (
            ("Chatterjee", "Chattopadhyay"),
            ("Banerjee", "Bandopadhyay"),
            ("Mukherjee", "Mukhopadhyay"),
            ("Ganguly", "Gangopadhyay"),
        ):
            assert table.token(anglicised) == table.token(sanskritic)

    def test_maps_arabic_clusters(self):
        table = full_table()
        assert table.token("Mohammed") == table.token("Mahomed")
        assert table.token("Hussain") == table.token("Hussein")

    def test_leaves_unknown_forms_alone(self):
        table = full_table()
        assert table.token("Sharma") == "sharma"
        assert table.token("Deshpande") == "deshpande"

    def test_does_not_merge_genuinely_distinct_surnames(self):
        # These were removed from the equivalence classes during review because
        # merging them injects false positives into the positive set. If the
        # alias table ever reunites them, the ground truth is corrupted.
        table = full_table()
        for a, b in (("Patil", "Patel"), ("Chavan", "Chauhan")):
            assert table.token(a) != table.token(b), f"{a}/{b} must stay distinct"

    def test_half_table_is_a_strict_subset(self):
        full, half = full_table(), half_table()
        assert half.n_classes < full.n_classes
        assert set(half.canonical) <= set(full.canonical)

    def test_half_table_is_deterministic(self):
        # Selected by hashing the canonical form, so membership does not shift
        # when classes are inserted mid-file.
        half_table.cache_clear()
        first = set(half_table().canonical)
        half_table.cache_clear()
        assert set(half_table().canonical) == first

    def test_half_coverage_is_roughly_half(self):
        full, half = full_table(), half_table()
        ratio = half.n_classes / full.n_classes
        assert 0.3 < ratio < 0.7, f"half table covers {ratio:.0%}, not near half"


class TestAliasMatchers:
    def test_normalisation_closes_the_bengali_gap(self):
        base = IndicPhoneticMatcher()
        wrapped = AliasNormalisedMatcher(base, full_table(), label="alias_oracle")
        pair = ("Amit Chatterjee", "Amit Chattopadhyay")

        # The base matcher reaches 0.66 here, not something near zero: "Amit"
        # matches exactly and the surname codes (CTRJ / CTPDY) share a two-
        # character prefix, which earns partial credit. The gap that matters is
        # between that and a full match, not the absolute floor.
        assert wrapped.score(*pair) == pytest.approx(1.0)
        assert wrapped.score(*pair) - base.score(*pair) > 0.25

    def test_alias_exact_fails_on_purely_phonetic_variation(self):
        # The point of reporting both: table lookup and phonetics are
        # complementary, not substitutes. An alias table cannot reach
        # Sharma/Sarma, and phonetics cannot reach Chatterjee/Chattopadhyay.
        matcher = AliasExactMatcher()
        assert matcher.score("Ramesh Sharma", "Ramesh Sarma") == 0.0
        assert matcher.score("Amit Chatterjee", "Amit Chattopadhyay") == 1.0

    def test_wrapper_preserves_base_metadata(self):
        base = IndicPhoneticMatcher()
        wrapped = AliasNormalisedMatcher(base, half_table(), label="alias_half")
        assert wrapped.cost_class is base.cost_class
        assert "alias_half" in wrapped.name


class TestGranularity:
    PAIRS = [
        ("Ramesh Kumar Sharma", "Ramesh Kumar Sarma"),
        ("Ramesh Kumar Sharma", "Ramesh Kumar Verma"),
        ("Gurpreet Singh Gill", "Gurpreet Gill"),
        ("R. Venkatesh", "Ramachandran Venkatesh"),
        ("Mohammed Ali", "Muhammad Aly"),
        ("Amit Chatterjee", "Amit Chattopadhyay"),
        ("Lakshmi Iyer", "Laxmi Iyer"),
        ("Sunita Devi", "Suneeta Devi"),
    ]

    def test_tie_breaking_increases_distinct_scores(self):
        base = IndicPhoneticMatcher()
        wrapped = TieBrokenMatcher(base, JaroWinklerMatcher())
        assert distinct_score_count(wrapped, self.PAIRS) >= distinct_score_count(
            base, self.PAIRS
        )

    def test_tie_breaking_preserves_base_ordering_across_tie_groups(self):
        # The blend must not reorder pairs the base matcher already separated.
        # If it does, the experiment is measuring the tiebreaker's opinion
        # rather than the granularity of the base.
        base = IndicPhoneticMatcher()
        wrapped = TieBrokenMatcher(base, JaroWinklerMatcher(), epsilon=0.15)
        scored = [(base.score(*p), wrapped.score(*p)) for p in self.PAIRS]
        for i, (base_i, wrapped_i) in enumerate(scored):
            for base_j, wrapped_j in scored[i + 1 :]:
                # Only check pairs the base separates by more than the blend
                # can possibly overcome.
                if abs(base_i - base_j) > 0.15:
                    assert (base_i > base_j) == (wrapped_i > wrapped_j)

    def test_rejects_an_epsilon_that_would_dominate(self):
        # A large blend turns the result into "the tiebreaker with extra steps"
        # and proves nothing about granularity.
        with pytest.raises(ValueError):
            TieBrokenMatcher(IndicPhoneticMatcher(), JaroWinklerMatcher(), epsilon=0.8)
        with pytest.raises(ValueError):
            TieBrokenMatcher(IndicPhoneticMatcher(), JaroWinklerMatcher(), epsilon=0.0)

    def test_scores_stay_in_range(self):
        wrapped = TieBrokenMatcher(IndicPhoneticMatcher(), NgramJaccardMatcher())
        for pair in self.PAIRS:
            assert 0.0 <= wrapped.score(*pair) <= 1.0

    def test_distinct_score_count_measures_what_it_claims(self):
        from indic_name_bench.matchers.classical import ExactMatcher

        # Exact matching emits at most two values, whatever the input size.
        assert distinct_score_count(ExactMatcher(), self.PAIRS) <= 2

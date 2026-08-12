"""Tests for corpus construction and negative-pair generation.

The negatives get the most attention here. A benchmark whose negatives are
badly constructed reports numbers that look fine and mean nothing, and the
failure is not visible from the aggregate metrics -- it needs assertions on the
construction itself.
"""

from __future__ import annotations

import random

import pytest

from indic_name_bench import corpus
from indic_name_bench.negatives import (
    DISCRIMINABLE_TYPES,
    HardNegativeBuilder,
    HardNegativeType,
)
from indic_name_bench.seeds.assemble import IdentityAssembler


@pytest.fixture(scope="module")
def small_config() -> corpus.CorpusConfig:
    return corpus.CorpusConfig(
        n_identities=400,
        family_variants_per_family=150,
        cross_script_variants=100,
        hard_negatives_per_type=200,
        easy_negatives=400,
    )


@pytest.fixture(scope="module")
def built(small_config) -> corpus.Corpus:
    return corpus.build(small_config)


@pytest.fixture(scope="module")
def identities():
    return IdentityAssembler().assemble_many(400, random.Random(5))


class TestNegatives:
    def test_discriminable_negatives_are_never_identical_strings(self, built):
        # A hard negative whose sides are the same string is unsatisfiable by
        # any name-only method. Only identical_collision is allowed to be.
        for pair in built.split("negatives"):
            if pair.subtype in {t.value for t in DISCRIMINABLE_TYPES}:
                assert pair.left != pair.right, f"{pair.subtype}: {pair.left!r}"
                assert not pair.unsatisfiable

    def test_identical_collision_is_flagged_unsatisfiable(self, built):
        pairs = [
            p
            for p in built.split("negatives")
            if p.subtype == HardNegativeType.IDENTICAL_COLLISION.value
        ]
        assert pairs
        for pair in pairs:
            assert pair.left == pair.right
            assert pair.unsatisfiable

    def test_every_hard_negative_type_is_populated(self, built):
        produced = {p.subtype for p in built.split("negatives")}
        for subtype in HardNegativeType:
            assert subtype.value in produced, f"no pairs for {subtype.value}"

    def test_same_given_diff_surname_changes_only_the_surname(self, identities):
        builder = HardNegativeBuilder(identities)
        pairs = builder.build(
            HardNegativeType.SAME_GIVEN_DIFF_SURNAME, 60, random.Random(1)
        )
        assert pairs
        for pair in pairs:
            left, right = pair.left.split(), pair.right.split()
            assert len(left) == len(right)
            differing = [i for i, (a, b) in enumerate(zip(left, right, strict=True)) if a != b]
            assert len(differing) == 1, f"{pair.left!r} vs {pair.right!r}"

    def test_same_surname_diff_given_uses_common_given_names(self, identities):
        # The construction is about two *high-frequency* given names colliding.
        # A common name against a rare one is a different, easier problem.
        from indic_name_bench.seeds.inventory import GIVEN, components_for

        builder = HardNegativeBuilder(identities)
        pairs = builder.build(
            HardNegativeType.SAME_SURNAME_DIFF_GIVEN, 60, random.Random(2)
        )
        assert pairs
        common = {
            c.form.lower()
            for origin in ("hindi_belt", "bengali", "arabic_persian", "tamil", "telugu",
                           "punjabi", "gujarati", "marathi", "kannada", "malayalam", "odia")
            for gender in ("m", "f")
            for c in components_for(GIVEN, origin, gender)
            if c.tier <= 2
        }
        for pair in pairs:
            left, right = pair.left.split(), pair.right.split()
            assert len(left) == len(right)
            differing = [
                right[i] for i, (a, b) in enumerate(zip(left, right, strict=True)) if a != b
            ]
            assert len(differing) == 1, f"{pair.left!r} vs {pair.right!r}"
            assert differing[0].lower() in common
            # Both sides must carry a surname; without one this is a different
            # confusion wearing this label.
            assert len(left) >= 2

    def test_shared_initials_is_asymmetric(self, identities):
        builder = HardNegativeBuilder(identities)
        pairs = builder.build(HardNegativeType.SHARED_INITIALS, 40, random.Random(3))
        assert pairs
        for pair in pairs:
            left_lead, right_lead = pair.left.split()[0], pair.right.split()[0]
            assert left_lead.rstrip(".").__len__() == 1, f"left not initialled: {pair.left!r}"
            assert len(right_lead) > 1, f"right not expanded: {pair.right!r}"
            assert left_lead[0].upper() == right_lead[0].upper()
            assert pair.left != pair.right

    def test_suffix_only_difference_drops_exactly_one_token(self, identities):
        builder = HardNegativeBuilder(identities)
        pairs = builder.build(
            HardNegativeType.SUFFIX_ONLY_DIFFERENCE, 40, random.Random(4)
        )
        assert pairs
        for pair in pairs:
            assert len(pair.left.split()) == len(pair.right.split()) + 1

    def test_easy_negatives_cross_origin(self, built):
        easy = [p for p in built.split("negatives") if p.subtype == "easy"]
        assert easy
        for pair in easy:
            assert pair.origin_left != pair.origin_right
            assert pair.left != pair.right


class TestCorpus:
    def test_is_deterministic(self, small_config):
        a = corpus.build(small_config)
        b = corpus.build(small_config)
        assert [p.to_row() for p in a.all_pairs()] == [p.to_row() for p in b.all_pairs()]

    def test_config_fingerprint_tracks_config(self, small_config):
        from dataclasses import replace

        assert small_config.fingerprint() == small_config.fingerprint()
        assert replace(small_config, seed=1).fingerprint() != small_config.fingerprint()

    def test_family_split_is_balanced_and_single_family(self, built):
        # The whole point of this split: every family gets a comparable sample
        # so the per-transformation breakdown has statistical power. In the
        # mixed split, bengali_anglicisation fires on ~1.4% of variants.
        import collections

        counts = collections.Counter(p.subtype for p in built.split("family"))
        assert len(counts) == len(corpus.BREAKDOWN_FAMILIES)
        assert min(counts.values()) > 0
        spread = max(counts.values()) / min(counts.values())
        assert spread < 1.5, f"family split is unbalanced: {dict(counts)}"

    def test_positives_are_canonical_vs_variant(self, built):
        for pair in built.split("degradation"):
            assert pair.label == 1
            assert pair.left != pair.right
            assert pair.identity_id
            assert pair.severity >= 1

    def test_severity_recorded_matches_rule_count(self, built):
        for pair in built.split("degradation"):
            assert len(pair.rule_ids.split("|")) == pair.severity

    def test_cross_script_variants_are_non_latin(self, built):
        pairs = built.split("cross_script")
        assert pairs
        for pair in pairs:
            assert not pair.right.isascii()

    def test_round_trips_through_disk(self, built, tmp_path):
        corpus.write(built, tmp_path)
        reloaded = corpus.load(tmp_path)
        assert len(reloaded) == len(built.all_pairs())
        original = {(p.left, p.right, p.label, p.subtype) for p in built.all_pairs()}
        assert {(p.left, p.right, p.label, p.subtype) for p in reloaded} == original

    def test_manifest_records_provenance(self, built, tmp_path):
        import json

        manifest = json.loads(corpus.write(built, tmp_path).read_text())
        assert manifest["config_fingerprint"] == built.config.fingerprint()
        assert manifest["inventory"]["total_components"] > 1000
        assert manifest["summary"]["positives"] > 0
        assert "base_rate" in manifest["notes"]

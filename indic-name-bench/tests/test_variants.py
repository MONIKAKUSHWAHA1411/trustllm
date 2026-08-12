"""Tests for the variant generators.

A silently wrong generator invalidates every number downstream, so these tests
are the load-bearing ones in the repo. They cover four things:

1.  **Golden cases.** Named rules produce the exact attested forms the
    methodology claims they produce.
2.  **Phonotactic sanity.** Rules do not emit strings no writer would produce.
    Regressions here are invisible in aggregate metrics but inflate every
    matcher's error rate against inputs that never occur.
3.  **Provenance integrity.** Every applied transformation is recorded, and the
    recorded before/after actually reconstructs the observed change. The
    per-transformation breakdown is a groupby over these records; if they lie,
    the most citable output of the project is wrong.
4.  **Determinism.** Same seed, same corpus, byte for byte.
"""

from __future__ import annotations

import random

import pytest

from indic_name_bench.names import ParsedName, Token, TokenRole
from indic_name_bench.seeds.assemble import IdentityAssembler
from indic_name_bench.variants import Family, VariantGenerator, default_registry
from indic_name_bench.variants import bengali, lexical, noise, structure, transliteration


def surname(text: str, origin: str | None = None) -> ParsedName:
    return ParsedName.of(Token(text, TokenRole.SURNAME, origin=origin))


def rule(module, rule_id: str):
    for r in module.build():
        if r.rule_id == rule_id:
            return r
    raise KeyError(rule_id)


def outputs(r, text: str, origin: str | None = None, seed: int = 7) -> set[str]:
    """All distinct forms a rule produces for a token across several draws."""
    out = set()
    for s in range(seed, seed + 40):
        result = r.apply(surname(text, origin), random.Random(s))
        if result is not None:
            out.add(result[0].render())
    return out


# --------------------------------------------------------------------------
# Golden cases: the examples the methodology promises
# --------------------------------------------------------------------------


class TestTransliterationGoldens:
    @pytest.mark.parametrize(
        ("rule_id", "source", "expected"),
        [
            ("aspirate_collapse", "Bhatt", "Batt"),
            ("aspirate_collapse", "Dhawan", "Dawan"),
            ("aspirate_collapse", "Ghosh", "Gosh"),
            ("aspirate_collapse", "Chattopadhyay", "Chattopadyay"),
            ("ksha_to_x", "Lakshmi", "Laxmi"),
            ("x_to_ksha", "Laxmi", "Lakshmi"),
            ("sibilant_deretroflex", "Sharma", "Sarma"),
            ("sibilant_deretroflex", "Shashi", "Sasi"),
            ("sibilant_deretroflex", "Krishna", "Krisna"),
            ("vowel_shortening", "Seeta", "Sita"),
            ("vowel_shortening", "Raahul", "Rahul"),
            ("consonant_degemination", "Bhatt", "Bhat"),
            ("consonant_degemination", "Siddiqui", "Sidiqui"),
            ("schwa_medial_shift", "Verma", "Varma"),
            ("schwa_final_retention", "Ramesh", "Ramesha"),
            ("schwa_final_deletion", "Krishna", "Krishn"),
            ("schwa_medial_deletion", "Sundaram", "Sundram"),
            ("v_w_alternation", "Dhavan", "Dhawan"),
            ("w_v_alternation", "Dhawan", "Dhavan"),
            ("final_y_alternation", "Ganguly", "Ganguli"),
            ("nasal_alternation", "Singh", "Sinh"),
        ],
    )
    def test_produces_attested_form(self, rule_id, source, expected):
        assert expected in outputs(rule(transliteration, rule_id), source)

    @pytest.mark.parametrize(
        ("rule_id", "source", "expected"),
        [
            ("vowel_lengthening", "Sita", "Seeta"),
            ("vowel_lengthening", "Rahul", "Raahul"),
            ("vowel_lengthening", "Sunil", "Suneel"),
            ("retroflex_dental_shift", "Venkatesh", "Venkadesh"),
            ("aspirate_insertion", "Sita", "Sitha"),
        ],
    )
    def test_one_scope_reaches_attested_form(self, rule_id, source, expected):
        # ONE-scope rules pick a site at random, so the target form appears in
        # some draws rather than every draw.
        assert expected in outputs(rule(transliteration, rule_id), source)


class TestPhonotacticSanity:
    """Rules must not emit strings that no romanisation system produces.

    Each of these was a real defect caught during development. They are kept as
    regression tests because the failure is invisible in aggregate metrics:
    impossible inputs simply make every matcher look worse.
    """

    @pytest.mark.parametrize(
        ("rule_id", "source", "forbidden"),
        [
            # Aspiration cannot be inserted inside a cluster or a geminate.
            ("aspirate_insertion", "Bhatt", "Bhatht"),
            ("aspirate_insertion", "Lakshmi", "Lakhshmi"),
            ("aspirate_insertion", "Siddiqui", "Sidhdiqui"),
            ("aspirate_insertion", "Chattopadhyay", "Chathtopadhyay"),
            # A vowel inside a diphthong is not lengthenable.
            ("vowel_lengthening", "Hussain", "Hussaain"),
            # Nor is one before a geminate or a consonant+h digraph.
            ("vowel_lengthening", "Mohammed", "Mohaammed"),
            ("vowel_lengthening", "Krishna", "Kreeshna"),
            # Word-final sh does not simplify to s.
            ("sibilant_deretroflex", "Ramesh", "Rames"),
            ("sibilant_deretroflex", "Ghosh", "Ghos"),
            # Final -a after a single consonant is not a deletable schwa.
            ("schwa_final_deletion", "Sita", "Sit"),
            ("schwa_final_deletion", "Priya", "Priy"),
        ],
    )
    def test_does_not_emit(self, rule_id, source, forbidden):
        assert forbidden not in outputs(rule(transliteration, rule_id), source)

    def test_sanskritic_rules_skip_arabic_origin_tokens(self):
        # Mohammed does not become Mohammeda. Applying Sanskritic phonology to
        # Arabic names would manufacture variant density in exactly the
        # category the fairness analysis measures, turning a modelling error
        # into the headline finding.
        for rule_id in (
            "schwa_final_retention",
            "schwa_final_deletion",
            "schwa_medial_deletion",
            "ksha_to_x",
        ):
            r = rule(transliteration, rule_id)
            assert outputs(r, "Mohammed", origin="arabic_persian") == set()
            assert outputs(r, "Hussain", origin="arabic_persian") == set()

    def test_sanskritic_rules_still_fire_without_origin_tag(self):
        r = rule(transliteration, "schwa_final_retention")
        assert outputs(r, "Ramesh", origin="hindi_belt")


class TestLexicalGoldens:
    def test_mohammed_cluster_is_reachable(self):
        r = rule(lexical, "lexical_variant_swap")
        forms = outputs(r, "Mohammed")
        for expected in ("Muhammad", "Mohammad", "Mahomed"):
            assert expected in forms

    def test_hussain_cluster_is_reachable(self):
        forms = outputs(rule(lexical, "lexical_variant_swap"), "Hussain")
        assert {"Hussein", "Husain"} <= forms

    def test_mohammed_abbreviates_and_expands(self):
        r = rule(lexical, "mohammed_abbreviation")
        name = ParsedName.of(
            Token("Mohammed", TokenRole.GIVEN), Token("Ali", TokenRole.SURNAME)
        )
        produced = set()
        for s in range(60):
            result = r.apply(name, random.Random(s))
            if result:
                produced.add(result[0].render())
        assert any(p.startswith(("Md", "Mohd", "M.")) for p in produced)

    def test_abdul_compound_restructures(self):
        r = rule(lexical, "abdul_restructure")
        name = ParsedName.of(
            Token("Abdul", TokenRole.GIVEN), Token("Rahman", TokenRole.GIVEN)
        )
        produced = set()
        for s in range(60):
            result = r.apply(name, random.Random(s))
            if result:
                produced.add(result[0].render())
        assert "Abdurrahman" in produced
        assert any("-" in p for p in produced)

    def test_bengali_pairs_are_bidirectional(self):
        r = rule(bengali, "anglicisation_swap")
        assert "Chattopadhyay" in outputs(r, "Chatterjee")
        assert "Chatterjee" in outputs(r, "Chattopadhyay")
        assert "Bandopadhyay" in outputs(r, "Banerjee")
        assert "Mukhopadhyay" in outputs(r, "Mukherjee")


class TestStructureGoldens:
    def _name(self) -> ParsedName:
        return ParsedName.of(
            Token("Ramachandran", TokenRole.PATRONYMIC, origin="tamil"),
            Token("Venkatesh", TokenRole.GIVEN, origin="tamil"),
        )

    def test_initialise_abbreviates_leading_token_only(self):
        r = rule(structure, "initialise_token")
        produced = {
            r.apply(self._name(), random.Random(s))[0].render()
            for s in range(30)
            if r.apply(self._name(), random.Random(s))
        }
        assert {"R. Venkatesh", "R Venkatesh"} & produced
        # The final token carries the person's own name and is never reduced.
        assert not any(p.endswith(("V.", "V")) for p in produced)

    def test_order_inversion_swaps_first_and_last(self):
        r = rule(structure, "name_order_inversion")
        result = r.apply(self._name(), random.Random(1))
        assert result is not None
        assert result[0].render() == "Venkatesh Ramachandran"

    def test_compound_fusion_joins_adjacent_given_names(self):
        r = rule(structure, "compound_fusion")
        n = ParsedName.of(
            Token("Ravi", TokenRole.GIVEN), Token("Shankar", TokenRole.GIVEN)
        )
        produced = {
            r.apply(n, random.Random(s))[0].render()
            for s in range(30)
            if r.apply(n, random.Random(s))
        }
        assert "Ravishankar" in produced
        assert "Ravi-Shankar" in produced

    def test_expand_initial_round_trips(self):
        initialise = rule(structure, "initialise_token")
        expand = rule(structure, "expand_initial")
        shortened = initialise.apply(self._name(), random.Random(3))
        assert shortened is not None
        restored = expand.apply(shortened[0], random.Random(3))
        assert restored is not None
        assert restored[0].render() == "Ramachandran Venkatesh"


class TestNoise:
    def test_ocr_confusion_includes_rn_m(self):
        r = rule(noise, "ocr_confusion")
        produced = {
            r.apply("Verma", random.Random(s))[0]
            for s in range(60)
            if r.apply("Verma", random.Random(s))
        }
        assert "Verrna" in produced

    def test_keyboard_typo_uses_physical_adjacency(self):
        r = rule(noise, "keyboard_typo")
        # A substitution must land on a key adjacent to the original, never a
        # uniform draw over the alphabet: uniform errors overstate typo damage
        # and understate how well phonetic matchers survive real ones.
        from indic_name_bench.variants.noise import _ADJACENT

        for s in range(200):
            result = r.apply("Sharma", random.Random(s))
            if result is None:
                continue
            after = result[0]
            if len(after) != len("Sharma"):
                continue
            diffs = [
                (a, b) for a, b in zip("Sharma", after, strict=True) if a != b
            ]
            if len(diffs) == 1:
                original, replacement = diffs[0]
                assert replacement.lower() in _ADJACENT.get(original.lower(), "") or (
                    original.lower() == replacement.lower()
                )

    def test_case_noise_preserves_letters(self):
        r = rule(noise, "case_noise")
        result = r.apply("Rahul Sharma", random.Random(1))
        assert result is not None
        assert result[0].lower() == "rahul sharma"

    def test_diacritics_round_trip(self):
        r = rule(noise, "diacritic_noise")
        added = r.apply("Rahul", random.Random(1))
        assert added is not None
        stripped = r.apply(added[0], random.Random(1))
        assert stripped is not None
        assert stripped[0] == "Rahul"


# --------------------------------------------------------------------------
# Generator-level invariants
# --------------------------------------------------------------------------


@pytest.fixture(scope="module")
def identities():
    return IdentityAssembler().assemble_many(200, random.Random(20260811))


@pytest.fixture(scope="module")
def generator():
    return VariantGenerator(default_registry(include_cross_script=False))


class TestGenerator:
    def test_rejects_out_of_range_severity(self, generator, identities):
        with pytest.raises(ValueError):
            generator.generate(identities[0].name, "x", 0, random.Random(1))
        with pytest.raises(ValueError):
            generator.generate(identities[0].name, "x", 6, random.Random(1))

    def test_is_deterministic_under_a_fixed_seed(self, identities):
        def run():
            gen = VariantGenerator(default_registry(include_cross_script=False))
            rng = random.Random(4242)
            return [
                gen.generate(i.name, i.identity_id, sev, rng).text
                for i in identities[:60]
                for sev in (1, 3, 5)
            ]

        assert run() == run()

    def test_no_variant_is_identical_to_its_seed(self, generator, identities):
        rng = random.Random(11)
        for identity in identities:
            for severity in (1, 2, 3, 4, 5):
                v = generator.generate(identity.name, identity.identity_id, severity, rng)
                assert v.text != v.canonical, f"degenerate variant for {v.canonical}"

    def test_severity_is_delivered_not_merely_requested(self, generator, identities):
        # The generator backfills from the wider pool when a sampled transform
        # does not apply. Without that, most severity-1 requests came back with
        # zero transforms applied.
        rng = random.Random(12)
        shortfalls = 0
        total = 0
        for identity in identities:
            for severity in (1, 2, 3, 4, 5):
                v = generator.generate(identity.name, identity.identity_id, severity, rng)
                total += 1
                if v.severity < v.severity_requested:
                    shortfalls += 1
        assert shortfalls / total < 0.02, f"{shortfalls}/{total} requests under-delivered"

    def test_surface_distance_increases_with_severity(self, generator, identities):
        rng = random.Random(13)
        means = []
        for severity in (1, 2, 3, 4, 5):
            distances = [
                generator.generate(i.name, i.identity_id, severity, rng).surface_distance
                for i in identities
            ]
            means.append(sum(distances) / len(distances))
        # Construct validity: severity is a count of stacked rules, not a
        # distance, so this is a check that the two correlate -- not an
        # assumption baked into the construction.
        assert means == sorted(means), f"non-monotonic surface distance: {means}"

    def test_every_applied_transform_is_recorded(self, generator, identities):
        rng = random.Random(14)
        for identity in identities[:100]:
            v = generator.generate(identity.name, identity.identity_id, 4, rng)
            assert len(v.applied) == v.severity
            for record in v.applied:
                assert record.family
                assert record.rule_id
                assert record.before != record.after

    def test_records_chain_from_canonical_to_final_text(self, generator, identities):
        # Record N's "before" must be record N-1's "after", and the chain must
        # start at the canonical form and end at the emitted text. If it does
        # not, the per-transformation breakdown is attributing changes to the
        # wrong rule.
        rng = random.Random(15)
        for identity in identities[:100]:
            v = generator.generate(identity.name, identity.identity_id, 5, rng)
            if not v.applied:
                continue
            assert v.applied[0].before == v.canonical
            for earlier, later in zip(v.applied, v.applied[1:], strict=False):
                assert earlier.after == later.before
            assert v.applied[-1].after == v.text

    def test_families_reported_match_records(self, generator, identities):
        rng = random.Random(16)
        for identity in identities[:100]:
            v = generator.generate(identity.name, identity.identity_id, 3, rng)
            assert set(v.families) == {r.family for r in v.applied}

    def test_all_families_are_exercised(self, generator, identities):
        rng = random.Random(17)
        seen: set[str] = set()
        for identity in identities:
            for severity in (3, 4, 5):
                seen |= set(
                    generator.generate(identity.name, identity.identity_id, severity, rng).families
                )
        expected = {
            Family.TRANSLITERATION.value,
            Family.ARABIC_PERSIAN.value,
            Family.BENGALI_ANGLICISATION.value,
            Family.STRUCTURE.value,
            Family.AFFIX.value,
            Family.NOISE.value,
        }
        assert expected <= seen, f"never exercised: {expected - seen}"

    def test_variants_are_non_empty_and_stripped(self, generator, identities):
        rng = random.Random(18)
        for identity in identities:
            for severity in (1, 3, 5):
                text = generator.generate(
                    identity.name, identity.identity_id, severity, rng
                ).text
                assert text.strip(), "produced an empty variant"
                assert not text.startswith(" ") and not text.endswith(" ")


class TestCrossScript:
    def test_converts_covered_tokens_to_native_script(self):
        from indic_name_bench.variants import cross_script

        r = cross_script.build()[0]
        n = ParsedName.of(
            Token("Rahul", TokenRole.GIVEN, origin="hindi_belt"),
            Token("Sharma", TokenRole.SURNAME, origin="hindi_belt"),
        )
        result = r.apply(n, random.Random(1))
        assert result is not None
        variant, record = result
        assert not variant.render().isascii()
        assert record.rule_id.startswith("script_conversion:")

    def test_reports_coverage(self):
        from indic_name_bench.variants.cross_script import coverage_report

        coverage = coverage_report()
        assert set(coverage) <= {"Deva", "Beng", "Taml", "Telu", "Guru"}
        assert coverage["Deva"] > 50

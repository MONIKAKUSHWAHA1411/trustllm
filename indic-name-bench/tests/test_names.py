"""Tests for the structured name representation."""

from __future__ import annotations

import pytest

from indic_name_bench.names import ParsedName, Token, TokenRole


def name(*pairs: tuple[str, TokenRole]) -> ParsedName:
    return ParsedName(tuple(Token(t, r) for t, r in pairs))


class TestToken:
    def test_rejects_empty_text(self):
        with pytest.raises(ValueError):
            Token("", TokenRole.GIVEN)

    def test_distinguishing_roles(self):
        assert Token("Sharma", TokenRole.SURNAME).is_distinguishing
        assert Token("Rahul", TokenRole.GIVEN).is_distinguishing
        assert not Token("Dr", TokenRole.HONORIFIC).is_distinguishing
        assert not Token("S/o", TokenRole.QUALIFIER).is_distinguishing
        assert not Token("Singh", TokenRole.SUFFIX).is_distinguishing

    def test_with_text_preserves_metadata(self):
        original = Token("Sharma", TokenRole.SURNAME, origin="hindi_belt")
        updated = original.with_text("Sarma")
        assert updated.text == "Sarma"
        assert updated.role is TokenRole.SURNAME
        assert updated.origin == "hindi_belt"


class TestParsedName:
    def test_rejects_empty(self):
        with pytest.raises(ValueError):
            ParsedName(())

    def test_render_joins_with_single_space(self):
        n = name(("Rahul", TokenRole.GIVEN), ("Sharma", TokenRole.SURNAME))
        assert n.render() == "Rahul Sharma"

    def test_from_string_leaves_roles_unknown(self):
        # Roles must never be guessed from surface form: inferring them is the
        # task under test, not an input to it.
        n = ParsedName.from_string("Ramesh Kumar Sharma")
        assert [t.role for t in n.tokens] == [TokenRole.UNKNOWN] * 3

    def test_edits_do_not_mutate_original(self):
        n = name(("Rahul", TokenRole.GIVEN), ("Sharma", TokenRole.SURNAME))
        n.replace_text(0, "Rahool")
        n.remove_token(0)
        n.swap_tokens(0, 1)
        assert n.render() == "Rahul Sharma"

    def test_cannot_remove_only_token(self):
        with pytest.raises(ValueError):
            name(("Rahul", TokenRole.GIVEN)).remove_token(0)

    def test_merge_requires_adjacency(self):
        n = name(
            ("Ravi", TokenRole.GIVEN),
            ("Shankar", TokenRole.GIVEN),
            ("Sharma", TokenRole.SURNAME),
        )
        with pytest.raises(ValueError):
            n.merge_tokens(0, 2)

    def test_merge_fuses_text(self):
        n = name(("Ravi", TokenRole.GIVEN), ("Shankar", TokenRole.GIVEN))
        assert n.merge_tokens(0, 1).render() == "Ravishankar"
        assert n.merge_tokens(0, 1, joiner="-").render() == "Ravi-Shankar"

    def test_origins_are_deduplicated_in_order(self):
        n = ParsedName(
            (
                Token("Gurpreet", TokenRole.GIVEN, origin="punjabi"),
                Token("Singh", TokenRole.SUFFIX, origin="punjabi"),
                Token("Sharma", TokenRole.SURNAME, origin="hindi_belt"),
            )
        )
        assert n.origins == ("punjabi", "hindi_belt")

    def test_distinguishing_indices_skips_affixes(self):
        n = name(
            ("Dr", TokenRole.HONORIFIC),
            ("Rahul", TokenRole.GIVEN),
            ("Sharma", TokenRole.SURNAME),
            ("S/o", TokenRole.QUALIFIER),
        )
        assert n.distinguishing_indices() == [1, 2]

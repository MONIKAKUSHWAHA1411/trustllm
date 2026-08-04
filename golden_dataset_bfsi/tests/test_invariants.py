"""Invariant tests for the golden BFSI dataset.

These are the properties that must hold for *every* version of the dataset,
independent of how many items it contains. If one fails, the golden set is not
safe to evaluate against.
"""

from __future__ import annotations

import re
from collections import Counter

import pytest

from golden_bfsi.grid import is_valid_cell, load_grid, uncovered_specs
from golden_bfsi.items import load_items, load_schema, validate_item
from golden_bfsi.ledger import build_integrity, load_ledger

ID_RE = re.compile(r"^L0-(BNK|LND|CRD|PAY|INS|WLT)-\d{4}$")

# Patterns that raw, unmasked identifiers would match. Golden data must use
# only masked or synthetic identifiers, so none of these may appear.
PAN_RE = re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b")          # e.g. an Indian PAN
LONG_DIGIT_RE = re.compile(r"\d{12,}")                   # Aadhaar / card-length runs


@pytest.fixture(scope="module")
def grid():
    return load_grid()


@pytest.fixture(scope="module")
def items():
    return load_items()


@pytest.fixture(scope="module")
def schema():
    return load_schema()


def test_dataset_not_empty(items):
    assert items, "L0 dataset is empty"


def test_ids_unique(items):
    dupes = [i for i, n in Counter(x["id"] for x in items).items() if n > 1]
    assert not dupes, f"duplicate ids: {dupes}"


def test_id_format(items):
    bad = [x["id"] for x in items if not ID_RE.match(x["id"])]
    assert not bad, f"ids not matching {ID_RE.pattern}: {bad}"


def test_id_domain_code_matches_cell(grid, items):
    """The 3-letter code in the id must match the item's domain."""
    codes = grid["domain_codes"]
    mismatched = []
    for x in items:
        expected = codes[x["cell"]["domain"]]
        actual = x["id"].split("-")[1]
        if expected != actual:
            mismatched.append((x["id"], x["cell"]["domain"]))
    assert not mismatched, f"id code != domain: {mismatched}"


def test_schema_conformance(items, schema):
    errors = {x.get("id", "?"): validate_item(x, schema) for x in items}
    failures = {k: v for k, v in errors.items() if v}
    assert not failures, f"schema violations: {failures}"


def test_all_declared_level_l0(items):
    bad = [x["id"] for x in items if x["level"] != "L0"]
    assert not bad, f"L0 file contains non-L0 items: {bad}"


def test_cells_are_valid_grid_points(grid, items):
    bad = [x["id"] for x in items if not is_valid_cell(grid, x["cell"])]
    assert not bad, f"items whose cell is not a valid grid point: {bad}"


def test_must_cover_is_satisfied(grid, items):
    missing = uncovered_specs(grid, (x["cell"] for x in items))
    assert not missing, f"must_cover cells with no L0 item: {missing}"


def test_refusal_consistency(items):
    """Refusal task <=> must_refuse=true <=> answer_type=refusal, always at T3."""
    problems = []
    for x in items:
        is_refusal_task = x["cell"]["task"] == "refusal"
        if is_refusal_task or x["must_refuse"] or x["answer_type"] == "refusal":
            if not (is_refusal_task and x["must_refuse"] and x["answer_type"] == "refusal"):
                problems.append((x["id"], "refusal signals disagree"))
            elif x["cell"]["risk_tier"] != "T3":
                problems.append((x["id"], "refusal item not tier T3"))
    assert not problems, f"refusal inconsistencies: {problems}"


def test_reference_is_non_empty(items):
    bad = [x["id"] for x in items if not x["reference"].strip()]
    assert not bad, f"items with empty reference: {bad}"


def test_no_raw_pii_identifiers(items):
    """Golden data must never carry unmasked PAN / Aadhaar / card-length numbers."""
    hits = []
    for x in items:
        blob = f"{x['input']}\n{x['reference']}"
        if PAN_RE.search(blob) or LONG_DIGIT_RE.search(blob):
            hits.append(x["id"])
    assert not hits, f"items containing raw PII-shaped identifiers: {hits}"


def test_ledger_matches_data(items):
    """The committed ledger must be in sync with the data (no silent drift)."""
    stored = load_ledger()
    fresh = build_integrity(items)
    assert stored["corpus_digest"] == fresh["corpus_digest"], "corpus_digest drift"
    assert stored["entries"] == fresh["entries"], "ledger entries drift"


def test_ledger_covers_every_item(items):
    stored = load_ledger()
    ledger_ids = {e["id"] for e in stored["entries"]}
    data_ids = {x["id"] for x in items}
    assert ledger_ids == data_ids, (
        f"ledger/data id mismatch: only in ledger {ledger_ids - data_ids}, "
        f"only in data {data_ids - ledger_ids}"
    )


def test_corpus_digest_is_deterministic(items):
    """Rebuilding the integrity core twice yields the same digest."""
    assert build_integrity(items)["corpus_digest"] == build_integrity(items)["corpus_digest"]

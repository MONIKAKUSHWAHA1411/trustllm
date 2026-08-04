"""T-02 — L2 arithmetic reconciliation. See TASKS.md.

The `ledger` fixture (tests/conftest.py) is a clean, reconciling synthetic
statement. Tests must never touch data/raw/ (real client data).
"""

from decimal import Decimal

from golden_dataset.layers.l2_arithmetic import (
    l2_arithmetic,
    ledger_from_dict,
    reconcile_archive,
)
from golden_dataset.ledger import Ledger, Txn


def _txn(row, page, date, debit, credit, balance, narration="TXN"):
    return Txn(row=row, page=page, date=date, narration=narration,
               debit=Decimal(debit), credit=Decimal(credit), balance=Decimal(balance))


# --- the authentic base ----------------------------------------------------

def test_authentic_ledger_has_no_flags(ledger):
    res = l2_arithmetic(ledger)
    assert res["reconciles"] is True
    assert res["hard_fail"] is False
    assert res["l2_score"] == 0.0
    assert res["flags"] == []


# --- the EASY class: naive tamper breaks arithmetic ------------------------

def test_naive_tamper_is_a_hard_fail(ledger):
    """recompute=False leaves the running balance broken. L2 must catch it.

    apply_delta shifts the edited row's amount AND its balance together, so the
    edited row (2) stays self-consistent; the discontinuity surfaces at the NEXT
    row (3), whose original balance no longer follows from the inflated one. That
    is exactly what a forger who forgets to cascade leaves behind.
    """
    ledger.apply_delta(row=2, delta=Decimal("100000.00"), recompute=False)
    res = l2_arithmetic(ledger)
    assert res["hard_fail"] is True
    assert res["reconciles"] is False
    breaks = [f for f in res["flags"] if f["code"] == "L2_BALANCE_BREAK"]
    assert len(breaks) == 1, "re-anchor must yield exactly one break, not a cascade"
    assert breaks[0]["evidence"]["row"] == 3


def test_break_reports_the_exact_delta(ledger):
    """The evidence must carry the precise rupee delta an analyst can cite."""
    ledger.apply_delta(row=2, delta=Decimal("100000.00"), recompute=False)
    break_flag = next(f for f in l2_arithmetic(ledger)["flags"]
                      if f["code"] == "L2_BALANCE_BREAK")
    # At row 3: expected 395000 - 42500 = 352500, stated 252500 -> delta -100000.
    assert Decimal(break_flag["evidence"]["delta"]) == Decimal("-100000.00")


# --- the HARD class: recomputed tamper is invisible to L2 by design --------

def test_recomputed_tamper_is_invisible_to_l2(ledger):
    """recompute=True rewrites every downstream balance so arithmetic closes.

    L2 reporting a clean reconcile here is CORRECT, not a miss — this is the
    ADVERSARIAL class L1/L0 must cover. CLAUDE.md invariant 3.
    """
    ledger.apply_delta(row=2, delta=Decimal("100000.00"), recompute=True)
    res = l2_arithmetic(ledger)
    assert res["reconciles"] is True
    assert res["hard_fail"] is False


# --- re-anchoring: one break must not cascade ------------------------------

def test_single_break_does_not_cascade():
    # Row 3 balance is wrong by 500; every other row is internally consistent.
    txns = [
        _txn(1, 0, "01/04/2025", "0", "1000", "1000"),
        _txn(2, 0, "02/04/2025", "200", "0", "800"),
        _txn(3, 0, "03/04/2025", "100", "0", "1200"),   # should be 700 -> break
        _txn(4, 0, "04/04/2025", "50", "0", "1150"),     # reconciles from 1200
    ]
    res = l2_arithmetic(Ledger(txns, opening_balance=Decimal(0)))
    assert res["breaking_rows"] == [3], "re-anchor must isolate the single break"


# --- page-boundary continuity ---------------------------------------------

def test_page_discontinuity_flagged():
    # Page 0 closes at 800; page 1 opens as if it were 5000.
    txns = [
        _txn(1, 0, "01/04/2025", "0", "1000", "1000"),
        _txn(2, 0, "02/04/2025", "200", "0", "800"),
        _txn(3, 1, "03/04/2025", "0", "100", "5100"),   # 800+100=900, not 5100
    ]
    res = l2_arithmetic(Ledger(txns, opening_balance=Decimal(0)))
    codes = {f["code"] for f in res["flags"]}
    assert "L2_PAGE_DISCONTINUITY" in codes
    assert res["hard_fail"] is True


def test_clean_page_boundary_has_no_flag():
    txns = [
        _txn(1, 0, "01/04/2025", "0", "1000", "1000"),
        _txn(2, 0, "02/04/2025", "200", "0", "800"),
        _txn(3, 1, "03/04/2025", "0", "100", "900"),     # carries cleanly
    ]
    assert l2_arithmetic(Ledger(txns, opening_balance=Decimal(0)))["flags"] == []


# --- date monotonicity & sequence gaps -------------------------------------

def test_date_non_monotonic_flagged():
    txns = [
        _txn(1, 0, "10/04/2025", "0", "1000", "1000"),
        _txn(2, 0, "02/04/2025", "0", "500", "1500"),    # date goes backwards
    ]
    codes = {f["code"] for f in l2_arithmetic(Ledger(txns, Decimal(0)))["flags"]}
    assert "L2_DATE_NON_MONOTONIC" in codes


def test_row_sequence_gap_flagged():
    txns = [
        _txn(1, 0, "01/04/2025", "0", "1000", "1000"),
        _txn(3, 0, "02/04/2025", "0", "500", "1500"),    # row 2 missing
    ]
    codes = {f["code"] for f in l2_arithmetic(Ledger(txns, Decimal(0)))["flags"]}
    assert "L2_ROW_SEQUENCE_GAP" in codes


# --- money is Decimal, never float -----------------------------------------

def test_decimal_precision_no_float_drift():
    """0.1 + 0.2 != 0.3 in float; a Decimal reconciler must not spuriously break."""
    txns = [
        _txn(1, 0, "01/04/2025", "0", "0.10", "0.10"),
        _txn(2, 0, "02/04/2025", "0", "0.20", "0.30"),
    ]
    assert l2_arithmetic(Ledger(txns, opening_balance=Decimal(0)))["reconciles"] is True


# --- structured evidence ---------------------------------------------------

def test_every_flag_has_structured_evidence(ledger):
    ledger.apply_delta(row=2, delta=Decimal("100000.00"), recompute=False)
    for f in l2_arithmetic(ledger)["flags"]:
        assert {"code", "severity", "evidence"} <= set(f)
        assert "page" in f["evidence"] and "row" in f["evidence"]


# --- archive report (T-02 half two) ----------------------------------------

def test_reconcile_archive_report(ledger):
    clean = ledger.snapshot()
    tampered = ledger.snapshot()
    tampered.apply_delta(row=2, delta=Decimal("100000.00"), recompute=False)

    report = reconcile_archive([("clean-01", clean), ("tampered-01", tampered)])
    assert report["statements_scanned"] == 2
    assert report["hard_fail_count"] == 1
    assert report["hard_fail_rate"] == 0.5
    assert [r["statement_id"] for r in report["hard_fail_statements"]] == ["tampered-01"]
    assert report["flag_breakdown"].get("L2_BALANCE_BREAK") == 1


def test_empty_archive_reports_zero_not_a_finding():
    report = reconcile_archive([])
    assert report["statements_scanned"] == 0
    assert report["hard_fail_count"] == 0
    assert report["hard_fail_rate"] == 0.0


# --- serialisation round-trip (the T-01 -> T-02 contract) ------------------

def test_ledger_from_dict_roundtrip(ledger):
    payload = {
        "statement_id": "stmt-1",
        "opening_balance": str(ledger.opening_balance),
        "txns": [
            {"row": t.row, "page": t.page, "date": t.date, "narration": t.narration,
             "debit": str(t.debit), "credit": str(t.credit), "balance": str(t.balance)}
            for t in ledger.txns
        ],
    }
    rebuilt = ledger_from_dict(payload)
    assert l2_arithmetic(rebuilt)["reconciles"] is True
    assert all(isinstance(t.balance, Decimal) for t in rebuilt.txns)

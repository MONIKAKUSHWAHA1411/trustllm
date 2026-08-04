from decimal import Decimal


def test_authentic_ledger_reconciles(ledger):
    ok, breaks = ledger.verify()
    assert ok and breaks == []


def test_naive_tamper_breaks_reconciliation(ledger):
    """recompute=False -> L2 catches it. This is the EASY class."""
    ledger.apply_delta(row=2, delta=Decimal("100000.00"), recompute=False)
    ok, breaks = ledger.verify()
    assert not ok, "L2 must detect a tamper that does not fix downstream balances"


def test_recomputed_tamper_survives_reconciliation(ledger):
    """recompute=True -> L2 is blind. This is why L1 cannot be descoped."""
    changes = ledger.apply_delta(row=2, delta=Decimal("100000.00"), recompute=True)
    ok, _ = ledger.verify()
    assert ok, "a fully recomputed ledger must still reconcile - L2 has no signal here"
    assert len(changes) == 6, "delta must propagate to every downstream balance"


def test_snapshot_isolates_mutations(ledger):
    """Without snapshot(), tamper N+1 builds on tamper N and the corpus is wrong."""
    snap = ledger.snapshot()
    snap.apply_delta(row=2, delta=Decimal("50000.00"), recompute=True)
    ok, _ = ledger.verify()
    assert ok, "mutating a snapshot must not touch the original ledger"

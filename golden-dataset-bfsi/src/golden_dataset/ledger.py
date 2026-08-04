"""Transaction ledger and the recompute decision that separates EASY from HARD."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


# ---------------------------------------------------------------------------
# Ledger — the recompute decision that separates EASY from HARD
# ---------------------------------------------------------------------------

@dataclass
class Txn:
    row: int
    page: int
    date: str
    narration: str
    debit: Decimal
    credit: Decimal
    balance: Decimal
    balance_bbox: list[float] | None = None
    amount_bbox: list[float] | None = None


class Ledger:
    """
    Holds the parsed transaction ledger of an authentic statement.

    The single most important method here is `apply_delta`. For every numeric
    tamper we emit TWO variants:

      recompute=False -> running balance breaks. L2 catches it deterministically.
                         This is the EASY class. Most real-world forgers stop here.

      recompute=True  -> every downstream balance is rewritten so the arithmetic
                         still closes. L2 is blind. Detection must come from L0
                         provenance or L1 pixel forensics. This is the HARD class.

    A corpus containing only recompute=False teaches the model that fraud ==
    broken arithmetic. It will then miss every competent forger. Generate both,
    and report metrics separately.
    """

    def __init__(self, txns: list[Txn], opening_balance: Decimal):
        self.txns = txns
        self.opening_balance = opening_balance

    def snapshot(self) -> "Ledger":
        """Deep copy. The grid applies deltas repeatedly to the same base
        ledger; without this, tamper N+1 would build on tamper N's mutations
        and every downstream balance in the corpus would be wrong."""
        return Ledger(
            [Txn(t.row, t.page, t.date, t.narration, t.debit, t.credit,
                 t.balance, t.balance_bbox, t.amount_bbox) for t in self.txns],
            self.opening_balance,
        )

    def verify(self, tol: Decimal = Decimal("0.01")) -> tuple[bool, list[int]]:
        """Row-level running-balance reconciliation. Returns (ok, breaking_rows)."""
        running = self.opening_balance
        breaks: list[int] = []
        for t in self.txns:
            running = running + t.credit - t.debit
            if abs(running - t.balance) > tol:
                breaks.append(t.row)
                running = t.balance          # re-anchor so one break != all break
        return (len(breaks) == 0, breaks)

    def apply_delta(
        self,
        row: int,
        delta: Decimal,
        recompute: bool,
    ) -> list[tuple[int, Decimal, Decimal]]:
        """
        Shift the amount at `row` by `delta`.

        Returns [(row, old_balance, new_balance), ...] — every balance cell that
        must be rewritten in the document. When recompute=False that is a single
        cell; when True it is that cell and every subsequent one.
        """
        changes: list[tuple[int, Decimal, Decimal]] = []
        idx = next(i for i, t in enumerate(self.txns) if t.row == row)

        t = self.txns[idx]
        if t.credit > 0:
            t.credit += delta
        else:
            t.debit -= delta

        old = t.balance
        t.balance = old + delta
        changes.append((t.row, old, t.balance))

        if recompute:
            for nxt in self.txns[idx + 1:]:
                old_b = nxt.balance
                nxt.balance = old_b + delta
                changes.append((nxt.row, old_b, nxt.balance))

        return changes



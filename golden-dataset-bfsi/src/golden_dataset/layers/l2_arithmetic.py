"""L2 - arithmetic and internal consistency. No model. Highest-precision layer.

Port of ``balance_reconcile_v2`` (BSA repo) into the layer cascade. See TASKS.md
T-02. This is an *anchored global solver*: it walks the ledger once, checks the
running balance at every row, re-anchors after a break so a single bad row does
not cascade into "every row is broken", and returns structured evidence an
analyst can act on under the RBI show-cause requirement.

Design notes (why this layer is worth its precision):

- Money is ``Decimal``, never ``float``. A float running-balance reconciler
  produces spurious sub-paise breaks and you chase them for days. Every amount
  arriving here is already ``Decimal`` (see ``ledger.Txn``); we never coerce.
- ``recompute=True`` tampers are *invisible* here by construction — every
  downstream balance was rewritten so the arithmetic still closes. That is the
  HARD class, and L2 reporting a clean reconcile on such a sample is correct,
  not a miss. Detection of that class is L0/L1's job. See CLAUDE.md invariant 3.
- Every flag carries ``page``, ``row`` and the exact ``delta``. A RED_FLAG an
  analyst cannot justify in writing is useless.

The public entry point is :func:`l2_arithmetic`. :func:`reconcile_archive`
applies it across a whole archive and produces the T-02 CTO report; it consumes
serialised ledgers (the format T-01 ingest emits) so it is ready the moment
real statements are parsed.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from datetime import datetime
from decimal import Decimal
from typing import Any

from golden_dataset.ledger import Ledger, Txn

# Shared with L0 so scores are comparable when L6 fuses layer outputs.
SEVERITY_WEIGHT = {"HIGH": 0.45, "MEDIUM": 0.18, "LOW": 0.06}

# Indian bank statements are near-universally DD/MM/YYYY; accept a couple of
# common variants rather than false-flag a parseable date as unreadable.
_DATE_FORMATS = ("%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y", "%Y-%m-%d")

DEFAULT_TOL = Decimal("0.01")


def _parse_date(raw: str) -> datetime | None:
    raw = (raw or "").strip()
    for fmt in _DATE_FORMATS:
        try:
            # Statement dates are date-only; a tz-aware parse would be wrong.
            return datetime.strptime(raw, fmt)  # noqa: DTZ007
        except ValueError:
            continue
    return None


def _flag(code: str, severity: str, evidence: dict[str, Any]) -> dict[str, Any]:
    return {"code": code, "severity": severity, "evidence": evidence}


def l2_arithmetic(ledger: Ledger, *, tol: Decimal = DEFAULT_TOL) -> dict[str, Any]:
    """Reconcile a parsed ledger and return arithmetic-consistency flags.

    Returns a dict shaped like the other layers::

        {
          "l2_score": float,          # min(1.0, weighted flag severity)
          "hard_fail": bool,          # any HIGH flag — the deterministic verdict
          "reconciles": bool,         # no balance/page-continuity break
          "flag_count": int,
          "breaking_rows": [int, ...],
          "flags": [{"code", "severity", "evidence": {...}}, ...],
        }

    ``hard_fail`` is the number that matters for the T-02 precision target: a
    HIGH flag here is a deterministic arithmetic contradiction, not a soft score.
    """
    flags: list[dict[str, Any]] = []

    running = ledger.opening_balance
    prev_page: int | None = None
    prev_row: int | None = None
    prev_date: datetime | None = None
    prev_date_raw: str | None = None

    for t in ledger.txns:
        # --- entry-level consistency -------------------------------------
        if t.debit < 0 or t.credit < 0:
            flags.append(_flag(
                "L2_NEGATIVE_AMOUNT", "HIGH",
                {"page": t.page, "row": t.row,
                 "debit": str(t.debit), "credit": str(t.credit)},
            ))
        if t.debit > 0 and t.credit > 0:
            flags.append(_flag(
                "L2_AMBIGUOUS_ENTRY", "MEDIUM",
                {"page": t.page, "row": t.row,
                 "debit": str(t.debit), "credit": str(t.credit)},
            ))

        # --- transaction-sequence gaps (within a page) -------------------
        if prev_row is not None and t.page == prev_page and t.row != prev_row + 1:
            flags.append(_flag(
                "L2_ROW_SEQUENCE_GAP", "MEDIUM",
                {"page": t.page, "expected_row": prev_row + 1, "got_row": t.row},
            ))

        # --- running-balance reconciliation ------------------------------
        expected = running + t.credit - t.debit
        delta = t.balance - expected
        if abs(delta) > tol:
            page_boundary = prev_page is not None and t.page != prev_page
            code = "L2_PAGE_DISCONTINUITY" if page_boundary else "L2_BALANCE_BREAK"
            flags.append(_flag(
                code, "HIGH",
                {"page": t.page, "row": t.row,
                 "expected_balance": str(expected),
                 "stated_balance": str(t.balance),
                 "delta": str(delta)},
            ))
            running = t.balance          # re-anchor: one break must not cascade
        else:
            running = expected

        # --- date monotonicity -------------------------------------------
        d = _parse_date(t.date)
        if d is None:
            flags.append(_flag(
                "L2_DATE_UNPARSEABLE", "LOW",
                {"page": t.page, "row": t.row, "date": t.date},
            ))
        else:
            if prev_date is not None and d < prev_date:
                flags.append(_flag(
                    "L2_DATE_NON_MONOTONIC", "MEDIUM",
                    {"page": t.page, "row": t.row,
                     "prev_date": prev_date_raw, "date": t.date},
                ))
            prev_date, prev_date_raw = d, t.date

        prev_page, prev_row = t.page, t.row

    score = min(1.0, sum(SEVERITY_WEIGHT[f["severity"]] for f in flags))
    breaking_rows = [
        f["evidence"]["row"] for f in flags
        if f["code"] in ("L2_BALANCE_BREAK", "L2_PAGE_DISCONTINUITY")
    ]
    return {
        "l2_score": round(score, 3),
        "hard_fail": any(f["severity"] == "HIGH" for f in flags),
        "reconciles": not breaking_rows,
        "flag_count": len(flags),
        "breaking_rows": breaking_rows,
        "flags": flags,
    }


# Uniform with the other layer stubs, which expose ``run``.
run = l2_arithmetic


# ---------------------------------------------------------------------------
# Ledger (de)serialisation — the contract T-01 ingest emits and T-02 consumes
# ---------------------------------------------------------------------------

def ledger_from_dict(d: dict[str, Any]) -> Ledger:
    """Rebuild a :class:`Ledger` from a plain dict. All money -> ``Decimal``."""
    txns = [
        Txn(
            row=int(t["row"]),
            page=int(t.get("page", 0)),
            date=str(t.get("date", "")),
            narration=str(t.get("narration", "")),
            debit=Decimal(str(t.get("debit", "0"))),
            credit=Decimal(str(t.get("credit", "0"))),
            balance=Decimal(str(t["balance"])),
            balance_bbox=t.get("balance_bbox"),
            amount_bbox=t.get("amount_bbox"),
        )
        for t in d["txns"]
    ]
    return Ledger(txns, opening_balance=Decimal(str(d["opening_balance"])))


def load_archive(input_dir: Any) -> Iterator[tuple[str, Ledger]]:
    """Yield ``(statement_id, Ledger)`` for every ``*.ledger.json`` in a dir.

    The T-01 ingest is expected to write one such file per authentic statement.
    Until it exists this simply yields nothing — the report then honestly says
    zero statements were scanned rather than inventing a finding.
    """
    import json
    from pathlib import Path

    root = Path(input_dir)
    if not root.exists():
        return
    for path in sorted(root.glob("*.ledger.json")):
        with open(path, encoding="utf-8") as fh:
            payload = json.load(fh)
        statement_id = payload.get("statement_id", path.stem)
        yield statement_id, ledger_from_dict(payload)


def reconcile_archive(
    ledgers: Iterable[tuple[str, Ledger]],
    *,
    tol: Decimal = DEFAULT_TOL,
) -> dict[str, Any]:
    """Run L2 across an archive and produce the T-02 report.

    The headline is ``hard_fail_statements``: any *already-approved* statement
    that fails reconciliation as received is either a parser bug or a fraud that
    was already funded. Both are worth putting in front of the CTO.
    """
    records: list[dict[str, Any]] = []
    flag_breakdown: dict[str, int] = {}
    hard_fail = 0

    for statement_id, ledger in ledgers:
        res = l2_arithmetic(ledger, tol=tol)
        records.append({
            "statement_id": statement_id,
            "hard_fail": res["hard_fail"],
            "l2_score": res["l2_score"],
            "reconciles": res["reconciles"],
            "breaking_rows": res["breaking_rows"],
            "flags": res["flags"],
        })
        if res["hard_fail"]:
            hard_fail += 1
        for f in res["flags"]:
            flag_breakdown[f["code"]] = flag_breakdown.get(f["code"], 0) + 1

    scanned = len(records)
    return {
        "statements_scanned": scanned,
        "hard_fail_count": hard_fail,
        "hard_fail_rate": round(hard_fail / scanned, 4) if scanned else 0.0,
        "flag_breakdown": flag_breakdown,
        "hard_fail_statements": [r for r in records if r["hard_fail"]],
        "records": records,
    }
